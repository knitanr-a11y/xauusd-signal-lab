from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BreakoutContinuationSettings:
    """Settings for C-signal breakout continuation candidates.

    C is intended to catch trend-continuation breakouts that A/B do not catch:
        - A: hidden divergence pullback continuation
        - B: EMA20 pullback + MACD reacceleration
        - C: H1-aligned M15 breakout continuation
    """

    breakout_lookback_bars: int = 12
    min_breakout_atr: float = 0.00
    max_breakout_atr: float | None = None
    require_h1_trend: bool = True
    require_m15_ema_alignment: bool = True
    require_close_beyond_ema20: bool = True
    require_macd_hist_direction: bool = True
    require_macd_hist_acceleration: bool = True
    avoid_ab_overlap: bool = True

    def validate(self) -> None:
        if self.breakout_lookback_bars <= 1:
            raise ValueError(f"breakout_lookback_bars must be > 1: {self.breakout_lookback_bars}")
        if self.min_breakout_atr < 0:
            raise ValueError(f"min_breakout_atr must be >= 0: {self.min_breakout_atr}")
        if self.max_breakout_atr is not None and self.max_breakout_atr < self.min_breakout_atr:
            raise ValueError(
                "max_breakout_atr must be None or >= min_breakout_atr: "
                f"min={self.min_breakout_atr}, max={self.max_breakout_atr}"
            )


def _bool_col(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return df[column].fillna(False).astype(bool)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required breakout continuation columns: {missing}")


def add_breakout_continuation_signals(
    df: pd.DataFrame,
    settings: BreakoutContinuationSettings | None = None,
) -> pd.DataFrame:
    """Add C breakout-continuation signal columns.

    Signal timing:
        A signal is confirmed on the M15 close that breaks the previous range.
        The existing backtest engine enters on the next M15 open.

    BUY concept:
        H1 BUY trend + M15 EMA20>EMA50 + close above previous N-bar high
        + MACD histogram positive/accelerating.

    SELL concept:
        H1 SELL trend + M15 EMA20<EMA50 + close below previous N-bar low
        + MACD histogram negative/accelerating.
    """
    settings = settings or BreakoutContinuationSettings()
    settings.validate()

    required = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "ema_20",
        "ema_50",
        "atr_14",
        "macd_hist",
        "h1_trend",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_high_price",
    ]
    _require_columns(df, required)

    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    lookback = settings.breakout_lookback_bars

    previous_high = out["high"].shift(1).rolling(lookback, min_periods=lookback).max()
    previous_low = out["low"].shift(1).rolling(lookback, min_periods=lookback).min()
    atr = pd.to_numeric(out["atr_14"], errors="coerce")

    buy_breakout_distance = pd.to_numeric(out["close"], errors="coerce") - previous_high
    sell_breakout_distance = previous_low - pd.to_numeric(out["close"], errors="coerce")

    out["c_previous_range_high"] = previous_high
    out["c_previous_range_low"] = previous_low
    out["c_previous_range_width"] = previous_high - previous_low
    out["c_previous_range_width_atr"] = out["c_previous_range_width"] / atr
    out["c_buy_breakout_distance"] = buy_breakout_distance
    out["c_sell_breakout_distance"] = sell_breakout_distance
    out["c_buy_breakout_distance_atr"] = buy_breakout_distance / atr
    out["c_sell_breakout_distance_atr"] = sell_breakout_distance / atr
    out["c_macd_hist_delta"] = pd.to_numeric(out["macd_hist"], errors="coerce") - pd.to_numeric(out["macd_hist"], errors="coerce").shift(1)
    out["c_macd_hist_delta_abs"] = out["c_macd_hist_delta"].abs()

    buy = buy_breakout_distance.gt(0)
    sell = sell_breakout_distance.gt(0)

    if settings.min_breakout_atr > 0:
        buy = buy & out["c_buy_breakout_distance_atr"].ge(settings.min_breakout_atr)
        sell = sell & out["c_sell_breakout_distance_atr"].ge(settings.min_breakout_atr)
    if settings.max_breakout_atr is not None:
        buy = buy & out["c_buy_breakout_distance_atr"].le(settings.max_breakout_atr)
        sell = sell & out["c_sell_breakout_distance_atr"].le(settings.max_breakout_atr)

    if settings.require_h1_trend:
        buy = buy & out["h1_trend"].eq("BUY")
        sell = sell & out["h1_trend"].eq("SELL")

    if settings.require_m15_ema_alignment:
        buy = buy & pd.to_numeric(out["ema_20"], errors="coerce").gt(pd.to_numeric(out["ema_50"], errors="coerce"))
        sell = sell & pd.to_numeric(out["ema_20"], errors="coerce").lt(pd.to_numeric(out["ema_50"], errors="coerce"))

    if settings.require_close_beyond_ema20:
        buy = buy & pd.to_numeric(out["close"], errors="coerce").gt(pd.to_numeric(out["ema_20"], errors="coerce"))
        sell = sell & pd.to_numeric(out["close"], errors="coerce").lt(pd.to_numeric(out["ema_20"], errors="coerce"))

    if settings.require_macd_hist_direction:
        buy = buy & pd.to_numeric(out["macd_hist"], errors="coerce").gt(0)
        sell = sell & pd.to_numeric(out["macd_hist"], errors="coerce").lt(0)

    if settings.require_macd_hist_acceleration:
        buy = buy & out["c_macd_hist_delta"].gt(0)
        sell = sell & out["c_macd_hist_delta"].lt(0)

    if settings.avoid_ab_overlap:
        ab_buy = _bool_col(out, "hidden_bullish_divergence") | _bool_col(out, "buy_reacceleration_signal")
        ab_sell = _bool_col(out, "hidden_bearish_divergence") | _bool_col(out, "sell_reacceleration_signal")
        buy = buy & ~ab_buy
        sell = sell & ~ab_sell

    conflict = buy & sell
    out["c_buy_signal"] = buy & ~conflict
    out["c_sell_signal"] = sell & ~conflict
    out["c_signal_conflict"] = conflict
    out["c_signal"] = out["c_buy_signal"] | out["c_sell_signal"]
    out["c_signal_side"] = "NONE"
    out.loc[out["c_buy_signal"], "c_signal_side"] = "BUY"
    out.loc[out["c_sell_signal"], "c_signal_side"] = "SELL"
    return out


def breakout_continuation_summary(df: pd.DataFrame) -> dict[str, object]:
    required = ["c_buy_signal", "c_sell_signal", "c_signal_conflict"]
    _require_columns(df, required)
    rows = len(df)
    buy = int(df["c_buy_signal"].sum())
    sell = int(df["c_sell_signal"].sum())
    conflict = int(df["c_signal_conflict"].sum())
    return {
        "rows": int(rows),
        "c_buy_signals": buy,
        "c_sell_signals": sell,
        "c_total_signals": buy + sell,
        "c_conflicts_skipped": conflict,
        "c_buy_ratio": buy / rows if rows else 0.0,
        "c_sell_ratio": sell / rows if rows else 0.0,
    }
