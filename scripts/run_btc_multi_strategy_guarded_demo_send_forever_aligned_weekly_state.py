#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Weekly-log BTC multi-strategy guarded demo-send aligned loop.

BTC sidecar runner separated from GOLD by BAT, logs, and persistent state.

Critical startup backlog rule:
- A signal that already exists at loop startup must not be notified late and then traded.
- The first cycle is always a no-send preview. If it has payload rows, their payload_key
  values are recorded in data/runtime_state/btc/multi_strategy/startup_backlog_payload_ledger.csv.
- Any later cycle whose payload_key is in that startup backlog ledger is blocked.
- A genuinely new signal after startup gets a different payload_key and may proceed.

Order send rule:
- Every cycle first runs the child once-wrapper with no --send to inspect payload_key safely.
- Only if payload exists, the key is not startup backlog, and parent --send is requested,
  the child once-wrapper is run a second time with --send. The child still requires its
  own Discord signal-notification gate before MT5 order send.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_BASE = Path("data/runtime_logs/btc")
DEFAULT_STATE_DIR = Path("data/runtime_state/btc/multi_strategy")
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
SUMMARY_NAME = "latest_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_result.json"
STOP_MARKER_NAME = "latest_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_stop_marker.json"
STARTUP_BACKLOG_LEDGER_NAME = "startup_backlog_payload_ledger.csv"

LOOP_LOG_COLUMNS = [
    "cycle_index", "cycle_start_utc", "cycle_end_utc", "returncode", "cycle_ok",
    "cycle_ok_classification", "reason", "allow_demo_send", "send_requested",
    "preview_returncode", "send_returncode", "send_stage_ran",
    "startup_backlog_capture_cycle", "startup_backlog_blocked", "startup_backlog_payload_keys",
    "startup_backlog_ledger_csv", "send_flag_passed_to_sender", "send_suppressed_reason",
    "payload_rows_out", "payload_keys", "guarded_sender_rows_out",
    "guarded_sender_dry_run_check_ok_rows", "guarded_sender_error_rows",
    "guarded_sender_order_send_called_count", "guarded_sender_sent_rows",
    "position_policy", "max_symbol_positions", "max_symbol_lot",
    "persistent_order_ledger_csv", "preview_order_ledger_csv", "send_order_ledger_csv",
    "ledger_synced_from_state", "ledger_synced_to_state", "total_seconds", "next_run_utc",
    "stdout_log", "stderr_log", "summary_json", "preview_summary_json", "send_summary_json",
]

STARTUP_BACKLOG_COLUMNS = [
    "created_at_utc", "payload_key", "signal_time", "entry_time", "strategy_id",
    "strategy_slot", "direction", "broker_symbol", "source_cycle_index", "source_csv",
]


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def path_exists(path: Path) -> bool:
    return Path(windows_long_path(path)).exists()


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_csv_header(path: Path) -> list[str]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8-sig", newline="") as f:
            return next(csv.reader(f), [])
    except Exception:
        return []


def rotate_legacy_csv(path: Path) -> Path:
    rotated = path.with_name(f"{path.stem}.legacy_header_mismatch_{utc_stamp()}{path.suffix}")
    os.replace(windows_long_path(path), windows_long_path(rotated))
    return rotated


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    exists = path_exists(path)
    if exists and read_csv_header(path) != columns:
        rotated = rotate_legacy_csv(path)
        print(f"[WARN] rotated legacy CSV due to header mismatch: {path} -> {rotated}", flush=True)
        exists = False
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in columns})


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path_exists(path):
        return []
    try:
        with open(windows_long_path(path), "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        print(f"[WARN] failed to read csv rows: {path}: {exc}", flush=True)
        return []


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def local_week_parts(now: datetime | None = None) -> tuple[str, str, str]:
    d = datetime.now() if now is None else now.astimezone().replace(tzinfo=None)
    year, week, _weekday = d.isocalendar()
    return f"{year:04d}", f"{d.month:02d}", f"week_{week:02d}"


def weekly_out_dir(log_base: Path) -> Path:
    y, m, w = local_week_parts()
    return log_base / y / m / w / "multi_strategy_btc" / "loop"


def next_aligned_time(now: datetime, interval_minutes: int, offset_seconds: int) -> datetime:
    base = now.replace(second=0, microsecond=0)
    next_bucket_minute = ((base.minute // interval_minutes) + 1) * interval_minutes
    if next_bucket_minute >= 60:
        base = base.replace(minute=0) + timedelta(hours=1)
    else:
        base = base.replace(minute=next_bucket_minute)
    return base + timedelta(seconds=offset_seconds)


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def safe_copy(src: Path, dst: Path) -> bool:
    if not path_exists(src):
        return False
    ensure_parent_dir(dst)
    shutil.copy2(windows_long_path(src), windows_long_path(dst))
    return True


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BTC multi-strategy guarded demo-send loop with weekly logs and persistent state ledger.")
    p.add_argument("--log-base", type=Path, default=DEFAULT_LOG_BASE)
    p.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--max-cycles", type=int, default=0, help="Number of cycles. 0 means infinite.")
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--offset-seconds", type=int, default=2)
    p.add_argument("--run-immediately", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--stop-on-error", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--echo-wrapper-output", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--spread-cost-usd", type=float, default=22.5)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--live-lookback-bars", type=int, default=1)
    p.add_argument("--cooldown-bars-m15", type=int, default=16)
    p.add_argument("--enable-sell-early-low-break-trade", action=argparse.BooleanOptionalAction, default=False)
    return p.parse_args()


def build_once_cmd(args: argparse.Namespace, cycle_dir: Path, *, pass_send: bool) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "run_btc_multi_strategy_guarded_demo_send_once.py"),
        "--csv-dir", str(args.csv_dir), "--out-dir", str(cycle_dir), "--csv-sep", str(args.csv_sep),
        "--broker-symbol", str(args.broker_symbol), "--expected-login", str(args.expected_login), "--require-demo-account",
        "--base-lot", str(args.base_lot), "--spread-cost-usd", str(args.spread_cost_usd), "--magic", "26050604",
        "--max-orders", str(args.max_orders), "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy), "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot), "--latest-confirmed-policy", str(args.latest_confirmed_policy),
        "--live-lookback-bars", str(args.live_lookback_bars), "--cooldown-bars-m15", str(args.cooldown_bars_m15),
    ]
    cmd.append("--enable-sell-early-low-break-trade" if args.enable_sell_early_low_break_trade else "--no-enable-sell-early-low-break-trade")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    if pass_send:
        cmd.append("--send")
    return cmd


def run_once(stage: str, cycle_index: int, args: argparse.Namespace, out_dir: Path, persistent_ledger: Path, *, pass_send: bool) -> dict[str, Any]:
    stage_dir = out_dir / "cycles" / f"cycle_{cycle_index:05d}" / stage
    child_ledger = stage_dir / "guarded_demo_order_ledger.csv"
    synced_from_state = safe_copy(persistent_ledger, child_ledger)

    log_dir = out_dir / "command_logs"
    mkdir_path(log_dir)
    stdout_log = log_dir / f"cycle_{cycle_index:05d}_{stage}_{utc_stamp()}_stdout.txt"
    stderr_log = log_dir / f"cycle_{cycle_index:05d}_{stage}_{utc_stamp()}_stderr.txt"
    cmd = build_once_cmd(args, stage_dir, pass_send=pass_send)

    print("=" * 80, flush=True)
    print(f"[CYCLE] {cycle_index} stage={stage} pass_send={pass_send} start_utc={utc_text()}", flush=True)
    print(f"[INFO] persistent_ledger={persistent_ledger}", flush=True)
    print(f"[INFO] child_ledger={child_ledger}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)

    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")
    if args.echo_wrapper_output:
        if completed.stdout:
            print(completed.stdout.rstrip(), flush=True)
        if completed.stderr:
            print(completed.stderr.rstrip(), file=sys.stderr, flush=True)
    else:
        print(f"[INFO] wrapper stdout saved: {stdout_log}", flush=True)
        if completed.stderr:
            print(f"[WARN] wrapper stderr saved: {stderr_log}", flush=True)

    synced_to_state = safe_copy(child_ledger, persistent_ledger)
    summary_path = stage_dir / "latest_btc_multi_strategy_guarded_demo_send_once_result.json"
    summary = read_json_or_empty(summary_path)
    print(f"[CYCLE] {cycle_index} stage={stage} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return {
        "stage": stage,
        "returncode": int(completed.returncode),
        "elapsed": elapsed,
        "stdout_log": stdout_log,
        "stderr_log": stderr_log,
        "stage_dir": stage_dir,
        "child_ledger": child_ledger,
        "summary_path": summary_path,
        "summary": summary,
        "ledger_synced_from_state": synced_from_state,
        "ledger_synced_to_state": synced_to_state,
    }


def candidate_csv_from_summary(summary: dict[str, Any]) -> Path | None:
    paths = summary.get("paths", {}) if isinstance(summary.get("paths"), dict) else {}
    raw = paths.get("selected_payload_candidates_csv") or paths.get("live_candidates_csv")
    if raw:
        return Path(str(raw))
    return None


def candidate_rows(summary: dict[str, Any]) -> list[dict[str, str]]:
    path = candidate_csv_from_summary(summary)
    if path is None:
        return []
    return read_csv_rows(path)


def payload_keys_from_rows(rows: list[dict[str, str]]) -> list[str]:
    keys: list[str] = []
    for row in rows:
        key = str(row.get("payload_key", "")).strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def load_backlog_keys(path: Path) -> set[str]:
    return {str(row.get("payload_key", "")).strip() for row in read_csv_rows(path) if str(row.get("payload_key", "")).strip()}


def append_startup_backlog(path: Path, rows: list[dict[str, str]], *, cycle_index: int) -> list[str]:
    existing = load_backlog_keys(path)
    added: list[str] = []
    source_csv = ""
    for row in rows:
        key = str(row.get("payload_key", "")).strip()
        if not key or key in existing:
            continue
        append_csv_row(path, {
            "created_at_utc": utc_text(),
            "payload_key": key,
            "signal_time": row.get("signal_time", row.get("signal_close_time", "")),
            "entry_time": row.get("entry_time", ""),
            "strategy_id": row.get("strategy_id", row.get("candidate_name", "")),
            "strategy_slot": row.get("strategy_slot", row.get("pair_name", "")),
            "direction": row.get("direction", ""),
            "broker_symbol": row.get("broker_symbol", ""),
            "source_cycle_index": cycle_index,
            "source_csv": source_csv,
        }, STARTUP_BACKLOG_COLUMNS)
        existing.add(key)
        added.append(key)
    return added


def build_loop_summary(args: argparse.Namespace, started_at: str, cycle_index: int, failed_cycles: int, last_cycle: dict[str, Any], out_dir: Path, persistent_ledger: Path, startup_backlog_ledger: Path, stopped_by_user: bool) -> dict[str, Any]:
    loop_ok = failed_cycles == 0
    return {
        "schema_version": "btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_v3_startup_backlog_key_gate",
        "started_at_utc": started_at,
        "updated_at_utc": utc_text(),
        "loop_ok": loop_ok,
        "stopped_by_user": stopped_by_user,
        "reason": "BTC_MULTI_STRATEGY_WEEKLY_STATE_STOPPED_BY_USER" if stopped_by_user else ("BTC_MULTI_STRATEGY_WEEKLY_STATE_PASS" if loop_ok else "BTC_MULTI_STRATEGY_WEEKLY_STATE_HAS_FAILURES"),
        "cycles_run": cycle_index,
        "failed_cycles": failed_cycles,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "persistent_order_ledger_csv": str(persistent_ledger),
        "startup_backlog_payload_ledger_csv": str(startup_backlog_ledger),
        "weekly_out_dir": str(out_dir),
        "safety": {
            "send_requires_allow_demo_send_and_send": True,
            "startup_backlog_uses_payload_key_not_time_window": True,
            "first_cycle_is_no_send_preview": True,
            "gold_bat_modified_by_this_runner": False,
            "gold_ledgers_mutated_by_this_runner": False,
            "trigger_state_mutated_by_this_runner": False,
            "early_low_break_trade_enabled": bool(args.enable_sell_early_low_break_trade),
            "cooldown_bars_m15": int(args.cooldown_bars_m15),
        },
        "last_cycle": last_cycle,
        "outputs": {"summary_json": str(out_dir / SUMMARY_NAME), "aligned_loop_log_csv": str(out_dir / "aligned_loop_log.csv"), "stop_marker_json": str(out_dir / STOP_MARKER_NAME)},
    }


def main() -> int:
    args = parse_args()
    if args.max_cycles < 0:
        raise ValueError("--max-cycles must be >= 0. Use 0 for infinite.")
    if args.interval_minutes <= 0:
        raise ValueError("--interval-minutes must be > 0")

    out_dir = weekly_out_dir(args.log_base)
    state_dir = args.state_dir
    persistent_ledger = state_dir / "guarded_demo_order_ledger.csv"
    startup_backlog_ledger = state_dir / STARTUP_BACKLOG_LEDGER_NAME
    mkdir_path(out_dir)
    mkdir_path(state_dir)

    print("=" * 80, flush=True)
    print("BTC multi-strategy guarded demo-send WEEKLY-LOG / PERSISTENT-STATE runner", flush=True)
    print(f"weekly_out_dir={out_dir}", flush=True)
    print(f"persistent_order_ledger_csv={persistent_ledger}", flush=True)
    print(f"startup_backlog_payload_ledger_csv={startup_backlog_ledger}", flush=True)
    print(f"allow_demo_send={args.allow_demo_send} send_requested={args.send}", flush=True)
    print("Startup backlog is blocked by payload_key, not by a fixed time window.", flush=True)
    print(f"max_cycles={'infinite' if args.max_cycles == 0 else args.max_cycles} interval_minutes={args.interval_minutes} offset_seconds={args.offset_seconds}", flush=True)
    print("Stop with Ctrl+C", flush=True)
    print("=" * 80, flush=True)

    started_at = utc_text()
    cycle_index = 0
    failed_cycles = 0
    last_cycle: dict[str, Any] = {}

    try:
        while args.max_cycles == 0 or cycle_index < args.max_cycles:
            current_out_dir = weekly_out_dir(args.log_base)
            if current_out_dir != out_dir:
                out_dir = current_out_dir
                mkdir_path(out_dir)
                print(f"[INFO] week boundary detected; switched weekly_out_dir={out_dir}", flush=True)

            if cycle_index > 0 or not args.run_immediately:
                target = next_aligned_time(utc_now(), args.interval_minutes, args.offset_seconds)
                wait_seconds = max(0.0, (target - utc_now()).total_seconds())
                print(f"[INFO] next aligned run UTC={utc_text(target)} wait_seconds={wait_seconds:.1f}", flush=True)
                time.sleep(wait_seconds)

            cycle_index += 1
            cycle_start = utc_text()
            preview = run_once("preview", cycle_index, args, out_dir, persistent_ledger, pass_send=False)
            preview_summary = preview["summary"]
            preview_metrics = preview_summary.get("key_metrics", {}) if isinstance(preview_summary.get("key_metrics"), dict) else {}
            preview_rows = candidate_rows(preview_summary)
            payload_keys = payload_keys_from_rows(preview_rows)
            payload_rows = as_int(preview_metrics.get("payload_rows_out"), 0)
            backlog_keys = load_backlog_keys(startup_backlog_ledger)
            blocked_keys = [key for key in payload_keys if key in backlog_keys]
            capture_cycle = bool(cycle_index == 1 and payload_rows > 0 and payload_keys)
            added_backlog_keys: list[str] = []
            startup_backlog_blocked = False
            send_stage = None

            if capture_cycle:
                added_backlog_keys = append_startup_backlog(startup_backlog_ledger, preview_rows, cycle_index=cycle_index)
                startup_backlog_blocked = True
                cycle_ok = True
                cycle_ok_classification = "STARTUP_BACKLOG_PAYLOAD_CAPTURED_BLOCKED"
                reason = "BTC_STARTUP_BACKLOG_PAYLOAD_CAPTURED_NO_NOTIFY_NO_ORDER"
            elif blocked_keys:
                startup_backlog_blocked = True
                cycle_ok = True
                cycle_ok_classification = "STARTUP_BACKLOG_PAYLOAD_BLOCKED_EXISTING"
                reason = "BTC_STARTUP_BACKLOG_PAYLOAD_KEY_BLOCKED_NO_NOTIFY_NO_ORDER"
            elif payload_rows > 0 and args.send:
                send_stage = run_once("send", cycle_index, args, out_dir, persistent_ledger, pass_send=True)
                send_summary = send_stage["summary"]
                send_metrics = send_summary.get("key_metrics", {}) if isinstance(send_summary.get("key_metrics"), dict) else {}
                cycle_ok = bool(send_stage["returncode"] == 0 and send_summary.get("cycle_ok", False) and (send_stage["ledger_synced_to_state"] or as_int(send_metrics.get("guarded_sender_sent_rows"), 0) == 0))
                cycle_ok_classification = str(send_summary.get("cycle_ok_classification", "SENT_PASS" if cycle_ok else "FAILED"))
                reason = str(send_summary.get("reason", "BTC_SEND_STAGE_DONE"))
            else:
                cycle_ok = bool(preview["returncode"] == 0 and preview_summary.get("cycle_ok", False))
                cycle_ok_classification = str(preview_summary.get("cycle_ok_classification", "SAFE_NO_PAYLOAD_PASS" if cycle_ok else "FAILED"))
                reason = str(preview_summary.get("reason", "BTC_PREVIEW_STAGE_DONE"))

            if not cycle_ok:
                failed_cycles += 1

            active = send_stage or preview
            active_summary = active["summary"]
            active_metrics = active_summary.get("key_metrics", {}) if isinstance(active_summary.get("key_metrics"), dict) else {}
            active_guards = active_summary.get("guards", {}) if isinstance(active_summary.get("guards"), dict) else {}
            cycle_end = utc_text()
            next_run = ""
            if args.max_cycles == 0 or cycle_index < args.max_cycles:
                next_run = utc_text(next_aligned_time(utc_now(), args.interval_minutes, args.offset_seconds))

            row = {
                "cycle_index": cycle_index,
                "cycle_start_utc": cycle_start,
                "cycle_end_utc": cycle_end,
                "returncode": active["returncode"],
                "cycle_ok": cycle_ok,
                "cycle_ok_classification": cycle_ok_classification,
                "reason": reason,
                "allow_demo_send": bool(args.allow_demo_send),
                "send_requested": bool(args.send),
                "preview_returncode": preview["returncode"],
                "send_returncode": "" if send_stage is None else send_stage["returncode"],
                "send_stage_ran": bool(send_stage is not None),
                "startup_backlog_capture_cycle": capture_cycle,
                "startup_backlog_blocked": startup_backlog_blocked,
                "startup_backlog_payload_keys": ";".join(added_backlog_keys or blocked_keys),
                "startup_backlog_ledger_csv": str(startup_backlog_ledger),
                "send_flag_passed_to_sender": as_bool(active_summary.get("send_flag_passed_to_sender"), False),
                "send_suppressed_reason": active_summary.get("send_suppressed_reason", ""),
                "payload_rows_out": payload_rows,
                "payload_keys": ";".join(payload_keys),
                "guarded_sender_rows_out": as_int(active_metrics.get("guarded_sender_rows_out"), 0),
                "guarded_sender_dry_run_check_ok_rows": as_int(active_metrics.get("guarded_sender_dry_run_check_ok_rows"), 0),
                "guarded_sender_error_rows": as_int(active_metrics.get("guarded_sender_error_rows"), 0),
                "guarded_sender_order_send_called_count": as_int(active_metrics.get("guarded_sender_order_send_called_count"), 0),
                "guarded_sender_sent_rows": as_int(active_metrics.get("guarded_sender_sent_rows"), 0),
                "position_policy": active_guards.get("position_policy", args.position_policy),
                "max_symbol_positions": active_guards.get("max_symbol_positions", args.max_symbol_positions),
                "max_symbol_lot": active_guards.get("max_symbol_lot", args.max_symbol_lot),
                "persistent_order_ledger_csv": str(persistent_ledger),
                "preview_order_ledger_csv": str(preview["child_ledger"]),
                "send_order_ledger_csv": "" if send_stage is None else str(send_stage["child_ledger"]),
                "ledger_synced_from_state": bool(active["ledger_synced_from_state"]),
                "ledger_synced_to_state": bool(active["ledger_synced_to_state"]),
                "total_seconds": as_float(active_summary.get("timing", {}).get("total_seconds") if isinstance(active_summary.get("timing"), dict) else active["elapsed"], active["elapsed"]),
                "next_run_utc": next_run,
                "stdout_log": str(active["stdout_log"]),
                "stderr_log": str(active["stderr_log"]),
                "summary_json": str(active["summary_path"]),
                "preview_summary_json": str(preview["summary_path"]),
                "send_summary_json": "" if send_stage is None else str(send_stage["summary_path"]),
            }
            append_csv_row(out_dir / "aligned_loop_log.csv", row, LOOP_LOG_COLUMNS)
            last_cycle = row
            write_json(out_dir / SUMMARY_NAME, build_loop_summary(args, started_at, cycle_index, failed_cycles, last_cycle, out_dir, persistent_ledger, startup_backlog_ledger, stopped_by_user=False))

            compact = {
                "cycle_index": cycle_index,
                "cycle_ok": cycle_ok,
                "cycle_ok_classification": cycle_ok_classification,
                "reason": reason,
                "payload_rows_out": payload_rows,
                "payload_keys": payload_keys,
                "startup_backlog_blocked": startup_backlog_blocked,
                "startup_backlog_payload_keys": added_backlog_keys or blocked_keys,
                "send_stage_ran": bool(send_stage is not None),
                "order_send_called_count": row["guarded_sender_order_send_called_count"],
                "sent_rows": row["guarded_sender_sent_rows"],
                "startup_backlog_ledger_csv": str(startup_backlog_ledger),
                "persistent_order_ledger_csv": str(persistent_ledger),
                "weekly_out_dir": str(out_dir),
                "next_run_utc": next_run,
            }
            print("=" * 80, flush=True)
            print("BTC weekly-state guarded loop compact cycle summary", flush=True)
            print(json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
            print("=" * 80, flush=True)

            if args.stop_on_error and not cycle_ok:
                print("[ERROR] stop_on_error=True and cycle failed; stopping", flush=True)
                break
    except KeyboardInterrupt:
        print("", flush=True)
        print("=" * 80, flush=True)
        print("[STOP] Ctrl+C received. BTC weekly-state guarded loop stopped gracefully.", flush=True)
        if cycle_index == 0:
            marker = {"schema_version": "btc_multi_strategy_weekly_state_precycle_stop_marker_v1", "started_at_utc": started_at, "stopped_at_utc": utc_text(), "stopped_by_user": True, "reason": "STOPPED_BY_USER_BEFORE_FIRST_CYCLE", "cycles_run_this_session": 0}
            write_json(out_dir / STOP_MARKER_NAME, marker)
        else:
            write_json(out_dir / SUMMARY_NAME, build_loop_summary(args, started_at, cycle_index, failed_cycles, last_cycle, out_dir, persistent_ledger, startup_backlog_ledger, stopped_by_user=True))
        print(f"cycles_run={cycle_index} failed_cycles={failed_cycles}", flush=True)
        print(f"summary_json={out_dir / SUMMARY_NAME}", flush=True)
        print("=" * 80, flush=True)
        return 0 if failed_cycles == 0 else 1

    return 0 if failed_cycles == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
