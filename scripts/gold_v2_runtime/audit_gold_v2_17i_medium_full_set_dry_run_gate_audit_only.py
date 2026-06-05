#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17I_MEDIUM_FULL_SET_DRY_RUN_GATE_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17i_medium_full_set_dry_run_gate_audit_only"
REPORT_NAME = "GOLD_V2_17I_MEDIUM_FULL_SET_DRY_RUN_GATE_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_DRY_RUN_GATE_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_DRY_RUN_GATE_STOPPED_AUDIT_ONLY"
EXPECTED_17H_STATUS = "MEDIUM_FULL_SET_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_TOTAL = 309
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "summary_17h": ("gold_v2_17h_medium_full_set_load_smoke_audit_only", "gold_v2_17h_medium_full_set_load_smoke_summary.json"),
    "load_checks_17h": ("gold_v2_17h_medium_full_set_load_smoke_audit_only", "gold_v2_17h_manifest_load_checks.csv"),
    "component_counts_17h": ("gold_v2_17h_medium_full_set_load_smoke_audit_only", "gold_v2_17h_component_counts_check.csv"),
    "safety_17h": ("gold_v2_17h_medium_full_set_load_smoke_audit_only", "gold_v2_17h_safety_matrix.csv"),
    "blockers_17h": ("gold_v2_17h_medium_full_set_load_smoke_audit_only", "gold_v2_17h_blockers.csv"),
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
        ["17I-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17I-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17i_blockers.csv")
    write_json(out / "gold_v2_17i_medium_full_set_dry_run_gate_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17I MEDIUM full-set dry-run gate audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17i_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return missing_exit(out, now, audit)

    summary_17h = read_json(input_path("summary_17h"))
    load_checks = read_csv(input_path("load_checks_17h"))
    counts = read_csv(input_path("component_counts_17h"))
    safety_17h = read_csv(input_path("safety_17h"))
    blockers_17h = read_csv(input_path("blockers_17h"))

    checks: list[list[Any]] = []
    add_check(checks, "17I-C001", "17H status", str(summary_17h.get("status", "")), EXPECTED_17H_STATUS)
    add_check(checks, "17I-C002", "17H manifest_load_smoke_passed", bool_value(summary_17h.get("manifest_load_smoke_passed", False)), True)
    add_check(checks, "17I-C003", "17H manifest_rows", int(summary_17h.get("manifest_rows", -1)), EXPECTED_TOTAL)
    add_check(checks, "17I-C004", "17H load check STOP rows", int(load_checks[load_checks["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17I-C005", "17H safety STOP rows", int(safety_17h[safety_17h["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17I-C006", "17H live evaluator allowed", bool_value(summary_17h.get("medium_live_evaluator_allowed", False)), False)
    add_check(checks, "17I-C007", "17H final signal allowed", bool_value(summary_17h.get("final_signal_allowed", False)), False)
    for component, expected in EXPECTED_COUNTS.items():
        sub = counts[counts["component"].astype(str).eq(component)] if "component" in counts.columns else pd.DataFrame()
        observed = int(sub["observed_manifest_rows"].iloc[0]) if len(sub) and "observed_manifest_rows" in sub.columns else -1
        status = str(sub["status"].iloc[0]) if len(sub) and "status" in sub.columns else "MISSING"
        add_check(checks, f"17I-COUNT-{component}", f"{component} observed rows", observed, expected)
        add_check(checks, f"17I-COUNT-STATUS-{component}", f"{component} count status", status, "PASS")
    gate_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    dry_scope = pd.DataFrame([
        ["17J", "MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY", True, "Design dry-run inputs/outputs and stop conditions only; no execution."],
        ["FINAL_SIGNAL", "final signal generation", False, "Explicitly blocked."],
        ["DISCORD", "Discord notification", False, "Explicitly blocked, including NO_SIGNAL."],
        ["MT5", "MT5 order placement", False, "Explicitly blocked."],
        ["AI_API", "AI API review", False, "Explicitly blocked."],
        ["LIVE_HOOK", "live hook integration", False, "Explicitly blocked."],
    ], columns=["scope_id", "scope", "allowed", "note"])
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
    blocker_rows = []
    for _, row in gate_checks[gate_checks["status"].eq("STOP")].iterrows():
        blocker_rows.append(["17I-BGATE", "MEDIUM_FULL_SET", "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blocker_rows += [
        ["17I-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "dry-run design only", "17J may design dry-run artifacts but must not execute final/live/external actions."],
        ["17I-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "live evaluator", "Full executable/live parity remains unapproved."],
        ["17I-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blocker_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(gate_checks, out / "gold_v2_17i_dry_run_gate_checks.csv")
    write_csv(dry_scope, out / "gold_v2_17i_dry_run_allowed_scope.csv")
    write_csv(blockers, out / "gold_v2_17i_blockers.csv")
    write_csv(safety, out / "gold_v2_17i_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "dry_run_design_allowed": ok, "dry_run_execution_allowed": False, "input_17h_status": str(summary_17h.get("status", "")), "manifest_rows": int(summary_17h.get("manifest_rows", -1)), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17J_MEDIUM_FULL_SET_DRY_RUN_DESIGN_AUDIT_ONLY" if ok else "STOP_REVIEW_17I_OUTPUTS"}
    write_json(out / "gold_v2_17i_medium_full_set_dry_run_gate_summary.json", summary)
    report = ["# GOLD V2 17I MEDIUM full-set dry-run gate audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17I permits only a later dry-run design step if all checks pass.", "- 17I does not run a dry-run evaluator and does not enable final/live/external actions.", "- All live/final/Discord/MT5/AI/live-hook paths remain blocked.", "", "## Input audit", markdown_table(audit), "", "## Dry-run gate checks", markdown_table(gate_checks), "", "## Allowed scope", markdown_table(dry_scope), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety), "", "## 17H blocker carry-forward", markdown_table(blockers_17h)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
