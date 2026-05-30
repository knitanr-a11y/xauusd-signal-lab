#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Forever aligned shadow-only loop for GOLD strict7.

This is the shadow counterpart of:
  run_gold_strict_7_guarded_demo_autotrade_forever_aligned.bat

It keeps the same 1-minute aligned signal generation settings, but it does not
pass --send or --allow-demo-send to the guarded autotrade wrapper. Therefore
mt5.order_send is never enabled by this loop.

Every cycle:
1. Run the existing strict7 CSV -> payload wrapper in dry-run/order-check mode.
2. Keep generated payload artifacts under data/verification/gold_strict7_shadow_payloads/.
3. Append generated payload rows to data/runtime_state/gold/strict_7/gold_strict7_shadow_signal_ledger.csv.
4. Write loop/collector summaries under data/verification/gold_strict7_shadow_forever_loop/.
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
COLLECT_SCRIPT = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "append_gold_strict_7_shadow_ledger_from_guarded_payloads.py"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_LOOP_OUT_DIR = Path("data/verification/gold_strict7_shadow_forever_loop")
DEFAULT_WRAPPER_OUT_DIR = Path("data/verification/gold_strict7_shadow_payloads")
DEFAULT_COLLECT_OUT_ROOT = Path("data/verification/gold_strict7_shadow_collect")
DEFAULT_SHADOW_LEDGER = Path("data/runtime_state/gold/strict_7/gold_strict7_shadow_signal_ledger.csv")
LATEST_SUMMARY_FILENAME = "latest_gold_strict_7_guarded_demo_autotrade_summary.json"
SCHEMA_VERSION = "gold_strict_7_shadow_only_forever_aligned_loop_v1"

SUMMARY_COLUMNS = [
    "loop_started_at", "loop_iteration", "scheduled_for", "started_at", "finished_at", "elapsed_seconds",
    "success", "wrapper_returncode", "collect_returncode", "wrapper_reason", "payload_rows",
    "sender_order_send_called_count", "sender_sent_rows", "shadow_added_rows", "shadow_skipped_duplicate_rows",
    "shadow_ledger_rows_after", "wrapper_period_out_dir", "wrapper_summary_json", "collect_summary_json",
    "stdout_log", "stderr_log",
]


def now() -> datetime:
    return datetime.now()


def ts_text(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")


def stamp_text(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y%m%d_%H%M%S")


def wpath(path: str | Path) -> str:
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
    Path(wpath(path)).mkdir(parents=True, exist_ok=True)


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def year_month_dir(base: Path, dt: datetime) -> Path:
    return resolve_repo_path(base) / f"{dt.year:04d}" / f"{dt.month:02d}"


def weekly_dir(base: Path, dt: datetime) -> Path:
    iso = dt.isocalendar()
    return resolve_repo_path(base) / f"{dt.year:04d}" / f"{dt.month:02d}" / f"week_{iso.week:02d}"


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: Path) -> tuple[str, dict[str, Any]]:
    if not path.exists():
        return "MISSING", {}
    try:
        with open(wpath(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return "OK", obj if isinstance(obj, dict) else {}
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}:{exc}", {}


def append_summary(path: Path, row: dict[str, Any]) -> None:
    mkdirp(path.parent)
    exists = path.exists()
    with open(wpath(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in SUMMARY_COLUMNS})


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


def build_wrapper_cmd(args: argparse.Namespace, run_dt: datetime) -> tuple[list[str], Path]:
    period_out_dir = year_month_dir(args.wrapper_out_dir, run_dt)
    cmd = [
        sys.executable, str(WRAPPER_SCRIPT),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(period_out_dir),
        "--order-ledger-csv", str(args.dry_run_order_ledger_csv),
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
    if args.terminal_path:
        cmd.extend(["--terminal-path", str(args.terminal_path)])
    if args.portable:
        cmd.append("--portable")
    # Critical: no --send and no --allow-demo-send here.
    return cmd, period_out_dir


def build_collect_cmd(args: argparse.Namespace, wrapper_out_dir: Path) -> list[str]:
    return [
        sys.executable, str(COLLECT_SCRIPT),
        "--logs-root", str(wrapper_out_dir),
        "--payload-glob", "**/gold_strict_7_order_payloads.csv",
        "--shadow-ledger-csv", str(args.shadow_ledger_csv),
        "--out-root", str(args.collect_out_root),
        "--max-files", str(args.collect_max_files),
    ]


def latest_collect_summary_path(args: argparse.Namespace) -> Path:
    return resolve_repo_path(args.collect_out_root) / "latest_gold_strict7_shadow_collect_summary.json"


def sync_root_latest_shadow_loop_summary(args: argparse.Namespace, row: dict[str, Any]) -> None:
    root = resolve_repo_path(args.loop_out_dir)
    write_json(root / "latest_gold_strict7_shadow_forever_loop_summary.json", {
        "schema_version": SCHEMA_VERSION,
        "created_at": ts_text(),
        "latest_row": row,
        "safety": {
            "mt5_order_send_enabled": False,
            "send_flag_passed_to_wrapper": False,
            "allow_demo_send_passed_to_wrapper": False,
            "shadow_ledger_csv": str(args.shadow_ledger_csv),
        },
    })


def run_one_iteration(args: argparse.Namespace, *, loop_started_at: str, iteration: int, scheduled_for: datetime, summary_csv: Path, log_dir: Path) -> dict[str, Any]:
    started = now()
    stamp = stamp_text(started)
    stdout_log = log_dir / f"gold_strict7_shadow_loop_iter_{iteration:06d}_{stamp}.stdout.log"
    stderr_log = log_dir / f"gold_strict7_shadow_loop_iter_{iteration:06d}_{stamp}.stderr.log"
    wrapper_cmd, wrapper_period_out_dir = build_wrapper_cmd(args, started)
    collect_cmd = build_collect_cmd(args, resolve_repo_path(args.wrapper_out_dir))

    print("=" * 100, flush=True)
    print(f"[{ts_text()}] SHADOW iteration={iteration} scheduled_for={ts_text(scheduled_for)}", flush=True)
    print(f"wrapper_period_out_dir: {wrapper_period_out_dir}", flush=True)
    print("WRAPPER CMD: " + " ".join(wrapper_cmd), flush=True)
    wrapper_proc = subprocess.run(wrapper_cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    write_text(stdout_log, wrapper_proc.stdout or "")
    write_text(stderr_log, wrapper_proc.stderr or "")

    wrapper_summary_path = wrapper_period_out_dir / LATEST_SUMMARY_FILENAME
    wrapper_status, wrapper_summary = read_json(wrapper_summary_path)

    print("COLLECT CMD: " + " ".join(collect_cmd), flush=True)
    collect_proc = subprocess.run(collect_cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    with open(wpath(stdout_log), "a", encoding="utf-8", newline="") as f:
        f.write("\n\n--- shadow collect stdout ---\n")
        f.write(collect_proc.stdout or "")
    with open(wpath(stderr_log), "a", encoding="utf-8", newline="") as f:
        f.write("\n\n--- shadow collect stderr ---\n")
        f.write(collect_proc.stderr or "")
    collect_status, collect_summary = read_json(latest_collect_summary_path(args))

    finished = now()
    order_send_called = wrapper_summary.get("sender_order_send_called_count", "")
    sent_rows = wrapper_summary.get("sender_sent_rows", "")
    success = (
        wrapper_proc.returncode == 0
        and collect_proc.returncode == 0
        and bool(wrapper_summary.get("cycle_ok", False))
        and int(order_send_called or 0) == 0
        and int(sent_rows or 0) == 0
    )
    row = {
        "loop_started_at": loop_started_at,
        "loop_iteration": iteration,
        "scheduled_for": ts_text(scheduled_for),
        "started_at": ts_text(started),
        "finished_at": ts_text(finished),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "success": bool(success),
        "wrapper_returncode": int(wrapper_proc.returncode),
        "collect_returncode": int(collect_proc.returncode),
        "wrapper_reason": wrapper_summary.get("reason", f"summary_status={wrapper_status}"),
        "payload_rows": wrapper_summary.get("payload_rows", ""),
        "sender_order_send_called_count": order_send_called,
        "sender_sent_rows": sent_rows,
        "shadow_added_rows": collect_summary.get("added_rows", "") if collect_status == "OK" else "",
        "shadow_skipped_duplicate_rows": collect_summary.get("skipped_duplicate_rows", "") if collect_status == "OK" else "",
        "shadow_ledger_rows_after": collect_summary.get("ledger_rows_after", "") if collect_status == "OK" else "",
        "wrapper_period_out_dir": str(wrapper_period_out_dir),
        "wrapper_summary_json": str(wrapper_summary_path),
        "collect_summary_json": str(latest_collect_summary_path(args)),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }
    append_summary(summary_csv, row)
    sync_root_latest_shadow_loop_summary(args, row)
    print(json.dumps(row, ensure_ascii=False, indent=2, default=str), flush=True)
    if wrapper_proc.stdout:
        print("--- wrapper stdout tail ---", flush=True)
        print("\n".join(wrapper_proc.stdout.splitlines()[-50:]), flush=True)
    if collect_proc.stdout:
        print("--- collect stdout tail ---", flush=True)
        print("\n".join(collect_proc.stdout.splitlines()[-50:]), flush=True)
    if wrapper_proc.stderr or collect_proc.stderr:
        print("--- stderr ---", flush=True)
        print((wrapper_proc.stderr or "") + "\n" + (collect_proc.stderr or ""), flush=True)
    print("=" * 100, flush=True)
    return row


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Forever aligned shadow-only GOLD strict7 signal collector.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--loop-out-dir", type=Path, default=DEFAULT_LOOP_OUT_DIR)
    p.add_argument("--wrapper-out-dir", type=Path, default=DEFAULT_WRAPPER_OUT_DIR)
    p.add_argument("--collect-out-root", type=Path, default=DEFAULT_COLLECT_OUT_ROOT)
    p.add_argument("--shadow-ledger-csv", type=Path, default=DEFAULT_SHADOW_LEDGER)
    p.add_argument("--dry-run-order-ledger-csv", type=Path, default=Path("data/runtime_state/gold/strict_7/shadow_only_guarded_sender_dry_run_order_ledger.csv"))
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--run-delay-seconds", type=int, default=5)
    p.add_argument("--scan-recent-bars", type=int, default=3)
    p.add_argument("--max-signal-age-minutes", type=int, default=15)
    p.add_argument("--tail-m5", type=int, default=2000)
    p.add_argument("--tail-h1", type=int, default=1000)
    p.add_argument("--tail-h4", type=int, default=500)
    p.add_argument("--tail-d1", type=int, default=300)
    p.add_argument("--bar-offset", type=int, default=0)
    p.add_argument("--max-orders", type=int, default=7)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=7)
    p.add_argument("--max-symbol-lot", type=float, default=0.07)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--terminal-path", default="")
    p.add_argument("--portable", action="store_true")
    p.add_argument("--collect-max-files", type=int, default=500)
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--stop-on-error", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0 or 60 % args.interval_minutes != 0:
        raise SystemExit("--interval-minutes must be a positive divisor of 60")
    loop_started_at = ts_text()
    loop_base = weekly_dir(args.loop_out_dir, now())
    log_dir = loop_base / "logs"
    summary_csv = loop_base / "gold_strict7_shadow_forever_loop_summary.csv"
    mkdirp(log_dir)
    print("=" * 100, flush=True)
    print("GOLD strict7 SHADOW-ONLY forever aligned loop", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"loop_started_at: {loop_started_at}", flush=True)
    print("send: False", flush=True)
    print("allow_demo_send: False", flush=True)
    print(f"interval_minutes: {args.interval_minutes} run_delay_seconds: {args.run_delay_seconds}", flush=True)
    print(f"csv_dir: {args.csv_dir}", flush=True)
    print(f"wrapper_out_dir_root: {resolve_repo_path(args.wrapper_out_dir)}", flush=True)
    print(f"shadow_ledger_csv: {resolve_repo_path(args.shadow_ledger_csv)}", flush=True)
    print(f"summary_csv: {summary_csv}", flush=True)
    print("Safety: this loop never passes --send or --allow-demo-send to the guarded wrapper.", flush=True)
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
        print(f"[{ts_text()}] next_shadow_run_at={ts_text(scheduled)}", flush=True)
        sleep_until(scheduled)
        iteration += 1
        row = run_one_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=scheduled, summary_csv=summary_csv, log_dir=log_dir)
        if args.stop_on_error and not row.get("success"):
            return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
