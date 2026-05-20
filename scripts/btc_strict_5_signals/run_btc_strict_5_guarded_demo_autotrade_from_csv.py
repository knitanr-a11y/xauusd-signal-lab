#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build BTC strict-5 order payloads and call the existing guarded MT5 sender.

This is the guarded demo connector layer for BTC strict 5.

It intentionally reuses:

    scripts/send_mt5_order_from_payload.py

Safety defaults:
- dry-run/order_check only unless BOTH --send and --allow-demo-send are passed
- max-orders=1
- lot=0.01
- position-policy=block_any
- require-demo-account is passed to the sender by default
- expected-login defaults to the known demo account 75539039
- no Discord send
- no AI call
- no direct mt5.order_send in this wrapper
- duplicate order_key prevention is handled by sender order ledger
- no D1 read or D1 condition

The wrapper only:
1. Reads BTC live CSVs.
2. Detects recent BTC strict-5 signals using the same detector as backtest/preview.
3. Builds order_payloads.csv in the existing sender-compatible schema.
4. Calls send_mt5_order_from_payload.py.
5. Writes a summary JSON.

Important execution note:
The backtest enters at the next M15 open. In live operation, actual execution is
current MT5 bid/ask when the sender runs. Therefore this wrapper uses the latest
available preview entry reference to build a candidate SL/TP, but the sender still
performs broker-side order_check before any send. Keep max_signal_age_minutes
small for live/demo operation.
"""
from __future__ import annotations

import argparse
import csv
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
SCRIPTS_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for path in [SCRIPT_DIR, SCRIPTS_DIR, REPO_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from btc_strict_5_signal_specs import (  # noqa: E402
    DEFAULT_BROKER_SYMBOL,
    DEFAULT_MAGIC_BASE,
    DEFAULT_SYMBOL,
    get_signal_specs,
    validate_signal_specs,
)
from run_btc_strict_5_backtest_from_csv import (  # noqa: E402
    DEFAULT_MQL5_FILES_DIR,
    add_indicators,
    choose_path,
    detect_signals,
    join_confirmed_context,
    read_ohlc_csv,
    time_text,
    windows_long_path,
)
from run_btc_strict_5_preview_from_csv import build_m15_next_open_lookup, build_preview_rows  # noqa: E402

SENDER_SCRIPT = REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"
DEFAULT_OUT_DIR = Path("data/runtime_logs/btc_strict_5_guarded_demo_autotrade")
DEFAULT_ORDER_LEDGER_CSV = Path("data/runtime_state/btc/strict_5/guarded_demo_order_ledger.csv")
DEFAULT_EXPECTED_LOGIN = 75539039
SCHEMA_VERSION = "btc_strict_5_guarded_demo_autotrade_v1"

PAYLOAD_COLUMNS = [
    "created_at_utc",
    "schema_version",
    "payload_key",
    "order_key",
    "signal_key",
    "notification_key",
    "broker_symbol",
    "symbol",
    "direction",
    "lot",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "tp_price_distance",
    "sl_price_distance",
    "tp_pips",
    "sl_pips",
    "rr",
    "magic_number",
    "comment",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "signal_time",
    "base_close_time",
    "entry_time",
    "source",
    "strict_no_future_ok",
    "h1_close_time",
    "h1_confirmed_ok",
    "h4_close_time",
    "h4_confirmed_ok",
    "d1_used",
    "reason",
]

SUMMARY_PRINT_KEYS = [
    "cycle_ok",
    "reason",
    "send_requested_by_user",
    "allow_demo_send",
    "send_flag_passed_to_sender",
    "payload_rows",
    "sender_returncode",
    "sender_rows_out",
    "sender_dry_run_check_ok_rows",
    "sender_sent_rows",
    "sender_error_rows",
    "sender_order_send_called_count",
    "payload_csv",
    "order_ledger_csv",
    "summary_json",
]

STRATEGY_PRIORITY = {
    "BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200_TP1900_SL400_H20H_CD0": 10,
    "BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06_TP2500_SL750_H4H_CD0": 20,
    "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0": 30,
    "BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06_TP2400_SL600_H6H_CD0": 40,
    "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0": 50,
}

STRATEGY_ALIAS = {
    "BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200_TP1900_SL400_H20H_CD0": "BTC_DON96_SELL",
    "BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06_TP2500_SL750_H4H_CD0": "BTC_DON32_SELL",
    "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0": "BTC_RSI40_BUY",
    "BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06_TP2400_SL600_H6H_CD0": "BTC_DON64_SELL",
    "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0": "BTC_CCI_BUY",
}


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def local_now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def file_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return float(default)
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def strategy_priority(strategy_id: str) -> int:
    return int(STRATEGY_PRIORITY.get(strategy_id, 999))


def strategy_alias(strategy_id: str) -> str:
    return STRATEGY_ALIAS.get(strategy_id, strategy_id[:20])


def magic_number(strategy_id: str) -> int:
    return int(DEFAULT_MAGIC_BASE + strategy_priority(strategy_id))


def id_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "UNKNOWN_TIME"
    return pd.Timestamp(ts).strftime("%Y%m%d_%H%M")


def notification_key(row: pd.Series) -> str:
    return "|".join([
        DEFAULT_SYMBOL,
        "STRICT5",
        clean_str(row.get("strategy_id")),
        clean_str(row.get("direction")),
        clean_str(row.get("signal_time")),
    ])


def order_key(row: pd.Series) -> str:
    return "|".join([
        "ORDER",
        DEFAULT_SYMBOL,
        "STRICT5",
        clean_str(row.get("strategy_id")),
        clean_str(row.get("direction")),
        clean_str(row.get("signal_time")),
    ])


def signal_key(row: pd.Series) -> str:
    return "|".join([
        "SIGNAL",
        DEFAULT_SYMBOL,
        "STRICT5",
        clean_str(row.get("strategy_id")),
        clean_str(row.get("direction")),
        clean_str(row.get("signal_time")),
    ])


def calc_payload_prices(row: pd.Series) -> tuple[float, float, float]:
    # Prefer next M15 open when it exists because it matches the backtest entry policy.
    # If the next open is not yet in CSV, fall back to signal close as a preview-only
    # reference. The sender still validates against current MT5 bid/ask with order_check.
    next_open_available = bool(row.get("next_m15_open_available", False))
    entry = safe_float(row.get("next_m15_open_price"), default=0.0) if next_open_available else safe_float(row.get("signal_close_price"), default=0.0)
    direction = clean_str(row.get("direction")).upper()
    tp_dist = safe_float(row.get("tp_price_distance"), default=0.0)
    sl_dist = safe_float(row.get("sl_price_distance"), default=0.0)
    if direction == "BUY":
        tp = entry + tp_dist
        sl = entry - sl_dist
    else:
        tp = entry - tp_dist
        sl = entry + sl_dist
    return entry, tp, sl


def load_preview(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    input_paths = {
        "m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file),
        "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file),
        "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file),
    }
    m15 = add_indicators(read_ohlc_csv(input_paths["m15"]), include_donchian=True)
    h1 = add_indicators(read_ohlc_csv(input_paths["h1"]))
    h4 = add_indicators(read_ohlc_csv(input_paths["h4"]))
    ctx = join_confirmed_context(m15, h1, h4)
    signals = detect_signals(ctx, get_signal_specs())
    if args.scan_recent_bars and int(args.scan_recent_bars) > 0 and not ctx.empty:
        cutoff_idx = max(0, len(ctx) - int(args.scan_recent_bars))
        cutoff_time = pd.Timestamp(ctx.iloc[cutoff_idx]["time"])
        if not signals.empty:
            signals = signals[pd.to_datetime(signals["signal_time"]) >= cutoff_time].copy()
    if args.max_signal_age_minutes and int(args.max_signal_age_minutes) > 0 and not ctx.empty:
        end_close_time = pd.Timestamp(ctx.iloc[-1]["base_close_time"])
        start_time = end_close_time - pd.Timedelta(minutes=int(args.max_signal_age_minutes))
        if not signals.empty:
            signals = signals[pd.to_datetime(signals["base_close_time"]) >= start_time].copy()
    if args.latest_only and not signals.empty:
        signals = signals.sort_values(["signal_time", "strategy_id"]).tail(1).copy()
    preview = build_preview_rows(
        signals=signals,
        ctx=ctx,
        m15_next_open_lookup=build_m15_next_open_lookup(m15),
        broker_symbol=str(args.broker_symbol),
        symbol=str(args.symbol),
    )
    if not preview.empty:
        preview = preview.sort_values(["signal_time", "strategy_id"]).reset_index(drop=True)
        preview["_priority"] = preview["strategy_id"].map(strategy_priority).fillna(999).astype(int)
        # Most recent first; for identical times, lower priority number first.
        preview = preview.sort_values(["signal_time", "_priority"], ascending=[False, True]).drop(columns=["_priority"]).reset_index(drop=True)
    meta = {
        "input_paths": {k: str(v) for k, v in input_paths.items()},
        "rows": {"m15": int(len(m15)), "h1": int(len(h1)), "h4": int(len(h4)), "preview_rows": int(len(preview))},
        "ctx_last_base_close_time": time_text(ctx.iloc[-1]["base_close_time"]) if not ctx.empty else "",
    }
    return preview, meta


def payload_row(row: pd.Series, args: argparse.Namespace, rank: int) -> dict[str, Any]:
    entry, tp, sl = calc_payload_prices(row)
    strategy_id = clean_str(row.get("strategy_id"))
    alias = strategy_alias(strategy_id)
    ok = order_key(row)
    pk = ok.replace("ORDER|", "PAYLOAD|", 1)
    sk = signal_key(row)
    comment = f"B5 {alias} {clean_str(row.get('direction'))}"
    return {
        "created_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "payload_key": pk,
        "order_key": ok,
        "signal_key": sk,
        "notification_key": notification_key(row),
        "broker_symbol": args.broker_symbol,
        "symbol": args.symbol,
        "direction": clean_str(row.get("direction")),
        "lot": float(args.lot),
        "entry_price_reference": round(entry, 5),
        "sl_price": round(sl, 5),
        "tp_price": round(tp, 5),
        "tp_price_distance": safe_float(row.get("tp_price_distance")),
        "sl_price_distance": safe_float(row.get("sl_price_distance")),
        "tp_pips": safe_float(row.get("tp_pips")),
        "sl_pips": safe_float(row.get("sl_pips")),
        "rr": safe_float(row.get("rr")),
        "magic_number": magic_number(strategy_id),
        "comment": comment[:31],
        "strategy_key": strategy_id,
        "strategy_alias": alias,
        "strategy_id": strategy_id,
        "condition_id": strategy_id,
        "router_strategy_slot": alias,
        "router_strategy_id": strategy_id,
        "candidate_rank": int(rank),
        "signal_time": clean_str(row.get("signal_time")),
        "base_close_time": clean_str(row.get("base_close_time")),
        "entry_time": clean_str(row.get("entry_time")),
        "source": "btc_strict_5_guarded_demo_autotrade_from_csv",
        "strict_no_future_ok": bool(row.get("strict_no_future_ok", False)),
        "h1_close_time": clean_str(row.get("h1_close_time")),
        "h1_confirmed_ok": bool(row.get("h1_confirmed_ok", False)),
        "h4_close_time": clean_str(row.get("h4_close_time")),
        "h4_confirmed_ok": bool(row.get("h4_confirmed_ok", False)),
        "d1_used": False,
        "reason": clean_str(row.get("reason")),
    }


def build_sender_cmd(args: argparse.Namespace, payload_csv: Path, order_ledger_csv: Path, sender_out_dir: Path, send_to_sender: bool) -> list[str]:
    cmd = [
        sys.executable,
        str(SENDER_SCRIPT),
        "--input-csv", str(payload_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(sender_out_dir),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--expected-login", str(args.expected_login),
        "--require-demo-account",
        "--select-symbol",
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--deviation", str(args.deviation),
        "--registry-preview-out-csv", str(sender_out_dir / "position_registry_preview.csv"),
        "--registry-preview-out-json", str(sender_out_dir / "position_registry_preview_summary.json"),
    ]
    if args.terminal_path:
        cmd.extend(["--terminal-path", str(args.terminal_path)])
    if args.portable:
        cmd.append("--portable")
    if send_to_sender:
        cmd.append("--send")
        cmd.append("--registry-preview-include-sent")
    return cmd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BTC strict 5 guarded demo autotrade connector from CSV.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
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

    preview, meta = load_preview(args)
    if not preview.empty and args.max_orders and int(args.max_orders) > 0:
        preview = preview.head(int(args.max_orders)).copy()
    payloads = [payload_row(row, args, rank=i + 1) for i, (_, row) in enumerate(preview.iterrows())]

    payload_csv = run_dir / "btc_strict_5_order_payloads.csv"
    summary_json = run_dir / "btc_strict_5_guarded_demo_autotrade_summary.json"
    write_csv(payload_csv, payloads, PAYLOAD_COLUMNS)

    send_to_sender = bool(args.send and args.allow_demo_send)
    send_suppressed_reason = ""
    if args.send and not args.allow_demo_send:
        send_suppressed_reason = "--send was requested but --allow-demo-send was not provided; sender will run dry-run/order_check only"

    sender_report: dict[str, Any] = {}
    sender_returncode: int | None = None
    sender_stdout = ""
    sender_stderr = ""
    if not payloads:
        reason = "NO_RECENT_STRICT5_SIGNAL"
        cycle_ok = bool(args.allow_no_signal_success)
        sender_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0}
    else:
        cmd = build_sender_cmd(args, payload_csv, order_ledger_csv, sender_out_dir, send_to_sender)
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
        sender_returncode = int(proc.returncode)
        sender_stdout = proc.stdout or ""
        sender_stderr = proc.stderr or ""
        write_text(run_dir / "sender_stdout.log", sender_stdout)
        write_text(run_dir / "sender_stderr.log", sender_stderr)
        write_text(run_dir / "sender_command.txt", " ".join(cmd))
        sender_report = read_json_or_empty(sender_out_dir / "mt5_order_send_report.json")
        cycle_ok = sender_returncode == 0
        reason = "SENDER_OK" if cycle_ok else "SENDER_ERROR_OR_GUARD_BLOCK"

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_local": local_now_text(),
        "created_at_utc": utc_now_text(),
        "cycle_ok": bool(cycle_ok),
        "reason": reason,
        "send_requested_by_user": bool(args.send),
        "allow_demo_send": bool(args.allow_demo_send),
        "send_flag_passed_to_sender": bool(send_to_sender),
        "send_suppressed_reason": send_suppressed_reason,
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "safety": {
            "wrapper_calls_mt5_order_send_directly": False,
            "sender_script": str(SENDER_SCRIPT),
            "sender_default_dry_run": True,
            "require_demo_account": True,
            "expected_login": int(args.expected_login),
            "position_policy": str(args.position_policy),
            "max_orders": int(args.max_orders),
            "max_symbol_positions": int(args.max_symbol_positions),
            "max_symbol_lot": float(args.max_symbol_lot),
            "discord_send": False,
            "ai_calls": False,
            "d1_read": False,
        },
        "inputs": meta.get("input_paths", {}),
        "run_dir": str(run_dir),
        "payload_csv": str(payload_csv),
        "order_ledger_csv": str(order_ledger_csv),
        "summary_json": str(summary_json),
        "sender_out_dir": str(sender_out_dir),
        "ctx_last_base_close_time": meta.get("ctx_last_base_close_time", ""),
        "scan_recent_bars": int(args.scan_recent_bars),
        "max_signal_age_minutes": int(args.max_signal_age_minutes),
        "raw_recent_preview_rows": int(meta.get("rows", {}).get("preview_rows", 0)),
        "payload_rows": int(len(payloads)),
        "payload_order_keys": [p.get("order_key") for p in payloads],
        "payload_strategy_ids": [p.get("strategy_id") for p in payloads],
        "sender_returncode": sender_returncode,
        "sender_rows_out": sender_report.get("rows_out", 0),
        "sender_dry_run_check_ok_rows": sender_report.get("dry_run_check_ok_rows", 0),
        "sender_sent_rows": sender_report.get("sent_rows", 0),
        "sender_error_rows": sender_report.get("error_rows", 0),
        "sender_order_send_called_count": sender_report.get("order_send_called_count", 0),
        "sender_report_json": str(sender_out_dir / "mt5_order_send_report.json") if payloads else "",
        "sender_stdout_log": str(run_dir / "sender_stdout.log") if payloads else "",
        "sender_stderr_log": str(run_dir / "sender_stderr.log") if payloads else "",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    write_json(summary_json, summary)
    write_json(out_dir / "latest_btc_strict_5_guarded_demo_autotrade_summary.json", summary)

    print("=" * 100, flush=True)
    print("BTC strict 5 guarded demo autotrade connector", flush=True)
    for key in SUMMARY_PRINT_KEYS:
        print(f"{key}: {summary.get(key)}", flush=True)
    print("=" * 100, flush=True)
    if sender_stdout:
        print("--- sender stdout tail ---", flush=True)
        print("\n".join(sender_stdout.splitlines()[-40:]), flush=True)
    if sender_stderr:
        print("--- sender stderr ---", flush=True)
        print(sender_stderr, flush=True)
    print("=" * 100, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
