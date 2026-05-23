#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Forever aligned guarded demo autotrade loop for GOLD strict 7.

Thin loop. Order payload logic lives in run_gold_strict_7_guarded_demo_autotrade_from_csv.py.

Runtime log policy:
- The loop summary remains grouped by ISO week under gold_strict_7_guarded_demo_autotrade_loop.
- Per-cycle autotrade payload/sender logs are stored under:

    data/runtime_logs/gold_strict_7_guarded_demo_autotrade/YYYY/MM/YYYYMMDD_HHMMSS/

- A compatibility latest summary is still written to the root wrapper output dir:

    data/runtime_logs/gold_strict_7_guarded_demo_autotrade/latest_gold_strict_7_guarded_demo_autotrade_summary.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER_SCRIPT = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "run_gold_strict_7_guarded_demo_autotrade_from_csv.py"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_LOOP_OUT_DIR = Path("data/runtime_logs/gold_strict_7_guarded_demo_autotrade_loop")
DEFAULT_WRAPPER_OUT_DIR = Path("data/runtime_logs/gold_strict_7_guarded_demo_autotrade")
LATEST_SUMMARY_FILENAME = "latest_gold_strict_7_guarded_demo_autotrade_summary.json"
SCHEMA_VERSION = "gold_strict_7_guarded_demo_autotrade_loop_v3_year_month_wrapper_logs"

SUMMARY_COLUMNS = [
    "loop_started_at", "loop_iteration", "scheduled_for", "started_at", "finished_at", "elapsed_seconds",
    "returncode", "success", "send_requested_by_user", "allow_demo_send", "send_flag_passed_to_sender",
    "reason", "payload_rows", "sender_returncode", "sender_rows_out", "sender_dry_run_check_ok_rows",
    "sender_sent_rows", "sender_error_rows", "sender_order_send_called_count", "raw_recent_signals_after_cooldown",
    "scan_recent_bars", "max_signal_age_minutes", "tail_m5", "tail_h1", "tail_h4", "tail_d1",
    "summary_read_status", "wrapper_out_dir", "wrapper_period_out_dir", "wrapper_summary_json", "root_latest_summary_json",
    "stdout_log", "stderr_log",
]


def now() -> datetime:
    return datetime.now()


def ts_text(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")


def safe_file_ts(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y%m%d_%H%M%S")


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


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def weekly_dir(base_dir: Path, dt: datetime) -> Path:
    iso = dt.isocalendar()
    return base_dir / f"{dt.year:04d}" / f"{dt.month:02d}" / f"week_{iso.week:02d}"


def year_month_dir(base_dir: Path, dt: datetime) -> Path:
    return base_dir / f"{dt.year:04d}" / f"{dt.month:02d}"


def wrapper_period_out_dir(args: argparse.Namespace, dt: datetime) -> Path:
    return year_month_dir(resolve_repo_path(args.wrapper_out_dir), dt)


def root_latest_summary_path(args: argparse.Namespace) -> Path:
    return resolve_repo_path(args.wrapper_out_dir) / LATEST_SUMMARY_FILENAME


def append_summary(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in SUMMARY_COLUMNS})


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: Path) -> tuple[str, dict[str, Any]]:
    if not path.exists():
        return "MISSING", {}
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return "OK", obj if isinstance(obj, dict) else {}
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}:{exc}", {}


def next_aligned_time(interval_minutes: int, delay_seconds: int) -> datetime:
    n = now()
    base = n.replace(second=0, microsecond=0)
    next_minute = ((base.minute // interval_minutes) + 1) * interval_minutes
    hour_add = next_minute // 60
    next_minute %= 60
    return base.replace(minute=next_minute) + timedelta(hours=hour_add, seconds=delay_seconds)


def sleep_until(target: datetime) -> None:
    while True:
        remaining = (target - now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 1.0))


def build_wrapper_cmd(args: argparse.Namespace, *, run_dt: datetime) -> tuple[list[str], Path]:
    period_out_dir = wrapper_period_out_dir(args, run_dt)
    cmd = [
        sys.executable, str(WRAPPER_SCRIPT),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(period_out_dir),
        "--order-ledger-csv", str(args.order_ledger_csv),
        "--broker-symbol", str(args.broker_symbol),
        "--expected-login", str(args.expected_login),
        "--lot", str(args.lot),
        "--scan-recent-bars", str(args.scan_recent_bars),
        "--max-signal-age-minutes", str(args.max_signal_age_minutes),
        "--max-orders", str(args.max_orders),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--bar-offset", str(args.bar_offset),
        "--deviation", str(args.deviation),
        "--tail-m5", str(args.tail_m5),
        "--tail-h1", str(args.tail_h1),
        "--tail-h4", str(args.tail_h4),
        "--tail-d1", str(args.tail_d1),
    ]
    if args.send:
        cmd.append("--send")
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    if args.terminal_path:
        cmd.extend(["--terminal-path", str(args.terminal_path)])
    if args.portable:
        cmd.append("--portable")
    return cmd, period_out_dir


def sync_root_latest_summary(args: argparse.Namespace, *, period_summary_path: Path, wrapper_summary: dict[str, Any]) -> Path:
    root_path = root_latest_summary_path(args)
    copied = dict(wrapper_summary)
    copied["root_latest_summary_json"] = str(root_path)
    copied["period_latest_summary_json"] = str(period_summary_path)
    copied["log_layout"] = {
        "schema_version": SCHEMA_VERSION,
        "wrapper_run_dir_layout": "YYYY/MM/YYYYMMDD_HHMMSS",
        "root_latest_summary_preserved": True,
    }
    write_json(root_path, copied)
    return root_path


def run_one_iteration(args: argparse.Namespace, *, loop_started_at: str, iteration: int, scheduled_for: datetime, summary_csv: Path, log_dir: Path) -> dict[str, Any]:
    started = now()
    stamp = safe_file_ts(started)
    stdout_log = log_dir / f"gold_strict7_autotrade_loop_iter_{iteration:06d}_{stamp}.stdout.log"
    stderr_log = log_dir / f"gold_strict7_autotrade_loop_iter_{iteration:06d}_{stamp}.stderr.log"
    cmd, period_out_dir = build_wrapper_cmd(args, run_dt=started)
    print("=" * 100, flush=True)
    print(f"[{ts_text()}] iteration={iteration} scheduled_for={ts_text(scheduled_for)}", flush=True)
    print(f"wrapper_period_out_dir: {period_out_dir}", flush=True)
    print("CMD: " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    finished = now()
    write_text(stdout_log, proc.stdout or "")
    write_text(stderr_log, proc.stderr or "")

    period_latest_summary = period_out_dir / LATEST_SUMMARY_FILENAME
    summary_status, wrapper_summary = read_json(period_latest_summary)
    root_latest = root_latest_summary_path(args)
    if summary_status == "OK":
        root_latest = sync_root_latest_summary(args, period_summary_path=period_latest_summary, wrapper_summary=wrapper_summary)
    success = proc.returncode == 0 and bool(wrapper_summary.get("cycle_ok", False))
    row = {
        "loop_started_at": loop_started_at,
        "loop_iteration": iteration,
        "scheduled_for": ts_text(scheduled_for),
        "started_at": ts_text(started),
        "finished_at": ts_text(finished),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "returncode": int(proc.returncode),
        "success": bool(success),
        "send_requested_by_user": bool(args.send),
        "allow_demo_send": bool(args.allow_demo_send),
        "send_flag_passed_to_sender": wrapper_summary.get("send_flag_passed_to_sender", ""),
        "reason": wrapper_summary.get("reason", ""),
        "payload_rows": wrapper_summary.get("payload_rows", ""),
        "sender_returncode": wrapper_summary.get("sender_returncode", ""),
        "sender_rows_out": wrapper_summary.get("sender_rows_out", ""),
        "sender_dry_run_check_ok_rows": wrapper_summary.get("sender_dry_run_check_ok_rows", ""),
        "sender_sent_rows": wrapper_summary.get("sender_sent_rows", ""),
        "sender_error_rows": wrapper_summary.get("sender_error_rows", ""),
        "sender_order_send_called_count": wrapper_summary.get("sender_order_send_called_count", ""),
        "raw_recent_signals_after_cooldown": wrapper_summary.get("raw_recent_signals_after_cooldown", ""),
        "scan_recent_bars": int(args.scan_recent_bars),
        "max_signal_age_minutes": int(args.max_signal_age_minutes),
        "tail_m5": int(args.tail_m5),
        "tail_h1": int(args.tail_h1),
        "tail_h4": int(args.tail_h4),
        "tail_d1": int(args.tail_d1),
        "summary_read_status": summary_status,
        "wrapper_out_dir": str(resolve_repo_path(args.wrapper_out_dir)),
        "wrapper_period_out_dir": str(period_out_dir),
        "wrapper_summary_json": str(period_latest_summary),
        "root_latest_summary_json": str(root_latest),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    append_summary(summary_csv, row)
    print(json.dumps(row, ensure_ascii=False, indent=2, default=str), flush=True)
    if proc.stdout:
        print("--- wrapper stdout tail ---", flush=True)
        print("\n".join(proc.stdout.splitlines()[-50:]), flush=True)
    if proc.stderr:
        print("--- wrapper stderr ---", flush=True)
        print(proc.stderr, flush=True)
    print("=" * 100, flush=True)
    return row


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Forever aligned guarded demo autotrade loop for GOLD strict 7.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--loop-out-dir", type=Path, default=DEFAULT_LOOP_OUT_DIR)
    p.add_argument("--wrapper-out-dir", type=Path, default=DEFAULT_WRAPPER_OUT_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=Path("data/runtime_state/gold/strict_7/guarded_demo_order_ledger.csv"))
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--interval-minutes", type=int, default=5)
    p.add_argument("--run-delay-seconds", type=int, default=2)
    p.add_argument("--scan-recent-bars", type=int, default=3)
    p.add_argument("--max-signal-age-minutes", type=int, default=15)
    p.add_argument("--tail-m5", type=int, default=2000)
    p.add_argument("--tail-h1", type=int, default=1000)
    p.add_argument("--tail-h4", type=int, default=500)
    p.add_argument("--tail-d1", type=int, default=300)
    p.add_argument("--bar-offset", type=int, default=1)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--terminal-path", default="")
    p.add_argument("--portable", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--stop-on-error", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0 or 60 % args.interval_minutes != 0:
        raise SystemExit("--interval-minutes must be a positive divisor of 60")
    if args.send and not args.allow_demo_send:
        print("WARNING: --send without --allow-demo-send; wrapper will suppress sender --send.", flush=True)
    loop_started_at = ts_text()
    loop_base = weekly_dir(resolve_repo_path(args.loop_out_dir), now())
    log_dir = loop_base / "logs"
    summary_csv = loop_base / "gold_strict_7_guarded_demo_autotrade_loop_summary.csv"
    mkdirp(log_dir)
    print("=" * 100, flush=True)
    print("GOLD strict 7 guarded demo autotrade loop", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"loop_started_at: {loop_started_at}", flush=True)
    print(f"send: {bool(args.send)}", flush=True)
    print(f"allow_demo_send: {bool(args.allow_demo_send)}", flush=True)
    print(f"run_delay_seconds: {args.run_delay_seconds}", flush=True)
    print(f"tails: M5={args.tail_m5} H1={args.tail_h1} H4={args.tail_h4} D1={args.tail_d1}", flush=True)
    print(f"csv_dir: {args.csv_dir}", flush=True)
    print(f"wrapper_out_dir_root: {resolve_repo_path(args.wrapper_out_dir)}", flush=True)
    print("wrapper_run_dir_layout: YYYY/MM/YYYYMMDD_HHMMSS", flush=True)
    print(f"root_latest_summary_json: {root_latest_summary_path(args)}", flush=True)
    print(f"summary_csv: {summary_csv}", flush=True)
    print(f"log_dir: {log_dir}", flush=True)
    print(f"Safety: existing guarded sender only. max-orders={args.max_orders}. demo guard. position-policy={args.position_policy}.", flush=True)
    print("=" * 100, flush=True)

    iteration = 0
    if args.run_immediately:
        iteration += 1
        row = run_one_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=now(), summary_csv=summary_csv, log_dir=log_dir)
        if args.stop_on_error and not row.get("success"):
            return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0

    while True:
        scheduled = next_aligned_time(int(args.interval_minutes), int(args.run_delay_seconds))
        print(f"[{ts_text()}] next_run_at={ts_text(scheduled)}", flush=True)
        sleep_until(scheduled)
        iteration += 1
        row = run_one_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=scheduled, summary_csv=summary_csv, log_dir=log_dir)
        if args.stop_on_error and not row.get("success"):
            return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
