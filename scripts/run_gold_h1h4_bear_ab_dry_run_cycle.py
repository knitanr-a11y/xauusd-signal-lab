#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run isolated dry-run cycles for GOLD bearish A/B classifier.

This script remains outside the existing Mochipoyo live/demo/autotrade flow and
outside the BUY-side C_ENV output directory.

It runs two dedicated SELL dry-run components in sequence:

1. scripts/run_gold_h1h4_bear_ab_live_scan_once.py
2. scripts/run_gold_h1h4_bear_ab_position_monitor_once.py

No Discord send.
No MT5 order placement.
No Mochipoyo trigger-state update.
No Mochipoyo ledger update.
No existing autotrade order-intent file update.

Default behavior is a single cycle. For repeated dry-run operation, pass
--cycles and --sleep-seconds. Use --cycles 0 for an intentionally infinite local
loop.
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
DEFAULT_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_live_scan")
CONDITION_FAMILY_ID = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"

CYCLE_LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "condition_family_id",
    "cycle_index",
    "csv_dir",
    "out_dir",
    "live_scan_returncode",
    "position_monitor_returncode",
    "cycle_ok",
    "live_signal_found",
    "live_rank",
    "live_a_pass",
    "live_b_pass",
    "live_trade_enabled",
    "live_duplicate",
    "live_reason",
    "live_latest_m15_close_time",
    "live_condition_id",
    "live_lot_multiplier",
    "live_effective_lot",
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
    parser = argparse.ArgumentParser(description="Run GOLD bearish A/B live scan + position monitor dry-run cycle.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cycles", type=int, default=1, help="Number of cycles. Use 0 for an intentionally infinite local loop.")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Sleep between cycles. Usually 900 for M15 operation.")
    parser.add_argument("--sl-usd", type=float, default=10.0)
    parser.add_argument("--tp-usd", type=float, default=20.0)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--horizon-hours", type=float, default=12.0)
    parser.add_argument("--base-lot", type=float, default=0.10)
    parser.add_argument("--core-lot-multiplier", type=float, default=2.0)
    parser.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    parser.add_argument("--max-lot-per-trade", type=float, default=99.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
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
    parser.add_argument(
        "--observe-only-ledger",
        action="store_true",
        help="Pass through to live scan. Normally leave off so A_ONLY is not ledgered.",
    )
    parser.add_argument(
        "--continue-monitor-on-live-error",
        action="store_true",
        help="Run monitor even if live scan exits non-zero. Default skips monitor on live scan failure.",
    )
    return parser.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def append_cycle_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in CYCLE_LOG_COLUMNS}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def run_command(label: str, command: list[str], log_dir: Path, cycle_index: int) -> tuple[int, Path, Path]:
    print(f"[INFO] running {label}")
    print("[CMD] " + " ".join(command))
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
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_live_scan_once.py"),
        "--csv-dir",
        str(args.csv_dir),
        "--out-dir",
        str(args.out_dir),
        "--sl-usd",
        str(args.sl_usd),
        "--tp-usd",
        str(args.tp_usd),
        "--rr",
        str(args.rr),
        "--horizon-hours",
        str(args.horizon_hours),
        "--base-lot",
        str(args.base_lot),
        "--core-lot-multiplier",
        str(args.core_lot_multiplier),
        "--standard-lot-multiplier",
        str(args.standard_lot_multiplier),
        "--max-lot-per-trade",
        str(args.max_lot_per_trade),
        "--latest-confirmed-policy",
        str(args.latest_confirmed_policy),
    ]
    if args.observe_only_ledger:
        cmd.append("--observe-only-ledger")
    return cmd


def build_position_monitor_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_position_monitor_once.py"),
        "--csv-dir",
        str(args.csv_dir),
        "--out-dir",
        str(args.out_dir),
        "--max-hold-hours",
        str(args.horizon_hours),
        "--inbar-priority",
        str(args.inbar_priority),
        "--latest-confirmed-m5-policy",
        str(args.latest_confirmed_m5_policy),
    ]


def run_one_cycle(args: argparse.Namespace, cycle_index: int) -> dict[str, Any]:
    cycle_start = utc_now_text()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_dir = args.out_dir / "dry_run_cycle_command_logs"
    cycle_log_path = args.out_dir / "dry_run_cycle_log.csv"
    latest_cycle_result_path = args.out_dir / "latest_dry_run_cycle_result.json"

    live_rc, live_stdout, live_stderr = run_command("live_scan", build_live_scan_command(args), log_dir, cycle_index)
    monitor_rc: int | str = "SKIPPED"
    monitor_stdout = Path("")
    monitor_stderr = Path("")
    if live_rc == 0 or args.continue_monitor_on_live_error:
        monitor_rc, monitor_stdout, monitor_stderr = run_command("position_monitor", build_position_monitor_command(args), log_dir, cycle_index)
    else:
        print("[WARN] live scan failed; skipped position monitor. Use --continue-monitor-on-live-error to force monitor.")

    live_result = read_json_or_empty(args.out_dir / "latest_scan_result.json")
    monitor_result = read_json_or_empty(args.out_dir / "latest_position_monitor_result.json")
    cycle_end = utc_now_text()
    cycle_ok = live_rc == 0 and monitor_rc == 0

    row = {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_family_id": CONDITION_FAMILY_ID,
        "cycle_index": cycle_index,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "live_scan_returncode": live_rc,
        "position_monitor_returncode": monitor_rc,
        "cycle_ok": bool(cycle_ok),
        "live_signal_found": live_result.get("signal_found", ""),
        "live_rank": live_result.get("rank", ""),
        "live_a_pass": live_result.get("a_pass", ""),
        "live_b_pass": live_result.get("b_pass", ""),
        "live_trade_enabled": live_result.get("trade_enabled", ""),
        "live_duplicate": live_result.get("duplicate", ""),
        "live_reason": live_result.get("reason", ""),
        "live_latest_m15_close_time": live_result.get("latest_m15_close_time", ""),
        "live_condition_id": live_result.get("condition_id", ""),
        "live_lot_multiplier": live_result.get("lot_multiplier", ""),
        "live_effective_lot": live_result.get("effective_lot", ""),
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

    payload = {
        "schema_version": "gold_h1h4_bear_ab_classifier_dry_run_cycle_v1",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_family_id": CONDITION_FAMILY_ID,
        "cycle_index": cycle_index,
        "cycle_ok": bool(cycle_ok),
        "live_scan_returncode": live_rc,
        "position_monitor_returncode": monitor_rc,
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
    write_json(latest_cycle_result_path, payload)
    print("[INFO] dry-run cycle completed")
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return payload


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

    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
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
