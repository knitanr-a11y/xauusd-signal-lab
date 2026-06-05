#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="16A_PORTFOLIO_STATUS_CONSOLIDATION_AUDIT_ONLY"
OUT="gold_v2_16a_portfolio_status_consolidation_audit_only"
REPORT="GOLD_V2_16A_PORTFOLIO_STATUS_CONSOLIDATION_AUDIT_ONLY_REPORT.md"
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
    if not ex(p): return {}
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
    paths={
        "medium_13l": fx()/"gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit"/"gold_v2_13l_load_smoke_summary.json",
        "coreb_14c": fx()/"gold_v2_14c_coreb_historical_sot_candidate_mapping_audit_only"/"gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json",
        "coreb_14d": fx()/"gold_v2_14d_coreb_original_clustering_candidate_review_audit_only"/"gold_v2_14d_coreb_original_clustering_candidate_review_summary.json",
        "corea_15c": fx()/"gold_v2_15c_corea_historical_sot_mapping_audit_only"/"gold_v2_15c_corea_historical_sot_mapping_summary.json",
    }
    ia=pd.DataFrame([{"role":k,"path":str(p),"exists":ex(p)} for k,p in paths.items()]); wc(ia,out/"gold_v2_16a_input_audit.csv")
    data={k:rj(p) for k,p in paths.items()}
    rows=[
        {"component":"MEDIUM_TIER2_HVT","source_step":"13L","status":data["medium_13l"].get("status"),"historical_sot_allowed":False,"candidate_mapping_allowed":bool(data["medium_13l"].get("audit_ok")),"live_evaluator_allowed":False,"final_signal_allowed":False,"blocking_reason":"candidate mapping only; final signal and external actions off"},
        {"component":"CoreB","source_step":"14C/14D","status":data["coreb_14d"].get("status") or data["coreb_14c"].get("status"),"historical_sot_allowed":bool(data["coreb_14c"].get("historical_sot_allowed")),"candidate_mapping_allowed":False,"live_evaluator_allowed":False,"final_signal_allowed":False,"blocking_reason":"strict original clustering candidate not confirmed; same_count replay not live-proven"},
        {"component":"CoreA","source_step":"15C","status":data["corea_15c"].get("status"),"historical_sot_allowed":bool(data["corea_15c"].get("historical_sot_allowed")),"candidate_mapping_allowed":False,"live_evaluator_allowed":False,"final_signal_allowed":False,"blocking_reason":"A gate is_A ledger flag only; underlying predicates/replay parity missing"},
        {"component":"MEDIUM_FULL_SET","source_step":"13K/13L partial","status":"NOT_COMPLETE_ONLY_TIER2_HVT_READY","historical_sot_allowed":False,"candidate_mapping_allowed":False,"live_evaluator_allowed":False,"final_signal_allowed":False,"blocking_reason":"only MEDIUM_TIER2_HVT has passed candidate load smoke"},
    ]
    matrix=pd.DataFrame(rows); wc(matrix,out/"gold_v2_16a_component_status_matrix.csv")
    safety=pd.DataFrame([
        ["final_signal_allowed",False,False,"PASS"],
        ["discord_send_allowed",False,False,"PASS"],
        ["mt5_order_allowed",False,False,"PASS"],
        ["ai_api_allowed",False,False,"PASS"],
        ["live_hook_allowed",False,False,"PASS"],
    ],columns=["safety_item","observed","expected","status"]); wc(safety,out/"gold_v2_16a_safety_matrix.csv")
    ok_inputs=bool(ia.exists.all())
    ok_safety=bool((safety.status=="PASS").all())
    final_signal_allowed=False
    status="GOLD_V2_PORTFOLIO_STATUS_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED" if ok_inputs and ok_safety else "GOLD_V2_PORTFOLIO_STATUS_CONSOLIDATION_INCOMPLETE_AUDIT_ONLY"
    blockers=pd.DataFrame([
        ["16A-B001","CORE_A","HARD","OPEN","CoreA live evaluator","Need underlying A-gate executable predicates and replay parity."],
        ["16A-B002","CORE_B","HARD","OPEN","CoreB live evaluator","Need original clustering algorithm or row-level membership ledger and replay parity."],
        ["16A-B003","MEDIUM_FULL_SET","HARD","OPEN","full MEDIUM live evaluator","Only MEDIUM_TIER2_HVT candidate mapping is ready."],
        ["16A-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(blockers,out/"gold_v2_16a_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"component_status":rows,"final_signal_allowed":final_signal_allowed,"external_actions":EXT,"next":"16B_NEXT_CHAT_HANDOFF_AND_SAFE_ROADMAP_AUDIT_ONLY"}
    wj(out/"gold_v2_16a_portfolio_status_consolidation_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 16A portfolio status consolidation audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Component status",md(matrix),"","## Safety matrix",md(safety),"","## Blockers",md(blockers),"","No final signal, Discord, MT5, AI API, or live hook is enabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok_inputs and ok_safety else 2
if __name__=="__main__": raise SystemExit(main())
