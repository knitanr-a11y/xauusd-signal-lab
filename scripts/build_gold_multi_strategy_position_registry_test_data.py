#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build controlled position_registry.csv test data for GOLD multi-strategy reconciliation.

This script is file-only and never touches MT5.

Purpose:
- Create isolated registry CSVs for validating the future position registry design.
- Provide deterministic cases for registry <-> open-position reconciliation before modifying
  send_mt5_order_from_payload.py.

Safety:
- No MetaTrader5 import.
- No order_check.
- No order_send.
- No existing Mochipoyo ledger mutation.
- No trigger-state mutation.

Scenarios:
- active_buy_c_ticket_990001
    One ACTIVE registry row for BUY_C_ENV_RR2_72H with position_ticket=990001.
    Use with mock_positions_same_strategy_buy_c.csv.
    Expected reconciliation: REGISTRY_ACTIVE_MATCHED.

- missing_mt5_buy_c_ticket_999999
    One ACTIVE registry row for BUY_C_ENV_RR2_72H with a ticket not present in mock positions.
    Expected reconciliation: REGISTRY_ACTIVE_MISSING_MT5.

- empty
    Writes an empty registry with the correct schema.
    Use with any positions snapshot to detect MT5_UNREGISTERED_POSITION rows.

- closed_buy_c_ticket_990001
    One CLOSED registry row for ticket=990001.
    Use with mock_positions_same_strategy_buy_c.csv to verify that closed registry rows do not count as active.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_position_registry")
DEFAULT_ACCOUNT_LOGIN = 75539039
DEFAULT_ACCOUNT_SERVER = "XMTrading-MT5 3"
DEFAULT_MAGIC = 26050601

REGISTRY_COLUMNS = [
    "created_at_utc",
    "updated_at_utc",
    "account_login",
    "account_server",
    "broker_symbol",
    "symbol",
    "position_ticket",
    "order_ticket",
    "deal_ticket",
    "magic_number",
    "direction",
    "lot",
    "entry_price",
    "sl_price",
    "tp_price",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "signal_key",
    "order_key",
    "payload_key",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "source_payload_csv",
    "sender_report_json",
    "position_status",
    "last_seen_utc",
    "close_status",
    "close_reason",
    "notes",
]

SCENARIOS = {
    "active_buy_c_ticket_990001",
    "missing_mt5_buy_c_ticket_999999",
    "empty",
    "closed_buy_c_ticket_990001",
}

BUY_C_STRATEGY_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H"
BUY_C_STRATEGY_KEY = "BUY_C_ENV_RR2_72H"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build controlled position_registry.csv test data. No MT5 calls.")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--account-login", type=int, default=DEFAULT_ACCOUNT_LOGIN)
    p.add_argument("--account-server", default=DEFAULT_ACCOUNT_SERVER)
    p.add_argument("--magic", type=int, default=DEFAULT_MAGIC)
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


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def buy_c_row(
    *,
    now: str,
    ticket: int,
    status: str,
    broker_symbol: str,
    account_login: int,
    account_server: str,
    magic: int,
    notes: str,
) -> dict[str, Any]:
    signal_key = f"REGISTRY_TEST|{BUY_C_STRATEGY_KEY}|BUY|0.01|ticket={ticket}"
    payload_key = f"{signal_key}|MOCHIPOYO_PAYLOAD"
    return {
        "created_at_utc": now,
        "updated_at_utc": now,
        "account_login": int(account_login),
        "account_server": account_server,
        "broker_symbol": broker_symbol,
        "symbol": "GOLD",
        "position_ticket": int(ticket),
        "order_ticket": int(ticket),
        "deal_ticket": int(ticket),
        "magic_number": int(magic),
        "direction": "BUY",
        "lot": 0.01,
        "entry_price": 4727.67,
        "sl_price": 4681.79,
        "tp_price": 4785.72,
        "strategy_key": BUY_C_STRATEGY_KEY,
        "strategy_alias": "BUY_C",
        "strategy_id": BUY_C_STRATEGY_ID,
        "condition_id": BUY_C_STRATEGY_ID,
        "signal_key": signal_key,
        "order_key": payload_key,
        "payload_key": payload_key,
        "router_strategy_slot": BUY_C_STRATEGY_KEY,
        "router_strategy_id": BUY_C_STRATEGY_ID,
        "candidate_rank": "REGISTRY_TEST_BUY_C",
        "source_payload_csv": "REGISTRY_TEST_DATA",
        "sender_report_json": "REGISTRY_TEST_DATA",
        "position_status": status,
        "last_seen_utc": now if status == "ACTIVE" else "",
        "close_status": "" if status == "ACTIVE" else "CLOSED_TEST",
        "close_reason": "" if status == "ACTIVE" else "REGISTRY_TEST_CLOSED_ROW",
        "notes": notes,
    }


def scenario_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    now = utc_now_text()
    scenario = str(args.scenario)
    if scenario == "empty":
        return []
    if scenario == "active_buy_c_ticket_990001":
        return [
            buy_c_row(
                now=now,
                ticket=990001,
                status="ACTIVE",
                broker_symbol=args.broker_symbol,
                account_login=args.account_login,
                account_server=args.account_server,
                magic=args.magic,
                notes="Expected to match mock_positions_same_strategy_buy_c.csv",
            )
        ]
    if scenario == "missing_mt5_buy_c_ticket_999999":
        return [
            buy_c_row(
                now=now,
                ticket=999999,
                status="ACTIVE",
                broker_symbol=args.broker_symbol,
                account_login=args.account_login,
                account_server=args.account_server,
                magic=args.magic,
                notes="Expected to be missing from current MT5/mock positions",
            )
        ]
    if scenario == "closed_buy_c_ticket_990001":
        return [
            buy_c_row(
                now=now,
                ticket=990001,
                status="CLOSED",
                broker_symbol=args.broker_symbol,
                account_login=args.account_login,
                account_server=args.account_server,
                magic=args.magic,
                notes="Closed row should not count as active ownership",
            )
        ]
    raise ValueError(f"unknown scenario: {scenario}")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / f"position_registry_test_{args.scenario}.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / f"position_registry_test_{args.scenario}.json"

    rows = scenario_rows(args)
    df = pd.DataFrame([{col: row.get(col, "") for col in REGISTRY_COLUMNS} for row in rows], columns=REGISTRY_COLUMNS)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(output_csv), index=False, encoding="utf-8-sig")

    summary = {
        "schema_version": "gold_multi_strategy_position_registry_test_data_v1",
        "scenario": args.scenario,
        "rows_out": int(len(df)),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "account_login": int(args.account_login),
        "account_server": args.account_server,
        "broker_symbol": args.broker_symbol,
        "created_at_utc": utc_now_text(),
        "safety": {
            "mt5_imported": False,
            "order_check_called": False,
            "order_send_called": False,
            "ledger_written": False,
            "trigger_state_written": False,
        },
        "records": df.to_dict(orient="records"),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print("build_gold_multi_strategy_position_registry_test_data")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True))
    if df.empty:
        print("[INFO] wrote empty registry schema")
    else:
        print(df[["position_ticket", "broker_symbol", "direction", "lot", "strategy_key", "position_status", "notes"]].to_string(index=False))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
