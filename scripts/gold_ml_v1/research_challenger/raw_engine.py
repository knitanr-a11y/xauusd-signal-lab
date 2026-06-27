from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

POINT = 0.01
TF_DELTA = {
    "M1": pd.Timedelta(minutes=1),
    "M5": pd.Timedelta(minutes=5),
    "M15": pd.Timedelta(minutes=15),
    "H1": pd.Timedelta(hours=1),
    "H4": pd.Timedelta(hours=4),
    "D1": pd.Timedelta(days=1),
}

RAW_FILENAMES = {
    "M1": "gold_v3_2023_2026_m1.csv",
    "M5": "gold_v3_2023_2026_m5.csv",
    "M15": "gold_v3_2023_2026_m15.csv",
    "H1": "gold_v3_2023_2026_h1.csv",
    "H4": "gold_v3_2023_2026_h4.csv",
    "D1": "gold_v3_2023_2026_d1.csv",
}
LIVE_FILENAMES = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}


@dataclass(frozen=True)
class SleeveResult:
    candidate_id: str
    comp: str
    direction: str
    weight: float
    size: float
    trades: pd.DataFrame
    historical_only: bool = False


def _required_columns() -> list[str]:
    return ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]


def read_bars(root: Path, timeframe: str, *, live: bool = False) -> pd.DataFrame:
    names = LIVE_FILENAMES if live else RAW_FILENAMES
    path = root / names[timeframe]
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    missing = [c for c in _required_columns() if c not in frame.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    frame = frame[_required_columns()].copy()
    parsed = pd.to_datetime(frame["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if parsed.isna().any():
        parsed = pd.to_datetime(frame["time"], errors="raise")
    frame["time"] = parsed
    frame = frame.sort_values("time", kind="mergesort").reset_index(drop=True)
    if frame["time"].duplicated().any():
        raise ValueError(f"{path.name}: duplicate time")
    for c in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        frame[c] = pd.to_numeric(frame[c], errors="raise")
    frame["bar_open_time"] = frame["time"]
    frame["bar_close_time"] = frame["time"] + TF_DELTA[timeframe]
    return frame


def true_range(frame: pd.DataFrame) -> pd.Series:
    prev = frame["close"].shift(1)
    return pd.concat(
        [
            (frame["high"] - frame["low"]).abs(),
            (frame["high"] - prev).abs(),
            (frame["low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr_simple(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(frame).rolling(period, min_periods=period).mean()


def atr_wilder(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(frame).to_numpy(float)
    values = np.full(len(tr), np.nan)
    if len(tr) >= period:
        values[period - 1] = float(np.mean(tr[:period]))
        for i in range(period, len(tr)):
            values[i] = (values[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(values, index=frame.index)


def rma(series: pd.Series, period: int) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").to_numpy(float)
    out = np.full(len(values), np.nan)
    if len(values) < period:
        return pd.Series(out, index=series.index)
    start = None
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        if np.isfinite(window).all():
            start = i
            out[i] = float(window.mean())
            break
    if start is None:
        return pd.Series(out, index=series.index)
    prev = out[start]
    for i in range(start + 1, len(values)):
        value = values[i]
        if not np.isfinite(value):
            prev = np.nan
            continue
        if not np.isfinite(prev):
            if i >= period - 1:
                window = values[i - period + 1 : i + 1]
                if np.isfinite(window).all():
                    prev = float(window.mean())
                    out[i] = prev
            continue
        prev = ((period - 1) * prev + value) / period
        out[i] = prev
    return pd.Series(out, index=series.index)


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0).fillna(0)
    losses = (-delta.clip(upper=0)).fillna(0)
    avg_gain = rma(gains, period)
    avg_loss = rma(losses, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    value = 100 - 100 / (1 + rs)
    value = value.where(avg_loss != 0, 100)
    return value.where(~((avg_gain == 0) & (avg_loss == 0)), 50)


def rci_rank_difference(series: pd.Series, period: int = 18) -> pd.Series:
    def calculate(window: np.ndarray) -> float:
        price_rank = pd.Series(window).rank(method="average").to_numpy(float)
        time_rank = np.arange(1, len(window) + 1, dtype=float)
        diff = time_rank - price_rank
        return float((1 - 6 * np.sum(diff * diff) / (len(window) * (len(window) ** 2 - 1))) * 100)

    return series.rolling(period, min_periods=period).apply(calculate, raw=True)


def trailing_percentile_current(window: Iterable[float]) -> float:
    values = np.asarray(window, dtype=float)
    return float(np.mean(values <= values[-1]))


class M1Engine:
    def __init__(self, frame: pd.DataFrame):
        ordered = frame.sort_values("bar_open_time", kind="mergesort").reset_index(drop=True)
        self.times = pd.DatetimeIndex(ordered["bar_open_time"]).asi8
        self.opens = ordered["open"].to_numpy(float)
        self.highs = ordered["high"].to_numpy(float)
        self.lows = ordered["low"].to_numpy(float)
        self.closes = ordered["close"].to_numpy(float)
        self.spreads = ordered["spread"].to_numpy(float)
        self.latest_close = pd.Timestamp(self.times[-1] + 60_000_000_000)

    def has_exact_entry(self, timestamp: pd.Timestamp) -> bool:
        value = pd.Timestamp(timestamp).value
        idx = int(np.searchsorted(self.times, value, side="left"))
        return idx < len(self.times) and int(self.times[idx]) == value

    def _bounds(self, decision: pd.Timestamp, horizon_hours: int) -> tuple[int, int] | None:
        decision = pd.Timestamp(decision)
        start = int(np.searchsorted(self.times, decision.value, side="left"))
        if start >= len(self.times) or int(self.times[start]) != decision.value:
            return None
        horizon_end = decision + pd.Timedelta(hours=horizon_hours)
        if horizon_end > self.latest_close:
            return None
        end = int(np.searchsorted(self.times, horizon_end.value, side="left"))
        if end <= start:
            return None
        return start, end

    def evaluate_long(
        self,
        decision: pd.Timestamp,
        atr: float,
        *,
        target_r: float,
        horizon_hours: int,
        exit_timestamp: str = "close",
    ) -> dict[str, object] | None:
        if not np.isfinite(atr) or atr <= 0:
            return None
        bounds = self._bounds(pd.Timestamp(decision), horizon_hours)
        if bounds is None:
            return None
        start, end = bounds
        entry = float(self.opens[start] + self.spreads[start] * POINT)
        stop = entry - atr
        target = entry + target_r * atr
        stop_hits = np.flatnonzero(self.lows[start:end] <= stop)
        target_hits = np.flatnonzero(self.highs[start:end] >= target)
        offset = 60_000_000_000 if exit_timestamp == "close" else 0
        if len(stop_hits) and (not len(target_hits) or int(stop_hits[0]) <= int(target_hits[0])):
            idx = start + int(stop_hits[0])
            return {"decision_time": pd.Timestamp(decision), "exit_time": pd.Timestamp(self.times[idx] + offset), "r": -1.0, "outcome": "SL"}
        if len(target_hits):
            idx = start + int(target_hits[0])
            return {"decision_time": pd.Timestamp(decision), "exit_time": pd.Timestamp(self.times[idx] + offset), "r": float(target_r), "outcome": "TP"}
        idx = end - 1
        r_value = float((self.closes[idx] - entry) / atr)
        return {"decision_time": pd.Timestamp(decision), "exit_time": pd.Timestamp(self.times[idx] + offset), "r": r_value, "outcome": "TIME"}

    def evaluate_short(
        self,
        decision: pd.Timestamp,
        atr: float,
        *,
        target_r: float,
        horizon_hours: int,
        exit_timestamp: str = "close",
    ) -> dict[str, object] | None:
        if not np.isfinite(atr) or atr <= 0:
            return None
        bounds = self._bounds(pd.Timestamp(decision), horizon_hours)
        if bounds is None:
            return None
        start, end = bounds
        entry = float(self.opens[start])
        stop = entry + atr
        target = entry - target_r * atr
        ask_high = self.highs[start:end] + self.spreads[start:end] * POINT
        ask_low = self.lows[start:end] + self.spreads[start:end] * POINT
        stop_hits = np.flatnonzero(ask_high >= stop)
        target_hits = np.flatnonzero(ask_low <= target)
        offset = 60_000_000_000 if exit_timestamp == "close" else 0
        if len(stop_hits) and (not len(target_hits) or int(stop_hits[0]) <= int(target_hits[0])):
            idx = start + int(stop_hits[0])
            return {"decision_time": pd.Timestamp(decision), "exit_time": pd.Timestamp(self.times[idx] + offset), "r": -1.0, "outcome": "SL"}
        if len(target_hits):
            idx = start + int(target_hits[0])
            return {"decision_time": pd.Timestamp(decision), "exit_time": pd.Timestamp(self.times[idx] + offset), "r": float(target_r), "outcome": "TP"}
        idx = end - 1
        exit_price = float(self.closes[idx] + self.spreads[idx] * POINT)
        r_value = float((entry - exit_price) / atr)
        return {"decision_time": pd.Timestamp(decision), "exit_time": pd.Timestamp(self.times[idx] + offset), "r": r_value, "outcome": "TIME"}


def evaluate_one_position(
    events: pd.DataFrame,
    engine: M1Engine,
    *,
    direction: str,
    atr_column: str,
    target_r: float,
    horizon_hours: int,
    exit_timestamp: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    open_until = pd.Timestamp.min
    for row in events.sort_values("bar_close_time", kind="mergesort").itertuples(index=False):
        decision = pd.Timestamp(row.bar_close_time)
        if decision < open_until:
            continue
        evaluator = engine.evaluate_long if direction == "LONG" else engine.evaluate_short
        trade = evaluator(
            decision,
            float(getattr(row, atr_column)),
            target_r=target_r,
            horizon_hours=horizon_hours,
            exit_timestamp=exit_timestamp,
        )
        if trade is None:
            continue
        rows.append(trade)
        open_until = pd.Timestamp(trade["exit_time"])
    return pd.DataFrame(rows, columns=["decision_time", "exit_time", "r", "outcome"])


def build_acore(raw_dir: Path) -> pd.DataFrame:
    m1 = read_bars(raw_dir, "M1")
    m15 = read_bars(raw_dir, "M15")
    h4 = read_bars(raw_dir, "H4")
    engine = M1Engine(m1)
    m15["atr14"] = atr_simple(m15, 14)
    sd20 = m15["close"].rolling(20, min_periods=20).std(ddof=0)
    sd60 = m15["close"].rolling(60, min_periods=60).std(ddof=0)
    m15["bb20_width_atr"] = 4 * sd20 / m15["atr14"]
    m15["bb60_width_atr"] = 4 * sd60 / m15["atr14"]
    m15["bb60_width_pct100"] = m15["bb60_width_atr"].rolling(100, min_periods=100).apply(trailing_percentile_current, raw=True)
    h4["atr_state"] = atr_simple(h4, 14)
    h4["atr_slope"] = atr_wilder(h4, 14)
    h4["rci18"] = rci_rank_difference(h4["close"], 18)
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    candle_range = (h4["high"] - h4["low"]).replace(0, np.nan)
    h4["upper_wick_frac"] = (h4["high"] - h4[["open", "close"]].max(axis=1)) / candle_range
    h4["ema40_slope6_atr"] = (h4["ema40"] - h4["ema40"].shift(6)) / h4["atr_slope"]
    h4["spread_atr"] = h4["spread"] * POINT / h4["atr_state"]
    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[["bar_close_time", "rci18", "spread_atr", "upper_wick_frac", "ema40_slope6_atr"]].dropna().sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["state"] = (joined["rci18"] >= 73.993808) & (joined["spread_atr"] <= 0.012772)
    joined["eligible"] = joined["bar_close_time"].map(engine.has_exact_entry) & ((joined["bar_close_time"] + pd.Timedelta(hours=6)) <= engine.latest_close)
    active = joined["state"] & joined["eligible"]
    joined["event"] = active & ~active.shift(fill_value=False)
    parent_events = joined[joined["event"]].copy()
    parent = evaluate_one_position(parent_events, engine, direction="LONG", atr_column="atr14", target_r=1.0, horizon_hours=6, exit_timestamp="close")
    features = parent_events[["bar_close_time", "upper_wick_frac", "ema40_slope6_atr"]].rename(columns={"bar_close_time": "decision_time"})
    parent = parent.merge(features, on="decision_time", how="left", validate="one_to_one")
    p7_keep = ~((parent["upper_wick_frac"] >= 0.27488556398168634) & (parent["ema40_slope6_atr"] >= 0.6863028800058267))
    p7 = parent[p7_keep].copy()
    watch_a = (p7["upper_wick_frac"] <= 0.1677737608541299) & (p7["ema40_slope6_atr"] <= 0.5056518291622855)
    watch_b = (p7["upper_wick_frac"] <= 0.06526044468913629) & (p7["ema40_slope6_atr"] >= 0.8700779249713114)
    out = p7[~(watch_a | watch_b)][["decision_time", "exit_time", "r", "outcome"]].copy()
    out["direction"] = "LONG"
    return out.sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def _bstate_context(raw_dir: Path) -> tuple[pd.DataFrame, M1Engine]:
    m1 = read_bars(raw_dir, "M1")
    h1 = read_bars(raw_dir, "H1")
    d1 = read_bars(raw_dir, "D1")
    engine = M1Engine(m1)
    h1["atr14"] = atr_wilder(h1, 14)
    mean = h1["close"].rolling(60, min_periods=60).mean()
    sd = h1["close"].rolling(60, min_periods=60).std(ddof=0)
    h1["bb60_upper"] = mean + 2 * sd
    h1["spread_atr"] = h1["spread"] * POINT / h1["atr14"]
    d1["atr14"] = atr_wilder(d1, 14)
    d1["rci18"] = rci_rank_difference(d1["close"], 18)
    d1["tickvol_ratio50"] = d1["tick_volume"] / d1["tick_volume"].rolling(50, min_periods=50).median()
    d1["delta_atr_3"] = (d1["close"] - d1["close"].shift(3)) / d1["atr14"]
    joined = pd.merge_asof(
        h1.sort_values("bar_close_time"),
        d1[["bar_close_time", "rci18", "tickvol_ratio50", "delta_atr_3"]].sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["base_breakout"] = (joined["close"].shift(1) <= joined["bb60_upper"].shift(1)) & (joined["close"] > joined["bb60_upper"]) & (joined["rci18"] >= 0)
    joined["p15_keep"] = ~((joined["tickvol_ratio50"] <= 0.876789995391398) & (joined["delta_atr_3"] <= 0.2256991669382677))
    joined["range_atr"] = (joined["high"] - joined["low"]) / joined["atr14"]
    joined["close_pos"] = (joined["close"] - joined["low"]) / (joined["high"] - joined["low"]).replace(0, np.nan)
    joined["range_atr_lag1"] = joined["range_atr"].shift(1)
    joined["close_pos_lag5"] = joined["close_pos"].shift(5)
    joined["range_atr_lag10"] = joined["range_atr"].shift(10)
    joined["span_atr_12"] = (joined["high"].rolling(12).max() - joined["low"].rolling(12).min()) / joined["atr14"]
    joined["keep_a"] = ~((joined["range_atr_lag1"] <= 0.6571970935503249) & (joined["span_atr_12"] >= 5.058013327710588))
    joined["keep_b"] = ~((joined["close_pos_lag5"] <= 0.424089068826) & (joined["range_atr_lag10"] >= 1.17215632583))
    joined["all_keep"] = joined["p15_keep"] & joined["keep_a"] & joined["keep_b"]
    return joined.sort_values("bar_close_time", kind="mergesort").reset_index(drop=True), engine


def build_bstate(raw_dir: Path) -> pd.DataFrame:
    joined, engine = _bstate_context(raw_dir)
    joined["above"] = joined["close"] > joined["bb60_upper"]
    joined["cross_any"] = joined["above"] & ~joined["above"].shift(fill_value=False)
    joined["entry_ok"] = joined["above"] & (joined["rci18"] >= 0) & joined["all_keep"]
    base = joined[joined["base_breakout"] & joined["all_keep"]].copy()
    base["kind"] = "base"
    base["origin"] = base["bar_close_time"]
    base["event_priority"] = 0
    reentries: list[pd.Series] = []
    due: pd.Timestamp | None = None
    origin: pd.Timestamp | None = None
    for _, row in joined.iterrows():
        timestamp = pd.Timestamp(row["bar_close_time"])
        if due is not None and timestamp >= due:
            if bool(row["entry_ok"]):
                item = row.copy()
                item["kind"] = "re24"
                item["origin"] = origin
                item["event_priority"] = 1
                reentries.append(item)
            due = None
            origin = None
        if bool(row["cross_any"]) and due is None:
            origin = timestamp
            due = timestamp + pd.Timedelta(hours=24)
    reentry = pd.DataFrame(reentries)
    events = pd.concat([base, reentry], ignore_index=True, sort=False)
    events = events.sort_values(["bar_close_time", "event_priority"], kind="mergesort").drop_duplicates("bar_close_time", keep="first")
    trades: list[dict[str, object]] = []
    open_until = pd.Timestamp.min
    for _, row in events.iterrows():
        decision = pd.Timestamp(row["bar_close_time"])
        if decision < open_until:
            continue
        trade = engine.evaluate_long(decision, float(row["atr14"]), target_r=1.0, horizon_hours=48, exit_timestamp="open")
        if trade is None:
            continue
        trade["kind"] = row["kind"]
        trade["origin"] = pd.Timestamp(row["origin"])
        trade["direction"] = "LONG"
        trades.append(trade)
        open_until = pd.Timestamp(trade["exit_time"])
    return pd.DataFrame(trades).sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def build_p18(raw_dir: Path) -> pd.DataFrame:
    m1 = read_bars(raw_dir, "M1")
    m15 = read_bars(raw_dir, "M15")
    h4 = read_bars(raw_dir, "H4")
    engine = M1Engine(m1)
    m15["atr14"] = atr_simple(m15, 14)
    mean = m15["close"].rolling(40, min_periods=40).mean()
    sd = m15["close"].rolling(40, min_periods=40).std(ddof=0)
    m15["bb40_upper"] = mean + 2 * sd
    m15["width"] = 4 * sd / m15["atr14"]
    m15["width_pct100"] = m15["width"].rolling(100, min_periods=100).apply(trailing_percentile_current, raw=True)
    m15["squeeze12"] = m15["width_pct100"].shift(1).rolling(12, min_periods=12).min()
    m15["event"] = (
        (m15["close"].shift(1) <= m15["bb40_upper"].shift(1))
        & (m15["close"] > m15["bb40_upper"])
        & (m15["width"] > m15["width"].shift(1))
        & (m15["squeeze12"] <= 0.30)
    )
    h4["atr14"] = atr_wilder(h4, 14)
    h4["atr_ratio"] = h4["atr14"] / h4["atr14"].rolling(50, min_periods=50).median()
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    h4["slope6"] = (h4["ema40"] - h4["ema40"].shift(6)) / h4["atr14"]
    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[["bar_close_time", "atr_ratio", "slope6"]].dropna().sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    events = joined[joined["event"] & (joined["atr_ratio"] >= 1) & (joined["slope6"] > 0)].copy()
    out = evaluate_one_position(events, engine, direction="LONG", atr_column="atr14", target_r=1.0, horizon_hours=12, exit_timestamp="close")
    out["direction"] = "LONG"
    return out.sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def _p16_proposals(raw_dir: Path) -> tuple[pd.DataFrame, M1Engine]:
    m15 = read_bars(raw_dir, "M15").sort_values("bar_close_time").reset_index(drop=True)
    h4 = read_bars(raw_dir, "H4").sort_values("bar_close_time").reset_index(drop=True)
    engine = M1Engine(read_bars(raw_dir, "M1"))
    m15["atr14"] = atr_simple(m15, 14)
    h4["atr"] = atr_wilder(h4, 14)
    h4["ratio"] = h4["atr"] / h4["atr"].rolling(50, min_periods=50).median()
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    h4["slope"] = (h4["ema40"] - h4["ema40"].shift(6)) / h4["atr"]
    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[["bar_close_time", "ratio", "slope"]].dropna().sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    ).reset_index(drop=True)
    highs = joined["high"].to_numpy(float)
    pivot = np.zeros(len(joined), dtype=bool)
    for idx in range(3, len(joined) - 3):
        pivot[idx] = highs[idx] >= np.max(highs[idx - 3 : idx + 4])
    line = np.full(len(joined), np.nan)
    available: list[int] = []
    for idx in range(len(joined)):
        newly_confirmed = idx - 3
        if newly_confirmed >= 0 and pivot[newly_confirmed]:
            available.append(newly_confirmed)
        if len(available) >= 2:
            a, b = available[-2], available[-1]
            slope = (highs[b] - highs[a]) / (b - a)
            line[idx] = highs[b] + slope * (idx - b)
    joined["line"] = line
    joined["break_event"] = (joined["close"] > joined["line"]) & (joined["close"].shift(1) <= joined["line"].shift(1))
    rows: list[pd.Series] = []
    active: dict[str, object] | None = None
    for idx, row in joined.iterrows():
        if active is not None:
            if idx > int(active["expire"]):
                active = None
            else:
                frozen = float(active["frozen"])
                if row["close"] < frozen - 0.5 * row["atr14"]:
                    active = None
                else:
                    touch = (row["low"] <= frozen + 0.1 * row["atr14"]) and (row["close"] > frozen) and (row["close"] > row["open"])
                    if touch:
                        rows.append(row)
                        active = None
        if bool(row["break_event"]):
            context = (row["ratio"] >= 1) and (row["slope"] > 0)
            if context:
                active = {"expire": idx + 24, "frozen": float(row["line"])}
    return pd.DataFrame(rows), engine


def _p16_loss_leaf_filter(raw_dir: Path, events: pd.DataFrame) -> pd.DataFrame:
    m15 = read_bars(raw_dir, "M15")
    h1 = read_bars(raw_dir, "H1")
    h4 = read_bars(raw_dir, "H4")
    m15["atr14_w"] = atr_wilder(m15, 14)
    m15["atr50_w"] = atr_wilder(m15, 50)
    m15["m15_log_return_32"] = np.log(m15["close"] / m15["close"].shift(32))
    m15["m15_log_return_4"] = np.log(m15["close"] / m15["close"].shift(4))
    m15["m15_atr14_atr50_ratio"] = m15["atr14_w"] / m15["atr50_w"]
    m15["m15_body_fraction"] = (m15["close"] - m15["open"]).abs() / (m15["high"] - m15["low"]).replace(0, np.nan)
    m15["m15_atr14_percentile_lag1_256"] = m15["atr14_w"].shift(1).rolling(256, min_periods=256).rank(pct=True)
    h1["h1_body_fraction"] = (h1["close"] - h1["open"]).abs() / (h1["high"] - h1["low"]).replace(0, np.nan)
    h4["atr14_w"] = atr_wilder(h4, 14)
    h4["ema20"] = h4["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    h4["ema50"] = h4["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    h4["h4_ema20_ema50_gap_atr14"] = (h4["ema20"] - h4["ema50"]) / h4["atr14_w"]
    h4["h4_log_return_24"] = np.log(h4["close"] / h4["close"].shift(24))
    features = events[["bar_close_time"]].merge(
        m15[["bar_close_time", "m15_log_return_32", "m15_log_return_4", "m15_atr14_atr50_ratio", "m15_body_fraction", "m15_atr14_percentile_lag1_256"]],
        on="bar_close_time",
        how="left",
    )
    features = pd.merge_asof(features.sort_values("bar_close_time"), h1[["bar_close_time", "h1_body_fraction"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    features = pd.merge_asof(features.sort_values("bar_close_time"), h4[["bar_close_time", "h4_ema20_ema50_gap_atr14", "h4_log_return_24"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    rule1 = (features["m15_log_return_32"] <= 0.002515326486900449) & (features["h1_body_fraction"] > 0.43690429627895355)
    rule2 = (features["h4_ema20_ema50_gap_atr14"] <= 2.0051413774490356) & (features["m15_atr14_atr50_ratio"] <= 0.8724351227283478) & (features["m15_body_fraction"] > 0.5077519416809082)
    rule3 = (features["m15_atr14_percentile_lag1_256"] <= 0.298828125) & (features["m15_log_return_4"] <= 0.0006831734790466726) & (features["h4_log_return_24"] <= 0.010968626011162996)
    excluded = set(features.loc[rule1 | rule2 | rule3, "bar_close_time"])
    return events[~events["bar_close_time"].isin(excluded)].copy()


def build_p16_pre_ml(raw_dir: Path) -> pd.DataFrame:
    events, engine = _p16_proposals(raw_dir)
    events = _p16_loss_leaf_filter(raw_dir, events)
    out = evaluate_one_position(events, engine, direction="LONG", atr_column="atr14", target_r=1.5, horizon_hours=6, exit_timestamp="close")
    out["direction"] = "LONG"
    return out.sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def _percent_b(frame: pd.DataFrame, period: int) -> pd.Series:
    mean = frame["close"].rolling(period, min_periods=period).mean()
    sd = frame["close"].rolling(period, min_periods=period).std(ddof=0)
    return (frame["close"] - (mean - 2 * sd)) / (4 * sd)


def _p19_proposals(raw_dir: Path) -> tuple[pd.DataFrame, M1Engine]:
    m15 = read_bars(raw_dir, "M15").sort_values("bar_close_time").reset_index(drop=True)
    h4 = read_bars(raw_dir, "H4").sort_values("bar_close_time").reset_index(drop=True)
    engine = M1Engine(read_bars(raw_dir, "M1"))
    m15["atr14"] = atr_simple(m15, 14)
    m15["ema20"] = m15["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    m15["donlow"] = m15["low"].shift(1).rolling(20, min_periods=20).min()
    m15["donlow_prev"] = m15["donlow"].shift(1)
    m15["break_event"] = (m15["close"] < m15["donlow"]) & (m15["close"].shift(1) >= m15["donlow_prev"])
    m15["bb40"] = _percent_b(m15, 40)
    m15["bb60"] = _percent_b(m15, 60)
    h4["rci18"] = rci_rank_difference(h4["close"], 18)
    h4["atr"] = atr_wilder(h4, 14)
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    h4["slope"] = (h4["ema40"] - h4["ema40"].shift(6)) / h4["atr"]
    joined = pd.merge_asof(m15.sort_values("bar_close_time"), h4[["bar_close_time", "rci18", "slope"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True).reset_index(drop=True)
    rows: list[pd.Series] = []
    active: dict[str, int] | None = None
    for idx, row in joined.iterrows():
        if active is not None:
            if idx > active["expire"]:
                active = None
            elif row["close"] > row["ema20"] + 0.6 * row["atr14"]:
                active = None
            else:
                touch = (row["high"] >= row["ema20"] - 0.1 * row["atr14"]) and (row["close"] < row["ema20"]) and (row["close"] < row["open"])
                if touch:
                    if not ((row["bb40"] >= 0.2834353304983317) and (row["bb60"] >= 0.2779747188942476)):
                        rows.append(row)
                    active = None
        if bool(row["break_event"]):
            context = (row["rci18"] <= 0) and (row["slope"] < 0)
            if context:
                active = {"expire": idx + 24}
    return pd.DataFrame(rows), engine


def _p19_loss_leaf_filter(raw_dir: Path, events: pd.DataFrame) -> pd.DataFrame:
    m15 = read_bars(raw_dir, "M15")
    h1 = read_bars(raw_dir, "H1")
    h4 = read_bars(raw_dir, "H4")
    d1 = read_bars(raw_dir, "D1")
    m15["m15_atr_w"] = atr_wilder(m15, 14)
    m15["m15_log_return_32"] = np.log(m15["close"] / m15["close"].shift(32))
    m15["m15_range_atr14"] = (m15["high"] - m15["low"]) / m15["m15_atr_w"]
    h1["h1_log_return_3"] = np.log(h1["close"] / h1["close"].shift(3))
    h1["h1_lower_wick_fraction"] = (h1[["open", "close"]].min(axis=1) - h1["low"]) / (h1["high"] - h1["low"]).replace(0, np.nan)
    h4["atr"] = atr_wilder(h4, 14)
    h4["h4_close_location"] = (h4["close"] - h4["low"]) / (h4["high"] - h4["low"]).replace(0, np.nan)
    sd = h4["close"].rolling(20).std(ddof=0)
    h4["h4_bb20_width_atr14"] = 4 * sd / h4["atr"]
    h4["h4_tick_volume_percentile_lag1_126"] = h4["tick_volume"].shift(1).rolling(126, min_periods=126).rank(pct=True)
    d1["atr"] = atr_wilder(d1, 14)
    d1["d1_close_location"] = (d1["close"] - d1["low"]) / (d1["high"] - d1["low"]).replace(0, np.nan)
    d1["d1_signed_body_atr14"] = (d1["close"] - d1["open"]) / d1["atr"]
    features = events[["bar_close_time"]].merge(m15[["bar_close_time", "close", "m15_atr_w", "m15_log_return_32", "m15_range_atr14"]], on="bar_close_time", how="left")
    features = pd.merge_asof(features.sort_values("bar_close_time"), h1[["bar_close_time", "h1_log_return_3", "h1_lower_wick_fraction"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    features = pd.merge_asof(features.sort_values("bar_close_time"), h4[["bar_close_time", "h4_close_location", "h4_bb20_width_atr14", "h4_tick_volume_percentile_lag1_126"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    features = pd.merge_asof(features.sort_values("bar_close_time"), d1[["bar_close_time", "low", "d1_close_location", "d1_signed_body_atr14"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    features["cross_distance_from_completed_day_low_atr14"] = (features["close"] - features["low"]) / features["m15_atr_w"]
    rule1 = (features["h4_tick_volume_percentile_lag1_126"] > 0.2619047686457634) & (features["h1_log_return_3"] > -0.0028210452292114496) & (features["cross_distance_from_completed_day_low_atr14"] <= 1.0043783485889435)
    rule2 = (features["h4_close_location"] <= 0.25287557393312454) & (features["m15_range_atr14"] <= 1.3447449803352356) & (features["h4_bb20_width_atr14"] <= 4.4248366355896)
    rule3 = (features["m15_log_return_32"] <= -0.0022371469531208277) & (features["d1_close_location"] <= 0.3406364172697067) & (features["d1_signed_body_atr14"] > -0.6241065263748169)
    rule4 = (features["m15_log_return_32"] > -0.0022371469531208277) & (features["h1_lower_wick_fraction"] <= 0.18452708423137665)
    excluded = set(features.loc[rule1 | rule2 | rule3 | rule4, "bar_close_time"])
    return events[~events["bar_close_time"].isin(excluded)].copy()


def build_p19_pre_ml(raw_dir: Path) -> pd.DataFrame:
    events, engine = _p19_proposals(raw_dir)
    events = _p19_loss_leaf_filter(raw_dir, events)
    out = evaluate_one_position(events, engine, direction="SHORT", atr_column="atr14", target_r=2.0, horizon_hours=6, exit_timestamp="close")
    out["direction"] = "SHORT"
    return out.sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def build_watch024a(raw_dir: Path) -> pd.DataFrame:
    m1 = read_bars(raw_dir, "M1")
    m15 = read_bars(raw_dir, "M15")
    h4 = read_bars(raw_dir, "H4")
    engine = M1Engine(m1)
    m15["atr14"] = atr_wilder(m15, 14)
    m15["rsi_centered"] = (rsi_wilder(m15["close"], 14) - 50) / 50
    m15["range_atr"] = (m15["high"] - m15["low"]) / m15["atr14"]
    m15["upper_wick"] = (m15["high"] - m15[["open", "close"]].max(axis=1)) / (m15["high"] - m15["low"]).replace(0, np.nan)
    m15["atr_percentile"] = m15["atr14"].shift(1).rolling(256, min_periods=256).rank(pct=True)
    ema200 = m15["close"].ewm(span=200, adjust=False, min_periods=200).mean()
    m15["ema200_slope12_atr14"] = (ema200 - ema200.shift(12)) / m15["atr14"]
    state = (m15["atr_percentile"] >= 0.75) & (m15["rsi_centered"] >= 0.35) & (m15["range_atr"] >= 1.0) & (m15["upper_wick"] >= 0.4)
    previous_state = state.shift(1).astype("boolean").fillna(False).astype(bool)
    previous_time = m15["bar_close_time"].shift(1)
    onset = state & (~previous_state | ((m15["bar_close_time"] - previous_time) != pd.Timedelta(minutes=15)))
    events = m15.loc[onset, ["bar_close_time", "atr14", "ema200_slope12_atr14"]].copy()
    h4["h4_body_fraction"] = (h4["close"] - h4["open"]).abs() / (h4["high"] - h4["low"]).replace(0, np.nan)
    events = pd.merge_asof(events.sort_values("bar_close_time"), h4[["bar_close_time", "h4_body_fraction"]].dropna().sort_values("bar_close_time"), on="bar_close_time", direction="backward", allow_exact_matches=True)
    events = events[
        (events["bar_close_time"] >= pd.Timestamp("2023-05-31 00:00:00"))
        & (events["h4_body_fraction"] >= 0.7290171082088)
        & (events["ema200_slope12_atr14"] >= 0.36208201390899997)
    ].copy()
    out = evaluate_one_position(events, engine, direction="SHORT", atr_column="atr14", target_r=1.5, horizon_hours=6, exit_timestamp="close")
    out["direction"] = "SHORT"
    return out.sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def apply_historical_ml_truth(pre_ml: pd.DataFrame, truth_path: Path, candidate: str) -> pd.DataFrame:
    truth = pd.read_csv(truth_path)
    truth["decision_time"] = pd.to_datetime(truth["decision_time"], errors="raise")
    truth = truth[truth["candidate"].eq(candidate)].copy()
    if truth["decision_time"].duplicated().any():
        raise ValueError(f"{truth_path.name}: duplicate decision_time")
    pre = pre_ml.copy()
    pre["decision_time"] = pd.to_datetime(pre["decision_time"], errors="raise")
    historical = pre[pre["decision_time"].dt.year.between(2024, 2026)].copy()
    if set(historical["decision_time"]) != set(truth["decision_time"]):
        missing = sorted(set(truth["decision_time"]) - set(historical["decision_time"]))
        extra = sorted(set(historical["decision_time"]) - set(truth["decision_time"]))
        raise ValueError(f"{candidate}: historical truth mismatch; missing={missing[:5]}, extra={extra[:5]}")
    keep = set(truth.loc[truth["ml_gate_status"].eq("KEEP"), "decision_time"])
    return historical[historical["decision_time"].isin(keep)].copy().sort_values("decision_time", kind="mergesort").reset_index(drop=True)


def to_portfolio_rows(result: SleeveResult) -> pd.DataFrame:
    frame = result.trades.copy()
    frame["candidate_id"] = result.candidate_id
    frame["comp"] = result.comp
    frame["direction"] = result.direction
    frame["w"] = result.weight
    frame["size"] = result.size
    frame["weighted_r"] = frame["r"] * result.size
    frame["historical_only"] = result.historical_only
    return frame[["candidate_id", "decision_time", "exit_time", "r", "direction", "comp", "w", "size", "weighted_r", "historical_only"]]
