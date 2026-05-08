#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build controlled order_payloads.csv for position-policy preflight tests.

This script is intentionally offline / file-only.
It does NOT import MetaTrader5.
It does NOT call order_check or order_send.
It does NOT write to any live ledger.

Purpose:
- Create small, explicit payload CSVs for validating
  scripts/run_gold_multi_strategy_position_policy_preflight_v2.py
- Test the future policy before modifying send_mt5_order_from_payload.py

Default scenario:
- opposite_sell
  Existing account currently has GOLD# BUY, so this creates a SELL payload.
  Expected preflight result: opposite_direction_blocked=true and final_policy_decision=BLOCK.

Other useful scenarios:
- same_direction_buy
  Existing account currently has GOLD# BUY, so this creates a BUY payload.
  Expected with default v2: ALLOW unless duplicate/lot/total cap blocks,
  because same_strategy cannot be detected from current MT5 comment unless strategy metadata exists.

- over_lot_sell
  Creates SELL lot=0.03.
  Expected: per_order_lot_blocked=true and final_policy_decision=BLOCK.

- duplicate_pair
  Creates two identical rows.
  Expected: second row duplicate_key_blocked=true and final_policy_decision=BLOCK.
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
DEFAULT_MAGIC = 26050601

OUTPUT_COLUMNS = [
    "order_index",
    "order_status",
    "is_valid_order_payload",
    "validation_errors",
    "symbol",
    "broker_symbol",
    "direction",
    "order_type",
    "lot",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "rr",
    "stop_distance",
    "take_distance",
    "magic_number",
    "comment",
    "payload_key",
    "order_key",
    "pair_name",
    "candidate_rank",
    "candidate_name",
    "signal_close_time",
    "entry_time",
    "live_window_status",
    "ledger_status",
    "strategy_id",
    "condition_id",
    "signal_key",
    "router_strategy_slot",
    "router_strategy_id",
    "router_source_path",
    "adapter_preview_key",
]

SCENARIOS = {
    "opposite_sell",
    "same_direction_buy",
    "over_lot_sell",
    "duplicate_pair",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build controlled policy-test order_payloads.csv. No MT5 calls.")
    p.add_argument("--scenario", choices=sorted(SCENARIOS), default="opposite_sell")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--magic", type=int, default=DEFAULT_MAGIC)
    p.add_argument("--entry-price", type=float, default=4727.67, help="Reference price only; preflight does not validate execution price.")
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


def normalize_price(v: float) -> float:
    return round(float(v), 3)


def build_row(
    *,
    order_index: int,
    scenario: str,
    direction: str,
    lot: float,
    broker_symbol: str,
    entry_price: float,
    magic: int,
    duplicate_suffix: str = "",
) -> dict[str, Any]:
    direction = direction.upper()
    rr = 2.0
    if direction == "BUY":
        sl = normalize_price(entry_price - 10.0)
        tp = normalize_price(entry_price + 20.0)
        stop_distance = normalize_price(entry_price - sl)
        take_distance = normalize_price(tp - entry_price)
        strategy_slot = "BUY_C_ENV_RR2_72H"
        strategy_id = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H"
        condition_id = strategy_id
        rank = "POLICY_TEST_BUY"
    else:
        sl = normalize_price(entry_price + 10.0)
        tp = normalize_price(entry_price - 20.0)
        stop_distance = normalize_price(sl - entry_price)
        take_distance = normalize_price(entry_price - tp)
        strategy_slot = "SELL_H1H4_BEAR_AB"
        strategy_id = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"
        condition_id = strategy_id
        rank = "POLICY_TEST_SELL"

    signal_time = utc_now_text()
    key_base = f"POLICY_TEST|{scenario}|{direction}|{lot:.2f}|{strategy_slot}"
    if duplicate_suffix:
        key_base = f"{key_base}|{duplicate_suffix}"
    payload_key = f"{key_base}|MOCHIPOYO_PAYLOAD"
    return {
        "order_index": int(order_index),
        "order_status": "DRY_RUN_READY",
        "is_valid_order_payload": True,
        "validation_errors": "",
        "symbol": "GOLD",
        "broker_symbol": broker_symbol,
        "direction": direction,
        "order_type": "MARKET",
        "lot": float(lot),
        "entry_price_reference": normalize_price(entry_price),
        "sl_price": sl,
        "tp_price": tp,
        "rr": rr,
        "stop_distance": stop_distance,
        "take_distance": take_distance,
        "magic_number": int(magic),
        "comment": f"policy {direction} {strategy_slot}"[:31],
        "payload_key": payload_key,
        "order_key": payload_key,
        "pair_name": strategy_slot,
        "candidate_rank": rank,
        "candidate_name": condition_id,
        "signal_close_time": signal_time,
        "entry_time": signal_time,
        "live_window_status": "POLICY_PREFLIGHT_TEST_ONLY",
        "ledger_status": "POLICY_TEST_READY",
        "strategy_id": strategy_id,
        "condition_id": condition_id,
        "signal_key": key_base,
        "router_strategy_slot": strategy_slot,
        "router_strategy_id": strategy_id,
        "router_source_path": "POLICY_TEST_PAYLOAD_BUILDER",
        "adapter_preview_key": f"{key_base}|ADAPTER_PREVIEW",
    }


def scenario_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    scenario = str(args.scenario)
    entry = float(args.entry_price)
    if scenario == "opposite_sell":
        return [build_row(order_index=1, scenario=scenario, direction="SELL", lot=0.01, broker_symbol=args.broker_symbol, entry_price=entry, magic=args.magic)]
    if scenario == "same_direction_buy":
        return [build_row(order_index=1, scenario=scenario, direction="BUY", lot=0.01, broker_symbol=args.broker_symbol, entry_price=entry, magic=args.magic)]
    if scenario == "over_lot_sell":
        return [build_row(order_index=1, scenario=scenario, direction="SELL", lot=0.03, broker_symbol=args.broker_symbol, entry_price=entry, magic=args.magic)]
    if scenario == "duplicate_pair":
        row = build_row(order_index=1, scenario=scenario, direction="SELL", lot=0.01, broker_symbol=args.broker_symbol, entry_price=entry, magic=args.magic)
        row2 = dict(row)
        row2["order_index"] = 2
        return [row, row2]
    raise ValueError(f"unknown scenario: {scenario}")


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / f"order_payloads_policy_test_{args.scenario}.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / f"order_payloads_policy_test_{args.scenario}.json"

    rows = scenario_rows(args)
    df = pd.DataFrame([{col: row.get(col, "") for col in OUTPUT_COLUMNS} for row in rows], columns=OUTPUT_COLUMNS)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(output_csv), index=False, encoding="utf-8-sig")

    summary = {
        "schema_version": "gold_multi_strategy_position_policy_test_payload_v1",
        "scenario": args.scenario,
        "rows_out": int(len(df)),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "broker_symbol": args.broker_symbol,
        "magic": int(args.magic),
        "entry_price_reference": float(args.entry_price),
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

    print("build_gold_multi_strategy_position_policy_test_payload")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True))
    print(df[["order_index", "broker_symbol", "direction", "lot", "strategy_id", "signal_key", "order_key"]].to_string(index=False))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
