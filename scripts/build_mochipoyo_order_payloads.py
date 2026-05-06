#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build dry-run order payloads from Mochipoyo notification rows.

This script does NOT place orders.
It converts notification_ledger_to_send.csv style rows into an order-payload CSV
that can be inspected before any MT5 execution layer is introduced.

Safety goals:
- explicit dry-run status
- BUY/SELL SL/TP direction validation
- payload_key based order key
- fixed safe lot default unless explicitly overridden
- no MT5 dependency
- no broker API call
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_MAGIC = 26050601


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


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def val(row: pd.Series, name: str, default: str = "") -> str:
    if name not in row.index:
        return default
    x = row.get(name)
    if pd.isna(x):
        return default
    s = str(x)
    return s if s else default


def fval(row: pd.Series, name: str) -> float | None:
    if name not in row.index:
        return None
    try:
        x = float(row.get(name))
    except Exception:
        return None
    if pd.isna(x):
        return None
    return x


def time_label(row: pd.Series, name: str) -> str:
    raw = val(row, name)
    if not raw:
        return ""
    try:
        return pd.to_datetime(raw).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return raw


def make_payload_key(row: pd.Series) -> str:
    if "payload_key" in row.index and pd.notna(row.get("payload_key")) and str(row.get("payload_key")):
        return str(row.get("payload_key"))
    fields = [
        "symbol",
        "candidate_name",
        "entry_time",
        "pair_name",
        "candidate_rank",
        "direction",
        "entry_price",
        "source_filter_name",
    ]
    return "|".join(str(row.get(c, "")) for c in fields)


def price_digits(symbol: str) -> int:
    s = symbol.upper()
    if s == "BTC":
        return 2
    if s == "GOLD":
        return 3
    return 5


def normalize_price(x: float | None, digits: int) -> float | None:
    if x is None:
        return None
    return round(float(x), int(digits))


def validate_side_prices(direction: str, entry: float | None, sl: float | None, tp: float | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    d = direction.upper()
    if d not in {"BUY", "SELL"}:
        errors.append(f"invalid direction: {direction}")
    if entry is None:
        errors.append("missing entry_price")
    if sl is None:
        errors.append("missing sl_price")
    if tp is None:
        errors.append("missing tp_price")
    if errors:
        return False, errors
    assert entry is not None and sl is not None and tp is not None
    if d == "BUY":
        if not sl < entry:
            errors.append(f"BUY requires sl_price < entry_price; sl={sl}; entry={entry}")
        if not tp > entry:
            errors.append(f"BUY requires tp_price > entry_price; tp={tp}; entry={entry}")
    elif d == "SELL":
        if not sl > entry:
            errors.append(f"SELL requires sl_price > entry_price; sl={sl}; entry={entry}")
        if not tp < entry:
            errors.append(f"SELL requires tp_price < entry_price; tp={tp}; entry={entry}")
    return len(errors) == 0, errors


def compute_stop_distance(direction: str, entry: float | None, sl: float | None) -> float | None:
    if entry is None or sl is None:
        return None
    if direction.upper() == "BUY":
        return entry - sl
    if direction.upper() == "SELL":
        return sl - entry
    return None


def compute_take_distance(direction: str, entry: float | None, tp: float | None) -> float | None:
    if entry is None or tp is None:
        return None
    if direction.upper() == "BUY":
        return tp - entry
    if direction.upper() == "SELL":
        return entry - tp
    return None


def load_existing_order_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        df = read_csv(path)
    except Exception:
        return set()
    if "order_key" not in df.columns:
        return set()
    return set(df["order_key"].dropna().astype(str).tolist())


def build_order_payloads(
    df: pd.DataFrame,
    *,
    fixed_lot: float,
    magic: int,
    broker_symbol: str | None,
    max_orders: int,
    existing_order_keys: set[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    work = df.copy()
    if "entry_time" in work.columns:
        work["entry_time_sort"] = pd.to_datetime(work["entry_time"], errors="coerce")
        work = work.sort_values("entry_time_sort").drop(columns=["entry_time_sort"], errors="ignore")
    if max_orders > 0:
        work = work.tail(max_orders)

    for i, (_, row) in enumerate(work.iterrows(), start=1):
        symbol = val(row, "symbol", "GOLD").upper()
        direction = val(row, "direction").upper()
        digits = price_digits(symbol)
        entry = normalize_price(fval(row, "entry_price"), digits)
        sl = normalize_price(fval(row, "sl_price"), digits)
        tp = normalize_price(fval(row, "tp_price"), digits)
        rr = fval(row, "rr")
        payload_key = make_payload_key(row)
        order_key = payload_key
        valid, errors = validate_side_prices(direction, entry, sl, tp)
        stop_distance = compute_stop_distance(direction, entry, sl)
        take_distance = compute_take_distance(direction, entry, tp)
        duplicate = order_key in existing_order_keys
        status = "DRY_RUN_DUPLICATE_WOULD_SKIP" if duplicate else "DRY_RUN_READY"
        if not valid:
            status = "INVALID_PRICE_RELATION"
        rows.append(
            {
                "order_index": i,
                "order_status": status,
                "is_valid_order_payload": bool(valid and not duplicate),
                "validation_errors": "; ".join(errors),
                "symbol": symbol,
                "broker_symbol": broker_symbol or symbol,
                "direction": direction,
                "order_type": "MARKET",
                "lot": float(fixed_lot),
                "entry_price_reference": entry,
                "sl_price": sl,
                "tp_price": tp,
                "rr": rr,
                "stop_distance": stop_distance,
                "take_distance": take_distance,
                "magic_number": int(magic),
                "comment": f"mochipoyo {symbol} {direction}",
                "payload_key": payload_key,
                "order_key": order_key,
                "pair_name": val(row, "pair_name"),
                "candidate_rank": val(row, "candidate_rank"),
                "candidate_name": val(row, "candidate_name"),
                "signal_close_time": time_label(row, "signal_close_time"),
                "entry_time": time_label(row, "entry_time"),
                "live_window_status": val(row, "live_window_status"),
                "ledger_status": val(row, "ledger_status"),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Build dry-run order payloads from Mochipoyo notification rows.")
    p.add_argument("--input-csv", required=True, help="notification_ledger_to_send.csv or equivalent")
    p.add_argument("--output-csv", required=True)
    p.add_argument("--output-json", default=None)
    p.add_argument("--order-ledger-csv", default=None, help="Optional existing order ledger for duplicate key checks")
    p.add_argument("--symbol", default=None)
    p.add_argument("--broker-symbol", default=None, help="Broker symbol to use in order payload, e.g. GOLD# or XAUUSD")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--magic", type=int, default=DEFAULT_MAGIC)
    p.add_argument("--max-orders", type=int, default=5)
    args = p.parse_args()

    src = Path(args.input_csv)
    df = read_csv(src)
    if args.symbol and "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == args.symbol.upper()].copy()

    existing_order_keys: set[str] = set()
    if args.order_ledger_csv:
        existing_order_keys = load_existing_order_keys(Path(args.order_ledger_csv))

    out = build_order_payloads(
        df,
        fixed_lot=float(args.fixed_lot),
        magic=int(args.magic),
        broker_symbol=args.broker_symbol,
        max_orders=int(args.max_orders),
        existing_order_keys=existing_order_keys,
    )
    write_csv(out, args.output_csv)

    output_json = Path(args.output_json) if args.output_json else Path(args.output_csv).with_suffix(".json")
    summary = {
        "source": str(src),
        "rows_in": int(len(df)),
        "rows_out": int(len(out)),
        "valid_order_payloads": int(out["is_valid_order_payload"].sum()) if "is_valid_order_payload" in out.columns else 0,
        "invalid_order_payloads": int((~out["is_valid_order_payload"].astype(bool)).sum()) if "is_valid_order_payload" in out.columns and not out.empty else 0,
        "fixed_lot": float(args.fixed_lot),
        "magic": int(args.magic),
        "broker_symbol": args.broker_symbol,
        "records": out.to_dict(orient="records"),
    }
    write_text(output_json, json.dumps(summary, ensure_ascii=False, indent=2))

    print("build_mochipoyo_order_payloads")
    print(f"source: {src}")
    print(f"rows_in: {len(df)}")
    print(f"rows_out: {len(out)}")
    print(f"valid_order_payloads: {summary['valid_order_payloads']}")
    print(f"invalid_order_payloads: {summary['invalid_order_payloads']}")
    print(f"output_csv: {args.output_csv}")
    print(f"output_json: {output_json}")
    if not out.empty:
        cols = [
            "order_status",
            "symbol",
            "broker_symbol",
            "direction",
            "lot",
            "entry_price_reference",
            "sl_price",
            "tp_price",
            "rr",
            "pair_name",
            "candidate_rank",
            "entry_time",
        ]
        cols = [c for c in cols if c in out.columns]
        print(out[cols].to_string(index=False))
    print("done")
    return 0 if summary["invalid_order_payloads"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
