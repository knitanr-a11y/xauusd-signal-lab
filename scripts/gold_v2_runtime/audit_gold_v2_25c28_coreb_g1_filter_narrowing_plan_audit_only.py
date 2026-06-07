#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C28_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY"
STATUS="COREB_G1_FILTER_NARROWING_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED"
STOP="25C28_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c28_coreb_g1_filter_narrowing_plan_audit_only"
IN27="gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only"

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
    base=fx_outputs()/IN27
    req={
        "s27":base/"02_25c27_coreb_g1_left_only_replay_filter_contract_summary.json",
        "drivers":base/"04_25c27_replay_filter_driver_matrix.csv",
        "families":base/"05_25c27_replay_filter_family_contract_matrix.csv",
        "risk":base/"06_25c27_replay_overlap_risk_matrix.csv",
        "decision":base/"07_25c27_replay_filter_contract_decision_matrix.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c28_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c28_coreb_g1_filter_narrowing_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s27=read_json(req["s27"]); drivers=read_csv(req["drivers"]); families=read_csv(req["families"]); risk=read_csv(req["risk"])
    drivers["rows"]=pd.to_numeric(drivers.get("rows",0), errors="coerce").fillna(0).astype(int)
    drivers["g1_keys"]=pd.to_numeric(drivers.get("g1_keys",0), errors="coerce").fillna(0).astype(int)
    top_family=str(s27.get("top_replay_filter_family",""))
    candidate_rows=[]
    top_drivers=drivers.sort_values(["rows","g1_keys"], ascending=[False,False]).head(8)
    for i, r in top_drivers.iterrows():
        fam=str(r.get("filter_family","")); filt=str(r.get("filter","")); rows=int(r.get("rows",0)); keys=int(r.get("g1_keys",0))
        action="review_remove_or_raise_threshold" if fam==top_family and rows>=30 else "diagnostic_keep_for_compare"
        candidate_rows.append({"candidate_id":f"N{len(candidate_rows)+1:03d}","filter_family":fam,"filter":filt,"observed_rows":rows,"observed_g1_keys":keys,"candidate_action":action,"executes_now":False})
    cand=pd.DataFrame(candidate_rows)
    write_csv(out/"04_25c28_narrowing_candidate_matrix.csv", cand)
    boundaries=pd.DataFrame([
        {"boundary":"change_coreb_conditions","allowed":False},
        {"boundary":"execute_narrowed_replay_now","allowed":False},
        {"boundary":"source_recovery","allowed":False},
        {"boundary":"live_evaluator_unblock","allowed":False},
        {"boundary":"prepare_filter_narrowing_plan","allowed":True},
    ])
    write_csv(out/"05_25c28_boundary_matrix.csv", boundaries)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C27 top family identified","observed":bool(top_family),"required":True,"status":"PASS" if top_family else "BLOCKED"},
        {"gate_id":"G002","gate":"narrowing candidates present","observed":len(cand)>0,"required":True,"status":"PASS" if len(cand)>0 else "BLOCKED"},
        {"gate_id":"G003","gate":"narrowed replay execution allowed now","observed":False,"required":False,"status":"BLOCKED_PLAN_ONLY"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out/"06_25c28_acceptance_gate_matrix.csv", gates)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C29_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"review candidate narrowing set before any execution"},
        {"rank":2,"next_step":"narrowed replay execution","allowed_now":False,"purpose":"blocked until candidate review"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c28_next_step_plan.csv", nxt)
    unnecessary=["25C27 older reports if summary is available","full replay rows","full target rows"]
    necessary=["01_25c28_GOLD_V2_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY_REPORT.md","02_25c28_coreb_g1_filter_narrowing_plan_summary.json","04_25c28_narrowing_candidate_matrix.csv","05_25c28_boundary_matrix.csv","06_25c28_acceptance_gate_matrix.csv","07_25c28_next_step_plan.csv"]
    write_csv(out/"00_不要_25c28_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    review_first_count=int((cand["candidate_action"]=="review_remove_or_raise_threshold").sum()) if len(cand) else 0
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"condition_changed":False,"full_coreb_parity":False,"top_replay_filter_family":top_family,"narrowing_candidate_count":int(len(cand)),"review_first_candidate_count":review_first_count,"narrowed_replay_executed":False,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C29_COREB_G1_NARROWING_CANDIDATE_REVIEW_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c28_coreb_g1_filter_narrowing_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C28 CoreB G1 filter narrowing plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Narrowing candidate matrix","",md_table(cand),"","## Boundary matrix","",md_table(boundaries),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c28_GOLD_V2_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"narrowing_candidate_count":int(len(cand)),"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
