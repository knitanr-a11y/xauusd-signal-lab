#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C14_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY"
STATUS = "COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_COMPLETED_AUDIT_ONLY_SELECTED_RULE_POLICY_GAP_CONFIRMED"
STOP = "25C14_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c14_coreb_selected_policy_assignment_audit_only"
IN25C13 = "gold_v2_25c13_coreb_policy_source_linkage_audit_only"
COMBINED = "configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json"
SOURCE_UNIVERSE = "configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json"
BUY_CONF = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
SOURCE_COND = "configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json"

def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def lp(p: Path) -> Path:
    if os.name != "nt": return p
    s=str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def read_json(p: Path) -> Any: return json.loads(lp(p).read_text(encoding="utf-8-sig"))
def write_csv(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")
def write_json(p: Path, obj: dict) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    v=df.head(n); cols=list(v.columns)
    lines=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(lines)
def rows_from_section(data: Any, section: str) -> list[dict[str, Any]]:
    obj = data.get(section, []) if isinstance(data, dict) else []
    if not isinstance(obj, list): return []
    rows=[]
    for i,r in enumerate(obj):
        if isinstance(r, dict):
            rows.append({"section":section,"index":i,"policy":str(r.get("policy","")),"candidate_id":str(r.get("candidate_id", r.get("origin_id", ""))),"origin_id":str(r.get("origin_id","")),"rule_id":str(r.get("rule_id", r.get("id", "")))})
    return rows

def main(argv: Optional[Sequence[str]]=None) -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={"25c13_summary": fx_outputs()/IN25C13/"02_25c13_coreb_policy_source_linkage_summary.json", "combined": repo_root()/COMBINED, "source_universe": repo_root()/SOURCE_UNIVERSE, "buy_conf": repo_root()/BUY_CONF, "source_cond": repo_root()/SOURCE_COND}
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c14_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c14_coreb_selected_policy_assignment_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    combined=read_json(req["combined"]); source_univ=read_json(req["source_universe"]); buy=read_json(req["buy_conf"]); source_cond=read_json(req["source_cond"])
    rows=[]
    rows += rows_from_section(combined, "selected_rules")
    rows += rows_from_section(combined, "same_count_source_rules")
    rows += rows_from_section(source_univ, "source_universe_rules")
    rows += rows_from_section(buy, "selected_rules")
    rows += rows_from_section(buy, "buy_confluence_rules")
    rows += rows_from_section(source_cond, "source_rule_conditions")
    df=pd.DataFrame(rows)
    if df.empty: df=pd.DataFrame(columns=["section","index","policy","candidate_id","origin_id","rule_id"])
    section_counts=df.groupby(["section","policy"],dropna=False).size().reset_index(name="rule_rows") if not df.empty else pd.DataFrame(columns=["section","policy","rule_rows"])
    write_csv(out/"04_25c14_section_policy_count_matrix.csv", section_counts)
    selected=df[df["section"].isin(["selected_rules","buy_confluence_rules"])].copy()
    source=df[df["section"].isin(["same_count_source_rules","source_universe_rules","source_rule_conditions"])].copy()
    write_csv(out/"05_25c14_selected_rule_policy_matrix.csv", selected)
    write_csv(out/"06_25c14_source_rule_policy_matrix.csv", source)
    selected_all_buy=int((selected["policy"]=="RR125_from_ALL_BUY_rules").sum()) if not selected.empty else 0
    selected_rr1=int((selected["policy"]=="RR125_from_RR1_rules").sum()) if not selected.empty else 0
    source_all_buy=int((source["policy"]=="RR125_from_ALL_BUY_rules").sum()) if not source.empty else 0
    source_rr1=int((source["policy"]=="RR125_from_RR1_rules").sum()) if not source.empty else 0
    gap_confirmed = selected_all_buy == 0 and source_all_buy > 0 and selected_rr1 > 0
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"ALL_BUY exists in source-side rule sections","decision":"YES" if source_all_buy>0 else "NO","observed":source_all_buy},
        {"decision_id":"D002","question":"ALL_BUY exists in selected-side rule sections","decision":"YES" if selected_all_buy>0 else "NO","observed":selected_all_buy},
        {"decision_id":"D003","question":"RR1 exists in selected-side rule sections","decision":"YES" if selected_rr1>0 else "NO","observed":selected_rr1},
        {"decision_id":"D004","question":"selected policy gap confirmed","decision":"YES" if gap_confirmed else "NO","observed":gap_confirmed},
        {"decision_id":"D005","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c14_assignment_gap_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C15_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY","allowed_now":True,"purpose":"define replay contract that preserves selected policy role"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c14_next_step_plan.csv", nxt)
    unnecessary=["25C13 older reports", "large config samples", "target ledger alone"]
    necessary=["01_25c14_GOLD_V2_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY_REPORT.md","02_25c14_coreb_selected_policy_assignment_summary.json","04_25c14_section_policy_count_matrix.csv","05_25c14_selected_rule_policy_matrix.csv","06_25c14_source_rule_policy_matrix.csv","07_25c14_assignment_gap_decision_matrix.csv","08_25c14_next_step_plan.csv"]
    write_csv(out/"00_不要_25c14_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    status = STATUS if gap_confirmed else "COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_COMPLETED_AUDIT_ONLY_REVIEW_REQUIRED"
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"selected_all_buy_rule_rows":selected_all_buy,"selected_rr1_rule_rows":selected_rr1,"source_all_buy_rule_rows":source_all_buy,"source_rr1_rule_rows":source_rr1,"selected_policy_gap_confirmed":gap_confirmed,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C15_COREB_SELECTED_POLICY_REPLAY_CONTRACT_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c14_coreb_selected_policy_assignment_summary.json", summary)
    report="\n".join(["# GOLD V2 25C14 CoreB selected policy assignment audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## Section policy counts","",md_table(section_counts),"","## Assignment decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c14_GOLD_V2_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"selected_policy_gap_confirmed":gap_confirmed,"selected_all_buy_rule_rows":selected_all_buy,"selected_rr1_rule_rows":selected_rr1,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
