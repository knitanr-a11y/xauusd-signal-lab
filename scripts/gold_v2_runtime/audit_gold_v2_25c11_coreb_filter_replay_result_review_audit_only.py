#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C11_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY"
PASS_STATUS = "COREB_FILTER_REPLAY_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_POLICY_MAPPING_REVIEW_REQUIRED"
STOP_STATUS = "25C11_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C10 = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
OUT_DIR = "gold_v2_25c11_coreb_filter_replay_result_review_audit_only"
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

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED": p.append("25C10 status mismatch")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in_dir=fx_outputs()/IN25C10
    req={"25c10_summary":in_dir/"02_25c10_coreb_target_filter_contract_replay_dry_run_summary.json","signals":in_dir/"04_25c10_filter_replay_signal_rows.csv","compare":in_dir/"05_25c10_filter_level_compare_matrix.csv","by_contract":in_dir/"06_25c10_filter_compare_by_contract.csv","gates":in_dir/"09_25c10_replay_gate_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c11_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c11_coreb_filter_replay_result_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c10_summary"]); problems=safety_problems(s)
    if problems:
        write_json(out_dir/"02_25c11_coreb_filter_replay_result_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    sig=read_csv(req["signals"]); by=read_csv(req["by_contract"]); compare=read_csv(req["compare"]); gates_in=read_csv(req["gates"])
    # remove zero rows and normalize columns
    by["rows"]=pd.to_numeric(by["rows"], errors="coerce").fillna(0).astype(int)
    nz=by[by["rows"].gt(0)].copy()
    pivot=nz.pivot_table(index=["policy","filter"], columns="_merge", values="rows", aggfunc="sum", fill_value=0).reset_index()
    for c in ["both","left_only","right_only"]:
        if c not in pivot.columns: pivot[c]=0
    pivot["total_compare_rows"]=pivot[["both","left_only","right_only"]].sum(axis=1)
    pivot["match_rate"]=(pivot["both"] / pivot["total_compare_rows"].where(pivot["total_compare_rows"].ne(0), 1)).round(6)
    sig_policy=sig.groupby("policy", dropna=False).size().reset_index(name="signal_filter_rows") if "policy" in sig.columns else pd.DataFrame(columns=["policy","signal_filter_rows"])
    target_like=nz[nz["_merge"].isin(["both","right_only"])].groupby("policy", dropna=False)["rows"].sum().reset_index(name="target_filter_rows_in_compare")
    extra_like=nz[nz["_merge"].eq("left_only")].groupby("policy", dropna=False)["rows"].sum().reset_index(name="extra_filter_rows")
    policy_matrix=sig_policy.merge(target_like,on="policy",how="outer").merge(extra_like,on="policy",how="outer").fillna(0)
    for c in ["signal_filter_rows","target_filter_rows_in_compare","extra_filter_rows"]: policy_matrix[c]=policy_matrix[c].astype(int)
    policy_matrix["policy_issue_class"]=policy_matrix.apply(lambda r: "TARGET_POLICY_WITH_NO_SIGNAL" if r["signal_filter_rows"]==0 and r["target_filter_rows_in_compare"]>0 else ("SIGNAL_POLICY_WITH_EXTRA" if r["extra_filter_rows"]>0 else "MIXED_OR_MATCHING"), axis=1)
    write_csv(out_dir/"04_25c11_policy_signal_target_matrix.csv", policy_matrix)
    write_csv(out_dir/"05_25c11_filter_contract_match_rate_matrix.csv", pivot.sort_values(["match_rate","total_compare_rows"], ascending=[True,False]))
    write_csv(out_dir/"06_25c11_top_overgenerated_contracts.csv", pivot[pivot["left_only"].gt(0)].sort_values("left_only", ascending=False).head(50))
    write_csv(out_dir/"07_25c11_top_missing_contracts.csv", pivot[pivot["right_only"].gt(0)].sort_values("right_only", ascending=False).head(50))
    all_buy_missing=int(policy_matrix[(policy_matrix["policy"].astype(str).str.contains("ALL_BUY", na=False))]["target_filter_rows_in_compare"].sum()) if not policy_matrix.empty else 0
    rr1_extra=int(policy_matrix[(policy_matrix["policy"].astype(str).str.contains("RR1", na=False))]["extra_filter_rows"].sum()) if not policy_matrix.empty else 0
    direct_match=int(s.get("filter_level_both",0)); left=int(s.get("filter_level_left_only",0)); right=int(s.get("filter_level_right_only",0))
    decisions=pd.DataFrame([
        {"decision_id":"D001","question":"Did filter-specific replay improve to exact parity?","decision":"NO","reason":f"both={direct_match}; extra={left}; missing={right}"},
        {"decision_id":"D002","question":"Is ALL_BUY target policy represented in signal side?","decision":"NO" if all_buy_missing>0 else "YES","reason":f"ALL_BUY target/right-side rows={all_buy_missing}"},
        {"decision_id":"D003","question":"Is RR1 policy over-generated by filter replay?","decision":"YES" if rr1_extra>0 else "NO","reason":f"RR1 extra rows={rr1_extra}"},
        {"decision_id":"D004","question":"Is this enough to unblock CoreB live?","decision":"NO","reason":"policy mapping and full parity unresolved"},
    ])
    write_csv(out_dir/"08_25c11_result_decision_matrix.csv", decisions)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C12_COREB_POLICY_MAPPING_AUDIT_ONLY","allowed_now":True,"purpose":"Determine why ALL_BUY policy is missing and RR1 is over-generated"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"09_25c11_next_step_plan.csv", next_plan)
    unnecessary=["25C10 large signal samples unless debugging","25C10B and older reports","target ledger alone"]
    necessary=["01_25c11_GOLD_V2_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY_REPORT.md","02_25c11_coreb_filter_replay_result_review_summary.json","04_25c11_policy_signal_target_matrix.csv","05_25c11_filter_contract_match_rate_matrix.csv","06_25c11_top_overgenerated_contracts.csv","07_25c11_top_missing_contracts.csv","08_25c11_result_decision_matrix.csv","09_25c11_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c11_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"result_review_only":True,"condition_changed":False,"intersection_only":True,"full_coreb_parity":False,"filter_level_both":direct_match,"filter_level_left_only":left,"filter_level_right_only":right,"all_buy_missing_target_rows":all_buy_missing,"rr1_extra_filter_rows":rr1_extra,"policy_mapping_review_required":True,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C12_COREB_POLICY_MAPPING_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c11_coreb_filter_replay_result_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C11 CoreB filter replay result review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Finding","","25C11 reviews 25C10 mismatches by policy and filter contract. It does not change CoreB conditions.","","## Policy signal/target matrix","",md_table(policy_matrix),"","## Worst match-rate filter contracts","",md_table(pivot.sort_values(["match_rate","total_compare_rows"], ascending=[True,False]).head(30)),"","## Top over-generated contracts","",md_table(pivot[pivot["left_only"].gt(0)].sort_values("left_only", ascending=False).head(30)),"","## Top missing contracts","",md_table(pivot[pivot["right_only"].gt(0)].sort_values("right_only", ascending=False).head(30)),"","## Decisions","",md_table(decisions),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c11_GOLD_V2_COREB_FILTER_REPLAY_RESULT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"all_buy_missing_target_rows":all_buy_missing,"rr1_extra_filter_rows":rr1_extra,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
