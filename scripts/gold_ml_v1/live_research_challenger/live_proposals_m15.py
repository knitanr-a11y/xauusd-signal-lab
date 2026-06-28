from __future__ import annotations

import numpy as np
import pandas as pd

from live_data import (
    POINT,
    atr_simple,
    atr_wilder,
    rci_rank_difference,
    rsi_wilder,
    trailing_percentile_current,
)


def acore_proposals(bars: dict[str, pd.DataFrame], after: pd.Timestamp) -> pd.DataFrame:
    m15 = bars["M15"].copy()
    h4 = bars["H4"].copy()

    m15["atr_for_trade"] = atr_simple(m15, 14)
    h4["atr_state"] = atr_simple(h4, 14)
    h4["atr_slope"] = atr_wilder(h4, 14)
    h4["rci18"] = rci_rank_difference(h4["close"], 18)
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    candle_range = (h4["high"] - h4["low"]).replace(0, np.nan)
    h4["upper_wick_frac"] = (
        h4["high"] - h4[["open", "close"]].max(axis=1)
    ) / candle_range
    h4["ema40_slope6_atr"] = (
        h4["ema40"] - h4["ema40"].shift(6)
    ) / h4["atr_slope"]
    h4["spread_atr"] = h4["spread"] * POINT / h4["atr_state"]

    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[
            [
                "bar_close_time",
                "rci18",
                "spread_atr",
                "upper_wick_frac",
                "ema40_slope6_atr",
            ]
        ]
        .dropna()
        .sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )

    state = (joined["rci18"] >= 73.993808) & (joined["spread_atr"] <= 0.012772)
    m1_times = set(pd.DatetimeIndex(bars["M1"]["bar_open_time"]))
    active = state & joined["bar_close_time"].isin(m1_times)
    joined["event"] = active & ~active.shift(fill_value=False)

    p7_keep = ~(
        (joined["upper_wick_frac"] >= 0.27488556398168634)
        & (joined["ema40_slope6_atr"] >= 0.6863028800058267)
    )
    watch_a = (
        (joined["upper_wick_frac"] <= 0.1677737608541299)
        & (joined["ema40_slope6_atr"] <= 0.5056518291622855)
    )
    watch_b = (
        (joined["upper_wick_frac"] <= 0.06526044468913629)
        & (joined["ema40_slope6_atr"] >= 0.8700779249713114)
    )
    joined["emit_candidate"] = p7_keep & ~(watch_a | watch_b)
    joined["candidate_id"] = "GML1-WATCH-022-C"
    joined["comp"] = "A_CORE"
    joined["source_timeframe"] = "M15"
    joined["higher_timeframe"] = "H4"
    joined["features_json"] = joined.apply(
        lambda row: {
            "upper_wick_frac": row.upper_wick_frac,
            "ema40_slope6_atr": row.ema40_slope6_atr,
            "rci18": row.rci18,
            "spread_atr": row.spread_atr,
        },
        axis=1,
    )
    columns = [
        "bar_close_time",
        "atr_for_trade",
        "emit_candidate",
        "candidate_id",
        "comp",
        "source_timeframe",
        "higher_timeframe",
        "features_json",
    ]
    return joined[joined["event"] & (joined["bar_close_time"] > after)][columns].copy()


def p18_proposals(bars: dict[str, pd.DataFrame], after: pd.Timestamp) -> pd.DataFrame:
    m15 = bars["M15"].copy()
    h4 = bars["H4"].copy()

    m15["atr_for_trade"] = atr_simple(m15, 14)
    mean = m15["close"].rolling(40, min_periods=40).mean()
    standard_deviation = m15["close"].rolling(40, min_periods=40).std(ddof=0)
    m15["bb40_upper"] = mean + 2 * standard_deviation
    m15["width"] = 4 * standard_deviation / m15["atr_for_trade"]
    m15["width_pct100"] = m15["width"].rolling(100, min_periods=100).apply(
        trailing_percentile_current,
        raw=True,
    )
    m15["squeeze12"] = m15["width_pct100"].shift(1).rolling(12, min_periods=12).min()
    m15["event"] = (
        (m15["close"].shift(1) <= m15["bb40_upper"].shift(1))
        & (m15["close"] > m15["bb40_upper"])
        & (m15["width"] > m15["width"].shift(1))
        & (m15["squeeze12"] <= 0.30)
    )

    h4["atr14"] = atr_wilder(h4, 14)
    h4["atr_ratio"] = h4["atr14"] / h4["atr14"].rolling(50, min_periods=50).median()
    h4["ema40"] = h4["close"].ewm(span=40, adjust=False, min_periods=40).mean()
    h4["slope6"] = (h4["ema40"] - h4["ema40"].shift(6)) / h4["atr14"]

    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[["bar_close_time", "atr_ratio", "slope6"]]
        .dropna()
        .sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["emit_candidate"] = True
    joined["candidate_id"] = "GML1-PROV-018-APPROX"
    joined["comp"] = "P18"
    joined["source_timeframe"] = "M15"
    joined["higher_timeframe"] = "H4"
    joined["features_json"] = joined.apply(
        lambda row: {
            "width": row.width,
            "width_pct100": row.width_pct100,
            "squeeze12": row.squeeze12,
            "atr_ratio": row.atr_ratio,
            "slope6": row.slope6,
        },
        axis=1,
    )
    columns = [
        "bar_close_time",
        "atr_for_trade",
        "emit_candidate",
        "candidate_id",
        "comp",
        "source_timeframe",
        "higher_timeframe",
        "features_json",
    ]
    mask = (
        joined["event"]
        & (joined["atr_ratio"] >= 1)
        & (joined["slope6"] > 0)
        & (joined["bar_close_time"] > after)
    )
    return joined[mask][columns].copy()


def w024_proposals(bars: dict[str, pd.DataFrame], after: pd.Timestamp) -> pd.DataFrame:
    m15 = bars["M15"].copy()
    h4 = bars["H4"].copy()

    m15["atr_for_trade"] = atr_wilder(m15, 14)
    m15["rsi_centered"] = (rsi_wilder(m15["close"], 14) - 50) / 50
    m15["range_atr"] = (m15["high"] - m15["low"]) / m15["atr_for_trade"]
    m15["upper_wick"] = (
        m15["high"] - m15[["open", "close"]].max(axis=1)
    ) / (m15["high"] - m15["low"]).replace(0, np.nan)
    m15["atr_percentile"] = (
        m15["atr_for_trade"].shift(1).rolling(256, min_periods=256).rank(pct=True)
    )
    ema200 = m15["close"].ewm(span=200, adjust=False, min_periods=200).mean()
    m15["ema200_slope12_atr14"] = (
        ema200 - ema200.shift(12)
    ) / m15["atr_for_trade"]

    state = (
        (m15["atr_percentile"] >= 0.75)
        & (m15["rsi_centered"] >= 0.35)
        & (m15["range_atr"] >= 1)
        & (m15["upper_wick"] >= 0.4)
    )
    previous_state = state.shift(1).astype("boolean").fillna(False).astype(bool)
    previous_time = m15["bar_close_time"].shift(1)
    m15["event"] = state & (
        ~previous_state
        | ((m15["bar_close_time"] - previous_time) != pd.Timedelta(minutes=15))
    )

    h4["h4_body_fraction"] = (
        h4["close"] - h4["open"]
    ).abs() / (h4["high"] - h4["low"]).replace(0, np.nan)
    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[["bar_close_time", "h4_body_fraction"]]
        .dropna()
        .sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["emit_candidate"] = True
    joined["candidate_id"] = "GML1-WATCH-024-A"
    joined["comp"] = "W024A"
    joined["source_timeframe"] = "M15"
    joined["higher_timeframe"] = "H4"
    joined["features_json"] = joined.apply(
        lambda row: {
            "atr_percentile": row.atr_percentile,
            "rsi_centered": row.rsi_centered,
            "range_atr": row.range_atr,
            "upper_wick": row.upper_wick,
            "ema200_slope12_atr14": row.ema200_slope12_atr14,
            "h4_body_fraction": row.h4_body_fraction,
        },
        axis=1,
    )
    columns = [
        "bar_close_time",
        "atr_for_trade",
        "emit_candidate",
        "candidate_id",
        "comp",
        "source_timeframe",
        "higher_timeframe",
        "features_json",
    ]
    mask = (
        joined["event"]
        & (joined["bar_close_time"] >= pd.Timestamp("2023-05-31"))
        & (joined["h4_body_fraction"] >= 0.7290171082088)
        & (joined["ema200_slope12_atr14"] >= 0.36208201390899997)
        & (joined["bar_close_time"] > after)
    )
    return joined[mask][columns].copy()
