#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate guarded demo-send behavior when payload rows are present.

This is a pure signal-present fixture validation.

It does NOT run live scans.
It does NOT call send_mt5_order_from_payload.py.
It does NOT call MetaTrader5.
It does NOT place orders.
It does NOT write production position_registry.csv.

Purpose:
- Move past the need to wait for a real strategy signal by simulating
  payload_rows_out=1.
- Validate the guarded wrapper's send suppression/eligibility decision for a
  payload-present state.
- Keep actual demo order sending as a separate, later, explicitly approved step.

Cases:
1. no flags + payload_rows=1
   -> sender --send must not be eligible
   -> reason SEND_NOT_REQUESTED

2. --send only + payload_rows=1
   -> sender --send must not be eligible
   -> reason ALLOW_DEMO_SEND_NOT_SET

3. --allow-demo-send only + payload_rows=1
   -> sender --send must not be eligible
   -> reason SEND_NOT_REQUESTED

4. --allow-demo-send --send + payload_rows=1
   -> guarded decision says sender --send would be eligible
   -> this validator still does not invoke sender or MT5

Important:
- Case 4 is an eligibility preview only. It proves the double-confirmed gate can
  open for one payload row, but does not execute order_send.
- If the next step is an actual order smoke test while GOLD is closed, use a
  separate BTC manual smoke-test path, not this GOLD strategy-sidecar fixture.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once as guarded_once  # noqa: E402

DEFAULT_OUT_DIR = Path("data/r/gds_signal_present_fixture")
SUMMARY_FILENAME = "latest_gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation_result.json"

FIXTURE_COLUMNS = [
    "payload_key",
    "order_key",
    "signal_key",
    "broker_symbol",
    "symbol",
    "direction",
    "lot",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "magic_number",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "fixture_note",
]

CASE_COLUMNS = [
    "case_name",
    "payload_rows",
    "send_requested",
    "allow_demo_send",
    "expected_pass_send",
    "actual_pass_send",
    "expected_reason",
    "actual_reason",
    "validation_ok",
]


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


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate signal-present guarded demo-send fixture without MT5/order_send.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--fixture-direction", choices=["BUY", "SELL"], default="BUY")
    p.add_argument("--entry-price", type=float, default=2400.0)
    p.add_argument("--sl-price", type=float, default=2390.0)
    p.add_argument("--tp-price", type=float, default=2420.0)
    p.add_argument("--magic", type=int, default=26050601)
    return p.parse_args()


def build_fixture_row(args: argparse.Namespace) -> dict[str, Any]:
    direction = str(args.fixture_direction).upper()
    if direction == "SELL" and not (args.sl_price > args.entry_price > args.tp_price):
        # Keep fixture internally coherent if caller flips direction without prices.
        sl_price = float(args.entry_price) + 10.0
        tp_price = float(args.entry_price) - 20.0
    elif direction == "BUY" and not (args.sl_price < args.entry_price < args.tp_price):
        sl_price = float(args.entry_price) - 10.0
        tp_price = float(args.entry_price) + 20.0
    else:
        sl_price = float(args.sl_price)
        tp_price = float(args.tp_price)

    return {
        "payload_key": "FIXTURE_SIGNAL_PRESENT_PAYLOAD_0001",
        "order_key": "FIXTURE_SIGNAL_PRESENT_ORDER_0001",
        "signal_key": "FIXTURE_SIGNAL_PRESENT_SIGNAL_0001",
        "broker_symbol": str(args.broker_symbol),
        "symbol": str(args.broker_symbol).replace("#", ""),
        "direction": direction,
        "lot": float(args.fixed_lot),
        "entry_price_reference": float(args.entry_price),
        "sl_price": sl_price,
        "tp_price": tp_price,
        "magic_number": int(args.magic),
        "strategy_key": "BUY_C_ENV_RR2_72H" if direction == "BUY" else "SELL_H1H4_BEAR_AB",
        "strategy_alias": "FIXTURE_NO_SEND",
        "strategy_id": "GOLD_SIGNAL_PRESENT_FIXTURE_NO_MT5_NO_ORDER_SEND",
        "condition_id": "GOLD_SIGNAL_PRESENT_FIXTURE_VALIDATION_ONLY",
        "router_strategy_slot": "BUY_C_ENV_RR2_72H" if direction == "BUY" else "SELL_H1H4_BEAR_AB",
        "router_strategy_id": "GOLD_SIGNAL_PRESENT_FIXTURE_VALIDATION_ONLY",
        "candidate_rank": 1,
        "fixture_note": "pure fixture; never invoke sender or MT5 from this validator",
    }


def evaluate_case(*, case_name: str, send: bool, allow_demo_send: bool, payload_rows: int, max_orders: int, expected_pass_send: bool, expected_reason: str) -> dict[str, Any]:
    fixture_args = argparse.Namespace(
        send=bool(send),
        allow_demo_send=bool(allow_demo_send),
        max_orders=int(max_orders),
    )
    actual_pass_send, actual_reason = guarded_once.decide_send_suppression(fixture_args, payload_rows=payload_rows)
    validation_ok = bool(actual_pass_send == expected_pass_send and actual_reason == expected_reason)
    return {
        "case_name": case_name,
        "payload_rows": int(payload_rows),
        "send_requested": bool(send),
        "allow_demo_send": bool(allow_demo_send),
        "expected_pass_send": bool(expected_pass_send),
        "actual_pass_send": bool(actual_pass_send),
        "expected_reason": expected_reason,
        "actual_reason": actual_reason,
        "validation_ok": validation_ok,
    }


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)

    fixture_payload_csv = args.out_dir / "fixture_order_payloads_signal_present.csv"
    case_log_csv = args.out_dir / "signal_present_fixture_case_log.csv"
    summary_json = args.out_dir / SUMMARY_FILENAME

    fixture_row = build_fixture_row(args)
    write_csv(fixture_payload_csv, [fixture_row], FIXTURE_COLUMNS)

    cases = [
        evaluate_case(
            case_name="payload_present_no_flags",
            send=False,
            allow_demo_send=False,
            payload_rows=1,
            max_orders=args.max_orders,
            expected_pass_send=False,
            expected_reason="SEND_NOT_REQUESTED",
        ),
        evaluate_case(
            case_name="payload_present_send_only",
            send=True,
            allow_demo_send=False,
            payload_rows=1,
            max_orders=args.max_orders,
            expected_pass_send=False,
            expected_reason="ALLOW_DEMO_SEND_NOT_SET",
        ),
        evaluate_case(
            case_name="payload_present_allow_only",
            send=False,
            allow_demo_send=True,
            payload_rows=1,
            max_orders=args.max_orders,
            expected_pass_send=False,
            expected_reason="SEND_NOT_REQUESTED",
        ),
        evaluate_case(
            case_name="payload_present_allow_and_send_eligibility_preview",
            send=True,
            allow_demo_send=True,
            payload_rows=1,
            max_orders=args.max_orders,
            expected_pass_send=True,
            expected_reason="",
        ),
    ]
    write_csv(case_log_csv, cases, CASE_COLUMNS)

    failed_cases = [c for c in cases if not c["validation_ok"]]
    validation_ok = len(failed_cases) == 0
    summary = {
        "schema_version": "gold_multi_strategy_guarded_demo_send_signal_present_fixture_validation_v1",
        "validation_time_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "reason": "SIGNAL_PRESENT_FIXTURE_VALIDATION_PASS" if validation_ok else "SIGNAL_PRESENT_FIXTURE_VALIDATION_FAILED",
        "fixture": {
            "payload_rows": 1,
            "broker_symbol": str(args.broker_symbol),
            "direction": str(args.fixture_direction).upper(),
            "fixed_lot": float(args.fixed_lot),
            "fixture_payload_csv": str(fixture_payload_csv),
            "fixture_payload_row": fixture_row,
        },
        "checks_total": len(cases),
        "checks_failed": len(failed_cases),
        "failed_cases": failed_cases,
        "cases": cases,
        "safety": {
            "live_scan_ran": False,
            "sender_invoked": False,
            "mt5_initialized": False,
            "order_check_called": False,
            "order_send_called_count": 0,
            "sent_rows": 0,
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
            "btc_order_smoke_test_performed": False,
        },
        "notes": [
            "This validation intentionally proves guarded eligibility only; it never sends.",
            "If GOLD market is closed and an actual order smoke test is required, create a separate BTC manual smoke-test path with explicit user approval.",
            "Do not treat this fixture row as a real strategy signal.",
        ],
        "outputs": {
            "summary_json": str(summary_json),
            "case_log_csv": str(case_log_csv),
            "fixture_payload_csv": str(fixture_payload_csv),
        },
    }
    write_json(summary_json, summary)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy guarded demo-send signal-present fixture validation", flush=True)
    print(json.dumps({
        "validation_ok": validation_ok,
        "reason": summary["reason"],
        "checks_total": summary["checks_total"],
        "checks_failed": summary["checks_failed"],
        "fixture_payload_csv": str(fixture_payload_csv),
        "case_log_csv": str(case_log_csv),
        "summary_json": str(summary_json),
        "safety": summary["safety"],
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
