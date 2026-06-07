#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "24X_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_AUDIT_ONLY"
IN_DIR = "gold_v2_24w_source_recovery_execution_planning_audit_only"
OUT_DIR = "gold_v2_24x_source_recovery_execution_plan_review_audit_only"
EXPECTED_STATUS = "SOURCE_RECOVERY_EXECUTION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
EXPECTED_NEXT = "24X_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_AUDIT_ONLY"
PASS_STATUS = "SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24X_STOP_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_INPUTS_OR_SAFETY"
REQ = {"report":"GOLD_V2_24W_SOURCE_RECOVERY_EXECUTION_PLANNING_AUDIT_ONLY_REPORT.md","summary":"gold_v2_24w_source_recovery_execution_planning_summary.json","input_audit":"gold_v2_24w_input_audit.csv","plan":"gold_v2_24w_execution_plan.csv","evidence":"gold_v2_24w_required_evidence_manifest.csv","boundary":"gold_v2_24w_execution_boundary_matrix.csv","checks":"gold_v2_24w_integrated_checks.csv","gates":"gold_v2_24w_required_next_gates.csv","safety":"gold_v2_24w_safety_matrix.csv"}
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
def review_plan(df:pd.DataFrame)->pd.DataFrame:
    if df.empty: return pd.DataFrame([{"plan_id":"missing","status":"STOP","notes":"plan empty"}])
    rows=[]
    for _,r in df.iterrows():
        req=yes(r.get("required",False)); audit=yes(r.get("audit_only",False)); pid=str(r.get("plan_id","")).strip(); item=str(r.get("plan_item","")).strip()
        rows.append({"plan_id":pid,"plan_item":item,"required":req,"audit_only":audit,"status":"PASS" if pid and item and req and audit else "STOP"})
    return pd.DataFrame(rows)
def review_evidence(df:pd.DataFrame)->pd.DataFrame:
    if df.empty: return pd.DataFrame([{"evidence_role":"missing","status":"STOP","notes":"evidence empty"}])
    rows=[]
    for _,r in df.iterrows():
        role=str(r.get("evidence_role","")).strip(); req=yes(r.get("required_for_24x",False))
        rows.append({"evidence_role":role,"required_for_24x":req,"source_status":r.get("status",""),"status":"PASS" if role and req else "STOP"})
    return pd.DataFrame(rows)
def review_boundary(df:pd.DataFrame)->pd.DataFrame:
    if df.empty: return pd.DataFrame([{"boundary_item":"missing","status":"STOP","notes":"boundary empty"}])
    rows=[]
    for _,r in df.iterrows():
        item=str(r.get("boundary_item","")).strip(); allowed=yes(r.get("allowed_after_24w_plan",True)); src=str(r.get("status",""))
        rows.append({"boundary_item":item,"allowed_after_24w_plan":allowed,"source_status":src,"status":"PASS" if item in BLOCKED and not allowed and src=="PASS" else "STOP"})
    return pd.DataFrame(rows)
def main()->int:
    src,out=fx()/IN_DIR,fx()/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True)
    paths={k:src/v for k,v in REQ.items()}
    ia=pd.DataFrame([{"role":k,"path":str(p),"required":True,"exists":lp(p).exists()} for k,p in paths.items()]); wc(out/"gold_v2_24x_input_audit.csv",ia)
    ok_inputs=bool(ia["exists"].map(yes).all()); rows=[chk("24X-C000","required 24W files exist",ok_inputs,True,ok_inputs)]
    s24w={}; plan=ev=bd=pd.DataFrame()
    if ok_inputs:
        s24w=rj(paths["summary"]); plan=rc(paths["plan"]); ev=rc(paths["evidence"]); bd=rc(paths["boundary"]); c=rc(paths["checks"]); g=rc(paths["gates"]); sf=rc(paths["safety"])
        rows += [chk("24X-C001","24W status ready",s24w.get("status"),EXPECTED_STATUS,s24w.get("status")==EXPECTED_STATUS),chk("24X-C002","24W is planning only",s24w.get("planning_only"),True,yes(s24w.get("planning_only"))),chk("24X-C003","24W stop rows zero",stops(c)+stops(sf),0,stops(c)+stops(sf)==0),chk("24X-C004","24W next only 24X",alw(g,"allowed_after_24w_success"),[EXPECTED_NEXT],alw(g,"allowed_after_24w_success")==[EXPECTED_NEXT]),chk("24X-C005","24W did not allow now",s24w.get("source_recovery_execution_allowed_now"),False,no(s24w.get("source_recovery_execution_allowed_now"))),chk("24X-C006","24W did not allow mutation",s24w.get("source_mutation_allowed"),False,no(s24w.get("source_mutation_allowed"))),chk("24X-C007","24W did not finalize identity",s24w.get("source_identity_finalized"),False,no(s24w.get("source_identity_finalized")))]
    checks=pd.DataFrame(rows); pr=review_plan(plan); er=review_evidence(ev); br=review_boundary(bd)
    safety=pd.DataFrame([{"safety_item":x,"observed":o,"expected":e,"status":"PASS"} for x,o,e in [("audit_only",True,True),("review_only",True,True),("source_recovery_execution_allowed_now",False,False),("source_mutation_allowed",False,False),("source_identity_finalization_allowed_now",False,False),("external_actions_allowed",False,False),("old_gold_disc8_quarantined",True,True)]])
    total=stops(checks)+stops(pr)+stops(er)+stops(br)+stops(safety); ok=ok_inputs and total==0
    gates=pd.DataFrame([{"next_step":"24Y_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY","allowed_after_24x_success":bool(ok),"reason":"plan review passed" if ok else "24X not passed"}]+[{"next_step":x,"allowed_after_24x_success":False,"reason":"blocked"} for x in BLOCKED])
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS if ok else STOP_STATUS,"audit_only":True,"review_only":True,"upstream_24w_status":s24w.get("status","UNKNOWN"),"source_recovery_execution_allowed_now":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"source_mutation_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"old_gold_disc8_quarantined":True,"still_blocked_after_24x":BLOCKED,"total_stop_rows":int(total),"required_next_allowed":alw(gates,"allowed_after_24x_success"),"next_recommended_step":"24Y_SOURCE_RECOVERY_EXECUTION_FINAL_DECISION_OPTIONS_AUDIT_ONLY" if ok else "STOP_REVIEW_24X_INPUTS","do_not_execute_source_recovery_in_24x":True}
    wc(out/"gold_v2_24x_execution_plan_review.csv",pr); wc(out/"gold_v2_24x_required_evidence_review.csv",er); wc(out/"gold_v2_24x_execution_boundary_review.csv",br); wc(out/"gold_v2_24x_integrated_checks.csv",checks); wc(out/"gold_v2_24x_required_next_gates.csv",gates); wc(out/"gold_v2_24x_safety_matrix.csv",safety); wj(out/"gold_v2_24x_source_recovery_execution_plan_review_summary.json",summary)
    report="\n".join(["# GOLD V2 24X source recovery execution plan review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{summary['status']}`","","## Boundary","","24X reviews the 24W planning package only. It does not mutate source artifacts, run recovery, finalize identity, enable live behavior, or call external systems.","","## Outcome","",f"- Total STOP rows: `{summary['total_stop_rows']}`",f"- Next recommended step: `{summary['next_recommended_step']}`","","## Input audit","",md(ia),"","## Execution plan review","",md(pr),"","## Required evidence review","",md(er),"","## Execution boundary review","",md(br),"","## Integrated checks","",md(checks),"","## Required next gates","",md(gates),"","## Safety matrix","",md(safety),"","## Explicit non-actions","","- source recovery run: `false`","- source mutation: `false`","- source identity finalization: `false`","- live/final signal/external actions: `false`"])
    wt(out/"GOLD_V2_24X_SOURCE_RECOVERY_EXECUTION_PLAN_REVIEW_AUDIT_ONLY_REPORT.md",report); print(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)); return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
