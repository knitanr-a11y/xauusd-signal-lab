from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from live_data import atr_wilder, rci_rank_difference


def bstate_joined(bars: dict[str, pd.DataFrame]) -> pd.DataFrame:
    h1 = bars["H1"].copy()
    d1 = bars["D1"].copy()

    h1["atr_for_trade"] = atr_wilder(h1, 14)
    mean = h1["close"].rolling(60, min_periods=60).mean()
    standard_deviation = h1["close"].rolling(60, min_periods=60).std(ddof=0)
    h1["bb60_upper"] = mean + 2 * standard_deviation

    d1["atr14"] = atr_wilder(d1, 14)
    d1["rci18"] = rci_rank_difference(d1["close"], 18)
    d1["tickvol_ratio50"] = d1["tick_volume"] / d1["tick_volume"].rolling(
        50,
        min_periods=50,
    ).median()
    d1["delta_atr_3"] = (d1["close"] - d1["close"].shift(3)) / d1["atr14"]

    joined = pd.merge_asof(
        h1.sort_values("bar_close_time"),
        d1[["bar_close_time", "rci18", "tickvol_ratio50", "delta_atr_3"]]
        .dropna()
        .sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["base_breakout"] = (
        (joined["close"].shift(1) <= joined["bb60_upper"].shift(1))
        & (joined["close"] > joined["bb60_upper"])
        & (joined["rci18"] >= 0)
    )
    joined["p15_keep"] = ~(
        (joined["tickvol_ratio50"] <= 0.876789995391398)
        & (joined["delta_atr_3"] <= 0.2256991669382677)
    )
    joined["range_atr"] = (
        joined["high"] - joined["low"]
    ) / joined["atr_for_trade"]
    joined["close_pos"] = (
        joined["close"] - joined["low"]
    ) / (joined["high"] - joined["low"]).replace(0, np.nan)
    joined["range_atr_lag1"] = joined["range_atr"].shift(1)
    joined["close_pos_lag5"] = joined["close_pos"].shift(5)
    joined["range_atr_lag10"] = joined["range_atr"].shift(10)
    joined["span_atr_12"] = (
        joined["high"].rolling(12).max() - joined["low"].rolling(12).min()
    ) / joined["atr_for_trade"]
    joined["keep_a"] = ~(
        (joined["range_atr_lag1"] <= 0.6571970935503249)
        & (joined["span_atr_12"] >= 5.058013327710588)
    )
    joined["keep_b"] = ~(
        (joined["close_pos_lag5"] <= 0.424089068826)
        & (joined["range_atr_lag10"] >= 1.17215632583)
    )
    joined["all_keep"] = joined["p15_keep"] & joined["keep_a"] & joined["keep_b"]
    joined["above"] = joined["close"] > joined["bb60_upper"]
    joined["cross_any"] = joined["above"] & ~joined["above"].shift(fill_value=False)
    joined["entry_ok"] = (
        joined["above"]
        & (joined["rci18"] >= 0)
        & joined["all_keep"]
    )
    return joined


def bstate_proposals(
    bars: dict[str, pd.DataFrame],
    after: pd.Timestamp,
    until: pd.Timestamp,
    pending_due: pd.Timestamp | None,
    pending_origin: pd.Timestamp | None,
) -> tuple[pd.DataFrame, pd.Timestamp | None, pd.Timestamp | None]:
    joined = bstate_joined(bars)
    rows: list[dict[str, Any]] = []
    new_rows = joined[
        (joined["bar_close_time"] > after)
        & (joined["bar_close_time"] <= until)
    ]

    for row in new_rows.itertuples(index=False):
        timestamp = pd.Timestamp(row.bar_close_time)
        due_event = False
        due_origin = pending_origin

        if pending_due is not None and timestamp >= pending_due:
            if bool(row.entry_ok):
                due_event = True
            pending_due = None
            pending_origin = None

        base_event = bool(row.base_breakout and row.all_keep)
        if base_event or due_event:
            event_kind = "BASE" if base_event else "REENTRY24"
            rows.append(
                {
                    "bar_close_time": timestamp,
                    "atr_for_trade": row.atr_for_trade,
                    "emit_candidate": True,
                    "candidate_id": "GML1-H1D1-STATEFUL-REENTRY24-C",
                    "comp": "B_STATE",
                    "source_timeframe": "H1",
                    "higher_timeframe": "D1",
                    "features_json": {
                        "event_kind": event_kind,
                        "origin_breakout_time": timestamp if base_event else due_origin,
                        "rci18": row.rci18,
                        "tickvol_ratio50": row.tickvol_ratio50,
                        "delta_atr_3": row.delta_atr_3,
                        "range_atr_lag1": row.range_atr_lag1,
                        "span_atr_12": row.span_atr_12,
                        "close_pos_lag5": row.close_pos_lag5,
                        "range_atr_lag10": row.range_atr_lag10,
                    },
                }
            )

        if bool(row.cross_any) and pending_due is None:
            pending_origin = timestamp
            pending_due = timestamp + pd.Timedelta(hours=24)

    return pd.DataFrame(rows), pending_due, pending_origin
