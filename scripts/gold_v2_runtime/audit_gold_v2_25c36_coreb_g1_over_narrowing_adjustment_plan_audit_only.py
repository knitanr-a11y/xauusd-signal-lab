#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C36_COREB_G1_OVER_NARROWING_ADJUSTMENT_PLAN_AUDIT_ONLY"
STATUS="COREB_G1_OVER_NARROWING_ADJUSTMENT_PLAN_READY_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_DRY_RUN"
STOP="25C36_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only"
IN35="gold_v2_25c35_coreb_g1_retention_aware_dry_run_result_review_audit_only"
IN34="gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only"
IN33="gold_v2_25c33_coreb_g1_retention_aware_narrowing_plan_audit_only"

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

def unique(seq):
    out=[]
    for x in seq:
        x=str(x)
        if x and x not in out: out.append(x)
    return out

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s35":fx_outputs()/IN35/"02_25c35_coreb_g1_retention_aware_dry_run_result_review_summary.json",
        "tradeoff":fx_outputs()/IN35/"04_25c35_variant_tradeoff_matrix.csv",
        "best_review":fx_outputs()/IN35/"05_25c35_best_variant_review_matrix.csv",
        "contract34":fx_outputs()/IN34/"04_25c34_variant_filter_contract.csv",
        "member33":fx_outputs()/IN33/"05_25c33_bundle_filter_membership.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c36_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c36_coreb_g1_over_narrowing_adjustment_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s35=read_json(req["s35"]); trade=read_csv(req["tradeoff"]); best=read_csv(req["best_review"]); c34=read_csv(req["contract34"]); m33=read_csv(req["member33"])
    b001=unique(c34[c34["bundle_id"].astype(str).eq("B001")]["filter"].tolist())
    b002=unique(c34[c34["bundle_id"].astype(str).eq("B002")]["filter"].tolist())
    primary=[f for f in b001 if "same_count>=" in f and "unique_origins>=2" in f and not f.startswith("unique_origins")]
    top_retainer=["unique_origins>=2"]
    sc8=["same_count>=8"]
    sc8u=["same_count>=8&unique_origins>=2"]
    sc10=["same_count>=10"]
    sc10u=["same_count>=10&unique_origins>=2"]
    bundles=[
        ("A001","PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8", unique(primary+top_retainer+sc8)),
        ("A002","PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U", unique(primary+top_retainer+sc8u)),
        ("A003","PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR", unique(primary+top_retainer+sc8+sc8u)),
        ("A004","PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR", unique(primary+top_retainer+sc10+sc10u)),
    ]
    rows=[]; mem=[]
    for bid,name,filters in bundles:
        rows.append({"adjusted_bundle_id":bid,"bundle_name":name,"filter_count":len(filters),"executes_now":False,"requires_acceptance":True,"intent":"less destructive than B002; stronger than B001"})
        for i,f in enumerate(filters,1): mem.append({"adjusted_bundle_id":bid,"member_order":i,"filter":f})
    bdf=pd.DataFrame(rows); mdf=pd.DataFrame(mem)
    write_csv(out/"04_25c36_adjusted_bundle_candidate_matrix.csv", bdf)
    write_csv(out/"05_25c36_adjusted_bundle_membership.csv", mdf)
    boundary=pd.DataFrame([
        {"boundary":"execute_adjusted_dry_run_now","allowed":False},
        {"boundary":"change_coreb_conditions","allowed":False},
        {"boundary":"source_recovery","allowed":False},
        {"boundary":"live_evaluator_unblock","allowed":False},
        {"boundary":"prepare_adjusted_bundles","allowed":True},
    ])
    write_csv(out/"06_25c36_execution_boundary_matrix.csv", boundary)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C35 over-narrowing detected","observed":bool(s35.get("over_narrowing_detected", False)),"status":"PASS" if bool(s35.get("over_narrowing_detected", False)) else "BLOCKED"},
        {"gate_id":"G002","gate":"adjusted bundles created","observed":len(bdf)>0,"status":"PASS" if len(bdf)>0 else "BLOCKED"},
        {"gate_id":"G003","gate":"adjusted dry-run execution allowed now","observed":False,"status":"BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"status":"BLOCKED"},
    ])
    write_csv(out/"07_25c36_acceptance_gate_matrix.csv", gates)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"HUMAN_ACCEPT_25C36_BEFORE_25C37_ADJUSTED_DRY_RUN","allowed_now":False,"purpose":"explicit acceptance required"},
        {"rank":2,"next_step":"25C37_COREB_G1_ADJUSTED_NARROWING_DRY_RUN_AUDIT_ONLY","allowed_now":False,"purpose":"blocked until acceptance"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c36_next_step_plan.csv", nxt)
    unnecessary=["25C35 older reports if summary is available","full replay rows","full target rows"]
    necessary=["01_25c36_GOLD_V2_COREB_G1_OVER_NARROWING_ADJUSTMENT_PLAN_AUDIT_ONLY_REPORT.md","02_25c36_coreb_g1_over_narrowing_adjustment_plan_summary.json","04_25c36_adjusted_bundle_candidate_matrix.csv","05_25c36_adjusted_bundle_membership.csv","06_25c36_execution_boundary_matrix.csv","07_25c36_acceptance_gate_matrix.csv","08_25c36_next_step_plan.csv"]
    write_csv(out/"00_不要_25c36_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"condition_changed":False,"full_coreb_parity":False,"adjusted_bundle_count":int(len(bdf)),"adjusted_dry_run_executed":False,"requires_human_acceptance_before_25c37":True,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"HUMAN_ACCEPT_25C36_BEFORE_25C37_ADJUSTED_DRY_RUN","total_stop_rows":0}
    write_json(out/"02_25c36_coreb_g1_over_narrowing_adjustment_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C36 CoreB G1 over-narrowing adjustment plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Adjusted bundle candidate matrix","",md_table(bdf),"","## Adjusted bundle membership","",md_table(mdf),"","## Execution boundaries","",md_table(boundary),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c36_GOLD_V2_COREB_G1_OVER_NARROWING_ADJUSTMENT_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"adjusted_bundle_count":int(len(bdf)),"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
