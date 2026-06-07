#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C4_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY"
PASS_STATUS = "COREB_INTERSECTION_DRY_RUN_REVIEW_COMPLETED_AUDIT_ONLY_AGGREGATION_REVISION_REQUIRED"
STOP_STATUS = "25C4_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C3 = "gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only"
OUT_DIR = "gold_v2_25c4_coreb_intersection_dry_run_review_audit_only"
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
    if s.get("status")!="COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_REVIEW_REQUIRED": p.append("25C3 status mismatch")
    if not bool(s.get("intersection_only")): p.append("25C3 intersection_only not true")
    if bool(s.get("full_coreb_parity")): p.append("25C3 full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in_dir=fx_outputs()/IN25C3
    req={"25c3_summary":in_dir/"02_25c3_coreb_intersection_only_dry_run_implementation_summary.json", "source_counts":in_dir/"07_25c3_source_universe_hit_counts_by_entry.csv", "selected_hits":in_dir/"08_25c3_selected_rule_hit_rows.csv", "signals":in_dir/"09_25c3_diagnostic_signal_rows.csv", "target_compare":in_dir/"10_25c3_target_compare_summary.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c4_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c4_coreb_intersection_dry_run_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c3_summary"]); problems=safety_problems(s)
    if problems:
        write_json(out_dir/"02_25c4_coreb_intersection_dry_run_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    src=read_csv(req["source_counts"]); sel=read_csv(req["selected_hits"]); sig=read_csv(req["signals"]); cmp=read_csv(req["target_compare"])
    keys=["dataset","entry_time"]
    agg=src.groupby(keys, dropna=False).agg(source_count_sum=("source_universe_hit_count","sum"), source_count_max=("source_universe_hit_count","max"), source_rows=("source_universe_hit_count","size"), source_rows_ge1=("source_universe_hit_count", lambda x:int((pd.to_numeric(x, errors="coerce")>=1).sum()))).reset_index()
    sel_agg=sel.groupby(keys, dropna=False).size().reset_index(name="selected_hit_rows") if not sel.empty else pd.DataFrame(columns=keys+["selected_hit_rows"])
    cand=agg.merge(sel_agg, on=keys, how="left"); cand["selected_hit_rows"]=cand["selected_hit_rows"].fillna(0).astype(int)
    cand["entry_time_source_sum_ge15"] = cand["source_count_sum"].ge(15)
    cand["entry_time_selected_hit"] = cand["selected_hit_rows"].gt(0)
    cand["would_signal_if_entry_time_sum"] = cand["entry_time_source_sum_ge15"] & cand["entry_time_selected_hit"]
    dist=pd.DataFrame([{
        "metric":"row_level_source_count_max", "value":int(pd.to_numeric(src["source_universe_hit_count"], errors="coerce").max())},
        {"metric":"row_level_rows_ge15", "value":int((pd.to_numeric(src["source_universe_hit_count"], errors="coerce")>=15).sum())},
        {"metric":"entry_time_source_sum_max", "value":int(cand["source_count_sum"].max())},
        {"metric":"entry_time_source_sum_ge15_entries", "value":int(cand["entry_time_source_sum_ge15"].sum())},
        {"metric":"entry_time_selected_entries", "value":int(cand["entry_time_selected_hit"].sum())},
        {"metric":"would_signal_if_entry_time_sum_entries", "value":int(cand["would_signal_if_entry_time_sum"].sum())},
        {"metric":"25c3_reported_diagnostic_signal_rows", "value":int(len(sig))},
    ])
    write_csv(out_dir/"04_25c4_source_count_granularity_matrix.csv", dist)
    cand_sorted=cand.sort_values(["would_signal_if_entry_time_sum","source_count_sum"], ascending=[False,False])
    write_csv(out_dir/"05_25c4_entry_time_aggregate_distribution.csv", cand_sorted)
    write_csv(out_dir/"06_25c4_selected_and_source_entry_candidates.csv", cand_sorted[cand_sorted["would_signal_if_entry_time_sum"]].head(1000))
    revision_required = bool(int(cand["would_signal_if_entry_time_sum"].sum())>0 and len(sig)==0)
    decisions=pd.DataFrame([
        {"decision_id":"D001","question":"Is 25C3 zero-signal result final?","decision":"NO" if revision_required else "REVIEW","reason":"entry-time aggregation produces candidates while row-level 25C3 produced zero" if revision_required else "no aggregate candidates found"},
        {"decision_id":"D002","question":"Was CoreB condition changed?","decision":"NO","reason":"review is about aggregation granularity, not condition thresholds"},
        {"decision_id":"D003","question":"Should 25C3 be revised?","decision":"YES" if revision_required else "NO","reason":"source_count must be by entry_time per plan contract"},
        {"decision_id":"D004","question":"Can CoreB be unblocked now?","decision":"NO","reason":"diagnostic/revision only; full parity remains false"},
    ])
    write_csv(out_dir/"07_25c4_review_decision_matrix.csv", decisions)
    next_step="25C5_COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_AUDIT_ONLY" if revision_required else "25C5_COREB_INTERSECTION_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":next_step,"allowed_now":True,"purpose":"Revise/review diagnostic dry-run aggregation without changing CoreB conditions"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked by intersection-only limitation"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"08_25c4_next_step_plan.csv", next_plan)
    unnecessary=["25C3 large source/selected row dumps unless debugging specific entries","25C2 and older report/summary files","rr125_top_ledgers.csv alone"]
    necessary=["01_25c4_GOLD_V2_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY_REPORT.md","02_25c4_coreb_intersection_dry_run_review_summary.json","04_25c4_source_count_granularity_matrix.csv","07_25c4_review_decision_matrix.csv","08_25c4_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c4_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    status=PASS_STATUS if revision_required else "COREB_INTERSECTION_DRY_RUN_REVIEW_COMPLETED_AUDIT_ONLY_NO_AGGREGATION_REVISION_NEEDED"
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"revision_required":revision_required,"row_level_source_count_max":int(pd.to_numeric(src["source_universe_hit_count"],errors="coerce").max()),"entry_time_source_sum_max":int(cand["source_count_sum"].max()),"entry_time_source_sum_ge15_entries":int(cand["entry_time_source_sum_ge15"].sum()),"entry_time_selected_entries":int(cand["entry_time_selected_hit"].sum()),"would_signal_if_entry_time_sum_entries":int(cand["would_signal_if_entry_time_sum"].sum()),"reported_25c3_diagnostic_signal_rows":int(len(sig)),"coreb_live_evaluator_unblocked":False,"source_recovery_executed":False,"source_mutation_executed":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":next_step,"total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c4_coreb_intersection_dry_run_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C4 CoreB intersection dry-run review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## Finding","","25C3 zero-signal result is not accepted as final when entry-time aggregation produces candidates.","","## Source count granularity matrix","",md_table(dist),"","## Review decision matrix","",md_table(decisions),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c4_GOLD_V2_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"revision_required":revision_required,"would_signal_if_entry_time_sum_entries":summary["would_signal_if_entry_time_sum_entries"],"next_recommended_step":next_step}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
