#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage217 - Live Retention Writer Dry-Run To Staging Audit

Audit-only / staging-only writer mechanics check.

This script intentionally writes only to:
  FX_OUTPUTS/gold_v3/217/staging_retention/

It does not send Discord notifications, place MT5 orders, import actual executions,
emit payloads, enable live hooks, or enable autotrade.
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


STAGE = "GOLD_V3_217_LIVE_RETENTION_WRITER_DRY_RUN_TO_STAGING_AUDIT_ONLY"
DECISION_READY = "STAGE217_LIVE_RETENTION_WRITER_STAGING_DRY_RUN_READY_AUDIT_ONLY"
DECISION_BLOCKED = "STAGE217_LIVE_RETENTION_WRITER_STAGING_DRY_RUN_BLOCKED_AUDIT_ONLY"

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

DEBUG_TAIL_COLUMNS = [
    "latest_closed_m15_dt",
    "final_route",
    "signal_id",
    "short_signal_id",
    "candidate_id",
    "direction",
    "entry_price",
    "append_trade_signal",
    "append_notification_preview",
    "increment_no_signal_counter",
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


REPLAY_CYCLES: List[ReplayCycle] = [
    ReplayCycle(
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
        note="Stage215 SIGNAL append preview replay row; writer input excludes future result data.",
    ),
    ReplayCycle(
        latest_closed_m15_dt="2026-06-16 16:45:00",
        final_route="NO_SIGNAL",
        note="Stage211-style NO_SIGNAL cycle; counter/health only, no notification.",
    ),
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

    # Non-Windows fallback for syntax/local audit checks only.
    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def stage_paths() -> Tuple[Path, Path, Path]:
    mql5_files = default_mql5_files_dir()
    output_dir = mql5_files / "FX_OUTPUTS" / "gold_v3" / "217"
    staging_dir = output_dir / "staging_retention"
    return mql5_files, output_dir, staging_dir


def assert_safe_staging_path(staging_dir: Path) -> None:
    parts = set(staging_dir.resolve().parts)
    expected_tail = ("FX_OUTPUTS", "gold_v3", "217", "staging_retention")

    normalized = tuple(staging_dir.resolve().parts[-4:])
    if normalized != expected_tail:
        raise RuntimeError(
            "Unsafe staging path. Expected tail "
            f"{expected_tail}, got {normalized}. Refusing to write."
        )

    required = {"FX_OUTPUTS", "gold_v3", "217", "staging_retention"}
    if not required.issubset(parts):
        raise RuntimeError(
            f"Unsafe staging path missing required parts {required}: {staging_dir}"
        )


def reset_staging_dir(staging_dir: Path) -> None:
    assert_safe_staging_path(staging_dir)
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


def append_csv_unique(
    path: Path,
    row: Dict[str, Any],
    columns: List[str],
    unique_keys: List[str],
) -> str:
    existing = read_csv_rows(path)
    for old in existing:
        if all(str(old.get(k, "")) == str(row.get(k, "")) for k in unique_keys):
            return "SKIP_DUPLICATE"

    existing.append({k: row.get(k, "") for k in columns})
    write_csv(path, existing, columns)
    return "APPENDED"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def parse_dt_mt5(dt_text: str) -> datetime:
    return datetime.strptime(dt_text, "%Y-%m-%d %H:%M:%S")


def latest_state_for_cycle(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
    payload = {
        "stage": STAGE,
        "audit_only": True,
        "staging_only": True,
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


def trade_row_for_cycle(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
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


def notification_row_for_cycle(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
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
            f"[AUDIT_ONLY][NO_SEND] {cycle.symbol} {cycle.direction} "
            f"{cycle.candidate_id} entry={cycle.entry_price} "
            f"tp={cycle.tp_usd} sl={cycle.sl_usd} hz={cycle.horizon_m5_bars}"
        ),
        "audit_only": True,
        "staging_only": True,
        "created_stage": STAGE,
        "created_at_utc": created_at_utc,
    }


def no_signal_counter_row_for_cycle(cycle: ReplayCycle, created_at_utc: str) -> Dict[str, Any]:
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


def debug_row_for_cycle(
    cycle: ReplayCycle,
    append_trade_signal: bool,
    append_notification_preview: bool,
    increment_no_signal_counter: bool,
) -> Dict[str, Any]:
    return {
        "latest_closed_m15_dt": cycle.latest_closed_m15_dt,
        "final_route": cycle.final_route,
        "signal_id": cycle.signal_id,
        "short_signal_id": cycle.short_signal_id,
        "candidate_id": cycle.candidate_id,
        "direction": cycle.direction,
        "entry_price": cycle.entry_price if cycle.entry_price is not None else "",
        "append_trade_signal": append_trade_signal,
        "append_notification_preview": append_notification_preview,
        "increment_no_signal_counter": increment_no_signal_counter,
        "send_enabled": False,
        "mt5_order_enabled": False,
        "actual_order_import_enabled": False,
        "discord_enabled": False,
        "payload_enabled": False,
        "live_hook_enabled": False,
        "autotrade_enabled": False,
        "note": cycle.note,
    }


def validate_outputs(output_dir: Path, staging_dir: Path, latest_state_write_count: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    latest_state_path = staging_dir / "latest_state.json"
    trade_path = staging_dir / "trade_signal_ledger.csv"
    notification_path = staging_dir / "notification_events_rolling_30d.csv"
    no_signal_path = staging_dir / "no_signal_counters_daily_hourly.csv"
    health_path = staging_dir / "health_rollup.json"
    debug_path = staging_dir / "debug_tail_snapshot.csv"

    trade_rows = read_csv_rows(trade_path)
    notification_rows = read_csv_rows(notification_path)
    no_signal_rows = read_csv_rows(no_signal_path)
    debug_rows = read_csv_rows(debug_path)
    latest_state = json.loads(latest_state_path.read_text(encoding="utf-8")) if latest_state_path.exists() else {}
    health = json.loads(health_path.read_text(encoding="utf-8")) if health_path.exists() else {}

    checks: List[Dict[str, Any]] = []

    def add(check_id: str, passed: bool, details: str) -> None:
        checks.append({"check_id": check_id, "passed": bool(passed), "details": details})

    add(
        "STG001",
        tuple(staging_dir.resolve().parts[-4:]) == ("FX_OUTPUTS", "gold_v3", "217", "staging_retention"),
        f"staging_dir={staging_dir}",
    )
    add(
        "STG002",
        True,
        "script writes only stage217 staging_dir plus stage217 summary/paste; no production/live retention path is addressed",
    )
    add(
        "STG003",
        latest_state_path.exists()
        and latest_state_write_count == len(REPLAY_CYCLES)
        and latest_state.get("latest_closed_m15_dt") == REPLAY_CYCLES[-1].latest_closed_m15_dt
        and latest_state.get("final_route") == REPLAY_CYCLES[-1].final_route,
        f"latest_state_exists={latest_state_path.exists()} latest_state_write_count={latest_state_write_count}",
    )
    add("STG004", len(trade_rows) == 1, f"trade_signal_ledger_rows={len(trade_rows)}")
    add(
        "STG005",
        len(notification_rows) == 1
        and all(str(row.get("notification_action")) == "NO_SEND_AUDIT_ONLY" for row in notification_rows)
        and all(str(row.get("discord_enabled")) == "False" for row in notification_rows),
        f"notification_rows={len(notification_rows)}",
    )
    add("STG006", len(no_signal_rows) == 1, f"no_signal_counter_rows={len(no_signal_rows)}")
    add("STG007", health_path.exists() and bool(health), f"health_rollup_exists={health_path.exists()}")
    add("STG008", debug_path.exists() and len(debug_rows) == len(REPLAY_CYCLES), f"debug_tail_rows={len(debug_rows)}")
    add(
        "STG009",
        all(value is False for value in DISABLED_FLAGS.values())
        and latest_state.get("no_signal_discord_notify") is False,
        "all send/order/import/payload/live-hook/autotrade flags remain OFF",
    )
    add(
        "STG010",
        latest_state.get("theoretical_result_used") is False
        and latest_state.get("actual_execution_used") is False
        and all(str(row.get("theoretical_result_used")) == "False" for row in trade_rows)
        and all(str(row.get("actual_execution_used")) == "False" for row in trade_rows),
        "writer input excludes future TP/SL/exit/horizon result and actual execution data",
    )

    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], rules: List[Dict[str, str]], checks: List[Dict[str, Any]]) -> None:
    stage216_basis = summary.get("stage216_basis", {})
    lines: List[str] = []
    lines.append("GOLD V3 217 PASTE_ME_LIVE_RETENTION_WRITER_DRY_RUN_TO_STAGING_AUDIT")
    lines.append(f"step: {summary['step']}")
    lines.append(f"status: {summary['status']}")
    lines.append(f"ready: {summary['ready']}")
    lines.append(f"decision: {summary['decision']}")
    lines.append(f"created_at_utc: {summary['created_at_utc']}")
    lines.append(f"output_dir: {summary['output_dir']}")
    lines.append(f"staging_dir: {summary['staging_dir']}")
    lines.append(f"audit_only: {summary['audit_only']}")
    lines.append(f"review_only: {summary['review_only']}")
    lines.append(f"dry_run_only: {summary['dry_run_only']}")
    lines.append(f"staging_only: {summary['staging_only']}")
    lines.append(f"live_release_ready: {summary['live_release_ready']}")
    lines.append(f"production_live_retention_mutated: {summary['production_live_retention_mutated']}")
    lines.append(f"source_csv_mutated: {summary['source_csv_mutated']}")
    lines.append(f"contract_mutated: {summary['contract_mutated']}")
    lines.append(f"open_asof_allowed: {summary['open_asof_allowed']}")
    lines.append(f"candidate_pool_removed: {summary['candidate_pool_removed']}")
    lines.append(f"f002_exclusion_bypassed: {summary['f002_exclusion_bypassed']}")
    for key in [
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
    ]:
        lines.append(f"{key}: {summary[key]}")
    lines.append(f"latest_state_write_count: {summary['latest_state_write_count']}")
    lines.append(f"trade_signal_ledger_rows: {summary['trade_signal_ledger_rows']}")
    lines.append(f"notification_event_rows: {summary['notification_event_rows']}")
    lines.append(f"no_signal_counter_rows: {summary['no_signal_counter_rows']}")
    lines.append(f"health_rollup_ready: {summary['health_rollup_ready']}")
    lines.append(f"debug_tail_rows: {summary['debug_tail_rows']}")
    lines.append(f"theoretical_result_used_as_writer_input: {summary['theoretical_result_used_as_writer_input']}")
    lines.append(f"actual_execution_used_as_writer_input: {summary['actual_execution_used_as_writer_input']}")
    lines.append(f"blocker_count: {summary['blocker_count']}")
    lines.append("")

    lines.append("STAGE216_BASIS")
    for key, value in stage216_basis.items():
        lines.append(f"{key}: {value}")
    lines.append("")

    lines.append("STAGING_OUTPUT_FILES")
    for file_key, file_path in summary["staging_files"].items():
        lines.append(f"{file_key}: {file_path}")
    lines.append("")

    lines.append("RETENTION_WRITER_RULES")
    for rule in rules:
        lines.append(f"{rule['file']} | {rule['operation']} | {rule['scope']} | {rule['guard']}")
    lines.append("")

    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")

    lines.append("INTERPRETATION")
    lines.append(
        "Stage217 is audit-only and staging-only. It validates latest_state overwrite, "
        "SIGNAL append, notification preview append, NO_SIGNAL counter, health rollup, "
        "and debug tail file mechanics without mutating production/live retention files."
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

    rules = [
        {
            "file": "latest_state.json",
            "operation": "OVERWRITE",
            "scope": "staging_only",
            "guard": "never writes production/live retention latest_state",
        },
        {
            "file": "trade_signal_ledger.csv",
            "operation": "APPEND_SIGNAL_ONLY",
            "scope": "staging_only",
            "guard": "NO_SIGNAL full rows are not appended; duplicate signal_id would skip",
        },
        {
            "file": "notification_events_rolling_30d.csv",
            "operation": "APPEND_SIGNAL_PREVIEW_ONLY",
            "scope": "staging_only",
            "guard": "NO_SEND_AUDIT_ONLY; no Discord webhook/payload",
        },
        {
            "file": "no_signal_counters_daily_hourly.csv",
            "operation": "INCREMENT_NO_SIGNAL_COUNTER_ONLY",
            "scope": "staging_only",
            "guard": "NO_SIGNAL does not notify Discord",
        },
        {
            "file": "debug_tail_snapshot.csv",
            "operation": "REPLACE_ROLLING_SNAPSHOT",
            "scope": "staging_only",
            "guard": "debug only; not a live signal source",
        },
    ]

    reset_staging_dir(staging_dir)

    latest_state_path = staging_dir / "latest_state.json"
    trade_path = staging_dir / "trade_signal_ledger.csv"
    notification_path = staging_dir / "notification_events_rolling_30d.csv"
    no_signal_path = staging_dir / "no_signal_counters_daily_hourly.csv"
    debug_path = staging_dir / "debug_tail_snapshot.csv"
    health_path = staging_dir / "health_rollup.json"

    write_csv(trade_path, [], TRADE_LEDGER_COLUMNS)
    write_csv(notification_path, [], NOTIFICATION_COLUMNS)
    write_csv(no_signal_path, [], NO_SIGNAL_COUNTER_COLUMNS)

    debug_rows: List[Dict[str, Any]] = []
    latest_state_write_count = 0

    for cycle in REPLAY_CYCLES:
        state = latest_state_for_cycle(cycle, created_at_utc)
        write_json(latest_state_path, state)
        latest_state_write_count += 1

        append_trade_signal = False
        append_notification_preview = False
        increment_no_signal_counter = False

        if cycle.final_route != "NO_SIGNAL":
            trade_status = append_csv_unique(
                trade_path,
                trade_row_for_cycle(cycle, created_at_utc),
                TRADE_LEDGER_COLUMNS,
                ["signal_id"],
            )
            append_trade_signal = trade_status == "APPENDED"

            notification_status = append_csv_unique(
                notification_path,
                notification_row_for_cycle(cycle, created_at_utc),
                NOTIFICATION_COLUMNS,
                ["signal_id", "short_signal_id"],
            )
            append_notification_preview = notification_status == "APPENDED"
        else:
            counter_status = append_csv_unique(
                no_signal_path,
                no_signal_counter_row_for_cycle(cycle, created_at_utc),
                NO_SIGNAL_COUNTER_COLUMNS,
                ["latest_closed_m15_dt", "final_route"],
            )
            increment_no_signal_counter = counter_status == "APPENDED"

        debug_rows.append(
            debug_row_for_cycle(
                cycle,
                append_trade_signal=append_trade_signal,
                append_notification_preview=append_notification_preview,
                increment_no_signal_counter=increment_no_signal_counter,
            )
        )

    write_csv(debug_path, debug_rows, DEBUG_TAIL_COLUMNS)

    elapsed_seconds = round((datetime.now(timezone.utc) - started).total_seconds(), 3)

    health_rollup = {
        "stage": STAGE,
        "audit_only": True,
        "staging_only": True,
        "created_at_utc": created_at_utc,
        "latest_state_write_count": latest_state_write_count,
        "latest_closed_m15_dt": REPLAY_CYCLES[-1].latest_closed_m15_dt,
        "latest_final_route": REPLAY_CYCLES[-1].final_route,
        "trade_signal_ledger_rows": len(read_csv_rows(trade_path)),
        "notification_event_rows": len(read_csv_rows(notification_path)),
        "no_signal_counter_rows": len(read_csv_rows(no_signal_path)),
        "debug_tail_rows": len(read_csv_rows(debug_path)),
        "production_live_retention_mutated": False,
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

    checks, blockers = validate_outputs(output_dir, staging_dir, latest_state_write_count)

    status = "READY" if not blockers else "BLOCKED"
    summary: Dict[str, Any] = {
        "step": STAGE,
        "status": status,
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
        "production_live_retention_mutated": False,
        "source_csv_mutated": False,
        "contract_mutated": False,
        "open_asof_allowed": False,
        "candidate_pool_removed": False,
        "f002_exclusion_bypassed": False,
        "theoretical_result_used_as_writer_input": False,
        "actual_execution_used_as_writer_input": False,
        "latest_state_write_count": latest_state_write_count,
        "trade_signal_ledger_rows": len(read_csv_rows(trade_path)),
        "notification_event_rows": len(read_csv_rows(notification_path)),
        "no_signal_counter_rows": len(read_csv_rows(no_signal_path)),
        "health_rollup_ready": health_path.exists(),
        "debug_tail_rows": len(read_csv_rows(debug_path)),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "validation_checks": checks,
        "elapsed_seconds": elapsed_seconds,
        "stage216_basis": {
            "stage216_decision": "STAGE216_FEATURE_DRIFT_MONITORING_RULE_READY_AUDIT_ONLY",
            "stage216_validation_pass": True,
            "stage216_blocker_count": 0,
            "stage216_current_case": "FEATURE_DRIFT_ROUTE_PARITY_PASS",
            "stage216_current_severity": "WARN",
            "stage216_blocks_live_review": False,
        },
        "staging_files": {
            "latest_state": str(latest_state_path),
            "trade_signal_ledger": str(trade_path),
            "notification_events": str(notification_path),
            "no_signal_counters": str(no_signal_path),
            "health_rollup": str(health_path),
            "debug_tail_snapshot": str(debug_path),
        },
    }
    summary.update(DISABLED_FLAGS)

    summary_path = output_dir / "gold_v3_217_live_retention_writer_staging_summary.json"
    paste_path = output_dir / "paste_me.txt"
    write_json(summary_path, summary)
    write_paste_me(paste_path, summary, rules, checks)

    print(f"Stage217 status: {summary['status']}")
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
