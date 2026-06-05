#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17K_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only"
REPORT_NAME = "GOLD_V2_17K_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_STOPPED_AUDIT_ONLY"
EXPECTED_17J_STATUS = "MEDIUM_FULL_SET_DRY_RUN_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
EXPECTED_TOTAL = 309
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "summary_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_medium_full_set_dry_run_design_summary.json"),
    "design_checks_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_design_gate_checks.csv"),
    "input_contract_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_dry_run_input_contract.csv"),
    "output_contract_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_dry_run_output_contract.csv"),
    "stop_conditions_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_dry_run_stop_conditions.csv"),
    "next_gates_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_required_next_gates.csv"),
    "safety_17j": ("gold_v2_17j_medium_full_set_dry_run_design_audit_only", "gold_v2_17j_safety_matrix.csv"),
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        ["17K-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17K-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17k_blockers.csv")
    write_json(out / "gold_v2_17k_medium_full_set_dry_run_implementation_plan_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17K MEDIUM full-set dry-run implementation plan audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17k_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return missing_exit(out, now, audit)

    summary_17j = read_json(input_path("summary_17j"))
    design_checks_17j = read_csv(input_path("design_checks_17j"))
    input_contract_17j = read_csv(input_path("input_contract_17j"))
    output_contract_17j = read_csv(input_path("output_contract_17j"))
    stop_conditions_17j = read_csv(input_path("stop_conditions_17j"))
    next_gates_17j = read_csv(input_path("next_gates_17j"))
    safety_17j = read_csv(input_path("safety_17j"))
    manifest = read_csv(input_path("manifest_17g"))

    checks: list[list[Any]] = []
    add_check(checks, "17K-C001", "17J status", str(summary_17j.get("status", "")), EXPECTED_17J_STATUS)
    add_check(checks, "17K-C002", "17J dry_run_design_ready", bool_value(summary_17j.get("dry_run_design_ready", False)), True)
    add_check(checks, "17K-C003", "17J dry_run_execution_allowed", bool_value(summary_17j.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17K-C004", "17J design STOP rows", int(design_checks_17j[design_checks_17j["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17K-C005", "17J safety STOP rows", int(safety_17j[safety_17j["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17K-C006", "17J input contract rows", int(input_contract_17j.shape[0]) >= 1, True)
    add_check(checks, "17K-C007", "17J output contract rows", int(output_contract_17j.shape[0]) >= 1, True)
    add_check(checks, "17K-C008", "17J stop condition rows", int(stop_conditions_17j.shape[0]) >= 1, True)
    add_check(checks, "17K-C009", "17J next gates include 17K", bool("17K" in set(next_gates_17j.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "17K-C010", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for component, expected in EXPECTED_COUNTS.items():
        observed = int(manifest[manifest["component"].astype(str).eq(component)].shape[0]) if "component" in manifest.columns else -1
        add_check(checks, f"17K-COUNT-{component}", f"manifest rows {component}", observed, expected)

    planned_artifacts = pd.DataFrame([
        ["future_script", "scripts/gold_v2_runtime/audit_gold_v2_17l_medium_full_set_dry_run_implementation_audit_only.py", "future_only", "not_created_by_17k", False, False],
        ["future_bat", "scripts/gold_v2_runtime/bat/17L_AUDIT_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY.bat", "future_only", "not_created_by_17k", False, False],
        ["dry_run_candidates_csv", "gold_v2_17l_medium_full_set_dry_run_candidate_audit.csv", "planned_output", "one audit row per manifest identity, no final signal", False, False],
        ["dry_run_summary_json", "gold_v2_17l_medium_full_set_dry_run_implementation_summary.json", "planned_output", "aggregate audit-only status", False, False],
        ["dry_run_safety_csv", "gold_v2_17l_safety_matrix.csv", "planned_output", "all external actions false", False, False],
    ], columns=["artifact_id", "path_or_name", "artifact_type", "note", "live_executable", "final_signal_allowed"])
    processing_steps = pd.DataFrame([
        ["P001", "load 17G manifest", "read-only", "stop if missing/count mismatch"],
        ["P002", "validate required columns", "audit-only", "stop if schema mismatch"],
        ["P003", "copy source identities to dry-run audit rows", "identity-only", "do not evaluate OHLC"],
        ["P004", "assign dry_run_status", "audit-only", "SOURCE_IDENTITY_OBSERVED only; not signal"],
        ["P005", "write summary/safety/blockers", "audit-only", "all external actions false"],
    ], columns=["step_id", "planned_step", "mode", "stop_or_note"])
    planned_stops = pd.DataFrame([
        ["17K-S001", "attempt to read OHLC", "STOP"],
        ["17K-S002", "attempt to create final signal", "STOP"],
        ["17K-S003", "attempt to notify Discord including NO_SIGNAL", "STOP"],
        ["17K-S004", "attempt to place MT5 order", "STOP"],
        ["17K-S005", "attempt to call AI API", "STOP"],
        ["17K-S006", "attempt to install live hook", "STOP"],
        ["17K-S007", "manifest count/hash/schema mismatch", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_gates = pd.DataFrame([
        ["17L", "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY", "Create the dry-run implementation artifact, still audit-only and identity-only.", True],
        ["17M", "MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY", "Load-smoke 17L outputs if created.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until separate executable/live parity and dry-run gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17k_success"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["dry_run_implementation_created", False, False, "PASS"],
        ["dry_run_execution_allowed", False, False, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    plan_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    ok = plan_checks[plan_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blocker_rows = []
    for _, row in plan_checks[plan_checks["status"].eq("STOP")].iterrows():
        blocker_rows.append(["17K-BPLAN", "MEDIUM_FULL_SET", "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blocker_rows += [
        ["17K-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "dry-run implementation", "17K plans the implementation only; 17L must be separately created and remain audit-only."],
        ["17K-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "dry-run execution", "17L, if created, must write audit rows only and not execute live/final logic."],
        ["17K-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blocker_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(plan_checks, out / "gold_v2_17k_plan_gate_checks.csv")
    write_csv(planned_artifacts, out / "gold_v2_17k_planned_artifacts.csv")
    write_csv(processing_steps, out / "gold_v2_17k_planned_processing_steps.csv")
    write_csv(planned_stops, out / "gold_v2_17k_planned_stop_conditions.csv")
    write_csv(next_gates, out / "gold_v2_17k_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17k_blockers.csv")
    write_csv(safety, out / "gold_v2_17k_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "implementation_plan_ready": ok, "dry_run_implementation_created": False, "dry_run_execution_allowed": False, "input_17j_status": str(summary_17j.get("status", "")), "manifest_rows": int(manifest.shape[0]), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17L_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY" if ok else "STOP_REVIEW_17K_OUTPUTS"}
    write_json(out / "gold_v2_17k_medium_full_set_dry_run_implementation_plan_summary.json", summary)
    report = ["# GOLD V2 17K MEDIUM full-set dry-run implementation plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17K writes an implementation plan only.", "- 17K does not create or execute the dry-run implementation.", "- The next possible step is 17L, which must remain audit-only and identity-only.", "", "## Input audit", markdown_table(audit), "", "## Plan gate checks", markdown_table(plan_checks), "", "## Planned artifacts", markdown_table(planned_artifacts), "", "## Planned processing steps", markdown_table(processing_steps), "", "## Planned stop conditions", markdown_table(planned_stops), "", "## Required next gates", markdown_table(next_gates), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
