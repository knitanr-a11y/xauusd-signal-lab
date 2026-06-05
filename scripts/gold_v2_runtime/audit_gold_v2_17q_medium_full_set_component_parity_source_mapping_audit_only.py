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

STEP = "17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only"
REPORT_NAME = "GOLD_V2_17Q_MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_STOPPED_AUDIT_ONLY"
EXPECTED_17P_STATUS = "MEDIUM_FULL_SET_EXECUTABLE_PARITY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_TOTAL = 309
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
EXPECTED_GAPS = [
    "TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP",
    "RANGE96_EXECUTABLE_PREDICATE_GAP",
    "VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP",
    "FULL_SET_ARBITRATION_EXECUTION_GAP",
    "LIVE_PARITY_AND_SAFETY_GATE_GAP",
]
INPUTS = {
    "summary_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_medium_full_set_executable_parity_plan_summary.json"),
    "checks_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_plan_checks.csv"),
    "component_plan_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_component_parity_plan.csv"),
    "gap_map_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_gap_to_next_step_map.csv"),
    "planned_stops_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_planned_stop_conditions.csv"),
    "next_gates_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_required_next_gates.csv"),
    "safety_17p": ("gold_v2_17p_medium_full_set_executable_parity_plan_audit_only", "gold_v2_17p_safety_matrix.csv"),
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
        [["17Q-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17q_blockers.csv")
    write_json(out / "gold_v2_17q_medium_full_set_component_parity_source_mapping_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17Q MEDIUM full-set component parity source mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17q_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17p = read_json(input_path("summary_17p"))
    checks_17p = read_csv(input_path("checks_17p"))
    component_plan = read_csv(input_path("component_plan_17p"))
    gap_map = read_csv(input_path("gap_map_17p"))
    planned_stops = read_csv(input_path("planned_stops_17p"))
    next_gates = read_csv(input_path("next_gates_17p"))
    safety_17p = read_csv(input_path("safety_17p"))
    manifest = read_csv(input_path("manifest_17g"))

    checks: list[list[Any]] = []
    add_check(checks, "17Q-C001", "17P status", str(summary_17p.get("status", "")), EXPECTED_17P_STATUS)
    add_check(checks, "17Q-C002", "17P parity_plan_ready", bool_value(summary_17p.get("parity_plan_ready", False)), True)
    add_check(checks, "17Q-C003", "17P executable parity implemented", bool_value(summary_17p.get("executable_parity_implemented", False)), False)
    add_check(checks, "17Q-C004", "17P dry-run execution allowed", bool_value(summary_17p.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17Q-C005", "17P final signal allowed", bool_value(summary_17p.get("final_signal_allowed", False)), False)
    add_check(checks, "17Q-C006", "17P check STOP rows", int(checks_17p[checks_17p["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17Q-C007", "17P safety STOP rows", int(safety_17p[safety_17p["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17Q-C008", "17P next gates include 17Q", bool("17Q" in set(next_gates.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "17Q-C009", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for component, expected in EXPECTED_COUNTS.items():
        observed = int(manifest[manifest["component"].astype(str).eq(component)].shape[0]) if "component" in manifest.columns else -1
        add_check(checks, f"17Q-COUNT-{component}", f"manifest rows {component}", observed, expected)
    gap_ids = set(component_plan.get("gap_id", pd.Series(dtype=str)).astype(str))
    for gap_id in EXPECTED_GAPS:
        add_check(checks, f"17Q-GAP-{gap_id}", f"component plan gap {gap_id}", gap_id in gap_ids, True)

    mapping_rows = [
        ["TIER2_ROW_LEVEL_SOURCE_IDENTITY_GAP", "TIER2_HVT", 1, "audited_tier2_row_level_source_identity_artifact", "17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY", "required_before_predicate_parity", False, False, False],
        ["RANGE96_EXECUTABLE_PREDICATE_GAP", "RANGE96_REFINED", EXPECTED_COUNTS["RANGE96_REFINED"], "audited_range96_predicate_source_mapping_artifact", "17S_RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "required_before_predicate_parity", False, False, False],
        ["VOL_TRMEAN32_EXECUTABLE_PREDICATE_GAP", "VOL_TRMEAN32_REFINED", EXPECTED_COUNTS["VOL_TRMEAN32_REFINED"], "audited_vol_trmean32_predicate_source_mapping_artifact", "17T_VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "required_before_predicate_parity", False, False, False],
        ["FULL_SET_ARBITRATION_EXECUTION_GAP", "MEDIUM_FULL_SET", EXPECTED_TOTAL, "audited_component_parity_completion_artifacts_and_arbitration_plan", "17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY", "requires_component_parity_first", False, False, False],
        ["LIVE_PARITY_AND_SAFETY_GATE_GAP", "MEDIUM_FULL_SET", EXPECTED_TOTAL, "explicit_live_safety_gate_artifacts", "17V_LIVE_PARITY_SAFETY_GATE_PLAN_AUDIT_ONLY", "requires_executable_parity_first", False, False, False],
    ]
    source_mapping = pd.DataFrame(mapping_rows, columns=["gap_id", "component", "affected_rows", "required_source_artifact_class", "planned_mapping_step", "requirement_status", "predicate_implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    source_requirements = source_mapping[["component", "required_source_artifact_class", "planned_mapping_step", "requirement_status"]].copy()
    mapping_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    next_required = pd.DataFrame([
        ["17R", "TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY", "Map TIER2 row-level source identity only; no executable predicate.", True],
        ["17S", "RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "Map RANGE96 predicate source only after 17R/source mapping gate.", False],
        ["17T", "VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "Map VOL predicate source only after earlier mapping gates.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until executable parity and safety gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17q_success"])
    safety = pd.DataFrame(
        [["audit_only", True, True, "PASS"], ["source_mapping_only", True, True, "PASS"], ["predicate_implementation_allowed", False, False, "PASS"], ["executable_parity_implemented", False, False, "PASS"], ["dry_run_execution_allowed", False, False, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"], ["no_signal_discord_notified", False, False, "PASS"]],
        columns=["safety_item", "observed", "expected", "status"],
    )
    ok = mapping_checks[mapping_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame(
        [["17Q-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "tier2 row-level source mapping", "17R may map TIER2 source identity only; no predicate implementation."], ["17Q-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "predicate implementation", "Predicate implementation remains blocked."], ["17Q-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(mapping_checks, out / "gold_v2_17q_source_mapping_checks.csv")
    write_csv(source_mapping, out / "gold_v2_17q_component_source_mapping_matrix.csv")
    write_csv(source_requirements, out / "gold_v2_17q_source_artifact_requirements.csv")
    write_csv(next_required, out / "gold_v2_17q_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17q_blockers.csv")
    write_csv(safety, out / "gold_v2_17q_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "source_mapping_ready": ok, "mapping_rows": int(source_mapping.shape[0]), "input_17p_status": str(summary_17p.get("status", "")), "predicate_implementation_allowed": False, "executable_parity_implemented": False, "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY" if ok else "STOP_REVIEW_17Q_OUTPUTS"}
    write_json(out / "gold_v2_17q_medium_full_set_component_parity_source_mapping_summary.json", summary)
    report = ["# GOLD V2 17Q MEDIUM full-set component parity source mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17Q maps gap rows to required source artifact classes only.", "- It does not implement predicates, evaluate OHLC, create final signals, or enable live/external actions.", "- The next possible step is TIER2 row-level source mapping only.", "", "## Input audit", markdown_table(audit), "", "## Source mapping checks", markdown_table(mapping_checks), "", "## Component source mapping matrix", markdown_table(source_mapping), "", "## Source artifact requirements", markdown_table(source_requirements), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17P gap map carry-forward", markdown_table(gap_map), "", "## 17P planned stop conditions", markdown_table(planned_stops)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
