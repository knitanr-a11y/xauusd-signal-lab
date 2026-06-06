#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="20Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_AUDIT_ONLY"
OUT_DIR="gold_v2_20y_tier2_source_identity_human_decision_selected_value_draft_reconciliation_audit_only"
IN20X="gold_v2_20x_tier2_source_identity_human_decision_selected_value_draft_content_audit_audit_only"
IN20W="gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_audit_only"
IN20V="gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_audit_only"
REPORT="GOLD_V2_20Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_RECONCILIATION_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_20Y_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
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
        ["20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY","Final-audit REQUEST_MORE_AUDIT selected-value chain","Audit-only next check.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after reconciliation.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after reconciliation.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after reconciliation.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after reconciliation.",False],
    ],columns=["next_step","name","purpose","allowed_after_20y_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["selected_value_reconciliation_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["request_more_audit_meaning_preserved",True,True,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_final_audit_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p20x=base/IN20X; p20w=base/IN20W; p20v=base/IN20V
    inputs={"backup_manifest":root/BACKUP,"summary_20x":p20x/"gold_v2_20x_tier2_source_identity_human_decision_selected_value_draft_content_audit_summary.json","checks_20x":p20x/"gold_v2_20x_content_checks.csv","gates_20x":p20x/"gold_v2_20x_required_next_gates.csv","safety_20x":p20x/"gold_v2_20x_safety_matrix.csv","report_20x":p20x/"GOLD_V2_20X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_AUDIT_ONLY_REPORT.md","summary_20w":p20w/"gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_summary.json","load_20w":p20w/"gold_v2_20w_draft_load_audit.csv","draft_20v":p20v/"gold_v2_20v_selected_value_draft.json"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_20y_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("20Y-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_20y_reconciliation_checks.csv",c); wc(out/"gold_v2_20y_safety_matrix.csv",s); wc(out/"gold_v2_20y_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"20Y_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"reconciliation_passed":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_20Y_INPUTS"}
        wj(out/"gold_v2_20y_tier2_source_identity_human_decision_selected_value_draft_reconciliation_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    sx=rj(inputs["summary_20x"]); sw=rj(inputs["summary_20w"]); draft=rj(inputs["draft_20v"]); checks=rc(inputs["checks_20x"]); gatesx=rc(inputs["gates_20x"]); safex=rc(inputs["safety_20x"]); load=rc(inputs["load_20w"])
    false_x=sum(int(bool(sx.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in sx.get("external_actions",{}).values())
    stage=pd.DataFrame([
        ["20V",draft.get("selected_value"),draft.get("decision_value"),draft.get("source_recovery_approved"),draft.get("script_executes_action")],
        ["20W",sw.get("selected_value"),sw.get("decision_value"),sw.get("source_recovery_approved"),False],
        ["20X",sx.get("selected_value"),sx.get("decision_value"),sx.get("source_recovery_approved"),False],
    ],columns=["stage","selected_value","decision_value","source_recovery_approved","script_executes_action"]); wc(out/"gold_v2_20y_stage_status_audit.csv",stage)
    rows=pd.DataFrame([
        chk("20Y-C001","20X status",sx.get("status"),EXPECTED,sx.get("status")==EXPECTED),
        chk("20Y-C002","20X content_audit_passed",sx.get("content_audit_passed"),True,bool(sx.get("content_audit_passed",False))),
        chk("20Y-C003","20X total_stop_rows",sx.get("total_stop_rows"),0,sx.get("total_stop_rows")==0),
        chk("20Y-C004","20X selected_value",sx.get("selected_value"),SELECTED,sx.get("selected_value")==SELECTED),
        chk("20Y-C005","20X decision_value",sx.get("decision_value"),SELECTED,sx.get("decision_value")==SELECTED),
        chk("20Y-C006","20X request_more_audit_meaning_preserved",sx.get("request_more_audit_meaning_preserved"),True,bool(sx.get("request_more_audit_meaning_preserved",False))),
        chk("20Y-C007","20X checks/safety STOP rows",sc(checks)+sc(safex),0,sc(checks)+sc(safex)==0),
        chk("20Y-C008","20X forbidden gates allowed",forbid_gates(gatesx,"allowed_after_20x_success"),0,forbid_gates(gatesx,"allowed_after_20x_success")==0),
        chk("20Y-C009","20X forbidden summary flags true",false_x,0,false_x==0),
        chk("20Y-C010","20W selected_value",sw.get("selected_value"),SELECTED,sw.get("selected_value")==SELECTED),
        chk("20Y-C011","20V draft selected_value",draft.get("selected_value"),SELECTED,draft.get("selected_value")==SELECTED),
        chk("20Y-C012","20V draft source_recovery_approved",draft.get("source_recovery_approved"),False,draft.get("source_recovery_approved") is False),
        chk("20Y-C013","20W load audit rows",len(load),">=5",len(load)>=5),
        chk("20Y-C014","stage selected values all match",stage["selected_value"].tolist(),SELECTED,all(stage["selected_value"].astype(str)==SELECTED)),
        chk("20Y-C015","stage source recovery approved all false",stage["source_recovery_approved"].tolist(),False,not any(stage["source_recovery_approved"].map(truthy))),
        chk("20Y-C016","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "20Y_STOP_REVIEW_SELECTED_VALUE_RECONCILIATION_OUTPUTS"; s=safety(ok); g=gates(ok)
    wc(out/"gold_v2_20y_reconciliation_checks.csv",rows); wc(out/"gold_v2_20y_safety_matrix.csv",s); wc(out/"gold_v2_20y_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"reconciliation_passed":ok,"request_more_audit_meaning_preserved":ok,"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"20Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_FINAL_AUDIT_AUDIT_ONLY" if ok else "STOP_REVIEW_20Y_OUTPUTS"}
    wj(out/"gold_v2_20y_tier2_source_identity_human_decision_selected_value_draft_reconciliation_summary.json",sm)
    rep=["# GOLD V2 20Y TIER2 selected human decision value draft reconciliation audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 20Y reconciled the selected-value chain: `REQUEST_MORE_AUDIT`.","- REQUEST_MORE_AUDIT remains a request for additional audit and is not source recovery approval.","- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.","","## Stage status audit",md(stage),"","## Reconciliation checks",md(rows),"","## Next gates",md(g),"","## Safety",md(s)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
