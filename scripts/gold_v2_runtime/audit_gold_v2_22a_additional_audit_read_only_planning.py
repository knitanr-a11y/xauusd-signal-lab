#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="22A_ADDITIONAL_AUDIT_EXECUTION_READ_ONLY_PLANNING_AUDIT_ONLY"
OUT_DIR="gold_v2_22a_additional_audit_read_only_planning_audit_only"
IN21H="gold_v2_21h_additional_audit_handoff_audit_only"
REPORT="GOLD_V2_22A_ADDITIONAL_AUDIT_READ_ONLY_PLANNING_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_READ_ONLY_PLANNING_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_HANDOFF_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_22A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_KEYS=["source_recovery_approved","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]

PLANS=[
    ("22A-P001","uncertainty_review_plan","Plan read-only review of why REQUEST_MORE_AUDIT remains unresolved."),
    ("22A-P002","evidence_inventory_plan","Plan read-only inventory of evidence needed before any later approval candidate."),
    ("22A-P003","blocked_path_recheck_plan","Plan recheck that recovery, live, final, and external paths remain off."),
    ("22A-P004","handoff_consistency_plan","Plan consistency check from 20U through 21H."),
    ("22A-P005","next_report_plan","Plan next read-only execution draft output and checks."),
]

def rr()->Path: return Path(__file__).resolve().parents[2]
def fx()->Path:
    r=rr(); return (r.parents[1] if len(r.parents)>=2 else r.parent)/"FX_OUTPUTS"
def lp(p:Path)->Path:
    p=p if p.is_absolute() else p.resolve()
    if os.name!="nt": return p
    s=str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def truthy(v:Any)->bool: return v if isinstance(v,bool) else str(v).strip().lower() in {"1","true","yes","y"}
def wt(p:Path,t:str)->None: lp(p.parent).mkdir(parents=True,exist_ok=True); lp(p).write_text(t,encoding="utf-8")
def wj(p:Path,o:dict[str,Any])->None: wt(p,json.dumps(o,ensure_ascii=False,indent=2))
def wc(p:Path,d:pd.DataFrame)->None: lp(p.parent).mkdir(parents=True,exist_ok=True); d.to_csv(lp(p),index=False,encoding="utf-8-sig")
def rj(p:Path)->dict[str,Any]: return json.loads(lp(p).read_text(encoding="utf-8"))
def rc(p:Path)->pd.DataFrame:
    for e in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(p),encoding=e,keep_default_na=False)
        except Exception: pass
    raise RuntimeError(f"CSV read failed: {p}")
def sc(d:pd.DataFrame)->int: return int((d.get("status",pd.Series(dtype=str)).astype(str)=="STOP").sum()) if not d.empty else 0
def chk(i,n,o,e,ok): return {"check_id":i,"check":n,"observed":o,"expected":e,"status":"PASS" if ok else "STOP"}
def md(d:pd.DataFrame)->str:
    if d.empty: return "_No rows._"
    c=list(d.columns); out=["| "+" | ".join(c)+" |","| "+" | ".join(["---"]*len(c))+" |"]
    for _,r in d.iterrows(): out.append("| "+" | ".join(str(r[x]).replace("|","\\|").replace("\n"," ") for x in c)+" |")
    return "\n".join(out)
def forbid_gates(d:pd.DataFrame,col:str)->int:
    if {"next_step",col}.issubset(d.columns): return int(d[d["next_step"].astype(str).isin(FORBID)][col].map(truthy).sum())
    return 999
def gates(ok:bool)->pd.DataFrame:
    return pd.DataFrame([
        ["22B_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_AUDIT_ONLY","Create next read-only execution draft","Audit-only next step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 22A.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 22A.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 22A.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 22A.",False],
    ],columns=["next_step","name","purpose","allowed_after_22a_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["read_only_planning_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_execution_draft_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN21H
    inputs={"backup_manifest":root/BACKUP,"summary_21h":p/"gold_v2_21h_additional_audit_handoff_summary.json","checks_21h":p/"gold_v2_21h_handoff_checks.csv","gates_21h":p/"gold_v2_21h_required_next_gates.csv","safety_21h":p/"gold_v2_21h_safety_matrix.csv","handoff_21h":p/"GOLD_V2_21H_NEXT_CHAT_HANDOFF_AUDIT_ONLY.md","report_21h":p/"GOLD_V2_21H_ADDITIONAL_AUDIT_HANDOFF_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_22a_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("22A-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_22a_planning_checks.csv",c); wc(out/"gold_v2_22a_safety_matrix.csv",s); wc(out/"gold_v2_22a_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"22A_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"planning_ready":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_22A_INPUTS"}
        wj(out/"gold_v2_22a_additional_audit_read_only_planning_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s21=rj(inputs["summary_21h"]); checks=rc(inputs["checks_21h"]); gates21=rc(inputs["gates_21h"]); safety21=rc(inputs["safety_21h"])
    false_21=sum(int(bool(s21.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s21.get("external_actions",{}).values())
    plan=pd.DataFrame([{"plan_id":pid,"planning_theme":theme,"purpose":purpose,"mode":"read_only_planning","executes_action":False,"allowed_in_22a":True} for pid,theme,purpose in PLANS]); wc(out/"gold_v2_22a_read_only_planning_rows.csv",plan)
    rows=pd.DataFrame([
        chk("22A-C001","21H status",s21.get("status"),EXPECTED,s21.get("status")==EXPECTED),
        chk("22A-C002","21H handoff_ready",s21.get("handoff_ready"),True,bool(s21.get("handoff_ready",False))),
        chk("22A-C003","21H selected_value",s21.get("selected_value"),SELECTED,s21.get("selected_value")==SELECTED),
        chk("22A-C004","21H total_stop_rows",s21.get("total_stop_rows"),0,s21.get("total_stop_rows")==0),
        chk("22A-C005","21H checks/safety STOP rows",sc(checks)+sc(safety21),0,sc(checks)+sc(safety21)==0),
        chk("22A-C006","21H forbidden gates allowed",forbid_gates(gates21,"allowed_after_21h_success"),0,forbid_gates(gates21,"allowed_after_21h_success")==0),
        chk("22A-C007","21H forbidden summary flags true",false_21,0,false_21==0),
        chk("22A-C008","planning rows",len(plan),5,len(plan)==5),
        chk("22A-C009","planning modes read-only",set(plan["mode"]),{"read_only_planning"},set(plan["mode"])=={"read_only_planning"}),
        chk("22A-C010","planning executes_action false",int(plan["executes_action"].map(truthy).sum()),0,int(plan["executes_action"].map(truthy).sum())==0),
        chk("22A-C011","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "22A_STOP_REVIEW_ADDITIONAL_AUDIT_READ_ONLY_PLANNING_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_22a_planning_checks.csv",rows); wc(out/"gold_v2_22a_safety_matrix.csv",smat); wc(out/"gold_v2_22a_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"planning_ready":ok,"planning_row_count":int(len(plan)),"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"22B_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_AUDIT_ONLY" if ok else "STOP_REVIEW_22A_OUTPUTS"}
    wj(out/"gold_v2_22a_additional_audit_read_only_planning_summary.json",sm)
    rep=["# GOLD V2 22A additional audit read-only planning audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 22A planned the next read-only additional audit execution after 21H.","- This planning step does not enable live, final, external, or recovery paths.","","## Planning rows",md(plan),"","## Planning checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
