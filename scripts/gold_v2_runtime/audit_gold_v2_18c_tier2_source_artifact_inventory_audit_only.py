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

STEP = "18C_TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_18c_tier2_source_artifact_inventory_audit_only"
REPORT_NAME = "GOLD_V2_18C_TIER2_SOURCE_ARTIFACT_INVENTORY_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "TIER2_SOURCE_ARTIFACT_INVENTORY_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "TIER2_SOURCE_ARTIFACT_INVENTORY_STOPPED_AUDIT_ONLY"
EXPECTED_18B_STATUS = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_RECOVERY_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_tier2_row_level_source_identity_recovery_plan_summary.json"),
    "checks_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_recovery_plan_checks.csv"),
    "fields_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_required_identity_fields.csv"),
    "classes_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_allowed_source_artifact_classes.csv"),
    "validation_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_recovery_validation_criteria.csv"),
    "stops_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_stop_conditions.csv"),
    "next_gates_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_required_next_gates.csv"),
    "blockers_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_blockers.csv"),
    "safety_18b": ("gold_v2_18b_tier2_row_level_source_identity_recovery_plan_audit_only", "gold_v2_18b_safety_matrix.csv"),
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
        [["18C-BINPUT", "TIER2_HVT", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_18c_blockers.csv")
    write_json(out / "gold_v2_18c_tier2_source_artifact_inventory_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "source_recovery_executed": False, "implementation_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 18C TIER2 source artifact inventory audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def classify(path: Path) -> str:
    s = str(path).lower()
    name = path.name.lower()
    if "tier2" in s and ("ledger" in name or "source" in name or "identity" in name or "manifest" in name):
        return "tier2_candidate_related"
    if "13d" in s or "13l" in s or "lineage" in s:
        return "lineage_related"
    if "summary" in name and "tier2" in s:
        return "summary_chain_or_status_related"
    if "tier2" in s:
        return "tier2_related_other"
    return "other"


def inventory_fx_outputs(root: Path, out: Path) -> pd.DataFrame:
    rows = []
    ignore = {str(out.resolve()).lower()}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if any(str(path.resolve()).lower().startswith(x) for x in ignore):
                continue
        except Exception:
            pass
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        cls = classify(path)
        if cls == "other":
            continue
        stat = path.stat()
        rows.append({
            "path": str(path),
            "relative_path": rel,
            "filename": path.name,
            "suffix": path.suffix,
            "bytes": stat.st_size,
            "sha256": sha256_file(path),
            "classification": cls,
            "source_recovery_executed": False,
            "implementation_allowed": False,
            "medium_live_evaluator_allowed": False,
            "final_signal_allowed": False,
        })
    return pd.DataFrame(rows).sort_values(["classification", "relative_path"]).reset_index(drop=True) if rows else pd.DataFrame(columns=["path", "relative_path", "filename", "suffix", "bytes", "sha256", "classification", "source_recovery_executed", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_18c_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_18b = read_json(ip("summary_18b"))
    checks_18b = read_csv(ip("checks_18b"))
    fields_18b = read_csv(ip("fields_18b"))
    classes_18b = read_csv(ip("classes_18b"))
    validation_18b = read_csv(ip("validation_18b"))
    stops_18b = read_csv(ip("stops_18b"))
    next_gates_18b = read_csv(ip("next_gates_18b"))
    blockers_18b = read_csv(ip("blockers_18b"))
    safety_18b = read_csv(ip("safety_18b"))
    inventory = inventory_fx_outputs(fx_outputs(), out)

    checks: list[list[Any]] = []
    add_check(checks, "18C-C001", "18B status", str(summary_18b.get("status", "")), EXPECTED_18B_STATUS)
    add_check(checks, "18C-C002", "18B recovery plan ready", bool_value(summary_18b.get("tier2_recovery_plan_ready", False)), True)
    add_check(checks, "18C-C003", "18B required identity fields", int(summary_18b.get("required_identity_fields", -1)), 10)
    add_check(checks, "18C-C004", "18B allowed source artifact classes", int(summary_18b.get("allowed_source_artifact_classes", -1)), 5)
    add_check(checks, "18C-C005", "18B validation criteria", int(summary_18b.get("validation_criteria", -1)), 6)
    add_check(checks, "18C-C006", "18B source recovery executed", bool_value(summary_18b.get("source_recovery_executed", False)), False)
    add_check(checks, "18C-C007", "18B checks STOP rows", int(checks_18b[checks_18b["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18C-C008", "18B safety STOP rows", int(safety_18b[safety_18b["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18C-C009", "18B next gates include 18C", bool("18C" in set(next_gates_18b.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "18C-C010", "inventory rows non-negative", int(inventory.shape[0]) >= 0, True)
    for flag in ["implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"18C-FLAG-18B-{flag}", f"18B {flag}", bool_value(summary_18b.get(flag, False)), False)
    external = summary_18b.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"18C-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "18C-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_18b.get("no_signal_discord_notified", False)), False)

    review_plan = pd.DataFrame([
        [1, "Filter tier2_candidate_related artifacts", "inventory_only", False, False, False],
        [2, "Check whether exact row-level identity fields exist", "review_only", False, False, False],
        [3, "Reject summary-chain-only artifacts as insufficient", "review_only", False, False, False],
        [4, "Reject OHLC reconstruction or approximate reimplementation", "safety_only", False, False, False],
        [5, "Prepare 18D candidate review inputs", "planning_only", False, False, False],
    ], columns=["review_order", "review_item", "action_type", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    next_required = pd.DataFrame([
        ["18D", "TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY", "Review inventory candidates only; no recovery/reconstruction.", True],
        ["18C_RECOVERY_IMPL", "TIER2_SOURCE_RECOVERY_EXECUTION", "Blocked; 18C is inventory only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18c_success"])
    inventory_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["inventory_only", True, True, "PASS"],
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
    ok = inventory_checks[inventory_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = blockers_18b.copy()
    if not blockers.empty:
        blockers["carried_forward_by"] = STEP
        blockers["source_recovery_executed"] = False
        blockers["implementation_allowed"] = False
        blockers["live_or_final_allowed"] = False
    write_csv(inventory_checks, out / "gold_v2_18c_inventory_checks.csv")
    write_csv(inventory, out / "gold_v2_18c_tier2_source_artifact_inventory.csv")
    write_csv(review_plan, out / "gold_v2_18c_candidate_review_plan.csv")
    write_csv(next_required, out / "gold_v2_18c_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_18c_blockers.csv")
    write_csv(safety, out / "gold_v2_18c_safety_matrix.csv")
    class_counts = inventory.groupby("classification").size().to_dict() if not inventory.empty else {}
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "tier2_source_artifact_inventory_ready": ok, "inventory_rows": int(inventory.shape[0]), "inventory_class_counts": {str(k): int(v) for k, v in class_counts.items()}, "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18D_TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY" if ok else "STOP_REVIEW_18C_OUTPUTS"}
    write_json(out / "gold_v2_18c_tier2_source_artifact_inventory_summary.json", summary)
    report = ["# GOLD V2 18C TIER2 source artifact inventory audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18C inventories candidate source artifacts only.", "- It does not recover source identity, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Inventory checks", markdown_table(inventory_checks), "", "## TIER2 source artifact inventory", markdown_table(inventory), "", "## Candidate review plan", markdown_table(review_plan), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 18B required fields carry-forward", markdown_table(fields_18b), "", "## 18B source classes carry-forward", markdown_table(classes_18b), "", "## 18B validation carry-forward", markdown_table(validation_18b), "", "## 18B stop conditions carry-forward", markdown_table(stops_18b)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
