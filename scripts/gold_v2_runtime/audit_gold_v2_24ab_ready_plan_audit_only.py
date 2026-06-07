#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="24AB_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_AUDIT_ONLY"
IN_DIR="gold_v2_24aa_source_recovery_execution_final_decision_routing_audit_only"
OUT_DIR="gold_v2_24ab_source_recovery_pre_execution_readiness_plan_audit_only"
EXPECTED_STATUS="SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_ROUTE="ROUTE_APPROVE_TO_PRE_EXECUTION_READINESS_PLAN_AUDIT_ONLY"
EXPECTED_NEXT="24AB_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_AUDIT_ONLY"
PASS_STATUS="SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS="24AB_STOP_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_INPUTS_OR_SAFETY"
REQ={"report":"GOLD_V2_24AA_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md","summary":"gold_v2_24aa_source_recovery_execution_final_decision_routing_summary.json","input_audit":"gold_v2_24aa_input_audit.csv","route":"gold_v2_24aa_decision_route.csv","checks":"gold_v2_24aa_integrated_checks.csv","gates":"gold_v2_24aa_required_next_gates.csv","safety":"gold_v2_24aa_safety_matrix.csv"}
BLOCKED=["SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","SOURCE_MUTATION","LIVE","FINAL_SIGNAL","DISCORD_SEND","MT5_ORDER","AI_API","LIVE_HOOK"]

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
        {"plan_id":"24AB-P001","plan_item":"verify_24aa_route_inputs","audit_only":True,"required":True,"description":"Confirm validated 24Z decision and 24AA route before any later review."},
        {"plan_id":"24AB-P002","plan_item":"freeze_pre_execution_artifact_scope","audit_only":True,"required":True,"description":"List exact audit artifacts required before later pre-execution review."},
        {"plan_id":"24AB-P003","plan_item":"define_pre_execution_evidence_requirements","audit_only":True,"required":True,"description":"Require independent evidence manifest review before any later execution decision."},
        {"plan_id":"24AB-P004","plan_item":"define_hard_blocked_actions","audit_only":True,"required":True,"description":"Keep recovery, mutation, finalization, live, and external systems blocked."},
        {"plan_id":"24AB-P005","plan_item":"require_24ac_review","audit_only":True,"required":True,"description":"Require 24AC review before any later decision options."},
    ])
def evidence()->pd.DataFrame:
    return pd.DataFrame([{"evidence_role":x,"required_for_24ac":True,"status":"PENDING_REVIEW"} for x in ["24Z validated decision","24AA route","24AB pre-execution plan","24AB boundary matrix","24AB stop conditions","old GOLD/DISC8 quarantine record"]])
def boundary()->pd.DataFrame:
    return pd.DataFrame([{"boundary_item":x,"allowed_after_24ab_plan":False,"reason":"24AB is planning-only; still blocked","status":"PASS"} for x in BLOCKED])
def stopconds()->pd.DataFrame:
    return pd.DataFrame([{"stop_condition_id":f"24AB-S{i:03d}","stop_condition":txt,"status":"ACTIVE"} for i,txt in enumerate(["Any missing upstream 24AA artifact","Any 24AA or 24AB STOP row","Any source recovery execution flag true","Any source mutation flag true","Any source identity finalization flag true","Any live/external action flag true","Old GOLD/DISC8 quarantine not confirmed"],1)])
def main()->int:
    src,out=fx()/IN_DIR,fx()/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True)
    paths={k:src/v for k,v in REQ.items()}
    ia=pd.DataFrame([{"role":k,"path":str(p),"required":True,"exists":lp(p).exists()} for k,p in paths.items()]); wc(out/"gold_v2_24ab_input_audit.csv",ia)
    ok_inputs=bool(ia["exists"].map(yes).all()); rows=[chk("24AB-C000","required 24AA files exist",ok_inputs,True,ok_inputs)]
    s24aa={}
    if ok_inputs:
        s24aa=rj(paths["summary"]); route=rc(paths["route"]); c=rc(paths["checks"]); g=rc(paths["gates"]); sf=rc(paths["safety"])
        rows += [chk("24AB-C001","24AA status routed",s24aa.get("status"),EXPECTED_STATUS,s24aa.get("status")==EXPECTED_STATUS),chk("24AB-C002","24AA route expected",s24aa.get("route_id"),EXPECTED_ROUTE,s24aa.get("route_id")==EXPECTED_ROUTE),chk("24AB-C003","24AA next 24AB",s24aa.get("routed_next_audit_step"),EXPECTED_NEXT,s24aa.get("routed_next_audit_step")==EXPECTED_NEXT),chk("24AB-C004","24AA route row passed",route.iloc[0].get("status","") if not route.empty else "missing","ROUTED_TO_NEXT_AUDIT_ONLY",(not route.empty and str(route.iloc[0].get("status",""))=="ROUTED_TO_NEXT_AUDIT_ONLY")),chk("24AB-C005","24AA stop rows zero",stops(c)+stops(sf)+stops(route),0,stops(c)+stops(sf)+stops(route)==0),chk("24AB-C006","24AA next only 24AB",alw(g,"allowed_after_24aa_success"),[EXPECTED_NEXT],alw(g,"allowed_after_24aa_success")==[EXPECTED_NEXT]),chk("24AB-C007","24AA did not allow now",s24aa.get("source_recovery_execution_allowed_now"),False,no(s24aa.get("source_recovery_execution_allowed_now"))),chk("24AB-C008","24AA did not allow mutation",s24aa.get("source_mutation_allowed"),False,no(s24aa.get("source_mutation_allowed"))),chk("24AB-C009","24AA did not finalize identity",s24aa.get("source_identity_finalized"),False,no(s24aa.get("source_identity_finalized")))]
    checks=pd.DataFrame(rows); pl=plan(); ev=evidence(); bd=boundary(); sc=stopconds()
    safety=pd.DataFrame([{"safety_item":x,"observed":o,"expected":e,"status":"PASS"} for x,o,e in [("audit_only",True,True),("planning_only",True,True),("source_recovery_execution_allowed_now",False,False),("source_mutation_allowed",False,False),("source_identity_finalization_allowed_now",False,False),("external_actions_allowed",False,False),("old_gold_disc8_quarantined",True,True)]])
    total=stops(checks)+stops(pl)+stops(ev)+stops(bd)+stops(sc)+stops(safety); ok=ok_inputs and total==0
    gates=pd.DataFrame([{"next_step":"24AC_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_REVIEW_AUDIT_ONLY","allowed_after_24ab_success":bool(ok),"reason":"pre-execution readiness plan ready" if ok else "24AB not passed"}]+[{"next_step":x,"allowed_after_24ab_success":False,"reason":"blocked"} for x in BLOCKED])
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS if ok else STOP_STATUS,"audit_only":True,"planning_only":True,"upstream_24aa_status":s24aa.get("status","UNKNOWN"),"upstream_route_id":s24aa.get("route_id",""),"source_recovery_execution_allowed_now":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"source_mutation_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"old_gold_disc8_quarantined":True,"still_blocked_after_24ab":BLOCKED,"total_stop_rows":int(total),"required_next_allowed":alw(gates,"allowed_after_24ab_success"),"next_recommended_step":"24AC_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_REVIEW_AUDIT_ONLY" if ok else "STOP_REVIEW_24AB_INPUTS","do_not_execute_source_recovery_in_24ab":True}
    wc(out/"gold_v2_24ab_pre_execution_readiness_plan.csv",pl); wc(out/"gold_v2_24ab_pre_execution_evidence_manifest.csv",ev); wc(out/"gold_v2_24ab_pre_execution_boundary_matrix.csv",bd); wc(out/"gold_v2_24ab_pre_execution_stop_conditions.csv",sc); wc(out/"gold_v2_24ab_integrated_checks.csv",checks); wc(out/"gold_v2_24ab_required_next_gates.csv",gates); wc(out/"gold_v2_24ab_safety_matrix.csv",safety); wj(out/"gold_v2_24ab_source_recovery_pre_execution_readiness_plan_summary.json",summary)
    report="\n".join(["# GOLD V2 24AB source recovery pre-execution readiness plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{summary['status']}`","","## Boundary","","24AB writes a pre-execution readiness planning package only. It does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.","","## Outcome","",f"- Total STOP rows: `{summary['total_stop_rows']}`",f"- Upstream route id: `{summary['upstream_route_id']}`",f"- Next recommended step: `{summary['next_recommended_step']}`","","## Input audit","",md(ia),"","## Pre-execution readiness plan","",md(pl),"","## Evidence manifest","",md(ev),"","## Boundary matrix","",md(bd),"","## Stop conditions","",md(sc),"","## Integrated checks","",md(checks),"","## Required next gates","",md(gates),"","## Safety matrix","",md(safety),"","## Explicit non-actions","","- source recovery run: `false`","- source mutation: `false`","- source identity finalization: `false`","- live/final signal/external actions: `false`"])
    wt(out/"GOLD_V2_24AB_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_AUDIT_ONLY_REPORT.md",report); print(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
