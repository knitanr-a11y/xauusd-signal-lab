#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_19d_tier2_source_identity_human_decision_intake_actual_decision_plan_reconciliation_audit_only"
IN19A = "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_audit_only"
IN19B = "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_audit_only"
IN19C = "gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_only"
REPORT = "GOLD_V2_19D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19C = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
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


def forbidden_summary_count(s: dict[str, Any]) -> int:
    n = sum(int(bool(s.get(k, False))) for k in FORBIDDEN_FLAGS)
    ext = s.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["19E", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_AUDIT_ONLY", "Review blockers after plan reconciliation only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19D.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19D.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19d_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["decision_plan_reconciliation_only", True, True, "PASS"],
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
        ["next_gate_19e_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19D-S001", "required inputs missing", "STOP"],
        ["19D-S002", "19C status not passed", "STOP"],
        ["19D-S003", "decision collected or approval already made", "STOP"],
        ["19D-S004", "upstream STOP rows present", "STOP"],
        ["19D-S005", "plan reconciliation failed", "STOP"],
        ["19D-S006", "field reconciliation failed", "STOP"],
        ["19D-S007", "value reconciliation failed", "STOP"],
        ["19D-S008", "forbidden gate or safety flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def extract_observed(df: pd.DataFrame, check_id: str) -> Any:
    if "check_id" not in df.columns:
        return None
    row = df[df["check_id"].astype(str) == check_id]
    if row.empty:
        return None
    return row.iloc[0].get("observed")


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19a, p19b, p19c = base / IN19A, base / IN19B, base / IN19C
    inputs = {
        "summary_19c": p19c / "gold_v2_19c_tier2_source_identity_human_decision_intake_actual_decision_plan_content_audit_summary.json",
        "checks_19c": p19c / "gold_v2_19c_content_checks.csv",
        "plan_content_19c": p19c / "gold_v2_19c_plan_content_audit.csv",
        "field_content_19c": p19c / "gold_v2_19c_field_content_audit.csv",
        "value_content_19c": p19c / "gold_v2_19c_value_content_audit.csv",
        "gates_19c": p19c / "gold_v2_19c_required_next_gates.csv",
        "safety_19c": p19c / "gold_v2_19c_safety_matrix.csv",
        "report_19c": p19c / "GOLD_V2_19C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_CONTENT_AUDIT_ONLY_REPORT.md",
        "summary_19b": p19b / "gold_v2_19b_tier2_source_identity_human_decision_intake_actual_decision_plan_load_smoke_summary.json",
        "plan_load_19b": p19b / "gold_v2_19b_plan_load_audit.csv",
        "field_load_19b": p19b / "gold_v2_19b_field_load_audit.csv",
        "value_load_19b": p19b / "gold_v2_19b_value_load_audit.csv",
        "summary_19a": p19a / "gold_v2_19a_tier2_source_identity_human_decision_intake_actual_decision_planning_summary.json",
        "plan_19a": p19a / "gold_v2_19a_decision_intake_plan.md",
        "fields_19a": p19a / "gold_v2_19a_required_decision_fields.csv",
        "values_19a": p19a / "gold_v2_19a_allowed_decision_values.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19d_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19D-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19d_reconciliation_checks.csv", checks)
        write_csv(out / "gold_v2_19d_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19D_STOP_MISSING_INPUTS", "audit_only": True, "plan_reconciliation_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19D_INPUTS"}
        write_json(out / "gold_v2_19d_tier2_source_identity_human_decision_intake_actual_decision_plan_reconciliation_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19D decision plan reconciliation audit-only report\n\nStatus: `19D_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19c = read_json(inputs["summary_19c"])
    s19b = read_json(inputs["summary_19b"])
    s19a = read_json(inputs["summary_19a"])
    checks19c = read_csv(inputs["checks_19c"])
    plan_content = read_csv(inputs["plan_content_19c"])
    field_content = read_csv(inputs["field_content_19c"])
    value_content = read_csv(inputs["value_content_19c"])
    gates19c = read_csv(inputs["gates_19c"])
    safety19c = read_csv(inputs["safety_19c"])
    plan_load = read_csv(inputs["plan_load_19b"])
    field_load = read_csv(inputs["field_load_19b"])
    value_load = read_csv(inputs["value_load_19b"])
    plan_text = lp(inputs["plan_19a"]).read_text(encoding="utf-8")
    fields = read_csv(inputs["fields_19a"])
    values = read_csv(inputs["values_19a"])

    plan_len_actual = len(plan_text)
    plan_len_19b = extract_observed(plan_load, "19B-P001")
    plan_len_19c = extract_observed(plan_content, "19C-P001")
    plan_recon = pd.DataFrame([
        check_row("19D-P001", "19A plan length vs 19B observed", plan_len_actual, plan_len_19b, str(plan_len_actual) == str(plan_len_19b)),
        check_row("19D-P002", "19A plan length vs 19C observed", plan_len_actual, plan_len_19c, str(plan_len_actual) == str(plan_len_19c)),
        check_row("19D-P003", "19B plan STOP rows", stop_count(plan_load), 0, stop_count(plan_load) == 0),
        check_row("19D-P004", "19C plan STOP rows", stop_count(plan_content), 0, stop_count(plan_content) == 0),
    ])
    write_csv(out / "gold_v2_19d_plan_reconciliation.csv", plan_recon)

    required_count_actual = int(fields.get("required", pd.Series(dtype=bool)).map(truthy).sum()) if not fields.empty else 0
    required_count_19b = extract_observed(field_load, "19B-F002")
    missing_19c = extract_observed(field_content, "19C-F001")
    field_recon = pd.DataFrame([
        check_row("19D-F001", "19A required field count vs 19B observed", required_count_actual, required_count_19b, str(required_count_actual) == str(required_count_19b)),
        check_row("19D-F002", "19C required fields missing", missing_19c, 0, str(missing_19c) == "0"),
        check_row("19D-F003", "19B field STOP rows", stop_count(field_load), 0, stop_count(field_load) == 0),
        check_row("19D-F004", "19C field STOP rows", stop_count(field_content), 0, stop_count(field_content) == 0),
    ])
    write_csv(out / "gold_v2_19d_field_reconciliation.csv", field_recon)

    value_count_actual = int(len(values))
    value_count_19b = extract_observed(value_load, "19B-V001")
    missing_values_19c = extract_observed(value_content, "19C-V001")
    action_values_19c = extract_observed(value_content, "19C-V003")
    value_recon = pd.DataFrame([
        check_row("19D-V001", "19A value count vs 19B observed", value_count_actual, value_count_19b, str(value_count_actual) == str(value_count_19b)),
        check_row("19D-V002", "19C expected values missing", missing_values_19c, 0, str(missing_values_19c) == "0"),
        check_row("19D-V003", "19C values execute no action", action_values_19c, 0, str(action_values_19c) == "0"),
        check_row("19D-V004", "19B value STOP rows", stop_count(value_load), 0, stop_count(value_load) == 0),
        check_row("19D-V005", "19C value STOP rows", stop_count(value_content), 0, stop_count(value_content) == 0),
    ])
    write_csv(out / "gold_v2_19d_value_reconciliation.csv", value_recon)

    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in [s19a, s19b, s19c])
    upstream_stop = stop_count(checks19c) + stop_count(safety19c)
    forbidden_gates = forbidden_gate_count(gates19c, "allowed_after_19c_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in [s19a, s19b, s19c])
    checks = pd.DataFrame([
        check_row("19D-C001", "19C status", s19c.get("status"), EXPECTED_19C, s19c.get("status") == EXPECTED_19C),
        check_row("19D-C002", "19C plan_content_audit_passed", s19c.get("plan_content_audit_passed"), True, bool(s19c.get("plan_content_audit_passed", False))),
        check_row("19D-C003", "19C total_stop_rows", s19c.get("total_stop_rows"), 0, s19c.get("total_stop_rows") == 0),
        check_row("19D-C004", "19A/19B/19C no decision/approval", no_decision, True, no_decision),
        check_row("19D-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19D-C006", "plan reconciliation STOP rows", stop_count(plan_recon), 0, stop_count(plan_recon) == 0),
        check_row("19D-C007", "field reconciliation STOP rows", stop_count(field_recon), 0, stop_count(field_recon) == 0),
        check_row("19D-C008", "value reconciliation STOP rows", stop_count(value_recon), 0, stop_count(value_recon) == 0),
        check_row("19D-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("19D-C010", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19D_STOP_REVIEW_PLAN_RECONCILIATION_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19d_reconciliation_checks.csv", checks)
    write_csv(out / "gold_v2_19d_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19d_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19d_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "plan_reconciliation_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_19c_status": s19c.get("status"),
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
        "next_recommended_step": "19E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_PLAN_BLOCKER_REVIEW_AUDIT_ONLY" if success else "STOP_REVIEW_19D_OUTPUTS",
    }
    write_json(out / "gold_v2_19d_tier2_source_identity_human_decision_intake_actual_decision_plan_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 19D TIER2 source identity human decision intake actual decision plan reconciliation audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19D reconciled 19A/19B/19C future human decision intake planning evidence only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Reconciliation checks",
        md_table(checks),
        "",
        "## Plan reconciliation",
        md_table(plan_recon),
        "",
        "## Field reconciliation",
        md_table(field_recon),
        "",
        "## Value reconciliation",
        md_table(value_recon),
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
