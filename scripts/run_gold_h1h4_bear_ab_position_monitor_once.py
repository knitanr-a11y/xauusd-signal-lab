#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Dry-run position monitor once for GOLD bearish A/B classifier.

This script is intentionally separated from Mochipoyo live/demo/autotrade code
and from the BUY-side C_ENV dry-run directory.

It reads the dedicated SELL signal ledger created by:

    scripts/run_gold_h1h4_bear_ab_live_scan_once.py

and checks each unresolved DRY_RUN_SIGNAL_CREATED row against confirmed M1 data.

SELL-specific rules:
- TP touch: M1 low <= tp_price
- SL touch: M1 high >= sl_price
- same-M1 conflict: default conservative SL priority
- realized R: (entry_price - exit_price) / risk_price
- close_side for close intent: BUY

Resolved-position handling:
- TP/SL/TIME_EXIT terminal outcomes are appended once to position_result_ledger.csv
- Any signal_key already present in position_result_ledger.csv is skipped on later monitor runs
- signal_ledger.csv is not mutated

No Discord send.
No MT5 order placement.
No Mochipoyo trigger-state update.
No Mochipoyo ledger update.
No existing autotrade/order-intent file update.
No mutation of MT5 source candle CSVs.
No mutation of signal_ledger.csv.

Backup note:
    The previous M5 monitor version is preserved on branch:
    backup/sell-ab-m5-monitor-before-m1-20260508
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

REPO_ROOT = Path(__file__).resolve().parents[1]
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
DEFAULT_M1_FILENAME = "goldsharp_m1.csv"
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
    "latest_m1_time",
    "latest_m1_close_time",
    "m1_first_time",
    "m1_last_time",
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

POSITION_RESULT_LEDGER_COLUMNS = [
    "resolved_at_utc",
    "condition_family_id",
    "condition_id",
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
    "outcome",
    "position_status",
    "exit_time_reference",
    "exit_price_reference",
    "realized_r_reference",
    "lot_weighted_r_reference",
    "bars_checked",
    "close_key",
    "close_intent_required",
    "close_intent_duplicate",
    "reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run M1 position monitor once for GOLD bearish A/B classifier.")
    parser.add_argument("--csv-dir", type=Path, required=True, help="Directory containing goldsharp_m1.csv.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--ledger-csv", type=Path, default=None, help="Default: <out-dir>/signal_ledger.csv")
    parser.add_argument("--position-result-ledger-csv", type=Path, default=None, help="Default: <out-dir>/position_result_ledger.csv")
    parser.add_argument("--m1-filename", type=str, default=DEFAULT_M1_FILENAME)
    parser.add_argument("--max-hold-hours", type=float, default=12.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument(
        "--latest-confirmed-m1-policy",
        choices=["last", "second_last"],
        default="last",
        help="Use second_last if the live M1 CSV includes a forming candle as the last row.",
    )
    parser.add_argument(
        "--latest-confirmed-m5-policy",
        choices=["last", "second_last"],
        default=None,
        help="Deprecated compatibility alias. If provided, it is mapped to --latest-confirmed-m1-policy.",
    )
    parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Re-monitor already resolved signal_keys. Default skips rows found in position_result_ledger.csv.",
    )
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
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


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
    required = [
        "signal_key",
        "condition_family_id",
        "condition_id",
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
        "trade_enabled",
        "status",
    ]
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


def normalize_position_result_ledger(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=POSITION_RESULT_LEDGER_COLUMNS)
    out = df.copy()
    for col in POSITION_RESULT_LEDGER_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out = out[out["condition_family_id"].astype(str).eq(CONDITION_FAMILY_ID)].copy()
    return out[POSITION_RESULT_LEDGER_COLUMNS].copy()


def resolved_signal_keys(position_result_ledger: pd.DataFrame) -> set[str]:
    if position_result_ledger.empty or "signal_key" not in position_result_ledger.columns:
        return set()
    return set(position_result_ledger["signal_key"].astype(str))


def load_confirmed_m1(csv_dir: Path, filename: str, policy: str) -> pd.DataFrame:
    m1 = read_ohlc_csv(csv_dir / filename).sort_values("time", kind="mergesort").reset_index(drop=True)
    if policy == "second_last" and len(m1) >= 2:
        m1 = m1.iloc[:-1].copy().reset_index(drop=True)
    m1["close_time"] = m1["time"] + pd.to_timedelta(1, unit="m")
    return m1


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


def build_base_monitor_row(
    *,
    monitor_time: str,
    csv_dir: Path,
    signal: pd.Series,
    latest_m1_time: object = "",
    latest_m1_close_time: object = "",
    m1_first_time: object = "",
    m1_last_time: object = "",
) -> dict[str, Any]:
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
        "latest_m1_time": latest_m1_time,
        "latest_m1_close_time": latest_m1_close_time,
        "m1_first_time": m1_first_time,
        "m1_last_time": m1_last_time,
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


def evaluate_signal(
    *,
    signal: pd.Series,
    m1: pd.DataFrame,
    monitor_time: str,
    csv_dir: Path,
    max_hold_fallback: float,
    inbar_priority: str,
    existing_close_keys: set[str],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    latest_m1_time = "" if m1.empty else pd.Timestamp(m1["time"].max())
    latest_m1_close_time = "" if m1.empty else pd.Timestamp(m1["close_time"].max())
    m1_first_time = "" if m1.empty else pd.Timestamp(m1["time"].min())
    m1_last_time = "" if m1.empty else pd.Timestamp(m1["time"].max())
    row = build_base_monitor_row(
        monitor_time=monitor_time,
        csv_dir=csv_dir,
        signal=signal,
        latest_m1_time=latest_m1_time,
        latest_m1_close_time=latest_m1_close_time,
        m1_first_time=m1_first_time,
        m1_last_time=m1_last_time,
    )

    signal_key = row_str(signal, "signal_key")
    condition_id = row_str(signal, "condition_id")
    entry_time = pd.Timestamp(signal["entry_time"])
    entry_price = row_float(signal, "entry_price_reference")
    sl_price = row_float(signal, "sl_price")
    tp_price = row_float(signal, "tp_price")
    risk_price = row_float(signal, "risk_price")
    rr = row_float(signal, "rr", 2.0)
    max_hold_hours = row_max_hold_hours(signal, max_hold_fallback)
    lot_multiplier = row_float(signal, "lot_multiplier", 0.0)
    horizon_time = entry_time + pd.to_timedelta(max_hold_hours, unit="h")
    row.update({"entry_time": entry_time, "horizon_time": horizon_time, "max_hold_hours": max_hold_hours})

    if not all(math.isfinite(v) for v in [entry_price, sl_price, tp_price, risk_price]) or risk_price <= 0:
        row.update({"outcome": "INVALID_RISK", "position_status": "INVALID_SIGNAL_RISK", "reason": "Entry/SL/TP/risk values are invalid."})
        return row, None
    if m1.empty:
        row.update({"outcome": "NO_M1_PATH", "position_status": "NO_M1_DATA", "reason": "M1 CSV has no confirmed rows."})
        return row, None
    if entry_time < pd.Timestamp(m1_first_time):
        row.update({"outcome": "NO_M1_PATH", "position_status": "NO_M1_PATH", "reason": "Entry time is earlier than first available M1 candle."})
        return row, None
    if pd.Timestamp(latest_m1_close_time) <= entry_time:
        row.update({"outcome": "OPEN", "position_status": "WAITING_FOR_M1_AFTER_ENTRY", "reason": "No confirmed M1 bar after entry yet."})
        return row, None

    path = m1[(m1["time"] >= entry_time) & (m1["time"] < horizon_time)].copy()
    path = path.sort_values("time", kind="mergesort").reset_index(drop=True)
    row["bars_checked"] = int(len(path))

    for checked, (_, bar) in enumerate(path.iterrows(), start=1):
        low = safe_float(bar.get("low"))
        high = safe_float(bar.get("high"))
        bar_time = pd.Timestamp(bar["time"])
        hit_tp = math.isfinite(low) and low <= tp_price
        hit_sl = math.isfinite(high) and high >= sl_price
        if hit_tp and hit_sl:
            if str(inbar_priority).upper() == "TP":
                realized_r = (entry_price - tp_price) / risk_price
                row.update({"bars_checked": checked, "outcome": "WIN", "position_status": "TP_TOUCHED_DRY_RUN", "exit_time_reference": bar_time, "exit_price_reference": tp_price, "realized_r_reference": realized_r, "lot_weighted_r_reference": realized_r * lot_multiplier, "reason": "TP and SL touched in same M1 bar; TP priority was requested."})
            else:
                row.update({"bars_checked": checked, "outcome": "LOSS", "position_status": "SL_TOUCHED_DRY_RUN", "exit_time_reference": bar_time, "exit_price_reference": sl_price, "realized_r_reference": -1.0, "lot_weighted_r_reference": -1.0 * lot_multiplier, "reason": "TP and SL touched in same M1 bar; SL priority was used."})
            return row, None
        if hit_sl:
            row.update({"bars_checked": checked, "outcome": "LOSS", "position_status": "SL_TOUCHED_DRY_RUN", "exit_time_reference": bar_time, "exit_price_reference": sl_price, "realized_r_reference": -1.0, "lot_weighted_r_reference": -1.0 * lot_multiplier, "reason": "SL was touched before TP."})
            return row, None
        if hit_tp:
            realized_r = (entry_price - tp_price) / risk_price
            row.update({"bars_checked": checked, "outcome": "WIN", "position_status": "TP_TOUCHED_DRY_RUN", "exit_time_reference": bar_time, "exit_price_reference": tp_price, "realized_r_reference": realized_r, "lot_weighted_r_reference": realized_r * lot_multiplier, "reason": "TP was touched before SL."})
            return row, None

    if pd.Timestamp(latest_m1_close_time) < horizon_time:
        row.update({"outcome": "OPEN", "position_status": "OPEN_UNRESOLVED_BEFORE_HORIZON", "reason": "No TP/SL touch yet and confirmed M1 data has not reached the horizon."})
        return row, None

    if path.empty:
        row.update({"outcome": "NO_M1_PATH", "position_status": "NO_M1_PATH_TO_HORIZON", "reason": "No M1 rows were available between entry and horizon."})
        return row, None

    last = path.iloc[-1]
    exit_time = pd.Timestamp(last["time"])
    exit_price = safe_float(last.get("close"))
    realized_r = (entry_price - exit_price) / risk_price if math.isfinite(exit_price) else float("nan")
    close_key = build_close_key(signal_key, condition_id, horizon_time)
    duplicate = close_key in existing_close_keys
    row.update({
        "outcome": "TIME_EXIT",
        "position_status": "TIME_EXIT_ALREADY_LOGGED" if duplicate else "TIME_EXIT_CLOSE_INTENT_REQUIRED",
        "exit_time_reference": exit_time,
        "exit_price_reference": exit_price,
        "realized_r_reference": realized_r,
        "lot_weighted_r_reference": realized_r * lot_multiplier if math.isfinite(realized_r) else float("nan"),
        "close_intent_required": not duplicate,
        "close_intent_duplicate": duplicate,
        "close_key": close_key,
        "reason": "Hold horizon reached without TP/SL touch.",
    })
    if duplicate:
        return row, None

    intent = {
        "schema_version": "gold_h1h4_bear_ab_classifier_close_intent_v1",
        "dry_run": True,
        "intent_type": "CLOSE_POSITION",
        "close_reason": f"TIME_EXIT_{max_hold_hours:g}H",
        "action": "DRY_RUN_ONLY_NO_MT5_CLOSE_ORDER",
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": condition_id,
        "strategy_id": CONDITION_FAMILY_ID,
        "signal_key": signal_key,
        "close_key": close_key,
        "symbol": row_str(signal, "symbol", SYMBOL),
        "direction": row_str(signal, "direction", DIRECTION),
        "rank": row_str(signal, "rank"),
        "close_side": "BUY",
        "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_price_reference": entry_price,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "risk_price": risk_price,
        "reward_price": row_float(signal, "reward_price"),
        "rr": rr,
        "max_hold_hours": max_hold_hours,
        "base_lot": row_float(signal, "base_lot", 0.0),
        "lot_multiplier": lot_multiplier,
        "effective_lot": row_float(signal, "effective_lot", 0.0),
        "horizon_time": horizon_time.strftime("%Y-%m-%d %H:%M:%S"),
        "exit_time_reference": exit_time.strftime("%Y-%m-%d %H:%M:%S"),
        "exit_price_reference": exit_price,
        "realized_r_reference": realized_r,
        "lot_weighted_r_reference": realized_r * lot_multiplier if math.isfinite(realized_r) else float("nan"),
        "source_signal_ledger_row": {str(k): ("" if pd.isna(v) else str(v)) for k, v in signal.to_dict().items()},
    }
    return row, intent


def flatten_close_intent(intent: dict[str, Any], created_at_utc: str) -> dict[str, Any]:
    return {col: (created_at_utc if col == "created_at_utc" else intent.get(col, "")) for col in CLOSE_INTENT_LOG_COLUMNS}


def is_terminal_monitor_row(row: dict[str, Any]) -> bool:
    return str(row.get("position_status", "")) in {
        "TP_TOUCHED_DRY_RUN",
        "SL_TOUCHED_DRY_RUN",
        "TIME_EXIT_CLOSE_INTENT_REQUIRED",
        "TIME_EXIT_ALREADY_LOGGED",
    }


def build_position_result_row(row: dict[str, Any], resolved_at_utc: str) -> dict[str, Any]:
    return {col: (resolved_at_utc if col == "resolved_at_utc" else row.get(col, "")) for col in POSITION_RESULT_LEDGER_COLUMNS}


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "signals_monitored": len(rows),
        "open_unresolved": 0,
        "tp_touched": 0,
        "sl_touched": 0,
        "time_exit_required": 0,
        "time_exit_already_logged": 0,
        "no_m1_path": 0,
        "invalid_risk": 0,
    }
    for row in rows:
        status = str(row.get("position_status", ""))
        outcome = str(row.get("outcome", ""))
        if status in {"OPEN_UNRESOLVED_BEFORE_HORIZON", "WAITING_FOR_M1_AFTER_ENTRY"}:
            counts["open_unresolved"] += 1
        if status == "TP_TOUCHED_DRY_RUN":
            counts["tp_touched"] += 1
        if status == "SL_TOUCHED_DRY_RUN":
            counts["sl_touched"] += 1
        if status == "TIME_EXIT_CLOSE_INTENT_REQUIRED":
            counts["time_exit_required"] += 1
        if status == "TIME_EXIT_ALREADY_LOGGED":
            counts["time_exit_already_logged"] += 1
        if outcome == "NO_M1_PATH":
            counts["no_m1_path"] += 1
        if outcome == "INVALID_RISK":
            counts["invalid_risk"] += 1
    return counts


def write_empty_outputs(*, out_dir: Path, monitor_log_path: Path, close_log_path: Path, position_result_ledger_path: Path, latest_result_path: Path, monitor_time: str, ledger_path: Path, reason: str = "NO_DRY_RUN_SIGNAL_CREATED_ROWS", resolved_skipped: int = 0) -> None:
    latest_rows_path = out_dir / "latest_position_monitor_rows.csv"
    close_intent_path = out_dir / "close_intent_dry_run.json"
    write_csv(pd.DataFrame(columns=MONITOR_LOG_COLUMNS), latest_rows_path)
    ensure_empty_csv(monitor_log_path, MONITOR_LOG_COLUMNS)
    ensure_empty_csv(close_log_path, CLOSE_INTENT_LOG_COLUMNS)
    ensure_empty_csv(position_result_ledger_path, POSITION_RESULT_LEDGER_COLUMNS)
    result = {
        "scan_time_utc": monitor_time,
        "condition_family_id": CONDITION_FAMILY_ID,
        "signals_monitored": 0,
        "resolved_skipped": int(resolved_skipped),
        "open_unresolved": 0,
        "tp_touched": 0,
        "sl_touched": 0,
        "time_exit_required": 0,
        "time_exit_already_logged": 0,
        "no_m1_path": 0,
        "invalid_risk": 0,
        "position_results_created": 0,
        "close_intent_created": 0,
        "reason": reason,
        "ledger_csv": str(ledger_path),
        "position_result_ledger_csv": str(position_result_ledger_path),
        "outputs": {
            "latest_position_monitor_rows": str(latest_rows_path),
            "position_monitor_log": str(monitor_log_path),
            "position_result_ledger": str(position_result_ledger_path),
            "close_intent_log": str(close_log_path),
            "close_intent_dry_run": str(close_intent_path) if close_intent_path.exists() else "",
        },
    }
    write_json(latest_result_path, result)


def main() -> int:
    args = parse_args()
    if args.latest_confirmed_m5_policy is not None:
        args.latest_confirmed_m1_policy = args.latest_confirmed_m5_policy
    args.out_dir.mkdir(parents=True, exist_ok=True)
    monitor_time = utc_now_text()
    ledger_path = args.ledger_csv if args.ledger_csv is not None else args.out_dir / "signal_ledger.csv"
    position_result_ledger_path = args.position_result_ledger_csv if args.position_result_ledger_csv is not None else args.out_dir / "position_result_ledger.csv"
    close_log_path = args.out_dir / "close_intent_log.csv"
    monitor_log_path = args.out_dir / "position_monitor_log.csv"
    latest_result_path = args.out_dir / "latest_position_monitor_result.json"
    close_intent_path = args.out_dir / "close_intent_dry_run.json"

    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] ledger_csv={ledger_path}")
    print(f"[INFO] position_result_ledger_csv={position_result_ledger_path}")
    print(f"[INFO] m1_filename={args.m1_filename}")

    ledger = normalize_signal_ledger(read_csv_or_empty(ledger_path))
    position_result_ledger = normalize_position_result_ledger(read_csv_or_empty(position_result_ledger_path))
    ensure_empty_csv(position_result_ledger_path, POSITION_RESULT_LEDGER_COLUMNS)
    resolved_keys = resolved_signal_keys(position_result_ledger)
    resolved_skipped = 0
    if not ledger.empty and not args.include_resolved:
        before = len(ledger)
        ledger = ledger[~ledger["signal_key"].astype(str).isin(resolved_keys)].copy().reset_index(drop=True)
        resolved_skipped = before - len(ledger)

    close_log = read_csv_or_empty(close_log_path)
    existing_close_keys = close_log_keys(close_log)
    if ledger.empty:
        reason = "NO_UNRESOLVED_DRY_RUN_SIGNAL_ROWS" if resolved_skipped else "NO_DRY_RUN_SIGNAL_CREATED_ROWS"
        write_empty_outputs(out_dir=args.out_dir, monitor_log_path=monitor_log_path, close_log_path=close_log_path, position_result_ledger_path=position_result_ledger_path, latest_result_path=latest_result_path, monitor_time=monitor_time, ledger_path=ledger_path, reason=reason, resolved_skipped=resolved_skipped)
        print(f"[INFO] {reason}")
        return 0

    m1 = load_confirmed_m1(args.csv_dir, args.m1_filename, args.latest_confirmed_m1_policy)
    rows: list[dict[str, Any]] = []
    intents: list[dict[str, Any]] = []
    position_results_created = 0
    current_resolved_keys = set(resolved_keys)

    for _, signal in ledger.iterrows():
        monitor_row, intent = evaluate_signal(
            signal=signal,
            m1=m1,
            monitor_time=monitor_time,
            csv_dir=args.csv_dir,
            max_hold_fallback=float(args.max_hold_hours),
            inbar_priority=str(args.inbar_priority),
            existing_close_keys=existing_close_keys,
        )
        rows.append(monitor_row)
        if intent is not None:
            intents.append(intent)
            existing_close_keys.add(str(intent["close_key"]))
            append_csv_row(close_log_path, flatten_close_intent(intent, monitor_time), CLOSE_INTENT_LOG_COLUMNS)

        signal_key = str(monitor_row.get("signal_key", ""))
        if is_terminal_monitor_row(monitor_row) and signal_key and signal_key not in current_resolved_keys:
            append_csv_row(position_result_ledger_path, build_position_result_row(monitor_row, monitor_time), POSITION_RESULT_LEDGER_COLUMNS)
            current_resolved_keys.add(signal_key)
            position_results_created += 1

    monitor_df = pd.DataFrame(rows)
    write_csv(monitor_df, args.out_dir / "latest_position_monitor_rows.csv")
    for row in rows:
        append_csv_row(monitor_log_path, row, MONITOR_LOG_COLUMNS)
    ensure_empty_csv(close_log_path, CLOSE_INTENT_LOG_COLUMNS)
    ensure_empty_csv(position_result_ledger_path, POSITION_RESULT_LEDGER_COLUMNS)

    if intents:
        write_json(close_intent_path, {
            "schema_version": "gold_h1h4_bear_ab_classifier_close_intent_batch_v1",
            "created_at_utc": monitor_time,
            "condition_family_id": CONDITION_FAMILY_ID,
            "dry_run": True,
            "intent_count": len(intents),
            "intents": intents,
        })

    result = {
        "scan_time_utc": monitor_time,
        "condition_family_id": CONDITION_FAMILY_ID,
        **summarize(rows),
        "resolved_skipped": int(resolved_skipped),
        "position_results_created": int(position_results_created),
        "close_intent_created": len(intents),
        "latest_m1_time": "" if m1.empty else str(pd.Timestamp(m1["time"].max())),
        "latest_m1_close_time": "" if m1.empty else str(pd.Timestamp(m1["close_time"].max())),
        "ledger_csv": str(ledger_path),
        "position_result_ledger_csv": str(position_result_ledger_path),
        "outputs": {
            "latest_position_monitor_rows": str(args.out_dir / "latest_position_monitor_rows.csv"),
            "position_monitor_log": str(monitor_log_path),
            "position_result_ledger": str(position_result_ledger_path),
            "close_intent_log": str(close_log_path),
            "close_intent_dry_run": str(close_intent_path) if intents else "",
        },
        "reason": "POSITION_MONITOR_COMPLETED",
    }
    write_json(latest_result_path, result)
    print("[INFO] position monitor completed")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
