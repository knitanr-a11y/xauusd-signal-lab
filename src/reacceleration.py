from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ReaccelerationSettings:
    recent_pullback_bars: int = 6
    require_macd_signal_alignment: bool = True
    require_histogram_acceleration: bool = True
    require_ema20_reclaim: bool = True

    def validate(self) -> None:
        if self.recent_pullback_bars <= 0:
            raise ValueError(f"recent_pullback_bars must be positive: {self.recent_pullback_bars}")


def add_reacceleration_signals(
    df: pd.DataFrame,
    settings: ReaccelerationSettings | None = None,
) -> pd.DataFrame:
    """Add EMA20 reclaim + MACD reacceleration signals.

    This is the B-signal candidate.

    BUY reacceleration:
        - H1 BUY environment
        - a BUY pullback candidate existed within recent N bars
        - close is above EMA20
        - previous close was at/below EMA20 if require_ema20_reclaim=True
        - MACD line is above MACD signal if require_macd_signal_alignment=True
        - MACD histogram is increasing if require_histogram_acceleration=True

    SELL reacceleration:
        - H1 SELL environment
        - a SELL pullback candidate existed within recent N bars
        - close is below EMA20
        - previous close was at/above EMA20 if require_ema20_reclaim=True
        - MACD line is below MACD signal if require_macd_signal_alignment=True
        - MACD histogram is decreasing if require_histogram_acceleration=True

    This signal intentionally uses existing project ingredients only:
        H1 context, EMA20, MACD, histogram, pullback candidates.
    """
    settings = settings or ReaccelerationSettings()
    settings.validate()

    required = [
        "time",
        "close",
        "ema_20",
        "macd_line",
        "macd_signal",
        "macd_histogram",
        "h1_buy_env",
        "h1_sell_env",
        "buy_pullback_candidate",
        "sell_pullback_candidate",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required reacceleration columns: {missing}")

    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    recent_window = settings.recent_pullback_bars
    out["recent_buy_pullback"] = (
        out["buy_pullback_candidate"].astype(bool).rolling(recent_window, min_periods=1).max().astype(bool)
    )
    out["recent_sell_pullback"] = (
        out["sell_pullback_candidate"].astype(bool).rolling(recent_window, min_periods=1).max().astype(bool)
    )

    prev_close = out["close"].shift(1)
    prev_ema20 = out["ema_20"].shift(1)
    prev_hist = out["macd_histogram"].shift(1)

    buy_reclaim = out["close"] > out["ema_20"]
    sell_reclaim = out["close"] < out["ema_20"]

    if settings.require_ema20_reclaim:
        buy_reclaim = buy_reclaim & (prev_close <= prev_ema20)
        sell_reclaim = sell_reclaim & (prev_close >= prev_ema20)

    buy_macd_alignment = pd.Series(True, index=out.index)
    sell_macd_alignment = pd.Series(True, index=out.index)
    if settings.require_macd_signal_alignment:
        buy_macd_alignment = out["macd_line"] > out["macd_signal"]
        sell_macd_alignment = out["macd_line"] < out["macd_signal"]

    buy_hist_accel = pd.Series(True, index=out.index)
    sell_hist_accel = pd.Series(True, index=out.index)
    if settings.require_histogram_acceleration:
        buy_hist_accel = out["macd_histogram"] > prev_hist
        sell_hist_accel = out["macd_histogram"] < prev_hist

    out["buy_reacceleration_signal"] = (
        out["h1_buy_env"].astype(bool)
        & out["recent_buy_pullback"].astype(bool)
        & buy_reclaim
        & buy_macd_alignment
        & buy_hist_accel
        & out["ema_20"].notna()
        & out["macd_line"].notna()
        & out["macd_signal"].notna()
        & out["macd_histogram"].notna()
    )

    out["sell_reacceleration_signal"] = (
        out["h1_sell_env"].astype(bool)
        & out["recent_sell_pullback"].astype(bool)
        & sell_reclaim
        & sell_macd_alignment
        & sell_hist_accel
        & out["ema_20"].notna()
        & out["macd_line"].notna()
        & out["macd_signal"].notna()
        & out["macd_histogram"].notna()
    )

    out["reacceleration_side"] = "NONE"
    out.loc[out["buy_reacceleration_signal"], "reacceleration_side"] = "BUY"
    out.loc[out["sell_reacceleration_signal"], "reacceleration_side"] = "SELL"
    out["both_reacceleration_signals"] = out["buy_reacceleration_signal"] & out["sell_reacceleration_signal"]

    # Diagnostics useful for later filters.
    out["macd_histogram_delta"] = out["macd_histogram"] - prev_hist
    out["close_ema20_delta"] = out["close"] - out["ema_20"]

    if "hidden_bullish_divergence" in out.columns:
        out["reaccel_overlap_hidden_bullish"] = out["buy_reacceleration_signal"] & out["hidden_bullish_divergence"].astype(bool)
    else:
        out["reaccel_overlap_hidden_bullish"] = False

    if "hidden_bearish_divergence" in out.columns:
        out["reaccel_overlap_hidden_bearish"] = out["sell_reacceleration_signal"] & out["hidden_bearish_divergence"].astype(bool)
    else:
        out["reaccel_overlap_hidden_bearish"] = False

    return out


def reacceleration_summary(df: pd.DataFrame) -> dict[str, object]:
    required = [
        "buy_reacceleration_signal",
        "sell_reacceleration_signal",
        "both_reacceleration_signals",
        "reaccel_overlap_hidden_bullish",
        "reaccel_overlap_hidden_bearish",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required reacceleration summary columns: {missing}")

    rows = len(df)
    buy = int(df["buy_reacceleration_signal"].sum())
    sell = int(df["sell_reacceleration_signal"].sum())
    both = int(df["both_reacceleration_signals"].sum())
    overlap_buy = int(df["reaccel_overlap_hidden_bullish"].sum())
    overlap_sell = int(df["reaccel_overlap_hidden_bearish"].sum())

    return {
        "rows": rows,
        "buy_reacceleration_signals": buy,
        "sell_reacceleration_signals": sell,
        "both_reacceleration_signals": both,
        "buy_reaccel_ratio": buy / rows if rows else 0.0,
        "sell_reaccel_ratio": sell / rows if rows else 0.0,
        "overlap_hidden_bullish": overlap_buy,
        "overlap_hidden_bearish": overlap_sell,
        "buy_overlap_ratio": overlap_buy / buy if buy else 0.0,
        "sell_overlap_ratio": overlap_sell / sell if sell else 0.0,
    }


def reacceleration_counts_by_jst_hour(df: pd.DataFrame) -> pd.DataFrame:
    required = ["jst_hour", "buy_reacceleration_signal", "sell_reacceleration_signal"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for reacceleration JST hour counts: {missing}")

    return (
        df.groupby("jst_hour", dropna=False)
        .agg(
            rows=("time", "count"),
            buy_reaccel=("buy_reacceleration_signal", "sum"),
            sell_reaccel=("sell_reacceleration_signal", "sum"),
        )
        .reset_index()
        .sort_values("jst_hour")
    )
