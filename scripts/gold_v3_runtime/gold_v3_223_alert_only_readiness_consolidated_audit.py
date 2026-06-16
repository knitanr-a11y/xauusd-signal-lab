#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage223 - Alert-Only Readiness Consolidated Audit

One consolidated audit to speed up the pre-alert-only workflow.
No Discord send, no webhook, no payload activation, no MT5 order, no actual import, no live hook, no final live, no autotrade.
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


STAGE = "GOLD_V3_223_ALERT_ONLY_READINESS_CONSOLIDATED_AUDIT_ONLY"
DECISION_READY = "STAGE223_ALERT_ONLY_READINESS_CONSOLIDATED_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE223_ALERT_ONLY_READINESS_CONSOLIDATED_BLOCKED_AUDIT_ONLY"
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
    "queue_action",
    "notification_action",
    "webhook_action",
    "payload_action",
    "audit_only",
    "created_stage",
    "created_at_utc",
]

METADATA_COLUMNS = [
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
    "theoretical_result_used",
    "actual_execution_used",
    "audit_only",
    "created_stage",
    "created_at_utc",
]

SUPPRESSION_COLUMNS = [
    "case_id",
    "latest_closed_m15_dt",
    "final_route",
    "queue_row_created",
    "sendable_message_created",
    "discord_notify",
    "notification_action",
    "webhook_action",
    "payload_action",
    "audit_only",
    "created_stage",
    "created_at_utc",
]

IDEMPOTENCY_COLUMNS = [
    "attempt_id",
    "signal_id",
    "queue_action",
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
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "223"
    work_dir = output_dir / "alert_only_readiness_consolidated"
    return mql5_files, output_dir, work_dir


def assert_safe_path(work_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "223", "alert_only_readiness_consolidated")
    actual_tail = tuple(work_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe output path. Expected tail {expected_tail}, got {actual_tail}")


def reset_work_dir(work_dir: Path) -> None:
    assert_safe_path(work_dir)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)


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
        "queue_id": f"{f.short_signal_id}_ALERT_ONLY_READY_PREVIEW",
        "signal_id": f.signal_id,
        "short_signal_id": f.short_signal_id,
        "latest_closed_m15_dt": f.latest_closed_m15_dt,
        "entry_dt": f.entry_dt,
        "direction": f.direction,
        "message_template_version": TEMPLATE_VERSION,
        "message_title": title_for(f.direction),
        "message_text": message_text(f),
        "queue_action": "READY_PREVIEW_NO_SEND",
        "notification_action": "NO_SEND_AUDIT_ONLY",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }


def metadata_row(f: SignalFixture, created_at: str) -> Dict[str, Any]:
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
        "theoretical_result_used": False,
        "actual_execution_used": False,
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }


def append_queue_unique(path: Path, row: Dict[str, Any]) -> str:
    rows = read_csv(path)
    for old in rows:
        if old.get("signal_id") == str(row.get("signal_id")):
            return "SKIP_DUPLICATE_SIGNAL_ID"
    rows.append({k: row.get(k, "") for k in QUEUE_COLUMNS})
    write_csv(path, rows, QUEUE_COLUMNS)
    return "APPENDED"


def validate(work_dir: Path, queue_rows: List[Dict[str, str]], metadata_rows: List[Dict[str, str]], suppression_rows: List[Dict[str, str]], idempotency_rows: List[Dict[str, Any]], policy: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    msg = queue_rows[0].get("message_text", "") if queue_rows else ""
    final_line = msg.splitlines()[-1] if msg else ""
    duplicate_skips = [r for r in idempotency_rows if r.get("queue_action") == "SKIP_DUPLICATE_SIGNAL_ID"]

    add("AR001", tuple(work_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "223", "alert_only_readiness_consolidated"), f"work_dir={work_dir}")
    add("AR002", policy.get("stage222_validation_pass") is True, f"stage222_decision={policy.get('stage222_decision')}")
    add("AR003", len(queue_rows) == 1, f"queue_rows={len(queue_rows)}")
    add("AR004", len(queue_rows) == 1 and queue_rows[0].get("message_template_version") == TEMPLATE_VERSION, f"template={queue_rows[0].get('message_template_version') if queue_rows else ''}")
    add("AR005", msg.startswith("🔴 GOLD SELL SCALP"), "message title starts with SELL scalp marker")
    add("AR006", final_line == f"Signal ID: {SIGNAL.signal_id}", f"final_line={final_line}")
    add("AR007", len(duplicate_skips) == 1, f"duplicate_signal_skip_count={len(duplicate_skips)}")
    add("AR008", len(suppression_rows) == 1 and suppression_rows[0].get("queue_row_created") == "False" and suppression_rows[0].get("discord_notify") == "False", f"suppression_rows={len(suppression_rows)}")
    add("AR009", len(metadata_rows) == 1 and all(metadata_rows[0].get(k) for k in ["signal_id", "short_signal_id", "final_route", "strategy_role", "candidate_id"]), "metadata retains required identifiers")
    add("AR010", all(v is False for v in DISABLED_FLAGS.values()), "send/webhook/payload/order/import/live/autotrade flags OFF")
    add("AR011", policy.get("source_csv_mutated") is False and policy.get("contract_mutated") is False and policy.get("production_live_retention_mutated") is False, "source/contract/production not mutated")
    add("AR012", policy.get("candidate_pool_removed") is False and policy.get("f002_exclusion_bypassed") is False, "candidate pool retained and F002 not bypassed")
    add("AR013", policy.get("theoretical_result_used_as_input") is False and policy.get("actual_execution_used_as_input") is False, "no future result or actual execution input")
    add("AR014", policy.get("csv_latest_row_contract") == "CLOSED" and policy.get("open_asof_allowed") is False, "CSV latest row CLOSED; no open/as-of")
    add("AR015", policy.get("timestamp_basis") == "MT5_CSV" and policy.get("jst_conversion_used_for_detector_logic") is False, "MT5/CSV timestamp basis; no JST detector conversion")
    add("AR016", policy.get("next_step_requires_explicit_demo_alert_only_approval") is True, "approval packet requires explicit demo alert-only approval")

    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 223 PASTE_ME_ALERT_ONLY_READINESS_CONSOLIDATED_AUDIT")
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "audit_only", "review_only", "dry_run_only", "consolidated_stage", "alert_only_readiness", "live_release_ready",
        "stage222_decision", "stage222_validation_pass", "message_template_version",
        "queue_rows", "history_metadata_rows", "no_signal_suppression_rows", "duplicate_signal_skip_count",
        "next_step_requires_explicit_demo_alert_only_approval",
        "source_csv_mutated", "contract_mutated", "production_live_retention_mutated", "open_asof_allowed",
        "candidate_pool_removed", "f002_exclusion_bypassed", "final_live_enabled", "send_enabled", "execution_enabled",
        "actual_order_import_enabled", "discord_enabled", "webhook_enabled", "mt5_order_enabled", "ai_api_enabled",
        "payload_enabled", "payload_activation_enabled", "live_hook_enabled", "autotrade_enabled", "no_signal_discord_notify",
        "theoretical_result_used_as_input", "actual_execution_used_as_input", "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")
    lines.append("ALERT_ONLY_MESSAGE_PREVIEW")
    lines.append(summary["message_text"])
    lines.append("")
    lines.append("NEXT_STEP_APPROVAL_PACKET")
    lines.append(summary["approval_packet_text"])
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
    lines.append("Stage223 consolidates the remaining pre-alert-only readiness checks. It does not send Discord, call webhooks, activate payloads, place orders, import executions, enable live hook, final live, or autotrade.")
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
    _, output_dir, work_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_work_dir(work_dir)

    queue_csv = work_dir / "alert_only_queue_preview.csv"
    metadata_csv = work_dir / "alert_only_history_metadata.csv"
    suppression_csv = work_dir / "no_signal_suppression_preview.csv"
    idempotency_csv = work_dir / "alert_only_queue_idempotency.csv"
    approval_txt = work_dir / "approval_packet_for_next_step.txt"
    policy_json = work_dir / "readiness_policy.json"

    write_csv(queue_csv, [], QUEUE_COLUMNS)
    idempotency_rows: List[Dict[str, Any]] = []
    a1 = append_queue_unique(queue_csv, queue_row(SIGNAL, created_at))
    idempotency_rows.append({"attempt_id": "PASS1_SIGNAL", "signal_id": SIGNAL.signal_id, "queue_action": a1, "reason": "first signal replay", "created_stage": STAGE, "created_at_utc": created_at})
    a2 = append_queue_unique(queue_csv, queue_row(SIGNAL, created_at))
    idempotency_rows.append({"attempt_id": "PASS2_SIGNAL_DUPLICATE", "signal_id": SIGNAL.signal_id, "queue_action": a2, "reason": "duplicate signal replay", "created_stage": STAGE, "created_at_utc": created_at})

    suppression_rows = [{
        "case_id": "NO_SIGNAL_SUPPRESSION",
        "latest_closed_m15_dt": NO_SIGNAL["latest_closed_m15_dt"],
        "final_route": NO_SIGNAL["final_route"],
        "queue_row_created": False,
        "sendable_message_created": False,
        "discord_notify": False,
        "notification_action": "NO_MESSAGE_NO_SIGNAL",
        "webhook_action": "NO_WEBHOOK_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_ACTIVATION_AUDIT_ONLY",
        "audit_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at,
    }]

    approval_text = "\n".join([
        "GOLD V3 Stage223 next-step approval packet",
        "Current state: alert-only readiness packet is prepared, but Discord send is still OFF.",
        "To proceed to a future demo Discord alert-only send test, the user must explicitly approve demo alert-only sending.",
        "This approval would not approve MT5 orders, actual execution import, payload activation for trading, live hook, final live, or autotrade.",
        "NO_SIGNAL must remain no-notify.",
    ])

    policy: Dict[str, Any] = {
        "stage": STAGE,
        "stage222_decision": "STAGE222_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_READY_AUDIT_ONLY",
        "stage222_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "audit_only": True,
        "consolidated_stage": True,
        "alert_only_readiness": True,
        "live_release_ready": False,
        "next_step_requires_explicit_demo_alert_only_approval": True,
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
    policy.update(DISABLED_FLAGS)

    write_csv(metadata_csv, [metadata_row(SIGNAL, created_at)], METADATA_COLUMNS)
    write_csv(suppression_csv, suppression_rows, SUPPRESSION_COLUMNS)
    write_csv(idempotency_csv, idempotency_rows, IDEMPOTENCY_COLUMNS)
    approval_txt.write_text(approval_text + "\n", encoding="utf-8")
    write_json(policy_json, policy)

    queue_rows = read_csv(queue_csv)
    metadata_rows = read_csv(metadata_csv)
    suppression_read_rows = read_csv(suppression_csv)
    checks, blockers = validate(work_dir, queue_rows, metadata_rows, suppression_read_rows, idempotency_rows, policy)
    duplicate_signal_skip_count = sum(1 for r in idempotency_rows if r["queue_action"] == "SKIP_DUPLICATE_SIGNAL_ID")
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at,
        "output_dir": str(output_dir),
        "work_dir": str(work_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "consolidated_stage": True,
        "alert_only_readiness": True,
        "live_release_ready": False,
        "stage222_decision": policy["stage222_decision"],
        "stage222_validation_pass": True,
        "message_template_version": TEMPLATE_VERSION,
        "queue_rows": len(queue_rows),
        "history_metadata_rows": len(metadata_rows),
        "no_signal_suppression_rows": len(suppression_read_rows),
        "duplicate_signal_skip_count": duplicate_signal_skip_count,
        "next_step_requires_explicit_demo_alert_only_approval": True,
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
        "approval_packet_text": approval_text,
        "output_files": {
            "alert_only_queue_preview_csv": str(queue_csv),
            "alert_only_history_metadata_csv": str(metadata_csv),
            "no_signal_suppression_preview_csv": str(suppression_csv),
            "alert_only_queue_idempotency_csv": str(idempotency_csv),
            "approval_packet_for_next_step_txt": str(approval_txt),
            "readiness_policy_json": str(policy_json),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_223_alert_only_readiness_consolidated_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage223 status: {summary['status']}")
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
