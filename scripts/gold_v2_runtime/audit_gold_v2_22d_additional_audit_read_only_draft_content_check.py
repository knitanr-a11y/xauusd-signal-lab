#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="22D_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_CONTENT_CHECK_AUDIT_ONLY"
OUT_DIR="gold_v2_22d_additional_audit_read_only_draft_content_check_audit_only"
IN22C="gold_v2_22c_additional_audit_read_only_draft_load_check_audit_only"
IN22B="gold_v2_22b_additional_audit_read_only_execution_draft_audit_only"
REPORT="GOLD_V2_22D_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_CONTENT_CHECK_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_READ_ONLY_DRAFT_CONTENT_CHECK_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_READ_ONLY_DRAFT_LOAD_CHECK_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_22D_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_KEYS=["source_recovery_approved","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]
EXPECTED_THEMES={"uncertainty_review_plan","evidence_inventory_plan","blocked_path_recheck_plan","handoff_consistency_plan","next_report_plan"}

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
        ["22E_ADDITIONAL_AUDIT_READ_ONLY_SCOPE_RECONCILIATION_AUDIT_ONLY","Reconcile read-only draft scope","Audit-only next step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 22D.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 22D.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 22D.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 22D.",False],
    ],columns=["next_step","name","purpose","allowed_after_22d_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["read_only_draft_content_check_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_scope_reconciliation_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p22c=base/IN22C; p22b=base/IN22B
    inputs={"backup_manifest":root/BACKUP,"summary_22c":p22c/"gold_v2_22c_additional_audit_read_only_draft_load_check_summary.json","checks_22c":p22c/"gold_v2_22c_load_checks.csv","gates_22c":p22c/"gold_v2_22c_required_next_gates.csv","safety_22c":p22c/"gold_v2_22c_safety_matrix.csv","report_22c":p22c/"GOLD_V2_22C_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_LOAD_CHECK_AUDIT_ONLY_REPORT.md","draft_csv_22b":p22b/"gold_v2_22b_read_only_execution_draft.csv","draft_json_22b":p22b/"gold_v2_22b_read_only_execution_draft.json"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_22d_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("22D-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_22d_content_checks.csv",c); wc(out/"gold_v2_22d_safety_matrix.csv",s); wc(out/"gold_v2_22d_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"22D_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"content_check_passed":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_22D_INPUTS"}
        wj(out/"gold_v2_22d_additional_audit_read_only_draft_content_check_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s22=rj(inputs["summary_22c"]); checks=rc(inputs["checks_22c"]); gates22=rc(inputs["gates_22c"]); safety22=rc(inputs["safety_22c"]); dc=rc(inputs["draft_csv_22b"]); dj=rj(inputs["draft_json_22b"])
    false_22=sum(int(bool(s22.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s22.get("external_actions",{}).values())
    themes=set(dc.get("planning_theme",pd.Series(dtype=str)).astype(str))
    content=pd.DataFrame([{"planning_theme":t,"expected":t in EXPECTED_THEMES,"present":t in themes,"status":"PASS" if t in themes else "STOP"} for t in sorted(EXPECTED_THEMES)]); wc(out/"gold_v2_22d_draft_content_audit.csv",content)
    rows=pd.DataFrame([
        chk("22D-C001","22C status",s22.get("status"),EXPECTED,s22.get("status")==EXPECTED),
        chk("22D-C002","22C load_check_passed",s22.get("load_check_passed"),True,bool(s22.get("load_check_passed",False))),
        chk("22D-C003","22C selected_value",s22.get("selected_value"),SELECTED,s22.get("selected_value")==SELECTED),
        chk("22D-C004","22C total_stop_rows",s22.get("total_stop_rows"),0,s22.get("total_stop_rows")==0),
        chk("22D-C005","22C checks/safety STOP rows",sc(checks)+sc(safety22),0,sc(checks)+sc(safety22)==0),
        chk("22D-C006","22C forbidden gates allowed",forbid_gates(gates22,"allowed_after_22c_success"),0,forbid_gates(gates22,"allowed_after_22c_success")==0),
        chk("22D-C007","22C forbidden summary flags true",false_22,0,false_22==0),
        chk("22D-C008","draft selected_value",dj.get("selected_value"),SELECTED,dj.get("selected_value")==SELECTED),
        chk("22D-C009","draft item count",len(dc),5,len(dc)==5),
        chk("22D-C010","expected planning themes present",themes,EXPECTED_THEMES,themes==EXPECTED_THEMES),
        chk("22D-C011","draft modes read_only_draft",set(dc.get("mode",pd.Series(dtype=str)).astype(str)),{"read_only_draft"},set(dc.get("mode",pd.Series(dtype=str)).astype(str))=={"read_only_draft"}),
        chk("22D-C012","draft executes_action false",int(dc.get("executes_action",pd.Series(dtype=object)).map(truthy).sum()),0,int(dc.get("executes_action",pd.Series(dtype=object)).map(truthy).sum())==0),
        chk("22D-C013","source recovery allowed false",int(dc.get("source_recovery_allowed",pd.Series(dtype=object)).map(truthy).sum()),0,int(dc.get("source_recovery_allowed",pd.Series(dtype=object)).map(truthy).sum())==0),
        chk("22D-C014","external action allowed false",int(dc.get("external_action_allowed",pd.Series(dtype=object)).map(truthy).sum()),0,int(dc.get("external_action_allowed",pd.Series(dtype=object)).map(truthy).sum())==0),
        chk("22D-C015","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "22D_STOP_REVIEW_ADDITIONAL_AUDIT_READ_ONLY_DRAFT_CONTENT_CHECK_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_22d_content_checks.csv",rows); wc(out/"gold_v2_22d_safety_matrix.csv",smat); wc(out/"gold_v2_22d_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"content_check_passed":ok,"draft_item_count":int(len(dc)),"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"22E_ADDITIONAL_AUDIT_READ_ONLY_SCOPE_RECONCILIATION_AUDIT_ONLY" if ok else "STOP_REVIEW_22D_OUTPUTS"}
    wj(out/"gold_v2_22d_additional_audit_read_only_draft_content_check_summary.json",sm)
    rep=["# GOLD V2 22D additional audit read-only draft content check audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 22D content-checked the read-only execution draft.","- This check does not enable live, final, external, or recovery paths.","","## Draft content audit",md(content),"","## Content checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
