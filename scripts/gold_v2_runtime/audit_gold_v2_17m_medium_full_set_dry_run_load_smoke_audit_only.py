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

STEP = "17M_MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17m_medium_full_set_dry_run_load_smoke_audit_only"
REPORT_NAME = "GOLD_V2_17M_MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_DRY_RUN_LOAD_SMOKE_STOPPED_AUDIT_ONLY"
EXPECTED_17L_STATUS = "MEDIUM_FULL_SET_DRY_RUN_IMPLEMENTATION_WRITTEN_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_TOTAL = 309
EXPECTED_STATUS = "SOURCE_IDENTITY_OBSERVED_AUDIT_ONLY_NOT_SIGNAL"
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
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
REQUIRED_COLUMNS = [
    "dry_run_row_id",
    "manifest_row_id",
    "component",
    "source_identity_type",
    "source_row_hash",
    "dry_run_status",
    "dry_run_signal",
    "audit_only",
] + FALSE_FLAGS
INPUTS = {
    "summary_17l": ("gold_v2_17l_medium_full_set_dry_run_implementation_audit_only", "gold_v2_17l_medium_full_set_dry_run_implementation_summary.json"),
    "dry_run_rows_17l": ("gold_v2_17l_medium_full_set_dry_run_implementation_audit_only", "gold_v2_17l_dry_run_candidate_audit.csv"),
    "component_counts_17l": ("gold_v2_17l_medium_full_set_dry_run_implementation_audit_only", "gold_v2_17l_component_counts.csv"),
    "implementation_checks_17l": ("gold_v2_17l_medium_full_set_dry_run_implementation_audit_only", "gold_v2_17l_implementation_checks.csv"),
    "safety_17l": ("gold_v2_17l_medium_full_set_dry_run_implementation_audit_only", "gold_v2_17l_safety_matrix.csv"),
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
        [["17M-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17m_blockers.csv")
    write_json(out / "gold_v2_17m_medium_full_set_dry_run_load_smoke_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17M MEDIUM full-set dry-run load-smoke audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17m_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return write_stop(out, now, audit)

    summary_17l = read_json(input_path("summary_17l"))
    rows = read_csv(input_path("dry_run_rows_17l"))
    counts_17l = read_csv(input_path("component_counts_17l"))
    implementation_checks_17l = read_csv(input_path("implementation_checks_17l"))
    safety_17l = read_csv(input_path("safety_17l"))

    checks: list[list[Any]] = []
    add_check(checks, "17M-C001", "17L status", str(summary_17l.get("status", "")), EXPECTED_17L_STATUS)
    add_check(checks, "17M-C002", "17L dry_run_rows_written", bool_value(summary_17l.get("dry_run_rows_written", False)), True)
    add_check(checks, "17M-C003", "17L dry_run_audit_rows", int(summary_17l.get("dry_run_audit_rows", -1)), EXPECTED_TOTAL)
    add_check(checks, "17M-C004", "17L implementation STOP rows", int(implementation_checks_17l[implementation_checks_17l["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17M-C005", "17L safety STOP rows", int(safety_17l[safety_17l["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17M-C006", "loaded dry-run rows", int(rows.shape[0]), EXPECTED_TOTAL)
    for col in REQUIRED_COLUMNS:
        add_check(checks, f"17M-COL-{col}", f"required column {col}", col in rows.columns, True)
    if "dry_run_status" in rows.columns:
        add_check(checks, "17M-STATUS", "expected dry_run_status rows", int(rows["dry_run_status"].astype(str).eq(EXPECTED_STATUS).sum()), EXPECTED_TOTAL)
    if "dry_run_signal" in rows.columns:
        add_check(checks, "17M-NOT-SIGNAL", "dry_run_signal NOT_SIGNAL rows", int(rows["dry_run_signal"].astype(str).eq("NOT_SIGNAL").sum()), EXPECTED_TOTAL)
    if "component" in rows.columns:
        for component, expected in EXPECTED_COUNTS.items():
            add_check(checks, f"17M-COUNT-{component}", f"rows {component}", int(rows[rows["component"].astype(str).eq(component)].shape[0]), expected)
    for flag in FALSE_FLAGS:
        if flag in rows.columns:
            add_check(checks, f"17M-FLAG-{flag}", f"{flag} false rows", int((rows[flag].map(bool_value) == False).sum()), EXPECTED_TOTAL)
    if "component" in counts_17l.columns and "dry_run_audit_rows" in counts_17l.columns:
        for component, expected in EXPECTED_COUNTS.items():
            sub = counts_17l[counts_17l["component"].astype(str).eq(component)]
            observed = int(sub["dry_run_audit_rows"].iloc[0]) if len(sub) else -1
            add_check(checks, f"17M-COUNT-FILE-{component}", f"component count file {component}", observed, expected)

    component_counts = rows.groupby("component", dropna=False).size().reset_index(name="loaded_dry_run_rows") if "component" in rows.columns else pd.DataFrame(columns=["component", "loaded_dry_run_rows"])
    load_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame(
        [["audit_only", True, True, "PASS"], ["dry_run_load_smoke_passed", True, True, "PASS"], ["dry_run_execution_allowed", False, False, "PASS"], ["medium_live_evaluator_allowed", False, False, "PASS"], ["final_signal_allowed", False, False, "PASS"], ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"], ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"], ["no_signal_discord_notified", False, False, "PASS"]],
        columns=["safety_item", "observed", "expected", "status"],
    )
    ok = load_checks[load_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame(
        [["17M-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "dry-run consolidation", "17N may consolidate audit status only; no live/final/external actions."], ["17M-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "final/live execution", "17M is load-smoke only, not an evaluator."], ["17M-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(load_checks, out / "gold_v2_17m_dry_run_load_checks.csv")
    write_csv(component_counts, out / "gold_v2_17m_component_counts_check.csv")
    write_csv(blockers, out / "gold_v2_17m_blockers.csv")
    write_csv(safety, out / "gold_v2_17m_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "dry_run_load_smoke_passed": ok, "loaded_dry_run_rows": int(rows.shape[0]), "component_counts": component_counts.to_dict("records"), "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17N_MEDIUM_FULL_SET_DRY_RUN_CONSOLIDATION_AUDIT_ONLY" if ok else "STOP_REVIEW_17M_OUTPUTS"}
    write_json(out / "gold_v2_17m_medium_full_set_dry_run_load_smoke_summary.json", summary)
    report = ["# GOLD V2 17M MEDIUM full-set dry-run load-smoke audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17M load-smokes 17L identity-only dry-run audit rows.", "- It does not evaluate OHLC, rediscover candidates, compute predicates, or emit final signals.", "- External actions and NO_SIGNAL notification remain disabled.", "", "## Input audit", markdown_table(audit), "", "## Dry-run load checks", markdown_table(load_checks), "", "## Component counts", markdown_table(component_counts), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
