#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY"
OUT_DIR = "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_audit_only"
IN20A = "gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_audit_only"
IN19H = "gold_v2_19h_tier2_source_identity_human_decision_intake_actual_decision_template_preparation_audit_only"
REPORT = "GOLD_V2_20B_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20A = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
AUTH_SCOPE = "ACTUAL_DECISION_INTAKE_AUDIT_ONLY_PREPARATION_ONLY"
FORBIDDEN_GATES = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "actual_decision_collection_allowed", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_DRAFT_FLAGS = [
    "approval_granted",
    "actual_decision_collection_allowed",
    "source_recovery_requested",
    "source_recovery_allowed",
    "source_identity_finalization_allowed",
    "source_identity_recovery_allowed",
    "ledger_source_of_truth_promotion_allowed",
    "oh_lc_replay_allowed",
    "live_evaluator_allowed",
    "live_or_final_implementation_allowed",
    "final_signal_allowed",
    "discord_send_allowed",
    "no_signal_discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
    "script_executes_action",
]
UNSET_FIELDS = [
    "decision_id",
    "decision_timestamp_utc",
    "decision_value",
    "human_reviewer",
    "explicit_phrase",
    "notes",
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
        ["20C", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY", "Load-smoke the unset decision intake draft only.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20B; not authorized by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20B.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20B.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20b_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["decision_intake_draft_only", True, True, "PASS"],
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
        ["next_gate_20c_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20B-S001", "required inputs missing", "STOP"],
        ["20B-S002", "20A status not passed", "STOP"],
        ["20B-S003", "authorization scope not preparation-only", "STOP"],
        ["20B-S004", "decision collected or approval already made", "STOP"],
        ["20B-S005", "actual decision collection allowed", "STOP"],
        ["20B-S006", "upstream STOP rows present", "STOP"],
        ["20B-S007", "draft failed unset/no-action checks", "STOP"],
        ["20B-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20a, p19h = base / IN20A, base / IN19H
    inputs = {
        "summary_20a": p20a / "gold_v2_20a_tier2_source_identity_human_decision_intake_authorization_gate_summary.json",
        "auth_record_20a": p20a / "gold_v2_20a_authorization_record.csv",
        "checks_20a": p20a / "gold_v2_20a_authorization_checks.csv",
        "gates_20a": p20a / "gold_v2_20a_required_next_gates.csv",
        "safety_20a": p20a / "gold_v2_20a_safety_matrix.csv",
        "report_20a": p20a / "GOLD_V2_20A_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md",
        "template_19h": p19h / "gold_v2_19h_actual_decision_template.json",
        "fields_19h": p19h / "gold_v2_19h_required_decision_fields.csv",
        "values_19h": p19h / "gold_v2_19h_allowed_decision_values.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20b_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20b_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20B-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20b_draft_checks.csv", checks)
        write_csv(out / "gold_v2_20b_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20b_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20B_STOP_MISSING_INPUTS",
            "audit_only": True,
            "draft_ready": False,
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
            "next_recommended_step": "STOP_REVIEW_20B_INPUTS",
        }
        write_json(out / "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20B decision intake draft audit-only report\n\nStatus: `20B_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20a = read_json(inputs["summary_20a"])
    auth_record = read_csv(inputs["auth_record_20a"])
    checks20a = read_csv(inputs["checks_20a"])
    gates20a = read_csv(inputs["gates_20a"])
    safety20a = read_csv(inputs["safety_20a"])
    source_template = read_json(inputs["template_19h"])
    fields = read_csv(inputs["fields_19h"])
    values = read_csv(inputs["values_19h"])
    write_csv(out / "gold_v2_20b_required_decision_fields.csv", fields)
    write_csv(out / "gold_v2_20b_allowed_decision_values.csv", values)

    draft = {
        "draft_version": "GOLD_V2_20B_ACTUAL_DECISION_INTAKE_DRAFT_V1",
        "created_utc": now,
        "draft_status": "DRAFT_ONLY_NOT_A_DECISION",
        "source_template_version": source_template.get("template_version"),
        "source_template_status": source_template.get("template_status"),
        "authorization_scope": s20a.get("authorization_scope"),
        "decision_id": "UNSET",
        "decision_timestamp_utc": "UNSET",
        "decision_value": "UNSET",
        "human_reviewer": "UNSET",
        "evidence_acknowledged": False,
        "explicit_phrase": "UNSET",
        "notes": "UNSET",
        "allowed_decision_values": values.get("decision_value", pd.Series(dtype=str)).astype(str).tolist(),
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "source_recovery_requested": False,
        "source_recovery_allowed": False,
        "source_identity_finalization_allowed": False,
        "source_identity_recovery_allowed": False,
        "ledger_source_of_truth_promotion_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_evaluator_allowed": False,
        "live_or_final_implementation_allowed": False,
        "final_signal_allowed": False,
        "discord_send_allowed": False,
        "no_signal_discord_send_allowed": False,
        "mt5_order_allowed": False,
        "ai_api_allowed": False,
        "live_hook_allowed": False,
        "script_executes_action": False,
    }
    write_json(out / "gold_v2_20b_decision_intake_draft.json", draft)

    field_rows_match = int(len(fields)) >= 6
    value_rows_match = int(len(values)) >= 4
    unset_bad = sum(int(draft.get(k) != "UNSET") for k in UNSET_FIELDS)
    restricted_true = sum(int(bool(draft.get(k, False))) for k in RESTRICTED_DRAFT_FLAGS)
    action_values = int(values.get("executes_action_in_18x", pd.Series(dtype=bool)).map(truthy).sum()) if not values.empty else 999
    auth_restricted_cols = [c for c in auth_record.columns if c.endswith("_allowed") and c != "allows_next_audit_only_preparation"]
    auth_restricted_true = int(auth_record[auth_restricted_cols].applymap(truthy).sum().sum()) if auth_restricted_cols else 999
    upstream_stop = stop_count(checks20a) + stop_count(safety20a)
    forbidden_gates = forbidden_gate_count(gates20a, "allowed_after_20a_success")
    forbidden_flags = forbidden_summary_count(s20a)

    checks = pd.DataFrame([
        check_row("20B-C001", "20A status", s20a.get("status"), EXPECTED_20A, s20a.get("status") == EXPECTED_20A),
        check_row("20B-C002", "20A authorization_gate_passed", s20a.get("authorization_gate_passed"), True, bool(s20a.get("authorization_gate_passed", False))),
        check_row("20B-C003", "20A total_stop_rows", s20a.get("total_stop_rows"), 0, s20a.get("total_stop_rows") == 0),
        check_row("20B-C004", "20A authorization_scope", s20a.get("authorization_scope"), AUTH_SCOPE, s20a.get("authorization_scope") == AUTH_SCOPE),
        check_row("20B-C005", "20A actual_decision_collection_allowed", s20a.get("actual_decision_collection_allowed"), False, s20a.get("actual_decision_collection_allowed") is False),
        check_row("20B-C006", "20A decision_collected", s20a.get("decision_collected"), False, s20a.get("decision_collected") is False),
        check_row("20B-C007", "20A decision_made", s20a.get("decision_made"), False, s20a.get("decision_made") is False),
        check_row("20B-C008", "20A approval_granted", s20a.get("approval_granted"), False, s20a.get("approval_granted") is False),
        check_row("20B-C009", "20A auth restricted allowed flags", auth_restricted_true, 0, auth_restricted_true == 0),
        check_row("20B-C010", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20B-C011", "19H field rows", len(fields), ">=6", field_rows_match),
        check_row("20B-C012", "19H value rows", len(values), ">=4", value_rows_match),
        check_row("20B-C013", "draft_status", draft.get("draft_status"), "DRAFT_ONLY_NOT_A_DECISION", draft.get("draft_status") == "DRAFT_ONLY_NOT_A_DECISION"),
        check_row("20B-C014", "draft decision_value", draft.get("decision_value"), "UNSET", draft.get("decision_value") == "UNSET"),
        check_row("20B-C015", "draft unset fields not UNSET", unset_bad, 0, unset_bad == 0),
        check_row("20B-C016", "draft evidence_acknowledged", draft.get("evidence_acknowledged"), False, draft.get("evidence_acknowledged") is False),
        check_row("20B-C017", "restricted draft true flags", restricted_true, 0, restricted_true == 0),
        check_row("20B-C018", "allowed values execute no action", action_values, 0, action_values == 0),
        check_row("20B-C019", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20B-C020", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20B_STOP_REVIEW_DECISION_DRAFT_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20b_draft_checks.csv", checks)
    write_csv(out / "gold_v2_20b_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20b_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "draft_ready": success,
        "draft_status": draft.get("draft_status"),
        "authorization_scope": s20a.get("authorization_scope"),
        "decision_value": draft.get("decision_value"),
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "field_rows": int(len(fields)),
        "value_rows": int(len(values)),
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
        "next_recommended_step": "20C_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_20B_OUTPUTS",
    }
    write_json(out / "gold_v2_20b_tier2_source_identity_human_decision_intake_draft_summary.json", summary)
    report = [
        "# GOLD V2 20B TIER2 source identity human decision intake draft audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20B prepared an unset actual decision intake draft package only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Draft checks",
        md_table(checks),
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
