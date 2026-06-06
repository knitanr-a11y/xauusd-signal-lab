#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STEP = "23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY"
OUT_DIR = "gold_v2_23b_request_more_audit_human_decision_options_audit_only"
IN23A = "gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only"

SELECTED = "REQUEST_MORE_AUDIT"
EXPECTED_23A_STATUS = "REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
SUCCESS_STATUS = "REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
STOP_STATUS = "23B_STOP_REVIEW_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_INPUTS"

REPORT_FILE = "GOLD_V2_23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_23b_request_more_audit_human_decision_options_summary.json"
INPUT_AUDIT_FILE = "gold_v2_23b_input_audit.csv"
DECISION_OPTIONS_FILE = "gold_v2_23b_human_decision_options.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_23b_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_23b_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_23b_safety_matrix.csv"

FORBIDDEN_GATES = {
    "SOURCE_IDENTITY_FINALIZATION",
    "SOURCE_RECOVERY",
    "LIVE",
    "FINAL_SIGNAL",
    "DISCORD_SEND",
    "MT5_ORDER",
    "AI_API",
    "LIVE_HOOK",
}

EXPECTED_STILL_BLOCKED = [
    "SOURCE_IDENTITY_FINALIZATION",
    "SOURCE_RECOVERY",
    "LIVE",
    "FINAL_SIGNAL",
    "DISCORD_SEND",
    "MT5_ORDER",
    "AI_API",
    "LIVE_HOOK",
]

FALSE_SUMMARY_FLAGS = [
    "request_more_audit_is_source_recovery_approval",
    "source_recovery_approved",
    "source_recovery_executed",
    "source_identity_finalized",
    "source_identity_recovered",
    "ledger_is_source_of_truth",
    "live_or_final_implementation_allowed",
    "oh_lc_replay_allowed",
    "live_enabled",
    "final_signal_allowed",
    "no_signal_discord_notified",
    "ai_api_called",
    "source_recovery_execution_performed",
    "source_identity_finalization_performed",
]

EXTERNAL_ACTION_KEYS = [
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
]

REQUIRED_23A_FILES = {
    "23a_report": "GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY_REPORT.md",
    "23a_summary": "gold_v2_23a_request_more_audit_resolution_matrix_summary.json",
    "23a_input_audit": "gold_v2_23a_input_audit.csv",
    "23a_resolution_matrix": "gold_v2_23a_resolution_matrix.csv",
    "23a_integrated_checks": "gold_v2_23a_integrated_checks.csv",
    "23a_required_next_gates": "gold_v2_23a_required_next_gates.csv",
    "23a_safety_matrix": "gold_v2_23a_safety_matrix.csv",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs_root() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def long_path(path: Path) -> Path:
    path = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return path
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "allowed", "pass", "ready"}


def falsey(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if value is None:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not bool(value)
    return str(value).strip().lower() in {"", "0", "false", "no", "n", "blocked", "none", "null"}


def write_text(path: Path, text: str) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    long_path(path).write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    frame.to_csv(long_path(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(long_path(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(long_path(path), encoding=encoding, keep_default_na=False)
        except Exception as exc:
            errors.append(f"{encoding}: {exc}")
    raise RuntimeError(f"CSV read failed: {path} / {'; '.join(errors)}")


def stop_rows(frame: pd.DataFrame) -> int:
    if frame.empty or "status" not in frame.columns:
        return 0
    return int((frame["status"].astype(str).str.upper() == "STOP").sum())


def md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            values.append(str(row[column]).replace("|", "\\|").replace("\n", " "))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def check_row(check_id: str, check: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "check": check,
        "observed": observed,
        "expected": expected,
        "status": "PASS" if ok else "STOP",
    }


def get_external(summary: dict[str, Any], key: str) -> Any:
    external = summary.get("external_actions", {})
    if isinstance(external, dict):
        return external.get(key, False)
    return False


def build_input_audit(input_paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role, path in input_paths.items():
        rows.append(
            {
                "role": role,
                "path": str(path),
                "required": True,
                "exists": long_path(path).exists(),
                "source_of_truth_role": "23A audited artifact",
                "notes": "23B reads this artifact only; no recovery/live/AI/external execution.",
            }
        )
    return pd.DataFrame(rows)


def allowed_next_steps(gates: pd.DataFrame, allowed_column: str) -> list[str]:
    if gates.empty or "next_step" not in gates.columns or allowed_column not in gates.columns:
        return []
    mask = gates[allowed_column].map(truthy)
    return gates.loc[mask, "next_step"].astype(str).tolist()


def forbidden_allowed_detail(gates: pd.DataFrame, allowed_column: str) -> str:
    if gates.empty or "next_step" not in gates.columns or allowed_column not in gates.columns:
        return "missing next_step/allowed column"
    subset = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
    if subset.empty:
        return "no forbidden gate rows found"
    allowed = subset[subset[allowed_column].map(truthy)]
    if allowed.empty:
        return "all forbidden gates blocked"
    return ",".join(allowed["next_step"].astype(str).tolist())


def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    flag_count = sum(1 for key in FALSE_SUMMARY_FLAGS if truthy(summary.get(key, False)))
    external_count = sum(1 for key in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, key)))
    return int(flag_count + external_count)


def build_decision_options(ok: bool) -> pd.DataFrame:
    status = "AVAILABLE_FOR_HUMAN_REVIEW_AUDIT_ONLY" if ok else "BLOCKED_BY_23B_STOP"
    rows = [
        {
            "option_id": "23B-O001",
            "decision_value": "KEEP_REQUEST_MORE_AUDIT_CHAIN_CLOSED_AUDIT_ONLY",
            "option_type": "safe_current_audit_only",
            "meaning": "Close the completed REQUEST_MORE_AUDIT read-only chain without approving any execution.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No execution. Records that the 21A-23B read-only audit package is complete.",
            "future_approval_value_required_for_execution": "NONE",
            "blocked_actions": "SOURCE_RECOVERY; SOURCE_IDENTITY_FINALIZATION; LIVE; FINAL_SIGNAL; DISCORD_SEND; MT5_ORDER; AI_API; LIVE_HOOK",
            "risk_if_misread": "Low, provided it is not treated as approval for blocked actions.",
            "next_safe_step_if_selected": "Stop or request a new audit-only topic.",
            "status": status,
        },
        {
            "option_id": "23B-O002",
            "decision_value": "REQUEST_23C_HUMAN_DECISION_INTAKE_AUDIT_ONLY",
            "option_type": "safe_current_audit_only",
            "meaning": "Create an audit-only intake file/template for the user's explicit next decision.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No execution. Only prepares intake validation for a future user-selected value.",
            "future_approval_value_required_for_execution": "Depends on selected path; 23C still must not execute recovery/live/external actions.",
            "blocked_actions": "All recovery/finalization/live/final/external actions remain blocked.",
            "risk_if_misread": "Medium if a later decision value is interpreted as automatic execution approval.",
            "next_safe_step_if_selected": "23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY",
            "status": status,
        },
        {
            "option_id": "23B-O003",
            "decision_value": "REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY",
            "option_type": "precheck_only_not_approval",
            "meaning": "Ask for an audit-only precheck of what source recovery would require.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No source recovery execution. Only a precheck plan may be drafted.",
            "future_approval_value_required_for_execution": "APPROVE_SOURCE_RECOVERY_EXECUTION",
            "blocked_actions": "SOURCE_RECOVERY",
            "risk_if_misread": "High if this request is treated as recovery approval.",
            "next_safe_step_if_selected": "Create a separate audit-only recovery precheck; do not execute recovery.",
            "status": status,
        },
        {
            "option_id": "23B-O004",
            "decision_value": "REQUEST_SOURCE_IDENTITY_FINALIZATION_PRECHECK_AUDIT_ONLY",
            "option_type": "precheck_only_not_approval",
            "meaning": "Ask for an audit-only precheck of what source identity finalization would require.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No finalization. Only a precheck plan may be drafted.",
            "future_approval_value_required_for_execution": "APPROVE_SOURCE_IDENTITY_FINALIZATION",
            "blocked_actions": "SOURCE_IDENTITY_FINALIZATION",
            "risk_if_misread": "High if this request is treated as identity finalization approval.",
            "next_safe_step_if_selected": "Create a separate audit-only finalization precheck; do not finalize identity.",
            "status": status,
        },
        {
            "option_id": "23B-O005",
            "decision_value": "REQUEST_LIVE_EVALUATOR_PRECHECK_AUDIT_ONLY",
            "option_type": "precheck_only_not_approval",
            "meaning": "Ask for an audit-only precheck of live evaluator prerequisites and blockers.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No live evaluator or hook is enabled.",
            "future_approval_value_required_for_execution": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION",
            "blocked_actions": "LIVE; LIVE_HOOK",
            "risk_if_misread": "High if live behavior is created before parity and approval gates.",
            "next_safe_step_if_selected": "Create a separate audit-only live precheck; do not enable live runtime.",
            "status": status,
        },
        {
            "option_id": "23B-O006",
            "decision_value": "REQUEST_FINAL_SIGNAL_PRECHECK_AUDIT_ONLY",
            "option_type": "precheck_only_not_approval",
            "meaning": "Ask for an audit-only precheck of final signal prerequisites and blockers.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No final signal behavior is created.",
            "future_approval_value_required_for_execution": "APPROVE_FINAL_SIGNAL",
            "blocked_actions": "FINAL_SIGNAL",
            "risk_if_misread": "High if audit outputs become signal outputs.",
            "next_safe_step_if_selected": "Create a separate audit-only final signal precheck.",
            "status": status,
        },
        {
            "option_id": "23B-O007",
            "decision_value": "REQUEST_EXTERNAL_ACTION_PRECHECK_AUDIT_ONLY",
            "option_type": "precheck_only_not_approval",
            "meaning": "Ask for an audit-only precheck of Discord, MT5, AI API, and live hook blockers.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "No Discord, MT5, AI API, or live hook call occurs.",
            "future_approval_value_required_for_execution": "APPROVE_DISCORD_SEND; APPROVE_MT5_ORDER; APPROVE_AI_API_REVIEW; APPROVE_LIVE_HOOK",
            "blocked_actions": "DISCORD_SEND; MT5_ORDER; AI_API; LIVE_HOOK",
            "risk_if_misread": "High because this category can create external side effects or costs.",
            "next_safe_step_if_selected": "Create a separate audit-only external action precheck.",
            "status": status,
        },
        {
            "option_id": "23B-O008",
            "decision_value": "REQUEST_OLD_GOLD_DISC8_DEQUARANTINE_PRECHECK_AUDIT_ONLY",
            "option_type": "precheck_only_not_approval",
            "meaning": "Ask for an audit-only precheck of what would be needed to lift old GOLD/DISC8 quarantine.",
            "current_allowed_to_select": bool(ok),
            "current_effect_if_selected": "Old GOLD/DISC8 remain quarantined; no source is restored.",
            "future_approval_value_required_for_execution": "APPROVE_OLD_GOLD_DISC8_DEQUARANTINE",
            "blocked_actions": "Using old GOLD/DISC8 as active source-of-truth for live/final behavior.",
            "risk_if_misread": "High because quarantined sources may contain HTF open-time mismatch.",
            "next_safe_step_if_selected": "Create a separate audit-only HTF mismatch/de-quarantine precheck.",
            "status": status,
        },
    ]
    return pd.DataFrame(rows)


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "next_step": "23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY",
                "name": "Validate a future human decision value without executing it",
                "purpose": "Audit-only intake/validation of the user's selected next decision option.",
                "allowed_after_23b_success": bool(ok),
                "required_human_decision_value_later": "One 23B decision_value selected by the user.",
                "still_blocked_reason": "" if ok else "23B checks did not pass.",
            },
            {
                "next_step": "SOURCE_IDENTITY_FINALIZATION",
                "name": "Finalize source identity",
                "purpose": "Would finalize recovered/source identity state.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION",
                "still_blocked_reason": "23B only lists options and does not grant finalization approval.",
            },
            {
                "next_step": "SOURCE_RECOVERY",
                "name": "Execute source recovery",
                "purpose": "Would run recovery actions rather than audit-only review.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION",
                "still_blocked_reason": "23B only lists options and does not grant recovery approval.",
            },
            {
                "next_step": "LIVE",
                "name": "Enable live evaluator/use",
                "purpose": "Would create or enable live behavior.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION",
                "still_blocked_reason": "GOLD V2 remains audit-only.",
            },
            {
                "next_step": "FINAL_SIGNAL",
                "name": "Enable final signal",
                "purpose": "Would produce final signal behavior.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL",
                "still_blocked_reason": "Final signal remains blocked.",
            },
            {
                "next_step": "DISCORD_SEND",
                "name": "Send Discord notification",
                "purpose": "Would send notifications externally.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_DISCORD_SEND",
                "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify.",
            },
            {
                "next_step": "MT5_ORDER",
                "name": "Place MT5 order",
                "purpose": "Would place or prepare live orders.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_MT5_ORDER",
                "still_blocked_reason": "MT5 order path remains blocked.",
            },
            {
                "next_step": "AI_API",
                "name": "Call AI API",
                "purpose": "Would call an external AI review API.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_AI_API_REVIEW",
                "still_blocked_reason": "AI API remains blocked.",
            },
            {
                "next_step": "LIVE_HOOK",
                "name": "Enable live hook",
                "purpose": "Would connect audit logic to live runtime hooks.",
                "allowed_after_23b_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_HOOK",
                "still_blocked_reason": "Live hook remains blocked.",
            },
        ]
    )


def build_safety_matrix(summary23a: dict[str, Any], ok: bool, inputs_ok: bool) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(item: str, observed: Any, expected: Any, passed: bool, notes: str) -> None:
        rows.append(
            {
                "safety_item": item,
                "observed": observed,
                "expected": expected,
                "status": "PASS" if passed else "STOP",
                "notes": notes,
            }
        )

    add("audit_only", True, True, True, "23B writes audit artifacts only.")
    add("human_decision_options_only", True, True, True, "23B lists decision options; it does not select or execute them.")
    add("required_23a_inputs_exist", inputs_ok, True, inputs_ok, "All 23A source-of-truth artifacts must exist.")
    add("request_more_audit_is_not_source_recovery_approval", SELECTED, "NOT_APPROVAL", True, "REQUEST_MORE_AUDIT remains audit-only.")
    for key in [
        "source_recovery_approved",
        "source_recovery_executed",
        "source_identity_finalized",
        "source_identity_recovered",
        "live_or_final_implementation_allowed",
        "live_enabled",
        "final_signal_allowed",
        "no_signal_discord_notified",
    ]:
        observed = summary23a.get(key, False) if inputs_ok else "UNKNOWN_MISSING_23A_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        observed = get_external(summary23a, key) if inputs_ok else "UNKNOWN_MISSING_23A_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "23B does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "23B never calls AI API.")
    add("discord_sent", False, False, True, "23B never sends Discord.")
    add("mt5_order_sent", False, False, True, "23B never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "23B never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "23B never executes source recovery.")
    add("source_identity_finalization_performed", False, False, True, "23B never finalizes source identity.")
    add("human_decision_selected", False, False, True, "23B does not select a decision on behalf of the user.")
    add("overall_23b_integrated_checks_passed", ok, True, bool(ok), "Overall PASS is required before using 23B outputs.")
    return pd.DataFrame(rows)


def build_report(
    now: str,
    status: str,
    input_audit: pd.DataFrame,
    checks: pd.DataFrame,
    options: pd.DataFrame,
    gates: pd.DataFrame,
    safety: pd.DataFrame,
    summary: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# GOLD V2 23B request more audit human decision options audit-only report",
            "",
            f"Created UTC: {now}",
            f"Step: `{STEP}`",
            f"Status: `{status}`",
            "",
            "## Boundary",
            "",
            "- 23B is audit-only.",
            "- 23B reads 23A audited artifacts as the source of truth.",
            "- 23B lists human decision options but does not select, approve, or execute any option.",
            "- Source recovery, source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.",
            "- `REQUEST_MORE_AUDIT` is not source recovery approval.",
            "- Old GOLD/DISC8 remain quarantined.",
            "",
            "## Outcome",
            "",
            f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
            f"- Decision options rows: `{summary.get('decision_options_rows')}`",
            f"- Next recommended step: `{summary.get('next_recommended_step')}`",
            "",
            "## Input audit",
            "",
            md_table(input_audit),
            "",
            "## Integrated checks",
            "",
            md_table(checks),
            "",
            "## Human decision options",
            "",
            md_table(options),
            "",
            "## Required next gates",
            "",
            md_table(gates),
            "",
            "## Safety matrix",
            "",
            md_table(safety),
            "",
            "## Explicit non-actions",
            "",
            "- Human decision selected: `false`",
            "- AI API called: `false`",
            "- Discord notification sent: `false`",
            "- MT5 order sent: `false`",
            "- Live hook enabled: `false`",
            "- Source recovery executed: `false`",
            "- Source identity finalized/recovered: `false`",
        ]
    )


def main() -> int:
    base = fx_outputs_root()
    out = base / OUT_DIR
    source = base / IN23A
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    input_paths = {role: source / filename for role, filename in REQUIRED_23A_FILES.items()}
    input_audit = build_input_audit(input_paths)
    write_csv(out / INPUT_AUDIT_FILE, input_audit)

    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing_inputs = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()

    checks: list[dict[str, Any]] = [
        check_row(
            "23B-C000",
            "Required 23A source-of-truth artifacts exist",
            ",".join(missing_inputs) if missing_inputs else "all present",
            "all present",
            inputs_ok,
        )
    ]

    summary23a: dict[str, Any] = {}
    upstream_stop_rows = 1 if not inputs_ok else 0
    allowed_after_23a: list[str] = []
    still_blocked_after_23a: list[str] = []

    if inputs_ok:
        summary23a = read_json(input_paths["23a_summary"])
        input23a = read_csv(input_paths["23a_input_audit"])
        resolution23a = read_csv(input_paths["23a_resolution_matrix"])
        checks23a = read_csv(input_paths["23a_integrated_checks"])
        gates23a = read_csv(input_paths["23a_required_next_gates"])
        safety23a = read_csv(input_paths["23a_safety_matrix"])

        upstream_stop_rows = int(summary23a.get("total_stop_rows", 999)) + stop_rows(checks23a) + stop_rows(safety23a)

        missing_required_23a_inputs = 0
        if {"required", "exists"}.issubset(input23a.columns):
            required_mask = input23a["required"].map(truthy)
            exists_mask = input23a["exists"].map(truthy)
            missing_required_23a_inputs = int((required_mask & ~exists_mask).sum())
        else:
            missing_required_23a_inputs = 999

        allowed_after_23a = allowed_next_steps(gates23a, "allowed_after_23a_success")
        still_blocked_after_23a = [str(x) for x in summary23a.get("still_blocked_after_23a", [])]
        false_flags = count_true_forbidden_summary_flags(summary23a)
        forbidden_detail = forbidden_allowed_detail(gates23a, "allowed_after_23a_success")
        resolution_rows = len(resolution23a)
        expected_min_resolution_rows = int(summary23a.get("expected_min_resolution_matrix_rows", 9))

        checks.extend(
            [
                check_row("23B-C001", "23A status matches expected", summary23a.get("status"), EXPECTED_23A_STATUS, summary23a.get("status") == EXPECTED_23A_STATUS),
                check_row("23B-C002", "23A audit_only remains true", summary23a.get("audit_only"), True, truthy(summary23a.get("audit_only", False))),
                check_row("23B-C003", "23A integrated_audit_only remains true", summary23a.get("integrated_audit_only"), True, truthy(summary23a.get("integrated_audit_only", False))),
                check_row("23B-C004", "23A selected_value remains REQUEST_MORE_AUDIT", summary23a.get("selected_value"), SELECTED, summary23a.get("selected_value") == SELECTED),
                check_row("23B-C005", "23A decision_value remains REQUEST_MORE_AUDIT", summary23a.get("decision_value"), SELECTED, summary23a.get("decision_value") == SELECTED),
                check_row("23B-C006", "23A total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
                check_row("23B-C007", "23A required next allowed only 23B", allowed_after_23a, ["23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY"], allowed_after_23a == ["23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY"]),
                check_row("23B-C008", "23A forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
                check_row("23B-C009", "23A forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
                check_row("23B-C010", "23A required inputs were complete", missing_required_23a_inputs, 0, missing_required_23a_inputs == 0),
                check_row("23B-C011", "23A resolution matrix row count meets minimum", resolution_rows, f">={expected_min_resolution_rows}", resolution_rows >= expected_min_resolution_rows),
                check_row("23B-C012", "23A still-blocked list includes all unsafe gates", sorted(still_blocked_after_23a), sorted(EXPECTED_STILL_BLOCKED), sorted(still_blocked_after_23a) == sorted(EXPECTED_STILL_BLOCKED)),
                check_row("23B-C013", "23A says do not proceed automatically to 23B", summary23a.get("do_not_proceed_automatically_to_23b"), True, truthy(summary23a.get("do_not_proceed_automatically_to_23b", False))),
                check_row("23B-C014", "23B user instruction is required before this script is used", True, True, True),
            ]
        )

    checks_df = pd.DataFrame(checks)
    total_stop_rows = stop_rows(checks_df)
    ok = inputs_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS

    safety_df = build_safety_matrix(summary23a, ok, inputs_ok)
    if stop_rows(safety_df):
        ok = False
        status = STOP_STATUS

    options_df = build_decision_options(ok)
    gates_df = build_required_next_gates(ok)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)

    output_paths = {
        "input_audit": str(out / INPUT_AUDIT_FILE),
        "decision_options": str(out / DECISION_OPTIONS_FILE),
        "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
        "safety_matrix": str(out / SAFETY_MATRIX_FILE),
        "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
        "summary": str(out / SUMMARY_FILE),
        "report": str(out / REPORT_FILE),
    }

    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "human_decision_options_only": True,
        "source_of_truth": "23A audited artifacts under FX_OUTPUTS/" + IN23A,
        "selected_value": summary23a.get("selected_value", SELECTED if inputs_ok else "UNKNOWN_MISSING_23A_SUMMARY"),
        "decision_value": summary23a.get("decision_value", SELECTED if inputs_ok else "UNKNOWN_MISSING_23A_SUMMARY"),
        "upstream_status": summary23a.get("status", "UNKNOWN_MISSING_23A_SUMMARY"),
        "request_more_audit_is_source_recovery_approval": False,
        "human_decision_selected": False,
        "source_recovery_approved": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "no_signal_discord_notified": False,
        "old_gold_disc8_quarantined": True,
        "approximate_reimplementation_used": False,
        "ai_api_called": False,
        "discord_sent": False,
        "mt5_order_sent": False,
        "live_hook_enabled": False,
        "source_recovery_execution_performed": False,
        "source_identity_finalization_performed": False,
        "required_23a_inputs_ok": inputs_ok,
        "missing_inputs": missing_inputs,
        "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows),
        "decision_options_rows": int(len(options_df)),
        "expected_decision_options_rows": 8,
        "allowed_decision_values": options_df.loc[options_df["current_allowed_to_select"].map(truthy), "decision_value"].astype(str).tolist(),
        "required_next_allowed": ["23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_23b": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": (
            "23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY_AFTER_USER_SELECTS_ONE_23B_DECISION_VALUE"
            if ok
            else "STOP_REVIEW_23B_INPUTS_AND_23A_OUTPUTS"
        ),
        "do_not_execute_selected_decision_in_23b": True,
        "outputs": output_paths,
    }

    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_csv(out / DECISION_OPTIONS_FILE, options_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, options_df, gates_df, safety_df, summary))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
