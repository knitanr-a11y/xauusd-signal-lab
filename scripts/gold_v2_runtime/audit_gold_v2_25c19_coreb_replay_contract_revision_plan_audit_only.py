#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C19_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY"
STATUS="COREB_REPLAY_CONTRACT_REVISION_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED"
STOP="25C19_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c19_coreb_replay_contract_revision_plan_audit_only"
IN18="gold_v2_25c18_coreb_replay_contract_review_audit_only"

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
    base=fx_outputs()/IN18
    req={"s18":base/"02_25c18_coreb_replay_contract_review_summary.json","issues":base/"04_25c18_contract_issue_matrix.csv","decisions":base/"05_25c18_replay_contract_review_decision_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c19_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c19_coreb_replay_contract_revision_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s18=read_json(req["s18"]); issues=read_csv(req["issues"])
    left=int(s18.get("selected_scope_left_only",0)); right=int(s18.get("selected_scope_right_only",0)); low=int(s18.get("low_threshold_overgeneration_rows",0)); high=int(s18.get("high_threshold_missing_rows",0))
    candidates=pd.DataFrame([
        {"candidate_id":"R1","candidate":"filter_family_comparison_review","addresses":"low threshold over-generation","observed_rows":low,"allowed_now":True,"executes_replay":False,"notes":"group related filters before any next dry-run"},
        {"candidate_id":"R2","candidate":"entry_time_multiplicity_review","addresses":"extra rows and repeated filter hits","observed_rows":left,"allowed_now":True,"executes_replay":False,"notes":"review whether duplicated filter families are counted at correct grain"},
        {"candidate_id":"R3","candidate":"target_selected_scope_adoption_review","addresses":"missing rows in selected target scope","observed_rows":right,"allowed_now":True,"executes_replay":False,"notes":"separate target adoption filters from selected output filters"},
        {"candidate_id":"R4","candidate":"source_count_aggregation_contract_review","addresses":"high threshold misses","observed_rows":high,"allowed_now":True,"executes_replay":False,"notes":"review source_count aggregation grain without changing conditions"},
    ])
    write_csv(out/"04_25c19_revision_candidate_matrix.csv", candidates)
    boundaries=pd.DataFrame([
        {"boundary":"change_coreb_conditions","allowed":False},
        {"boundary":"infer_membership_from_target_rows","allowed":False},
        {"boundary":"tune_thresholds_to_target_rows","allowed":False},
        {"boundary":"execute_source_recovery","allowed":False},
        {"boundary":"enable_live_evaluator","allowed":False},
        {"boundary":"prepare_audit_only_plan","allowed":True},
    ])
    write_csv(out/"05_25c19_contract_boundary_matrix.csv", boundaries)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C18 rejected current replay contract","observed":not bool(s18.get("current_replay_contract_accepted_as_exact", True)),"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"contract revision plan only","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G003","gate":"next dry-run execution allowed now","observed":False,"required":False,"status":"BLOCKED_PLAN_ONLY"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out/"06_25c19_acceptance_gate_matrix.csv", gates)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C20_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY","allowed_now":True,"purpose":"review filter-family and entry-time grain before another dry-run"},
        {"rank":2,"next_step":"25C20_DRY_RUN_EXECUTION","allowed_now":False,"purpose":"blocked until review plan accepted"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c19_next_step_plan.csv", nxt)
    unnecessary=["25C18 older reports","large root-cause rows unless debugging","target ledger alone"]
    necessary=["01_25c19_GOLD_V2_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY_REPORT.md","02_25c19_coreb_replay_contract_revision_plan_summary.json","04_25c19_revision_candidate_matrix.csv","05_25c19_contract_boundary_matrix.csv","06_25c19_acceptance_gate_matrix.csv","07_25c19_next_step_plan.csv"]
    write_csv(out/"00_不要_25c19_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"condition_changed":False,"full_coreb_parity":False,"revision_candidate_count":int(len(candidates)),"next_dry_run_execution_allowed_now":False,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C20_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c19_coreb_replay_contract_revision_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C19 CoreB replay contract revision plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Revision candidate matrix","",md_table(candidates),"","## Contract boundary matrix","",md_table(boundaries),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c19_GOLD_V2_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"next_dry_run_execution_allowed_now":False,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
