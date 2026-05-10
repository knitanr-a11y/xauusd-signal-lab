#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run one or more isolated dry-run cycles for GOLD C_ENV RR2 72h.

This script intentionally remains outside the existing Mochipoyo live/demo/autotrade
flow. It simply runs the two dedicated dry-run components in sequence:

1. scripts/run_gold_c_env_rr2_72h_live_scan_once.py
2. scripts/run_gold_c_env_rr2_72h_position_monitor_once.py

It does not send Discord messages, place MT5 orders, update Mochipoyo trigger
state, update Mochipoyo ledgers, or write existing autotrade order-intent files.

Default behavior is a single cycle. For repeated dry-run operation, pass
--cycles and --sleep-seconds. Use --cycles 0 for an intentionally infinite local
loop.

Example single cycle:

    python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --out-dir data\research_results\gold_c_env_rr2_72h_live_scan

Example repeated cycle every 15 minutes:

    python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --out-dir data\research_results\gold_c_env_rr2_72h_live_scan ^
      --cycles 0 ^
      --sleep-seconds 900
"""

from __future__ import annotations

import argparse
import json
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

CYCLE_LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "condition_id",
    "cycle_index",
    "csv_dir",
    "out_dir",
    "live_scan_returncode",
    "position_monitor_returncode",
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
    parser.add_argument("--risk-mode", type=str, default="dry_run_no_lot")
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument(
        "--continue-monitor-on-live-error",
        action="store_true",
        help="Run position monitor even if live scan exits non-zero. Default is to skip monitor on live scan failure.",
    )
    return parser.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_cycle_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{col: row.get(col, "") for col in CYCLE_LOG_COLUMNS}])
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False, encoding="utf-8-sig")


def run_command(label: str, command: list[str], log_dir: Path, cycle_index: int) -> tuple[int, Path, Path]:
    print(f"[INFO] running {label}")
    print("[CMD] " + " ".join(command))
    log_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stamp = utc_stamp()
    stdout_path = log_dir / f"cycle_{cycle_index:05d}_{stamp}_{label}_stdout.txt"
    stderr_path = log_dir / f"cycle_{cycle_index:05d}_{stamp}_{label}_stderr.txt"
    write_text(stdout_path, completed.stdout or "")
    write_text(stderr_path, completed.stderr or "")

    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    print(f"[INFO] {label} returncode={completed.returncode}")
    return int(completed.returncode), stdout_path, stderr_path


def build_live_scan_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_c_env_rr2_72h_live_scan_once.py"),
        "--csv-dir",
        str(args.csv_dir),
        "--out-dir",
        str(args.out_dir),
        "--pivot-left",
        str(args.pivot_left),
        "--pivot-right",
        str(args.pivot_right),
        "--entry-window-hours",
        str(args.entry_window_hours),
        "--breakout-lookback",
        str(args.breakout_lookback),
        "--sl-lookback-m15",
        str(args.sl_lookback_m15),
        "--sl-atr-buffer-mult",
        str(args.sl_atr_buffer_mult),
        "--rr",
        str(args.rr),
        "--max-hold-hours",
        str(args.max_hold_hours),
        "--risk-mode",
        str(args.risk_mode),
        "--latest-confirmed-policy",
        str(args.latest_confirmed_policy),
    ]


def build_position_monitor_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_c_env_rr2_72h_position_monitor_once.py"),
        "--csv-dir",
        str(args.csv_dir),
        "--out-dir",
        str(args.out_dir),
        "--max-hold-hours",
        str(args.max_hold_hours),
        "--inbar-priority",
        str(args.inbar_priority),
        "--latest-confirmed-m5-policy",
        str(args.latest_confirmed_m5_policy),
    ]


def run_one_cycle(args: argparse.Namespace, cycle_index: int) -> dict[str, Any]:
    cycle_start = utc_now_text()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_dir = args.out_dir / "dry_run_cycle_command_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    cycle_log_path = args.out_dir / "dry_run_cycle_log.csv"
    latest_cycle_result_path = args.out_dir / "latest_dry_run_cycle_result.json"

    live_returncode, live_stdout, live_stderr = run_command(
        "live_scan",
        build_live_scan_command(args),
        log_dir,
        cycle_index,
    )

    monitor_returncode: int | str = "SKIPPED"
    monitor_stdout = Path("")
    monitor_stderr = Path("")

    if live_returncode == 0 or args.continue_monitor_on_live_error:
        monitor_returncode, monitor_stdout, monitor_stderr = run_command(
            "position_monitor",
            build_position_monitor_command(args),
            log_dir,
            cycle_index,
        )
    else:
        print("[WARN] live scan failed; skipped position monitor. Use --continue-monitor-on-live-error to force monitor.")

    live_result = read_json_or_empty(args.out_dir / "latest_scan_result.json")
    monitor_result = read_json_or_empty(args.out_dir / "latest_position_monitor_result.json")
    cycle_end = utc_now_text()
    cycle_ok = live_returncode == 0 and monitor_returncode == 0

    row = {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_id": CONDITION_ID,
        "cycle_index": cycle_index,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "live_scan_returncode": live_returncode,
        "position_monitor_returncode": monitor_returncode,
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
        "live_stdout_log": str(live_stdout),
        "live_stderr_log": str(live_stderr),
        "monitor_stdout_log": str(monitor_stdout) if monitor_stdout else "",
        "monitor_stderr_log": str(monitor_stderr) if monitor_stderr else "",
    }
    append_cycle_log(cycle_log_path, row)

    latest_payload = {
        "schema_version": "gold_c_env_rr2_72h_dry_run_cycle_v1",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_id": CONDITION_ID,
        "cycle_index": cycle_index,
        "cycle_ok": bool(cycle_ok),
        "live_scan_returncode": live_returncode,
        "position_monitor_returncode": monitor_returncode,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
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
    print(json.dumps(latest_payload, ensure_ascii=False, indent=2, sort_keys=True))
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
