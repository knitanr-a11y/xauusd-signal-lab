from __future__ import annotations
import json,time
from pathlib import Path
import numpy as np
import pandas as pd
from gold_v3_289_artifacts import validate_model_bundle
from gold_v3_289_feature_core import EXTERNAL_FILES,GOLD_FILES,read_candles
from gold_v3_289_candidates import model_dir
from gold_v3_290_io import require_columns

AUTH="USER_APPROVED_SAFE_PORTFOLIO_LIVE_SIGNAL_2026_06_23"
TARGETS={2024:(242,1.645,279.45,28.94),2025:(229,1.941,600.16,42.92),2026:(102,2.843,965.60,66.06)}

def metrics(frame):
    values=pd.to_numeric(frame.pnl,errors="coerce").dropna().to_numpy(float)
    gp=values[values>0].sum(); gl=-values[values<0].sum(); pf=gp/gl if gl>0 else np.inf
    curve=np.cumsum(values); peak=np.maximum.accumulate(np.r_[0.0,curve])
    dd=float((peak[1:]-curve).max()) if len(curve) else 0.0
    return len(values),float(pf),float(values.sum()),dd

def historical_parity(path: Path):
    data=pd.read_csv(path,encoding="utf-8-sig")
    require_columns(data,{"entry_dt","pnl"},"historical safe portfolio ledger")
    if "portfolio" in data: data=data[data.portfolio.astype(str).eq("PLUS_STRICT_SAFE")]
    data["entry_dt"]=pd.to_datetime(data.entry_dt,errors="coerce")
    rows=[]; passed=True
    for year,target in TARGETS.items():
        observed=metrics(data[data.entry_dt.dt.year.eq(year)].sort_values("entry_dt"))
        ok=(observed[0]==target[0] and abs(observed[1]-target[1])<=0.001 and abs(observed[2]-target[2])<=0.02 and abs(observed[3]-target[3])<=0.02)
        passed &= ok; rows.append({"year":year,"passed":ok,"observed_n":observed[0],"observed_pf":observed[1],"observed_sum":observed[2],"observed_dd":observed[3],"expected_n":target[0],"expected_pf":target[1],"expected_sum":target[2],"expected_dd":target[3]})
    return passed,rows

def check_readiness(candle_dir: Path,bootstrap_path: Path,authorization: str,max_file_age_seconds=180):
    checks=[]; blockers=[]
    for tf,name in GOLD_FILES.items():
        path=candle_dir/name
        try:
            data=read_candles(path,4,timeframe=tf,require_spread=True)
            age=max(0.0,time.time()-path.stat().st_mtime); ok=age<=max_file_age_seconds
            checks.append({"check":f"{tf}_closed_csv","passed":ok,"latest":str(data.time.max()),"file_age_seconds":age})
            if not ok: blockers.append(f"STALE_{name}")
        except Exception as exc:
            checks.append({"check":f"{tf}_closed_csv","passed":False,"detail":repr(exc)}); blockers.append(f"INVALID_{name}")
    for key,name in EXTERNAL_FILES.items():
        try: read_candles(candle_dir/name,4,timeframe="M15",require_spread=False); checks.append({"check":key,"passed":True})
        except Exception as exc: checks.append({"check":key,"passed":False,"detail":repr(exc)}); blockers.append(f"INVALID_{name}")
    try: validate_model_bundle(model_dir()); checks.append({"check":"stage289_model_bundle","passed":True})
    except Exception as exc: checks.append({"check":"stage289_model_bundle","passed":False,"detail":repr(exc)}); blockers.append("MODEL_BUNDLE_NOT_PASS")
    try:
        parity,rows=historical_parity(bootstrap_path); checks.extend({"check":f"historical_parity_{r['year']}",**r} for r in rows)
        if not parity: blockers.append("HISTORICAL_SAFE_PORTFOLIO_PARITY_FAILED")
    except Exception as exc: checks.append({"check":"historical_parity","passed":False,"detail":repr(exc)}); blockers.append("HISTORICAL_SAFE_PORTFOLIO_LEDGER_INVALID")
    base_summary=candle_dir/"FX_OUTPUTS"/"gold_v3"/"70_live_csv_signal_decision_preview_audit_only"/"gold_v3_70_live_csv_signal_decision_preview_summary.json"
    try:
        base=json.loads(base_summary.read_text(encoding="utf-8")); ok=base.get("status")=="GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_READY_AUDIT_ONLY"; checks.append({"check":"base_stage70_ready","passed":ok,"status":base.get("status")})
        if not ok: blockers.append("BASE_STAGE70_NOT_READY")
    except Exception as exc: checks.append({"check":"base_stage70_ready","passed":False,"detail":repr(exc)}); blockers.append("BASE_STAGE70_NOT_READY")
    auth_ok=authorization==AUTH; checks.append({"check":"user_authorization","passed":auth_ok})
    if not auth_ok: blockers.append("AUTHORIZATION_TOKEN_MISMATCH")
    return {"status":"PASS" if not blockers else "BLOCKED","live_signal_ready":not blockers,"blockers":blockers,"checks":checks}
