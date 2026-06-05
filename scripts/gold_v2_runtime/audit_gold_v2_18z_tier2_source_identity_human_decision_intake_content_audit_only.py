#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_only"
IN18Y = "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only"
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
    "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_audit_only",
]
REPORT = "GOLD_V2_18Z_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18Y = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
EXPECTED_FIELDS = {
    "decision_id": {"type": "string", "required": True},
    "decision_timestamp_utc": {"type": "string", "required": True},
    "decision_value": {"type": "enum", "required": True},
    "human_reviewer": {"type": "string", "required": True},
    "evidence_acknowledged": {"type": "boolean", "required": True},
    "explicit_phrase": {"type": "string", "required": True},
    "notes": {"type": "string", "required": False},
}
EXPECTED_VALUES = {"DEFER", "REQUEST_MORE_AUDIT", "REJECT_SOURCE_RECOVERY", "EXPLICIT_APPROVAL_CANDIDATE"}


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
        ["18AA", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY", "Reconcile 18X/18Y/18Z intake evidence only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18Z.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18Z.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18z_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["intake_content_audit_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18aa_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18Z-S001", "required inputs missing", "STOP"], ["18Z-S002", "18Y status not passed", "STOP"],
        ["18Z-S003", "decision collected or approval already made", "STOP"], ["18Z-S004", "upstream STOP rows present", "STOP"],
        ["18Z-S005", "field content invalid", "STOP"], ["18Z-S006", "value content invalid", "STOP"],
        ["18Z-S007", "template content unsafe", "STOP"], ["18Z-S008", "forbidden gate allowed", "STOP"],
        ["18Z-S009", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18y, p18x = fx() / IN18Y, fx() / IN18X
    inputs = {
        "summary_18y": p18y / "gold_v2_18y_tier2_source_identity_human_decision_intake_load_smoke_summary.json",
        "load_checks_18y": p18y / "gold_v2_18y_load_checks.csv",
        "template_audit_18y": p18y / "gold_v2_18y_template_audit.csv",
        "gates_18y": p18y / "gold_v2_18y_required_next_gates.csv",
        "safety_18y": p18y / "gold_v2_18y_safety_matrix.csv",
        "report_18y": p18y / "GOLD_V2_18Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "fields_18x": p18x / "gold_v2_18x_required_intake_fields.csv",
        "values_18x": p18x / "gold_v2_18x_allowed_decision_values.csv",
        "template_18x": p18x / "gold_v2_18x_human_decision_template.json",
        "gates_18x": p18x / "gold_v2_18x_required_next_gates.csv",
        "safety_18x": p18x / "gold_v2_18x_safety_matrix.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18z_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18Z-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18z_content_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18z_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18Z_STOP_MISSING_INPUTS", "audit_only": True, "intake_content_audit_passed": False, "next_recommended_step": "STOP_REVIEW_18Z_INPUTS"}
        wjson(out / "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18Z intake content audit-only report\n\nStatus: `18Z_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18y = rjson(inputs["summary_18y"])
    load18y, template_audit18y, safe18y = rcsv(inputs["load_checks_18y"]), rcsv(inputs["template_audit_18y"]), rcsv(inputs["safety_18y"])
    fields, values, template = rcsv(inputs["fields_18x"]), rcsv(inputs["values_18x"]), rjson(inputs["template_18x"])
    gates18y, gates18x = rcsv(inputs["gates_18y"]), rcsv(inputs["gates_18x"])
    field_rows = []
    field_names = fields.get("field", pd.Series(dtype=str)).astype(str).tolist()
    for field, expected in EXPECTED_FIELDS.items():
        row = fields[fields.get("field", pd.Series(dtype=str)).astype(str) == field]
        exists = len(row) == 1
        type_ok = exists and str(row.iloc[0].get("type", "")) == expected["type"]
        req_ok = exists and truthy(row.iloc[0].get("required", False)) == bool(expected["required"])
        req_text_ok = exists and bool(str(row.iloc[0].get("requirement", "")).strip())
        ok = exists and type_ok and req_ok and req_text_ok
        field_rows.append([field, exists, row.iloc[0].get("type", "MISSING") if exists else "MISSING", expected["type"], row.iloc[0].get("required", "MISSING") if exists else "MISSING", expected["required"], ok, "PASS" if ok else "STOP"])
    duplicate_fields = len(field_names) - len(set(field_names))
    field_audit = pd.DataFrame(field_rows, columns=["field", "exists_once", "observed_type", "expected_type", "observed_required", "expected_required", "ok", "status"])
    field_audit = pd.concat([field_audit, pd.DataFrame([{"field": "__duplicate_field_count__", "exists_once": True, "observed_type": duplicate_fields, "expected_type": 0, "observed_required": "", "expected_required": "", "ok": duplicate_fields == 0, "status": "PASS" if duplicate_fields == 0 else "STOP"}])], ignore_index=True)
    field_audit = field_audit.drop(columns=["ok"])
    value_names = values.get("decision_value", pd.Series(dtype=str)).astype(str).tolist()
    value_rows = []
    for val in EXPECTED_VALUES:
        row = values[values.get("decision_value", pd.Series(dtype=str)).astype(str) == val]
        exists = len(row) == 1
        executes = truthy(row.iloc[0].get("executes_action_in_18x", True)) if exists else True
        meaning = str(row.iloc[0].get("meaning", "")) if exists else ""
        meaning_ok = bool(meaning.strip())
        approval_candidate_safe = True
        if val == "EXPLICIT_APPROVAL_CANDIDATE":
            low = meaning.lower()
            approval_candidate_safe = ("later" in low or "guarded" in low) and not executes
        ok = exists and not executes and meaning_ok and approval_candidate_safe
        value_rows.append([val, exists, meaning, executes, approval_candidate_safe, "PASS" if ok else "STOP"])
    duplicate_values = len(value_names) - len(set(value_names))
    value_audit = pd.DataFrame(value_rows, columns=["decision_value", "exists_once", "meaning", "executes_action_in_18x", "approval_candidate_guarded", "status"])
    value_audit = pd.concat([value_audit, pd.DataFrame([{"decision_value": "__duplicate_value_count__", "exists_once": True, "meaning": duplicate_values, "executes_action_in_18x": False, "approval_candidate_guarded": True, "status": "PASS" if duplicate_values == 0 else "STOP"}])], ignore_index=True)
    template_rows = [
        ["decision_id", template.get("decision_id"), "UNSET", template.get("decision_id") == "UNSET"],
        ["decision_timestamp_utc", template.get("decision_timestamp_utc"), None, template.get("decision_timestamp_utc") is None],
        ["decision_value", template.get("decision_value"), "UNSET", template.get("decision_value") == "UNSET"],
        ["human_reviewer", template.get("human_reviewer"), "UNSET", template.get("human_reviewer") == "UNSET"],
        ["evidence_acknowledged", template.get("evidence_acknowledged"), False, template.get("evidence_acknowledged") is False],
        ["explicit_phrase", template.get("explicit_phrase"), "UNSET", template.get("explicit_phrase") == "UNSET"],
        ["script_validation_status", template.get("script_validation_status"), "TEMPLATE_ONLY_NOT_A_DECISION", template.get("script_validation_status") == "TEMPLATE_ONLY_NOT_A_DECISION"],
        ["source_recovery_executed", template.get("source_recovery_executed"), False, template.get("source_recovery_executed") is False],
        ["source_identity_finalized", template.get("source_identity_finalized"), False, template.get("source_identity_finalized") is False],
        ["live_enabled", template.get("live_enabled"), False, template.get("live_enabled") is False],
    ]
    template_content = pd.DataFrame([[f"18Z-T{i+1:03d}", item, obs, exp, "PASS" if ok else "STOP"] for i, (item, obs, exp, ok) in enumerate(template_rows)], columns=["template_check_id", "item", "observed", "expected", "status"])
    for name, df in [("gold_v2_18z_field_content_audit.csv", field_audit), ("gold_v2_18z_value_content_audit.csv", value_audit), ("gold_v2_18z_template_content_audit.csv", template_content)]:
        wcsv(df, out / name)
    upstream_stop = stop_count(load18y) + stop_count(template_audit18y) + stop_count(safe18y)
    forbidden_gates = forbidden_gate_count(gates18y, "allowed_after_18y_success") + forbidden_gate_count(gates18x, "allowed_after_18x_success")
    summaries = []
    for name in REFS:
        path = fx() / name
        if lp(path).exists():
            found = list(lp(path).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    checks = pd.DataFrame([
        ck("18Z-C001", "18Y status", s18y.get("status"), EXPECTED_18Y, s18y.get("status") == EXPECTED_18Y),
        ck("18Z-C002", "18Y intake_load_smoke_passed", s18y.get("intake_load_smoke_passed"), True, bool(s18y.get("intake_load_smoke_passed", False))),
        ck("18Z-C003", "18Y total_stop_rows", s18y.get("total_stop_rows"), 0, s18y.get("total_stop_rows") == 0),
        ck("18Z-C004", "18Y decision_collected", s18y.get("decision_collected"), False, s18y.get("decision_collected") is False),
        ck("18Z-C005", "18Y decision_made", s18y.get("decision_made"), False, s18y.get("decision_made") is False),
        ck("18Z-C006", "18Y approval_granted", s18y.get("approval_granted"), False, s18y.get("approval_granted") is False),
        ck("18Z-C007", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18Z-C008", "field audit STOP rows", stop_count(field_audit), 0, stop_count(field_audit) == 0),
        ck("18Z-C009", "value audit STOP rows", stop_count(value_audit), 0, stop_count(value_audit) == 0),
        ck("18Z-C010", "template content STOP rows", stop_count(template_content), 0, stop_count(template_content) == 0),
        ck("18Z-C011", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18Z-C012", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18Z_STOP_REVIEW_INTAKE_CONTENT_AUDIT_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18z_content_checks.csv", checks),
        ("gold_v2_18z_required_next_gates.csv", gates),
        ("gold_v2_18z_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18z_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "intake_content_audit_passed": success, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "upstream_18y_status": s18y.get("status"), "field_rows_checked": int(len(fields)),
        "allowed_values_checked": int(len(values)), "template_checked": True, "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18AA_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_18Z_OUTPUTS",
    }
    wjson(out / "gold_v2_18z_tier2_source_identity_human_decision_intake_content_audit_summary.json", summary)
    report = [
        "# GOLD V2 18Z TIER2 source identity human decision intake content audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18Z content-audited the unset human-decision intake template and validation tables only.", "- No decision was collected and no approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Content checks", mdtable(checks), "", "## Field content audit", mdtable(field_audit), "", "## Value content audit", mdtable(value_audit), "", "## Template content audit", mdtable(template_content), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
