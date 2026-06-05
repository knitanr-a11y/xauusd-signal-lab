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

STEP = "18B_TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only"
REPORT_NAME = "GOLD_V2_18B_TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_18A_STATUS = "EXECUTABLE_PARITY_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_executable_parity_design_summary.json"),
    "checks_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_design_checks.csv"),
    "component_design_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_component_parity_design_matrix.csv"),
    "acceptance_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_acceptance_criteria.csv"),
    "stops_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_stop_conditions.csv"),
    "next_gates_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_required_next_gates.csv"),
    "blockers_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_blockers.csv"),
    "safety_18a": ("gold_v2_18a_executable_parity_design_audit_only", "gold_v2_18a_safety_matrix.csv"),
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
        [["18B-BINPUT", "TIER2_HVT", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_18b_blockers.csv")
    write_json(out / "gold_v2_18b_tier2_row_level_source_identity_recovery_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "implementation_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 18B TIER2 row-level source identity recovery plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_18b_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_18a = read_json(ip("summary_18a"))
    checks_18a = read_csv(ip("checks_18a"))
    component_design_18a = read_csv(ip("component_design_18a"))
    acceptance_18a = read_csv(ip("acceptance_18a"))
    stops_18a = read_csv(ip("stops_18a"))
    next_gates_18a = read_csv(ip("next_gates_18a"))
    blockers_18a = read_csv(ip("blockers_18a"))
    safety_18a = read_csv(ip("safety_18a"))

    tier2_blockers = blockers_18a[blockers_18a.astype(str).apply(lambda r: r.str.contains("TIER2", case=False, na=False).any(), axis=1)].copy()
    checks: list[list[Any]] = []
    add_check(checks, "18B-C001", "18A status", str(summary_18a.get("status", "")), EXPECTED_18A_STATUS)
    add_check(checks, "18B-C002", "18A design ready", bool_value(summary_18a.get("executable_parity_design_ready", False)), True)
    add_check(checks, "18B-C003", "18A component design rows", int(summary_18a.get("component_design_rows", -1)), 4)
    add_check(checks, "18B-C004", "18A blockers carried", int(summary_18a.get("open_blockers_carried_forward", -1)), 4)
    add_check(checks, "18B-C005", "18A checks STOP rows", int(checks_18a[checks_18a["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18B-C006", "18A safety STOP rows", int(safety_18a[safety_18a["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18B-C007", "18A next gates include 18B", bool("18B" in set(next_gates_18a.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "18B-C008", "TIER2 blocker carried", int(tier2_blockers.shape[0]) >= 1, True)
    for flag in ["implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"18B-FLAG-18A-{flag}", f"18A {flag}", bool_value(summary_18a.get(flag, False)), False)
    external = summary_18a.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"18B-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "18B-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_18a.get("no_signal_discord_notified", False)), False)

    required_fields = pd.DataFrame([
        ["manifest_row_id", "unique TIER2 row identifier", "required", False, False, False],
        ["component", "must equal TIER2_HVT", "required", False, False, False],
        ["source_step", "audited source step that produced the row", "required", False, False, False],
        ["source_identity_type", "must be row-level identity, not summary-chain only", "required", False, False, False],
        ["source_role", "source table role such as ledger/rule row", "required", False, False, False],
        ["source_row_number_1based", "1-based row number in audited source artifact", "required", False, False, False],
        ["source_key", "candidate key/time/direction identity", "required", False, False, False],
        ["source_row_hash", "hash of exact audited row", "required", False, False, False],
        ["strategy_id", "must map to TIER2_HVT", "required", False, False, False],
        ["source_status", "source audit status", "required", False, False, False],
    ], columns=["field", "meaning", "requirement_status", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    source_classes = pd.DataFrame([
        ["audited_tier2_candidate_source_ledger", "preferred", "must be existing audited artifact; no approximation", False, False, False],
        ["audited_tier2_rule_source_row", "allowed", "must identify one exact source row", False, False, False],
        ["audited_13d_13l_lineage_artifact", "allowed_for_lineage_only", "cannot substitute for row-level identity", False, False, False],
        ["reconstructed_from_ohlc", "forbidden", "near/approx reimplementation is prohibited", False, False, False],
        ["summary_chain_reference_only", "insufficient", "current state; not executable parity ready", False, False, False],
    ], columns=["source_artifact_class", "classification", "rule", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    validation = pd.DataFrame([
        ["VAL-EXISTS", "source artifact exists and is audited", "required", False, False, False],
        ["VAL-UNIQUE", "exactly one TIER2_HVT row maps to the recovered identity", "required", False, False, False],
        ["VAL-ROW-HASH", "source row hash is reproducible from the source row", "required", False, False, False],
        ["VAL-KEY", "source_key matches manifest/candidate identity", "required", False, False, False],
        ["VAL-NO-APPROX", "no OHLC rediscovery or approximate reconstruction used", "required", False, False, False],
        ["VAL-SAFETY", "live/final/external action flags remain false", "required", False, False, False],
    ], columns=["validation_id", "validation_rule", "requirement_status", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    stops = pd.DataFrame([
        ["18B-S001", "attempt to recover or reconstruct source in 18B", "STOP"],
        ["18B-S002", "attempt to use OHLC rediscovery or approximate source", "STOP"],
        ["18B-S003", "multiple or missing TIER2 source candidates", "STOP"],
        ["18B-S004", "source row hash/key cannot be reproduced", "STOP"],
        ["18B-S005", "attempt to enable implementation/OHLC replay/live/final/external action", "STOP"],
        ["18B-S006", "NO_SIGNAL Discord notification true", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_required = pd.DataFrame([
        ["18C", "TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY", "Inventory possible audited TIER2 source artifacts only; no reconstruction.", True],
        ["18B_RECOVERY_IMPL", "TIER2_SOURCE_RECOVERY_EXECUTION", "Blocked; 18B is planning only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18b_success"])
    recovery_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["recovery_plan_only", True, True, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
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
    ok = recovery_checks[recovery_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = blockers_18a.copy()
    if not blockers.empty:
        blockers["carried_forward_by"] = STEP
        blockers["source_recovery_executed"] = False
        blockers["implementation_allowed"] = False
        blockers["live_or_final_allowed"] = False
    write_csv(recovery_checks, out / "gold_v2_18b_recovery_plan_checks.csv")
    write_csv(required_fields, out / "gold_v2_18b_required_identity_fields.csv")
    write_csv(source_classes, out / "gold_v2_18b_allowed_source_artifact_classes.csv")
    write_csv(validation, out / "gold_v2_18b_recovery_validation_criteria.csv")
    write_csv(stops, out / "gold_v2_18b_stop_conditions.csv")
    write_csv(next_required, out / "gold_v2_18b_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_18b_blockers.csv")
    write_csv(safety, out / "gold_v2_18b_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "tier2_recovery_plan_ready": ok, "required_identity_fields": int(required_fields.shape[0]), "allowed_source_artifact_classes": int(source_classes.shape[0]), "validation_criteria": int(validation.shape[0]), "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18C_TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY" if ok else "STOP_REVIEW_18B_OUTPUTS"}
    write_json(out / "gold_v2_18b_tier2_row_level_source_identity_recovery_plan_summary.json", summary)
    report = ["# GOLD V2 18B TIER2 row-level source identity recovery plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18B writes a TIER2 row-level source identity recovery plan only.", "- It does not recover sources, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Recovery plan checks", markdown_table(recovery_checks), "", "## Required identity fields", markdown_table(required_fields), "", "## Allowed source artifact classes", markdown_table(source_classes), "", "## Recovery validation criteria", markdown_table(validation), "", "## Stop conditions", markdown_table(stops), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 18A component design carry-forward", markdown_table(component_design_18a), "", "## 18A acceptance carry-forward", markdown_table(acceptance_18a), "", "## 18A stop conditions carry-forward", markdown_table(stops_18a)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
