from __future__ import annotations

import argparse
import gzip
import io
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = SCRIPT_DIR.parent / "research_challenger"
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from raw_engine import atr_wilder, read_bars


CANDIDATES = {
    "GML1-NCD-001-L": ("NCD-001", "FROZEN_20_BREAKOUT_LEVEL_RETEST", "LONG"),
    "GML1-NCD-001-S": ("NCD-001", "FROZEN_20_BREAKOUT_LEVEL_RETEST", "SHORT"),
    "GML1-NCD-002-L": ("NCD-002", "FROZEN_50_DONCHIAN_SHALLOW_RECLAIM", "LONG"),
    "GML1-NCD-002-S": ("NCD-002", "FROZEN_50_DONCHIAN_SHALLOW_RECLAIM", "SHORT"),
    "GML1-NCD-003-L": ("NCD-003", "COMPRESSION_RELEASE_FIRST_EMA20_PULLBACK", "LONG"),
    "GML1-NCD-003-S": ("NCD-003", "COMPRESSION_RELEASE_FIRST_EMA20_PULLBACK", "SHORT"),
    "GML1-NCD-004-L": ("NCD-004", "EMA20_EMA50_BAND_RECOVERY_ONSET", "LONG"),
    "GML1-NCD-004-S": ("NCD-004", "EMA20_EMA50_BAND_RECOVERY_ONSET", "SHORT"),
    "GML1-NCD-005-L": ("NCD-005", "FAILED_20_BREAK_STRUCTURE_RECOVERY", "LONG"),
    "GML1-NCD-005-S": ("NCD-005", "FAILED_20_BREAK_STRUCTURE_RECOVERY", "SHORT"),
}


@dataclass
class Pending:
    setup_index: int
    level: float
    opposite: float | None = None
    setup_range_atr: float | None = None


def deterministic_csv_gzip(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                frame.to_csv(
                    text,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def build_context(raw_dir: Path, *, live: bool = False) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    m1 = read_bars(raw_dir, "M1", live=live)
    m15 = read_bars(raw_dir, "M15", live=live)
    h1 = read_bars(raw_dir, "H1", live=live)
    h4 = read_bars(raw_dir, "H4", live=live)

    m15["atr14"] = atr_wilder(m15, 14)
    m15["ema20"] = m15["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    m15["ema50"] = m15["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    m15["signed_body"] = m15["close"] - m15["open"]
    m15["candle_range"] = m15["high"] - m15["low"]
    m15["close_location"] = (m15["close"] - m15["low"]) / m15["candle_range"].replace(0, np.nan)
    m15["prev_high_20"] = m15["high"].shift(1).rolling(20, min_periods=20).max()
    m15["prev_low_20"] = m15["low"].shift(1).rolling(20, min_periods=20).min()
    m15["prev_high_50"] = m15["high"].shift(1).rolling(50, min_periods=50).max()
    m15["prev_low_50"] = m15["low"].shift(1).rolling(50, min_periods=50).min()
    bb_mid = m15["close"].rolling(20, min_periods=20).mean()
    bb_std = m15["close"].rolling(20, min_periods=20).std(ddof=0)
    m15["bb_upper"] = bb_mid + 2 * bb_std
    m15["bb_lower"] = bb_mid - 2 * bb_std
    m15["bb_width_atr"] = 4 * bb_std / m15["atr14"]
    m15["bb_width_pct_lag1_256"] = m15["bb_width_atr"].shift(1).rolling(256, min_periods=256).rank(pct=True)
    m15["atr_pct_lag1_256"] = m15["atr14"].shift(1).rolling(256, min_periods=256).rank(pct=True)

    h1["atr14_h1"] = atr_wilder(h1, 14)
    h1["ema20_h1"] = h1["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    h1["ema50_h1"] = h1["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    h1["gap_h1_atr"] = (h1["ema20_h1"] - h1["ema50_h1"]) / h1["atr14_h1"]

    h4["atr14_h4"] = atr_wilder(h4, 14)
    h4["ema20_h4"] = h4["close"].ewm(span=20, adjust=False, min_periods=20).mean()
    h4["ema50_h4"] = h4["close"].ewm(span=50, adjust=False, min_periods=50).mean()
    h4["gap_h4_atr"] = (h4["ema20_h4"] - h4["ema50_h4"]) / h4["atr14_h4"]

    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h1[["bar_close_time", "gap_h1_atr"]].dropna().sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined = pd.merge_asof(
        joined.sort_values("bar_close_time"),
        h4[["bar_close_time", "gap_h4_atr"]].dropna().sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    ).sort_values("bar_close_time", kind="mergesort").reset_index(drop=True)

    joined["band_upper"] = joined[["ema20", "ema50"]].max(axis=1)
    joined["band_lower"] = joined[["ema20", "ema50"]].min(axis=1)
    long_touch = joined["close"] <= joined["band_upper"]
    short_touch = joined["close"] >= joined["band_lower"]
    joined["prior_long_touch4"] = long_touch.shift(1).rolling(4, min_periods=4).max().fillna(0).astype(bool)
    joined["prior_short_touch4"] = short_touch.shift(1).rolling(4, min_periods=4).max().fillna(0).astype(bool)
    return joined, pd.DatetimeIndex(m1["bar_open_time"])


def proposal_record(row: object, candidate_id: str, strength: float, exact_m1: pd.DatetimeIndex) -> dict[str, object]:
    code, family, direction = CANDIDATES[candidate_id]
    decision = pd.Timestamp(row.bar_close_time)
    percentile = float(row.atr_pct_lag1_256) if np.isfinite(row.atr_pct_lag1_256) else np.nan
    volatility = "UNKNOWN"
    if np.isfinite(percentile):
        volatility = "LOW" if percentile <= 1 / 3 else ("HIGH" if percentile >= 2 / 3 else "MID")
    if row.gap_h1_atr >= 0.15 and row.gap_h4_atr >= 0.15:
        trend = "UP_TREND"
    elif row.gap_h1_atr <= -0.15 and row.gap_h4_atr <= -0.15:
        trend = "DOWN_TREND"
    else:
        trend = "RANGE_TRANSITION"
    exact = decision in exact_m1
    return {
        "decision_time": decision,
        "candidate_id": candidate_id,
        "candidate_definition_version": "v1",
        "candidate_code": code,
        "candidate_family": family,
        "direction": direction,
        "source_timeframe": "M15",
        "source_bar_open_time": pd.Timestamp(row.bar_open_time),
        "source_bar_close_time": decision,
        "proposal_strength_label_free": float(strength),
        "exact_m1_available": bool(exact),
        "entry_eligible": bool(exact),
        "server_hour": int(decision.hour),
        "server_weekday": int(decision.dayofweek),
        "volatility_regime": volatility,
        "trend_regime": trend,
        "m15_atr_pct_lag1_256": percentile,
        "h1_gap_atr": float(row.gap_h1_atr),
        "h4_gap_atr": float(row.gap_h4_atr),
    }


def generate_raw_proposals(joined: pd.DataFrame, exact_m1: pd.DatetimeIndex) -> pd.DataFrame:
    pending: dict[str, Pending | None] = {key: None for key in CANDIDATES if "004" not in key}
    active_004_long = False
    active_004_short = False
    output: list[dict[str, object]] = []

    for index, row in enumerate(joined.itertuples(index=False)):
        if not np.isfinite([row.atr14, row.ema20, row.ema50, row.gap_h1_atr, row.gap_h4_atr]).all():
            active_004_long = False
            active_004_short = False
            continue
        atr = float(row.atr14)
        long_cont = row.gap_h1_atr > 0 and row.gap_h4_atr >= -0.10
        short_cont = row.gap_h1_atr < 0 and row.gap_h4_atr <= 0.10
        long_failed = row.gap_h1_atr >= -0.15
        short_failed = row.gap_h1_atr <= 0.15
        cleared_this_bar: set[str] = set()

        for candidate_id, maximum_age in (("GML1-NCD-001-L", 8), ("GML1-NCD-001-S", 8)):
            state = pending[candidate_id]
            if state is None:
                continue
            age = index - state.setup_index
            if age > maximum_age:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
                continue
            if candidate_id.endswith("-L"):
                invalid = row.close < state.level - 0.20 * atr
                confirmed = row.low <= state.level + 0.15 * atr and row.close >= state.level + 0.05 * atr and row.signed_body > 0
                strength = (row.close - state.level) / atr
            else:
                invalid = row.close > state.level + 0.20 * atr
                confirmed = row.high >= state.level - 0.15 * atr and row.close <= state.level - 0.05 * atr and row.signed_body < 0
                strength = (state.level - row.close) / atr
            if invalid:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
            elif confirmed:
                output.append(proposal_record(row, candidate_id, strength, exact_m1))
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)

        for candidate_id, maximum_age in (("GML1-NCD-002-L", 6), ("GML1-NCD-002-S", 6)):
            state = pending[candidate_id]
            if state is None:
                continue
            age = index - state.setup_index
            if age > maximum_age:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
                continue
            if candidate_id.endswith("-L"):
                invalid = row.close < state.level - 0.20 * atr
                confirmed = row.low <= state.level and row.low >= state.level - 0.40 * atr and row.close > state.level + 0.03 * atr and row.signed_body > 0
                strength = (row.close - state.level) / atr
            else:
                invalid = row.close > state.level + 0.20 * atr
                confirmed = row.high >= state.level and row.high <= state.level + 0.40 * atr and row.close < state.level - 0.03 * atr and row.signed_body < 0
                strength = (state.level - row.close) / atr
            if invalid:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
            elif confirmed:
                output.append(proposal_record(row, candidate_id, strength, exact_m1))
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)

        for candidate_id, maximum_age in (("GML1-NCD-003-L", 12), ("GML1-NCD-003-S", 12)):
            state = pending[candidate_id]
            if state is None:
                continue
            age = index - state.setup_index
            if age > maximum_age:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
                continue
            if candidate_id.endswith("-L"):
                invalid = row.close < state.level - 0.25 * atr
                confirmed = age >= 2 and row.low <= row.ema20 + 0.20 * atr and row.close > state.level and row.close_location >= 0.60 and row.signed_body > 0
                strength = float(state.setup_range_atr or 0) + max(0.0, row.close_location - 0.5)
            else:
                invalid = row.close > state.level + 0.25 * atr
                confirmed = age >= 2 and row.high >= row.ema20 - 0.20 * atr and row.close < state.level and row.close_location <= 0.40 and row.signed_body < 0
                strength = float(state.setup_range_atr or 0) + max(0.0, 0.5 - row.close_location)
            if invalid:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
            elif confirmed:
                output.append(proposal_record(row, candidate_id, strength, exact_m1))
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)

        for candidate_id, maximum_age in (("GML1-NCD-005-L", 4), ("GML1-NCD-005-S", 4)):
            state = pending[candidate_id]
            if state is None:
                continue
            age = index - state.setup_index
            if age > maximum_age:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
                continue
            if candidate_id.endswith("-L"):
                invalid = row.close < state.level - 0.20 * atr
                confirmed = row.close > float(state.opposite) and row.signed_body > 0 and row.close_location >= 0.60
                strength = (row.close - float(state.opposite)) / atr
            else:
                invalid = row.close > state.level + 0.20 * atr
                confirmed = row.close < float(state.opposite) and row.signed_body < 0 and row.close_location <= 0.40
                strength = (float(state.opposite) - row.close) / atr
            if invalid:
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)
            elif confirmed:
                output.append(proposal_record(row, candidate_id, strength, exact_m1))
                pending[candidate_id] = None
                cleared_this_bar.add(candidate_id)

        active_long = row.ema20 > row.ema50 and long_cont and row.prior_long_touch4 and row.close >= row.band_upper + 0.10 * atr and row.signed_body >= 0.25 * atr and row.close_location >= 0.65
        active_short = row.ema20 < row.ema50 and short_cont and row.prior_short_touch4 and row.close <= row.band_lower - 0.10 * atr and row.signed_body <= -0.25 * atr and row.close_location <= 0.35
        if active_long and not active_004_long:
            output.append(proposal_record(row, "GML1-NCD-004-L", (row.close - row.band_upper) / atr, exact_m1))
        if active_short and not active_004_short:
            output.append(proposal_record(row, "GML1-NCD-004-S", (row.band_lower - row.close) / atr, exact_m1))
        active_004_long = bool(active_long)
        active_004_short = bool(active_short)

        if "GML1-NCD-001-L" not in cleared_this_bar and pending["GML1-NCD-001-L"] is None and long_cont and np.isfinite(row.prev_high_20) and row.close > row.prev_high_20 + 0.10 * atr and row.signed_body >= 0.35 * atr:
            pending["GML1-NCD-001-L"] = Pending(index, float(row.prev_high_20))
        if "GML1-NCD-001-S" not in cleared_this_bar and pending["GML1-NCD-001-S"] is None and short_cont and np.isfinite(row.prev_low_20) and row.close < row.prev_low_20 - 0.10 * atr and row.signed_body <= -0.35 * atr:
            pending["GML1-NCD-001-S"] = Pending(index, float(row.prev_low_20))
        if "GML1-NCD-002-L" not in cleared_this_bar and pending["GML1-NCD-002-L"] is None and long_cont and np.isfinite(row.prev_high_50) and row.close > row.prev_high_50 + 0.05 * atr and row.signed_body >= 0.25 * atr:
            pending["GML1-NCD-002-L"] = Pending(index, float(row.prev_high_50))
        if "GML1-NCD-002-S" not in cleared_this_bar and pending["GML1-NCD-002-S"] is None and short_cont and np.isfinite(row.prev_low_50) and row.close < row.prev_low_50 - 0.05 * atr and row.signed_body <= -0.25 * atr:
            pending["GML1-NCD-002-S"] = Pending(index, float(row.prev_low_50))
        if "GML1-NCD-003-L" not in cleared_this_bar and pending["GML1-NCD-003-L"] is None and long_cont and np.isfinite(row.bb_width_pct_lag1_256) and row.bb_width_pct_lag1_256 <= 0.25 and row.close > row.prev_high_20 and row.close > row.bb_upper and row.candle_range >= atr and row.signed_body > 0:
            pending["GML1-NCD-003-L"] = Pending(index, float(row.prev_high_20), setup_range_atr=float(row.candle_range / atr))
        if "GML1-NCD-003-S" not in cleared_this_bar and pending["GML1-NCD-003-S"] is None and short_cont and np.isfinite(row.bb_width_pct_lag1_256) and row.bb_width_pct_lag1_256 <= 0.25 and row.close < row.prev_low_20 and row.close < row.bb_lower and row.candle_range >= atr and row.signed_body < 0:
            pending["GML1-NCD-003-S"] = Pending(index, float(row.prev_low_20), setup_range_atr=float(row.candle_range / atr))
        if "GML1-NCD-005-L" not in cleared_this_bar and pending["GML1-NCD-005-L"] is None and long_failed and np.isfinite(row.prev_low_20) and row.low < row.prev_low_20 - 0.10 * atr and row.close > row.prev_low_20:
            pending["GML1-NCD-005-L"] = Pending(index, float(row.prev_low_20), opposite=float(row.high))
        if "GML1-NCD-005-S" not in cleared_this_bar and pending["GML1-NCD-005-S"] is None and short_failed and np.isfinite(row.prev_high_20) and row.high > row.prev_high_20 + 0.10 * atr and row.close < row.prev_high_20:
            pending["GML1-NCD-005-S"] = Pending(index, float(row.prev_high_20), opposite=float(row.low))

    frame = pd.DataFrame(output)
    if frame.empty:
        return frame
    frame = frame.sort_values(["decision_time", "candidate_id"], kind="mergesort").reset_index(drop=True)
    if frame.duplicated(["decision_time", "candidate_id"]).any():
        raise AssertionError("Duplicate raw proposal key")
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GML1 NCD v1 raw proposals without labels or outcomes")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    context, exact_m1 = build_context(args.raw_dir, live=args.live)
    proposals = generate_raw_proposals(context, exact_m1)
    deterministic_csv_gzip(proposals, args.output)
    print(proposals.groupby("candidate_id").size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
