#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="22B_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_AUDIT_ONLY"
OUT_DIR="gold_v2_22b_additional_audit_read_only_execution_draft_audit_only"
IN22A="gold_v2_22a_additional_audit_read_only_planning_audit_only"
REPORT="GOLD_V2_22B_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_READ_ONLY_PLANNING_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_22B_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_KEYS=["source_recovery_approved","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]

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
        ["22C_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_LOAD_CHECK_AUDIT_ONLY","Load-check read-only execution draft","Audit-only next step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 22B.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 22B.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 22B.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 22B.",False],
    ],columns=["next_step","name","purpose","allowed_after_22b_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["read_only_execution_draft_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["draft_executes_actions",False,False,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_load_check_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN22A
    inputs={"backup_manifest":root/BACKUP,"summary_22a":p/"gold_v2_22a_additional_audit_read_only_planning_summary.json","plan_22a":p/"gold_v2_22a_read_only_planning_rows.csv","checks_22a":p/"gold_v2_22a_planning_checks.csv","gates_22a":p/"gold_v2_22a_required_next_gates.csv","safety_22a":p/"gold_v2_22a_safety_matrix.csv","report_22a":p/"GOLD_V2_22A_ADDITIONAL_AUDIT_READ_ONLY_PLANNING_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_22b_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("22B-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_22b_draft_checks.csv",c); wc(out/"gold_v2_22b_safety_matrix.csv",s); wc(out/"gold_v2_22b_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"22B_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"draft_ready":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_22B_INPUTS"}
        wj(out/"gold_v2_22b_additional_audit_read_only_execution_draft_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s22=rj(inputs["summary_22a"]); plan=rc(inputs["plan_22a"]); checks=rc(inputs["checks_22a"]); gates22=rc(inputs["gates_22a"]); safety22=rc(inputs["safety_22a"])
    false_22=sum(int(bool(s22.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s22.get("external_actions",{}).values())
    draft=plan.copy(); draft.insert(0,"draft_id",[f"22B-D{i+1:03d}" for i in range(len(draft))]); draft["mode"]="read_only_draft"; draft["executes_action"]=False; draft["source_recovery_allowed"]=False; draft["external_action_allowed"]=False; draft["status"]="DRAFT_ONLY"
    wc(out/"gold_v2_22b_read_only_execution_draft.csv",draft)
    wj(out/"gold_v2_22b_read_only_execution_draft.json",{"created_utc":now,"draft_status":"ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_ONLY","selected_value":SELECTED,"decision_value":SELECTED,"source_step":"22A","source_status":s22.get("status"),"executes_actions":False,"source_recovery_approved":False,"source_recovery_allowed":False,"source_recovery_executed":False,"source_identity_finalization_allowed":False,"source_identity_finalized":False,"live_evaluator_allowed":False,"final_signal_allowed":False,"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False,"draft_items":draft.to_dict(orient="records")})
    rows=pd.DataFrame([
        chk("22B-C001","22A status",s22.get("status"),EXPECTED,s22.get("status")==EXPECTED),
        chk("22B-C002","22A planning_ready",s22.get("planning_ready"),True,bool(s22.get("planning_ready",False))),
        chk("22B-C003","22A selected_value",s22.get("selected_value"),SELECTED,s22.get("selected_value")==SELECTED),
        chk("22B-C004","22A total_stop_rows",s22.get("total_stop_rows"),0,s22.get("total_stop_rows")==0),
        chk("22B-C005","22A planning rows",len(plan),5,len(plan)==5),
        chk("22B-C006","22A checks/safety STOP rows",sc(checks)+sc(safety22),0,sc(checks)+sc(safety22)==0),
        chk("22B-C007","22A forbidden gates allowed",forbid_gates(gates22,"allowed_after_22a_success"),0,forbid_gates(gates22,"allowed_after_22a_success")==0),
        chk("22B-C008","22A forbidden summary flags true",false_22,0,false_22==0),
        chk("22B-C009","draft rows match plan",len(draft),len(plan),len(draft)==len(plan)),
        chk("22B-C010","draft modes read-only",set(draft["mode"].astype(str)),{"read_only_draft"},set(draft["mode"].astype(str))=={"read_only_draft"}),
        chk("22B-C011","draft executes_action false",int(draft["executes_action"].map(truthy).sum()),0,int(draft["executes_action"].map(truthy).sum())==0),
        chk("22B-C012","source recovery allowed false",int(draft["source_recovery_allowed"].map(truthy).sum()),0,int(draft["source_recovery_allowed"].map(truthy).sum())==0),
        chk("22B-C013","external action allowed false",int(draft["external_action_allowed"].map(truthy).sum()),0,int(draft["external_action_allowed"].map(truthy).sum())==0),
        chk("22B-C014","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "22B_STOP_REVIEW_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_22b_draft_checks.csv",rows); wc(out/"gold_v2_22b_safety_matrix.csv",smat); wc(out/"gold_v2_22b_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"draft_ready":ok,"draft_item_count":int(len(draft)),"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"22C_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_LOAD_CHECK_AUDIT_ONLY" if ok else "STOP_REVIEW_22B_OUTPUTS"}
    wj(out/"gold_v2_22b_additional_audit_read_only_execution_draft_summary.json",sm)
    rep=["# GOLD V2 22B additional audit read-only execution draft audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 22B created a read-only execution draft from 22A planning rows.","- This draft does not enable live, final, external, or recovery paths.","","## Read-only execution draft",md(draft),"","## Draft checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
