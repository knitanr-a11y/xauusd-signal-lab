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

STEP = "17L_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17l_medium_full_set_dry_run_implementation_audit_only"
REPORT_NAME = "GOLD_V2_17L_MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_WRITTEN_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_STOPPED_AUDIT_ONLY"
EXPECTED_17K_STATUS = "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_TOTAL = 309
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
DRY_STATUS = "SOURCE_IDENTITY_OBSERVED_AUDIT_ONLY_NOT_SIGNAL"
FALSE_FLAGS = [
    "ohlc_evaluated",
    "candidate_rediscovered",
    "predicate_evaluated",
    "medium_live_evaluator_allowed",
    "final_signal_allowed",
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
    "no_signal_discord_notified",
]
REQUIRED_MANIFEST_COLUMNS = [
    "manifest_row_id",
    "component",
    "source_step",
    "source_identity_type",
    "source_role",
    "source_row_number_1based",
    "source_key",
    "strategy_id",
    "source_row_hash",
    "source_status",
    "live_executable",
    "final_signal_allowed",
]
INPUTS = {
    "summary_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_medium_full_set_dry_run_implementation_plan_summary.json"),
    "plan_checks_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_plan_gate_checks.csv"),
    "planned_artifacts_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_planned_artifacts.csv"),
    "planned_processing_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_planned_processing_steps.csv"),
    "planned_stops_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_planned_stop_conditions.csv"),
    "next_gates_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_required_next_gates.csv"),
    "safety_17k": ("gold_v2_17k_medium_full_set_dry_run_implementation_plan_audit_only", "gold_v2_17k_safety_matrix.csv"),
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
        path = input_path(role)
        row = {"role": role, "path": str(path), "required": True, "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
        rows.append(row)
    return pd.DataFrame(rows)


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def write_stop(out: Path, now: str, audit: pd.DataFrame) -> int:
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    blockers = pd.DataFrame(
        [["17L-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17l_blockers.csv")
    write_json(out / "gold_v2_17l_medium_full_set_dry_run_implementation_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17L MEDIUM full-set dry-run implementation audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def build_audit_rows(manifest: pd.DataFrame) -> pd.DataFrame:
    rows = manifest.copy()
    rows.insert(0, "dry_run_row_id", [f"17L_DRY_RUN_AUDIT_{i+1:06d}" for i in range(len(rows))])
    rows["dry_run_status"] = DRY_STATUS
    rows["dry_run_signal"] = "NOT_SIGNAL"
    rows["audit_only"] = True
    for col in FALSE_FLAGS:
        rows[col] = False
    return rows


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17l_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return write_stop(out, now, audit)

    summary_17k = read_json(input_path("summary_17k"))
    plan_checks = read_csv(input_path("plan_checks_17k"))
    safety_17k = read_csv(input_path("safety_17k"))
    # These files are loaded to make the input contract explicit; they are not used to run trading logic.
    _ = read_csv(input_path("planned_artifacts_17k"))
    _ = read_csv(input_path("planned_processing_17k"))
    _ = read_csv(input_path("planned_stops_17k"))
    _ = read_csv(input_path("next_gates_17k"))
    manifest = read_csv(input_path("manifest_17g"))

    checks: list[list[Any]] = []
    add_check(checks, "17L-C001", "17K status", str(summary_17k.get("status", "")), EXPECTED_17K_STATUS)
    add_check(checks, "17L-C002", "17K implementation_plan_ready", bool_value(summary_17k.get("implementation_plan_ready", False)), True)
    add_check(checks, "17L-C003", "17K implementation_created flag", bool_value(summary_17k.get("dry_run_implementation_created", False)), False)
    add_check(checks, "17L-C004", "17K execution_allowed flag", bool_value(summary_17k.get("dry_run_execution_allowed", False)), False)
    add_check(checks, "17L-C005", "17K plan STOP rows", int(plan_checks[plan_checks["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17L-C006", "17K safety STOP rows", int(safety_17k[safety_17k["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17L-C007", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for col in REQUIRED_MANIFEST_COLUMNS:
        add_check(checks, f"17L-COL-{col}", f"manifest column {col}", col in manifest.columns, True)
    for component, expected in EXPECTED_COUNTS.items():
        observed = int(manifest[manifest["component"].astype(str).eq(component)].shape[0]) if "component" in manifest.columns else -1
        add_check(checks, f"17L-COUNT-{component}", f"manifest rows {component}", observed, expected)

    audit_rows = build_audit_rows(manifest)
    add_check(checks, "17L-OUT-ROWS", "audit output rows", int(audit_rows.shape[0]), EXPECTED_TOTAL)
    add_check(checks, "17L-OUT-STATUS", "audit status rows", int(audit_rows["dry_run_status"].astype(str).eq(DRY_STATUS).sum()), EXPECTED_TOTAL)
    for flag in FALSE_FLAGS:
        add_check(checks, f"17L-FLAG-{flag}", f"{flag} false rows", int((audit_rows[flag].map(bool_value) == False).sum()), EXPECTED_TOTAL)

    component_counts = audit_rows.groupby("component", dropna=False).size().reset_index(name="dry_run_audit_rows")
    implementation_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame(
        [["audit_only", True, True, "PASS"], ["dry_run_rows_written", True, True, "PASS"], ["dry_run_execution_allowed", False, False, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"], ["no_signal_discord_notified", False, False, "PASS"]],
        columns=["safety_item", "observed", "expected", "status"],
    )
    ok = implementation_checks[implementation_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame(
        [["17L-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "load-smoke", "17M must load-smoke 17L outputs before any later dry-run discussion."], ["17L-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "final/live execution", "17L is identity-only audit rows, not executable evaluator."], ["17L-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(audit_rows, out / "gold_v2_17l_dry_run_candidate_audit.csv")
    write_csv(component_counts, out / "gold_v2_17l_component_counts.csv")
    write_csv(implementation_checks, out / "gold_v2_17l_implementation_checks.csv")
    write_csv(blockers, out / "gold_v2_17l_blockers.csv")
    write_csv(safety, out / "gold_v2_17l_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "dry_run_rows_written": True, "dry_run_audit_rows": int(audit_rows.shape[0]), "dry_run_status": DRY_STATUS, "component_counts": component_counts.to_dict("records"), "dry_run_execution_allowed": False, "ohlc_evaluated": False, "candidate_rediscovered": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17M_MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY" if ok else "STOP_REVIEW_17L_OUTPUTS"}
    write_json(out / "gold_v2_17l_medium_full_set_dry_run_implementation_summary.json", summary)
    report = ["# GOLD V2 17L MEDIUM full-set dry-run implementation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17L writes identity-only audit rows from the 17G manifest.", "- It does not evaluate OHLC, rediscover candidates, compute predicates, or emit final signals.", "- External actions and NO_SIGNAL notification remain disabled.", "", "## Input audit", markdown_table(audit), "", "## Implementation checks", markdown_table(implementation_checks), "", "## Component counts", markdown_table(component_counts), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
