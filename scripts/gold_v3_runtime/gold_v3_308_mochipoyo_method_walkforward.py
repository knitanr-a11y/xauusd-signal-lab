#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_304_stage280_approximate_walkforward_backtest as metrics_base
from gold_v3_289_feature_core import GOLD_FILES, read_candles

POINT_SIZE = 0.01
YEARS = (2024, 2025, 2026)
RCI_PERIODS = (9, 14, 18)
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4
EMA_PERIODS = (20, 30, 40)
ZZ_DEPTH = 5
ZZ_DEVIATION_POINTS = 3.0
ZZ_BACKSTEP = 2


@dataclass(frozen=True)
class PairSpec:
    name: str
    main_tf: str
    higher_tf: str
    max_hold_minutes: int
    cooldown_bars: int


PAIR_SPECS = (
    PairSpec("M5_H4", "M5", "H4", 720, 12),
    PairSpec("M15_H4", "M15", "H4", 2160, 8),
    PairSpec("H1_D1", "H1", "D1", 10080, 4),
)

SETUP_SPECS = (
    {"name": "TREND_SCORE6", "kind": "TREND", "threshold": 6.0, "required": None},
    {"name": "TREND_SCORE7", "kind": "TREND", "threshold": 7.0, "required": None},
    {"name": "HIDDEN_SCORE6", "kind": "TREND", "threshold": 6.0, "required": "HIDDEN"},
    {"name": "REVERSAL_SCORE6", "kind": "REVERSAL", "threshold": 6.0, "required": "REGULAR"},
)

EXIT_PROFILES = (
    {"name": "RR1_0", "kind": "RR", "rr": 1.0},
    {"name": "RR1_5", "kind": "RR", "rr": 1.5},
    {"name": "RCI_OPPOSITE70", "kind": "RCI", "rr": None},
    {"name": "STRUCT_TARGET", "kind": "STRUCT", "rr": None},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--trades-csv", default="")
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    parser.add_argument("--top", type=int, default=200)
    return parser.parse_args()


def rci(series: pd.Series, period: int) -> pd.Series:
    time_rank = np.arange(1.0, period + 1.0)
    denominator = period * (period * period - 1.0)

    def calculate(values: np.ndarray) -> float:
        if not np.isfinite(values).all():
            return np.nan
        price_rank = pd.Series(values).rank(method="average").to_numpy(float)
        difference = time_rank - price_rank
        return float((1.0 - 6.0 * np.square(difference).sum() / denominator) * 100.0)

    return series.rolling(period, min_periods=period).apply(calculate, raw=True)


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous = frame.close.shift(1)
    true_range = pd.concat(
        [
            frame.high - frame.low,
            (frame.high - previous).abs(),
            (frame.low - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def confirmed_zigzag(
    frame: pd.DataFrame,
    macd_line: pd.Series,
    atr_series: pd.Series,
    *,
    depth: int,
    deviation_price: float,
    backstep: int,
) -> pd.DataFrame:
    size = len(frame)
    high = frame.high.to_numpy(float)
    low = frame.low.to_numpy(float)
    macd = macd_line.to_numpy(float)

    event_high_price = np.full(size, np.nan)
    event_high_pivot = np.full(size, np.nan)
    event_low_price = np.full(size, np.nan)
    event_low_pivot = np.full(size, np.nan)
    bull_regular_event = np.zeros(size, dtype=bool)
    bull_hidden_event = np.zeros(size, dtype=bool)
    bear_regular_event = np.zeros(size, dtype=bool)
    bear_hidden_event = np.zeros(size, dtype=bool)

    highs: list[tuple[int, float, float]] = []
    lows: list[tuple[int, float, float]] = []

    for confirmed_index in range(depth * 2, size):
        pivot = confirmed_index - depth
        left = pivot - depth
        right = pivot + depth + 1
        high_window = high[left:right]
        low_window = low[left:right]
        is_high = bool(np.isfinite(high[pivot]) and high[pivot] >= np.nanmax(high_window))
        is_low = bool(np.isfinite(low[pivot]) and low[pivot] <= np.nanmin(low_window))
        if is_high and is_low:
            continue

        if is_high:
            if highs and pivot - highs[-1][0] < backstep:
                if high[pivot] <= highs[-1][1]:
                    is_high = False
                else:
                    highs.pop()
            if is_high and lows and abs(high[pivot] - lows[-1][1]) < deviation_price:
                is_high = False
            if is_high:
                current = (pivot, float(high[pivot]), float(macd[pivot]))
                if highs:
                    previous = highs[-1]
                    bear_regular_event[confirmed_index] = current[1] > previous[1] and current[2] < previous[2]
                    bear_hidden_event[confirmed_index] = current[1] < previous[1] and current[2] > previous[2]
                highs.append(current)
                event_high_price[confirmed_index] = current[1]
                event_high_pivot[confirmed_index] = current[0]

        if is_low:
            if lows and pivot - lows[-1][0] < backstep:
                if low[pivot] >= lows[-1][1]:
                    is_low = False
                else:
                    lows.pop()
            if is_low and highs and abs(highs[-1][1] - low[pivot]) < deviation_price:
                is_low = False
            if is_low:
                current = (pivot, float(low[pivot]), float(macd[pivot]))
                if lows:
                    previous = lows[-1]
                    bull_regular_event[confirmed_index] = current[1] < previous[1] and current[2] > previous[2]
                    bull_hidden_event[confirmed_index] = current[1] > previous[1] and current[2] < previous[2]
                lows.append(current)
                event_low_price[confirmed_index] = current[1]
                event_low_pivot[confirmed_index] = current[0]

    result = pd.DataFrame(index=frame.index)
    result["last_swing_high"] = pd.Series(event_high_price, index=frame.index).ffill()
    result["last_swing_low"] = pd.Series(event_low_price, index=frame.index).ffill()
    result["last_swing_high_pivot"] = pd.Series(event_high_pivot, index=frame.index).ffill()
    result["last_swing_low_pivot"] = pd.Series(event_low_pivot, index=frame.index).ffill()

    ttl = max(depth + backstep, 6)
    for name, events in (
        ("bull_regular_div", bull_regular_event),
        ("bull_hidden_div", bull_hidden_event),
        ("bear_regular_div", bear_regular_event),
        ("bear_hidden_div", bear_hidden_event),
    ):
        result[name] = (
            pd.Series(events.astype(int), index=frame.index)
            .rolling(ttl, min_periods=1)
            .max()
            .astype(bool)
        )

    wave = (result.last_swing_high - result.last_swing_low).abs()
    result["zigzag_wave_atr"] = wave / atr_series.replace(0.0, np.nan)
    return result


def indicator_frame(candle_dir: Path, timeframe: str, point_size: float) -> pd.DataFrame:
    raw = read_candles(
        candle_dir / GOLD_FILES[timeframe],
        None,
        timeframe=timeframe,
        require_spread=True,
    ).copy()
    work = raw[["time", "close_time", "open", "high", "low", "close", "spread"]].copy()
    work["atr14"] = atr(work, 14)
    for period in EMA_PERIODS:
        work[f"ema{period}"] = work.close.ewm(span=period, adjust=False).mean()
    fast = work.close.ewm(span=MACD_FAST, adjust=False).mean()
    slow = work.close.ewm(span=MACD_SLOW, adjust=False).mean()
    work["macd"] = fast - slow
    work["macd_signal"] = work.macd.ewm(span=MACD_SIGNAL, adjust=False).mean()
    work["macd_hist"] = work.macd - work.macd_signal
    for period in RCI_PERIODS:
        work[f"rci{period}"] = rci(work.close, period)

    zigzag = confirmed_zigzag(
        work,
        work.macd,
        work.atr14,
        depth=ZZ_DEPTH,
        deviation_price=ZZ_DEVIATION_POINTS * point_size,
        backstep=ZZ_BACKSTEP,
    )
    work = pd.concat([work, zigzag], axis=1)
    work["atr_median200"] = work.atr14.rolling(200, min_periods=50).median()
    work["atr_ratio"] = work.atr14 / work.atr_median200.replace(0.0, np.nan)
    work["ema_sep_atr"] = (work.ema20 - work.ema40).abs() / work.atr14.replace(0.0, np.nan)
    work["ema20_slope_atr"] = (work.ema20 - work.ema20.shift(3)) / work.atr14.replace(0.0, np.nan)
    work["rolling_low20"] = work.low.rolling(20, min_periods=10).min().shift(1)
    work["rolling_high20"] = work.high.rolling(20, min_periods=10).max().shift(1)
    return work


def recent_extreme_turn(series: pd.Series, direction: int, lookback: int = 5) -> pd.Series:
    if direction == 1:
        touched = series.rolling(lookback, min_periods=1).min() <= -70.0
        return touched & (series > -70.0) & (series.diff() > 0.0)
    touched = series.rolling(lookback, min_periods=1).max() >= 70.0
    return touched & (series < 70.0) & (series.diff() < 0.0)


def enrich_main_with_higher(main: pd.DataFrame, higher: pd.DataFrame) -> pd.DataFrame:
    higher_columns = [
        "close_time",
        "close",
        "atr14",
        "ema20",
        "ema30",
        "ema40",
        "ema_sep_atr",
        "ema20_slope_atr",
        "rci9",
        "rci14",
        "rci18",
        "macd_hist",
        "bull_regular_div",
        "bull_hidden_div",
        "bear_regular_div",
        "bear_hidden_div",
        "zigzag_wave_atr",
        "atr_ratio",
        "rci_turn_long_ctx",
        "rci_turn_short_ctx",
    ]
    renamed = higher[higher_columns].rename(
        columns={column: f"htf_{column}" for column in higher_columns if column != "close_time"}
    )
    merged = pd.merge_asof(
        main.sort_values("close_time"),
        renamed.sort_values("close_time"),
        on="close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    boolean_columns = [
        "htf_bull_regular_div",
        "htf_bull_hidden_div",
        "htf_bear_regular_div",
        "htf_bear_hidden_div",
        "htf_rci_turn_long_ctx",
        "htf_rci_turn_short_ctx",
    ]
    for column in boolean_columns:
        merged[column] = merged[column].fillna(False).astype(bool)
    return merged.reset_index(drop=True)


def build_signal_frame(main: pd.DataFrame, higher: pd.DataFrame) -> pd.DataFrame:
    higher_context = higher.copy()
    higher_context["rci_turn_long_ctx"] = (
        recent_extreme_turn(higher_context.rci9, 1, 4)
        | recent_extreme_turn(higher_context.rci14, 1, 4)
    )
    higher_context["rci_turn_short_ctx"] = (
        recent_extreme_turn(higher_context.rci9, -1, 4)
        | recent_extreme_turn(higher_context.rci14, -1, 4)
    )
    work = enrich_main_with_higher(main, higher_context)

    work["ltf_bull_trend"] = (
        (work.ema20 > work.ema30)
        & (work.ema30 > work.ema40)
        & (work.ema20_slope_atr > 0.02)
        & (work.ema_sep_atr >= 0.08)
    )
    work["ltf_bear_trend"] = (
        (work.ema20 < work.ema30)
        & (work.ema30 < work.ema40)
        & (work.ema20_slope_atr < -0.02)
        & (work.ema_sep_atr >= 0.08)
    )
    work["htf_bull_trend"] = (
        (work.htf_ema20 > work.htf_ema30)
        & (work.htf_ema30 > work.htf_ema40)
        & (work.htf_ema20_slope_atr > 0.01)
        & (work.htf_ema_sep_atr >= 0.06)
    )
    work["htf_bear_trend"] = (
        (work.htf_ema20 < work.htf_ema30)
        & (work.htf_ema30 < work.htf_ema40)
        & (work.htf_ema20_slope_atr < -0.01)
        & (work.htf_ema_sep_atr >= 0.06)
    )

    for direction, suffix in ((1, "long"), (-1, "short")):
        work[f"rci_turn_{suffix}"] = recent_extreme_turn(work.rci9, direction, 6) | recent_extreme_turn(work.rci14, direction, 6)
        work[f"htf_rci_turn_{suffix}"] = work[f"htf_rci_turn_{suffix}_ctx"]
        if direction == 1:
            work[f"macd_accel_{suffix}"] = (
                ((work.macd_hist > 0.0) & (work.macd_hist.shift(1) <= 0.0))
                | ((work.macd_hist > work.macd_hist.shift(1)) & (work.macd_hist.shift(1) > work.macd_hist.shift(2)))
            )
            work[f"ema_reclaim_{suffix}"] = (work.close > work.ema20) & (work.close.shift(1) <= work.ema20.shift(1))
            work[f"pullback_{suffix}"] = (
                ((work.low - work.ema20) / work.atr14.replace(0.0, np.nan))
                .rolling(6, min_periods=1)
                .min()
                <= 0.15
            ) & (work.close >= work.ema20)
            level = work.last_swing_high.shift(1)
            breakout = (work.close > level) & (work.close.shift(1) <= level.shift(1))
            recent_break = breakout.rolling(12, min_periods=1).max().astype(bool)
            work[f"roll_reversal_{suffix}"] = recent_break & (work.low <= level + 0.20 * work.atr14) & (work.close >= level)
        else:
            work[f"macd_accel_{suffix}"] = (
                ((work.macd_hist < 0.0) & (work.macd_hist.shift(1) >= 0.0))
                | ((work.macd_hist < work.macd_hist.shift(1)) & (work.macd_hist.shift(1) < work.macd_hist.shift(2)))
            )
            work[f"ema_reclaim_{suffix}"] = (work.close < work.ema20) & (work.close.shift(1) >= work.ema20.shift(1))
            work[f"pullback_{suffix}"] = (
                ((work.high - work.ema20) / work.atr14.replace(0.0, np.nan))
                .rolling(6, min_periods=1)
                .max()
                >= -0.15
            ) & (work.close <= work.ema20)
            level = work.last_swing_low.shift(1)
            breakout = (work.close < level) & (work.close.shift(1) >= level.shift(1))
            recent_break = breakout.rolling(12, min_periods=1).max().astype(bool)
            work[f"roll_reversal_{suffix}"] = recent_break & (work.high >= level - 0.20 * work.atr14) & (work.close <= level)

    work["high_volatility"] = (
        (work.atr_ratio >= 0.90)
        & ((work.zigzag_wave_atr >= 1.25) | (work.atr_ratio >= 1.10))
    )
    nearest_five = np.round(work.close / 5.0) * 5.0
    work["round_number_near"] = (work.close - nearest_five).abs() <= 0.15 * work.atr14

    work["trend_score_long"] = (
        2.0 * work.htf_bull_trend.astype(float)
        + 1.0 * (work.htf_rci_turn_long | work.htf_bull_hidden_div).astype(float)
        + 2.0 * work.ltf_bull_trend.astype(float)
        + 1.0 * work.pullback_long.astype(float)
        + 1.0 * work.rci_turn_long.astype(float)
        + 1.0 * work.macd_accel_long.astype(float)
        + 2.0 * work.bull_hidden_div.astype(float)
        + 1.0 * work.high_volatility.astype(float)
        + 1.0 * work.roll_reversal_long.astype(float)
        + 0.5 * work.round_number_near.astype(float)
    )
    work["trend_score_short"] = (
        2.0 * work.htf_bear_trend.astype(float)
        + 1.0 * (work.htf_rci_turn_short | work.htf_bear_hidden_div).astype(float)
        + 2.0 * work.ltf_bear_trend.astype(float)
        + 1.0 * work.pullback_short.astype(float)
        + 1.0 * work.rci_turn_short.astype(float)
        + 1.0 * work.macd_accel_short.astype(float)
        + 2.0 * work.bear_hidden_div.astype(float)
        + 1.0 * work.high_volatility.astype(float)
        + 1.0 * work.roll_reversal_short.astype(float)
        + 0.5 * work.round_number_near.astype(float)
    )

    work["reversal_score_long"] = (
        2.0 * work.htf_rci_turn_long.astype(float)
        + 2.0 * (work.htf_bull_regular_div | work.bull_regular_div).astype(float)
        + 1.0 * work.rci_turn_long.astype(float)
        + 1.0 * work.macd_accel_long.astype(float)
        + 1.0 * work.ema_reclaim_long.astype(float)
        + 1.0 * work.high_volatility.astype(float)
        + 0.5 * work.round_number_near.astype(float)
        + 1.0 * (~work.htf_bear_trend).astype(float)
    )
    work["reversal_score_short"] = (
        2.0 * work.htf_rci_turn_short.astype(float)
        + 2.0 * (work.htf_bear_regular_div | work.bear_regular_div).astype(float)
        + 1.0 * work.rci_turn_short.astype(float)
        + 1.0 * work.macd_accel_short.astype(float)
        + 1.0 * work.ema_reclaim_short.astype(float)
        + 1.0 * work.high_volatility.astype(float)
        + 0.5 * work.round_number_near.astype(float)
        + 1.0 * (~work.htf_bull_trend).astype(float)
    )
    return work


def edge_with_cooldown(mask: pd.Series, cooldown_bars: int) -> pd.Series:
    values = mask.fillna(False).to_numpy(bool)
    result = np.zeros(len(values), dtype=bool)
    last = -10**9
    armed = True
    for index, current in enumerate(values):
        if not current:
            armed = True
            continue
        if armed and index - last >= cooldown_bars:
            result[index] = True
            last = index
            armed = False
    return pd.Series(result, index=mask.index)


def generate_signals(frame: pd.DataFrame, pair: PairSpec) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for setup in SETUP_SPECS:
        for direction, suffix in ((1, "long"), (-1, "short")):
            if setup["kind"] == "TREND":
                score_column = f"trend_score_{suffix}"
                core = frame[f"htf_{'bull' if direction == 1 else 'bear'}_trend"] & frame[f"ltf_{'bull' if direction == 1 else 'bear'}_trend"]
            else:
                score_column = f"reversal_score_{suffix}"
                core = frame[f"htf_rci_turn_{suffix}"] & frame[f"rci_turn_{suffix}"]
            mask = core & (frame[score_column] >= float(setup["threshold"]))
            if setup["required"] == "HIDDEN":
                hidden = frame["bull_hidden_div" if direction == 1 else "bear_hidden_div"] | frame["htf_bull_hidden_div" if direction == 1 else "htf_bear_hidden_div"]
                mask &= hidden
            elif setup["required"] == "REGULAR":
                regular = frame["bull_regular_div" if direction == 1 else "bear_regular_div"] | frame["htf_bull_regular_div" if direction == 1 else "htf_bear_regular_div"]
                mask &= regular
            mask &= frame.high_volatility & frame.atr14.notna()
            onset = edge_with_cooldown(mask, pair.cooldown_bars)
            for index in frame.index[onset]:
                row = frame.loc[index]
                signals.append(
                    {
                        "pair": pair.name,
                        "main_tf": pair.main_tf,
                        "higher_tf": pair.higher_tf,
                        "setup": setup["name"],
                        "direction": "LONG" if direction == 1 else "SHORT",
                        "direction_num": direction,
                        "signal_index": int(index),
                        "decision_dt": pd.Timestamp(row.close_time),
                        "quality_score": float(row[score_column]),
                        "atr_entry_context": float(row.atr14),
                        "last_swing_high": float(row.last_swing_high) if pd.notna(row.last_swing_high) else None,
                        "last_swing_low": float(row.last_swing_low) if pd.notna(row.last_swing_low) else None,
                        "round_number_near": bool(row.round_number_near),
                        "high_volatility": bool(row.high_volatility),
                    }
                )
    return signals


def scheduled_rci_exit(frame: pd.DataFrame, entry_index: int, direction: int, max_exit_dt: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    for index in range(entry_index, len(frame)):
        close_dt = pd.Timestamp(frame.close_time.iloc[index])
        if close_dt > max_exit_dt:
            return None
        rci_value = float(frame.rci9.iloc[index])
        if direction == 1 and rci_value >= 70.0:
            return close_dt, float(frame.close.iloc[index])
        if direction == -1 and rci_value <= -70.0:
            return close_dt, float(frame.close.iloc[index])
    return None


def simulate_trade(
    signal: dict[str, Any],
    frame: pd.DataFrame,
    m1: pd.DataFrame,
    pair: PairSpec,
    exit_profile: dict[str, Any],
    point_size: float,
) -> dict[str, Any] | None:
    signal_index = int(signal["signal_index"])
    entry_index = signal_index + 1
    if entry_index >= len(frame):
        return None
    entry_dt = pd.Timestamp(frame.time.iloc[entry_index])
    if entry_dt != pd.Timestamp(signal["decision_dt"]):
        return None
    entry_price = float(frame.open.iloc[entry_index])
    spread_points = max(float(frame.spread.iloc[entry_index]), 0.0)
    spread_price = spread_points * point_size
    atr_value = float(frame.atr14.iloc[signal_index])
    if not math.isfinite(atr_value) or atr_value <= 0.0:
        return None

    direction = int(signal["direction_num"])
    if direction == 1:
        swing = signal["last_swing_low"]
        fallback = float(frame.rolling_low20.iloc[signal_index])
        structural = float(swing) if swing is not None else fallback
        if not math.isfinite(structural):
            return None
        raw_stop = structural - 0.10 * atr_value
        stop_distance = entry_price - raw_stop
    else:
        swing = signal["last_swing_high"]
        fallback = float(frame.rolling_high20.iloc[signal_index])
        structural = float(swing) if swing is not None else fallback
        if not math.isfinite(structural):
            return None
        raw_stop = structural + 0.10 * atr_value
        stop_distance = raw_stop - entry_price

    stop_distance = max(stop_distance, 0.75 * atr_value)
    if stop_distance > 2.0 * atr_value:
        return None
    sl_price = entry_price - direction * stop_distance

    max_exit_dt = entry_dt + pd.Timedelta(minutes=pair.max_hold_minutes)
    target_price: float | None = None
    scheduled_exit: tuple[pd.Timestamp, float] | None = None
    if exit_profile["kind"] == "RR":
        target_price = entry_price + direction * float(exit_profile["rr"]) * stop_distance
    elif exit_profile["kind"] == "STRUCT":
        target = signal["last_swing_high"] if direction == 1 else signal["last_swing_low"]
        if target is None:
            return None
        target_price = float(target)
        reward = direction * (target_price - entry_price)
        if reward < stop_distance:
            return None
    elif exit_profile["kind"] == "RCI":
        scheduled_exit = scheduled_rci_exit(frame, entry_index, direction, max_exit_dt)

    effective_end = scheduled_exit[0] if scheduled_exit is not None else max_exit_dt
    m1_time = m1.time.to_numpy("datetime64[ns]")
    first = int(np.searchsorted(m1_time, np.datetime64(entry_dt), side="left"))
    last_exclusive = int(np.searchsorted(m1_time, np.datetime64(effective_end), side="left"))
    if first >= len(m1) or pd.Timestamp(m1.time.iloc[first]) != entry_dt:
        return None
    if last_exclusive <= first:
        return None

    exit_reason = "TIME"
    exit_dt = effective_end
    if scheduled_exit is not None:
        exit_reason = "RCI70"
        exit_price = float(scheduled_exit[1])
    else:
        last_bar = min(last_exclusive - 1, len(m1) - 1)
        exit_price = float(m1.close.iloc[last_bar])
        exit_dt = pd.Timestamp(m1.time.iloc[last_bar]) + pd.Timedelta(minutes=1)

    for index in range(first, min(last_exclusive, len(m1))):
        high = float(m1.high.iloc[index])
        low = float(m1.low.iloc[index])
        hit_sl = low <= sl_price if direction == 1 else high >= sl_price
        hit_tp = False
        if target_price is not None:
            hit_tp = high >= target_price if direction == 1 else low <= target_price
        if hit_sl:
            exit_reason = "SL"
            exit_price = sl_price
            exit_dt = pd.Timestamp(m1.time.iloc[index]) + pd.Timedelta(minutes=1)
            break
        if hit_tp:
            exit_reason = "TP" if exit_profile["kind"] == "RR" else "STRUCT_TARGET"
            exit_price = target_price
            exit_dt = pd.Timestamp(m1.time.iloc[index]) + pd.Timedelta(minutes=1)
            break

    gross_pnl = direction * (exit_price - entry_price)
    net_pnl = gross_pnl - spread_price
    trade = dict(signal)
    trade.update(
        {
            "exit_profile": exit_profile["name"],
            "entry_dt": entry_dt,
            "exit_dt": exit_dt,
            "entry_price": entry_price,
            "entry_spread_points": spread_points,
            "entry_spread_price": spread_price,
            "atr_entry": atr_value,
            "risk_price": stop_distance,
            "sl_price": sl_price,
            "tp_price": target_price,
            "exit_price": float(exit_price),
            "exit_reason": exit_reason,
            "gross_pnl": float(gross_pnl),
            "spread_adjusted_pnl": float(net_pnl),
            "gross_r": float(gross_pnl / stop_distance),
            "spread_adjusted_r": float(net_pnl / stop_distance),
        }
    )
    return trade


def one_position(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_entry: dict[pd.Timestamp, dict[str, Any]] = {}
    for trade in trades:
        entry = pd.Timestamp(trade["entry_dt"])
        current = by_entry.get(entry)
        if current is None or float(trade["quality_score"]) > float(current["quality_score"]):
            by_entry[entry] = trade
    ordered = sorted(
        by_entry.values(),
        key=lambda row: (pd.Timestamp(row["entry_dt"]), -float(row["quality_score"]), row["pair"], row["setup"]),
    )
    kept: list[dict[str, Any]] = []
    active_until = pd.Timestamp.min
    for trade in ordered:
        entry = pd.Timestamp(trade["entry_dt"])
        if entry < active_until:
            continue
        kept.append(trade)
        active_until = pd.Timestamp(trade["exit_dt"])
    return kept


def summarize(trades: list[dict[str, Any]]) -> dict[str, Any]:
    summary = metrics_base.summarize_trades(trades)
    summary["exit_reason_counts"] = {
        reason: int(sum(row["exit_reason"] == reason for row in trades))
        for reason in sorted({row["exit_reason"] for row in trades})
    }
    summary["long_trades"] = int(sum(row["direction_num"] == 1 for row in trades))
    summary["short_trades"] = int(sum(row["direction_num"] == -1 for row in trades))
    return summary


def yearly_summary(trades: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for year in YEARS:
        year_trades = [row for row in trades if pd.Timestamp(row["entry_dt"]).year == year]
        result[str(year)] = summarize(year_trades)
    return result


def gate_result(summary: dict[str, Any], yearly: dict[str, Any]) -> dict[str, bool]:
    pf = summary["spread_adjusted_profit_factor"]
    pf_value = float("inf") if pf is None and summary["spread_adjusted_total_usd"] > 0 else float(pf or 0.0)
    minimum_year = min(int(yearly[str(year)]["trades"]) for year in YEARS)
    worst_year_r = min(float(yearly[str(year)]["spread_adjusted_total_r"]) for year in YEARS)
    balanced = bool(
        summary["trades"] >= 75
        and minimum_year >= 12
        and summary["win_rate"] >= 0.50
        and pf_value >= 1.30
        and summary["spread_adjusted_total_r"] > 0.0
        and summary["spread_adjusted_max_drawdown_r"] <= 12.0
        and worst_year_r > -1.0
    )
    high_frequency = bool(
        summary["trades"] >= 150
        and minimum_year >= 20
        and summary["win_rate"] >= 0.48
        and pf_value >= 1.20
        and summary["spread_adjusted_total_r"] > 0.0
        and summary["spread_adjusted_max_drawdown_r"] <= 16.0
        and worst_year_r > -1.0
    )
    return {"balanced_pass": balanced, "high_frequency_pass": high_frequency}


def build_pools(family_keys: list[str]) -> dict[str, list[str]]:
    pools: dict[str, list[str]] = {}
    for exit_profile in (item["name"] for item in EXIT_PROFILES):
        same_exit = [key for key in family_keys if key.endswith("|" + exit_profile)]
        pools[f"MOCHIPOYO_ALL|{exit_profile}"] = same_exit
        pools[f"MOCHIPOYO_TREND_ALL|{exit_profile}"] = [key for key in same_exit if "REVERSAL" not in key]
        pools[f"MOCHIPOYO_HIDDEN_ALL|{exit_profile}"] = [key for key in same_exit if "HIDDEN" in key]
        pools[f"MOCHIPOYO_REVERSAL_ALL|{exit_profile}"] = [key for key in same_exit if "REVERSAL" in key]
        for pair in PAIR_SPECS:
            pair_keys = [key for key in same_exit if key.startswith(pair.name + "|")]
            pools[f"{pair.name}_ALL|{exit_profile}"] = pair_keys
            pools[f"{pair.name}_TREND|{exit_profile}"] = [key for key in pair_keys if "REVERSAL" not in key]
    return {name: members for name, members in pools.items() if members}


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else candle_dir / "stage308_mochipoyo_method_walkforward.json"
    trades_csv = Path(args.trades_csv).expanduser().resolve() if args.trades_csv else output.with_name(output.stem + "_trades.csv")

    point_size = float(args.point_size)
    m1 = read_candles(
        candle_dir / GOLD_FILES["M1"],
        None,
        timeframe="M1",
        require_spread=True,
    ).copy()

    indicators: dict[str, pd.DataFrame] = {}
    pair_frames: dict[str, pd.DataFrame] = {}
    all_signals: list[dict[str, Any]] = []
    for pair in PAIR_SPECS:
        if pair.main_tf not in indicators:
            indicators[pair.main_tf] = indicator_frame(candle_dir, pair.main_tf, point_size)
        if pair.higher_tf not in indicators:
            indicators[pair.higher_tf] = indicator_frame(candle_dir, pair.higher_tf, point_size)
        frame = build_signal_frame(indicators[pair.main_tf], indicators[pair.higher_tf])
        pair_frames[pair.name] = frame
        pair_signals = generate_signals(frame, pair)
        pair_signals = [
            signal
            for signal in pair_signals
            if pd.Timestamp("2024-01-01") <= pd.Timestamp(signal["decision_dt"]) < pd.Timestamp("2027-01-01")
        ]
        all_signals.extend(pair_signals)

    trades: list[dict[str, Any]] = []
    for signal in all_signals:
        pair = next(item for item in PAIR_SPECS if item.name == signal["pair"])
        frame = pair_frames[pair.name]
        for exit_profile in EXIT_PROFILES:
            trade = simulate_trade(signal, frame, m1, pair, exit_profile, point_size)
            if trade is not None:
                trade["family_key"] = f"{signal['pair']}|{signal['setup']}|{signal['direction']}|{exit_profile['name']}"
                trades.append(trade)

    family_keys = sorted({row["family_key"] for row in trades})
    family_results: list[dict[str, Any]] = []
    family_raw_map: dict[str, list[dict[str, Any]]] = {}
    for family_key in family_keys:
        raw = [row for row in trades if row["family_key"] == family_key]
        portfolio = one_position(raw)
        family_raw_map[family_key] = raw
        summary = summarize(portfolio)
        yearly = yearly_summary(portfolio)
        family_results.append(
            {
                "family_key": family_key,
                "raw_trade_count": len(raw),
                "aggregate": summary,
                "yearly": yearly,
                **gate_result(summary, yearly),
            }
        )

    pools = build_pools(family_keys)
    pool_results: list[dict[str, Any]] = []
    for pool_name, members in pools.items():
        raw = [row for member in members for row in family_raw_map.get(member, [])]
        portfolio = one_position(raw)
        summary = summarize(portfolio)
        yearly = yearly_summary(portfolio)
        pool_results.append(
            {
                "pool": pool_name,
                "members": members,
                "aggregate": summary,
                "yearly": yearly,
                **gate_result(summary, yearly),
            }
        )

    def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        aggregate = row["aggregate"]
        return (
            not row["high_frequency_pass"],
            not row["balanced_pass"],
            -float(aggregate["spread_adjusted_total_r"]),
            float(aggregate["spread_adjusted_max_drawdown_r"]),
            -int(aggregate["trades"]),
        )

    family_results.sort(key=sort_key)
    pool_results.sort(key=sort_key)
    passes = [row for row in family_results + pool_results if row["balanced_pass"] or row["high_frequency_pass"]]

    pd.DataFrame([dict(trade) for trade in trades]).to_csv(trades_csv, index=False, encoding="utf-8-sig")

    report = {
        "status": "GOLD_V3_308_MOCHIPOYO_METHOD_WALKFORWARD_READY",
        "mode": "AUDIT_ONLY_RESEARCH_RULE_TRANSLATION",
        "decision": "MOCHIPOYO_RESEARCH_CANDIDATES_FOUND" if passes else "NO_MOCHIPOYO_CANDIDATE_PASSED",
        "source_translation": {
            "timeframe_pairs": [{"pair": item.name, "main": item.main_tf, "higher": item.higher_tf} for item in PAIR_SPECS],
            "ema": list(EMA_PERIODS),
            "rci": list(RCI_PERIODS),
            "macd": [MACD_FAST, MACD_SLOW, MACD_SIGNAL],
            "zigzag": {
                "depth": ZZ_DEPTH,
                "deviation_points": ZZ_DEVIATION_POINTS,
                "backstep": ZZ_BACKSTEP,
                "confirmation": "pivot is usable only after depth later bars have closed",
            },
            "confluence": [
                "higher-timeframe trend or RCI turn",
                "EMA20/30/40 alignment",
                "RCI extreme-zone turn",
                "MACD acceleration and regular/hidden divergence",
                "pullback/retest and roll-reversal bonus",
                "high-volatility gate using ATR ratio and confirmed ZigZag wave width",
                "round-number proximity is bonus only",
            ],
            "entry": "signal on closed main-timeframe bar; enter next exact main-timeframe open",
            "stop": "latest confirmed ZigZag swing plus 0.10 ATR buffer; minimum 0.75 ATR; skip above 2.0 ATR",
            "exit_profiles": [item["name"] for item in EXIT_PROFILES],
        },
        "important_scope": "The guide does not disclose the proprietary Mochipoyo alert formula. Stage308 implements the documented discretionary method objectively; it does not claim to reproduce the proprietary alert itself.",
        "data_contract": {
            "closed_candles_only": True,
            "time_basis": "MT5 server bar-open time; close_time derived from timeframe",
            "latest_rows": {tf: str(frame.time.max()) for tf, frame in indicators.items()},
            "m1_latest": str(m1.time.max()),
            "point_size": point_size,
            "years": list(YEARS),
        },
        "search": {
            "signals": len(all_signals),
            "simulated_trades_all_exit_profiles": len(trades),
            "family_count": len(family_results),
            "pool_count": len(pool_results),
            "pass_count": len(passes),
            "balanced_gate": {
                "trades": 75,
                "minimum_each_year": 12,
                "win_rate": 0.50,
                "profit_factor": 1.30,
                "max_dd_r": 12.0,
                "worst_year_r": -1.0,
            },
            "high_frequency_gate": {
                "trades": 150,
                "minimum_each_year": 20,
                "win_rate": 0.48,
                "profit_factor": 1.20,
                "max_dd_r": 16.0,
                "worst_year_r": -1.0,
            },
        },
        "passing_candidates": passes[:100],
        "family_leaderboard": family_results[: max(1, int(args.top))],
        "pool_leaderboard": pool_results[: max(1, int(args.top))],
        "outputs": {"trades_csv": str(trades_csv)},
        "promotion": {
            "performed": False,
            "production_stage280": "UNCHANGED_BLOCKED",
            "stage281": "UNCHANGED",
            "stage286": "UNCHANGED",
            "stage307": "RESULT_RETAINED_RESEARCH_ONLY",
            "next_if_pass": "integrated overlap/DD replay against Stage307 top ensemble and existing Stage292 candidates",
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
