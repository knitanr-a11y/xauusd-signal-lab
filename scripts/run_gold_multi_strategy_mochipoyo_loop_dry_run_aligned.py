#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""M15-aligned GOLD multi-strategy Mochipoyo-loop dry-run runner.

This script repeatedly calls the independent dry-run wrapper BAT:

    scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run.bat

Safety boundaries:
- This script never passes --send.
- It calls only the independent dry-run BAT.
- It does not call or modify existing Mochipoyo production/demo BATs.
- It does not write production position_registry.csv.
- It does not intentionally mutate existing Mochipoyo ledgers or trigger-state.
- It writes its own loop logs under --out-dir with Windows long-path support.

Purpose:
- Validate the new GOLD BUY/SELL multi-strategy path on a repeated or M15-aligned cadence.
- Keep this separate from the existing Mochipoyo loop until explicitly approved.
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
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_loop_dry_run_aligned")
WRAPPER_SUMMARY_JSON = REPO_ROOT / "data" / "research_results" / "gold_multi_strategy_mochipoyo_loop_dry_run" / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json"

LOOP_LOG_COLUMNS = [
    "cycle_index",
    "cycle_start_utc",
    "cycle_end_utc",
    "returncode",
    "cycle_ok",
    "reason",
    "signals_found_count",
    "open_order_intent_count",
    "payload_rows_out",
    "sender_order_send_called_count",
    "sender_sent_rows",
    "next_run_utc",
    "stdout_log",
    "stderr_log",
    "wrapper_summary_json",
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


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    exists = Path(windows_long_path(path)).exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in columns})


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def next_aligned_time(now: datetime, interval_minutes: int, offset_seconds: int) -> datetime:
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be > 0")
    base = now.replace(second=0, microsecond=0)
    minute = base.minute
    next_bucket_minute = ((minute // interval_minutes) + 1) * interval_minutes
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


def run_wrapper_bat(cycle_index: int, out_dir: Path) -> tuple[int, Path, Path]:
    log_dir = out_dir / "command_logs"
    mkdir_path(log_dir)
    stamp = utc_stamp()
    stdout_log = log_dir / f"cycle_{cycle_index:05d}_{stamp}_stdout.txt"
    stderr_log = log_dir / f"cycle_{cycle_index:05d}_{stamp}_stderr.txt"
    bat = REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_dry_run.bat"
    cmd = ["cmd.exe", "/c", str(bat)]
    print("=" * 80, flush=True)
    print(f"[CYCLE] {cycle_index}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")
    if completed.stdout:
        print(completed.stdout.rstrip(), flush=True)
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr, flush=True)
    print(f"[CYCLE] {cycle_index} returncode={completed.returncode}", flush=True)
    return int(completed.returncode), stdout_log, stderr_log


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run independent GOLD multi-strategy Mochipoyo-loop dry-run wrapper on an aligned cadence.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--max-cycles", type=int, default=1, help="Number of cycles to run. Use 0 for infinite dry-run loop.")
    p.add_argument("--interval-minutes", type=int, default=15)
    p.add_argument("--offset-seconds", type=int, default=8, help="Run this many seconds after each aligned interval boundary.")
    p.add_argument("--run-immediately", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--stop-on-error", action=argparse.BooleanOptionalAction, default=False)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_cycles < 0:
        raise ValueError("--max-cycles must be >= 0. Use 0 for infinite dry-run loop.")
    if args.interval_minutes <= 0:
        raise ValueError("--interval-minutes must be > 0")
    if args.offset_seconds < 0:
        raise ValueError("--offset-seconds must be >= 0")
    mkdir_path(args.out_dir)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy Mochipoyo-loop aligned DRY-RUN runner", flush=True)
    print("NO --send / independent wrapper only / Windows long-path outputs", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"max_cycles={'infinite' if args.max_cycles == 0 else args.max_cycles}", flush=True)
    print(f"interval_minutes={args.interval_minutes} offset_seconds={args.offset_seconds}", flush=True)
    print("=" * 80, flush=True)

    started_at = utc_text()
    cycle_index = 0
    failed_cycles = 0
    last_cycle_summary: dict[str, Any] = {}

    while args.max_cycles == 0 or cycle_index < args.max_cycles:
        if cycle_index > 0 or not args.run_immediately:
            target = next_aligned_time(utc_now(), args.interval_minutes, args.offset_seconds)
            wait_seconds = max(0.0, (target - utc_now()).total_seconds())
            print(f"[INFO] next aligned run UTC={utc_text(target)} wait_seconds={wait_seconds:.1f}", flush=True)
            time.sleep(wait_seconds)

        cycle_index += 1
        cycle_start = utc_text()
        returncode, stdout_log, stderr_log = run_wrapper_bat(cycle_index, args.out_dir)
        cycle_end = utc_text()
        wrapper_summary = read_json_or_empty(WRAPPER_SUMMARY_JSON)
        metrics = wrapper_summary.get("key_metrics", {}) if isinstance(wrapper_summary.get("key_metrics"), dict) else {}
        safety = wrapper_summary.get("safety", {}) if isinstance(wrapper_summary.get("safety"), dict) else {}
        cycle_ok = bool(returncode == 0 and wrapper_summary.get("cycle_ok", False))
        if as_int(metrics.get("sender_order_send_called_count"), as_int(safety.get("sender_order_send_called_count"), 0)) != 0:
            cycle_ok = False
        if as_int(metrics.get("sender_sent_rows"), as_int(safety.get("sender_sent_rows"), 0)) != 0:
            cycle_ok = False
        if not cycle_ok:
            failed_cycles += 1

        next_run = ""
        if args.max_cycles == 0 or cycle_index < args.max_cycles:
            next_run = utc_text(next_aligned_time(utc_now(), args.interval_minutes, args.offset_seconds))

        row = {
            "cycle_index": cycle_index,
            "cycle_start_utc": cycle_start,
            "cycle_end_utc": cycle_end,
            "returncode": returncode,
            "cycle_ok": cycle_ok,
            "reason": wrapper_summary.get("reason", "WRAPPER_SUMMARY_MISSING_OR_FAILED"),
            "signals_found_count": as_int(metrics.get("signals_found_count"), 0),
            "open_order_intent_count": as_int(metrics.get("open_order_intent_count"), 0),
            "payload_rows_out": as_int(metrics.get("payload_rows_out"), 0),
            "sender_order_send_called_count": as_int(metrics.get("sender_order_send_called_count"), as_int(safety.get("sender_order_send_called_count"), 0)),
            "sender_sent_rows": as_int(metrics.get("sender_sent_rows"), as_int(safety.get("sender_sent_rows"), 0)),
            "next_run_utc": next_run,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "wrapper_summary_json": str(WRAPPER_SUMMARY_JSON),
        }
        append_csv_row(args.out_dir / "aligned_loop_log.csv", row, LOOP_LOG_COLUMNS)
        last_cycle_summary = row
        loop_summary = {
            "schema_version": "gold_multi_strategy_mochipoyo_loop_dry_run_aligned_v1",
            "started_at_utc": started_at,
            "updated_at_utc": utc_text(),
            "loop_ok": failed_cycles == 0,
            "reason": "GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_ALIGNED_PASS" if failed_cycles == 0 else "GOLD_MULTI_STRATEGY_MOCHIPOYO_LOOP_DRY_RUN_ALIGNED_HAS_FAILURES",
            "cycles_run": cycle_index,
            "failed_cycles": failed_cycles,
            "max_cycles": args.max_cycles,
            "interval_minutes": args.interval_minutes,
            "offset_seconds": args.offset_seconds,
            "safety": {
                "send_flag_passed_by_this_runner": False,
                "existing_mochipoyo_bat_modified_by_this_runner": False,
                "production_registry_mutated_by_this_runner": False,
            },
            "last_cycle": last_cycle_summary,
            "outputs": {
                "summary_json": str(args.out_dir / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json"),
                "aligned_loop_log_csv": str(args.out_dir / "aligned_loop_log.csv"),
            },
        }
        write_json(args.out_dir / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json", loop_summary)
        print("=" * 80, flush=True)
        print("aligned dry-run loop cycle summary", flush=True)
        print(json.dumps(loop_summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
        print("=" * 80, flush=True)

        if args.stop_on_error and not cycle_ok:
            print("[ERROR] stop_on_error=True and cycle failed; stopping", flush=True)
            break

    return 0 if failed_cycles == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
