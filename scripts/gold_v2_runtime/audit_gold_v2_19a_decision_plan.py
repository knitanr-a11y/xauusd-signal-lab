#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY"
OUT_DIR = "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only"
IN18AI = "gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_audit_only"
IN18X = "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only"
REPORT = "GOLD_V2_19A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AI = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
REQUIRED_PLAN_PHRASES = [
    "plan-only",
    "not an actual decision",
    "no approval",
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
        ["19B", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY", "Load-smoke 19A decision intake plan only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19A.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19A.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19a_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["decision_intake_planning_only", True, True, "PASS"],
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
        ["next_gate_19b_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19A-S001", "required inputs missing", "STOP"],
        ["19A-S002", "18AI status not passed", "STOP"],
        ["19A-S003", "decision collected or approval already made", "STOP"],
        ["19A-S004", "upstream STOP rows present", "STOP"],
        ["19A-S005", "future intake field or value plan invalid", "STOP"],
        ["19A-S006", "template already contains a decision", "STOP"],
        ["19A-S007", "plan text missing plan-only prohibitions", "STOP"],
        ["19A-S008", "forbidden gate allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def build_plan(now: str, fields: pd.DataFrame, values: pd.DataFrame) -> str:
    field_lines = [f"- {row.get('field', '')}: required={row.get('required', '')}, type={row.get('type', '')}" for _, row in fields.iterrows()]
    value_lines = [f"- {row.get('decision_value', '')}: executes_action_in_18x={row.get('executes_action_in_18x', '')}" for _, row in values.iterrows()]
    return "\n".join([
        "# GOLD V2 19A actual human decision intake plan audit-only",
        "",
        f"Created UTC: {now}",
        "",
        "This is plan-only and not an actual decision.",
        "No decision is collected by 19A.",
        "No approval is granted by 19A.",
        "No source recovery is executed by 19A.",
        "No source identity finalization is performed by 19A.",
        "No live enablement is allowed by 19A.",
        "No final signal is allowed by 19A.",
        "",
        "## Future required intake fields",
        *field_lines,
        "",
        "## Future allowed decision values",
        *value_lines,
        "",
        "## Future validation concept",
        "A later step may load-smoke this plan before any actual human decision intake is accepted.",
        "Any later actual intake must be explicit, complete, evidence-acknowledged, and separately audited.",
    ])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18ai, p18x = base / IN18AI, base / IN18X
    inputs = {
        "summary_18ai": p18ai / "gold_v2_18ai_tier2_source_identity_human_decision_intake_final_handoff_summary.json",
        "checks_18ai": p18ai / "gold_v2_18ai_handoff_checks.csv",
        "note_18ai": p18ai / "gold_v2_18ai_handoff_note.md",
        "gates_18ai": p18ai / "gold_v2_18ai_required_next_gates.csv",
        "safety_18ai": p18ai / "gold_v2_18ai_safety_matrix.csv",
        "report_18ai": p18ai / "GOLD_V2_18AI_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md",
        "fields_18x": p18x / "gold_v2_18x_required_intake_fields.csv",
        "values_18x": p18x / "gold_v2_18x_allowed_decision_values.csv",
        "template_18x": p18x / "gold_v2_18x_human_decision_template.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19a_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19A-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19a_planning_checks.csv", checks)
        write_csv(out / "gold_v2_19a_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19A_STOP_MISSING_INPUTS", "audit_only": True, "decision_planning_ready": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19A_INPUTS"}
        write_json(out / "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19A decision planning audit-only report\n\nStatus: `19A_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18ai = read_json(inputs["summary_18ai"])
    checks18ai = read_csv(inputs["checks_18ai"])
    gates18ai = read_csv(inputs["gates_18ai"])
    safety18ai = read_csv(inputs["safety_18ai"])
    fields = read_csv(inputs["fields_18x"])
    values = read_csv(inputs["values_18x"])
    template = read_json(inputs["template_18x"])
    plan = build_plan(now, fields, values)
    write_text(out / "gold_v2_19a_decision_intake_plan.md", plan)
    write_csv(out / "gold_v2_19a_required_decision_fields.csv", fields)
    write_csv(out / "gold_v2_19a_allowed_decision_values.csv", values)
    required_field_count = int(fields.get("required", pd.Series(dtype=bool)).map(truthy).sum()) if not fields.empty else 0
    value_count = int(len(values))
    value_action_count = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    template_unset = template.get("decision_value") == "UNSET" and template.get("script_validation_status") == "TEMPLATE_ONLY_NOT_A_DECISION"
    plan_lower = plan.lower()
    missing_phrases = [phrase for phrase in REQUIRED_PLAN_PHRASES if phrase not in plan_lower]
    upstream_stop = stop_count(checks18ai) + stop_count(safety18ai)
    forbidden_gates = forbidden_gate_count(gates18ai, "allowed_after_18ai_success")
    checks = pd.DataFrame([
        check_row("19A-C001", "18AI status", s18ai.get("status"), EXPECTED_18AI, s18ai.get("status") == EXPECTED_18AI),
        check_row("19A-C002", "18AI handoff_ready", s18ai.get("handoff_ready"), True, bool(s18ai.get("handoff_ready", False))),
        check_row("19A-C003", "18AI total_stop_rows", s18ai.get("total_stop_rows"), 0, s18ai.get("total_stop_rows") == 0),
        check_row("19A-C004", "18AI decision_collected", s18ai.get("decision_collected"), False, s18ai.get("decision_collected") is False),
        check_row("19A-C005", "18AI decision_made", s18ai.get("decision_made"), False, s18ai.get("decision_made") is False),
        check_row("19A-C006", "18AI approval_granted", s18ai.get("approval_granted"), False, s18ai.get("approval_granted") is False),
        check_row("19A-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19A-C008", "required future fields", required_field_count, ">=6", required_field_count >= 6),
        check_row("19A-C009", "allowed future decision values", value_count, ">=4", value_count >= 4),
        check_row("19A-C010", "decision values execute no action", value_action_count, 0, value_action_count == 0),
        check_row("19A-C011", "template remains unset", template_unset, True, template_unset),
        check_row("19A-C012", "plan required phrases missing", len(missing_phrases), 0, len(missing_phrases) == 0),
        check_row("19A-C013", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19A_STOP_REVIEW_DECISION_PLAN_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19a_planning_checks.csv", checks)
    write_csv(out / "gold_v2_19a_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19a_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19a_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "decision_planning_ready": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18ai_status": s18ai.get("status"),
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
        "next_recommended_step": "19B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_19A_OUTPUTS",
    }
    write_json(out / "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_summary.json", summary)
    report = [
        "# GOLD V2 19A TIER2 source identity human decision intake actual decision planning audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19A prepared a plan for a later actual human decision intake only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Planning checks",
        md_table(checks),
        "",
        "## Decision intake plan",
        plan,
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
