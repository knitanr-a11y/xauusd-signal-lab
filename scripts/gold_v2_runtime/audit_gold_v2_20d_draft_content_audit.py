#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_only"
IN20C = "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_audit_only"
IN20B = "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only"
REPORT = "GOLD_V2_20D_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20C = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
AUTH_SCOPE = "ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY"

# 20D may validate that the minimum intake fields exist, but must not invent allowed
# decision values. The allowed decision values are source-defined by the 19H/20B
# artifacts and are audited for structure/no-action only.
EXPECTED_FIELDS = {"decision_id", "decision_timestamp_utc", "decision_value", "human_reviewer", "evidence_acknowledged", "explicit_phrase"}
MIN_ALLOWED_VALUE_ROWS = 4

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
UNSET_FIELDS = ["decision_id", "decision_timestamp_utc", "decision_value", "human_reviewer", "explicit_phrase", "notes"]


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


def first_existing_col(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    for col in names:
        if col in df.columns:
            return col
    return None


def field_values(df: pd.DataFrame) -> list[str]:
    col = first_existing_col(df, ("field_name", "field", "name"))
    if col is None:
        return []
    return df[col].astype(str).str.strip().tolist()


def decision_values(df: pd.DataFrame) -> list[str]:
    col = first_existing_col(df, ("decision_value", "value", "name"))
    if col is None:
        return []
    return df[col].astype(str).str.strip().tolist()


def expected_field_required_false_count(fields: pd.DataFrame, fvals: list[str]) -> int:
    """Count required=false only for the expected core intake fields.

    Optional fields such as notes are allowed to be non-required and must not stop
    the audit. A missing required column is still a STOP condition.
    """
    field_col = first_existing_col(fields, ("field_name", "field", "name"))
    if field_col is None or "required" not in fields.columns:
        return 999
    mask = fields[field_col].astype(str).str.strip().isin(EXPECTED_FIELDS)
    return int(fields.loc[mask, "required"].map(lambda x: not truthy(x)).sum())


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["20E", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY", "Reconcile draft preparation/load/content audits only.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20D; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20D.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20D.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20d_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["draft_content_audit_only", True, True, "PASS"],
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
        ["next_gate_20e_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20D-S001", "required inputs missing", "STOP"],
        ["20D-S002", "20C status not passed", "STOP"],
        ["20D-S003", "draft content no longer unset/no-action", "STOP"],
        ["20D-S004", "core required fields missing, duplicated, or marked non-required", "STOP"],
        ["20D-S005", "allowed value source malformed, duplicated, empty, too small, or action-executing", "STOP"],
        ["20D-S006", "upstream STOP rows present", "STOP"],
        ["20D-S007", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20c, p20b = base / IN20C, base / IN20B
    inputs = {
        "summary_20c": p20c / "gold_v2_20c_tier2_source_identity_human_decision_intake_draft_load_smoke_summary.json",
        "draft_load_20c": p20c / "gold_v2_20c_draft_load_audit.csv",
        "checks_20c": p20c / "gold_v2_20c_load_checks.csv",
        "gates_20c": p20c / "gold_v2_20c_required_next_gates.csv",
        "safety_20c": p20c / "gold_v2_20c_safety_matrix.csv",
        "report_20c": p20c / "GOLD_V2_20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "draft_20b": p20b / "gold_v2_20b_decision_intake_draft.json",
        "fields_20b": p20b / "gold_v2_20b_required_decision_fields.csv",
        "values_20b": p20b / "gold_v2_20b_allowed_decision_values.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20d_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20d_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20D-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20d_content_checks.csv", checks)
        write_csv(out / "gold_v2_20d_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20d_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20D_STOP_MISSING_INPUTS",
            "audit_only": True,
            "content_audit_passed": False,
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
            "next_recommended_step": "STOP_REVIEW_20D_INPUTS",
        }
        write_json(out / "gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20D draft content audit-only report\n\nStatus: `20D_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20c = read_json(inputs["summary_20c"])
    draft_load = read_csv(inputs["draft_load_20c"])
    checks20c = read_csv(inputs["checks_20c"])
    gates20c = read_csv(inputs["gates_20c"])
    safety20c = read_csv(inputs["safety_20c"])
    draft = read_json(inputs["draft_20b"])
    fields = read_csv(inputs["fields_20b"])
    values = read_csv(inputs["values_20b"])

    fvals = field_values(fields)
    dvals = decision_values(values)
    missing_fields = sorted(EXPECTED_FIELDS.difference(set(fvals)))
    duplicated_fields = int(pd.Series(fvals).duplicated().sum()) if fvals else 999
    duplicated_values = int(pd.Series(dvals).duplicated().sum()) if dvals else 999
    expected_required_false = expected_field_required_false_count(fields, fvals)
    empty_allowed_values = int((pd.Series(dvals).astype(str).str.strip() == "").sum()) if dvals else 999
    action_values = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    unset_bad = sum(int(draft.get(k) != "UNSET") for k in UNSET_FIELDS)
    restricted_true = sum(int(bool(draft.get(k, False))) for k in RESTRICTED_DRAFT_FLAGS)
    upstream_stop = stop_count(draft_load) + stop_count(checks20c) + stop_count(safety20c)
    forbidden_gates = forbidden_gate_count(gates20c, "allowed_after_20c_success")
    forbidden_flags = forbidden_summary_count(s20c)

    field_audit = pd.DataFrame([
        check_row("20D-F001", "field column present", bool(fvals), True, bool(fvals)),
        check_row("20D-F002", "missing expected core fields", len(missing_fields), 0, len(missing_fields) == 0),
        check_row("20D-F003", "duplicate fields", duplicated_fields, 0, duplicated_fields == 0),
        check_row("20D-F004", "expected core fields required=false rows", expected_required_false, 0, expected_required_false == 0),
        check_row("20D-F005", "field rows", len(fields), ">=6", len(fields) >= 6),
    ])
    value_audit = pd.DataFrame([
        check_row("20D-V001", "decision value column present", bool(dvals), True, bool(dvals)),
        check_row("20D-V002", "empty allowed values", empty_allowed_values, 0, empty_allowed_values == 0),
        check_row("20D-V003", "duplicate values", duplicated_values, 0, duplicated_values == 0),
        check_row("20D-V004", "action-executing values", action_values, 0, action_values == 0),
        check_row("20D-V005", "value rows", len(values), f">={MIN_ALLOWED_VALUE_ROWS}", len(values) >= MIN_ALLOWED_VALUE_ROWS),
    ])
    write_csv(out / "gold_v2_20d_required_field_audit.csv", field_audit)
    write_csv(out / "gold_v2_20d_allowed_value_audit.csv", value_audit)

    checks = pd.DataFrame([
        check_row("20D-C001", "20C status", s20c.get("status"), EXPECTED_20C, s20c.get("status") == EXPECTED_20C),
        check_row("20D-C002", "20C draft_load_smoke_passed", s20c.get("draft_load_smoke_passed"), True, bool(s20c.get("draft_load_smoke_passed", False))),
        check_row("20D-C003", "20C total_stop_rows", s20c.get("total_stop_rows"), 0, s20c.get("total_stop_rows") == 0),
        check_row("20D-C004", "20C decision_value", s20c.get("decision_value"), "UNSET", s20c.get("decision_value") == "UNSET"),
        check_row("20D-C005", "20C decision_collected", s20c.get("decision_collected"), False, s20c.get("decision_collected") is False),
        check_row("20D-C006", "20C decision_made", s20c.get("decision_made"), False, s20c.get("decision_made") is False),
        check_row("20D-C007", "20C approval_granted", s20c.get("approval_granted"), False, s20c.get("approval_granted") is False),
        check_row("20D-C008", "20C actual_decision_collection_allowed", s20c.get("actual_decision_collection_allowed"), False, s20c.get("actual_decision_collection_allowed") is False),
        check_row("20D-C009", "draft_status", draft.get("draft_status"), "DRAFT_ONLY_NOT_A_DECISION", draft.get("draft_status") == "DRAFT_ONLY_NOT_A_DECISION"),
        check_row("20D-C010", "draft decision_value", draft.get("decision_value"), "UNSET", draft.get("decision_value") == "UNSET"),
        check_row("20D-C011", "draft unset fields not UNSET", unset_bad, 0, unset_bad == 0),
        check_row("20D-C012", "draft evidence_acknowledged", draft.get("evidence_acknowledged"), False, draft.get("evidence_acknowledged") is False),
        check_row("20D-C013", "draft actual_decision_collection_allowed", draft.get("actual_decision_collection_allowed"), False, draft.get("actual_decision_collection_allowed") is False),
        check_row("20D-C014", "draft approval_granted", draft.get("approval_granted"), False, draft.get("approval_granted") is False),
        check_row("20D-C015", "restricted draft true flags", restricted_true, 0, restricted_true == 0),
        check_row("20D-C016", "field audit STOP rows", stop_count(field_audit), 0, stop_count(field_audit) == 0),
        check_row("20D-C017", "value audit STOP rows", stop_count(value_audit), 0, stop_count(value_audit) == 0),
        check_row("20D-C018", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20D-C019", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20D-C020", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20D_STOP_REVIEW_DRAFT_CONTENT_AUDIT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20d_content_checks.csv", checks)
    write_csv(out / "gold_v2_20d_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20d_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "content_audit_passed": success,
        "draft_status": draft.get("draft_status"),
        "authorization_scope": draft.get("authorization_scope"),
        "decision_value": draft.get("decision_value"),
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "field_rows": int(len(fields)),
        "value_rows": int(len(values)),
        "missing_required_fields": missing_fields,
        "allowed_decision_values_audited": dvals,
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
        "next_recommended_step": "20E_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_20D_OUTPUTS",
    }
    write_json(out / "gold_v2_20d_tier2_source_identity_human_decision_intake_draft_content_audit_summary.json", summary)
    report = [
        "# GOLD V2 20D TIER2 source identity human decision intake draft content audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20D content-audited the unset actual decision intake draft package only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Content checks",
        md_table(checks),
        "",
        "## Required field audit",
        md_table(field_audit),
        "",
        "## Allowed value audit",
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
