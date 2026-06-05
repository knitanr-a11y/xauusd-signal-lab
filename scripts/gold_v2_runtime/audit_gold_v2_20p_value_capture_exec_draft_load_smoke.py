#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="20P_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR="gold_v2_20p_tier2_source_identity_human_decision_value_capture_execution_draft_load_smoke_audit_only"
IN20O="gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_audit_only"
REPORT="GOLD_V2_20P_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_20P_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBID={"ACTUAL_DECISION_COLLECTION","SOURCE_IDENTITY_FINALIZATION","SOURCE_RECOVERY","LIVE","FINAL_SIGNAL"}
FALSE_KEYS=["decision_value_collected","decision_collected","decision_made","approval_granted","actual_decision_collection_allowed","actual_decision_collection_completed","signal_conditions_changed","source_recovery_executed","source_identity_finalized","source_identity_recovered","ledger_is_source_of_truth","live_or_final_implementation_allowed","oh_lc_replay_allowed","live_enabled","final_signal_allowed","no_signal_discord_notified"]
FALSE_DRAFT=["actual_decision_value_collected","actual_decision_collection_completed","approval_granted","source_recovery_allowed","source_identity_finalization_allowed","source_identity_recovery_allowed","ledger_source_of_truth_promotion_allowed","oh_lc_replay_allowed","live_evaluator_allowed","final_signal_allowed","discord_send_allowed","no_signal_discord_send_allowed","mt5_order_allowed","ai_api_allowed","live_hook_allowed","signal_conditions_change_allowed","script_executes_action"]

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
        ["20Q","TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_CONTENT_AUDIT_ONLY","Content-audit the still-UNSET execution draft only.",bool(ok)],
        ["ACTUAL_DECISION_COLLECTION","TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION","Still blocked after 20P.",False],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 20P.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 20P.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 20P.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 20P.",False],
    ],columns=["next_step","name","purpose","allowed_after_20p_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["execution_draft_load_smoke_only",True,True,"PASS"],["decision_value","UNSET","UNSET","PASS"],["decision_value_collected",False,False,"PASS"],["decision_collected",False,False,"PASS"],["decision_made",False,False,"PASS"],["approval_granted",False,False,"PASS"],["actual_decision_collection_completed",False,False,"PASS"],["actual_decision_collection_allowed",False,False,"PASS"],["signal_conditions_changed",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_gate_20q_only_after_success",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN20O
    inputs={"backup_manifest":root/BACKUP,"summary_20o":p/"gold_v2_20o_tier2_source_identity_human_decision_value_capture_execution_draft_summary.json","draft_20o":p/"gold_v2_20o_execution_draft.json","checks_20o":p/"gold_v2_20o_execution_draft_checks.csv","gates_20o":p/"gold_v2_20o_required_next_gates.csv","safety_20o":p/"gold_v2_20o_safety_matrix.csv","report_20o":p/"GOLD_V2_20O_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_20p_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("20P-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_20p_load_checks.csv",c); wc(out/"gold_v2_20p_safety_matrix.csv",s); wc(out/"gold_v2_20p_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"20P_STOP_MISSING_INPUTS","audit_only":True,"draft_load_smoke_passed":False,"decision_value":"UNSET","total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_20P_INPUTS"}
        wj(out/"gold_v2_20p_tier2_source_identity_human_decision_value_capture_execution_draft_load_smoke_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    summ=rj(inputs["summary_20o"]); draft=rj(inputs["draft_20o"]); checks=rc(inputs["checks_20o"]); ng=rc(inputs["gates_20o"]); sf=rc(inputs["safety_20o"])
    false_sum=sum(int(bool(summ.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in summ.get("external_actions",{}).values())
    draft_restricted=sum(int(bool(draft.get(k,False))) for k in FALSE_DRAFT)
    load_audit=pd.DataFrame([[summ.get("status"),draft.get("draft_status"),draft.get("decision_value"),len(draft.get("allowed_decision_values",[]))]],columns=["summary_status","draft_status","decision_value","allowed_values_in_draft"])
    wc(out/"gold_v2_20p_draft_load_audit.csv",load_audit)
    rows=pd.DataFrame([
        chk("20P-C001","20O status",summ.get("status"),EXPECTED,summ.get("status")==EXPECTED),
        chk("20P-C002","20O execution_draft_ready",summ.get("execution_draft_ready"),True,bool(summ.get("execution_draft_ready",False))),
        chk("20P-C003","20O total_stop_rows",summ.get("total_stop_rows"),0,summ.get("total_stop_rows")==0),
        chk("20P-C004","20O decision_value",summ.get("decision_value"),"UNSET",summ.get("decision_value")=="UNSET"),
        chk("20P-C005","20O forbidden summary flags true",false_sum,0,false_sum==0),
        chk("20P-C006","20O checks/safety STOP rows",sc(checks)+sc(sf),0,sc(checks)+sc(sf)==0),
        chk("20P-C007","20O forbidden gates allowed",forbid_gates(ng,"allowed_after_20o_success"),0,forbid_gates(ng,"allowed_after_20o_success")==0),
        chk("20P-C008","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
        chk("20P-C009","draft_status",draft.get("draft_status"),"EXECUTION_DRAFT_ONLY_NOT_A_DECISION",draft.get("draft_status")=="EXECUTION_DRAFT_ONLY_NOT_A_DECISION"),
        chk("20P-C010","draft decision_value",draft.get("decision_value"),"UNSET",draft.get("decision_value")=="UNSET"),
        chk("20P-C011","draft allowed value rows",len(draft.get("allowed_decision_values",[])),">=4",len(draft.get("allowed_decision_values",[]))>=4),
        chk("20P-C012","draft restricted true flags",draft_restricted,0,draft_restricted==0),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "20P_STOP_REVIEW_VALUE_CAPTURE_EXECUTION_DRAFT_LOAD_SMOKE_OUTPUTS"; s=safety(ok); g=gates(ok)
    wc(out/"gold_v2_20p_load_checks.csv",rows); wc(out/"gold_v2_20p_safety_matrix.csv",s); wc(out/"gold_v2_20p_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"draft_load_smoke_passed":ok,"draft_status":draft.get("draft_status"),"decision_value":"UNSET","decision_value_collected":False,"decision_collected":False,"decision_made":False,"approval_granted":False,"actual_decision_collection_allowed":False,"actual_decision_collection_completed":False,"allowed_value_rows":len(draft.get("allowed_decision_values",[])),"total_stop_rows":int(total),"signal_conditions_changed":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"next_recommended_step":"20Q_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_EXECUTION_DRAFT_CONTENT_AUDIT_ONLY" if ok else "STOP_REVIEW_20P_OUTPUTS"}
    wj(out/"gold_v2_20p_tier2_source_identity_human_decision_value_capture_execution_draft_load_smoke_summary.json",sm)
    rep=["# GOLD V2 20P TIER2 source identity human decision value capture execution draft load-smoke audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 20P load-smoked the still-UNSET actual decision value capture execution draft only.","- No actual decision value was collected and no approval was made by this script.","- Signal conditions, source recovery, identity finalization/recovery, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.","","## Load checks",md(rows),"","## Draft load audit",md(load_audit),"","## Next gates",md(g),"","## Safety",md(s)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
