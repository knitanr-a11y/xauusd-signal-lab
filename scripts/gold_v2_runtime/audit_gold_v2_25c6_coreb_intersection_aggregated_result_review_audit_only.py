#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C6_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY"
PASS_STATUS = "COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_TARGET_MISMATCH_REVIEW_REQUIRED"
STOP_STATUS = "25C6_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C5 = "gold_v2_25c5_coreb_intersection_dry_run_aggregated_revision_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c6_coreb_intersection_aggregated_result_review_audit_only"
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
    if s.get("status")!="COREB_INTERSECTION_DRY_RUN_AGGREGATED_REVISION_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED": p.append("25C5 status mismatch")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in5=fx_outputs()/IN25C5; inb3=fx_outputs()/IN25B3
    req={"25c5_summary":in5/"02_25c5_coreb_intersection_dry_run_aggregated_revision_summary.json","signals":in5/"04_25c5_aggregated_entry_signal_rows.csv","25b3_file_audit":inb3/"gold_v2_25b3_shortlist_file_content_audit.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c6_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c6_coreb_intersection_aggregated_result_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c5_summary"]); problems=safety_problems(s); audit=read_csv(req["25b3_file_audit"]); target_path=path_from_audit(audit,TARGET_LEDGER_NAME)
    if not str(target_path) or not lp(target_path).exists(): problems.append("target ledger missing")
    if problems:
        write_json(out_dir/"02_25c6_coreb_intersection_aggregated_result_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    sig=read_csv(req["signals"]); target=read_csv(target_path)
    key_contract=pd.DataFrame([
        {"level":"entry", "key_cols":"dataset;entry_time;policy", "reason":"25C5 signals are entry-time aggregate rows"},
        {"level":"filter", "key_cols":"dataset;entry_time;policy;filter", "reason":"target top ledger has multiple filter rows per entry_time"},
    ])
    write_csv(out_dir/"04_25c6_target_key_contract.csv", key_contract)
    for df in [sig,target]:
        if "dataset" in df.columns: df["dataset"] = df["dataset"].astype(str)
        if "entry_time" in df.columns: df["entry_time"] = df["entry_time"].astype(str)
        if "policy" in df.columns: df["policy"] = df["policy"].astype(str)
    sig_entry=sig[["dataset","entry_time","selected_policies"]].copy() if "selected_policies" in sig.columns else sig[["dataset","entry_time"]].copy()
    sig_entry["policy"] = sig_entry.get("selected_policies", "RR125_from_RR1_rules").astype(str)
    sig_entry=sig_entry[["dataset","entry_time","policy"]].drop_duplicates()
    tgt_entry=target[["dataset","entry_time","policy"]].drop_duplicates()
    entry_cmp=sig_entry.merge(tgt_entry, on=["dataset","entry_time","policy"], how="outer", indicator=True)
    entry_matrix=entry_cmp["_merge"].value_counts(dropna=False).reset_index(); entry_matrix.columns=["compare_status","entry_rows"]
    write_csv(out_dir/"05_25c6_entry_level_compare_matrix.csv", entry_matrix)
    tgt_filter=target[[c for c in ["dataset","entry_time","policy","filter"] if c in target.columns]].drop_duplicates()
    filter_cmp=sig_entry.merge(tgt_filter, on=["dataset","entry_time","policy"], how="outer", indicator=True)
    filter_matrix=filter_cmp["_merge"].value_counts(dropna=False).reset_index(); filter_matrix.columns=["compare_status","filter_rows"]
    write_csv(out_dir/"06_25c6_filter_level_compare_matrix.csv", filter_matrix)
    write_csv(out_dir/"07_25c6_signal_extra_samples.csv", entry_cmp[entry_cmp["_merge"].eq("left_only")].head(200))
    write_csv(out_dir/"08_25c6_target_missing_samples.csv", entry_cmp[entry_cmp["_merge"].eq("right_only")].head(200))
    both=int((entry_cmp["_merge"]=="both").sum()); left=int((entry_cmp["_merge"]=="left_only").sum()); right=int((entry_cmp["_merge"]=="right_only").sum())
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C5 aggregate result loaded","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"entry-level target match exists","observed":both>0,"required":True,"status":"PASS" if both>0 else "BLOCKED"},
        {"gate_id":"G003","gate":"no extra diagnostic signals","observed":left==0,"required":True,"status":"PASS" if left==0 else "REVIEW"},
        {"gate_id":"G004","gate":"no missing target entries","observed":right==0,"required":True,"status":"PASS" if right==0 else "REVIEW"},
        {"gate_id":"G005","gate":"full_coreb_parity","observed":False,"required":False,"status":"BLOCKED"},
        {"gate_id":"G006","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out_dir/"09_25c6_review_gate_matrix.csv", gates)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C7_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY","allowed_now":True,"purpose":"Analyze extra/missing target mismatches and filter-level contract"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked by excluded raw rows"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"10_25c6_next_step_plan.csv", next_plan)
    unnecessary=["25C5 detail rows already processed unless debugging", "25C4 and older report/summary files", "rr125_top_ledgers.csv alone"]
    necessary=["01_25c6_GOLD_V2_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY_REPORT.md","02_25c6_coreb_intersection_aggregated_result_review_summary.json","05_25c6_entry_level_compare_matrix.csv","06_25c6_filter_level_compare_matrix.csv","09_25c6_review_gate_matrix.csv","10_25c6_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c6_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    status=PASS_STATUS
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"intersection_only":True,"full_coreb_parity":False,"condition_changed":False,"aggregated_signal_entry_rows":int(len(sig_entry)),"target_entry_rows":int(len(tgt_entry)),"entry_level_both":both,"entry_level_left_only":left,"entry_level_right_only":right,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C7_COREB_TARGET_COMPARE_MISMATCH_TRIAGE_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c6_coreb_intersection_aggregated_result_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C6 CoreB intersection aggregated result review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## Boundary","","25C6 compares aggregated diagnostic entries to target. It does not prove full CoreB parity or unblock CoreB.","","## Entry-level compare matrix","",md_table(entry_matrix),"","## Filter-level compare matrix","",md_table(filter_matrix),"","## Review gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c6_GOLD_V2_COREB_INTERSECTION_AGGREGATED_RESULT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"entry_level_both":both,"entry_level_left_only":left,"entry_level_right_only":right,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
