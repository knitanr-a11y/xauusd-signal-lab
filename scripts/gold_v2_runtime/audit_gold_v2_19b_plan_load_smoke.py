#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only"
IN19A = "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only"
REPORT = "GOLD_V2_19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19A = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
REQUIRED_FIELDS = {"decision_id", "decision_timestamp_utc", "decision_value", "human_reviewer", "evidence_acknowledged", "explicit_phrase"}
REQUIRED_PLAN_PHRASES = [
    "plan-only",
    "not an actual decision",
    "no decision is collected",
    "no approval is granted",
    "no source recovery",
    "no source identity finalization",
    "no live enablement",
    "no final signal",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


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


def ensure_parent(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    lp(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    ensure_parent(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def check_row(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(rows)


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["19C", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY", "Content-audit 19A decision intake plan only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19B.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19B.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19b_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["decision_plan_load_smoke_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
        ["next_gate_19c_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19B-S001", "required inputs missing", "STOP"],
        ["19B-S002", "19A status not passed", "STOP"],
        ["19B-S003", "decision collected or approval already made", "STOP"],
        ["19B-S004", "upstream STOP rows present", "STOP"],
        ["19B-S005", "plan text missing plan-only prohibitions", "STOP"],
        ["19B-S006", "required future decision fields missing", "STOP"],
        ["19B-S007", "decision values execute actions", "STOP"],
        ["19B-S008", "forbidden gate allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19a = base / IN19A
    inputs = {
        "summary_19a": p19a / "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_summary.json",
        "checks_19a": p19a / "gold_v2_19a_planning_checks.csv",
        "plan_19a": p19a / "gold_v2_19a_decision_intake_plan.md",
        "fields_19a": p19a / "gold_v2_19a_required_decision_fields.csv",
        "values_19a": p19a / "gold_v2_19a_allowed_decision_values.csv",
        "gates_19a": p19a / "gold_v2_19a_required_next_gates.csv",
        "safety_19a": p19a / "gold_v2_19a_safety_matrix.csv",
        "report_19a": p19a / "GOLD_V2_19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19b_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19B-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19b_load_checks.csv", checks)
        write_csv(out / "gold_v2_19b_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19B_STOP_MISSING_INPUTS", "audit_only": True, "plan_load_smoke_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19B_INPUTS"}
        write_json(out / "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19B decision plan load-smoke audit-only report\n\nStatus: `19B_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19a = read_json(inputs["summary_19a"])
    checks19a = read_csv(inputs["checks_19a"])
    plan_text = lp(inputs["plan_19a"]).read_text(encoding="utf-8")
    fields = read_csv(inputs["fields_19a"])
    values = read_csv(inputs["values_19a"])
    gates19a = read_csv(inputs["gates_19a"])
    safety19a = read_csv(inputs["safety_19a"])

    plan_lower = plan_text.lower()
    missing_plan_phrases = [p for p in REQUIRED_PLAN_PHRASES if p not in plan_lower]
    plan_audit = pd.DataFrame([
        check_row("19B-P001", "plan loads", len(plan_text), ">0", len(plan_text) > 0),
        check_row("19B-P002", "plan required phrases missing", len(missing_plan_phrases), 0, len(missing_plan_phrases) == 0),
    ])
    write_csv(out / "gold_v2_19b_plan_load_audit.csv", plan_audit)

    field_names = set(fields.get("field", pd.Series(dtype=str)).astype(str).tolist())
    missing_fields = sorted(REQUIRED_FIELDS - field_names)
    required_field_count = int(fields.get("required", pd.Series(dtype=bool)).map(truthy).sum()) if not fields.empty else 0
    field_audit = pd.DataFrame([
        check_row("19B-F001", "required core fields missing", len(missing_fields), 0, len(missing_fields) == 0),
        check_row("19B-F002", "required field count", required_field_count, ">=6", required_field_count >= 6),
    ])
    write_csv(out / "gold_v2_19b_field_load_audit.csv", field_audit)

    value_count = int(len(values))
    value_action_count = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    value_audit = pd.DataFrame([
        check_row("19B-V001", "allowed value count", value_count, ">=4", value_count >= 4),
        check_row("19B-V002", "values execute no action", value_action_count, 0, value_action_count == 0),
    ])
    write_csv(out / "gold_v2_19b_value_load_audit.csv", value_audit)

    upstream_stop = stop_count(checks19a) + stop_count(safety19a)
    forbidden_gates = forbidden_gate_count(gates19a, "allowed_after_19a_success")
    checks = pd.DataFrame([
        check_row("19B-C001", "19A status", s19a.get("status"), EXPECTED_19A, s19a.get("status") == EXPECTED_19A),
        check_row("19B-C002", "19A decision_planning_ready", s19a.get("decision_planning_ready"), True, bool(s19a.get("decision_planning_ready", False))),
        check_row("19B-C003", "19A total_stop_rows", s19a.get("total_stop_rows"), 0, s19a.get("total_stop_rows") == 0),
        check_row("19B-C004", "19A decision_collected", s19a.get("decision_collected"), False, s19a.get("decision_collected") is False),
        check_row("19B-C005", "19A decision_made", s19a.get("decision_made"), False, s19a.get("decision_made") is False),
        check_row("19B-C006", "19A approval_granted", s19a.get("approval_granted"), False, s19a.get("approval_granted") is False),
        check_row("19B-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19B-C008", "plan load audit STOP rows", stop_count(plan_audit), 0, stop_count(plan_audit) == 0),
        check_row("19B-C009", "field load audit STOP rows", stop_count(field_audit), 0, stop_count(field_audit) == 0),
        check_row("19B-C010", "value load audit STOP rows", stop_count(value_audit), 0, stop_count(value_audit) == 0),
        check_row("19B-C011", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19B_STOP_REVIEW_PLAN_LOAD_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19b_load_checks.csv", checks)
    write_csv(out / "gold_v2_19b_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19b_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19b_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "plan_load_smoke_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_19a_status": s19a.get("status"),
        "required_decision_fields": required_field_count,
        "allowed_decision_values": value_count,
        "total_stop_rows": int(total_stop),
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_19B_OUTPUTS",
    }
    write_json(out / "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 19B TIER2 source identity human decision intake actual decision plan load-smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19B load-smoked the 19A future human decision intake plan only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Load checks",
        md_table(checks),
        "",
        "## Plan load audit",
        md_table(plan_audit),
        "",
        "## Field load audit",
        md_table(field_audit),
        "",
        "## Value load audit",
        md_table(value_audit),
        "",
        "## Next gates",
        md_table(gates),
        "",
        "## Safety",
        md_table(sm),
    ]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
