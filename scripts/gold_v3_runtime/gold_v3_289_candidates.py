#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 fixed candidate detection from contractually closed live candles."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gold_v3_289_artifacts import load_frozen_booster, validate_model_bundle
from gold_v3_289_live_features import (
    EXTERNAL_FILES,
    GOLD_FILES,
    add_external_short_features,
    build_stage280_context,
    build_stage281_context,
    find_trigger,
    m5_trigger_frame,
    read_candles,
    stage280_model_frame,
    stage281_model_frame,
)

STAGE286_Q90_LOWER = 2.162461836828524
STAGE286_SCORE_UPPER = 2.992581130893
STAGE286_RISK_UPPER = 0.410970621210


def model_dir() -> Path:
    return Path(__file__).resolve().with_name("models") / "gold_v3_289"


def load_model_contracts() -> tuple[
    Path, dict[str, Any], Path, dict[str, Any], dict[str, Any]
]:
    """Validate the entire local bundle before returning either model."""
    validated = validate_model_bundle(model_dir())
    stage280 = validated["models"]["stage280"]
    stage281 = validated["models"]["stage281"]
    return (
        Path(stage280["model_path"]),
        dict(stage280["contract"]),
        Path(stage281["model_path"]),
        dict(stage281["contract"]),
        validated,
    )


def candidate_id(source: str, entry: pd.Timestamp) -> str:
    return f"{source}|{pd.Timestamp(entry).isoformat()}"


def dedupe_source_candidates(
    dataframe: pd.DataFrame, source: str, cooldown_minutes: int = 0
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe.copy()
    selected = dataframe[dataframe.source.eq(source)].copy()
    if selected.empty:
        return selected
    selected = (
        selected.sort_values(
            ["entry_dt", "ml_score", "decision_dt"],
            ascending=[True, False, True],
        )
        .drop_duplicates("entry_dt", keep="first")
    )
    if cooldown_minutes > 0:
        keep: list[int] = []
        last = pd.Timestamp.min
        for row in selected.sort_values(
            ["decision_dt", "entry_dt"]
        ).itertuples():
            decision = pd.Timestamp(row.decision_dt)
            if decision >= last + pd.Timedelta(minutes=cooldown_minutes):
                keep.append(row.Index)
                last = decision
        selected = selected.loc[keep]
    selected["candidate_id"] = [
        candidate_id(source, entry) for entry in selected.entry_dt
    ]
    return selected.sort_values("entry_dt").reset_index(drop=True)


def detect_candidates(
    candle_dir: Path,
    lookback_hours: int,
    stage286_external_ready: bool | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    stage280_model_path, stage280_contract, stage281_model_path, stage281_contract, validated = load_model_contracts()
    stage280_booster = load_frozen_booster(stage280_model_path)
    stage281_booster = load_frozen_booster(stage281_model_path)

    m5 = m5_trigger_frame(candle_dir)
    latest_m15 = read_candles(
        candle_dir / GOLD_FILES["M15"],
        4,
        timeframe="M15",
        require_spread=True,
    )
    latest_time = max(
        pd.Timestamp(m5.time.max()), pd.Timestamp(latest_m15.time.max())
    )
    cutoff = latest_time - pd.Timedelta(hours=lookback_hours)
    rows: list[dict[str, Any]] = []

    context280 = build_stage280_context(candle_dir, include_next=True)
    recent280 = context280[context280.time >= cutoff].copy()
    frame280 = stage280_model_frame(
        recent280, list(stage280_contract["features"])
    )
    recent280["ml_score"] = stage280_booster.predict(frame280)
    recent280["score_threshold"] = float(
        stage280_contract["score_threshold"]
    )
    eligible280 = recent280[
        (recent280.h4_trend == -1)
        & (recent280.ml_score >= recent280.score_threshold)
    ]
    for row in eligible280.itertuples():
        trigger, entry, price = find_trigger(
            m5, pd.Timestamp(row.time), 1, "BRK6", 60
        )
        if (
            pd.isna(entry)
            or not np.isfinite(price)
            or not np.isfinite(float(row.atr_prev))
        ):
            continue
        rows.append(
            {
                "candidate_id": "",
                "source": "STAGE280",
                "priority": 10,
                "decision_dt": row.time,
                "trigger_dt": trigger,
                "entry_dt": entry,
                "entry_price": price,
                "direction": "LONG",
                "direction_num": 1,
                "ml_score": row.ml_score,
                "score_threshold": row.score_threshold,
                "atr_entry": row.atr_prev,
                "tp_atr": 1.75,
                "sl_atr": 1.0,
                "max_holding_minutes": 360,
                "candidate_contract": "REV_LONG_Q95_BRK6_E175_SHADOW_RESEARCH",
            }
        )

    context281 = build_stage281_context(candle_dir, include_next=True)
    recent281 = context281[context281.time >= cutoff].copy()
    frame281 = stage281_model_frame(
        recent281, list(stage281_contract["features"])
    )
    recent281["ml_score"] = stage281_booster.predict(frame281)
    recent281["score_threshold"] = float(
        stage281_contract["score_threshold"]
    )
    eligible281 = recent281[
        (recent281.h4_trend == 1)
        & (recent281.ml_score >= recent281.score_threshold)
    ]
    for row in eligible281.itertuples():
        trigger, entry, price = find_trigger(
            m5, pd.Timestamp(row.time), 1, "EMA20", 45
        )
        if (
            pd.isna(entry)
            or not np.isfinite(price)
            or not np.isfinite(float(row.h1_atr14))
        ):
            continue
        rows.append(
            {
                "candidate_id": "",
                "source": "STAGE281",
                "priority": 20,
                "decision_dt": row.time,
                "trigger_dt": trigger,
                "entry_dt": entry,
                "entry_price": price,
                "direction": "LONG",
                "direction_num": 1,
                "ml_score": row.ml_score,
                "score_threshold": row.score_threshold,
                "atr_entry": row.h1_atr14,
                "tp_atr": 2.25,
                "sl_atr": 1.25,
                "max_holding_minutes": 480,
                "candidate_contract": "M15_CONT_LONG_Q85_EMA20_E225_AFTER_BASE_LOSS_72H_SHADOW_NEAR_MISS",
            }
        )

    external_ready = (
        bool(stage286_external_ready)
        if stage286_external_ready is not None
        else all(
            (candle_dir / filename).exists()
            for filename in EXTERNAL_FILES.values()
        )
    )
    if external_ready:
        short_context = add_external_short_features(context281, candle_dir)
        short_recent = short_context[short_context.time >= cutoff].copy()
        strict = short_recent[
            (short_recent.h4_trend == 1)
            & (short_recent.m15_ret8_atr >= STAGE286_Q90_LOWER)
            & (short_recent.m15_ret8_atr <= STAGE286_SCORE_UPPER)
            & (short_recent.m15_pos4 >= 0.75)
            & (
                short_recent.m15_upper_wick_ratio
                >= short_recent.m15_lower_wick_ratio
            )
            & (short_recent.risk_m15_ret4_mean <= STAGE286_RISK_UPPER)
        ]
        for row in strict.itertuples():
            trigger, entry, price = find_trigger(
                m5, pd.Timestamp(row.time), -1, "EMA20", 60
            )
            if (
                pd.isna(entry)
                or not np.isfinite(price)
                or not np.isfinite(float(row.h1_atr14))
            ):
                continue
            rows.append(
                {
                    "candidate_id": "",
                    "source": "STAGE286",
                    "priority": 60,
                    "decision_dt": row.time,
                    "trigger_dt": trigger,
                    "entry_dt": entry,
                    "entry_price": price,
                    "direction": "SHORT",
                    "direction_num": -1,
                    "ml_score": np.nan,
                    "score_threshold": np.nan,
                    "atr_entry": row.h1_atr14,
                    "tp_atr": 2.25,
                    "sl_atr": 1.25,
                    "max_holding_minutes": 480,
                    "candidate_contract": "SHORT_EXHAUST_MODERATE_OVERHEAT_SUBDUED_US_EQUITY",
                    "gold_exhaustion_score": row.m15_ret8_atr,
                    "risk_m15_ret4_mean": row.risk_m15_ret4_mean,
                }
            )

    result = pd.DataFrame(rows)
    if len(result):
        result["decision_dt"] = pd.to_datetime(result.decision_dt)
        result["trigger_dt"] = pd.to_datetime(result.trigger_dt)
        result["entry_dt"] = pd.to_datetime(result.entry_dt)
        parts = [
            dedupe_source_candidates(result, "STAGE280", 0),
            dedupe_source_candidates(result, "STAGE281", 120),
            dedupe_source_candidates(result, "STAGE286", 120),
        ]
        nonempty = [part for part in parts if len(part)]
        result = (
            pd.concat(nonempty, ignore_index=True)
            if nonempty
            else pd.DataFrame(columns=result.columns)
        )
        result = result.sort_values(
            ["entry_dt", "priority", "candidate_id"]
        ).reset_index(drop=True)

    return result, {
        "latest_candle_time": str(latest_time),
        "stage280_threshold": float(stage280_contract["score_threshold"]),
        "stage281_threshold": float(stage281_contract["score_threshold"]),
        "external_short_ready": external_ready,
        "model_bundle_status": validated["status"],
        "stage280_model_sha256": validated["models"]["stage280"]["model_sha256"],
        "stage281_model_sha256": validated["models"]["stage281"]["model_sha256"],
    }
