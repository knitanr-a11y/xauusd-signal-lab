#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_audit_only"
IN19H = "gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only"
IN19I = "gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_audit_only"
IN19J = "gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_only"
REPORT = "GOLD_V2_19K_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_19J = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
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


def extract_observed(df: pd.DataFrame, check_id: str) -> Any:
    if "check_id" not in df.columns:
        return None
    row = df[df["check_id"].astype(str) == check_id]
    if row.empty:
        return None
    return row.iloc[0].get("observed")


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["19L", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY", "Review blockers after template reconciliation only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 19K.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 19K.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_19k_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["template_reconciliation_only", True, True, "PASS"],
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
        ["next_gate_19l_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["19K-S001", "required inputs missing", "STOP"],
        ["19K-S002", "19J status not passed", "STOP"],
        ["19K-S003", "decision collected or approval already made", "STOP"],
        ["19K-S004", "upstream STOP rows present", "STOP"],
        ["19K-S005", "template reconciliation failed", "STOP"],
        ["19K-S006", "field reconciliation failed", "STOP"],
        ["19K-S007", "value reconciliation failed", "STOP"],
        ["19K-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p19h, p19i, p19j = base / IN19H, base / IN19I, base / IN19J
    inputs = {
        "summary_19j": p19j / "gold_v2_19j_tier2_source_identity_human_decision_intake_actual_decision_template_content_audit_summary.json",
        "checks_19j": p19j / "gold_v2_19j_content_checks.csv",
        "template_content_19j": p19j / "gold_v2_19j_template_content_audit.csv",
        "field_content_19j": p19j / "gold_v2_19j_field_content_audit.csv",
        "value_content_19j": p19j / "gold_v2_19j_value_content_audit.csv",
        "gates_19j": p19j / "gold_v2_19j_required_next_gates.csv",
        "safety_19j": p19j / "gold_v2_19j_safety_matrix.csv",
        "report_19j": p19j / "GOLD_V2_19J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_CONTENT_AUDIT_ONLY_REPORT.md",
        "summary_19i": p19i / "gold_v2_19i_tier2_source_identity_human_decision_intake_actual_decision_template_load_smoke_summary.json",
        "load_audit_19i": p19i / "gold_v2_19i_template_load_audit.csv",
        "summary_19h": p19h / "gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_summary.json",
        "template_19h": p19h / "gold_v2_19h_actual_decision_template.json",
        "fields_19h": p19h / "gold_v2_19h_required_decision_fields.csv",
        "values_19h": p19h / "gold_v2_19h_allowed_decision_values.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_19k_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("19K-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_19k_reconciliation_checks.csv", checks)
        write_csv(out / "gold_v2_19k_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "19K_STOP_MISSING_INPUTS", "audit_only": True, "template_reconciliation_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_19K_INPUTS"}
        write_json(out / "gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 19K template reconciliation audit-only report\n\nStatus: `19K_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s19j = read_json(inputs["summary_19j"])
    s19i = read_json(inputs["summary_19i"])
    s19h = read_json(inputs["summary_19h"])
    checks19j = read_csv(inputs["checks_19j"])
    tmpl_content = read_csv(inputs["template_content_19j"])
    field_content = read_csv(inputs["field_content_19j"])
    value_content = read_csv(inputs["value_content_19j"])
    gates19j = read_csv(inputs["gates_19j"])
    safety19j = read_csv(inputs["safety_19j"])
    load_audit = read_csv(inputs["load_audit_19i"])
    template = read_json(inputs["template_19h"])
    fields = read_csv(inputs["fields_19h"])
    values = read_csv(inputs["values_19h"])

    tmpl_status = template.get("template_status")
    decision_value = template.get("decision_value")
    tmpl_status_19i = extract_observed(load_audit, "19I-T002")
    decision_value_19j = extract_observed(tmpl_content, "19J-T005")
    template_recon = pd.DataFrame([
        check_row("19K-T001", "19H template_status vs 19I", tmpl_status, tmpl_status_19i, str(tmpl_status) == str(tmpl_status_19i)),
        check_row("19K-T002", "19H decision_value vs 19J", decision_value, decision_value_19j, str(decision_value) == str(decision_value_19j)),
        check_row("19K-T003", "19I load audit STOP rows", stop_count(load_audit), 0, stop_count(load_audit) == 0),
        check_row("19K-T004", "19J template content STOP rows", stop_count(tmpl_content), 0, stop_count(tmpl_content) == 0),
    ])
    write_csv(out / "gold_v2_19k_template_reconciliation.csv", template_recon)

    field_rows = int(len(fields))
    missing_fields_19j = extract_observed(field_content, "19J-F001")
    field_recon = pd.DataFrame([
        check_row("19K-F001", "19H field rows", field_rows, ">=6", field_rows >= 6),
        check_row("19K-F002", "19J required fields missing", missing_fields_19j, 0, str(missing_fields_19j) == "0"),
        check_row("19K-F003", "19J field content STOP rows", stop_count(field_content), 0, stop_count(field_content) == 0),
    ])
    write_csv(out / "gold_v2_19k_field_reconciliation.csv", field_recon)

    value_rows = int(len(values))
    missing_values_19j = extract_observed(value_content, "19J-V001")
    action_values_19j = extract_observed(value_content, "19J-V003")
    allowed_count_19j = extract_observed(value_content, "19J-V004")
    value_recon = pd.DataFrame([
        check_row("19K-V001", "19H value rows vs 19J template allowed count", value_rows, allowed_count_19j, str(value_rows) == str(allowed_count_19j)),
        check_row("19K-V002", "19J expected values missing", missing_values_19j, 0, str(missing_values_19j) == "0"),
        check_row("19K-V003", "19J values execute no action", action_values_19j, 0, str(action_values_19j) == "0"),
        check_row("19K-V004", "19J value content STOP rows", stop_count(value_content), 0, stop_count(value_content) == 0),
    ])
    write_csv(out / "gold_v2_19k_value_reconciliation.csv", value_recon)

    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in [s19h, s19i, s19j])
    upstream_stop = stop_count(checks19j) + stop_count(safety19j)
    forbidden_gates = forbidden_gate_count(gates19j, "allowed_after_19j_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in [s19h, s19i, s19j])
    checks = pd.DataFrame([
        check_row("19K-C001", "19J status", s19j.get("status"), EXPECTED_19J, s19j.get("status") == EXPECTED_19J),
        check_row("19K-C002", "19J template_content_audit_passed", s19j.get("template_content_audit_passed"), True, bool(s19j.get("template_content_audit_passed", False))),
        check_row("19K-C003", "19J total_stop_rows", s19j.get("total_stop_rows"), 0, s19j.get("total_stop_rows") == 0),
        check_row("19K-C004", "19H/19I/19J no decision/approval", no_decision, True, no_decision),
        check_row("19K-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("19K-C006", "template reconciliation STOP rows", stop_count(template_recon), 0, stop_count(template_recon) == 0),
        check_row("19K-C007", "field reconciliation STOP rows", stop_count(field_recon), 0, stop_count(field_recon) == 0),
        check_row("19K-C008", "value reconciliation STOP rows", stop_count(value_recon), 0, stop_count(value_recon) == 0),
        check_row("19K-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("19K-C010", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "19K_STOP_REVIEW_TEMPLATE_RECONCILIATION_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_19k_reconciliation_checks.csv", checks)
    write_csv(out / "gold_v2_19k_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_19k_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_19k_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "template_reconciliation_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "template_status": template.get("template_status"),
        "decision_value": template.get("decision_value"),
        "upstream_19j_status": s19j.get("status"),
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
        "next_recommended_step": "19L_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_TEMPLATE_BLOCKER_REVIEW_AUDIT_ONLY" if success else "STOP_REVIEW_19K_OUTPUTS",
    }
    write_json(out / "gold_v2_19k_tier2_source_identity_human_decision_intake_actual_decision_template_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 19K TIER2 source identity human decision intake actual decision template reconciliation audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 19K reconciled the still-unset actual human decision template evidence only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Reconciliation checks",
        md_table(checks),
        "",
        "## Template reconciliation",
        md_table(template_recon),
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
