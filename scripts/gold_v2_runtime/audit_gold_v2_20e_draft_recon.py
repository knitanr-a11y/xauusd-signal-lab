#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_audit_only"
IN20B = "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only"
IN20C = "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only"
IN20D = "gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only"
REPORT = "GOLD_V2_20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20B = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20C = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20D = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "actual_decision_collection_allowed", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_DRAFT_FLAGS = [
    "approval_granted", "actual_decision_collection_allowed", "source_recovery_requested", "source_recovery_allowed",
    "source_identity_finalization_allowed", "source_identity_recovery_allowed", "ledger_source_of_truth_promotion_allowed",
    "oh_lc_replay_allowed", "live_evaluator_allowed", "live_or_final_implementation_allowed", "final_signal_allowed",
    "discord_send_allowed", "no_signal_discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed",
    "script_executes_action",
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
        ["20F", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY", "Final audit-only review of the still-unset draft package.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20E; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20E.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20E.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20e_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["draft_reconciliation_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"],
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
        ["next_gate_20f_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20E-S001", "required inputs missing", "STOP"],
        ["20E-S002", "upstream status not passed", "STOP"],
        ["20E-S003", "upstream STOP rows present", "STOP"],
        ["20E-S004", "decision value no longer UNSET or decision/approval collected", "STOP"],
        ["20E-S005", "actual decision collection allowed", "STOP"],
        ["20E-S006", "field/value row count conflict", "STOP"],
        ["20E-S007", "draft restricted flag true", "STOP"],
        ["20E-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20b, p20c, p20d = base / IN20B, base / IN20C, base / IN20D
    inputs = {
        "summary_20b": p20b / "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json",
        "draft_20b": p20b / "gold_v2_20b_decision_intake_draft.json",
        "checks_20b": p20b / "gold_v2_20b_draft_checks.csv",
        "gates_20b": p20b / "gold_v2_20b_required_next_gates.csv",
        "safety_20b": p20b / "gold_v2_20b_safety_matrix.csv",
        "summary_20c": p20c / "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json",
        "draft_load_20c": p20c / "gold_v2_20c_draft_load_audit.csv",
        "checks_20c": p20c / "gold_v2_20c_load_checks.csv",
        "gates_20c": p20c / "gold_v2_20c_required_next_gates.csv",
        "safety_20c": p20c / "gold_v2_20c_safety_matrix.csv",
        "summary_20d": p20d / "gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_summary.json",
        "checks_20d": p20d / "gold_v2_20d_content_checks.csv",
        "field_audit_20d": p20d / "gold_v2_20d_required_field_audit.csv",
        "value_audit_20d": p20d / "gold_v2_20d_allowed_value_audit.csv",
        "gates_20d": p20d / "gold_v2_20d_required_next_gates.csv",
        "safety_20d": p20d / "gold_v2_20d_safety_matrix.csv",
        "report_20d": p20d / "GOLD_V2_20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20e_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20e_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20E-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20e_reconciliation_checks.csv", checks)
        write_csv(out / "gold_v2_20e_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20e_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20E_STOP_MISSING_INPUTS",
            "audit_only": True,
            "reconciliation_passed": False,
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
            "actual_decision_collection_allowed": False,
            "total_stop_rows": 1,
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
            "next_recommended_step": "STOP_REVIEW_20E_INPUTS",
        }
        write_json(out / "gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20E draft reconciliation audit-only report\n\nStatus: `20E_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20b, s20c, s20d = read_json(inputs["summary_20b"]), read_json(inputs["summary_20c"]), read_json(inputs["summary_20d"])
    draft = read_json(inputs["draft_20b"])
    checks20b, checks20c, checks20d = read_csv(inputs["checks_20b"]), read_csv(inputs["checks_20c"]), read_csv(inputs["checks_20d"])
    safety20b, safety20c, safety20d = read_csv(inputs["safety_20b"]), read_csv(inputs["safety_20c"]), read_csv(inputs["safety_20d"])
    gates20b, gates20c, gates20d = read_csv(inputs["gates_20b"]), read_csv(inputs["gates_20c"]), read_csv(inputs["gates_20d"])
    draft_load20c = read_csv(inputs["draft_load_20c"])
    field_audit20d = read_csv(inputs["field_audit_20d"])
    value_audit20d = read_csv(inputs["value_audit_20d"])

    stage_status = pd.DataFrame([
        ["20B", s20b.get("status"), EXPECTED_20B, s20b.get("status") == EXPECTED_20B, s20b.get("decision_value"), s20b.get("total_stop_rows"), s20b.get("field_rows"), s20b.get("value_rows")],
        ["20C", s20c.get("status"), EXPECTED_20C, s20c.get("status") == EXPECTED_20C, s20c.get("decision_value"), s20c.get("total_stop_rows"), s20c.get("field_rows"), s20c.get("value_rows")],
        ["20D", s20d.get("status"), EXPECTED_20D, s20d.get("status") == EXPECTED_20D, s20d.get("decision_value"), s20d.get("total_stop_rows"), s20d.get("field_rows"), s20d.get("value_rows")],
    ], columns=["stage", "observed_status", "expected_status", "status_ok", "decision_value", "summary_stop_rows", "field_rows", "value_rows"])
    write_csv(out / "gold_v2_20e_stage_status_audit.csv", stage_status)

    upstream_stop = (
        stop_count(checks20b) + stop_count(safety20b) +
        stop_count(checks20c) + stop_count(draft_load20c) + stop_count(safety20c) +
        stop_count(checks20d) + stop_count(field_audit20d) + stop_count(value_audit20d) + stop_count(safety20d)
    )
    forbidden_gates = (
        forbidden_gate_count(gates20b, "allowed_after_20b_success") +
        forbidden_gate_count(gates20c, "allowed_after_20c_success") +
        forbidden_gate_count(gates20d, "allowed_after_20d_success")
    )
    forbidden_flags = forbidden_summary_count(s20b) + forbidden_summary_count(s20c) + forbidden_summary_count(s20d)
    decisions_not_unset = sum(int(s.get("decision_value") != "UNSET") for s in (s20b, s20c, s20d)) + int(draft.get("decision_value") != "UNSET")
    decision_flags_true = sum(int(bool(s.get(k, False))) for s in (s20b, s20c, s20d) for k in ("decision_collected", "decision_made", "approval_granted", "actual_decision_collection_allowed"))
    restricted_draft_true = sum(int(bool(draft.get(k, False))) for k in RESTRICTED_DRAFT_FLAGS)
    field_rows = [int(s.get("field_rows", -1)) for s in (s20b, s20c, s20d)]
    value_rows = [int(s.get("value_rows", -1)) for s in (s20b, s20c, s20d)]
    field_row_conflict = len(set(field_rows)) != 1
    value_row_conflict = len(set(value_rows)) != 1

    checks = pd.DataFrame([
        check_row("20E-C001", "20B status", s20b.get("status"), EXPECTED_20B, s20b.get("status") == EXPECTED_20B),
        check_row("20E-C002", "20C status", s20c.get("status"), EXPECTED_20C, s20c.get("status") == EXPECTED_20C),
        check_row("20E-C003", "20D status", s20d.get("status"), EXPECTED_20D, s20d.get("status") == EXPECTED_20D),
        check_row("20E-C004", "20B draft_ready", s20b.get("draft_ready"), True, bool(s20b.get("draft_ready", False))),
        check_row("20E-C005", "20C draft_load_smoke_passed", s20c.get("draft_load_smoke_passed"), True, bool(s20c.get("draft_load_smoke_passed", False))),
        check_row("20E-C006", "20D content_audit_passed", s20d.get("content_audit_passed"), True, bool(s20d.get("content_audit_passed", False))),
        check_row("20E-C007", "summary STOP rows", int(s20b.get("total_stop_rows", 999)) + int(s20c.get("total_stop_rows", 999)) + int(s20d.get("total_stop_rows", 999)), 0, int(s20b.get("total_stop_rows", 999)) + int(s20c.get("total_stop_rows", 999)) + int(s20d.get("total_stop_rows", 999)) == 0),
        check_row("20E-C008", "upstream artifact STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20E-C009", "decision values not UNSET", decisions_not_unset, 0, decisions_not_unset == 0),
        check_row("20E-C010", "decision/approval/collection flags true", decision_flags_true, 0, decision_flags_true == 0),
        check_row("20E-C011", "draft restricted flags true", restricted_draft_true, 0, restricted_draft_true == 0),
        check_row("20E-C012", "field row count conflict", field_row_conflict, False, not field_row_conflict),
        check_row("20E-C013", "value row count conflict", value_row_conflict, False, not value_row_conflict),
        check_row("20E-C014", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20E-C015", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20E_STOP_REVIEW_DRAFT_RECONCILIATION_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20e_reconciliation_checks.csv", checks)
    write_csv(out / "gold_v2_20e_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20e_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "reconciliation_passed": success,
        "decision_value": "UNSET",
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "field_rows": field_rows[0] if not field_row_conflict else field_rows,
        "value_rows": value_rows[0] if not value_row_conflict else value_rows,
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
        "next_recommended_step": "20F_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_AUDIT_ONLY" if success else "STOP_REVIEW_20E_OUTPUTS",
    }
    write_json(out / "gold_v2_20e_tier2_source_identity_human_decision_intake_draft_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 20E TIER2 source identity human decision intake draft reconciliation audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20E reconciled the unset actual decision intake draft package across 20B/20C/20D only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Reconciliation checks",
        md_table(checks),
        "",
        "## Stage status audit",
        md_table(stage_status),
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
