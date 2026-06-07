#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C23_COREB_G1_ENTRY_LEVEL_REVIEW_PLAN_AUDIT_ONLY"
STATUS="COREB_G1_ENTRY_LEVEL_REVIEW_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED"
STOP="25C23_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c23_coreb_g1_entry_level_review_plan_audit_only"
IN22="gold_v2_25c22_coreb_entry_grain_contract_review_audit_only"

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
    base=fx_outputs()/IN22
    req={"s22":base/"02_25c22_coreb_entry_grain_contract_review_summary.json","selected_grain":base/"05_25c22_selected_grain_contract.csv","decision":base/"06_25c22_grain_contract_decision_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c23_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c23_coreb_g1_entry_level_review_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s22=read_json(req["s22"]); grain=read_csv(req["selected_grain"])
    input_contract=pd.DataFrame([
        {"input_id":"I001","role":"selected replay signal rows","source":"25C10 filter replay signal rows","required":True},
        {"input_id":"I002","role":"target ledger rows","source":"25B3 rr125_top_ledgers.csv via file audit","required":True},
        {"input_id":"I003","role":"selected policy scope","source":"25C15 selected output policy contract","required":True},
        {"input_id":"I004","role":"feature overlap window","source":"25C7 feature_min_time / feature_max_time","required":True},
    ])
    write_csv(out/"04_25c23_g1_input_contract.csv", input_contract)
    key_contract=pd.DataFrame([
        {"key_order":1,"key_column":"dataset","required":True,"normalization":"string"},
        {"key_order":2,"key_column":"entry_time","required":True,"normalization":"string timestamp as emitted"},
        {"key_order":3,"key_column":"policy","required":True,"normalization":"string"},
    ])
    write_csv(out/"05_25c23_g1_compare_key_contract.csv", key_contract)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"G1 selected in 25C22","required":True,"status":"PASS" if s22.get("selected_grain")=="G1" else "BLOCKED"},
        {"gate_id":"G002","gate":"dry-run execution in 25C23","required":False,"status":"BLOCKED_PLAN_ONLY"},
        {"gate_id":"G003","gate":"CoreB live evaluator unblock","required":False,"status":"BLOCKED"},
        {"gate_id":"G004","gate":"source recovery execution","required":False,"status":"BLOCKED"},
    ])
    write_csv(out/"06_25c23_g1_acceptance_gate_matrix.csv", gates)
    stops=pd.DataFrame([
        {"stop_id":"S001","condition":"missing required input","action":"stop"},
        {"stop_id":"S002","condition":"selected grain is not G1","action":"stop"},
        {"stop_id":"S003","condition":"selected policy scope missing","action":"stop"},
        {"stop_id":"S004","condition":"target rows missing required key columns","action":"stop"},
        {"stop_id":"S005","condition":"replay rows missing required key columns","action":"stop"},
    ])
    write_csv(out/"07_25c23_g1_stop_condition_matrix.csv", stops)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C24_COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_AUDIT_ONLY","allowed_now":False,"purpose":"requires explicit acceptance of 25C23 plan"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c23_next_step_plan.csv", nxt)
    unnecessary=["25C22 older reports if summary is available","large row samples","target ledger alone"]
    necessary=["01_25c23_GOLD_V2_COREB_G1_ENTRY_LEVEL_REVIEW_PLAN_AUDIT_ONLY_REPORT.md","02_25c23_coreb_g1_entry_level_review_plan_summary.json","04_25c23_g1_input_contract.csv","05_25c23_g1_compare_key_contract.csv","06_25c23_g1_acceptance_gate_matrix.csv","07_25c23_g1_stop_condition_matrix.csv","08_25c23_next_step_plan.csv"]
    write_csv(out/"00_不要_25c23_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"dry_run_executed":False,"condition_changed":False,"full_coreb_parity":False,"selected_grain":"G1","g1_compare_key":["dataset","entry_time","policy"],"next_dry_run_execution_allowed_now":False,"requires_human_acceptance_before_25c24":True,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"HUMAN_ACCEPT_25C23_PLAN_BEFORE_25C24_DRY_RUN","total_stop_rows":0}
    write_json(out/"02_25c23_coreb_g1_entry_level_review_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C23 CoreB G1 entry-level review plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## G1 input contract","",md_table(input_contract),"","## G1 compare key contract","",md_table(key_contract),"","## Acceptance gates","",md_table(gates),"","## Stop conditions","",md_table(stops),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c23_GOLD_V2_COREB_G1_ENTRY_LEVEL_REVIEW_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"selected_grain":"G1","requires_human_acceptance_before_25c24":True,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
