#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C20_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY"
STATUS="COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_COMPLETED_AUDIT_ONLY_GRAIN_CONTRACT_REVIEW_REQUIRED"
STOP="25C20_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c20_coreb_filter_family_and_entry_grain_audit_only"
IN19="gold_v2_25c19_coreb_replay_contract_revision_plan_audit_only"
IN10="gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
IN15="gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only"
IN7="gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
INB3="gold_v2_25b3_coreb_source_shortlist_content_audit_only"
TARGET_NAME="rr125_top_ledgers.csv"

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
def family_name(x:str)->str:
    s=str(x)
    if "unique_origins" in s and "same_count" in s: return "same_count_and_unique_origins"
    if "unique_origins" in s: return "unique_origins_only"
    if "same_count" in s: return "same_count_only"
    return "other"
def fill_missing_numeric_only(df:pd.DataFrame)->pd.DataFrame:
    out=df.copy()
    numeric_cols=out.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        out[numeric_cols]=out[numeric_cols].fillna(0)
    return out

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s19":fx_outputs()/IN19/"02_25c19_coreb_replay_contract_revision_plan_summary.json",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
        "contract":fx_outputs()/IN15/"02_25c15_coreb_selected_policy_replay_contract_summary.json",
        "s7":fx_outputs()/IN7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "audit":fx_outputs()/INB3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c20_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c20_coreb_filter_family_and_entry_grain_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s19=read_json(req["s19"]); c15=read_json(req["contract"]); s7=read_json(req["s7"]); audit=read_csv(req["audit"])
    selected=set(c15.get("selected_output_policies", []))
    signals=read_csv(req["signals"]); target=read_csv(path_from_audit(audit,TARGET_NAME))
    for df in (signals,target):
        for col in ("dataset","entry_time","policy","filter"):
            if col in df.columns: df[col]=df[col].astype(str)
    fmin=pd.to_datetime(s7.get("feature_min_time"), errors="coerce"); fmax=pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    target["time_norm"]=pd.to_datetime(target["entry_time"], errors="coerce")
    target=target[(target["time_norm"]>=fmin)&(target["time_norm"]<=fmax)&target["policy"].isin(selected)].copy()
    signals=signals[signals["policy"].isin(selected)].copy()
    signals["filter_family"]=signals["filter"].map(family_name); target["filter_family"]=target["filter"].map(family_name)
    sk=signals[["dataset","entry_time","policy","filter_family"]].drop_duplicates(); tk=target[["dataset","entry_time","policy","filter_family"]].drop_duplicates()
    fam=sk.merge(tk,on=["dataset","entry_time","policy","filter_family"],how="outer",indicator=True)
    fam["_merge"]=fam["_merge"].astype(str)
    fam_m=fam.groupby(["policy","filter_family","_merge"],dropna=False, observed=False).size().reset_index(name="rows")
    write_csv(out/"04_25c20_filter_family_mismatch_matrix.csv", fam_m)
    s_entry=signals.groupby(["dataset","entry_time","policy"],dropna=False).agg(filter_rows=("filter","count"),filter_unique=("filter","nunique"),family_unique=("filter_family","nunique")).reset_index()
    t_entry=target.groupby(["dataset","entry_time","policy"],dropna=False).agg(filter_rows=("filter","count"),filter_unique=("filter","nunique"),family_unique=("filter_family","nunique")).reset_index()
    write_csv(out/"05_25c20_replay_entry_grain_distribution.csv", s_entry.describe(include="all").reset_index())
    write_csv(out/"06_25c20_target_entry_grain_distribution.csv", t_entry.describe(include="all").reset_index())
    eg=s_entry.merge(t_entry,on=["dataset","entry_time","policy"],how="outer",suffixes=("_replay","_target"),indicator=True)
    eg["_merge"]=eg["_merge"].astype(str)
    eg=fill_missing_numeric_only(eg)
    eg_summary=eg["_merge"].value_counts(dropna=False).reset_index(); eg_summary.columns=["entry_compare_status","entry_rows"]
    write_csv(out/"07_25c20_entry_grain_compare_matrix.csv", eg_summary)
    fam_left=int((fam["_merge"]=="left_only").sum()); fam_right=int((fam["_merge"]=="right_only").sum()); entry_left=int((eg["_merge"]=="left_only").sum()); entry_right=int((eg["_merge"]=="right_only").sum())
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"filter-family mismatch remains","decision":"YES" if fam_left+fam_right>0 else "NO","observed":f"left={fam_left}; right={fam_right}"},
        {"decision_id":"D002","question":"entry grain mismatch remains","decision":"YES" if entry_left+entry_right>0 else "NO","observed":f"left={entry_left}; right={entry_right}"},
        {"decision_id":"D003","question":"next dry-run allowed now","decision":"NO","observed":False},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"08_25c20_grain_review_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C21_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"define entry-grain contract before execution"},
        {"rank":2,"next_step":"next dry-run execution","allowed_now":False,"purpose":"blocked"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"09_25c20_next_step_plan.csv", nxt)
    unnecessary=["25C19 older reports","large per-row signal samples unless debugging","target ledger alone"]
    necessary=["01_25c20_GOLD_V2_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY_REPORT.md","02_25c20_coreb_filter_family_and_entry_grain_summary.json","04_25c20_filter_family_mismatch_matrix.csv","05_25c20_replay_entry_grain_distribution.csv","06_25c20_target_entry_grain_distribution.csv","07_25c20_entry_grain_compare_matrix.csv","08_25c20_grain_review_decision_matrix.csv","09_25c20_next_step_plan.csv"]
    write_csv(out/"00_不要_25c20_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"dry_run_executed":False,"condition_changed":False,"full_coreb_parity":False,"filter_family_left_only":fam_left,"filter_family_right_only":fam_right,"entry_grain_left_only":entry_left,"entry_grain_right_only":entry_right,"next_dry_run_execution_allowed_now":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C21_COREB_ENTRY_GRAIN_CONTRACT_PLAN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c20_coreb_filter_family_and_entry_grain_summary.json", summary)
    report="\n".join(["# GOLD V2 25C20 CoreB filter family and entry grain audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Filter family mismatch matrix","",md_table(fam_m),"","## Entry grain compare matrix","",md_table(eg_summary),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c20_GOLD_V2_COREB_FILTER_FAMILY_AND_ENTRY_GRAIN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"filter_family_left_only":fam_left,"entry_grain_left_only":entry_left,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
