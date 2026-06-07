#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C31_COREB_G1_NARROWED_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"
STATUS="COREB_G1_NARROWED_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_G1_KEY_RETENTION_REVIEW_REQUIRED"
STOP="25C31_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c31_coreb_g1_narrowed_dry_run_result_review_audit_only"
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

def normalize_key(df:pd.DataFrame)->pd.DataFrame:
    out=df.copy()
    for c in KEY: out[c]=out[c].astype(str)
    return out

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    base=fx_outputs()/IN30
    req={
        "s30":base/"02_25c30_coreb_g1_narrowed_dry_run_summary.json",
        "contract":base/"04_25c30_candidate_execution_contract.csv",
        "compare":base/"05_25c30_variant_compare_matrix.csv",
        "delta":base/"06_25c30_variant_delta_matrix.csv",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c31_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c31_coreb_g1_narrowed_dry_run_result_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s30=read_json(req["s30"]); contract=read_csv(req["contract"]); compare=read_csv(req["compare"]); delta=read_csv(req["delta"]); signals=normalize_key(read_csv(req["signals"]))
    contract_filters=set(contract["filter"].astype(str).tolist())
    signals["filter"]=signals.get("filter", pd.Series(dtype=str)).astype(str)
    signals["filter_family"]=signals.get("filter_family", pd.Series(dtype=str)).astype(str) if "filter_family" in signals.columns else ""
    primary_rows=signals[signals["filter"].isin(contract_filters)].copy()
    primary_keys=primary_rows[KEY].drop_duplicates()
    retaining=signals[~signals["filter"].isin(contract_filters)].copy()
    retaining_keys=retaining[KEY+ ["filter"]].drop_duplicates()
    retained=primary_keys.merge(retaining_keys, on=KEY, how="left")
    retained["retained_by_non_primary"] = retained["filter"].astype(str).ne("") & retained["filter"].notna()
    retention=retained.groupby(KEY, dropna=False).agg(retaining_filter_count=("filter", lambda s: int(s.dropna().astype(str).replace("", pd.NA).dropna().nunique()))).reset_index()
    retention["retained_by_non_primary"]=retention["retaining_filter_count"]>0
    write_csv(out/"05_25c31_primary_filter_key_retention_matrix.csv", retention)
    family=retained[retained["retained_by_non_primary"].copy()].merge(signals[[*KEY,"filter","filter_family"]].drop_duplicates(), on=[*KEY,"filter"], how="left") if not retained.empty else pd.DataFrame(columns=["filter_family","retaining_filter_rows","retained_g1_keys"])
    if not family.empty:
        fam=family.groupby(["filter_family"], dropna=False).agg(retaining_filter_rows=("filter","count"), retained_g1_keys=("entry_time","nunique")).reset_index().sort_values("retaining_filter_rows", ascending=False)
    else:
        fam=pd.DataFrame(columns=["filter_family","retaining_filter_rows","retained_g1_keys"])
    write_csv(out/"06_25c31_retaining_filter_family_matrix.csv", fam)
    no_effect=delta.copy(); no_effect["is_zero_delta"]=pd.to_numeric(no_effect["delta"], errors="coerce").fillna(0).eq(0)
    write_csv(out/"04_25c31_no_effect_delta_review.csv", no_effect)
    retained_count=int(retention["retained_by_non_primary"].sum()) if not retention.empty else 0
    primary_key_count=int(len(primary_keys))
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"25C30 changed G1 counts","decision":"NO" if bool(no_effect["is_zero_delta"].all()) else "YES","observed":"all_delta_zero" if bool(no_effect["is_zero_delta"].all()) else "non_zero_delta"},
        {"decision_id":"D002","question":"primary-filter G1 keys retained by other filters","decision":"YES" if retained_count>0 else "NO","observed":f"{retained_count}/{primary_key_count}"},
        {"decision_id":"D003","question":"next review should target retaining filters","decision":"YES" if retained_count>0 else "NO","observed":"G1 key retention"},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c31_result_review_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C32_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"review non-primary filters retaining same G1 keys"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c31_next_step_plan.csv", nxt)
    unnecessary=["25C30 older reports if summary is available","full target rows","full replay rows"]
    necessary=["01_25c31_GOLD_V2_COREB_G1_NARROWED_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY_REPORT.md","02_25c31_coreb_g1_narrowed_dry_run_result_review_summary.json","04_25c31_no_effect_delta_review.csv","05_25c31_primary_filter_key_retention_matrix.csv","06_25c31_retaining_filter_family_matrix.csv","07_25c31_result_review_decision_matrix.csv","08_25c31_next_step_plan.csv"]
    write_csv(out/"00_不要_25c31_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"g1_counts_changed_in_25c30":False,"primary_filter_g1_key_count":primary_key_count,"retained_primary_g1_key_count":retained_count,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C32_COREB_G1_RETAINING_FILTER_REVIEW_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c31_coreb_g1_narrowed_dry_run_result_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C31 CoreB G1 narrowed dry-run result review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## No-effect delta review","",md_table(no_effect),"","## Primary filter key retention matrix","",md_table(retention),"","## Retaining filter family matrix","",md_table(fam),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c31_GOLD_V2_COREB_G1_NARROWED_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"retained_primary_g1_key_count":retained_count,"primary_filter_g1_key_count":primary_key_count,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
