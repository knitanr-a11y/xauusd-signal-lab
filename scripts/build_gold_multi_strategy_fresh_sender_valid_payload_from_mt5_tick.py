#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a fresh sender-valid GOLD multi-strategy order_payloads.csv from current MT5 tick.

Purpose:
- Create a non-stale payload whose SL/TP relation is valid against the current tick.
- Validate the real sender dry-run path until DRY_RUN_ORDER_CHECK_OK without using --send.

Safety:
- Imports/initializes MetaTrader5 only to read account/symbol/tick metadata.
- Does not call mt5.order_check.
- Does not call mt5.order_send.
- Does not mutate ledgers.
- Does not mutate trigger state.
- Does not write production registry.

Default output is a SELL_H1H4_BEAR_AB / B_ONLY_SAFE style payload with:
- SELL price reference = bid
- sl_price = bid + 10.0
- tp_price = bid - 20.0
- lot = 0.01
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

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as e:  # pragma: no cover
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(e)
else:
    MT5_IMPORT_ERROR = ""

SCHEMA_VERSION = "gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick_v1"

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_sender_registry_preview/fresh_sender_valid_payload")
DEFAULT_STRATEGY_SLOT = "SELL_H1H4_BEAR_AB"
DEFAULT_STRATEGY_ID = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"
DEFAULT_CONDITION_ID = "B_ONLY_SAFE"
DEFAULT_MAGIC = 26050601


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build fresh sender-valid order_payloads.csv from current MT5 tick. No order_check/order_send.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="SELL")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--sl-distance", type=float, default=10.0)
    p.add_argument("--tp-distance", type=float, default=20.0)
    p.add_argument("--strategy-slot", default=DEFAULT_STRATEGY_SLOT)
    p.add_argument("--strategy-id", default=DEFAULT_STRATEGY_ID)
    p.add_argument("--condition-id", default=DEFAULT_CONDITION_ID)
    p.add_argument("--magic-number", type=int, default=DEFAULT_MAGIC)
    p.add_argument("--comment-prefix", default="ms")
    p.add_argument("--expected-login", type=int, default=None)
    p.add_argument("--require-demo-account", action="store_true")
    p.add_argument("--allow-live-account", action="store_true")
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument("--select-symbol", action="store_true")
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


def slug_time() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def asdict_obj(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        raw = obj._asdict()
    elif isinstance(obj, dict):
        raw = obj
    else:
        raw = {"value": str(obj)}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        try:
            json.dumps(v)
            out[str(k)] = v
        except TypeError:
            out[str(k)] = str(v)
    return out


def write_csv(df: pd.DataFrame, path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def finite_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
    except Exception:
        return float(default)
    if not math.isfinite(v):
        return float(default)
    return float(v)


def build_prices(direction: str, bid: float, ask: float, sl_distance: float, tp_distance: float, digits: int) -> tuple[float, float, float]:
    d = direction.upper()
    if d == "BUY":
        entry = ask
        sl = entry - float(sl_distance)
        tp = entry + float(tp_distance)
    else:
        entry = bid
        sl = entry + float(sl_distance)
        tp = entry - float(tp_distance)
    return round(entry, digits), round(sl, digits), round(tp, digits)


def validate_prices(direction: str, entry: float, sl: float, tp: float) -> list[str]:
    if direction.upper() == "BUY":
        if not sl < entry:
            return [f"BUY invalid SL relation: sl={sl}; entry={entry}"]
        if not tp > entry:
            return [f"BUY invalid TP relation: tp={tp}; entry={entry}"]
    elif direction.upper() == "SELL":
        if not sl > entry:
            return [f"SELL invalid SL relation: sl={sl}; entry={entry}"]
        if not tp < entry:
            return [f"SELL invalid TP relation: tp={tp}; entry={entry}"]
    else:
        return [f"invalid direction: {direction}"]
    return []


def build_payload_row(args: argparse.Namespace, tick: dict[str, Any], symbol_info: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    digits = int(symbol_info.get("digits", 2) or 2)
    bid = finite_float(tick.get("bid"), 0.0)
    ask = finite_float(tick.get("ask"), 0.0)
    entry, sl, tp = build_prices(args.direction, bid, ask, args.sl_distance, args.tp_distance, digits)
    validation_errors = validate_prices(args.direction, entry, sl, tp)
    ts = slug_time()
    signal_key = f"FRESH_SENDER_VALID|{args.strategy_slot}|{args.symbol}|{args.direction}|{args.condition_id}|{ts}"
    order_key = f"{signal_key}|MOCHIPOYO_PAYLOAD"
    comment = f"{args.comment_prefix} {args.strategy_slot} {args.direction}"[:31]
    row = {
        "payload_created_at_utc": utc_now_text(),
        "symbol": args.symbol,
        "broker_symbol": args.broker_symbol,
        "direction": args.direction,
        "lot": float(args.lot),
        "entry_price_reference": entry,
        "entry_price": entry,
        "sl_price": sl,
        "tp_price": tp,
        "magic_number": int(args.magic_number),
        "comment": comment,
        "strategy_id": args.strategy_id,
        "router_strategy_id": args.strategy_id,
        "router_strategy_slot": args.strategy_slot,
        "pair_name": args.strategy_slot,
        "condition_id": args.condition_id,
        "candidate_rank": 1,
        "signal_key": signal_key,
        "order_key": order_key,
        "payload_key": order_key,
        "source": "fresh_sender_valid_payload_from_mt5_tick",
        "tick_bid": bid,
        "tick_ask": ask,
        "tick_time": tick.get("time", ""),
        "tick_time_msc": tick.get("time_msc", ""),
        "digits": digits,
        "sl_distance": float(args.sl_distance),
        "tp_distance": float(args.tp_distance),
    }
    meta = {
        "validation_errors": validation_errors,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "bid": bid,
        "ask": ask,
        "digits": digits,
    }
    return row, meta


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": mt5 is not None,
        "order_check_called_count": 0,
        "order_send_called_count": 0,
        "ledger_mutated": False,
        "trigger_state_mutated": False,
        "production_registry_mutated": False,
    }


def main() -> int:
    args = parse_args()
    Path(windows_long_path(args.out_dir)).mkdir(parents=True, exist_ok=True)
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / "order_payloads.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / "fresh_sender_valid_payload_summary.json"

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "build_ok": False,
        "reason": "STARTED",
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "broker_symbol": args.broker_symbol,
        "direction": args.direction,
        "lot": float(args.lot),
        "mt5_import_ok": mt5 is not None,
        "mt5_import_error": MT5_IMPORT_ERROR,
        "safety": safety_summary(),
    }

    if mt5 is None:
        summary["reason"] = "MT5_IMPORT_FAILED"
        write_json(output_json, summary)
        print("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 2

    init_kwargs: dict[str, Any] = {}
    if args.terminal_path:
        init_kwargs["path"] = args.terminal_path
    if args.portable:
        init_kwargs["portable"] = True
    initialized = bool(mt5.initialize(**init_kwargs))
    summary["initialize_ok"] = initialized
    summary["last_error_after_initialize"] = str(mt5.last_error())
    if not initialized:
        summary["reason"] = "MT5_INITIALIZE_FAILED"
        write_json(output_json, summary)
        print("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 3

    try:
        terminal_info = asdict_obj(mt5.terminal_info())
        account_info = asdict_obj(mt5.account_info())
        summary["terminal_info"] = terminal_info
        summary["account_info"] = account_info
        guard_errors: list[str] = []
        if args.expected_login is not None and int(account_info.get("login") or -1) != int(args.expected_login):
            guard_errors.append(f"expected_login mismatch: expected={args.expected_login}; actual={account_info.get('login')}")
        if args.require_demo_account and not args.allow_live_account and not account_looks_demo(account_info):
            guard_errors.append("require_demo_account is set but account/server/company does not look like demo")
        if guard_errors:
            summary["reason"] = "ACCOUNT_GUARD_FAILED"
            summary["guard_errors"] = guard_errors
            write_json(output_json, summary)
            print("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick")
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
            return 4

        if args.select_symbol:
            summary["symbol_select_ok"] = bool(mt5.symbol_select(args.broker_symbol, True))
            summary["last_error_after_symbol_select"] = str(mt5.last_error())

        symbol_info = asdict_obj(mt5.symbol_info(args.broker_symbol))
        tick = asdict_obj(mt5.symbol_info_tick(args.broker_symbol))
        if not symbol_info or not tick:
            summary["reason"] = "SYMBOL_INFO_OR_TICK_NOT_FOUND"
            summary["symbol_info_found"] = bool(symbol_info)
            summary["tick_found"] = bool(tick)
            write_json(output_json, summary)
            print("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick")
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
            return 5

        row, meta = build_payload_row(args, tick, symbol_info)
        if meta["validation_errors"]:
            summary["reason"] = "LOCAL_PRICE_RELATION_INVALID"
            summary["validation_errors"] = meta["validation_errors"]
            summary["price_meta"] = meta
            write_json(output_json, summary)
            print("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick")
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
            return 6

        df = pd.DataFrame([row])
        write_csv(df, output_csv)
        summary.update({
            "build_ok": True,
            "reason": "FRESH_SENDER_VALID_PAYLOAD_BUILT",
            "rows_out": 1,
            "price_meta": meta,
            "signal_key": row["signal_key"],
            "order_key": row["order_key"],
            "safety": safety_summary(),
        })
        write_json(output_json, summary)
        print("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick")
        print(json.dumps({k: v for k, v in summary.items() if k not in {"terminal_info", "account_info"}}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        print(df[["broker_symbol", "direction", "lot", "entry_price_reference", "sl_price", "tp_price", "strategy_id", "router_strategy_slot", "signal_key"]].to_string(index=False))
        print(f"output_csv: {output_csv}")
        print(f"output_json: {output_json}")
        print("done")
        return 0
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
