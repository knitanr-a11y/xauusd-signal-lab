#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C5_COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_AUDIT_ONLY"
PASS_STATUS = "COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED"
STOP_STATUS = "25C5_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C4 = "gold_v2_25c4_coreb_intersection_dry_run_review_audit_only"
IN25C3 = "gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only"
OUT_DIR = "gold_v2_25c5_coreb_intersection_dry_run_aggregated_revision_audit_only"
SAFETY_FLAGS = {
    "source_recovery_execution_allowed_now": False,
    "source_mutation_allowed": False,
    "source_identity_finalization_allowed_now": False,
    "live_evaluator_final_signal_allowed": False,
    "final_signal_allowed": False,
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "no_signal_discord_notification_allowed": False,
    "old_gold_disc8_quarantined": True,
    "source_recovery_chain_status": "PAUSED_AT_24AF",
}

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
def md_table(df:pd.DataFrame, max_rows:int=60)->str:
    if df.empty: return "_No rows._"
    v=df.head(max_rows); cols=list(v.columns)
    lines=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in cols)+" |")
    if len(df)>max_rows: lines.append(f"| ... | truncated {len(df)-max_rows} more rows |"+" |"*max(0,len(cols)-2))
    return "\n".join(lines)

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_INTERSECTION_DRY_RUN_REVIEW_COMPLETED_AUDIT_ONLY_AGGREGATION_REVISION_REQUIRED": p.append("25C4 status mismatch")
    if not bool(s.get("revision_required")): p.append("25C4 revision_required not true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in4=fx_outputs()/IN25C4; in3=fx_outputs()/IN25C3
    req={
        "25c4_summary":in4/"02_25c4_coreb_intersection_dry_run_review_summary.json",
        "source_counts":in3/"07_25c3_source_universe_hit_counts_by_entry.csv",
        "selected_hits":in3/"08_25c3_selected_rule_hit_rows.csv",
        "target_compare_25c3":in3/"10_25c3_target_compare_summary.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c5_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c5_coreb_intersection_dry_run_aggregated_revision_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c4_summary"]); problems=safety_problems(s)
    if problems:
        write_json(out_dir/"02_25c5_coreb_intersection_dry_run_aggregated_revision_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    src=read_csv(req["source_counts"]); sel=read_csv(req["selected_hits"])
    keys=["dataset","entry_time"]
    src["source_universe_hit_count"] = pd.to_numeric(src["source_universe_hit_count"], errors="coerce").fillna(0).astype(int)
    agg=src.groupby(keys, dropna=False).agg(source_universe_hit_count_by_entry_time=("source_universe_hit_count","sum"), source_universe_row_count=("source_universe_hit_count","size"), source_universe_max_row_count=("source_universe_hit_count","max")).reset_index()
    sel_agg=sel.groupby(keys, dropna=False).agg(selected_rule_hit_rows=("entry_time","size"), selected_candidate_ids=("candidate_id", lambda x:";".join(sorted(set(map(str,x)))[:20])), selected_policies=("policy", lambda x:";".join(sorted(set(map(str,x)))[:20]))).reset_index() if not sel.empty else pd.DataFrame(columns=keys+["selected_rule_hit_rows","selected_candidate_ids","selected_policies"])
    merged=agg.merge(sel_agg, on=keys, how="left")
    merged["selected_rule_hit_rows"] = pd.to_numeric(merged["selected_rule_hit_rows"], errors="coerce").fillna(0).astype(int)
    merged["selected_rule_hit_by_entry_time"] = merged["selected_rule_hit_rows"].gt(0)
    merged["source_count_ge15_by_entry_time"] = merged["source_universe_hit_count_by_entry_time"].ge(15)
    signals=merged[merged["selected_rule_hit_by_entry_time"] & merged["source_count_ge15_by_entry_time"]].copy()
    signals["intersection_only"] = True; signals["full_coreb_parity"] = False; signals["condition_changed"] = False
    write_csv(out_dir/"04_25c5_aggregated_entry_signal_rows.csv", signals)
    dist=pd.DataFrame([
        {"metric":"entry_rows", "value":int(len(merged))},
        {"metric":"selected_entry_rows", "value":int(merged["selected_rule_hit_by_entry_time"].sum())},
        {"metric":"source_count_ge15_entry_rows", "value":int(merged["source_count_ge15_by_entry_time"].sum())},
        {"metric":"aggregated_signal_entry_rows", "value":int(len(signals))},
        {"metric":"max_source_count_by_entry_time", "value":int(merged["source_universe_hit_count_by_entry_time"].max()) if len(merged) else 0},
    ])
    write_csv(out_dir/"05_25c5_aggregated_entry_distribution.csv", dist)
    # target compare with target unavailable here intentionally limited to 25C3 compare snapshot; exact target comparison deferred if needed
    compare=pd.DataFrame([
        {"compare_metric":"aggregated_signal_entry_rows", "value":int(len(signals)), "scope":"intersection_only_not_full_parity"},
        {"compare_metric":"exact_target_compare_status", "value":"DEFERRED_TO_REVIEW", "scope":"requires explicit target key contract review"},
        {"compare_metric":"full_coreb_parity", "value":"FALSE", "scope":"2127 rows excluded"},
    ])
    write_csv(out_dir/"06_25c5_target_compare_summary.csv", compare)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C4 revision required", "observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"entry-time aggregation applied", "observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G003","gate":"CoreB condition thresholds unchanged", "observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G004","gate":"full_coreb_parity", "observed":False,"required":False,"status":"BLOCKED"},
        {"gate_id":"G005","gate":"source_recovery_execution", "observed":False,"required":False,"status":"BLOCKED"},
        {"gate_id":"G006","gate":"CoreB live evaluator unblock", "observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out_dir/"07_25c5_review_gate_matrix.csv", gates)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C6_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"Review aggregated diagnostic signals and target key comparison contract"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked by excluded raw rows"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"08_25c5_next_step_plan.csv", next_plan)
    unnecessary=["25C4 input/detail CSVs already processed","25C3 large row dumps unless debugging specific entries","25C2 and older report/summary files"]
    necessary=["01_25c5_GOLD_V2_COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_AUDIT_ONLY_REPORT.md","02_25c5_coreb_intersection_dry_run_aggregated_revision_summary.json","04_25c5_aggregated_entry_signal_rows.csv","05_25c5_aggregated_entry_distribution.csv","06_25c5_target_compare_summary.csv","07_25c5_review_gate_matrix.csv","08_25c5_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c5_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"intersection_only":True,"full_coreb_parity":False,"condition_changed":False,"aggregated_signal_entry_rows":int(len(signals)),"selected_entry_rows":int(merged["selected_rule_hit_by_entry_time"].sum()),"source_count_ge15_entry_rows":int(merged["source_count_ge15_by_entry_time"].sum()),"max_source_count_by_entry_time":int(merged["source_universe_hit_count_by_entry_time"].max()) if len(merged) else 0,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C6_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c5_coreb_intersection_dry_run_aggregated_revision_summary.json", summary)
    report="\n".join(["# GOLD V2 25C5 CoreB intersection dry-run aggregated revision audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Finding","","25C5 applies entry-time aggregation without changing CoreB conditions.","","## Aggregated entry distribution","",md_table(dist),"","## Target compare summary","",md_table(compare),"","## Review gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c5_GOLD_V2_COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"aggregated_signal_entry_rows":len(signals),"condition_changed":False,"full_coreb_parity":False,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
