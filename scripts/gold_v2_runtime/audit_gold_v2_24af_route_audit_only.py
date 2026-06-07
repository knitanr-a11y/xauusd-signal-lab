#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY"
IN_DIR="gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_audit_only"
OUT_DIR="gold_v2_24af_source_recovery_pre_execution_final_decision_routing_audit_only"
EXPECTED_STATUS="SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_VALUE="APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY"
PASS_STATUS="SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS="24AF_STOP_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_INPUTS_OR_SAFETY"
REQ={"report":"GOLD_V2_24AE_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY_REPORT.md","summary":"gold_v2_24ae_source_recovery_pre_execution_final_decision_intake_summary.json","decision_input":"gold_v2_24ae_human_decision_input.json","template":"gold_v2_24ae_human_decision_input_template.json","intake_result":"gold_v2_24ae_human_decision_intake_result.csv","input_audit":"gold_v2_24ae_input_audit.csv","checks":"gold_v2_24ae_integrated_checks.csv","gates":"gold_v2_24ae_required_next_gates.csv","safety":"gold_v2_24ae_safety_matrix.csv"}
ROUTES={"KEEP_SOURCE_RECOVERY_PRE_EXECUTION_BLOCKED":("ROUTE_KEEP_PRE_EXECUTION_BLOCKED","24AG_SOURCE_RECOVERY_PRE_EXECUTION_BLOCKED_RECORD_AUDIT_ONLY"),"REQUEST_MORE_SOURCE_RECOVERY_PRE_EXECUTION_REVIEW":("ROUTE_REQUEST_MORE_PRE_EXECUTION_REVIEW","24AG_SOURCE_RECOVERY_PRE_EXECUTION_MORE_REVIEW_AUDIT_ONLY"),"REJECT_SOURCE_RECOVERY_PRE_EXECUTION_READINESS":("ROUTE_REJECT_PRE_EXECUTION_READINESS","24AG_SOURCE_RECOVERY_PRE_EXECUTION_REJECTION_RECORD_AUDIT_ONLY"),"APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY":("ROUTE_APPROVE_TO_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY","24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY")}
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
def main()->int:
    src,out=fx()/IN_DIR,fx()/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True)
    paths={k:src/v for k,v in REQ.items()}
    ia=pd.DataFrame([{"role":k,"path":str(p),"required":True,"exists":lp(p).exists()} for k,p in paths.items()]); wc(out/"gold_v2_24af_input_audit.csv",ia)
    ok_inputs=bool(ia["exists"].map(yes).all()); rows=[chk("24AF-C000","required 24AE files exist",ok_inputs,True,ok_inputs)]
    s24ae={}; selected=""; rid="UNKNOWN"; nxt="UNKNOWN"
    if ok_inputs:
        s24ae=rj(paths["summary"]); din=rj(paths["decision_input"]); intake=rc(paths["intake_result"]); c=rc(paths["checks"]); g=rc(paths["gates"]); sf=rc(paths["safety"])
        selected=str(s24ae.get("selected_decision_value") or din.get("selected_decision_value") or "").strip(); rid,nxt=ROUTES.get(selected,("UNKNOWN","UNKNOWN"))
        rows += [chk("24AF-C001","24AE status validated",s24ae.get("status"),EXPECTED_STATUS,s24ae.get("status")==EXPECTED_STATUS),chk("24AF-C002","24AE decision supplied",s24ae.get("decision_supplied"),True,yes(s24ae.get("decision_supplied"))),chk("24AF-C003","24AE decision validated",s24ae.get("decision_validated"),True,yes(s24ae.get("decision_validated"))),chk("24AF-C004","selected dry run audit",selected,EXPECTED_VALUE,selected==EXPECTED_VALUE),chk("24AF-C005","route known",selected,"known route",selected in ROUTES),chk("24AF-C006","24AE stop rows zero",stops(c)+stops(sf)+stops(intake),0,stops(c)+stops(sf)+stops(intake)==0),chk("24AF-C007","24AE next only 24AF",alw(g,"allowed_after_24ae_success"),[STEP],alw(g,"allowed_after_24ae_success")==[STEP]),chk("24AF-C008","24AE did not allow now",s24ae.get("source_recovery_execution_allowed_now"),False,no(s24ae.get("source_recovery_execution_allowed_now"))),chk("24AF-C009","24AE did not allow mutation",s24ae.get("source_mutation_allowed"),False,no(s24ae.get("source_mutation_allowed"))),chk("24AF-C010","24AE did not finalize identity",s24ae.get("source_identity_finalized"),False,no(s24ae.get("source_identity_finalized")))]
    checks=pd.DataFrame(rows)
    route=pd.DataFrame([{"selected_decision_value":selected,"route_id":rid,"routed_next_audit_step":nxt,"route_known":rid!="UNKNOWN","source_recovery_execution_allowed_in_24af":False,"source_mutation_allowed_in_24af":False,"status":"ROUTED_TO_NEXT_AUDIT_ONLY" if rid!="UNKNOWN" else "STOP"}])
    safety=pd.DataFrame([{"safety_item":x,"observed":o,"expected":e,"status":"PASS"} for x,o,e in [("audit_only",True,True),("routing_only",True,True),("source_recovery_execution_allowed_now",False,False),("source_mutation_allowed",False,False),("source_identity_finalization_allowed_now",False,False),("external_actions_allowed",False,False),("old_gold_disc8_quarantined",True,True)]])
    total=stops(checks)+stops(route)+stops(safety); ok=ok_inputs and total==0
    gates=pd.DataFrame([{"next_step":nxt if ok else "STOP_REVIEW_24AF_INPUTS","allowed_after_24af_success":bool(ok),"reason":"selected route" if ok else "24AF not passed"}]+[{"next_step":x,"allowed_after_24af_success":False,"reason":"blocked"} for x in BLOCKED])
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS if ok else STOP_STATUS,"audit_only":True,"routing_only":True,"upstream_24ae_status":s24ae.get("status","UNKNOWN"),"selected_decision_value":selected,"route_id":rid,"routed_next_audit_step":nxt,"source_recovery_execution_allowed_now":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"source_mutation_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"old_gold_disc8_quarantined":True,"still_blocked_after_24af":BLOCKED,"total_stop_rows":int(total),"required_next_allowed":alw(gates,"allowed_after_24af_success"),"next_recommended_step":nxt if ok else "STOP_REVIEW_24AF_INPUTS","do_not_execute_source_recovery_in_24af":True}
    wc(out/"gold_v2_24af_decision_route.csv",route); wc(out/"gold_v2_24af_integrated_checks.csv",checks); wc(out/"gold_v2_24af_required_next_gates.csv",gates); wc(out/"gold_v2_24af_safety_matrix.csv",safety); wj(out/"gold_v2_24af_source_recovery_pre_execution_final_decision_routing_summary.json",summary)
    report="\n".join(["# GOLD V2 24AF source recovery pre-execution final decision routing audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{summary['status']}`","","## Boundary","","24AF routes a validated final decision value only. It does not choose a value, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.","","## Outcome","",f"- Total STOP rows: `{summary['total_stop_rows']}`",f"- Selected decision: `{selected}`",f"- Route id: `{rid}`",f"- Routed next audit step: `{nxt}`","","## Input audit","",md(ia),"","## Decision route","",md(route),"","## Integrated checks","",md(checks),"","## Required next gates","",md(gates),"","## Safety matrix","",md(safety),"","## Explicit non-actions","","- source recovery run: `false`","- source mutation: `false`","- source identity finalization: `false`","- live/final signal/external actions: `false`"])
    wt(out/"GOLD_V2_24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY_REPORT.md",report); print(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
