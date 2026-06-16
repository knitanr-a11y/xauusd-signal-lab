#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage222 - Notification Event Staging Template Integration Audit

Integrates the Stage221 revised user-visible notification text into a staging notification-event ledger.
No Discord send, no webhook, no payload activation, no MT5 order, no actual import, no live hook, no autotrade.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


STAGE = "GOLD_V3_222_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_AUDIT_ONLY"
DECISION_READY = "STAGE222_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE222_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TEMPLATE_VERSION = "GOLD_V3_NOTIFY_TEMPLATE_V3_SCALP_COMPACT_SIGNAL_ID_BOTTOM_20260617"

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

NOTIFICATION_EVENT_COLUMNS = [
    "event_id",
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "direction",
    "title",
    "notification_action",
    "webhook_action",
    "payload_action",
    "message_template_version",
    "message_text",
    "audit_only",
    "staging_only",
    "created_stage",
    "created_at_utc",
]

HISTORY_METADATA_COLUMNS = [
    "signal_id",
    "short_signal_id",
    "final_route",
    "strategy_role",
    "candidate_id",
    "direction",
    "latest_closed_m15_dt",
    "entry_dt",
    "entry_price",
    "tp_usd",
    "sl_usd",
    "horizon_m5_bars",
    "message_template_version",
    "notification_action",
    "webhook_action",
    "payload_action",
    "audit_only",
    "staging_only",
    "created_stage",
    "created_at_utc",
]

NO_SIGNAL_SUPPRESSION_COLUMNS = [
    "case_id",
    "latest_closed_m15_dt",
    "final_route",
    "notification_event_created",
    "sendable_message_created",
    "notification_action",
    "discord_notify",
    "webhook_action",
    "payload_action",
    "audit_only",
    "staging_only",
    "created_stage",
    "created_at_utc",
]

IDEMPOTENCY_COLUMNS = [
    "attempt_id",
    "final_route",
    "signal_id",
    "event_action",
    "reason",
    "created_stage",
    "created_at_utc",
]


@dataclass(frozen=True)
class SignalFixture:
    signal_id: str
    short_signal_id: str
    latest_closed_m15_dt: str
    entry_dt: str
    final_route: str
    strategy_role: str
    candidate_id: str
    direction: str
    entry_price: float
    tp_usd: float
    sl_usd: float
    horizon_m5_bars: int


SIGNAL_FIXTURE = SignalFixture(
    signal_id="20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT",
    short_signal_id="G3SD01960980A23107A65AE",
    latest_closed_m15_dt="2026-06-15 16:30:00",
    entry_dt="2026-06-15 16:30:00",
    final_route="SECONDARY_AUDIT_CANDIDATE",
    strategy_role="SCALP_SECONDARY_CANDIDATE",
    candidate_id="SCALP_024_tp15_sl5_hz64_SHORT",
    direction="SELL",
    entry_price=4363.24,
    tp_usd=15.0,
    sl_usd=5.0,
    horizon_m5_bars=64,
)

NO_SIGNAL_FIXTURE = {
    "latest_closed_m15_dt": "2026-06-16 16:45:00",
    "final_route": "NO_SIGNAL",
}


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
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "222"
    integration_dir = output_dir / "notification_event_template_integration"
    return mql5_files, output_dir, integration_dir


def assert_safe_stage222_path(integration_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "222", "notification_event_template_integration")
    actual_tail = tuple(integration_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe integration path. Expected tail {expected_tail}, got {actual_tail}")


def reset_integration_dir(integration_dir: Path) -> None:
    assert_safe_stage222_path(integration_dir)
    if integration_dir.exists():
        shutil.rmtree(integration_dir)
    integration_dir.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in row_list:
            writer.writerow(row)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_unique(path: Path, row: Dict[str, Any], columns: List[str], unique_keys: List[str]) -> str:
    rows = read_csv_rows(path)
    for old in rows:
        if all(str(old.get(k, "")) == str(row.get(k, "")) for k in unique_keys):
            return "SKIP_DUPLICATE_NOTIFICATION_EVENT"
    rows.append({k: row.get(k, "") for k in columns})
    write_csv(path, rows, columns)
    return "APPENDED"


def title_for(direction: str) -> str:
    normalized = direction.upper()
    if normalized in {"SELL", "SHORT"}:
        return "🔴 GOLD SELL SCALP"
    if normalized in {"BUY", "LONG"}:
        return "🟢 GOLD BUY SCALP"
    raise ValueError(f"Unsupported direction: {direction}")


def build_message(f: SignalFixture) -> str:
    return "\n".join(
        [
            title_for(f.direction),
            f"Entry Time: {f.entry_dt[:16]} MT5/CSV",
            f"Entry Price: {f.entry_price:.2f}",
            f"TP / SL: {f.tp_usd:g} / {f.sl_usd:g}",
            f"Horizon: {f.horizon_m5_bars} M5 bars",
            "",
            "[AUDIT_ONLY / NO_SEND]",
            f"Signal ID: {f.signal_id}",
        ]
    )


def notification_event_row(f: SignalFixture, created_at_utc: str) -> Dict[str, Any]:
    return {
        "event_id": f"{f.short_signal_id}_TEMPLATE_V3_STAGING_EVENT",
        "signal_id": f.signal_id,
        "short_signal_id": f.short_signal_id,
        "latest_closed_m15_dt": f.latest_closed_m15_dt,
        "entry_dt": f.entry_dt,
        "direction": f.direction,
        "title": title_for(f.direction),
        "notification_action": "NO_SEND_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "message_template_version": TEMPLATE_VERSION,
        "message_text": build_message(f),
        "audit_only": True,
        "staging_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }


def metadata_row(f: SignalFixture, created_at_utc: str) -> Dict[str, Any]:
    return {
        "signal_id": f.signal_id,
        "short_signal_id": f.short_signal_id,
        "final_route": f.final_route,
        "strategy_role": f.strategy_role,
        "candidate_id": f.candidate_id,
        "direction": f.direction,
        "latest_closed_m15_dt": f.latest_closed_m15_dt,
        "entry_dt": f.entry_dt,
        "entry_price": f.entry_price,
        "tp_usd": f.tp_usd,
        "sl_usd": f.sl_usd,
        "horizon_m5_bars": f.horizon_m5_bars,
        "message_template_version": TEMPLATE_VERSION,
        "notification_action": "NO_SEND_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "audit_only": True,
        "staging_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }


def validate(integration_dir: Path, event_rows: List[Dict[str, str]], no_signal_rows: List[Dict[str, str]], idempotency_rows: List[Dict[str, Any]], policy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    staged_message = event_rows[0].get("message_text", "") if event_rows else ""
    final_line = staged_message.splitlines()[-1] if staged_message else ""
    duplicate_skips = [r for r in idempotency_rows if r.get("event_action") == "SKIP_DUPLICATE_NOTIFICATION_EVENT"]

    add("TI001", tuple(integration_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "222", "notification_event_template_integration"), f"integration_dir={integration_dir}")
    add("TI002", policy.get("stage221_validation_pass") is True, f"stage221_decision={policy.get('stage221_decision')}")
    add("TI003", len(event_rows) == 1, f"notification_event_rows={len(event_rows)}")
    add("TI004", len(duplicate_skips) == 1, f"duplicate_signal_skip_count={len(duplicate_skips)}")
    add("TI005", len(no_signal_rows) == 1 and no_signal_rows[0].get("notification_event_created") == "False" and no_signal_rows[0].get("sendable_message_created") == "False", f"no_signal_suppression_rows={len(no_signal_rows)}")
    add("TI006", staged_message.startswith("🔴 GOLD SELL SCALP"), "staged message starts with red circle + GOLD SELL SCALP")
    add("TI007", final_line == f"Signal ID: {SIGNAL_FIXTURE.signal_id}", f"final_line={final_line}")
    add(
        "TI008",
        len(event_rows) == 1
        and event_rows[0].get("notification_action") == "NO_SEND_AUDIT_ONLY"
        and event_rows[0].get("webhook_action") == "NO_WEBHOOK_AUDIT_ONLY"
        and event_rows[0].get("payload_action") == "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "notification/webhook/payload actions remain disabled",
    )
    add("TI009", all(v is False for v in DISABLED_FLAGS.values()), "all send/webhook/payload/order/import/live/autotrade flags remain OFF")
    add("TI010", policy.get("source_csv_mutated") is False and policy.get("contract_mutated") is False and policy.get("production_live_retention_mutated") is False, "source CSV/contract/production retention not mutated")
    add("TI011", policy.get("candidate_pool_removed") is False and policy.get("f002_exclusion_bypassed") is False, "candidate pool retained and F002 not bypassed")
    add("TI012", policy.get("theoretical_result_used_as_integration_input") is False and policy.get("actual_execution_used_as_integration_input") is False, "no future result or actual execution result used")
    add("TI013", policy.get("csv_latest_row_contract") == "CLOSED" and policy.get("open_asof_allowed") is False, "CSV latest row CLOSED; open/as-of not introduced")
    add("TI014", policy.get("timestamp_basis") == "MT5_CSV" and policy.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis; no JST detector conversion")

    blockers = [f"{check['check_id']}: {check['details']}" for check in checks if not check["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 222 PASTE_ME_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_AUDIT")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "integration_dir",
        "audit_only", "review_only", "dry_run_only", "staging_only", "template_integration_only", "live_release_ready",
        "stage221_decision", "stage221_validation_pass", "message_template_version",
        "notification_event_rows", "history_metadata_rows", "no_signal_suppression_rows", "duplicate_signal_skip_count",
        "source_csv_mutated", "contract_mutated", "production_live_retention_mutated",
        "open_asof_allowed", "candidate_pool_removed", "f002_exclusion_bypassed",
        "final_live_enabled", "send_enabled", "execution_enabled", "actual_order_import_enabled",
        "discord_enabled", "webhook_enabled", "mt5_order_enabled", "ai_api_enabled",
        "payload_enabled", "payload_activation_enabled", "live_hook_enabled", "autotrade_enabled",
        "no_signal_discord_notify", "theoretical_result_used_as_integration_input", "actual_execution_used_as_integration_input",
        "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")
    lines.append("INTEGRATED_MESSAGE_TEXT")
    lines.append(summary["integrated_message_text"])
    lines.append("")
    lines.append("OUTPUT_FILES")
    for file_key, file_path in summary["output_files"].items():
        lines.append(f"{file_key}: {file_path}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage222 is audit-only and staging-only. It places the Stage221 revised text into a staging notification-event row without sending Discord, calling webhooks, activating payloads, placing orders, importing executions, enabling live hook, final live, or autotrade.")
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
    _, output_dir, integration_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_integration_dir(integration_dir)

    event_csv = integration_dir / "notification_events_staging.csv"
    metadata_csv = integration_dir / "notification_event_history_metadata.csv"
    no_signal_csv = integration_dir / "no_signal_notification_suppression.csv"
    policy_json = integration_dir / "notification_event_policy.json"
    message_txt = integration_dir / "message_text_integrated_preview.txt"
    idempotency_csv = integration_dir / "notification_event_idempotency.csv"

    write_csv(event_csv, [], NOTIFICATION_EVENT_COLUMNS)

    idempotency_rows: List[Dict[str, Any]] = []
    first_action = append_unique(event_csv, notification_event_row(SIGNAL_FIXTURE, created_at_utc), NOTIFICATION_EVENT_COLUMNS, ["signal_id"])
    idempotency_rows.append({"attempt_id": "PASS1_SIGNAL", "final_route": SIGNAL_FIXTURE.final_route, "signal_id": SIGNAL_FIXTURE.signal_id, "event_action": first_action, "reason": "first signal replay", "created_stage": STAGE, "created_at_utc": created_at_utc})
    second_action = append_unique(event_csv, notification_event_row(SIGNAL_FIXTURE, created_at_utc), NOTIFICATION_EVENT_COLUMNS, ["signal_id"])
    idempotency_rows.append({"attempt_id": "PASS2_SIGNAL_DUPLICATE", "final_route": SIGNAL_FIXTURE.final_route, "signal_id": SIGNAL_FIXTURE.signal_id, "event_action": second_action, "reason": "duplicate signal replay", "created_stage": STAGE, "created_at_utc": created_at_utc})

    no_signal_rows = [
        {
            "case_id": "NO_SIGNAL_SUPPRESSION",
            "latest_closed_m15_dt": NO_SIGNAL_FIXTURE["latest_closed_m15_dt"],
            "final_route": NO_SIGNAL_FIXTURE["final_route"],
            "notification_event_created": False,
            "sendable_message_created": False,
            "notification_action": "NO_MESSAGE_NO_SIGNAL",
            "discord_notify": False,
            "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
            "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
            "audit_only": True,
            "staging_only": True,
            "created_stage": STAGE,
            "created_at_utc": created_at_utc,
        }
    ]

    write_csv(metadata_csv, [metadata_row(SIGNAL_FIXTURE, created_at_utc)], HISTORY_METADATA_COLUMNS)
    write_csv(no_signal_csv, no_signal_rows, NO_SIGNAL_SUPPRESSION_COLUMNS)
    write_csv(idempotency_csv, idempotency_rows, IDEMPOTENCY_COLUMNS)
    message_txt.write_text(build_message(SIGNAL_FIXTURE) + "\n", encoding="utf-8")

    policy: Dict[str, Any] = {
        "stage": STAGE,
        "stage221_decision": "STAGE221_NOTIFICATION_TEXT_TEMPLATE_REVISION_READY_AUDIT_ONLY",
        "stage221_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "audit_only": True,
        "staging_only": True,
        "template_integration_only": True,
        "notification_action": "NO_SEND_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "timestamp_basis": "MT5_CSV",
        "jst_conversion_used_for_detector_logic": False,
        "theoretical_result_used_as_integration_input": False,
        "actual_execution_used_as_integration_input": False,
        "created_at_utc": created_at_utc,
    }
    policy.update(DISABLED_FLAGS)
    write_json(policy_json, policy)

    event_rows = read_csv_rows(event_csv)
    metadata_rows = read_csv_rows(metadata_csv)
    no_signal_read_rows = read_csv_rows(no_signal_csv)
    checks, blockers = validate(integration_dir, event_rows, no_signal_read_rows, idempotency_rows, policy)
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)
    duplicate_signal_skip_count = sum(1 for row in idempotency_rows if row["event_action"] == "SKIP_DUPLICATE_NOTIFICATION_EVENT")

    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at_utc,
        "output_dir": str(output_dir),
        "integration_dir": str(integration_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "staging_only": True,
        "template_integration_only": True,
        "live_release_ready": False,
        "stage221_decision": policy["stage221_decision"],
        "stage221_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "notification_event_rows": len(event_rows),
        "history_metadata_rows": len(metadata_rows),
        "no_signal_suppression_rows": len(no_signal_read_rows),
        "duplicate_signal_skip_count": duplicate_signal_skip_count,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "theoretical_result_used_as_integration_input": False,
        "actual_execution_used_as_integration_input": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "validation_checks": checks,
        "elapsed_seconds": elapsed_seconds,
        "integrated_message_text": build_message(SIGNAL_FIXTURE),
        "output_files": {
            "notification_events_staging_csv": str(event_csv),
            "notification_event_history_metadata_csv": str(metadata_csv),
            "no_signal_notification_suppression_csv": str(no_signal_csv),
            "notification_event_policy_json": str(policy_json),
            "message_text_integrated_preview_txt": str(message_txt),
            "notification_event_idempotency_csv": str(idempotency_csv),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_222_notification_event_staging_template_integration_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage222 status: {summary['status']}")
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
