#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILD_SCRIPT = REPO_ROOT / "scripts" / "run_btc_youtube_candidates_operational_forever.py"
AUDIT_DIR_NAME = "gold_v3_style_audit"
SUMMARY_NAME = "btc_youtube_operational_audit_summary.json"
PASTE_ME_NAME = "btc_youtube_PASTE_ME_OPERATIONAL_SUMMARY.txt"
LEDGER_NAME = "btc_youtube_operational_audit_cycle_ledger.csv"
LEDGER_COLUMNS = [
    "cycle_key", "cycle_index", "cycle_start_utc", "cycle_end_utc", "cycle_ok", "classification",
    "btc6_open_trades", "btc6_closed_trades", "btc6_total_r", "btc6_total_pips",
    "btc6_discord_status", "trade_ledger_rows", "event_ledger_rows", "status",
]


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def arg_value(argv: list[str], name: str, default: str) -> str:
    try:
        index = argv.index(name)
    except ValueError:
        return default
    if index + 1 >= len(argv):
        return default
    return argv[index + 1]


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")


def csv_row_count(path: Path) -> int:
    if not path.exists() or path.stat().st_size <= 0:
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    except Exception:
        return 0


def cycle_key(row: dict[str, Any]) -> str:
    return f"{row.get('cycle_start_utc', '')}::{row.get('cycle_index', '')}"


def append_cycle_once(path: Path, row: dict[str, Any]) -> None:
    key = str(row.get("cycle_key", "")) or cycle_key(row)
    if not key or key == "::":
        return
    existing_keys: set[str] = set()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                for item in csv.DictReader(handle):
                    existing_keys.add(str(item.get("cycle_key", "")) or cycle_key(item))
        except Exception:
            existing_keys = set()
    if key in existing_keys:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        output = {column: row.get(column, "") for column in LEDGER_COLUMNS}
        output["cycle_key"] = key
        writer.writerow(output)


def nested_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_summary(
    latest_state: dict[str, Any], *, state_dir: Path, log_base: Path,
    discord_env_name: str, child_running: bool,
) -> dict[str, Any]:
    last_cycle = nested_dict(latest_state.get("last_cycle"))
    metrics = nested_dict(latest_state.get("btc6_metrics"))
    cycle_ok = bool(last_cycle.get("cycle_ok")) if last_cycle else False
    status = (
        "BTC_YOUTUBE_OPERATIONAL_READY_DEMO_ONLY"
        if cycle_ok
        else "BTC_YOUTUBE_OPERATIONAL_STARTING_DEMO_ONLY"
        if child_running and not last_cycle
        else "BTC_YOUTUBE_OPERATIONAL_ATTENTION_REQUIRED_DEMO_ONLY"
    )
    once_summary_path_text = str(last_cycle.get("once_summary_json", ""))
    once_summary = read_json(Path(once_summary_path_text)) if once_summary_path_text else {}
    dry_run = nested_dict(once_summary.get("dry_run"))
    latest_closed = nested_dict(dry_run.get("latest_closed"))
    cycle_rows = nested_dict(once_summary.get("rows"))

    trade_ledger = state_dir / "btc6_shadow_trade_ledger.csv"
    event_ledger = state_dir / "btc6_shadow_events.csv"
    discord_trade_ledger = state_dir / "discord_trade_send_ledger.csv"
    discord_monitor_ledger = state_dir / "discord_monitor_send_ledger.csv"
    order_ledger = state_dir / "demo_order_ledger.csv"
    summary = {
        "schema_version": "btc_youtube_gold_v3_style_operational_audit_v1",
        "generated_at_utc": utc_text(),
        "status": status,
        "operational_scope": "MT5_DEMO_ONLY",
        "runtime_process_running": bool(child_running),
        "cycle_ok": cycle_ok,
        "classification": last_cycle.get("classification", "STARTING"),
        "cycle_index": last_cycle.get("cycle_index"),
        "cycle_start_utc": last_cycle.get("cycle_start_utc"),
        "cycle_end_utc": last_cycle.get("cycle_end_utc"),
        "csv_contract": "open/in-progress candles are not written to CSV; latest row is closed",
        "latest_closed": latest_closed,
        "cycle_rows": cycle_rows,
        "open_asof_allowed": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "real_money_enabled": False,
        "live_ready": False,
        "final_signal": False,
        "discord": {
            "enabled": True,
            "webhook_configured": bool(os.environ.get(discord_env_name, "").strip()),
            "webhook_value_logged": False,
            "purpose": "send BTC4/BTC5 trade notifications and BTC6 monitoring lifecycle notifications",
            "last_btc6_status": last_cycle.get("btc6_discord_status", ""),
        },
        "candidates": {
            "BTC4_RISK_CAP_400": {"mode": "MT5_DEMO_ORDER", "lot": 0.02, "split": "0.01 TP1 + 0.01 TP2"},
            "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786": {"mode": "MT5_DEMO_ORDER", "lot": 0.01},
            "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886": {
                "mode": "SHADOW_LIVE_NO_BROKER_ORDER", "reference_lot": 0.01,
            },
        },
        "btc6_metrics": metrics,
        "resolved_live_csvs": latest_state.get("resolved_live_csvs", {}),
        "row_counts": {
            "btc6_shadow_trade_ledger": csv_row_count(trade_ledger),
            "btc6_shadow_event_ledger": csv_row_count(event_ledger),
            "discord_trade_send_ledger": csv_row_count(discord_trade_ledger),
            "discord_monitor_send_ledger": csv_row_count(discord_monitor_ledger),
            "demo_order_ledger": csv_row_count(order_ledger),
        },
        "last_cycle": last_cycle,
        "paths": {
            "state_dir": str(state_dir),
            "log_base": str(log_base),
            "latest_operational_state": str(log_base / "youtube_candidates_operational" / "latest_operational_state.json"),
            "btc6_shadow_trade_ledger": str(trade_ledger),
            "btc6_shadow_event_ledger": str(event_ledger),
            "demo_order_ledger": str(order_ledger),
            "once_summary_json": once_summary_path_text,
        },
    }
    return summary


def paste_me_text(summary: dict[str, Any]) -> str:
    metrics = nested_dict(summary.get("btc6_metrics"))
    counts = nested_dict(summary.get("row_counts"))
    discord = nested_dict(summary.get("discord"))
    latest_closed = nested_dict(summary.get("latest_closed"))
    cycle_rows = nested_dict(summary.get("cycle_rows"))
    lines = [
        "BTC YOUTUBE OPERATIONAL AUDIT SUMMARY",
        f"generated_at_utc: {summary.get('generated_at_utc')}",
        f"status: {summary.get('status')}",
        f"operational_scope: {summary.get('operational_scope')}",
        f"runtime_process_running: {summary.get('runtime_process_running')}",
        f"cycle_index: {summary.get('cycle_index')}",
        f"cycle_ok: {summary.get('cycle_ok')}",
        f"classification: {summary.get('classification')}",
        f"real_money_enabled: {summary.get('real_money_enabled')}",
        f"live_ready: {summary.get('live_ready')}",
        f"final_signal: {summary.get('final_signal')}",
        f"open_asof_allowed: {summary.get('open_asof_allowed')}",
        f"contract_mutated: {summary.get('contract_mutated')}",
        f"manual_candidate_demotion_or_removal: {summary.get('manual_candidate_demotion_or_removal')}",
        f"discord_enabled: {discord.get('enabled')}",
        f"discord_webhook_configured: {discord.get('webhook_configured')}",
        f"discord_webhook_value_logged: {discord.get('webhook_value_logged')}",
        f"latest_closed_m5: {latest_closed.get('m5', latest_closed.get('M5', ''))}",
        f"latest_closed_m15: {latest_closed.get('m15', latest_closed.get('M15', ''))}",
        f"latest_closed_h4: {latest_closed.get('h4', latest_closed.get('H4', ''))}",
        f"trade_notification_rows: {cycle_rows.get('trade_notifications', 0)}",
        f"monitor_notification_rows: {cycle_rows.get('monitor_notifications', 0)}",
        f"order_payload_rows: {cycle_rows.get('order_payloads', 0)}",
        "BTC4_mode: MT5_DEMO_ORDER_0.02_SPLIT",
        "BTC5_mode: MT5_DEMO_ORDER_0.01",
        "BTC6_mode: SHADOW_LIVE_REFERENCE_LOT_0.01_NO_BROKER_ORDER",
        f"btc6_open_trades: {metrics.get('open_trades', 0)}",
        f"btc6_closed_trades: {metrics.get('closed_trades', 0)}",
        f"btc6_total_r: {metrics.get('total_r', 0)}",
        f"btc6_total_pips: {metrics.get('total_pips', 0)}",
        f"btc6_trade_ledger_rows: {counts.get('btc6_shadow_trade_ledger', 0)}",
        f"btc6_event_ledger_rows: {counts.get('btc6_shadow_event_ledger', 0)}",
        f"csv_contract: {summary.get('csv_contract')}",
    ]
    return "\n".join(lines) + "\n"


def write_audit_artifacts(
    *, state_dir: Path, log_base: Path, discord_env_name: str, child_running: bool,
) -> dict[str, Any]:
    stable_root = log_base / "youtube_candidates_operational"
    audit_dir = stable_root / AUDIT_DIR_NAME
    latest_state = read_json(stable_root / "latest_operational_state.json")
    summary = build_summary(
        latest_state, state_dir=state_dir, log_base=log_base,
        discord_env_name=discord_env_name, child_running=child_running,
    )
    atomic_write_json(audit_dir / SUMMARY_NAME, summary)
    atomic_write_text(audit_dir / PASTE_ME_NAME, paste_me_text(summary))
    last_cycle = nested_dict(summary.get("last_cycle"))
    counts = nested_dict(summary.get("row_counts"))
    ledger_row = {
        "cycle_key": cycle_key(last_cycle),
        "cycle_index": last_cycle.get("cycle_index", ""),
        "cycle_start_utc": last_cycle.get("cycle_start_utc", ""),
        "cycle_end_utc": last_cycle.get("cycle_end_utc", ""),
        "cycle_ok": last_cycle.get("cycle_ok", ""),
        "classification": last_cycle.get("classification", ""),
        "btc6_open_trades": last_cycle.get("btc6_open_trades", 0),
        "btc6_closed_trades": last_cycle.get("btc6_closed_trades", 0),
        "btc6_total_r": last_cycle.get("btc6_total_r", 0),
        "btc6_total_pips": last_cycle.get("btc6_total_pips", 0),
        "btc6_discord_status": last_cycle.get("btc6_discord_status", ""),
        "trade_ledger_rows": counts.get("btc6_shadow_trade_ledger", 0),
        "event_ledger_rows": counts.get("btc6_shadow_event_ledger", 0),
        "status": summary.get("status", ""),
    }
    append_cycle_once(audit_dir / LEDGER_NAME, ledger_row)
    return summary


def main() -> int:
    forwarded = sys.argv[1:]
    log_base = resolve_path(arg_value(forwarded, "--log-base", "data/runtime_logs/btc"))
    state_dir = resolve_path(arg_value(forwarded, "--state-dir", "data/runtime_state/btc/youtube_candidates"))
    discord_env_name = arg_value(forwarded, "--discord-webhook-env", "DISCORD_WEBHOOK_URL")
    command = [sys.executable, str(CHILD_SCRIPT), *forwarded]
    process = subprocess.Popen(command, cwd=str(REPO_ROOT))
    last_cycle: Any = object()
    try:
        while process.poll() is None:
            summary = write_audit_artifacts(
                state_dir=state_dir, log_base=log_base,
                discord_env_name=discord_env_name, child_running=True,
            )
            cycle = summary.get("cycle_index")
            if cycle != last_cycle:
                print(
                    f"[AUDIT] status={summary.get('status')} cycle={cycle} "
                    f"summary={log_base / 'youtube_candidates_operational' / AUDIT_DIR_NAME / SUMMARY_NAME}",
                    flush=True,
                )
                last_cycle = cycle
            time.sleep(5.0)
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130
    finally:
        write_audit_artifacts(
            state_dir=state_dir, log_base=log_base,
            discord_env_name=discord_env_name, child_running=False,
        )
    return int(process.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
