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

STEP = "18D_TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_18d_tier2_source_artifact_candidate_review_audit_only"
REPORT_NAME = "GOLD_V2_18D_TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "TIER2_SOURCE_ARTIFACT_CANDIDATE_REVIEW_STOPPED_AUDIT_ONLY"
EXPECTED_18C_STATUS = "TIER2_SOURCE_ARTIFACT_INVENTORY_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_tier2_source_artifact_inventory_summary.json"),
    "checks_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_inventory_checks.csv"),
    "inventory_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_tier2_source_artifact_inventory.csv"),
    "review_plan_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_candidate_review_plan.csv"),
    "next_gates_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_required_next_gates.csv"),
    "blockers_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_blockers.csv"),
    "safety_18c": ("gold_v2_18c_tier2_source_artifact_inventory_audit_only", "gold_v2_18c_safety_matrix.csv"),
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
        [["18D-BINPUT", "TIER2_HVT", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_18d_blockers.csv")
    write_json(out / "gold_v2_18d_tier2_source_artifact_candidate_review_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "source_recovery_executed": False, "implementation_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 18D TIER2 source artifact candidate review audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def review_classification(row: pd.Series) -> tuple[str, int, str]:
    name = str(row.get("filename", "")).lower()
    classification = str(row.get("classification", "")).lower()
    rel = str(row.get("relative_path", "")).lower()
    if "source_rows" in name:
        return "candidate_exact_source_rows_metadata", 1, "metadata indicates source rows"
    if "manifest_match" in name or "manifest_mismatch" in name or "final_manifest" in name:
        return "candidate_manifest_match_metadata", 2, "metadata indicates manifest matching rows"
    if "portfolio_ledger" in name:
        return "candidate_portfolio_ledger_metadata", 3, "metadata indicates portfolio ledger"
    if "reconciled_rule" in name or "rule_candidate" in name or "patch_preview" in name:
        return "candidate_rule_or_reconciled_metadata", 4, "metadata indicates reconciled/rule candidate"
    if classification == "lineage_related":
        return "supporting_lineage_metadata", 5, "lineage/supporting metadata only"
    if classification == "summary_chain_or_status_related" or "summary" in name:
        return "insufficient_summary_or_status_metadata", 99, "summary/status only is insufficient"
    if "tier2" in rel:
        return "other_supporting_metadata", 6, "other tier2-related metadata"
    return "other_supporting_metadata", 7, "other supporting metadata"


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_18d_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_18c = read_json(ip("summary_18c"))
    checks_18c = read_csv(ip("checks_18c"))
    inventory_18c = read_csv(ip("inventory_18c"))
    review_plan_18c = read_csv(ip("review_plan_18c"))
    next_gates_18c = read_csv(ip("next_gates_18c"))
    blockers_18c = read_csv(ip("blockers_18c"))
    safety_18c = read_csv(ip("safety_18c"))

    checks: list[list[Any]] = []
    add_check(checks, "18D-C001", "18C status", str(summary_18c.get("status", "")), EXPECTED_18C_STATUS)
    add_check(checks, "18D-C002", "18C inventory ready", bool_value(summary_18c.get("tier2_source_artifact_inventory_ready", False)), True)
    add_check(checks, "18D-C003", "18C inventory rows", int(summary_18c.get("inventory_rows", -1)), int(inventory_18c.shape[0]))
    add_check(checks, "18D-C004", "18C source recovery executed", bool_value(summary_18c.get("source_recovery_executed", False)), False)
    add_check(checks, "18D-C005", "18C checks STOP rows", int(checks_18c[checks_18c["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18D-C006", "18C safety STOP rows", int(safety_18c[safety_18c["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "18D-C007", "18C next gates include 18D", bool("18D" in set(next_gates_18c.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    for flag in ["implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "medium_live_evaluator_allowed", "final_signal_allowed"]:
        add_check(checks, f"18D-FLAG-18C-{flag}", f"18C {flag}", bool_value(summary_18c.get(flag, False)), False)
    external = summary_18c.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"18D-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "18D-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_18c.get("no_signal_discord_notified", False)), False)

    rows = []
    for _, row in inventory_18c.iterrows():
        review_class, priority, reason = review_classification(row)
        rows.append({
            **row.to_dict(),
            "review_classification": review_class,
            "review_priority": priority,
            "review_reason": reason,
            "content_inspection_allowed_now": False,
            "source_recovery_executed": False,
            "implementation_allowed": False,
            "medium_live_evaluator_allowed": False,
            "final_signal_allowed": False,
        })
    review_matrix = pd.DataFrame(rows).sort_values(["review_priority", "relative_path"]).reset_index(drop=True) if rows else pd.DataFrame()
    priority_candidates = review_matrix[review_matrix.get("review_priority", pd.Series(dtype=int)).astype(int).le(4)].copy() if not review_matrix.empty else pd.DataFrame()
    insufficient = review_matrix[review_matrix.get("review_classification", pd.Series(dtype=str)).astype(str).eq("insufficient_summary_or_status_metadata")].copy() if not review_matrix.empty else pd.DataFrame()
    add_check(checks, "18D-C008", "priority candidate rows non-negative", int(priority_candidates.shape[0]) >= 0, True)
    add_check(checks, "18D-C009", "content inspection allowed rows", int(review_matrix[review_matrix.get("content_inspection_allowed_now", pd.Series(dtype=bool)).map(bool_value)].shape[0]) if not review_matrix.empty else 0, 0)

    next_required = pd.DataFrame([
        ["18E", "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY", "Plan content inspection of selected candidate artifacts only.", True],
        ["18D_CONTENT_INSPECTION", "TIER2_CONTENT_INSPECTION_EXECUTION", "Blocked; 18D is metadata review only.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18d_success"])
    review_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["metadata_review_only", True, True, "PASS"],
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
    ok = review_checks[review_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = blockers_18c.copy()
    if not blockers.empty:
        blockers["carried_forward_by"] = STEP
        blockers["content_inspection_allowed_now"] = False
        blockers["source_recovery_executed"] = False
        blockers["implementation_allowed"] = False
        blockers["live_or_final_allowed"] = False
    write_csv(review_checks, out / "gold_v2_18d_candidate_review_checks.csv")
    write_csv(review_matrix, out / "gold_v2_18d_candidate_review_matrix.csv")
    write_csv(priority_candidates, out / "gold_v2_18d_priority_candidate_artifacts.csv")
    write_csv(insufficient, out / "gold_v2_18d_insufficient_artifacts.csv")
    write_csv(next_required, out / "gold_v2_18d_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_18d_blockers.csv")
    write_csv(safety, out / "gold_v2_18d_safety_matrix.csv")
    review_counts = review_matrix.groupby("review_classification").size().to_dict() if not review_matrix.empty else {}
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "candidate_review_ready": ok, "review_rows": int(review_matrix.shape[0]), "priority_candidate_rows": int(priority_candidates.shape[0]), "insufficient_rows": int(insufficient.shape[0]), "review_class_counts": {str(k): int(v) for k, v in review_counts.items()}, "content_inspection_allowed_now": False, "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18E_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_18D_OUTPUTS"}
    write_json(out / "gold_v2_18d_tier2_source_artifact_candidate_review_summary.json", summary)
    report = ["# GOLD V2 18D TIER2 source artifact candidate review audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18D reviews candidate artifact metadata only.", "- It does not inspect content, recover source identity, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Candidate review checks", markdown_table(review_checks), "", "## Candidate review matrix", markdown_table(review_matrix), "", "## Priority candidate artifacts", markdown_table(priority_candidates), "", "## Insufficient artifacts", markdown_table(insufficient), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 18C review plan carry-forward", markdown_table(review_plan_18c)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
