from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
RUNTIME=Path(__file__).resolve().parents[2]/"scripts"/"gold_v3_runtime"
sys.path.insert(0,str(RUNTIME))
from gold_v3_290_admission import evaluate_intents
from gold_v3_290_state import state_at
from gold_v3_290_trigger_intent import find_trigger_intent

def test_closed_trigger_entry_intent():
    t=pd.date_range("2026-06-23 10:00",periods=8,freq="5min")
    f=pd.DataFrame({"time":t,"open":[100]*8,"high":[101,101,101,101,101,101,102,104],"low":[99]*8,"close":[100,100,100,100,100,100,101,104],"body_signed":[0,0,0,0,0,0,0.2,0.8],"ema20":[100]*8})
    trigger,entry,reference=find_trigger_intent(f,t[6],1,"BRK6",60)
    assert trigger==t[7] and entry==t[7]+pd.Timedelta(minutes=5) and reference==104

def test_resolved_only_state():
    b=pd.DataFrame([{"candidate_id":"a","source":"BASE","entry_dt":"2026-01-01","exit_dt":"2026-01-02","pnl":10},{"candidate_id":"b","source":"BASE","entry_dt":"2026-01-03","exit_dt":"2026-01-05","pnl":-5}])
    b[["entry_dt","exit_dt"]]=b[["entry_dt","exit_dt"]].apply(pd.to_datetime)
    assert state_at(pd.Timestamp("2026-01-04"),pd.DataFrame(),b)["equity"]==10
    assert state_at(pd.Timestamp("2026-01-05"),pd.DataFrame(),b)["equity"]==5

def test_stage286_dd_gate():
    b=pd.DataFrame([{"candidate_id":"a","source":"BASE","entry_dt":pd.Timestamp("2026-01-01"),"exit_dt":pd.Timestamp("2026-01-02"),"pnl":20},{"candidate_id":"b","source":"BASE","entry_dt":pd.Timestamp("2026-01-03"),"exit_dt":pd.Timestamp("2026-01-04"),"pnl":-15}])
    i=pd.DataFrame([{"candidate_id":"s","source":"STAGE286","priority":60,"planned_entry_dt":pd.Timestamp("2026-01-05"),"decision_dt":pd.Timestamp("2026-01-05"),"trigger_dt":pd.Timestamp("2026-01-05"),"direction":"SHORT","direction_num":-1,"reference_price":100,"atr_entry":10,"tp_atr":2.25,"sl_atr":1.25,"max_holding_minutes":480,"intent_lag_seconds":0}])
    d,l=evaluate_intents(i,pd.DataFrame(),b)
    assert not bool(d.iloc[0].final_signal)
    assert "RESOLVED_COMBINED_DD_ABOVE_10" in d.iloc[0].reject_reasons
    assert l.empty
