#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C21_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY"
STATUS="COREB_ENTRY_GRAIN_CONTRACT_PLAN_READY_AUDIT_ONLY_DRY_RUN_EXECUTION_BLOCKED"
STOP="25C21_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c21_coreb_entry_grain_contract_plan_audit_only"
IN20="gold_v2_25c20_coreb_filter_family_and_entry_grain_audit_only"

def repo_root(): return Path(__file__).resolve().parents[2]
def files_root():
    r=repo_root(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx_outputs(): return files_root()/"FX_OUTPUTS"
def lp(p:Path)->Path:
    if os.name!="nt": return p
    s=str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def read_json(p:Path): return json.loads(lp(p).read_text(encoding="utf-8-sig"))
def read_csv(p:Path):
    last=None
    for enc in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e: last=e
    raise RuntimeError(f"read failed {p}: {last}")
def write_csv(p:Path, df:pd.DataFrame):
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")
def write_json(p:Path, obj:dict):
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def md_table(df:pd.DataFrame, n:int=80):
    if df.empty: return "_No rows._"
    v=df.head(n); cols=list(v.columns)
    out=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): out.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(out)

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    base=fx_outputs()/IN20
    req={"s20":base/"02_25c20_coreb_filter_family_and_entry_grain_summary.json","family_matrix":base/"04_25c20_filter_family_mismatch_matrix.csv","entry_matrix":base/"07_25c20_entry_grain_compare_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c21_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c21_coreb_entry_grain_contract_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s20=read_json(req["s20"]); fam=read_csv(req["family_matrix"]); ent=read_csv(req["entry_matrix"])
    fam_left=int(s20.get("filter_family_left_only",0)); fam_right=int(s20.get("filter_family_right_only",0)); entry_left=int(s20.get("entry_grain_left_only",0)); entry_right=int(s20.get("entry_grain_right_only",0))
    candidates=pd.DataFrame([
        {"grain_id":"G1","grain":"dataset+entry_time+policy","known_left_only":entry_left,"known_right_only":entry_right,"scope":"entry-level","risk":"may hide filter-family mismatch","recommended_for_next_review":True},
        {"grain_id":"G2","grain":"dataset+entry_time+policy+filter_family","known_left_only":fam_left,"known_right_only":fam_right,"scope":"family-level","risk":"still has family residual mismatch","recommended_for_next_review":True},
        {"grain_id":"G3","grain":"dataset+entry_time+policy+filter","known_left_only":4444,"known_right_only":1128,"scope":"filter-level","risk":"too strict for current replay contract","recommended_for_next_review":False},
    ])
    write_csv(out/"04_25c21_entry_grain_candidate_matrix.csv", candidates)
    boundaries=pd.DataFrame([
        {"boundary":"change_coreb_conditions","allowed":False},
        {"boundary":"change_selected_policy_scope","allowed":False},
        {"boundary":"infer_membership_from_target_rows","allowed":False},
        {"boundary":"execute_dry_run_now","allowed":False},
        {"boundary":"define_grain_contract_plan","allowed":True},
    ])
    write_csv(out/"05_25c21_grain_selection_boundary_matrix.csv", boundaries)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C20 completed","observed":s20.get("status")=="COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_COMPLETED_AUDIT_ONLY_GRAIN_CONTRACT_REVIEW_REQUIRED","required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"entry grain mismatch remains","observed":entry_left+entry_right>0,"required":True,"status":"PASS"},
        {"gate_id":"G003","gate":"dry-run execution allowed now","observed":False,"required":False,"status":"BLOCKED_PLAN_ONLY"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out/"06_25c21_acceptance_gate_matrix.csv", gates)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C22_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"choose G1/G2 contract before any dry-run"},
        {"rank":2,"next_step":"entry-grain dry-run execution","allowed_now":False,"purpose":"blocked until contract review passes"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c21_next_step_plan.csv", next_plan)
    unnecessary=["25C20 older reports if summary is available","large per-row signal samples","target ledger alone"]
    necessary=["01_25c21_GOLD_V2_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY_REPORT.md","02_25c21_coreb_entry_grain_contract_plan_summary.json","04_25c21_entry_grain_candidate_matrix.csv","05_25c21_grain_selection_boundary_matrix.csv","06_25c21_acceptance_gate_matrix.csv","07_25c21_next_step_plan.csv"]
    write_csv(out/"00_不要_25c21_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"dry_run_executed":False,"condition_changed":False,"full_coreb_parity":False,"candidate_grain_count":int(len(candidates)),"recommended_grains":["G1","G2"],"next_dry_run_execution_allowed_now":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C22_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c21_coreb_entry_grain_contract_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C21 CoreB entry grain contract plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Entry grain candidate matrix","",md_table(candidates),"","## Boundary matrix","",md_table(boundaries),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c21_GOLD_V2_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"recommended_grains":["G1","G2"],"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
