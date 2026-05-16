#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find Mochipoyo notification_ledger_to_send.csv files containing target rows.

This is a local-log helper for safe dry-run checks. It does not send Discord
messages, does not call AI, and does not place orders.

Typical use:
  python scripts/find_mochipoyo_notification_csv.py \
    --root data/runtime_logs/gold/2026/05/week_20/mochipoyo_gold/loop \
    --symbol GOLD --pair-name GOLD_H4_M15_DAYTRADE --direction BUY \
    --output-csv data/runtime_logs/trade_ai_review/found_h4_m15_buy_notifications.csv
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


def read_csv_empty_ok(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def infer_from_pipe_key(*values: Any) -> dict[str, str]:
    for value in values:
        text = clean_str(value)
        if "|" not in text:
            continue
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 4:
            return {
                "symbol": parts[0].upper(),
                "pair_name": parts[1],
                "strategy_id": parts[1],
                "candidate_rank": parts[2],
                "direction": parts[3].upper(),
            }
    return {}


def row_value(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index:
            value = clean_str(row.get(name))
            if value:
                return value
    return default


def normalize_symbol(value: Any) -> str:
    text = clean_str(value).upper()
    if text.startswith("XAUUSD") or text.startswith("GOLD"):
        return "GOLD"
    if text.startswith("BTC"):
        return "BTC"
    return text


def row_context(row: pd.Series) -> dict[str, str]:
    inferred = infer_from_pipe_key(
        row_value(row, ["order_key"]),
        row_value(row, ["payload_key"]),
        row_value(row, ["signal_key"]),
    )
    pair_name = row_value(row, ["pair_name", "strategy_key", "strategy_id", "router_strategy_id"], inferred.get("pair_name", ""))
    return {
        "symbol": normalize_symbol(row_value(row, ["symbol", "broker_symbol"], inferred.get("symbol", ""))),
        "pair_name": pair_name,
        "strategy_id": row_value(row, ["strategy_id", "strategy_key"], pair_name),
        "candidate_rank": row_value(row, ["candidate_rank"], inferred.get("candidate_rank", "")),
        "direction": row_value(row, ["direction", "order_type"], inferred.get("direction", "")).upper(),
        "entry_time": row_value(row, ["entry_time", "signal_close_time", "sent_at", "created_at_utc"]),
        "entry_price": row_value(row, ["entry_price", "price", "current_execution_price"]),
        "payload_key": row_value(row, ["payload_key"]),
    }


def matches(ctx: dict[str, str], args: argparse.Namespace) -> bool:
    if args.symbol and normalize_symbol(ctx.get("symbol")) != normalize_symbol(args.symbol):
        return False
    if args.pair_name and clean_str(ctx.get("pair_name")) != clean_str(args.pair_name):
        return False
    if args.strategy_id and clean_str(ctx.get("strategy_id")) != clean_str(args.strategy_id):
        return False
    if args.direction and clean_str(ctx.get("direction")).upper() != clean_str(args.direction).upper():
        return False
    if args.candidate_rank and clean_str(ctx.get("candidate_rank")) != clean_str(args.candidate_rank):
        return False
    return True


def parse_iter_name(path: Path) -> str:
    for part in path.parts:
        if part.lower().startswith("iter_"):
            return part
    return ""


def main() -> int:
    p = argparse.ArgumentParser(description="Find notification_ledger_to_send.csv files containing target rows.")
    p.add_argument("--root", default="data/runtime_logs/gold/2026/05/week_20/mochipoyo_gold/loop")
    p.add_argument("--file-name", default="notification_ledger_to_send.csv")
    p.add_argument("--symbol", default="")
    p.add_argument("--pair-name", default="")
    p.add_argument("--strategy-id", default="")
    p.add_argument("--direction", default="")
    p.add_argument("--candidate-rank", default="")
    p.add_argument("--latest-first", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--max-results", type=int, default=20)
    p.add_argument("--output-csv", default="")
    args = p.parse_args()

    root = Path(args.root)
    rows: list[dict[str, Any]] = []
    if not root.exists():
        print("find_mochipoyo_notification_csv")
        print(f"root_not_found: {root}")
        return 2

    files = list(root.rglob(args.file_name))
    files = sorted(files, key=lambda pth: pth.stat().st_mtime if pth.exists() else 0, reverse=bool(args.latest_first))
    for path in files:
        if path.exists() and path.stat().st_size <= 0:
            continue
        df = read_csv_empty_ok(path)
        if df.empty:
            continue
        for row_index, row in df.iterrows():
            ctx = row_context(row)
            if not matches(ctx, args):
                continue
            rows.append({
                "file_path": str(path),
                "iter_name": parse_iter_name(path),
                "last_write_time": pd.Timestamp.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "file_size": int(path.stat().st_size),
                "row_index_1based": int(row_index) + 1,
                **ctx,
            })
            if args.max_results > 0 and len(rows) >= args.max_results:
                break
        if args.max_results > 0 and len(rows) >= args.max_results:
            break

    out = pd.DataFrame(rows)
    if args.output_csv:
        out_path = Path(args.output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(windows_long_path(out_path), index=False, encoding="utf-8-sig")

    print("find_mochipoyo_notification_csv")
    print(f"root: {root}")
    print(f"files_scanned: {len(files)}")
    print(f"matches: {len(out)}")
    if args.output_csv:
        print(f"output_csv: {args.output_csv}")
    if not out.empty:
        cols = ["file_path", "iter_name", "last_write_time", "symbol", "pair_name", "direction", "candidate_rank", "entry_time", "entry_price"]
        print(out[[c for c in cols if c in out.columns]].head(int(args.max_results) if args.max_results > 0 else 20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
