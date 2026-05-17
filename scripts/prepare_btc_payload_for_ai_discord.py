#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert BTC order payload CSV rows into Discord-notification-like rows.

This is a formatting bridge only. It never sends Discord, never calls AI, and
never places orders. The output CSV is for send_mochipoyo_discord_messages.py.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError


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


def clean_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    s = str(x).strip()
    return s if s else default


def clean_float(x: Any, default: float | None = None) -> float | None:
    if x is None or x == "":
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return default


def read_csv(path: str | Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def value(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index:
            v = clean_str(row.get(name))
            if v:
                return v
    return default


def infer_rr(entry: float | None, sl: float | None, tp: float | None, direction: str) -> float | None:
    if entry is None or sl is None or tp is None:
        return None
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0:
        return None
    return reward / risk


def convert_row(row: pd.Series) -> dict[str, Any]:
    direction = value(row, ["direction"], "").upper()
    broker_symbol = value(row, ["broker_symbol", "symbol"], "BTC")
    entry = clean_float(row.get("entry_price"), clean_float(row.get("entry_price_reference")))
    sl = clean_float(row.get("sl_price"))
    tp = clean_float(row.get("tp_price"))
    rr = clean_float(row.get("rr"), infer_rr(entry, sl, tp, direction))
    strategy_id = value(row, ["strategy_id", "strategy_key", "router_strategy_id"], "BTC_MANUAL_DEMO_ORDER_SEND_SMOKE_TEST_SEND_ONCE")
    rank = value(row, ["candidate_rank"], "1")
    payload_key = value(row, ["payload_key"], "")
    payload_id = payload_key or value(row, ["order_key", "signal_key"], "")
    reason_bits = [
        "btc_manual_demo_send_path",
        "ai_history_warning_connected",
    ]
    source = value(row, ["source"], "")
    if source:
        reason_bits.append(source)
    return {
        "payload_id": payload_id,
        "payload_key": payload_key,
        "order_key": value(row, ["order_key"], ""),
        "signal_key": value(row, ["signal_key"], ""),
        "symbol": "BTC",
        "broker_symbol": broker_symbol,
        "pair_name": strategy_id,
        "strategy_id": strategy_id,
        "strategy_key": value(row, ["strategy_key"], strategy_id),
        "candidate_rank": rank,
        "candidate_name": value(row, ["strategy_alias", "condition_id"], strategy_id),
        "direction": direction,
        "entry_time": value(row, ["entry_time", "signal_close_time", "created_at_utc"], ""),
        "signal_close_time": value(row, ["signal_close_time", "entry_time", "created_at_utc"], ""),
        "entry_price": entry if entry is not None else "",
        "sl_price": sl if sl is not None else "",
        "tp_price": tp if tp is not None else "",
        "rr": rr if rr is not None else "",
        "lot": clean_float(row.get("lot"), ""),
        "magic_number": value(row, ["magic_number"], ""),
        "reason_text": ";".join(reason_bits),
        "caution_labels": "NONE",
        "context_granville_type": "BTC_MANUAL",
        "context_ema_order": "",
        "base_ema_order": "",
        "total_score": "",
        "context_score": "",
        "base_score": "",
        "fixture_note": value(row, ["fixture_note"], ""),
        "source": source,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Convert BTC payload rows into Discord-format input rows.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-csv", required=True)
    args = p.parse_args()

    src = read_csv(args.input_csv)
    rows = [convert_row(row) for _, row in src.iterrows()] if not src.empty else []
    out = pd.DataFrame(rows)
    write_csv(out, args.output_csv)
    print("prepare_btc_payload_for_ai_discord")
    print(f"input_csv: {args.input_csv}")
    print(f"rows_in: {len(src)}")
    print(f"rows_out: {len(out)}")
    print(f"output_csv: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
