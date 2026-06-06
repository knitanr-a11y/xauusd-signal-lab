#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="20S_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_ONLY"
OUT_DIR="gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_only"
IN20R="gold_v2_20r_tier2_source_identity_human_decision_value_capture_execution_draft_reconciliation_audit_only"
REPORT="GOLD_V2_20S_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_ONLY_REPORT.md"
SUCCESS="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_20S_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"ACTUAL_DECISION_COLLECTION","SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_KEYS=["decision_value_collected","decision_collected","decision_made","approval_granted","actual_decision_collection_allowed","actual_decision_collection_completed","signal_conditions_changed","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]

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
        ["AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE_ACTUAL_VALUE_ENTRY","Human authorization required before actual value entry","No script may collect a value until explicit human authorization is provided.",bool(ok)],
        ["ACTUAL_DECISION_COLLECTION","TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION","Still blocked after 20S.",False],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 20S.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 20S.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 20S.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 20S.",False],
    ],columns=["next_step","name","purpose","allowed_after_20s_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["execution_draft_final_audit_only",True,True,"PASS"],["decision_value","UNSET","UNSET","PASS"],["decision_value_collected",False,False,"PASS"],["decision_collected",False,False,"PASS"],["decision_made",False,False,"PASS"],["approval_granted",False,False,"PASS"],["actual_decision_collection_completed",False,False,"PASS"],["actual_decision_collection_allowed",False,False,"PASS"],["signal_conditions_changed",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["await_explicit_human_authorization_after_success",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN20R
    inputs={"backup_manifest":root/BACKUP,"summary_20r":p/"gold_v2_20r_tier2_source_identity_human_decision_value_capture_execution_draft_reconciliation_summary.json","checks_20r":p/"gold_v2_20r_reconciliation_checks.csv","stage_20r":p/"gold_v2_20r_stage_status_audit.csv","gates_20r":p/"gold_v2_20r_required_next_gates.csv","safety_20r":p/"gold_v2_20r_safety_matrix.csv","report_20r":p/"GOLD_V2_20R_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_20s_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("20S-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_20s_final_checks.csv",c); wc(out/"gold_v2_20s_safety_matrix.csv",s); wc(out/"gold_v2_20s_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"20S_STOP_MISSING_INPUTS","audit_only":True,"final_audit_ready":False,"decision_value":"UNSET","total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_20S_INPUTS"}
        wj(out/"gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    summ=rj(inputs["summary_20r"]); checks=rc(inputs["checks_20r"]); stage=rc(inputs["stage_20r"]); ng=rc(inputs["gates_20r"]); sf=rc(inputs["safety_20r"])
    false_sum=sum(int(bool(summ.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in summ.get("external_actions",{}).values())
    stage_bad=999
    if {"decision_value","summary_stop_rows"}.issubset(stage.columns): stage_bad=int((stage["decision_value"].astype(str)!="UNSET").sum())+int((stage["summary_stop_rows"].astype(int)!=0).sum())
    wc(out/"gold_v2_20s_stage_status_audit.csv",stage)
    rows=pd.DataFrame([
        chk("20S-C001","20R status",summ.get("status"),EXPECTED,summ.get("status")==EXPECTED),
        chk("20S-C002","20R reconciliation_passed",summ.get("reconciliation_passed"),True,bool(summ.get("reconciliation_passed",False))),
        chk("20S-C003","20R total_stop_rows",summ.get("total_stop_rows"),0,summ.get("total_stop_rows")==0),
        chk("20S-C004","20R decision_value",summ.get("decision_value"),"UNSET",summ.get("decision_value")=="UNSET"),
        chk("20S-C005","20R forbidden summary flags true",false_sum,0,false_sum==0),
        chk("20S-C006","20R checks/safety STOP rows",sc(checks)+sc(sf),0,sc(checks)+sc(sf)==0),
        chk("20S-C007","20R stage audit bad rows",stage_bad,0,stage_bad==0),
        chk("20S-C008","20R forbidden gates allowed",forbid_gates(ng,"allowed_after_20r_success"),0,forbid_gates(ng,"allowed_after_20r_success")==0),
        chk("20S-C009","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "20S_STOP_REVIEW_VALUE_CAPTURE_EXECUTION_DRAFT_FINAL_AUDIT_OUTPUTS"; s=safety(ok); g=gates(ok)
    wc(out/"gold_v2_20s_final_checks.csv",rows); wc(out/"gold_v2_20s_safety_matrix.csv",s); wc(out/"gold_v2_20s_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"final_audit_ready":ok,"decision_value":"UNSET","decision_value_collected":False,"decision_collected":False,"decision_made":False,"approval_granted":False,"actual_decision_collection_allowed":False,"actual_decision_collection_completed":False,"allowed_value_rows":int(summ.get("allowed_value_rows",0)),"total_stop_rows":int(total),"signal_conditions_changed":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"next_recommended_step":"AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE_ACTUAL_VALUE_ENTRY" if ok else "STOP_REVIEW_20S_OUTPUTS"}
    wj(out/"gold_v2_20s_tier2_source_identity_human_decision_value_capture_execution_draft_final_audit_summary.json",sm)
    rep=["# GOLD V2 20S TIER2 source identity human decision value capture execution draft final audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 20S final-audited the still-UNSET actual decision value capture execution draft chain only.","- No actual decision value was collected and no approval was made by this script.","- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.","","## Final checks",md(rows),"","## Stage status audit",md(stage),"","## Next gates",md(g),"","## Safety",md(s)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
