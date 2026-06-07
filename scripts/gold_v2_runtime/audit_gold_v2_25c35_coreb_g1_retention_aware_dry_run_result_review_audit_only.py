#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C35_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"
STATUS="COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_OVER_NARROWING_ADJUSTMENT_REQUIRED"
STOP="25C35_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c35_coreb_g1_retention_aware_dry_run_result_review_audit_only"
IN34="gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only"

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

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    base=fx_outputs()/IN34
    req={
        "s34":base/"02_25c34_coreb_g1_retention_aware_dry_run_summary.json",
        "contract":base/"04_25c34_variant_filter_contract.csv",
        "compare":base/"05_25c34_variant_compare_matrix.csv",
        "delta":base/"06_25c34_variant_delta_matrix.csv",
        "by_policy":base/"07_25c34_variant_by_dataset_policy.csv",
        "gates":base/"09_25c34_acceptance_gate_matrix.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c35_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c35_coreb_g1_retention_aware_dry_run_result_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s34=read_json(req["s34"]); contract=read_csv(req["contract"]); compare=read_csv(req["compare"]); delta=read_csv(req["delta"]); gates=read_csv(req["gates"])
    for c in ["replay_g1_rows","both","left_only","right_only"]:
        compare[c]=pd.to_numeric(compare[c], errors="coerce").fillna(0).astype(int)
    base_row=compare[compare["variant"].eq("BASELINE_CURRENT")].iloc[0]
    review=compare[~compare["variant"].eq("BASELINE_CURRENT")].copy()
    review["left_only_reduction"]=int(base_row["left_only"])-review["left_only"]
    review["right_only_increase"]=review["right_only"]-int(base_row["right_only"])
    review["both_loss"]=int(base_row["both"])-review["both"]
    review["over_narrowing_score"]=review["right_only_increase"]+review["both_loss"]
    review["net_tradeoff_score"]=review["left_only_reduction"]-review["over_narrowing_score"]
    review["review_class"]=review.apply(lambda r: "OVER_NARROWED" if r["right_only_increase"]>0 or r["both_loss"]>0 else "NO_OVER_NARROWING", axis=1)
    review=review.sort_values(["net_tradeoff_score","left_only_reduction"], ascending=[False,False])
    write_csv(out/"04_25c35_variant_tradeoff_matrix.csv", review)
    best_variant=str(s34.get("best_variant", review.iloc[0]["variant"] if len(review) else ""))
    best=review[review["variant"].astype(str).eq(best_variant)].copy()
    if best.empty and len(review): best=review.head(1).copy()
    best_review=best[["variant","left_only","right_only","both","left_only_reduction","right_only_increase","both_loss","over_narrowing_score","net_tradeoff_score","review_class"]].copy() if not best.empty else pd.DataFrame()
    best_review["usable_as_is"]=False
    best_review["reason"]="left_only improves but right_only increase and/or both loss remains unacceptable"
    write_csv(out/"05_25c35_best_variant_review_matrix.csv", best_review)
    over=bool((review["review_class"]=="OVER_NARROWED").any())
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"any exact match reached in 25C34","decision":"NO" if not bool(s34.get("any_exact_match", False)) else "YES","observed":bool(s34.get("any_exact_match", False))},
        {"decision_id":"D002","question":"best variant improves left_only","decision":"YES" if not best.empty and int(best.iloc[0]["left_only_reduction"])>0 else "NO","observed":int(best.iloc[0]["left_only_reduction"]) if not best.empty else 0},
        {"decision_id":"D003","question":"best variant over-narrows","decision":"YES" if not best.empty and str(best.iloc[0]["review_class"])=="OVER_NARROWED" else "NO","observed":str(best.iloc[0]["review_class"]) if not best.empty else "NONE"},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"06_25c35_over_narrowing_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C36_COREB_G1_OVER_NARROWING_ADJUSTMENT_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"plan less destructive bundle adjustment"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c35_next_step_plan.csv", nxt)
    unnecessary=["25C34 older reports if summary is available","full target rows","full replay rows"]
    necessary=["01_25c35_GOLD_V2_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY_REPORT.md","02_25c35_coreb_g1_retention_aware_dry_run_result_review_summary.json","04_25c35_variant_tradeoff_matrix.csv","05_25c35_best_variant_review_matrix.csv","06_25c35_over_narrowing_decision_matrix.csv","07_25c35_next_step_plan.csv"]
    write_csv(out/"00_不要_25c35_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"best_variant":best_variant,"best_variant_usable_as_is":False,"over_narrowing_detected":over,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C36_COREB_G1_OVER_NARROWING_ADJUSTMENT_PLAN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c35_coreb_g1_retention_aware_dry_run_result_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C35 CoreB G1 retention-aware dry-run result review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Variant tradeoff matrix","",md_table(review),"","## Best variant review matrix","",md_table(best_review),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c35_GOLD_V2_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"best_variant":best_variant,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
