#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows-long-path hardened wrapper for registry policy preview.

This wrapper intentionally reuses the validated policy logic in
`scripts/run_gold_multi_strategy_registry_policy_preview.py`, while monkey-patching
only file existence and output write helpers to use the existing `windows_long_path()`
helper everywhere.

Purpose:
- Keep the policy logic unchanged.
- Avoid Windows MAX_PATH-style FileNotFoundError when the repo is under the deep
  MetaTrader5/MQL5/Files directory.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No registry mutation.
- No ledger mutation.
- No trigger-state mutation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

import run_gold_multi_strategy_registry_policy_preview as base


def path_exists(path: Path) -> bool:
    try:
        return Path(base.windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def write_csv_longpath(df: pd.DataFrame, path: Path) -> None:
    Path(base.windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    df.to_csv(base.windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json_longpath(path: Path, obj: dict[str, Any]) -> None:
    Path(base.windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(base.windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def read_positions_longpath(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path_exists(path):
        return [], "POSITIONS_CSV_NOT_FOUND"
    df = base.read_csv(path)
    if df.empty:
        return [], "POSITIONS_EMPTY"
    return [{str(k): row.get(k) for k in df.columns} for _, row in df.iterrows()], "POSITIONS_READ_OK"


def read_payloads_longpath(path: Path, max_orders: int) -> tuple[pd.DataFrame, str, bool]:
    if not path_exists(path):
        return pd.DataFrame(), "NO_INPUT_CSV", False
    df = base.read_csv(path)
    if df.empty:
        return df, "NO_INPUT_ROWS", True
    if max_orders > 0:
        df = df.head(max_orders).copy()
    return df, "INPUT_ROWS_FOUND", True


def read_registry_longpath(path: Path) -> tuple[pd.DataFrame, str, bool]:
    if not path_exists(path):
        return pd.DataFrame(columns=base.REGISTRY_COLUMNS), "REGISTRY_NOT_FOUND", False
    df = base.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=base.REGISTRY_COLUMNS), "REGISTRY_EMPTY", True
    for col in base.REGISTRY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[base.REGISTRY_COLUMNS].copy(), "REGISTRY_READ_OK", True


def read_existing_keys_longpath(order_ledger_csv: Path) -> tuple[set[str], set[str], str]:
    if not path_exists(order_ledger_csv):
        return set(), set(), "ORDER_LEDGER_NOT_FOUND"
    df = base.read_csv(order_ledger_csv)
    if df.empty:
        return set(), set(), "ORDER_LEDGER_EMPTY"
    order_keys: set[str] = set()
    signal_keys: set[str] = set()
    for col in ["order_key", "payload_key"]:
        if col in df.columns:
            order_keys.update(base.clean_str(v) for v in df[col].dropna().tolist() if base.clean_str(v))
    if "signal_key" in df.columns:
        signal_keys.update(base.clean_str(v) for v in df["signal_key"].dropna().tolist() if base.clean_str(v))
    return order_keys, signal_keys, "ORDER_LEDGER_READ_OK"


def main() -> int:
    base.write_csv = write_csv_longpath
    base.write_json = write_json_longpath
    base.read_positions = read_positions_longpath
    base.read_payloads = read_payloads_longpath
    base.read_registry = read_registry_longpath
    base.read_existing_keys = read_existing_keys_longpath
    return int(base.main())


if __name__ == "__main__":
    raise SystemExit(main())
