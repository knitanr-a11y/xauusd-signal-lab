#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Dry-run position monitor once for GOLD C_ENV RR2 72h setup.

This script is intentionally separated from Mochipoyo live/demo/autotrade code.

It reads the dedicated dry-run signal ledger created by:

    scripts/run_gold_c_env_rr2_72h_live_scan_once.py

and checks whether each DRY_RUN_SIGNAL_CREATED row is still unresolved,
has hypothetically touched TP/SL in confirmed M5 data, or has reached the
72h time-exit horizon without TP/SL.

Important separation policy:
- No Discord send.
- No MT5 order placement.
- No Mochipoyo trigger-state update.
- No Mochipoyo notification ledger update.
- No existing autotrade/order-intent file update.
- No mutation of MT5 source candle CSVs.
- No mutation of signal_ledger.csv.

The only close intent this script creates is a dry-run TIME_EXIT close intent
for a signal that has not touched TP/SL and has enough confirmed M5 data to
reach entry_time + max_hold_hours.

Example:

    python scripts\run_gold_c_env_rr2_72h_position_monitor_once.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_c_env_rr2_72h_notification_and_intent_preview import CONDITION_ID  # noqa: E402
from scripts.research_gold_c_strict_h1_regular_bullish_m15_break import (  # noqa: E402
    read_ohlc_csv,
    safe_float,
)

DEFAULT_OUT_DIR = Path("data/research_results/gold_c_env_rr2_72h_live_scan")
DEFAULT_M5_FILENAME = "goldsharp_m5.csv"

SIGNAL_STATUS_CREATED = "DRY_RUN_SIGNAL_CREATED"

MONITOR_LOG_COLUMNS = [
    "monitor_time_utc",
    "condition_id",
    "csv_dir",
    "signal_key",
    "symbol",
    "direction",
    "entry_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "risk_price",
    "rr",
    "max_hold_hours",
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
    "close_intent_required",
    "close_intent_duplicate",
    "close_key",
    "reason",
]

CLOSE_INTENT_LOG_COLUMNS = [
    "created_at_utc",
    "close_key",
    "condition_id",
    "signal_key",
    "symbol",
    "direction",
    "intent_type",
    "close_reason",
    "entry_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "risk_price",
    "rr",
    "max_hold_hours",
    "horizon_time",
    "exit_time_reference",
    "exit_price_reference",
    "realized_r_reference",
    "dry_run",
    "action",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run position monitor once for GOLD C_ENV RR2 72h.")
    parser.add_argument("--csv-dir", type=Path, required=True, help="Directory containing goldsharp_m5.csv.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--ledger-csv",
        type=Path,
        default=None,
        help="Dedicated dry-run signal ledger. Default: <out-dir>/signal_ledger.csv",
    )
    parser.add_argument("--m5-filename", type=str, default=DEFAULT_M5_FILENAME)
    parser.add_argument("--max-hold-hours", type=float, default=72.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument(
        "--latest-confirmed-m5-policy",
        choices=["last", "second_last"],
        default="last",
        help="Use second_last if the live M5 CSV includes a currently forming candle as the last row.",
    )
    return parser.parse_args()


def utc_now_text() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{col: row.get(col, "") for col in columns}])
    header = not path.exists()
    df.to_csv(path, mode="a", header=header, index=False, encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_signal_ledger(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    for col in [
        "created_at_utc",
        "signal_key",
        "condition_id",
        "symbol",
        "direction",
        "entry_time",
        "entry_price_reference",
        "sl_price",
        "tp_price",
        "rr",
        "max_hold_hours",
        "status",
    ]:
        if col not in out.columns:
            out[col] = ""

    out["condition_id"] = out["condition_id"].astype(str)
    out["status"] = out["status"].astype(str)
    out = out[out["condition_id"].eq(CONDITION_ID)].copy()
    out = out[out["status"].eq(SIGNAL_STATUS_CREATED)].copy()
    if out.empty:
        return out

    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out = out.dropna(subset=["entry_time"]).copy()
    out = out.sort_values(["entry_time", "signal_key"], kind="mergesort").reset_index(drop=True)
    return out


def load_confirmed_m5(csv_dir: Path, filename: str, policy: str) -> pd.DataFrame:
    m5_path = csv_dir / filename
    m5 = read_ohlc_csv(m5_path)
    m5 = m5.sort_values("time", kind="mergesort").reset_index(drop=True)
    if policy == "second_last" and len(m5) >= 2:
        m5 = m5.iloc[:-1].copy().reset_index(drop=True)
    m5["close_time"] = m5["time"] + pd.to_timedelta(5, unit="m")
    return m5


def finite_or_default(value: object, default: float) -> float:
    out = safe_float(value, default=float("nan"))
    return out if math.isfinite(out) else default


def row_float(row: pd.Series, col: str, default: float = float("nan")) -> float:
    return finite_or_default(row.get(col, default), default)


def row_str(row: pd.Series, col: str, default: str = "") -> str:
    value = row.get(col, default)
    if pd.isna(value):
        return default
    return str(value)


def row_max_hold_hours(row: pd.Series, fallback: float) -> float:
    value = finite_or_default(row.get("max_hold_hours", fallback), fallback)
    return value if value > 0 else fallback


def build_close_key(signal_key: str, horizon_time: pd.Timestamp) -> str:
    return f"{CONDITION_ID}|{signal_key}|TIME_EXIT|{horizon_time.strftime('%Y-%m-%d %H:%M:%S')}"


def close_log_keys(close_log: pd.DataFrame) -> set[str]:
    if close_log.empty or "close_key" not in close_log.columns:
        return set()
    return set(close_log["close_key"].astype(str))


def build_base_monitor_row(
    *,
    monitor_time: str,
    csv_dir: Path,
    signal: pd.Series,
    latest_m5_time: object = "",
    latest_m5_close_time: object = "",
    m5_first_time: object = "",
    m5_last_time: object = "",
) -> dict[str, Any]:
    entry_price = row_float(signal, "entry_price_reference")
    sl_price = row_float(signal, "sl_price")
    risk_price = entry_price - sl_price if math.isfinite(entry_price) and math.isfinite(sl_price) else float("nan")

    return {
        "monitor_time_utc": monitor_time,
        "condition_id": CONDITION_ID,
        "csv_dir": str(csv_dir),
        "signal_key": row_str(signal, "signal_key"),
        "symbol": row_str(signal, "symbol", "GOLD"),
        "direction": row_str(signal, "direction", "BUY"),
        "entry_time": signal.get("entry_time", ""),
        "entry_price_reference": entry_price,
        "sl_price": sl_price,
        "tp_price": row_float(signal, "tp_price"),
        "risk_price": risk_price,
        "rr": row_float(signal, "rr", 2.0),
        "max_hold_hours": row_float(signal, "max_hold_hours", 72.0),
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
        "close_intent_required": False,
        "close_intent_duplicate": False,
        "close_key": "",
        "reason": "",
    }


def evaluate_signal(
    *,
    signal: pd.Series,
    m5: pd.DataFrame,
    monitor_time: str,
    csv_dir: Path,
    max_hold_fallback: float,
    inbar_priority: str,
    existing_close_keys: set[str],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    latest_m5_time = "" if m5.empty else pd.Timestamp(m5["time"].max())
    latest_m5_close_time = "" if m5.empty else pd.Timestamp(m5["close_time"].max())
    m5_first_time = "" if m5.empty else pd.Timestamp(m5["time"].min())
    m5_last_time = "" if m5.empty else pd.Timestamp(m5["time"].max())

    monitor_row = build_base_monitor_row(
        monitor_time=monitor_time,
        csv_dir=csv_dir,
        signal=signal,
        latest_m5_time=latest_m5_time,
        latest_m5_close_time=latest_m5_close_time,
        m5_first_time=m5_first_time,
        m5_last_time=m5_last_time,
    )

    signal_key = row_str(signal, "signal_key")
    entry_time = pd.Timestamp(signal["entry_time"])
    entry_price = row_float(signal, "entry_price_reference")
    sl_price = row_float(signal, "sl_price")
    tp_price = row_float(signal, "tp_price")
    rr = row_float(signal, "rr", 2.0)
    max_hold_hours = row_max_hold_hours(signal, max_hold_fallback)
    risk_price = entry_price - sl_price if math.isfinite(entry_price) and math.isfinite(sl_price) else float("nan")
    horizon_time = entry_time + pd.to_timedelta(max_hold_hours, unit="h")

    monitor_row.update(
        {
            "entry_time": entry_time,
            "risk_price": risk_price,
            "rr": rr,
            "max_hold_hours": max_hold_hours,
            "horizon_time": horizon_time,
        }
    )

    if not all(math.isfinite(v) for v in [entry_price, sl_price, tp_price, risk_price]) or risk_price <= 0:
        monitor_row.update(
            {
                "outcome": "INVALID_RISK",
                "position_status": "INVALID_SIGNAL_RISK",
                "reason": "Entry/SL/TP/risk values are invalid.",
            }
        )
        return monitor_row, None

    if m5.empty:
        monitor_row.update(
            {
                "outcome": "NO_M5_PATH",
                "position_status": "NO_M5_DATA",
                "reason": "M5 CSV has no confirmed rows.",
            }
        )
        return monitor_row, None

    if entry_time < pd.Timestamp(m5_first_time):
        monitor_row.update(
            {
                "outcome": "NO_M5_PATH",
                "position_status": "NO_M5_PATH",
                "reason": "Entry time is earlier than first available M5 candle.",
            }
        )
        return monitor_row, None

    if pd.Timestamp(latest_m5_close_time) <= entry_time:
        monitor_row.update(
            {
                "outcome": "OPEN",
                "position_status": "WAITING_FOR_M5_AFTER_ENTRY",
                "reason": "No confirmed M5 bar after entry yet.",
            }
        )
        return monitor_row, None

    touch_path = m5[(m5["time"] >= entry_time) & (m5["time"] < horizon_time)].copy()
    touch_path = touch_path.sort_values("time", kind="mergesort").reset_index(drop=True)
    monitor_row["bars_checked"] = int(len(touch_path))

    for checked, (_, bar) in enumerate(touch_path.iterrows(), start=1):
        low = safe_float(bar.get("low"))
        high = safe_float(bar.get("high"))
        bar_time = pd.Timestamp(bar["time"])
        hit_sl = math.isfinite(low) and low <= sl_price
        hit_tp = math.isfinite(high) and high >= tp_price

        if hit_sl and hit_tp:
            if str(inbar_priority).upper() == "TP":
                realized_r = (tp_price - entry_price) / risk_price
                monitor_row.update(
                    {
                        "bars_checked": checked,
                        "outcome": "WIN",
                        "position_status": "TP_TOUCHED_DRY_RUN",
                        "exit_time_reference": bar_time,
                        "exit_price_reference": tp_price,
                        "realized_r_reference": realized_r,
                        "reason": "TP and SL touched in same M5 bar; TP priority was requested.",
                    }
                )
            else:
                monitor_row.update(
                    {
                        "bars_checked": checked,
                        "outcome": "LOSS",
                        "position_status": "SL_TOUCHED_DRY_RUN",
                        "exit_time_reference": bar_time,
                        "exit_price_reference": sl_price,
                        "realized_r_reference": -1.0,
                        "reason": "TP and SL touched in same M5 bar; SL priority was used.",
                    }
                )
            return monitor_row, None

        if hit_sl:
            monitor_row.update(
                {
                    "bars_checked": checked,
                    "outcome": "LOSS",
                    "position_status": "SL_TOUCHED_DRY_RUN",
                    "exit_time_reference": bar_time,
                    "exit_price_reference": sl_price,
                    "realized_r_reference": -1.0,
                    "reason": "SL was touched before TP within the 72h path.",
                }
            )
            return monitor_row, None

        if hit_tp:
            realized_r = (tp_price - entry_price) / risk_price
            monitor_row.update(
                {
                    "bars_checked": checked,
                    "outcome": "WIN",
                    "position_status": "TP_TOUCHED_DRY_RUN",
                    "exit_time_reference": bar_time,
                    "exit_price_reference": tp_price,
                    "realized_r_reference": realized_r,
                    "reason": "TP was touched before SL within the 72h path.",
                }
            )
            return monitor_row, None

    if pd.Timestamp(latest_m5_close_time) < horizon_time:
        monitor_row.update(
            {
                "outcome": "OPEN",
                "position_status": "OPEN_UNRESOLVED_BEFORE_72H",
                "reason": "No TP/SL touch yet and confirmed M5 data has not reached the 72h horizon.",
            }
        )
        return monitor_row, None

    horizon_path = m5[(m5["time"] >= entry_time) & (m5["time"] < horizon_time)].copy()
    horizon_path = horizon_path.sort_values("time", kind="mergesort").reset_index(drop=True)
    if horizon_path.empty:
        monitor_row.update(
            {
                "outcome": "NO_M5_PATH",
                "position_status": "NO_M5_PATH_TO_HORIZON",
                "reason": "No M5 rows were available between entry and the 72h horizon.",
            }
        )
        return monitor_row, None

    last = horizon_path.iloc[-1]
    exit_time = pd.Timestamp(last["time"])
    exit_price = safe_float(last.get("close"))
    realized_r = (exit_price - entry_price) / risk_price if math.isfinite(exit_price) else float("nan")
    close_key = build_close_key(signal_key, horizon_time)
    duplicate = close_key in existing_close_keys

    monitor_row.update(
        {
            "outcome": "TIME_EXIT",
            "position_status": "TIME_EXIT_ALREADY_LOGGED" if duplicate else "TIME_EXIT_CLOSE_INTENT_REQUIRED",
            "exit_time_reference": exit_time,
            "exit_price_reference": exit_price,
            "realized_r_reference": realized_r,
            "close_intent_required": not duplicate,
            "close_intent_duplicate": duplicate,
            "close_key": close_key,
            "reason": "72h horizon reached without TP/SL touch.",
        }
    )

    if duplicate:
        return monitor_row, None

    intent = {
        "schema_version": "gold_c_env_rr2_72h_close_intent_v1",
        "dry_run": True,
        "intent_type": "CLOSE_POSITION",
        "close_reason": "TIME_EXIT_72H",
        "action": "DRY_RUN_ONLY_NO_MT5_CLOSE_ORDER",
        "condition_id": CONDITION_ID,
        "strategy_id": CONDITION_ID,
        "signal_key": signal_key,
        "close_key": close_key,
        "symbol": row_str(signal, "symbol", "GOLD"),
        "direction": row_str(signal, "direction", "BUY"),
        "close_side": "SELL",
        "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_price_reference": entry_price,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "risk_price": risk_price,
        "rr": rr,
        "max_hold_hours": max_hold_hours,
        "horizon_time": horizon_time.strftime("%Y-%m-%d %H:%M:%S"),
        "exit_time_reference": exit_time.strftime("%Y-%m-%d %H:%M:%S"),
        "exit_price_reference": exit_price,
        "realized_r_reference": realized_r,
        "source_signal_ledger_row": {str(k): ("" if pd.isna(v) else str(v)) for k, v in signal.to_dict().items()},
    }
    return monitor_row, intent


def flatten_close_intent(intent: dict[str, Any], created_at_utc: str) -> dict[str, Any]:
    return {
        "created_at_utc": created_at_utc,
        "close_key": intent.get("close_key", ""),
        "condition_id": intent.get("condition_id", ""),
        "signal_key": intent.get("signal_key", ""),
        "symbol": intent.get("symbol", ""),
        "direction": intent.get("direction", ""),
        "intent_type": intent.get("intent_type", ""),
        "close_reason": intent.get("close_reason", ""),
        "entry_time": intent.get("entry_time", ""),
        "entry_price_reference": intent.get("entry_price_reference", ""),
        "sl_price": intent.get("sl_price", ""),
        "tp_price": intent.get("tp_price", ""),
        "risk_price": intent.get("risk_price", ""),
        "rr": intent.get("rr", ""),
        "max_hold_hours": intent.get("max_hold_hours", ""),
        "horizon_time": intent.get("horizon_time", ""),
        "exit_time_reference": intent.get("exit_time_reference", ""),
        "exit_price_reference": intent.get("exit_price_reference", ""),
        "realized_r_reference": intent.get("realized_r_reference", ""),
        "dry_run": intent.get("dry_run", True),
        "action": intent.get("action", ""),
    }


def summarize_monitor_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "signals_monitored": len(rows),
        "open_unresolved": 0,
        "tp_touched": 0,
        "sl_touched": 0,
        "time_exit_required": 0,
        "time_exit_already_logged": 0,
        "no_m5_path": 0,
        "invalid_risk": 0,
    }
    for row in rows:
        status = str(row.get("position_status", ""))
        outcome = str(row.get("outcome", ""))
        if status == "OPEN_UNRESOLVED_BEFORE_72H" or status == "WAITING_FOR_M5_AFTER_ENTRY":
            counts["open_unresolved"] += 1
        if status == "TP_TOUCHED_DRY_RUN":
            counts["tp_touched"] += 1
        if status == "SL_TOUCHED_DRY_RUN":
            counts["sl_touched"] += 1
        if status == "TIME_EXIT_CLOSE_INTENT_REQUIRED":
            counts["time_exit_required"] += 1
        if status == "TIME_EXIT_ALREADY_LOGGED":
            counts["time_exit_already_logged"] += 1
        if outcome == "NO_M5_PATH":
            counts["no_m5_path"] += 1
        if outcome == "INVALID_RISK":
            counts["invalid_risk"] += 1
    return counts


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    monitor_time = utc_now_text()
    ledger_path = args.ledger_csv if args.ledger_csv is not None else args.out_dir / "signal_ledger.csv"
    close_log_path = args.out_dir / "close_intent_log.csv"
    monitor_log_path = args.out_dir / "position_monitor_log.csv"
    latest_result_path = args.out_dir / "latest_position_monitor_result.json"
    close_intent_path = args.out_dir / "close_intent_dry_run.json"

    print(f"[INFO] condition_id={CONDITION_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] ledger_csv={ledger_path}")

    ledger_raw = read_csv_or_empty(ledger_path)
    signals = normalize_signal_ledger(ledger_raw)
    close_log = read_csv_or_empty(close_log_path)
    existing_close_keys = close_log_keys(close_log)

    if signals.empty:
        result = {
            "scan_time_utc": monitor_time,
            "condition_id": CONDITION_ID,
            "signals_monitored": 0,
            "close_intent_created": 0,
            "reason": "NO_DRY_RUN_SIGNAL_CREATED_ROWS",
            "ledger_csv": str(ledger_path),
            "close_intent_log": str(close_log_path),
        }
        write_json(latest_result_path, result)
        print("[INFO] no DRY_RUN_SIGNAL_CREATED rows to monitor")
        return 0

    print(f"[INFO] loading M5: {args.csv_dir / args.m5_filename}")
    m5 = load_confirmed_m5(args.csv_dir, args.m5_filename, args.latest_confirmed_m5_policy)

    monitor_rows: list[dict[str, Any]] = []
    new_close_intents: list[dict[str, Any]] = []

    for _, signal in signals.iterrows():
        monitor_row, intent = evaluate_signal(
            signal=signal,
            m5=m5,
            monitor_time=monitor_time,
            csv_dir=args.csv_dir,
            max_hold_fallback=float(args.max_hold_hours),
            inbar_priority=str(args.inbar_priority),
            existing_close_keys=existing_close_keys,
        )
        monitor_rows.append(monitor_row)
        if intent is not None:
            new_close_intents.append(intent)
            existing_close_keys.add(str(intent["close_key"]))
            append_csv_row(
                close_log_path,
                flatten_close_intent(intent, created_at_utc=monitor_time),
                CLOSE_INTENT_LOG_COLUMNS,
            )

    monitor_df = pd.DataFrame(monitor_rows)
    write_csv(monitor_df, args.out_dir / "latest_position_monitor_rows.csv")
    for row in monitor_rows:
        append_csv_row(monitor_log_path, row, MONITOR_LOG_COLUMNS)

    if new_close_intents:
        write_json(
            close_intent_path,
            {
                "schema_version": "gold_c_env_rr2_72h_close_intent_batch_v1",
                "created_at_utc": monitor_time,
                "condition_id": CONDITION_ID,
                "dry_run": True,
                "intent_count": len(new_close_intents),
                "intents": new_close_intents,
            },
        )

    counts = summarize_monitor_rows(monitor_rows)
    result = {
        "scan_time_utc": monitor_time,
        "condition_id": CONDITION_ID,
        **counts,
        "close_intent_created": len(new_close_intents),
        "latest_m5_time": "" if m5.empty else str(pd.Timestamp(m5["time"].max())),
        "latest_m5_close_time": "" if m5.empty else str(pd.Timestamp(m5["close_time"].max())),
        "ledger_csv": str(ledger_path),
        "outputs": {
            "latest_position_monitor_rows": str(args.out_dir / "latest_position_monitor_rows.csv"),
            "position_monitor_log": str(monitor_log_path),
            "close_intent_log": str(close_log_path),
            "close_intent_dry_run": str(close_intent_path) if new_close_intents else "",
        },
        "reason": "POSITION_MONITOR_COMPLETED",
    }
    write_json(latest_result_path, result)

    print("[INFO] position monitor completed")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
