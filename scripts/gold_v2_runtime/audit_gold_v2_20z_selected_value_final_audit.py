#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY"
OUT_DIR="gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_audit_only"
IN20Y="gold_v2_20y_tier2_source_identity_human_decision_selected_value_draft_reconciliation_audit_only"
REPORT="GOLD_V2_20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_ADDITIONAL_AUDIT_REQUIRED_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_20Z_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
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
        ["21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY","Plan additional audit requested by REQUEST_MORE_AUDIT","Audit-only next planning step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after final audit.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after final audit.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after final audit.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after final audit.",False],
    ],columns=["next_step","name","purpose","allowed_after_20z_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["selected_value_final_audit_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["additional_audit_required",True,True,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_additional_audit_planning_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN20Y
    inputs={"backup_manifest":root/BACKUP,"summary_20y":p/"gold_v2_20y_tier2_source_identity_human_decision_selected_value_draft_reconciliation_summary.json","checks_20y":p/"gold_v2_20y_reconciliation_checks.csv","stage_20y":p/"gold_v2_20y_stage_status_audit.csv","gates_20y":p/"gold_v2_20y_required_next_gates.csv","safety_20y":p/"gold_v2_20y_safety_matrix.csv","report_20y":p/"GOLD_V2_20Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_20z_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("20Z-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_20z_final_checks.csv",c); wc(out/"gold_v2_20z_safety_matrix.csv",s); wc(out/"gold_v2_20z_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"20Z_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"final_audit_passed":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_20Z_INPUTS"}
        wj(out/"gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    sy=rj(inputs["summary_20y"]); checks=rc(inputs["checks_20y"]); stage=rc(inputs["stage_20y"]); gatesy=rc(inputs["gates_20y"]); safetyy=rc(inputs["safety_20y"])
    false_y=sum(int(bool(sy.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in sy.get("external_actions",{}).values())
    stage_ok=(not stage.empty) and all(stage.get("selected_value",pd.Series(dtype=str)).astype(str)==SELECTED) and not any(stage.get("source_recovery_approved",pd.Series(dtype=object)).map(truthy))
    rows=pd.DataFrame([
        chk("20Z-C001","20Y status",sy.get("status"),EXPECTED,sy.get("status")==EXPECTED),
        chk("20Z-C002","20Y reconciliation_passed",sy.get("reconciliation_passed"),True,bool(sy.get("reconciliation_passed",False))),
        chk("20Z-C003","20Y total_stop_rows",sy.get("total_stop_rows"),0,sy.get("total_stop_rows")==0),
        chk("20Z-C004","20Y selected_value",sy.get("selected_value"),SELECTED,sy.get("selected_value")==SELECTED),
        chk("20Z-C005","20Y decision_value",sy.get("decision_value"),SELECTED,sy.get("decision_value")==SELECTED),
        chk("20Z-C006","20Y request_more_audit_meaning_preserved",sy.get("request_more_audit_meaning_preserved"),True,bool(sy.get("request_more_audit_meaning_preserved",False))),
        chk("20Z-C007","20Y checks/safety STOP rows",sc(checks)+sc(safetyy),0,sc(checks)+sc(safetyy)==0),
        chk("20Z-C008","20Y forbidden gates allowed",forbid_gates(gatesy,"allowed_after_20y_success"),0,forbid_gates(gatesy,"allowed_after_20y_success")==0),
        chk("20Z-C009","20Y forbidden summary flags true",false_y,0,false_y==0),
        chk("20Z-C010","20Y stage status audit ok",stage_ok,True,stage_ok),
        chk("20Z-C011","additional audit required",True,True,True),
        chk("20Z-C012","source recovery approval denied by value",False,False,True),
        chk("20Z-C013","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "20Z_STOP_REVIEW_SELECTED_VALUE_FINAL_AUDIT_OUTPUTS"; s=safety(ok); g=gates(ok)
    wc(out/"gold_v2_20z_final_checks.csv",rows); wc(out/"gold_v2_20z_safety_matrix.csv",s); wc(out/"gold_v2_20z_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"final_audit_passed":ok,"additional_audit_required":ok,"request_more_audit_meaning_preserved":ok,"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"21A_ADDITIONAL_AUDIT_PLANNING_AUDIT_ONLY" if ok else "STOP_REVIEW_20Z_OUTPUTS"}
    wj(out/"gold_v2_20z_tier2_source_identity_human_decision_selected_value_final_audit_summary.json",sm)
    rep=["# GOLD V2 20Z TIER2 selected human decision value final audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 20Z final-audited the selected-value chain: `REQUEST_MORE_AUDIT`.","- REQUEST_MORE_AUDIT requires additional audit and is not source recovery approval.","- Source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.","","## Final checks",md(rows),"","## Next gates",md(g),"","## Safety",md(s)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
