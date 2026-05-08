#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze hold time for the current best GOLD C_ENV RR2 setup.

Research-only script. It reads copied research CSV snapshots and writes only
research outputs. It does not touch Mochipoyo live/demo/autotrade files.

Fixed best setup under review:
    GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT_12H_BO8_SL_H1_PIVOT

Rule:
    H4 C_ENV:
        Latest confirmed H4 candle at M15 signal close time:
            ema20 > ema50 and close > ema50

    H1:
        Newly confirmed H1 regular bullish divergence and loose exhaustion:
            close < ema50 OR ema20 < ema50

    M15:
        First M15 break trigger within 12h after H1 confirmation.
        close > high.shift(1).rolling(8).max()
        close > ema20
        MACD(6,13,4) > signal
        macd_hist > previous macd_hist

    Entry:
        M15 close.

    SL:
        H1 regular bullish pivot low - M15 ATR14 * 0.05.

    TP:
        RR2.0.

    Outcome:
        M5 first-touch without timeout. If TP and SL touch in the same M5 bar,
        SL wins by default.

Hold-time analysis:
    Buckets by time to TP/SL:
        <=24h
        24-48h
        48-72h
        72-120h
        >120h

Example:
    python scripts\research_gold_c_env_rr2_best_hold_time_analysis.py ^
      --csv-dir data\research_csv_snapshots\gold_cb_20260508_01 ^
      --out-dir data\research_results\gold_c_env_rr2_best_hold_time_analysis
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_c_env_rr2_sl_breakout_grid_no_timeout import (  # noqa: E402
    build_m15_trigger_base_for_lookback,
    build_trade_candidates_grid,
)
from scripts.research_gold_c_env_rr2_entry_window_no_timeout import (  # noqa: E402
    EVALUATED_OUTCOMES,
    evaluate_trades_no_timeout,
)
from scripts.research_gold_c_strict_h1_regular_bullish_m15_break import (  # noqa: E402
    add_indicators,
    build_data_coverage,
    build_h1_events,
    load_research_csvs,
    max_drawdown_r,
    profit_factor,
    write_csv,
)
from scripts.research_gold_h4_permission_modes_h1_regular_bullish_m15_break import (  # noqa: E402
    prepare_h4_env_frame,
)

CONDITION_ID = "GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_NOWAIT_12H_BO8_SL_H1_PIVOT"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze hold time for best C_ENV RR2 setup.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/research_results/gold_c_env_rr2_best_hold_time_analysis"),
    )
    parser.add_argument("--pivot-left", type=int, default=2)
    parser.add_argument("--pivot-right", type=int, default=2)
    parser.add_argument("--entry-window-hours", type=float, default=12.0)
    parser.add_argument("--breakout-lookback", type=int, default=8)
    parser.add_argument("--sl-lookback-m15", type=int, default=12)
    parser.add_argument("--sl-atr-buffer-mult", type=float, default=0.05)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    return parser.parse_args()


def hold_bucket(hold_hours: float) -> str:
    if pd.isna(hold_hours):
        return "UNKNOWN"
    if hold_hours <= 24:
        return "<=24h"
    if hold_hours <= 48:
        return "24-48h"
    if hold_hours <= 72:
        return "48-72h"
    if hold_hours <= 120:
        return "72-120h"
    return ">120h"


def summarize_overall(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame(
            [
                {
                    "condition_id": CONDITION_ID,
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": np.nan,
                    "total_r": 0.0,
                    "avg_r": np.nan,
                    "pf": np.nan,
                    "max_dd_r": 0.0,
                    "avg_hold_hours": np.nan,
                    "median_hold_hours": np.nan,
                    "max_hold_hours": np.nan,
                }
            ]
        )
    r = pd.to_numeric(trades_eval["realized_r"], errors="coerce")
    hold_hours = pd.to_numeric(trades_eval["hold_hours"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "condition_id": CONDITION_ID,
                "trades": int(len(trades_eval)),
                "wins": int(trades_eval["outcome"].eq("WIN").sum()),
                "losses": int(trades_eval["outcome"].eq("LOSS").sum()),
                "win_rate": float(trades_eval["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "avg_hold_hours": float(hold_hours.mean()),
                "median_hold_hours": float(hold_hours.median()),
                "max_hold_hours": float(hold_hours.max()),
                "first_entry_time": trades_eval["entry_time"].min(),
                "last_entry_time": trades_eval["entry_time"].max(),
                "months_with_trades": int(trades_eval["entry_month"].nunique()),
            }
        ]
    )


def summarize_hold_buckets(trades_eval: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "condition_id",
        "hold_bucket",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "avg_hold_hours",
        "max_hold_hours",
    ]
    if trades_eval.empty:
        return pd.DataFrame(columns=cols)
    rows: list[dict[str, object]] = []
    for bucket, group in trades_eval.groupby("hold_bucket", dropna=False):
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        hold_hours = pd.to_numeric(group["hold_hours"], errors="coerce")
        rows.append(
            {
                "condition_id": CONDITION_ID,
                "hold_bucket": bucket,
                "trades": int(len(group)),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "win_rate": float(group["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "avg_hold_hours": float(hold_hours.mean()),
                "max_hold_hours": float(hold_hours.max()),
            }
        )
    order = {"<=24h": 0, "24-48h": 1, "48-72h": 2, "72-120h": 3, ">120h": 4, "UNKNOWN": 5}
    out = pd.DataFrame(rows)[cols]
    out["_order"] = out["hold_bucket"].map(order).fillna(999)
    return out.sort_values("_order", kind="mergesort").drop(columns=["_order"]).reset_index(drop=True)


def summarize_monthly(trades_eval: pd.DataFrame) -> pd.DataFrame:
    if trades_eval.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for month, group in trades_eval.groupby("entry_month", dropna=False):
        r = pd.to_numeric(group["realized_r"], errors="coerce")
        hold_hours = pd.to_numeric(group["hold_hours"], errors="coerce")
        rows.append(
            {
                "condition_id": CONDITION_ID,
                "entry_month": str(month),
                "trades": int(len(group)),
                "wins": int(group["outcome"].eq("WIN").sum()),
                "losses": int(group["outcome"].eq("LOSS").sum()),
                "win_rate": float(group["outcome"].eq("WIN").mean()),
                "total_r": float(r.sum()),
                "avg_r": float(r.mean()),
                "pf": profit_factor(r),
                "max_dd_r": max_drawdown_r(r),
                "avg_hold_hours": float(hold_hours.mean()),
                "max_hold_hours": float(hold_hours.max()),
            }
        )
    return pd.DataFrame(rows).sort_values("entry_month", kind="mergesort").reset_index(drop=True)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] research-only best C_ENV RR2 hold-time analysis")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_research_csvs(args.csv_dir)
    coverage = build_data_coverage(frames)
    coverage["condition_id"] = CONDITION_ID
    write_csv(coverage, args.out_dir / "data_coverage.csv")

    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m5 = frames["M5"].copy().sort_values("time", kind="mergesort").reset_index(drop=True)

    h1_events = build_h1_events(h1, args)
    h4_env = prepare_h4_env_frame(h4)
    m15_base = build_m15_trigger_base_for_lookback(
        m15,
        breakout_lookback=int(args.breakout_lookback),
        sl_lookback_m15=int(args.sl_lookback_m15),
    )

    write_csv(h1_events, args.out_dir / "context_h1_regular_bullish_events.csv")
    write_csv(h4_env, args.out_dir / "context_h4_env_rows.csv")
    write_csv(m15_base, args.out_dir / "m15_trigger_base_bo8.csv")

    pending = build_trade_candidates_grid(
        h1_events=h1_events,
        h4_env=h4_env,
        m15_base=m15_base,
        breakout_lookback=int(args.breakout_lookback),
        sl_mode="h1_pivot",
        args=args,
    )
    evaluated = evaluate_trades_no_timeout(pending, m5, args) if not pending.empty else pd.DataFrame()
    if not evaluated.empty:
        evaluated["condition_id"] = CONDITION_ID
        evaluated["hold_hours"] = pd.to_numeric(evaluated["hold_minutes"], errors="coerce") / 60.0
        evaluated["hold_bucket"] = evaluated["hold_hours"].map(hold_bucket)
    trades_eval = evaluated[evaluated["outcome"].isin(EVALUATED_OUTCOMES)].copy() if not evaluated.empty else pd.DataFrame()
    trades_no_m5 = evaluated[evaluated["outcome"].eq("NO_M5_PATH")].copy() if not evaluated.empty else pd.DataFrame()

    write_csv(pending, args.out_dir / "trades_pending.csv")
    write_csv(evaluated, args.out_dir / "trades_all_candidates.csv")
    write_csv(trades_eval, args.out_dir / "trades_evaluated_only.csv")
    write_csv(trades_no_m5, args.out_dir / "trades_no_m5_path.csv")
    write_csv(summarize_overall(trades_eval), args.out_dir / "summary_evaluated_only.csv")
    write_csv(summarize_hold_buckets(trades_eval), args.out_dir / "summary_hold_buckets.csv")
    write_csv(summarize_monthly(trades_eval), args.out_dir / "monthly_evaluated_only.csv")

    print("[INFO] completed")
    print(f"[INFO] all_candidates={len(evaluated)} evaluated={len(trades_eval)} no_m5_path={len(trades_no_m5)}")
    print(summarize_overall(trades_eval).to_string(index=False))
    print("[INFO] hold buckets")
    print(summarize_hold_buckets(trades_eval).to_string(index=False))
    print(f"[INFO] wrote outputs to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
