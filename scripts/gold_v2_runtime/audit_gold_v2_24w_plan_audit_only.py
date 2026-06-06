#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY"
IN_DIR = "gold_v2_24v_source_recovery_readiness_final_decision_routing_audit_only"
OUT_DIR = "gold_v2_24w_source_recovery_execution_planning_audit_only"
EXPECTED_STATUS = "SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_ROUTE = "ROUTE_APPROVE_TO_EXECUTION_PLANNING_AUDIT_ONLY"
EXPECTED_NEXT = "24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24W_STOP_SOURCE_RECOVERY_EXECUTION_PLANNING_INPUTS_OR_SAFETY"
REQ = {"report":"GOLD_V2_24V_SOURCE_RECOVERY_READINESS_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md","summary":"gold_v2_24v_source_recovery_readiness_final_decision_routing_summary.json","input_audit":"gold_v2_24v_input_audit.csv","route":"gold_v2_24v_decision_route.csv","checks":"gold_v2_24v_integrated_checks.csv","gates":"gold_v2_24v_required_next_gates.csv","safety":"gold_v2_24v_safety_matrix.csv"}
BLOCKED = ["SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","SOURCE_MUTATION","LIVE","FINAL_SIGNAL","DISCORD_SEND","MT5_ORDER","AI_API","LIVE_HOOK"]

def root()->Path: return Path(__file__).resolve().parents[2]
def fx()->Path:
    r=root(); return (r.parents[1] if len(r.parents)>=2 else r.parent)/"FX_OUTPUTS"
def lp(p:Path)->Path:
    p=p if p.is_absolute() else p.resolve()
    if os.name!="nt": return p
    s=str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def yes(v:Any)->bool:
    if isinstance(v,bool): return v
    if v is None: return False
    return str(v).strip().lower() in {"1","true","yes","pass","allowed","ready"}
def no(v:Any)->bool:
    if isinstance(v,bool): return not v
    if v is None: return True
    return str(v).strip().lower() in {"","0","false","no","blocked","none","null"}
def rj(p:Path)->dict[str,Any]: return json.loads(lp(p).read_text(encoding="utf-8"))
def rc(p:Path)->pd.DataFrame:
    for e in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(p),encoding=e,keep_default_na=False)
        except Exception: pass
    raise RuntimeError(str(p))
def wc(p:Path,df:pd.DataFrame)->None:
    lp(p.parent).mkdir(parents=True,exist_ok=True); df.to_csv(lp(p),index=False,encoding="utf-8-sig")
def wj(p:Path,o:dict[str,Any])->None:
    lp(p.parent).mkdir(parents=True,exist_ok=True); lp(p).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
def wt(p:Path,s:str)->None:
    lp(p.parent).mkdir(parents=True,exist_ok=True); lp(p).write_text(s,encoding="utf-8")
def stops(df:pd.DataFrame)->int:
    return 0 if df.empty or "status" not in df.columns else int((df["status"].astype(str).str.upper()=="STOP").sum())
def md(df:pd.DataFrame)->str:
    if df.empty: return "_No rows._"
    cols=list(df.columns); lines=["| "+" | ".join(cols)+" |","| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in df.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in cols)+" |")
    return "\n".join(lines)
def chk(i:str,n:str,o:Any,e:Any,ok:bool)->dict[str,Any]: return {"check_id":i,"check":n,"observed":o,"expected":e,"status":"PASS" if ok else "STOP"}
def alw(g:pd.DataFrame,col:str)->list[str]:
    if g.empty or "next_step" not in g.columns or col not in g.columns: return []
    return g.loc[g[col].map(yes),"next_step"].astype(str).tolist()
def plan()->pd.DataFrame:
    return pd.DataFrame([
        {"plan_id":"24W-P001","plan_item":"freeze_audit_inputs","audit_only":True,"required":True,"description":"List exact 24V and upstream audit artifacts before later review."},
        {"plan_id":"24W-P002","plan_item":"define_candidate_recovery_scope","audit_only":True,"required":True,"description":"Describe scope for later planning review without modifying source artifacts."},
        {"plan_id":"24W-P003","plan_item":"define_pre_execution_stop_conditions","audit_only":True,"required":True,"description":"Specify conditions that keep later execution blocked."},
        {"plan_id":"24W-P004","plan_item":"define_no_live_boundary","audit_only":True,"required":True,"description":"Keep live, final signal, Discord, MT5, AI API, and live hook disabled."},
        {"plan_id":"24W-P005","plan_item":"require_24x_plan_review","audit_only":True,"required":True,"description":"Require 24X review before any further decision intake."},
    ])
def evidence()->pd.DataFrame:
    return pd.DataFrame([{"evidence_role":x,"required_for_24x":True,"status":"PENDING_REVIEW"} for x in ["24T options","24U validated decision","24V route","24W plan","24W boundary matrix","old GOLD/DISC8 quarantine record"]])
def boundary()->pd.DataFrame:
    return pd.DataFrame([{"boundary_item":x,"allowed_after_24w_plan":False,"reason":"24W is planning-only; still blocked","status":"PASS"} for x in BLOCKED])
def main()->int:
    src,out=fx()/IN_DIR,fx()/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True)
    paths={k:src/v for k,v in REQ.items()}
    ia=pd.DataFrame([{"role":k,"path":str(p),"required":True,"exists":lp(p).exists()} for k,p in paths.items()]); wc(out/"gold_v2_24w_input_audit.csv",ia)
    ok_inputs=bool(ia["exists"].map(yes).all())
    rows=[chk("24W-C000","required 24V files exist",ok_inputs,True,ok_inputs)]
    s24v={}
    if ok_inputs:
        s24v=rj(paths["summary"]); route=rc(paths["route"]); c=rc(paths["checks"]); g=rc(paths["gates"]); sf=rc(paths["safety"])
        rows += [chk("24W-C001","24V status routed",s24v.get("status"),EXPECTED_STATUS,s24v.get("status")==EXPECTED_STATUS),chk("24W-C002","24V route expected",s24v.get("route_id"),EXPECTED_ROUTE,s24v.get("route_id")==EXPECTED_ROUTE),chk("24W-C003","24V next 24W",s24v.get("routed_next_audit_step"),EXPECTED_NEXT,s24v.get("routed_next_audit_step")==EXPECTED_NEXT),chk("24W-C004","24V route row passed",route.iloc[0].get("status","") if not route.empty else "missing","ROUTED_TO_NEXT_AUDIT_ONLY",(not route.empty and str(route.iloc[0].get("status",""))=="ROUTED_TO_NEXT_AUDIT_ONLY")),chk("24W-C005","24V stop rows zero",stops(c)+stops(sf)+stops(route),0,stops(c)+stops(sf)+stops(route)==0),chk("24W-C006","24V next only 24W",alw(g,"allowed_after_24v_success"),[EXPECTED_NEXT],alw(g,"allowed_after_24v_success")==[EXPECTED_NEXT]),chk("24W-C007","24V did not allow now",s24v.get("source_recovery_execution_allowed_now"),False,no(s24v.get("source_recovery_execution_allowed_now"))),chk("24W-C008","24V did not allow mutation",s24v.get("source_mutation_allowed"),False,no(s24v.get("source_mutation_allowed")))]
    checks=pd.DataFrame(rows); pl=plan(); ev=evidence(); bd=boundary()
    safety=pd.DataFrame([{"safety_item":x,"observed":o,"expected":e,"status":"PASS"} for x,o,e in [("audit_only",True,True),("planning_only",True,True),("source_recovery_execution_allowed_now",False,False),("source_mutation_allowed",False,False),("source_identity_finalization_allowed_now",False,False),("external_actions_allowed",False,False),("old_gold_disc8_quarantined",True,True)]])
    total=stops(checks)+stops(pl)+stops(ev)+stops(bd)+stops(safety); ok=ok_inputs and total==0
    gates=pd.DataFrame([{"next_step":"24X_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_AUDIT_ONLY","allowed_after_24w_success":bool(ok),"reason":"plan ready" if ok else "24W not passed"}]+[{"next_step":x,"allowed_after_24w_success":False,"reason":"blocked"} for x in BLOCKED])
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS if ok else STOP_STATUS,"audit_only":True,"planning_only":True,"upstream_24v_status":s24v.get("status","UNKNOWN"),"upstream_route_id":s24v.get("route_id",""),"source_recovery_execution_allowed_now":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"source_mutation_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"old_gold_disc8_quarantined":True,"still_blocked_after_24w":BLOCKED,"total_stop_rows":int(total),"required_next_allowed":alw(gates,"allowed_after_24w_success"),"next_recommended_step":"24X_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_AUDIT_ONLY" if ok else "STOP_REVIEW_24W_INPUTS","do_not_execute_source_recovery_in_24w":True}
    wc(out/"gold_v2_24w_execution_plan.csv",pl); wc(out/"gold_v2_24w_required_evidence_manifest.csv",ev); wc(out/"gold_v2_24w_execution_boundary_matrix.csv",bd); wc(out/"gold_v2_24w_integrated_checks.csv",checks); wc(out/"gold_v2_24w_required_next_gates.csv",gates); wc(out/"gold_v2_24w_safety_matrix.csv",safety); wj(out/"gold_v2_24w_source_recovery_execution_planning_summary.json",summary)
    report="\n".join(["# GOLD V2 24W source recovery execution planning audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{summary['status']}`","","## Boundary","","24W writes a planning package only. It does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.","","## Outcome","",f"- Total STOP rows: `{summary['total_stop_rows']}`",f"- Upstream route id: `{summary['upstream_route_id']}`",f"- Next recommended step: `{summary['next_recommended_step']}`","","## Input audit","",md(ia),"","## Execution plan","",md(pl),"","## Required evidence manifest","",md(ev),"","## Execution boundary matrix","",md(bd),"","## Integrated checks","",md(checks),"","## Required next gates","",md(gates),"","## Safety matrix","",md(safety),"","## Explicit non-actions","","- source recovery run: `false`","- source mutation: `false`","- source identity finalization: `false`","- live/final signal/external actions: `false`"])
    wt(out/"GOLD_V2_24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY_REPORT.md",report); print(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
