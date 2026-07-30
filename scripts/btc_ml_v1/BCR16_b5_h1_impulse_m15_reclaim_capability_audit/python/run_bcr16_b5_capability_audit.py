from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

EXPECTED_INPUT_SHA256 = "b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
EXPECTED_INPUT_ROWS = 30_661
DEFAULT_INPUT = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv")
PACKAGE_NAME = "BCR16_B5_OUTCOME_BLIND_CAPABILITY_AUDIT_20260731.zip"
FIXED_ZIP_DT = (2026, 7, 31, 0, 0, 0)
M15 = pd.Timedelta(minutes=15)
H1 = pd.Timedelta(hours=1)

MACHINES = (
    ("TRACK_B_B5_R06_B075_W08_H1_IMPULSE_M15_RECLAIM", 6, 0.75, 8),
    ("TRACK_B_B5_R06_B075_W16_H1_IMPULSE_M15_RECLAIM", 6, 0.75, 16),
    ("TRACK_B_B5_R06_B100_W08_H1_IMPULSE_M15_RECLAIM", 6, 1.00, 8),
    ("TRACK_B_B5_R06_B100_W16_H1_IMPULSE_M15_RECLAIM", 6, 1.00, 16),
    ("TRACK_B_B5_R12_B075_W08_H1_IMPULSE_M15_RECLAIM", 12, 0.75, 8),
    ("TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM", 12, 0.75, 16),
    ("TRACK_B_B5_R12_B100_W08_H1_IMPULSE_M15_RECLAIM", 12, 1.00, 8),
    ("TRACK_B_B5_R12_B100_W16_H1_IMPULSE_M15_RECLAIM", 12, 1.00, 16),
)

FORBIDDEN_OUTPUT_COLUMNS = {
    "return", "win_loss", "pf", "pnl", "mfe", "mae", "future_exit_result",
    "entry_price", "exit_price", "profit", "loss", "r_multiple",
}


@dataclass(frozen=True)
class MachineSpec:
    machine_id: str
    prior_h1_range: int
    impulse_body_atr: float
    pullback_deadline: int


@dataclass
class RuntimeState:
    state: str = "IDLE"
    direction: str | None = None
    impulse_h1_open: pd.Timestamp | None = None
    impulse_end_time: pd.Timestamp | None = None
    impulse_origin: float | None = None
    impulse_extreme: float | None = None
    impulse_range: float | None = None
    frozen_h1_atr: float | None = None
    near_boundary: float | None = None
    deep_boundary: float | None = None
    pullback_time: pd.Timestamp | None = None
    entry_time: pd.Timestamp | None = None
    reclaim_time: pd.Timestamp | None = None

    def clear(self) -> None:
        self.__dict__.update(RuntimeState().__dict__)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _prefix_candidates(raw: bytes, expected_rows: int) -> Iterable[bytes]:
    lines = raw.splitlines(keepends=True)
    need = expected_rows + 1
    if len(lines) < need:
        return ()
    prefix = b"".join(lines[:need])
    candidates = [prefix]
    if prefix.endswith(b"\r\n"):
        candidates.append(prefix[:-2])
    elif prefix.endswith((b"\n", b"\r")):
        candidates.append(prefix[:-1])
    return candidates


def resolve_frozen_input(source: Path, work_dir: Path, allow_prefix_rehydrate: bool) -> tuple[Path, dict[str, Any]]:
    if not source.exists():
        raise FileNotFoundError(f"BCR16 input not found: {source}")
    actual_sha = sha256_file(source)
    if actual_sha == EXPECTED_INPUT_SHA256:
        return source, {
            "source_path": str(source),
            "source_sha256": actual_sha,
            "frozen_sha256": actual_sha,
            "prefix_rehydrated": False,
        }
    if not allow_prefix_rehydrate:
        raise ValueError("Input SHA mismatch and prefix rehydration was not enabled")
    raw = source.read_bytes()
    work_dir.mkdir(parents=True, exist_ok=True)
    for candidate in _prefix_candidates(raw, EXPECTED_INPUT_ROWS):
        if sha256_bytes(candidate) == EXPECTED_INPUT_SHA256:
            out = work_dir / "frozen_btc_m15_snapshot.csv"
            out.write_bytes(candidate)
            return out, {
                "source_path": str(source),
                "source_sha256": actual_sha,
                "frozen_sha256": EXPECTED_INPUT_SHA256,
                "prefix_rehydrated": True,
                "prefix_rows": EXPECTED_INPUT_ROWS,
            }
    raise ValueError(
        "Input SHA mismatch and no byte-exact 30,661-row prefix reproduced the frozen SHA; "
        "no similar-file, nearest-row, sorting, or interpolation fallback is permitted"
    )


def _wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    tr = np.empty(len(high), dtype=float)
    tr[0] = high[0] - low[0]
    if len(high) > 1:
        prev = close[:-1]
        tr[1:] = np.maximum.reduce([high[1:] - low[1:], np.abs(high[1:] - prev), np.abs(low[1:] - prev)])
    atr = np.full(len(high), np.nan, dtype=float)
    if len(high) >= 14:
        atr[13] = float(np.mean(tr[:14]))
        for i in range(14, len(high)):
            atr[i] = (atr[i - 1] * 13.0 + tr[i]) / 14.0
    return atr


def read_m15(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [str(c).strip().lower().lstrip("\ufeff") for c in df.columns]
    aliases = {"datetime": "time", "date_time": "time", "timestamp": "time"}
    df = df.rename(columns={c: aliases.get(c, c) for c in df.columns})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required M15 columns: {missing}; got {list(df.columns)}")
    df = df[required].copy()
    df["time"] = pd.to_datetime(df["time"], errors="raise")
    if getattr(df["time"].dt, "tz", None) is not None:
        raise ValueError("BCR16 requires naive MT5 broker-server timestamps")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="raise").astype(float)
    if len(df) != EXPECTED_INPUT_ROWS:
        raise ValueError(f"Frozen row-count mismatch: expected {EXPECTED_INPUT_ROWS}, got {len(df)}")
    if df["time"].duplicated().any():
        raise ValueError("Duplicate M15 open timestamp")
    if not df["time"].is_monotonic_increasing:
        raise ValueError("M15 rows are not strictly increasing; implicit sorting is forbidden")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("OHLC integrity failure: high")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("OHLC integrity failure: low")
    return add_m15_features(df)


def add_m15_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    gap = out["time"].diff().ne(M15)
    gap.iloc[0] = True
    out["segment_id"] = gap.cumsum().astype(int)
    out["segment_pos"] = out.groupby("segment_id").cumcount().astype(int)
    out["atr14"] = np.nan
    for _, idx in out.groupby("segment_id", sort=False).groups.items():
        pos = np.asarray(list(idx), dtype=int)
        atr = _wilder_atr(
            out.loc[pos, "high"].to_numpy(float),
            out.loc[pos, "low"].to_numpy(float),
            out.loc[pos, "close"].to_numpy(float),
        )
        out.loc[pos, "atr14"] = atr
    return out


def build_complete_h1(m15: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    temp = m15.copy()
    temp["h1_open"] = temp["time"].dt.floor("h")
    for h1_open, group in temp.groupby("h1_open", sort=True):
        g = group.sort_values("time")
        expected = [h1_open + pd.Timedelta(minutes=m) for m in (0, 15, 30, 45)]
        actual = list(pd.to_datetime(g["time"]))
        if actual != expected:
            continue
        rows.append({
            "time": h1_open,
            "end_time": h1_open + H1,
            "open": float(g.iloc[0]["open"]),
            "high": float(g["high"].max()),
            "low": float(g["low"].min()),
            "close": float(g.iloc[-1]["close"]),
        })
    h1 = pd.DataFrame(rows)
    if h1.empty:
        return pd.DataFrame(columns=["time", "end_time", "open", "high", "low", "close", "atr14", "segment_id"])
    gap = h1["time"].diff().ne(H1)
    gap.iloc[0] = True
    h1["segment_id"] = gap.cumsum().astype(int)
    h1["atr14"] = np.nan
    for _, idx in h1.groupby("segment_id", sort=False).groups.items():
        pos = np.asarray(list(idx), dtype=int)
        h1.loc[pos, "atr14"] = _wilder_atr(
            h1.loc[pos, "high"].to_numpy(float),
            h1.loc[pos, "low"].to_numpy(float),
            h1.loc[pos, "close"].to_numpy(float),
        )
        for lookback in (6, 12):
            highs = pd.Series(h1.loc[pos, "high"].to_numpy(float), index=pos).rolling(lookback, min_periods=lookback).max().shift(1)
            lows = pd.Series(h1.loc[pos, "low"].to_numpy(float), index=pos).rolling(lookback, min_periods=lookback).min().shift(1)
            h1.loc[pos, f"prior_high_{lookback}"] = highs.to_numpy()
            h1.loc[pos, f"prior_low_{lookback}"] = lows.to_numpy()
    return h1.reset_index(drop=True)


def _bars_between(later: pd.Timestamp, earlier: pd.Timestamp) -> int:
    return int(round((later - earlier).total_seconds() / 900.0))


def _impulse_flags(h1: pd.DataFrame, idx: int, spec: MachineSpec) -> tuple[bool, bool, dict[str, float]]:
    if idx <= 0:
        return False, False, {}
    atr = float(h1.at[idx - 1, "atr14"])
    prior_high = float(h1.at[idx, f"prior_high_{spec.prior_h1_range}"])
    prior_low = float(h1.at[idx, f"prior_low_{spec.prior_h1_range}"])
    if not (math.isfinite(atr) and atr > 0 and math.isfinite(prior_high) and math.isfinite(prior_low)):
        return False, False, {}
    o = float(h1.at[idx, "open"])
    hi = float(h1.at[idx, "high"])
    lo = float(h1.at[idx, "low"])
    c = float(h1.at[idx, "close"])
    rng = hi - lo
    if rng <= 0:
        return False, False, {}
    long_flag = (
        c >= prior_high + 0.25 * atr
        and c > o
        and c - o >= spec.impulse_body_atr * atr
        and c >= lo + 0.75 * rng
    )
    short_flag = (
        c <= prior_low - 0.25 * atr
        and c < o
        and o - c >= spec.impulse_body_atr * atr
        and c <= hi - 0.75 * rng
    )
    return bool(long_flag), bool(short_flag), {"atr": atr, "open": o, "high": hi, "low": lo, "range": rng}


def _invalidated(close: float, state: RuntimeState) -> bool:
    assert state.impulse_origin is not None and state.frozen_h1_atr is not None
    if state.direction == "LONG":
        return close < state.impulse_origin - 0.25 * state.frozen_h1_atr
    return close > state.impulse_origin + 0.25 * state.frozen_h1_atr


def _pullback_overlap(high: float, low: float, state: RuntimeState) -> bool:
    assert state.near_boundary is not None and state.deep_boundary is not None
    zone_low = min(state.near_boundary, state.deep_boundary)
    zone_high = max(state.near_boundary, state.deep_boundary)
    return low <= zone_high and high >= zone_low


def _reclaim(m15: pd.DataFrame, j: int, state: RuntimeState) -> bool:
    if j <= 0:
        return False
    atr_pre = float(m15.at[j - 1, "atr14"])
    if not (math.isfinite(atr_pre) and atr_pre > 0 and state.near_boundary is not None):
        return False
    o = float(m15.at[j, "open"])
    c = float(m15.at[j, "close"])
    if state.direction == "LONG":
        return (
            c > state.near_boundary
            and c > o
            and c - o >= 0.25 * atr_pre
            and c > float(m15.at[j - 1, "high"])
        )
    return (
        c < state.near_boundary
        and c < o
        and o - c >= 0.25 * atr_pre
        and c < float(m15.at[j - 1, "low"])
    )


def _transition(rows: list[dict[str, Any]], spec: MachineSpec, t: pd.Timestamp, before: str, after: str, event: str, direction: str | None) -> None:
    rows.append({
        "machine_id": spec.machine_id,
        "boundary_time": t.isoformat(sep=" "),
        "state_before": before,
        "state_after": after,
        "event": event,
        "direction": direction or "",
    })


def replay_machine(m15: pd.DataFrame, h1: pd.DataFrame, spec: MachineSpec) -> dict[str, Any]:
    times = list(pd.to_datetime(m15["time"]))
    time_to_idx = {t: i for i, t in enumerate(times)}
    h1_end_to_idx = {pd.Timestamp(t): i for i, t in enumerate(pd.to_datetime(h1["end_time"]))}
    state = RuntimeState()
    counts: Counter[str] = Counter()
    transitions: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    entry_months: Counter[str] = Counter()
    holdings: list[int] = []
    pending_ages: list[int] = []
    closed_dir: Counter[str] = Counter()
    open_dir: Counter[str] = Counter()
    active_intervals = 0
    entry_count = 0

    for i in range(1, len(m15)):
        t = times[i]
        j = time_to_idx.get(t - M15)
        exited = False
        entered = False
        if j is None:
            counts["decision_boundary_missing_exact_previous"] += 1
            if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
                counts["active_decision_unavailable_gap"] += 1
                active_intervals += 1
            elif state.state != "IDLE":
                counts["cancel_gap_in_sequence"] += 1
                _transition(transitions, spec, t, state.state, "IDLE", "CANCEL_GAP_IN_SEQUENCE", state.direction)
                if state.impulse_end_time is not None:
                    pending_ages.append(_bars_between(t, state.impulse_end_time))
                state.clear()
            continue

        c_prev = float(m15.at[j, "close"])
        if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
            assert state.entry_time is not None and state.impulse_origin is not None and state.impulse_extreme is not None and state.frozen_h1_atr is not None
            age = _bars_between(t, state.entry_time)
            if state.direction == "LONG":
                failure = c_prev <= state.impulse_origin - 0.25 * state.frozen_h1_atr
                success = c_prev >= state.impulse_extreme + 0.50 * state.frozen_h1_atr
            else:
                failure = c_prev >= state.impulse_origin + 0.25 * state.frozen_h1_atr
                success = c_prev <= state.impulse_extreme - 0.50 * state.frozen_h1_atr
            reason = ""
            if failure:
                reason = "STRUCTURAL_FAILURE"
            elif success:
                reason = "STRUCTURAL_SUCCESS"
            elif age >= 32:
                reason = "THESIS_EXPIRY_32_BARS"
            if reason:
                holdings.append(age)
                closed_dir[state.direction] += 1
                episodes.append({
                    "machine_id": spec.machine_id,
                    "direction": state.direction,
                    "impulse_h1_open": state.impulse_h1_open.isoformat(sep=" "),
                    "pullback_time": state.pullback_time.isoformat(sep=" "),
                    "reclaim_time": state.reclaim_time.isoformat(sep=" "),
                    "entry_time": state.entry_time.isoformat(sep=" "),
                    "exit_time": t.isoformat(sep=" "),
                    "holding_bars": age,
                    "endpoint_open": False,
                    "exit_reason": reason,
                })
                counts[f"exit_{reason.lower()}"] += 1
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", f"EXIT_{reason}", direction)
                exited = True
            else:
                active_intervals += 1
            if not exited:
                continue

        if state.state in {"LONG_H1_IMPULSE_ARMED", "SHORT_H1_IMPULSE_ARMED"}:
            assert state.impulse_end_time is not None
            age = _bars_between(t, state.impulse_end_time)
            if _invalidated(c_prev, state):
                counts["cancel_preentry_invalidation"] += 1
                pending_ages.append(age)
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", "CANCEL_PREENTRY_INVALIDATION", direction)
            elif age > spec.pullback_deadline:
                counts["cancel_pullback_expired"] += 1
                pending_ages.append(age)
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", "CANCEL_PULLBACK_EXPIRED", direction)
            elif 1 <= age <= spec.pullback_deadline and _pullback_overlap(float(m15.at[j, "high"]), float(m15.at[j, "low"]), state):
                counts["pullback"] += 1
                before = state.state
                state.pullback_time = times[j]
                state.state = "LONG_PULLBACK_SEEN" if state.direction == "LONG" else "SHORT_PULLBACK_SEEN"
                _transition(transitions, spec, t, before, state.state, "PULLBACK", state.direction)
            elif age == spec.pullback_deadline:
                counts["cancel_pullback_expired"] += 1
                pending_ages.append(age)
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", "CANCEL_PULLBACK_EXPIRED", direction)

        if state.state in {"LONG_PULLBACK_SEEN", "SHORT_PULLBACK_SEEN"}:
            assert state.pullback_time is not None and state.impulse_end_time is not None
            age_pullback = _bars_between(t, state.pullback_time + M15)
            total_age = _bars_between(t, state.impulse_end_time)
            if _invalidated(c_prev, state):
                counts["cancel_preentry_invalidation"] += 1
                pending_ages.append(total_age)
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", "CANCEL_PREENTRY_INVALIDATION", direction)
            elif age_pullback > 4:
                counts["cancel_reclaim_expired"] += 1
                pending_ages.append(total_age)
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", "CANCEL_RECLAIM_EXPIRED", direction)
            elif 1 <= age_pullback <= 4 and _reclaim(m15, j, state):
                counts["reclaim"] += 1
                counts["entry"] += 1
                counts[f"entry_{state.direction.lower()}"] += 1
                entry_count += 1
                entry_months[t.strftime("%Y-%m")] += 1
                before = state.state
                state.reclaim_time = times[j]
                state.entry_time = t
                state.state = "ACTIVE_LONG" if state.direction == "LONG" else "ACTIVE_SHORT"
                _transition(transitions, spec, t, before, state.state, "ENTRY_EXACT_NEXT_OPEN", state.direction)
                entered = True
            elif age_pullback == 4:
                counts["cancel_reclaim_expired"] += 1
                pending_ages.append(total_age)
                before = state.state
                direction = state.direction
                state.clear()
                _transition(transitions, spec, t, before, "IDLE", "CANCEL_RECLAIM_EXPIRED", direction)

        if state.state == "IDLE" and not entered and not exited:
            hidx = h1_end_to_idx.get(t)
            if hidx is not None:
                long_flag, short_flag, meta = _impulse_flags(h1, hidx, spec)
                if long_flag and short_flag:
                    counts["simultaneous_impulse_conflict"] += 1
                    _transition(transitions, spec, t, "IDLE", "IDLE", "SIMULTANEOUS_IMPULSE_NO_TRANSITION", None)
                elif long_flag or short_flag:
                    direction = "LONG" if long_flag else "SHORT"
                    counts["h1_impulse"] += 1
                    counts[f"h1_impulse_{direction.lower()}"] += 1
                    state.direction = direction
                    state.impulse_h1_open = pd.Timestamp(h1.at[hidx, "time"])
                    state.impulse_end_time = t
                    state.impulse_origin = meta["open"]
                    state.impulse_extreme = meta["high"] if direction == "LONG" else meta["low"]
                    state.impulse_range = meta["range"]
                    state.frozen_h1_atr = meta["atr"]
                    if direction == "LONG":
                        state.near_boundary = meta["high"] - 0.382 * meta["range"]
                        state.deep_boundary = meta["high"] - 0.618 * meta["range"]
                        state.state = "LONG_H1_IMPULSE_ARMED"
                    else:
                        state.near_boundary = meta["low"] + 0.382 * meta["range"]
                        state.deep_boundary = meta["low"] + 0.618 * meta["range"]
                        state.state = "SHORT_H1_IMPULSE_ARMED"
                    _transition(transitions, spec, t, "IDLE", state.state, "H1_IMPULSE_ARMED", direction)

        if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
            active_intervals += 1

    endpoint_open = 0
    if state.state in {"ACTIVE_LONG", "ACTIVE_SHORT"}:
        endpoint_open = 1
        open_dir[state.direction] += 1
        assert state.entry_time is not None and state.impulse_h1_open is not None and state.pullback_time is not None and state.reclaim_time is not None
        episodes.append({
            "machine_id": spec.machine_id,
            "direction": state.direction,
            "impulse_h1_open": state.impulse_h1_open.isoformat(sep=" "),
            "pullback_time": state.pullback_time.isoformat(sep=" "),
            "reclaim_time": state.reclaim_time.isoformat(sep=" "),
            "entry_time": state.entry_time.isoformat(sep=" "),
            "exit_time": "",
            "holding_bars": _bars_between(times[-1] + M15, state.entry_time),
            "endpoint_open": True,
            "exit_reason": "ENDPOINT_OPEN_NOT_FORCE_CLOSED",
        })

    closed = len(holdings)
    months = len(entry_months)
    max_month_share = max(entry_months.values(), default=0) / entry_count if entry_count else 0.0
    p90 = float(np.percentile(holdings, 90)) if holdings else math.inf
    max_hold = max(holdings, default=math.inf)
    state_integrity = (
        entry_count == closed + endpoint_open
        and endpoint_open <= 1
        and not any(int(e["holding_bars"]) < 0 for e in episodes)
        and len({e["entry_time"] for e in episodes}) == len(episodes)
    )
    gate_checks = {
        "minimum_closed_episodes_total": closed >= 50,
        "minimum_closed_episodes_each_direction": closed_dir["LONG"] >= 20 and closed_dir["SHORT"] >= 20,
        "minimum_entry_months": months >= 6,
        "maximum_single_month_entry_share": max_month_share <= 0.35,
        "maximum_p90_holding_bars": p90 <= 384,
        "maximum_holding_bars": max_hold <= 1500,
        "maximum_endpoint_open_episodes": endpoint_open <= 1,
        "state_integrity_required": state_integrity,
        "fallback_used_allowed": True,
    }
    metrics = {
        "machine_id": spec.machine_id,
        "prior_H1_range_R": spec.prior_h1_range,
        "minimum_H1_impulse_body_B_ATR": spec.impulse_body_atr,
        "first_pullback_deadline_W_M15_bars": spec.pullback_deadline,
        "h1_impulses": counts["h1_impulse"],
        "pullbacks": counts["pullback"],
        "reclaims": counts["reclaim"],
        "entries": entry_count,
        "closed_episodes": closed,
        "closed_long": closed_dir["LONG"],
        "closed_short": closed_dir["SHORT"],
        "endpoint_open_episodes": endpoint_open,
        "endpoint_open_long": open_dir["LONG"],
        "endpoint_open_short": open_dir["SHORT"],
        "distinct_entry_months": months,
        "maximum_single_month_entry_share": max_month_share,
        "holding_p50_bars": float(np.percentile(holdings, 50)) if holdings else None,
        "holding_p90_bars": None if math.isinf(p90) else p90,
        "holding_max_bars": None if math.isinf(max_hold) else int(max_hold),
        "position_occupancy": active_intervals / max(1, len(m15) - 1),
        "pending_age_p90_bars": float(np.percentile(pending_ages, 90)) if pending_ages else None,
        "pending_age_max_bars": max(pending_ages, default=None),
        "gap_cancel_count": counts["cancel_gap_in_sequence"],
        "exact_entry_missing_count": counts["no_trade_exact_entry_missing"],
        "active_gap_count": counts["active_decision_unavailable_gap"],
        "simultaneous_conflict_count": counts["simultaneous_impulse_conflict"],
        "state_integrity": state_integrity,
        "fallback_or_interpolation_used": False,
        "capability_pass": all(gate_checks.values()),
    }
    return {
        "spec": spec,
        "counts": counts,
        "metrics": metrics,
        "gate_checks": gate_checks,
        "transitions": transitions,
        "episodes": episodes,
        "monthly": dict(sorted(entry_months.items())),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    bad = FORBIDDEN_OUTPUT_COLUMNS.intersection({c.lower() for c in columns})
    if bad:
        raise AssertionError(f"Forbidden BCR16 output columns: {sorted(bad)}")
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else round(value, 12)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _deterministic_zip(output_dir: Path, members: list[Path]) -> Path:
    zip_path = output_dir / PACKAGE_NAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(members, key=lambda p: p.name):
            info = zipfile.ZipInfo(path.name, date_time=FIXED_ZIP_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return zip_path


def validate_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["frozen_input"]["BTC_M15_sha256"] != EXPECTED_INPUT_SHA256:
        raise ValueError("BCR15 contract input SHA mismatch")
    actual = [(m["id"], int(m["R"]), float(m["B"]), int(m["W"])) for m in payload["grammar"]["machines"]]
    if actual != list(MACHINES):
        raise ValueError("BCR15 eight-machine grammar mismatch")
    if payload["authorization"].get("B5_outcome_access") is not False:
        raise ValueError("BCR15 contract unexpectedly permits outcome access")
    return payload


def build_once(input_path: Path, contract_path: Path, output_dir: Path, allow_prefix_rehydrate: bool) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="bcr16_input_") as td:
        frozen_path, input_meta = resolve_frozen_input(input_path, Path(td), allow_prefix_rehydrate)
        contract = validate_contract(contract_path)
        m15 = read_m15(frozen_path)
    h1 = build_complete_h1(m15)
    results = [replay_machine(m15, h1, MachineSpec(*m)) for m in MACHINES]

    machine_rows = [r["metrics"] for r in results]
    event_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    for r in results:
        mid = r["spec"].machine_id
        for event, count in sorted(r["counts"].items()):
            event_rows.append({"machine_id": mid, "event": event, "count": count})
        for month, count in r["monthly"].items():
            monthly_rows.append({"machine_id": mid, "entry_month": month, "entries": count})
        transition_rows.extend(r["transitions"])
        episode_rows.extend(r["episodes"])
        for check, passed in r["gate_checks"].items():
            gate_rows.append({"machine_id": mid, "gate_check": check, "passed": bool(passed)})

    _write_csv(output_dir / "bcr16_machine_metrics.csv", machine_rows, list(machine_rows[0].keys()))
    _write_csv(output_dir / "bcr16_event_counts.csv", event_rows, ["machine_id", "event", "count"])
    _write_csv(output_dir / "bcr16_monthly_entries.csv", monthly_rows, ["machine_id", "entry_month", "entries"])
    _write_csv(output_dir / "bcr16_gate_checks.csv", gate_rows, ["machine_id", "gate_check", "passed"])
    _write_csv(output_dir / "bcr16_transition_ledger.csv", transition_rows, ["machine_id", "boundary_time", "state_before", "state_after", "event", "direction"])
    _write_csv(output_dir / "bcr16_episode_ledger.csv", episode_rows, ["machine_id", "direction", "impulse_h1_open", "pullback_time", "reclaim_time", "entry_time", "exit_time", "holding_bars", "endpoint_open", "exit_reason"])

    summary = {
        "project": "BTC_CANDIDATE_RESEARCH_REDESIGN",
        "stage": "BCR16_B5_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT",
        "status": "BCR16_LABEL_FREE_AUDIT_OUTPUT_BUILT_NO_VALUE_FIELDS",
        "branch": "feature/btc-fresh-forward-research",
        "input": input_meta,
        "input_rows": len(m15),
        "input_first_time": m15["time"].iloc[0].isoformat(sep=" "),
        "input_last_time": m15["time"].iloc[-1].isoformat(sep=" "),
        "complete_h1_bars": len(h1),
        "contract_stage": contract["stage"],
        "machine_count": len(results),
        "all_eight_reported": len(results) == 8,
        "capability_pass_count": sum(bool(r["metrics"]["capability_pass"]) for r in results),
        "capability_fail_count": sum(not bool(r["metrics"]["capability_pass"]) for r in results),
        "outcome_fields_opened": False,
        "value_evaluation_performed": False,
        "candidate_promoted": False,
        "portfolio_selected": False,
        "prospective_start_set": False,
        "shadow_started": False,
        "discord_sent": False,
        "mt5_order_sent": False,
        "machine_metrics": machine_rows,
    }
    _json_dump(output_dir / "bcr16_summary.json", _normalize(summary))

    manifest_files = []
    for path in sorted(output_dir.glob("bcr16_*")):
        manifest_files.append({"name": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "stage": "BCR16_B5_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT",
        "source_sha256": EXPECTED_INPUT_SHA256,
        "contract_sha256": sha256_file(contract_path),
        "files": manifest_files,
        "deterministic_zip_timestamp": FIXED_ZIP_DT,
        "forbidden_value_fields_present": False,
    }
    _json_dump(output_dir / "manifest.json", manifest)
    members = [p for p in output_dir.iterdir() if p.is_file() and p.name != PACKAGE_NAME]
    zip_path = _deterministic_zip(output_dir, members)
    package_sha = sha256_file(zip_path)
    (output_dir / "package_sha256.txt").write_text(f"{package_sha}  {PACKAGE_NAME}\n", encoding="ascii")
    return {"package_path": str(zip_path), "package_sha256": package_sha, "summary": summary}


def build_with_repeat(input_path: Path, contract_path: Path, output_dir: Path, allow_prefix_rehydrate: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="bcr16_repeat_") as td:
        root = Path(td)
        a = build_once(input_path, contract_path, root / "run_a", allow_prefix_rehydrate)
        b = build_once(input_path, contract_path, root / "run_b", allow_prefix_rehydrate)
        if a["package_sha256"] != b["package_sha256"]:
            raise RuntimeError("Deterministic repeat package SHA mismatch")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(root / "run_a", output_dir)
        repeat = {
            "deterministic_repeat_match": True,
            "package_sha256_run_a": a["package_sha256"],
            "package_sha256_run_b": b["package_sha256"],
        }
        _json_dump(output_dir / "deterministic_repeat.json", repeat)
        return {**a, **repeat, "published_output_dir": str(output_dir)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BCR16 outcome-blind B5 H1 impulse / M15 reclaim capability audit")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--allow-prefix-rehydrate", action="store_true")
    p.add_argument("--repeat-check", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    result = build_with_repeat(args.input, args.contract, args.output_dir, args.allow_prefix_rehydrate) if args.repeat_check else build_once(args.input, args.contract, args.output_dir, args.allow_prefix_rehydrate)
    print(json.dumps(_normalize(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
