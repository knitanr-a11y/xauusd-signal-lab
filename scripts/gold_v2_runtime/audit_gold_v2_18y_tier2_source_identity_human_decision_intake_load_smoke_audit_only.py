#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only"
IN18X = "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only"
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
]
REPORT = "GOLD_V2_18Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18X = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
REQUIRED_FIELDS = {"decision_id", "decision_timestamp_utc", "decision_value", "human_reviewer", "evidence_acknowledged", "explicit_phrase"}
REQUIRED_VALUES = {"DEFER", "REQUEST_MORE_AUDIT", "REJECT_SOURCE_RECOVERY", "EXPLICIT_APPROVAL_CANDIDATE"}


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
        ["18Z", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY", "Content-audit intake template and validation tables only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18Y.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18Y.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18y_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["intake_load_smoke_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18z_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18Y-S001", "required inputs missing", "STOP"], ["18Y-S002", "18X status not passed", "STOP"],
        ["18Y-S003", "decision collected or approval already made", "STOP"], ["18Y-S004", "upstream STOP rows present", "STOP"],
        ["18Y-S005", "template not unset or unsafe", "STOP"], ["18Y-S006", "required fields or values missing", "STOP"],
        ["18Y-S007", "forbidden gate allowed", "STOP"], ["18Y-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18x = fx() / IN18X
    inputs = {
        "summary_18x": p18x / "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json",
        "checks_18x": p18x / "gold_v2_18x_intake_planning_checks.csv",
        "fields_18x": p18x / "gold_v2_18x_required_intake_fields.csv",
        "values_18x": p18x / "gold_v2_18x_allowed_decision_values.csv",
        "template_18x": p18x / "gold_v2_18x_human_decision_template.json",
        "gates_18x": p18x / "gold_v2_18x_required_next_gates.csv",
        "safety_18x": p18x / "gold_v2_18x_safety_matrix.csv",
        "report_18x": p18x / "GOLD_V2_18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18y_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18Y-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18y_load_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18y_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18Y_STOP_MISSING_INPUTS", "audit_only": True, "intake_load_smoke_passed": False, "next_recommended_step": "STOP_REVIEW_18Y_INPUTS"}
        wjson(out / "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18Y human decision intake load-smoke audit-only report\n\nStatus: `18Y_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18x = rjson(inputs["summary_18x"])
    checks18x, fields, values = rcsv(inputs["checks_18x"]), rcsv(inputs["fields_18x"]), rcsv(inputs["values_18x"])
    gates18x, safe18x = rcsv(inputs["gates_18x"]), rcsv(inputs["safety_18x"])
    template = rjson(inputs["template_18x"])
    observed_fields = set(fields.get("field", pd.Series(dtype=str)).astype(str))
    observed_values = set(values.get("decision_value", pd.Series(dtype=str)).astype(str))
    required_missing = sorted(REQUIRED_FIELDS - observed_fields)
    values_missing = sorted(REQUIRED_VALUES - observed_values)
    required_field_rows = int(fields.get("required", pd.Series(dtype=bool)).map(truthy).sum()) if not fields.empty else 0
    values_execute = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    template_audit = pd.DataFrame([
        ["18Y-T001", "decision_id unset", template.get("decision_id"), "UNSET", template.get("decision_id") == "UNSET"],
        ["18Y-T002", "decision_value unset", template.get("decision_value"), "UNSET", template.get("decision_value") == "UNSET"],
        ["18Y-T003", "human_reviewer unset", template.get("human_reviewer"), "UNSET", template.get("human_reviewer") == "UNSET"],
        ["18Y-T004", "evidence_acknowledged false", template.get("evidence_acknowledged"), False, template.get("evidence_acknowledged") is False],
        ["18Y-T005", "script_validation_status template only", template.get("script_validation_status"), "TEMPLATE_ONLY_NOT_A_DECISION", template.get("script_validation_status") == "TEMPLATE_ONLY_NOT_A_DECISION"],
        ["18Y-T006", "source_recovery_executed false", template.get("source_recovery_executed"), False, template.get("source_recovery_executed") is False],
        ["18Y-T007", "source_identity_finalized false", template.get("source_identity_finalized"), False, template.get("source_identity_finalized") is False],
        ["18Y-T008", "live_enabled false", template.get("live_enabled"), False, template.get("live_enabled") is False],
    ], columns=["template_check_id", "check", "observed", "expected", "ok"])
    template_audit["status"] = template_audit["ok"].map(lambda x: "PASS" if bool(x) else "STOP")
    template_audit = template_audit.drop(columns=["ok"])
    wcsv(template_audit, out / "gold_v2_18y_template_audit.csv")
    upstream_stop = stop_count(checks18x) + stop_count(safe18x)
    forbidden_gates = forbidden_gate_count(gates18x, "allowed_after_18x_success")
    summaries = []
    for name in REFS:
        path = fx() / name
        if lp(path).exists():
            found = list(lp(path).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    checks = pd.DataFrame([
        ck("18Y-C001", "18X status", s18x.get("status"), EXPECTED_18X, s18x.get("status") == EXPECTED_18X),
        ck("18Y-C002", "18X intake_planning_ready", s18x.get("intake_planning_ready"), True, bool(s18x.get("intake_planning_ready", False))),
        ck("18Y-C003", "18X total_stop_rows", s18x.get("total_stop_rows"), 0, s18x.get("total_stop_rows") == 0),
        ck("18Y-C004", "18X decision_collected", s18x.get("decision_collected"), False, s18x.get("decision_collected") is False),
        ck("18Y-C005", "18X decision_made", s18x.get("decision_made"), False, s18x.get("decision_made") is False),
        ck("18Y-C006", "18X approval_granted", s18x.get("approval_granted"), False, s18x.get("approval_granted") is False),
        ck("18Y-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18Y-C008", "missing required fields", len(required_missing), 0, len(required_missing) == 0),
        ck("18Y-C009", "required field rows", required_field_rows, ">=6", required_field_rows >= 6),
        ck("18Y-C010", "missing allowed values", len(values_missing), 0, len(values_missing) == 0),
        ck("18Y-C011", "allowed values execute no action", values_execute, 0, values_execute == 0),
        ck("18Y-C012", "template STOP rows", stop_count(template_audit), 0, stop_count(template_audit) == 0),
        ck("18Y-C013", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18Y-C014", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18Y_STOP_REVIEW_INTAKE_LOAD_SMOKE_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18y_load_checks.csv", checks),
        ("gold_v2_18y_required_next_gates.csv", gates),
        ("gold_v2_18y_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18y_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "intake_load_smoke_passed": success, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "upstream_18x_status": s18x.get("status"), "template_loaded": True, "required_fields_checked": int(len(fields)),
        "allowed_values_checked": int(len(values)), "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_18Y_OUTPUTS",
    }
    wjson(out / "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 18Y TIER2 source identity human decision intake load-smoke audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18Y load-smoked the unset human-decision intake template only.", "- No decision was collected and no approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Load checks", mdtable(checks), "", "## Template audit", mdtable(template_audit), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
