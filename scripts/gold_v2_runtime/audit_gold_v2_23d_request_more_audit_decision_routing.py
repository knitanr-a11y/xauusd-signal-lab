#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STEP = "23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY"
OUT_DIR = "gold_v2_23d_request_more_audit_decision_routing_audit_only"
IN23C = "gold_v2_23c_request_more_audit_human_decision_intake_audit_only"

EXPECTED_DECISION_VALUE = "REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY"
EXPECTED_23C_STATUS = "REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
SUCCESS_STATUS = "REQUEST_MORE_AUDIT_DECISION_ROUTED_TO_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
STOP_STATUS = "23D_STOP_REVIEW_REQUEST_MORE_AUDIT_DECISION_ROUTING_INPUTS"

REPORT_FILE = "GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_23d_request_more_audit_decision_routing_summary.json"
INPUT_AUDIT_FILE = "gold_v2_23d_input_audit.csv"
ROUTING_MATRIX_FILE = "gold_v2_23d_decision_routing_matrix.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_23d_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_23d_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_23d_safety_matrix.csv"

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
    "execution_approved",
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
    "discord_sent",
    "mt5_order_sent",
    "live_hook_enabled",
    "source_recovery_execution_performed",
    "source_identity_finalization_performed",
]

EXTERNAL_ACTION_KEYS = [
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
]

REQUIRED_23C_FILES = {
    "23c_report": "GOLD_V2_23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY_REPORT.md",
    "23c_summary": "gold_v2_23c_request_more_audit_human_decision_intake_summary.json",
    "23c_input_audit": "gold_v2_23c_input_audit.csv",
    "23c_allowed_values": "gold_v2_23c_allowed_23b_decision_values.csv",
    "23c_intake_result": "gold_v2_23c_human_decision_intake_result.csv",
    "23c_integrated_checks": "gold_v2_23c_integrated_checks.csv",
    "23c_required_next_gates": "gold_v2_23c_required_next_gates.csv",
    "23c_safety_matrix": "gold_v2_23c_safety_matrix.csv",
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


def build_input_audit(input_paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role, path in input_paths.items():
        rows.append(
            {
                "role": role,
                "path": str(path),
                "required": True,
                "exists": long_path(path).exists(),
                "source_of_truth_role": "23C validated artifact",
                "notes": "23D reads this artifact only; no recovery/live/AI/external execution.",
            }
        )
    return pd.DataFrame(rows)


def build_routing_matrix(ok: bool, selected_value: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "route_id": "23D-R001",
                "validated_decision_value": selected_value if selected_value else "UNKNOWN_OR_NOT_VALIDATED",
                "route_target": "24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY" if ok else "STOP_OR_WAIT_FOR_VALIDATED_23C",
                "route_type": "audit_only_precheck_not_approval",
                "execution_approved": False,
                "source_recovery_approved": False,
                "source_recovery_executed": False,
                "allowed_current_action": "Route to source recovery precheck audit-only." if ok else "Do not route until 23C is validated.",
                "blocked_actions": "SOURCE_RECOVERY; SOURCE_IDENTITY_FINALIZATION; LIVE; FINAL_SIGNAL; DISCORD_SEND; MT5_ORDER; AI_API; LIVE_HOOK",
                "required_future_approval_for_execution": "APPROVE_SOURCE_RECOVERY_EXECUTION",
                "risk_if_misread": "High if precheck routing is treated as recovery approval.",
                "status": "ROUTED_AUDIT_ONLY" if ok else "STOP_NOT_ROUTED",
            }
        ]
    )


def build_required_next_gates(ok: bool) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "next_step": "24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY",
                "name": "Source recovery precheck audit-only",
                "purpose": "Determine prerequisites, evidence, blockers, and required explicit approvals before any recovery execution.",
                "allowed_after_23d_success": bool(ok),
                "required_human_decision_value_later": "None for precheck; APPROVE_SOURCE_RECOVERY_EXECUTION would be required later for execution.",
                "still_blocked_reason": "" if ok else "23D routing checks did not pass.",
            },
            {
                "next_step": "SOURCE_IDENTITY_FINALIZATION",
                "name": "Finalize source identity",
                "purpose": "Would finalize recovered/source identity state.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION",
                "still_blocked_reason": "23D routes precheck only and does not grant finalization approval.",
            },
            {
                "next_step": "SOURCE_RECOVERY",
                "name": "Execute source recovery",
                "purpose": "Would run recovery actions rather than audit-only review.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION",
                "still_blocked_reason": "23D routes precheck only and does not grant recovery approval.",
            },
            {
                "next_step": "LIVE",
                "name": "Enable live evaluator/use",
                "purpose": "Would create or enable live behavior.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION",
                "still_blocked_reason": "GOLD V2 remains audit-only.",
            },
            {
                "next_step": "FINAL_SIGNAL",
                "name": "Enable final signal",
                "purpose": "Would produce final signal behavior.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL",
                "still_blocked_reason": "Final signal remains blocked.",
            },
            {
                "next_step": "DISCORD_SEND",
                "name": "Send Discord notification",
                "purpose": "Would send notifications externally.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_DISCORD_SEND",
                "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify.",
            },
            {
                "next_step": "MT5_ORDER",
                "name": "Place MT5 order",
                "purpose": "Would place or prepare live orders.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_MT5_ORDER",
                "still_blocked_reason": "MT5 order path remains blocked.",
            },
            {
                "next_step": "AI_API",
                "name": "Call AI API",
                "purpose": "Would call an external AI review API.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_AI_API_REVIEW",
                "still_blocked_reason": "AI API remains blocked.",
            },
            {
                "next_step": "LIVE_HOOK",
                "name": "Enable live hook",
                "purpose": "Would connect audit logic to live runtime hooks.",
                "allowed_after_23d_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_HOOK",
                "still_blocked_reason": "Live hook remains blocked.",
            },
        ]
    )


def build_safety_matrix(summary23c: dict[str, Any], ok: bool, inputs_ok: bool) -> pd.DataFrame:
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

    add("audit_only", True, True, True, "23D writes audit artifacts only.")
    add("decision_routing_only", True, True, True, "23D routes a validated decision to an audit-only precheck and never executes it.")
    add("required_23c_inputs_exist", inputs_ok, True, inputs_ok, "All 23C source-of-truth artifacts must exist.")
    add("validated_decision_is_precheck_not_approval", summary23c.get("human_decision_value", "UNKNOWN"), EXPECTED_DECISION_VALUE, inputs_ok and summary23c.get("human_decision_value") == EXPECTED_DECISION_VALUE, "The selected value is a precheck request, not execution approval.")
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
        observed = summary23c.get(key, False) if inputs_ok else "UNKNOWN_MISSING_23C_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        observed = get_external(summary23c, key) if inputs_ok else "UNKNOWN_MISSING_23C_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "23D does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "23D never calls AI API.")
    add("discord_sent", False, False, True, "23D never sends Discord.")
    add("mt5_order_sent", False, False, True, "23D never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "23D never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "23D never executes source recovery.")
    add("source_identity_finalization_performed", False, False, True, "23D never finalizes source identity.")
    add("overall_23d_routing_checks_passed", ok, True, bool(ok), "Overall PASS is required before using 23D outputs.")
    return pd.DataFrame(rows)


def build_report(
    now: str,
    status: str,
    input_audit: pd.DataFrame,
    checks: pd.DataFrame,
    routing: pd.DataFrame,
    gates: pd.DataFrame,
    safety: pd.DataFrame,
    summary: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# GOLD V2 23D request more audit decision routing audit-only report",
            "",
            f"Created UTC: {now}",
            f"Step: `{STEP}`",
            f"Status: `{status}`",
            "",
            "## Boundary",
            "",
            "- 23D is audit-only.",
            "- 23D reads validated 23C artifacts as the source of truth.",
            "- 23D routes the validated decision value to source recovery precheck audit-only.",
            "- 23D does not approve or execute source recovery.",
            "- Source recovery, source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.",
            "- Old GOLD/DISC8 remain quarantined.",
            "",
            "## Outcome",
            "",
            f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
            f"- Routed decision value: `{summary.get('validated_decision_value')}`",
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
            "## Decision routing matrix",
            "",
            md_table(routing),
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
            "- Source recovery approved: `false`",
            "- Source recovery executed: `false`",
            "- AI API called: `false`",
            "- Discord notification sent: `false`",
            "- MT5 order sent: `false`",
            "- Live hook enabled: `false`",
            "- Source identity finalized/recovered: `false`",
        ]
    )


def main() -> int:
    base = fx_outputs_root()
    out = base / OUT_DIR
    source = base / IN23C
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    input_paths = {role: source / filename for role, filename in REQUIRED_23C_FILES.items()}
    input_audit = build_input_audit(input_paths)
    write_csv(out / INPUT_AUDIT_FILE, input_audit)

    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing_inputs = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()

    checks: list[dict[str, Any]] = [
        check_row("23D-C000", "Required 23C source-of-truth artifacts exist", ",".join(missing_inputs) if missing_inputs else "all present", "all present", inputs_ok)
    ]

    summary23c: dict[str, Any] = {}
    selected_value = ""
    upstream_stop_rows = 1 if not inputs_ok else 0

    if inputs_ok:
        summary23c = read_json(input_paths["23c_summary"])
        input23c = read_csv(input_paths["23c_input_audit"])
        allowed23c = read_csv(input_paths["23c_allowed_values"])
        intake23c = read_csv(input_paths["23c_intake_result"])
        checks23c = read_csv(input_paths["23c_integrated_checks"])
        gates23c = read_csv(input_paths["23c_required_next_gates"])
        safety23c = read_csv(input_paths["23c_safety_matrix"])

        selected_value = str(summary23c.get("human_decision_value", ""))
        upstream_stop_rows = int(summary23c.get("total_stop_rows", 999)) + stop_rows(checks23c) + stop_rows(safety23c)

        missing_required_23c_inputs = 0
        if {"required", "exists"}.issubset(input23c.columns):
            required_mask = input23c["required"].map(truthy)
            exists_mask = input23c["exists"].map(truthy)
            missing_required_23c_inputs = int((required_mask & ~exists_mask).sum())
        else:
            missing_required_23c_inputs = 999

        allowed_values = allowed23c["decision_value"].astype(str).tolist() if "decision_value" in allowed23c.columns else []
        intake_valid = False
        if not intake23c.empty and "valid_allowed_23b_value" in intake23c.columns:
            intake_valid = bool(intake23c["valid_allowed_23b_value"].map(truthy).any())
        intake_not_execution = True
        for column in ["execution_approved", "source_recovery_approved", "source_identity_finalization_approved", "live_or_final_approved", "external_action_approved"]:
            if column in intake23c.columns:
                intake_not_execution = intake_not_execution and not bool(intake23c[column].map(truthy).any())

        allowed_after_23c = allowed_next_steps(gates23c, "allowed_after_23c_success")
        forbidden_detail = forbidden_allowed_detail(gates23c, "allowed_after_23c_success")
        false_flags = count_true_forbidden_summary_flags(summary23c)

        checks.extend(
            [
                check_row("23D-C001", "23C status is validated", summary23c.get("status"), EXPECTED_23C_STATUS, summary23c.get("status") == EXPECTED_23C_STATUS),
                check_row("23D-C002", "23C audit_only remains true", summary23c.get("audit_only"), True, truthy(summary23c.get("audit_only", False))),
                check_row("23D-C003", "23C human_decision_intake_only remains true", summary23c.get("human_decision_intake_only"), True, truthy(summary23c.get("human_decision_intake_only", False))),
                check_row("23D-C004", "23C supplied a human decision value", summary23c.get("human_decision_value_supplied"), True, truthy(summary23c.get("human_decision_value_supplied", False))),
                check_row("23D-C005", "23C human decision value is valid", summary23c.get("human_decision_value_valid"), True, truthy(summary23c.get("human_decision_value_valid", False))),
                check_row("23D-C006", "23C selected value is source recovery precheck audit-only", selected_value, EXPECTED_DECISION_VALUE, selected_value == EXPECTED_DECISION_VALUE),
                check_row("23D-C007", "Selected value is present in allowed 23B decision values", selected_value in allowed_values, True, selected_value in allowed_values),
                check_row("23D-C008", "23C intake result validates selected value", intake_valid, True, intake_valid),
                check_row("23D-C009", "23C intake result grants no execution approval", intake_not_execution, True, intake_not_execution),
                check_row("23D-C010", "23C total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
                check_row("23D-C011", "23C required inputs were complete", missing_required_23c_inputs, 0, missing_required_23c_inputs == 0),
                check_row("23D-C012", "23C required next allowed only 23D", allowed_after_23c, ["23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY"], allowed_after_23c == ["23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY"]),
                check_row("23D-C013", "23C forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
                check_row("23D-C014", "23C forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
                check_row("23D-C015", "23C selected decision is not executed in 23C", summary23c.get("do_not_execute_selected_decision_in_23c"), True, truthy(summary23c.get("do_not_execute_selected_decision_in_23c", False))),
            ]
        )

    checks_df = pd.DataFrame(checks)
    preliminary_ok = inputs_ok and stop_rows(checks_df) == 0
    routing_df = build_routing_matrix(preliminary_ok, selected_value)
    safety_df = build_safety_matrix(summary23c, preliminary_ok, inputs_ok)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = preliminary_ok and total_stop_rows == 0
    status = SUCCESS_STATUS if ok else STOP_STATUS
    if not ok:
        routing_df = build_routing_matrix(False, selected_value)
    gates_df = build_required_next_gates(ok)

    output_paths = {
        "input_audit": str(out / INPUT_AUDIT_FILE),
        "routing_matrix": str(out / ROUTING_MATRIX_FILE),
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
        "decision_routing_only": True,
        "source_of_truth": "23C validated artifacts under FX_OUTPUTS/" + IN23C,
        "validated_decision_value": selected_value if selected_value else "NO_VALIDATED_DECISION_VALUE",
        "route_target": "24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY" if ok else "STOP_OR_WAIT_FOR_VALIDATED_23C",
        "route_target_allowed": bool(ok),
        "request_more_audit_is_source_recovery_approval": False,
        "source_recovery_precheck_requested": bool(ok),
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
        "required_23c_inputs_ok": inputs_ok,
        "missing_inputs": missing_inputs,
        "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows),
        "routing_matrix_rows": int(len(routing_df)),
        "required_next_allowed": ["24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY"] if ok else [],
        "still_blocked_after_23d": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": "24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY" if ok else "STOP_REVIEW_23D_INPUTS_AND_VALIDATED_23C_OUTPUTS",
        "do_not_execute_source_recovery_in_23d": True,
        "outputs": output_paths,
    }

    write_csv(out / ROUTING_MATRIX_FILE, routing_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, routing_df, gates_df, safety_df, summary))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
