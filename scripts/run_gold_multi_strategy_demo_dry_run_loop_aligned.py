#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Aligned loop wrapper for GOLD multi-strategy demo dry-run cycle.

This script repeatedly runs:

    scripts/run_gold_multi_strategy_demo_dry_run_cycle.py

Safety boundaries:
- The called cycle runner never passes --send.
- This wrapper does not send Discord messages.
- This wrapper does not modify existing Mochipoyo BAT/loop files.
- This wrapper uses a lock file by default to avoid double-running loops.

Example finite validation:

    python scripts\run_gold_multi_strategy_demo_dry_run_loop_aligned.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --iterations 2 ^
      --interval-seconds 0

Live-like aligned dry-run:

    python scripts\run_gold_multi_strategy_demo_dry_run_loop_aligned.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --iterations 0 ^
      --align-to-minute ^
      --align-to-second 2

Notes:
- --iterations 0 means run forever until Ctrl+C.
- For quick validation, use --interval-seconds 0 without --align-to-minute.
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

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_demo_dry_run_loop")
DEFAULT_CYCLE_OUT_DIR = Path("data/research_results/gold_multi_strategy_demo_dry_run_cycle")
DEFAULT_ROUTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_dry_run")
DEFAULT_BUY_OUT_DIR = Path("data/research_results/gold_c_env_rr2_72h_live_scan")
DEFAULT_SELL_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_live_loop")
DEFAULT_ADAPTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_autotrade_adapter_dry_run")
DEFAULT_PAYLOAD_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run")
DEFAULT_MT5_DRY_RUN_OUT_DIR = DEFAULT_PAYLOAD_OUT_DIR / "mt5_order_check_dry_run"
DEFAULT_ORDER_LEDGER_CSV = DEFAULT_PAYLOAD_OUT_DIR / "dry_run_order_ledger.csv"

LOOP_LOG_COLUMNS = [
    "loop_started_utc",
    "cycle_index",
    "cycle_start_utc",
    "cycle_end_utc",
    "cycle_returncode",
    "cycle_ok",
    "safe_no_send",
    "router_ok",
    "adapter_ok",
    "bridge_ok",
    "signals_found_count",
    "open_order_intent_count",
    "close_intent_count",
    "payload_rows_out",
    "mt5_order_send_called_count",
    "mt5_sent_rows",
    "mt5_blocked_position_policy_rows",
    "mt5_error_rows",
    "cycle_result_json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run aligned GOLD multi-strategy demo dry-run loop.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--cycle-out-dir", type=Path, default=DEFAULT_CYCLE_OUT_DIR)
    p.add_argument("--router-out-dir", type=Path, default=DEFAULT_ROUTER_OUT_DIR)
    p.add_argument("--buy-out-dir", type=Path, default=DEFAULT_BUY_OUT_DIR)
    p.add_argument("--sell-out-dir", type=Path, default=DEFAULT_SELL_OUT_DIR)
    p.add_argument("--adapter-out-dir", type=Path, default=DEFAULT_ADAPTER_OUT_DIR)
    p.add_argument("--payload-out-dir", type=Path, default=DEFAULT_PAYLOAD_OUT_DIR)
    p.add_argument("--mt5-dry-run-out-dir", type=Path, default=DEFAULT_MT5_DRY_RUN_OUT_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--broker-symbol", type=str, default="GOLD#")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--magic", type=int, default=26050601)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--iterations", type=int, default=1, help="Number of cycles. 0 means run forever until Ctrl+C.")
    p.add_argument("--interval-seconds", type=float, default=60.0)
    p.add_argument("--align-to-minute", action="store_true", help="Sleep to next minute boundary plus --align-to-second between cycles.")
    p.add_argument("--align-to-second", type=int, default=2)
    p.add_argument("--lock-file", type=Path, default=None)
    p.add_argument("--no-lock", action="store_true")
    p.add_argument("--continue-on-cycle-error", action="store_true")
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m5-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def default_lock_file(args: argparse.Namespace) -> Path:
    return args.out_dir / "gold_multi_strategy_demo_dry_run_loop.lock"


def acquire_lock(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        raise RuntimeError(f"Lock file already exists: {lock_path}. Delete it if no loop is running.")
    lock_payload = {
        "created_at_utc": utc_now_text(),
        "pid": os.getpid(),
        "script": Path(__file__).name,
    }
    lock_path.write_text(json.dumps(lock_payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def release_lock(lock_path: Path) -> None:
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception as exc:
        print(f"[WARN] failed to remove lock file {lock_path}: {exc}", flush=True)


def sleep_seconds_until_next_minute(align_to_second: int) -> float:
    now = datetime.now()
    target = now.replace(second=int(align_to_second), microsecond=0)
    if target <= now:
        target = target + timedelta(minutes=1)
    return max(0.0, (target - now).total_seconds())


def build_cycle_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_demo_dry_run_cycle.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(args.cycle_out_dir),
        "--router-out-dir", str(args.router_out_dir),
        "--buy-out-dir", str(args.buy_out_dir),
        "--sell-out-dir", str(args.sell_out_dir),
        "--adapter-out-dir", str(args.adapter_out_dir),
        "--payload-out-dir", str(args.payload_out_dir),
        "--mt5-dry-run-out-dir", str(args.mt5_dry_run_out_dir),
        "--order-ledger-csv", str(args.order_ledger_csv),
        "--broker-symbol", str(args.broker_symbol),
        "--fixed-lot", str(args.fixed_lot),
        "--magic", str(args.magic),
        "--expected-login", str(args.expected_login),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--max-orders", str(args.max_orders),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy),
        "--latest-confirmed-m5-policy", str(args.latest_confirmed_m5_policy),
        "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy),
    ]


def run_cycle(args: argparse.Namespace) -> int:
    cmd = build_cycle_cmd(args)
    print("[CMD] " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    return int(completed.returncode)


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def metric(result: dict[str, Any], name: str, default: Any = "") -> Any:
    km = result.get("key_metrics", {})
    if isinstance(km, dict) and name in km:
        return km.get(name, default)
    return default


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    loop_started = utc_now_text()
    lock_path = args.lock_file if args.lock_file is not None else default_lock_file(args)
    print(f"[INFO] loop_started_utc={loop_started}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] cycle_out_dir={args.cycle_out_dir}")
    print(f"[INFO] iterations={args.iterations}")
    print(f"[INFO] send mode disabled by cycle runner; wrapper never passes --send")

    if not args.no_lock:
        acquire_lock(lock_path)
        print(f"[INFO] acquired lock: {lock_path}")

    final_status = 0
    cycle_index = 0
    latest_loop_result_path = args.out_dir / "latest_multi_strategy_demo_dry_run_loop_result.json"
    loop_log_path = args.out_dir / "multi_strategy_demo_dry_run_loop_log.csv"

    try:
        while True:
            cycle_index += 1
            cycle_start = utc_now_text()
            print("=" * 80, flush=True)
            print(f"[INFO] loop cycle {cycle_index} start utc={cycle_start}", flush=True)
            rc = run_cycle(args)
            cycle_result_path = args.cycle_out_dir / "latest_multi_strategy_demo_dry_run_cycle_result.json"
            cycle_result = read_json_or_empty(cycle_result_path)
            cycle_end = utc_now_text()
            cycle_ok = boolish(cycle_result.get("cycle_ok", False)) and rc == 0
            row = {
                "loop_started_utc": loop_started,
                "cycle_index": cycle_index,
                "cycle_start_utc": cycle_start,
                "cycle_end_utc": cycle_end,
                "cycle_returncode": rc,
                "cycle_ok": cycle_ok,
                "safe_no_send": cycle_result.get("safe_no_send", ""),
                "router_ok": metric(cycle_result, "router_ok"),
                "adapter_ok": metric(cycle_result, "adapter_ok"),
                "bridge_ok": metric(cycle_result, "bridge_ok"),
                "signals_found_count": metric(cycle_result, "signals_found_count", 0),
                "open_order_intent_count": metric(cycle_result, "open_order_intent_count", 0),
                "close_intent_count": metric(cycle_result, "close_intent_count", 0),
                "payload_rows_out": metric(cycle_result, "payload_rows_out", 0),
                "mt5_order_send_called_count": metric(cycle_result, "mt5_order_send_called_count", 0),
                "mt5_sent_rows": metric(cycle_result, "mt5_sent_rows", 0),
                "mt5_blocked_position_policy_rows": metric(cycle_result, "mt5_blocked_position_policy_rows", 0),
                "mt5_error_rows": metric(cycle_result, "mt5_error_rows", 0),
                "cycle_result_json": str(cycle_result_path),
            }
            append_csv_row(loop_log_path, row, LOOP_LOG_COLUMNS)
            write_json(latest_loop_result_path, {
                "schema_version": "gold_multi_strategy_demo_dry_run_loop_v1",
                "loop_started_utc": loop_started,
                "latest_cycle_index": cycle_index,
                "latest_cycle_returncode": rc,
                "latest_cycle_ok": cycle_ok,
                "latest_cycle_result": cycle_result,
                "latest_loop_log_row": row,
                "outputs": {
                    "latest_loop_result": str(latest_loop_result_path),
                    "loop_log": str(loop_log_path),
                    "cycle_result": str(cycle_result_path),
                    "lock_file": str(lock_path) if not args.no_lock else "",
                },
            })
            print(f"[INFO] cycle_ok={cycle_ok} safe_no_send={row['safe_no_send']} payload_rows_out={row['payload_rows_out']} mt5_order_send_called_count={row['mt5_order_send_called_count']}", flush=True)
            if not cycle_ok:
                final_status = 1
                if not args.continue_on_cycle_error:
                    print("[ERROR] cycle failed; stopping loop because --continue-on-cycle-error was not provided", flush=True)
                    break
            if args.iterations > 0 and cycle_index >= args.iterations:
                print("[INFO] requested iterations completed", flush=True)
                break
            if args.align_to_minute:
                sleep_sec = sleep_seconds_until_next_minute(args.align_to_second)
            else:
                sleep_sec = max(0.0, float(args.interval_seconds))
            print(f"[INFO] sleeping {sleep_sec:.1f}s before next cycle", flush=True)
            time.sleep(sleep_sec)
    except KeyboardInterrupt:
        print("[INFO] interrupted by user", flush=True)
        final_status = 0
    finally:
        if not args.no_lock:
            release_lock(lock_path)
            print(f"[INFO] released lock: {lock_path}")

    return final_status


if __name__ == "__main__":
    raise SystemExit(main())
