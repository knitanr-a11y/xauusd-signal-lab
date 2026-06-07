#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C9_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY"
PASS_STATUS = "COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED"
STOP_STATUS = "25C9_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C8 = "gold_v2_25c8_coreb_mismatch_root_cause_audit_only"
OUT_DIR = "gold_v2_25c9_coreb_target_filter_contract_replay_plan_audit_only"
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

def parse_filter_contract(filter_text: str) -> dict[str, Any]:
    s=str(filter_text)
    sm=re.search(r"same_count>=(\d+)", s)
    um=re.search(r"unique_origins>=(\d+)", s)
    return {"same_count_threshold": int(sm.group(1)) if sm else None, "unique_origins_threshold": int(um.group(1)) if um else None}

def safety_problems(s:dict[str,Any])->list[str]:
    p=[]
    if s.get("status")!="COREB_MISMATCH_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_FILTER_CONTRACT_REVIEW_REQUIRED": p.append("25C8 status mismatch")
    if bool(s.get("condition_changed")): p.append("condition_changed unexpectedly true")
    if bool(s.get("full_coreb_parity")): p.append("full_coreb_parity unexpectedly true")
    for k,e in SAFETY_FLAGS.items():
        if s.get(k)!=e: p.append(f"safety flag mismatch: {k}")
    return p

def main(argv:Optional[Sequence[str]]=None)->int:
    args=parse_args(argv); out_dir=Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in8=fx_outputs()/IN25C8
    req={"25c8_summary":in8/"02_25c8_coreb_mismatch_root_cause_summary.json","target_filter_inventory":in8/"04_25c8_target_filter_inventory.csv","threshold_alignment":in8/"07_25c8_threshold_filter_alignment_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c9_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c9_coreb_target_filter_contract_replay_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s=read_json(req["25c8_summary"]); problems=safety_problems(s)
    if problems:
        write_json(out_dir/"02_25c9_coreb_target_filter_contract_replay_plan_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2
    inv=read_csv(req["target_filter_inventory"]); align=read_csv(req["threshold_alignment"])
    plan_rows=[]
    for _,r in inv.iterrows():
        pc=parse_filter_contract(str(r.get("filter","")))
        plan_rows.append({
            "policy":r.get("policy",""),"filter":r.get("filter",""),"filter_class":r.get("filter_class",""),"target_rows":int(r.get("target_rows",0)),
            "same_count_threshold": "" if pc["same_count_threshold"] is None else pc["same_count_threshold"],
            "unique_origins_threshold": "" if pc["unique_origins_threshold"] is None else pc["unique_origins_threshold"],
            "required_same_count_metric":"source_count_by_entry_time" if pc["same_count_threshold"] is not None else "NOT_REQUIRED",
            "required_unique_origin_metric":"unique_origin_count_by_entry_time" if pc["unique_origins_threshold"] is not None else "NOT_REQUIRED",
            "can_replay_with_25c5_outputs_only": bool(pc["same_count_threshold"] is not None and pc["unique_origins_threshold"] is None),
            "requires_additional_unique_origin_derivation": bool(pc["unique_origins_threshold"] is not None),
            "execution_now": False,
        })
    plan=pd.DataFrame(plan_rows).sort_values("target_rows", ascending=False)
    write_csv(out_dir/"04_25c9_filter_contract_plan.csv", plan)
    variant=pd.DataFrame([
        {"variant_id":"V001","variant":"same_count_only_filters","scope":"filters with same_count>=N and no unique_origins threshold","replay_metric":"source_count_by_entry_time","execution_now":False},
        {"variant_id":"V002","variant":"unique_origins_only_filters","scope":"filters with unique_origins>=M and no same_count threshold","replay_metric":"unique_origin_count_by_entry_time","execution_now":False},
        {"variant_id":"V003","variant":"same_count_and_unique_origins_filters","scope":"filters with both same_count>=N and unique_origins>=M","replay_metric":"source_count_by_entry_time AND unique_origin_count_by_entry_time","execution_now":False},
    ])
    write_csv(out_dir/"05_25c9_replay_variant_matrix.csv", variant)
    required=pd.DataFrame([
        {"metric":"source_count_by_entry_time","available_from":"25C5/25C4 aggregated source counts","available_now":True,"required_for":"same_count filters"},
        {"metric":"unique_origin_count_by_entry_time","available_from":"raw source-universe hit rows grouped by origin_id after condition eval","available_now":False,"required_for":"unique_origins filters"},
        {"metric":"filter_specific_target_rows","available_from":"rr125_top_ledgers filter column","available_now":True,"required_for":"filter-level comparison"},
    ])
    write_csv(out_dir/"06_25c9_required_metric_matrix.csv", required)
    can_same_count_only=int(plan[plan["can_replay_with_25c5_outputs_only"].astype(bool)]["target_rows"].sum()) if not plan.empty else 0
    needs_unique=int(plan[plan["requires_additional_unique_origin_derivation"].astype(bool)]["target_rows"].sum()) if not plan.empty else 0
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C8 status clean","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"same_count-only filters can be planned","observed":can_same_count_only>0,"required":True,"status":"PASS" if can_same_count_only>0 else "BLOCKED"},
        {"gate_id":"G003","gate":"unique_origins metric available now","observed":False,"required":True,"status":"BLOCKED_UNTIL_DERIVED" if needs_unique>0 else "PASS_NOT_REQUIRED"},
        {"gate_id":"G004","gate":"execution allowed now","observed":False,"required":False,"status":"BLOCKED_PLAN_ONLY"},
        {"gate_id":"G005","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out_dir/"07_25c9_acceptance_gate_matrix.csv", gates)
    forbidden=pd.DataFrame([
        {"method":"compare_one_contract_to_all_filters","forbidden":True,"reason":"25C8 found 14 filter classes"},
        {"method":"ignore_unique_origins_filters","forbidden":True,"reason":"target contains unique_origins dimensions"},
        {"method":"change_coreb_conditions_to_match_target","forbidden":True,"reason":"CoreB conditions must not change"},
        {"method":"source_recovery_execution","forbidden":True,"reason":"not approved"},
        {"method":"live_or_final_signal","forbidden":True,"reason":"CoreB blocked"},
    ])
    write_csv(out_dir/"08_25c9_forbidden_methods.csv", forbidden)
    next_step="25C10_COREB_TARGET_FILTER_CONTRACT_REPLAY_DRY_RUN_AUDIT_ONLY"
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":next_step,"allowed_now":False,"purpose":"Execute filter-specific diagnostic only after accepting 25C9 plan"},
        {"rank":2,"next_step":"25C10A_UNIQUE_ORIGIN_METRIC_DERIVATION_AUDIT_ONLY","allowed_now":True if needs_unique>0 else False,"purpose":"Derive unique_origin_count_by_entry_time if unique_origins filters are to be compared"},
        {"rank":3,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Still blocked"},
        {"rank":4,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"09_25c9_next_step_plan.csv", next_plan)
    unnecessary=["25C8 older summaries already processed","25C5 large signal rows unless debugging","target top ledger alone"]
    necessary=["01_25c9_GOLD_V2_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY_REPORT.md","02_25c9_coreb_target_filter_contract_replay_plan_summary.json","04_25c9_filter_contract_plan.csv","05_25c9_replay_variant_matrix.csv","06_25c9_required_metric_matrix.csv","07_25c9_acceptance_gate_matrix.csv","08_25c9_forbidden_methods.csv","09_25c9_next_step_plan.csv"]
    write_csv(out_dir/"00_不要_25c9_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"plan_only":True,"filter_contract_rows":int(len(plan)),"same_count_only_target_rows_plannable_now":can_same_count_only,"unique_origin_target_rows_need_derivation":needs_unique,"condition_changed":False,"intersection_only":True,"full_coreb_parity":False,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"HUMAN_DECISION_ACCEPT_25C9_FILTER_CONTRACT_PLAN_BEFORE_25C10","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c9_coreb_target_filter_contract_replay_plan_summary.json", summary)
    report="\n".join(["# GOLD V2 25C9 CoreB target filter contract replay plan audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Finding","","25C9 converts target filter inventory into filter-specific replay contracts. It does not execute replay.","","## Filter contract plan","",md_table(plan),"","## Replay variant matrix","",md_table(variant),"","## Required metric matrix","",md_table(required),"","## Acceptance gates","",md_table(gates),"","## Forbidden methods","",md_table(forbidden),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c9_GOLD_V2_COREB_TARGET_FILTER_CONTRACT_REPLAY_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"same_count_only_target_rows_plannable_now":can_same_count_only,"unique_origin_target_rows_need_derivation":needs_unique,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
