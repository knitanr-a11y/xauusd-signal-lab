#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP = "25C12_COREB_POLICY_MAPPING_AUDIT_ONLY"
STATUS = "COREB_POLICY_MAPPING_AUDIT_COMPLETED_AUDIT_ONLY_SOURCE_POLICY_REVIEW_REQUIRED"
STOP = "25C12_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c12_coreb_policy_mapping_audit_only"
IN25C11 = "gold_v2_25c11_coreb_filter_replay_result_review_audit_only"
IN25C10 = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
IN25C7 = "gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
IN25C3 = "gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
RAW_LEDGER_NAME = "rr125_raw_signal_ledger.csv"
TARGET_LEDGER_NAME = "rr125_top_ledgers.csv"

def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def lp(p: Path) -> Path:
    if os.name != "nt": return p
    s = str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)
def read_csv(p: Path) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try: return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e: last = e
    raise RuntimeError(f"read failed: {p}: {last}")
def read_json(p: Path) -> dict: return json.loads(lp(p).read_text(encoding="utf-8-sig"))
def write_csv(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")
def write_json(p: Path, obj: dict) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    v = df.head(n); cols = list(v.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows(): out.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(out)
def path_from_audit(df: pd.DataFrame, name: str) -> Path:
    m = df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0]["absolute_path"])) if not m.empty else Path("")
def count_policy(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df.empty or "policy" not in df.columns: return pd.DataFrame(columns=["policy", col])
    return df.groupby("policy", dropna=False).size().reset_index(name=col)

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req = {
        "25c11_summary": fx_outputs()/IN25C11/"02_25c11_coreb_filter_replay_result_review_summary.json",
        "source_counts": fx_outputs()/IN25C3/"07_25c3_source_universe_hit_counts_by_entry.csv",
        "selected_hits": fx_outputs()/IN25C3/"08_25c3_selected_rule_hit_rows.csv",
        "replay_signals": fx_outputs()/IN25C10/"04_25c10_filter_replay_signal_rows.csv",
        "25c7_summary": fx_outputs()/IN25C7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "25b3_audit": fx_outputs()/IN25B3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia = pd.DataFrame([{"role": k, "path": str(v), "exists": lp(v).exists(), "status": "PASS" if lp(v).exists() else "STOP"} for k, v in req.items()])
    write_csv(out/"03_25c12_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c12_coreb_policy_mapping_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP, "total_stop_rows": int((ia["status"]=="STOP").sum())}); return 2
    s11 = read_json(req["25c11_summary"]); s7 = read_json(req["25c7_summary"]); audit = read_csv(req["25b3_audit"])
    raw_path = path_from_audit(audit, RAW_LEDGER_NAME); target_path = path_from_audit(audit, TARGET_LEDGER_NAME)
    raw = read_csv(raw_path); target = read_csv(target_path); source = read_csv(req["source_counts"]); selected = read_csv(req["selected_hits"]); replay = read_csv(req["replay_signals"])
    for df in (raw, target, source, selected, replay):
        for c in ("policy", "dataset", "entry_time"):
            if c in df.columns: df[c] = df[c].astype(str)
    fmin = pd.to_datetime(s7.get("feature_min_time"), errors="coerce"); fmax = pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    target["time_norm"] = pd.to_datetime(target["entry_time"], errors="coerce")
    target_scope = target[(target["time_norm"] >= fmin) & (target["time_norm"] <= fmax)].copy()
    cov = count_policy(raw, "raw_rows").merge(count_policy(source, "source_count_rows"), on="policy", how="outer").merge(count_policy(selected, "selected_hit_rows"), on="policy", how="outer").merge(count_policy(replay, "filter_replay_rows"), on="policy", how="outer").merge(count_policy(target_scope, "target_in_scope_rows"), on="policy", how="outer").fillna(0)
    for c in [x for x in cov.columns if x != "policy"]: cov[c] = cov[c].astype(int)
    cov["issue_class"] = cov.apply(lambda r: "target_present_signal_absent" if r["target_in_scope_rows"] > 0 and r["filter_replay_rows"] == 0 else ("signal_over_target" if r["target_in_scope_rows"] > 0 and r["filter_replay_rows"] > r["target_in_scope_rows"] * 2 else "review"), axis=1)
    write_csv(out/"04_25c12_policy_pipeline_coverage_matrix.csv", cov)
    all_buy = cov[cov["policy"].astype(str).str.contains("ALL_BUY", na=False)].copy(); rr1 = cov[cov["policy"].astype(str).str.contains("RR1", na=False)].copy()
    write_csv(out/"05_25c12_all_buy_gap_trace_matrix.csv", all_buy); write_csv(out/"06_25c12_rr1_overgeneration_trace_matrix.csv", rr1)
    pfilter = replay.groupby(["policy", "filter"], dropna=False).size().reset_index(name="replay_filter_rows") if "filter" in replay.columns else pd.DataFrame(columns=["policy","filter","replay_filter_rows"])
    tfilter = target_scope.groupby(["policy", "filter"], dropna=False).size().reset_index(name="target_filter_rows") if "filter" in target_scope.columns else pd.DataFrame(columns=["policy","filter","target_filter_rows"])
    pf = pfilter.merge(tfilter, on=["policy", "filter"], how="outer").fillna(0)
    for c in ("replay_filter_rows", "target_filter_rows"): pf[c] = pf[c].astype(int)
    pf["replay_minus_target"] = pf["replay_filter_rows"] - pf["target_filter_rows"]
    write_csv(out/"07_25c12_policy_filter_contract_matrix.csv", pf.sort_values("replay_minus_target", ascending=False))
    all_buy_gap = bool((all_buy["target_in_scope_rows"] > 0).any() and (all_buy["filter_replay_rows"] == 0).all()) if not all_buy.empty else False
    rr1_over = bool((rr1["filter_replay_rows"] > rr1["target_in_scope_rows"] * 2).any()) if not rr1.empty else False
    dec = pd.DataFrame([
        {"decision_id":"D001", "question":"ALL_BUY target exists but replay signal absent", "decision":"YES" if all_buy_gap else "NO"},
        {"decision_id":"D002", "question":"RR1 replay exceeds target by large margin", "decision":"YES" if rr1_over else "NO"},
        {"decision_id":"D003", "question":"policy linkage review required", "decision":"YES"},
        {"decision_id":"D004", "question":"CoreB unblock allowed", "decision":"NO"},
    ])
    write_csv(out/"08_25c12_policy_mapping_decision_matrix.csv", dec)
    nxt = pd.DataFrame([
        {"rank":1,"next_step":"25C13_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY","allowed_now":True,"purpose":"review policy linkage in audited configs"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"09_25c12_next_step_plan.csv", nxt)
    unnecessary = ["25C11 older report", "large samples unless debugging", "target ledger alone"]
    necessary = ["01_25c12_GOLD_V2_COREB_POLICY_MAPPING_AUDIT_ONLY_REPORT.md", "02_25c12_coreb_policy_mapping_summary.json", "04_25c12_policy_pipeline_coverage_matrix.csv", "05_25c12_all_buy_gap_trace_matrix.csv", "06_25c12_rr1_overgeneration_trace_matrix.csv", "07_25c12_policy_filter_contract_matrix.csv", "08_25c12_policy_mapping_decision_matrix.csv", "09_25c12_next_step_plan.csv"]
    write_csv(out/"00_不要_25c12_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STATUS, "audit_only": True, "condition_changed": False, "intersection_only": True, "full_coreb_parity": False, "all_buy_policy_missing_in_replay": all_buy_gap, "rr1_policy_overexpanded_in_replay": rr1_over, "filter_level_both": int(s11.get("filter_level_both",0)), "filter_level_left_only": int(s11.get("filter_level_left_only",0)), "filter_level_right_only": int(s11.get("filter_level_right_only",0)), "coreb_live_evaluator_unblocked": False, "target_key_parity_proven": False, "next_recommended_step": "25C13_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY", "total_stop_rows": 0}
    write_json(out/"02_25c12_coreb_policy_mapping_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C12 CoreB policy mapping audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "", "## Policy pipeline coverage matrix", "", md_table(cov), "", "## ALL_BUY gap trace", "", md_table(all_buy), "", "## RR1 over-generation trace", "", md_table(rr1), "", "## Decisions", "", md_table(dec), "", "## File request list", "", "```text", "00_不要_貼らなくてOK", *[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)], "", "必要・貼ってほしい", *[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)], "```", "", "## Next step plan", "", md_table(nxt), "", "## Safety", "", "CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c12_GOLD_V2_COREB_POLICY_MAPPING_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "all_buy_policy_missing_in_replay": all_buy_gap, "rr1_policy_overexpanded_in_replay": rr1_over, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
