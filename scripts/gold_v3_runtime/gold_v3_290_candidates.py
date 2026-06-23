from __future__ import annotations
from pathlib import Path
import pandas as pd
import gold_v3_289_candidates as stage289
from gold_v3_289_feature_core import GOLD_FILES,read_candles
from gold_v3_290_trigger_intent import find_trigger_intent

def detect_addition_intents(candle_dir: Path,lookback_hours=96,external_ready=None):
    """Reuse frozen Stage289 models but do not wait for a future M5 row."""
    original=stage289.find_trigger
    stage289.find_trigger=find_trigger_intent
    try:
        data,meta=stage289.detect_candidates(candle_dir,lookback_hours,stage286_external_ready=external_ready)
    finally:
        stage289.find_trigger=original
    if data.empty:
        return data,meta
    data=data.rename(columns={"entry_price":"reference_price"})
    data["planned_entry_dt"]=pd.to_datetime(data.entry_dt,errors="coerce")
    data["status"]="INTENT"
    m1=read_candles(candle_dir/GOLD_FILES["M1"],10,timeframe="M1",require_spread=True)
    latest_m1_close=pd.Timestamp(m1.time.max())+pd.Timedelta(minutes=1)
    data["intent_lag_seconds"]=(latest_m1_close-data.planned_entry_dt).dt.total_seconds()
    meta=dict(meta); meta["latest_m1_close"]=str(latest_m1_close)
    return data,meta
