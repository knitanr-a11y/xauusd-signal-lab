#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Weekly-log GOLD multi-strategy guarded demo-send aligned loop with persistent state ledger.

This runner solves two operational needs at once:

1. Log growth control
   Operational logs are written to a date-partitioned folder:

     data/runtime_logs/gold/YYYY/MM/week_XX/multi_strategy_gold/loop

2. Duplicate-order safety across weekly log rotation
   The guarded sender order ledger is persisted under:

     data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv

   The child once-wrapper currently expects its guarded order ledger under its
   own out-dir. Therefore this runner synchronizes the persistent ledger into
   each per-cycle child out-dir before the child runs, and synchronizes it back
   after the child finishes.

Safety:
- Sender --send still requires both --allow-demo-send and --send.
- Uses allow_any_until_max, not block_any.
- Adapter lot is used by child once-wrapper.
- Existing Mochipoyo GOLD BAT/state/ledgers are not modified.
- Ctrl+C exits gracefully.

Important no-order behavior:
- If there are no payload rows, sender is not invoked and no child order ledger
  is produced. This is a normal waiting state, not a failure.
- This runner creates an empty persistent ledger at startup so the state folder is
  not empty and duplicate-key state has a stable file path before the first order.
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
DEFAULT_LOG_BASE = Path("data/runtime_logs/gold")
DEFAULT_STATE_DIR = Path("data/runtime_state/gold/multi_strategy")
SUMMARY_NAME = "latest_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_result.json"
STOP_MARKER_NAME = "latest_gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_stop_marker.json"
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
    "cycle_ok_classification",
    "reason",
    "allow_demo_send",
    "send_requested",
    "send_flag_passed_to_sender",
    "send_suppressed_reason",
    "payload_rows_out",
    "guarded_sender_rows_out",
    "guarded_sender_dry_run_check_ok_rows",
    "guarded_sender_error_rows",
    "guarded_sender_order_send_called_count",
    "guarded_sender_sent_rows",
    "position_policy",
    "max_symbol_positions",
    "max_symbol_lot",
    "use_adapter_lot",
    "persistent_order_ledger_csv",
    "child_order_ledger_csv",
    "ledger_synced_from_state",
    "ledger_synced_to_state",
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


def ensure_empty_csv(path: Path, columns: list[str]) -> bool:
    """Create an empty CSV with headers when it does not exist.

    Returns True when the file already existed or was created successfully.
    """
    if path_exists(path):
        return True
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(columns)
    return True


def rotate_legacy_csv(path: Path) -> Path:
    stamp = utc_stamp()
    rotated = path.with_name(f"{path.stem}.legacy_header_mismatch_{stamp}{path.suffix}")
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


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_text(dt: datetime | None = None) -> str:
    return (dt or utc_now()).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def local_week_parts(now: datetime | None = None) -> tuple[str, str, str]:
    # Use local clock for folder naming so it matches Windows operator expectation.
    d = datetime.now() if now is None else now.astimezone().replace(tzinfo=None)
    year, week, _weekday = d.isocalendar()
    return f"{year:04d}", f"{d.month:02d}", f"week_{week:02d}"


def weekly_out_dir(log_base: Path) -> Path:
    y, m, w = local_week_parts()
    return log_base / y / m / w / "multi_strategy_gold" / "loop"


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
    p = argparse.ArgumentParser(description="Run GOLD multi-strategy guarded demo-send loop with weekly logs and persistent state ledger.")
    p.add_argument("--log-base", type=Path, default=DEFAULT_LOG_BASE)
    p.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    p.add_argument("--max-cycles", type=int, default=0, help="Number of cycles. 0 means infinite.")
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--offset-seconds", type=int, default=2)
    p.add_argument("--run-immediately", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--stop-on-error", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--echo-wrapper-output", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--csv-dir", type=Path, default=Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"))
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=50)
    return p.parse_args()


def build_once_cmd(args: argparse.Namespace, cycle_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(cycle_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--expected-login", str(args.expected_login),
        "--require-demo-account",
        "--fixed-lot", "0.01",
        "--magic", "26050601",
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
    ] + (["--allow-demo-send"] if args.allow_demo_send else []) + (["--send"] if args.send else [])


def run_once(cycle_index: int, args: argparse.Namespace, out_dir: Path, persistent_ledger: Path) -> tuple[int, Path, Path, float, bool, bool, Path, Path]:
    ensure_empty_csv(persistent_ledger, ORDER_LEDGER_COLUMNS)
    cycle_dir = out_dir / "cycles" / f"cycle_{cycle_index:05d}"
    child_ledger = cycle_dir / "guarded_demo_order_ledger.csv"
    synced_from_state = safe_copy(persistent_ledger, child_ledger)

    log_dir = out_dir / "command_logs"
    mkdir_path(log_dir)
    stdout_log = log_dir / f"cycle_{cycle_index:05d}_{utc_stamp()}_stdout.txt"
    stderr_log = log_dir / f"cycle_{cycle_index:05d}_{utc_stamp()}_stderr.txt"
    cmd = build_once_cmd(args, cycle_dir)
    print("=" * 80, flush=True)
    print(f"[CYCLE] {cycle_index} start_utc={utc_text()}", flush=True)
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
    if not synced_to_state and path_exists(persistent_ledger):
        # No-payload cycles do not create a child ledger. Keeping the existing
        # persistent empty ledger is a successful no-op sync.
        synced_to_state = True
    print(f"[CYCLE] {cycle_index} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), stdout_log, stderr_log, elapsed, synced_from_state, synced_to_state, cycle_dir, child_ledger


def build_loop_summary(args: argparse.Namespace, started_at: str, cycle_index: int, failed_cycles: int, last_cycle: dict[str, Any], out_dir: Path, persistent_ledger: Path, stopped_by_user: bool) -> dict[str, Any]:
    loop_ok = failed_cycles == 0
    return {
        "schema_version": "gold_multi_strategy_guarded_demo_send_forever_aligned_weekly_state_v2_initialized_ledger",
        "started_at_utc": started_at,
        "updated_at_utc": utc_text(),
        "loop_ok": loop_ok,
        "stopped_by_user": stopped_by_user,
        "reason": "GOLD_MULTI_STRATEGY_WEEKLY_STATE_STOPPED_BY_USER" if stopped_by_user else (
            "GOLD_MULTI_STRATEGY_WEEKLY_STATE_PASS" if loop_ok else "GOLD_MULTI_STRATEGY_WEEKLY_STATE_HAS_FAILURES"
        ),
        "cycles_run": cycle_index,
        "failed_cycles": failed_cycles,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "persistent_order_ledger_csv": str(persistent_ledger),
        "weekly_out_dir": str(out_dir),
        "safety": {
            "send_requires_allow_demo_send_and_send": True,
            "position_policy_block_any_used": str(args.position_policy) == "block_any",
            "existing_mochipoyo_bat_modified_by_this_runner": False,
            "existing_mochipoyo_ledgers_mutated_by_this_runner": False,
            "trigger_state_mutated_by_this_runner": False,
        },
        "last_cycle": last_cycle,
        "outputs": {
            "summary_json": str(out_dir / SUMMARY_NAME),
            "aligned_loop_log_csv": str(out_dir / "aligned_loop_log.csv"),
            "stop_marker_json": str(out_dir / STOP_MARKER_NAME),
        },
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
    mkdir_path(out_dir)
    mkdir_path(state_dir)
    ensure_empty_csv(persistent_ledger, ORDER_LEDGER_COLUMNS)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy guarded demo-send WEEKLY-LOG / PERSISTENT-STATE runner", flush=True)
    print(f"weekly_out_dir={out_dir}", flush=True)
    print(f"persistent_order_ledger_csv={persistent_ledger}", flush=True)
    print(f"allow_demo_send={args.allow_demo_send} send_requested={args.send}", flush=True)
    print(f"position_policy={args.position_policy} max_symbol_positions={args.max_symbol_positions} max_symbol_lot={args.max_symbol_lot}", flush=True)
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
            returncode, stdout_log, stderr_log, elapsed, synced_from, synced_to, cycle_dir, child_ledger = run_once(cycle_index, args, out_dir, persistent_ledger)
            cycle_end = utc_text()
            child_summary_path = cycle_dir / "latest_gold_multi_strategy_guarded_demo_send_once_result.json"
            child = read_json_or_empty(child_summary_path)
            metrics = child.get("key_metrics", {}) if isinstance(child.get("key_metrics"), dict) else {}
            guards = child.get("guards", {}) if isinstance(child.get("guards"), dict) else {}
            cycle_ok = bool(returncode == 0 and child.get("cycle_ok", False) and synced_to)
            cycle_ok_classification = str(child.get("cycle_ok_classification", "NATURAL_PASS" if cycle_ok else "FAILED"))
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
                "cycle_ok_classification": cycle_ok_classification,
                "reason": child.get("reason", "CHILD_SUMMARY_MISSING_OR_FAILED"),
                "allow_demo_send": bool(args.allow_demo_send),
                "send_requested": bool(args.send),
                "send_flag_passed_to_sender": as_bool(child.get("send_flag_passed_to_sender"), False),
                "send_suppressed_reason": child.get("send_suppressed_reason", ""),
                "payload_rows_out": as_int(metrics.get("payload_rows_out"), 0),
                "guarded_sender_rows_out": as_int(metrics.get("guarded_sender_rows_out"), 0),
                "guarded_sender_dry_run_check_ok_rows": as_int(metrics.get("guarded_sender_dry_run_check_ok_rows"), 0),
                "guarded_sender_error_rows": as_int(metrics.get("guarded_sender_error_rows"), 0),
                "guarded_sender_order_send_called_count": as_int(metrics.get("guarded_sender_order_send_called_count"), 0),
                "guarded_sender_sent_rows": as_int(metrics.get("guarded_sender_sent_rows"), 0),
                "position_policy": guards.get("position_policy", args.position_policy),
                "max_symbol_positions": guards.get("max_symbol_positions", args.max_symbol_positions),
                "max_symbol_lot": guards.get("max_symbol_lot", args.max_symbol_lot),
                "use_adapter_lot": guards.get("use_adapter_lot", True),
                "persistent_order_ledger_csv": str(persistent_ledger),
                "child_order_ledger_csv": str(child_ledger),
                "ledger_synced_from_state": bool(synced_from),
                "ledger_synced_to_state": bool(synced_to),
                "total_seconds": as_float(child.get("timing", {}).get("total_seconds") if isinstance(child.get("timing"), dict) else elapsed, elapsed),
                "next_run_utc": next_run,
                "stdout_log": str(stdout_log),
                "stderr_log": str(stderr_log),
                "summary_json": str(child_summary_path),
            }
            append_csv_row(out_dir / "aligned_loop_log.csv", row, LOOP_LOG_COLUMNS)
            last_cycle = row
            write_json(out_dir / SUMMARY_NAME, build_loop_summary(args, started_at, cycle_index, failed_cycles, last_cycle, out_dir, persistent_ledger, stopped_by_user=False))

            compact = {
                "cycle_index": cycle_index,
                "cycle_ok": cycle_ok,
                "cycle_ok_classification": cycle_ok_classification,
                "reason": row["reason"],
                "payload_rows_out": row["payload_rows_out"],
                "order_send_called_count": row["guarded_sender_order_send_called_count"],
                "sent_rows": row["guarded_sender_sent_rows"],
                "ledger_synced_from_state": row["ledger_synced_from_state"],
                "ledger_synced_to_state": row["ledger_synced_to_state"],
                "persistent_order_ledger_csv": str(persistent_ledger),
                "weekly_out_dir": str(out_dir),
                "next_run_utc": next_run,
            }
            print("=" * 80, flush=True)
            print("weekly-state guarded loop compact cycle summary", flush=True)
            print(json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
            print("=" * 80, flush=True)

            if args.stop_on_error and not cycle_ok:
                print("[ERROR] stop_on_error=True and cycle failed; stopping", flush=True)
                break
    except KeyboardInterrupt:
        print("", flush=True)
        print("=" * 80, flush=True)
        print("[STOP] Ctrl+C received. GOLD weekly-state guarded loop stopped gracefully.", flush=True)
        if cycle_index == 0:
            marker = {
                "schema_version": "gold_multi_strategy_weekly_state_precycle_stop_marker_v1",
                "started_at_utc": started_at,
                "stopped_at_utc": utc_text(),
                "stopped_by_user": True,
                "reason": "STOPPED_BY_USER_BEFORE_FIRST_CYCLE",
                "cycles_run_this_session": 0,
            }
            write_json(out_dir / STOP_MARKER_NAME, marker)
        else:
            write_json(out_dir / SUMMARY_NAME, build_loop_summary(args, started_at, cycle_index, failed_cycles, last_cycle, out_dir, persistent_ledger, stopped_by_user=True))
        print(f"cycles_run={cycle_index} failed_cycles={failed_cycles}", flush=True)
        print(f"summary_json={out_dir / SUMMARY_NAME}", flush=True)
        print("=" * 80, flush=True)
        return 0 if failed_cycles == 0 else 1

    return 0 if failed_cycles == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
