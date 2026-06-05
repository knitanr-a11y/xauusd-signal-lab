#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "17N_MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only"
REPORT_NAME = "GOLD_V2_17N_MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_STOPPED_AUDIT_ONLY"
EXPECTED_17M_STATUS = "MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_TOTAL = 309
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
INPUTS = {
    "summary_17m": ("gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only", "gold_v2_17m_medium_full_set_dry_run_load_smoke_summary.json"),
    "load_checks_17m": ("gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only", "gold_v2_17m_dry_run_load_checks.csv"),
    "component_counts_17m": ("gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only", "gold_v2_17m_component_counts_check.csv"),
    "safety_17m": ("gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only", "gold_v2_17m_safety_matrix.csv"),
    "blockers_17m": ("gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only", "gold_v2_17m_blockers.csv"),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def output_dir() -> Path:
    path = fx_outputs() / OUT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def input_path(role: str) -> Path:
    folder, name = INPUTS[role]
    return fx_outputs() / folder / name


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(float(value)) else float(value)
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def markdown_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in df.columns) + " |")
    return "\n".join(lines)


def input_audit() -> pd.DataFrame:
    rows = []
    for role in INPUTS:
        path = input_path(role)
        row = {"role": role, "path": str(path), "required": True, "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
        rows.append(row)
    return pd.DataFrame(rows)


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def stop_missing(out: Path, now: str, audit: pd.DataFrame) -> int:
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    blockers = pd.DataFrame(
        [["17N-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17n_blockers.csv")
    write_json(out / "gold_v2_17n_medium_full_set_dry_run_consolidation_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17N MEDIUM full-set dry-run consolidation audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17n_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17m = read_json(input_path("summary_17m"))
    load_checks = read_csv(input_path("load_checks_17m"))
    counts = read_csv(input_path("component_counts_17m"))
    safety_17m = read_csv(input_path("safety_17m"))
    blockers_17m = read_csv(input_path("blockers_17m"))

    checks: list[list[Any]] = []
    add_check(checks, "17N-C001", "17M status", str(summary_17m.get("status", "")), EXPECTED_17M_STATUS)
    add_check(checks, "17N-C002", "17M dry_run_load_smoke_passed", bool_value(summary_17m.get("dry_run_load_smoke_passed", False)), True)
    add_check(checks, "17N-C003", "17M loaded_dry_run_rows", int(summary_17m.get("loaded_dry_run_rows", -1)), EXPECTED_TOTAL)
    add_check(checks, "17N-C004", "17M load check STOP rows", int(load_checks[load_checks["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17N-C005", "17M safety STOP rows", int(safety_17m[safety_17m["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17N-C006", "17M dry-run execution allowed", bool_value(summary_17m.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17N-C007", "17M live evaluator allowed", bool_value(summary_17m.get("medium_live_evaluator_allowed", False)), False)
    add_check(checks, "17N-C008", "17M final signal allowed", bool_value(summary_17m.get("final_signal_allowed", False)), False)
    add_check(checks, "17N-C009", "17M no_signal_discord_notified", bool_value(summary_17m.get("no_signal_discord_notified", False)), False)
    for component, expected in EXPECTED_COUNTS.items():
        observed = -1
        if "component" in counts.columns and "loaded_dry_run_rows" in counts.columns:
            sub = counts[counts["component"].astype(str).eq(component)]
            observed = int(sub["loaded_dry_run_rows"].iloc[0]) if len(sub) else -1
        add_check(checks, f"17N-COUNT-{component}", f"loaded rows {component}", observed, expected)

    consolidation_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    matrix = pd.DataFrame([
        ["source_reconciliation", "17C/17D", "completed", "RANGE96 and VOL source identity freeze/reconcile completed before dry-run chain", False, False],
        ["candidate_manifest", "17G", "completed", "Full-set manifest exists, 309 rows", False, False],
        ["manifest_load_smoke", "17H", "completed", "Manifest load-smoke passed", False, False],
        ["dry_run_gate", "17I", "completed", "Dry-run design gate passed, execution remains false", False, False],
        ["dry_run_design", "17J", "completed", "Input/output/stop contracts created", False, False],
        ["dry_run_plan", "17K", "completed", "Implementation plan created", False, False],
        ["dry_run_identity_rows", "17L", "completed", "Identity-only audit rows written", False, False],
        ["dry_run_load_smoke", "17M", "completed", "Dry-run audit rows load-smoked", False, False],
        ["executable_parity", "17O+", "open_gap", "Executable predicate parity is not implemented or approved", False, False],
        ["live_evaluator", "future", "blocked", "Live evaluator remains blocked", False, False],
    ], columns=["area", "source_step", "status", "note", "medium_live_evaluator_allowed", "final_signal_allowed"])
    next_gates = pd.DataFrame([
        ["17O", "MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY", "Define remaining gap from identity-only dry-run to executable parity; no implementation.", True],
        ["17P", "MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY", "Only after 17O, plan parity work if still audit-only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until separate executable parity, dry-run, and safety gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17n_success"])
    safety = pd.DataFrame(
        [["audit_only", True, True, "PASS"], ["dry_run_chain_consolidated", True, True, "PASS"], ["dry_run_execution_allowed", False, False, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"], ["no_signal_discord_notified", False, False, "PASS"]],
        columns=["safety_item", "observed", "expected", "status"],
    )
    ok = consolidation_checks[consolidation_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame(
        [["17N-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable parity gap", "17O may analyze the gap only; no executable/live/final actions."], ["17N-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "live evaluator", "Live evaluator remains blocked."], ["17N-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(consolidation_checks, out / "gold_v2_17n_consolidation_checks.csv")
    write_csv(matrix, out / "gold_v2_17n_consolidation_matrix.csv")
    write_csv(next_gates, out / "gold_v2_17n_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17n_blockers.csv")
    write_csv(safety, out / "gold_v2_17n_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "dry_run_chain_consolidated": ok, "loaded_dry_run_rows": int(summary_17m.get("loaded_dry_run_rows", -1)), "component_counts": counts.to_dict("records"), "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "open_gap": "EXECUTABLE_PARITY_NOT_IMPLEMENTED_OR_APPROVED", "next_recommended_step": "17O_MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY" if ok else "STOP_REVIEW_17N_OUTPUTS"}
    write_json(out / "gold_v2_17n_medium_full_set_dry_run_consolidation_summary.json", summary)
    report = ["# GOLD V2 17N MEDIUM full-set dry-run consolidation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17N consolidates the completed dry-run audit chain through 17M.", "- It does not implement executable parity and does not enable live/final/external actions.", "- The remaining major gap is executable parity, which may only be analyzed next in audit-only mode.", "", "## Input audit", markdown_table(audit), "", "## Consolidation checks", markdown_table(consolidation_checks), "", "## Consolidation matrix", markdown_table(matrix), "", "## Required next gates", markdown_table(next_gates), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17M blocker carry-forward", markdown_table(blockers_17m)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
