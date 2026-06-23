#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

from gold_v3_289_artifacts import load_frozen_booster
from gold_v3_289_candidates import (
    candidate_id, dedupe_source_candidates, load_model_contracts,
)
from gold_v3_289_live_features import (
    GOLD_FILES, build_stage280_context, build_stage281_context,
    m5_trigger_frame, read_candles, stage280_model_frame, stage281_model_frame,
)
from gold_v3_291_stage286_external_live import detect_stage286_candidates

COMMON_COLUMNS = [
    "candidate_id","source","priority","decision_dt","trigger_dt","entry_dt",
    "reference_price","direction","direction_num","atr_entry","tp_atr","sl_atr",
    "tp_distance","sl_distance","max_holding_minutes","candidate_contract","candidate_key",
]


def find_live_trigger(m5, decision_time, direction, kind, max_wait_minutes):
    times = m5.time.to_numpy("datetime64[ns]")
    start = max(np.searchsorted(times, np.datetime64(decision_time), side="left"), 6)
    limit = np.datetime64(pd.Timestamp(decision_time) + pd.Timedelta(minutes=max_wait_minutes))
    end = min(np.searchsorted(times, limit, side="left"), len(m5))
    high, low, close = m5.high.to_numpy(float), m5.low.to_numpy(float), m5.close.to_numpy(float)
    body, ema = m5.body_signed.to_numpy(float), m5.ema20.to_numpy(float)
    for index in range(start, end):
        signed = direction * body[index]
        if kind == "BRK6":
            passed = ((close[index] > high[index-6:index].max()) if direction == 1 else (close[index] < low[index-6:index].min())) and signed >= 0.20
        elif kind == "EMA20":
            passed = ((close[index] > ema[index] and close[index-1] <= ema[index-1] and close[index] > high[index-1]) if direction == 1 else (close[index] < ema[index] and close[index-1] >= ema[index-1] and close[index] < low[index-1])) and signed >= (0.15 if direction == 1 else 0.12)
        else:
            raise ValueError(kind)
        if passed:
            trigger = pd.Timestamp(times[index])
            return trigger, trigger + pd.Timedelta(minutes=5), float(close[index])
    return pd.NaT, pd.NaT, np.nan


def load_base_candidate(candle_dir: Path) -> pd.DataFrame:
    root = Path(candle_dir) / "FX_OUTPUTS" / "gold_v3" / "70_live_csv_signal_decision_preview_audit_only"
    path = root / "gold_v3_70_latest_closed_signal_decision.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    data = pd.read_csv(path, encoding="utf-8-sig")
    if data.empty or str(data.iloc[-1].get("decision", "")) != "SIGNAL":
        return pd.DataFrame(columns=COMMON_COLUMNS)
    row = data.iloc[-1]
    bar_time = pd.Timestamp(row["entry_dt"])
    entry_time = bar_time + pd.Timedelta(minutes=15)
    candidate_key = str(row.get("candidate_key", row.get("candidate_label", "BASE")))
    record = {
        "candidate_id":f"BASE|{candidate_key}|{entry_time.isoformat()}",
        "source":"BASE","priority":0,"decision_dt":entry_time,"trigger_dt":entry_time,
        "entry_dt":entry_time,"reference_price":float(row["entry_price"]),
        "direction":"LONG","direction_num":1,"atr_entry":np.nan,"tp_atr":np.nan,"sl_atr":np.nan,
        "tp_distance":float(row["tp_usd"]),"sl_distance":float(row["sl_usd"]),
        "max_holding_minutes":int(row["horizon_m15"])*15,
        "candidate_contract":str(row.get("candidate_label","BASE")),"candidate_key":candidate_key,
    }
    return pd.DataFrame([record], columns=COMMON_COLUMNS)


def detect_addition_candidates(candle_dir: Path, lookback_hours: int = 96):
    cdir = Path(candle_dir)
    m5 = m5_trigger_frame(cdir)
    latest = max(
        pd.Timestamp(m5.time.max()),
        pd.Timestamp(read_candles(cdir / GOLD_FILES["M15"], 4, timeframe="M15", require_spread=True).time.max()),
    )
    cutoff = latest - pd.Timedelta(hours=lookback_hours)
    p280, c280, p281, c281, validated = load_model_contracts()
    b280, b281 = load_frozen_booster(p280), load_frozen_booster(p281)
    rows = []

    x280 = build_stage280_context(cdir, include_next=True)
    x280 = x280[x280.time >= cutoff].copy()
    x280["ml_score"] = b280.predict(stage280_model_frame(x280, list(c280["features"])))
    for row in x280[(x280.h4_trend == -1) & (x280.ml_score >= float(c280["score_threshold"]))].itertuples():
        trigger, entry, price = find_live_trigger(m5, row.time, 1, "BRK6", 60)
        if pd.notna(entry) and np.isfinite(price) and np.isfinite(float(row.atr_prev)):
            rows.append({
                "candidate_id":"","source":"STAGE280","priority":10,"decision_dt":row.time,
                "trigger_dt":trigger,"entry_dt":entry,"reference_price":price,"entry_price":price,
                "direction":"LONG","direction_num":1,"ml_score":row.ml_score,
                "atr_entry":row.atr_prev,"tp_atr":1.75,"sl_atr":1.0,
                "tp_distance":1.75*float(row.atr_prev),"sl_distance":float(row.atr_prev),
                "max_holding_minutes":360,"candidate_contract":"REV_LONG_Q95_BRK6_E175","candidate_key":"",
            })

    x281 = build_stage281_context(cdir, include_next=True)
    x281 = x281[x281.time >= cutoff].copy()
    x281["ml_score"] = b281.predict(stage281_model_frame(x281, list(c281["features"])))
    for row in x281[(x281.h4_trend == 1) & (x281.ml_score >= float(c281["score_threshold"]))].itertuples():
        trigger, entry, price = find_live_trigger(m5, row.time, 1, "EMA20", 45)
        if pd.notna(entry) and np.isfinite(price) and np.isfinite(float(row.h1_atr14)):
            rows.append({
                "candidate_id":"","source":"STAGE281","priority":20,"decision_dt":row.time,
                "trigger_dt":trigger,"entry_dt":entry,"reference_price":price,"entry_price":price,
                "direction":"LONG","direction_num":1,"ml_score":row.ml_score,
                "atr_entry":row.h1_atr14,"tp_atr":2.25,"sl_atr":1.25,
                "tp_distance":2.25*float(row.h1_atr14),"sl_distance":1.25*float(row.h1_atr14),
                "max_holding_minutes":480,"candidate_contract":"M15_CONT_LONG_Q85_EMA20_E225_AFTER_BASE_LOSS_72H","candidate_key":"",
            })

    additions = pd.DataFrame(rows)
    if len(additions):
        parts = [
            dedupe_source_candidates(additions, "STAGE280", 0),
            dedupe_source_candidates(additions, "STAGE281", 120),
        ]
        additions = pd.concat([part for part in parts if len(part)], ignore_index=True)
        additions["reference_price"] = additions["entry_price"]
    short, _, short_meta = detect_stage286_candidates(cdir, lookback_hours=lookback_hours)
    if len(short):
        short = short.rename(columns={"planned_entry_dt":"entry_dt"})
        short["entry_price"] = short.reference_price
        short["tp_distance"] = short.tp_atr * short.atr_entry
        short["sl_distance"] = short.sl_atr * short.atr_entry
        short["candidate_key"] = ""
        short["candidate_id"] = [candidate_id("STAGE286", value) for value in short.entry_dt]
    combined = pd.concat([additions, short], ignore_index=True, sort=False)
    if combined.empty:
        combined = pd.DataFrame(columns=COMMON_COLUMNS)
    else:
        combined = combined.sort_values(["entry_dt","priority","candidate_id"], kind="mergesort")
    return combined, {
        "latest_candle_time":str(latest),
        "model_bundle_status":validated["status"],
        "stage286":short_meta,
    }


def detect_all_candidates(candle_dir: Path, lookback_hours: int = 96):
    base = load_base_candidate(candle_dir)
    additions, meta = detect_addition_candidates(candle_dir, lookback_hours)
    result = pd.concat([base, additions], ignore_index=True, sort=False)
    if len(result):
        result["entry_dt"] = pd.to_datetime(result.entry_dt)
        result["decision_dt"] = pd.to_datetime(result.decision_dt)
        result["trigger_dt"] = pd.to_datetime(result.trigger_dt)
        result = result.sort_values(["entry_dt","priority","candidate_id"], kind="mergesort")
    return result, meta
