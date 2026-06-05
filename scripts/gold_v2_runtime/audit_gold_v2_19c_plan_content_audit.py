#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_only"
IN19A = "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only"
IN19B = "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only"
REPORT = "GOLD_V2_19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19B = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
REQUIRED_FIELDS = {
    "decision_id",
    "decision_timestamp_utc",
    "decision_value",
    "human_reviewer",
    "evidence_acknowledged",
    "explicit_phrase",
}
EXPECTED_VALUES = {"DEFER", "REQUEST_MORE_AUDIT", "REJECT_SOURCE_RECOVERY", "EXPLICIT_APPROVAL_CANDIDATE"}
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
        ["19D", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY", "Reconcile 19A/19B/19C decision plan evidence only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19C.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19C.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19c_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["decision_plan_content_audit_only", True, True, "PASS"],
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
        ["next_gate_19d_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19C-S001", "required inputs missing", "STOP"],
        ["19C-S002", "19B status not passed", "STOP"],
        ["19C-S003", "decision collected or approval already made", "STOP"],
        ["19C-S004", "upstream STOP rows present", "STOP"],
        ["19C-S005", "plan content missing plan-only prohibitions", "STOP"],
        ["19C-S006", "required field content invalid", "STOP"],
        ["19C-S007", "allowed value content invalid", "STOP"],
        ["19C-S008", "forbidden gate allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19a = base / IN19A
    p19b = base / IN19B
    inputs = {
        "summary_19b": p19b / "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_summary.json",
        "checks_19b": p19b / "gold_v2_19b_load_checks.csv",
        "plan_load_19b": p19b / "gold_v2_19b_plan_load_audit.csv",
        "field_load_19b": p19b / "gold_v2_19b_field_load_audit.csv",
        "value_load_19b": p19b / "gold_v2_19b_value_load_audit.csv",
        "gates_19b": p19b / "gold_v2_19b_required_next_gates.csv",
        "safety_19b": p19b / "gold_v2_19b_safety_matrix.csv",
        "report_19b": p19b / "GOLD_V2_19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "plan_19a": p19a / "gold_v2_19a_decision_intake_plan.md",
        "fields_19a": p19a / "gold_v2_19a_required_decision_fields.csv",
        "values_19a": p19a / "gold_v2_19a_allowed_decision_values.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19c_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19C-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19c_content_checks.csv", checks)
        write_csv(out / "gold_v2_19c_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19C_STOP_MISSING_INPUTS", "audit_only": True, "plan_content_audit_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19C_INPUTS"}
        write_json(out / "gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19C plan content audit-only report\n\nStatus: `19C_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19b = read_json(inputs["summary_19b"])
    checks19b = read_csv(inputs["checks_19b"])
    plan_load = read_csv(inputs["plan_load_19b"])
    field_load = read_csv(inputs["field_load_19b"])
    value_load = read_csv(inputs["value_load_19b"])
    gates19b = read_csv(inputs["gates_19b"])
    safety19b = read_csv(inputs["safety_19b"])
    plan_text = lp(inputs["plan_19a"]).read_text(encoding="utf-8")
    fields = read_csv(inputs["fields_19a"])
    values = read_csv(inputs["values_19a"])

    plan_lower = plan_text.lower()
    missing_plan_phrases = [p for p in REQUIRED_PLAN_PHRASES if p not in plan_lower]
    actual_decision_bad = int("not an actual decision" not in plan_lower or "no decision is collected" not in plan_lower)
    plan_content = pd.DataFrame([
        check_row("19C-P001", "plan text length", len(plan_text), ">0", len(plan_text) > 0),
        check_row("19C-P002", "plan required phrases missing", len(missing_plan_phrases), 0, len(missing_plan_phrases) == 0),
        check_row("19C-P003", "plan states not actual decision and no collection", actual_decision_bad, 0, actual_decision_bad == 0),
    ])
    write_csv(out / "gold_v2_19c_plan_content_audit.csv", plan_content)

    field_names = set(fields.get("field", pd.Series(dtype=str)).astype(str).tolist())
    missing_fields = sorted(REQUIRED_FIELDS - field_names)
    required_core_missing_required_true = 0
    if "field" in fields.columns and "required" in fields.columns:
        for f in REQUIRED_FIELDS:
            row = fields[fields["field"].astype(str) == f]
            if row.empty or not truthy(row.iloc[0].get("required")):
                required_core_missing_required_true += 1
    else:
        required_core_missing_required_true = 999
    field_content = pd.DataFrame([
        check_row("19C-F001", "required core fields missing", len(missing_fields), 0, len(missing_fields) == 0),
        check_row("19C-F002", "required core fields not required true", required_core_missing_required_true, 0, required_core_missing_required_true == 0),
    ])
    write_csv(out / "gold_v2_19c_field_content_audit.csv", field_content)

    value_names = set(values.get("decision_value", pd.Series(dtype=str)).astype(str).tolist())
    missing_values = sorted(EXPECTED_VALUES - value_names)
    extra_values = sorted(value_names - EXPECTED_VALUES)
    action_true = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    value_content = pd.DataFrame([
        check_row("19C-V001", "expected values missing", len(missing_values), 0, len(missing_values) == 0),
        check_row("19C-V002", "unexpected values", len(extra_values), 0, len(extra_values) == 0),
        check_row("19C-V003", "values execute no action", action_true, 0, action_true == 0),
    ])
    write_csv(out / "gold_v2_19c_value_content_audit.csv", value_content)

    upstream_stop = stop_count(checks19b) + stop_count(plan_load) + stop_count(field_load) + stop_count(value_load) + stop_count(safety19b)
    forbidden_gates = forbidden_gate_count(gates19b, "allowed_after_19b_success")
    checks = pd.DataFrame([
        check_row("19C-C001", "19B status", s19b.get("status"), EXPECTED_19B, s19b.get("status") == EXPECTED_19B),
        check_row("19C-C002", "19B plan_load_smoke_passed", s19b.get("plan_load_smoke_passed"), True, bool(s19b.get("plan_load_smoke_passed", False))),
        check_row("19C-C003", "19B total_stop_rows", s19b.get("total_stop_rows"), 0, s19b.get("total_stop_rows") == 0),
        check_row("19C-C004", "19B decision_collected", s19b.get("decision_collected"), False, s19b.get("decision_collected") is False),
        check_row("19C-C005", "19B decision_made", s19b.get("decision_made"), False, s19b.get("decision_made") is False),
        check_row("19C-C006", "19B approval_granted", s19b.get("approval_granted"), False, s19b.get("approval_granted") is False),
        check_row("19C-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19C-C008", "plan content STOP rows", stop_count(plan_content), 0, stop_count(plan_content) == 0),
        check_row("19C-C009", "field content STOP rows", stop_count(field_content), 0, stop_count(field_content) == 0),
        check_row("19C-C010", "value content STOP rows", stop_count(value_content), 0, stop_count(value_content) == 0),
        check_row("19C-C011", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19C_STOP_REVIEW_PLAN_CONTENT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19c_content_checks.csv", checks)
    write_csv(out / "gold_v2_19c_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19c_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19c_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "plan_content_audit_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_19b_status": s19b.get("status"),
        "required_core_fields": len(REQUIRED_FIELDS),
        "expected_decision_values": len(EXPECTED_VALUES),
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
        "next_recommended_step": "19D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_19C_OUTPUTS",
    }
    write_json(out / "gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_summary.json", summary)
    report = [
        "# GOLD V2 19C TIER2 source identity human decision intake actual decision plan content audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19C content-audited the 19A future human decision intake plan only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Content checks",
        md_table(checks),
        "",
        "## Plan content audit",
        md_table(plan_content),
        "",
        "## Field content audit",
        md_table(field_content),
        "",
        "## Value content audit",
        md_table(value_content),
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
