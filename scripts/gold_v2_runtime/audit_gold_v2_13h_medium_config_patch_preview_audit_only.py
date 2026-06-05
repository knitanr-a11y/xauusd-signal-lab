#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13H_MEDIUM_CONFIG_PATCH_PREVIEW_AUDIT_ONLY"
OUT="gold_v2_13h_medium_config_patch_preview_audit_only"
REPORT="GOLD_V2_13H_MEDIUM_CONFIG_PATCH_PREVIEW_AUDIT_ONLY_REPORT.md"
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
    g=fx()/"gold_v2_13g_medium_live_evaluator_replay_audit_only"/"gold_v2_13g_medium_live_evaluator_replay_summary.json"
    c=fx()/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"/"gold_v2_13d3_tier2_reconciled_rule_candidate.json"
    m=rr()/"configs"/"gold_v2"/"live_evaluator_mapping_medium_20260603.json"
    f=rr()/"configs"/"gold_v2"/"frozen_medium_rules_20260603.json"
    inputs=[g,c,m,f]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_13h_input_audit.csv")
    if not ex(g) or not ex(c):
        status="MISSING_13H_REQUIRED_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_13h_medium_config_patch_preview_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    gj=rj(g); cj=rj(c); cond=cj.get("reconciled_conditions",{})
    g_ok=gj.get("status")=="MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_PROVEN_AUDIT_ONLY"
    cond_ok=all(k in cond for k in ["trend_eff96_max","ret96_max","tr_mean_32_min"])
    patch={"patch_preview_only":True,"do_not_apply_automatically":True,"target_component":"MEDIUM_TIER2_HVT","source_step":"13H","requires_prior_status":"MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_PROVEN_AUDIT_ONLY","rule":{"component":"TIER2_HVT","feature_source":"coreb_refined_rule_ledgers.csv","conditions":cond,"expected_replay":{"source_rows":31,"selected_rows":31,"missing_source_rows":0,"extra_selected_rows":0}},"safety":{"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT}}
    wj(out/"gold_v2_13h_patch_preview.json",patch)
    card=pd.DataFrame([{"rule_id":"MEDIUM_TIER2_HVT_RECONCILED_13D3","component":"TIER2_HVT","trend_eff96_max":cond.get("trend_eff96_max"),"ret96_max":cond.get("ret96_max"),"tr_mean_32_min":cond.get("tr_mean_32_min"),"feature_source":"coreb_refined_rule_ledgers.csv","apply_now":False}]); wc(card,out/"gold_v2_13h_rule_card.csv")
    status="MEDIUM_CONFIG_PATCH_PREVIEW_BUILT_AUDIT_ONLY" if g_ok and cond_ok else "MEDIUM_CONFIG_PATCH_PREVIEW_BLOCKED_AUDIT_ONLY"
    block=pd.DataFrame([["13H-B004","DRY_RUN","HARD","OPEN","patch dry-run","13I must run patch preview through live evaluator dry-run before applying."],["13H-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false and config is not modified."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13h_blockers.csv")
    dec=pd.DataFrame([["13H-C001","13G replay proven",g_ok,True,"PASS" if g_ok else "STOP"],["13H-C002","candidate conditions present",cond_ok,True,"PASS" if cond_ok else "STOP"],["13H-C003","production config modified",False,False,"PASS_NOT_MODIFIED"],["13H-C004","next","13I_PATCH_PREVIEW_LIVE_DRY_RUN_AUDIT_ONLY" if g_ok and cond_ok else "STOP","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_13h_decision_matrix.csv")
    wj(out/"gold_v2_13h_medium_config_patch_preview_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"g_ok":g_ok,"conditions_present":cond_ok,"patch_preview_created":True,"production_config_modified":False,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wt(out/REPORT,"\n".join(["# GOLD V2 13H MEDIUM config patch preview audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Rule card",md(card),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false. Production config is not modified."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"patch_preview_created":True,"production_config_modified":False,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if g_ok and cond_ok else 2
if __name__=="__main__": raise SystemExit(main())
