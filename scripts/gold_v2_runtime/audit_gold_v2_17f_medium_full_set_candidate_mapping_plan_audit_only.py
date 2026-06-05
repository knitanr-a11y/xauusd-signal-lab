#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17F_MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only"
REPORT_NAME = "GOLD_V2_17F_MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_17E_STATUS = "MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_FREEZE_STATUS = "SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "summary_17e": ("gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only", "gold_v2_17e_medium_full_set_consolidation_summary.json"),
    "component_status_17e": ("gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only", "gold_v2_17e_component_status_matrix.csv"),
    "readiness_17e": ("gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only", "gold_v2_17e_readiness_checks.csv"),
    "safety_17e": ("gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only", "gold_v2_17e_safety_matrix.csv"),
    "range96_freeze": ("gold_v2_17c_range96_refined_reconciliation_audit_only", "gold_v2_17c_range96_candidate_source_freeze_preview.json"),
    "vol_freeze": ("gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only", "gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json"),
}
EXPECTED_COUNTS = {"RANGE96_REFINED": {"rule_ledger_rows": 51, "combined_ledger_rows": 117}, "VOL_TRMEAN32_REFINED": {"rule_ledger_rows": 36, "combined_ledger_rows": 104}}


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


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)):
            return None
        return float(value)
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


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


def missing_exit(out: Path, now: str, audit: pd.DataFrame) -> int:
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    blockers = pd.DataFrame([
        ["17F-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17F-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17f_blockers.csv")
    write_json(out / "gold_v2_17f_medium_full_set_candidate_mapping_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17F MEDIUM full-set candidate mapping plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17f_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return missing_exit(out, now, audit)

    s17e = read_json(input_path("summary_17e"))
    component_status = read_csv(input_path("component_status_17e"))
    readiness_17e = read_csv(input_path("readiness_17e"))
    safety_17e = read_csv(input_path("safety_17e"))
    range_freeze = read_json(input_path("range96_freeze"))
    vol_freeze = read_json(input_path("vol_freeze"))

    checks: list[list[Any]] = []
    add_check(checks, "17F-C001", "17E status", str(s17e.get("status", "")), EXPECTED_17E_STATUS)
    add_check(checks, "17F-C002", "17E readiness_ok", bool_value(s17e.get("readiness_ok", False)), True)
    add_check(checks, "17F-C003", "17E live evaluator allowed", bool_value(s17e.get("medium_live_evaluator_allowed", False)), False)
    add_check(checks, "17F-C004", "17E final signal allowed", bool_value(s17e.get("final_signal_allowed", False)), False)
    add_check(checks, "17F-C005", "17E readiness STOP rows", int(readiness_17e[readiness_17e["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17F-C006", "17E safety STOP rows", int(safety_17e[safety_17e["status"].astype(str).eq("STOP")].shape[0]), 0)
    for label, obj, comp in [("17C", range_freeze, "RANGE96_REFINED"), ("17D", vol_freeze, "VOL_TRMEAN32_REFINED")]:
        counts = obj.get("observed_counts", {}) or {}
        exp = EXPECTED_COUNTS[comp]
        add_check(checks, f"17F-{label}-FREEZE", f"{comp} freeze status", str(obj.get("candidate_status", "")), EXPECTED_FREEZE_STATUS)
        add_check(checks, f"17F-{label}-RULE", f"{comp} rule rows", int(counts.get("rule_ledger_rows", -1)), exp["rule_ledger_rows"])
        add_check(checks, f"17F-{label}-COMBINED", f"{comp} combined rows", int(counts.get("combined_ledger_rows", -1)), exp["combined_ledger_rows"])
        add_check(checks, f"17F-{label}-LIVE", f"{comp} live evaluator allowed", bool_value(obj.get("medium_live_evaluator_allowed", False)), False)
        add_check(checks, f"17F-{label}-FINAL", f"{comp} final signal allowed", bool_value(obj.get("final_signal_allowed", False)), False)

    gate_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    plan = pd.DataFrame([
        ["TIER2_HVT", "13L_candidate_mapping_load_smoke", "existing_audited_candidate_source", "use_existing_13L_mapping", "no_rediscovery", "requires_full_set_mapping_smoke", False, False],
        ["RANGE96_REFINED", "17C_source_row_identity_freeze_preview", "candidate_input_only", "use_17c_source_row_hashes", "not_executable_rule", "requires_candidate_mapping_load_smoke_dry_run", False, False],
        ["VOL_TRMEAN32_REFINED", "17D_source_row_identity_freeze_preview", "candidate_input_only", "use_17d_source_row_hashes", "not_executable_rule", "requires_candidate_mapping_load_smoke_dry_run", False, False],
    ], columns=["component", "source", "mapping_role", "planned_handling", "prohibited_action", "required_next_gate", "medium_live_evaluator_allowed", "final_signal_allowed"])
    required_gates = pd.DataFrame([
        ["17G", "MEDIUM_FULL_SET_CANDIDATE_MAPPING_AUDIT_ONLY", "Map TIER2/RANGE96/VOL source identities into a full-set candidate manifest without OHLC rediscovery.", "audit_only", False],
        ["17H", "MEDIUM_FULL_SET_LOAD_SMOKE_AUDIT_ONLY", "Load the full-set candidate manifest and verify row/hash/count integrity.", "audit_only", False],
        ["17I", "MEDIUM_FULL_SET_DRY_RUN_GATE_AUDIT_ONLY", "Dry-run only; no final signal, no Discord, no MT5, no AI, no live hook.", "audit_only", False],
    ], columns=["gate", "name", "purpose", "mode", "external_actions_allowed"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = gate_checks[gate_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers_rows = []
    for _, row in gate_checks[gate_checks["status"].eq("STOP")].iterrows():
        blockers_rows.append(["17F-BGATE", "MEDIUM_FULL_SET", "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blockers_rows += [
        ["17F-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable full-set rule", "17F is planning only; 17G/17H/17I are required before any later evaluator discussion."],
        ["17F-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "live evaluator", "Full-set executable parity/load-smoke/dry-run is not completed."],
        ["17F-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blockers_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(component_status, out / "gold_v2_17f_input_component_status_17e_copy.csv")
    write_csv(gate_checks, out / "gold_v2_17f_gate_checks.csv")
    write_csv(plan, out / "gold_v2_17f_candidate_mapping_plan.csv")
    write_csv(required_gates, out / "gold_v2_17f_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17f_blockers.csv")
    write_csv(safety, out / "gold_v2_17f_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "plan_ready": ok, "input_17e_status": str(s17e.get("status", "")), "planned_components": plan["component"].tolist(), "required_next_gates": required_gates["gate"].tolist(), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17G_MEDIUM_FULL_SET_CANDIDATE_MAPPING_AUDIT_ONLY" if ok else "STOP_REVIEW_17F_OUTPUTS"}
    write_json(out / "gold_v2_17f_medium_full_set_candidate_mapping_plan_summary.json", summary)
    report = ["# GOLD V2 17F MEDIUM full-set candidate mapping plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17F writes a full-set candidate mapping plan only.", "- It does not create executable rules and does not enable final/live/external actions.", "- TIER2_HVT uses the existing 13L candidate mapping/load-smoke chain.", "- RANGE96 and VOL use 17C/17D source-row identity freeze previews only.", "", "## Input audit", markdown_table(audit), "", "## Gate checks", markdown_table(gate_checks), "", "## Candidate mapping plan", markdown_table(plan), "", "## Required next gates", markdown_table(required_gates), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
