#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C7_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY"
PASS_STATUS = "COREB_TARGET_COMPARE_MISMATCH_TRIAGE_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED"
STOP_STATUS = "25C7_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C6 = "gold_v2_25c6_coreb_intersection_aggregated_result_review_audit_only"
IN25C5 = "gold_v2_25c5_coreb_intersection_dry_run_aggregated_revision_audit_only"
IN25C1B = "gold_v2_25c1b_coreb_alignment_gap_review_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
TARGET_LEDGER_NAME = "rr125_top_ledgers.csv"
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
def md_table(df:pd.DataFrame, max_rows:int=60)->str:
    if df.empty: return "_No rows._"
    v=df.head(max_rows); cols=list(v.columns)
    lines=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in cols)+" |")
    if len(df)>max_rows: lines.append(f"| ... | truncated {len(df)-max_rows} more rows |"+" |"*max(0,len(cols)-2))
    return "\n".join(lines)

def path_from_audit(df:pd.DataFrame, name:str)->Path:
    m=df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0]["absolute_path"])) if not m.empty else Path("")

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_TARGET_MISMATCH_REVIEW_REQUIRED": p.append("25C6 status mismatch")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def expand_signal_policy(sig: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _,r in sig.iterrows():
        pols=[]
        if "selected_policies" in sig.columns and str(r.get("selected_policies", "")):
            pols=[p for p in str(r["selected_policies"]).split(";") if p]
        elif "policy" in sig.columns and str(r.get("policy", "")):
            pols=[str(r["policy"])]
        else:
            pols=["RR125_from_RR1_rules"]
        for p in sorted(set(pols)):
            rows.append({"dataset":str(r["dataset"]),"entry_time":str(r["entry_time"]),"policy":p,"source_universe_hit_count_by_entry_time":r.get("source_universe_hit_count_by_entry_time","")})
    return pd.DataFrame(rows).drop_duplicates()

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    req={
        "25c6_summary":fx_outputs()/IN25C6/"02_25c6_coreb_intersection_aggregated_result_review_summary.json",
        "signals":fx_outputs()/IN25C5/"04_25c5_aggregated_entry_signal_rows.csv",
        "25c1b_summary":fx_outputs()/IN25C1B/"02_25c1b_coreb_alignment_gap_review_summary.json",
        "25b3_file_audit":fx_outputs()/IN25B3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c7_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c7_coreb_target_compare_mismatch_triage_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s6=read_json(req["25c6_summary"]); s1b=read_json(req["25c1b_summary"]); problems=safety_problems(s6); audit=read_csv(req["25b3_file_audit"]); target_path=path_from_audit(audit,TARGET_LEDGER_NAME)
    if not str(target_path) or not lp(target_path).exists(): problems.append("target ledger missing")
    if problems:
        write_json(out_dir/"02_25c7_coreb_target_compare_mismatch_triage_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    sig=read_csv(req["signals"]); target=read_csv(target_path)
    feature_min=pd.to_datetime(s1b.get("feature_min_time"), errors="coerce"); feature_max=pd.to_datetime(s1b.get("feature_max_time"), errors="coerce")
    sig_exp=expand_signal_policy(sig)
    target_entry=target[["dataset","entry_time","policy"]].drop_duplicates().copy()
    for df in [sig_exp,target_entry,target]:
        for c in ["dataset","entry_time","policy"]:
            if c in df.columns: df[c]=df[c].astype(str)
    target_entry["time_norm"]=pd.to_datetime(target_entry["entry_time"], errors="coerce")
    target_entry["scope_class"]=target_entry["time_norm"].map(lambda x: "BEFORE_FEATURE_START" if pd.notna(x) and x<feature_min else ("AFTER_FEATURE_END" if pd.notna(x) and x>feature_max else "IN_FEATURE_RANGE"))
    scope_counts=target_entry.groupby("scope_class", dropna=False).size().reset_index(name="target_entry_rows")
    write_csv(out_dir/"06_25c7_target_scope_classification.csv", scope_counts)
    in_scope_target=target_entry[target_entry["scope_class"].eq("IN_FEATURE_RANGE")][["dataset","entry_time","policy"]].drop_duplicates()
    base_sig=sig_exp[["dataset","entry_time","policy"]].drop_duplicates()
    cmp=base_sig.merge(in_scope_target, on=["dataset","entry_time","policy"], how="outer", indicator=True)
    matrix=cmp["_merge"].value_counts(dropna=False).reset_index(); matrix.columns=["compare_status","entry_rows"]
    write_csv(out_dir/"04_25c7_in_scope_entry_compare_matrix.csv", matrix)
    # policy-expanded matrix is same compare but records expanded signal rows count explicitly
    pol_matrix=pd.DataFrame([
        {"metric":"policy_expanded_signal_entries", "value":int(len(base_sig))},
        {"metric":"in_scope_target_entries", "value":int(len(in_scope_target))},
        {"metric":"both", "value":int((cmp["_merge"]=="both").sum())},
        {"metric":"left_only", "value":int((cmp["_merge"]=="left_only").sum())},
        {"metric":"right_only", "value":int((cmp["_merge"]=="right_only").sum())},
    ])
    write_csv(out_dir/"05_25c7_policy_expanded_compare_matrix.csv", pol_matrix)
    filt=target.groupby(["dataset","entry_time","policy"], dropna=False).agg(target_filter_rows=("filter","nunique") if "filter" in target.columns else ("entry_time","size"), target_rows=("entry_time","size")).reset_index()
    filt_dist=filt.groupby("target_filter_rows", dropna=False).size().reset_index(name="entry_rows").sort_values("target_filter_rows")
    write_csv(out_dir/"07_25c7_filter_multiplicity_matrix.csv", filt_dist)
    true_extra=cmp[cmp["_merge"].eq("left_only")].head(300)
    true_missing=cmp[cmp["_merge"].eq("right_only")].head(300)
    write_csv(out_dir/"08_25c7_true_extra_samples.csv", true_extra)
    write_csv(out_dir/"09_25c7_true_missing_samples.csv", true_missing)
    both=int((cmp["_merge"]=="both").sum()); left=int((cmp["_merge"]=="left_only").sum()); right=int((cmp["_merge"]=="right_only").sum())
    before=int(scope_counts.loc[scope_counts["scope_class"].eq("BEFORE_FEATURE_START"),"target_entry_rows"].sum()) if not scope_counts.empty else 0
    decisions=pd.DataFrame([
        {"decision_id":"D001","question":"Does feature-scope filtering explain some target missing rows?","decision":"YES" if before>0 else "NO","reason":f"target entries before feature start={before}"},
        {"decision_id":"D002","question":"Are all mismatches resolved after scope/policy expansion?","decision":"NO" if (left or right) else "YES","reason":f"both={both}; extra={left}; missing={right}"},
        {"decision_id":"D003","question":"Is CoreB condition changed?","decision":"NO","reason":"triage compares keys only"},
        {"decision_id":"D004","question":"Can CoreB be unblocked now?","decision":"NO","reason":"mismatch remains and full parity false"},
    ])
    write_csv(out_dir/"10_25c7_triage_decision_matrix.csv", decisions)
    next_step="25C8_COREB_MISMATCH_ROOT_CAUSE_AUDIT_ONLY" if (left or right) else "25C8_COREB_INTERSECTION_RESULT_SUMMARY_AUDIT_ONLY"
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":next_step,"allowed_now":True,"purpose":"Inspect remaining true extra/missing entries and compare key semantics"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"11_25c7_next_step_plan.csv", next_plan)
    unnecessary=["25C6 samples already incorporated","25C5 large signal rows unless debugging","older report/summary files"]
    necessary=["01_25c7_GOLD_V2_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY_REPORT.md","02_25c7_coreb_target_compare_mismatch_triage_summary.json","04_25c7_in_scope_entry_compare_matrix.csv","05_25c7_policy_expanded_compare_matrix.csv","06_25c7_target_scope_classification.csv","10_25c7_triage_decision_matrix.csv","11_25c7_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c7_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"intersection_only":True,"full_coreb_parity":False,"condition_changed":False,"feature_min_time":str(feature_min),"feature_max_time":str(feature_max),"target_entries_before_feature_start":before,"policy_expanded_signal_entries":int(len(base_sig)),"in_scope_target_entries":int(len(in_scope_target)),"in_scope_both":both,"in_scope_left_only":left,"in_scope_right_only":right,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":next_step,"total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c7_coreb_target_compare_mismatch_triage_summary.json", summary)
    report="\n".join(["# GOLD V2 25C7 CoreB target compare mismatch triage audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Finding","","25C7 separates feature-scope target rows, policy-expanded signal rows, and remaining in-scope mismatches.","","## In-scope entry compare matrix","",md_table(matrix),"","## Policy-expanded compare matrix","",md_table(pol_matrix),"","## Target scope classification","",md_table(scope_counts),"","## Triage decisions","",md_table(decisions),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c7_GOLD_V2_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"in_scope_both":both,"in_scope_left_only":left,"in_scope_right_only":right,"target_entries_before_feature_start":before,"next_recommended_step":next_step}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
