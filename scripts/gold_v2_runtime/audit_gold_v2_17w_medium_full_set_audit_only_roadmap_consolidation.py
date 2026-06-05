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

STEP = "17W_MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION"
OUT_DIR_NAME = "gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation"
REPORT_NAME = "GOLD_V2_17W_MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATED_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_AUDIT_ONLY_ROADMAP_CONSOLIDATION_STOPPED"
EXPECTED_17V_STATUS = "LIVE_PARITY_SAFETY_GATE_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
INPUTS = {
    "summary_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_live_parity_safety_gate_plan_summary.json"),
    "checks_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_safety_gate_plan_checks.csv"),
    "gate_matrix_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_live_safety_gate_matrix.csv"),
    "non_enablement_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_non_enablement_matrix.csv"),
    "next_gates_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_required_next_gates.csv"),
    "blockers_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_blockers.csv"),
    "safety_17v": ("gold_v2_17v_live_parity_safety_gate_plan_audit_only", "gold_v2_17v_safety_matrix.csv"),
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
        [["17W-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17w_open_blockers_consolidated.csv")
    write_json(out / "gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17W MEDIUM full-set audit-only roadmap consolidation report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17w_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17v = read_json(ip("summary_17v"))
    checks_17v = read_csv(ip("checks_17v"))
    gate_matrix_17v = read_csv(ip("gate_matrix_17v"))
    non_enablement_17v = read_csv(ip("non_enablement_17v"))
    next_gates_17v = read_csv(ip("next_gates_17v"))
    blockers_17v = read_csv(ip("blockers_17v"))
    safety_17v = read_csv(ip("safety_17v"))

    checks: list[list[Any]] = []
    add_check(checks, "17W-C001", "17V status", str(summary_17v.get("status", "")), EXPECTED_17V_STATUS)
    add_check(checks, "17W-C002", "17V safety gate plan ready", bool_value(summary_17v.get("live_parity_safety_gate_plan_ready", False)), True)
    add_check(checks, "17W-C003", "17V planned safety gates", int(summary_17v.get("planned_safety_gates", -1)), 11)
    add_check(checks, "17W-C004", "17V enabled safety gates now", int(summary_17v.get("enabled_safety_gates_now", -1)), 0)
    add_check(checks, "17W-C005", "17V live enabled", bool_value(summary_17v.get("live_enabled", False)), False)
    add_check(checks, "17W-C006", "17V final signal allowed", bool_value(summary_17v.get("final_signal_allowed", False)), False)
    add_check(checks, "17W-C007", "17V checks STOP rows", int(checks_17v[checks_17v["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17W-C008", "17V non-enablement STOP rows", int(non_enablement_17v[non_enablement_17v["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17W-C009", "17V safety STOP rows", int(safety_17v[safety_17v["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17W-C010", "17V next gates include 17W", bool("17W" in set(next_gates_17v.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "17W-C011", "enabled gate matrix rows", int(gate_matrix_17v[gate_matrix_17v["gate_enabled_now"].map(bool_value)].shape[0]) if "gate_enabled_now" in gate_matrix_17v.columns else -1, 0)
    external = summary_17v.get("external_actions", {}) or {}
    for flag in ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]:
        add_check(checks, f"17W-EXT-{flag}", flag, bool_value(external.get(flag, False)), False)
    add_check(checks, "17W-NO-SIGNAL", "no_signal_discord_notified", bool_value(summary_17v.get("no_signal_discord_notified", False)), False)

    roadmap = pd.DataFrame([
        [1, "Resolve TIER2 row-level source identity", "TIER2_HVT", "open_hard_blocker", "audit_only", False, False, False],
        [2, "Design component executable parity", "RANGE96_REFINED/VOL_TRMEAN32_REFINED/TIER2_HVT", "not_started", "design_only", False, False, False],
        [3, "Design MEDIUM arbitration replay parity", "MEDIUM_FULL_SET", "not_started", "design_only", False, False, False],
        [4, "Re-run safety-gate planning after parity design", "SAFETY", "not_started", "planning_only", False, False, False],
        [5, "Keep live/final/external actions disabled", "SAFETY", "active_block", "safety_only", False, False, False],
    ], columns=["roadmap_order", "roadmap_item", "scope", "current_status", "action_type", "implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    open_blockers = blockers_17v.copy()
    if not open_blockers.empty:
        open_blockers["carried_forward_by"] = STEP
        open_blockers["live_or_final_allowed"] = False
    next_required = pd.DataFrame([
        ["18A", "EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY", "Design executable parity requirements only; no implementation/OHLC/live/final.", True],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until parity and safety gates pass.", False],
        ["FINAL", "MEDIUM_FULL_SET_FINAL_SIGNAL", "Blocked until explicit final authorization.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17w_success"])
    consolidation_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["roadmap_consolidation_only", True, True, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = consolidation_checks[consolidation_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    write_csv(consolidation_checks, out / "gold_v2_17w_consolidation_checks.csv")
    write_csv(roadmap, out / "gold_v2_17w_roadmap_matrix.csv")
    write_csv(open_blockers, out / "gold_v2_17w_open_blockers_consolidated.csv")
    write_csv(next_required, out / "gold_v2_17w_required_next_gates.csv")
    write_csv(safety, out / "gold_v2_17w_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "roadmap_consolidated": ok, "roadmap_items": int(roadmap.shape[0]), "open_blockers": int(open_blockers.shape[0]), "enabled_safety_gates_now": int(summary_17v.get("enabled_safety_gates_now", -1)), "live_enabled": False, "implementation_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18A_EXECUTABLE_PARITY_DESIGN_AUDIT_ONLY" if ok else "STOP_REVIEW_17W_OUTPUTS"}
    write_json(out / "gold_v2_17w_medium_full_set_audit_only_roadmap_consolidation_summary.json", summary)
    report = ["# GOLD V2 17W MEDIUM full-set audit-only roadmap consolidation report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17W consolidates the audit-only roadmap only.", "- It does not implement predicates/arbitration, evaluate OHLC, enable live mode, create final signals, or enable external actions.", "", "## Input audit", markdown_table(audit), "", "## Consolidation checks", markdown_table(consolidation_checks), "", "## Roadmap matrix", markdown_table(roadmap), "", "## Open blockers consolidated", markdown_table(open_blockers), "", "## Required next gates", markdown_table(next_required), "", "## Safety", markdown_table(safety), "", "## 17V gate matrix carry-forward", markdown_table(gate_matrix_17v), "", "## 17V non-enablement carry-forward", markdown_table(non_enablement_17v)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
