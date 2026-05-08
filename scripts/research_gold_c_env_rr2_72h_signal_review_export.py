#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export notification/review rows for the best GOLD C_ENV RR2 72h setup.

Research-only utility.

Input:
    data/research_results/gold_c_env_rr2_best_hold_horizon_compare/trades_evaluated_only_72h.csv

Output:
    signal_review_72h.csv

Purpose:
    Convert the detailed backtest/research trade CSV into a compact row format
    that can later be reused for notification text, manual chart review, and
    validation logs.

This script does not touch live CSVs, Mochipoyo state, ledgers, Discord, or
autotrade/order-intent files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

CONDITION_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H"

DEFAULT_RESULT_DIR = Path("data/research_results/gold_c_env_rr2_best_hold_horizon_compare")
DEFAULT_INPUT = DEFAULT_RESULT_DIR / "trades_evaluated_only_72h.csv"
DEFAULT_OUTPUT = DEFAULT_RESULT_DIR / "signal_review_72h.csv"

REVIEW_COLUMNS = [
    "condition_id",
    "symbol",
    "direction",
    "entry_time",
    "entry_price",
    "sl_price",
    "tp_price",
    "risk_price",
    "rr",
    "max_hold_hours",
    "exit_rule",
    "h4_env_close_time",
    "h4_env_close",
    "h4_env_ema20",
    "h4_env_ema50",
    "h1_event_id",
    "h1_pivot_time",
    "h1_pivot_confirm_time",
    "h1_pivot_low",
    "h1_prev_pivot_low",
    "h1_pivot_macd",
    "h1_prev_pivot_macd",
    "h1_close_at_confirm",
    "h1_ema20_at_confirm",
    "h1_ema50_at_confirm",
    "m15_time",
    "m15_close_time",
    "m15_close",
    "m15_ema20",
    "m15_atr14",
    "m15_macd",
    "m15_macd_signal",
    "m15_macd_hist",
    "m15_rolling_high_prev",
    "outcome",
    "realized_r",
    "exit_time",
    "exit_price",
    "hold_hours",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export compact signal review CSV for best 72h setup.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str], *, path: Path) -> None:
    missing = [col for col in columns if col not in df.columns]
    # condition_id/max_hold_hours/exit_rule may be added by this script.
    allowed_to_add = {"condition_id", "max_hold_hours", "exit_rule"}
    blocking = [col for col in missing if col not in allowed_to_add]
    if blocking:
        raise RuntimeError(f"Missing required columns in {path}: {blocking}")


def main() -> int:
    args = parse_args()
    if not args.input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {args.input_csv}")

    df = pd.read_csv(args.input_csv, encoding="utf-8-sig")
    if df.empty:
        out = pd.DataFrame(columns=REVIEW_COLUMNS)
    else:
        require_columns(df, REVIEW_COLUMNS, path=args.input_csv)
        df = df.copy()
        df["condition_id"] = CONDITION_ID
        df["max_hold_hours"] = 72
        df["exit_rule"] = "TP/SL first-touch; if unresolved, exit at last M5 close before 72h"

        if "hold_hours" not in df.columns and "hold_minutes" in df.columns:
            df["hold_hours"] = pd.to_numeric(df["hold_minutes"], errors="coerce") / 60.0

        out = df[[col for col in REVIEW_COLUMNS if col in df.columns]].copy()
        out = out.sort_values("entry_time", kind="mergesort").reset_index(drop=True)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    print(f"[INFO] input={args.input_csv}")
    print(f"[INFO] output={args.output_csv}")
    print(f"[INFO] rows={len(out)}")
    if not out.empty:
        print(out[["entry_time", "entry_price", "sl_price", "tp_price", "outcome", "realized_r", "hold_hours"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
