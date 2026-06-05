#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13F_MEDIUM_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY"
OUT="gold_v2_13f_medium_live_eligibility_matrix_audit_only"
REPORT="GOLD_V2_13F_MEDIUM_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY_REPORT.md"
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
def md(d):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    d3=fx()/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json"
    e5=fx()/"gold_v2_13e5_read_replay_feature_source_chain_audit_only"/"gold_v2_13e5_feature_source_chain_summary.json"
    cand=fx()/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"/"gold_v2_13d3_tier2_reconciled_rule_candidate.json"
    frozen=rr()/"configs"/"gold_v2"/"frozen_medium_rules_20260603.json"
    mapping=rr()/"configs"/"gold_v2"/"live_evaluator_mapping_medium_20260603.json"
    inputs=[d3,e5,cand,frozen,mapping]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_13f_input_audit.csv")
    d3j=rj(d3) if ex(d3) else {}; e5j=rj(e5) if ex(e5) else {}; cj=rj(cand) if ex(cand) else {}
    d3_ok=d3j.get("status")=="TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY"
    e5_ok=e5j.get("status")=="FEATURE_SOURCE_CHAIN_FIXED_AUDIT_ONLY" and e5j.get("join_ok") is True and e5j.get("code_ok") is True
    ext_false=all(v is False for v in cj.get("external_actions",EXT).values()) and all(v is False for v in e5j.get("external_actions",EXT).values())
    rows=[
        ["13F-E001","13D3 TIER2_HVT reconciled replay",d3_ok,"PASS" if d3_ok else "BLOCK","Required before any live mapping."],
        ["13F-E002","13E5 feature source chain",e5_ok,"PASS" if e5_ok else "BLOCK","Feature values must be traced to refined ledgers."],
        ["13F-E003","External actions disabled",ext_false,"PASS" if ext_false else "BLOCK","Safety must remain false."],
        ["13F-E004","Candidate still audit-only",cj.get("audit_only") is True,"PASS" if cj.get("audit_only") is True else "BLOCK","Candidate is not production config."],
        ["13F-E005","Frozen medium config exists",ex(frozen),"INFO" if ex(frozen) else "BLOCK","Existing config is inspected only, not updated."],
        ["13F-E006","Live mapping config exists",ex(mapping),"INFO" if ex(mapping) else "BLOCK","Existing mapping is inspected only, not updated."],
        ["13F-E007","Live evaluator replay proven",False,"BLOCK","13G must implement replay against live evaluator."],
    ]
    mat=pd.DataFrame(rows,columns=["check_id","check","observed","status","note"]); wc(mat,out/"gold_v2_13f_eligibility_matrix.csv")
    status="MEDIUM_LIVE_ELIGIBILITY_MATRIX_BUILT_AUDIT_ONLY_BLOCKED_PENDING_13G" if d3_ok and e5_ok and ext_false else "MEDIUM_LIVE_ELIGIBILITY_MATRIX_BLOCKED_AUDIT_ONLY"
    block=pd.DataFrame([["13F-B004","LIVE_REPLAY","HARD","OPEN","live evaluator replay","13G must prove live evaluator reproduces frozen TIER2_HVT source rows."],["13F-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13f_blockers.csv")
    dec=pd.DataFrame([["13F-C001","D3 and E5 prerequisites",d3_ok and e5_ok,True,"PASS" if d3_ok and e5_ok else "STOP"],["13F-C002","live permission",False,False,"PASS_BLOCKED_AS_EXPECTED"],["13F-C003","next","13G_MEDIUM_LIVE_EVALUATOR_REPLAY_AUDIT_ONLY","13G","INFO"]],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_13f_decision_matrix.csv")
    wj(out/"gold_v2_13f_medium_live_eligibility_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"d3_ok":d3_ok,"e5_ok":e5_ok,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wt(out/REPORT,"\n".join(["# GOLD V2 13F MEDIUM live eligibility matrix audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Eligibility matrix",md(mat),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"audit_only":True,"medium_live_evaluator_allowed":False,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
