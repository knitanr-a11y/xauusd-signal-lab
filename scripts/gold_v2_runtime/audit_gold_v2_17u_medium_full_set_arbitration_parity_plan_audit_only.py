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

STEP = "17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17u_medium_full_set_arbitration_parity_plan_audit_only"
REPORT_NAME = "GOLD_V2_17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_17T_STATUS = "VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_17S_STATUS = "RANGE96_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_17R_STATUS = "TIER2_ROW_LEVEL_SOURCE_MAPPING_GAP_CONFIRMED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
EXPECTED_TOTAL = 309
INPUTS = {
    "summary_17t": ("gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only", "gold_v2_17t_vol_trmean32_predicate_source_mapping_summary.json"),
    "checks_17t": ("gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only", "gold_v2_17t_vol_trmean32_source_mapping_checks.csv"),
    "requirements_17t": ("gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only", "gold_v2_17t_vol_trmean32_required_source_artifacts.csv"),
    "next_gates_17t": ("gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only", "gold_v2_17t_required_next_gates.csv"),
    "safety_17t": ("gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only", "gold_v2_17t_safety_matrix.csv"),
    "summary_17s": ("gold_v2_17s_range96_predicate_source_mapping_audit_only", "gold_v2_17s_range96_predicate_source_mapping_summary.json"),
    "summary_17r": ("gold_v2_17r_tier2_row_level_source_mapping_audit_only", "gold_v2_17r_tier2_row_level_source_mapping_summary.json"),
    "manifest_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_full_set_candidate_manifest.csv"),
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
        [["17U-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17u_blockers.csv")
    write_json(out / "gold_v2_17u_medium_full_set_arbitration_parity_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17U MEDIUM full-set arbitration parity plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17u_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17t = read_json(ip("summary_17t"))
    checks_17t = read_csv(ip("checks_17t"))
    requirements_17t = read_csv(ip("requirements_17t"))
    next_gates_17t = read_csv(ip("next_gates_17t"))
    safety_17t = read_csv(ip("safety_17t"))
    summary_17s = read_json(ip("summary_17s"))
    summary_17r = read_json(ip("summary_17r"))
    manifest = read_csv(ip("manifest_17g"))

    counts = manifest.groupby("component").size().to_dict() if "component" in manifest.columns else {}
    checks: list[list[Any]] = []
    add_check(checks, "17U-C001", "17T status", str(summary_17t.get("status", "")), EXPECTED_17T_STATUS)
    add_check(checks, "17U-C002", "17S status", str(summary_17s.get("status", "")), EXPECTED_17S_STATUS)
    add_check(checks, "17U-C003", "17R status", str(summary_17r.get("status", "")), EXPECTED_17R_STATUS)
    add_check(checks, "17U-C004", "17T VOL mapping ready", bool_value(summary_17t.get("vol_trmean32_predicate_source_mapping_ready", False)), True)
    add_check(checks, "17U-C005", "17S RANGE96 mapping ready", bool_value(summary_17s.get("range96_predicate_source_mapping_ready", False)), True)
    add_check(checks, "17U-C006", "17R TIER2 gap confirmed", bool_value(summary_17r.get("tier2_row_level_source_mapping_gap_confirmed", False)), True)
    add_check(checks, "17U-C007", "17T checks STOP rows", int(checks_17t[checks_17t["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17U-C008", "17T safety STOP rows", int(safety_17t[safety_17t["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17U-C009", "17T next gates include 17U", bool("17U" in set(next_gates_17t.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "17U-C010", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for component, expected in EXPECTED_COUNTS.items():
        add_check(checks, f"17U-COUNT-{component}", f"manifest rows {component}", int(counts.get(component, -1)), expected)
    for flag in ["predicate_implementation_allowed", "executable_parity_implemented", "dry_run_execution_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"17U-FLAG-17T-{flag}", f"17T {flag}", bool_value(summary_17t.get(flag, False)), False)

    component_dependency = pd.DataFrame([
        ["TIER2_HVT", int(counts.get("TIER2_HVT", 0)), "TIER2_ROW_LEVEL_SOURCE_IDENTITY_MISSING_CONFIRMED", "blocks_tier2_executable_parity", False, False, False],
        ["RANGE96_REFINED", int(counts.get("RANGE96_REFINED", 0)), "RANGE96_SOURCE_MAPPING_READY_NOT_IMPLEMENTED", "requires_predicate_parity_design_before_execution", False, False, False],
        ["VOL_TRMEAN32_REFINED", int(counts.get("VOL_TRMEAN32_REFINED", 0)), "VOL_SOURCE_MAPPING_READY_NOT_IMPLEMENTED", "requires_predicate_parity_design_before_execution", False, False, False],
        ["MEDIUM_FULL_SET", EXPECTED_TOTAL, "ARBITRATION_PARITY_PLAN_REQUIRED", "requires_component_parity_completion_first", False, False, False],
    ], columns=["component", "rows", "current_state", "dependency_status", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    arbitration_plan = pd.DataFrame([
        [1, "Freeze component dependency status", "Use 17R/17S/17T only", "planning_only", False, False, False],
        [2, "Define arbitration source contract", "Specify required component parity artifacts", "planning_only", False, False, False],
        [3, "Define replay parity acceptance criteria", "No OHLC evaluation in 17U", "planning_only", False, False, False],
        [4, "Define later stop gates", "Stop on missing TIER2 row-level identity or predicate mismatch", "planning_only", False, False, False],
        [5, "Defer live/final safety", "17V may plan safety gates only", "planning_only", False, False, False],
    ], columns=["planned_order", "planned_item", "scope", "action_type", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    planned_stops = pd.DataFrame([
        ["17U-S001", "attempt to implement arbitration", "STOP"],
        ["17U-S002", "attempt to implement predicates", "STOP"],
        ["17U-S003", "attempt to evaluate OHLC", "STOP"],
        ["17U-S004", "attempt to emit final signal", "STOP"],
        ["17U-S005", "attempt to enable Discord/MT5/AI/live hook", "STOP"],
        ["17U-S006", "missing TIER2 row-level source identity before executable parity", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_required = pd.DataFrame([
        ["17V", "LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY", "Plan live/final safety gates only; no enablement.", True],
        ["17U_IMPL", "MEDIUM_FULL_SET_ARBITRATION_IMPLEMENTATION", "Blocked; 17U is planning only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until executable parity and safety gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17u_success"])
    plan_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["planning_only", True, True, "PASS"],
        ["arbitration_implementation_allowed", False, False, "PASS"],
        ["predicate_implementation_allowed", False, False, "PASS"],
        ["executable_parity_implemented", False, False, "PASS"],
        ["dry_run_execution_allowed", False, False, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = plan_checks[plan_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame([
        ["17U-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "arbitration implementation", "Arbitration implementation remains blocked."],
        ["17U-B020", "TIER2_HVT", "HARD", "OPEN", "TIER2 row-level source identity", "Still required before executable parity."],
        ["17U-B030", "MEDIUM_FULL_SET", "HARD", "OPEN", "live safety gates", "17V may plan safety gates only; no enablement."],
        ["17U-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(plan_checks, out / "gold_v2_17u_arbitration_plan_checks.csv")
    write_csv(component_dependency, out / "gold_v2_17u_component_dependency_matrix.csv")
    write_csv(arbitration_plan, out / "gold_v2_17u_arbitration_parity_plan.csv")
    write_csv(planned_stops, out / "gold_v2_17u_planned_stop_conditions.csv")
    write_csv(next_required, out / "gold_v2_17u_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17u_blockers.csv")
    write_csv(safety, out / "gold_v2_17u_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "arbitration_parity_plan_ready": ok, "component_counts": EXPECTED_COUNTS, "total_manifest_rows": EXPECTED_TOTAL, "tier2_row_level_gap_confirmed": bool_value(summary_17r.get("tier2_row_level_source_mapping_gap_confirmed", False)), "range96_mapping_ready": bool_value(summary_17s.get("range96_predicate_source_mapping_ready", False)), "vol_trmean32_mapping_ready": bool_value(summary_17t.get("vol_trmean32_predicate_source_mapping_ready", False)), "arbitration_implementation_allowed": False, "predicate_implementation_allowed": False, "executable_parity_implemented": False, "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17V_LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_17U_OUTPUTS"}
    write_json(out / "gold_v2_17u_medium_full_set_arbitration_parity_plan_summary.json", summary)
    report = ["# GOLD V2 17U MEDIUM full-set arbitration parity plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17U writes an arbitration parity plan only.", "- It does not implement arbitration/predicates, evaluate OHLC, create final signals, or enable live/external actions.", "", "## Input audit", markdown_table(audit), "", "## Arbitration plan checks", markdown_table(plan_checks), "", "## Component dependency matrix", markdown_table(component_dependency), "", "## Arbitration parity plan", markdown_table(arbitration_plan), "", "## Planned stop conditions", markdown_table(planned_stops), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17T requirements carry-forward", markdown_table(requirements_17t)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
