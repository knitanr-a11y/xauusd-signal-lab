#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC strict-5 guarded demo-send aligned forever runner.

This runner calls the BTC strict-5 once-wrapper on an aligned schedule and keeps
persistent duplicate-order state under data/runtime_state/btc/strict_5.

Safety:
- The child wrapper still only passes --send to the guarded sender when both
  --send and --allow-demo-send are present.
- This runner does not call MT5 directly.
- This runner does not send Discord notifications.
- This runner does not call AI.
- D1 is not read by the BTC strict-5 child wrapper.
- Duplicate order_key protection is handled by the persistent sender ledger.

Typical live-demo use is via:

  scripts/run_btc_strict_5_guarded_demo_send_forever_aligned_weekly_state.bat
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_BASE = Path("data/runtime_logs/btc")
DEFAULT_STATE_DIR = Path("data/runtime_state/btc/strict_5")
CHILD_SCRIPT = REPO_ROOT / "scripts" / "btc_strict_5_signals" / "run_btc_strict_5_guarded_demo_autotrade_from_csv.py"
SUMMARY_NAME = "latest_btc_strict_5_guarded_demo_send_forever_aligned_weekly_state_result.json"
STOP_MARKER_NAME = "latest_btc_strict_5_guarded_demo_send_forever_aligned_weekly_state_stop_marker.json"

ORDER_LEDGER_COLUMNS = [
    "created_at_utc",
    "order_key",
    "payload_key",
    "signal_key",
    "broker_symbol",
    "symbol",
    "direction",
    "lot",
    "order_status",
    "order_send_called",
    "order_send_ok",
    "source",
]

LOOP_LOG_COLUMNS = [
    "cycle_index",
    "cycle_start_utc",
    "cycle_end_utc",
    "returncode",
    "cycle_ok",
    "reason",
    "send_requested",
    "allow_demo_send",
    "send_flag_passed_to_sender",
    "payload_rows",
    "sender_rows_out",
    "sender_dry_run_check_ok_rows",
    "sender_error_rows",
    "sender_sent_rows",
    "sender_order_send_called_count",
    "raw_recent_preview_rows",
    "ctx_last_base_close_time",
    "d1_used",
    "position_policy",
    "max_symbol_positions",
    "max_symbol_lot",
    "persistent_order_ledger_csv",
    "total_seconds",
    "next_run_utc",
    "stdout_log",
    "stderr_log",
    "summary_json",
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


def ensure_parent(path: Path) -> None:
    mkdir_path(path.parent)


def path_exists(path: Path) -> bool:
    return Path(windows_long_path(path)).exists()


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def read_csv_header(path: Path) -> list[str]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8-sig", newline="") as f:
            return next(csv.reader(f), [])
    except Exception:
        return []


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def ensure_empty_csv(path: Path, columns: list[str]) -> None:
    if path_exists(path):
        return
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(columns)


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent(path)
    exists = path_exists(path)
    if exists and read_csv_header(path) != columns:
        rotated = path.with_name(f"{path.stem}.legacy_header_mismatch_{utc_stamp()}{path.suffix}")
        os.replace(windows_long_path(path), windows_long_path(rotated))
        print(f"[WARN] rotated legacy CSV due to header mismatch: {path} -> {rotated}", flush=True)
        exists = False
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in columns})


def local_week_parts(now: datetime | None = None) -> tuple[str, str, str]:
    d = datetime.now() if now is None else now.astimezone().replace(tzinfo=None)
    year, week, _weekday = d.isocalendar()
    return f"{year:04d}", f"{d.month:02d}", f"week_{week:02d}"


def weekly_out_dir(log_base: Path) -> Path:
    y, m, w = local_week_parts()
    return log_base / y / m / w / "strict_5_btc" / "guarded_demo_loop"


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


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def build_child_cmd(args: argparse.Namespace, child_out_dir: Path, persistent_order_ledger: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(CHILD_SCRIPT),
        "--out-dir", str(child_out_dir),
        "--order-ledger-csv", str(persistent_order_ledger),
        "--scan-recent-bars", str(args.scan_recent_bars),
        "--max-signal-age-minutes", str(args.max_signal_age_minutes),
        "--max-orders", str(args.max_orders),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--lot", str(args.lot),
        "--expected-login", str(args.expected_login),
        "--deviation", str(args.deviation),
        "--broker-symbol", str(args.broker_symbol),
        "--symbol", str(args.symbol),
    ]
    if args.mql5_files_dir:
        cmd.extend(["--mql5-files-dir", str(args.mql5_files_dir)])
    if args.m15_csv:
        cmd.extend(["--m15-csv", str(args.m15_csv)])
    if args.h1_csv:
        cmd.extend(["--h1-csv", str(args.h1_csv)])
    if args.h4_csv:
        cmd.extend(["--h4-csv", str(args.h4_csv)])
    if args.latest_only:
        cmd.append("--latest-only")
    if args.terminal_path:
        cmd.extend(["--terminal-path", str(args.terminal_path)])
    if args.portable:
        cmd.append("--portable")
    if args.send:
        cmd.append("--send")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    return cmd


def run_cycle(args: argparse.Namespace, cycle_index: int, loop_dir: Path, persistent_order_ledger: Path) -> dict[str, Any]:
    cycle_start = utc_now()
    stamp = utc_stamp()
    stdout_log = loop_dir / "cycle_logs" / f"cycle_{cycle_index:06d}_{stamp}_stdout.log"
    stderr_log = loop_dir / "cycle_logs" / f"cycle_{cycle_index:06d}_{stamp}_stderr.log"
    child_out_dir = loop_dir / "child_runs"
    mkdir_path(child_out_dir)
    cmd = build_child_cmd(args, child_out_dir, persistent_order_ledger)
    print(f"[CYCLE {cycle_index}] {utc_text(cycle_start)} running child", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    elapsed = round(time.perf_counter() - started, 3)
    cycle_end = utc_now()
    write_text(stdout_log, proc.stdout or "")
    write_text(stderr_log, proc.stderr or "")
    child_summary = read_json_or_empty(child_out_dir / "latest_btc_strict_5_guarded_demo_autotrade_summary.json")
    row = {
        "cycle_index": cycle_index,
        "cycle_start_utc": utc_text(cycle_start),
        "cycle_end_utc": utc_text(cycle_end),
        "returncode": int(proc.returncode),
        "cycle_ok": bool(proc.returncode == 0 and as_bool(child_summary.get("cycle_ok"), False)),
        "reason": child_summary.get("reason", "CHILD_SUMMARY_MISSING_OR_ERROR"),
        "send_requested": bool(args.send),
        "allow_demo_send": bool(args.allow_demo_send),
        "send_flag_passed_to_sender": as_bool(child_summary.get("send_flag_passed_to_sender"), False),
        "payload_rows": as_int(child_summary.get("payload_rows"), 0),
        "sender_rows_out": as_int(child_summary.get("sender_rows_out"), 0),
        "sender_dry_run_check_ok_rows": as_int(child_summary.get("sender_dry_run_check_ok_rows"), 0),
        "sender_error_rows": as_int(child_summary.get("sender_error_rows"), 0),
        "sender_sent_rows": as_int(child_summary.get("sender_sent_rows"), 0),
        "sender_order_send_called_count": as_int(child_summary.get("sender_order_send_called_count"), 0),
        "raw_recent_preview_rows": as_int(child_summary.get("raw_recent_preview_rows"), 0),
        "ctx_last_base_close_time": child_summary.get("ctx_last_base_close_time", ""),
        "d1_used": as_bool(child_summary.get("d1_used"), False),
        "position_policy": str(args.position_policy),
        "max_symbol_positions": int(args.max_symbol_positions),
        "max_symbol_lot": float(args.max_symbol_lot),
        "persistent_order_ledger_csv": str(persistent_order_ledger),
        "total_seconds": elapsed,
        "next_run_utc": "",
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "summary_json": str(child_summary.get("summary_json", child_out_dir / "latest_btc_strict_5_guarded_demo_autotrade_summary.json")),
    }
    print(
        f"[CYCLE {cycle_index}] ok={row['cycle_ok']} reason={row['reason']} "
        f"payload_rows={row['payload_rows']} sent={row['sender_sent_rows']} "
        f"order_send_called={row['sender_order_send_called_count']} seconds={elapsed}",
        flush=True,
    )
    if proc.returncode != 0:
        print("[STDOUT tail]", flush=True)
        print("\n".join((proc.stdout or "").splitlines()[-40:]), flush=True)
        print("[STDERR tail]", flush=True)
        print("\n".join((proc.stderr or "").splitlines()[-40:]), flush=True)
    return row


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BTC strict 5 guarded demo-send aligned forever runner.")
    p.add_argument("--log-base", type=Path, default=DEFAULT_LOG_BASE)
    p.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=None)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--interval-minutes", type=int, default=15)
    p.add_argument("--offset-seconds", type=int, default=5)
    p.add_argument("--scan-recent-bars", type=int, default=5)
    p.add_argument("--max-signal-age-minutes", type=int, default=30)
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--symbol", default="BTC")
    p.add_argument("--terminal-path", default="")
    p.add_argument("--portable", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--max-cycles", type=int, default=0, help="0 = forever. Positive value exits after N cycles for smoke tests.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0:
        raise SystemExit("--interval-minutes must be positive")
    log_base = REPO_ROOT / args.log_base if not args.log_base.is_absolute() else args.log_base
    state_dir = REPO_ROOT / args.state_dir if not args.state_dir.is_absolute() else args.state_dir
    mkdir_path(log_base)
    mkdir_path(state_dir)
    persistent_order_ledger = state_dir / "guarded_demo_order_ledger.csv"
    ensure_empty_csv(persistent_order_ledger, ORDER_LEDGER_COLUMNS)
    cycle_index = 0

    print("=" * 100, flush=True)
    print("BTC strict 5 guarded demo-send aligned forever runner", flush=True)
    print(f"log_base={log_base}", flush=True)
    print(f"state_dir={state_dir}", flush=True)
    print(f"persistent_order_ledger={persistent_order_ledger}", flush=True)
    print(f"interval_minutes={args.interval_minutes} offset_seconds={args.offset_seconds}", flush=True)
    print(f"send={args.send} allow_demo_send={args.allow_demo_send}", flush=True)
    print("Stop with Ctrl+C", flush=True)
    print("=" * 100, flush=True)

    try:
        while True:
            cycle_index += 1
            loop_dir = weekly_out_dir(log_base)
            mkdir_path(loop_dir)
            row = run_cycle(args, cycle_index, loop_dir, persistent_order_ledger)
            next_run = next_aligned_time(utc_now(), int(args.interval_minutes), int(args.offset_seconds))
            row["next_run_utc"] = utc_text(next_run)
            loop_csv = loop_dir / "aligned_loop_log.csv"
            append_csv_row(loop_csv, row, LOOP_LOG_COLUMNS)
            latest_summary = {
                "schema_version": "btc_strict_5_guarded_demo_send_forever_aligned_weekly_state_v1",
                "updated_at_utc": utc_text(),
                "cycle_index": cycle_index,
                "cycle_ok": bool(row.get("cycle_ok")),
                "reason": row.get("reason"),
                "send_requested": bool(args.send),
                "allow_demo_send": bool(args.allow_demo_send),
                "send_flag_passed_to_sender": row.get("send_flag_passed_to_sender"),
                "payload_rows": row.get("payload_rows"),
                "sender_sent_rows": row.get("sender_sent_rows"),
                "sender_order_send_called_count": row.get("sender_order_send_called_count"),
                "d1_used": row.get("d1_used"),
                "log_dir": str(loop_dir),
                "loop_csv": str(loop_csv),
                "persistent_order_ledger_csv": str(persistent_order_ledger),
                "last_cycle": row,
            }
            write_json(loop_dir / SUMMARY_NAME, latest_summary)
            if args.max_cycles > 0 and cycle_index >= int(args.max_cycles):
                print(f"max_cycles reached: {args.max_cycles}", flush=True)
                return 0
            sleep_seconds = max(1.0, (next_run - utc_now()).total_seconds())
            print(f"[SLEEP] next_run_utc={utc_text(next_run)} sleep_seconds={sleep_seconds:.1f}", flush=True)
            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        marker_dir = weekly_out_dir(log_base)
        mkdir_path(marker_dir)
        marker = {
            "schema_version": "btc_strict_5_guarded_demo_send_forever_aligned_weekly_state_stop_marker_v1",
            "stopped_at_utc": utc_text(),
            "cycle_index": cycle_index,
            "reason": "KEYBOARD_INTERRUPT",
            "log_dir": str(marker_dir),
            "persistent_order_ledger_csv": str(persistent_order_ledger),
        }
        write_json(marker_dir / STOP_MARKER_NAME, marker)
        print("KeyboardInterrupt received; stop marker written.", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
