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

STEP = "18A_EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_18a_executable_parity_design_audit_only"
REPORT_NAME = "GOLD_V2_18A_EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "EXECUTABLE_PARITY_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "EXECUTABLE_PARITY_DESIGN_STOPPED_AUDIT_ONLY"
EXPECTED_17W_STATUS = "MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATED_LIVE_BLOCKED"
INPUTS = {
    "summary_17w": ("gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation", "gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation_summary.json"),
    "checks_17w": ("gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation", "gold_v2_17w_consolidation_checks.csv"),
    "roadmap_17w": ("gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation", "gold_v2_17w_roadmap_matrix.csv"),
    "blockers_17w": ("gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation", "gold_v2_17w_open_blockers_consolidated.csv"),
    "next_gates_17w": ("gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation", "gold_v2_17w_required_next_gates.csv"),
    "safety_17w": ("gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation", "gold_v2_17w_safety_matrix.csv"),
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
        [["18A-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_18a_blockers.csv")
    write_json(out / "gold_v2_18a_executable_parity_design_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "implementation_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 18A executable parity design audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_18a_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17w = read_json(ip("summary_17w"))
    checks_17w = read_csv(ip("checks_17w"))
    roadmap_17w = read_csv(ip("roadmap_17w"))
    blockers_17w = read_csv(ip("blockers_17w"))
    next_gates_17w = read_csv(ip("next_gates_17w"))
    safety_17w = read_csv(ip("safety_17w"))

    checks: list[list[Any]] = []
    add_check(checks, "18A-C001", "17W status", str(summary_17w.get("status", "")), EXPECTED_17W_STATUS)
    add_check(checks, "18A-C002", "17W roadmap consolidated", bool_value(summary_17w.get("roadmap_consolidated", False)), True)
    add_check(checks, "18A-C003", "17W roadmap items", int(summary_17w.get("roadmap_items", -1)), 5)
    add_check(checks, "18A-C004", "17W open blockers", int(summary_17w.get("open_blockers", -1)), 4)
    add_check(checks, "18A-C005", "17W enabled safety gates", int(summary_17w.get("enabled_safety_gates_now", -1)), 0)
    add_check(checks, "18A-C006", "17W checks STOP rows", int(checks_17w[checks_17w["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18A-C007", "17W safety STOP rows", int(safety_17w[safety_17w["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18A-C008", "17W next gates include 18A", bool("18A" in set(next_gates_17w.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "18A-C009", "17W implementation allowed", bool_value(summary_17w.get("implementation_allowed", False)), False)
    add_check(checks, "18A-C010", "17W live enabled", bool_value(summary_17w.get("live_enabled", False)), False)
    add_check(checks, "18A-C011", "17W final signal allowed", bool_value(summary_17w.get("final_signal_allowed", False)), False)
    external = summary_17w.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"18A-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "18A-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_17w.get("no_signal_discord_notified", False)), False)

    component_design = pd.DataFrame([
        ["TIER2_HVT", "row_level_source_identity", "required_before_executable_parity", "missing_confirmed", "design_only", False, False, False],
        ["RANGE96_REFINED", "predicate_parity_contract", "required_before_implementation", "source_mapping_ready_not_implemented", "design_only", False, False, False],
        ["VOL_TRMEAN32_REFINED", "predicate_parity_contract", "required_before_implementation", "source_mapping_ready_not_implemented", "design_only", False, False, False],
        ["MEDIUM_FULL_SET", "component_integration_contract", "required_before_arbitration", "not_started", "design_only", False, False, False],
    ], columns=["component", "design_area", "requirement", "current_status", "action_type", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    arbitration_design = pd.DataFrame([
        [1, "Define component input contract", "TIER2/RANGE96/VOL candidate identity and predicate outputs", "design_only", False, False, False],
        [2, "Define tie-break and arbitration order", "MEDIUM full-set candidate ordering", "design_only", False, False, False],
        [3, "Define replay comparison keys", "source row hash/key/component/time/direction", "design_only", False, False, False],
        [4, "Define acceptance thresholds", "exact count/key/status parity first", "design_only", False, False, False],
        [5, "Define hard stop gates", "missing TIER2 source identity or predicate mismatch", "design_only", False, False, False],
    ], columns=["design_order", "design_item", "scope", "action_type", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    acceptance = pd.DataFrame([
        ["AC-COUNT", "component and full-set row counts match audited manifest", "required", False, False, False],
        ["AC-KEY", "candidate keys match audited source rows", "required", False, False, False],
        ["AC-HASH", "source row hashes match audited artifacts", "required", False, False, False],
        ["AC-STATUS", "NO_SIGNAL/live/final status remains blocked unless approved", "required", False, False, False],
        ["AC-SAFETY", "Discord/MT5/AI/live hook remain false", "required", False, False, False],
    ], columns=["criteria_id", "criteria", "requirement_status", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    stops = pd.DataFrame([
        ["18A-S001", "attempt to implement predicate/arbitration", "STOP"],
        ["18A-S002", "attempt to evaluate OHLC or run replay", "STOP"],
        ["18A-S003", "attempt to enable live/final/external action", "STOP"],
        ["18A-S004", "missing 17W safety or blocker carry-forward", "STOP"],
        ["18A-S005", "NO_SIGNAL Discord notification true", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_required = pd.DataFrame([
        ["18B", "TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY", "Plan TIER2 row-level source identity recovery only.", True],
        ["18A_IMPL", "EXECUTABLE_PARITY_IMPLEMENTATION", "Blocked; 18A is design only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18a_success"])
    design_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["design_only", True, True, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = design_checks[design_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = blockers_17w.copy()
    if not blockers.empty:
        blockers["carried_forward_by"] = STEP
        blockers["implementation_allowed"] = False
        blockers["live_or_final_allowed"] = False
    write_csv(design_checks, out / "gold_v2_18a_design_checks.csv")
    write_csv(component_design, out / "gold_v2_18a_component_parity_design_matrix.csv")
    write_csv(arbitration_design, out / "gold_v2_18a_arbitration_design_matrix.csv")
    write_csv(acceptance, out / "gold_v2_18a_acceptance_criteria.csv")
    write_csv(stops, out / "gold_v2_18a_stop_conditions.csv")
    write_csv(next_required, out / "gold_v2_18a_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_18a_blockers.csv")
    write_csv(safety, out / "gold_v2_18a_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "executable_parity_design_ready": ok, "component_design_rows": int(component_design.shape[0]), "arbitration_design_rows": int(arbitration_design.shape[0]), "acceptance_criteria_rows": int(acceptance.shape[0]), "open_blockers_carried_forward": int(blockers.shape[0]), "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18B_TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_18A_OUTPUTS"}
    write_json(out / "gold_v2_18a_executable_parity_design_summary.json", summary)
    report = ["# GOLD V2 18A executable parity design audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18A writes executable parity design requirements only.", "- It does not implement predicates/arbitration, run OHLC replay, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Design checks", markdown_table(design_checks), "", "## Component parity design matrix", markdown_table(component_design), "", "## Arbitration design matrix", markdown_table(arbitration_design), "", "## Acceptance criteria", markdown_table(acceptance), "", "## Stop conditions", markdown_table(stops), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17W roadmap carry-forward", markdown_table(roadmap_17w)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
