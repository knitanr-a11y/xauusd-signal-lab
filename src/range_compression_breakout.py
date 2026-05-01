from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RangeCompressionBreakoutSettings:
    """Settings for C2 range-compression breakout candidates.

    C1 was a trend-continuation breakout and worked best on BUY.
    C2 is designed as a different vector:
        - wait for a compressed recent M15 range
        - enter only when price breaks out of that range by close
        - use H1 direction and M15 EMA/MACD confirmation

    The first research target is SELL, because plain C1 SELL behaved poorly and
    likely needs a pre-breakout compression / accumulation condition.
    """

    range_lookback_bars: int = 12
    max_range_width_atr: float = 2.50
    min_breakout_atr: float = 0.00
    max_breakout_atr: float | None = None
    require_h1_trend: bool = True
    require_m15_ema_alignment: bool = True
    require_close_beyond_ema20: bool = True
    require_macd_hist_direction: bool = True
    require_macd_hist_acceleration: bool = True
    avoid_ab_overlap: bool = True

    def validate(self) -> None:
        if self.range_lookback_bars <= 1:
            raise ValueError(f"range_lookback_bars must be > 1: {self.range_lookback_bars}")
        if self.max_range_width_atr <= 0:
            raise ValueError(f"max_range_width_atr must be > 0: {self.max_range_width_atr}")
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
        raise ValueError(f"Missing required range-compression breakout columns: {missing}")


def add_range_compression_breakout_signals(
    df: pd.DataFrame,
    settings: RangeCompressionBreakoutSettings | None = None,
) -> pd.DataFrame:
    """Add C2 range-compression breakout signal columns.

    BUY concept:
        previous N-bar range is narrow relative to ATR, then close breaks above
        previous range high while H1/M15/MACD point up.

    SELL concept:
        previous N-bar range is narrow relative to ATR, then close breaks below
        previous range low while H1/M15/MACD point down.

    Signal is confirmed on the M15 close. The existing backtest engine enters on
    the next M15 open, same as A/B/C1.
    """
    settings = settings or RangeCompressionBreakoutSettings()
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
    lookback = settings.range_lookback_bars

    previous_high = out["high"].shift(1).rolling(lookback, min_periods=lookback).max()
    previous_low = out["low"].shift(1).rolling(lookback, min_periods=lookback).min()
    atr = pd.to_numeric(out["atr_14"], errors="coerce")
    close = pd.to_numeric(out["close"], errors="coerce")

    range_width = previous_high - previous_low
    range_width_atr = range_width / atr
    compressed = range_width_atr.le(settings.max_range_width_atr)

    buy_breakout_distance = close - previous_high
    sell_breakout_distance = previous_low - close

    out["c2_previous_range_high"] = previous_high
    out["c2_previous_range_low"] = previous_low
    out["c2_previous_range_width"] = range_width
    out["c2_previous_range_width_atr"] = range_width_atr
    out["c2_range_compressed"] = compressed.fillna(False)
    out["c2_buy_breakout_distance"] = buy_breakout_distance
    out["c2_sell_breakout_distance"] = sell_breakout_distance
    out["c2_buy_breakout_distance_atr"] = buy_breakout_distance / atr
    out["c2_sell_breakout_distance_atr"] = sell_breakout_distance / atr
    out["c2_macd_hist_delta"] = pd.to_numeric(out["macd_hist"], errors="coerce") - pd.to_numeric(out["macd_hist"], errors="coerce").shift(1)
    out["c2_macd_hist_delta_abs"] = out["c2_macd_hist_delta"].abs()

    buy = compressed & buy_breakout_distance.gt(0)
    sell = compressed & sell_breakout_distance.gt(0)

    if settings.min_breakout_atr > 0:
        buy = buy & out["c2_buy_breakout_distance_atr"].ge(settings.min_breakout_atr)
        sell = sell & out["c2_sell_breakout_distance_atr"].ge(settings.min_breakout_atr)
    if settings.max_breakout_atr is not None:
        buy = buy & out["c2_buy_breakout_distance_atr"].le(settings.max_breakout_atr)
        sell = sell & out["c2_sell_breakout_distance_atr"].le(settings.max_breakout_atr)

    if settings.require_h1_trend:
        buy = buy & out["h1_trend"].eq("BUY")
        sell = sell & out["h1_trend"].eq("SELL")

    if settings.require_m15_ema_alignment:
        buy = buy & pd.to_numeric(out["ema_20"], errors="coerce").gt(pd.to_numeric(out["ema_50"], errors="coerce"))
        sell = sell & pd.to_numeric(out["ema_20"], errors="coerce").lt(pd.to_numeric(out["ema_50"], errors="coerce"))

    if settings.require_close_beyond_ema20:
        buy = buy & close.gt(pd.to_numeric(out["ema_20"], errors="coerce"))
        sell = sell & close.lt(pd.to_numeric(out["ema_20"], errors="coerce"))

    if settings.require_macd_hist_direction:
        buy = buy & pd.to_numeric(out["macd_hist"], errors="coerce").gt(0)
        sell = sell & pd.to_numeric(out["macd_hist"], errors="coerce").lt(0)

    if settings.require_macd_hist_acceleration:
        buy = buy & out["c2_macd_hist_delta"].gt(0)
        sell = sell & out["c2_macd_hist_delta"].lt(0)

    if settings.avoid_ab_overlap:
        ab_buy = _bool_col(out, "hidden_bullish_divergence") | _bool_col(out, "buy_reacceleration_signal")
        ab_sell = _bool_col(out, "hidden_bearish_divergence") | _bool_col(out, "sell_reacceleration_signal")
        buy = buy & ~ab_buy
        sell = sell & ~ab_sell

    conflict = buy & sell
    out["c2_buy_signal"] = buy & ~conflict
    out["c2_sell_signal"] = sell & ~conflict
    out["c2_signal_conflict"] = conflict
    out["c2_signal"] = out["c2_buy_signal"] | out["c2_sell_signal"]
    out["c2_signal_side"] = "NONE"
    out.loc[out["c2_buy_signal"], "c2_signal_side"] = "BUY"
    out.loc[out["c2_sell_signal"], "c2_signal_side"] = "SELL"
    return out


def range_compression_breakout_summary(df: pd.DataFrame) -> dict[str, object]:
    required = ["c2_buy_signal", "c2_sell_signal", "c2_signal_conflict", "c2_range_compressed"]
    _require_columns(df, required)
    rows = len(df)
    buy = int(df["c2_buy_signal"].sum())
    sell = int(df["c2_sell_signal"].sum())
    conflict = int(df["c2_signal_conflict"].sum())
    compressed = int(df["c2_range_compressed"].sum())
    return {
        "rows": int(rows),
        "compressed_rows": compressed,
        "compressed_ratio": compressed / rows if rows else 0.0,
        "c2_buy_signals": buy,
        "c2_sell_signals": sell,
        "c2_total_signals": buy + sell,
        "c2_conflicts_skipped": conflict,
        "c2_buy_ratio": buy / rows if rows else 0.0,
        "c2_sell_ratio": sell / rows if rows else 0.0,
    }
