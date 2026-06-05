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

STEP = "17P_MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17p_medium_full_set_executable_parity_plan_audit_only"
REPORT_NAME = "GOLD_V2_17P_MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_17O_STATUS = "MEDIUM_FULL_SET_EXECUTABLE_PARITY_GAP_ANALYSIS_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_OPEN_GAP = "EXECUTABLE_PARITY_NOT_IMPLEMENTED_OR_APPROVED"
EXPECTED_GAPS = [
    "TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP",
    "RANGE96_EXECUTABLE_PREDICATE_GAP",
    "VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP",
    "FULL_SET_ARBITRATION_EXECUTION_GAP",
    "LIVE_PARITY_AND_SAFETY_GATE_GAP",
]
INPUTS = {
    "summary_17o": ("gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only", "gold_v2_17o_medium_full_set_executable_parity_gap_analysis_summary.json"),
    "checks_17o": ("gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only", "gold_v2_17o_gap_analysis_checks.csv"),
    "gap_matrix_17o": ("gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only", "gold_v2_17o_executable_parity_gap_matrix.csv"),
    "gap_counts_17o": ("gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only", "gold_v2_17o_component_gap_counts.csv"),
    "next_gates_17o": ("gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only", "gold_v2_17o_required_next_gates.csv"),
    "safety_17o": ("gold_v2_17o_medium_full_set_executable_parity_gap_analysis_audit_only", "gold_v2_17o_safety_matrix.csv"),
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
        [["17P-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17p_blockers.csv")
    write_json(out / "gold_v2_17p_medium_full_set_executable_parity_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17P MEDIUM full-set executable parity plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17p_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17o = read_json(input_path("summary_17o"))
    checks_17o = read_csv(input_path("checks_17o"))
    gap_matrix_17o = read_csv(input_path("gap_matrix_17o"))
    gap_counts_17o = read_csv(input_path("gap_counts_17o"))
    next_gates_17o = read_csv(input_path("next_gates_17o"))
    safety_17o = read_csv(input_path("safety_17o"))

    checks: list[list[Any]] = []
    add_check(checks, "17P-C001", "17O status", str(summary_17o.get("status", "")), EXPECTED_17O_STATUS)
    add_check(checks, "17P-C002", "17O gap_analysis_ready", bool_value(summary_17o.get("gap_analysis_ready", False)), True)
    add_check(checks, "17P-C003", "17O open gap", str(summary_17o.get("open_gap", "")), EXPECTED_OPEN_GAP)
    add_check(checks, "17P-C004", "17O executable parity implemented", bool_value(summary_17o.get("executable_parity_implemented", False)), False)
    add_check(checks, "17P-C005", "17O dry-run execution allowed", bool_value(summary_17o.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17P-C006", "17O final signal allowed", bool_value(summary_17o.get("final_signal_allowed", False)), False)
    add_check(checks, "17P-C007", "17O checks STOP rows", int(checks_17o[checks_17o["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17P-C008", "17O safety STOP rows", int(safety_17o[safety_17o["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17P-C009", "17O next gates include 17P", bool("17P" in set(next_gates_17o.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    gap_ids = set(gap_matrix_17o.get("gap_id", pd.Series(dtype=str)).astype(str))
    for gap_id in EXPECTED_GAPS:
        add_check(checks, f"17P-GAP-{gap_id}", f"gap present {gap_id}", gap_id in gap_ids, True)

    ordering = {
        "TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP": 1,
        "RANGE96_EXECUTABLE_PREDICATE_GAP": 2,
        "VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP": 3,
        "FULL_SET_ARBITRATION_EXECUTION_GAP": 4,
        "LIVE_PARITY_AND_SAFETY_GATE_GAP": 5,
    }
    next_step_map = {
        "TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP": "17Q_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY",
        "RANGE96_EXECUTABLE_PREDICATE_GAP": "17R_RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY",
        "VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP": "17S_VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY",
        "FULL_SET_ARBITRATION_EXECUTION_GAP": "17T_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY",
        "LIVE_PARITY_AND_SAFETY_GATE_GAP": "17U_LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY",
    }
    plan_rows = []
    for _, row in gap_matrix_17o.iterrows():
        gap_id = str(row.get("gap_id", ""))
        plan_rows.append([
            gap_id,
            row.get("component", ""),
            int(row.get("affected_rows", 0)),
            ordering.get(gap_id, 99),
            next_step_map.get(gap_id, "UNMAPPED_REVIEW_REQUIRED"),
            "planning_or_source_mapping_only",
            "no implementation; no OHLC; no final/live/external actions",
            False,
            False,
        ])
    component_plan = pd.DataFrame(plan_rows, columns=["gap_id", "component", "affected_rows", "planned_order", "planned_next_step", "planned_action_type", "restriction", "medium_live_evaluator_allowed", "final_signal_allowed"]).sort_values("planned_order")
    gap_to_next = component_plan[["gap_id", "planned_next_step", "planned_order", "restriction"]].copy()
    planned_stops = pd.DataFrame([
        ["17P-S001", "attempt to implement executable predicate", "STOP"],
        ["17P-S002", "attempt to evaluate OHLC", "STOP"],
        ["17P-S003", "attempt to emit final signal", "STOP"],
        ["17P-S004", "attempt to enable Discord/MT5/AI/live hook", "STOP"],
        ["17P-S005", "missing audited source mapping for a gap", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_gates = pd.DataFrame([
        ["17Q", "MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY", "Begin source-mapping plan for component parity; no predicates implemented.", True],
        ["17R", "RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "Only after source-mapping plan is approved.", False],
        ["17S", "VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "Only after source-mapping plan is approved.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until executable parity and safety gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17p_success"])
    plan_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame(
        [["audit_only", True, True, "PASS"], ["planning_only", True, True, "PASS"], ["executable_parity_implemented", False, False, "PASS"], ["dry_run_execution_allowed", False, False, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"], ["no_signal_discord_notified", False, False, "PASS"]],
        columns=["safety_item", "observed", "expected", "status"],
    )
    ok = plan_checks[plan_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame(
        [["17P-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "source mapping only", "17Q may map sources only; no executable predicate implementation."], ["17P-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "live evaluator", "Live evaluator remains blocked."], ["17P-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(plan_checks, out / "gold_v2_17p_plan_checks.csv")
    write_csv(component_plan, out / "gold_v2_17p_component_parity_plan.csv")
    write_csv(gap_to_next, out / "gold_v2_17p_gap_to_next_step_map.csv")
    write_csv(planned_stops, out / "gold_v2_17p_planned_stop_conditions.csv")
    write_csv(next_gates, out / "gold_v2_17p_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17p_blockers.csv")
    write_csv(safety, out / "gold_v2_17p_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "parity_plan_ready": ok, "gap_count": int(component_plan.shape[0]), "input_17o_status": str(summary_17o.get("status", "")), "executable_parity_implemented": False, "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY" if ok else "STOP_REVIEW_17P_OUTPUTS"}
    write_json(out / "gold_v2_17p_medium_full_set_executable_parity_plan_summary.json", summary)
    report = ["# GOLD V2 17P MEDIUM full-set executable parity plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17P writes a parity plan only.", "- It does not implement predicates, evaluate OHLC, create final signals, or enable live/external actions.", "- The next possible step is source mapping only.", "", "## Input audit", markdown_table(audit), "", "## Plan checks", markdown_table(plan_checks), "", "## Component parity plan", markdown_table(component_plan), "", "## Gap to next step map", markdown_table(gap_to_next), "", "## Planned stop conditions", markdown_table(planned_stops), "", "## Required next gates", markdown_table(next_gates), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17O component gap counts", markdown_table(gap_counts_17o)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
