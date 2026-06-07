#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP = "25C15_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY"
STATUS = "COREB_SELECTED_POLICY_REPLAY_CONTRACT_DEFINED_AUDIT_ONLY_TARGET_SCOPE_REVIEW_REQUIRED"
STOP = "25C15_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only"
IN25C14 = "gold_v2_25c14_coreb_selected_policy_assignment_audit_only"

def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r=repo_root(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx_outputs() -> Path: return files_root()/"FX_OUTPUTS"
def lp(p: Path) -> Path:
    if os.name != "nt": return p
    s=str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def read_json(p: Path): return json.loads(lp(p).read_text(encoding="utf-8-sig"))
def read_csv(p: Path) -> pd.DataFrame:
    last=None
    for enc in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e: last=e
    raise RuntimeError(f"read failed: {p}: {last}")
def write_csv(p: Path, df: pd.DataFrame):
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")
def write_json(p: Path, obj: dict):
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def md_table(df: pd.DataFrame, n:int=80) -> str:
    if df.empty: return "_No rows._"
    v=df.head(n); cols=list(v.columns)
    out=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): out.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(out)

def main(argv: Optional[Sequence[str]]=None) -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    base=fx_outputs()/IN25C14
    req={"25c14_summary":base/"02_25c14_coreb_selected_policy_assignment_summary.json", "selected_matrix":base/"05_25c14_selected_rule_policy_matrix.csv", "source_matrix":base/"06_25c14_source_rule_policy_matrix.csv"}
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c15_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c15_coreb_selected_policy_replay_contract_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s14=read_json(req["25c14_summary"]); selected=read_csv(req["selected_matrix"]); source=read_csv(req["source_matrix"])
    selected_policies=sorted([p for p in selected.get("policy", pd.Series(dtype=str)).astype(str).unique().tolist() if p])
    source_policies=sorted([p for p in source.get("policy", pd.Series(dtype=str)).astype(str).unique().tolist() if p])
    sel_contract=pd.DataFrame([{"policy":p,"selected_output_scope":True,"reason":"present in selected-side rule matrix"} for p in selected_policies])
    src_contract=pd.DataFrame([{"policy":p,"source_universe_scope":True,"reason":"present in source-side rule matrix"} for p in source_policies])
    all_policies=sorted(set(selected_policies) | set(source_policies) | {"RR125_from_ALL_BUY_rules","RR125_from_RR1_rules"})
    target_rows=[]
    for p in all_policies:
        target_rows.append({
            "policy":p,
            "selected_output_scope":p in selected_policies,
            "source_universe_scope":p in source_policies,
            "direct_selected_output_target":p in selected_policies,
            "handling":"DIRECT_COMPARE" if p in selected_policies else "SOURCE_ONLY_NOT_DIRECT_SELECTED_TARGET",
        })
    target_contract=pd.DataFrame(target_rows)
    write_csv(out/"04_25c15_selected_policy_scope_contract.csv", sel_contract)
    write_csv(out/"05_25c15_source_universe_policy_scope_contract.csv", src_contract)
    write_csv(out/"06_25c15_target_policy_handling_contract.csv", target_contract)
    gap_confirmed=bool(s14.get("selected_policy_gap_confirmed", False))
    rr1_direct="RR125_from_RR1_rules" in selected_policies
    all_buy_direct="RR125_from_ALL_BUY_rules" in selected_policies
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"selected output scope is non-empty","decision":"YES" if len(selected_policies)>0 else "NO","observed":";".join(selected_policies)},
        {"decision_id":"D002","question":"RR1 is direct selected-output target","decision":"YES" if rr1_direct else "NO","observed":rr1_direct},
        {"decision_id":"D003","question":"ALL_BUY is direct selected-output target","decision":"YES" if all_buy_direct else "NO","observed":all_buy_direct},
        {"decision_id":"D004","question":"contract should preserve selected/source policy roles","decision":"YES","observed":gap_confirmed},
        {"decision_id":"D005","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c15_replay_contract_decision_matrix.csv", dec)
    next_plan=pd.DataFrame([
        {"rank":1,"next_step":"25C16_COREB_SELECTED_SCOPE_TARGET_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"compare target rows only inside selected output policy scope"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c15_next_step_plan.csv", next_plan)
    unnecessary=["25C14 older reports", "large config samples", "target ledger alone"]
    necessary=["01_25c15_GOLD_V2_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY_REPORT.md","02_25c15_coreb_selected_policy_replay_contract_summary.json","04_25c15_selected_policy_scope_contract.csv","05_25c15_source_universe_policy_scope_contract.csv","06_25c15_target_policy_handling_contract.csv","07_25c15_replay_contract_decision_matrix.csv","08_25c15_next_step_plan.csv"]
    write_csv(out/"00_不要_25c15_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"selected_output_policies":selected_policies,"source_universe_policies":source_policies,"all_buy_direct_selected_output_target":all_buy_direct,"rr1_direct_selected_output_target":rr1_direct,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C16_COREB_SELECTED_SCOPE_TARGET_REVIEW_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c15_coreb_selected_policy_replay_contract_summary.json", summary)
    report="\n".join(["# GOLD V2 25C15 CoreB selected policy replay contract audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Selected policy scope", "", md_table(sel_contract), "", "## Source universe policy scope", "", md_table(src_contract), "", "## Target policy handling", "", md_table(target_contract), "", "## Decisions", "", md_table(dec), "", "## File request list", "", "```text", "00_不要_貼らなくてOK", *[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)], "", "必要・貼ってほしい", *[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)], "```", "", "## Next step plan", "", md_table(next_plan), "", "## Safety", "", "CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c15_GOLD_V2_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"selected_output_policies":selected_policies,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
