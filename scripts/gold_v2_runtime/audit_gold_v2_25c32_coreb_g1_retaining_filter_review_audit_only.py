#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C32_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY"
STATUS="COREB_G1_RETAINING_FILTER_REVIEW_COMPLETED_AUDIT_ONLY_RETENTION_AWARE_NARROWING_PLAN_REQUIRED"
STOP="25C32_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c32_coreb_g1_retaining_filter_review_audit_only"
IN31="gold_v2_25c31_coreb_g1_narrowed_dry_run_result_review_audit_only"
IN30="gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only"
IN10="gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
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
    rows=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): rows.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(rows)
def family_name(x):
    s=str(x)
    if "same_count" in s and "unique_origins" in s: return "same_count_and_unique_origins"
    if "unique_origins" in s: return "unique_origins_only"
    if "same_count" in s: return "same_count_only"
    return "other"
def norm(df):
    out=df.copy()
    for c in KEY: out[c]=out[c].astype(str)
    return out

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s31":fx_outputs()/IN31/"02_25c31_coreb_g1_narrowed_dry_run_result_review_summary.json",
        "retention":fx_outputs()/IN31/"05_25c31_primary_filter_key_retention_matrix.csv",
        "contract":fx_outputs()/IN30/"04_25c30_candidate_execution_contract.csv",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c32_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c32_coreb_g1_retaining_filter_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s31=read_json(req["s31"]); retention=norm(read_csv(req["retention"])); contract=read_csv(req["contract"]); signals=norm(read_csv(req["signals"]))
    primary=set(contract["filter"].astype(str).tolist())
    signals["filter"]=signals.get("filter",pd.Series(dtype=str)).astype(str)
    retained_keys=retention[retention["retained_by_non_primary"].astype(str).str.lower().isin(["true","1","yes"])] [KEY].drop_duplicates()
    retaining=retained_keys.merge(signals, on=KEY, how="left")
    retaining=retaining[~retaining["filter"].isin(primary)].copy()
    retaining["filter_family_derived"]=retaining["filter"].map(family_name)
    driver=retaining.groupby(["filter_family_derived","filter"],dropna=False).agg(retained_g1_keys=("entry_time","nunique"), retaining_rows=("filter","count")).reset_index().sort_values(["retaining_rows","retained_g1_keys"], ascending=[False,False])
    write_csv(out/"04_25c32_retaining_filter_driver_matrix.csv", driver)
    fam=retaining.groupby(["filter_family_derived"],dropna=False).agg(retained_g1_keys=("entry_time","nunique"), retaining_rows=("filter","count"), retaining_filter_unique=("filter","nunique")).reset_index().sort_values("retaining_rows", ascending=False)
    write_csv(out/"05_25c32_retaining_filter_family_matrix.csv", fam)
    dist=retention.copy(); dist["retaining_filter_count"]=pd.to_numeric(dist["retaining_filter_count"], errors="coerce").fillna(0).astype(int)
    d=dist.groupby("retaining_filter_count",dropna=False).size().reset_index(name="g1_key_count").sort_values("retaining_filter_count")
    write_csv(out/"06_25c32_retention_count_distribution.csv", d)
    top_family=str(fam.iloc[0]["filter_family_derived"]) if len(fam) else ""
    top_rows=int(fam.iloc[0]["retaining_rows"]) if len(fam) else 0
    retained_count=int(s31.get("retained_primary_g1_key_count", len(retained_keys)))
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"primary keys retained","decision":"YES" if retained_count>0 else "NO","observed":retained_count},
        {"decision_id":"D002","question":"retaining filters identified","decision":"YES" if len(driver)>0 else "NO","observed":len(driver)},
        {"decision_id":"D003","question":"retention-aware narrowing required","decision":"YES","observed":top_family},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c32_retaining_filter_review_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C33_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"plan narrowing including retaining filters"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c32_next_step_plan.csv", nxt)
    unnecessary=["25C31 older reports if summary is available","full target rows","full replay rows"]
    necessary=["01_25c32_GOLD_V2_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY_REPORT.md","02_25c32_coreb_g1_retaining_filter_review_summary.json","04_25c32_retaining_filter_driver_matrix.csv","05_25c32_retaining_filter_family_matrix.csv","06_25c32_retention_count_distribution.csv","07_25c32_retaining_filter_review_decision_matrix.csv","08_25c32_next_step_plan.csv"]
    write_csv(out/"00_不要_25c32_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"retained_primary_g1_key_count":retained_count,"retaining_filter_unique":int(retaining["filter"].nunique()) if "filter" in retaining.columns else 0,"top_retaining_filter_family":top_family,"top_retaining_filter_family_rows":top_rows,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C33_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c32_coreb_g1_retaining_filter_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C32 CoreB G1 retaining filter review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Retaining filter driver matrix","",md_table(driver),"","## Retaining filter family matrix","",md_table(fam),"","## Retention count distribution","",md_table(d),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c32_GOLD_V2_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"retaining_filter_unique":summary["retaining_filter_unique"],"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
