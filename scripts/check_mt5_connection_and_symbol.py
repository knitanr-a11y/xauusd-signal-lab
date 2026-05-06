#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check MT5 connection and inspect a broker symbol without placing orders.

This script is intentionally read-only:
- initializes MetaTrader5 Python package
- optionally selects a symbol in Market Watch
- prints account/terminal/symbol/tick information
- writes CSV/JSON reports
- DOES NOT send orders
- DOES NOT modify positions
"""
from __future__ import annotations

import argparse
import json
import os
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


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding=encoding, newline="") as f:
        f.write(text)


def asdict_obj(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        d = obj._asdict()
    else:
        d = dict(obj) if isinstance(obj, dict) else {"value": str(obj)}
    out: dict[str, Any] = {}
    for k, v in d.items():
        try:
            json.dumps(v)
            out[k] = v
        except TypeError:
            out[k] = str(v)
    return out


def compact_symbol_fields(symbol_info: dict[str, Any], tick: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "name",
        "path",
        "description",
        "trade_mode",
        "trade_calc_mode",
        "digits",
        "point",
        "trade_contract_size",
        "volume_min",
        "volume_max",
        "volume_step",
        "trade_stops_level",
        "trade_freeze_level",
        "spread",
        "spread_float",
        "currency_base",
        "currency_profit",
        "currency_margin",
        "visible",
        "select",
    ]
    row = {k: symbol_info.get(k) for k in keys if k in symbol_info}
    row.update({
        "tick_time": tick.get("time"),
        "bid": tick.get("bid"),
        "ask": tick.get("ask"),
        "last": tick.get("last"),
        "tick_volume": tick.get("volume"),
    })
    bid = tick.get("bid")
    ask = tick.get("ask")
    point = symbol_info.get("point")
    try:
        row["spread_price"] = float(ask) - float(bid)
    except Exception:
        row["spread_price"] = None
    try:
        row["spread_points_from_tick"] = (float(ask) - float(bid)) / float(point)
    except Exception:
        row["spread_points_from_tick"] = None
    return row


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Read-only MT5 connection and symbol check.")
    p.add_argument("--symbol", required=True, help="Broker symbol name, e.g. GOLD, GOLD#, XAUUSD")
    p.add_argument("--out-dir", default="data/mt5_connection_check")
    p.add_argument("--portable", action="store_true", help="Pass portable=True to mt5.initialize")
    p.add_argument("--terminal-path", default=None, help="Optional explicit terminal64.exe path")
    p.add_argument("--login", type=int, default=None, help="Optional account login. Usually not needed when MT5 is already logged in.")
    p.add_argument("--password", default=None, help="Optional account password. Avoid using this unless needed.")
    p.add_argument("--server", default=None, help="Optional broker server. Avoid using this unless needed.")
    p.add_argument("--select-symbol", action="store_true", help="Call mt5.symbol_select(symbol, True) before reading info.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "symbol_requested": args.symbol,
        "mt5_import_ok": mt5 is not None,
        "mt5_import_error": MT5_IMPORT_ERROR,
        "initialize_ok": False,
        "last_error": None,
        "symbol_select_ok": None,
        "symbol_info_ok": False,
        "symbol_tick_ok": False,
        "read_only": True,
        "order_sent": False,
    }

    if mt5 is None:
        write_text(out_dir / "mt5_connection_report.json", json.dumps(report, ensure_ascii=False, indent=2))
        print("check_mt5_connection_and_symbol")
        print("ERROR: MetaTrader5 package import failed")
        print(MT5_IMPORT_ERROR)
        return 2

    init_kwargs: dict[str, Any] = {}
    if args.terminal_path:
        init_kwargs["path"] = args.terminal_path
    if args.login is not None:
        init_kwargs["login"] = int(args.login)
    if args.password:
        init_kwargs["password"] = args.password
    if args.server:
        init_kwargs["server"] = args.server
    if args.portable:
        init_kwargs["portable"] = True

    initialized = False
    try:
        initialized = bool(mt5.initialize(**init_kwargs))
        report["initialize_ok"] = initialized
        report["last_error"] = mt5.last_error()
        if not initialized:
            print("check_mt5_connection_and_symbol")
            print("ERROR: mt5.initialize failed")
            print(f"last_error: {report['last_error']}")
            write_text(out_dir / "mt5_connection_report.json", json.dumps(report, ensure_ascii=False, indent=2))
            return 3

        terminal_info = asdict_obj(mt5.terminal_info())
        account_info = asdict_obj(mt5.account_info())
        version = mt5.version()
        report["terminal_info"] = terminal_info
        report["account_info"] = account_info
        report["version"] = version

        if args.select_symbol:
            report["symbol_select_ok"] = bool(mt5.symbol_select(args.symbol, True))
            report["last_error_after_symbol_select"] = mt5.last_error()

        info = mt5.symbol_info(args.symbol)
        tick = mt5.symbol_info_tick(args.symbol)
        symbol_info = asdict_obj(info)
        tick_info = asdict_obj(tick)
        report["symbol_info_ok"] = bool(symbol_info)
        report["symbol_tick_ok"] = bool(tick_info)
        report["symbol_info"] = symbol_info
        report["tick_info"] = tick_info
        report["last_error_after_symbol_read"] = mt5.last_error()

        compact = compact_symbol_fields(symbol_info, tick_info)
        write_csv(pd.DataFrame([compact]), out_dir / "mt5_symbol_compact.csv")
        write_csv(pd.DataFrame([terminal_info]), out_dir / "mt5_terminal_info.csv")
        write_csv(pd.DataFrame([account_info]), out_dir / "mt5_account_info.csv")
        write_text(out_dir / "mt5_connection_report.json", json.dumps(report, ensure_ascii=False, indent=2, default=str))

        print("check_mt5_connection_and_symbol")
        print(f"symbol: {args.symbol}")
        print(f"initialize_ok: {initialized}")
        print(f"symbol_select_ok: {report['symbol_select_ok']}")
        print(f"symbol_info_ok: {report['symbol_info_ok']}")
        print(f"symbol_tick_ok: {report['symbol_tick_ok']}")
        print(f"terminal_connected: {terminal_info.get('connected')}")
        print(f"account_login: {account_info.get('login')}")
        print(f"account_server: {account_info.get('server')}")
        print(f"trade_allowed_terminal: {terminal_info.get('trade_allowed')}")
        print(f"trade_allowed_account: {account_info.get('trade_allowed')}")
        print(f"bid: {tick_info.get('bid')}")
        print(f"ask: {tick_info.get('ask')}")
        print(f"digits: {symbol_info.get('digits')}")
        print(f"point: {symbol_info.get('point')}")
        print(f"volume_min: {symbol_info.get('volume_min')}")
        print(f"volume_step: {symbol_info.get('volume_step')}")
        print(f"volume_max: {symbol_info.get('volume_max')}")
        print(f"trade_stops_level: {symbol_info.get('trade_stops_level')}")
        print(f"trade_freeze_level: {symbol_info.get('trade_freeze_level')}")
        print(f"spread_points_symbol: {symbol_info.get('spread')}")
        print(f"spread_price_tick: {compact.get('spread_price')}")
        print(f"out_dir: {out_dir}")
        print("order_sent: False")
        print("done")
        return 0 if report["symbol_info_ok"] and report["symbol_tick_ok"] else 1
    finally:
        if initialized:
            mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
