#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C10B_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY"
PASS_STATUS = "COREB_FILTER_REPLAY_EXECUTION_DECISION_COMPLETED_AUDIT_ONLY_25C10_READY"
STOP_STATUS = "25C10B_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C10A = "gold_v2_25c10a_coreb_unique_origin_metric_derivation_audit_only"
OUT_DIR = "gold_v2_25c10b_coreb_filter_replay_execution_decision_audit_only"
SAFETY_FLAGS = {"source_recovery_execution_allowed_now":False,"source_mutation_allowed":False,"source_identity_finalization_allowed_now":False,"live_evaluator_final_signal_allowed":False,"final_signal_allowed":False,"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False,"no_signal_discord_notification_allowed":False,"old_gold_disc8_quarantined":True,"source_recovery_chain_status":"PAUSED_AT_24AF"}

def parse_args(argv: Optional[Sequence[str]]=None)->argparse.Namespace:
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", default=None); return p.parse_args(argv)
def repo_root()->Path: return Path(__file__).resolve().parents[2]
def files_dir_from_repo()->Path:
    r=repo_root(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx_outputs()->Path: return files_dir_from_repo()/"FX_OUTPUTS"
def lp(path:Path)->Path:
    if os.name!="nt": return path
    s=str(path)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def read_csv(path:Path)->pd.DataFrame:
    last=None
    for enc in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as e: last=e
    raise RuntimeError(f"Could not read {path}: {last}")
def read_json(path:Path)->dict[str,Any]: return json.loads(lp(path).read_text(encoding="utf-8-sig"))
def write_csv(path:Path, df:pd.DataFrame)->None:
    lp(path.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(path), index=False, encoding="utf-8-sig")
def write_json(path:Path, obj:dict[str,Any])->None:
    lp(path.parent).mkdir(parents=True, exist_ok=True); lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
def md_table(df:pd.DataFrame, max_rows:int=80)->str:
    if df.empty: return "_No rows._"
    v=df.head(max_rows); cols=list(v.columns)
    lines=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in cols)+" |")
    if len(df)>max_rows: lines.append(f"| ... | truncated {len(df)-max_rows} more rows |"+" |"*max(0,len(cols)-2))
    return "\n".join(lines)

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_UNIQUE_ORIGIN_METRIC_DERIVED_AUDIT_ONLY_FILTER_REPLAY_STILL_BLOCKED_PENDING_REVIEW": p.append("25C10A status mismatch")
    if not bool(s.get("metric_derivation_only")): p.append("25C10A metric_derivation_only not true")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in_dir=fx_outputs()/IN25C10A
    req={"25c10a_summary":in_dir/"02_25c10a_coreb_unique_origin_metric_derivation_summary.json","distribution":in_dir/"05_25c10a_unique_origin_distribution.csv","readiness":in_dir/"06_25c10a_filter_readiness_after_derivation.csv","gates":in_dir/"07_25c10a_metric_derivation_gate_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c10b_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c10b_coreb_filter_replay_execution_decision_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c10a_summary"]); problems=safety_problems(s)
    if problems:
        write_json(out_dir/"02_25c10b_coreb_filter_replay_execution_decision_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    dist=read_csv(req["distribution"]); ready=read_csv(req["readiness"]); gates_in=read_csv(req["gates"])
    active=int(s.get("active_entry_rows",0)); ge2=int(s.get("entries_unique_origins_ge2",0)); ge3=int(s.get("entries_unique_origins_ge3",0))
    metric_review=pd.DataFrame([
        {"metric":"active_entry_rows","observed":active,"required":">0","status":"PASS" if active>0 else "BLOCKED"},
        {"metric":"entries_unique_origins_ge2","observed":ge2,"required":">0 for unique_origins>=2 filters","status":"PASS" if ge2>0 else "BLOCKED"},
        {"metric":"entries_unique_origins_ge3","observed":ge3,"required":">0 for unique_origins>=3 filters","status":"PASS" if ge3>0 else "BLOCKED"},
    ])
    write_csv(out_dir/"04_25c10b_metric_review_matrix.csv", metric_review)
    ready_bool=ready.copy()
    for c in ["filter_replay_ready_after_25c10a","same_count_metric_available","unique_origin_metric_available_after_25c10a"]:
        if c in ready_bool.columns: ready_bool[c]=ready_bool[c].astype(str).str.lower().isin(["true","1","yes"])
    total_filters=len(ready_bool); ready_filters=int(ready_bool["filter_replay_ready_after_25c10a"].sum()) if "filter_replay_ready_after_25c10a" in ready_bool.columns else 0
    readiness_matrix=pd.DataFrame([
        {"metric":"filter_contract_rows","observed":total_filters,"required":">0","status":"PASS" if total_filters>0 else "BLOCKED"},
        {"metric":"ready_filter_contract_rows","observed":ready_filters,"required":"all filter rows ready","status":"PASS" if total_filters>0 and ready_filters==total_filters else "BLOCKED"},
    ])
    write_csv(out_dir/"05_25c10b_filter_replay_readiness_matrix.csv", readiness_matrix)
    all_metric_pass=bool((metric_review["status"]=="PASS").all()); all_ready=bool(total_filters>0 and ready_filters==total_filters)
    allow_25c10=all_metric_pass and all_ready
    decision=pd.DataFrame([
        {"decision_id":"D001","question":"Is unique-origin metric derivation sufficient?","decision":"YES" if all_metric_pass else "NO","reason":f"active={active}; ge2={ge2}; ge3={ge3}"},
        {"decision_id":"D002","question":"Are all filter contracts ready after 25C10A?","decision":"YES" if all_ready else "NO","reason":f"ready={ready_filters}/{total_filters}"},
        {"decision_id":"D003","question":"May 25C10 filter replay be implemented next?","decision":"YES" if allow_25c10 else "NO","reason":"audit-only dry-run only; no live/source recovery"},
        {"decision_id":"D004","question":"Can CoreB be unblocked now?","decision":"NO","reason":"replay not executed and full parity false"},
    ])
    write_csv(out_dir/"06_25c10b_execution_decision_matrix.csv", decision)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C10_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY","allowed_now":allow_25c10,"purpose":"Execute filter-specific diagnostic replay; audit-only"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"07_25c10b_next_step_plan.csv", next_plan)
    unnecessary=["25C10A detail rows already processed","25C9 older summaries already processed","target ledger alone"]
    necessary=["01_25c10b_GOLD_V2_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY_REPORT.md","02_25c10b_coreb_filter_replay_execution_decision_summary.json","04_25c10b_metric_review_matrix.csv","05_25c10b_filter_replay_readiness_matrix.csv","06_25c10b_execution_decision_matrix.csv","07_25c10b_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c10b_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    status=PASS_STATUS if allow_25c10 else "COREB_FILTER_REPLAY_EXECUTION_DECISION_COMPLETED_AUDIT_ONLY_25C10_BLOCKED"
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"decision_only":True,"condition_changed":False,"intersection_only":True,"full_coreb_parity":False,"active_entry_rows":active,"entries_unique_origins_ge2":ge2,"entries_unique_origins_ge3":ge3,"ready_filter_contract_rows":ready_filters,"filter_contract_rows":total_filters,"filter_replay_allowed_next":allow_25c10,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C10_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY" if allow_25c10 else "REVIEW_25C10A_BLOCKERS","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c10b_coreb_filter_replay_execution_decision_summary.json", summary)
    report="\n".join(["# GOLD V2 25C10B CoreB filter replay execution decision audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## Finding","","25C10B reviews 25C10A metric derivation and decides whether 25C10 filter replay may be implemented next. It does not execute replay.","","## Metric review matrix","",md_table(metric_review),"","## Filter replay readiness matrix","",md_table(readiness_matrix),"","## Execution decision matrix","",md_table(decision),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c10b_GOLD_V2_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"filter_replay_allowed_next":allow_25c10,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
