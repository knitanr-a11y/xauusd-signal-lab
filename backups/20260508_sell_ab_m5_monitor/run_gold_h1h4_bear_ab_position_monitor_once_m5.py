#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Dry-run position monitor once for GOLD bearish A/B classifier.

This script is intentionally separated from Mochipoyo live/demo/autotrade code
and from the BUY-side C_ENV dry-run directory.

It reads the dedicated SELL signal ledger created by:

    scripts/run_gold_h1h4_bear_ab_live_scan_once.py

and checks each DRY_RUN_SIGNAL_CREATED row against confirmed M5 data.

SELL-specific rules:
- TP touch: M5 low <= tp_price
- SL touch: M5 high >= sl_price
- same-M5 conflict: default conservative SL priority
- realized R: (entry_price - exit_price) / risk_price
- close_side for close intent: BUY

No Discord send.
No MT5 order placement.
No Mochipoyo trigger-state update.
No Mochipoyo ledger update.
No existing autotrade/order-intent file update.
No mutation of MT5 source candle CSVs.
No mutation of signal_ledger.csv.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import (  # noqa: E402
    CONDITION_FAMILY_ID,
    DIRECTION,
    SYMBOL,
    read_ohlc_csv,
    safe_float,
)

DEFAULT_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_live_scan")
DEFAULT_M5_FILENAME = "goldsharp_m5.csv"
SIGNAL_STATUS_CREATED = "DRY_RUN_SIGNAL_CREATED"

MONITOR_LOG_COLUMNS = [
    "monitor_time_utc",
    "condition_family_id",
    "condition_id",
    "csv_dir",
    "signal_key",
    "symbol",
    "direction",
    "rank",
    "signal_group",
    "entry_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "risk_price",
    "reward_price",
    "rr",
    "max_hold_hours",
    "base_lot",
    "lot_multiplier",
    "effective_lot",
    "horizon_time",
    "latest_m5_time",
    "latest_m5_close_time",
    "m5_first_time",
    "m5_last_time",
    "bars_checked",
    "outcome",
    "position_status",
    "exit_time_reference",
    "exit_price_reference",
    "realized_r_reference",
    "lot_weighted_r_reference",
    "close_intent_required",
    "close_intent_duplicate",
    "close_key",
    "reason",
]

CLOSE_INTENT_LOG_COLUMNS = [
    "created_at_utc",
    "close_key",
    "condition_family_id",
    "condition_id",
    "signal_key",
    "symbol",
    "direction",
    "rank",
    "intent_type",
    "close_reason",
    "close_side",
    "entry_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "risk_price",
    "reward_price",
    "rr",
    "max_hold_hours",
    "base_lot",
    "lot_multiplier",
    "effective_lot",
    "horizon_time",
    "exit_time_reference",
    "exit_price_reference",
    "realized_r_reference",
    "lot_weighted_r_reference",
    "dry_run",
    "action",
]

# This backup copy intentionally preserves the 2026-05-08 M5 monitor version.
# The active script was later switched to M1 to align with the existing
# Mochipoyo demo/autotrade monitor convention.


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BACKUP M5 dry-run position monitor once for GOLD bearish A/B classifier.")
    parser.add_argument("--csv-dir", type=Path, required=True, help="Directory containing goldsharp_m5.csv.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--ledger-csv", type=Path, default=None, help="Default: <out-dir>/signal_ledger.csv")
    parser.add_argument("--m5-filename", type=str, default=DEFAULT_M5_FILENAME)
    parser.add_argument("--max-hold-hours", type=float, default=12.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument("--latest-confirmed-m5-policy", choices=["last", "second_last"], default="last")
    return parser.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def ensure_empty_csv(path: Path, columns: list[str]) -> None:
    if not path.exists():
        write_csv(pd.DataFrame(columns=columns), path)


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def normalize_signal_ledger(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    required = ["signal_key", "condition_family_id", "condition_id", "symbol", "direction", "rank", "signal_group", "entry_time", "entry_price_reference", "sl_price", "tp_price", "risk_price", "reward_price", "rr", "max_hold_hours", "base_lot", "lot_multiplier", "effective_lot", "trade_enabled", "status"]
    for col in required:
        if col not in out.columns:
            out[col] = ""
    out = out[out["condition_family_id"].astype(str).eq(CONDITION_FAMILY_ID)].copy()
    out = out[out["status"].astype(str).eq(SIGNAL_STATUS_CREATED)].copy()
    out = out[out["trade_enabled"].map(bool_value)].copy()
    if out.empty:
        return out
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out = out.dropna(subset=["entry_time"]).copy()
    return out.sort_values(["entry_time", "signal_key"], kind="mergesort").reset_index(drop=True)


def load_confirmed_m5(csv_dir: Path, filename: str, policy: str) -> pd.DataFrame:
    m5 = read_ohlc_csv(csv_dir / filename).sort_values("time", kind="mergesort").reset_index(drop=True)
    if policy == "second_last" and len(m5) >= 2:
        m5 = m5.iloc[:-1].copy().reset_index(drop=True)
    m5["close_time"] = m5["time"] + pd.to_timedelta(5, unit="m")
    return m5


def row_float(row: pd.Series, col: str, default: float = float("nan")) -> float:
    value = row.get(col, default)
    out = safe_float(value, default=float("nan"))
    return out if math.isfinite(out) else default


def row_str(row: pd.Series, col: str, default: str = "") -> str:
    value = row.get(col, default)
    if pd.isna(value):
        return default
    return str(value)


def row_max_hold_hours(row: pd.Series, fallback: float) -> float:
    value = row_float(row, "max_hold_hours", fallback)
    return value if math.isfinite(value) and value > 0 else fallback


def build_close_key(signal_key: str, condition_id: str, horizon_time: pd.Timestamp) -> str:
    return f"{condition_id}|{signal_key}|TIME_EXIT|{horizon_time.strftime('%Y-%m-%d %H:%M:%S')}"


def close_log_keys(close_log: pd.DataFrame) -> set[str]:
    if close_log.empty or "close_key" not in close_log.columns:
        return set()
    return set(close_log["close_key"].astype(str))


def build_base_monitor_row(*, monitor_time: str, csv_dir: Path, signal: pd.Series, latest_m5_time: object = "", latest_m5_close_time: object = "", m5_first_time: object = "", m5_last_time: object = "") -> dict[str, Any]:
    return {
        "monitor_time_utc": monitor_time,
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": row_str(signal, "condition_id"),
        "csv_dir": str(csv_dir),
        "signal_key": row_str(signal, "signal_key"),
        "symbol": row_str(signal, "symbol", SYMBOL),
        "direction": row_str(signal, "direction", DIRECTION),
        "rank": row_str(signal, "rank"),
        "signal_group": row_str(signal, "signal_group"),
        "entry_time": signal.get("entry_time", ""),
        "entry_price_reference": row_float(signal, "entry_price_reference"),
        "sl_price": row_float(signal, "sl_price"),
        "tp_price": row_float(signal, "tp_price"),
        "risk_price": row_float(signal, "risk_price"),
        "reward_price": row_float(signal, "reward_price"),
        "rr": row_float(signal, "rr", 2.0),
        "max_hold_hours": row_float(signal, "max_hold_hours", 12.0),
        "base_lot": row_float(signal, "base_lot", 0.0),
        "lot_multiplier": row_float(signal, "lot_multiplier", 0.0),
        "effective_lot": row_float(signal, "effective_lot", 0.0),
        "horizon_time": "",
        "latest_m5_time": latest_m5_time,
        "latest_m5_close_time": latest_m5_close_time,
        "m5_first_time": m5_first_time,
        "m5_last_time": m5_last_time,
        "bars_checked": 0,
        "outcome": "",
        "position_status": "",
        "exit_time_reference": "",
        "exit_price_reference": "",
        "realized_r_reference": "",
        "lot_weighted_r_reference": "",
        "close_intent_required": False,
        "close_intent_duplicate": False,
        "close_key": "",
        "reason": "",
    }

# The rest of this backup file is intentionally abbreviated in comments? No.
# For actual rollback, prefer the backup branch:
# backup/sell-ab-m5-monitor-before-m1-20260508
# which contains the complete original active M5 monitor and cycle runner.


def main() -> int:
    raise SystemExit(
        "This is a backup stub. Use branch backup/sell-ab-m5-monitor-before-m1-20260508 for the full M5 implementation."
    )


if __name__ == "__main__":
    raise SystemExit(main())
