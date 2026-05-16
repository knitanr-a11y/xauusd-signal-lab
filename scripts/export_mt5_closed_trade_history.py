#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Export MT5 closed trade history for the trade AI review journal.

This script is read-only. It does not place, modify, or close orders.

Outputs:
- mt5_history_deals.csv
- mt5_history_orders.csv
- mt5_history_positions.csv
- latest_mt5_closed_trade_history_export.json

The position summary is grouped mainly by position_id where available. It is not
intended to replace the strategy order ledger. It is a raw MT5 history export
used by build_trade_outcome_ledger_from_order_ledger.py.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as exc:  # pragma: no cover
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = repr(exc)
else:
    MT5_IMPORT_ERROR = ""

from trade_ai_review_utils import (
    asdict_list,
    clean_float,
    clean_int,
    clean_str,
    normalize_direction,
    normalize_symbol_from_broker,
    utc_now_text,
    windows_long_path,
    write_csv,
    write_json,
)

SUMMARY_FILENAME = "latest_mt5_closed_trade_history_export.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export MT5 closed deal/order history for AI trade review.")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--date-from", default=None, help="YYYY-MM-DD or YYYY-MM-DD HH:MM:SS. Default: now - lookback-days.")
    p.add_argument("--date-to", default=None, help="YYYY-MM-DD or YYYY-MM-DD HH:MM:SS. Default: now.")
    p.add_argument("--lookback-days", type=int, default=30)
    p.add_argument("--symbols", default="", help="Comma-separated broker symbols to keep, e.g. GOLD#,BTCUSD#. Empty = all.")
    p.add_argument("--expected-login", type=int, default=None)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    return p.parse_args()


def parse_dt(text: str | None, *, default: datetime) -> datetime:
    if not text:
        return default
    ts = pd.to_datetime(text, errors="raise")
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is not None:
            ts = ts.tz_convert(None)
        return ts.to_pydatetime()
    return default


def parse_symbols(text: str) -> set[str]:
    out: set[str] = set()
    for part in str(text or "").replace(";", ",").split(","):
        s = part.strip()
        if s:
            out.add(s)
    return out


def deal_entry_label(value: Any) -> str:
    try:
        v = int(value)
    except Exception:
        return clean_str(value)
    if mt5 is not None:
        mapping = {
            int(mt5.DEAL_ENTRY_IN): "IN",
            int(mt5.DEAL_ENTRY_OUT): "OUT",
            int(getattr(mt5, "DEAL_ENTRY_INOUT", -9999)): "INOUT",
            int(getattr(mt5, "DEAL_ENTRY_OUT_BY", -9998)): "OUT_BY",
        }
        if v in mapping:
            return mapping[v]
    fallback = {0: "IN", 1: "OUT", 2: "INOUT", 3: "OUT_BY"}
    return fallback.get(v, str(v))


def deal_type_direction(value: Any) -> str:
    try:
        v = int(value)
    except Exception:
        return ""
    if mt5 is not None:
        if v == int(mt5.DEAL_TYPE_BUY):
            return "BUY"
        if v == int(mt5.DEAL_TYPE_SELL):
            return "SELL"
    if v == 0:
        return "BUY"
    if v == 1:
        return "SELL"
    return ""


def order_type_direction(value: Any) -> str:
    try:
        v = int(value)
    except Exception:
        return ""
    if mt5 is not None:
        buy_types = {int(mt5.ORDER_TYPE_BUY), int(getattr(mt5, "ORDER_TYPE_BUY_LIMIT", -1)), int(getattr(mt5, "ORDER_TYPE_BUY_STOP", -2)), int(getattr(mt5, "ORDER_TYPE_BUY_STOP_LIMIT", -3))}
        sell_types = {int(mt5.ORDER_TYPE_SELL), int(getattr(mt5, "ORDER_TYPE_SELL_LIMIT", -4)), int(getattr(mt5, "ORDER_TYPE_SELL_STOP", -5)), int(getattr(mt5, "ORDER_TYPE_SELL_STOP_LIMIT", -6))}
        if v in buy_types:
            return "BUY"
        if v in sell_types:
            return "SELL"
    if v in {0, 2, 4, 6}:
        return "BUY"
    if v in {1, 3, 5, 7}:
        return "SELL"
    return ""


def time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["time", "time_msc", "time_setup", "time_setup_msc", "time_done", "time_done_msc"]:
        if col not in out.columns:
            continue
        if col.endswith("_msc"):
            out[col + "_text"] = pd.to_datetime(pd.to_numeric(out[col], errors="coerce"), unit="ms", errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            out[col + "_text"] = pd.to_datetime(pd.to_numeric(out[col], errors="coerce"), unit="s", errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def build_position_summary(deals_df: pd.DataFrame, orders_df: pd.DataFrame) -> pd.DataFrame:
    if deals_df.empty:
        return pd.DataFrame()
    df = deals_df.copy()
    if "position_id" not in df.columns:
        df["position_id"] = 0
    df["entry_label"] = df.get("entry", pd.Series(dtype=object)).map(deal_entry_label)
    df["deal_direction"] = df.get("type", pd.Series(dtype=object)).map(deal_type_direction)
    df["time_dt"] = pd.to_datetime(pd.to_numeric(df.get("time", pd.Series(dtype=float)), errors="coerce"), unit="s", errors="coerce")
    df["price_num"] = pd.to_numeric(df.get("price", pd.Series(dtype=float)), errors="coerce")
    df["volume_num"] = pd.to_numeric(df.get("volume", pd.Series(dtype=float)), errors="coerce")
    df["profit_num"] = pd.to_numeric(df.get("profit", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    df["commission_num"] = pd.to_numeric(df.get("commission", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    df["swap_num"] = pd.to_numeric(df.get("swap", pd.Series(dtype=float)), errors="coerce").fillna(0.0)

    rows: list[dict[str, Any]] = []
    for position_id, g in df.groupby("position_id", dropna=False):
        if clean_int(position_id, 0) == 0 and len(g) <= 1:
            continue
        g = g.sort_values("time_dt")
        entries = g[g["entry_label"].isin(["IN", "INOUT"])]
        exits = g[g["entry_label"].isin(["OUT", "OUT_BY", "INOUT"])]
        if entries.empty:
            entries = g.head(1)
        if exits.empty:
            exits = g.tail(1)
        entry_row = entries.iloc[0]
        exit_row = exits.iloc[-1]
        direction = normalize_direction(entry_row.get("deal_direction", ""))
        if not direction:
            # For closing deal direction, BUY close often means a SELL position. Prefer entry deal when possible.
            direction = normalize_direction(exit_row.get("deal_direction", ""))
        symbol = clean_str(entry_row.get("symbol"), clean_str(exit_row.get("symbol")))
        rows.append({
            "position_id": clean_int(position_id, 0),
            "symbol": symbol,
            "normalized_symbol": normalize_symbol_from_broker(symbol),
            "direction": direction,
            "entry_time": entry_row.get("time_text", ""),
            "entry_time_msc": entry_row.get("time_msc_text", ""),
            "entry_price": clean_float(entry_row.get("price_num"), 0.0),
            "entry_volume": clean_float(entry_row.get("volume_num"), 0.0),
            "entry_deal_ticket": clean_int(entry_row.get("ticket"), 0),
            "entry_order_ticket": clean_int(entry_row.get("order"), 0),
            "close_time": exit_row.get("time_text", ""),
            "close_time_msc": exit_row.get("time_msc_text", ""),
            "close_price": clean_float(exit_row.get("price_num"), 0.0),
            "close_volume": clean_float(exit_row.get("volume_num"), 0.0),
            "close_deal_ticket": clean_int(exit_row.get("ticket"), 0),
            "close_order_ticket": clean_int(exit_row.get("order"), 0),
            "profit": float(g["profit_num"].sum()),
            "commission": float(g["commission_num"].sum()),
            "swap": float(g["swap_num"].sum()),
            "net_profit": float(g["profit_num"].sum() + g["commission_num"].sum() + g["swap_num"].sum()),
            "deal_count": int(len(g)),
            "comment_concat": " | ".join(clean_str(x) for x in g.get("comment", pd.Series(dtype=object)).dropna().astype(str).tolist() if clean_str(x)),
        })
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_to = parse_dt(args.date_to, default=now)
    date_from = parse_dt(args.date_from, default=now - timedelta(days=int(args.lookback_days)))
    symbols = parse_symbols(args.symbols)

    report: dict[str, Any] = {
        "script": "export_mt5_closed_trade_history.py",
        "created_at_utc": utc_now_text(),
        "out_dir": str(out_dir),
        "date_from": date_from.strftime("%Y-%m-%d %H:%M:%S"),
        "date_to": date_to.strftime("%Y-%m-%d %H:%M:%S"),
        "symbols_filter": sorted(symbols),
        "mt5_import_ok": mt5 is not None,
        "mt5_import_error": MT5_IMPORT_ERROR,
        "initialize_ok": False,
    }

    if mt5 is None:
        write_json(out_dir / SUMMARY_FILENAME, report)
        print("export_mt5_closed_trade_history")
        print("ERROR: MetaTrader5 import failed")
        return 2

    initialized = False
    try:
        init_kwargs: dict[str, Any] = {}
        if args.terminal_path:
            init_kwargs["path"] = args.terminal_path
        if args.portable:
            init_kwargs["portable"] = True
        initialized = bool(mt5.initialize(**init_kwargs))
        report["initialize_ok"] = initialized
        report["last_error_after_initialize"] = str(mt5.last_error())
        if not initialized:
            write_json(out_dir / SUMMARY_FILENAME, report)
            print("export_mt5_closed_trade_history")
            print("ERROR: mt5.initialize failed")
            print(f"last_error: {report['last_error_after_initialize']}")
            return 3

        account_info = mt5.account_info()
        account_d = account_info._asdict() if account_info is not None and hasattr(account_info, "_asdict") else {}
        report["account_info"] = account_d
        current_login = clean_int(account_d.get("login"), 0)
        if args.expected_login is not None and current_login != int(args.expected_login):
            report["error"] = f"expected_login mismatch: expected={args.expected_login}; actual={current_login}"
            write_json(out_dir / SUMMARY_FILENAME, report)
            print("export_mt5_closed_trade_history")
            print(f"ERROR: {report['error']}")
            return 4

        deals = mt5.history_deals_get(date_from, date_to)
        orders = mt5.history_orders_get(date_from, date_to)
        deals_df = pd.DataFrame(asdict_list(deals))
        orders_df = pd.DataFrame(asdict_list(orders))

        if not deals_df.empty:
            deals_df = time_columns(deals_df)
            deals_df["entry_label"] = deals_df.get("entry", pd.Series(dtype=object)).map(deal_entry_label)
            deals_df["deal_direction"] = deals_df.get("type", pd.Series(dtype=object)).map(deal_type_direction)
            deals_df["normalized_symbol"] = deals_df.get("symbol", pd.Series(dtype=object)).map(normalize_symbol_from_broker)
            if symbols and "symbol" in deals_df.columns:
                deals_df = deals_df[deals_df["symbol"].astype(str).isin(symbols)].copy()
        if not orders_df.empty:
            orders_df = time_columns(orders_df)
            orders_df["order_direction"] = orders_df.get("type", pd.Series(dtype=object)).map(order_type_direction)
            orders_df["normalized_symbol"] = orders_df.get("symbol", pd.Series(dtype=object)).map(normalize_symbol_from_broker)
            if symbols and "symbol" in orders_df.columns:
                orders_df = orders_df[orders_df["symbol"].astype(str).isin(symbols)].copy()

        positions_df = build_position_summary(deals_df, orders_df)

        deals_csv = out_dir / "mt5_history_deals.csv"
        orders_csv = out_dir / "mt5_history_orders.csv"
        positions_csv = out_dir / "mt5_history_positions.csv"
        write_csv(deals_df, deals_csv)
        write_csv(orders_df, orders_csv)
        write_csv(positions_df, positions_csv)

        report.update({
            "success": True,
            "deals_csv": str(deals_csv),
            "orders_csv": str(orders_csv),
            "positions_csv": str(positions_csv),
            "deals_rows": int(len(deals_df)),
            "orders_rows": int(len(orders_df)),
            "positions_rows": int(len(positions_df)),
        })
        write_json(out_dir / SUMMARY_FILENAME, report)

        print("export_mt5_closed_trade_history")
        print(f"account_login: {current_login}")
        print(f"date_from: {report['date_from']}")
        print(f"date_to: {report['date_to']}")
        print(f"deals_rows: {report['deals_rows']}")
        print(f"orders_rows: {report['orders_rows']}")
        print(f"positions_rows: {report['positions_rows']}")
        print(f"deals_csv: {deals_csv}")
        print(f"orders_csv: {orders_csv}")
        print(f"positions_csv: {positions_csv}")
        print(f"summary_json: {out_dir / SUMMARY_FILENAME}")
        return 0
    finally:
        if initialized:
            try:
                mt5.shutdown()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
