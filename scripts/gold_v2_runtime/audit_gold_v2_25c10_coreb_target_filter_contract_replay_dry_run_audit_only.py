#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C10_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY"
PASS_STATUS = "COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED"
STOP_STATUS = "25C10_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C10B = "gold_v2_25c10b_coreb_filter_replay_execution_decision_audit_only"
IN25C9 = "gold_v2_25c9_coreb_target_filter_contract_replay_plan_audit_only"
IN25C10A = "gold_v2_25c10a_coreb_unique_origin_metric_derivation_audit_only"
IN25C3 = "gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only"
IN25C7 = "gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
TARGET_LEDGER_NAME = "rr125_top_ledgers.csv"
SAFETY_FLAGS = {"source_recovery_execution_allowed_now":False,"source_mutation_allowed":False,"source_identity_finalization_allowed_now":False,"live_evaluator_final_signal_allowed":False,"final_signal_allowed":False,"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False,"no_signal_discord_notification_allowed":False,"old_gold_disc8_quarantined":True,"source_recovery_chain_status":"PAUSED_AT_24AF"}

def parse_args(argv: Optional[Sequence[str]]=None)->argparse.Namespace:
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", default=None); return p.parse_args(argv)
def repo_root()->Path: return Path(__file__).resolve().parents[2]
def files_dir_from_repo()->Path:
    r=repo_root(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx_outputs()->Path: return files_dir_from_repo()/"FX_OUTPUTS"
def lp(path:Path)->Path:
    if os.name!="nt": return path
    s=str(path)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def read_csv(path:Path)->pd.DataFrame:
    last=None
    for enc in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as e: last=e
    raise RuntimeError(f"Could not read {path}: {last}")
def read_json(path:Path)->dict[str,Any]: return json.loads(lp(path).read_text(encoding="utf-8-sig"))
def write_csv(path:Path, df:pd.DataFrame)->None:
    lp(path.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(path), index=False, encoding="utf-8-sig")
def write_json(path:Path, obj:dict[str,Any])->None:
    lp(path.parent).mkdir(parents=True, exist_ok=True); lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
def md_table(df:pd.DataFrame, max_rows:int=80)->str:
    if df.empty: return "_No rows._"
    v=df.head(max_rows); cols=list(v.columns)
    lines=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in cols)+" |")
    if len(df)>max_rows: lines.append(f"| ... | truncated {len(df)-max_rows} more rows |"+" |"*max(0,len(cols)-2))
    return "\n".join(lines)

def path_from_audit(df:pd.DataFrame, name:str)->Path:
    m=df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0]["absolute_path"])) if not m.empty else Path("")

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_FILTER_REPLAY_EXECUTION_DECISION_COMPLETED_AUDIT_ONLY_25C10_READY": p.append("25C10B status mismatch")
    if not bool(s.get("filter_replay_allowed_next")): p.append("25C10B filter_replay_allowed_next not true")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    req={
        "25c10b_summary":fx_outputs()/IN25C10B/"02_25c10b_coreb_filter_replay_execution_decision_summary.json",
        "filter_plan":fx_outputs()/IN25C9/"04_25c9_filter_contract_plan.csv",
        "origin_counts":fx_outputs()/IN25C10A/"04_25c10a_unique_origin_counts_by_entry_time.csv",
        "selected_hits":fx_outputs()/IN25C3/"08_25c3_selected_rule_hit_rows.csv",
        "25c7_summary":fx_outputs()/IN25C7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "25b3_file_audit":fx_outputs()/IN25B3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c10_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c10b_summary"]); problems=safety_problems(s); audit=read_csv(req["25b3_file_audit"]); target_path=path_from_audit(audit,TARGET_LEDGER_NAME)
    if not str(target_path) or not lp(target_path).exists(): problems.append("target ledger missing")
    if problems:
        write_json(out_dir/"02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    plan=read_csv(req["filter_plan"]); metrics=read_csv(req["origin_counts"]); sel=read_csv(req["selected_hits"]); target=read_csv(target_path); s7=read_json(req["25c7_summary"])
    feature_min=pd.to_datetime(s7.get("feature_min_time"), errors="coerce"); feature_max=pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    for df in [plan,metrics,sel,target]:
        for c in ["dataset","entry_time","policy"]:
            if c in df.columns: df[c]=df[c].astype(str)
    # selected hit is entry-time+policy level; if policy absent, keep dataset+entry_time only and fan-out later.
    if "policy" in sel.columns:
        selected=sel[["dataset","entry_time","policy"]].drop_duplicates().copy()
    else:
        selected=sel[["dataset","entry_time"]].drop_duplicates().copy(); selected["policy"]=""
    # metrics may lack policy because source counts may be policy-independent; duplicate across plan policies after join by dataset/time if needed.
    if "policy" in metrics.columns:
        metric_key=["dataset","entry_time","policy"]
    else:
        metric_key=["dataset","entry_time"]
    rows=[]
    for _,f in plan.iterrows():
        pol=str(f.get("policy","")); filt=str(f.get("filter",""))
        sc=pd.to_numeric(pd.Series([f.get("same_count_threshold","")]), errors="coerce").iloc[0]
        uc=pd.to_numeric(pd.Series([f.get("unique_origins_threshold","")]), errors="coerce").iloc[0]
        sel_pol=selected[selected["policy"].eq(pol)] if "policy" in selected.columns and pol else selected.copy()
        m=metrics.copy()
        if "policy" in m.columns and pol: m=m[m["policy"].eq(pol)]
        base=sel_pol.merge(m, on=[c for c in ["dataset","entry_time","policy"] if c in sel_pol.columns and c in m.columns], how="inner")
        base["source_count_by_entry_time"] = pd.to_numeric(base.get("source_count_by_entry_time",0), errors="coerce").fillna(0)
        base["unique_origin_count_by_entry_time"] = pd.to_numeric(base.get("unique_origin_count_by_entry_time",0), errors="coerce").fillna(0)
        cond=pd.Series(True, index=base.index)
        if pd.notna(sc): cond &= base["source_count_by_entry_time"].ge(float(sc))
        if pd.notna(uc): cond &= base["unique_origin_count_by_entry_time"].ge(float(uc))
        hit=base[cond].copy()
        if not hit.empty:
            hit["policy"]=pol; hit["filter"]=filt; hit["same_count_threshold"]="" if pd.isna(sc) else int(sc); hit["unique_origins_threshold"]="" if pd.isna(uc) else int(uc); hit["intersection_only"]=True; hit["full_coreb_parity"]=False
            rows.append(hit[["dataset","entry_time","policy","filter","source_count_by_entry_time","unique_origin_count_by_entry_time","same_count_threshold","unique_origins_threshold","intersection_only","full_coreb_parity"]].drop_duplicates())
    signals=pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["dataset","entry_time","policy","filter","source_count_by_entry_time","unique_origin_count_by_entry_time","same_count_threshold","unique_origins_threshold","intersection_only","full_coreb_parity"])
    write_csv(out_dir/"04_25c10_filter_replay_signal_rows.csv", signals)
    target["time_norm"]=pd.to_datetime(target["entry_time"], errors="coerce")
    target_scope=target[(target["time_norm"]>=feature_min)&(target["time_norm"]<=feature_max)].copy()
    if "filter" not in target_scope.columns: target_scope["filter"]=""
    tkey=target_scope[["dataset","entry_time","policy","filter"]].drop_duplicates(); skey=signals[["dataset","entry_time","policy","filter"]].drop_duplicates()
    cmp=skey.merge(tkey,on=["dataset","entry_time","policy","filter"],how="outer",indicator=True)
    matrix=cmp["_merge"].value_counts(dropna=False).reset_index(); matrix.columns=["compare_status","filter_rows"]
    write_csv(out_dir/"05_25c10_filter_level_compare_matrix.csv", matrix)
    by_contract=cmp.merge(plan[["policy","filter","filter_class"]].drop_duplicates(),on=["policy","filter"],how="left").groupby(["policy","filter","filter_class","_merge"],dropna=False).size().reset_index(name="rows")
    write_csv(out_dir/"06_25c10_filter_compare_by_contract.csv", by_contract)
    write_csv(out_dir/"07_25c10_extra_signal_samples.csv", cmp[cmp["_merge"].eq("left_only")].head(300))
    write_csv(out_dir/"08_25c10_missing_target_samples.csv", cmp[cmp["_merge"].eq("right_only")].head(300))
    both=int((cmp["_merge"]=="both").sum()); left=int((cmp["_merge"]=="left_only").sum()); right=int((cmp["_merge"]=="right_only").sum())
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C10B ready","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"filter-specific replay executed","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G003","gate":"filter-level target matches exist","observed":both>0,"required":True,"status":"PASS" if both>0 else "BLOCKED"},
        {"gate_id":"G004","gate":"no extra filter signals","observed":left==0,"required":True,"status":"PASS" if left==0 else "REVIEW"},
        {"gate_id":"G005","gate":"no missing target filters","observed":right==0,"required":True,"status":"PASS" if right==0 else "REVIEW"},
        {"gate_id":"G006","gate":"full_coreb_parity","observed":False,"required":False,"status":"BLOCKED"},
        {"gate_id":"G007","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out_dir/"09_25c10_replay_gate_matrix.csv", gates)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C11_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"Review filter-specific replay parity/mismatches"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked by intersection-only and mismatch review"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"10_25c10_next_step_plan.csv", next_plan)
    unnecessary=["25C10B decision files already processed","25C9/25C10A older summaries","target ledger alone"]
    necessary=["01_25c10_GOLD_V2_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY_REPORT.md","02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json","04_25c10_filter_replay_signal_rows.csv","05_25c10_filter_level_compare_matrix.csv","06_25c10_filter_compare_by_contract.csv","09_25c10_replay_gate_matrix.csv","10_25c10_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c10_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"filter_specific_replay":True,"condition_changed":False,"intersection_only":True,"full_coreb_parity":False,"filter_replay_signal_rows":int(len(skey)),"target_filter_rows_in_scope":int(len(tkey)),"filter_level_both":both,"filter_level_left_only":left,"filter_level_right_only":right,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C11_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json", summary)
    report="\n".join(["# GOLD V2 25C10 CoreB target filter contract replay dry-run audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Boundary","","25C10 executes filter-specific diagnostic replay. It does not prove full CoreB parity or unblock CoreB.","","## Filter-level compare matrix","",md_table(matrix),"","## Replay gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c10_GOLD_V2_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"filter_level_both":both,"filter_level_left_only":left,"filter_level_right_only":right,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
