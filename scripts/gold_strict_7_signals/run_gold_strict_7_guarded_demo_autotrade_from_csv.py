#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build GOLD strict 7 order payloads and call the existing guarded MT5 sender.

This is the autotrade connection layer for GOLD strict 7.

It intentionally reuses:

    scripts/send_mt5_order_from_payload.py

Safety defaults:
- dry-run/order_check only unless BOTH --send and --allow-demo-send are passed
- max-orders=1
- lot=0.01
- position-policy=block_any
- require-demo-account is passed to the sender by default
- expected-login defaults to the known GOLD demo account 75539039
- no Discord send
- no AI call
- no direct mt5.order_send in this wrapper
- duplicate order_key prevention is handled by sender order ledger

The wrapper only:
1. Reads GOLD live CSVs.
2. Detects recent GOLD strict 7 signals using the same strict detector.
3. Builds order_payloads.csv in the existing sender-compatible schema.
4. Calls send_mt5_order_from_payload.py.
5. Writes a summary JSON.
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

from gold_strict_7_signal_specs import DEFAULT_SYMBOL, GoldStrictSignalSpec, get_signal_specs, validate_signal_specs  # noqa: E402
from run_gold_strict_7_backtest_from_csv import (  # noqa: E402
    add_indicators,
    apply_cooldown,
    attach_strict_context,
    detect_spec_candidates,
    read_ohlc_csv,
)

SENDER_SCRIPT = REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_strict_7_guarded_demo_autotrade")
DEFAULT_ORDER_LEDGER_CSV = Path("data/runtime_state/gold/strict_7/guarded_demo_order_ledger.csv")
DEFAULT_BROKER_SYMBOL = "GOLD#"
DEFAULT_EXPECTED_LOGIN = 75539039
SCHEMA_VERSION = "gold_strict_7_guarded_demo_autotrade_v2"

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
    "session",
    "source",
    "strict_no_future_ok",
    "context_h1_close_time",
    "context_h4_close_time",
    "context_d1_close_time",
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
    "SELL_KC_CCI150_LONDON_TP100_SL10": 10,
    "BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5": 20,
    "SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5": 30,
    "BUY_STOCH_BB_KTURN_NY_TP150_SL10": 40,
    "BUY_SWEEP_RECLAIM_RSI_TP150_SL10": 50,
    "SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120": 60,
    "SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60": 70,
}

STRATEGY_ALIAS = {
    "SELL_KC_CCI150_LONDON_TP100_SL10": "SELL_KC_CCI150",
    "BUY_SWEEP_RECLAIM_RSI_TP150_SL10": "BUY_SWEEP_RSI",
    "BUY_STOCH_BB_KTURN_NY_TP150_SL10": "BUY_STOCH_BB",
    "SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5": "SELL_DON48",
    "SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120": "SELL_DON96_CD120",
    "SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60": "SELL_DON96_CD60",
    "BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5": "BUY_BB_RSI30",
}


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def local_now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def file_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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


def time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return clean_str(value)
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


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


def calc_prices(row: pd.Series, spec: GoldStrictSignalSpec) -> tuple[float, float, float]:
    entry = float(row["close"])
    if spec.direction == "BUY":
        tp = entry + spec.tp_price_distance
        sl = entry - spec.sl_price_distance
    else:
        tp = entry - spec.tp_price_distance
        sl = entry + spec.sl_price_distance
    return entry, tp, sl


def strategy_priority(strategy_id: str) -> int:
    return int(STRATEGY_PRIORITY.get(strategy_id, 999))


def strategy_alias(strategy_id: str) -> str:
    return STRATEGY_ALIAS.get(strategy_id, strategy_id[:20])


def magic_number(strategy_id: str) -> int:
    return 26052070 + strategy_priority(strategy_id)


def notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, time_text(row.get("close_time"))])


def order_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    return "|".join(["ORDER", DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, time_text(row.get("close_time"))])


def signal_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    return "|".join(["SIGNAL", DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, time_text(row.get("close_time"))])


def resolve_csv_paths(args: argparse.Namespace) -> dict[str, Path]:
    csv_dir = Path(args.csv_dir)
    return {
        "M5": Path(args.gold_m5_csv) if args.gold_m5_csv else csv_dir / "goldsharp_m5.csv",
        "H1": Path(args.gold_h1_csv) if args.gold_h1_csv else csv_dir / "goldsharp_h1.csv",
        "H4": Path(args.gold_h4_csv) if args.gold_h4_csv else csv_dir / "goldsharp_h4.csv",
        "D1": Path(args.gold_d1_csv) if args.gold_d1_csv else csv_dir / "goldsharp_d1.csv",
    }


def load_context(paths: dict[str, Path], args: argparse.Namespace) -> pd.DataFrame:
    m5 = add_indicators(read_ohlc_csv(paths["M5"], tail_bars=args.tail_m5), "M5")
    h1 = add_indicators(read_ohlc_csv(paths["H1"], tail_bars=args.tail_h1), "H1")
    h4 = add_indicators(read_ohlc_csv(paths["H4"], tail_bars=args.tail_h4), "H4")
    d1 = add_indicators(read_ohlc_csv(paths["D1"], tail_bars=args.tail_d1), "D1")
    return attach_strict_context(m5, h1, h4, d1)


def collect_recent_signals(ctx: pd.DataFrame, specs: list[GoldStrictSignalSpec], args: argparse.Namespace) -> list[tuple[pd.Timestamp, GoldStrictSignalSpec, pd.Series]]:
    if ctx.empty:
        return []
    end_idx = len(ctx) - 1 - int(args.bar_offset)
    if end_idx < 0:
        return []
    end_close_time = pd.Timestamp(ctx.iloc[end_idx]["close_time"])
    start_by_bars = end_close_time - pd.Timedelta(minutes=5 * max(1, int(args.scan_recent_bars) - 1))
    start_by_age = end_close_time - pd.Timedelta(minutes=max(1, int(args.max_signal_age_minutes)))
    start_close_time = max(start_by_bars, start_by_age)
    items: list[tuple[pd.Timestamp, GoldStrictSignalSpec, pd.Series]] = []
    for spec in specs:
        raw = detect_spec_candidates(ctx, spec)
        if raw.empty:
            continue
        cooled = apply_cooldown(raw, spec)
        if cooled.empty:
            continue
        close_times = pd.to_datetime(cooled["close_time"], errors="coerce")
        mask = (close_times >= start_close_time) & (close_times <= end_close_time)
        recent = cooled[mask.fillna(False)].copy()
        for _, row in recent.iterrows():
            items.append((pd.Timestamp(row["close_time"]), spec, row))
    items.sort(key=lambda x: (x[0], -strategy_priority(x[1].strategy_id)), reverse=True)
    return items


def payload_row(row: pd.Series, spec: GoldStrictSignalSpec, args: argparse.Namespace, rank: int) -> dict[str, Any]:
    entry, tp, sl = calc_prices(row, spec)
    ok = order_key(row, spec)
    pk = ok.replace("ORDER|", "PAYLOAD|", 1)
    sk = signal_key(row, spec)
    alias = strategy_alias(spec.strategy_id)
    comment = f"G7 {alias} {spec.direction}"
    return {
        "created_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "payload_key": pk,
        "order_key": ok,
        "signal_key": sk,
        "notification_key": notification_key(row, spec),
        "broker_symbol": args.broker_symbol,
        "symbol": DEFAULT_SYMBOL,
        "direction": spec.direction,
        "lot": float(args.lot),
        "entry_price_reference": round(entry, 5),
        "sl_price": round(sl, 5),
        "tp_price": round(tp, 5),
        "tp_pips": float(spec.tp_pips),
        "sl_pips": float(spec.sl_pips),
        "rr": float(spec.rr),
        "magic_number": int(magic_number(spec.strategy_id)),
        "comment": comment[:31],
        "strategy_key": spec.strategy_id,
        "strategy_alias": alias,
        "strategy_id": spec.strategy_id,
        "condition_id": spec.strategy_id,
        "router_strategy_slot": alias,
        "router_strategy_id": spec.strategy_id,
        "candidate_rank": int(rank),
        "signal_time": time_text(row.get("close_time")),
        "session": spec.session,
        "source": "gold_strict_7_guarded_demo_autotrade_from_csv",
        "strict_no_future_ok": bool(row.get("strict_no_future_ok", False)),
        "context_h1_close_time": time_text(row.get("h1_close_time")),
        "context_h4_close_time": time_text(row.get("h4_close_time")),
        "context_d1_close_time": time_text(row.get("d1_close_time")),
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
    p = argparse.ArgumentParser(description="GOLD strict 7 guarded demo autotrade connector from CSV.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--gold-m5-csv", default="")
    p.add_argument("--gold-h1-csv", default="")
    p.add_argument("--gold-h4-csv", default="")
    p.add_argument("--gold-d1-csv", default="")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--expected-login", type=int, default=DEFAULT_EXPECTED_LOGIN)
    p.add_argument("--scan-recent-bars", type=int, default=3)
    p.add_argument("--max-signal-age-minutes", type=int, default=15)
    p.add_argument("--bar-offset", type=int, default=1)
    p.add_argument("--tail-m5", type=int, default=20000)
    p.add_argument("--tail-h1", type=int, default=5000)
    p.add_argument("--tail-h4", type=int, default=2000)
    p.add_argument("--tail-d1", type=int, default=1000)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--deviation", type=int, default=50)
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
    specs = get_signal_specs()
    out_dir = resolve_repo_path(args.out_dir)
    order_ledger_csv = resolve_repo_path(args.order_ledger_csv)
    run_dir = out_dir / file_stamp()
    sender_out_dir = run_dir / "sender"
    mkdirp(sender_out_dir)

    paths = resolve_csv_paths(args)
    ctx = load_context(paths, args)
    signals = collect_recent_signals(ctx, specs, args)
    payloads = [payload_row(row, spec, args, rank=i + 1) for i, (_, spec, row) in enumerate(signals)]

    payload_csv = run_dir / "gold_strict_7_order_payloads.csv"
    summary_json = run_dir / "gold_strict_7_guarded_demo_autotrade_summary.json"
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
        reason = "NO_RECENT_STRICT7_SIGNAL"
        cycle_ok = bool(args.allow_no_signal_success)
        sender_report = {
            "rows_out": 0,
            "dry_run_check_ok_rows": 0,
            "sent_rows": 0,
            "error_rows": 0,
            "order_send_called_count": 0,
        }
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
        },
        "inputs": {tf: str(p) for tf, p in paths.items()},
        "run_dir": str(run_dir),
        "payload_csv": str(payload_csv),
        "order_ledger_csv": str(order_ledger_csv),
        "summary_json": str(summary_json),
        "sender_out_dir": str(sender_out_dir),
        "ctx_rows": int(len(ctx)),
        "scan_recent_bars": int(args.scan_recent_bars),
        "max_signal_age_minutes": int(args.max_signal_age_minutes),
        "bar_offset": int(args.bar_offset),
        "raw_recent_signals_after_cooldown": int(len(signals)),
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
    write_json(out_dir / "latest_gold_strict_7_guarded_demo_autotrade_summary.json", summary)

    print("=" * 100, flush=True)
    print("GOLD strict 7 guarded demo autotrade connector", flush=True)
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
