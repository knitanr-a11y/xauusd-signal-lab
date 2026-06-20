from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from stage260_live_replay_contract import candidate_key

STATE_VERSION = "E6_V1"
EVENT_TYPE = "E6_FAILED_DISPLACEMENT_REVERSAL"


@dataclass
class Setup:
    original_direction: str
    anchor_time: pd.Timestamp
    anchor_start_time: pd.Timestamp
    anchor_start_price: float
    anchor_end_price: float
    anchor_move: float
    anchor_atr14: float
    efficiency: float
    anchor_bar_index: int
    state: str = "ANCHOR_ACTIVE"
    failure_bar_index: int | None = None
    failure_time: pd.Timestamp | None = None
    failure_type: str | None = None

    @property
    def direction(self) -> str:
        return "SHORT" if self.original_direction == "LONG" else "LONG"

    @property
    def midpoint(self) -> float:
        s = -1 if self.original_direction == "LONG" else 1
        return self.anchor_end_price + s * 0.50 * self.anchor_move

    @property
    def invalid65(self) -> float:
        s = -1 if self.original_direction == "LONG" else 1
        return self.anchor_end_price + s * 0.65 * self.anchor_move

    @property
    def reversal_level(self) -> float:
        s = 1 if self.original_direction == "LONG" else -1
        return self.anchor_start_price + s * 0.20 * self.anchor_move

    @property
    def reclaim_level(self) -> float:
        s = -1 if self.original_direction == "LONG" else 1
        return self.anchor_end_price + s * 0.20 * self.anchor_move

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> "Setup":
        v = dict(value)
        for c in ("anchor_time", "anchor_start_time", "failure_time"):
            if v.get(c) is not None:
                v[c] = pd.Timestamp(v[c])
        return cls(**v)


def prepare_m15_context(m15: pd.DataFrame, h1_context: pd.DataFrame, h4_context: pd.DataFrame) -> pd.DataFrame:
    x = m15.sort_values("time").copy().reset_index(drop=True)
    x["time"] = pd.to_datetime(x["time"], errors="raise")
    x["source_close_time"] = pd.to_datetime(x["source_close_time"], errors="raise")
    x["decision_time"] = x["source_close_time"]
    pc = x["close"].shift(1)
    x["m15_tr"] = pd.concat(
        [x["high"] - x["low"], (x["high"] - pc).abs(), (x["low"] - pc).abs()], axis=1
    ).max(axis=1)
    x = pd.merge_asof(
        x.sort_values("decision_time"), h1_context.sort_values("source_close_time"),
        left_on="decision_time", right_on="source_close_time", direction="backward",
        allow_exact_matches=True, suffixes=("", "_h1src"),
    )
    x = pd.merge_asof(
        x.sort_values("decision_time"), h4_context.sort_values("source_close_time"),
        left_on="decision_time", right_on="source_close_time", direction="backward",
        allow_exact_matches=True, suffixes=("", "_h4src"),
    )
    if (x["source_close_time_h1src"] > x["decision_time"]).fillna(False).any():
        raise AssertionError("H1 lookahead")
    if (x["source_close_time_h4src"] > x["decision_time"]).fillna(False).any():
        raise AssertionError("H4 lookahead")
    return x.reset_index(drop=True)


def _anchor(three: list[dict[str, Any]], i: int) -> dict[str, Any] | None:
    if len(three) != 3:
        return None
    times = [pd.Timestamp(r["time"]) for r in three]
    if times[1] - times[0] != pd.Timedelta(minutes=15) or times[2] - times[1] != pd.Timedelta(minutes=15):
        return None
    atr = float(three[-1]["h1_atr14"])
    if not np.isfinite(atr) or atr <= 0:
        return None
    start, end = float(three[0]["open"]), float(three[-1]["close"])
    net, move = end - start, abs(end - start)
    tr_sum = sum(float(r["m15_tr"]) for r in three)
    if move < 0.80 * atr or tr_sum <= 0 or move / tr_sum < 0.70:
        return None
    hi = max(float(r["high"]) for r in three)
    lo = min(float(r["low"]) for r in three)
    span = hi - lo
    if span <= 0:
        return None
    bull = sum(float(r["close"]) > float(r["open"]) for r in three)
    bear = sum(float(r["close"]) < float(r["open"]) for r in three)
    if net > 0 and bull >= 2 and end >= hi - 0.20 * span:
        d = "LONG"
    elif net < 0 and bear >= 2 and end <= lo + 0.20 * span:
        d = "SHORT"
    else:
        return None
    return {
        "original_direction": d,
        "anchor_time": pd.Timestamp(three[-1]["decision_time"]),
        "anchor_start_time": times[0],
        "anchor_start_price": start,
        "anchor_end_price": end,
        "anchor_move": move,
        "anchor_atr14": atr,
        "anchor_move_atr": move / atr,
        "efficiency": move / tr_sum,
        "anchor_bar_index": int(i),
        "h1_atr_band": str(three[-1].get("h1_atr_band", "")),
        "h4_atr_band": str(three[-1].get("h4_atr_band", "")),
    }


def _failure(setup: Setup, bar: dict[str, Any] | pd.Series) -> str | None:
    c, h, l = float(bar["close"]), float(bar["high"]), float(bar["low"])
    if setup.original_direction == "LONG":
        if c <= setup.invalid65:
            return "INVALID_CLOSE_65"
        if l < setup.midpoint and c <= setup.midpoint:
            return "DEEP_CLOSE_50"
    else:
        if c >= setup.invalid65:
            return "INVALID_CLOSE_65"
        if h > setup.midpoint and c >= setup.midpoint:
            return "DEEP_CLOSE_50"
    return None


def _accepted(setup: Setup, bar: dict[str, Any] | pd.Series, prev_close: float) -> bool:
    c, o = float(bar["close"]), float(bar["open"])
    if setup.original_direction == "LONG":
        return c <= setup.reversal_level and c < prev_close and c < o
    return c >= setup.reversal_level and c > prev_close and c > o


def _reclaimed(setup: Setup, bar: dict[str, Any] | pd.Series) -> bool:
    c = float(bar["close"])
    return c >= setup.reclaim_level if setup.original_direction == "LONG" else c <= setup.reclaim_level


def _event(setup: Setup, bar: dict[str, Any] | pd.Series) -> dict[str, Any]:
    t = pd.Timestamp(bar["decision_time"])
    return {
        "candidate_key": candidate_key(EVENT_TYPE, setup.direction, setup.anchor_time, t),
        "event_type": EVENT_TYPE,
        "direction": setup.direction,
        "original_direction": setup.original_direction,
        "anchor_time": setup.anchor_time,
        "anchor_start_time": setup.anchor_start_time,
        "failure_time": setup.failure_time,
        "decision_time": t,
        "entry_time": t,
        "entry_price_source_time": t,
        "state_version": STATE_VERSION,
        "anchor_start_price": setup.anchor_start_price,
        "anchor_end_price": setup.anchor_end_price,
        "anchor_move": setup.anchor_move,
        "anchor_atr14": setup.anchor_atr14,
        "anchor_move_atr": setup.anchor_move / setup.anchor_atr14,
        "efficiency": setup.efficiency,
        "failure_type": setup.failure_type,
        "reversal_acceptance_close": float(bar["close"]),
        "h1_atr_band": str(bar.get("h1_atr_band", "")),
        "h4_atr_band": str(bar.get("h4_atr_band", "")),
        "weekday": int(t.weekday()), "server_hour": int(t.hour),
        "month": t.strftime("%Y-%m"), "quarter": f"{t.year}Q{t.quarter}",
        "half": f"{t.year}H{1 if t.month <= 6 else 2}",
    }


class E6StreamingDetector:
    def __init__(self) -> None:
        self.history: deque[dict[str, Any]] = deque(maxlen=3)
        self.raw_history = {"LONG": deque(), "SHORT": deque()}
        self.active: dict[str, Setup | None] = {"LONG": None, "SHORT": None}
        self.raw_anchors: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.resolutions: list[dict[str, Any]] = []
        self.global_trade_active_until = pd.Timestamp.min
        self.last_bar_time: pd.Timestamp | None = None
        self.bar_index = -1

    def snapshot(self) -> dict[str, Any]:
        return {
            "history": list(self.history),
            "raw_history": {k: list(v) for k, v in self.raw_history.items()},
            "active": {k: None if v is None else v.snapshot() for k, v in self.active.items()},
            "raw_anchors": list(self.raw_anchors), "failures": list(self.failures),
            "events": list(self.events), "resolutions": list(self.resolutions),
            "global_trade_active_until": self.global_trade_active_until,
            "last_bar_time": self.last_bar_time, "bar_index": self.bar_index,
        }

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> "E6StreamingDetector":
        o = cls()
        o.history = deque(value.get("history", []), maxlen=3)
        o.raw_history = {k: deque((int(i), float(m)) for i, m in value["raw_history"].get(k, [])) for k in ("LONG", "SHORT")}
        o.active = {k: None if value["active"].get(k) is None else Setup.from_snapshot(value["active"][k]) for k in ("LONG", "SHORT")}
        o.raw_anchors, o.failures = list(value.get("raw_anchors", [])), list(value.get("failures", []))
        o.events, o.resolutions = list(value.get("events", [])), list(value.get("resolutions", []))
        o.global_trade_active_until = pd.Timestamp(value.get("global_trade_active_until", pd.Timestamp.min))
        o.last_bar_time = None if value.get("last_bar_time") is None else pd.Timestamp(value["last_bar_time"])
        o.bar_index = int(value.get("bar_index", -1))
        return o

    def _resolve(self, d: str, reason: str, bar: dict[str, Any]) -> None:
        s = self.active[d]
        if s is None:
            return
        self.resolutions.append({"original_direction": d, "anchor_time": s.anchor_time,
                                 "failure_time": s.failure_time,
                                 "resolution_time": pd.Timestamp(bar["decision_time"]),
                                 "resolution": reason})
        self.active[d] = None

    def _update(self, d: str, bar: dict[str, Any]) -> bool:
        s = self.active[d]
        if s is None:
            return False
        i = self.bar_index
        if s.state == "ANCHOR_ACTIVE":
            if i - s.anchor_bar_index > 6:
                self._resolve(d, "EXPIRED_FAILURE", bar); return True
            f = _failure(s, bar)
            if f is not None:
                s.state, s.failure_bar_index = "FAILURE_SEEN", i
                s.failure_time, s.failure_type = pd.Timestamp(bar["decision_time"]), f
                self.failures.append({"original_direction": d, "direction": s.direction,
                                      "anchor_time": s.anchor_time, "failure_time": s.failure_time,
                                      "failure_type": f, "anchor_move": s.anchor_move,
                                      "anchor_atr14": s.anchor_atr14, "efficiency": s.efficiency})
        if s.state == "FAILURE_SEEN":
            assert s.failure_bar_index is not None
            if i - s.failure_bar_index > 3:
                self._resolve(d, "EXPIRED_REVERSAL", bar); return True
            prev = float(self.history[-1]["close"]) if self.history else np.nan
            if np.isfinite(prev) and _accepted(s, bar, prev):
                e = _event(s, bar)
                if e["decision_time"] >= self.global_trade_active_until:
                    self.events.append(e)
                    self.global_trade_active_until = e["entry_time"] + pd.Timedelta(minutes=120)
                    self._resolve(d, "REVERSAL_ACCEPTED_EMITTED", bar)
                else:
                    self._resolve(d, "REVERSAL_ACCEPTED_DEDUP_SUPPRESSED", bar)
                return True
            if _reclaimed(s, bar):
                self._resolve(d, "ORIGINAL_DIRECTION_RECLAIMED", bar); return True
        return False

    def on_bar(self, bar: pd.Series | dict[str, Any]) -> None:
        b = bar.to_dict() if isinstance(bar, pd.Series) else dict(bar)
        t = pd.Timestamp(b["time"])
        if pd.Timestamp(b["decision_time"]) != pd.Timestamp(b["source_close_time"]):
            raise ValueError("decision_time must equal source_close_time")
        if self.last_bar_time is not None and t <= self.last_bar_time:
            raise ValueError("bars must be strictly increasing")
        self.bar_index += 1
        gap = self.last_bar_time is not None and t - self.last_bar_time != pd.Timedelta(minutes=15)
        if gap:
            for d in ("LONG", "SHORT"):
                if self.active[d] is not None:
                    self._resolve(d, "GAP", b)
            self.history.clear(); self.raw_history = {"LONG": deque(), "SHORT": deque()}
        resolved = {d: self._update(d, b) for d in ("LONG", "SHORT")}
        records = list(self.history) + [b]
        a = _anchor(records[-3:], self.bar_index) if len(records) >= 3 else None
        if a is not None:
            d = a["original_direction"]
            hist = self.raw_history[d]
            while hist and self.bar_index - hist[0][0] > 8:
                hist.popleft()
            suppressed = any(m >= a["anchor_move"] for _, m in hist)
            hist.append((self.bar_index, a["anchor_move"]))
            a.update({"suppressed_prior8": suppressed,
                      "suppressed_active": self.active[d] is not None,
                      "suppressed_resolution_bar": bool(resolved[d])})
            self.raw_anchors.append(a.copy())
            if not suppressed and self.active[d] is None and not resolved[d]:
                self.active[d] = Setup(
                    original_direction=d, anchor_time=a["anchor_time"],
                    anchor_start_time=a["anchor_start_time"],
                    anchor_start_price=a["anchor_start_price"],
                    anchor_end_price=a["anchor_end_price"], anchor_move=a["anchor_move"],
                    anchor_atr14=a["anchor_atr14"], efficiency=a["efficiency"],
                    anchor_bar_index=self.bar_index,
                )
        self.history.append(b); self.last_bar_time = t

    def event_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.events)


def detect_e6_streaming(context: pd.DataFrame):
    d = E6StreamingDetector()
    for bar in context.to_dict(orient="records"):
        d.on_bar(bar)
    return pd.DataFrame(d.raw_anchors), pd.DataFrame(d.failures), d.event_frame(), d


def detect_e6_batch(context: pd.DataFrame):
    records = context.to_dict(orient="records")
    raw, failures, candidates = [], [], []
    hist = {"LONG": deque(), "SHORT": deque()}
    for i in range(len(records)):
        if i and pd.Timestamp(records[i]["time"]) - pd.Timestamp(records[i-1]["time"]) != pd.Timedelta(minutes=15):
            hist = {"LONG": deque(), "SHORT": deque()}
        a = _anchor(records[max(0, i-2):i+1], i)
        if a is None:
            continue
        d = a["original_direction"]
        while hist[d] and i - hist[d][0][0] > 8:
            hist[d].popleft()
        a["suppressed_prior8"] = any(m >= a["anchor_move"] for _, m in hist[d])
        hist[d].append((i, a["anchor_move"])); raw.append(a)
    available, resolution_bar = {"LONG": -1, "SHORT": -1}, {"LONG": -1, "SHORT": -1}
    for a in raw:
        d, i = a["original_direction"], int(a["anchor_bar_index"])
        if a["suppressed_prior8"] or i <= available[d] or i == resolution_bar[d]:
            continue
        s = Setup(d, a["anchor_time"], a["anchor_start_time"], a["anchor_start_price"],
                  a["anchor_end_price"], a["anchor_move"], a["anchor_atr14"],
                  a["efficiency"], i)
        failure_i = None; end_i = min(i + 7, len(records) - 1)
        for j in range(i + 1, min(i + 7, len(records))):
            if pd.Timestamp(records[j]["time"]) - pd.Timestamp(records[j-1]["time"]) != pd.Timedelta(minutes=15):
                end_i = j; break
            f = _failure(s, records[j])
            if f is not None:
                failure_i = j; s.state = "FAILURE_SEEN"; s.failure_bar_index = j
                s.failure_time = pd.Timestamp(records[j]["decision_time"]); s.failure_type = f
                failures.append({"original_direction": d, "direction": s.direction,
                                 "anchor_time": s.anchor_time, "failure_time": s.failure_time,
                                 "failure_type": f, "anchor_move": s.anchor_move,
                                 "anchor_atr14": s.anchor_atr14, "efficiency": s.efficiency})
                break
        if failure_i is not None:
            end_i = min(failure_i + 4, len(records) - 1)
            for j in range(failure_i, min(failure_i + 4, len(records))):
                if j > failure_i and pd.Timestamp(records[j]["time"]) - pd.Timestamp(records[j-1]["time"]) != pd.Timedelta(minutes=15):
                    end_i = j; break
                if _accepted(s, records[j], float(records[j-1]["close"])):
                    candidates.append(_event(s, records[j])); end_i = j; break
                if _reclaimed(s, records[j]):
                    end_i = j; break
        available[d] = resolution_bar[d] = end_i
    events = pd.DataFrame(candidates).sort_values("decision_time").reset_index(drop=True) if candidates else pd.DataFrame()
    if not events.empty:
        keep, active_until = [], pd.Timestamp.min
        for i, t in enumerate(events["entry_time"]):
            if pd.Timestamp(t) >= active_until:
                keep.append(i); active_until = pd.Timestamp(t) + pd.Timedelta(minutes=120)
        events = events.iloc[keep].reset_index(drop=True)
    return pd.DataFrame(raw), pd.DataFrame(failures), events
