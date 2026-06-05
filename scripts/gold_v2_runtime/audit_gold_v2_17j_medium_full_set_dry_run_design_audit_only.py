#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17J_MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17j_medium_full_set_dry_run_design_audit_only"
REPORT_NAME = "GOLD_V2_17J_MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_DRY_RUN_DESIGN_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_DRY_RUN_DESIGN_STOPPED_AUDIT_ONLY"
EXPECTED_17I_STATUS = "MEDIUM_FULL_SET_DRY_RUN_GATE_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
EXPECTED_TOTAL = 309
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "summary_17i": ("gold_v2_17i_medium_full_set_dry_run_gate_audit_only", "gold_v2_17i_medium_full_set_dry_run_gate_summary.json"),
    "gate_checks_17i": ("gold_v2_17i_medium_full_set_dry_run_gate_audit_only", "gold_v2_17i_dry_run_gate_checks.csv"),
    "allowed_scope_17i": ("gold_v2_17i_medium_full_set_dry_run_gate_audit_only", "gold_v2_17i_dry_run_allowed_scope.csv"),
    "safety_17i": ("gold_v2_17i_medium_full_set_dry_run_gate_audit_only", "gold_v2_17i_safety_matrix.csv"),
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
        ["17J-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17J-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17j_blockers.csv")
    write_json(out / "gold_v2_17j_medium_full_set_dry_run_design_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17J MEDIUM full-set dry-run design audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17j_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return missing_exit(out, now, audit)

    summary_17i = read_json(input_path("summary_17i"))
    gate_checks_17i = read_csv(input_path("gate_checks_17i"))
    allowed_scope_17i = read_csv(input_path("allowed_scope_17i"))
    safety_17i = read_csv(input_path("safety_17i"))
    manifest = read_csv(input_path("manifest_17g"))

    checks: list[list[Any]] = []
    add_check(checks, "17J-C001", "17I status", str(summary_17i.get("status", "")), EXPECTED_17I_STATUS)
    add_check(checks, "17J-C002", "17I dry_run_design_allowed", bool_value(summary_17i.get("dry_run_design_allowed", False)), True)
    add_check(checks, "17J-C003", "17I dry_run_execution_allowed", bool_value(summary_17i.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17J-C004", "17I gate STOP rows", int(gate_checks_17i[gate_checks_17i["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17J-C005", "17I safety STOP rows", int(safety_17i[safety_17i["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17J-C006", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for component, expected in EXPECTED_COUNTS.items():
        observed = int(manifest[manifest["component"].astype(str).eq(component)].shape[0]) if "component" in manifest.columns else -1
        add_check(checks, f"17J-COUNT-{component}", f"manifest rows {component}", observed, expected)
    allowed_map = {str(r["scope_id"]): bool_value(r["allowed"]) for _, r in allowed_scope_17i.iterrows()} if "scope_id" in allowed_scope_17i.columns and "allowed" in allowed_scope_17i.columns else {}
    add_check(checks, "17J-SCOPE-17J", "scope 17J allowed", allowed_map.get("17J", False), True)
    for scope in ["FINAL_SIGNAL", "DISCORD", "MT5", "AI_API", "LIVE_HOOK"]:
        add_check(checks, f"17J-SCOPE-{scope}", f"scope {scope} allowed", allowed_map.get(scope, True), False)

    input_contract = pd.DataFrame([
        ["manifest_csv", "gold_v2_17g_full_set_candidate_manifest.csv", "required", "source identity rows only; no executable predicates"],
        ["component", "component", "required_column", "TIER2_HVT/RANGE96_REFINED/VOL_TRMEAN32_REFINED"],
        ["manifest_row_id", "manifest_row_id", "required_column", "unique identity row id"],
        ["source_identity_type", "source_identity_type", "required_column", "13L_SUMMARY_CHAIN_REFERENCE or SOURCE_ROW_HASH"],
        ["source_row_hash", "source_row_hash", "required_column", "hash only; not a live signal predicate"],
    ], columns=["contract_id", "field_or_file", "requirement", "note"])
    output_contract = pd.DataFrame([
        ["dry_run_candidate_audit", "csv", "one row per manifest identity if later implemented", "not final signal"],
        ["dry_run_gate_summary", "json", "aggregate dry-run-only audit status", "must keep live/final/external false"],
        ["no_signal_handling", "policy", "NO_SIGNAL rows may be counted but not sent to Discord", "no notifications"],
        ["external_actions", "json", "all false", "Discord/MT5/AI/live hook blocked"],
    ], columns=["output_id", "format", "requirement", "note"])
    stop_conditions = pd.DataFrame([
        ["17J-S001", "missing manifest or required columns", "STOP"],
        ["17J-S002", "manifest count mismatch", "STOP"],
        ["17J-S003", "any live/final/external action true", "STOP"],
        ["17J-S004", "attempt to evaluate OHLC or rediscover candidates", "STOP"],
        ["17J-S005", "attempt to send Discord/MT5/AI/live hook", "STOP"],
        ["17J-S006", "attempt to convert source identities into final signals", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    next_gates = pd.DataFrame([
        ["17K", "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY", "Plan a dry-run implementation, still no execution or external actions.", True],
        ["17L", "MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY", "Only after 17K, validate the dry-run implementation artifacts if created.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked until separate executable parity and dry-run gates pass.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17j_success"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["dry_run_execution_allowed", False, False, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    design_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    ok = design_checks[design_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blocker_rows = []
    for _, row in design_checks[design_checks["status"].eq("STOP")].iterrows():
        blocker_rows.append(["17J-BDESIGN", "MEDIUM_FULL_SET", "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blocker_rows += [
        ["17J-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "dry-run implementation only", "17K may plan implementation but must not execute dry-run/live/final/external actions."],
        ["17J-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "live evaluator", "Full executable/live parity remains unapproved."],
        ["17J-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blocker_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(design_checks, out / "gold_v2_17j_design_gate_checks.csv")
    write_csv(input_contract, out / "gold_v2_17j_dry_run_input_contract.csv")
    write_csv(output_contract, out / "gold_v2_17j_dry_run_output_contract.csv")
    write_csv(stop_conditions, out / "gold_v2_17j_dry_run_stop_conditions.csv")
    write_csv(next_gates, out / "gold_v2_17j_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17j_blockers.csv")
    write_csv(safety, out / "gold_v2_17j_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "dry_run_design_ready": ok, "dry_run_execution_allowed": False, "input_17i_status": str(summary_17i.get("status", "")), "manifest_rows": int(manifest.shape[0]), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17K_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_17J_OUTPUTS"}
    write_json(out / "gold_v2_17j_medium_full_set_dry_run_design_summary.json", summary)
    report = ["# GOLD V2 17J MEDIUM full-set dry-run design audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17J writes design contracts only.", "- 17J does not execute a dry-run evaluator and does not enable final/live/external actions.", "- The next possible step is implementation planning only, still audit-only.", "", "## Input audit", markdown_table(audit), "", "## Design gate checks", markdown_table(design_checks), "", "## Dry-run input contract", markdown_table(input_contract), "", "## Dry-run output contract", markdown_table(output_contract), "", "## Stop conditions", markdown_table(stop_conditions), "", "## Required next gates", markdown_table(next_gates), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
