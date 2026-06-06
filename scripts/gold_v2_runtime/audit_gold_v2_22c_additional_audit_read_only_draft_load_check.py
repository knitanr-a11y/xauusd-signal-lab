#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="22C_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_LOAD_CHECK_AUDIT_ONLY"
OUT_DIR="gold_v2_22c_additional_audit_read_only_draft_load_check_audit_only"
IN22B="gold_v2_22b_additional_audit_read_only_execution_draft_audit_only"
REPORT="GOLD_V2_22C_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_LOAD_CHECK_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_READ_ONLY_DRAFT_LOAD_CHECK_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_22C_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_KEYS=["source_recovery_approved","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]
DRAFT_FALSE=["executes_actions","source_recovery_approved","source_recovery_allowed","source_recovery_executed","source_identity_finalization_allowed","source_identity_finalized","live_evaluator_allowed","final_signal_allowed","discord_send_allowed","mt5_order_allowed","ai_api_allowed","live_hook_allowed"]

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
        ["22D_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_CONTENT_CHECK_AUDIT_ONLY","Content-check read-only execution draft","Audit-only next step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 22C.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 22C.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 22C.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 22C.",False],
    ],columns=["next_step","name","purpose","allowed_after_22c_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["read_only_draft_load_check_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["draft_executes_actions",False,False,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_content_check_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN22B
    inputs={"backup_manifest":root/BACKUP,"summary_22b":p/"gold_v2_22b_additional_audit_read_only_execution_draft_summary.json","draft_json_22b":p/"gold_v2_22b_read_only_execution_draft.json","draft_csv_22b":p/"gold_v2_22b_read_only_execution_draft.csv","checks_22b":p/"gold_v2_22b_draft_checks.csv","gates_22b":p/"gold_v2_22b_required_next_gates.csv","safety_22b":p/"gold_v2_22b_safety_matrix.csv","report_22b":p/"GOLD_V2_22B_ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_22c_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("22C-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_22c_load_checks.csv",c); wc(out/"gold_v2_22c_safety_matrix.csv",s); wc(out/"gold_v2_22c_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"22C_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"load_check_passed":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_22C_INPUTS"}
        wj(out/"gold_v2_22c_additional_audit_read_only_draft_load_check_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s22=rj(inputs["summary_22b"]); dj=rj(inputs["draft_json_22b"]); dc=rc(inputs["draft_csv_22b"]); checks=rc(inputs["checks_22b"]); gates22=rc(inputs["gates_22b"]); safety22=rc(inputs["safety_22b"])
    false_22=sum(int(bool(s22.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s22.get("external_actions",{}).values())
    false_draft=sum(int(bool(dj.get(k,False))) for k in DRAFT_FALSE)
    load=pd.DataFrame([["draft_status",dj.get("draft_status")],["selected_value",dj.get("selected_value")],["executes_actions",dj.get("executes_actions")],["draft_item_count_json",len(dj.get("draft_items",[]))],["draft_item_count_csv",len(dc)]],columns=["field","observed"]); wc(out/"gold_v2_22c_draft_load_audit.csv",load)
    rows=pd.DataFrame([
        chk("22C-C001","22B status",s22.get("status"),EXPECTED,s22.get("status")==EXPECTED),
        chk("22C-C002","22B draft_ready",s22.get("draft_ready"),True,bool(s22.get("draft_ready",False))),
        chk("22C-C003","22B selected_value",s22.get("selected_value"),SELECTED,s22.get("selected_value")==SELECTED),
        chk("22C-C004","22B total_stop_rows",s22.get("total_stop_rows"),0,s22.get("total_stop_rows")==0),
        chk("22C-C005","22B checks/safety STOP rows",sc(checks)+sc(safety22),0,sc(checks)+sc(safety22)==0),
        chk("22C-C006","22B forbidden gates allowed",forbid_gates(gates22,"allowed_after_22b_success"),0,forbid_gates(gates22,"allowed_after_22b_success")==0),
        chk("22C-C007","22B forbidden summary flags true",false_22,0,false_22==0),
        chk("22C-C008","draft JSON status",dj.get("draft_status"),"ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_ONLY",dj.get("draft_status")=="ADDITIONAL_AUDIT_READ_ONLY_EXECUTION_DRAFT_ONLY"),
        chk("22C-C009","draft JSON selected_value",dj.get("selected_value"),SELECTED,dj.get("selected_value")==SELECTED),
        chk("22C-C010","draft JSON forbidden flags true",false_draft,0,false_draft==0),
        chk("22C-C011","draft CSV rows",len(dc),5,len(dc)==5),
        chk("22C-C012","draft CSV read_only_draft only",set(dc.get("mode",pd.Series(dtype=str)).astype(str)),{"read_only_draft"},set(dc.get("mode",pd.Series(dtype=str)).astype(str))=={"read_only_draft"}),
        chk("22C-C013","draft CSV executes_action false",int(dc.get("executes_action",pd.Series(dtype=object)).map(truthy).sum()),0,int(dc.get("executes_action",pd.Series(dtype=object)).map(truthy).sum())==0),
        chk("22C-C014","source recovery allowed false",int(dc.get("source_recovery_allowed",pd.Series(dtype=object)).map(truthy).sum()),0,int(dc.get("source_recovery_allowed",pd.Series(dtype=object)).map(truthy).sum())==0),
        chk("22C-C015","external action allowed false",int(dc.get("external_action_allowed",pd.Series(dtype=object)).map(truthy).sum()),0,int(dc.get("external_action_allowed",pd.Series(dtype=object)).map(truthy).sum())==0),
        chk("22C-C016","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "22C_STOP_REVIEW_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_LOAD_CHECK_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_22c_load_checks.csv",rows); wc(out/"gold_v2_22c_safety_matrix.csv",smat); wc(out/"gold_v2_22c_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"load_check_passed":ok,"draft_item_count":int(len(dc)),"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"22D_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_CONTENT_CHECK_AUDIT_ONLY" if ok else "STOP_REVIEW_22C_OUTPUTS"}
    wj(out/"gold_v2_22c_additional_audit_read_only_draft_load_check_summary.json",sm)
    rep=["# GOLD V2 22C additional audit read-only draft load check audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 22C load-checked the 22B read-only execution draft.","- This check does not enable live, final, external, or recovery paths.","","## Draft load audit",md(load),"","## Load checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
