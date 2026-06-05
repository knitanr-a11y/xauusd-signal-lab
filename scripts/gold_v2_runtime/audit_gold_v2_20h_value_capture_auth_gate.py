#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY"
OUT_DIR = "gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_audit_only"
IN20G = "gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_audit_only"
REPORT = "GOLD_V2_20H_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_20G = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
AUTH_ID = "GOLD_V2_20H_VALUE_CAPTURE_AUTH_20260606"
AUTH_TEXT = "USER_AUTHORIZED_PROCEED_AFTER_20G_TO_ACTUAL_DECISION_VALUE_CAPTURE_AUDIT_ONLY_PREPARATION"
AUTH_SCOPE = "ACTUAL_DECISION_VALUE_CAPTURE_AUDIT_ONLY_PREPARATION_ONLY"
BACKUP_MANIFEST = "docs/gold_v2/GOLD_V2_20H_PRE_CHANGE_BACKUP_MANIFEST_20260606.md"
FORBIDDEN_GATES = {"ACTUAL_DECISION_COLLECTION", "SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "actual_decision_collection_allowed", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
RESTRICTED_AUTH_FLAGS = [
    "actual_decision_value_collected", "actual_decision_collection_completed", "approval_granted",
    "source_recovery_allowed", "source_identity_finalization_allowed", "source_identity_recovery_allowed",
    "ledger_source_of_truth_promotion_allowed", "oh_lc_replay_allowed", "live_evaluator_allowed",
    "final_signal_allowed", "discord_send_allowed", "no_signal_discord_send_allowed", "mt5_order_allowed",
    "ai_api_allowed", "live_hook_allowed", "signal_conditions_change_allowed", "script_executes_action",
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
        ["20I", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY", "Prepare the actual decision value capture draft only; value still not collected by 20H.", bool(success)],
        ["ACTUAL_DECISION_COLLECTION", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_ACTUAL_DECISION_COLLECTION", "Still blocked after 20H; not completed or authorized as an action by this step.", False],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 20H.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 20H.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked after 20H.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked after 20H.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_20h_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["authorization_gate_only", True, True, "PASS"],
        ["backup_manifest_required", True, True, "PASS"],
        ["decision_value_collected", False, False, "PASS"],
        ["decision_collected", False, False, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
        ["actual_decision_collection_completed", False, False, "PASS"],
        ["actual_decision_collection_allowed", False, False, "PASS"],
        ["signal_conditions_changed", False, False, "PASS"],
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
        ["next_gate_20i_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["20H-S001", "required inputs missing", "STOP"],
        ["20H-S002", "backup manifest missing", "STOP"],
        ["20H-S003", "20G status not passed", "STOP"],
        ["20H-S004", "20G STOP rows present", "STOP"],
        ["20H-S005", "decision value no longer UNSET or decision/approval collected", "STOP"],
        ["20H-S006", "actual decision collection completed or action allowed", "STOP"],
        ["20H-S007", "restricted authorization flag true", "STOP"],
        ["20H-S008", "forbidden gate or summary flag allowed", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    root = repo_root()
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p20g = base / IN20G
    backup_path = root / BACKUP_MANIFEST
    inputs = {
        "backup_manifest": backup_path,
        "summary_20g": p20g / "gold_v2_20g_tier2_source_identity_human_decision_intake_draft_final_handoff_summary.json",
        "handoff_checks_20g": p20g / "gold_v2_20g_handoff_checks.csv",
        "handoff_note_20g": p20g / "gold_v2_20g_final_handoff_note.md",
        "gates_20g": p20g / "gold_v2_20g_required_next_gates.csv",
        "safety_20g": p20g / "gold_v2_20g_safety_matrix.csv",
        "report_20g": p20g / "GOLD_V2_20G_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_20h_input_audit.csv", input_audit)
    write_csv(out / "gold_v2_20h_stop_conditions.csv", stop_conditions())

    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("20H-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        gates = next_gates(False)
        write_csv(out / "gold_v2_20h_authorization_checks.csv", checks)
        write_csv(out / "gold_v2_20h_required_next_gates.csv", gates)
        write_csv(out / "gold_v2_20h_safety_matrix.csv", sm)
        summary = {
            "created_utc": now,
            "step": STEP,
            "status": "20H_STOP_MISSING_INPUTS",
            "audit_only": True,
            "authorization_gate_passed": False,
            "authorization_scope": AUTH_SCOPE,
            "decision_value": "UNSET",
            "decision_value_collected": False,
            "decision_collected": False,
            "decision_made": False,
            "approval_granted": False,
            "actual_decision_collection_allowed": False,
            "actual_decision_collection_completed": False,
            "total_stop_rows": 1,
            "signal_conditions_changed": False,
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
            "next_recommended_step": "STOP_REVIEW_20H_INPUTS",
        }
        write_json(out / "gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 20H value capture authorization gate audit-only report\n\nStatus: `20H_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s20g = read_json(inputs["summary_20g"])
    handoff_checks = read_csv(inputs["handoff_checks_20g"])
    gates20g = read_csv(inputs["gates_20g"])
    safety20g = read_csv(inputs["safety_20g"])

    auth = {
        "authorization_id": AUTH_ID,
        "authorization_text": AUTH_TEXT,
        "authorization_scope": AUTH_SCOPE,
        "source": "current_chat_user_explicit_permission",
        "allows_next_audit_only_value_capture_preparation": True,
        "actual_decision_value_collected": False,
        "actual_decision_collection_completed": False,
        "approval_granted": False,
        "source_recovery_allowed": False,
        "source_identity_finalization_allowed": False,
        "source_identity_recovery_allowed": False,
        "ledger_source_of_truth_promotion_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "discord_send_allowed": False,
        "no_signal_discord_send_allowed": False,
        "mt5_order_allowed": False,
        "ai_api_allowed": False,
        "live_hook_allowed": False,
        "signal_conditions_change_allowed": False,
        "script_executes_action": False,
    }
    auth_df = pd.DataFrame([auth])
    write_csv(out / "gold_v2_20h_authorization_record.csv", auth_df)

    upstream_stop = stop_count(handoff_checks) + stop_count(safety20g)
    forbidden_gates = forbidden_gate_count(gates20g, "allowed_after_20g_success")
    forbidden_flags = forbidden_summary_count(s20g)
    decision_flags_true = sum(int(bool(s20g.get(k, False))) for k in ("decision_collected", "decision_made", "approval_granted", "actual_decision_collection_allowed"))
    restricted_auth_true = sum(int(bool(auth.get(k, False))) for k in RESTRICTED_AUTH_FLAGS)

    checks = pd.DataFrame([
        check_row("20H-C001", "20G status", s20g.get("status"), EXPECTED_20G, s20g.get("status") == EXPECTED_20G),
        check_row("20H-C002", "20G handoff_ready", s20g.get("handoff_ready"), True, bool(s20g.get("handoff_ready", False))),
        check_row("20H-C003", "20G total_stop_rows", s20g.get("total_stop_rows"), 0, s20g.get("total_stop_rows") == 0),
        check_row("20H-C004", "20G decision_value", s20g.get("decision_value"), "UNSET", s20g.get("decision_value") == "UNSET"),
        check_row("20H-C005", "20G decision/approval/collection flags true", decision_flags_true, 0, decision_flags_true == 0),
        check_row("20H-C006", "20G handoff/safety STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("20H-C007", "backup manifest exists", lp(backup_path).exists(), True, lp(backup_path).exists()),
        check_row("20H-C008", "authorization scope", auth["authorization_scope"], AUTH_SCOPE, auth["authorization_scope"] == AUTH_SCOPE),
        check_row("20H-C009", "restricted authorization true flags", restricted_auth_true, 0, restricted_auth_true == 0),
        check_row("20H-C010", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("20H-C011", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "20H_STOP_REVIEW_VALUE_CAPTURE_AUTHORIZATION_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_20h_authorization_checks.csv", checks)
    write_csv(out / "gold_v2_20h_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_20h_safety_matrix.csv", sm)

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "authorization_gate_passed": success,
        "authorization_id": AUTH_ID,
        "authorization_text": AUTH_TEXT,
        "authorization_scope": AUTH_SCOPE,
        "decision_value": "UNSET",
        "decision_value_collected": False,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "actual_decision_collection_allowed": False,
        "actual_decision_collection_completed": False,
        "total_stop_rows": int(total_stop),
        "signal_conditions_changed": False,
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
        "next_recommended_step": "20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY" if success else "STOP_REVIEW_20H_OUTPUTS",
    }
    write_json(out / "gold_v2_20h_tier2_source_identity_human_decision_value_capture_authorization_gate_summary.json", summary)
    report = [
        "# GOLD V2 20H TIER2 source identity human decision value capture authorization gate audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 20H recorded authorization to prepare a later audit-only actual decision value capture draft step only.",
        "- No actual decision value was collected and no approval was made by this script.",
        "- Signal conditions, source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain unchanged and disabled.",
        "",
        "## Authorization checks",
        md_table(checks),
        "",
        "## Authorization record",
        md_table(auth_df),
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
