from __future__ import annotations

import pandas as pd


def add_hidden_divergence_flags(
    df: pd.DataFrame,
    macd_col: str = "macd_line",
) -> pd.DataFrame:
    """Add simplified hidden divergence flags.

    This is the first implementation for signal narrowing.

    BUY hidden divergence:
        - BUY pullback candidate
        - previous confirmed swing low exists
        - current bar low is higher than previous confirmed swing low
        - current bar MACD is lower than MACD at previous confirmed swing low

    SELL hidden divergence:
        - SELL pullback candidate
        - previous confirmed swing high exists
        - current bar high is lower than previous confirmed swing high
        - current bar MACD is higher than MACD at previous confirmed swing high

    Important:
        This first version compares the current candidate bar directly.
        Later, it can be upgraded to group consecutive pullback bars and use
        the lowest low / highest high inside the pullback segment.
    """
    required = [
        "time",
        "high",
        "low",
        macd_col,
        "buy_pullback_candidate",
        "sell_pullback_candidate",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_low_macd",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_high_macd",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required divergence columns: {missing}")

    out = df.copy()

    out["hidden_bullish_divergence"] = (
        out["buy_pullback_candidate"].astype(bool)
        & out["last_confirmed_swing_low_price"].notna()
        & out["last_confirmed_swing_low_macd"].notna()
        & out[macd_col].notna()
        & (out["low"] > out["last_confirmed_swing_low_price"])
        & (out[macd_col] < out["last_confirmed_swing_low_macd"])
    )

    out["hidden_bearish_divergence"] = (
        out["sell_pullback_candidate"].astype(bool)
        & out["last_confirmed_swing_high_price"].notna()
        & out["last_confirmed_swing_high_macd"].notna()
        & out[macd_col].notna()
        & (out["high"] < out["last_confirmed_swing_high_price"])
        & (out[macd_col] > out["last_confirmed_swing_high_macd"])
    )

    out["hidden_divergence_side"] = "NONE"
    out.loc[out["hidden_bullish_divergence"], "hidden_divergence_side"] = "BUY"
    out.loc[out["hidden_bearish_divergence"], "hidden_divergence_side"] = "SELL"

    out["both_hidden_divergences"] = out["hidden_bullish_divergence"] & out["hidden_bearish_divergence"]

    # Diagnostic distances. Positive values support the corresponding hidden divergence.
    out["bullish_hidden_price_delta"] = out["low"] - out["last_confirmed_swing_low_price"]
    out["bullish_hidden_macd_delta"] = out["last_confirmed_swing_low_macd"] - out[macd_col]

    out["bearish_hidden_price_delta"] = out["last_confirmed_swing_high_price"] - out["high"]
    out["bearish_hidden_macd_delta"] = out[macd_col] - out["last_confirmed_swing_high_macd"]

    return out


def hidden_divergence_summary(df: pd.DataFrame) -> dict[str, object]:
    required = ["hidden_bullish_divergence", "hidden_bearish_divergence", "both_hidden_divergences"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing hidden divergence summary columns: {missing}")

    rows = len(df)
    bullish = int(df["hidden_bullish_divergence"].sum())
    bearish = int(df["hidden_bearish_divergence"].sum())
    both = int(df["both_hidden_divergences"].sum())

    return {
        "rows": rows,
        "hidden_bullish_divergence": bullish,
        "hidden_bearish_divergence": bearish,
        "both_hidden_divergences": both,
        "bullish_ratio": bullish / rows if rows else 0.0,
        "bearish_ratio": bearish / rows if rows else 0.0,
    }


def hidden_divergence_counts_by_h1_trend(df: pd.DataFrame) -> pd.DataFrame:
    required = ["h1_trend", "hidden_bullish_divergence", "hidden_bearish_divergence"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for hidden divergence trend counts: {missing}")

    return (
        df.groupby("h1_trend", dropna=False)
        .agg(
            rows=("time", "count"),
            hidden_bullish=("hidden_bullish_divergence", "sum"),
            hidden_bearish=("hidden_bearish_divergence", "sum"),
        )
        .reset_index()
    )
