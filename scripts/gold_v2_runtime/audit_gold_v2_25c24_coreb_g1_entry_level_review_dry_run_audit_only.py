#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C24_COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_AUDIT_ONLY"
STATUS_PASS="COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_COMPLETED_AUDIT_ONLY_G1_EXACT_MATCH_REVIEW_REQUIRED"
STATUS_MISMATCH="COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_COMPLETED_AUDIT_ONLY_G1_MISMATCH_REVIEW_REQUIRED"
STOP="25C24_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c24_coreb_g1_entry_level_review_dry_run_audit_only"
IN23="gold_v2_25c23_coreb_g1_entry_level_review_plan_audit_only"
IN15="gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only"
IN10="gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
IN7="gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
INB3="gold_v2_25b3_coreb_source_shortlist_content_audit_only"
TARGET_NAME="rr125_top_ledgers.csv"
KEY=["dataset","entry_time","policy"]

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
def path_from_audit(df:pd.DataFrame, name:str)->Path:
    m=df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0]["absolute_path"])) if not m.empty else Path("")
def normalize_key_columns(df:pd.DataFrame)->pd.DataFrame:
    out=df.copy()
    for col in KEY:
        if col not in out.columns:
            raise KeyError(f"missing required key column: {col}")
        out[col]=out[col].astype(str)
    return out

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s23":fx_outputs()/IN23/"02_25c23_coreb_g1_entry_level_review_plan_summary.json",
        "contract":fx_outputs()/IN15/"02_25c15_coreb_selected_policy_replay_contract_summary.json",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
        "s7":fx_outputs()/IN7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "audit":fx_outputs()/INB3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c24_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c24_coreb_g1_entry_level_review_dry_run_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s23=read_json(req["s23"])
    if s23.get("selected_grain")!="G1" or list(s23.get("g1_compare_key",[]))!=KEY:
        write_json(out/"02_25c24_coreb_g1_entry_level_review_dry_run_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":"25C24_STOP_G1_CONTRACT_NOT_CONFIRMED_AUDIT_ONLY","total_stop_rows":1}); return 2
    c15=read_json(req["contract"]); s7=read_json(req["s7"]); audit=read_csv(req["audit"])
    selected=set(c15.get("selected_output_policies", []))
    signals=normalize_key_columns(read_csv(req["signals"])); target=normalize_key_columns(read_csv(path_from_audit(audit,TARGET_NAME)))
    fmin=pd.to_datetime(s7.get("feature_min_time"), errors="coerce"); fmax=pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    target["time_norm"]=pd.to_datetime(target["entry_time"], errors="coerce")
    target=target[(target["time_norm"]>=fmin)&(target["time_norm"]<=fmax)&target["policy"].isin(selected)].copy()
    signals=signals[signals["policy"].isin(selected)].copy()
    replay_key=signals[KEY].drop_duplicates().copy(); target_key=target[KEY].drop_duplicates().copy()
    cmp=replay_key.merge(target_key,on=KEY,how="outer",indicator=True)
    cmp["_merge"]=cmp["_merge"].astype(str)
    matrix=cmp["_merge"].value_counts(dropna=False).reset_index(); matrix.columns=["g1_compare_status","entry_rows"]
    write_csv(out/"04_25c24_g1_entry_compare_matrix.csv", matrix)
    by=cmp.groupby(["dataset","policy","_merge"],dropna=False).size().reset_index(name="entry_rows")
    write_csv(out/"05_25c24_g1_compare_by_dataset_policy.csv", by)
    left=cmp[cmp["_merge"].eq("left_only")].sort_values(KEY).head(200)
    right=cmp[cmp["_merge"].eq("right_only")].sort_values(KEY).head(200)
    write_csv(out/"06_25c24_g1_left_only_samples.csv", left)
    write_csv(out/"07_25c24_g1_right_only_samples.csv", right)
    both_n=int((cmp["_merge"]=="both").sum()); left_n=int((cmp["_merge"]=="left_only").sum()); right_n=int((cmp["_merge"]=="right_only").sum())
    exact=(left_n==0 and right_n==0)
    status=STATUS_PASS if exact else STATUS_MISMATCH
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"G1 plan confirmed","observed":True,"status":"PASS"},
        {"gate_id":"G002","gate":"G1 exact match","observed":exact,"status":"PASS" if exact else "REVIEW_REQUIRED"},
        {"gate_id":"G003","gate":"dry-run was audit-only","observed":True,"status":"PASS"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"status":"BLOCKED"},
    ])
    write_csv(out/"08_25c24_g1_acceptance_gate_matrix.csv", gates)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C25_COREB_G1_MISMATCH_REVIEW_AUDIT_ONLY" if not exact else "25C25_COREB_G1_EXACT_MATCH_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"review G1 dry-run result"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"09_25c24_next_step_plan.csv", nxt)
    unnecessary=["25C23 older reports if summary is available","full target ledger","full replay signal rows"]
    necessary=["01_25c24_GOLD_V2_COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_AUDIT_ONLY_REPORT.md","02_25c24_coreb_g1_entry_level_review_dry_run_summary.json","04_25c24_g1_entry_compare_matrix.csv","05_25c24_g1_compare_by_dataset_policy.csv","06_25c24_g1_left_only_samples.csv","07_25c24_g1_right_only_samples.csv","08_25c24_g1_acceptance_gate_matrix.csv","09_25c24_next_step_plan.csv"]
    write_csv(out/"00_不要_25c24_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"dry_run_executed":True,"condition_changed":False,"full_coreb_parity":False,"selected_grain":"G1","g1_compare_key":KEY,"g1_both":both_n,"g1_left_only":left_n,"g1_right_only":right_n,"g1_exact_match":exact,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":str(nxt.iloc[0]["next_step"]),"total_stop_rows":0}
    write_json(out/"02_25c24_coreb_g1_entry_level_review_dry_run_summary.json", summary)
    report="\n".join(["# GOLD V2 25C24 CoreB G1 entry-level review dry-run audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## G1 entry compare matrix","",md_table(matrix),"","## G1 compare by dataset/policy","",md_table(by),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c24_GOLD_V2_COREB_G1_ENTRY_LEVEL_REVIEW_DRY_RUN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"g1_both":both_n,"g1_left_only":left_n,"g1_right_only":right_n,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
