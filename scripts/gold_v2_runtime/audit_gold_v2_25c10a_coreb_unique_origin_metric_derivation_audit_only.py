#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C10A_COREB_UNIQUE_ORIGIN_METRIC_DERIVATION_AUDIT_ONLY"
PASS_STATUS = "COREB_UNIQUE_ORIGIN_METRIC_DERIVED_AUDIT_ONLY_FILTER_REPLAY_STILL_BLOCKED_PENDING_REVIEW"
STOP_STATUS = "25C10A_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C9 = "gold_v2_25c9_coreb_target_filter_contract_replay_plan_audit_only"
IN25C3 = "gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only"
OUT_DIR = "gold_v2_25c10a_coreb_unique_origin_metric_derivation_audit_only"
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
    if s.get("status")!="COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED": p.append("25C9 status mismatch")
    if not bool(s.get("plan_only")): p.append("25C9 plan_only not true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in9=fx_outputs()/IN25C9; in3=fx_outputs()/IN25C3
    req={"25c9_summary":in9/"02_25c9_coreb_target_filter_contract_replay_plan_summary.json","filter_plan":in9/"04_25c9_filter_contract_plan.csv","source_counts":in3/"07_25c3_source_universe_hit_counts_by_entry.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c10a_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c10a_coreb_unique_origin_metric_derivation_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c9_summary"]); problems=safety_problems(s)
    if problems:
        write_json(out_dir/"02_25c10a_coreb_unique_origin_metric_derivation_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    plan=read_csv(req["filter_plan"]); src=read_csv(req["source_counts"])
    if "origin_id" not in src.columns:
        write_json(out_dir/"02_25c10a_coreb_unique_origin_metric_derivation_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":["source_counts missing origin_id"],"total_stop_rows":1,**SAFETY_FLAGS}); return 2
    src["source_universe_hit_count"] = pd.to_numeric(src["source_universe_hit_count"], errors="coerce").fillna(0).astype(int)
    active=src[src["source_universe_hit_count"].gt(0)].copy()
    keys=["dataset","entry_time","policy"] if "policy" in src.columns else ["dataset","entry_time"]
    counts=active.groupby(keys, dropna=False).agg(unique_origin_count_by_entry_time=("origin_id", lambda x:int(pd.Series(x).astype(str).nunique())), active_source_rows=("origin_id","size"), source_count_by_entry_time=("source_universe_hit_count","sum")).reset_index()
    write_csv(out_dir/"04_25c10a_unique_origin_counts_by_entry_time.csv", counts)
    dist=pd.DataFrame([
        {"metric":"active_entry_rows","value":int(len(counts))},
        {"metric":"max_unique_origin_count_by_entry_time","value":int(counts["unique_origin_count_by_entry_time"].max()) if len(counts) else 0},
        {"metric":"entries_unique_origins_ge2","value":int(counts["unique_origin_count_by_entry_time"].ge(2).sum()) if len(counts) else 0},
        {"metric":"entries_unique_origins_ge3","value":int(counts["unique_origin_count_by_entry_time"].ge(3).sum()) if len(counts) else 0},
    ])
    write_csv(out_dir/"05_25c10a_unique_origin_distribution.csv", dist)
    fp=plan.copy()
    fp["requires_additional_unique_origin_derivation"] = fp["requires_additional_unique_origin_derivation"].astype(str).str.lower().isin(["true","1","yes"])
    fp["unique_origin_metric_available_after_25c10a"] = fp["requires_additional_unique_origin_derivation"]
    fp["same_count_metric_available"] = fp["required_same_count_metric"].astype(str).ne("NOT_REQUIRED")
    fp["filter_replay_ready_after_25c10a"] = True
    write_csv(out_dir/"06_25c10a_filter_readiness_after_derivation.csv", fp)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C9 status clean","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"origin_id available in source-count rows","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G003","gate":"unique origin metric derived","observed":len(counts)>0,"required":True,"status":"PASS" if len(counts)>0 else "BLOCKED"},
        {"gate_id":"G004","gate":"filter replay execution allowed now","observed":False,"required":False,"status":"BLOCKED_PENDING_REVIEW"},
        {"gate_id":"G005","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out_dir/"07_25c10a_metric_derivation_gate_matrix.csv", gates)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C10B_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY","allowed_now":True,"purpose":"Review 25C10A metric derivation and decide whether to run 25C10 filter replay"},
        {"rank":2,"next_step":"25C10_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY","allowed_now":False,"purpose":"Still blocked until 25C10A review/acceptance"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"08_25c10a_next_step_plan.csv", next_plan)
    unnecessary=["25C9 older summaries already processed","25C3 large row dumps unless debugging","target ledger alone"]
    necessary=["01_25c10a_GOLD_V2_COREB_UNIQUE_ORIGIN_METRIC_DERIVATION_AUDIT_ONLY_REPORT.md","02_25c10a_coreb_unique_origin_metric_derivation_summary.json","04_25c10a_unique_origin_counts_by_entry_time.csv","05_25c10a_unique_origin_distribution.csv","06_25c10a_filter_readiness_after_derivation.csv","07_25c10a_metric_derivation_gate_matrix.csv","08_25c10a_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c10a_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"metric_derivation_only":True,"condition_changed":False,"intersection_only":True,"full_coreb_parity":False,"active_entry_rows":int(len(counts)),"max_unique_origin_count_by_entry_time":int(counts["unique_origin_count_by_entry_time"].max()) if len(counts) else 0,"entries_unique_origins_ge2":int(counts["unique_origin_count_by_entry_time"].ge(2).sum()) if len(counts) else 0,"entries_unique_origins_ge3":int(counts["unique_origin_count_by_entry_time"].ge(3).sum()) if len(counts) else 0,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C10B_COREB_FILTER_REPLAY_EXECUTION_DECISION_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c10a_coreb_unique_origin_metric_derivation_summary.json", summary)
    report="\n".join(["# GOLD V2 25C10A CoreB unique origin metric derivation audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Finding","","25C10A derives unique_origin_count_by_entry_time. It does not execute filter replay or unblock CoreB.","","## Unique origin distribution","",md_table(dist),"","## Filter readiness after derivation","",md_table(fp),"","## Metric derivation gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c10a_GOLD_V2_COREB_UNIQUE_ORIGIN_METRIC_DERIVATION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"active_entry_rows":summary["active_entry_rows"],"entries_unique_origins_ge2":summary["entries_unique_origins_ge2"],"entries_unique_origins_ge3":summary["entries_unique_origins_ge3"],"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
