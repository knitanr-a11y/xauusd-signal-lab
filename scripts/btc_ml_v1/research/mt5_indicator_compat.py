from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

H4_HOURS = 4
EMA_APPLIED_PRICE_CHOICES = ("close", "typical", "weighted")


def mt5_ema(values: Sequence[float] | pd.Series, period: int) -> np.ndarray:
    """MT5-style EMA: first value is the SMA of the first period, then recursive EMA."""
    if period <= 0:
        raise ValueError("period must be positive")
    array = np.asarray(values, dtype=float)
    output = np.full(len(array), np.nan, dtype=float)
    if len(array) < period:
        return output
    if not np.isfinite(array[:period]).all():
        raise ValueError("EMA seed contains non-finite values")
    output[period - 1] = float(array[:period].mean())
    alpha = 2.0 / (period + 1.0)
    for index in range(period, len(array)):
        value = array[index]
        if not np.isfinite(value):
            raise ValueError(f"EMA input is non-finite at index {index}")
        output[index] = alpha * value + (1.0 - alpha) * output[index - 1]
    return output


def applied_price(h4: pd.DataFrame, name: str) -> pd.Series:
    if name == "close":
        return h4["close"].astype(float)
    if name == "typical":
        return (h4["high"] + h4["low"] + h4["close"]) / 3.0
    if name == "weighted":
        return (h4["high"] + h4["low"] + 2.0 * h4["close"]) / 4.0
    raise ValueError(
        f"unsupported EMA applied price: {name}; choose one of {EMA_APPLIED_PRICE_CHOICES}"
    )


def mt5_true_range(high: Sequence[float], low: Sequence[float], close: Sequence[float]) -> np.ndarray:
    high_array = np.asarray(high, dtype=float)
    low_array = np.asarray(low, dtype=float)
    close_array = np.asarray(close, dtype=float)
    if not (len(high_array) == len(low_array) == len(close_array)):
        raise ValueError("OHLC lengths do not match")
    output = np.full(len(close_array), np.nan, dtype=float)
    if len(close_array) == 0:
        return output
    output[0] = abs(high_array[0] - low_array[0])
    for index in range(1, len(close_array)):
        output[index] = max(
            abs(high_array[index] - low_array[index]),
            abs(high_array[index] - close_array[index - 1]),
            abs(low_array[index] - close_array[index - 1]),
        )
    return output


def mt5_atr(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    period: int = 14,
) -> np.ndarray:
    """MT5/Wilder ATR: SMA seed followed by Wilder recursive smoothing."""
    if period <= 0:
        raise ValueError("period must be positive")
    true_range = mt5_true_range(high, low, close)
    output = np.full(len(true_range), np.nan, dtype=float)
    if len(true_range) < period:
        return output
    output[period - 1] = float(true_range[:period].mean())
    for index in range(period, len(true_range)):
        output[index] = (
            output[index - 1] * (period - 1) + true_range[index]
        ) / period
    return output


def add_h4_features_mt5(h4: pd.DataFrame, *, ema_applied_price: str) -> pd.DataFrame:
    required = {"time", "open", "high", "low", "close"}
    missing = sorted(required.difference(h4.columns))
    if missing:
        raise ValueError(f"H4 data is missing columns: {missing}")
    frame = h4.copy()
    price = applied_price(frame, ema_applied_price)
    frame["decision_time"] = frame["time"] + pd.Timedelta(hours=H4_HOURS)
    frame["ema20"] = mt5_ema(price, 20)
    frame["ema200"] = mt5_ema(price, 200)
    frame["atr14"] = mt5_atr(frame["high"], frame["low"], frame["close"], 14)
    frame["cross_long"] = (
        (frame["ema20"] > frame["ema200"])
        & (frame["ema20"].shift(1) <= frame["ema200"].shift(1))
    )
    frame["cross_short"] = (
        (frame["ema20"] < frame["ema200"])
        & (frame["ema20"].shift(1) >= frame["ema200"].shift(1))
    )
    frame["ema_applied_price"] = ema_applied_price
    return frame


def require_h4_warmup(
    h4: pd.DataFrame,
    *,
    research_start: pd.Timestamp,
    minimum_closed_bars: int = 1500,
) -> int:
    """Reject a run whose EMA200 history is too short to match a mature MT5 chart."""
    if "time" not in h4.columns:
        raise ValueError("H4 data has no time column")
    warmup_bars = int((pd.to_datetime(h4["time"]) < research_start).sum())
    if warmup_bars < minimum_closed_bars:
        earliest = pd.to_datetime(h4["time"]).min()
        raise ValueError(
            "Insufficient H4 EMA warm-up: "
            f"{warmup_bars} bars before {research_start}; need at least {minimum_closed_bars}. "
            f"Earliest H4 bar is {earliest}. Re-export H4 from 2017-01-01."
        )
    return warmup_bars
