#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build mock MT5 position snapshots for strategy policy preflight v3 tests.

This script is file-only and never touches MT5.

Purpose:
- Generate controlled mock positions CSVs to test future strategy-aware policy.
- Validate same_strategy and total_position_cap logic without opening real demo positions.

Scenarios:
- same_strategy_buy_c
    One existing GOLD# BUY position with detectable BUY_C_ENV_RR2_72H strategy key.

- same_strategy_sell_ab
    One existing GOLD# SELL position with detectable SELL_H1H4_BEAR_AB strategy key.

- total_cap_5
    Five existing mock positions across symbols/strategies.

- opposite_buy
    One existing GOLD# BUY position, useful for SELL opposite-direction block tests.

Safety:
- No MetaTrader5 import.
- No order_check.
- No order_send.
- No ledger mutation.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_position_policy_preflight")

POSITION_COLUMNS = [
    "ticket",
    "identifier",
    "symbol",
    "direction",
    "type",
    "volume",
    "price_open",
    "sl",
    "tp",
    "magic",
    "comment",
    "external_id",
    "time",
    "time_msc",
    "profit",
    "swap",
]

SCENARIOS = {
    "same_strategy_buy_c",
    "same_strategy_sell_ab",
    "total_cap_5",
    "opposite_buy",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build mock positions CSV for preflight v3. No MT5 calls.")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--broker-symbol", default="GOLD#")
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


def mt5_type(direction: str) -> int:
    return 0 if direction.upper() == "BUY" else 1


def base_position(
    *,
    ticket: int,
    symbol: str,
    direction: str,
    volume: float,
    price_open: float,
    sl: float,
    tp: float,
    magic: int,
    comment: str,
    external_id: str = "",
) -> dict[str, Any]:
    return {
        "ticket": int(ticket),
        "identifier": int(ticket),
        "symbol": symbol,
        "direction": direction.upper(),
        "type": mt5_type(direction),
        "volume": float(volume),
        "price_open": float(price_open),
        "sl": float(sl),
        "tp": float(tp),
        "magic": int(magic),
        "comment": comment,
        "external_id": external_id,
        "time": "",
        "time_msc": "",
        "profit": 0.0,
        "swap": 0.0,
    }


def scenario_rows(scenario: str, broker_symbol: str) -> list[dict[str, Any]]:
    if scenario == "same_strategy_buy_c":
        return [
            base_position(
                ticket=990001,
                symbol=broker_symbol,
                direction="BUY",
                volume=0.01,
                price_open=4727.67,
                sl=4681.79,
                tp=4785.72,
                magic=26050601,
                comment="ms BUY_C BUY_C_ENV_RR2_72H",
                external_id="BUY_C_ENV_RR2_72H|MOCK",
            )
        ]
    if scenario == "same_strategy_sell_ab":
        return [
            base_position(
                ticket=990101,
                symbol=broker_symbol,
                direction="SELL",
                volume=0.01,
                price_open=4727.67,
                sl=4737.67,
                tp=4707.67,
                magic=26050601,
                comment="ms SELL_AB SELL_H1H4_BEAR_AB",
                external_id="SELL_H1H4_BEAR_AB|MOCK",
            )
        ]
    if scenario == "opposite_buy":
        return [
            base_position(
                ticket=990201,
                symbol=broker_symbol,
                direction="BUY",
                volume=0.01,
                price_open=4727.67,
                sl=4681.79,
                tp=4785.72,
                magic=26050601,
                comment="mock opposite BUY",
            )
        ]
    if scenario == "total_cap_5":
        return [
            base_position(ticket=991001, symbol=broker_symbol, direction="BUY", volume=0.01, price_open=4727.67, sl=4681.79, tp=4785.72, magic=26050601, comment="ms BUY_C BUY_C_ENV_RR2_72H", external_id="BUY_C_ENV_RR2_72H|MOCK1"),
            base_position(ticket=991002, symbol="BTCUSD#", direction="BUY", volume=0.01, price_open=100000.0, sl=99000.0, tp=102000.0, magic=26050601, comment="ms BTC_A", external_id="BTC_A|MOCK2"),
            base_position(ticket=991003, symbol="EURUSD", direction="BUY", volume=0.01, price_open=1.1000, sl=1.0900, tp=1.1200, magic=26050601, comment="mock pos 3", external_id="MOCK3"),
            base_position(ticket=991004, symbol="USDJPY", direction="SELL", volume=0.01, price_open=155.0, sl=156.0, tp=153.0, magic=26050601, comment="mock pos 4", external_id="MOCK4"),
            base_position(ticket=991005, symbol="XAGUSD", direction="BUY", volume=0.01, price_open=30.0, sl=29.0, tp=32.0, magic=26050601, comment="mock pos 5", external_id="MOCK5"),
        ]
    raise ValueError(f"unknown scenario: {scenario}")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / f"mock_positions_{args.scenario}.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / f"mock_positions_{args.scenario}.json"

    rows = scenario_rows(str(args.scenario), str(args.broker_symbol))
    df = pd.DataFrame([{col: row.get(col, "") for col in POSITION_COLUMNS} for row in rows], columns=POSITION_COLUMNS)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(output_csv), index=False, encoding="utf-8-sig")

    summary = {
        "schema_version": "gold_multi_strategy_mock_positions_v1",
        "scenario": args.scenario,
        "rows_out": int(len(df)),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "broker_symbol": args.broker_symbol,
        "created_at_utc": utc_now_text(),
        "safety": {
            "mt5_imported": False,
            "order_check_called": False,
            "order_send_called": False,
            "ledger_written": False,
        },
        "records": df.to_dict(orient="records"),
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print("build_gold_multi_strategy_mock_positions")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True))
    print(df[["ticket", "symbol", "direction", "volume", "magic", "comment", "external_id"]].to_string(index=False))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
