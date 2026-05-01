from __future__ import annotations

import pandas as pd


DEFAULT_ATR_COLUMN = "atr_14"


def add_pullback_candidates(
    df: pd.DataFrame,
    ema_col: str = "ema_20",
    atr_col: str = DEFAULT_ATR_COLUMN,
    near_atr_multiplier: float = 0.30,
    close_tolerance_atr_multiplier: float = 0.50,
) -> pd.DataFrame:
    """Add M15 pullback/retracement candidate flags.

    This does not create trade signals yet.
    It only marks bars where price is near M15 EMA20 while H1 context agrees.

    BUY pullback candidate:
        - H1 is BUY environment
        - M15 low reaches near EMA20
        - M15 close is not too far below EMA20

    SELL retracement candidate:
        - H1 is SELL environment
        - M15 high reaches near EMA20
        - M15 close is not too far above EMA20

    Parameters:
        near_atr_multiplier:
            How close the wick must come to EMA20.
            Example: 0.30 means ATR14 * 0.30.

        close_tolerance_atr_multiplier:
            Allows the close to be slightly beyond EMA20.
            This avoids rejecting useful pullbacks because of small overshoots.
    """
    required = [
        "time",
        "high",
        "low",
        "close",
        ema_col,
        atr_col,
        "h1_buy_env",
        "h1_sell_env",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required pullback columns: {missing}")

    if near_atr_multiplier < 0:
        raise ValueError("near_atr_multiplier must be >= 0")
    if close_tolerance_atr_multiplier < 0:
        raise ValueError("close_tolerance_atr_multiplier must be >= 0")

    out = df.copy()

    near_band = out[atr_col] * near_atr_multiplier
    close_tolerance = out[atr_col] * close_tolerance_atr_multiplier

    out["ema20_near_upper"] = out[ema_col] + near_band
    out["ema20_near_lower"] = out[ema_col] - near_band
    out["ema20_close_upper"] = out[ema_col] + close_tolerance
    out["ema20_close_lower"] = out[ema_col] - close_tolerance

    out["buy_pullback_candidate"] = (
        out["h1_buy_env"].astype(bool)
        & out[ema_col].notna()
        & out[atr_col].notna()
        & (out["low"] <= out["ema20_near_upper"])
        & (out["close"] >= out["ema20_close_lower"])
    )

    out["sell_pullback_candidate"] = (
        out["h1_sell_env"].astype(bool)
        & out[ema_col].notna()
        & out[atr_col].notna()
        & (out["high"] >= out["ema20_near_lower"])
        & (out["close"] <= out["ema20_close_upper"])
    )

    out["pullback_side"] = "NONE"
    out.loc[out["buy_pullback_candidate"], "pullback_side"] = "BUY"
    out.loc[out["sell_pullback_candidate"], "pullback_side"] = "SELL"

    # In rare cases both can be true if H1 context is inconsistent, which should not happen
    # because H1 buy/sell env are mutually exclusive. Keep a diagnostic flag anyway.
    out["both_pullback_candidates"] = out["buy_pullback_candidate"] & out["sell_pullback_candidate"]

    return out


def pullback_summary(df: pd.DataFrame) -> dict[str, object]:
    required = ["buy_pullback_candidate", "sell_pullback_candidate", "both_pullback_candidates"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing pullback summary columns: {missing}")

    rows = len(df)
    buy_count = int(df["buy_pullback_candidate"].sum())
    sell_count = int(df["sell_pullback_candidate"].sum())
    both_count = int(df["both_pullback_candidates"].sum())

    return {
        "rows": rows,
        "buy_pullback_candidates": buy_count,
        "sell_pullback_candidates": sell_count,
        "both_pullback_candidates": both_count,
        "buy_ratio": buy_count / rows if rows else 0.0,
        "sell_ratio": sell_count / rows if rows else 0.0,
    }


def pullback_counts_by_h1_trend(df: pd.DataFrame) -> pd.DataFrame:
    required = ["h1_trend", "buy_pullback_candidate", "sell_pullback_candidate"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for pullback trend counts: {missing}")

    grouped = (
        df.groupby("h1_trend", dropna=False)
        .agg(
            rows=("time", "count"),
            buy_pullbacks=("buy_pullback_candidate", "sum"),
            sell_pullbacks=("sell_pullback_candidate", "sum"),
        )
        .reset_index()
    )
    return grouped
