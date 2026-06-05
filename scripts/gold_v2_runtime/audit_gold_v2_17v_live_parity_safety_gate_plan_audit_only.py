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

STEP = "17V_LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17v_live_parity_safety_gate_plan_audit_only"
REPORT_NAME = "GOLD_V2_17V_LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "LIVE_PARITY_SAFETY_GATE_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "LIVE_PARITY_SAFETY_GATE_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_17U_STATUS = "MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_medium_full_set_arbitration_parity_plan_summary.json"),
    "checks_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_arbitration_plan_checks.csv"),
    "dependency_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_component_dependency_matrix.csv"),
    "plan_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_arbitration_parity_plan.csv"),
    "stops_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_planned_stop_conditions.csv"),
    "next_gates_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_required_next_gates.csv"),
    "safety_17u": ("gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only", "gold_v2_17u_safety_matrix.csv"),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def out_dir() -> Path:
    p = fx_outputs() / OUT_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def ip(role: str) -> Path:
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
        path = ip(role)
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
        [["17V-BINPUT", "SAFETY", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17v_blockers.csv")
    write_json(out / "gold_v2_17v_live_parity_safety_gate_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17V live parity safety gate plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17v_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17u = read_json(ip("summary_17u"))
    checks_17u = read_csv(ip("checks_17u"))
    dependency_17u = read_csv(ip("dependency_17u"))
    plan_17u = read_csv(ip("plan_17u"))
    stops_17u = read_csv(ip("stops_17u"))
    next_gates_17u = read_csv(ip("next_gates_17u"))
    safety_17u = read_csv(ip("safety_17u"))

    checks: list[list[Any]] = []
    add_check(checks, "17V-C001", "17U status", str(summary_17u.get("status", "")), EXPECTED_17U_STATUS)
    add_check(checks, "17V-C002", "17U arbitration plan ready", bool_value(summary_17u.get("arbitration_parity_plan_ready", False)), True)
    add_check(checks, "17V-C003", "17U TIER2 gap confirmed", bool_value(summary_17u.get("tier2_row_level_gap_confirmed", False)), True)
    add_check(checks, "17V-C004", "17U RANGE96 mapping ready", bool_value(summary_17u.get("range96_mapping_ready", False)), True)
    add_check(checks, "17V-C005", "17U VOL mapping ready", bool_value(summary_17u.get("vol_trmean32_mapping_ready", False)), True)
    add_check(checks, "17V-C006", "17U checks STOP rows", int(checks_17u[checks_17u["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17V-C007", "17U safety STOP rows", int(safety_17u[safety_17u["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17V-C008", "17U next gates include 17V", bool("17V" in set(next_gates_17u.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    for flag in ["arbitration_implementation_allowed", "predicate_implementation_allowed", "executable_parity_implemented", "dry_run_execution_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"17V-FLAG-17U-{flag}", f"17U {flag}", bool_value(summary_17u.get(flag, False)), False)
    external = summary_17u.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"17V-EXT-17U-{flag}", f"17U {flag}", bool_value(external.get(flag, False)), False)
    add_check(checks, "17V-NO-SIGNAL", "17U no_signal_discord_notified", bool_value(summary_17u.get("no_signal_discord_notified", False)), False)

    gate_rows = [
        ["GATE_EXECUTABLE_PARITY_COMPLETE", "executable parity must be implemented and separately audited", "not_satisfied", False, False, False, False],
        ["GATE_TIER2_ROW_LEVEL_SOURCE_IDENTITY", "TIER2 row-level source identity must be resolved", "not_satisfied", False, False, False, False],
        ["GATE_COMPONENT_PREDICATE_PARITY", "RANGE96/VOL/TIER2 predicate parity must be audited", "not_satisfied", False, False, False, False],
        ["GATE_ARBITRATION_REPLAY_PARITY", "MEDIUM arbitration replay parity must be audited", "not_satisfied", False, False, False, False],
        ["GATE_LIVE_EVALUATOR_REVIEW", "live evaluator implementation review must pass", "not_satisfied", False, False, False, False],
        ["GATE_FINAL_SIGNAL_AUTHORIZATION", "final signal must be explicitly authorized", "not_satisfied", False, False, False, False],
        ["GATE_DISCORD_AUTHORIZATION", "Discord notifications must be explicitly authorized", "not_satisfied", False, False, False, False],
        ["GATE_MT5_AUTHORIZATION", "MT5 orders must be explicitly authorized", "not_satisfied", False, False, False, False],
        ["GATE_AI_API_AUTHORIZATION", "AI API must be explicitly authorized", "not_satisfied", False, False, False, False],
        ["GATE_LIVE_HOOK_AUTHORIZATION", "live hook must be explicitly authorized", "not_satisfied", False, False, False, False],
        ["GATE_NO_SIGNAL_NON_NOTIFICATION", "NO_SIGNAL must not notify Discord", "satisfied_as_false", False, False, False, False],
    ]
    gate_matrix = pd.DataFrame(gate_rows, columns=["gate_id", "requirement", "current_status", "gate_enabled_now", "medium_live_evaluator_allowed", "final_signal_allowed", "external_action_allowed"])
    non_enablement = pd.DataFrame([
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["item", "observed", "expected", "status"])
    plan_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    next_required = pd.DataFrame([
        ["17W", "MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION", "Consolidate audit-only roadmap and blockers; no enablement.", True],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until executable parity and safety gates pass.", False],
        ["FINAL", "MEDIUM_FULL_SET_FINAL_SIGNAL", "Blocked until explicit final authorization.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17v_success"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["safety_gate_plan_only", True, True, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    add_check(plan_checks_rows := [], "17V-GATES-ENABLED", "enabled gate rows", int(gate_matrix[gate_matrix["gate_enabled_now"].map(bool_value)].shape[0]), 0)
    extra_gate_check = pd.DataFrame(plan_checks_rows, columns=["check_id", "check", "observed", "expected", "status"])
    plan_checks = pd.concat([plan_checks, extra_gate_check], ignore_index=True)
    ok = plan_checks[plan_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty and non_enablement[non_enablement["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame([
        ["17V-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable parity", "Executable parity is not complete."],
        ["17V-B020", "TIER2_HVT", "HARD", "OPEN", "TIER2 row-level source identity", "Still required before executable parity."],
        ["17V-B030", "MEDIUM_FULL_SET", "HARD", "OPEN", "live/final authorization", "No live or final authorization exists."],
        ["17V-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(plan_checks, out / "gold_v2_17v_safety_gate_plan_checks.csv")
    write_csv(gate_matrix, out / "gold_v2_17v_live_safety_gate_matrix.csv")
    write_csv(non_enablement, out / "gold_v2_17v_non_enablement_matrix.csv")
    write_csv(next_required, out / "gold_v2_17v_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17v_blockers.csv")
    write_csv(safety, out / "gold_v2_17v_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "live_parity_safety_gate_plan_ready": ok, "planned_safety_gates": int(gate_matrix.shape[0]), "enabled_safety_gates_now": int(gate_matrix[gate_matrix["gate_enabled_now"].map(bool_value)].shape[0]), "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17W_MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION" if ok else "STOP_REVIEW_17V_OUTPUTS"}
    write_json(out / "gold_v2_17v_live_parity_safety_gate_plan_summary.json", summary)
    report = ["# GOLD V2 17V live parity safety gate plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17V writes a live parity safety-gate plan only.", "- It does not enable live mode, final signals, Discord, MT5, AI API, or live hook.", "", "## Input audit", markdown_table(audit), "", "## Safety gate plan checks", markdown_table(plan_checks), "", "## Live safety gate matrix", markdown_table(gate_matrix), "", "## Non-enablement matrix", markdown_table(non_enablement), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17U dependency carry-forward", markdown_table(dependency_17u), "", "## 17U arbitration plan carry-forward", markdown_table(plan_17u), "", "## 17U stop conditions carry-forward", markdown_table(stops_17u)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
