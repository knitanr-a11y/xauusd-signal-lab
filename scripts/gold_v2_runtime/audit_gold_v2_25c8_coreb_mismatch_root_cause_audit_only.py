#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C8_COREB_MISMATCH_ROOT_CAUSE_AUDIT_ONLY"
PASS_STATUS = "COREB_MISMATCH_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_FILTER_CONTRACT_REVIEW_REQUIRED"
STOP_STATUS = "25C8_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C7 = "gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
IN25C5 = "gold_v2_25c5_coreb_intersection_dry_run_aggregated_revision_audit_only"
IN25C4 = "gold_v2_25c4_coreb_intersection_dry_run_review_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c8_coreb_mismatch_root_cause_audit_only"
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

def filter_threshold(f: str) -> str:
    s=str(f)
    m=re.search(r"same_count>=(\d+)", s)
    sc=m.group(1) if m else "NONE"
    u="unique_origins>=2" if "unique_origins>=2" in s else "NO_UNIQUE_ORIGINS_FILTER"
    return f"same_count>={sc};{u}"

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

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_TARGET_COMPARE_MISMATCH_TRIAGE_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED": p.append("25C7 status mismatch")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    req={
        "25c7_summary":fx_outputs()/IN25C7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "signals":fx_outputs()/IN25C5/"04_25c5_aggregated_entry_signal_rows.csv",
        "entry_agg":fx_outputs()/IN25C4/"05_25c4_entry_time_aggregate_distribution.csv",
        "25b3_file_audit":fx_outputs()/IN25B3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c8_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c8_coreb_mismatch_root_cause_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c7_summary"]); problems=safety_problems(s); audit=read_csv(req["25b3_file_audit"]); target_path=path_from_audit(audit,TARGET_LEDGER_NAME)
    if not str(target_path) or not lp(target_path).exists(): problems.append("target ledger missing")
    if problems:
        write_json(out_dir/"02_25c8_coreb_mismatch_root_cause_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    sig=read_csv(req["signals"]); agg=read_csv(req["entry_agg"]); target=read_csv(target_path)
    for df in [target,agg]:
        for c in ["dataset","entry_time","policy"]:
            if c in df.columns: df[c]=df[c].astype(str)
    sig_exp=expand_signal_policy(sig)
    if "filter" not in target.columns: target["filter"]=""
    target["filter_class"]=target["filter"].map(filter_threshold)
    filter_inventory=target.groupby(["policy","filter","filter_class"], dropna=False).size().reset_index(name="target_rows").sort_values("target_rows", ascending=False)
    write_csv(out_dir/"04_25c8_target_filter_inventory.csv", filter_inventory)
    feature_min=pd.to_datetime(s.get("feature_min_time"), errors="coerce"); feature_max=pd.to_datetime(s.get("feature_max_time"), errors="coerce")
    target["time_norm"]=pd.to_datetime(target["entry_time"], errors="coerce")
    in_scope=target[(target["time_norm"]>=feature_min)&(target["time_norm"]<=feature_max)].copy()
    sig_key=sig_exp[["dataset","entry_time","policy"]].drop_duplicates(); tgt_key=in_scope[["dataset","entry_time","policy"]].drop_duplicates()
    cmp=sig_key.merge(tgt_key,on=["dataset","entry_time","policy"],how="outer",indicator=True)
    missing=cmp[cmp["_merge"].eq("right_only")].drop(columns=["_merge"])
    extra=cmp[cmp["_merge"].eq("left_only")].drop(columns=["_merge"])
    miss_detail=missing.merge(in_scope[["dataset","entry_time","policy","filter","filter_class"]].drop_duplicates(),on=["dataset","entry_time","policy"],how="left")
    miss_matrix=miss_detail.groupby(["policy","filter_class"],dropna=False).size().reset_index(name="missing_entry_filter_rows").sort_values("missing_entry_filter_rows",ascending=False)
    write_csv(out_dir/"05_25c8_missing_root_cause_matrix.csv", miss_matrix)
    target_any=in_scope[["dataset","entry_time"]].drop_duplicates(); extra_detail=extra.merge(target_any,on=["dataset","entry_time"],how="left",indicator="entry_in_target_any")
    extra_detail["extra_class"]=extra_detail["entry_in_target_any"].map(lambda x:"ENTRY_TIME_PRESENT_TARGET_OTHER_POLICY" if x=="both" else "ENTRY_TIME_NOT_IN_TARGET")
    extra_matrix=extra_detail.groupby(["policy","extra_class"],dropna=False).size().reset_index(name="extra_entries").sort_values("extra_entries",ascending=False)
    write_csv(out_dir/"06_25c8_extra_root_cause_matrix.csv", extra_matrix)
    # threshold alignment: how many target filter classes are covered by current source_count>=15 signal contract
    threshold_matrix=filter_inventory.groupby("filter_class",dropna=False).agg(target_rows=("target_rows","sum"), filters=("filter","nunique")).reset_index().sort_values("target_rows",ascending=False)
    threshold_matrix["current_signal_contract"]="source_count_by_entry_time>=15"
    threshold_matrix["contract_alignment"] = threshold_matrix["filter_class"].map(lambda x:"DIRECT" if str(x).startswith("same_count>=15;") and "NO_UNIQUE" in str(x) else ("STRICTER_THAN_TARGET" if str(x).startswith("same_count>=8;") or str(x).startswith("same_count>=10;") else ("LOOSER_THAN_TARGET" if str(x).startswith("same_count>=20;") else "DIFFERENT_DIMENSION")))
    write_csv(out_dir/"07_25c8_threshold_filter_alignment_matrix.csv", threshold_matrix)
    policy_matrix=pd.DataFrame([
        {"metric":"signal_policies", "value":";".join(sorted(sig_key["policy"].unique()))},
        {"metric":"target_policies", "value":";".join(sorted(in_scope["policy"].astype(str).unique()))},
        {"metric":"missing_policy_counts", "value":miss_detail.groupby("policy").size().to_dict()},
        {"metric":"extra_policy_counts", "value":extra_detail.groupby("policy").size().to_dict()},
    ])
    write_csv(out_dir/"08_25c8_policy_root_cause_matrix.csv", policy_matrix)
    true_direct_miss=int(miss_matrix[miss_matrix["filter_class"].astype(str).str.startswith("same_count>=15;NO_UNIQUE")]["missing_entry_filter_rows"].sum()) if not miss_matrix.empty else 0
    direct_target_rows=int(threshold_matrix[threshold_matrix["contract_alignment"].eq("DIRECT")]["target_rows"].sum()) if not threshold_matrix.empty else 0
    decisions=pd.DataFrame([
        {"decision_id":"D001","question":"Are mismatches fully explained by feature scope?","decision":"NO","reason":"in-scope mismatches remain"},
        {"decision_id":"D002","question":"Do target filters use multiple contracts?","decision":"YES","reason":f"filter classes={threshold_matrix['filter_class'].nunique()}"},
        {"decision_id":"D003","question":"Is current diagnostic contract directly comparable to all target rows?","decision":"NO","reason":"target includes thresholds and unique_origins dimensions beyond source_count>=15"},
        {"decision_id":"D004","question":"Can CoreB be unblocked now?","decision":"NO","reason":"full parity false and target mismatch unresolved"},
    ])
    write_csv(out_dir/"09_25c8_root_cause_decision_matrix.csv", decisions)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C9_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"Plan filter-specific comparison contracts without changing CoreB conditions"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"10_25c8_next_step_plan.csv", next_plan)
    unnecessary=["25C7 samples already incorporated","25C5 large signal rows unless debugging","older report/summary files"]
    necessary=["01_25c8_GOLD_V2_COREB_MISMATCH_ROOT_CAUSE_AUDIT_ONLY_REPORT.md","02_25c8_coreb_mismatch_root_cause_summary.json","04_25c8_target_filter_inventory.csv","05_25c8_missing_root_cause_matrix.csv","06_25c8_extra_root_cause_matrix.csv","07_25c8_threshold_filter_alignment_matrix.csv","09_25c8_root_cause_decision_matrix.csv","10_25c8_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c8_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"intersection_only":True,"full_coreb_parity":False,"condition_changed":False,"filter_class_count":int(threshold_matrix["filter_class"].nunique()),"direct_contract_target_rows":direct_target_rows,"direct_contract_missing_rows":true_direct_miss,"extra_entries":int(len(extra_detail)),"missing_entries":int(len(missing)),"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C9_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c8_coreb_mismatch_root_cause_summary.json", summary)
    report="\n".join(["# GOLD V2 25C8 CoreB mismatch root cause audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Finding","","25C8 classifies remaining mismatches by target filter contract and policy/entry semantics. It does not change CoreB conditions.","","## Target filter inventory","",md_table(filter_inventory),"","## Missing root cause matrix","",md_table(miss_matrix),"","## Extra root cause matrix","",md_table(extra_matrix),"","## Threshold filter alignment matrix","",md_table(threshold_matrix),"","## Decisions","",md_table(decisions),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c8_GOLD_V2_COREB_MISMATCH_ROOT_CAUSE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"filter_class_count":summary["filter_class_count"],"extra_entries":summary["extra_entries"],"missing_entries":summary["missing_entries"],"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
