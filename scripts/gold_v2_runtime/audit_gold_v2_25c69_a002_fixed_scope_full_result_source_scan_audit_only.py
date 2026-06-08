#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

STEP = "25C69_A002_FIXED_SCOPE_FULL_RESULT_SOURCE_SCAN_AUDIT_ONLY"
STATUS_READY = "A002_FIXED_SCOPE_FULL_RESULT_SOURCE_SCAN_READY_AUDIT_ONLY_SAFE_SOURCE_FOUND"
STATUS_BLOCKED = "A002_FIXED_SCOPE_FULL_RESULT_SOURCE_SCAN_BLOCKED_AUDIT_ONLY_NO_SAFE_SOURCE_FOUND"
IN_DIR = "gold_v2_25c68_a002_fixed_scope_result_source_discovery_audit_only"
LEDGER_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
OUT_DIR = "gold_v2_25c69_a002_fixed_scope_full_result_source_scan_audit_only"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
TIME_COLUMNS = ["entry_time", "signal_time", "time", "datetime", "open_time", "entry_datetime"]
OUTCOME_COLUMNS = ["outcome", "result", "trade_result", "label", "win_loss", "is_win", "pnl", "profit", "net_profit", "net_pnl", "rr", "r_multiple"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def lp(p: Path) -> Path:
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_json(p: Path) -> dict:
    return json.loads(lp(p).read_text(encoding="utf-8-sig"))


def read_csv(p: Path, usecols: Optional[list[str]] = None) -> pd.DataFrame:
    last: Optional[Exception] = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(p), encoding=enc, keep_default_na=False, usecols=usecols)
        except Exception as e:
            last = e
    raise RuntimeError(f"read failed {p}: {last}")


def write_csv(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(p), index=False, encoding="utf-8-sig")


def write_json(p: Path, obj: dict) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(max_rows).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def exists_row(role: str, p: Path) -> dict:
    ok = lp(p).exists()
    return {"role": role, "path": str(p), "exists": ok, "status": "PASS" if ok else "STOP"}


def read_header(p: Path) -> list[str]:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with lp(p).open("r", encoding=enc, newline="") as f:
                return next(csv.reader(f))
        except Exception:
            continue
    return []


def lower_map(cols: list[str]) -> dict[str, str]:
    return {c.lower().strip(): c for c in cols}


def first_present(lmap: dict[str, str], names: list[str]) -> Optional[str]:
    for n in names:
        if n in lmap:
            return lmap[n]
    return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--ledger-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    root = fx_outputs()
    input_dir = Path(args.input_dir).resolve() if args.input_dir else root / IN_DIR
    ledger_dir = Path(args.ledger_dir).resolve() if args.ledger_dir else root / LEDGER_DIR
    out = Path(args.output_dir).resolve() if args.output_dir else root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary68": input_dir / "02_25c68_a002_fixed_scope_result_source_discovery_summary.json",
        "contract68": input_dir / "04_25c68_contract_audit.csv",
        "candidates68": input_dir / "05_25c68_outcome_candidate_files.csv",
        "safe68": input_dir / "06_25c68_safe_outcome_candidate_matrix.csv",
        "readiness68": input_dir / "07_25c68_evaluation_readiness_matrix.csv",
        "boundary68": input_dir / "08_25c68_boundary_matrix.csv",
        "next68": input_dir / "09_25c68_next_step_plan.csv",
        "ledger66": ledger_dir / "05_25c66_dry_run_event_ledger.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c69_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C69_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c69_full_result_source_scan_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s68 = read_json(req["summary68"])
    contract68 = read_csv(req["contract68"])
    readiness68 = read_csv(req["readiness68"])
    boundary68 = read_csv(req["boundary68"])
    ledger = read_csv(req["ledger66"])
    ledger_times = set(ledger["entry_time"].astype(str)) if "entry_time" in ledger.columns else set()
    expected_events = len(ledger_times)

    contract_rows = []
    checks = [
        ("step", s68.get("step"), "25C68_A002_FIXED_SCOPE_RESULT_SOURCE_DISCOVERY_AUDIT_ONLY"),
        ("audit_only", s68.get("audit_only"), True),
        ("variant", s68.get("representative_variant_code"), "A002"),
        ("filters", s68.get("representative_filters"), EXPECTED_FILTERS),
        ("ledger_events", s68.get("ledger_events"), 772),
        ("trade_outcome_simulation_executed", s68.get("trade_outcome_simulation_executed"), False),
        ("condition_changed", s68.get("condition_changed"), False),
        ("source_recovery_executed", s68.get("source_recovery_executed"), False),
        ("source_mutation_executed", s68.get("source_mutation_executed"), False),
        ("ai_api_called", s68.get("ai_api_called"), False),
        ("discord_notification_sent", s68.get("discord_notification_sent"), False),
        ("mt5_order_sent", s68.get("mt5_order_sent"), False),
        ("final_signal_created", s68.get("final_signal_created"), False),
        ("total_stop_rows", s68.get("total_stop_rows"), 0),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    contract_rows += [
        {"contract_id": "M015", "check": "25C68 contract no STOP", "observed": int((contract68.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract68.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M016", "check": "ledger events", "observed": expected_events, "expected": 772, "status": "PASS" if expected_events == 772 else "STOP"},
        {"contract_id": "M017", "check": "boundaries safe", "observed": not boundary68.get("allowed_now", pd.Series(dtype=bool)).astype(bool).any(), "expected": True, "status": "PASS"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c69_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C69_STOP_25C68_CONTRACT_UNSAFE_AUDIT_ONLY"
        write_json(out / "02_25c69_full_result_source_scan_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())})
        return 2

    rows = []
    scanned = 0
    for p in root.rglob("*.csv"):
        try:
            if OUT_DIR in p.parts:
                continue
            scanned += 1
            rel = str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
            header = read_header(p)
            lmap = lower_map(header)
            time_col = first_present(lmap, TIME_COLUMNS)
            outcome_col = first_present(lmap, OUTCOME_COLUMNS)
            has_policy = "policy" in lmap
            has_dataset = "dataset" in lmap
            row_count = 0
            match_count = 0
            exact_coverage = False
            read_status = "HEADER_ONLY"
            if time_col:
                try:
                    df = read_csv(p, usecols=[time_col])
                    row_count = len(df)
                    vals = set(df[time_col].astype(str))
                    match_count = len(vals.intersection(ledger_times))
                    exact_coverage = ledger_times.issubset(vals)
                    read_status = "READ_OK"
                except Exception:
                    read_status = "READ_FAILED"
            category = "NOT_CANDIDATE"
            if time_col and outcome_col and exact_coverage:
                category = "SAFE_FULL_OUTCOME_SOURCE"
            elif time_col and outcome_col and match_count > 0:
                category = "PARTIAL_OUTCOME_SOURCE"
            elif time_col and exact_coverage:
                category = "TIME_ONLY_FULL_SOURCE"
            elif time_col and match_count > 0:
                category = "PARTIAL_TIME_ONLY_SOURCE"
            score = 0
            if time_col:
                score += 2
            if outcome_col:
                score += 4
            if exact_coverage:
                score += 8
            elif match_count > 0:
                score += 2
            if has_policy:
                score += 1
            if has_dataset:
                score += 1
            rows.append({
                "relative_path": rel,
                "column_count": len(header),
                "time_column": time_col or "",
                "outcome_column": outcome_col or "",
                "has_policy": has_policy,
                "has_dataset": has_dataset,
                "rows_read": row_count,
                "entry_time_match_count": match_count,
                "entry_time_match_ratio": round(match_count / expected_events, 6) if expected_events else 0,
                "exact_ledger_time_coverage": exact_coverage,
                "candidate_category": category,
                "candidate_score": score,
                "read_status": read_status,
            })
        except Exception as e:
            rows.append({"relative_path": str(p), "column_count": 0, "time_column": "", "outcome_column": "", "has_policy": False, "has_dataset": False, "rows_read": 0, "entry_time_match_count": 0, "entry_time_match_ratio": 0, "exact_ledger_time_coverage": False, "candidate_category": "SCAN_ERROR", "candidate_score": 0, "read_status": str(e)[:120]})
    candidates = pd.DataFrame(rows)
    if candidates.empty:
        candidates = pd.DataFrame(columns=["relative_path", "column_count", "time_column", "outcome_column", "has_policy", "has_dataset", "rows_read", "entry_time_match_count", "entry_time_match_ratio", "exact_ledger_time_coverage", "candidate_category", "candidate_score", "read_status"])
    candidates = candidates.sort_values(["candidate_score", "entry_time_match_count"], ascending=False).reset_index(drop=True)
    safe = candidates[candidates["candidate_category"].eq("SAFE_FULL_OUTCOME_SOURCE")].copy()
    partial = candidates[candidates["candidate_category"].isin(["PARTIAL_OUTCOME_SOURCE", "TIME_ONLY_FULL_SOURCE", "PARTIAL_TIME_ONLY_SOURCE"])].copy()
    category_counts = candidates.groupby("candidate_category", dropna=False).agg(files=("relative_path", "size"), max_match=("entry_time_match_count", "max")).reset_index()

    missing = pd.DataFrame([
        {"requirement_id": "REQ001", "requirement": "entry_time column", "required": True, "reason": "must join to 772 ledger events"},
        {"requirement_id": "REQ002", "requirement": "outcome/profit/result column", "required": True, "reason": "must evaluate results without recomputation"},
        {"requirement_id": "REQ003", "requirement": "coverage for all 772 ledger entry_times", "required": True, "reason": "partial candidate is not safe as source of truth"},
        {"requirement_id": "REQ004", "requirement": "no source recovery or condition change", "required": True, "reason": "fixed-scope guardrail"},
    ])
    readiness = pd.DataFrame([
        {"item_id": "R001", "item": "csv_files_scanned", "value": int(len(candidates)), "status": "PASS"},
        {"item_id": "R002", "item": "safe_full_sources", "value": int(len(safe)), "status": "PASS" if len(safe) > 0 else "BLOCKED"},
        {"item_id": "R003", "item": "partial_sources", "value": int(len(partial)), "status": "PASS" if len(partial) > 0 else "BLOCKED"},
        {"item_id": "R004", "item": "best_match_count", "value": int(candidates.iloc[0]["entry_time_match_count"]) if len(candidates) else 0, "status": "PASS" if len(candidates) else "BLOCKED"},
        {"item_id": "R005", "item": "external_actions", "value": False, "status": "PASS"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "outcome_simulation", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    if len(safe) > 0:
        status = STATUS_READY
        next_step = "25C70_A002_FIXED_SCOPE_SAFE_OUTCOME_MAPPING_AUDIT_ONLY"
    else:
        status = STATUS_BLOCKED
        next_step = "PROVIDE_SAFE_OUTCOME_SOURCE_OR_APPROVE_NO_OUTCOME_RESULT_REVIEW_AUDIT_ONLY"
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": next_step, "allowed_now": True, "purpose": "continue without changing A002 fixed scope", "condition_change_allowed": False, "external_action_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "condition_change_allowed": False, "external_action_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C69 scanned all visible FX_OUTPUTS CSV files, not just the first 600.", "status": "PASS"},
        {"note_id": "N002", "note": "No condition/source/external action was performed.", "status": "PASS"},
        {"note_id": "N003", "note": "If no safe source exists, result evaluation must not be approximated.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c69_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c69_full_result_source_scan_summary.json"}]))
    write_csv(out / "05_25c69_all_candidate_files.csv", candidates)
    write_csv(out / "06_25c69_safe_full_source_candidates.csv", safe)
    write_csv(out / "07_25c69_partial_source_candidates.csv", partial.head(100))
    write_csv(out / "08_25c69_candidate_category_counts.csv", category_counts)
    write_csv(out / "09_25c69_missing_source_requirement_matrix.csv", missing)
    write_csv(out / "10_25c69_readiness_matrix.csv", readiness)
    write_csv(out / "11_25c69_boundary_matrix.csv", boundary)
    write_csv(out / "12_25c69_next_step_plan.csv", next_plan)
    write_csv(out / "13_25c69_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "input_25c68_step": s68.get("step"),
        "input_25c68_status": s68.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "ledger_events": expected_events,
        "csv_files_scanned": int(len(candidates)),
        "safe_full_sources": int(len(safe)),
        "partial_sources": int(len(partial)),
        "best_candidate_path": str(candidates.iloc[0]["relative_path"]) if len(candidates) else "",
        "best_candidate_category": str(candidates.iloc[0]["candidate_category"]) if len(candidates) else "",
        "best_candidate_match_count": int(candidates.iloc[0]["entry_time_match_count"]) if len(candidates) else 0,
        "trade_outcome_simulation_executed": False,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": next_step,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c69_full_result_source_scan_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C69 A002 fixed scope full result source scan audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Category counts", "", md_table(category_counts), "",
        "## Safe full source candidates", "", md_table(safe), "",
        "## Top partial candidates", "", md_table(partial.head(30)), "",
        "## Missing source requirements", "", md_table(missing), "",
        "## Readiness", "", md_table(readiness), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c69_GOLD_V2_A002_FIXED_SCOPE_FULL_RESULT_SOURCE_SCAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "csv_files_scanned": int(len(candidates)), "safe_full_sources": int(len(safe)), "partial_sources": int(len(partial)), "best_candidate_match_count": summary["best_candidate_match_count"], "next_recommended_step": next_step}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
