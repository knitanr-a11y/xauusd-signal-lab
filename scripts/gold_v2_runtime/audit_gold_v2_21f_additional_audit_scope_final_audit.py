#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP="21F_ADDITIONAL_AUDIT_SCOPE_FINAL_AUDIT_AUDIT_ONLY"
OUT_DIR="gold_v2_21f_additional_audit_scope_final_audit_audit_only"
IN21E="gold_v2_21e_additional_audit_scope_reconciliation_audit_only"
REPORT="GOLD_V2_21F_ADDITIONAL_AUDIT_SCOPE_FINAL_AUDIT_AUDIT_ONLY_REPORT.md"
SELECTED="REQUEST_MORE_AUDIT"
SUCCESS="ADDITIONAL_AUDIT_SCOPE_FINAL_AUDIT_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED="ADDITIONAL_AUDIT_SCOPE_RECONCILIATION_PASSED_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
BACKUP="docs/gold_v2/GOLD_V2_21F_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
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
        ["21G_ADDITIONAL_AUDIT_EXECUTION_READ_ONLY_REPORT_AUDIT_ONLY","Create read-only additional audit report","Audit-only next step.",bool(ok)],
        ["SOURCE_IDENTITY_FINALIZATION","TIER2_SOURCE_IDENTITY_FINALIZATION","Blocked after 21F.",False],
        ["SOURCE_RECOVERY","TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION","Blocked after 21F.",False],
        ["LIVE","MEDIUM_FULL_SET_LIVE_EVALUATOR","Blocked after 21F.",False],
        ["FINAL_SIGNAL","MEDIUM_FINAL_SIGNAL","Blocked after 21F.",False],
    ],columns=["next_step","name","purpose","allowed_after_21f_success"])
def safety(ok:bool)->pd.DataFrame:
    rows=[["audit_only",True,True,"PASS"],["additional_audit_scope_final_audit_only",True,True,"PASS"],["selected_value",SELECTED,SELECTED,"PASS"],["source_recovery_approved",False,False,"PASS"],["source_recovery_executed",False,False,"PASS"],["source_identity_finalized",False,False,"PASS"],["source_identity_recovered",False,False,"PASS"],["live_or_final_implementation_allowed",False,False,"PASS"],["discord_send_allowed",False,False,"PASS"],["mt5_order_allowed",False,False,"PASS"],["ai_api_allowed",False,False,"PASS"],["live_hook_allowed",False,False,"PASS"],["next_read_only_report_allowed",bool(ok),bool(ok),"PASS"]]
    return pd.DataFrame(rows,columns=["safety_item","observed","expected","status"])

def main()->int:
    root,base=rr(),fx(); out=base/OUT_DIR; lp(out).mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc).isoformat(); p=base/IN21E
    inputs={"backup_manifest":root/BACKUP,"summary_21e":p/"gold_v2_21e_additional_audit_scope_reconciliation_summary.json","checks_21e":p/"gold_v2_21e_reconciliation_checks.csv","gates_21e":p/"gold_v2_21e_required_next_gates.csv","safety_21e":p/"gold_v2_21e_safety_matrix.csv","report_21e":p/"GOLD_V2_21E_ADDITIONAL_AUDIT_SCOPE_RECONCILIATION_AUDIT_ONLY_REPORT.md"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists()} for k,v in inputs.items()]); wc(out/"gold_v2_21f_input_audit.csv",ia)
    if not bool(ia["exists"].all()):
        c=pd.DataFrame([chk("21F-C000","required inputs exist",False,True,False)]); s=safety(False); g=gates(False)
        wc(out/"gold_v2_21f_final_checks.csv",c); wc(out/"gold_v2_21f_safety_matrix.csv",s); wc(out/"gold_v2_21f_required_next_gates.csv",g)
        sm={"created_utc":now,"step":STEP,"status":"21F_STOP_MISSING_INPUTS","audit_only":True,"selected_value":SELECTED,"final_audit_passed":False,"total_stop_rows":1,"next_recommended_step":"STOP_REVIEW_21F_INPUTS"}
        wj(out/"gold_v2_21f_additional_audit_scope_final_audit_summary.json",sm); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 2
    s21=rj(inputs["summary_21e"]); checks=rc(inputs["checks_21e"]); gates21=rc(inputs["gates_21e"]); safety21=rc(inputs["safety_21e"])
    false_21=sum(int(bool(s21.get(k,False))) for k in FALSE_KEYS)+sum(int(bool(v)) for v in s21.get("external_actions",{}).values())
    rows=pd.DataFrame([
        chk("21F-C001","21E status",s21.get("status"),EXPECTED,s21.get("status")==EXPECTED),
        chk("21F-C002","21E scope_reconciliation_passed",s21.get("scope_reconciliation_passed"),True,bool(s21.get("scope_reconciliation_passed",False))),
        chk("21F-C003","21E selected_value",s21.get("selected_value"),SELECTED,s21.get("selected_value")==SELECTED),
        chk("21F-C004","21E total_stop_rows",s21.get("total_stop_rows"),0,s21.get("total_stop_rows")==0),
        chk("21F-C005","21E scope_theme_count",s21.get("scope_theme_count"),5,s21.get("scope_theme_count")==5),
        chk("21F-C006","21E checks/safety STOP rows",sc(checks)+sc(safety21),0,sc(checks)+sc(safety21)==0),
        chk("21F-C007","21E forbidden gates allowed",forbid_gates(gates21,"allowed_after_21e_success"),0,forbid_gates(gates21,"allowed_after_21e_success")==0),
        chk("21F-C008","21E forbidden summary flags true",false_21,0,false_21==0),
        chk("21F-C009","backup manifest exists",lp(inputs["backup_manifest"]).exists(),True,lp(inputs["backup_manifest"]).exists()),
    ])
    total=sc(rows); ok=total==0; status=SUCCESS if ok else "21F_STOP_REVIEW_ADDITIONAL_AUDIT_SCOPE_FINAL_AUDIT_OUTPUTS"; smat=safety(ok); g=gates(ok)
    wc(out/"gold_v2_21f_final_checks.csv",rows); wc(out/"gold_v2_21f_safety_matrix.csv",smat); wc(out/"gold_v2_21f_required_next_gates.csv",g)
    sm={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_value":SELECTED,"decision_value":SELECTED,"final_audit_passed":ok,"source_recovery_approved":False,"source_recovery_executed":False,"source_identity_finalized":False,"source_identity_recovered":False,"ledger_is_source_of_truth":False,"live_or_final_implementation_allowed":False,"oh_lc_replay_allowed":False,"live_enabled":False,"final_signal_allowed":False,"external_actions":{"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False},"no_signal_discord_notified":False,"total_stop_rows":int(total),"next_recommended_step":"21G_ADDITIONAL_AUDIT_EXECUTION_READ_ONLY_REPORT_AUDIT_ONLY" if ok else "STOP_REVIEW_21F_OUTPUTS"}
    wj(out/"gold_v2_21f_additional_audit_scope_final_audit_summary.json",sm)
    rep=["# GOLD V2 21F additional audit scope final audit audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Final decision","- 21F final-audited the additional audit scope after 21E.","- This final audit does not enable live, final, external, or recovery paths.","","## Final checks",md(rows),"","## Next gates",md(g),"","## Safety",md(smat)]
    wt(out/REPORT,"\n".join(rep)); print(json.dumps(sm,ensure_ascii=False,indent=2)); return 0 if ok else 2

if __name__=="__main__": raise SystemExit(main())
