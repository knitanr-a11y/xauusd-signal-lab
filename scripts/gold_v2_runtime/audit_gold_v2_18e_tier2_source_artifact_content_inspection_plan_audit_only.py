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

STEP = "18E_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_18e_tier2_source_artifact_content_inspection_plan_audit_only"
REPORT_NAME = "GOLD_V2_18E_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_18D_STATUS = "TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_tier2_source_artifact_candidate_review_summary.json"),
    "checks_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_candidate_review_checks.csv"),
    "review_matrix_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_candidate_review_matrix.csv"),
    "priority_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_priority_candidate_artifacts.csv"),
    "insufficient_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_insufficient_artifacts.csv"),
    "next_gates_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_required_next_gates.csv"),
    "blockers_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_blockers.csv"),
    "safety_18d": ("gold_v2_18d_tier2_source_artifact_candidate_review_audit_only", "gold_v2_18d_safety_matrix.csv"),
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
        [["18E-BINPUT", "TIER2_HVT", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_18e_blockers.csv")
    write_json(out / "gold_v2_18e_tier2_source_artifact_content_inspection_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "content_inspection_allowed_now": False, "source_recovery_executed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 18E TIER2 source artifact content inspection plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def inspection_method(suffix: str) -> str:
    s = str(suffix).lower()
    if s == ".csv":
        return "read_csv_header_and_schema_only_in_future_authorized_step"
    if s == ".json":
        return "read_json_keys_only_in_future_authorized_step"
    if s == ".zip":
        return "list_zip_members_only_in_future_authorized_step"
    if s == ".md":
        return "read_markdown_metadata_only_in_future_authorized_step"
    return "read_only_metadata_first_in_future_authorized_step"


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_18e_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_18d = read_json(ip("summary_18d"))
    checks_18d = read_csv(ip("checks_18d"))
    review_matrix_18d = read_csv(ip("review_matrix_18d"))
    priority_18d = read_csv(ip("priority_18d"))
    insufficient_18d = read_csv(ip("insufficient_18d"))
    next_gates_18d = read_csv(ip("next_gates_18d"))
    blockers_18d = read_csv(ip("blockers_18d"))
    safety_18d = read_csv(ip("safety_18d"))

    checks: list[list[Any]] = []
    add_check(checks, "18E-C001", "18D status", str(summary_18d.get("status", "")), EXPECTED_18D_STATUS)
    add_check(checks, "18E-C002", "18D candidate review ready", bool_value(summary_18d.get("candidate_review_ready", False)), True)
    add_check(checks, "18E-C003", "18D review rows", int(summary_18d.get("review_rows", -1)), int(review_matrix_18d.shape[0]))
    add_check(checks, "18E-C004", "18D priority candidate rows", int(summary_18d.get("priority_candidate_rows", -1)), int(priority_18d.shape[0]))
    add_check(checks, "18E-C005", "18D insufficient rows", int(summary_18d.get("insufficient_rows", -1)), int(insufficient_18d.shape[0]))
    add_check(checks, "18E-C006", "18D content inspection allowed now", bool_value(summary_18d.get("content_inspection_allowed_now", False)), False)
    add_check(checks, "18E-C007", "18D source recovery executed", bool_value(summary_18d.get("source_recovery_executed", False)), False)
    add_check(checks, "18E-C008", "18D checks STOP rows", int(checks_18d[checks_18d["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18E-C009", "18D safety STOP rows", int(safety_18d[safety_18d["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18E-C010", "18D next gates include 18E", bool("18E" in set(next_gates_18d.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    for flag in ["implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"18E-FLAG-18D-{flag}", f"18D {flag}", bool_value(summary_18d.get(flag, False)), False)
    external = summary_18d.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"18E-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "18E-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_18d.get("no_signal_discord_notified", False)), False)

    selected = priority_18d.copy()
    if not selected.empty:
        selected = selected.sort_values(["review_priority", "relative_path"]).reset_index(drop=True)
        selected.insert(0, "planned_inspection_order", range(1, len(selected) + 1))
        selected["content_inspection_allowed_now"] = False
        selected["source_recovery_executed"] = False
        selected["implementation_allowed"] = False
        selected["medium_live_evaluator_allowed"] = False
        selected["final_signal_allowed"] = False
    plan_rows = []
    for _, row in selected.iterrows():
        plan_rows.append({
            "planned_inspection_order": int(row["planned_inspection_order"]),
            "relative_path": row.get("relative_path", ""),
            "filename": row.get("filename", ""),
            "review_classification": row.get("review_classification", ""),
            "review_priority": row.get("review_priority", ""),
            "planned_method": inspection_method(row.get("suffix", "")),
            "planned_scope": "content_inspection_plan_only_no_execution",
            "content_inspection_allowed_now": False,
            "source_recovery_executed": False,
            "implementation_allowed": False,
            "medium_live_evaluator_allowed": False,
            "final_signal_allowed": False,
        })
    inspection_plan = pd.DataFrame(plan_rows)
    required_fields = pd.DataFrame([
        ["manifest_row_id", "required", "must identify unique TIER2 row", False, False, False],
        ["component", "required", "must equal TIER2_HVT", False, False, False],
        ["source_identity_type", "required", "must be row-level source identity", False, False, False],
        ["source_role", "required", "must identify ledger/rule/source role", False, False, False],
        ["source_row_number_1based", "required", "must map to exact row number", False, False, False],
        ["source_key", "required", "must identify candidate key/time/direction", False, False, False],
        ["source_row_hash", "required", "must be reproducible", False, False, False],
        ["strategy_id", "required", "must map to TIER2_HVT", False, False, False],
        ["source_status", "required", "must be audited source status", False, False, False],
    ], columns=["field", "requirement_status", "validation_rule", "content_inspection_allowed_now", "implementation_allowed", "final_signal_allowed"])
    stops = pd.DataFrame([
        ["18E-S001", "attempt to inspect contents during 18E", "STOP"],
        ["18E-S002", "attempt to recover TIER2 row-level identity during 18E", "STOP"],
        ["18E-S003", "attempt to reconstruct from OHLC or approximate implementation", "STOP"],
        ["18E-S004", "attempt to enable implementation/OHLC replay/live/final/external action", "STOP"],
        ["18E-S005", "priority candidate list missing despite 18D priority candidates", "STOP"],
        ["18E-S006", "NO_SIGNAL Discord notification true", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_required = pd.DataFrame([
        ["18F", "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY", "Authorization gate before any content inspection execution.", True],
        ["18E_CONTENT_INSPECTION", "TIER2_CONTENT_INSPECTION_EXECUTION", "Blocked; 18E is planning only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18e_success"])
    add_check(checks, "18E-C011", "inspection plan rows", int(inspection_plan.shape[0]), int(priority_18d.shape[0]))
    add_check(checks, "18E-C012", "content inspection allowed rows", int(inspection_plan[inspection_plan.get("content_inspection_allowed_now", pd.Series(dtype=bool)).map(bool_value)].shape[0]) if not inspection_plan.empty else 0, 0)

    plan_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["content_inspection_plan_only", True, True, "PASS"],
        ["content_inspection_allowed_now", False, False, "PASS"],
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
    ok = plan_checks[plan_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = blockers_18d.copy()
    if not blockers.empty:
        blockers["carried_forward_by"] = STEP
        blockers["content_inspection_allowed_now"] = False
        blockers["source_recovery_executed"] = False
        blockers["implementation_allowed"] = False
        blockers["live_or_final_allowed"] = False
    write_csv(plan_checks, out / "gold_v2_18e_content_inspection_plan_checks.csv")
    write_csv(selected, out / "gold_v2_18e_selected_priority_artifacts.csv")
    write_csv(inspection_plan, out / "gold_v2_18e_content_inspection_plan.csv")
    write_csv(required_fields, out / "gold_v2_18e_required_identity_validation_fields.csv")
    write_csv(stops, out / "gold_v2_18e_stop_conditions.csv")
    write_csv(next_required, out / "gold_v2_18e_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_18e_blockers.csv")
    write_csv(safety, out / "gold_v2_18e_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "content_inspection_plan_ready": ok, "selected_priority_artifacts": int(selected.shape[0]), "inspection_plan_rows": int(inspection_plan.shape[0]), "content_inspection_allowed_now": False, "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18F_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_AUDIT_ONLY" if ok else "STOP_REVIEW_18E_OUTPUTS"}
    write_json(out / "gold_v2_18e_tier2_source_artifact_content_inspection_plan_summary.json", summary)
    report = ["# GOLD V2 18E TIER2 source artifact content inspection plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18E plans content inspection only.", "- It does not inspect content, recover source identity, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Content inspection plan checks", markdown_table(plan_checks), "", "## Selected priority artifacts", markdown_table(selected), "", "## Content inspection plan", markdown_table(inspection_plan), "", "## Required identity validation fields", markdown_table(required_fields), "", "## Stop conditions", markdown_table(stops), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 18D insufficient carry-forward", markdown_table(insufficient_18d)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
