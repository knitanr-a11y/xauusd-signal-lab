#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC manual demo close smoke test PREVIEW.

This script is READ-ONLY with respect to trading.

Purpose:
- Inspect current BTCUSD# demo positions created by manual smoke tests.
- Build close-intent preview rows for the matching positions.
- Do NOT call order_send.
- Do NOT close positions.
- Do NOT write production position_registry.csv.

This is NOT a strategy close engine.
This is NOT BTC strategy integration.
This is only a manual close preview for demo smoke-test positions.

Safety:
- Requires expected-login by default.
- Requires demo-account guard by default.
- Uses isolated output directory.
- Filters by symbol BTCUSD# by default.
- Optionally filters by magic numbers used by the BTC manual smoke tests.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as exc:  # pragma: no cover
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(exc)
else:
    MT5_IMPORT_ERROR = ""

DEFAULT_OUT_DIR = Path("data/r/btc_manual_demo_close_smoke_test_preview")
SUMMARY_FILENAME = "latest_btc_manual_demo_close_smoke_test_preview_result.json"

POSITIONS_COLUMNS = [
    "position_ticket",
    "time",
    "time_msc",
    "symbol",
    "type",
    "direction",
    "volume",
    "price_open",
    "price_current",
    "sl",
    "tp",
    "profit",
    "swap",
    "magic",
    "comment",
    "identifier",
    "reason",
]

CLOSE_INTENT_COLUMNS = [
    "close_intent_key",
    "position_ticket",
    "symbol",
    "position_direction",
    "close_direction",
    "volume",
    "price_open",
    "price_current",
    "sl",
    "tp",
    "profit",
    "magic",
    "comment",
    "source",
    "preview_note",
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


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def asdict_obj(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        d = obj._asdict()
    elif isinstance(obj, dict):
        d = obj
    else:
        d = {"value": str(obj)}
    out: dict[str, Any] = {}
    for k, v in d.items():
        try:
            json.dumps(v)
            out[k] = v
        except TypeError:
            out[k] = str(v)
    return out


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def parse_int_set(text: str) -> set[int]:
    out: set[int] = set()
    for part in str(text).replace(";", ",").split(","):
        s = part.strip()
        if not s:
            continue
        out.add(int(s))
    return out


def mt5_initialize_or_raise(terminal_path: str | None, portable: bool) -> None:
    if mt5 is None:
        raise RuntimeError(f"MetaTrader5 import failed: {MT5_IMPORT_ERROR}")
    if terminal_path:
        ok = mt5.initialize(path=terminal_path, portable=portable)
    else:
        ok = mt5.initialize()
    if not ok:
        raise RuntimeError(f"mt5.initialize failed: last_error={mt5.last_error()}")


def account_looks_demo(account_info: dict[str, Any]) -> bool:
    haystack = " ".join(str(account_info.get(k, "")) for k in ["name", "server", "company"]).lower()
    return "demo" in haystack


def direction_from_position_type(pos_type: Any) -> str:
    t = safe_int(pos_type, -1)
    if mt5 is not None:
        if t == mt5.POSITION_TYPE_BUY:
            return "BUY"
        if t == mt5.POSITION_TYPE_SELL:
            return "SELL"
    if t == 0:
        return "BUY"
    if t == 1:
        return "SELL"
    return f"UNKNOWN_{t}"


def close_direction_from_position_direction(direction: str) -> str:
    d = str(direction).upper()
    if d == "BUY":
        return "SELL"
    if d == "SELL":
        return "BUY"
    return "UNKNOWN"


def build_position_row(pos: Any) -> dict[str, Any]:
    d = asdict_obj(pos)
    direction = direction_from_position_type(d.get("type"))
    return {
        "position_ticket": d.get("ticket", ""),
        "time": d.get("time", ""),
        "time_msc": d.get("time_msc", ""),
        "symbol": d.get("symbol", ""),
        "type": d.get("type", ""),
        "direction": direction,
        "volume": d.get("volume", ""),
        "price_open": d.get("price_open", ""),
        "price_current": d.get("price_current", ""),
        "sl": d.get("sl", ""),
        "tp": d.get("tp", ""),
        "profit": d.get("profit", ""),
        "swap": d.get("swap", ""),
        "magic": d.get("magic", ""),
        "comment": d.get("comment", ""),
        "identifier": d.get("identifier", ""),
        "reason": d.get("reason", ""),
    }


def build_close_intent_row(position_row: dict[str, Any], index: int) -> dict[str, Any]:
    ticket = position_row.get("position_ticket", "")
    symbol = position_row.get("symbol", "")
    direction = position_row.get("direction", "")
    return {
        "close_intent_key": f"BTC_MANUAL_CLOSE_PREVIEW_{symbol}_{ticket}_{utc_stamp()}_{index:03d}",
        "position_ticket": ticket,
        "symbol": symbol,
        "position_direction": direction,
        "close_direction": close_direction_from_position_direction(str(direction)),
        "volume": position_row.get("volume", ""),
        "price_open": position_row.get("price_open", ""),
        "price_current": position_row.get("price_current", ""),
        "sl": position_row.get("sl", ""),
        "tp": position_row.get("tp", ""),
        "profit": position_row.get("profit", ""),
        "magic": position_row.get("magic", ""),
        "comment": position_row.get("comment", ""),
        "source": "btc_manual_close_preview_no_order_send",
        "preview_note": "preview only; no order_send; no close executed",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Preview BTC manual demo close smoke-test positions. No order_send.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol", default="BTCUSD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--magic-filter", default="26050603", help="Comma-separated magic numbers to include. Use empty string to disable magic filtering.")
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    positions_csv = args.out_dir / "btc_manual_positions_preview.csv"
    close_intents_csv = args.out_dir / "btc_manual_close_intents_preview.csv"
    summary_json = args.out_dir / SUMMARY_FILENAME

    magic_filter = parse_int_set(args.magic_filter) if str(args.magic_filter).strip() else set()

    print("=" * 80, flush=True)
    print("BTC manual demo close smoke test PREVIEW - NO ORDER_SEND", flush=True)
    print("This is not a strategy close. It only reads positions and writes close-intent preview rows.", flush=True)
    print(f"symbol={args.symbol} expected_login={args.expected_login} require_demo_account={args.require_demo_account}", flush=True)
    print(f"magic_filter={sorted(magic_filter) if magic_filter else 'disabled'}", flush=True)
    print("=" * 80, flush=True)

    init_ok = False
    account_info: dict[str, Any] = {}
    all_position_rows: list[dict[str, Any]] = []
    matched_position_rows: list[dict[str, Any]] = []
    close_intent_rows: list[dict[str, Any]] = []

    try:
        mt5_initialize_or_raise(args.terminal_path, bool(args.portable))
        init_ok = True
        assert mt5 is not None
        account_raw = mt5.account_info()
        account_info = asdict_obj(account_raw)
        if not account_info:
            raise RuntimeError(f"mt5.account_info returned empty: last_error={mt5.last_error()}")
        actual_login = safe_int(account_info.get("login"), 0)
        if int(args.expected_login) != actual_login:
            raise RuntimeError(f"expected-login mismatch: expected={args.expected_login}; actual={actual_login}")
        if args.require_demo_account and not account_looks_demo(account_info):
            raise RuntimeError(f"require-demo-account guard failed: account_info={account_info}")

        positions_raw = mt5.positions_get(symbol=args.symbol)
        if positions_raw is None:
            positions_raw = []
        all_position_rows = [build_position_row(pos) for pos in positions_raw]
        for row in all_position_rows:
            magic = safe_int(row.get("magic"), 0)
            if magic_filter and magic not in magic_filter:
                continue
            matched_position_rows.append(row)
        close_intent_rows = [build_close_intent_row(row, i + 1) for i, row in enumerate(matched_position_rows)]
    finally:
        if init_ok and mt5 is not None:
            mt5.shutdown()

    write_csv(positions_csv, matched_position_rows, POSITIONS_COLUMNS)
    write_csv(close_intents_csv, close_intent_rows, CLOSE_INTENT_COLUMNS)

    matched_total_volume = round(sum(safe_float(r.get("volume"), 0.0) for r in matched_position_rows), 8)
    matched_total_profit = round(sum(safe_float(r.get("profit"), 0.0) for r in matched_position_rows), 2)
    preview_ok = True
    summary = {
        "schema_version": "btc_manual_demo_close_smoke_test_preview_v1",
        "cycle_time_utc": utc_now_text(),
        "preview_ok": preview_ok,
        "reason": "BTC_MANUAL_DEMO_CLOSE_SMOKE_TEST_PREVIEW_PASS",
        "mode": "PREVIEW_ONLY_NO_ORDER_SEND",
        "symbol": args.symbol,
        "magic_filter": sorted(magic_filter) if magic_filter else [],
        "account_info": account_info,
        "positions_total_for_symbol": len(all_position_rows),
        "positions_matched": len(matched_position_rows),
        "matched_total_volume": matched_total_volume,
        "matched_total_profit": matched_total_profit,
        "close_intent_rows": len(close_intent_rows),
        "safety": {
            "order_send_called_count": 0,
            "close_executed_count": 0,
            "production_registry_mutated": False,
            "gold_strategy_signal_used": False,
            "btc_strategy_integration_used": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
        },
        "paths": {
            "positions_csv": str(positions_csv),
            "close_intents_csv": str(close_intents_csv),
            "summary_json": str(summary_json),
        },
        "positions": matched_position_rows,
        "close_intents": close_intent_rows,
    }
    write_json(summary_json, summary)

    print(json.dumps({
        "preview_ok": preview_ok,
        "reason": summary["reason"],
        "symbol": args.symbol,
        "positions_total_for_symbol": len(all_position_rows),
        "positions_matched": len(matched_position_rows),
        "matched_total_volume": matched_total_volume,
        "matched_total_profit": matched_total_profit,
        "close_intent_rows": len(close_intent_rows),
        "order_send_called_count": 0,
        "close_executed_count": 0,
        "positions_csv": str(positions_csv),
        "close_intents_csv": str(close_intents_csv),
        "summary_json": str(summary_json),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
