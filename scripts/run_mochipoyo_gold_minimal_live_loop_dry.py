#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry loop wrapper for GOLD minimal live once.

This script is a safety-first scheduler wrapper around:

  scripts/run_mochipoyo_gold_minimal_live_once.py

It does NOT send Discord messages and does NOT auto-trade.
It repeatedly runs the validated one-shot flow with --discord-dry-run,
collects each iteration summary, and exits safely on Ctrl+C.

Default behavior is finite: --iterations 3.
Use --forever explicitly for continuous dry-run operation.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def read_summary(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, encoding="utf-8-sig")


def append_csv_row(row: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame([row])
    if p.exists():
        old = pd.read_csv(p, encoding="utf-8-sig")
        all_cols = list(dict.fromkeys(list(old.columns) + list(new.columns)))
        out = pd.concat([old.reindex(columns=all_cols), new.reindex(columns=all_cols)], ignore_index=True)
    else:
        out = new
    out.to_csv(p, index=False, encoding="utf-8-sig")


def add_optional(cmd: list[str], name: str, value: Any) -> None:
    if value is not None:
        cmd.extend([name, str(value)])


def add_flag(cmd: list[str], name: str, enabled: bool) -> None:
    if bool(enabled):
        cmd.append(name)


def build_once_command(args: argparse.Namespace, iteration: int, iteration_out_dir: Path, run_id: str) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/run_mochipoyo_gold_minimal_live_once.py",
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(iteration_out_dir),
        "--symbol", str(args.symbol),
        "--trigger-state-csv", str(args.trigger_state_csv),
        "--notification-ledger-csv", str(args.notification_ledger_csv),
        "--run-id", run_id,
        "--trigger-tail-bars", str(args.trigger_tail_bars),
        "--discord-max-rows", str(args.discord_max_rows),
        "--discord-style", str(args.discord_style),
        "--tail-m1", str(args.tail_m1),
        "--tail-m5", str(args.tail_m5),
        "--tail-m15", str(args.tail_m15),
        "--tail-h1", str(args.tail_h1),
        "--tail-h4", str(args.tail_h4),
        "--tail-d1", str(args.tail_d1),
        "--risk-rr", str(args.risk_rr),
        "--gold-min-stop-distance", str(args.gold_min_stop_distance),
        "--btc-min-stop-distance", str(args.btc_min_stop_distance),
        "--btc-point-size", str(args.btc_point_size),
        "--btc-spread-caution-threshold", str(args.btc_spread_caution_threshold),
        "--btc-max-spread-to-sl-ratio", str(args.btc_max_spread_to_sl_ratio),
        "--btc-min-effective-rr-after-spread", str(args.btc_min_effective_rr_after_spread),
    ]
    if args.csv_sep != "auto":
        cmd.extend(["--csv-sep", str(args.csv_sep)])
    add_flag(cmd, "--scan-on-initial-state", args.scan_on_initial_state)
    add_flag(cmd, "--commit-trigger-state", args.commit_trigger_state)
    add_flag(cmd, "--commit-ledger", args.commit_ledger)
    # This dry loop always runs the one-shot script in Discord dry-run mode.
    cmd.append("--discord-dry-run")
    add_flag(cmd, "--disable-trigger-window-filter", args.disable_trigger_window_filter)

    add_optional(cmd, "--gold-m1-csv", args.gold_m1_csv)
    add_optional(cmd, "--gold-m5-csv", args.gold_m5_csv)
    add_optional(cmd, "--gold-m15-csv", args.gold_m15_csv)
    add_optional(cmd, "--gold-h1-csv", args.gold_h1_csv)
    add_optional(cmd, "--gold-h4-csv", args.gold_h4_csv)
    add_optional(cmd, "--gold-d1-csv", args.gold_d1_csv)
    add_optional(cmd, "--btc-m1-csv", args.btc_m1_csv)
    add_optional(cmd, "--btc-m5-csv", args.btc_m5_csv)
    add_optional(cmd, "--btc-m15-csv", args.btc_m15_csv)
    add_optional(cmd, "--btc-h1-csv", args.btc_h1_csv)
    add_optional(cmd, "--btc-h4-csv", args.btc_h4_csv)
    return cmd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD minimal live once repeatedly in dry mode.")
    p.add_argument("--csv-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--trigger-state-csv", required=True)
    p.add_argument("--notification-ledger-csv", required=True)
    p.add_argument("--iterations", type=int, default=3, help="Finite dry-loop iterations. Ignored when --forever is used.")
    p.add_argument("--forever", action="store_true", help="Run until Ctrl+C. Explicit only.")
    p.add_argument("--sleep-seconds", type=float, default=10.0)
    p.add_argument("--stop-on-error", action="store_true", help="Stop loop if one-shot command returns non-zero.")
    p.add_argument("--commit-trigger-state", action="store_true")
    p.add_argument("--commit-ledger", action="store_true")
    p.add_argument("--scan-on-initial-state", action="store_true")
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--trigger-tail-bars", type=int, default=20)
    p.add_argument("--discord-max-rows", type=int, default=5)
    p.add_argument("--discord-style", choices=["compact", "detailed"], default="compact")
    p.add_argument("--disable-trigger-window-filter", action="store_true", help="Unsafe/debug only.")
    p.add_argument("--tail-m1", type=int, default=12000)
    p.add_argument("--tail-m5", type=int, default=6000)
    p.add_argument("--tail-m15", type=int, default=5000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=1500)
    p.add_argument("--tail-d1", type=int, default=800)
    p.add_argument("--risk-rr", type=float, default=1.2)
    p.add_argument("--gold-min-stop-distance", type=float, default=1.0)
    p.add_argument("--btc-min-stop-distance", type=float, default=50.0)
    p.add_argument("--btc-point-size", type=float, default=0.01)
    p.add_argument("--btc-spread-caution-threshold", type=float, default=0.07)
    p.add_argument("--btc-max-spread-to-sl-ratio", type=float, default=0.07)
    p.add_argument("--btc-min-effective-rr-after-spread", type=float, default=1.0)
    p.add_argument("--gold-m1-csv")
    p.add_argument("--gold-m5-csv")
    p.add_argument("--gold-m15-csv")
    p.add_argument("--gold-h1-csv")
    p.add_argument("--gold-h4-csv")
    p.add_argument("--gold-d1-csv")
    p.add_argument("--btc-m1-csv")
    p.add_argument("--btc-m5-csv")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    loop_summary_csv = out_dir / "gold_minimal_live_loop_dry_summary.csv"
    loop_events_csv = out_dir / "gold_minimal_live_loop_dry_events.csv"

    if args.forever:
        max_iterations: int | None = None
    else:
        max_iterations = max(0, int(args.iterations))

    print("run_mochipoyo_gold_minimal_live_loop_dry")
    print(f"out_dir: {out_dir}")
    print(f"iterations: {'forever' if max_iterations is None else max_iterations}")
    print(f"sleep_seconds: {args.sleep_seconds}")
    print("discord_send: disabled")
    print("auto_trade: disabled")

    iteration = 0
    exit_code = 0
    try:
        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            run_id = f"gold_minimal_live_loop_dry_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_i{iteration:04d}"
            iteration_dir = out_dir / f"iter_{iteration:04d}"
            cmd = build_once_command(args, iteration, iteration_dir, run_id)
            start = pd.Timestamp.now()
            proc = subprocess.run(cmd, text=True, capture_output=True)
            end = pd.Timestamp.now()
            duration_sec = (end - start).total_seconds()

            iteration_dir.mkdir(parents=True, exist_ok=True)
            (iteration_dir / "once_stdout.txt").write_text(proc.stdout, encoding="utf-8")
            (iteration_dir / "once_stderr.txt").write_text(proc.stderr, encoding="utf-8")
            (iteration_dir / "once_command.txt").write_text(" ".join(cmd), encoding="utf-8")

            once_summary_path = iteration_dir / "minimal_live_once_summary.csv"
            once_summary = read_summary(once_summary_path)
            if once_summary.empty:
                event = {
                    "loop_iteration": iteration,
                    "run_id": run_id,
                    "started_at": start.strftime("%Y-%m-%d %H:%M:%S"),
                    "finished_at": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_sec": duration_sec,
                    "returncode": int(proc.returncode),
                    "summary_status": "MISSING_ONCE_SUMMARY",
                    "success": False,
                }
            else:
                row = once_summary.iloc[0].to_dict()
                event = {
                    "loop_iteration": iteration,
                    "started_at": start.strftime("%Y-%m-%d %H:%M:%S"),
                    "finished_at": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_sec": duration_sec,
                    "returncode": int(proc.returncode),
                    "summary_status": "OK",
                    **row,
                }
            append_csv_row(event, loop_events_csv)
            append_csv_row(event, loop_summary_csv)

            printable = {k: event.get(k) for k in [
                "loop_iteration",
                "returncode",
                "pairs_to_scan",
                "notification_ok_live_rows",
                "notification_outside_trigger_window_rows",
                "ledger_new_candidates",
                "discord_status",
                "success",
            ] if k in event}
            print(pd.DataFrame([printable]).to_string(index=False))

            if proc.returncode != 0:
                exit_code = int(proc.returncode)
                if args.stop_on_error:
                    print("stop_on_error: stopping loop")
                    break

            if max_iterations is not None and iteration >= max_iterations:
                break
            time.sleep(max(0.0, float(args.sleep_seconds)))
    except KeyboardInterrupt:
        print("KeyboardInterrupt: stopping dry loop safely")
        exit_code = 130

    final = pd.DataFrame([
        {
            "finished_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iterations_completed": iteration,
            "exit_code": exit_code,
            "loop_summary_csv": str(loop_summary_csv),
            "loop_events_csv": str(loop_events_csv),
        }
    ])
    write_csv(final, out_dir / "gold_minimal_live_loop_dry_final.csv")
    print("done")
    print(f"loop_summary_csv: {loop_summary_csv}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
