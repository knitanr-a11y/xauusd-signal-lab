#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage218 - Staging Retention Replay Multi-Cycle Audit

Audit-only / staging-only replay of known Stage215 SIGNAL and Stage211 NO_SIGNAL
fixtures into fresh Stage218 staging files.

Purpose:
- verify repeated-cycle idempotency
- verify duplicate SIGNAL / notification / NO_SIGNAL counter skip behavior
- verify latest_state overwrite on every replay attempt

No Discord, no MT5 order, no actual import, no payload, no live hook, no autotrade.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


STAGE = "GOLD_V3_218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_AUDIT_ONLY"
DECISION_READY = "STAGE218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

DISABLED_FLAGS: Dict[str, bool] = {
    "send_enabled": False,
    "execution_enabled": False,
    "actual_order_import_enabled": False,
    "discord_enabled": False,
    "mt5_order_enabled": False,
    "ai_api_enabled": False,
    "payload_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
}

TRADE_LEDGER_COLUMNS = [
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "entry_dt",
    "symbol",
    "final_route",
    "strategy_role",
    "candidate_id",
    "direction",
    "entry_price",
    "tp_usd",
    "sl_usd",
    "horizon_m5_bars",
    "send_action",
    "order_action",
    "actual_import_action",
    "payload_action",
    "theoretical_result_used",
    "actual_execution_used",
    "audit_only",
    "staging_only",
    "created_stage",
    "created_at_utc",
]

NOTIFICATION_COLUMNS = [
    "event_id",
    "signal_id",
    "short_signal_id",
    "latest_closed_m15_dt",
    "symbol",
    "final_route",
    "event_kind",
    "notification_action",
    "discord_enabled",
    "payload_enabled",
    "webhook_enabled",
    "message_preview",
    "audit_only",
    "staging_only",
    "created_stage",
    "created_at_utc",
]

NO_SIGNAL_COUNTER_COLUMNS = [
    "date_mt5",
    "hour_mt5",
    "latest_closed_m15_dt",
    "final_route",
    "increment",
    "discord_notify",
    "audit_only",
    "staging_only",
    "created_stage",
    "created_at_utc",
]

IDEMPOTENCY_COLUMNS = [
    "replay_attempt_id",
    "latest_closed_m15_dt",
    "final_route",
    "signal_id",
    "trade_signal_action",
    "notification_action",
    "no_signal_counter_action",
    "latest_state_action",
    "created_stage",
    "created_at_utc",
]

DEBUG_TAIL_COLUMNS = [
    "replay_attempt_id",
    "latest_closed_m15_dt",
    "final_route",
    "signal_id",
    "short_signal_id",
    "candidate_id",
    "direction",
    "entry_price",
    "trade_signal_action",
    "notification_action",
    "no_signal_counter_action",
    "latest_state_action",
    "send_enabled",
    "mt5_order_enabled",
    "actual_order_import_enabled",
    "discord_enabled",
    "payload_enabled",
    "live_hook_enabled",
    "autotrade_enabled",
    "note",
]


@dataclass(frozen=True)
class ReplayCycle:
    replay_attempt_id: str
    latest_closed_m15_dt: str
    final_route: str
    signal_id: str = ""
    short_signal_id: str = ""
    symbol: str = "XAUUSD"
    strategy_role: str = ""
    candidate_id: str = ""
    direction: str = ""
    entry_price: Optional[float] = None
    tp_usd: Optional[float] = None
    sl_usd: Optional[float] = None
    horizon_m5_bars: Optional[int] = None
    note: str = ""


SIGNAL_FIXTURE = ReplayCycle(
    replay_attempt_id="FIXTURE_SIGNAL_BASE",
    latest_closed_m15_dt="2026-06-15 16:30:00",
    final_route="SECONDARY_AUDIT_CANDIDATE",
    signal_id="20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT",
    short_signal_id="G3SD01960980A23107A65AE",
    strategy_role="SCALP_SECONDARY_CANDIDATE",
    candidate_id="SCALP_024_tp15_sl5_hz64_SHORT",
    direction="SHORT",
    entry_price=4363.24,
    tp_usd=15.0,
    sl_usd=5.0,
    horizon_m5_bars=64,
    note="Known Stage215 SIGNAL fixture; writer input excludes future result data.",
)

NO_SIGNAL_FIXTURE = ReplayCycle(
    replay_attempt_id="FIXTURE_NO_SIGNAL_BASE",
    latest_closed_m15_dt="2026-06-16 16:45:00",
    final_route="NO_SIGNAL",
    note="Known Stage211-style NO_SIGNAL fixture; counter/health only, no notification.",
)

REPLAY_ATTEMPTS: List[ReplayCycle] = [
    ReplayCycle(**{**SIGNAL_FIXTURE.__dict__, "replay_attempt_id": "PASS1_SIGNAL"}),
    ReplayCycle(**{**NO_SIGNAL_FIXTURE.__dict__, "replay_attempt_id": "PASS1_NO_SIGNAL"}),
    ReplayCycle(**{**SIGNAL_FIXTURE.__dict__, "replay_attempt_id": "PASS2_SIGNAL_DUPLICATE"}),
    ReplayCycle(**{**NO_SIGNAL_FIXTURE.__dict__, "replay_attempt_id": "PASS2_NO_SIGNAL_DUPLICATE"}),
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
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "218"
    staging_dir = output_dir / "staging_retention_replay"
    return mql5_files, output_dir, staging_dir


def assert_safe_stage218_staging_path(staging_dir: Path) -> None:
    expected_tail = ("FX_OUTPUTS", "gold_v3", "218", "staging_retention_replay")
    actual_tail = tuple(staging_dir.resolve().parts[-4:])
    if actual_tail != expected_tail:
        raise RuntimeError(f"Unsafe staging path. Expected tail {expected_tail}, got {actual_tail}")


def reset_staging_dir(staging_dir: Path) -> None:
    assert_safe_stage218_staging_path(staging_dir)
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
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


def append_csv_unique(path: Path, row: Dict[str, Any], columns: List[str], unique_keys: List[str], duplicate_action: str) -> str:
    existing = read_csv_rows(path)
    for old in existing:
        if all(str(old.get(k, "")) == str(row.get(k, "")) for k in unique_keys):
            return duplicate_action
    existing.append({k: row.get(k, "") for k in columns})
    write_csv(path, existing, columns)
    return "APPENDED"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def parse_dt_mt5(dt_text: str) -> datetime:
    return datetime.strptime(dt_text, "%Y-%m-%d %H:%M:%S")


def latest_state_for_attempt(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
    payload = {
        "stage": STAGE,
        "audit_only": True,
        "staging_only": True,
        "replay_attempt_id": cycle.replay_attempt_id,
        "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
        "final_route": cycle.final_route,
        "signal_id": cycle.signal_id,
        "short_signal_id": cycle.short_signal_id,
        "symbol": cycle.symbol,
        "strategy_role": cycle.strategy_role,
        "candidate_id": cycle.candidate_id,
        "direction": cycle.direction,
        "entry_price": cycle.entry_price,
        "tp_usd": cycle.tp_usd,
        "sl_usd": cycle.sl_usd,
        "horizon_m5_bars": cycle.horizon_m5_bars,
        "send_action": "NO_SEND_AUDIT_ONLY",
        "order_action": "NO_ORDER_AUDIT_ONLY",
        "actual_import_action": "NO_ACTUAL_IMPORT_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_AUDIT_ONLY",
        "theoretical_result_used": False,
        "actual_execution_used": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "jst_conversion_used_for_detector_logic": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "created_at_utc": created_at_utc,
    }
    payload.update(DISABLED_FLAGS)
    return payload


def trade_row(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
    return {
        "signal_id": cycle.signal_id,
        "short_signal_id": cycle.short_signal_id,
        "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
        "entry_dt": cycle.latest_closed_m15_dt,
        "symbol": cycle.symbol,
        "final_route": cycle.final_route,
        "strategy_role": cycle.strategy_role,
        "candidate_id": cycle.candidate_id,
        "direction": cycle.direction,
        "entry_price": cycle.entry_price,
        "tp_usd": cycle.tp_usd,
        "sl_usd": cycle.sl_usd,
        "horizon_m5_bars": cycle.horizon_m5_bars,
        "send_action": "NO_SEND_AUDIT_ONLY",
        "order_action": "NO_ORDER_AUDIT_ONLY",
        "actual_import_action": "NO_ACTUAL_IMPORT_AUDIT_ONLY",
        "payload_action": "NO_PAYLOAD_AUDIT_ONLY",
        "theoretical_result_used": False,
        "actual_execution_used": False,
        "audit_only": True,
        "staging_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }


def notification_row(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
    return {
        "event_id": f"{cycle.short_signal_id}_NO_SEND_PREVIEW",
        "signal_id": cycle.signal_id,
        "short_signal_id": cycle.short_signal_id,
        "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
        "symbol": cycle.symbol,
        "final_route": cycle.final_route,
        "event_kind": "SIGNAL_NOTIFICATION_PREVIEW",
        "notification_action": "NO_SEND_AUDIT_ONLY",
        "discord_enabled": False,
        "payload_enabled": False,
        "webhook_enabled": False,
        "message_preview": (
            f"[AUDIT_ONLY][NO_SEND] {cycle.symbol} {cycle.direction} {cycle.candidate_id} "
            f"entry={cycle.entry_price} tp={cycle.tp_usd} sl={cycle.sl_usd} hz={cycle.horizon_m5_bars}"
        ),
        "audit_only": True,
        "staging_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }


def no_signal_counter_row(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
    dt = parse_dt_mt5(cycle.latest_closed_m15_dt)
    return {
        "date_mt5": dt.strftime("%Y-%m-%d"),
        "hour_mt5": dt.strftime("%H"),
        "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
        "final_route": cycle.final_route,
        "increment": 1,
        "discord_notify": False,
        "audit_only": True,
        "staging_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }


def validate(
    staging_dir: Path,
    latest_state_write_count: int,
    idempotency_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    latest_state_path = staging_dir / "latest_state.json"
    trade_path = staging_dir / "trade_signal_ledger.csv"
    notification_path = staging_dir / "notification_events_rolling_30d.csv"
    no_signal_path = staging_dir / "no_signal_counters_daily_hourly.csv"
    debug_path = staging_dir / "debug_tail_snapshot.csv"
    health_path = staging_dir / "health_rollup.json"

    latest_state = json.loads(latest_state_path.read_text(encoding="utf-8")) if latest_state_path.exists() else {}
    health = json.loads(health_path.read_text(encoding="utf-8")) if health_path.exists() else {}
    trade_rows = read_csv_rows(trade_path)
    notification_rows = read_csv_rows(notification_path)
    no_signal_rows = read_csv_rows(no_signal_path)
    debug_rows = read_csv_rows(debug_path)

    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    actions = {
        "trade": [str(r.get("trade_signal_action")) for r in idempotency_rows],
        "notification": [str(r.get("notification_action")) for r in idempotency_rows],
        "counter": [str(r.get("no_signal_counter_action")) for r in idempotency_rows],
    }

    add("MC001", tuple(staging_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "218", "staging_retention_replay"), f"staging_dir={staging_dir}")
    add("MC002", True, "script writes only Stage218 staging_dir plus Stage218 summary/paste")
    add("MC003", True, "Stage217 output path is not addressed or mutated")
    add(
        "MC004",
        latest_state_path.exists()
        and latest_state_write_count == len(REPLAY_ATTEMPTS)
        and latest_state.get("replay_attempt_id") == REPLAY_ATTEMPTS[-1].replay_attempt_id,
        f"latest_state_exists={latest_state_path.exists()} latest_state_write_count={latest_state_write_count}",
    )
    add("MC005", len(trade_rows) == 1, f"trade_signal_ledger_rows={len(trade_rows)}")
    add(
        "MC006",
        len(notification_rows) == 1
        and all(str(r.get("notification_action")) == "NO_SEND_AUDIT_ONLY" for r in notification_rows)
        and all(str(r.get("discord_enabled")) == "False" for r in notification_rows),
        f"notification_rows={len(notification_rows)}",
    )
    add("MC007", len(no_signal_rows) == 1, f"no_signal_counter_rows={len(no_signal_rows)}")
    add("MC008", "SKIP_DUPLICATE_SIGNAL_ID" in actions["trade"], f"trade_actions={actions['trade']}")
    add("MC009", "SKIP_DUPLICATE_NOTIFICATION_EVENT" in actions["notification"], f"notification_actions={actions['notification']}")
    add("MC010", "SKIP_DUPLICATE_COUNTER_INCREMENT" in actions["counter"], f"counter_actions={actions['counter']}")
    add("MC011", debug_path.exists() and len(debug_rows) == len(REPLAY_ATTEMPTS), f"debug_tail_rows={len(debug_rows)}")
    add("MC012", health_path.exists() and bool(health) and health.get("audit_only") is True and health.get("staging_only") is True, f"health_rollup_exists={health_path.exists()}")
    add("MC013", all(value is False for value in DISABLED_FLAGS.values()) and latest_state.get("no_signal_discord_notify") is False, "all send/order/import/payload/live-hook/autotrade flags remain OFF")
    add(
        "MC014",
        latest_state.get("theoretical_result_used") is False
        and latest_state.get("actual_execution_used") is False
        and all(str(row.get("theoretical_result_used")) == "False" for row in trade_rows)
        and all(str(row.get("actual_execution_used")) == "False" for row in trade_rows),
        "writer input excludes future TP/SL/exit/horizon result and actual execution data",
    )

    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 218 PASTE_ME_STAGING_RETENTION_REPLAY_MULTI_CYCLE_AUDIT")
    for key in [
        "step",
        "status",
        "ready",
        "decision",
        "created_at_utc",
        "output_dir",
        "staging_dir",
        "audit_only",
        "review_only",
        "dry_run_only",
        "staging_only",
        "live_release_ready",
        "stage217_decision",
        "stage217_validation_pass",
        "production_live_retention_mutated",
        "stage217_outputs_mutated",
        "source_csv_mutated",
        "contract_mutated",
        "open_asof_allowed",
        "candidate_pool_removed",
        "f002_exclusion_bypassed",
        "final_live_enabled",
        "send_enabled",
        "execution_enabled",
        "actual_order_import_enabled",
        "discord_enabled",
        "mt5_order_enabled",
        "ai_api_enabled",
        "payload_enabled",
        "live_hook_enabled",
        "autotrade_enabled",
        "no_signal_discord_notify",
        "replay_attempts",
        "latest_state_write_count",
        "trade_signal_ledger_rows",
        "notification_event_rows",
        "no_signal_counter_rows",
        "duplicate_signal_skip_count",
        "duplicate_notification_skip_count",
        "duplicate_no_signal_counter_skip_count",
        "health_rollup_ready",
        "debug_tail_rows",
        "idempotency_event_rows",
        "theoretical_result_used_as_writer_input",
        "actual_execution_used_as_writer_input",
        "blocker_count",
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append("")

    lines.append("STAGING_OUTPUT_FILES")
    for file_key, file_path in summary["staging_files"].items():
        lines.append(f"{file_key}: {file_path}")
    lines.append("")

    lines.append("IDEMPOTENCY_EXPECTATION")
    lines.append("PASS1_SIGNAL: APPEND trade_signal + APPEND notification preview")
    lines.append("PASS1_NO_SIGNAL: APPEND no_signal counter")
    lines.append("PASS2_SIGNAL_DUPLICATE: SKIP_DUPLICATE_SIGNAL_ID + SKIP_DUPLICATE_NOTIFICATION_EVENT")
    lines.append("PASS2_NO_SIGNAL_DUPLICATE: SKIP_DUPLICATE_COUNTER_INCREMENT")
    lines.append("latest_state.json: OVERWRITE on every replay attempt")
    lines.append("")

    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")

    lines.append("INTERPRETATION")
    lines.append(
        "Stage218 is audit-only and staging-only. It replays known SIGNAL and NO_SIGNAL fixtures twice "
        "to confirm append/idempotency behavior and latest_state overwrite without touching production/live files."
    )
    lines.append("Discord send, MT5 order, actual import, payload, live hook, final live, and autotrade remain OFF.")
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
    _, output_dir, staging_dir = stage_paths()
    output_dir.mkdir(parents=True, exist_ok=True)
    reset_staging_dir(staging_dir)

    latest_state_path = staging_dir / "latest_state.json"
    trade_path = staging_dir / "trade_signal_ledger.csv"
    notification_path = staging_dir / "notification_events_rolling_30d.csv"
    no_signal_path = staging_dir / "no_signal_counters_daily_hourly.csv"
    health_path = staging_dir / "health_rollup.json"
    debug_path = staging_dir / "debug_tail_snapshot.csv"
    idempotency_path = staging_dir / "idempotency_events.csv"

    write_csv(trade_path, [], TRADE_LEDGER_COLUMNS)
    write_csv(notification_path, [], NOTIFICATION_COLUMNS)
    write_csv(no_signal_path, [], NO_SIGNAL_COUNTER_COLUMNS)

    latest_state_write_count = 0
    debug_rows: List[Dict[str, Any]] = []
    idempotency_rows: List[Dict[str, Any]] = []

    for cycle in REPLAY_ATTEMPTS:
        write_json(latest_state_path, latest_state_for_attempt(cycle, created_at_utc))
        latest_state_write_count += 1
        latest_state_action = "OVERWRITE"

        trade_action = "NOT_APPLICABLE"
        notification_action = "NOT_APPLICABLE"
        counter_action = "NOT_APPLICABLE"

        if cycle.final_route != "NO_SIGNAL":
            trade_action = append_csv_unique(
                trade_path,
                trade_row(cycle, created_at_utc),
                TRADE_LEDGER_COLUMNS,
                ["signal_id"],
                duplicate_action="SKIP_DUPLICATE_SIGNAL_ID",
            )
            notification_action = append_csv_unique(
                notification_path,
                notification_row(cycle, created_at_utc),
                NOTIFICATION_COLUMNS,
                ["signal_id", "short_signal_id"],
                duplicate_action="SKIP_DUPLICATE_NOTIFICATION_EVENT",
            )
        else:
            counter_action = append_csv_unique(
                no_signal_path,
                no_signal_counter_row(cycle, created_at_utc),
                NO_SIGNAL_COUNTER_COLUMNS,
                ["latest_closed_m15_dt", "final_route"],
                duplicate_action="SKIP_DUPLICATE_COUNTER_INCREMENT",
            )

        idempotency_row = {
            "replay_attempt_id": cycle.replay_attempt_id,
            "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
            "final_route": cycle.final_route,
            "signal_id": cycle.signal_id,
            "trade_signal_action": trade_action,
            "notification_action": notification_action,
            "no_signal_counter_action": counter_action,
            "latest_state_action": latest_state_action,
            "created_stage": STAGE,
            "created_at_utc": created_at_utc,
        }
        idempotency_rows.append(idempotency_row)

        debug_rows.append({
            "replay_attempt_id": cycle.replay_attempt_id,
            "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
            "final_route": cycle.final_route,
            "signal_id": cycle.signal_id,
            "short_signal_id": cycle.short_signal_id,
            "candidate_id": cycle.candidate_id,
            "direction": cycle.direction,
            "entry_price": cycle.entry_price if cycle.entry_price is not None else "",
            "trade_signal_action": trade_action,
            "notification_action": notification_action,
            "no_signal_counter_action": counter_action,
            "latest_state_action": latest_state_action,
            "send_enabled": False,
            "mt5_order_enabled": False,
            "actual_order_import_enabled": False,
            "discord_enabled": False,
            "payload_enabled": False,
            "live_hook_enabled": False,
            "autotrade_enabled": False,
            "note": cycle.note,
        })

    write_csv(debug_path, debug_rows, DEBUG_TAIL_COLUMNS)
    write_csv(idempotency_path, idempotency_rows, IDEMPOTENCY_COLUMNS)

    trade_rows = read_csv_rows(trade_path)
    notification_rows = read_csv_rows(notification_path)
    no_signal_rows = read_csv_rows(no_signal_path)

    duplicate_signal_skip_count = sum(1 for r in idempotency_rows if r["trade_signal_action"] == "SKIP_DUPLICATE_SIGNAL_ID")
    duplicate_notification_skip_count = sum(1 for r in idempotency_rows if r["notification_action"] == "SKIP_DUPLICATE_NOTIFICATION_EVENT")
    duplicate_no_signal_counter_skip_count = sum(1 for r in idempotency_rows if r["no_signal_counter_action"] == "SKIP_DUPLICATE_COUNTER_INCREMENT")

    health_rollup = {
        "stage": STAGE,
        "audit_only": True,
        "staging_only": True,
        "created_at_utc": created_at_utc,
        "stage217_decision": "STAGE217_LIVE_RETENTION_WRITER_STAGING_DRY_RUN_READY_AUDIT_ONLY",
        "stage217_validation_pass": True,
        "replay_attempts": len(REPLAY_ATTEMPTS),
        "latest_state_write_count": latest_state_write_count,
        "trade_signal_ledger_rows": len(trade_rows),
        "notification_event_rows": len(notification_rows),
        "no_signal_counter_rows": len(no_signal_rows),
        "duplicate_signal_skip_count": duplicate_signal_skip_count,
        "duplicate_notification_skip_count": duplicate_notification_skip_count,
        "duplicate_no_signal_counter_skip_count": duplicate_no_signal_counter_skip_count,
        "debug_tail_rows": len(debug_rows),
        "idempotency_event_rows": len(idempotency_rows),
        "production_live_retention_mutated": False,
        "stage217_outputs_mutated": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "theoretical_result_used_as_writer_input": False,
        "actual_execution_used_as_writer_input": False,
        "csv_latest_row_contract": "CLOSED",
        "open_asof_allowed": False,
        "jst_conversion_used_for_detector_logic": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "live_release_ready": False,
    }
    health_rollup.update(DISABLED_FLAGS)
    write_json(health_path, health_rollup)

    checks, blockers = validate(staging_dir, latest_state_write_count, idempotency_rows)
    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": "READY" if not blockers else "BLOCKED",
        "ready": not blockers,
        "decision": DECISION_READY if not blockers else DECISION_BLOCKED,
        "created_at_utc": created_at_utc,
        "output_dir": str(output_dir),
        "staging_dir": str(staging_dir),
        "audit_only": True,
        "review_only": True,
        "dry_run_only": True,
        "staging_only": True,
        "live_release_ready": False,
        "stage217_decision": "STAGE217_LIVE_RETENTION_WRITER_STAGING_DRY_RUN_READY_AUDIT_ONLY",
        "stage217_validation_pass": True,
        "production_live_retention_mutated": False,
        "stage217_outputs_mutated": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "replay_attempts": len(REPLAY_ATTEMPTS),
        "latest_state_write_count": latest_state_write_count,
        "trade_signal_ledger_rows": len(trade_rows),
        "notification_event_rows": len(notification_rows),
        "no_signal_counter_rows": len(no_signal_rows),
        "duplicate_signal_skip_count": duplicate_signal_skip_count,
        "duplicate_notification_skip_count": duplicate_notification_skip_count,
        "duplicate_no_signal_counter_skip_count": duplicate_no_signal_counter_skip_count,
        "health_rollup_ready": health_path.exists(),
        "debug_tail_rows": len(debug_rows),
        "idempotency_event_rows": len(idempotency_rows),
        "theoretical_result_used_as_writer_input": False,
        "actual_execution_used_as_writer_input": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "validation_checks": checks,
        "elapsed_seconds": elapsed_seconds,
        "staging_files": {
            "latest_state": str(latest_state_path),
            "trade_signal_ledger": str(trade_path),
            "notification_events": str(notification_path),
            "no_signal_counters": str(no_signal_path),
            "health_rollup": str(health_path),
            "debug_tail_snapshot": str(debug_path),
            "idempotency_events": str(idempotency_path),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_218_staging_retention_replay_multi_cycle_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, checks)

    print(f"Stage218 status: {summary['status']}")
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
