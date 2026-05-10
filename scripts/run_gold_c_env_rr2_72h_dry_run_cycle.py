#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run one or more isolated dry-run cycles for GOLD C_ENV RR2 72h.

This script intentionally remains outside the existing Mochipoyo live/demo/autotrade
flow. It simply runs the two dedicated dry-run components in sequence:

1. scripts/run_gold_c_env_rr2_72h_live_scan_once.py
2. scripts/run_gold_c_env_rr2_72h_position_monitor_once.py

It does not send Discord messages, place MT5 orders, update Mochipoyo trigger
state, update Mochipoyo ledgers, or write existing autotrade order-intent files.

Runtime/lightweight option:
- --skip-monitor-when-no-open-signals skips the position monitor only when the
  strategy dry-run signal ledger has no DRY_RUN_SIGNAL_CREATED rows.
- This does not change signal detection logic.
- If a dry-run signal exists in the ledger, the monitor still runs.

Lot policy:
- BUY_C_ENV_RR2_72H is pinned to base_lot=0.01 by default.
- The cycle explicitly passes --base-lot to the live scan so order_intent_dry_run
  never emits lot=None on the guarded sender integration path.

Default behavior is a single cycle. For repeated dry-run operation, pass
--cycles and --sleep-seconds. Use --cycles 0 for an intentionally infinite local
loop.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/research_results/gold_c_env_rr2_72h_live_scan")
CONDITION_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H"
DEFAULT_BASE_LOT = 0.01

CYCLE_LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "condition_id",
    "cycle_index",
    "csv_dir",
    "out_dir",
    "live_scan_returncode",
    "position_monitor_returncode",
    "monitor_skipped",
    "monitor_skip_reason",
    "cycle_ok",
    "live_signal_found",
    "live_duplicate",
    "live_reason",
    "live_latest_m15_close_time",
    "live_candidate_count",
    "live_latest_candidate_entry_time",
    "monitor_signals_monitored",
    "monitor_close_intent_created",
    "monitor_reason",
    "monitor_open_unresolved",
    "monitor_tp_touched",
    "monitor_sl_touched",
    "monitor_time_exit_required",
    "monitor_no_m5_path",
    "live_seconds",
    "monitor_seconds",
    "total_seconds",
    "live_stdout_log",
    "live_stderr_log",
    "monitor_stdout_log",
    "monitor_stderr_log",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GOLD C_ENV RR2 72h dry-run live scan + position monitor cycle.")
    parser.add_argument("--csv-dir", type=Path, required=True, help="Directory containing goldsharp_h4/h1/m15/m5 CSVs.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cycles", type=int, default=1, help="Number of cycles. Use 0 for an intentionally infinite local loop.")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Sleep between cycles. Usually 900 for M15 operation.")
    parser.add_argument(
        "--latest-confirmed-policy",
        choices=["last", "second_last"],
        default="last",
        help="M15 confirmation policy passed to live scan.",
    )
    parser.add_argument(
        "--latest-confirmed-m5-policy",
        choices=["last", "second_last"],
        default="last",
        help="M5 confirmation policy passed to position monitor.",
    )
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--entry-window-hours", type=float, default=12.0)
    parser.add_argument("--breakout-lookback", type=int, default=8)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--max-hold-hours", type=int, default=72)
    parser.add_argument("--risk-mode", type=str, default="base_lot_0_01_dry_run")
    parser.add_argument("--base-lot", type=float, default=DEFAULT_BASE_LOT)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument(
        "--skip-monitor-when-no-open-signals",
        action="store_true",
        help="Skip position monitor when signal_ledger.csv has no DRY_RUN_SIGNAL_CREATED rows.",
    )
    parser.add_argument(
        "--continue-monitor-on-live-error",
        action="store_true",
        help="Run position monitor even if live scan exits non-zero. Default is to skip monitor on live scan failure.",
    )
    return parser.parse_args()


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


def ensure_parent_dir(path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def path_exists(path: Path) -> bool:
    return Path(windows_long_path(path)).exists()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path_exists(path):
        return {}
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def append_cycle_log(path: Path, row: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    df = pd.DataFrame([{col: row.get(col, "") for col in CYCLE_LOG_COLUMNS}])
    header = not path_exists(path)
    df.to_csv(windows_long_path(path), mode="a", header=header, index=False, encoding="utf-8-sig")


def run_command(label: str, command: list[str], log_dir: Path, cycle_index: int) -> tuple[int, Path, Path, float]:
    print(f"[INFO] running {label}")
    print("[CMD] " + " ".join(command))
    mkdir_path(log_dir)
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = round(time.perf_counter() - started, 3)

    stamp = utc_stamp()
    stdout_path = log_dir / f"cycle_{cycle_index:05d}_{stamp}_{label}_stdout.txt"
    stderr_path = log_dir / f"cycle_{cycle_index:05d}_{stamp}_{label}_stderr.txt"
    write_text(stdout_path, completed.stdout or "")
    write_text(stderr_path, completed.stderr or "")

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    print(f"[INFO] {label} returncode={completed.returncode} elapsed_seconds={elapsed}")
    return int(completed.returncode), stdout_path, stderr_path, elapsed


def has_monitorable_dry_run_signals(out_dir: Path) -> bool:
    ledger_path = out_dir / "signal_ledger.csv"
    if not path_exists(ledger_path):
        return False
    try:
        df = pd.read_csv(windows_long_path(ledger_path), encoding="utf-8-sig")
    except Exception:
        return True
    if df.empty or "status" not in df.columns:
        return False
    return bool(df["status"].astype(str).eq("DRY_RUN_SIGNAL_CREATED").any())


def build_live_scan_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_c_env_rr2_72h_live_scan_once.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(args.out_dir),
        "--pivot-left", str(args.pivot_left),
        "--pivot-right", str(args.pivot_right),
        "--entry-window-hours", str(args.entry_window_hours),
        "--breakout-lookback", str(args.breakout_lookback),
        "--sl-lookback-m15", str(args.sl_lookback_m15),
        "--sl-atr-buffer-mult", str(args.sl_atr_buffer_mult),
        "--rr", str(args.rr),
        "--max-hold-hours", str(args.max_hold_hours),
        "--risk-mode", str(args.risk_mode),
        "--base-lot", str(args.base_lot),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy),
    ]


def build_position_monitor_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_c_env_rr2_72h_position_monitor_once.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(args.out_dir),
        "--max-hold-hours", str(args.max_hold_hours),
        "--inbar-priority", str(args.inbar_priority),
        "--latest-confirmed-m5-policy", str(args.latest_confirmed_m5_policy),
    ]


def run_one_cycle(args: argparse.Namespace, cycle_index: int) -> dict[str, Any]:
    total_started = time.perf_counter()
    cycle_start = utc_now_text()
    mkdir_path(args.out_dir)
    log_dir = args.out_dir / "dry_run_cycle_command_logs"
    mkdir_path(log_dir)
    cycle_log_path = args.out_dir / "dry_run_cycle_log.csv"
    latest_cycle_result_path = args.out_dir / "latest_dry_run_cycle_result.json"

    live_returncode, live_stdout, live_stderr, live_seconds = run_command(
        "live_scan",
        build_live_scan_command(args),
        log_dir,
        cycle_index,
    )

    live_result = read_json_or_empty(args.out_dir / "latest_scan_result.json")
    monitor_returncode: int | str = "SKIPPED"
    monitor_stdout = Path("")
    monitor_stderr = Path("")
    monitor_seconds = 0.0
    monitor_skipped = False
    monitor_skip_reason = ""
    monitor_result: dict[str, Any] = {}

    should_run_monitor = live_returncode == 0 or args.continue_monitor_on_live_error
    if should_run_monitor and args.skip_monitor_when_no_open_signals and not has_monitorable_dry_run_signals(args.out_dir):
        should_run_monitor = False
        monitor_skipped = True
        monitor_returncode = "SKIPPED_NO_OPEN_SIGNALS"
        monitor_skip_reason = "MONITOR_SKIPPED_NO_DRY_RUN_SIGNAL_CREATED_ROWS"
        monitor_result = {
            "scan_time_utc": utc_now_text(),
            "condition_id": CONDITION_ID,
            "signals_monitored": 0,
            "close_intent_created": 0,
            "open_unresolved": 0,
            "tp_touched": 0,
            "sl_touched": 0,
            "time_exit_required": 0,
            "no_m5_path": 0,
            "reason": monitor_skip_reason,
        }
        write_json(args.out_dir / "latest_position_monitor_result.json", monitor_result)
        print(f"[INFO] {monitor_skip_reason}")

    if should_run_monitor:
        monitor_returncode, monitor_stdout, monitor_stderr, monitor_seconds = run_command(
            "position_monitor",
            build_position_monitor_command(args),
            log_dir,
            cycle_index,
        )
        monitor_result = read_json_or_empty(args.out_dir / "latest_position_monitor_result.json")
    elif not monitor_skipped and live_returncode != 0:
        print("[WARN] live scan failed; skipped position monitor. Use --continue-monitor-on-live-error to force monitor.")

    cycle_end = utc_now_text()
    cycle_ok = live_returncode == 0 and monitor_returncode in [0, "SKIPPED_NO_OPEN_SIGNALS"]
    total_seconds = round(time.perf_counter() - total_started, 3)

    row = {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_id": CONDITION_ID,
        "cycle_index": cycle_index,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "live_scan_returncode": live_returncode,
        "position_monitor_returncode": monitor_returncode,
        "monitor_skipped": bool(monitor_skipped),
        "monitor_skip_reason": monitor_skip_reason,
        "cycle_ok": bool(cycle_ok),
        "live_signal_found": live_result.get("signal_found", ""),
        "live_duplicate": live_result.get("duplicate", ""),
        "live_reason": live_result.get("reason", ""),
        "live_latest_m15_close_time": live_result.get("latest_m15_close_time", ""),
        "live_candidate_count": live_result.get("candidate_count", ""),
        "live_latest_candidate_entry_time": live_result.get("latest_candidate_entry_time", ""),
        "monitor_signals_monitored": monitor_result.get("signals_monitored", ""),
        "monitor_close_intent_created": monitor_result.get("close_intent_created", ""),
        "monitor_reason": monitor_result.get("reason", ""),
        "monitor_open_unresolved": monitor_result.get("open_unresolved", ""),
        "monitor_tp_touched": monitor_result.get("tp_touched", ""),
        "monitor_sl_touched": monitor_result.get("sl_touched", ""),
        "monitor_time_exit_required": monitor_result.get("time_exit_required", ""),
        "monitor_no_m5_path": monitor_result.get("no_m5_path", ""),
        "live_seconds": live_seconds,
        "monitor_seconds": monitor_seconds,
        "total_seconds": total_seconds,
        "live_stdout_log": str(live_stdout),
        "live_stderr_log": str(live_stderr),
        "monitor_stdout_log": str(monitor_stdout) if monitor_stdout else "",
        "monitor_stderr_log": str(monitor_stderr) if monitor_stderr else "",
    }
    append_cycle_log(cycle_log_path, row)

    latest_payload = {
        "schema_version": "gold_c_env_rr2_72h_dry_run_cycle_v3_base_lot",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_id": CONDITION_ID,
        "cycle_index": cycle_index,
        "cycle_ok": bool(cycle_ok),
        "live_scan_returncode": live_returncode,
        "position_monitor_returncode": monitor_returncode,
        "monitor_skipped": bool(monitor_skipped),
        "monitor_skip_reason": monitor_skip_reason,
        "timing": {
            "live_seconds": live_seconds,
            "monitor_seconds": monitor_seconds,
            "total_seconds": total_seconds,
        },
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "base_lot": float(args.base_lot),
        "live_scan_result": live_result,
        "position_monitor_result": monitor_result,
        "outputs": {
            "dry_run_cycle_log": str(cycle_log_path),
            "live_stdout_log": str(live_stdout),
            "live_stderr_log": str(live_stderr),
            "monitor_stdout_log": str(monitor_stdout) if monitor_stdout else "",
            "monitor_stderr_log": str(monitor_stderr) if monitor_stderr else "",
        },
    }
    write_json(latest_cycle_result_path, latest_payload)

    print("[INFO] dry-run cycle completed")
    print(json.dumps(latest_payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return latest_payload


def should_continue(args: argparse.Namespace, completed_cycles: int) -> bool:
    if args.cycles == 0:
        return True
    return completed_cycles < args.cycles


def main() -> int:
    args = parse_args()
    if args.cycles < 0:
        raise ValueError("--cycles must be >= 0. Use 0 for an intentionally infinite loop.")
    if args.sleep_seconds < 0:
        raise ValueError("--sleep-seconds must be >= 0")

    print(f"[INFO] condition_id={CONDITION_ID}")
    print(f"[INFO] repo_root={REPO_ROOT}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] cycles={'infinite' if args.cycles == 0 else args.cycles}")
    print(f"[INFO] sleep_seconds={args.sleep_seconds}")
    print(f"[INFO] base_lot={args.base_lot}")
    print(f"[INFO] skip_monitor_when_no_open_signals={args.skip_monitor_when_no_open_signals}")

    completed = 0
    last_ok = True
    while True:
        completed += 1
        result = run_one_cycle(args, completed)
        last_ok = bool(result.get("cycle_ok", False))

        if not should_continue(args, completed):
            break
        if args.sleep_seconds > 0:
            print(f"[INFO] sleeping {args.sleep_seconds} seconds before next cycle")
            time.sleep(args.sleep_seconds)

    return 0 if last_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
