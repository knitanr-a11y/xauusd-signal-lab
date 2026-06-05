#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13J_FINAL_APPROVAL_GATE_AUDIT_ONLY"
OUT="gold_v2_13j_final_approval_gate_audit_only"
REPORT="GOLD_V2_13J_FINAL_APPROVAL_GATE_AUDIT_ONLY_REPORT.md"
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
    g=fx()/"gold_v2_13g_medium_live_evaluator_replay_audit_only"/"gold_v2_13g_medium_live_evaluator_replay_summary.json"
    h=fx()/"gold_v2_13h_medium_config_patch_preview_audit_only"/"gold_v2_13h_medium_config_patch_preview_summary.json"
    i=fx()/"gold_v2_13i_patch_preview_live_dry_run_audit_only"/"gold_v2_13i_patch_preview_live_dry_run_summary.json"
    patch=fx()/"gold_v2_13h_medium_config_patch_preview_audit_only"/"gold_v2_13h_patch_preview.json"
    inputs=[d3,e5,g,h,i,patch]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_13j_input_audit.csv")
    if not ia.exists.all():
        status="FINAL_APPROVAL_GATE_BLOCKED_MISSING_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_13j_final_approval_gate_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    js={"d3":rj(d3),"e5":rj(e5),"g":rj(g),"h":rj(h),"i":rj(i),"patch":rj(patch)}
    checks=[
        ["13J-A001","13D3 reconciled rule frozen",js["d3"].get("status")=="TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY"],
        ["13J-A002","13E5 source chain fixed",js["e5"].get("status")=="FEATURE_SOURCE_CHAIN_FIXED_AUDIT_ONLY"],
        ["13J-A003","13G replay proven",js["g"].get("status")=="MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_PROVEN_AUDIT_ONLY"],
        ["13J-A004","13H patch preview built",js["h"].get("status")=="MEDIUM_CONFIG_PATCH_PREVIEW_BUILT_AUDIT_ONLY"],
        ["13J-A005","13I dry-run passed",js["i"].get("status")=="PATCH_PREVIEW_LIVE_DRY_RUN_PASSED_AUDIT_ONLY"],
        ["13J-A006","patch preview only",js["patch"].get("patch_preview_only") is True and js["patch"].get("do_not_apply_automatically") is True],
        ["13J-A007","production config not modified",js["h"].get("production_config_modified") is False and js["i"].get("production_config_modified") is False],
        ["13J-A008","external actions false",all(v is False for v in js["i"].get("external_actions",EXT).values())],
        ["13J-A009","explicit user approval present",False],
    ]
    mat=pd.DataFrame(checks,columns=["check_id","check","observed"]); mat["status"]=mat.apply(lambda r:"PASS" if r.observed else ("USER_APPROVAL_REQUIRED" if r.check_id=="13J-A009" else "STOP"),axis=1); wc(mat,out/"gold_v2_13j_approval_matrix.csv")
    prereq_ok=bool((mat[mat.check_id.ne("13J-A009")]["status"]=="PASS").all())
    status="FINAL_APPROVAL_GATE_READY_AUDIT_ONLY_USER_APPROVAL_REQUIRED" if prereq_ok else "FINAL_APPROVAL_GATE_BLOCKED_AUDIT_ONLY"
    block=pd.DataFrame([["13J-B001","USER_APPROVAL","HARD","OPEN","apply patch","Explicit user approval is required before any config update."],["13J-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false and config is not modified."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13j_blockers.csv")
    dec=pd.DataFrame([["13J-C001","all audit prerequisites",prereq_ok,True,"PASS" if prereq_ok else "STOP"],["13J-C002","user approval",False,True,"USER_APPROVAL_REQUIRED"],["13J-C003","production config modified",False,False,"PASS_NOT_MODIFIED"],["13J-C004","next","WAIT_FOR_EXPLICIT_USER_APPROVAL_TO_APPLY_PATCH","approval","INFO"]],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_13j_decision_matrix.csv")
    wj(out/"gold_v2_13j_final_approval_gate_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"all_audit_prerequisites_passed":prereq_ok,"user_approval_required":True,"user_approval_present":False,"production_config_modified":False,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wt(out/REPORT,"\n".join(["# GOLD V2 13J final approval gate audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Approval matrix",md(mat),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false. Production config is not modified."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"all_audit_prerequisites_passed":prereq_ok,"user_approval_required":True,"production_config_modified":False,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
