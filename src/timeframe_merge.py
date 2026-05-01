from __future__ import annotations

import pandas as pd


H1_CONTEXT_COLUMNS = [
    "time",
    "h1_time",
    "h1_close",
    "h1_ema_20",
    "h1_ema_50",
    "h1_trend",
    "h1_buy_env",
    "h1_sell_env",
]


def add_h1_environment(h1_df: pd.DataFrame) -> pd.DataFrame:
    """Add H1 trend/environment columns.

    BUY environment:
        h1 ema20 > h1 ema50 and h1 close > h1 ema20

    SELL environment:
        h1 ema20 < h1 ema50 and h1 close < h1 ema20

    Other cases are treated as NONE.
    """
    required = ["time", "close", "ema_20", "ema_50"]
    missing = [col for col in required if col not in h1_df.columns]
    if missing:
        raise ValueError(f"Missing required H1 columns: {missing}")

    out = h1_df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    out["h1_time"] = out["time"]
    out["h1_close"] = out["close"]
    out["h1_ema_20"] = out["ema_20"]
    out["h1_ema_50"] = out["ema_50"]

    buy_env = (out["h1_ema_20"] > out["h1_ema_50"]) & (out["h1_close"] > out["h1_ema_20"])
    sell_env = (out["h1_ema_20"] < out["h1_ema_50"]) & (out["h1_close"] < out["h1_ema_20"])

    out["h1_buy_env"] = buy_env.fillna(False)
    out["h1_sell_env"] = sell_env.fillna(False)
    out["h1_trend"] = "NONE"
    out.loc[out["h1_buy_env"], "h1_trend"] = "BUY"
    out.loc[out["h1_sell_env"], "h1_trend"] = "SELL"

    return out


def prepare_h1_context_for_m15(h1_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare H1 context so it can be safely merged into M15.

    Important:
        A H1 candle starting at 07:00 is only confirmed at 08:00.
        Therefore its information becomes usable from 08:00 onward.

    The output contains `time` as the usability time, not the original H1 candle open time.
    The original H1 candle open time is kept as `h1_time`.
    """
    env = add_h1_environment(h1_df)

    context = env[[
        "h1_time",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "h1_buy_env",
        "h1_sell_env",
    ]].copy()

    # H1 candle data is usable only after that H1 candle has closed.
    context["time"] = env["h1_time"] + pd.Timedelta(hours=1)

    context = context[[
        "time",
        "h1_time",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "h1_buy_env",
        "h1_sell_env",
    ]]

    return context.sort_values("time", kind="mergesort").reset_index(drop=True)


def merge_confirmed_h1_context(m15_df: pd.DataFrame, h1_df: pd.DataFrame) -> pd.DataFrame:
    """Merge confirmed H1 context into M15 rows without look-ahead.

    Uses pandas.merge_asof with direction='backward'.

    For example:
        M15 07:15 receives H1 candle that became usable at or before 07:15.
        The H1 candle starting 07:00 becomes usable only at 08:00, so 07:15 will not use it.
    """
    if "time" not in m15_df.columns:
        raise ValueError("m15_df must contain a time column")
    if "time" not in h1_df.columns:
        raise ValueError("h1_df must contain a time column")

    m15 = m15_df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    context = prepare_h1_context_for_m15(h1_df)

    merged = pd.merge_asof(
        m15,
        context,
        on="time",
        direction="backward",
        allow_exact_matches=True,
    )

    # Before enough H1 data exists, these will be NaN. Treat environment as False/NONE.
    merged["h1_buy_env"] = merged["h1_buy_env"].fillna(False).astype(bool)
    merged["h1_sell_env"] = merged["h1_sell_env"].fillna(False).astype(bool)
    merged["h1_trend"] = merged["h1_trend"].fillna("NONE")

    return merged


def h1_context_summary(merged_df: pd.DataFrame) -> dict[str, object]:
    """Build a compact summary for merged M15/H1 context."""
    required = ["h1_time", "h1_trend", "h1_buy_env", "h1_sell_env"]
    missing = [col for col in required if col not in merged_df.columns]
    if missing:
        raise ValueError(f"Missing merged H1 context columns: {missing}")

    rows = len(merged_df)
    missing_h1_time = int(merged_df["h1_time"].isna().sum())
    trend_counts = merged_df["h1_trend"].value_counts(dropna=False).to_dict()

    # Look-ahead safety check:
    # h1_time + 1h must be <= M15 time whenever h1_time exists.
    usable_time = merged_df["h1_time"] + pd.Timedelta(hours=1)
    lookahead_mask = merged_df["h1_time"].notna() & (usable_time > merged_df["time"])
    lookahead_violations = int(lookahead_mask.sum())

    return {
        "rows": rows,
        "missing_h1_time": missing_h1_time,
        "trend_counts": trend_counts,
        "lookahead_violations": lookahead_violations,
    }
