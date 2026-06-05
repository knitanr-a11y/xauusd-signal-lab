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

STEP = "18F_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only"
REPORT_NAME = "GOLD_V2_18F_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_READY_AUDIT_ONLY_CONTENT_INSPECTION_BLOCKED"
STOP_STATUS = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_STOPPED_AUDIT_ONLY"
EXPECTED_18E_STATUS = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_tier2_source_artifact_content_inspection_plan_summary.json"),
    "checks_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_content_inspection_plan_checks.csv"),
    "selected_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_selected_priority_artifacts.csv"),
    "plan_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_content_inspection_plan.csv"),
    "fields_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_required_identity_validation_fields.csv"),
    "stops_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_stop_conditions.csv"),
    "next_gates_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_required_next_gates.csv"),
    "blockers_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_blockers.csv"),
    "safety_18e": ("gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only", "gold_v2_18e_safety_matrix.csv"),
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
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        [["18F-BINPUT", "TIER2_HVT", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_18f_blockers.csv")
    write_json(out / "gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "content_inspection_authorized": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 18F TIER2 source artifact content inspection authorization gate audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_18f_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_18e = read_json(ip("summary_18e"))
    checks_18e = read_csv(ip("checks_18e"))
    selected_18e = read_csv(ip("selected_18e"))
    plan_18e = read_csv(ip("plan_18e"))
    fields_18e = read_csv(ip("fields_18e"))
    stops_18e = read_csv(ip("stops_18e"))
    next_gates_18e = read_csv(ip("next_gates_18e"))
    blockers_18e = read_csv(ip("blockers_18e"))
    safety_18e = read_csv(ip("safety_18e"))

    checks: list[list[Any]] = []
    add_check(checks, "18F-C001", "18E status", str(summary_18e.get("status", "")), EXPECTED_18E_STATUS)
    add_check(checks, "18F-C002", "18E plan ready", bool_value(summary_18e.get("content_inspection_plan_ready", False)), True)
    add_check(checks, "18F-C003", "18E selected priority artifacts", int(summary_18e.get("selected_priority_artifacts", -1)), int(selected_18e.shape[0]))
    add_check(checks, "18F-C004", "18E inspection plan rows", int(summary_18e.get("inspection_plan_rows", -1)), int(plan_18e.shape[0]))
    add_check(checks, "18F-C005", "18E content inspection allowed now", bool_value(summary_18e.get("content_inspection_allowed_now", False)), False)
    add_check(checks, "18F-C006", "18E source recovery executed", bool_value(summary_18e.get("source_recovery_executed", False)), False)
    add_check(checks, "18F-C007", "18E checks STOP rows", int(checks_18e[checks_18e["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18F-C008", "18E safety STOP rows", int(safety_18e[safety_18e["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18F-C009", "18E next gates include 18F", bool("18F" in set(next_gates_18e.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    for flag in ["implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"18F-FLAG-18E-{flag}", f"18E {flag}", bool_value(summary_18e.get(flag, False)), False)
    external = summary_18e.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"18F-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "18F-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_18e.get("no_signal_discord_notified", False)), False)

    authorization = pd.DataFrame([
        ["AUTH-CONTENT-INSPECTION", "TIER2 content inspection execution", "BLOCKED", False, "explicit approval required before 18G", False, False, False],
        ["AUTH-SOURCE-RECOVERY", "TIER2 row-level source identity recovery", "BLOCKED", False, "requires successful authorized content inspection first", False, False, False],
        ["AUTH-PREDICATE-IMPLEMENTATION", "predicate implementation", "BLOCKED", False, "requires source recovery and separate implementation approval", False, False, False],
        ["AUTH-LIVE-FINAL", "live/final signal path", "BLOCKED", False, "requires parity gates and explicit live/final approval", False, False, False],
        ["AUTH-EXTERNAL", "Discord/MT5/AI/live hook", "BLOCKED", False, "requires explicit external action approval", False, False, False],
    ], columns=["authorization_id", "scope", "authorization_status", "content_inspection_authorized", "required_resolution", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    blocked_execution = plan_18e.copy()
    if not blocked_execution.empty:
        blocked_execution["execution_status"] = "BLOCKED_AWAIT_EXPLICIT_APPROVAL"
        blocked_execution["content_inspection_authorized"] = False
        blocked_execution["source_recovery_executed"] = False
        blocked_execution["implementation_allowed"] = False
        blocked_execution["final_signal_allowed"] = False
    next_required = pd.DataFrame([
        ["AWAIT_APPROVAL", "AWAIT_EXPLICIT_TIER2_CONTENT_INSPECTION_APPROVAL", "No execution step is allowed until explicit approval is provided.", True],
        ["18G", "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTION_AUDIT_ONLY", "Blocked unless explicit approval is separately provided.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18f_success"])
    add_check(checks, "18F-C010", "authorized content inspection rows", int(authorization[authorization["content_inspection_authorized"].map(bool_value)].shape[0]), 0)
    add_check(checks, "18F-C011", "blocked execution rows", int(blocked_execution.shape[0]), int(plan_18e.shape[0]))
    gate_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["authorization_gate_only", True, True, "PASS"],
        ["content_inspection_authorized", False, False, "PASS"],
        ["content_inspection_executed", False, False, "PASS"],
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
    ok = gate_checks[gate_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = blockers_18e.copy()
    if not blockers.empty:
        blockers["carried_forward_by"] = STEP
        blockers["content_inspection_authorized"] = False
        blockers["source_recovery_executed"] = False
        blockers["implementation_allowed"] = False
        blockers["live_or_final_allowed"] = False
    write_csv(gate_checks, out / "gold_v2_18f_authorization_gate_checks.csv")
    write_csv(authorization, out / "gold_v2_18f_authorization_matrix.csv")
    write_csv(blocked_execution, out / "gold_v2_18f_blocked_execution_plan.csv")
    write_csv(next_required, out / "gold_v2_18f_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_18f_blockers.csv")
    write_csv(safety, out / "gold_v2_18f_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "authorization_gate_ready": ok, "selected_priority_artifacts": int(selected_18e.shape[0]), "blocked_execution_rows": int(blocked_execution.shape[0]), "content_inspection_authorized": False, "content_inspection_executed": False, "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "AWAIT_EXPLICIT_TIER2_CONTENT_INSPECTION_APPROVAL" if ok else "STOP_REVIEW_18F_OUTPUTS"}
    write_json(out / "gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_summary.json", summary)
    report = ["# GOLD V2 18F TIER2 source artifact content inspection authorization gate audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18F records the authorization gate only.", "- Content inspection remains blocked because no explicit approval artifact/command is provided.", "- It does not inspect content, recover source identity, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Authorization gate checks", markdown_table(gate_checks), "", "## Authorization matrix", markdown_table(authorization), "", "## Blocked execution plan", markdown_table(blocked_execution), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 18E selected artifacts carry-forward", markdown_table(selected_18e), "", "## 18E required fields carry-forward", markdown_table(fields_18e), "", "## 18E stop conditions carry-forward", markdown_table(stops_18e)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
