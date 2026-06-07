#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C25_COREB_G1_MISMATCH_REVIEW_AUDIT_ONLY"
STATUS="COREB_G1_MISMATCH_REVIEW_COMPLETED_AUDIT_ONLY_LEFT_ONLY_DOMINANT_REVIEW_REQUIRED"
STOP="25C25_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c25_coreb_g1_mismatch_review_audit_only"
IN24="gold_v2_25c24_coreb_g1_entry_level_review_dry_run_audit_only"

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
    base=fx_outputs()/IN24
    req={
        "s24":base/"02_25c24_coreb_g1_entry_level_review_dry_run_summary.json",
        "compare":base/"04_25c24_g1_entry_compare_matrix.csv",
        "by_dataset":base/"05_25c24_g1_compare_by_dataset_policy.csv",
        "left_samples":base/"06_25c24_g1_left_only_samples.csv",
        "right_samples":base/"07_25c24_g1_right_only_samples.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c25_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c25_coreb_g1_mismatch_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s24=read_json(req["s24"]); by=read_csv(req["by_dataset"]); left_s=read_csv(req["left_samples"]); right_s=read_csv(req["right_samples"])
    both=int(s24.get("g1_both",0)); left=int(s24.get("g1_left_only",0)); right=int(s24.get("g1_right_only",0)); total=both+left+right
    balance=pd.DataFrame([
        {"metric":"g1_both","rows":both,"ratio":round(both/total,6) if total else 0},
        {"metric":"g1_left_only","rows":left,"ratio":round(left/total,6) if total else 0},
        {"metric":"g1_right_only","rows":right,"ratio":round(right/total,6) if total else 0},
        {"metric":"left_to_right_ratio","rows":round(left/max(right,1),6),"ratio":""},
    ])
    write_csv(out/"04_25c25_g1_mismatch_balance_matrix.csv", balance)
    by["entry_rows"]=pd.to_numeric(by["entry_rows"], errors="coerce").fillna(0).astype(int)
    pivot=by.pivot_table(index=["dataset","policy"], columns="_merge", values="entry_rows", aggfunc="sum", fill_value=0).reset_index()
    for col in ["both","left_only","right_only"]:
        if col not in pivot.columns: pivot[col]=0
    pivot["left_to_right_ratio"]=(pivot["left_only"] / pivot["right_only"].where(pivot["right_only"].ne(0),1)).round(6)
    write_csv(out/"05_25c25_g1_dataset_skew_matrix.csv", pivot)
    bounds=[]
    for name,df in [("left_only",left_s),("right_only",right_s)]:
        if not df.empty and "entry_time" in df.columns:
            t=pd.to_datetime(df["entry_time"], errors="coerce")
            bounds.append({"sample_type":name,"sample_rows":int(len(df)),"min_entry_time":str(t.min()),"max_entry_time":str(t.max())})
        else:
            bounds.append({"sample_type":name,"sample_rows":0,"min_entry_time":"","max_entry_time":""})
    bounds_df=pd.DataFrame(bounds)
    write_csv(out/"06_25c25_g1_sample_time_bounds.csv", bounds_df)
    dominant="LEFT_ONLY" if left > right*2 else ("RIGHT_ONLY" if right > left*2 else "MIXED")
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"G1 exact match reached","decision":"NO" if left+right>0 else "YES","observed":f"both={both}; left={left}; right={right}"},
        {"decision_id":"D002","question":"left-only dominant","decision":"YES" if dominant=="LEFT_ONLY" else "NO","observed":dominant},
        {"decision_id":"D003","question":"right-only dominant","decision":"YES" if dominant=="RIGHT_ONLY" else "NO","observed":dominant},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c25_g1_mismatch_review_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C26_COREB_G1_LEFT_ONLY_ROOT_CAUSE_AUDIT_ONLY" if dominant=="LEFT_ONLY" else "25C26_COREB_G1_MIXED_MISMATCH_ROOT_CAUSE_AUDIT_ONLY","allowed_now":True,"purpose":"review dominant G1 mismatch source"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c25_next_step_plan.csv", nxt)
    unnecessary=["25C24 older reports if summary is available","full target ledger","full replay rows"]
    necessary=["01_25c25_GOLD_V2_COREB_G1_MISMATCH_REVIEW_AUDIT_ONLY_REPORT.md","02_25c25_coreb_g1_mismatch_review_summary.json","04_25c25_g1_mismatch_balance_matrix.csv","05_25c25_g1_dataset_skew_matrix.csv","06_25c25_g1_sample_time_bounds.csv","07_25c25_g1_mismatch_review_decision_matrix.csv","08_25c25_next_step_plan.csv"]
    write_csv(out/"00_不要_25c25_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"g1_both":both,"g1_left_only":left,"g1_right_only":right,"g1_mismatch_dominance":dominant,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":str(nxt.iloc[0]["next_step"]),"total_stop_rows":0}
    write_json(out/"02_25c25_coreb_g1_mismatch_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C25 CoreB G1 mismatch review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## G1 mismatch balance","",md_table(balance),"","## Dataset skew matrix","",md_table(pivot),"","## Sample time bounds","",md_table(bounds_df),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c25_GOLD_V2_COREB_G1_MISMATCH_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"g1_mismatch_dominance":dominant,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
