from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fast_m1_engine_hotfix import evaluate_fast_m1_no_infinity

path = Path(__file__).with_name("nine_candidate_local_replay_v4.py")
spec = importlib.util.spec_from_file_location("batch023_v4_for_v5", path)
if spec is None or spec.loader is None:
    raise RuntimeError(path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.FastM1Engine.evaluate = evaluate_fast_m1_no_infinity

_SELECTED_EVENT_MODE = "masked_full_series"


def prepare_h1_d1_frozen(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = frame.copy()
    out["atr14"] = module.atr_wilder_local(out, 14)
    if timeframe == "H1":
        mean = out["close"].rolling(60, min_periods=60).mean()
        sd = out["close"].rolling(60, min_periods=60).std(ddof=0)
        out["bb60_upper"] = mean + 2.0 * sd
        out["spread_atr"] = out["spread"] * module.base.POINT / out["atr14"]
        return out
    if timeframe == "D1":
        out["rci18"] = module.rci_variant(out["close"], 18, "average", "d2")
        out["tickvol_ratio50"] = out["tick_volume"] / out["tick_volume"].rolling(50, min_periods=50).mean()
        out["delta_atr_3"] = (out["close"] - out["close"].shift(3)) / out["atr14"]
        return out
    raise ValueError(timeframe)


def derive_m15_with_mode(
    engine: Any,
    m15: pd.DataFrame,
    h4: pd.DataFrame,
    event_mode: str,
) -> dict[str, pd.DataFrame]:
    joined = pd.merge_asof(
        m15.sort_values("bar_close_time"),
        h4[["bar_close_time", "rci18", "spread_atr", "upper_wick_frac", "ema40_slope6_atr"]]
        .dropna(subset=["rci18", "spread_atr"])
        .sort_values("bar_close_time"),
        on="bar_close_time",
        direction="backward",
        allow_exact_matches=True,
    )
    joined["state"] = (
        (joined["rci18"] >= module.RCI_THRESHOLD)
        & (joined["spread_atr"] <= module.SPREAD_ATR_THRESHOLD)
    )
    joined["eligible"] = (
        (joined["source"] == "historical")
        & joined["bar_close_time"].map(engine.has_exact_entry)
        & ((joined["bar_close_time"] + pd.Timedelta(hours=6)) <= engine.latest_close)
    )

    if event_mode == "masked_full_series":
        active = joined["state"] & joined["eligible"]
        joined["event"] = active & ~active.shift(fill_value=False)
        events = joined[joined["event"]].copy()
    elif event_mode == "filtered_eligible_series":
        eligible = joined[joined["eligible"]].copy()
        eligible["event"] = eligible["state"] & ~eligible["state"].shift(fill_value=False)
        events = eligible[eligible["event"]].copy()
    elif event_mode == "state_onset_then_eligible":
        joined["event"] = (
            joined["state"]
            & ~joined["state"].shift(fill_value=False)
            & joined["eligible"]
        )
        events = joined[joined["event"]].copy()
    else:
        raise ValueError(event_mode)

    parent = module.evaluate_events_fast(
        events,
        engine,
        6,
        ["upper_wick_frac", "ema40_slope6_atr", "bb20_width_atr", "bb60_width_pct100"],
    )
    if parent.empty:
        parent = pd.DataFrame(columns=[
            "decision_close_time", "entry_time", "exit_time", "r_value", "direction",
            "upper_wick_frac", "ema40_slope6_atr", "bb20_width_atr", "bb60_width_pct100",
        ])
    parent["candidate_id"] = "GML1-PROV-002-DIAGNOSTIC"

    p7 = parent[~(
        (parent["upper_wick_frac"] >= 0.27488556398168634)
        & (parent["ema40_slope6_atr"] >= 0.6863028800058267)
    )].copy()
    p7["candidate_id"] = "GML1-PROV-007"

    p8 = parent[~(
        (parent["bb20_width_atr"] <= 3.3719018700718184)
        & (parent["bb60_width_pct100"] <= 0.536)
    )].copy()
    p8["candidate_id"] = "GML1-PROV-008"

    w22 = p7[~(
        (p7["upper_wick_frac"] <= 0.06526044468913629)
        & (p7["ema40_slope6_atr"] >= 0.8700779249713114)
    )].copy()
    w22["candidate_id"] = "GML1-WATCH-022-B"

    return {
        "GML1-PROV-002-DIAGNOSTIC": parent,
        "GML1-PROV-007": p7,
        "GML1-PROV-008": p8,
        "GML1-WATCH-022-B": w22,
    }


def resolve_m15_contract(
    h4: pd.DataFrame,
    m15: pd.DataFrame,
    engine: Any,
    geometry: dict[str, Any],
    expected_p7: pd.DataFrame,
    expected_p8: pd.DataFrame,
    expected_w22: pd.DataFrame,
) -> dict[str, Any]:
    global _SELECTED_EVENT_MODE
    selected_geometry = geometry["selected"]
    candidates: list[dict[str, Any]] = []

    for formula in ["d2", "corr"]:
        for shift in [0, 1]:
            features = module.build_h4_features(
                h4,
                selected_geometry["atr_name"],
                selected_geometry["ema_name"],
                "close",
                "average",
                formula,
                shift,
            )
            for mode in ["masked_full_series", "filtered_eligible_series", "state_onset_then_eligible"]:
                derived = derive_m15_with_mode(engine, m15, features, mode)
                s7 = module.set_score(derived["GML1-PROV-007"], expected_p7)
                s8 = module.set_score(derived["GML1-PROV-008"], expected_p8)
                s22 = module.set_score(derived["GML1-WATCH-022-B"], expected_w22)
                score = s7["symmetric_difference"] + s8["symmetric_difference"] + s22["symmetric_difference"]
                candidates.append({
                    "source": "close",
                    "rank_method": "average",
                    "formula": formula,
                    "shift": shift,
                    "event_mode": mode,
                    "p7": s7,
                    "p8": s8,
                    "w22": s22,
                    "score": score,
                })

    ranked = sorted(candidates, key=lambda row: row["score"])
    if ranked[0]["score"] != 0:
        raise RuntimeError(f"No exact frozen M15 evaluator contract match; top={ranked[:12]}")
    _SELECTED_EVENT_MODE = ranked[0]["event_mode"]
    return {"selected": ranked[0], "ranked": ranked}


def derive_selected(engine: Any, m15: pd.DataFrame, h4: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return derive_m15_with_mode(engine, m15, h4, _SELECTED_EVENT_MODE)


module.prepare_h1_d1 = prepare_h1_d1_frozen
module.resolve_rci_contract = resolve_m15_contract
module.derive_m15_candidates = derive_selected

raise SystemExit(module.main())
