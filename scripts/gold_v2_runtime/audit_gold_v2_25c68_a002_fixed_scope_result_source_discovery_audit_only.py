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

STEP = "25C68_A002_FIXED_SCOPE_RESULT_SOURCE_DISCOVERY_AUDIT_ONLY"
STATUS_READY = "A002_FIXED_SCOPE_RESULT_SOURCE_DISCOVERY_READY_AUDIT_ONLY_CANDIDATES_REVIEWED"
STATUS_BLOCKED = "A002_FIXED_SCOPE_RESULT_SOURCE_DISCOVERY_BLOCKED_AUDIT_ONLY_NO_SAFE_OUTCOME_SOURCE"
IN_DIR = "gold_v2_25c67_a002_fixed_scope_dry_run_result_review_audit_only"
LEDGER_DIR = "gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only"
OUT_DIR = "gold_v2_25c68_a002_fixed_scope_result_source_discovery_audit_only"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
TIME_COLUMNS = ["entry_time", "signal_time", "time", "datetime", "open_time", "entry_datetime"]
OUTCOME_COLUMNS = ["outcome", "result", "trade_result", "label", "win_loss", "is_win", "pnl", "profit", "net_profit", "net_pnl", "rr", "r_multiple"]
EXCLUDE_DIR_PARTS = {OUT_DIR}


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
    ap.add_argument("--scan-limit", type=int, default=600)
    args = ap.parse_args(argv)

    root = fx_outputs()
    input_dir = Path(args.input_dir).resolve() if args.input_dir else root / IN_DIR
    ledger_dir = Path(args.ledger_dir).resolve() if args.ledger_dir else root / LEDGER_DIR
    out = Path(args.output_dir).resolve() if args.output_dir else root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary67": input_dir / "02_25c67_a002_fixed_scope_result_review_summary.json",
        "contract67": input_dir / "04_25c67_contract_audit.csv",
        "contradiction67": input_dir / "06_25c67_contradiction_review_matrix.csv",
        "event_summary67": input_dir / "07_25c67_event_summary.csv",
        "boundary67": input_dir / "10_25c67_boundary_matrix.csv",
        "next67": input_dir / "11_25c67_next_step_plan.csv",
        "ledger66": ledger_dir / "05_25c66_dry_run_event_ledger.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c68_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        status = "25C68_STOP_MISSING_INPUT_AUDIT_ONLY"
        write_json(out / "02_25c68_a002_fixed_scope_result_source_discovery_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum())})
        return 2

    s67 = read_json(req["summary67"])
    contract67 = read_csv(req["contract67"])
    contradiction67 = read_csv(req["contradiction67"])
    event_summary67 = read_csv(req["event_summary67"])
    boundary67 = read_csv(req["boundary67"])
    next67 = read_csv(req["next67"])
    ledger = read_csv(req["ledger66"])
    ledger_times = set(ledger["entry_time"].astype(str)) if "entry_time" in ledger.columns else set()

    contract_rows = []
    checks = [
        ("step", s67.get("step"), "25C67_A002_FIXED_SCOPE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY"),
        ("status", s67.get("status"), "A002_FIXED_SCOPE_DRY_RUN_RESULT_REVIEW_READY_AUDIT_ONLY_NO_CONTRADICTION_FOUND"),
        ("audit_only", s67.get("audit_only"), True),
        ("variant", s67.get("representative_variant_code"), "A002"),
        ("filters", s67.get("representative_filters"), EXPECTED_FILTERS),
        ("events", s67.get("audit_only_dry_run_events"), 772),
        ("contradiction_found", s67.get("contradiction_found"), False),
        ("trade_outcome_simulation_executed", s67.get("trade_outcome_simulation_executed"), False),
        ("live_execution_executed", s67.get("live_execution_executed"), False),
        ("external_action_executed", s67.get("external_action_executed"), False),
        ("condition_changed", s67.get("condition_changed"), False),
        ("source_recovery_executed", s67.get("source_recovery_executed"), False),
        ("source_mutation_executed", s67.get("source_mutation_executed"), False),
        ("ai_api_called", s67.get("ai_api_called"), False),
        ("discord_notification_sent", s67.get("discord_notification_sent"), False),
        ("mt5_order_sent", s67.get("mt5_order_sent"), False),
        ("final_signal_created", s67.get("final_signal_created"), False),
        ("total_stop_rows", s67.get("total_stop_rows"), 0),
    ]
    for i, (name, obs, exp) in enumerate(checks, 1):
        contract_rows.append({"contract_id": f"C{i:03d}", "check": name, "observed": obs, "expected": exp, "status": "PASS" if obs == exp else "STOP"})
    contract_rows += [
        {"contract_id": "M019", "check": "25C67 contract no STOP", "observed": int((contract67.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contract67.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M020", "check": "25C67 contradiction no STOP", "observed": int((contradiction67.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()), "expected": 0, "status": "PASS" if not (contradiction67.get("status", pd.Series(dtype=str)).astype(str) == "STOP").any() else "STOP"},
        {"contract_id": "M021", "check": "ledger rows", "observed": int(len(ledger)), "expected": 772, "status": "PASS" if len(ledger) == 772 else "STOP"},
        {"contract_id": "M022", "check": "ledger entry_time count", "observed": int(len(ledger_times)), "expected": 772, "status": "PASS" if len(ledger_times) == 772 else "STOP"},
    ]
    contract = pd.DataFrame(contract_rows)
    write_csv(out / "04_25c68_contract_audit.csv", contract)
    if contract["status"].eq("STOP").any():
        status = "25C68_STOP_25C67_CONTRACT_UNSAFE_AUDIT_ONLY"
        write_json(out / "02_25c68_a002_fixed_scope_result_source_discovery_summary.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "total_stop_rows": int((contract["status"] == "STOP").sum())})
        return 2

    rows = []
    csv_paths = []
    for p in root.rglob("*.csv"):
        if any(part in EXCLUDE_DIR_PARTS for part in p.parts):
            continue
        csv_paths.append(p)
        if len(csv_paths) >= args.scan_limit:
            break

    for p in csv_paths:
        rel = str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
        header = read_header(p)
        lmap = lower_map(header)
        time_col = first_present(lmap, TIME_COLUMNS)
        outcome_col = first_present(lmap, OUTCOME_COLUMNS)
        has_policy = "policy" in lmap
        has_dataset = "dataset" in lmap
        has_result_signal = outcome_col is not None
        match_count = 0
        sample_rows = 0
        read_status = "HEADER_ONLY"
        if time_col:
            try:
                df = read_csv(p, usecols=[time_col])
                sample_rows = len(df)
                match_count = int(df[time_col].astype(str).isin(ledger_times).sum())
                read_status = "READ_OK"
            except Exception:
                read_status = "READ_FAILED"
        score = 0
        if time_col:
            score += 2
        if outcome_col:
            score += 4
        if match_count >= 700:
            score += 5
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
            "rows_read": sample_rows,
            "entry_time_match_count": match_count,
            "entry_time_match_ratio": round(match_count / 772, 6) if ledger_times else 0,
            "candidate_score": score,
            "read_status": read_status,
        })
    candidates = pd.DataFrame(rows)
    if candidates.empty:
        candidates = pd.DataFrame(columns=["relative_path", "column_count", "time_column", "outcome_column", "has_policy", "has_dataset", "rows_read", "entry_time_match_count", "entry_time_match_ratio", "candidate_score", "read_status"])
    candidates = candidates.sort_values(["candidate_score", "entry_time_match_count"], ascending=False).reset_index(drop=True)

    safe_candidates = candidates[(candidates["outcome_column"].astype(str) != "") & (candidates["entry_time_match_count"].astype(int) >= 700)].copy()
    readiness = pd.DataFrame([
        {"item_id": "R001", "item": "ledger_ready", "value": len(ledger) == 772, "status": "PASS" if len(ledger) == 772 else "STOP"},
        {"item_id": "R002", "item": "candidate_files_scanned", "value": int(len(candidates)), "status": "PASS"},
        {"item_id": "R003", "item": "safe_outcome_candidates", "value": int(len(safe_candidates)), "status": "PASS" if len(safe_candidates) > 0 else "BLOCKED"},
        {"item_id": "R004", "item": "condition_change", "value": False, "status": "PASS"},
        {"item_id": "R005", "item": "source_recovery", "value": False, "status": "PASS"},
        {"item_id": "R006", "item": "external_actions", "value": False, "status": "PASS"},
    ])
    boundary = pd.DataFrame([
        {"boundary_id": "B001", "boundary": "condition_change", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B002", "boundary": "source_recovery", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B003", "boundary": "outcome_simulation", "allowed_now": False, "observed": False, "status": "PASS"},
        {"boundary_id": "B004", "boundary": "live_external_ai_discord_mt5_final", "allowed_now": False, "observed": False, "status": "PASS"},
    ])
    if len(safe_candidates) > 0:
        next_step = "25C69_A002_FIXED_SCOPE_OUTCOME_MAPPING_AUDIT_ONLY"
        allowed = True
        status = STATUS_READY
    else:
        next_step = "WAIT_FOR_SAFE_OUTCOME_SOURCE_ARTIFACT_AUDIT_ONLY"
        allowed = True
        status = STATUS_BLOCKED
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": next_step, "allowed_now": allowed, "purpose": "map 772 ledger events to a safe outcome source or provide missing artifact", "condition_change_allowed": False, "external_action_allowed": False},
        {"rank": 2, "next_step": "live_or_external", "allowed_now": False, "purpose": "blocked", "condition_change_allowed": False, "external_action_allowed": False},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C68 used 25C67 and 25C66 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Existing artifacts were scanned for entry_time plus outcome-like columns.", "status": "PASS"},
        {"note_id": "N003", "note": "No condition/source/external action was performed.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c68_file_request_list.csv", pd.DataFrame([{"section": "必要", "rank": 1, "item": "02_25c68_a002_fixed_scope_result_source_discovery_summary.json"}]))
    write_csv(out / "05_25c68_outcome_candidate_files.csv", candidates)
    write_csv(out / "06_25c68_safe_outcome_candidate_matrix.csv", safe_candidates)
    write_csv(out / "07_25c68_evaluation_readiness_matrix.csv", readiness)
    write_csv(out / "08_25c68_boundary_matrix.csv", boundary)
    write_csv(out / "09_25c68_next_step_plan.csv", next_plan)
    write_csv(out / "10_25c68_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "input_25c67_step": s67.get("step"),
        "input_25c67_status": s67.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "ledger_events": int(len(ledger)),
        "candidate_files_scanned": int(len(candidates)),
        "safe_outcome_candidates": int(len(safe_candidates)),
        "best_candidate_path": str(safe_candidates.iloc[0]["relative_path"]) if len(safe_candidates) > 0 else "",
        "best_candidate_match_count": int(safe_candidates.iloc[0]["entry_time_match_count"]) if len(safe_candidates) > 0 else 0,
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
    write_json(out / "02_25c68_a002_fixed_scope_result_source_discovery_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C68 A002 fixed scope result source discovery audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Contract audit", "", md_table(contract), "",
        "## Top candidate files", "", md_table(candidates.head(20)), "",
        "## Safe outcome candidates", "", md_table(safe_candidates), "",
        "## Readiness", "", md_table(readiness), "",
        "## Boundaries", "", md_table(boundary), "",
        "## Next", "", md_table(next_plan), "",
        "## Notes", "", md_table(notes),
    ])
    lp(out / "01_25c68_GOLD_V2_A002_FIXED_SCOPE_RESULT_SOURCE_DISCOVERY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "candidate_files_scanned": int(len(candidates)), "safe_outcome_candidates": int(len(safe_candidates)), "best_candidate_path": summary["best_candidate_path"], "trade_outcome_simulation_executed": False, "next_recommended_step": next_step}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
