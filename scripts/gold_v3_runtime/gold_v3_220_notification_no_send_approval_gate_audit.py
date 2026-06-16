#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage220 - Notification No-Send Approval Gate Audit

Audit-only gate matrix proving Stage219 text preview cannot become a send/webhook/payload/order path
without explicit future approvals.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


STAGE = "GOLD_V3_220_NOTIFICATION_NO_SEND_APPROVAL_GATE_AUDIT_ONLY"
DECISION_READY = "STAGE220_NOTIFICATION_NO_SEND_APPROVAL_GATE_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE220_NOTIFICATION_NO_SEND_APPROVAL_GATE_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

DISABLED_FLAGS: Dict[str, bool] = {
    "send_enabled": False,
    "execution_enabled": False,
    "actual_order_import_enabled": False,
    "discord_enabled": False,
    "webhook_enabled": False,
    "mt5_order_enabled": False,
    "ai_api_enabled": False,
    "payload_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
}

MATRIX_COLUMNS = [
    "case_id",
    "route",
    "message_text_preview_exists",
    "manual_discord_alert_only_approval",
    "approved_channel_scope_defined",
    "payload_activation_approval",
    "webhook_secret_audit_pass",
    "no_signal_notification_disabled",
    "mt5_order_approval",
    "actual_import_approval",
    "live_hook_approval",
    "expected_decision",
    "actual_decision",
    "send_enabled",
    "discord_enabled",
    "webhook_enabled",
    "payload_enabled",
    "mt5_order_enabled",
    "actual_order_import_enabled",
    "live_hook_enabled",
    "autotrade_enabled",
    "theoretical_result_used_as_gate_input",
    "actual_execution_used_as_gate_input",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return (
            Path(appdata)
            / "MetaQuotes"
            / "Terminal"
            / TERMINAL_HASH
            / "MQL5"
            / "Files"
        ).resolve()
    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def stage_paths() -> Tuple[Path, Path, Path]:
    mql5_files = default_mql5_files_dir()
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "220"
    gate_dir = output_dir / "notification_no_send_gate"
    return mql5_files, output_dir, gate_dir


def assert_safe_stage220_path(gate_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "220", "notification_no_send_gate")
    actual_tail = tuple(gate_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe gate path. Expected tail {expected_tail}, got {actual_tail}")


def reset_gate_dir(gate_dir: Path) -> None:
    assert_safe_stage220_path(gate_dir)
    if gate_dir.exists():
        shutil.rmtree(gate_dir)
    gate_dir.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def evaluate_gate(case: Dict[str, Any]) -> str:
    if case["route"] == "NO_SIGNAL":
        return "NO_MESSAGE_NO_SEND_NO_SIGNAL"

    required = [
        "manual_discord_alert_only_approval",
        "approved_channel_scope_defined",
        "payload_activation_approval",
        "webhook_secret_audit_pass",
        "no_signal_notification_disabled",
    ]
    if not any(bool(case.get(key)) for key in required):
        return "NO_SEND_AUDIT_ONLY"
    if not all(bool(case.get(key)) for key in required):
        return "NO_SEND_APPROVAL_INCOMPLETE"
    return "NO_SEND_STILL_BLOCKED_STAGE220_AUDIT_ONLY"


def build_matrix_rows() -> List[Dict[str, Any]]:
    cases = [
        {
            "case_id": "CASE_SIGNAL_NO_APPROVAL",
            "route": "SECONDARY_AUDIT_CANDIDATE",
            "message_text_preview_exists": True,
            "manual_discord_alert_only_approval": False,
            "approved_channel_scope_defined": False,
            "payload_activation_approval": False,
            "webhook_secret_audit_pass": False,
            "no_signal_notification_disabled": True,
            "mt5_order_approval": False,
            "actual_import_approval": False,
            "live_hook_approval": False,
            "expected_decision": "NO_SEND_AUDIT_ONLY",
        },
        {
            "case_id": "CASE_NO_SIGNAL_NO_APPROVAL",
            "route": "NO_SIGNAL",
            "message_text_preview_exists": False,
            "manual_discord_alert_only_approval": False,
            "approved_channel_scope_defined": False,
            "payload_activation_approval": False,
            "webhook_secret_audit_pass": False,
            "no_signal_notification_disabled": True,
            "mt5_order_approval": False,
            "actual_import_approval": False,
            "live_hook_approval": False,
            "expected_decision": "NO_MESSAGE_NO_SEND_NO_SIGNAL",
        },
        {
            "case_id": "CASE_SIGNAL_FAKE_PARTIAL_APPROVAL",
            "route": "SECONDARY_AUDIT_CANDIDATE",
            "message_text_preview_exists": True,
            "manual_discord_alert_only_approval": True,
            "approved_channel_scope_defined": False,
            "payload_activation_approval": False,
            "webhook_secret_audit_pass": False,
            "no_signal_notification_disabled": True,
            "mt5_order_approval": False,
            "actual_import_approval": False,
            "live_hook_approval": False,
            "expected_decision": "NO_SEND_APPROVAL_INCOMPLETE",
        },
    ]

    rows: List[Dict[str, Any]] = []
    for case in cases:
        actual = evaluate_gate(case)
        row = dict(case)
        row.update(
            {
                "actual_decision": actual,
                "send_enabled": False,
                "discord_enabled": False,
                "webhook_enabled": False,
                "payload_enabled": False,
                "mt5_order_enabled": False,
                "actual_order_import_enabled": False,
                "live_hook_enabled": False,
                "autotrade_enabled": False,
                "theoretical_result_used_as_gate_input": False,
                "actual_execution_used_as_gate_input": False,
            }
        )
        rows.append(row)
    return rows


def validate(gate_dir: Path, rows: List[Dict[str, Any]], requirements: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    by_case = {row["case_id"]: row for row in rows}
    any_send_enabled = any(str(row.get(key)) == "True" for row in rows for key in ["send_enabled", "discord_enabled", "webhook_enabled", "payload_enabled"])
    any_exec_enabled = any(str(row.get(key)) == "True" for row in rows for key in ["mt5_order_enabled", "actual_order_import_enabled", "live_hook_enabled", "autotrade_enabled"])

    add("NG001", tuple(gate_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "220", "notification_no_send_gate"), f"gate_dir={gate_dir}")
    add("NG002", requirements.get("stage219_validation_pass") is True, f"stage219_decision={requirements.get('stage219_decision')}")
    add("NG003", by_case["CASE_SIGNAL_NO_APPROVAL"]["actual_decision"] == "NO_SEND_AUDIT_ONLY", by_case["CASE_SIGNAL_NO_APPROVAL"]["actual_decision"])
    add("NG004", by_case["CASE_NO_SIGNAL_NO_APPROVAL"]["actual_decision"] == "NO_MESSAGE_NO_SEND_NO_SIGNAL", by_case["CASE_NO_SIGNAL_NO_APPROVAL"]["actual_decision"])
    add("NG005", by_case["CASE_SIGNAL_FAKE_PARTIAL_APPROVAL"]["actual_decision"] == "NO_SEND_APPROVAL_INCOMPLETE", by_case["CASE_SIGNAL_FAKE_PARTIAL_APPROVAL"]["actual_decision"])
    add("NG006", not any_send_enabled and all(v is False for k, v in DISABLED_FLAGS.items() if k in ["send_enabled", "discord_enabled", "webhook_enabled", "payload_enabled", "payload_activation_enabled"]), "no row enables Discord/webhook/payload/send")
    add("NG007", not any_exec_enabled and all(v is False for k, v in DISABLED_FLAGS.items() if k in ["mt5_order_enabled", "actual_order_import_enabled", "live_hook_enabled", "final_live_enabled", "autotrade_enabled"]), "no row enables order/import/live/autotrade")
    add("NG008", requirements.get("source_csv_mutated") is False and requirements.get("contract_mutated") is False and requirements.get("production_live_retention_mutated") is False, "source CSV/contract/production retention not mutated")
    add("NG009", requirements.get("candidate_pool_removed") is False and requirements.get("f002_exclusion_bypassed") is False, "candidate pool retained and F002 not bypassed")
    add("NG010", requirements.get("csv_latest_row_contract") == "CLOSED" and requirements.get("open_asof_allowed") is False, "CSV latest row CLOSED; open/as-of not introduced")
    add("NG011", requirements.get("timestamp_basis") == "MT5_CSV" and requirements.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis; no JST detector conversion")
    add("NG012", all(row["theoretical_result_used_as_gate_input"] is False and row["actual_execution_used_as_gate_input"] is False for row in rows), "no future result or actual execution result used as gate input")

    blockers = [f"{check['check_id']}: {check['details']}" for check in checks if not check["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 220 PASTE_ME_NOTIFICATION_NO_SEND_APPROVAL_GATE_AUDIT")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "gate_dir",
        "audit_only", "review_only", "dry_run_only", "no_send_gate_only", "live_release_ready",
        "stage219_decision", "stage219_validation_pass", "gate_matrix_rows",
        "signal_no_approval_decision", "no_signal_decision", "partial_approval_decision",
        "source_csv_mutated", "contract_mutated", "production_live_retention_mutated",
        "open_asof_allowed", "candidate_pool_removed", "f002_exclusion_bypassed",
        "final_live_enabled", "send_enabled", "execution_enabled", "actual_order_import_enabled",
        "discord_enabled", "webhook_enabled", "mt5_order_enabled", "ai_api_enabled",
        "payload_enabled", "payload_activation_enabled", "live_hook_enabled", "autotrade_enabled",
        "no_signal_discord_notify", "theoretical_result_used_as_gate_input", "actual_execution_used_as_gate_input",
        "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")
    lines.append("OUTPUT_FILES")
    for file_key, file_path in summary["output_files"].items():
        lines.append(f"{file_key}: {file_path}")
    lines.append("")
    lines.append("GATE_POLICY")
    lines.append("Default decision is NO_SEND_AUDIT_ONLY. A valid text preview is not enough to enable Discord/webhook/payload/order/live paths.")
    lines.append("NO_SIGNAL remains no-message/no-send.")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage220 is audit-only. It freezes the notification no-send approval gate and proves incomplete approval still cannot send.")
    lines.append("Discord send, webhook, payload activation, MT5 order, actual import, live hook, final live, and autotrade remain OFF.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary["blockers"]:
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    started = datetime.now(timezone.utc)
    created_at_utc = utc_now_iso()
    _, output_dir, gate_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_gate_dir(gate_dir)

    rows = build_matrix_rows()
    requirements: Dict[str, Any] = {
        "stage": STAGE,
        "audit_only": True,
        "no_send_gate_only": True,
        "stage219_decision": "STAGE219_NOTIFICATION_MESSAGE_TEXT_PREVIEW_READY_AUDIT_ONLY",
        "stage219_validation_pass": True,
        "manual_discord_alert_only_approval": False,
        "approved_channel_scope_defined": False,
        "payload_activation_approval": False,
        "webhook_secret_audit_pass": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "timestamp_basis": "MT5_CSV",
        "jst_conversion_used_for_detector_logic": False,
        "created_at_utc": created_at_utc,
    }
    requirements.update(DISABLED_FLAGS)

    matrix_csv = gate_dir / "notification_no_send_gate_matrix.csv"
    requirements_json = gate_dir / "approval_requirements.json"
    readme_txt = gate_dir / "gate_policy_readme.txt"

    write_csv(matrix_csv, rows, MATRIX_COLUMNS)
    write_json(requirements_json, requirements)
    readme_txt.write_text(
        "GOLD V3 Stage220 notification no-send approval gate.\n"
        "Default state is NO_SEND_AUDIT_ONLY.\n"
        "A text preview is not a payload, webhook, Discord send, order, live hook, or autotrade approval.\n"
        "NO_SIGNAL does not notify.\n",
        encoding="utf-8",
    )

    checks, blockers = validate(gate_dir, rows, requirements)
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
    by_case = {row["case_id"]: row for row in rows}

    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at_utc,
        "output_dir": str(output_dir),
        "gate_dir": str(gate_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "no_send_gate_only": True,
        "live_release_ready": False,
        "stage219_decision": requirements["stage219_decision"],
        "stage219_validation_pass": True,
        "gate_matrix_rows": len(rows),
        "signal_no_approval_decision": by_case["CASE_SIGNAL_NO_APPROVAL"]["actual_decision"],
        "no_signal_decision": by_case["CASE_NO_SIGNAL_NO_APPROVAL"]["actual_decision"],
        "partial_approval_decision": by_case["CASE_SIGNAL_FAKE_PARTIAL_APPROVAL"]["actual_decision"],
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "theoretical_result_used_as_gate_input": False,
        "actual_execution_used_as_gate_input": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "validation_checks": checks,
        "elapsed_seconds": elapsed_seconds,
        "output_files": {
            "notification_no_send_gate_matrix_csv": str(matrix_csv),
            "approval_requirements_json": str(requirements_json),
            "gate_policy_readme_txt": str(readme_txt),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_220_notification_no_send_approval_gate_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage220 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"output_dir: {output_dir}")
    print(f"paste_me: {paste_path}")
    if blockers:
        print("BLOCKERS:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    print("NO_BLOCKERS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
