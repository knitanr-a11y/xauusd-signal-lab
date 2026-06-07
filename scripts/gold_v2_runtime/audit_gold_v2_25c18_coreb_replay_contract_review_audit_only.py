#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C18_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY"
STATUS="COREB_REPLAY_CONTRACT_REVIEW_COMPLETED_AUDIT_ONLY_CONTRACT_REVISION_PLAN_REQUIRED"
STOP="25C18_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c18_coreb_replay_contract_review_audit_only"
IN17="gold_v2_25c17_coreb_selected_scope_mismatch_root_cause_audit_only"

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
    base=fx_outputs()/IN17
    req={
        "s17":base/"02_25c17_coreb_selected_scope_mismatch_root_cause_summary.json",
        "root_matrix":base/"04_25c17_selected_scope_filter_root_cause_matrix.csv",
        "over_profile":base/"05_25c17_overgeneration_threshold_profile.csv",
        "missing_profile":base/"06_25c17_missing_threshold_profile.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c18_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c18_coreb_replay_contract_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s17=read_json(req["s17"]); root=read_csv(req["root_matrix"]); over=read_csv(req["over_profile"]); miss=read_csv(req["missing_profile"])
    left=int(s17.get("selected_scope_left_only",0)); right=int(s17.get("selected_scope_right_only",0)); both=int(s17.get("selected_scope_both",0))
    low=int(s17.get("low_threshold_overgeneration_rows",0)); high=int(s17.get("high_threshold_missing_rows",0))
    issues=pd.DataFrame([
        {"issue_id":"I001","issue":"low threshold over-generation","observed_rows":low,"severity":"HIGH" if low>0 else "NONE","contract_implication":"current low-threshold filters are too broad for exact replay"},
        {"issue_id":"I002","issue":"high threshold target missing","observed_rows":high,"severity":"MEDIUM" if high>0 else "NONE","contract_implication":"some high-threshold target rows are not reproduced"},
        {"issue_id":"I003","issue":"overall selected-scope extra","observed_rows":left,"severity":"HIGH" if left>0 else "NONE","contract_implication":"current replay produces rows outside target"},
        {"issue_id":"I004","issue":"overall selected-scope missing","observed_rows":right,"severity":"HIGH" if right>0 else "NONE","contract_implication":"current replay misses target rows"},
        {"issue_id":"I005","issue":"exact parity status","observed_rows":both,"severity":"BLOCKED","contract_implication":"not enough to unblock CoreB"},
    ])
    write_csv(out/"04_25c18_contract_issue_matrix.csv", issues)
    accept_as_is = (left==0 and right==0)
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"accept current replay contract as exact","decision":"YES" if accept_as_is else "NO","reason":f"both={both}; extra={left}; missing={right}"},
        {"decision_id":"D002","question":"revise contract before another dry-run","decision":"YES" if not accept_as_is else "NO","reason":"low-threshold over-generation and high-threshold misses coexist"},
        {"decision_id":"D003","question":"allow source recovery","decision":"NO","reason":"audit-only; exact parity not proven"},
        {"decision_id":"D004","question":"allow live evaluator","decision":"NO","reason":"CoreB remains blocked"},
    ])
    write_csv(out/"05_25c18_replay_contract_review_decision_matrix.csv", dec)
    forbidden=pd.DataFrame([
        {"action":"source_recovery_execution","allowed":False},
        {"action":"source_mutation","allowed":False},
        {"action":"coreb_live_evaluator_unblock","allowed":False},
        {"action":"discord_send","allowed":False},
        {"action":"mt5_order","allowed":False},
        {"action":"ai_api","allowed":False},
        {"action":"final_signal","allowed":False},
    ])
    write_csv(out/"06_25c18_forbidden_actions.csv", forbidden)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C19_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"define revised comparison/replay contract without changing CoreB conditions"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"07_25c18_next_step_plan.csv", nxt)
    unnecessary=["25C17 large root matrix if summary sufficient","older reports","target ledger alone"]
    necessary=["01_25c18_GOLD_V2_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY_REPORT.md","02_25c18_coreb_replay_contract_review_summary.json","04_25c18_contract_issue_matrix.csv","05_25c18_replay_contract_review_decision_matrix.csv","06_25c18_forbidden_actions.csv","07_25c18_next_step_plan.csv"]
    write_csv(out/"00_不要_25c18_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"selected_scope_both":both,"selected_scope_left_only":left,"selected_scope_right_only":right,"low_threshold_overgeneration_rows":low,"high_threshold_missing_rows":high,"current_replay_contract_accepted_as_exact":accept_as_is,"contract_revision_plan_required":not accept_as_is,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C19_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c18_coreb_replay_contract_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C18 CoreB replay contract review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Contract issue matrix","",md_table(issues),"","## Decision matrix","",md_table(dec),"","## Forbidden actions","",md_table(forbidden),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c18_GOLD_V2_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"contract_revision_plan_required":not accept_as_is,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
