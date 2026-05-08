#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find historical replay candidates for GOLD bearish A/B classifier.

This helper lists historical M15 close_time values that can be replayed with:

    scripts/run_gold_h1h4_bear_ab_historical_replay_simple.py

It is research-only and does not write ledgers, notifications, order intents, or
Mochipoyo/autotrade files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import (
    CONDITION_FAMILY_ID,
    add_indicators,
    attach_context,
    build_signal_candidates,
    load_frames,
    write_csv,
)
from scripts.run_gold_h1h4_bear_ab_live_scan_once import compute_live_ab_flags


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Find GOLD bearish A/B historical replay candidates.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_h1h4_bear_ab_replay_candidates"))
    p.add_argument("--rank", choices=["CORE_AB_CONFIRM", "B_ONLY_SAFE", "A_ONLY_OBSERVE", "ALL"], default="B_ONLY_SAFE")
    p.add_argument("--start", type=str, default="")
    p.add_argument("--end", type=str, default="")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--prefer-with-backtest-outcome", action="store_true")
    p.add_argument("--sl-usd", type=float, default=10.0)
    p.add_argument("--tp-usd", type=float, default=20.0)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=float, default=12.0)
    p.add_argument("--cooldown-bars-m15", type=int, default=8)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--base-lot", type=float, default=0.10)
    p.add_argument("--core-lot-multiplier", type=float, default=2.0)
    p.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    p.add_argument("--max-lot-per-trade", type=float, default=99.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_frames(args.csv_dir)
    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    ctx = attach_context(m15, h1, h4, d1)

    flags = compute_live_ab_flags(ctx)
    candidates = flags[flags["rank"] != "NO_SIGNAL"].copy()
    candidates["as_of_m15_close_time"] = pd.to_datetime(candidates["close_time"], errors="coerce")
    candidates["signal_bar_time"] = pd.to_datetime(candidates["time"], errors="coerce")

    if args.rank != "ALL":
        candidates = candidates[candidates["rank"].eq(args.rank)].copy()
    if args.start:
        candidates = candidates[candidates["as_of_m15_close_time"] >= pd.Timestamp(args.start)].copy()
    if args.end:
        candidates = candidates[candidates["as_of_m15_close_time"] <= pd.Timestamp(args.end)].copy()

    # Backtest-style rows are useful because they carry next-M15-open entry references.
    bt = build_signal_candidates(ctx, args)
    if not bt.empty:
        bt_key = bt[["m15_close_time", "entry_time", "entry_price", "sl_price", "tp_price", "rank", "condition_id"]].copy()
        bt_key["as_of_m15_close_time"] = pd.to_datetime(bt_key["m15_close_time"], errors="coerce")
        bt_key = bt_key.rename(columns={
            "entry_time": "backtest_entry_time",
            "entry_price": "backtest_entry_price",
            "sl_price": "backtest_sl_price",
            "tp_price": "backtest_tp_price",
            "rank": "backtest_rank",
            "condition_id": "backtest_condition_id",
        })
        candidates = candidates.merge(
            bt_key.drop(columns=["m15_close_time"]),
            on="as_of_m15_close_time",
            how="left",
        )

    cols = [
        "rank",
        "condition_id",
        "signal_bar_time",
        "as_of_m15_close_time",
        "a_pass",
        "b_pass",
        "trade_enabled",
        "close",
        "low",
        "high",
        "close_pos",
        "range_atr_ratio",
        "macd_hist",
        "macd_hist_delta",
        "h1_close_time",
        "h1_close",
        "h1_ema20",
        "h1_ema50",
        "h1_dist_e20_atr_sell",
        "h4_close_time",
        "h4_close",
        "h4_ema20",
        "h4_ema50",
        "d1_close_time",
        "d1_close",
        "d1_ema20",
        "backtest_entry_time",
        "backtest_entry_price",
        "backtest_sl_price",
        "backtest_tp_price",
    ]
    for col in cols:
        if col not in candidates.columns:
            candidates[col] = pd.NA
    candidates = candidates[cols].sort_values("as_of_m15_close_time", kind="mergesort").reset_index(drop=True)

    all_path = args.out_dir / "replay_candidates_all.csv"
    write_csv(candidates, all_path)
    head = candidates.head(max(args.limit, 0)).copy()
    write_csv(head, args.out_dir / "replay_candidates_head.csv")

    print(f"[INFO] candidates={len(candidates)} rank={args.rank}")
    print(f"[INFO] all_csv={all_path}")
    if head.empty:
        print("[INFO] no candidates found")
        return 0

    show_cols = ["rank", "signal_bar_time", "as_of_m15_close_time", "backtest_entry_price", "backtest_sl_price", "backtest_tp_price"]
    print(head[show_cols].to_string(index=False))
    print("\n[INFO] Replay command example:")
    first_time = head.iloc[0]["as_of_m15_close_time"]
    print(
        'python scripts\\run_gold_h1h4_bear_ab_historical_replay_simple.py '
        f'--csv-dir "{args.csv_dir}" '
        '--out-dir data\\research_results\\gold_h1h4_bear_ab_historical_replay_simple_bonly '
        f'--as-of-m15-close-time "{first_time}" --reset-out-dir'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
