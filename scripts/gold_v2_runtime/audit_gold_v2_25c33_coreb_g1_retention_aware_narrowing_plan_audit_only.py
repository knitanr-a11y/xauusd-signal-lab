#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C33_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY"
STATUS="COREB_G1_RETENTION_AWARE_NARROWING_PLAN_READY_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_DRY_RUN"
STOP="25C33_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c33_coreb_g1_retention_aware_narrowing_plan_audit_only"
IN32="gold_v2_25c32_coreb_g1_retaining_filter_review_audit_only"
IN30="gold_v2_25c30_coreb_g1_narrowed_dry_run_audit_only"

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
    req={
        "s32":fx_outputs()/IN32/"02_25c32_coreb_g1_retaining_filter_review_summary.json",
        "drivers":fx_outputs()/IN32/"04_25c32_retaining_filter_driver_matrix.csv",
        "families":fx_outputs()/IN32/"05_25c32_retaining_filter_family_matrix.csv",
        "distribution":fx_outputs()/IN32/"06_25c32_retention_count_distribution.csv",
        "primary_contract":fx_outputs()/IN30/"04_25c30_candidate_execution_contract.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c33_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c33_coreb_g1_retention_aware_narrowing_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s32=read_json(req["s32"]); drivers=read_csv(req["drivers"]); families=read_csv(req["families"]); dist=read_csv(req["distribution"]); primary=read_csv(req["primary_contract"])
    primary_filters=primary["filter"].astype(str).tolist()
    drivers["retained_g1_keys"]=pd.to_numeric(drivers.get("retained_g1_keys",0), errors="coerce").fillna(0).astype(int)
    drivers["retaining_rows"]=pd.to_numeric(drivers.get("retaining_rows",0), errors="coerce").fillna(0).astype(int)
    top_retainer=str(drivers.sort_values("retaining_rows", ascending=False).iloc[0]["filter"]) if len(drivers) else ""
    secondary=drivers.sort_values("retaining_rows", ascending=False).head(5)["filter"].astype(str).tolist()
    bundles=[
        {"bundle_id":"B001","bundle_name":"PRIMARY_PLUS_TOP_RETAINER","description":"primary 25C30 filters plus top retaining filter","filters":primary_filters+[top_retainer]},
        {"bundle_id":"B002","bundle_name":"PRIMARY_PLUS_TOP5_RETAINERS","description":"primary 25C30 filters plus top five retaining filters","filters":primary_filters+secondary},
        {"bundle_id":"B003","bundle_name":"UNIQUE_ORIGINS_RETAINERS_ONLY","description":"retaining filters from unique_origins family","filters":drivers[drivers.get("filter_family_derived","").astype(str).eq("unique_origins_only")]["filter"].astype(str).tolist()},
    ]
    bundle_rows=[]; member_rows=[]
    for b in bundles:
        uniq=[]
        for f in b["filters"]:
            if f and f not in uniq: uniq.append(f)
        bundle_rows.append({"bundle_id":b["bundle_id"],"bundle_name":b["bundle_name"],"description":b["description"],"filter_count":len(uniq),"executes_now":False,"requires_acceptance":True})
        for idx,f in enumerate(uniq,1):
            hit=drivers[drivers["filter"].astype(str).eq(f)]
            member_rows.append({"bundle_id":b["bundle_id"],"member_order":idx,"filter":f,"retaining_rows":int(hit.iloc[0]["retaining_rows"]) if len(hit) else 0,"retained_g1_keys":int(hit.iloc[0]["retained_g1_keys"]) if len(hit) else 0})
    bundle_df=pd.DataFrame(bundle_rows); member_df=pd.DataFrame(member_rows)
    write_csv(out/"04_25c33_retention_aware_bundle_matrix.csv", bundle_df)
    write_csv(out/"05_25c33_bundle_filter_membership.csv", member_df)
    boundary=pd.DataFrame([
        {"boundary":"execute_retention_aware_dry_run_now","allowed":False},
        {"boundary":"change_coreb_conditions","allowed":False},
        {"boundary":"source_recovery","allowed":False},
        {"boundary":"live_evaluator_unblock","allowed":False},
        {"boundary":"prepare_candidate_bundles","allowed":True},
    ])
    write_csv(out/"06_25c33_execution_boundary_matrix.csv", boundary)
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"retaining filters identified","observed":len(drivers)>0,"status":"PASS" if len(drivers)>0 else "BLOCKED"},
        {"gate_id":"G002","gate":"candidate bundles created","observed":len(bundle_df)>0,"status":"PASS" if len(bundle_df)>0 else "BLOCKED"},
        {"gate_id":"G003","gate":"dry-run execution allowed now","observed":False,"status":"BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id":"G004","gate":"CoreB live evaluator unblock","observed":False,"status":"BLOCKED"},
    ])
    write_csv(out/"07_25c33_acceptance_gate_matrix.csv", gates)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"HUMAN_ACCEPT_25C33_BEFORE_25C34_RETENTION_AWARE_DRY_RUN","allowed_now":False,"purpose":"explicit acceptance required"},
        {"rank":2,"next_step":"25C34_COREB_G1_RETENTION_AWARE_DRY_RUN_AUDIT_ONLY","allowed_now":False,"purpose":"blocked until acceptance"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c33_next_step_plan.csv", nxt)
    unnecessary=["25C32 older reports if summary is available","full replay rows","full target rows"]
    necessary=["01_25c33_GOLD_V2_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY_REPORT.md","02_25c33_coreb_g1_retention_aware_narrowing_plan_summary.json","04_25c33_retention_aware_bundle_matrix.csv","05_25c33_bundle_filter_membership.csv","06_25c33_execution_boundary_matrix.csv","07_25c33_acceptance_gate_matrix.csv","08_25c33_next_step_plan.csv"]
    write_csv(out/"00_不要_25c33_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"plan_only":True,"condition_changed":False,"full_coreb_parity":False,"top_retaining_filter":top_retainer,"bundle_count":int(len(bundle_df)),"retention_aware_dry_run_executed":False,"requires_human_acceptance_before_25c34":True,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"HUMAN_ACCEPT_25C33_BEFORE_25C34_RETENTION_AWARE_DRY_RUN","total_stop_rows":0}
    write_json(out/"02_25c33_coreb_g1_retention_aware_narrowing_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C33 CoreB G1 retention-aware narrowing plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Retention-aware bundle matrix","",md_table(bundle_df),"","## Bundle filter membership","",md_table(member_df),"","## Execution boundaries","",md_table(boundary),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c33_GOLD_V2_COREB_G1_RETENTION_AWARE_NARROWING_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"bundle_count":int(len(bundle_df)),"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
