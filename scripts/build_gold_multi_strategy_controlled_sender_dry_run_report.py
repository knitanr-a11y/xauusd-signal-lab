#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build controlled send_mt5_order_from_payload dry-run outputs.

This creates a synthetic sender output directory containing:
- mt5_order_send_report.json
- mt5_order_send_results.csv

Purpose:
- Validate sender-adjacent registry preview hooks without relying on current market
  price or a live MT5 order_check result.
- Produce a controlled `DRY_RUN_ORDER_CHECK_OK` row from an order_payloads.csv row.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No ledger mutation.
- No trigger-state mutation.
- No production registry mutation.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

SCHEMA_VERSION = "gold_multi_strategy_controlled_sender_dry_run_report_v1"

DEFAULT_PAYLOAD_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit/order_payloads.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_sender_registry_preview/controlled_sender_dry_run_ok")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build controlled sender dry-run OK outputs. No MT5 calls.")
    p.add_argument("--payload-csv", type=Path, default=DEFAULT_PAYLOAD_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--max-rows", type=int, default=1)
    p.add_argument("--account-login", type=int, default=75539039)
    p.add_argument("--account-server", default="XMTrading-MT5 3")
    p.add_argument("--account-name", default="Demo Account")
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--position-policy", default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=5)
    p.add_argument("--max-symbol-lot", type=float, default=0.05)
    p.add_argument("--existing-symbol-positions", type=int, default=1)
    p.add_argument("--existing-symbol-lot", type=float, default=0.01)
    p.add_argument("--existing-symbol-directions", default="BUY")
    p.add_argument("--current-execution-price", type=float, default=None)
    p.add_argument("--sl-price", type=float, default=None)
    p.add_argument("--tp-price", type=float, default=None)
    p.add_argument("--digits", type=int, default=2)
    p.add_argument("--order-status", default="DRY_RUN_ORDER_CHECK_OK")
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


def path_exists(path: Path) -> bool:
    try:
        return Path(windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value)
    return text if text else default


def clean_float(value: Any, default: float | None = None) -> float | None:
    try:
        v = float(value)
    except Exception:
        return default
    if pd.isna(v) or not math.isfinite(v):
        return default
    return v


def clean_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return default


def first_available_float(row: pd.Series, keys: list[str], default: float | None = None) -> float | None:
    for key in keys:
        v = clean_float(row.get(key), None)
        if v is not None:
            return v
    return default


def infer_controlled_prices(row: pd.Series, direction: str, args: argparse.Namespace) -> tuple[float, float, float]:
    sl = args.sl_price if args.sl_price is not None else first_available_float(row, ["sl_price", "sl", "stop_loss"], None)
    tp = args.tp_price if args.tp_price is not None else first_available_float(row, ["tp_price", "tp", "take_profit"], None)
    entry = args.current_execution_price if args.current_execution_price is not None else first_available_float(
        row,
        ["entry_price", "entry_price_reference", "open_price", "price"],
        None,
    )

    d = direction.upper()
    if entry is None:
        if sl is not None and tp is not None:
            entry = (float(sl) + float(tp)) / 2.0
        elif d == "BUY":
            entry = 4727.67
        else:
            entry = 5015.38
    if sl is None or tp is None:
        if d == "BUY":
            sl = float(entry) - 10.0 if sl is None else sl
            tp = float(entry) + 20.0 if tp is None else tp
        else:
            sl = float(entry) + 20.0 if sl is None else sl
            tp = float(entry) - 10.0 if tp is None else tp

    # If a stale payload makes the relation invalid, keep the payload SL/TP but put the
    # controlled execution price between them when possible. This preserves payload risk
    # levels while creating a sender-style DRY_RUN_ORDER_CHECK_OK fixture.
    assert sl is not None and tp is not None and entry is not None
    if d == "BUY" and not (float(sl) < float(entry) < float(tp)):
        entry = (float(sl) + float(tp)) / 2.0
    if d == "SELL" and not (float(tp) < float(entry) < float(sl)):
        entry = (float(sl) + float(tp)) / 2.0

    digits = int(args.digits)
    return round(float(entry), digits), round(float(sl), digits), round(float(tp), digits)


def make_sender_row(payload_row: pd.Series, row_index: int, args: argparse.Namespace) -> dict[str, Any]:
    direction = clean_str(payload_row.get("direction"), "BUY").upper()
    broker_symbol = args.broker_symbol or clean_str(payload_row.get("broker_symbol"), clean_str(payload_row.get("symbol"), "GOLD#"))
    lot = clean_float(payload_row.get("lot"), 0.01) or 0.01
    entry, sl, tp = infer_controlled_prices(payload_row, direction, args)
    order_key = clean_str(payload_row.get("order_key"), clean_str(payload_row.get("payload_key")))
    payload_key = clean_str(payload_row.get("payload_key"), order_key)
    magic = clean_int(payload_row.get("magic_number"), 26050601)
    request = {
        "action": "CONTROLLED_DEAL",
        "symbol": broker_symbol,
        "volume": lot,
        "type": direction,
        "price": entry,
        "sl": sl,
        "tp": tp,
        "magic": magic,
        "comment": clean_str(payload_row.get("comment"), f"mochipoyo {direction}")[:31],
    }
    check_raw = {
        "retcode": 0,
        "comment": "Done",
        "controlled": True,
        "note": "synthetic order_check success; no MT5 call",
    }
    return {
        "row_index": row_index,
        "order_key": order_key,
        "payload_key": payload_key,
        "broker_symbol": broker_symbol,
        "direction": direction,
        "lot": lot,
        "send_requested": False,
        "position_policy": args.position_policy,
        "max_symbol_positions": int(args.max_symbol_positions),
        "max_symbol_lot": float(args.max_symbol_lot),
        "order_send_called": False,
        "order_send_ok": False,
        "order_status": args.order_status,
        "existing_symbol_positions": int(args.existing_symbol_positions),
        "existing_symbol_lot": float(args.existing_symbol_lot),
        "existing_symbol_directions": args.existing_symbol_directions,
        "current_execution_price": entry,
        "sl_price": sl,
        "tp_price": tp,
        "digits": int(args.digits),
        "point": 0.01,
        "volume_min": 0.01,
        "volume_max": 50.0,
        "volume_step": 0.01,
        "trade_stops_level": 0,
        "bid": entry if direction == "SELL" else round(entry - 0.05, int(args.digits)),
        "ask": entry if direction == "BUY" else round(entry + 0.05, int(args.digits)),
        "order_check_request": json.dumps(request, ensure_ascii=False, default=str),
        "order_check_raw": json.dumps(check_raw, ensure_ascii=False, default=str),
        "order_check_retcode": 0,
        "order_check_comment": "Done",
        "order_check_ok": True,
        "validation_errors": "",
    }


def main() -> int:
    args = parse_args()
    Path(windows_long_path(args.out_dir)).mkdir(parents=True, exist_ok=True)
    report_json = args.out_dir / "mt5_order_send_report.json"
    results_csv = args.out_dir / "mt5_order_send_results.csv"
    summary_json = args.out_dir / "controlled_sender_dry_run_report_build_summary.json"

    if not path_exists(args.payload_csv):
        empty = pd.DataFrame()
        write_csv(empty, results_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "build_ok": False,
            "reason": "PAYLOAD_CSV_NOT_FOUND",
            "payload_csv": str(args.payload_csv),
            "out_dir": str(args.out_dir),
            "safety": safety_summary(),
        }
        write_json(report_json, summary)
        write_json(summary_json, summary)
        print("build_gold_multi_strategy_controlled_sender_dry_run_report")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 2

    payload_df = read_csv(args.payload_csv)
    if args.max_rows and args.max_rows > 0:
        payload_df = payload_df.head(int(args.max_rows)).copy()
    rows = [make_sender_row(row, i + 1, args) for i, (_, row) in enumerate(payload_df.iterrows())]
    out_df = pd.DataFrame(rows)
    write_csv(out_df, results_csv)

    report = {
        "schema_version": SCHEMA_VERSION,
        "input_csv": str(args.payload_csv),
        "order_ledger_csv": str(args.out_dir / "controlled_no_ledger_mutation.csv"),
        "send_requested": False,
        "order_send_called_count": 0,
        "mt5_import_ok": False,
        "mt5_import_error": "CONTROLLED_NO_MT5_IMPORT",
        "initialize_ok": False,
        "position_policy": args.position_policy,
        "max_symbol_positions": int(args.max_symbol_positions),
        "max_symbol_lot": float(args.max_symbol_lot),
        "account_info": {
            "login": int(args.account_login),
            "server": args.account_server,
            "name": args.account_name,
            "trade_allowed": True,
        },
        "terminal_info": {
            "trade_allowed": True,
            "controlled": True,
        },
        "rows_in": int(len(payload_df)),
        "rows_out": int(len(out_df)),
        "dry_run_check_ok_rows": int((out_df["order_status"] == "DRY_RUN_ORDER_CHECK_OK").sum()) if not out_df.empty else 0,
        "sent_rows": 0,
        "blocked_position_policy_rows": int((out_df["order_status"] == "BLOCKED_POSITION_POLICY").sum()) if not out_df.empty else 0,
        "error_rows": int(out_df["order_status"].astype(str).str.startswith(("ERROR", "BLOCKED")).sum()) if not out_df.empty else 0,
        "results": rows,
        "safety": safety_summary(),
    }
    write_json(report_json, report)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "build_ok": True,
        "reason": "CONTROLLED_SENDER_DRY_RUN_REPORT_BUILT",
        "payload_csv": str(args.payload_csv),
        "out_dir": str(args.out_dir),
        "report_json": str(report_json),
        "results_csv": str(results_csv),
        "rows_in": int(len(payload_df)),
        "rows_out": int(len(out_df)),
        "dry_run_check_ok_rows": int(report["dry_run_check_ok_rows"]),
        "order_send_called_count": 0,
        "safety": safety_summary(),
    }
    write_json(summary_json, summary)

    print("build_gold_multi_strategy_controlled_sender_dry_run_report")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if not out_df.empty:
        show_cols = ["row_index", "order_status", "broker_symbol", "direction", "lot", "current_execution_price", "sl_price", "tp_price", "order_check_ok", "order_send_called"]
        print(out_df[show_cols].to_string(index=False))
    print(f"report_json: {report_json}")
    print(f"results_csv: {results_csv}")
    print("done")
    return 0


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": False,
        "order_check_called_count": 0,
        "order_send_called_count": 0,
        "order_ledger_mutated": False,
        "trigger_state_mutated": False,
        "production_registry_mutated": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
