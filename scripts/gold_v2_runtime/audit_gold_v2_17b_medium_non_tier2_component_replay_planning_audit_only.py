#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="17B_MEDIUM_NON_TIER2_COMPONENT_REPLAY_PLANNING_AUDIT_ONLY"
OUT="gold_v2_17b_medium_non_tier2_component_replay_planning_audit_only"
REPORT="GOLD_V2_17B_MEDIUM_NON_TIER2_COMPONENT_REPLAY_PLANNING_AUDIT_ONLY_REPORT.md"
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
def md(d,limit=100):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    bdir=fx()/"gold_v2_17a_medium_full_set_source_arbitration_audit_only"
    sp=bdir/"gold_v2_17a_medium_full_set_source_arbitration_summary.json"
    arbp=bdir/"gold_v2_17a_medium_arbitration_matrix.csv"
    invp=bdir/"gold_v2_17a_medium_component_inventory.csv"
    inputs=[sp,arbp,invp]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_17b_input_audit.csv")
    if not all(ex(p) for p in inputs):
        status="MEDIUM_NON_TIER2_COMPONENT_REPLAY_PLAN_MISSING_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_17b_medium_non_tier2_component_replay_planning_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    sj=rj(sp); arb=rd(arbp); inv=rd(invp)
    targets=arb[arb["arbitration_status"].astype(str).eq("NEEDS_REPLAY_PARITY")].copy()
    order=[]
    for comp in ["RANGE96_REFINED","VOL_TRMEAN32_REFINED"]:
        row=targets[targets.component.astype(str).eq(comp)]
        if row.empty: continue
        r=row.iloc[0].to_dict()
        order.append({"planned_step":"17C" if comp=="RANGE96_REFINED" else "17D","component":comp,"rule_ledger_rows":int(r.get("rule_ledger_rows",0)),"combined_ledger_rows":int(r.get("combined_ledger_rows",0)),"planning_status":"PLAN_READY","required_audits":"source_rows_reconciliation -> candidate_rule_freeze -> load_smoke -> dry_run_gate","stop_condition":"any mismatch, missing source, or safety flag not false","live_evaluator_allowed":False,"final_signal_allowed":False})
    plan=pd.DataFrame(order); wc(plan,out/"gold_v2_17b_replay_planning_matrix.csv")
    exec_order=plan[["planned_step","component","planning_status","required_audits","stop_condition"]].copy() if not plan.empty else pd.DataFrame(columns=["planned_step","component","planning_status","required_audits","stop_condition"])
    wc(exec_order,out/"gold_v2_17b_execution_order.csv")
    blockers=pd.DataFrame([
        ["17B-B001","RANGE96_REFINED","HARD","OPEN","MEDIUM full set","Need 17C reconciliation and load-smoke chain before inclusion."],
        ["17B-B002","VOL_TRMEAN32_REFINED","HARD","OPEN","MEDIUM full set","Need 17D reconciliation and load-smoke chain before inclusion."],
        ["17B-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(blockers,out/"gold_v2_17b_blockers.csv")
    status="MEDIUM_NON_TIER2_COMPONENT_REPLAY_PLAN_BUILT_AUDIT_ONLY"
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"planned_components":plan.component.tolist() if not plan.empty else [],"medium_full_set_live_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"17C_RANGE96_REFINED_RECONCILIATION_AUDIT_ONLY"}
    wj(out/"gold_v2_17b_medium_non_tier2_component_replay_planning_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 17B MEDIUM non-TIER2 component replay planning audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Source arbitration input",md(arb),"","## Replay planning matrix",md(plan),"","## Execution order",md(exec_order),"","## Blockers",md(blockers),"","No final signal, Discord, MT5, AI API, or live hook is enabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
