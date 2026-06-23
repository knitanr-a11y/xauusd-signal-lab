from __future__ import annotations
from pathlib import Path
import pandas as pd
from gold_v3_290_io import read_csv_optional,require_columns

READY="GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_READY_AUDIT_ONLY"

def load_base_intent(files_dir: Path) -> pd.DataFrame:
    root=files_dir/"FX_OUTPUTS"/"gold_v3"/"70_live_csv_signal_decision_preview_audit_only"
    summary_path=root/"gold_v3_70_live_csv_signal_decision_preview_summary.json"
    decision_path=root/"gold_v3_70_latest_closed_signal_decision.csv"
    if not summary_path.exists() or not decision_path.exists(): return pd.DataFrame()
    import json
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status")!=READY: raise ValueError("Stage70 BASE decision preview is not READY")
    data=read_csv_optional(decision_path)
    if data.empty or str(data.iloc[-1].get("decision",""))!="SIGNAL": return pd.DataFrame()
    require_columns(data,{"candidate_key","entry_dt","entry_price","tp_usd","sl_usd","horizon_m15"},"Stage70 BASE signal")
    row=data.iloc[-1]
    bar_open=pd.Timestamp(row.entry_dt)
    planned=bar_open+pd.Timedelta(minutes=15)
    return pd.DataFrame([{
        "candidate_id":f"BASE|{row.candidate_key}|{planned.isoformat()}",
        "source":"BASE","priority":0,"decision_dt":planned,"trigger_dt":planned,
        "planned_entry_dt":planned,"direction":"LONG","direction_num":1,
        "reference_price":float(row.entry_price),"atr_entry":float("nan"),
        "tp_atr":float("nan"),"sl_atr":float("nan"),
        "tp_usd":float(row.tp_usd),"sl_usd":float(row.sl_usd),
        "max_holding_minutes":int(row.horizon_m15)*15,
        "candidate_contract":str(row.get("candidate_label","BASE_V3")),
        "status":"INTENT"
    }])
