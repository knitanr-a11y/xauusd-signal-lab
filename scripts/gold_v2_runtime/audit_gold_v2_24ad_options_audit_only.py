#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="24AD_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY"
IN_DIR="gold_v2_24ac_source_recovery_pre_execution_readiness_plan_review_audit_only"
OUT_DIR="gold_v2_24ad_source_recovery_pre_execution_final_decision_options_audit_only"
EXPECTED_STATUS="SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_NEXT="24AD_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY"
PASS_STATUS="SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS="24AD_STOP_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_OPTIONS_INPUTS_OR_SAFETY"
REQ={"report":"GOLD_V2_24AC_SOURCE_RECOVERY_PRE_EXECUTION_READINESS_PLAN_REVIEW_AUDIT_ONLY_REPORT.md","summary":"gold_v2_24ac_source_recovery_pre_execution_readiness_plan_review_summary.json","input_audit":"gold_v2_24ac_input_audit.csv","plan_review":"gold_v2_24ac_pre_execution_readiness_plan_review.csv","evidence_review":"gold_v2_24ac_pre_execution_evidence_review.csv","boundary_review":"gold_v2_24ac_pre_execution_boundary_review.csv","stop_review":"gold_v2_24ac_pre_execution_stop_condition_review.csv","checks":"gold_v2_24ac_integrated_checks.csv","gates":"gold_v2_24ac_required_next_gates.csv","safety":"gold_v2_24ac_safety_matrix.csv"}
OPTIONS=["KEEP_SOURCE_RECOVERY_PRE_EXECUTION_BLOCKED","REQUEST_MORE_SOURCE_RECOVERY_PRE_EXECUTION_REVIEW","REJECT_SOURCE_RECOVERY_PRE_EXECUTION_READINESS","APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY"]
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
    ia=pd.DataFrame([{"role":k,"path":str(p),"required":True,"exists":lp(p).exists()} for k,p in paths.items()]); wc(out/"gold_v2_24ad_input_audit.csv",ia)
    ok_inputs=bool(ia["exists"].map(yes).all()); rows=[chk("24AD-C000","required 24AC files exist",ok_inputs,True,ok_inputs)]
    s24ac={}
    if ok_inputs:
        s24ac=rj(paths["summary"]); pr=rc(paths["plan_review"]); er=rc(paths["evidence_review"]); br=rc(paths["boundary_review"]); sr=rc(paths["stop_review"]); c=rc(paths["checks"]); g=rc(paths["gates"]); sf=rc(paths["safety"])
        rows += [chk("24AD-C001","24AC status passed",s24ac.get("status"),EXPECTED_STATUS,s24ac.get("status")==EXPECTED_STATUS),chk("24AD-C002","24AC review only",s24ac.get("review_only"),True,yes(s24ac.get("review_only"))),chk("24AD-C003","24AC stop rows zero",stops(c)+stops(sf)+stops(pr)+stops(er)+stops(br)+stops(sr),0,stops(c)+stops(sf)+stops(pr)+stops(er)+stops(br)+stops(sr)==0),chk("24AD-C004","24AC next only 24AD",alw(g,"allowed_after_24ac_success"),[EXPECTED_NEXT],alw(g,"allowed_after_24ac_success")==[EXPECTED_NEXT]),chk("24AD-C005","24AC did not allow now",s24ac.get("source_recovery_execution_allowed_now"),False,no(s24ac.get("source_recovery_execution_allowed_now"))),chk("24AD-C006","24AC did not allow mutation",s24ac.get("source_mutation_allowed"),False,no(s24ac.get("source_mutation_allowed"))),chk("24AD-C007","24AC did not finalize identity",s24ac.get("source_identity_finalized"),False,no(s24ac.get("source_identity_finalized")))]
    checks=pd.DataFrame(rows)
    opts=pd.DataFrame([{"decision_value":v,"allowed_for_later_24ae_intake":True,"source_recovery_execution_allowed_in_24ad":False,"source_mutation_allowed_in_24ad":False} for v in OPTIONS])
    safety=pd.DataFrame([{"safety_item":x,"observed":o,"expected":e,"status":"PASS"} for x,o,e in [("audit_only",True,True),("decision_options_only",True,True),("source_recovery_execution_allowed_now",False,False),("source_mutation_allowed",False,False),("source_identity_finalization_allowed_now",False,False),("external_actions_allowed",False,False),("old_gold_disc8_quarantined",True,True)]])
    total=stops(checks)+stops(opts)+stops(safety); ok=ok_inputs and total==0 and len(opts)==4
    gates=pd.DataFrame([{"next_step":"24AE_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY","allowed_after_24ad_success":bool(ok),"reason":"decision options ready" if ok else "24AD not passed"}]+[{"next_step":x,"allowed_after_24ad_success":False,"reason":"blocked"} for x in BLOCKED])
    template={"template_name":"GOLD_V2_24AD_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INPUT","created_by_step":STEP,"audit_only":True,"allowed_decision_values":OPTIONS,"selected_decision_value":"","source_recovery_execution_allowed_now":False,"source_mutation_allowed":False,"still_blocked_after_template_creation":BLOCKED}
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS if ok else STOP_STATUS,"audit_only":True,"decision_options_only":True,"upstream_24ac_status":s24ac.get("status","UNKNOWN"),"decision_options_rows":int(len(opts)),"allowed_decision_values":OPTIONS,"source_recovery_execution_allowed_now":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"source_mutation_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"old_gold_disc8_quarantined":True,"still_blocked_after_24ad":BLOCKED,"total_stop_rows":int(total),"required_next_allowed":alw(gates,"allowed_after_24ad_success"),"next_recommended_step":"24AE_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_AUDIT_ONLY" if ok else "STOP_REVIEW_24AD_INPUTS","do_not_execute_source_recovery_in_24ad":True}
    wc(out/"gold_v2_24ad_decision_options.csv",opts); wj(out/"gold_v2_24ad_human_decision_input_template.json",template); wc(out/"gold_v2_24ad_integrated_checks.csv",checks); wc(out/"gold_v2_24ad_required_next_gates.csv",gates); wc(out/"gold_v2_24ad_safety_matrix.csv",safety); wj(out/"gold_v2_24ad_source_recovery_pre_execution_final_decision_options_summary.json",summary)
    report="\n".join(["# GOLD V2 24AD source recovery pre-execution final decision options audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{summary['status']}`","","## Boundary","","24AD prepares decision options only. It does not choose a decision, mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.","","## Outcome","",f"- Total STOP rows: `{summary['total_stop_rows']}`",f"- Decision option rows: `{summary['decision_options_rows']}`",f"- Next recommended step: `{summary['next_recommended_step']}`","","## Input audit","",md(ia),"","## Decision options","",md(opts),"","## Integrated checks","",md(checks),"","## Required next gates","",md(gates),"","## Safety matrix","",md(safety),"","## Explicit non-actions","","- source recovery run: `false`","- source mutation: `false`","- source identity finalization: `false`","- live/final signal/external actions: `false`"])
    wt(out/"GOLD_V2_24AD_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md",report); print(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
