#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STEP = "23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_23c_request_more_audit_human_decision_intake_audit_only"
IN23B = "gold_v2_23b_request_more_audit_human_decision_options_audit_only"

SELECTED = "REQUEST_MORE_AUDIT"
EXPECTED_23B_STATUS = "REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
STATUS_TEMPLATE_READY = "REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SELECTED_SOURCE_RECOVERY_STILL_BLOCKED"
STATUS_VALIDATED = "REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
STOP_STATUS = "23C_STOP_REVIEW_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_INPUTS"

REPORT_FILE = "GOLD_V2_23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_23c_request_more_audit_human_decision_intake_summary.json"
INPUT_AUDIT_FILE = "gold_v2_23c_input_audit.csv"
DECISION_INTAKE_TEMPLATE_FILE = "gold_v2_23c_human_decision_input_template.json"
DECISION_INTAKE_RESULT_FILE = "gold_v2_23c_human_decision_intake_result.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_23c_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_23c_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_23c_safety_matrix.csv"
OPTION_SNAPSHOT_FILE = "gold_v2_23c_allowed_23b_decision_values.csv"

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
    "human_decision_selected",
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

REQUIRED_23B_FILES = {
    "23b_report": "GOLD_V2_23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md",
    "23b_summary": "gold_v2_23b_request_more_audit_human_decision_options_summary.json",
    "23b_input_audit": "gold_v2_23b_input_audit.csv",
    "23b_decision_options": "gold_v2_23b_human_decision_options.csv",
    "23b_integrated_checks": "gold_v2_23b_integrated_checks.csv",
    "23b_required_next_gates": "gold_v2_23b_required_next_gates.csv",
    "23b_safety_matrix": "gold_v2_23b_safety_matrix.csv",
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
                "source_of_truth_role": "23B audited artifact",
                "notes": "23C reads this artifact only; no recovery/live/AI/external execution.",
            }
        )
    return pd.DataFrame(rows)


def normalize_decision_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_decision_value(cli_value: str | None, out_dir: Path) -> tuple[str, str, str]:
    cli = normalize_decision_value(cli_value)
    if cli:
        return cli, "cli_argument", "--decision-value"
    env = normalize_decision_value(os.environ.get("GOLD_V2_23C_DECISION_VALUE"))
    if env:
        return env, "environment", "GOLD_V2_23C_DECISION_VALUE"
    input_json = out_dir / "gold_v2_23c_human_decision_input.json"
    if long_path(input_json).exists():
        try:
            payload = read_json(input_json)
            file_value = normalize_decision_value(payload.get("decision_value"))
            return file_value, "json_file", str(input_json)
        except Exception as exc:
            return "", "json_file_error", f"{input_json}: {exc}"
    return "", "none", "no decision value supplied"


def build_template(allowed_values: list[str]) -> dict[str, Any]:
    return {
        "decision_value": "",
        "instructions": [
            "Copy exactly one value from allowed_decision_values into decision_value.",
            "This file is only for audit-only validation.",
            "Do not use this file to approve or execute source recovery, live, Discord, MT5, AI API, or final signal.",
        ],
        "allowed_decision_values": allowed_values,
        "not_approval_values": [
            "REQUEST_MORE_AUDIT",
            "REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY",
            "REQUEST_SOURCE_IDENTITY_FINALIZATION_PRECHECK_AUDIT_ONLY",
            "REQUEST_LIVE_EVALUATOR_PRECHECK_AUDIT_ONLY",
            "REQUEST_FINAL_SIGNAL_PRECHECK_AUDIT_ONLY",
            "REQUEST_EXTERNAL_ACTION_PRECHECK_AUDIT_ONLY",
            "REQUEST_OLD_GOLD_DISC8_DEQUARANTINE_PRECHECK_AUDIT_ONLY",
        ],
        "forbidden_execution_approval_values": [
            "APPROVE_SOURCE_RECOVERY_EXECUTION",
            "APPROVE_SOURCE_IDENTITY_FINALIZATION",
            "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION",
            "APPROVE_FINAL_SIGNAL",
            "APPROVE_DISCORD_SEND",
            "APPROVE_MT5_ORDER",
            "APPROVE_AI_API_REVIEW",
            "APPROVE_LIVE_HOOK",
        ],
    }


def build_intake_result(decision_value: str, source: str, detail: str, allowed_values: list[str], ok: bool, upstream_ok: bool) -> pd.DataFrame:
    supplied = bool(decision_value)
    valid = supplied and decision_value in allowed_values
    unsafe_approval = decision_value.startswith("APPROVE_") if supplied else False
    if not upstream_ok:
        status = "STOP_UPSTREAM_23B_NOT_READY"
    elif unsafe_approval:
        status = "STOP_DIRECT_EXECUTION_APPROVAL_VALUE_NOT_ALLOWED_IN_23C"
    elif not supplied:
        status = "WAITING_FOR_HUMAN_DECISION_VALUE"
    elif valid:
        status = "VALID_AUDIT_ONLY_DECISION_VALUE"
    else:
        status = "STOP_UNKNOWN_DECISION_VALUE"
    return pd.DataFrame(
        [
            {
                "decision_value": decision_value if supplied else "NO_HUMAN_DECISION_VALUE_PROVIDED",
                "source": source,
                "source_detail": detail,
                "supplied": supplied,
                "valid_allowed_23b_value": valid,
                "unsafe_direct_approval_value": unsafe_approval,
                "selected_by_script": False,
                "execution_approved": False,
                "source_recovery_approved": False,
                "source_identity_finalization_approved": False,
                "live_or_final_approved": False,
                "external_action_approved": False,
                "status": status,
                "notes": "23C validates or templates a decision value only. It never executes the selected value.",
            }
        ]
    )


def build_required_next_gates(ok: bool, valid_decision: bool, decision_value: str) -> pd.DataFrame:
    if ok and valid_decision:
        allowed_intake_next = True
        intake_reason = ""
    elif ok:
        allowed_intake_next = False
        intake_reason = "No valid human decision value has been supplied yet."
    else:
        allowed_intake_next = False
        intake_reason = "23C checks did not pass."

    return pd.DataFrame(
        [
            {
                "next_step": "23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY",
                "name": "Route a validated 23B decision value without executing it",
                "purpose": "Audit-only routing after 23C validates a user-supplied decision value.",
                "allowed_after_23c_success": allowed_intake_next,
                "required_human_decision_value_later": "Validated 23B decision value already supplied to 23C.",
                "still_blocked_reason": intake_reason,
            },
            {
                "next_step": "WAIT_FOR_HUMAN_DECISION_VALUE",
                "name": "Wait for one exact 23B decision_value",
                "purpose": "No execution. User must select exactly one 23B value before routing can continue.",
                "allowed_after_23c_success": bool(ok and not valid_decision),
                "required_human_decision_value_later": "One exact value from gold_v2_23b_human_decision_options.csv",
                "still_blocked_reason": "" if ok and not valid_decision else "Not applicable when a valid decision is already supplied or 23C stopped.",
            },
            {
                "next_step": "SOURCE_IDENTITY_FINALIZATION",
                "name": "Finalize source identity",
                "purpose": "Would finalize recovered/source identity state.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION",
                "still_blocked_reason": "23C validates intake only and does not grant finalization approval.",
            },
            {
                "next_step": "SOURCE_RECOVERY",
                "name": "Execute source recovery",
                "purpose": "Would run recovery actions rather than audit-only review.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION",
                "still_blocked_reason": "23C validates intake only and does not grant recovery approval.",
            },
            {
                "next_step": "LIVE",
                "name": "Enable live evaluator/use",
                "purpose": "Would create or enable live behavior.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION",
                "still_blocked_reason": "GOLD V2 remains audit-only.",
            },
            {
                "next_step": "FINAL_SIGNAL",
                "name": "Enable final signal",
                "purpose": "Would produce final signal behavior.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL",
                "still_blocked_reason": "Final signal remains blocked.",
            },
            {
                "next_step": "DISCORD_SEND",
                "name": "Send Discord notification",
                "purpose": "Would send notifications externally.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_DISCORD_SEND",
                "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify.",
            },
            {
                "next_step": "MT5_ORDER",
                "name": "Place MT5 order",
                "purpose": "Would place or prepare live orders.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_MT5_ORDER",
                "still_blocked_reason": "MT5 order path remains blocked.",
            },
            {
                "next_step": "AI_API",
                "name": "Call AI API",
                "purpose": "Would call an external AI review API.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_AI_API_REVIEW",
                "still_blocked_reason": "AI API remains blocked.",
            },
            {
                "next_step": "LIVE_HOOK",
                "name": "Enable live hook",
                "purpose": "Would connect audit logic to live runtime hooks.",
                "allowed_after_23c_success": False,
                "required_human_decision_value_later": "APPROVE_LIVE_HOOK",
                "still_blocked_reason": "Live hook remains blocked.",
            },
        ]
    )


def build_safety_matrix(summary23b: dict[str, Any], ok: bool, inputs_ok: bool, valid_decision: bool) -> pd.DataFrame:
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

    add("audit_only", True, True, True, "23C writes audit artifacts only.")
    add("human_decision_intake_only", True, True, True, "23C validates/templates a decision value but never executes it.")
    add("required_23b_inputs_exist", inputs_ok, True, inputs_ok, "All 23B source-of-truth artifacts must exist.")
    add("request_more_audit_is_not_source_recovery_approval", SELECTED, "NOT_APPROVAL", True, "REQUEST_MORE_AUDIT remains audit-only.")
    add("human_decision_validated", valid_decision, "optional", True, "False is allowed when no decision value was supplied.")
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
        observed = summary23b.get(key, False) if inputs_ok else "UNKNOWN_MISSING_23B_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        observed = get_external(summary23b, key) if inputs_ok else "UNKNOWN_MISSING_23B_SUMMARY"
        add(key, observed, False, inputs_ok and falsey(observed), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("approximate_reimplementation_used", False, False, True, "23C does not recreate strategy/source logic.")
    add("ai_api_called", False, False, True, "23C never calls AI API.")
    add("discord_sent", False, False, True, "23C never sends Discord.")
    add("mt5_order_sent", False, False, True, "23C never sends MT5 orders.")
    add("live_hook_enabled", False, False, True, "23C never enables live hooks.")
    add("source_recovery_execution_performed", False, False, True, "23C never executes source recovery.")
    add("source_identity_finalization_performed", False, False, True, "23C never finalizes source identity.")
    add("human_decision_selected_by_script", False, False, True, "23C never chooses a decision value for the user.")
    add("overall_23c_upstream_checks_passed", ok, True, bool(ok), "Upstream PASS is required before using 23C outputs.")
    return pd.DataFrame(rows)


def build_report(
    now: str,
    status: str,
    input_audit: pd.DataFrame,
    checks: pd.DataFrame,
    options: pd.DataFrame,
    intake_result: pd.DataFrame,
    gates: pd.DataFrame,
    safety: pd.DataFrame,
    summary: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# GOLD V2 23C request more audit human decision intake audit-only report",
            "",
            f"Created UTC: {now}",
            f"Step: `{STEP}`",
            f"Status: `{status}`",
            "",
            "## Boundary",
            "",
            "- 23C is audit-only.",
            "- 23C reads 23B audited artifacts as the source of truth.",
            "- 23C creates a decision input template and optionally validates one user-supplied 23B decision value.",
            "- 23C does not choose, approve, or execute any decision value.",
            "- Source recovery, source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.",
            "- `REQUEST_MORE_AUDIT` is not source recovery approval.",
            "- Old GOLD/DISC8 remain quarantined.",
            "",
            "## Outcome",
            "",
            f"- Total STOP rows: `{summary.get('total_stop_rows')}`",
            f"- Decision value supplied: `{summary.get('human_decision_value_supplied')}`",
            f"- Decision value valid: `{summary.get('human_decision_value_valid')}`",
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
            "## Allowed 23B decision values snapshot",
            "",
            md_table(options),
            "",
            "## Human decision intake result",
            "",
            md_table(intake_result),
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
            "- Human decision selected by script: `false`",
            "- Execution approved: `false`",
            "- AI API called: `false`",
            "- Discord notification sent: `false`",
            "- MT5 order sent: `false`",
            "- Live hook enabled: `false`",
            "- Source recovery executed: `false`",
            "- Source identity finalized/recovered: `false`",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=STEP)
    parser.add_argument(
        "--decision-value",
        default="",
        help="Optional exact decision_value from 23B. If omitted, 23C writes an input template and waits.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = fx_outputs_root()
    out = base / OUT_DIR
    source = base / IN23B
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    input_paths = {role: source / filename for role, filename in REQUIRED_23B_FILES.items()}
    input_audit = build_input_audit(input_paths)
    write_csv(out / INPUT_AUDIT_FILE, input_audit)

    inputs_ok = bool(input_audit["exists"].all()) if not input_audit.empty else False
    missing_inputs = input_audit.loc[~input_audit["exists"], "role"].astype(str).tolist()

    checks: list[dict[str, Any]] = [
        check_row(
            "23C-C000",
            "Required 23B source-of-truth artifacts exist",
            ",".join(missing_inputs) if missing_inputs else "all present",
            "all present",
            inputs_ok,
        )
    ]

    summary23b: dict[str, Any] = {}
    upstream_stop_rows = 1 if not inputs_ok else 0
    allowed_decision_values: list[str] = []
    allowed_after_23b: list[str] = []
    still_blocked_after_23b: list[str] = []

    if inputs_ok:
        summary23b = read_json(input_paths["23b_summary"])
        input23b = read_csv(input_paths["23b_input_audit"])
        options23b = read_csv(input_paths["23b_decision_options"])
        checks23b = read_csv(input_paths["23b_integrated_checks"])
        gates23b = read_csv(input_paths["23b_required_next_gates"])
        safety23b = read_csv(input_paths["23b_safety_matrix"])

        upstream_stop_rows = int(summary23b.get("total_stop_rows", 999)) + stop_rows(checks23b) + stop_rows(safety23b)

        missing_required_23b_inputs = 0
        if {"required", "exists"}.issubset(input23b.columns):
            required_mask = input23b["required"].map(truthy)
            exists_mask = input23b["exists"].map(truthy)
            missing_required_23b_inputs = int((required_mask & ~exists_mask).sum())
        else:
            missing_required_23b_inputs = 999

        if "decision_value" in options23b.columns:
            allowed_decision_values = options23b["decision_value"].astype(str).tolist()
            options_snapshot = options23b[["option_id", "decision_value", "option_type", "current_allowed_to_select", "status"]].copy()
        else:
            options_snapshot = pd.DataFrame(columns=["option_id", "decision_value", "option_type", "current_allowed_to_select", "status"])

        allowed_after_23b = allowed_next_steps(gates23b, "allowed_after_23b_success")
        still_blocked_after_23b = [str(x) for x in summary23b.get("still_blocked_after_23b", [])]
        false_flags = count_true_forbidden_summary_flags(summary23b)
        forbidden_detail = forbidden_allowed_detail(gates23b, "allowed_after_23b_success")
        expected_decision_options_rows = int(summary23b.get("expected_decision_options_rows", 8))

        checks.extend(
            [
                check_row("23C-C001", "23B status matches expected", summary23b.get("status"), EXPECTED_23B_STATUS, summary23b.get("status") == EXPECTED_23B_STATUS),
                check_row("23C-C002", "23B audit_only remains true", summary23b.get("audit_only"), True, truthy(summary23b.get("audit_only", False))),
                check_row("23C-C003", "23B human_decision_options_only remains true", summary23b.get("human_decision_options_only"), True, truthy(summary23b.get("human_decision_options_only", False))),
                check_row("23C-C004", "23B selected_value remains REQUEST_MORE_AUDIT", summary23b.get("selected_value"), SELECTED, summary23b.get("selected_value") == SELECTED),
                check_row("23C-C005", "23B decision_value remains REQUEST_MORE_AUDIT", summary23b.get("decision_value"), SELECTED, summary23b.get("decision_value") == SELECTED),
                check_row("23C-C006", "23B total upstream/own STOP rows are zero", upstream_stop_rows, 0, upstream_stop_rows == 0),
                check_row("23C-C007", "23B required next allowed only 23C", allowed_after_23b, ["23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY"], allowed_after_23b == ["23C_REQUEST_MORE_AUDIT_HUMAN_DECISION_INTAKE_AUDIT_ONLY"]),
                check_row("23C-C008", "23B forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
                check_row("23C-C009", "23B forbidden summary/external flags remain false", false_flags, 0, false_flags == 0),
                check_row("23C-C010", "23B required inputs were complete", missing_required_23b_inputs, 0, missing_required_23b_inputs == 0),
                check_row("23C-C011", "23B decision options row count matches expected", len(allowed_decision_values), expected_decision_options_rows, len(allowed_decision_values) == expected_decision_options_rows),
                check_row("23C-C012", "23B still-blocked list includes all unsafe gates", sorted(still_blocked_after_23b), sorted(EXPECTED_STILL_BLOCKED), sorted(still_blocked_after_23b) == sorted(EXPECTED_STILL_BLOCKED)),
                check_row("23C-C013", "23B did not select a human decision", summary23b.get("human_decision_selected"), False, falsey(summary23b.get("human_decision_selected", False))),
                check_row("23C-C014", "23B says selected decision must not execute in 23B", summary23b.get("do_not_execute_selected_decision_in_23b"), True, truthy(summary23b.get("do_not_execute_selected_decision_in_23b", False))),
            ]
        )
    else:
        options_snapshot = pd.DataFrame(columns=["option_id", "decision_value", "option_type", "current_allowed_to_select", "status"])

    upstream_checks_df = pd.DataFrame(checks)
    upstream_ok = inputs_ok and stop_rows(upstream_checks_df) == 0

    decision_value, decision_source, decision_detail = load_decision_value(args.decision_value, out)
    write_json(out / DECISION_INTAKE_TEMPLATE_FILE, build_template(allowed_decision_values))

    intake_result_df = build_intake_result(decision_value, decision_source, decision_detail, allowed_decision_values, ok=True, upstream_ok=upstream_ok)
    human_decision_value_supplied = bool(decision_value)
    human_decision_value_valid = bool(human_decision_value_supplied and decision_value in allowed_decision_values)
    unsafe_direct_approval = bool(decision_value.startswith("APPROVE_")) if human_decision_value_supplied else False

    intake_checks = [
        check_row("23C-C015", "No direct APPROVE_* execution value is accepted", decision_value if decision_value else "NO_VALUE", "not APPROVE_*", not unsafe_direct_approval),
    ]
    if human_decision_value_supplied:
        intake_checks.append(
            check_row("23C-C016", "Supplied decision value is one of the 23B allowed decision values", decision_value, "one 23B decision_value", human_decision_value_valid)
        )
    else:
        intake_checks.append(
            check_row("23C-C016", "No human decision value supplied; template mode is allowed", "NO_HUMAN_DECISION_VALUE_PROVIDED", "template mode", True)
        )

    checks_df = pd.concat([upstream_checks_df, pd.DataFrame(intake_checks)], ignore_index=True)
    upstream_and_intake_ok = stop_rows(checks_df) == 0 and upstream_ok

    safety_df = build_safety_matrix(summary23b, upstream_and_intake_ok, inputs_ok, human_decision_value_valid)
    safety_stop_rows = stop_rows(safety_df)

    if safety_stop_rows:
        overall_ok = False
        status = STOP_STATUS
    elif not upstream_and_intake_ok:
        overall_ok = False
        status = STOP_STATUS
    elif human_decision_value_valid:
        overall_ok = True
        status = STATUS_VALIDATED
    else:
        overall_ok = True
        status = STATUS_TEMPLATE_READY

    gates_df = build_required_next_gates(overall_ok, human_decision_value_valid, decision_value)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)

    output_paths = {
        "input_audit": str(out / INPUT_AUDIT_FILE),
        "allowed_23b_decision_values": str(out / OPTION_SNAPSHOT_FILE),
        "decision_input_template": str(out / DECISION_INTAKE_TEMPLATE_FILE),
        "decision_intake_result": str(out / DECISION_INTAKE_RESULT_FILE),
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
        "human_decision_intake_only": True,
        "source_of_truth": "23B audited artifacts under FX_OUTPUTS/" + IN23B,
        "selected_value": summary23b.get("selected_value", SELECTED if inputs_ok else "UNKNOWN_MISSING_23B_SUMMARY"),
        "decision_value": summary23b.get("decision_value", SELECTED if inputs_ok else "UNKNOWN_MISSING_23B_SUMMARY"),
        "upstream_status": summary23b.get("status", "UNKNOWN_MISSING_23B_SUMMARY"),
        "request_more_audit_is_source_recovery_approval": False,
        "human_decision_value_supplied": human_decision_value_supplied,
        "human_decision_value": decision_value if human_decision_value_supplied else "NO_HUMAN_DECISION_VALUE_PROVIDED",
        "human_decision_value_source": decision_source,
        "human_decision_value_valid": human_decision_value_valid,
        "human_decision_selected_by_script": False,
        "execution_approved": False,
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
        "required_23b_inputs_ok": inputs_ok,
        "missing_inputs": missing_inputs,
        "upstream_stop_rows": int(upstream_stop_rows),
        "total_stop_rows": int(total_stop_rows),
        "allowed_decision_values_count": int(len(allowed_decision_values)),
        "allowed_decision_values": allowed_decision_values,
        "required_next_allowed": (
            ["23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY"]
            if human_decision_value_valid and overall_ok
            else (["WAIT_FOR_HUMAN_DECISION_VALUE"] if overall_ok else [])
        ),
        "still_blocked_after_23c": EXPECTED_STILL_BLOCKED,
        "next_recommended_step": (
            "23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_ONLY_AFTER_VALIDATED_HUMAN_DECISION_VALUE"
            if human_decision_value_valid and overall_ok
            else ("WAIT_FOR_ONE_EXACT_23B_DECISION_VALUE" if overall_ok else "STOP_REVIEW_23C_INPUTS_AND_23B_OUTPUTS")
        ),
        "do_not_execute_selected_decision_in_23c": True,
        "outputs": output_paths,
    }

    write_csv(out / OPTION_SNAPSHOT_FILE, options_snapshot)
    write_csv(out / DECISION_INTAKE_RESULT_FILE, intake_result_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(now, status, input_audit, checks_df, options_snapshot, intake_result_df, gates_df, safety_df, summary))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
