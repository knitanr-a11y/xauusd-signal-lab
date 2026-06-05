#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18J_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY"
OUT_DIR = "gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_audit_only"
REPORT = "GOLD_V2_18J_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_PLAN_READY_AUDIT_ONLY_DRY_RUN_EXECUTION_BLOCKED"
EXPECTED_18I = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED"
IN_DIR = "gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def ensure(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def wcsv(df: pd.DataFrame, path: Path) -> None:
    ensure(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, text: str) -> None:
    ensure(path)
    lp(path).write_text(text, encoding="utf-8")


def wjson(path: Path, obj: dict[str, Any]) -> None:
    wtxt(path, json.dumps(obj, ensure_ascii=False, indent=2))


def rjson(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def rcsv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"csv read failed: {path}: {last}")


def mdtable(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def main() -> int:
    base = fx() / IN_DIR
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    inputs = {
        "summary_18i": base / "gold_v2_18i_tier2_source_identity_extraction_dry_run_design_summary.json",
        "checks_18i": base / "gold_v2_18i_design_checks.csv",
        "selected_18i": base / "gold_v2_18i_selected_artifact_design.csv",
        "recipe_18i": base / "gold_v2_18i_dry_run_field_recipe.csv",
        "stops_18i": base / "gold_v2_18i_dry_run_stop_conditions.csv",
        "next_gates_18i": base / "gold_v2_18i_required_next_gates.csv",
        "blockers_18i": base / "gold_v2_18i_blockers.csv",
        "safety_18i": base / "gold_v2_18i_safety_matrix.csv",
    }
    audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(audit, out / "gold_v2_18j_input_audit.csv")
    if not audit["exists"].all():
        wjson(out / "gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_summary.json", {"created_utc": now, "step": STEP, "status": "18J_STOP_MISSING_INPUTS", "audit_only": True, "dry_run_implemented": False})
        return 2

    s18i = rjson(inputs["summary_18i"])
    checks18i = rcsv(inputs["checks_18i"])
    selected = rcsv(inputs["selected_18i"])
    recipe = rcsv(inputs["recipe_18i"])
    stops18i = rcsv(inputs["stops_18i"])
    blockers = rcsv(inputs["blockers_18i"])
    safety18i = rcsv(inputs["safety_18i"])

    stop_checks = int((checks18i["status"].astype(str) == "STOP").sum())
    stop_safety = int((safety18i["status"].astype(str) == "STOP").sum())
    empty_candidate_cols = int(((recipe["future_dry_run_action"].astype(str).str.contains("DERIVE", na=False)) & (recipe["candidate_columns"].astype(str).str.strip().eq(""))).sum()) if "candidate_columns" in recipe.columns else -1
    checks = pd.DataFrame([
        ["18J-C001", "18I status", s18i.get("status"), EXPECTED_18I, "PASS" if s18i.get("status") == EXPECTED_18I else "STOP"],
        ["18J-C002", "18I checks STOP rows", stop_checks, 0, "PASS" if stop_checks == 0 else "STOP"],
        ["18J-C003", "18I safety STOP rows", stop_safety, 0, "PASS" if stop_safety == 0 else "STOP"],
        ["18J-C004", "18I dry-run implemented", bool(s18i.get("dry_run_implemented", False)), False, "PASS" if not bool(s18i.get("dry_run_implemented", False)) else "STOP"],
        ["18J-C005", "18I source rows read", bool(s18i.get("source_rows_read", False)), False, "PASS" if not bool(s18i.get("source_rows_read", False)) else "STOP"],
        ["18J-C006", "18I row hash computed", bool(s18i.get("row_hash_computed", False)), False, "PASS" if not bool(s18i.get("row_hash_computed", False)) else "STOP"],
        ["18J-C007", "derived recipe rows with empty candidate columns", empty_candidate_cols, 0, "PASS" if empty_candidate_cols == 0 else "STOP"],
    ], columns=["check_id", "check", "observed", "expected", "status"])

    planned_artifacts = selected.copy()
    planned_artifacts["future_dry_run_input_role"] = planned_artifacts["selection_role"]
    planned_artifacts["dry_run_execution_allowed_now"] = False
    planned_artifacts["source_recovery_allowed_now"] = False

    step_rows = []
    ordered_steps = [
        (1, "load_18i_recipe", "Load 18I recipe only; do not read source data rows."),
        (2, "validate_candidate_columns", "Validate that every derive action has candidate columns."),
        (3, "prepare_dry_run_output_schema", "Prepare output schema only."),
        (4, "plan_direct_field_copy", "Plan direct copy fields from recipe."),
        (5, "plan_derived_field_rules", "Plan derived fields from candidate columns without executing."),
        (6, "write_plan_outputs", "Write audit-only plan outputs."),
    ]
    for order, name, desc in ordered_steps:
        step_rows.append({"step_order": order, "planned_step": name, "description": desc, "reads_source_rows": False, "computes_row_hash": False, "recovers_source_identity": False, "implements_dry_run": False, "implementation_allowed_now": False})
    planned_steps = pd.DataFrame(step_rows)

    output_contract = pd.DataFrame([
        ["manifest_row_id", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["component", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["source_identity_type", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["source_role", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["source_row_number_1based", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["source_key", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["source_row_hash", "planned_field", "future dry-run output field; hash not computed in 18J"],
        ["strategy_id", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["source_status", "planned_field", "future dry-run output field; no value produced in 18J"],
        ["dry_run_status", "planned_metadata", "future status marker"],
        ["source_recovery_executed", "safety_field", "must remain false"],
    ], columns=["field", "field_class", "planned_meaning"])

    stop_conditions = pd.concat([
        stops18i.assign(carried_forward_from="18I"),
        pd.DataFrame([
            ["18J-S001", "attempt to implement or execute dry-run during 18J", "STOP", "18J"],
            ["18J-S002", "attempt to read source rows during 18J", "STOP", "18J"],
            ["18J-S003", "attempt to compute source_row_hash during 18J", "STOP", "18J"],
            ["18J-S004", "attempt to recover/finalize source identity during 18J", "STOP", "18J"],
        ], columns=["stop_id", "condition", "action", "carried_forward_from"]),
    ], ignore_index=True)

    nextg = pd.DataFrame([
        ["18K", "TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY", "Implement audit-only dry-run script after plan review; no source recovery finalization.", True],
        ["DRY_RUN_EXECUTION", "TIER2_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_EXECUTION", "Blocked after 18J until 18K exists and is reviewed.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18J.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18j_success"])

    blockers = blockers.copy()
    blockers["carried_forward_by"] = STEP
    blockers["dry_run_implemented"] = False
    blockers["dry_run_execution_allowed"] = False
    blockers["source_recovery_executed"] = False
    blockers["implementation_allowed"] = False
    blockers["live_or_final_allowed"] = False
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["implementation_plan_only", True, True, "PASS"],
        ["dry_run_implemented", False, False, "PASS"],
        ["dry_run_executed", False, False, "PASS"],
        ["source_rows_read", False, False, "PASS"],
        ["row_hash_computed", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])

    ok = int((checks["status"].astype(str) == "STOP").sum()) == 0
    status = SUCCESS if ok else "18J_STOP_REVIEW_OUTPUTS"
    for name, df in [
        ("gold_v2_18j_plan_checks.csv", checks),
        ("gold_v2_18j_planned_artifacts.csv", planned_artifacts),
        ("gold_v2_18j_planned_processing_steps.csv", planned_steps),
        ("gold_v2_18j_planned_output_contract.csv", output_contract),
        ("gold_v2_18j_planned_stop_conditions.csv", stop_conditions),
        ("gold_v2_18j_required_next_gates.csv", nextg),
        ("gold_v2_18j_blockers.csv", blockers),
        ("gold_v2_18j_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "implementation_plan_ready": ok, "planned_artifacts": int(len(planned_artifacts)), "planned_processing_steps": int(len(planned_steps)), "planned_output_fields": int(len(output_contract)), "dry_run_implemented": False, "dry_run_executed": False, "source_rows_read": False, "row_hash_computed": False, "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY" if ok else "STOP_REVIEW_18J_OUTPUTS"}
    wjson(out / "gold_v2_18j_tier2_source_identity_dry_run_implementation_plan_summary.json", summary)
    report = ["# GOLD V2 18J TIER2 source identity dry-run implementation plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18J created an implementation plan only.", "- It did not implement or execute a dry-run, read source rows, compute row hashes, recover identity, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live/final, or enable external actions.", "", "## Checks", mdtable(checks), "", "## Planned artifacts", mdtable(planned_artifacts), "", "## Planned processing steps", mdtable(planned_steps), "", "## Planned output contract", mdtable(output_contract), "", "## Stop conditions", mdtable(stop_conditions), "", "## Next gates", mdtable(nextg), "", "## Blockers", mdtable(blockers), "", "## Safety", mdtable(safety)]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
