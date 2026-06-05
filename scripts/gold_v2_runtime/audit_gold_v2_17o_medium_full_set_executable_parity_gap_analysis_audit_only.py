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

STEP = "17O_MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only"
REPORT_NAME = "GOLD_V2_17O_MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_STOPPED_AUDIT_ONLY"
EXPECTED_17N_STATUS = "MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_OPEN_GAP = "EXECUTABLE_PARITY_NOT_IMPLEMENTED_OR_APPROVED"
EXPECTED_TOTAL = 309
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
INPUTS = {
    "summary_17n": ("gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only", "gold_v2_17n_medium_full_set_dry_run_consolidation_summary.json"),
    "checks_17n": ("gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only", "gold_v2_17n_consolidation_checks.csv"),
    "matrix_17n": ("gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only", "gold_v2_17n_consolidation_matrix.csv"),
    "next_gates_17n": ("gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only", "gold_v2_17n_required_next_gates.csv"),
    "safety_17n": ("gold_v2_17n_medium_full_set_dry_run_consolidation_audit_only", "gold_v2_17n_safety_matrix.csv"),
    "manifest_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_full_set_candidate_manifest.csv"),
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
        [["17O-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17o_blockers.csv")
    write_json(out / "gold_v2_17o_medium_full_set_executable_parity_gap_analysis_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17O MEDIUM full-set executable parity gap analysis audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17o_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17n = read_json(input_path("summary_17n"))
    checks_17n = read_csv(input_path("checks_17n"))
    matrix_17n = read_csv(input_path("matrix_17n"))
    next_gates_17n = read_csv(input_path("next_gates_17n"))
    safety_17n = read_csv(input_path("safety_17n"))
    manifest = read_csv(input_path("manifest_17g"))

    checks: list[list[Any]] = []
    add_check(checks, "17O-C001", "17N status", str(summary_17n.get("status", "")), EXPECTED_17N_STATUS)
    add_check(checks, "17O-C002", "17N chain consolidated", bool_value(summary_17n.get("dry_run_chain_consolidated", False)), True)
    add_check(checks, "17O-C003", "17N open gap", str(summary_17n.get("open_gap", "")), EXPECTED_OPEN_GAP)
    add_check(checks, "17O-C004", "17N consolidation STOP rows", int(checks_17n[checks_17n["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17O-C005", "17N safety STOP rows", int(safety_17n[safety_17n["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17O-C006", "17N dry-run execution allowed", bool_value(summary_17n.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17O-C007", "17N live evaluator allowed", bool_value(summary_17n.get("medium_live_evaluator_allowed", False)), False)
    add_check(checks, "17O-C008", "17N final signal allowed", bool_value(summary_17n.get("final_signal_allowed", False)), False)
    add_check(checks, "17O-C009", "17N no_signal_discord_notified", bool_value(summary_17n.get("no_signal_discord_notified", False)), False)
    add_check(checks, "17O-C010", "17N next gates include 17O", bool("17O" in set(next_gates_17n.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "17O-C011", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for component, expected in EXPECTED_COUNTS.items():
        observed = int(manifest[manifest["component"].astype(str).eq(component)].shape[0]) if "component" in manifest.columns else -1
        add_check(checks, f"17O-COUNT-{component}", f"manifest rows {component}", observed, expected)

    gap_rows = []
    gap_rows.append(["TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP", "TIER2_HVT", 1, "13L summary-chain reference exists, but row-level executable source identity is not available in this chain.", "requires audited row-level TIER2 source identity artifact before executable parity", False, False])
    gap_rows.append(["RANGE96_EXECUTABLE_PREDICATE_GAP", "RANGE96_REFINED", EXPECTED_COUNTS["RANGE96_REFINED"], "RANGE96 source identities are frozen, but executable predicate parity is not implemented.", "requires predicate-source mapping plan and parity audit", False, False])
    gap_rows.append(["VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP", "VOL_TRMEAN32_REFINED", EXPECTED_COUNTS["VOL_TRMEAN32_REFINED"], "VOL source identities are frozen, but executable predicate parity is not implemented.", "requires predicate-source mapping plan and parity audit", False, False])
    gap_rows.append(["FULL_SET_ARBITRATION_EXECUTION_GAP", "MEDIUM_FULL_SET", EXPECTED_TOTAL, "Identity-only dry-run rows do not define executable MEDIUM arbitration behavior.", "requires arbitration replay/execution parity design after component parity", False, False])
    gap_rows.append(["LIVE_PARITY_AND_SAFETY_GATE_GAP", "MEDIUM_FULL_SET", EXPECTED_TOTAL, "No live evaluator/final signal/external action permission exists.", "requires later explicit live safety gates; currently blocked", False, False])
    gap_matrix = pd.DataFrame(gap_rows, columns=["gap_id", "component", "affected_rows", "gap_description", "required_resolution_before_implementation", "medium_live_evaluator_allowed", "final_signal_allowed"])
    component_gap_counts = gap_matrix.groupby("component", dropna=False)["affected_rows"].sum().reset_index(name="affected_rows")
    gap_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    next_gates = pd.DataFrame([
        ["17P", "MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY", "Plan parity work only; no implementation.", True],
        ["17Q", "MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY", "Only after 17P, map component parity sources if approved.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until executable parity and safety gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17o_success"])
    safety = pd.DataFrame(
        [["audit_only", True, True, "PASS"], ["gap_analysis_only", True, True, "PASS"], ["executable_parity_implemented", False, False, "PASS"], ["dry_run_execution_allowed", False, False, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"], ["no_signal_discord_notified", False, False, "PASS"]],
        columns=["safety_item", "observed", "expected", "status"],
    )
    ok = gap_checks[gap_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame(
        [["17O-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "parity plan only", "17P may plan parity work only; no implementation."], ["17O-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable predicates", "Executable parity is not implemented or approved."], ["17O-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(gap_checks, out / "gold_v2_17o_gap_analysis_checks.csv")
    write_csv(gap_matrix, out / "gold_v2_17o_executable_parity_gap_matrix.csv")
    write_csv(component_gap_counts, out / "gold_v2_17o_component_gap_counts.csv")
    write_csv(next_gates, out / "gold_v2_17o_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17o_blockers.csv")
    write_csv(safety, out / "gold_v2_17o_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "gap_analysis_ready": ok, "open_gap": EXPECTED_OPEN_GAP, "gap_count": int(gap_matrix.shape[0]), "affected_manifest_rows": int(EXPECTED_TOTAL), "executable_parity_implemented": False, "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17P_MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_17O_OUTPUTS"}
    write_json(out / "gold_v2_17o_medium_full_set_executable_parity_gap_analysis_summary.json", summary)
    report = ["# GOLD V2 17O MEDIUM full-set executable parity gap analysis audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17O documents executable parity gaps only.", "- It does not implement predicates, evaluate OHLC, create final signals, or enable live/external actions.", "- The next possible step is parity planning only.", "", "## Input audit", markdown_table(audit), "", "## Gap analysis checks", markdown_table(gap_checks), "", "## Executable parity gap matrix", markdown_table(gap_matrix), "", "## Component gap counts", markdown_table(component_gap_counts), "", "## Required next gates", markdown_table(next_gates), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17N consolidation carry-forward", markdown_table(matrix_17n)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
