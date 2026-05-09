#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a controlled payload-bearing guarded-send-cycle report for registry preview tests.

This script is file-only and never touches MT5.

Purpose:
- Create a controlled latest_multi_strategy_demo_autotrade_send_cycle_result.json-like report.
- Point that report at a payload_out_dir containing order_payloads.csv.
- Allow scripts/run_gold_multi_strategy_send_report_registry_preview.py to validate the
  payload-bearing report path without running the real guarded send cycle.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No real sender modification.
- No existing Mochipoyo ledger mutation.
- No trigger-state mutation.

Default behavior:
- Copy a controlled payload CSV into <out-dir>/payload_bridge_send/order_payloads.csv.
- Write a send-cycle-like JSON report with source_payload_rows_out > 0.
- By default, no real sent ticket is claimed; downstream wrapper should use fallback tickets.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

SCHEMA_VERSION = "gold_multi_strategy_controlled_send_report_v1"
DEFAULT_PAYLOAD_CSV = Path("data/research_results/gold_multi_strategy_position_policy_preflight/order_payloads_policy_test_same_direction_buy.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_controlled_send_report")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build controlled payload-bearing send report. No MT5 calls.")
    p.add_argument("--payload-csv", type=Path, default=DEFAULT_PAYLOAD_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--payload-out-dir", type=Path, default=None)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--account-login", type=int, default=75539039)
    p.add_argument("--account-server", default="XMTrading-MT5 3")
    p.add_argument("--account-name", default="Demo Account")
    p.add_argument("--send-enabled", action="store_true", default=True)
    p.add_argument("--send-requested", action="store_true", default=False)
    p.add_argument("--safe-send-guard-ok", action="store_true", default=True)
    p.add_argument("--include-ticket-result", action="store_true", help="Include synthetic ticket/order/deal fields in mt5_report.results[0].")
    p.add_argument("--position-ticket", type=int, default=990001)
    p.add_argument("--order-ticket", type=int, default=880001)
    p.add_argument("--deal-ticket", type=int, default=770001)
    p.add_argument("--position-policy", default="block_any")
    p.add_argument("--mt5-status-summary", default="CONTROLLED_PAYLOAD_REPORT_NO_REAL_SEND")
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def read_payload(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def copy_payload(src: Path, dst: Path) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(windows_long_path(src), windows_long_path(dst))
    return int(len(read_payload(dst)))


def first_payload_metadata(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    row = df.iloc[0]
    return {
        "broker_symbol": str(row.get("broker_symbol", row.get("symbol", ""))),
        "direction": str(row.get("direction", "")),
        "lot": float(row.get("lot", 0.0) or 0.0),
        "strategy_id": str(row.get("strategy_id", "")),
        "router_strategy_slot": str(row.get("router_strategy_slot", row.get("pair_name", ""))),
        "signal_key": str(row.get("signal_key", "")),
        "order_key": str(row.get("order_key", row.get("payload_key", ""))),
        "payload_key": str(row.get("payload_key", row.get("order_key", ""))),
    }


def build_report(args: argparse.Namespace, payload_out_dir: Path, payload_rows: int, payload_meta: dict[str, Any]) -> dict[str, Any]:
    now = utc_now_text()
    mt5_result_row: dict[str, Any] = {
        "order_status": args.mt5_status_summary,
        "broker_symbol": args.broker_symbol,
        "send_requested": bool(args.send_requested),
        "order_send_called": False,
        "note": "controlled payload-bearing report; no real MT5 call",
        **payload_meta,
    }
    if args.include_ticket_result:
        mt5_result_row.update({
            "position_ticket": int(args.position_ticket),
            "order_ticket": int(args.order_ticket),
            "deal_ticket": int(args.deal_ticket),
        })
    mt5_report = {
        "schema_version": "controlled_mt5_send_report_v1",
        "send_requested": bool(args.send_requested),
        "position_policy": args.position_policy,
        "rows_out": payload_rows,
        "dry_run_check_ok_rows": 0,
        "blocked_position_policy_rows": 0,
        "order_send_called_count": 0,
        "sent_rows": 0,
        "error_rows": 0,
        "account_info": {
            "login": int(args.account_login),
            "server": args.account_server,
            "name": args.account_name,
        },
        "results": [mt5_result_row] if payload_rows > 0 else [],
        "safety": {
            "mt5_imported": False,
            "order_check_called": False,
            "order_send_called": False,
        },
    }
    key_metrics = {
        "payload_rows_out": payload_rows,
        "valid_order_payloads": payload_rows,
        "mt5_order_send_called_count": 0,
        "mt5_sent_rows": 0,
        "mt5_blocked_position_policy_rows": 0,
        "mt5_status_summary": args.mt5_status_summary,
        "mt5_account_login": int(args.account_login),
        "mt5_account_server": args.account_server,
        "mt5_account_name": args.account_name,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "cycle_start_utc": now,
        "cycle_end_utc": now,
        "cycle_ok": True,
        "send_enabled": bool(args.send_enabled),
        "send_requested": bool(args.send_requested),
        "safe_send_guard_ok": bool(args.safe_send_guard_ok),
        "guard_errors": [],
        "csv_dir": "CONTROLLED_SEND_REPORT_TEST",
        "out_dir": str(args.out_dir),
        "payload_out_dir": str(payload_out_dir),
        "mt5_send_out_dir": str(args.out_dir / "mt5_order_send_controlled"),
        "order_ledger_csv": str(args.out_dir / "controlled_demo_send_order_ledger.csv"),
        "returncodes": {
            "router": "CONTROLLED_SKIPPED",
            "adapter": "CONTROLLED_SKIPPED",
            "payload_bridge": 0,
            "mt5_send": "CONTROLLED_NO_REAL_SEND",
        },
        "router_result": {},
        "adapter_result": {},
        "payload_bridge_result": {
            "bridge_ok": True,
            "rows_in": payload_rows,
            "rows_out": payload_rows,
            "valid_order_payloads": payload_rows,
            "output_csv": str(payload_out_dir / "order_payloads.csv"),
            "controlled": True,
        },
        "mt5_report": mt5_report,
        "key_metrics": key_metrics,
        "controlled_payload_metadata": payload_meta,
        "safety": {
            "mt5_imported": False,
            "order_check_called_count": 0,
            "order_send_called_count": 0,
            "registry_mutated": False,
            "ledger_mutated": False,
            "trigger_state_mutated": False,
            "real_sender_modified": False,
            "existing_bat_modified": False,
        },
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_json = args.output_json if args.output_json is not None else args.out_dir / "latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json"
    payload_out_dir = args.payload_out_dir if args.payload_out_dir is not None else args.out_dir / "payload_bridge_send_controlled"
    payload_out_csv = payload_out_dir / "order_payloads.csv"

    if not args.payload_csv.exists():
        summary = {
            "schema_version": SCHEMA_VERSION,
            "build_ok": False,
            "reason": "PAYLOAD_CSV_NOT_FOUND",
            "payload_csv": str(args.payload_csv),
            "output_json": str(output_json),
            "safety": safety_summary(),
        }
        write_json(output_json, summary)
        print("build_gold_multi_strategy_controlled_send_report")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    payload_rows = copy_payload(args.payload_csv, payload_out_csv)
    payload_df = read_payload(payload_out_csv)
    payload_meta = first_payload_metadata(payload_df)
    report = build_report(args, payload_out_dir, payload_rows, payload_meta)
    write_json(output_json, report)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "build_ok": True,
        "reason": "CONTROLLED_SEND_REPORT_BUILT",
        "payload_csv": str(args.payload_csv),
        "payload_out_csv": str(payload_out_csv),
        "output_json": str(output_json),
        "payload_rows": payload_rows,
        "include_ticket_result": bool(args.include_ticket_result),
        "payload_metadata": payload_meta,
        "safety": safety_summary(),
    }
    summary_json = args.out_dir / "controlled_send_report_build_summary.json"
    write_json(summary_json, summary)

    print("build_gold_multi_strategy_controlled_send_report")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print(f"output_json: {output_json}")
    print(f"payload_out_csv: {payload_out_csv}")
    print("done")
    return 0


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": False,
        "order_check_called": False,
        "order_send_called": False,
        "existing_mochipoyo_ledger_mutated": False,
        "trigger_state_mutated": False,
        "real_sender_modified": False,
        "existing_bat_modified": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
