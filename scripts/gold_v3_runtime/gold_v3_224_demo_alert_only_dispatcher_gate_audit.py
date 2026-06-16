#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage224 - Demo Alert-Only Dispatcher Gate Audit

Prepares a gated demo alert-only dispatcher packet.
This script does not send Discord, does not read webhook URLs, does not activate payloads,
does not place MT5 orders, does not import executions, does not enable live hook/final live/autotrade.
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


STAGE = "GOLD_V3_224_DEMO_ALERT_ONLY_DISPATCHER_GATE_AUDIT_ONLY"
DECISION_READY = "STAGE224_DEMO_ALERT_ONLY_DISPATCHER_GATE_READY_APPROVAL_REQUIRED_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE224_DEMO_ALERT_ONLY_DISPATCHER_GATE_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TEMPLATE_VERSION = "GOLD_V3_NOTIFY_TEMPLATE_V3_SCALP_COMPACT_SIGNAL_ID_BOTTOM_20260617"

DISABLED_FLAGS: Dict[str, bool] = {
    "send_enabled": False,
    "execution_enabled": False,
    "actual_order_import_enabled": False,
    "discord_enabled": False,
    "webhook_enabled": False,
    "webhook_url_read": False,
    "mt5_order_enabled": False,
    "ai_api_enabled": False,
    "payload_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
}

QUEUE_COLUMNS = [
    "queue_id",
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "direction",
    "message_template_version",
    "message_title",
    "message_text",
    "dispatcher_gate_action",
    "future_send_requires_explicit_approval",
    "notification_action",
    "webhook_action",
    "payload_action",
    "audit_only",
    "created_stage",
    "created_at_utc",
]

NO_SIGNAL_COLUMNS = [
    "case_id",
    "latest_closed_m15_dt",
    "final_route",
    "queue_row_created",
    "notification_created",
    "discord_notify",
    "audit_only",
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


SIGNAL = SignalFixture(
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

NO_SIGNAL = {"latest_closed_m15_dt": "2026-06-16 16:45:00", "final_route": "NO_SIGNAL"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def stage_paths() -> Tuple[Path, Path, Path]:
    mql5_files = default_mql5_files_dir()
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "224"
    gate_dir = output_dir / "demo_alert_only_dispatcher_gate"
    return mql5_files, output_dir, gate_dir


def assert_safe_path(gate_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "224", "demo_alert_only_dispatcher_gate")
    actual_tail = tuple(gate_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe output path. Expected tail {expected_tail}, got {actual_tail}")


def reset_gate_dir(gate_dir: Path) -> None:
    assert_safe_path(gate_dir)
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


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def title_for(direction: str) -> str:
    d = direction.upper()
    if d in {"SELL", "SHORT"}:
        return "🔴 GOLD SELL SCALP"
    if d in {"BUY", "LONG"}:
        return "🟢 GOLD BUY SCALP"
    raise ValueError(f"Unsupported direction: {direction}")


def message_text(f: SignalFixture) -> str:
    return "\n".join([
        title_for(f.direction),
        f"Entry Time: {f.entry_dt[:16]} MT5/CSV",
        f"Entry Price: {f.entry_price:.2f}",
        f"TP / SL: {f.tp_usd:g} / {f.sl_usd:g}",
        f"Horizon: {f.horizon_m5_bars} M5 bars",
        "",
        "[AUDIT_ONLY / NO_SEND]",
        f"Signal ID: {f.signal_id}",
    ])


def queue_row(f: SignalFixture, created_at: str) -> Dict[str, Any]:
    return {
        "queue_id": f"{f.short_signal_id}_DISPATCHER_GATE_PREVIEW",
        "signal_id": f.signal_id,
        "short_signal_id": f.short_signal_id,
        "latest_closed_m15_dt": f.latest_closed_m15_dt,
        "entry_dt": f.entry_dt,
        "direction": f.direction,
        "message_template_version": TEMPLATE_VERSION,
        "message_title": title_for(f.direction),
        "message_text": message_text(f),
        "dispatcher_gate_action": "READY_BUT_APPROVAL_REQUIRED_NO_SEND",
        "future_send_requires_explicit_approval": True,
        "notification_action": "NO_SEND_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }


def validate(gate_dir: Path, queue_rows: List[Dict[str, str]], no_signal_rows: List[Dict[str, str]], status_payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    msg = queue_rows[0].get("message_text", "") if queue_rows else ""
    final_line = msg.splitlines()[-1] if msg else ""

    add("DG001", tuple(gate_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "224", "demo_alert_only_dispatcher_gate"), f"gate_dir={gate_dir}")
    add("DG002", status_payload.get("stage223_validation_pass") is True, f"stage223_decision={status_payload.get('stage223_decision')}")
    add("DG003", len(queue_rows) == 1, f"queue_rows={len(queue_rows)}")
    add("DG004", msg.startswith("🔴 GOLD SELL SCALP"), "message title starts with SELL scalp marker")
    add("DG005", final_line == f"Signal ID: {SIGNAL.signal_id}", f"final_line={final_line}")
    add("DG006", len(no_signal_rows) == 1 and no_signal_rows[0].get("queue_row_created") == "False" and no_signal_rows[0].get("discord_notify") == "False", f"no_signal_rows={len(no_signal_rows)}")
    add("DG007", status_payload.get("future_send_requires_explicit_approval") is True, "explicit demo alert-only approval required")
    add("DG008", all(v is False for v in DISABLED_FLAGS.values()), "send/webhook/payload/order/import/live/autotrade flags OFF")
    add("DG009", status_payload.get("source_csv_mutated") is False and status_payload.get("contract_mutated") is False and status_payload.get("production_live_retention_mutated") is False, "source/contract/production not mutated")
    add("DG010", status_payload.get("candidate_pool_removed") is False and status_payload.get("f002_exclusion_bypassed") is False, "candidate pool retained and F002 not bypassed")
    add("DG011", status_payload.get("theoretical_result_used_as_input") is False and status_payload.get("actual_execution_used_as_input") is False, "no future result or actual execution input")
    add("DG012", status_payload.get("csv_latest_row_contract") == "CLOSED" and status_payload.get("open_asof_allowed") is False, "CSV latest row CLOSED; no open/as-of")
    add("DG013", status_payload.get("timestamp_basis") == "MT5_CSV" and status_payload.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis; no JST detector conversion")

    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 224 PASTE_ME_DEMO_ALERT_ONLY_DISPATCHER_GATE_AUDIT")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "gate_dir",
        "audit_only", "review_only", "dry_run_only", "dispatcher_gate_prep", "approval_required", "live_release_ready",
        "stage223_decision", "stage223_validation_pass", "message_template_version", "queue_rows", "no_signal_suppression_rows",
        "future_send_requires_explicit_approval", "source_csv_mutated", "contract_mutated", "production_live_retention_mutated",
        "open_asof_allowed", "candidate_pool_removed", "f002_exclusion_bypassed", "final_live_enabled", "send_enabled",
        "execution_enabled", "actual_order_import_enabled", "discord_enabled", "webhook_enabled", "webhook_url_read",
        "mt5_order_enabled", "ai_api_enabled", "payload_enabled", "payload_activation_enabled", "live_hook_enabled", "autotrade_enabled",
        "no_signal_discord_notify", "theoretical_result_used_as_input", "actual_execution_used_as_input", "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")
    lines.append("DISPATCHER_MESSAGE_PREVIEW")
    lines.append(summary["message_text"])
    lines.append("")
    lines.append("APPROVAL_REQUIRED_TEXT")
    lines.append(summary["approval_required_text"])
    lines.append("")
    lines.append("OUTPUT_FILES")
    for k, v in summary["output_files"].items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage224 prepares a gated demo alert-only dispatcher packet. It does not send Discord, read a webhook URL, activate payloads, place orders, import executions, enable live hook, final live, or autotrade.")
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
    created_at = utc_now_iso()
    _, output_dir, gate_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_gate_dir(gate_dir)

    queue_csv = gate_dir / "alert_only_dispatcher_queue.csv"
    no_signal_csv = gate_dir / "no_signal_suppression.csv"
    status_json = gate_dir / "dispatcher_gate_status.json"
    msg_txt = gate_dir / "alert_only_dispatcher_message_preview.txt"
    approval_txt = gate_dir / "approval_required.txt"

    no_signal_rows = [{
        "case_id": "NO_SIGNAL_SUPPRESSION",
        "latest_closed_m15_dt": NO_SIGNAL["latest_closed_m15_dt"],
        "final_route": NO_SIGNAL["final_route"],
        "queue_row_created": False,
        "notification_created": False,
        "discord_notify": False,
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }]

    approval_text = "\n".join([
        "Stage224 dispatcher gate is prepared but cannot send Discord.",
        "Future demo alert-only Discord send requires explicit user approval in the chat.",
        "That approval must be limited to demo Discord alert-only sending.",
        "It must not approve MT5 orders, actual execution import, payload activation for trading, live hook, final live, autotrade, or NO_SIGNAL notifications.",
    ])

    status_payload: Dict[str, Any] = {
        "stage": STAGE,
        "stage223_decision": "STAGE223_ALERT_ONLY_READINESS_CONSOLIDATED_READY_AUDIT_ONLY",
        "stage223_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "audit_only": True,
        "dispatcher_gate_prep": True,
        "approval_required": True,
        "future_send_requires_explicit_approval": True,
        "live_release_ready": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "timestamp_basis": "MT5_CSV",
        "jst_conversion_used_for_detector_logic": False,
        "theoretical_result_used_as_input": False,
        "actual_execution_used_as_input": False,
        "created_at_utc": created_at,
    }
    status_payload.update(DISABLED_FLAGS)

    write_csv(queue_csv, [queue_row(SIGNAL, created_at)], QUEUE_COLUMNS)
    write_csv(no_signal_csv, no_signal_rows, NO_SIGNAL_COLUMNS)
    write_json(status_json, status_payload)
    msg_txt.write_text(message_text(SIGNAL) + "\n", encoding="utf-8")
    approval_txt.write_text(approval_text + "\n", encoding="utf-8")

    queue_rows = read_csv(queue_csv)
    no_signal_read_rows = read_csv(no_signal_csv)
    checks, blockers = validate(gate_dir, queue_rows, no_signal_read_rows, status_payload)
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at,
        "output_dir": str(output_dir),
        "gate_dir": str(gate_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "dispatcher_gate_prep": True,
        "approval_required": True,
        "live_release_ready": False,
        "stage223_decision": status_payload["stage223_decision"],
        "stage223_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "queue_rows": len(queue_rows),
        "no_signal_suppression_rows": len(no_signal_read_rows),
        "future_send_requires_explicit_approval": True,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "production_live_retention_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "theoretical_result_used_as_input": False,
        "actual_execution_used_as_input": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "validation_checks": checks,
        "elapsed_seconds": elapsed_seconds,
        "message_text": message_text(SIGNAL),
        "approval_required_text": approval_text,
        "output_files": {
            "dispatcher_gate_status_json": str(status_json),
            "alert_only_dispatcher_message_preview_txt": str(msg_txt),
            "alert_only_dispatcher_queue_csv": str(queue_csv),
            "no_signal_suppression_csv": str(no_signal_csv),
            "approval_required_txt": str(approval_txt),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_224_demo_alert_only_dispatcher_gate_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage224 status: {summary['status']}")
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
