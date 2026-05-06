#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loop wrapper for GOLD minimal live once.

This script is a safety-first scheduler wrapper around:

  scripts/run_mochipoyo_gold_minimal_live_once.py

Default behavior is dry-run only:
- Discord messages are NOT sent unless --discord-send is explicitly passed.
- Auto-trading is never performed unless a future explicit live-send flag is added.
- Order payload generation is dry-run only and does NOT call MT5.
- Auto-trade dry-run can call MT5 order_check via send_mt5_order_from_payload.py,
  but DOES NOT call order_send.

It repeatedly runs the validated one-shot flow, collects each iteration summary,
and exits safely on Ctrl+C.

Default behavior is finite: --iterations 3.
Use --forever explicitly for continuous operation.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd


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


def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding=encoding, newline="") as f:
        f.write(text)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def read_summary(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return read_csv(p)


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(windows_long_path(p), "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def append_csv_row(row: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = pd.DataFrame([row])
    if p.exists():
        old = read_csv(p)
        all_cols = list(dict.fromkeys(list(old.columns) + list(new.columns)))
        out = pd.concat([old.reindex(columns=all_cols), new.reindex(columns=all_cols)], ignore_index=True)
    else:
        out = new
    write_csv(out, p)


def precreate_iteration_dirs(iteration_dir: Path) -> None:
    """Create output directories expected by the one-shot flow."""
    for name in ["scan", "notification", "ledger", "discord", "order", "auto_trade"]:
        (iteration_dir / name).mkdir(parents=True, exist_ok=True)


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

    if args.discord_send:
        cmd.append("--discord-send")
    else:
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


def run_order_payload_stage(args: argparse.Namespace, iteration_dir: Path) -> dict[str, Any]:
    """Generate dry-run order payloads from NEW notification rows.

    This never places orders. It only calls build_mochipoyo_order_payloads.py
    to create order/order_payloads.csv for inspection.
    """
    order_dir = iteration_dir / "order"
    order_dir.mkdir(parents=True, exist_ok=True)
    to_send_csv = iteration_dir / "ledger" / "notification_ledger_to_send.csv"
    stdout_path = order_dir / "order_payload_stdout.txt"
    stderr_path = order_dir / "order_payload_stderr.txt"
    output_csv = order_dir / "order_payloads.csv"
    output_json = order_dir / "order_payloads.json"

    base = {
        "order_payload_status": "SKIPPED",
        "order_payload_returncode": 0,
        "order_payload_rows": 0,
        "valid_order_payloads": 0,
        "invalid_order_payloads": 0,
    }
    if not args.enable_order_payload_dry_run:
        write_text(stdout_path, "SKIPPED_DISABLED\n")
        write_text(stderr_path, "")
        return {**base, "order_payload_status": "SKIPPED_DISABLED"}
    if not to_send_csv.exists():
        write_text(stdout_path, "SKIPPED_NO_TO_SEND_CSV\n")
        write_text(stderr_path, "")
        return {**base, "order_payload_status": "SKIPPED_NO_TO_SEND_CSV"}
    try:
        to_send = read_csv(to_send_csv)
    except Exception as e:
        write_text(stdout_path, "")
        write_text(stderr_path, repr(e) + "\n")
        return {**base, "order_payload_status": "ERROR_READ_TO_SEND", "order_payload_returncode": 1}
    if to_send.empty:
        write_text(stdout_path, "SKIPPED_NO_ROWS\n")
        write_text(stderr_path, "")
        return {**base, "order_payload_status": "SKIPPED_NO_ROWS"}

    cmd = [
        sys.executable,
        "scripts/build_mochipoyo_order_payloads.py",
        "--input-csv", str(to_send_csv),
        "--output-csv", str(output_csv),
        "--output-json", str(output_json),
        "--symbol", str(args.symbol),
        "--fixed-lot", str(args.order_fixed_lot),
        "--magic", str(args.order_magic),
        "--max-orders", str(args.order_max_rows),
    ]
    if args.order_broker_symbol:
        cmd.extend(["--broker-symbol", str(args.order_broker_symbol)])
    if args.order_ledger_csv:
        cmd.extend(["--order-ledger-csv", str(args.order_ledger_csv)])

    proc = subprocess.run(cmd, text=True, capture_output=True)
    write_text(stdout_path, proc.stdout)
    write_text(stderr_path, proc.stderr)
    write_text(order_dir / "order_payload_command.txt", " ".join(cmd))

    rows = 0
    valid = 0
    invalid = 0
    if output_csv.exists():
        try:
            out_df = read_csv(output_csv)
            rows = int(len(out_df))
            if "is_valid_order_payload" in out_df.columns:
                valid = int(out_df["is_valid_order_payload"].fillna(False).astype(bool).sum())
                invalid = int((~out_df["is_valid_order_payload"].fillna(False).astype(bool)).sum())
        except Exception:
            pass
    status = "OK" if proc.returncode == 0 else "ERROR"
    return {
        "order_payload_status": status,
        "order_payload_returncode": int(proc.returncode),
        "order_payload_rows": rows,
        "valid_order_payloads": valid,
        "invalid_order_payloads": invalid,
    }


def run_auto_trade_dry_run_stage(args: argparse.Namespace, iteration_dir: Path, order_event: dict[str, Any]) -> dict[str, Any]:
    """Run guarded MT5 auto-trade dry-run from generated order payloads.

    This calls scripts/send_mt5_order_from_payload.py WITHOUT --send. It can
    connect to MT5 and run order_check, but never calls order_send.

    Position-policy blocks are treated as safe dry-run skips when order_send was
    not called. That means an existing-position guard can intentionally block a
    candidate without failing the whole live notification loop.
    """
    auto_dir = iteration_dir / "auto_trade"
    auto_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = auto_dir / "auto_trade_stdout.txt"
    stderr_path = auto_dir / "auto_trade_stderr.txt"
    input_csv = iteration_dir / "order" / "order_payloads.csv"
    report_json = auto_dir / "mt5_order_send_report.json"

    base = {
        "auto_trade_status": "SKIPPED",
        "auto_trade_returncode": 0,
        "auto_trade_rows": 0,
        "auto_trade_dry_run_check_ok_rows": 0,
        "auto_trade_blocked_position_policy_rows": 0,
        "auto_trade_sent_rows": 0,
        "auto_trade_error_rows": 0,
        "auto_trade_order_send_called_count": 0,
    }
    if not args.enable_auto_trade_dry_run:
        write_text(stdout_path, "SKIPPED_DISABLED\n")
        write_text(stderr_path, "")
        return {**base, "auto_trade_status": "SKIPPED_DISABLED"}
    if int(order_event.get("order_payload_rows", 0) or 0) <= 0:
        write_text(stdout_path, "SKIPPED_NO_ORDER_PAYLOAD_ROWS\n")
        write_text(stderr_path, "")
        return {**base, "auto_trade_status": "SKIPPED_NO_ORDER_PAYLOAD_ROWS"}
    if not input_csv.exists():
        write_text(stdout_path, "SKIPPED_NO_ORDER_PAYLOAD_CSV\n")
        write_text(stderr_path, "")
        return {**base, "auto_trade_status": "SKIPPED_NO_ORDER_PAYLOAD_CSV"}
    if not args.auto_trade_order_ledger_csv:
        write_text(stdout_path, "")
        write_text(stderr_path, "ERROR: --auto-trade-order-ledger-csv is required when --enable-auto-trade-dry-run is used.\n")
        return {**base, "auto_trade_status": "ERROR_MISSING_ORDER_LEDGER", "auto_trade_returncode": 1}

    cmd = [
        sys.executable,
        "scripts/send_mt5_order_from_payload.py",
        "--input-csv", str(input_csv),
        "--order-ledger-csv", str(args.auto_trade_order_ledger_csv),
        "--out-dir", str(auto_dir),
        "--max-orders", str(args.auto_trade_max_orders),
        "--deviation", str(args.auto_trade_deviation),
        "--position-policy", str(args.auto_trade_position_policy),
        "--max-symbol-positions", str(args.auto_trade_max_symbol_positions),
        "--max-symbol-lot", str(args.auto_trade_max_symbol_lot),
    ]
    if args.auto_trade_broker_symbol:
        cmd.extend(["--symbol", str(args.auto_trade_broker_symbol)])
    if args.auto_trade_expected_login is not None:
        cmd.extend(["--expected-login", str(args.auto_trade_expected_login)])
    if args.auto_trade_select_symbol:
        cmd.append("--select-symbol")
    if args.auto_trade_require_demo_account:
        cmd.append("--require-demo-account")
    if args.auto_trade_terminal_path:
        cmd.extend(["--terminal-path", str(args.auto_trade_terminal_path)])
    if args.auto_trade_portable:
        cmd.append("--portable")

    # Deliberately no --send here. This stage is dry-run only.
    proc = subprocess.run(cmd, text=True, capture_output=True)
    write_text(stdout_path, proc.stdout)
    write_text(stderr_path, proc.stderr)
    write_text(auto_dir / "auto_trade_command.txt", " ".join(cmd))

    report = read_json(report_json)
    rows = int(report.get("rows_out", 0) or 0)
    dry_ok = int(report.get("dry_run_check_ok_rows", 0) or 0)
    blocked_policy = int(report.get("blocked_position_policy_rows", 0) or 0)
    sent = int(report.get("sent_rows", 0) or 0)
    errors = int(report.get("error_rows", 0) or 0)
    called = int(report.get("order_send_called_count", 0) or 0)

    if called > 0 or sent > 0:
        status = "ERROR_ORDER_SEND_WAS_CALLED_IN_DRY_RUN"
        normalized_returncode = 1
    elif proc.returncode == 0:
        status = "OK"
        normalized_returncode = 0
    elif blocked_policy > 0 and rows > 0:
        status = "OK_BLOCKED_POSITION_POLICY"
        normalized_returncode = 0
    else:
        status = "ERROR"
        normalized_returncode = int(proc.returncode)

    return {
        "auto_trade_status": status,
        "auto_trade_returncode": normalized_returncode,
        "auto_trade_raw_returncode": int(proc.returncode),
        "auto_trade_rows": rows,
        "auto_trade_dry_run_check_ok_rows": dry_ok,
        "auto_trade_blocked_position_policy_rows": blocked_policy,
        "auto_trade_sent_rows": sent,
        "auto_trade_error_rows": errors,
        "auto_trade_order_send_called_count": called,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD minimal live once repeatedly.")
    p.add_argument("--csv-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--trigger-state-csv", required=True)
    p.add_argument("--notification-ledger-csv", required=True)
    p.add_argument("--iterations", type=int, default=3, help="Finite loop iterations. Ignored when --forever is used.")
    p.add_argument("--forever", action="store_true", help="Run until Ctrl+C. Explicit only.")
    p.add_argument("--sleep-seconds", type=float, default=10.0)
    p.add_argument("--stop-on-error", action="store_true", help="Stop loop if one-shot command returns non-zero.")
    p.add_argument("--commit-trigger-state", action="store_true")
    p.add_argument("--commit-ledger", action="store_true")
    p.add_argument("--scan-on-initial-state", action="store_true")
    p.add_argument("--discord-send", action="store_true", help="Actually send NEW live-window rows to Discord. Without this, loop uses Discord dry-run.")
    p.add_argument("--enable-order-payload-dry-run", action="store_true", help="Generate order/order_payloads.csv from notification_ledger_to_send.csv. No MT5 connection and no order placement.")
    p.add_argument("--order-broker-symbol", default=None, help="Broker symbol for order payloads, e.g. GOLD, GOLD#, XAUUSD")
    p.add_argument("--order-fixed-lot", type=float, default=0.01)
    p.add_argument("--order-magic", type=int, default=26050601)
    p.add_argument("--order-max-rows", type=int, default=5)
    p.add_argument("--order-ledger-csv", default=None, help="Optional order ledger for duplicate order_key checks during payload build")

    p.add_argument("--enable-auto-trade-dry-run", action="store_true", help="Run MT5 guarded dry-run/order_check from generated order payloads. Never calls order_send.")
    p.add_argument("--auto-trade-broker-symbol", default=None, help="Broker symbol override for MT5 dry-run, e.g. GOLD#")
    p.add_argument("--auto-trade-order-ledger-csv", default=None, help="Order ledger used by MT5 sender duplicate guard")
    p.add_argument("--auto-trade-expected-login", type=int, default=None)
    p.add_argument("--auto-trade-select-symbol", action="store_true")
    p.add_argument("--auto-trade-require-demo-account", action="store_true")
    p.add_argument("--auto-trade-position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--auto-trade-max-symbol-positions", type=int, default=1)
    p.add_argument("--auto-trade-max-symbol-lot", type=float, default=0.01)
    p.add_argument("--auto-trade-max-orders", type=int, default=1)
    p.add_argument("--auto-trade-deviation", type=int, default=50)
    p.add_argument("--auto-trade-terminal-path", default=None)
    p.add_argument("--auto-trade-portable", action="store_true")

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
    mode = "live" if args.discord_send else "dry"
    loop_summary_csv = out_dir / f"gold_minimal_live_loop_{mode}_summary.csv"
    loop_events_csv = out_dir / f"gold_minimal_live_loop_{mode}_events.csv"

    if args.forever:
        max_iterations: int | None = None
    else:
        max_iterations = max(0, int(args.iterations))

    print("run_mochipoyo_gold_minimal_live_loop")
    print(f"out_dir: {out_dir}")
    print(f"mode: {mode}")
    print(f"iterations: {'forever' if max_iterations is None else max_iterations}")
    print(f"sleep_seconds: {args.sleep_seconds}")
    print(f"discord_send: {'enabled' if args.discord_send else 'disabled'}")
    print("auto_trade_live: disabled")
    print(f"order_payload_dry_run: {'enabled' if args.enable_order_payload_dry_run else 'disabled'}")
    print(f"auto_trade_dry_run: {'enabled' if args.enable_auto_trade_dry_run else 'disabled'}")
    if args.discord_send:
        print("WARNING: --discord-send is enabled. Only NEW live-window rows will be sent, and once flow prevents partial live sends.")
    if args.enable_order_payload_dry_run:
        print("ORDER DRY-RUN: order payload CSVs may be generated, but MT5 is not called by that stage and no orders are placed.")
    if args.enable_auto_trade_dry_run:
        print("AUTO-TRADE DRY-RUN: MT5 order_check may run, but order_send is not called.")

    iteration = 0
    exit_code = 0
    try:
        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            run_id = f"gold_minimal_live_loop_{mode}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_i{iteration:04d}"
            iteration_dir = out_dir / f"iter_{iteration:04d}"
            iteration_dir.mkdir(parents=True, exist_ok=True)
            precreate_iteration_dirs(iteration_dir)
            cmd = build_once_command(args, iteration, iteration_dir, run_id)
            start = pd.Timestamp.now()
            proc = subprocess.run(cmd, text=True, capture_output=True)
            end = pd.Timestamp.now()
            duration_sec = (end - start).total_seconds()

            write_text(iteration_dir / "once_stdout.txt", proc.stdout)
            write_text(iteration_dir / "once_stderr.txt", proc.stderr)
            write_text(iteration_dir / "once_command.txt", " ".join(cmd))

            order_event = run_order_payload_stage(args, iteration_dir)
            auto_trade_event = run_auto_trade_dry_run_stage(args, iteration_dir, order_event)

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
                    **order_event,
                    **auto_trade_event,
                }
            else:
                row = once_summary.iloc[0].to_dict()
                combined_success = (
                    bool(row.get("success", False))
                    and int(order_event.get("order_payload_returncode", 0)) == 0
                    and int(auto_trade_event.get("auto_trade_returncode", 0)) == 0
                    and int(auto_trade_event.get("auto_trade_order_send_called_count", 0)) == 0
                    and int(auto_trade_event.get("auto_trade_sent_rows", 0)) == 0
                )
                event = {
                    "loop_iteration": iteration,
                    "started_at": start.strftime("%Y-%m-%d %H:%M:%S"),
                    "finished_at": end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_sec": duration_sec,
                    "returncode": int(proc.returncode),
                    "summary_status": "OK",
                    **row,
                    **order_event,
                    **auto_trade_event,
                    "success": combined_success,
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
                "ledger_append_rows",
                "discord_send",
                "discord_status",
                "order_payload_status",
                "order_payload_rows",
                "valid_order_payloads",
                "auto_trade_status",
                "auto_trade_rows",
                "auto_trade_dry_run_check_ok_rows",
                "auto_trade_blocked_position_policy_rows",
                "auto_trade_order_send_called_count",
                "auto_trade_sent_rows",
                "success",
            ] if k in event}
            print(pd.DataFrame([printable]).to_string(index=False))

            has_error = (
                proc.returncode != 0
                or int(order_event.get("order_payload_returncode", 0)) != 0
                or int(auto_trade_event.get("auto_trade_returncode", 0)) != 0
                or int(auto_trade_event.get("auto_trade_order_send_called_count", 0)) != 0
                or int(auto_trade_event.get("auto_trade_sent_rows", 0)) != 0
            )
            if has_error:
                exit_code = int(proc.returncode) if proc.returncode != 0 else int(order_event.get("order_payload_returncode", 0) or auto_trade_event.get("auto_trade_returncode", 1))
                if exit_code == 0:
                    exit_code = 1
                if args.stop_on_error:
                    print("stop_on_error: stopping loop")
                    break

            if max_iterations is not None and iteration >= max_iterations:
                break
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
            "iterations_completed": iteration,
            "exit_code": exit_code,
            "loop_summary_csv": str(loop_summary_csv),
            "loop_events_csv": str(loop_events_csv),
        }
    ])
    write_csv(final, out_dir / f"gold_minimal_live_loop_{mode}_final.csv")
    print("done")
    print(f"loop_summary_csv: {loop_summary_csv}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
