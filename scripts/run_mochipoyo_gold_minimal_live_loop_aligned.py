#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aligned scheduler wrapper for GOLD minimal live loop.

This wrapper reuses the validated stages from
scripts/run_mochipoyo_gold_minimal_live_loop_dry.py, but starts each iteration
at a fixed second of every minute.

Safety rules:
- MT5 ExportOhlcToCsv writes confirmed CSVs at second 00.
- This wrapper can start Python reads at second 02.
- A lock file prevents two live loops from using the same out-dir.
- Auto-trade/order-payload stages are allowed only after the one-shot live flow
  succeeds. If the one-shot flow fails because of scan errors, Discord errors,
  partial-send protection, or a missing summary, order payload and MT5
  auto-trade are skipped.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_mochipoyo_gold_minimal_live_loop_dry as base  # noqa: E402


class LoopLock:
    """Small cross-process lock using O_EXCL file creation."""

    def __init__(self, path: Path, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self.fd: int | None = None

    def acquire(self) -> None:
        if not self.enabled:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise SystemExit(
                "ERROR: loop lock already exists. Another loop may be running.\n"
                f"lock_file: {self.path}\n"
                "If you confirmed no Python loop is running, delete this lock file and retry."
            ) from exc
        payload = (
            f"pid={os.getpid()}\n"
            f"created_at={pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        os.write(self.fd, payload.encode("utf-8"))

    def release(self) -> None:
        if not self.enabled:
            return
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def split_aligned_args(argv: list[str]) -> argparse.Namespace:
    """Parse only aligned-loop args, then delegate the rest to base.parse_args()."""
    align_parser = argparse.ArgumentParser(add_help=False)
    align_parser.add_argument(
        "--align-to-second",
        type=int,
        default=None,
        help="Start each iteration at this second of every minute, e.g. 2 means HH:MM:02.",
    )
    align_parser.add_argument(
        "--disable-loop-lock",
        action="store_true",
        help="Unsafe/debug only. Allow multiple loop processes to share the same out-dir.",
    )
    align_parser.add_argument(
        "--loop-lock-file",
        default=None,
        help="Optional explicit lock file path. Defaults to <out-dir>/gold_minimal_live_loop.lock.",
    )

    aligned_args, remaining = align_parser.parse_known_args(argv)
    old_argv = sys.argv[:]
    try:
        sys.argv = [old_argv[0]] + remaining
        args = base.parse_args()
    finally:
        sys.argv = old_argv

    args.align_to_second = aligned_args.align_to_second
    args.disable_loop_lock = bool(aligned_args.disable_loop_lock)
    args.loop_lock_file = aligned_args.loop_lock_file

    if args.align_to_second is not None and not (0 <= int(args.align_to_second) <= 59):
        raise SystemExit("ERROR: --align-to-second must be between 0 and 59.")
    return args


def seconds_until_next_aligned_second(target_second: int) -> float:
    now = pd.Timestamp.now()
    current = float(now.second) + float(now.microsecond) / 1_000_000.0
    target = float(target_second)
    wait = (target - current) % 60.0
    if wait < 0.005:
        return 0.0
    return wait


def sleep_before_iteration(args: argparse.Namespace) -> float:
    if args.align_to_second is None:
        return 0.0
    wait = seconds_until_next_aligned_second(int(args.align_to_second))
    if wait > 0:
        time.sleep(wait)
    return wait


def skipped_order_event(reason: str) -> dict[str, Any]:
    return {
        "order_payload_status": reason,
        "order_payload_returncode": 0,
        "order_payload_rows": 0,
        "valid_order_payloads": 0,
    }


def skipped_auto_trade_event(reason: str, send_enabled: bool) -> dict[str, Any]:
    return {
        "auto_trade_status": reason,
        "auto_trade_returncode": 0,
        "auto_trade_send_enabled": bool(send_enabled),
        "auto_trade_rows": 0,
        "auto_trade_dry_run_check_ok_rows": 0,
        "auto_trade_blocked_position_policy_rows": 0,
        "auto_trade_order_send_called_count": 0,
        "auto_trade_sent_rows": 0,
    }


def once_flow_succeeded(proc_returncode: int, once_row: dict[str, Any], once_summary_empty: bool) -> bool:
    if once_summary_empty:
        return False
    if int(proc_returncode) != 0:
        return False
    return bool(once_row.get("success", False))


def main() -> int:
    args = split_aligned_args(sys.argv[1:])
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lock_path = Path(args.loop_lock_file) if args.loop_lock_file else out_dir / "gold_minimal_live_loop.lock"
    lock = LoopLock(lock_path, enabled=not bool(args.disable_loop_lock))
    lock.acquire()

    mode = "live" if args.discord_send else "dry"
    loop_summary_csv = out_dir / f"gold_minimal_live_loop_{mode}_summary.csv"
    loop_events_csv = out_dir / f"gold_minimal_live_loop_{mode}_events.csv"

    max_iterations: int | None = None if args.forever else max(0, int(args.iterations))

    print("run_mochipoyo_gold_minimal_live_loop_aligned")
    print(f"out_dir: {out_dir}")
    print(f"mode: {mode}")
    print(f"iterations: {'forever' if max_iterations is None else max_iterations}")
    print(f"sleep_seconds: {args.sleep_seconds}")
    print(f"align_to_second: {args.align_to_second if args.align_to_second is not None else 'disabled'}")
    print(f"loop_lock: {'disabled' if args.disable_loop_lock else str(lock_path)}")
    print(f"discord_send: {'enabled' if args.discord_send else 'disabled'}")
    print(f"auto_trade_live: {'enabled' if args.enable_auto_trade_send else 'disabled'}")
    print(f"order_payload_dry_run: {'enabled' if args.enable_order_payload_dry_run else 'disabled'}")
    print(f"auto_trade_dry_run: {'enabled' if args.enable_auto_trade_dry_run else 'disabled'}")
    if args.align_to_second is not None:
        print("SCHEDULE: each iteration starts on the requested second; --sleep-seconds is only used when alignment is disabled.")
    if args.discord_send:
        print("WARNING: --discord-send is enabled. Only NEW live-window rows will be sent, and once flow prevents partial live sends.")
    if args.enable_order_payload_dry_run:
        print("ORDER DRY-RUN: order payload CSVs may be generated, but MT5 is not called by that stage and no orders are placed.")
    if args.enable_auto_trade_dry_run:
        print("AUTO-TRADE DRY-RUN: MT5 order_check may run, but order_send is not called.")
    if args.enable_auto_trade_send:
        print("WARNING: AUTO-TRADE SEND is enabled. MT5 order_send may be called only after once flow succeeds.")

    iteration = 0
    exit_code = 0
    try:
        try:
            while max_iterations is None or iteration < max_iterations:
                align_wait_sec = sleep_before_iteration(args)
                iteration += 1
                run_id = f"gold_minimal_live_loop_{mode}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_i{iteration:04d}"
                iteration_dir = out_dir / f"iter_{iteration:04d}"
                iteration_dir.mkdir(parents=True, exist_ok=True)
                base.precreate_iteration_dirs(iteration_dir)

                cmd = base.build_once_command(args, iteration, iteration_dir, run_id)
                start = pd.Timestamp.now()
                proc = base.subprocess.run(cmd, text=True, capture_output=True)
                end = pd.Timestamp.now()
                duration_sec = (end - start).total_seconds()

                base.write_text(iteration_dir / "once_stdout.txt", proc.stdout)
                base.write_text(iteration_dir / "once_stderr.txt", proc.stderr)
                base.write_text(iteration_dir / "once_command.txt", " ".join(cmd))

                once_summary_path = iteration_dir / "minimal_live_once_summary.csv"
                once_summary = base.read_summary(once_summary_path)
                once_row: dict[str, Any] = {}
                if not once_summary.empty:
                    once_row = once_summary.iloc[0].to_dict()

                once_ok = once_flow_succeeded(proc.returncode, once_row, once_summary.empty)
                if once_ok:
                    order_event = base.run_order_payload_stage(args, iteration_dir, once_row)
                    auto_trade_event = base.run_auto_trade_stage(args, iteration_dir, order_event)
                else:
                    reason = "SKIPPED_ONCE_FAILED"
                    order_event = skipped_order_event(reason)
                    auto_trade_event = skipped_auto_trade_event(reason, bool(args.enable_auto_trade_send))
                    print(
                        "SAFETY: once flow failed; skipped order payload and auto-trade. "
                        f"returncode={int(proc.returncode)}, once_success={bool(once_row.get('success', False))}, "
                        f"discord_status={once_row.get('discord_status', 'UNKNOWN')}"
                    )

                base_event = {
                    "loop_iteration": iteration,
                    "run_id": run_id,
                    "scheduled_align_second": args.align_to_second,
                    "align_wait_sec": align_wait_sec,
                    "started_at": start.strftime("%Y-%m-%d %H:%M:%S"),
                    "finished_at": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_sec": duration_sec,
                    "returncode": int(proc.returncode),
                }

                if once_summary.empty:
                    event = {
                        **base_event,
                        "summary_status": "MISSING_ONCE_SUMMARY",
                        **order_event,
                        **auto_trade_event,
                        "success": False,
                    }
                else:
                    combined_success = (
                        bool(once_row.get("success", False))
                        and int(proc.returncode) == 0
                        and int(order_event.get("order_payload_returncode", 0)) == 0
                        and int(auto_trade_event.get("auto_trade_returncode", 0)) == 0
                    )
                    if args.enable_auto_trade_dry_run:
                        combined_success = (
                            combined_success
                            and int(auto_trade_event.get("auto_trade_order_send_called_count", 0)) == 0
                            and int(auto_trade_event.get("auto_trade_sent_rows", 0)) == 0
                        )
                    event = {
                        **base_event,
                        "summary_status": "OK",
                        **once_row,
                        **order_event,
                        **auto_trade_event,
                        "success": combined_success,
                    }

                base.append_csv_row(event, loop_events_csv)
                base.append_csv_row(event, loop_summary_csv)

                printable = {k: event.get(k) for k in [
                    "loop_iteration",
                    "scheduled_align_second",
                    "align_wait_sec",
                    "started_at",
                    "returncode",
                    "pairs_to_scan",
                    "notification_ok_live_rows",
                    "notification_outside_trigger_window_rows",
                    "ledger_new_candidates",
                    "ledger_append_rows",
                    "discord_send",
                    "discord_status",
                    "order_payload_status",
                    "order_payload_rows",
                    "valid_order_payloads",
                    "auto_trade_status",
                    "auto_trade_send_enabled",
                    "auto_trade_rows",
                    "auto_trade_dry_run_check_ok_rows",
                    "auto_trade_blocked_position_policy_rows",
                    "auto_trade_order_send_called_count",
                    "auto_trade_sent_rows",
                    "success",
                ] if k in event}
                print(pd.DataFrame([printable]).to_string(index=False))

                has_error = (
                    int(proc.returncode) != 0
                    or int(order_event.get("order_payload_returncode", 0)) != 0
                    or int(auto_trade_event.get("auto_trade_returncode", 0)) != 0
                )
                if args.enable_auto_trade_dry_run:
                    has_error = (
                        has_error
                        or int(auto_trade_event.get("auto_trade_order_send_called_count", 0)) != 0
                        or int(auto_trade_event.get("auto_trade_sent_rows", 0)) != 0
                    )

                if has_error:
                    exit_code = int(proc.returncode) if int(proc.returncode) != 0 else int(
                        order_event.get("order_payload_returncode", 0)
                        or auto_trade_event.get("auto_trade_returncode", 1)
                    )
                    if exit_code == 0:
                        exit_code = 1
                    if args.stop_on_error:
                        print("stop_on_error: stopping loop")
                        break

                if max_iterations is not None and iteration >= max_iterations:
                    break
                if args.align_to_second is None:
                    time.sleep(max(0.0, float(args.sleep_seconds)))
        except KeyboardInterrupt:
            print("KeyboardInterrupt: stopping loop safely")
            exit_code = 130

        final = pd.DataFrame([
            {
                "finished_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mode": mode,
                "discord_send": bool(args.discord_send),
                "order_payload_dry_run": bool(args.enable_order_payload_dry_run),
                "auto_trade_dry_run": bool(args.enable_auto_trade_dry_run),
                "auto_trade_send": bool(args.enable_auto_trade_send),
                "align_to_second": args.align_to_second,
                "loop_lock_file": str(lock_path) if not args.disable_loop_lock else "disabled",
                "iterations_completed": iteration,
                "exit_code": exit_code,
                "loop_summary_csv": str(loop_summary_csv),
                "loop_events_csv": str(loop_events_csv),
            }
        ])
        base.write_csv(final, out_dir / f"gold_minimal_live_loop_{mode}_final.csv")
        print("done")
        print(f"loop_summary_csv: {loop_summary_csv}")
        return exit_code
    finally:
        lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
