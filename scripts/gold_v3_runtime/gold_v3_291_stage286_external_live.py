#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage291: connect live US100/US500 M15 candles to Stage286 strict SHORT.

This module is read-only. It validates the two broker-exported index files,
builds the exact Stage286 entry-known features, and emits live trigger intents
without waiting for a future M5 row.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gold_v3_289_candidates import (
    STAGE286_Q90_LOWER,
    STAGE286_RISK_UPPER,
    STAGE286_SCORE_UPPER,
)
from gold_v3_289_feature_core import EXTERNAL_FILES, merge_closed, read_candles
from gold_v3_289_stage281_features import build_stage281_context
from gold_v3_289_trigger_features import m5_trigger_frame

MIN_EXTERNAL_ROWS = 20


@dataclass(frozen=True)
class ExternalPair:
    sp: pd.DataFrame
    nq: pd.DataFrame
    checks: list[dict[str, Any]]
    latest_time: pd.Timestamp


def _add_ret4_atr(data: pd.DataFrame) -> pd.DataFrame:
    out = data.copy()
    previous_close = out.close.shift(1)
    true_range = pd.concat(
        [
            (out.high - out.low).abs(),
            (out.high - previous_close).abs(),
            (out.low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr14"] = true_range.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    out["ret4_atr"] = (out.close - out.close.shift(4)) / out.atr14
    out["source_bar_time"] = out.time
    return out


def validate_external_pair(
    candle_dir: Path, tail_rows: int = 6000
) -> ExternalPair:
    candle_dir = Path(candle_dir)
    checks: list[dict[str, Any]] = []
    loaded: dict[str, pd.DataFrame] = {}

    for key, label in [("SP_M15", "US500"), ("NQ_M15", "US100")]:
        filename = EXTERNAL_FILES[key]
        path = candle_dir / filename
        frame = read_candles(
            path,
            tail_rows,
            timeframe="M15",
            require_spread=False,
        )
        if len(frame) < MIN_EXTERNAL_ROWS:
            raise ValueError(
                f"{filename}: insufficient rows {len(frame)} < {MIN_EXTERNAL_ROWS}"
            )
        if frame.attrs.get("duplicate_time_ohlc_conflict_count", 0):
            raise ValueError(f"{filename}: conflicting duplicate OHLC rows")
        loaded[label] = _add_ret4_atr(frame)
        checks.append(
            {
                "check": f"{label}_M15_CSV",
                "passed": True,
                "filename": filename,
                "rows": int(len(frame)),
                "first_time": str(frame.time.min()),
                "latest_time": str(frame.time.max()),
                "separator": frame.attrs.get("separator"),
                "latest_row_closed_by_contract": bool(
                    frame.attrs.get("latest_row_closed_by_contract", False)
                ),
                "dropped_incomplete": int(
                    frame.attrs.get("rows_dropped_incomplete", 0)
                ),
                "duplicate_time_count": int(
                    frame.attrs.get("duplicate_time_count", 0)
                ),
            }
        )

    sp = loaded["US500"]
    nq = loaded["US100"]
    sp_latest = pd.Timestamp(sp.time.max())
    nq_latest = pd.Timestamp(nq.time.max())
    if sp_latest != nq_latest:
        raise ValueError(
            f"external latest M15 mismatch: US500={sp_latest}, US100={nq_latest}"
        )

    common = pd.Index(sp.time).intersection(pd.Index(nq.time))
    if len(common) < MIN_EXTERNAL_ROWS:
        raise ValueError(
            f"external common M15 rows insufficient: {len(common)}"
        )
    if pd.Timestamp(common.max()) != sp_latest:
        raise ValueError("external latest M15 row is not common to both indices")

    checks.append(
        {
            "check": "US500_US100_M15_ALIGNMENT",
            "passed": True,
            "common_rows": int(len(common)),
            "latest_common_time": str(common.max()),
        }
    )
    return ExternalPair(sp=sp, nq=nq, checks=checks, latest_time=sp_latest)


def build_stage286_context(
    candle_dir: Path, tail_rows: int = 6000
) -> tuple[pd.DataFrame, ExternalPair]:
    pair = validate_external_pair(candle_dir, tail_rows=tail_rows)
    context = build_stage281_context(
        Path(candle_dir), include_next=True, tail_only=True
    )
    out = context.copy()
    for prefix, source in [("sp_m15", pair.sp), ("nq_m15", pair.nq)]:
        out = merge_closed(
            out,
            source,
            prefix,
            15,
            ["source_bar_time", "ret4_atr"],
        )

    out["risk_m15_ret4_mean"] = out[
        ["sp_m15_ret4_atr", "nq_m15_ret4_atr"]
    ].mean(axis=1)
    out["gate_h4_up"] = out.h4_trend.eq(1)
    out["gate_q90_lower"] = out.m15_ret8_atr.ge(STAGE286_Q90_LOWER)
    out["gate_score_upper"] = out.m15_ret8_atr.le(
        STAGE286_SCORE_UPPER
    )
    out["gate_pos4"] = out.m15_pos4.ge(0.75)
    out["gate_upper_wick"] = out.m15_upper_wick_ratio.ge(
        out.m15_lower_wick_ratio
    )
    out["gate_us_equity"] = out.risk_m15_ret4_mean.le(
        STAGE286_RISK_UPPER
    )
    feature_columns = [
        "m15_ret8_atr",
        "m15_pos4",
        "m15_upper_wick_ratio",
        "m15_lower_wick_ratio",
        "sp_m15_ret4_atr",
        "nq_m15_ret4_atr",
        "risk_m15_ret4_mean",
        "h1_atr14",
    ]
    out["gate_features_finite"] = np.isfinite(
        out[feature_columns].astype(float)
    ).all(axis=1)
    gate_columns = [
        "gate_h4_up",
        "gate_q90_lower",
        "gate_score_upper",
        "gate_pos4",
        "gate_upper_wick",
        "gate_us_equity",
        "gate_features_finite",
    ]
    out["stage286_condition_pass"] = out[gate_columns].all(axis=1)
    return out, pair


def find_live_trigger(
    m5: pd.DataFrame,
    decision_time: pd.Timestamp,
    max_wait_minutes: int = 60,
) -> tuple[pd.Timestamp, pd.Timestamp, float]:
    """Return a SHORT EMA20 trigger at the close of an observed M5 bar.

    No next-row open is read. ``planned_entry_dt`` is the trigger bar close and
    ``reference_price`` is the trigger bar close; actual live fill is separate.
    """
    times = m5.time.to_numpy("datetime64[ns]")
    start = max(
        np.searchsorted(times, np.datetime64(decision_time), side="left"), 1
    )
    limit = np.datetime64(
        pd.Timestamp(decision_time)
        + pd.Timedelta(minutes=max_wait_minutes)
    )
    end = min(np.searchsorted(times, limit, side="left"), len(m5))
    high = m5.high.to_numpy(float)
    low = m5.low.to_numpy(float)
    close = m5.close.to_numpy(float)
    body = m5.body_signed.to_numpy(float)
    ema20 = m5.ema20.to_numpy(float)

    for index in range(start, end):
        signed_body = -1.0 * body[index]
        passed = (
            close[index] < ema20[index]
            and close[index - 1] >= ema20[index - 1]
            and close[index] < low[index - 1]
            and signed_body >= 0.12
        )
        if passed:
            trigger_time = pd.Timestamp(times[index])
            planned_entry = trigger_time + pd.Timedelta(minutes=5)
            return trigger_time, planned_entry, float(close[index])
    return pd.NaT, pd.NaT, np.nan


def detect_stage286_candidates(
    candle_dir: Path, lookback_hours: int = 96
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    context, pair = build_stage286_context(candle_dir)
    m5 = m5_trigger_frame(Path(candle_dir))
    latest_m5_close = pd.Timestamp(m5.time.max()) + pd.Timedelta(minutes=5)
    latest_decision = pd.Timestamp(context.time.max())
    cutoff = max(latest_decision, pd.Timestamp(m5.time.max())) - pd.Timedelta(
        hours=lookback_hours
    )

    recent = context[context.time.ge(cutoff)].copy()
    strict = recent[recent.stage286_condition_pass].copy()
    rows: list[dict[str, Any]] = []
    for row in strict.itertuples(index=False):
        trigger, planned_entry, reference_price = find_live_trigger(
            m5, pd.Timestamp(row.time), 60
        )
        if pd.isna(planned_entry) or not np.isfinite(reference_price):
            continue
        rows.append(
            {
                "candidate_id": (
                    "STAGE286|" + pd.Timestamp(planned_entry).isoformat()
                ),
                "source": "STAGE286",
                "priority": 60,
                "decision_dt": row.time,
                "trigger_dt": trigger,
                "planned_entry_dt": planned_entry,
                "reference_price": reference_price,
                "direction": "SHORT",
                "direction_num": -1,
                "atr_entry": row.h1_atr14,
                "tp_atr": 2.25,
                "sl_atr": 1.25,
                "max_holding_minutes": 480,
                "candidate_contract": (
                    "SHORT_EXHAUST_MODERATE_OVERHEAT_SUBDUED_US_EQUITY"
                ),
                "gold_exhaustion_score": row.m15_ret8_atr,
                "m15_pos4": row.m15_pos4,
                "m15_upper_wick_ratio": row.m15_upper_wick_ratio,
                "m15_lower_wick_ratio": row.m15_lower_wick_ratio,
                "us500_source_bar_time": row.sp_m15_source_bar_time,
                "us500_ret4_atr": row.sp_m15_ret4_atr,
                "us100_source_bar_time": row.nq_m15_source_bar_time,
                "us100_ret4_atr": row.nq_m15_ret4_atr,
                "risk_m15_ret4_mean": row.risk_m15_ret4_mean,
                "is_latest_live_trigger": (
                    pd.Timestamp(planned_entry) == latest_m5_close
                ),
            }
        )

    candidates = pd.DataFrame(rows)
    if len(candidates):
        candidates = (
            candidates.sort_values(
                ["planned_entry_dt", "decision_dt", "candidate_id"]
            )
            .drop_duplicates("planned_entry_dt", keep="first")
            .reset_index(drop=True)
        )

    snapshot_columns = [
        "time",
        "h4_trend",
        "m15_ret8_atr",
        "m15_pos4",
        "m15_upper_wick_ratio",
        "m15_lower_wick_ratio",
        "sp_m15_source_bar_time",
        "sp_m15_ret4_atr",
        "nq_m15_source_bar_time",
        "nq_m15_ret4_atr",
        "risk_m15_ret4_mean",
        "gate_h4_up",
        "gate_q90_lower",
        "gate_score_upper",
        "gate_pos4",
        "gate_upper_wick",
        "gate_us_equity",
        "gate_features_finite",
        "stage286_condition_pass",
    ]
    snapshot = recent[snapshot_columns].tail(1).reset_index(drop=True)
    meta = {
        "us500_file": EXTERNAL_FILES["SP_M15"],
        "us100_file": EXTERNAL_FILES["NQ_M15"],
        "external_latest_m15_time": str(pair.latest_time),
        "latest_gold_decision_time": str(latest_decision),
        "latest_m5_close_time": str(latest_m5_close),
        "condition_pass_count": int(strict.shape[0]),
        "candidate_count": int(candidates.shape[0]),
        "latest_live_candidate_count": int(
            candidates.is_latest_live_trigger.sum()
        )
        if len(candidates)
        else 0,
        "checks": pair.checks,
    }
    return candidates, snapshot, meta
