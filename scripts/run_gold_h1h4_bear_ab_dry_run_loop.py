#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Isolated dry-run loop for GOLD H1/H4 bearish A/B classifier.

This runner repeatedly executes:

1. scripts/run_gold_h1h4_bear_ab_live_scan_once.py
2. scripts/run_gold_h1h4_bear_ab_position_monitor_once.py

It is intentionally isolated from Mochipoyo live/demo/autotrade and from the
BUY-side GOLD C_ENV candidate.

No Discord send.
No MT5 order placement.
No Mochipoyo trigger-state update.
No Mochipoyo ledger update.
No existing autotrade order-intent mutation.

Lot default:
- base_lot=0.01.
- CORE_AB_CONFIRM uses multiplier 2.0 => 0.02 lot.
- B_ONLY_SAFE uses multiplier 1.0 => 0.01 lot.

Runtime/lightweight option:
- --skip-monitor-when-no-open-signals skips the position monitor only when the
  strategy dry-run signal ledger has no DRY_RUN_SIGNAL_CREATED rows.
- This does not change signal detection logic.
- If a dry-run signal exists in the ledger, the monitor still runs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import CONDITION_FAMILY_ID  # noqa: E402

CYCLE_LOG_COLUMNS = [
    "cycle_index",
    "cycle_start_utc",
    "cycle_end_utc",
    "condition_family_id",
    "csv_dir",
    "out_dir",
    "live_scan_returncode",
    "position_monitor_returncode",
    "monitor_skipped",
    "monitor_skip_reason",
    "cycle_ok",
    "signal_found",
    "rank",
    "trade_enabled",
    "duplicate",
    "signal_key",
    "scan_reason",
    "signals_monitored",
    "resolved_skipped",
    "position_results_created",
    "tp_touched",
    "sl_touched",
    "time_exit_required",
    "time_exit_already_logged",
    "close_intent_created",
    "open_unresolved",
    "no_m1_path",
    "monitor_reason",
    "live_seconds",
    "monitor_seconds",
    "total_seconds",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run isolated SELL A/B dry-run loop.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_h1h4_bear_ab_live_loop"))
    p.add_argument("--iterations", type=int, default=1, help="Number of cycles. 0 means run forever until Ctrl+C.")
    p.add_argument("--interval-seconds", type=float, default=900.0, help="Sleep seconds between cycles when not aligned.")
    p.add_argument("--align-to-quarter-hour", action="store_true", help="Sleep until the next 00/15/30/45 minute boundary plus post-close delay.")
    p.add_argument("--post-close-delay-seconds", type=float, default=5.0)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--sl-usd", type=float, default=10.0)
    p.add_argument("--tp-usd", type=float, default=20.0)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=float, default=12.0)
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--core-lot-multiplier", type=float, default=2.0)
    p.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    p.add_argument("--max-lot-per-trade", type=float, default=99.0)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--observe-only-ledger", action="store_true")
    p.add_argument(
        "--skip-monitor-when-no-open-signals",
        action="store_true",
        help="Skip position monitor when signal_ledger.csv has no DRY_RUN_SIGNAL_CREATED rows.",
    )
    p.add_argument("--continue-on-error", action="store_true", help="Continue loop after a cycle error. Default stops on error.")
    return p.parse_args()


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


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path_exists(path):
        return {}
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        windows_long_path(path),
        mode="a",
        header=not path_exists(path),
        index=False,
        encoding="utf-8-sig",
    )


def seconds_until_next_quarter(post_close_delay_seconds: float) -> float:
    now = datetime.now()
    minute = now.minute
    next_q = ((minute // 15) + 1) * 15
    if next_q >= 60:
        base = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        base = now.replace(minute=next_q, second=0, microsecond=0)
    target = base + timedelta(seconds=float(post_close_delay_seconds))
    return max(0.0, (target - now).total_seconds())


def run_subprocess(label: str, cmd: list[str]) -> tuple[int, float]:
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[INFO] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


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


def build_live_scan_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_live_scan_once.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(args.out_dir),
        "--sl-usd", str(args.sl_usd),
        "--tp-usd", str(args.tp_usd),
        "--rr", str(args.rr),
        "--horizon-hours", str(args.horizon_hours),
        "--base-lot", str(args.base_lot),
        "--core-lot-multiplier", str(args.core_lot_multiplier),
        "--standard-lot-multiplier", str(args.standard_lot_multiplier),
        "--max-lot-per-trade", str(args.max_lot_per_trade),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy),
    ]
    if args.observe_only_ledger:
        cmd.append("--observe-only-ledger")
    return cmd


def build_monitor_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_position_monitor_once.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(args.out_dir),
        "--max-hold-hours", str(args.horizon_hours),
        "--inbar-priority", str(args.inbar_priority),
        "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy),
    ]


def run_cycle(args: argparse.Namespace, cycle_index: int) -> dict[str, Any]:
    total_started = time.perf_counter()
    cycle_start = utc_now_text()
    print("=" * 80, flush=True)
    print(f"[INFO] SELL A/B dry-run cycle start index={cycle_index} utc={cycle_start}", flush=True)

    live_rc, live_seconds = run_subprocess("live_scan", build_live_scan_cmd(args))
    scan_result = read_json_or_empty(args.out_dir / "latest_scan_result.json")

    monitor_skipped = False
    monitor_skip_reason = ""
    monitor_rc: int | str = -1
    monitor_seconds = 0.0
    monitor_result: dict[str, Any] = {}

    should_run_monitor = live_rc == 0
    if should_run_monitor and args.skip_monitor_when_no_open_signals and not has_monitorable_dry_run_signals(args.out_dir):
        should_run_monitor = False
        monitor_skipped = True
        monitor_rc = "SKIPPED_NO_OPEN_SIGNALS"
        monitor_skip_reason = "MONITOR_SKIPPED_NO_DRY_RUN_SIGNAL_CREATED_ROWS"
        monitor_result = {
            "scan_time_utc": utc_now_text(),
            "condition_family_id": CONDITION_FAMILY_ID,
            "signals_monitored": 0,
            "resolved_skipped": 0,
            "position_results_created": 0,
            "tp_touched": 0,
            "sl_touched": 0,
            "time_exit_required": 0,
            "time_exit_already_logged": 0,
            "close_intent_created": 0,
            "open_unresolved": 0,
            "no_m1_path": 0,
            "reason": monitor_skip_reason,
        }
        write_json(args.out_dir / "latest_position_monitor_result.json", monitor_result)
        print(f"[INFO] {monitor_skip_reason}", flush=True)

    if should_run_monitor:
        monitor_rc, monitor_seconds = run_subprocess("position_monitor", build_monitor_cmd(args))
        monitor_result = read_json_or_empty(args.out_dir / "latest_position_monitor_result.json")

    cycle_end = utc_now_text()
    cycle_ok = live_rc == 0 and monitor_rc in [0, "SKIPPED_NO_OPEN_SIGNALS"]
    total_seconds = round(time.perf_counter() - total_started, 3)

    row = {
        "cycle_index": cycle_index,
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_family_id": CONDITION_FAMILY_ID,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "live_scan_returncode": live_rc,
        "position_monitor_returncode": monitor_rc,
        "monitor_skipped": bool(monitor_skipped),
        "monitor_skip_reason": monitor_skip_reason,
        "cycle_ok": bool(cycle_ok),
        "signal_found": scan_result.get("signal_found", ""),
        "rank": scan_result.get("rank", ""),
        "trade_enabled": scan_result.get("trade_enabled", ""),
        "duplicate": scan_result.get("duplicate", ""),
        "signal_key": scan_result.get("signal_key", ""),
        "scan_reason": scan_result.get("reason", ""),
        "signals_monitored": monitor_result.get("signals_monitored", ""),
        "resolved_skipped": monitor_result.get("resolved_skipped", ""),
        "position_results_created": monitor_result.get("position_results_created", ""),
        "tp_touched": monitor_result.get("tp_touched", ""),
        "sl_touched": monitor_result.get("sl_touched", ""),
        "time_exit_required": monitor_result.get("time_exit_required", ""),
        "time_exit_already_logged": monitor_result.get("time_exit_already_logged", ""),
        "close_intent_created": monitor_result.get("close_intent_created", ""),
        "open_unresolved": monitor_result.get("open_unresolved", ""),
        "no_m1_path": monitor_result.get("no_m1_path", ""),
        "monitor_reason": monitor_result.get("reason", ""),
        "live_seconds": live_seconds,
        "monitor_seconds": monitor_seconds,
        "total_seconds": total_seconds,
    }

    append_csv_row(args.out_dir / "dry_run_loop_cycle_log.csv", row, CYCLE_LOG_COLUMNS)
    write_json(args.out_dir / "latest_dry_run_loop_cycle_result.json", {
        "schema_version": "gold_h1h4_bear_ab_dry_run_loop_cycle_v2",
        "cycle": row,
        "timing": {
            "live_seconds": live_seconds,
            "monitor_seconds": monitor_seconds,
            "total_seconds": total_seconds,
        },
        "latest_scan_result": scan_result,
        "latest_position_monitor_result": monitor_result,
    })
    print(f"[INFO] cycle_ok={cycle_ok} signal_found={row['signal_found']} rank={row['rank']} scan_reason={row['scan_reason']} monitor_reason={row['monitor_reason']} total_seconds={total_seconds}", flush=True)
    return row


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] iterations={args.iterations} align_to_quarter_hour={args.align_to_quarter_hour} interval_seconds={args.interval_seconds}")
    print(f"[INFO] skip_monitor_when_no_open_signals={args.skip_monitor_when_no_open_signals}")

    cycle_index = 0
    try:
        while True:
            cycle_index += 1
            row = run_cycle(args, cycle_index)
            if not bool(row["cycle_ok"]) and not args.continue_on_error:
                print("[ERROR] cycle failed; stopping because --continue-on-error was not provided", flush=True)
                return 1
            if args.iterations > 0 and cycle_index >= args.iterations:
                print("[INFO] requested iterations completed", flush=True)
                return 0
            if args.align_to_quarter_hour:
                sleep_sec = seconds_until_next_quarter(args.post_close_delay_seconds)
            else:
                sleep_sec = max(0.0, float(args.interval_seconds))
            print(f"[INFO] sleeping {sleep_sec:.1f}s before next cycle", flush=True)
            time.sleep(sleep_sec)
    except KeyboardInterrupt:
        print("[INFO] interrupted by user", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
