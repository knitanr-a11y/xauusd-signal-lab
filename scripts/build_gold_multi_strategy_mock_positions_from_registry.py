#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build mock MT5 positions CSV from a position_registry preview CSV.

Purpose:
- Create a positions CSV whose ticket/symbol/direction/lot exactly match ACTIVE
  registry rows.
- Validate registry reconciliation happy paths without touching MT5.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No ledger mutation.
- No registry mutation.
- No trigger-state mutation.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

SCHEMA_VERSION = "gold_multi_strategy_mock_positions_from_registry_v1"
ACTIVE_STATUSES = {"ACTIVE", "OPEN", "SENT", "FILLED"}

POSITION_COLUMNS = [
    "ticket",
    "identifier",
    "symbol",
    "direction",
    "type",
    "volume",
    "price_open",
    "sl",
    "tp",
    "magic",
    "comment",
    "external_id",
    "time",
    "time_msc",
    "profit",
    "swap",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build mock positions CSV from registry preview rows. No MT5 calls.")
    p.add_argument("--registry-csv", type=Path, required=True)
    p.add_argument("--output-csv", type=Path, required=True)
    p.add_argument("--output-json", type=Path, default=None)
    p.add_argument("--max-rows", type=int, default=0, help="Limit ACTIVE rows. 0 means no limit.")
    p.add_argument("--comment-prefix", default="ms")
    p.add_argument("--profit", type=float, default=0.0)
    p.add_argument("--swap", type=float, default=0.0)
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


def path_exists(path: Path) -> bool:
    try:
        return Path(windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def write_csv(df: pd.DataFrame, path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def clean_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return default


def clean_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        if pd.isna(value):
            return float(default)
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return float(default)


def direction_type(direction: str) -> int:
    return 0 if direction.upper() == "BUY" else 1 if direction.upper() == "SELL" else -1


def build_comment(prefix: str, row: pd.Series) -> str:
    alias = clean_str(row.get("strategy_alias"))
    key = clean_str(row.get("strategy_key"))
    direction = clean_str(row.get("direction"))
    parts = [prefix, alias, key, direction]
    return " ".join(p for p in parts if p).strip()[:31]


def build_external_id(row: pd.Series) -> str:
    key = clean_str(row.get("strategy_key"))
    signal = clean_str(row.get("signal_key"))
    if signal:
        return f"{key}|{signal}"[:255]
    return f"{key}|MOCK_FROM_REGISTRY"[:255]


def active_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if "position_status" not in df.columns:
        return df.copy()
    return df[df["position_status"].astype(str).str.upper().isin(ACTIVE_STATUSES)].copy()


def make_position_row(row: pd.Series, now: str, args: argparse.Namespace) -> dict[str, Any]:
    ticket = clean_int(row.get("position_ticket"), 0)
    direction = clean_str(row.get("direction")).upper()
    return {
        "ticket": ticket,
        "identifier": ticket,
        "symbol": clean_str(row.get("broker_symbol"), clean_str(row.get("symbol"))),
        "direction": direction,
        "type": direction_type(direction),
        "volume": clean_float(row.get("lot"), 0.0),
        "price_open": clean_float(row.get("entry_price"), 0.0),
        "sl": clean_float(row.get("sl_price"), 0.0),
        "tp": clean_float(row.get("tp_price"), 0.0),
        "magic": clean_int(row.get("magic_number"), 26050601),
        "comment": build_comment(args.comment_prefix, row),
        "external_id": build_external_id(row),
        "time": now,
        "time_msc": now,
        "profit": float(args.profit),
        "swap": float(args.swap),
    }


def main() -> int:
    args = parse_args()
    output_json = args.output_json if args.output_json is not None else args.output_csv.with_suffix(".json")
    now = utc_now_text()

    if not path_exists(args.registry_csv):
        empty = pd.DataFrame(columns=POSITION_COLUMNS)
        write_csv(empty, args.output_csv)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "build_ok": False,
            "reason": "REGISTRY_CSV_NOT_FOUND",
            "registry_csv": str(args.registry_csv),
            "output_csv": str(args.output_csv),
            "output_json": str(output_json),
            "rows_out": 0,
            "safety": safety_summary(),
        }
        write_json(output_json, summary)
        print("build_gold_multi_strategy_mock_positions_from_registry")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 2

    registry_df = read_csv(args.registry_csv)
    active_df = active_rows(registry_df)
    if args.max_rows and args.max_rows > 0:
        active_df = active_df.head(int(args.max_rows)).copy()
    rows = [make_position_row(row, now, args) for _, row in active_df.iterrows()]
    out_df = pd.DataFrame([{col: row.get(col, "") for col in POSITION_COLUMNS} for row in rows], columns=POSITION_COLUMNS)
    write_csv(out_df, args.output_csv)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "build_ok": True,
        "reason": "MOCK_POSITIONS_BUILT_FROM_REGISTRY",
        "registry_csv": str(args.registry_csv),
        "output_csv": str(args.output_csv),
        "output_json": str(output_json),
        "registry_rows": int(len(registry_df)),
        "active_registry_rows": int(len(active_df)),
        "rows_out": int(len(out_df)),
        "safety": safety_summary(),
        "records": out_df.to_dict(orient="records"),
    }
    write_json(output_json, summary)

    print("build_gold_multi_strategy_mock_positions_from_registry")
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if not out_df.empty:
        print(out_df[["ticket", "symbol", "direction", "volume", "magic", "comment", "external_id"]].to_string(index=False))
    else:
        print("[INFO] no active registry rows; empty mock positions written")
    print("done")
    return 0


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": False,
        "order_check_called": False,
        "order_send_called": False,
        "ledger_written": False,
        "registry_mutated": False,
        "trigger_state_mutated": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
