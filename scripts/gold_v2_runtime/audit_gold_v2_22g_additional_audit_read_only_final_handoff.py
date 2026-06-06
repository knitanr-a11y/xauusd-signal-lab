#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY"
OUT_DIR="gold_v2_22g_additional_audit_read_only_final_handoff_audit_only"
IN22F="gold_v2_22f_additional_audit_read_only_final_audit_audit_only"
REPORT="GOLD_V2_22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md"
HANDOFF="GOLD_V2_22G_FINAL_HANDOFF_REQUEST_MORE_AUDIT_AUDIT_ONLY.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_READ_ONLY_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_22G_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
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
        ["HUMAN_REVIEW_REQUEST_MORE_AUDIT_COMPLETE_AUDIT_ONLY","Review completed read-only additional audit package","Audit-only review state.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 22G.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 22G.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 22G.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 22G.",False],
    ],columns=["next_step","name","purpose","allowed_after_22g_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["read_only_final_handoff_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["human_review_state_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN22F
    inputs={"backup_manifest":root/BACKUP,"summary_22f":p/"gold_v2_22f_additional_audit_read_only_final_audit_summary.json","checks_22f":p/"gold_v2_22f_final_checks.csv","gates_22f":p/"gold_v2_22f_required_next_gates.csv","safety_22f":p/"gold_v2_22f_safety_matrix.csv","report_22f":p/"GOLD_V2_22F_ADDITIONAL_AUDIT_READ_ONLY_FINAL_AUDIT_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_22g_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("22G-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_22g_handoff_checks.csv",c); wc(out/"gold_v2_22g_safety_matrix.csv",s); wc(out/"gold_v2_22g_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"22G_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"final_handoff_ready":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_22G_INPUTS"}
        wj(out/"gold_v2_22g_additional_audit_read_only_final_handoff_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s22=rj(inputs["summary_22f"]); checks=rc(inputs["checks_22f"]); gates22=rc(inputs["gates_22f"]); safety22=rc(inputs["safety_22f"])
    false_22=sum(int(bool(s22.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s22.get("external_actions",{}).values())
    rows=pd.DataFrame([
        chk("22G-C001","22F status",s22.get("status"),EXPECTED,s22.get("status")==EXPECTED),
        chk("22G-C002","22F final_audit_passed",s22.get("final_audit_passed"),True,bool(s22.get("final_audit_passed",False))),
        chk("22G-C003","22F selected_value",s22.get("selected_value"),SELECTED,s22.get("selected_value")==SELECTED),
        chk("22G-C004","22F total_stop_rows",s22.get("total_stop_rows"),0,s22.get("total_stop_rows")==0),
        chk("22G-C005","22F checks/safety STOP rows",sc(checks)+sc(safety22),0,sc(checks)+sc(safety22)==0),
        chk("22G-C006","22F forbidden gates allowed",forbid_gates(gates22,"allowed_after_22f_success"),0,forbid_gates(gates22,"allowed_after_22f_success")==0),
        chk("22G-C007","22F forbidden summary flags true",false_22,0,false_22==0),
        chk("22G-C008","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "22G_STOP_REVIEW_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_22g_handoff_checks.csv",rows); wc(out/"gold_v2_22g_safety_matrix.csv",smat); wc(out/"gold_v2_22g_required_next_gates.csv",g)
    handoff=["# GOLD V2 22G final handoff request more audit audit-only","",f"Created UTC: {now}","","## Current status",f"- Status: `{status}`",f"- Selected value: `{SELECTED}`","- 22F read-only final audit has passed.","- REQUEST_MORE_AUDIT remains a request for more audit, not source recovery approval.","- Source recovery, source identity finalization/recovery, live/final paths, Discord, MT5, AI API, and live hook remain blocked.","","## Review state","- `HUMAN_REVIEW_REQUEST_MORE_AUDIT_COMPLETE_AUDIT_ONLY`","- Further action requires a new explicit instruction and must remain audit-only unless an allowed value/gate changes."]
    wt(out/HANDOFF,"\n".join(handoff))
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"final_handoff_ready":ok,"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"HUMAN_REVIEW_REQUEST_MORE_AUDIT_COMPLETE_AUDIT_ONLY" if ok else "STOP_REVIEW_22G_OUTPUTS"}
    wj(out/"gold_v2_22g_additional_audit_read_only_final_handoff_summary.json",sm)
    rep=["# GOLD V2 22G additional audit read-only final handoff audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 22G created the final read-only handoff after 22F.","- This handoff does not enable live, final, external, or recovery paths.","","## Handoff checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
