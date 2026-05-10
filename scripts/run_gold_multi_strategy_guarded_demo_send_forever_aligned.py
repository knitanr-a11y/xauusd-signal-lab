#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Minute-aligned GOLD multi-strategy guarded demo-send loop.

This loop repeatedly calls:

    scripts/run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py

It is the send-capable aligned runner for the new GOLD multi-strategy sidecar
flow. It does not replace or mutate the existing Mochipoyo GOLD BAT.

Safety / integration policy:
- Default is NO SEND unless this runner receives both --allow-demo-send and --send.
- The child once wrapper still requires both --allow-demo-send and --send before
  it passes --send to send_mt5_order_from_payload.py.
- Existing Mochipoyo trigger-state / notification ledger are not mutated by this
  runner.
- Existing Mochipoyo GOLD demo autotrade BAT is not modified by this runner.
- Uses allow_any_until_max, not block_any, so separate GOLD signals are not
  blocked merely because another GOLD position exists.
- Duplicate protection remains order_key/order ledger based.
- Adapter lot is used by the child wrapper, so BUY=0.01, SELL B_ONLY=0.01,
  SELL CORE_AB=0.02.

Timing:
- Default cadence is every minute at second 02.
- Strategy evaluation is still latest confirmed M15; minute cadence only improves
  pickup timing after MT5 CSV export.

Stop:
- Ctrl+C exits gracefully without traceback.

Safe no-payload classification:
- Some child wrapper versions can return code 1 even when the state is a safe
  no-signal/no-payload cycle. This runner classifies such cycles as PASS only if
  payload_rows_out=0, no sender --send was passed, order_send_called_count=0,
  sent_rows=0, and the integration guards still show allow_any_until_max plus
  adapter lot. This prevents a harmless no-payload cycle from making the forever
  loop look failed while still preserving hard failures when order_send/sent rows
  appear or guard settings drift.
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
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_guarded_demo_send_forever_aligned")
SUMMARY_NAME = "latest_gold_multi_strategy_guarded_demo_send_forever_aligned_result.json"
STOP_MARKER_NAME = "latest_gold_multi_strategy_guarded_demo_send_forever_aligned_stop_marker.json"

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
    stamp = utc_stamp()
    rotated = path.with_name(f"{path.stem}.legacy_header_mismatch_{stamp}{path.suffix}")
    os.replace(windows_long_path(path), windows_long_path(rotated))
    return rotated


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    exists = Path(windows_long_path(path)).exists()
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


def is_safe_no_payload_cycle(*, returncode: int, child: dict[str, Any], metrics: dict[str, Any], guards: dict[str, Any], safety: dict[str, Any]) -> bool:
    """Classify harmless no-payload/no-send cycles as operationally OK."""
    payload_rows = as_int(metrics.get("payload_rows_out"), 0)
    order_send_called = as_int(metrics.get("guarded_sender_order_send_called_count"), 0)
    sent_rows = as_int(metrics.get("guarded_sender_sent_rows"), 0)
    sender_rows_out = as_int(metrics.get("guarded_sender_rows_out"), 0)
    send_passed = as_bool(child.get("send_flag_passed_to_sender"), False) or as_bool(safety.get("guarded_sender_send_flag_passed"), False)
    position_policy = str(guards.get("position_policy", ""))
    use_adapter_lot = as_bool(guards.get("use_adapter_lot"), False)
    suppressed = str(child.get("send_suppressed_reason", ""))
    return bool(
        payload_rows == 0
        and sender_rows_out == 0
        and order_send_called == 0
        and sent_rows == 0
        and not send_passed
        and position_policy == "allow_any_until_max"
        and use_adapter_lot
        and suppressed in {"SEND_NOT_REQUESTED", "NO_PAYLOAD_ROWS", "ALLOW_DEMO_SEND_NOT_SET"}
        and returncode in {0, 1}
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD multi-strategy guarded demo-send once wrapper on an aligned cadence.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
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
    cmd = [
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
    ]
    if args.allow_demo_send:
        cmd.append("--allow-demo-send")
    if args.send:
        cmd.append("--send")
    return cmd


def run_once(cycle_index: int, args: argparse.Namespace, cycle_dir: Path) -> tuple[int, Path, Path, float]:
    log_dir = args.out_dir / "command_logs"
    mkdir_path(log_dir)
    stdout_log = log_dir / f"cycle_{cycle_index:05d}_{utc_stamp()}_stdout.txt"
    stderr_log = log_dir / f"cycle_{cycle_index:05d}_{utc_stamp()}_stderr.txt"
    cmd = build_once_cmd(args, cycle_dir)
    print("=" * 80, flush=True)
    print(f"[CYCLE] {cycle_index} start_utc={utc_text()}", flush=True)
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
    print(f"[CYCLE] {cycle_index} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), stdout_log, stderr_log, elapsed


def build_loop_summary(args: argparse.Namespace, started_at: str, cycle_index: int, failed_cycles: int, last_cycle: dict[str, Any], stopped_by_user: bool) -> dict[str, Any]:
    loop_ok = failed_cycles == 0
    return {
        "schema_version": "gold_multi_strategy_guarded_demo_send_forever_aligned_v2_safe_no_payload_classification",
        "started_at_utc": started_at,
        "updated_at_utc": utc_text(),
        "loop_ok": loop_ok,
        "stopped_by_user": stopped_by_user,
        "reason": "GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_FOREVER_ALIGNED_STOPPED_BY_USER" if stopped_by_user else (
            "GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_FOREVER_ALIGNED_PASS" if loop_ok else "GOLD_MULTI_STRATEGY_GUARDED_DEMO_SEND_FOREVER_ALIGNED_HAS_FAILURES"
        ),
        "cycles_run": cycle_index,
        "failed_cycles": failed_cycles,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "safety": {
            "send_requires_allow_demo_send_and_send": True,
            "position_policy_block_any_used": str(args.position_policy) == "block_any",
            "existing_mochipoyo_bat_modified_by_this_runner": False,
            "existing_mochipoyo_ledgers_mutated_by_this_runner": False,
            "trigger_state_mutated_by_this_runner": False,
        },
        "last_cycle": last_cycle,
        "outputs": {
            "summary_json": str(args.out_dir / SUMMARY_NAME),
            "aligned_loop_log_csv": str(args.out_dir / "aligned_loop_log.csv"),
            "stop_marker_json": str(args.out_dir / STOP_MARKER_NAME),
        },
    }


def main() -> int:
    args = parse_args()
    if args.max_cycles < 0:
        raise ValueError("--max-cycles must be >= 0. Use 0 for infinite.")
    if args.interval_minutes <= 0:
        raise ValueError("--interval-minutes must be > 0")
    mkdir_path(args.out_dir)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy guarded demo-send FOREVER aligned runner", flush=True)
    print("Sender receives --send only when this runner AND child wrapper both have --allow-demo-send and --send.", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
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
            if cycle_index > 0 or not args.run_immediately:
                target = next_aligned_time(utc_now(), args.interval_minutes, args.offset_seconds)
                wait_seconds = max(0.0, (target - utc_now()).total_seconds())
                print(f"[INFO] next aligned run UTC={utc_text(target)} wait_seconds={wait_seconds:.1f}", flush=True)
                time.sleep(wait_seconds)

            cycle_index += 1
            cycle_start = utc_text()
            cycle_dir = args.out_dir / "cycles" / f"cycle_{cycle_index:05d}"
            returncode, stdout_log, stderr_log, elapsed = run_once(cycle_index, args, cycle_dir)
            cycle_end = utc_text()
            child_summary_path = cycle_dir / "latest_gold_multi_strategy_guarded_demo_send_once_result.json"
            child = read_json_or_empty(child_summary_path)
            metrics = child.get("key_metrics", {}) if isinstance(child.get("key_metrics"), dict) else {}
            guards = child.get("guards", {}) if isinstance(child.get("guards"), dict) else {}
            safety = child.get("safety", {}) if isinstance(child.get("safety"), dict) else {}
            natural_ok = bool(returncode == 0 and child.get("cycle_ok", False))
            safe_no_payload_ok = is_safe_no_payload_cycle(returncode=returncode, child=child, metrics=metrics, guards=guards, safety=safety)
            cycle_ok = bool(natural_ok or safe_no_payload_ok)
            cycle_ok_classification = "NATURAL_PASS" if natural_ok else ("SAFE_NO_PAYLOAD_PASS" if safe_no_payload_ok else "FAILED")
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
                "total_seconds": as_float(child.get("timing", {}).get("total_seconds") if isinstance(child.get("timing"), dict) else elapsed, elapsed),
                "next_run_utc": next_run,
                "stdout_log": str(stdout_log),
                "stderr_log": str(stderr_log),
                "summary_json": str(child_summary_path),
            }
            append_csv_row(args.out_dir / "aligned_loop_log.csv", row, LOOP_LOG_COLUMNS)
            last_cycle = row
            write_json(args.out_dir / SUMMARY_NAME, build_loop_summary(args, started_at, cycle_index, failed_cycles, last_cycle, stopped_by_user=False))

            compact = {
                "cycle_index": cycle_index,
                "cycle_ok": cycle_ok,
                "cycle_ok_classification": cycle_ok_classification,
                "reason": row["reason"],
                "allow_demo_send": row["allow_demo_send"],
                "send_requested": row["send_requested"],
                "send_flag_passed_to_sender": row["send_flag_passed_to_sender"],
                "send_suppressed_reason": row["send_suppressed_reason"],
                "payload_rows_out": row["payload_rows_out"],
                "order_send_called_count": row["guarded_sender_order_send_called_count"],
                "sent_rows": row["guarded_sender_sent_rows"],
                "position_policy": row["position_policy"],
                "use_adapter_lot": row["use_adapter_lot"],
                "next_run_utc": next_run,
                "stdout_log": str(stdout_log),
                "summary_json": str(args.out_dir / SUMMARY_NAME),
            }
            print("=" * 80, flush=True)
            print("guarded demo-send aligned loop compact cycle summary", flush=True)
            print(json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
            print("=" * 80, flush=True)

            if args.stop_on_error and not cycle_ok:
                print("[ERROR] stop_on_error=True and cycle failed; stopping", flush=True)
                break
    except KeyboardInterrupt:
        print("", flush=True)
        print("=" * 80, flush=True)
        print("[STOP] Ctrl+C received. GOLD guarded demo-send aligned loop stopped gracefully.", flush=True)
        if cycle_index == 0:
            marker = {
                "schema_version": "gold_multi_strategy_guarded_demo_send_forever_aligned_precycle_stop_marker_v1",
                "started_at_utc": started_at,
                "stopped_at_utc": utc_text(),
                "stopped_by_user": True,
                "reason": "STOPPED_BY_USER_BEFORE_FIRST_CYCLE",
                "cycles_run_this_session": 0,
                "safety": {
                    "send_requires_allow_demo_send_and_send": True,
                    "existing_mochipoyo_bat_modified_by_this_runner": False,
                },
            }
            write_json(args.out_dir / STOP_MARKER_NAME, marker)
        else:
            write_json(args.out_dir / SUMMARY_NAME, build_loop_summary(args, started_at, cycle_index, failed_cycles, last_cycle, stopped_by_user=True))
        print(f"cycles_run={cycle_index} failed_cycles={failed_cycles}", flush=True)
        print(f"summary_json={args.out_dir / SUMMARY_NAME}", flush=True)
        print("=" * 80, flush=True)
        return 0 if failed_cycles == 0 else 1

    return 0 if failed_cycles == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
