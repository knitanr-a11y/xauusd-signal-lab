#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Dry-run live scan once for GOLD C_ENV RR2 72h setup.

This is intentionally separated from Mochipoyo live/demo/autotrade code.
It reads GOLD CSVs, checks only the latest confirmed M15 signal point, and
writes research/dry-run outputs only.

No Discord send.
No order placement.
No Mochipoyo trigger-state update.
No Mochipoyo ledger update.
No autotrade/order-intent file used by existing live flow.

Strategy:
    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H

Outputs in --out-dir:
    latest_scan_result.json
    latest_signal_payload.json              only when a new signal is eligible
    order_intent_dry_run.json               only when a new signal is eligible
    notification_preview_latest.txt         only when a new signal is eligible
    live_scan_log.csv
    signal_ledger.csv

Windows path policy:
    This script writes its own JSON/CSV/TXT outputs through Windows long-path helpers.

Example:
    python scripts\run_gold_c_env_rr2_72h_live_scan_once.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_c_env_rr2_72h_notification_and_intent_preview import (  # noqa: E402
    CONDITION_ID,
    build_order_intent,
    build_signal_payload,
    notification_text,
)
from scripts.research_gold_c_env_rr2_sl_breakout_grid_no_timeout import (  # noqa: E402
    build_m15_trigger_base_for_lookback,
    build_trade_candidates_grid,
)
from scripts.research_gold_c_strict_h1_regular_bullish_m15_break import (  # noqa: E402
    add_indicators,
    build_data_coverage,
    build_h1_events,
    load_research_csvs,
)
from scripts.research_gold_h4_permission_modes_h1_regular_bullish_m15_break import prepare_h4_env_frame  # noqa: E402

DEFAULT_OUT_DIR = Path("data/research_results/gold_c_env_rr2_72h_live_scan")
LEDGER_COLUMNS = [
    "created_at_utc",
    "signal_key",
    "condition_id",
    "symbol",
    "direction",
    "entry_time",
    "h1_event_id",
    "h1_pivot_confirm_time",
    "m15_close_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "rr",
    "max_hold_hours",
    "status",
]
LOG_COLUMNS = [
    "scan_time_utc",
    "condition_id",
    "csv_dir",
    "latest_m15_close_time",
    "candidate_count",
    "latest_candidate_entry_time",
    "signal_found",
    "duplicate",
    "signal_key",
    "reason",
]


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


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def write_df_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent_dir(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dry-run live scan once for GOLD C_ENV RR2 72h setup.")
    p.add_argument("--csv-dir", type=Path, required=True, help="Directory containing goldsharp_h4/h1/m15/m5 CSVs.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--pivot-left", type=int, default=2)
    p.add_argument("--pivot-right", type=int, default=2)
    p.add_argument("--entry-window-hours", type=float, default=12.0)
    p.add_argument("--breakout-lookback", type=int, default=8)
    p.add_argument("--sl-lookback-m15", type=int, default=12)
    p.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--max-hold-hours", type=int, default=72)
    p.add_argument("--risk-mode", type=str, default="dry_run_no_lot")
    p.add_argument(
        "--latest-confirmed-policy",
        choices=["last", "second_last"],
        default="last",
        help="Use last M15 row close_time as latest confirmed by default. Use second_last if live CSV includes a forming candle.",
    )
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_ledger(path: Path) -> pd.DataFrame:
    if not Path(windows_long_path(path)).exists():
        return pd.DataFrame(columns=LEDGER_COLUMNS)
    df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[LEDGER_COLUMNS].copy()


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    df = pd.DataFrame([{col: row.get(col, "") for col in columns}])
    header = not Path(windows_long_path(path)).exists()
    df.to_csv(windows_long_path(path), mode="a", header=header, index=False, encoding="utf-8-sig")


def latest_m15_close_time(m15: pd.DataFrame, *, policy: str) -> pd.Timestamp | None:
    if m15.empty:
        return None
    m15_sorted = m15.sort_values("close_time", kind="mergesort").reset_index(drop=True)
    if policy == "second_last" and len(m15_sorted) >= 2:
        return pd.Timestamp(m15_sorted.iloc[-2]["close_time"])
    return pd.Timestamp(m15_sorted.iloc[-1]["close_time"])


def build_signal_key(row: pd.Series) -> str:
    return "|".join(
        [
            CONDITION_ID,
            str(row.get("symbol", "GOLD")),
            str(row.get("direction", "BUY")),
            str(row.get("entry_time", "")),
            str(row.get("h1_event_id", "")),
            str(row.get("m15_close_time", "")),
        ]
    )


def normalize_live_row(row: pd.Series, *, max_hold_hours: int) -> pd.Series:
    out = row.copy()
    out["condition_id"] = CONDITION_ID
    out["max_hold_hours"] = max_hold_hours
    out["exit_rule"] = "TP/SL first-touch; if unresolved, time exit around 72h"
    out["outcome"] = "LIVE_DRY_RUN_SIGNAL"
    out["realized_r"] = 0.0
    out["exit_time"] = ""
    out["exit_price"] = 0.0
    out["hold_hours"] = 0.0
    return out


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    scan_time = utc_now_text()

    result_path = args.out_dir / "latest_scan_result.json"
    ledger_path = args.out_dir / "signal_ledger.csv"
    log_path = args.out_dir / "live_scan_log.csv"

    print(f"[INFO] condition_id={CONDITION_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print("[INFO] loading CSVs")

    frames = load_research_csvs(args.csv_dir)
    write_df_csv(build_data_coverage(frames), args.out_dir / "data_coverage.csv")

    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")

    latest_close_time = latest_m15_close_time(m15, policy=args.latest_confirmed_policy)
    if latest_close_time is None:
        result = {
            "scan_time_utc": scan_time,
            "condition_id": CONDITION_ID,
            "signal_found": False,
            "duplicate": False,
            "reason": "NO_M15_ROWS",
        }
        write_json(result_path, result)
        append_csv_row(log_path, {**result, "csv_dir": str(args.csv_dir), "latest_m15_close_time": "", "candidate_count": 0, "latest_candidate_entry_time": "", "signal_key": ""}, LOG_COLUMNS)
        print("[INFO] no M15 rows")
        return 0

    print(f"[INFO] latest_m15_close_time={latest_close_time}")
    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    m15_base = build_m15_trigger_base_for_lookback(
        m15,
        breakout_lookback=int(args.breakout_lookback),
        sl_lookback_m15=int(args.sl_lookback_m15),
    )

    pending = build_trade_candidates_grid(
        h1_events=h1_events,
        h4_env=h4_env,
        m15_base=m15_base,
        breakout_lookback=int(args.breakout_lookback),
        sl_mode="h1_pivot",
        args=args,
    )
    write_df_csv(pending, args.out_dir / "latest_pending_candidates.csv")

    if pending.empty:
        latest_candidate_entry_time = ""
        latest_rows = pd.DataFrame()
    else:
        pending["entry_time"] = pd.to_datetime(pending["entry_time"], errors="coerce")
        latest_candidate_entry_time = str(pending["entry_time"].max())
        latest_rows = pending[pending["entry_time"] == latest_close_time].copy()

    if latest_rows.empty:
        result = {
            "scan_time_utc": scan_time,
            "condition_id": CONDITION_ID,
            "signal_found": False,
            "duplicate": False,
            "reason": "NO_SIGNAL_ON_LATEST_CONFIRMED_M15",
            "latest_m15_close_time": str(latest_close_time),
            "candidate_count": int(len(pending)),
            "latest_candidate_entry_time": latest_candidate_entry_time,
        }
        write_json(result_path, result)
        append_csv_row(log_path, {**result, "csv_dir": str(args.csv_dir), "signal_key": ""}, LOG_COLUMNS)
        print("[INFO] no signal on latest confirmed M15")
        return 0

    signal_row = latest_rows.sort_values("entry_time", kind="mergesort").iloc[-1]
    signal_row = normalize_live_row(signal_row, max_hold_hours=int(args.max_hold_hours))
    signal_key = build_signal_key(signal_row)

    ledger = read_ledger(ledger_path)
    duplicate = signal_key in set(ledger["signal_key"].astype(str)) if not ledger.empty else False
    if duplicate:
        result = {
            "scan_time_utc": scan_time,
            "condition_id": CONDITION_ID,
            "signal_found": True,
            "duplicate": True,
            "reason": "DUPLICATE_SIGNAL_KEY",
            "latest_m15_close_time": str(latest_close_time),
            "candidate_count": int(len(pending)),
            "latest_candidate_entry_time": latest_candidate_entry_time,
            "signal_key": signal_key,
        }
        write_json(result_path, result)
        append_csv_row(log_path, {**result, "csv_dir": str(args.csv_dir)}, LOG_COLUMNS)
        print(f"[INFO] duplicate signal: {signal_key}")
        return 0

    payload = build_signal_payload(signal_row)
    intent = build_order_intent(signal_row, risk_mode=args.risk_mode, dry_run=True)
    text = notification_text(payload)

    write_json(args.out_dir / "latest_signal_payload.json", payload)
    write_json(args.out_dir / "order_intent_dry_run.json", intent)
    write_text(args.out_dir / "notification_preview_latest.txt", text + "\n")

    ledger_row = {
        "created_at_utc": scan_time,
        "signal_key": signal_key,
        "condition_id": CONDITION_ID,
        "symbol": str(signal_row.get("symbol", "GOLD")),
        "direction": str(signal_row.get("direction", "BUY")),
        "entry_time": str(signal_row.get("entry_time", "")),
        "h1_event_id": str(signal_row.get("h1_event_id", "")),
        "h1_pivot_confirm_time": str(signal_row.get("h1_pivot_confirm_time", "")),
        "m15_close_time": str(signal_row.get("m15_close_time", "")),
        "entry_price_reference": signal_row.get("entry_price", ""),
        "sl_price": signal_row.get("sl_price", ""),
        "tp_price": signal_row.get("tp_price", ""),
        "rr": signal_row.get("rr", ""),
        "max_hold_hours": int(args.max_hold_hours),
        "status": "DRY_RUN_SIGNAL_CREATED",
    }
    append_csv_row(ledger_path, ledger_row, LEDGER_COLUMNS)

    result = {
        "scan_time_utc": scan_time,
        "condition_id": CONDITION_ID,
        "signal_found": True,
        "duplicate": False,
        "reason": "NEW_DRY_RUN_SIGNAL_CREATED",
        "latest_m15_close_time": str(latest_close_time),
        "candidate_count": int(len(pending)),
        "latest_candidate_entry_time": latest_candidate_entry_time,
        "signal_key": signal_key,
        "outputs": {
            "latest_signal_payload": str(args.out_dir / "latest_signal_payload.json"),
            "order_intent_dry_run": str(args.out_dir / "order_intent_dry_run.json"),
            "notification_preview_latest": str(args.out_dir / "notification_preview_latest.txt"),
            "signal_ledger": str(ledger_path),
        },
    }
    write_json(result_path, result)
    append_csv_row(log_path, {**result, "csv_dir": str(args.csv_dir)}, LOG_COLUMNS)

    print("[INFO] new dry-run signal created")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
