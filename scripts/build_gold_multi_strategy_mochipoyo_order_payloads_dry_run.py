#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build Mochipoyo-compatible order_payloads.csv from multi-strategy adapter previews.

This is a dry-run bridge only.

Input:
- adapter_order_preview.csv from scripts/run_gold_multi_strategy_autotrade_adapter_dry_run.py

Output:
- order_payloads.csv compatible with scripts/send_mt5_order_from_payload.py
- order_payloads.json summary
- payload_bridge_rejects.csv

Safety boundaries:
- No MT5 connection.
- No mt5.order_check.
- No mt5.order_send.
- No Discord send.
- No existing Mochipoyo notification ledger writes.
- No existing demo/autotrade order ledger writes.

The generated CSV is intentionally placed in a separate research out-dir first.
A later step may feed it into send_mt5_order_from_payload.py WITHOUT --send for
order_check validation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ADAPTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_autotrade_adapter_dry_run")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run")
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

REJECT_COLUMNS = [
    "reject_time_utc",
    "adapter_preview_key",
    "strategy_id",
    "condition_id",
    "signal_key",
    "router_strategy_slot",
    "reject_reason",
    "raw_json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Mochipoyo-compatible order_payloads.csv from adapter order previews.")
    p.add_argument("--adapter-out-dir", type=Path, default=DEFAULT_ADAPTER_OUT_DIR)
    p.add_argument("--input-csv", type=Path, default=None, help="Default: <adapter-out-dir>/adapter_order_preview.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--output-csv", type=Path, default=None, help="Default: <out-dir>/order_payloads.csv")
    p.add_argument("--output-json", type=Path, default=None, help="Default: <out-dir>/order_payloads.json")
    p.add_argument("--rejects-csv", type=Path, default=None, help="Default: <out-dir>/payload_bridge_rejects.csv")
    p.add_argument("--broker-symbol", type=str, default="GOLD#")
    p.add_argument("--fixed-lot", type=float, default=0.01, help="Safety default matching demo bat. Overrides adapter effective_lot unless --use-adapter-lot is set.")
    p.add_argument("--use-adapter-lot", action="store_true", help="Use adapter effective_lot instead of fixed lot. Not recommended before additional risk review.")
    p.add_argument("--magic", type=int, default=DEFAULT_MAGIC)
    p.add_argument("--max-orders", type=int, default=5)
    p.add_argument("--allow-duplicate-order-key", action="store_true", help="Allow duplicate order_key within this generated file.")
    p.add_argument("--strict", action="store_true", help="Return non-zero if any reject exists.")
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


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None or value == "":
            return default
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value)
    return text if text else default


def normalize_time(value: Any) -> str:
    text = clean_str(value)
    if not text:
        return ""
    try:
        return pd.Timestamp(text).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return text


def price_digits(symbol: str) -> int:
    s = symbol.upper()
    if s == "BTC":
        return 2
    if s == "GOLD":
        return 3
    return 5


def normalize_price(value: float, digits: int) -> float:
    return round(float(value), int(digits))


def stop_distance(direction: str, entry: float, sl: float) -> float:
    return entry - sl if direction == "BUY" else sl - entry


def take_distance(direction: str, entry: float, tp: float) -> float:
    return tp - entry if direction == "BUY" else entry - tp


def validate_preview(row: pd.Series) -> list[str]:
    errors: list[str] = []
    action = clean_str(row.get("adapter_action"))
    if action != "WOULD_OPEN_POSITION_DRY_RUN":
        errors.append(f"adapter_action must be WOULD_OPEN_POSITION_DRY_RUN: {action}")
    symbol = clean_str(row.get("symbol"))
    if symbol != "GOLD":
        errors.append(f"symbol must be GOLD: {symbol}")
    side = clean_str(row.get("side")).upper()
    if side not in {"BUY", "SELL"}:
        errors.append(f"side must be BUY or SELL: {side}")
    for col in ["strategy_id", "condition_id", "signal_key", "preview_key"]:
        if not clean_str(row.get(col)):
            errors.append(f"{col} is required")
    entry = safe_float(row.get("entry_price_reference"))
    sl = safe_float(row.get("sl_price"))
    tp = safe_float(row.get("tp_price"))
    rr = safe_float(row.get("rr"))
    if not math.isfinite(entry):
        errors.append("entry_price_reference must be finite")
    if not math.isfinite(sl):
        errors.append("sl_price must be finite")
    if not math.isfinite(tp):
        errors.append("tp_price must be finite")
    if not math.isfinite(rr) or rr <= 0:
        errors.append("rr must be > 0")
    if all(math.isfinite(x) for x in [entry, sl, tp]):
        if side == "BUY":
            if not sl < entry:
                errors.append("BUY requires sl_price < entry_price_reference")
            if not tp > entry:
                errors.append("BUY requires tp_price > entry_price_reference")
        if side == "SELL":
            if not sl > entry:
                errors.append("SELL requires sl_price > entry_price_reference")
            if not tp < entry:
                errors.append("SELL requires tp_price < entry_price_reference")
    return errors


def build_payload_key(row: pd.Series) -> str:
    strategy_id = clean_str(row.get("strategy_id"))
    signal_key = clean_str(row.get("signal_key"))
    preview_key = clean_str(row.get("preview_key"))
    if strategy_id and signal_key:
        return f"{strategy_id}|{signal_key}|MOCHIPOYO_PAYLOAD"
    return f"{preview_key}|MOCHIPOYO_PAYLOAD"


def build_output_row(index: int, row: pd.Series, *, broker_symbol: str, fixed_lot: float, use_adapter_lot: bool, magic: int) -> dict[str, Any]:
    symbol = clean_str(row.get("symbol"), "GOLD").upper()
    direction = clean_str(row.get("side")).upper()
    digits = price_digits(symbol)
    entry = normalize_price(safe_float(row.get("entry_price_reference")), digits)
    sl = normalize_price(safe_float(row.get("sl_price")), digits)
    tp = normalize_price(safe_float(row.get("tp_price")), digits)
    rr = safe_float(row.get("rr"))
    adapter_lot = safe_float(row.get("effective_lot"))
    lot = adapter_lot if use_adapter_lot else float(fixed_lot)
    payload_key = build_payload_key(row)
    order_key = payload_key
    stop = stop_distance(direction, entry, sl)
    take = take_distance(direction, entry, tp)
    return {
        "order_index": int(index),
        "order_status": "DRY_RUN_READY",
        "is_valid_order_payload": True,
        "validation_errors": "",
        "symbol": symbol,
        "broker_symbol": broker_symbol or clean_str(row.get("broker_symbol"), symbol),
        "direction": direction,
        "order_type": "MARKET",
        "lot": float(lot),
        "entry_price_reference": entry,
        "sl_price": sl,
        "tp_price": tp,
        "rr": rr,
        "stop_distance": stop,
        "take_distance": take,
        "magic_number": int(magic),
        "comment": f"multi {direction} {clean_str(row.get('router_strategy_slot'))}"[:31],
        "payload_key": payload_key,
        "order_key": order_key,
        "pair_name": clean_str(row.get("router_strategy_slot"), clean_str(row.get("strategy_id"))),
        "candidate_rank": clean_str(row.get("rank")),
        "candidate_name": clean_str(row.get("condition_id")),
        "signal_close_time": normalize_time(row.get("signal_time")),
        "entry_time": normalize_time(row.get("signal_time")),
        "live_window_status": "MULTI_STRATEGY_ADAPTER_DRY_RUN",
        "ledger_status": "ADAPTER_PREVIEW_READY",
        "strategy_id": clean_str(row.get("strategy_id")),
        "condition_id": clean_str(row.get("condition_id")),
        "signal_key": clean_str(row.get("signal_key")),
        "router_strategy_slot": clean_str(row.get("router_strategy_slot")),
        "router_strategy_id": clean_str(row.get("router_strategy_id")),
        "router_source_path": clean_str(row.get("router_source_path")),
        "adapter_preview_key": clean_str(row.get("preview_key")),
    }


def reject_row(now: str, row: pd.Series, reason: str) -> dict[str, Any]:
    return {
        "reject_time_utc": now,
        "adapter_preview_key": clean_str(row.get("preview_key")),
        "strategy_id": clean_str(row.get("strategy_id")),
        "condition_id": clean_str(row.get("condition_id")),
        "signal_key": clean_str(row.get("signal_key")),
        "router_strategy_slot": clean_str(row.get("router_strategy_slot")),
        "reject_reason": reason,
        "raw_json": json.dumps({str(k): clean_str(v) for k, v in row.to_dict().items()}, ensure_ascii=False, sort_keys=True),
    }


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    input_csv = args.input_csv if args.input_csv is not None else args.adapter_out_dir / "adapter_order_preview.csv"
    output_csv = args.output_csv if args.output_csv is not None else args.out_dir / "order_payloads.csv"
    output_json = args.output_json if args.output_json is not None else args.out_dir / "order_payloads.json"
    rejects_csv = args.rejects_csv if args.rejects_csv is not None else args.out_dir / "payload_bridge_rejects.csv"
    now = utc_now_text()

    if not input_csv.exists():
        empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        write_csv(empty, output_csv)
        write_csv(pd.DataFrame(columns=REJECT_COLUMNS), rejects_csv)
        summary = {
            "schema_version": "gold_multi_strategy_mochipoyo_payload_bridge_dry_run_v1",
            "bridge_ok": True,
            "reason": "NO_ADAPTER_ORDER_PREVIEW_CSV",
            "input_csv": str(input_csv),
            "rows_in": 0,
            "rows_out": 0,
            "valid_order_payloads": 0,
            "rejects": 0,
            "output_csv": str(output_csv),
            "rejects_csv": str(rejects_csv),
        }
        write_json(output_json, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    src = read_csv(input_csv)
    if src.empty:
        write_csv(pd.DataFrame(columns=OUTPUT_COLUMNS), output_csv)
        write_csv(pd.DataFrame(columns=REJECT_COLUMNS), rejects_csv)
        summary = {
            "schema_version": "gold_multi_strategy_mochipoyo_payload_bridge_dry_run_v1",
            "bridge_ok": True,
            "reason": "NO_ADAPTER_ORDER_PREVIEW_ROWS",
            "input_csv": str(input_csv),
            "rows_in": 0,
            "rows_out": 0,
            "valid_order_payloads": 0,
            "rejects": 0,
            "output_csv": str(output_csv),
            "rejects_csv": str(rejects_csv),
        }
        write_json(output_json, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.max_orders > 0:
        src = src.tail(int(args.max_orders)).copy()

    rows: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    seen_order_keys: set[str] = set()
    for _, row in src.iterrows():
        errors = validate_preview(row)
        if errors:
            rejects.append(reject_row(now, row, "; ".join(errors)))
            continue
        out_row = build_output_row(
            len(rows) + 1,
            row,
            broker_symbol=str(args.broker_symbol),
            fixed_lot=float(args.fixed_lot),
            use_adapter_lot=bool(args.use_adapter_lot),
            magic=int(args.magic),
        )
        order_key = str(out_row["order_key"])
        if not args.allow_duplicate_order_key and order_key in seen_order_keys:
            rejects.append(reject_row(now, row, f"duplicate order_key within generated payloads: {order_key}"))
            continue
        seen_order_keys.add(order_key)
        rows.append(out_row)

    out = pd.DataFrame([{col: row.get(col, "") for col in OUTPUT_COLUMNS} for row in rows], columns=OUTPUT_COLUMNS)
    rej = pd.DataFrame([{col: row.get(col, "") for col in REJECT_COLUMNS} for row in rejects], columns=REJECT_COLUMNS)
    write_csv(out, output_csv)
    write_csv(rej, rejects_csv)
    summary = {
        "schema_version": "gold_multi_strategy_mochipoyo_payload_bridge_dry_run_v1",
        "bridge_ok": len(rejects) == 0 or not bool(args.strict),
        "strict": bool(args.strict),
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "output_json": str(output_json),
        "rejects_csv": str(rejects_csv),
        "rows_in": int(len(src)),
        "rows_out": int(len(out)),
        "valid_order_payloads": int(out["is_valid_order_payload"].astype(bool).sum()) if not out.empty else 0,
        "rejects": int(len(rejects)),
        "broker_symbol": str(args.broker_symbol),
        "fixed_lot": float(args.fixed_lot),
        "use_adapter_lot": bool(args.use_adapter_lot),
        "magic": int(args.magic),
        "records": out.to_dict(orient="records"),
    }
    write_json(output_json, summary)
    print("build_gold_multi_strategy_mochipoyo_order_payloads_dry_run")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True))
    if not out.empty:
        show_cols = ["order_status", "broker_symbol", "direction", "lot", "entry_price_reference", "sl_price", "tp_price", "rr", "candidate_rank", "pair_name", "order_key"]
        print(out[show_cols].to_string(index=False))
    return 0 if summary["bridge_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
