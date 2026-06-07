#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C29_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY"
STATUS="COREB_G1_NARROWING_CANDIDATE_REVIEW_COMPLETED_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_NARROWED_DRY_RUN"
STOP="25C29_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c29_coreb_g1_narrowing_candidate_review_audit_only"
IN28="gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only"

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
    base=fx_outputs()/IN28
    req={
        "s28":base/"02_25c28_coreb_g1_filter_narrowing_plan_summary.json",
        "candidates":base/"04_25c28_narrowing_candidate_matrix.csv",
        "boundary":base/"05_25c28_boundary_matrix.csv",
        "gates":base/"06_25c28_acceptance_gate_matrix.csv",
        "next":base/"07_25c28_next_step_plan.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c29_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c29_coreb_g1_narrowing_candidate_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s28=read_json(req["s28"]); cand=read_csv(req["candidates"]); boundary=read_csv(req["boundary"]); gates=read_csv(req["gates"])
    cand["observed_rows"]=pd.to_numeric(cand.get("observed_rows",0), errors="coerce").fillna(0).astype(int)
    cand["observed_g1_keys"]=pd.to_numeric(cand.get("observed_g1_keys",0), errors="coerce").fillna(0).astype(int)
    cand["candidate_action"]=cand.get("candidate_action","").astype(str)
    review=cand.copy()
    review["review_status"]=review["candidate_action"].apply(lambda x: "PRIMARY_REVIEW" if x=="review_remove_or_raise_threshold" else "DIAGNOSTIC_REVIEW")
    review["execution_allowed_now"]=False
    write_csv(out/"04_25c29_candidate_review_matrix.csv", review)
    action=review.groupby(["candidate_action","review_status"], dropna=False).agg(candidate_count=("candidate_id","count"), observed_rows=("observed_rows","sum"), observed_g1_keys=("observed_g1_keys","sum")).reset_index().sort_values("observed_rows", ascending=False)
    write_csv(out/"05_25c29_candidate_action_summary.csv", action)
    primary_count=int((review["review_status"]=="PRIMARY_REVIEW").sum())
    diagnostic_count=int((review["review_status"]=="DIAGNOSTIC_REVIEW").sum())
    exec_gate=pd.DataFrame([
        {"gate_id":"G001","gate":"candidate set present","observed":len(review)>0,"status":"PASS" if len(review)>0 else "BLOCKED"},
        {"gate_id":"G002","gate":"primary candidates present","observed":primary_count>0,"status":"PASS" if primary_count>0 else "BLOCKED"},
        {"gate_id":"G003","gate":"narrowed dry-run execution allowed now","observed":False,"status":"BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"status":"BLOCKED"},
    ])
    write_csv(out/"06_25c29_execution_readiness_gate_matrix.csv", exec_gate)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"HUMAN_ACCEPT_25C29_BEFORE_25C30_NARROWED_DRY_RUN","allowed_now":False,"purpose":"explicit acceptance required"},
        {"rank":2,"next_step":"25C30_COREB_G1_NARROWED_DRY_RUN_AUDIT_ONLY","allowed_now":False,"purpose":"blocked until acceptance"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c29_next_step_plan.csv", nxt)
    unnecessary=["25C28 older reports if summary is available","full replay rows","full target rows"]
    necessary=["01_25c29_GOLD_V2_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md","02_25c29_coreb_g1_narrowing_candidate_review_summary.json","04_25c29_candidate_review_matrix.csv","05_25c29_candidate_action_summary.csv","06_25c29_execution_readiness_gate_matrix.csv","07_25c29_next_step_plan.csv"]
    write_csv(out/"00_不要_25c29_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"condition_changed":False,"full_coreb_parity":False,"candidate_count":int(len(review)),"primary_candidate_count":primary_count,"diagnostic_candidate_count":diagnostic_count,"narrowed_dry_run_executed":False,"requires_human_acceptance_before_25c30":True,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"HUMAN_ACCEPT_25C29_BEFORE_25C30_NARROWED_DRY_RUN","total_stop_rows":0}
    write_json(out/"02_25c29_coreb_g1_narrowing_candidate_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C29 CoreB G1 narrowing candidate review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Candidate review matrix","",md_table(review),"","## Candidate action summary","",md_table(action),"","## Execution readiness gates","",md_table(exec_gate),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c29_GOLD_V2_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"candidate_count":int(len(review)),"primary_candidate_count":primary_count,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
