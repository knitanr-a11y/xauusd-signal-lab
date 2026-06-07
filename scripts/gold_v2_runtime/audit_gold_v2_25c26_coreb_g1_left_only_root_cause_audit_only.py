#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C26_COREB_G1_LEFT_ONLY_ROOT_CAUSE_AUDIT_ONLY"
STATUS="COREB_G1_LEFT_ONLY_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_REPLAY_OVERGENERATION_CONTRACT_REVIEW_REQUIRED"
STOP="25C26_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c26_coreb_g1_left_only_root_cause_audit_only"
IN24="gold_v2_25c24_coreb_g1_entry_level_review_dry_run_audit_only"
IN25="gold_v2_25c25_coreb_g1_mismatch_review_audit_only"
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
    out=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): out.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(out)
def family_name(x:str)->str:
    s=str(x)
    if "unique_origins" in s and "same_count" in s: return "same_count_and_unique_origins"
    if "unique_origins" in s: return "unique_origins_only"
    if "same_count" in s: return "same_count_only"
    return "other"
def normalize_key(df:pd.DataFrame)->pd.DataFrame:
    out=df.copy()
    for col in KEY:
        out[col]=out[col].astype(str)
    return out

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s25":fx_outputs()/IN25/"02_25c25_coreb_g1_mismatch_review_summary.json",
        "left_keys":fx_outputs()/IN24/"06_25c24_g1_left_only_samples.csv",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c26_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c26_coreb_g1_left_only_root_cause_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s25=read_json(req["s25"]); left_keys=normalize_key(read_csv(req["left_keys"])); signals=normalize_key(read_csv(req["signals"]))
    if s25.get("g1_mismatch_dominance")!="LEFT_ONLY":
        write_json(out/"02_25c26_coreb_g1_left_only_root_cause_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":"25C26_STOP_LEFT_ONLY_NOT_DOMINANT_AUDIT_ONLY","total_stop_rows":1}); return 2
    signals["filter"]=signals["filter"].astype(str)
    signals["filter_family"]=signals["filter"].map(family_name)
    enriched=left_keys[KEY].drop_duplicates().merge(signals, on=KEY, how="left")
    profile=enriched.groupby(["filter_family"], dropna=False).agg(left_only_g1_keys=("entry_time","nunique"), replay_filter_rows=("filter","count"), replay_filter_unique=("filter","nunique")).reset_index().sort_values("replay_filter_rows", ascending=False)
    write_csv(out/"04_25c26_left_only_filter_family_profile.csv", profile)
    mult=enriched.groupby(KEY, dropna=False).agg(replay_filter_rows=("filter","count"), replay_filter_unique=("filter","nunique"), replay_family_unique=("filter_family","nunique")).reset_index()
    dist=mult.groupby(["replay_filter_rows","replay_filter_unique","replay_family_unique"], dropna=False).size().reset_index(name="g1_key_count").sort_values(["g1_key_count","replay_filter_rows"], ascending=[False,False])
    write_csv(out/"05_25c26_left_only_signal_multiplicity_profile.csv", dist)
    sample=enriched.sort_values(KEY + ["filter"]).head(300)
    write_csv(out/"06_25c26_left_only_sample_enrichment.csv", sample)
    left_total=int(s25.get("g1_left_only",0)); enriched_keys=int(mult.shape[0]); high_multi=int((mult["replay_filter_rows"]>1).sum())
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"left-only dominance confirmed","decision":"YES","observed":s25.get("g1_mismatch_dominance")},
        {"decision_id":"D002","question":"left-only samples enriched with replay filters","decision":"YES" if enriched_keys>0 else "NO","observed":enriched_keys},
        {"decision_id":"D003","question":"multi-filter replay entries present","decision":"YES" if high_multi>0 else "NO","observed":high_multi},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c26_left_only_root_cause_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C27_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY","allowed_now":True,"purpose":"review replay-side filter contract causing left-only entries"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c26_next_step_plan.csv", nxt)
    unnecessary=["25C25 older reports if summary is available","full replay rows","full target rows"]
    necessary=["01_25c26_GOLD_V2_COREB_G1_LEFT_ONLY_ROOT_CAUSE_AUDIT_ONLY_REPORT.md","02_25c26_coreb_g1_left_only_root_cause_summary.json","04_25c26_left_only_filter_family_profile.csv","05_25c26_left_only_signal_multiplicity_profile.csv","06_25c26_left_only_sample_enrichment.csv","07_25c26_left_only_root_cause_decision_matrix.csv","08_25c26_next_step_plan.csv"]
    write_csv(out/"00_不要_25c26_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"g1_left_only_total":left_total,"left_only_sample_keys_enriched":enriched_keys,"left_only_multi_filter_key_count":high_multi,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C27_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c26_coreb_g1_left_only_root_cause_summary.json", summary)
    report="\n".join(["# GOLD V2 25C26 CoreB G1 left-only root cause audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Left-only filter family profile","",md_table(profile),"","## Left-only signal multiplicity profile","",md_table(dist),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c26_GOLD_V2_COREB_G1_LEFT_ONLY_ROOT_CAUSE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"left_only_sample_keys_enriched":enriched_keys,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
