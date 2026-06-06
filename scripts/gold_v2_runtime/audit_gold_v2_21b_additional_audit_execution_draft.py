#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="21B_ADDITIONAL_AUDIT_EXECUTION_DRAFT_AUDIT_ONLY"
OUT_DIR="gold_v2_21b_additional_audit_execution_draft_audit_only"
IN21A="gold_v2_21a_additional_audit_planning_audit_only"
REPORT="GOLD_V2_21B_ADDITIONAL_AUDIT_EXECUTION_DRAFT_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_EXECUTION_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_PLANNING_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_21B_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
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
        ["21C_ADDITIONAL_AUDIT_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY","Load-smoke the read-only additional audit draft","Audit-only next check.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after additional audit draft.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after additional audit draft.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after additional audit draft.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after additional audit draft.",False],
    ],columns=["next_step","name","purpose","allowed_after_21b_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["additional_audit_execution_draft_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["draft_executes_actions",False,False,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_load_smoke_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN21A
    inputs={"backup_manifest":root/BACKUP,"summary_21a":p/"gold_v2_21a_additional_audit_planning_summary.json","plan_21a":p/"gold_v2_21a_additional_audit_plan.csv","checks_21a":p/"gold_v2_21a_planning_checks.csv","gates_21a":p/"gold_v2_21a_required_next_gates.csv","safety_21a":p/"gold_v2_21a_safety_matrix.csv","report_21a":p/"GOLD_V2_21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_21b_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("21B-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_21b_draft_checks.csv",c); wc(out/"gold_v2_21b_safety_matrix.csv",s); wc(out/"gold_v2_21b_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"21B_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"draft_ready":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_21B_INPUTS"}
        wj(out/"gold_v2_21b_additional_audit_execution_draft_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s21=rj(inputs["summary_21a"]); plan=rc(inputs["plan_21a"]); checks=rc(inputs["checks_21a"]); gates21=rc(inputs["gates_21a"]); safety21=rc(inputs["safety_21a"])
    false_21=sum(int(bool(s21.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s21.get("external_actions",{}).values())
    draft_rows=[]
    for i,r in plan.iterrows():
        draft_rows.append({"draft_id":f"21B-D{i+1:03d}","source_plan_id":str(r.get("plan_id","")),"audit_theme":str(r.get("audit_theme","")),"mode":"read_only","executes_action":False,"source_recovery_allowed":False,"external_action_allowed":False,"status":"DRAFT_ONLY"})
    draft_df=pd.DataFrame(draft_rows); wc(out/"gold_v2_21b_execution_draft.csv",draft_df)
    draft_json={"created_utc":now,"draft_status":"ADDITIONAL_AUDIT_EXECUTION_DRAFT_ONLY","selected_value":SELECTED,"decision_value":SELECTED,"source_step":"21A","source_status":s21.get("status"),"executes_actions":False,"source_recovery_approved":False,"source_recovery_allowed":False,"source_recovery_executed":False,"source_identity_finalization_allowed":False,"source_identity_finalized":False,"live_evaluator_allowed":False,"final_signal_allowed":False,"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False,"draft_items":draft_rows}
    wj(out/"gold_v2_21b_execution_draft.json",draft_json)
    rows=pd.DataFrame([
        chk("21B-C001","21A status",s21.get("status"),EXPECTED,s21.get("status")==EXPECTED),
        chk("21B-C002","21A planning_ready",s21.get("planning_ready"),True,bool(s21.get("planning_ready",False))),
        chk("21B-C003","21A selected_value",s21.get("selected_value"),SELECTED,s21.get("selected_value")==SELECTED),
        chk("21B-C004","21A total_stop_rows",s21.get("total_stop_rows"),0,s21.get("total_stop_rows")==0),
        chk("21B-C005","21A checks/safety STOP rows",sc(checks)+sc(safety21),0,sc(checks)+sc(safety21)==0),
        chk("21B-C006","21A forbidden gates allowed",forbid_gates(gates21,"allowed_after_21a_success"),0,forbid_gates(gates21,"allowed_after_21a_success")==0),
        chk("21B-C007","21A forbidden summary flags true",false_21,0,false_21==0),
        chk("21B-C008","source plan rows",len(plan),5,len(plan)==5),
        chk("21B-C009","draft rows match plan",len(draft_df),len(plan),len(draft_df)==len(plan)),
        chk("21B-C010","draft modes read-only",set(draft_df["mode"]),{"read_only"},set(draft_df["mode"])=={"read_only"}),
        chk("21B-C011","draft executes actions false",draft_df["executes_action"].map(truthy).sum(),0,int(draft_df["executes_action"].map(truthy).sum())==0),
        chk("21B-C012","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "21B_STOP_REVIEW_ADDITIONAL_AUDIT_EXECUTION_DRAFT_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_21b_draft_checks.csv",rows); wc(out/"gold_v2_21b_safety_matrix.csv",smat); wc(out/"gold_v2_21b_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"draft_ready":ok,"draft_item_count":int(len(draft_df)),"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"21C_ADDITIONAL_AUDIT_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY" if ok else "STOP_REVIEW_21B_OUTPUTS"}
    wj(out/"gold_v2_21b_additional_audit_execution_draft_summary.json",sm)
    rep=["# GOLD V2 21B additional audit execution draft audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 21B created a read-only additional audit execution draft from the 21A plan.","- This draft does not execute source recovery, live/final, or external actions.","","## Execution draft",md(draft_df),"","## Draft checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
