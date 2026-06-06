#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="20W_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR="gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_audit_only"
IN20V="gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_audit_only"
REPORT="GOLD_V2_20W_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_LOAD_SMOKE_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_20W_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_DRAFT=["source_recovery_approved","source_recovery_allowed","source_recovery_executed","source_identity_finalization_allowed","source_identity_finalized","live_evaluator_allowed","final_signal_allowed","discord_send_allowed","mt5_order_allowed","ai_api_allowed","live_hook_allowed","script_executes_action"]
FALSE_SUM=["source_recovery_approved","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]

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
        ["20X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_AUDIT_ONLY","Content-audit selected-value draft","Audit-only next check.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after REQUEST_MORE_AUDIT load-smoke.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after REQUEST_MORE_AUDIT load-smoke.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after REQUEST_MORE_AUDIT load-smoke.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after REQUEST_MORE_AUDIT load-smoke.",False],
    ],columns=["next_step","name","purpose","allowed_after_20w_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["selected_value_draft_load_smoke_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_content_audit_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN20V
    inputs={"backup_manifest":root/BACKUP,"summary_20v":p/"gold_v2_20v_tier2_source_identity_human_decision_selected_value_draft_summary.json","draft_20v":p/"gold_v2_20v_selected_value_draft.json","checks_20v":p/"gold_v2_20v_draft_checks.csv","gates_20v":p/"gold_v2_20v_required_next_gates.csv","safety_20v":p/"gold_v2_20v_safety_matrix.csv","report_20v":p/"GOLD_V2_20V_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_20w_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("20W-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_20w_load_checks.csv",c); wc(out/"gold_v2_20w_safety_matrix.csv",s); wc(out/"gold_v2_20w_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"20W_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"load_smoke_passed":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_20W_INPUTS"}
        wj(out/"gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    summ=rj(inputs["summary_20v"]); draft=rj(inputs["draft_20v"]); checks=rc(inputs["checks_20v"]); ng=rc(inputs["gates_20v"]); sf=rc(inputs["safety_20v"])
    false_draft=sum(int(bool(draft.get(k,False))) for k in FALSE_DRAFT)
    false_sum=sum(int(bool(summ.get(k,False))) for k in FALSE_SUM)+sum(int(bool(v)) for v in summ.get("external_actions",{}).values())
    load=pd.DataFrame([{"field":"draft_status","observed":draft.get("draft_status")},{"field":"selected_value","observed":draft.get("selected_value")},{"field":"decision_value","observed":draft.get("decision_value")},{"field":"source_recovery_approved","observed":draft.get("source_recovery_approved")},{"field":"script_executes_action","observed":draft.get("script_executes_action")}]); wc(out/"gold_v2_20w_draft_load_audit.csv",load)
    rows=pd.DataFrame([
        chk("20W-C001","20V status",summ.get("status"),EXPECTED,summ.get("status")==EXPECTED),
        chk("20W-C002","20V draft_ready",summ.get("draft_ready"),True,bool(summ.get("draft_ready",False))),
        chk("20W-C003","20V total_stop_rows",summ.get("total_stop_rows"),0,summ.get("total_stop_rows")==0),
        chk("20W-C004","20V selected_value",summ.get("selected_value"),SELECTED,summ.get("selected_value")==SELECTED),
        chk("20W-C005","20V decision_value",summ.get("decision_value"),SELECTED,summ.get("decision_value")==SELECTED),
        chk("20W-C006","20V checks/safety STOP rows",sc(checks)+sc(sf),0,sc(checks)+sc(sf)==0),
        chk("20W-C007","20V forbidden gates allowed",forbid_gates(ng,"allowed_after_20v_success"),0,forbid_gates(ng,"allowed_after_20v_success")==0),
        chk("20W-C008","20V forbidden summary flags true",false_sum,0,false_sum==0),
        chk("20W-C009","draft status",draft.get("draft_status"),"SELECTED_VALUE_DRAFT_ONLY_NOT_SOURCE_RECOVERY_APPROVAL",draft.get("draft_status")=="SELECTED_VALUE_DRAFT_ONLY_NOT_SOURCE_RECOVERY_APPROVAL"),
        chk("20W-C010","draft selected_value",draft.get("selected_value"),SELECTED,draft.get("selected_value")==SELECTED),
        chk("20W-C011","draft decision_value",draft.get("decision_value"),SELECTED,draft.get("decision_value")==SELECTED),
        chk("20W-C012","draft forbidden flags true",false_draft,0,false_draft==0),
        chk("20W-C013","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "20W_STOP_REVIEW_SELECTED_VALUE_DRAFT_LOAD_SMOKE_OUTPUTS"; s=safety(ok); g=gates(ok)
    wc(out/"gold_v2_20w_load_checks.csv",rows); wc(out/"gold_v2_20w_safety_matrix.csv",s); wc(out/"gold_v2_20w_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"load_smoke_passed":ok,"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"20X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_SELECTED_VALUE_DRAFT_CONTENT_AUDIT_AUDIT_ONLY" if ok else "STOP_REVIEW_20W_OUTPUTS"}
    wj(out/"gold_v2_20w_tier2_source_identity_human_decision_selected_value_draft_load_smoke_summary.json",sm)
    rep=["# GOLD V2 20W TIER2 selected human decision value draft load-smoke audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 20W load-smoked the selected value draft: `REQUEST_MORE_AUDIT`.","- This remains not source recovery approval and does not permit source recovery execution.","- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.","","## Draft load audit",md(load),"","## Load checks",md(rows),"","## Next gates",md(g),"","## Safety",md(s)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
