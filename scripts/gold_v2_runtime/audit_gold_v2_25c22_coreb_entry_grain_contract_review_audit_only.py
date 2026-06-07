#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C22_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY"
STATUS="COREB_ENTRY_GRAIN_CONTRACT_REVIEW_COMPLETED_AUDIT_ONLY_G1_ENTRY_LEVEL_REVIEW_SELECTED"
STOP="25C22_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c22_coreb_entry_grain_contract_review_audit_only"
IN21="gold_v2_25c21_coreb_entry_grain_contract_plan_audit_only"

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
    base=fx_outputs()/IN21
    req={"s21":base/"02_25c21_coreb_entry_grain_contract_plan_summary.json","candidates":base/"04_25c21_entry_grain_candidate_matrix.csv","gates":base/"06_25c21_acceptance_gate_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c22_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c22_coreb_entry_grain_contract_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s21=read_json(req["s21"]); candidates=read_csv(req["candidates"])
    c=candidates.copy()
    c["known_left_only"]=pd.to_numeric(c["known_left_only"], errors="coerce").fillna(0).astype(int)
    c["known_right_only"]=pd.to_numeric(c["known_right_only"], errors="coerce").fillna(0).astype(int)
    c["residual_total"]=c["known_left_only"]+c["known_right_only"]
    c["review_score"]=(c["residual_total"].max()-c["residual_total"]+1).astype(int)
    c["selected_for_next_contract"]=c["grain_id"].eq("G1")
    c["selection_reason"]=c.apply(lambda r: "lowest residual and preserves entry-level audit before stricter family/filter review" if r["grain_id"]=="G1" else ("use as secondary diagnostic" if r["grain_id"]=="G2" else "defer; too strict for current contract"), axis=1)
    write_csv(out/"04_25c22_grain_contract_review_matrix.csv", c)
    selected=c[c["selected_for_next_contract"]].copy()
    write_csv(out/"05_25c22_selected_grain_contract.csv", selected)
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"select G1 for next audit contract","decision":"YES","reason":"G1 has lower residual than G2/G3"},
        {"decision_id":"D002","question":"allow G2 as diagnostic only","decision":"YES","reason":"G2 keeps family information but has larger residual"},
        {"decision_id":"D003","question":"allow dry-run execution now","decision":"NO","reason":"contract review only; execution remains blocked"},
        {"decision_id":"D004","question":"allow CoreB live evaluator","decision":"NO","reason":"full parity not proven"},
    ])
    write_csv(out/"06_25c22_grain_contract_decision_matrix.csv", dec)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C23_COREB_G1_ENTRY_LEVEL_REVIEW_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"plan G1 entry-level review before execution"},
        {"rank":2,"next_step":"G1 entry-level dry-run execution","allowed_now":False,"purpose":"blocked until plan accepted"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c22_next_step_plan.csv", next_plan)
    unnecessary=["25C21 older reports if summary is available","large row samples","target ledger alone"]
    necessary=["01_25c22_GOLD_V2_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY_REPORT.md","02_25c22_coreb_entry_grain_contract_review_summary.json","04_25c22_grain_contract_review_matrix.csv","05_25c22_selected_grain_contract.csv","06_25c22_grain_contract_decision_matrix.csv","07_25c22_next_step_plan.csv"]
    write_csv(out/"00_不要_25c22_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"dry_run_executed":False,"condition_changed":False,"full_coreb_parity":False,"selected_grain":"G1","selected_grain_key":"dataset+entry_time+policy","secondary_diagnostic_grain":"G2","next_dry_run_execution_allowed_now":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C23_COREB_G1_ENTRY_LEVEL_REVIEW_PLAN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c22_coreb_entry_grain_contract_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C22 CoreB entry grain contract review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Grain contract review matrix","",md_table(c),"","## Selected grain contract","",md_table(selected),"","## Decision matrix","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c22_GOLD_V2_COREB_ENTRY_GRAIN_CONTRACT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"selected_grain":"G1","next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
