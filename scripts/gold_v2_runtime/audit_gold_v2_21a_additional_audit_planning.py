#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY"
OUT_DIR="gold_v2_21a_additional_audit_planning_audit_only"
IN20Z="gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_audit_only"
REPORT="GOLD_V2_21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_PLANNING_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_ADDITIONAL_AUDIT_REQUIRED_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_21A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
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
        ["21B_ADDITIONAL_AUDIT_EXECUTION_DRAFT_AUDIT_ONLY","Create additional audit execution draft","Audit-only next planning execution step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after additional audit planning.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after additional audit planning.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after additional audit planning.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after additional audit planning.",False],
    ],columns=["next_step","name","purpose","allowed_after_21a_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["additional_audit_planning_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["additional_audit_required",True,True,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_additional_audit_execution_draft_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN20Z
    inputs={"backup_manifest":root/BACKUP,"summary_20z":p/"gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_summary.json","checks_20z":p/"gold_v2_20z_final_checks.csv","gates_20z":p/"gold_v2_20z_required_next_gates.csv","safety_20z":p/"gold_v2_20z_safety_matrix.csv","report_20z":p/"GOLD_V2_20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_21a_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("21A-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_21a_planning_checks.csv",c); wc(out/"gold_v2_21a_safety_matrix.csv",s); wc(out/"gold_v2_21a_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"21A_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"planning_ready":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_21A_INPUTS"}
        wj(out/"gold_v2_21a_additional_audit_planning_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    sz=rj(inputs["summary_20z"]); checks=rc(inputs["checks_20z"]); gatesz=rc(inputs["gates_20z"]); safetyz=rc(inputs["safety_20z"])
    false_z=sum(int(bool(sz.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in sz.get("external_actions",{}).values())
    plan=pd.DataFrame([
        ["21A-P001","summarize_request_more_audit_uncertainty","Explain why REQUEST_MORE_AUDIT was selected and what remains unknown.","read_only",True],
        ["21A-P002","verify_recovery_blocked","Confirm source recovery remains blocked after 20Z.","read_only",True],
        ["21A-P003","source_identity_evidence_inventory","List source identity evidence still needing review without executing recovery.","read_only",True],
        ["21A-P004","approval_candidate_requirements","Define evidence needed before any future EXPLICIT_APPROVAL_CANDIDATE.","read_only",True],
        ["21A-P005","external_path_off_audit","Confirm Discord, MT5, AI API, live hook, live evaluator, and final signal remain off.","read_only",True],
    ],columns=["plan_id","audit_theme","purpose","mode","allowed_in_21a"]); wc(out/"gold_v2_21a_additional_audit_plan.csv",plan)
    rows=pd.DataFrame([
        chk("21A-C001","20Z status",sz.get("status"),EXPECTED,sz.get("status")==EXPECTED),
        chk("21A-C002","20Z final_audit_passed",sz.get("final_audit_passed"),True,bool(sz.get("final_audit_passed",False))),
        chk("21A-C003","20Z additional_audit_required",sz.get("additional_audit_required"),True,bool(sz.get("additional_audit_required",False))),
        chk("21A-C004","20Z selected_value",sz.get("selected_value"),SELECTED,sz.get("selected_value")==SELECTED),
        chk("21A-C005","20Z decision_value",sz.get("decision_value"),SELECTED,sz.get("decision_value")==SELECTED),
        chk("21A-C006","20Z total_stop_rows",sz.get("total_stop_rows"),0,sz.get("total_stop_rows")==0),
        chk("21A-C007","20Z checks/safety STOP rows",sc(checks)+sc(safetyz),0,sc(checks)+sc(safetyz)==0),
        chk("21A-C008","20Z forbidden gates allowed",forbid_gates(gatesz,"allowed_after_20z_success"),0,forbid_gates(gatesz,"allowed_after_20z_success")==0),
        chk("21A-C009","20Z forbidden summary flags true",false_z,0,false_z==0),
        chk("21A-C010","plan rows",len(plan),5,len(plan)==5),
        chk("21A-C011","plan read-only only",set(plan["mode"]),{"read_only"},set(plan["mode"])=={"read_only"}),
        chk("21A-C012","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "21A_STOP_REVIEW_ADDITIONAL_AUDIT_PLANNING_OUTPUTS"; s=safety(ok); g=gates(ok)
    wc(out/"gold_v2_21a_planning_checks.csv",rows); wc(out/"gold_v2_21a_safety_matrix.csv",s); wc(out/"gold_v2_21a_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"planning_ready":ok,"additional_audit_required":True,"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"21B_ADDITIONAL_AUDIT_EXECUTION_DRAFT_AUDIT_ONLY" if ok else "STOP_REVIEW_21A_OUTPUTS"}
    wj(out/"gold_v2_21a_additional_audit_planning_summary.json",sm)
    rep=["# GOLD V2 21A additional audit planning audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 21A planned additional audit requested by `REQUEST_MORE_AUDIT`.","- This is read-only planning and is not source recovery approval.","- Source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.","","## Additional audit plan",md(plan),"","## Planning checks",md(rows),"","## Next gates",md(g),"","## Safety",md(s)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
