from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from gold_v3_67_health_gate_rehydration_audit import KEY_COLS,build_candidate_key,loss_streak,pf
from gold_v3_70_live_csv_signal_decision_preview_audit import add_key_columns
from gold_v3_290_io import require_columns

RESULT_COLUMNS=["pnl","result_usd","profit","net_profit","outcome_usd"]
EXIT_COLUMNS=["exit_dt","resolved_at","close_time","exit_time"]

def load_base_history(path: Path) -> pd.DataFrame:
    data=pd.read_csv(path,encoding="utf-8-sig")
    result=next((c for c in RESULT_COLUMNS if c in data.columns),None)
    exit_col=next((c for c in EXIT_COLUMNS if c in data.columns),None)
    if result is None or exit_col is None: raise ValueError("base history requires resolved exit time and pnl")
    if "candidate_key" not in data.columns:
        require_columns(data,set(KEY_COLS),"base resolved health history")
        data["candidate_key"]=build_candidate_key(data)
    data["exit_dt"]=pd.to_datetime(data[exit_col],errors="coerce")
    data["pnl"]=pd.to_numeric(data[result],errors="coerce")
    return data[["candidate_key","exit_dt","pnl"]].dropna().sort_values(["exit_dt","candidate_key"])

def live_base_history(ledger: pd.DataFrame) -> pd.DataFrame:
    needed={"source","status","candidate_key","exit_dt","pnl"}
    if ledger.empty or not needed.issubset(ledger.columns): return pd.DataFrame(columns=["candidate_key","exit_dt","pnl"])
    data=ledger[(ledger.source.astype(str)=="BASE") & (ledger.status.astype(str)=="CLOSED")].copy()
    data["exit_dt"]=pd.to_datetime(data.exit_dt,errors="coerce"); data["pnl"]=pd.to_numeric(data.pnl,errors="coerce")
    return data[["candidate_key","exit_dt","pnl"]].dropna()

def health_for(candidate_key,time,history):
    values=history[(history.candidate_key.astype(str)==str(candidate_key)) & (history.exit_dt<=pd.Timestamp(time))].sort_values("exit_dt").pnl.tail(30).to_list()
    if len(values)<20: return True,"INSUFFICIENT_HISTORY",len(values),np.nan,np.nan
    rolling_pf=float(pf(values)); streak=int(loss_streak(values)); passed=rolling_pf>=1.10 and streak<3
    reason="PASS" if passed else "+".join((["PF_BELOW_THRESHOLD"] if rolling_pf<1.10 else [])+(["LOSS_STREAK_LIMIT"] if streak>=3 else []))
    return passed,reason,len(values),rolling_pf,streak

def load_base_intent(files_dir: Path,base_history_path: Path,ledger: pd.DataFrame) -> pd.DataFrame:
    root=files_dir/"FX_OUTPUTS"/"gold_v3"/"69_live_csv_condition_detector_audit_only"
    summary_path=root/"gold_v3_69_live_csv_condition_detector_summary.json"; latest_path=root/"gold_v3_69_latest_closed_condition_candidates.csv"
    if not summary_path.exists() or not latest_path.exists(): return pd.DataFrame()
    import json
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status")!="GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY": raise ValueError("Stage69 BASE detector is not READY")
    latest=pd.read_csv(latest_path,encoding="utf-8-sig")
    if latest.empty: return pd.DataFrame()
    latest=add_key_columns(latest); planned=pd.Timestamp(summary["latest_closed_m15_time"])+pd.Timedelta(minutes=15)
    history=pd.concat([load_base_history(base_history_path),live_base_history(ledger)],ignore_index=True).drop_duplicates(["candidate_key","exit_dt"],keep="last")
    rows=[]
    for row in latest.sort_values(["priority","candidate_label","candidate_key","condition_id"],kind="mergesort").itertuples(index=False):
        passed,reason,n,rpf,streak=health_for(row.candidate_key,planned,history)
        if not passed: continue
        rows.append({"candidate_id":f"BASE|{row.candidate_key}|{planned.isoformat()}","candidate_key":row.candidate_key,"source":"BASE","priority":0,"decision_dt":planned,"trigger_dt":planned,"planned_entry_dt":planned,"direction":"LONG","direction_num":1,"reference_price":float(row.entry_price),"atr_entry":np.nan,"tp_atr":np.nan,"sl_atr":np.nan,"tp_usd":float(row.tp_usd),"sl_usd":float(row.sl_usd),"max_holding_minutes":int(row.horizon_m15)*15,"candidate_contract":str(row.candidate_label),"base_health_reason":reason,"base_health_history_count":n,"base_health_pf":rpf,"base_health_loss_streak":streak,"status":"INTENT"})
        break
    return pd.DataFrame(rows)
