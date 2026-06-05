#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_audit_only"
IN18X = "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only"
IN18Y = "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only"
IN18Z = "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only"
REFS = [
    "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only",
    "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only",
    "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only",
    "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only",
    "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only",
    "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only",
    "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only",
    "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only",
    "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only",
    "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only",
    "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only",
    "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only",
    "gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only",
    "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only",
    "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only",
    "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only",
]
REPORT = "GOLD_V2_18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18Z = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]


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


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    return int((df["status"].astype(str) == "STOP").sum()) if "status" in df.columns else 999


def ck(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def mdtable(df: pd.DataFrame, limit: int = 100) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def forbidden_gate_count(df: pd.DataFrame, col: str) -> int:
    if {"next_step", col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][col].map(truthy).sum())
    return 999


def summary_forbidden_true(summary: dict[str, Any]) -> int:
    n = sum(int(bool(summary.get(k, False))) for k in FORBIDDEN_SUMMARY_FLAGS)
    ext = summary.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18AB", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY", "Summarize blockers before any later human decision intake only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AA.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AA.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18aa_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["intake_reconciliation_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18ab_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AA-S001", "required inputs missing", "STOP"], ["18AA-S002", "18Z status not passed", "STOP"],
        ["18AA-S003", "decision collected or approval already made", "STOP"], ["18AA-S004", "upstream STOP rows present", "STOP"],
        ["18AA-S005", "field count reconciliation failed", "STOP"], ["18AA-S006", "value count reconciliation failed", "STOP"],
        ["18AA-S007", "template state reconciliation failed", "STOP"], ["18AA-S008", "forbidden gate allowed", "STOP"],
        ["18AA-S009", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18x, p18y, p18z = fx()/IN18X, fx()/IN18Y, fx()/IN18Z
    inputs = {
        "summary_18z": p18z / "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_summary.json",
        "content_checks_18z": p18z / "gold_v2_18z_content_checks.csv",
        "field_audit_18z": p18z / "gold_v2_18z_field_content_audit.csv",
        "value_audit_18z": p18z / "gold_v2_18z_value_content_audit.csv",
        "template_audit_18z": p18z / "gold_v2_18z_template_content_audit.csv",
        "gates_18z": p18z / "gold_v2_18z_required_next_gates.csv",
        "safety_18z": p18z / "gold_v2_18z_safety_matrix.csv",
        "report_18z": p18z / "GOLD_V2_18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY_REPORT.md",
        "summary_18y": p18y / "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json",
        "load_checks_18y": p18y / "gold_v2_18y_load_checks.csv",
        "template_audit_18y": p18y / "gold_v2_18y_template_audit.csv",
        "gates_18y": p18y / "gold_v2_18y_required_next_gates.csv",
        "safety_18y": p18y / "gold_v2_18y_safety_matrix.csv",
        "summary_18x": p18x / "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json",
        "fields_18x": p18x / "gold_v2_18x_required_intake_fields.csv",
        "values_18x": p18x / "gold_v2_18x_allowed_decision_values.csv",
        "template_18x": p18x / "gold_v2_18x_human_decision_template.json",
        "gates_18x": p18x / "gold_v2_18x_required_next_gates.csv",
        "safety_18x": p18x / "gold_v2_18x_safety_matrix.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18aa_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18AA-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18aa_reconciliation_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18aa_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18AA_STOP_MISSING_INPUTS", "audit_only": True, "intake_reconciliation_passed": False, "next_recommended_step": "STOP_REVIEW_18AA_INPUTS"}
        wjson(out / "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18AA intake reconciliation audit-only report\n\nStatus: `18AA_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18z, s18y, s18x = rjson(inputs["summary_18z"]), rjson(inputs["summary_18y"]), rjson(inputs["summary_18x"])
    z_checks, z_field, z_value, z_template, z_safe = rcsv(inputs["content_checks_18z"]), rcsv(inputs["field_audit_18z"]), rcsv(inputs["value_audit_18z"]), rcsv(inputs["template_audit_18z"]), rcsv(inputs["safety_18z"])
    y_load, y_template, y_safe = rcsv(inputs["load_checks_18y"]), rcsv(inputs["template_audit_18y"]), rcsv(inputs["safety_18y"])
    fields_x, values_x, template_x = rcsv(inputs["fields_18x"]), rcsv(inputs["values_18x"]), rjson(inputs["template_18x"])
    gates_x, gates_y, gates_z = rcsv(inputs["gates_18x"]), rcsv(inputs["gates_18y"]), rcsv(inputs["gates_18z"])
    x_required_count = int(fields_x.get("required", pd.Series(dtype=bool)).map(truthy).sum()) if not fields_x.empty else 0
    z_required_pass_count = int((z_field[z_field["field"].astype(str).isin(["decision_id", "decision_timestamp_utc", "decision_value", "human_reviewer", "evidence_acknowledged", "explicit_phrase"])] ["status"].astype(str) == "PASS").sum()) if "field" in z_field.columns else 0
    field_recon = pd.DataFrame([
        ["18AA-F001", "18X required field count vs 18Z required PASS count", x_required_count, z_required_pass_count, "PASS" if x_required_count == z_required_pass_count else "STOP"],
        ["18AA-F002", "18Z field audit STOP rows", stop_count(z_field), 0, "PASS" if stop_count(z_field) == 0 else "STOP"],
    ], columns=["recon_id", "check", "observed", "expected", "status"])
    x_value_count = int(len(values_x))
    z_value_pass_count = int((z_value[~z_value["decision_value"].astype(str).str.startswith("__")]["status"].astype(str) == "PASS").sum()) if "decision_value" in z_value.columns else 0
    value_recon = pd.DataFrame([
        ["18AA-V001", "18X value count vs 18Z value PASS count", x_value_count, z_value_pass_count, "PASS" if x_value_count == z_value_pass_count else "STOP"],
        ["18AA-V002", "18Z value audit STOP rows", stop_count(z_value), 0, "PASS" if stop_count(z_value) == 0 else "STOP"],
    ], columns=["recon_id", "check", "observed", "expected", "status"])
    y_template_stop = stop_count(y_template)
    z_template_stop = stop_count(z_template)
    template_unset = template_x.get("decision_value") == "UNSET" and template_x.get("script_validation_status") == "TEMPLATE_ONLY_NOT_A_DECISION"
    template_recon = pd.DataFrame([
        ["18AA-T001", "18X template remains unset", template_unset, True, "PASS" if template_unset else "STOP"],
        ["18AA-T002", "18Y template audit STOP rows", y_template_stop, 0, "PASS" if y_template_stop == 0 else "STOP"],
        ["18AA-T003", "18Z template content STOP rows", z_template_stop, 0, "PASS" if z_template_stop == 0 else "STOP"],
    ], columns=["recon_id", "check", "observed", "expected", "status"])
    upstream_stop = stop_count(z_checks) + stop_count(z_safe) + stop_count(y_load) + stop_count(y_safe)
    forbidden_gates = forbidden_gate_count(gates_x, "allowed_after_18x_success") + forbidden_gate_count(gates_y, "allowed_after_18y_success") + forbidden_gate_count(gates_z, "allowed_after_18z_success")
    summaries = []
    for name in REFS:
        path = fx() / name
        if lp(path).exists():
            found = list(lp(path).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in [s18x, s18y, s18z])
    checks = pd.DataFrame([
        ck("18AA-C001", "18Z status", s18z.get("status"), EXPECTED_18Z, s18z.get("status") == EXPECTED_18Z),
        ck("18AA-C002", "18Z intake_content_audit_passed", s18z.get("intake_content_audit_passed"), True, bool(s18z.get("intake_content_audit_passed", False))),
        ck("18AA-C003", "18Z total_stop_rows", s18z.get("total_stop_rows"), 0, s18z.get("total_stop_rows") == 0),
        ck("18AA-C004", "18X/18Y/18Z no collected decision/approval", no_decision, True, no_decision),
        ck("18AA-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18AA-C006", "field reconciliation STOP rows", stop_count(field_recon), 0, stop_count(field_recon) == 0),
        ck("18AA-C007", "value reconciliation STOP rows", stop_count(value_recon), 0, stop_count(value_recon) == 0),
        ck("18AA-C008", "template reconciliation STOP rows", stop_count(template_recon), 0, stop_count(template_recon) == 0),
        ck("18AA-C009", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18AA-C010", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = sum(stop_count(df) for df in [checks, field_recon, value_recon, template_recon])
    success = total_stop == 0
    status = SUCCESS if success else "18AA_STOP_REVIEW_INTAKE_RECONCILIATION_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18aa_reconciliation_checks.csv", checks),
        ("gold_v2_18aa_field_count_reconciliation.csv", field_recon),
        ("gold_v2_18aa_value_count_reconciliation.csv", value_recon),
        ("gold_v2_18aa_template_state_reconciliation.csv", template_recon),
        ("gold_v2_18aa_required_next_gates.csv", gates),
        ("gold_v2_18aa_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18aa_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "intake_reconciliation_passed": success, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "upstream_18z_status": s18z.get("status"), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18AB_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_BLOCKER_REVIEW_AUDIT_ONLY" if success else "STOP_REVIEW_18AA_OUTPUTS",
    }
    wjson(out / "gold_v2_18aa_tier2_source_identity_human_decision_intake_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 18AA TIER2 source identity human decision intake reconciliation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18AA reconciled 18X/18Y/18Z intake evidence only.", "- No decision was collected and no approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Reconciliation checks", mdtable(checks), "", "## Field reconciliation", mdtable(field_recon), "", "## Value reconciliation", mdtable(value_recon), "", "## Template reconciliation", mdtable(template_recon), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
