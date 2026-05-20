#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Official BTC strict-5 guarded demo autotrade connector.

Official default filter variant is buy_h4_context_conservative_v1.
Pass --filter-variant baseline only for research comparison.

This wrapper does not call mt5.order_send directly.  It builds payloads from the
shared official filtered runtime and calls send_mt5_order_from_payload.py.

Safety:
- no direct mt5.order_send in this wrapper
- sender --send is passed only when --send and --allow-demo-send are both set
- no Discord send
- no AI call
- no D1 read
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

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT / "scripts"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from btc_strict_5_filter_variants import BTC_STRICT_5_DEFAULT_FILTER_VARIANT, available_filter_variants
from btc_strict_5_official_runtime import build_context_from_csvs, build_filtered_preview
from btc_strict_5_signal_specs import DEFAULT_BROKER_SYMBOL, DEFAULT_SYMBOL, validate_signal_specs
from run_btc_strict_5_backtest_from_csv import DEFAULT_MQL5_FILES_DIR, choose_path, windows_long_path, write_csv, write_json
from run_btc_strict_5_guarded_demo_autotrade_from_csv import (
    DEFAULT_EXPECTED_LOGIN,
    DEFAULT_ORDER_LEDGER_CSV,
    PAYLOAD_COLUMNS,
    build_sender_cmd,
    payload_row,
    read_json_or_empty,
)

SCHEMA_VERSION = "btc_strict_5_official_guarded_demo_autotrade_v2_long_path_fix"


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def file_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    mkdirp(p.parent)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Official BTC strict 5 guarded demo autotrade connector.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=2000)
    p.add_argument("--tail-h4", type=int, default=1000)
    p.add_argument("--filter-variant", default=BTC_STRICT_5_DEFAULT_FILTER_VARIANT, choices=available_filter_variants())
    p.add_argument("--out-dir", type=Path, default=Path("data/runtime_logs/btc_strict_5_official_guarded_demo_autotrade"))
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--expected-login", type=int, default=DEFAULT_EXPECTED_LOGIN)
    p.add_argument("--scan-recent-bars", type=int, default=5)
    p.add_argument("--max-signal-age-minutes", type=int, default=30)
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--terminal-path", default="")
    p.add_argument("--portable", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--allow-no-signal-success", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    validate_signal_specs()
    out_dir = resolve_repo_path(args.out_dir)
    order_ledger_csv = resolve_repo_path(args.order_ledger_csv)
    run_dir = out_dir / file_stamp()
    sender_out_dir = run_dir / "sender"
    mkdirp(sender_out_dir)
    paths = {
        "m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file),
        "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file),
        "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file),
    }
    m15, _h1, _h4, ctx = build_context_from_csvs(
        m15_csv=paths["m15"], h1_csv=paths["h1"], h4_csv=paths["h4"],
        tail_m15=args.tail_m15, tail_h1=args.tail_h1, tail_h4=args.tail_h4,
    )
    preview, _raw, excluded, meta = build_filtered_preview(
        m15=m15,
        ctx=ctx,
        filter_variant=args.filter_variant,
        scan_recent_bars=args.scan_recent_bars,
        max_signal_age_minutes=args.max_signal_age_minutes,
        latest_only=args.latest_only,
        broker_symbol=args.broker_symbol,
        symbol=args.symbol,
    )
    if not preview.empty:
        preview = preview.sort_values(["signal_time", "strategy_id"]).reset_index(drop=True)
        if args.max_orders and int(args.max_orders) > 0:
            preview = preview.tail(int(args.max_orders)).copy()
    payloads = [payload_row(row, args, rank=i + 1) for i, (_, row) in enumerate(preview.iterrows())]
    for payload in payloads:
        payload["schema_version"] = SCHEMA_VERSION
        payload["source"] = "btc_strict_5_official_guarded_demo_autotrade_from_csv"
        payload["filter_variant"] = args.filter_variant
    payload_csv = run_dir / "btc_strict_5_official_order_payloads.csv"
    summary_json = run_dir / "btc_strict_5_official_guarded_demo_autotrade_summary.json"
    write_csv(pd.DataFrame(payloads, columns=PAYLOAD_COLUMNS + ["filter_variant"]), payload_csv)
    send_to_sender = bool(args.send and args.allow_demo_send)
    sender_report: dict[str, Any] = {}
    sender_returncode: int | None = None
    if not payloads:
        cycle_ok = bool(args.allow_no_signal_success)
        reason = "NO_RECENT_STRICT5_SIGNAL_AFTER_OFFICIAL_FILTER"
        sender_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0}
    else:
        cmd = build_sender_cmd(args, payload_csv, order_ledger_csv, sender_out_dir, send_to_sender)
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
        sender_returncode = int(proc.returncode)
        write_text(run_dir / "sender_stdout.log", proc.stdout or "")
        write_text(run_dir / "sender_stderr.log", proc.stderr or "")
        write_text(run_dir / "sender_command.txt", " ".join(cmd))
        sender_report = read_json_or_empty(sender_out_dir / "mt5_order_send_report.json")
        cycle_ok = sender_returncode == 0
        reason = "SENDER_OK" if cycle_ok else "SENDER_ERROR_OR_GUARD_BLOCK"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": bool(cycle_ok),
        "reason": reason,
        "filter_variant": args.filter_variant,
        "official_default_filter_variant": BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "is_official_default_variant": args.filter_variant == BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "send_requested_by_user": bool(args.send),
        "allow_demo_send": bool(args.allow_demo_send),
        "send_flag_passed_to_sender": bool(send_to_sender),
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "inputs": {k: str(v) for k, v in paths.items()},
        "run_dir": str(run_dir),
        "payload_csv": str(payload_csv),
        "order_ledger_csv": str(order_ledger_csv),
        "summary_json": str(summary_json),
        "filter_meta": meta,
        "signals_excluded_by_official_filter": int(len(excluded)),
        "payload_rows": int(len(payloads)),
        "sender_returncode": sender_returncode,
        "sender_rows_out": sender_report.get("rows_out", 0),
        "sender_dry_run_check_ok_rows": sender_report.get("dry_run_check_ok_rows", 0),
        "sender_sent_rows": sender_report.get("sent_rows", 0),
        "sender_error_rows": sender_report.get("error_rows", 0),
        "sender_order_send_called_count": sender_report.get("order_send_called_count", 0),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "safety": {
            "mt5_calls_direct_in_wrapper": False,
            "order_send_direct_in_wrapper": False,
            "discord_send": False,
            "ai_calls": False,
            "d1_read": False,
        },
    }
    write_json(summary_json, summary)
    write_json(out_dir / "latest_btc_strict_5_official_guarded_demo_autotrade_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
