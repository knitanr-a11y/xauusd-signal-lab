from __future__ import annotations

from typing import Iterable

import pandas as pd


TF_MINUTES: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}

DEFAULT_JOIN_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "ema8",
    "ema20",
    "ema50",
    "ema100",
    "ema200",
    "ema_align",
    "ema20_gt_ema50",
    "ema20_lt_ema50",
    "atr14",
    "macd_hist",
    "macd_delta",
    "macd_delta3",
    "close_change_3_atr",
    "close_change_6_atr",
    "close_ema8_gap_atr",
    "close_ema20_gap_atr",
    "close_ema50_gap_atr",
    "rsi14",
    "rsi14_delta",
    "stoch14",
    "stoch14_delta",
    "rci9",
    "rci9_delta",
    "rci26",
    "rci26_delta",
    "rci52",
    "rci52_delta",
]

H1_GOLD_JOIN_COLUMNS = ["time", "ema_align", "macd_hist", "macd_delta", "macd_delta3", "rsi14", "rci26", "rci52"]


def timeframe_minutes(tf: str) -> int:
    key = str(tf).upper()
    if key not in TF_MINUTES:
        raise ValueError(f"Unsupported timeframe for confirmed join: {tf}")
    return TF_MINUTES[key]


def add_close_time(df: pd.DataFrame, *, tf: str, output_col: str = "close_time") -> pd.DataFrame:
    out = df.copy()
    out[output_col] = pd.to_datetime(out["time"], errors="coerce") + pd.to_timedelta(timeframe_minutes(tf), unit="m")
    return out


def prefix_for_confirmed_join(
    df: pd.DataFrame,
    *,
    prefix: str,
    tf: str,
    columns: Iterable[str] = DEFAULT_JOIN_COLUMNS,
) -> pd.DataFrame:
    use_cols = [c for c in columns if c in df.columns]
    if "time" not in use_cols:
        use_cols = ["time", *use_cols]
    out = df[use_cols].copy()
    out[f"{prefix}_time"] = pd.to_datetime(out["time"], errors="coerce")
    out[f"{prefix}_close_time"] = out[f"{prefix}_time"] + pd.to_timedelta(timeframe_minutes(tf), unit="m")
    out = out.drop(columns=["time"])
    out = out.rename(columns={c: f"{prefix}_{c}" for c in out.columns if c not in {f"{prefix}_time", f"{prefix}_close_time"}})
    return out


def join_context_confirmed(
    base: pd.DataFrame,
    *,
    base_tf: str,
    contexts: list[tuple[pd.DataFrame, str, str]],
) -> pd.DataFrame:
    """Join higher timeframe features without live lookahead.

    CSV rows store candle open time. A row is only usable after its candle close time.
    For a base signal row, use contexts whose context_close_time <= base_close_time.

    Example:
    - M5 00:55 closes at 01:00
    - H1 00:00 closes at 01:00
    - M5 00:55 may use H1 00:00, but M5 00:50 may not.
    """
    out = base.copy().sort_values("time").reset_index(drop=True)
    out["_base_close_time_for_join"] = pd.to_datetime(out["time"], errors="coerce") + pd.to_timedelta(timeframe_minutes(base_tf), unit="m")

    for ctx, prefix, ctx_tf in contexts:
        ctx_pref = prefix_for_confirmed_join(ctx, prefix=prefix, tf=ctx_tf).sort_values(f"{prefix}_close_time")
        out = pd.merge_asof(
            out.sort_values("_base_close_time_for_join"),
            ctx_pref,
            left_on="_base_close_time_for_join",
            right_on=f"{prefix}_close_time",
            direction="backward",
        ).reset_index(drop=True)
        out = out.sort_values("time", kind="mergesort").reset_index(drop=True)

    return out.drop(columns=["_base_close_time_for_join"], errors="ignore")


def join_h1_confirmed_for_gold_m15(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    out = m15.copy().sort_values("time").reset_index(drop=True)
    out["_m15_close_time_for_join"] = pd.to_datetime(out["time"], errors="coerce") + pd.to_timedelta(15, unit="m")
    h1_feat = prefix_for_confirmed_join(h1, prefix="h1", tf="H1", columns=H1_GOLD_JOIN_COLUMNS).sort_values("h1_close_time")
    joined = pd.merge_asof(
        out.sort_values("_m15_close_time_for_join"),
        h1_feat,
        left_on="_m15_close_time_for_join",
        right_on="h1_close_time",
        direction="backward",
    ).reset_index(drop=True)
    joined = joined.sort_values("time", kind="mergesort").reset_index(drop=True)
    return joined.drop(columns=["_m15_close_time_for_join"], errors="ignore")


def join_h1_confirmed_for_btc_m15(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    out = m15.copy().sort_values("time").reset_index(drop=True)
    out["_m15_close_time_for_join"] = pd.to_datetime(out["time"], errors="coerce") + pd.to_timedelta(15, unit="m")
    h1_feat = prefix_for_confirmed_join(h1, prefix="h1", tf="H1", columns=H1_GOLD_JOIN_COLUMNS).sort_values("h1_close_time")
    joined = pd.merge_asof(
        out.sort_values("_m15_close_time_for_join"),
        h1_feat,
        left_on="_m15_close_time_for_join",
        right_on="h1_close_time",
        direction="backward",
    ).reset_index(drop=True)
    joined = joined.sort_values("time", kind="mergesort").reset_index(drop=True)
    return joined.drop(columns=["_m15_close_time_for_join"], errors="ignore")
