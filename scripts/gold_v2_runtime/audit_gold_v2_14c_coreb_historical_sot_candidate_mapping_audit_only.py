#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="14C_COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_AUDIT_ONLY"
OUT="gold_v2_14c_coreb_historical_sot_candidate_mapping_audit_only"
REPORT="GOLD_V2_14C_COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_AUDIT_ONLY_REPORT.md"
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
def rd(p): return pd.read_csv(lp(p))
def rj(p):
    with open(lp(p),"r",encoding="utf-8") as f: return json.load(f)
def wt(p,s):
    os.makedirs(lp(Path(p).parent),exist_ok=True)
    with open(lp(p),"w",encoding="utf-8",newline="") as f: f.write(s)
def wc(d,p): d.to_csv(lp(p),index=False,encoding="utf-8-sig")
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
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    bdir=fx()/"gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only"
    sp=bdir/"gold_v2_14b_coreb_cluster_source_read_and_replay_summary.json"
    targetp=bdir/"gold_v2_14b_coreb_source_top_ledger_target_rows.csv"
    rulesp=bdir/"gold_v2_14b_coreb_source_rule_rows.csv"
    inputs=[sp,targetp,rulesp]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_14c_input_audit.csv")
    if not all(ex(p) for p in inputs):
        status="COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_MISSING_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    sj=rj(sp); target=rd(targetp); rules=rd(rulesp)
    mapping={
        "schema_version":"gold_v2_coreb_historical_sot_mapping.v1",
        "created_utc":now,
        "status":"COREB_HISTORICAL_SOT_ONLY_LIVE_BLOCKED",
        "scope":"COREB_RR125_BUY_CONFLUENCE_HISTORICAL_ONLY",
        "source":"rr125_top_ledgers.csv",
        "policy":"RR125_from_RR1_rules",
        "filter":"same_count>=15",
        "direction":"BUY_ONLY",
        "target_rows":int(len(target)),
        "source_rule_rows":int(len(rules)),
        "live_use_allowed":False,
        "historical_sot_allowed":True,
        "requires_for_live":["original clustering algorithm", "row-level cluster membership ledger", "same_count replay parity"],
        "source_rule_columns":[c for c in rules.columns],
        "safety":{"coreb_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT},
    }
    wj(out/"gold_v2_14c_coreb_historical_sot_candidate_mapping.json",mapping)
    checks=pd.DataFrame([
        ["14C-C001","14B status",sj.get("status"),"COREB_SOURCE_TOP_LEDGER_READABLE_BUT_LIVE_REPLAY_BLOCKED_AUDIT_ONLY"],
        ["14C-C002","target rows",len(target),125],
        ["14C-C003","source rule rows",len(rules),12],
        ["14C-C004","historical SOT allowed",sj.get("coreb_historical_sot_allowed"),True],
        ["14C-C005","CoreB live allowed",sj.get("coreb_live_evaluator_allowed"),False],
        ["14C-C006","final signal allowed",sj.get("final_signal_allowed"),False],
        ["14C-C007","mapping live_use_allowed",mapping.get("live_use_allowed"),False],
    ],columns=["check_id","check","observed","expected"])
    checks["status"]=checks.apply(lambda r:"PASS" if r.observed==r.expected else "STOP",axis=1); wc(checks,out/"gold_v2_14c_mapping_checks.csv")
    ok=bool((checks.status=="PASS").all())
    status="COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_BUILT_AUDIT_ONLY_LIVE_BLOCKED" if ok else "COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_BLOCKED_AUDIT_ONLY"
    dec=pd.DataFrame([
        ["14C-D001","historical SOT mapping built",ok,True,"PASS" if ok else "STOP"],
        ["14C-D002","CoreB live enabled",False,False,"PASS_BLOCKED_AS_EXPECTED"],
        ["14C-D003","next","14D_COREB_ORIGINAL_CLUSTERING_CANDIDATE_REVIEW_AUDIT_ONLY" if ok else "STOP","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_14c_decision_matrix.csv")
    block=pd.DataFrame([
        ["14C-B004","COREB_LIVE_REPLAY","HARD","OPEN","CoreB live evaluator","Need original clustering algorithm or membership ledger before live CoreB."],
        ["14C-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_14c_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"target_rows":int(len(target)),"source_rule_rows":int(len(rules)),"historical_sot_allowed":True,"coreb_live_evaluator_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"14D_COREB_ORIGINAL_CLUSTERING_CANDIDATE_REVIEW_AUDIT_ONLY" if ok else "STOP"}
    wj(out/"gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 14C CoreB historical SOT candidate mapping audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Mapping checks",md(checks),"","## Decision",md(dec),"","## Blockers",md(block),"","CoreB is historical-only. Live evaluator and final signal remain disabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
