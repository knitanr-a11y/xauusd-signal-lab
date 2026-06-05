#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="15C_COREA_HISTORICAL_SOT_MAPPING_AUDIT_ONLY"
OUT="gold_v2_15c_corea_historical_sot_mapping_audit_only"
REPORT="GOLD_V2_15C_COREA_HISTORICAL_SOT_MAPPING_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}

def rr(): return Path(__file__).resolve().parents[2]
def fr():
    r=rr(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx(): return fr()/"FX_OUTPUTS"
def lp(p):
    s=str(Path(p).resolve(strict=False))
    if os.name!="nt" or s.startswith("\\\\?\\"): return s
    return "\\\\?\\UNC\\"+s.lstrip("\\") if s.startswith("\\\\") else "\\\\?\\"+s
def ex(p): return os.path.exists(lp(p))
def od():
    p=fx()/OUT; os.makedirs(lp(p),exist_ok=True); return p
def wt(p,s):
    os.makedirs(lp(Path(p).parent),exist_ok=True)
    with open(lp(p),"w",encoding="utf-8",newline="") as f: f.write(s)
def wc(d,p): d.to_csv(lp(p),index=False,encoding="utf-8-sig")
def rd(p): return pd.read_csv(lp(p))
def rj(p):
    with open(lp(p),"r",encoding="utf-8") as f: return json.load(f)
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,float)):
        if math.isnan(float(x)): return None
        if math.isinf(float(x)): return "inf" if float(x)>0 else "-inf"
        return float(x)
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x
def wj(p,o): wt(p,json.dumps(clean(o),ensure_ascii=False,indent=2,allow_nan=False))
def md(d,limit=80):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    bdir=fx()/"gold_v2_15b_corea_a_gate_source_read_and_replay_audit_only"
    sp=bdir/"gold_v2_15b_corea_a_gate_read_replay_summary.json"
    countp=bdir/"gold_v2_15b_selected_signal_counts.csv"
    agatep=bdir/"gold_v2_15b_a_gate_inventory_rows.csv"
    unmapp=bdir/"gold_v2_15b_a_gate_unmapped_rows.csv"
    inputs=[sp,countp,agatep,unmapp]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_15c_input_audit.csv")
    if not all(ex(p) for p in inputs):
        status="COREA_HISTORICAL_SOT_MAPPING_MISSING_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_15c_corea_historical_sot_mapping_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    sj=rj(sp); counts=rd(countp); agate=rd(agatep); unmapped=rd(unmapp)
    mapping={
        "schema_version":"gold_v2_corea_historical_sot_mapping.v1",
        "created_utc":now,
        "status":"COREA_HISTORICAL_SOT_ONLY_LIVE_BLOCKED",
        "scope":"COREA_FOLD4_ABC_CAP_HISTORICAL_ONLY",
        "source":"gold_v2_13b_corea_selected_source_rows.csv",
        "policy":"fold4_rules + ABC gate + A_CAP5_BC_CAP3",
        "selected_source_rows":int(sj.get("selected_source_rows",0)),
        "a_selected_rows":int(sj.get("a_selected_rows",0)),
        "signal_counts":counts.to_dict(orient="records"),
        "a_gate_status":"LEDGER_FLAG_ONLY_NOT_LIVE_EXECUTABLE",
        "a_known_formula":sj.get("a_known_formula"),
        "live_use_allowed":False,
        "historical_sot_allowed":True,
        "requires_for_live":["underlying A-gate executable predicates", "A-gate replay parity", "B/C ordering after A rejection", "feature snapshot parity"],
        "safety":{"corea_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT},
    }
    wj(out/"gold_v2_15c_corea_historical_sot_mapping.json",mapping)
    checks=pd.DataFrame([
        ["15C-C001","15B status",sj.get("status"),"COREA_A_GATE_SOURCE_READABLE_BUT_LIVE_MAPPING_BLOCKED_AUDIT_ONLY"],
        ["15C-C002","selected source rows",sj.get("selected_source_rows"),325],
        ["15C-C003","A selected rows",sj.get("a_selected_rows"),173],
        ["15C-C004","A gate executable",sj.get("a_gate_executable"),False],
        ["15C-C005","CoreA live allowed",sj.get("corea_live_evaluator_allowed"),False],
        ["15C-C006","final signal allowed",sj.get("final_signal_allowed"),False],
        ["15C-C007","mapping live_use_allowed",mapping.get("live_use_allowed"),False],
    ],columns=["check_id","check","observed","expected"])
    checks["status"]=checks.apply(lambda r:"PASS" if r.observed==r.expected else "STOP",axis=1); wc(checks,out/"gold_v2_15c_mapping_checks.csv")
    ok=bool((checks.status=="PASS").all())
    status="COREA_HISTORICAL_SOT_MAPPING_BUILT_AUDIT_ONLY_LIVE_BLOCKED" if ok else "COREA_HISTORICAL_SOT_MAPPING_BLOCKED_AUDIT_ONLY"
    dec=pd.DataFrame([
        ["15C-D001","historical SOT mapping built",ok,True,"PASS" if ok else "STOP"],
        ["15C-D002","CoreA live enabled",False,False,"PASS_BLOCKED_AS_EXPECTED"],
        ["15C-D003","next","16A_PORTFOLIO_STATUS_CONSOLIDATION_AUDIT_ONLY" if ok else "STOP","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_15c_decision_matrix.csv")
    block=pd.DataFrame([
        ["15C-B001","COREA_A_GATE","HARD","OPEN","CoreA live evaluator","Need underlying A-gate executable predicates and replay parity before live CoreA."],
        ["15C-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_15c_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_source_rows":int(sj.get("selected_source_rows",0)),"a_selected_rows":int(sj.get("a_selected_rows",0)),"historical_sot_allowed":True,"corea_live_evaluator_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"16A_PORTFOLIO_STATUS_CONSOLIDATION_AUDIT_ONLY" if ok else "STOP"}
    wj(out/"gold_v2_15c_corea_historical_sot_mapping_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 15C CoreA historical SOT mapping audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Mapping checks",md(checks),"","## Signal counts",md(counts),"","## A gate inventory",md(agate),"","## A gate unmapped rows",md(unmapped),"","## Decision",md(dec),"","## Blockers",md(block),"","CoreA is historical-only. Live evaluator and final signal remain disabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
