#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate reproducible commands for GOLD_MOCHIPOYO_RR12_REFINED_205.

This script does not run the pipeline. It writes a Windows .cmd file that reruns
all documented steps from raw MT5 CSVs into a clean output directory.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def q(s: str) -> str:
    return '"' + str(s).replace('"', '\\"') + '"'


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--m1-csv", required=True)
    p.add_argument("--m5-csv", required=True)
    p.add_argument("--m15-csv", required=True)
    p.add_argument("--h1-csv", required=True)
    p.add_argument("--h4-csv", required=True)
    p.add_argument("--d1-csv", required=True)
    p.add_argument("--out-dir", default="data/results/mochipoyo/reproduce_gold_mochipoyo_rr12_refined_205")
    p.add_argument("--cmd-file", default="data/results/mochipoyo/reproduce_gold_mochipoyo_rr12_refined_205/run_reproduce.cmd")
    args = p.parse_args()

    out = Path(args.out_dir)
    cmd_file = Path(args.cmd_file)
    cmd_file.parent.mkdir(parents=True, exist_ok=True)

    candidates = out / "regen_multi_tf_candidates.csv"
    events = out / "regen_events.csv"
    touch_events = out / "regen_events_touch_range.csv"
    backtest = out / "regen_backtest_rr12.csv"
    positive_prefix = out / "regen_positive"
    monthly_prefix = out / "regen_monthly_validated"
    refined_prefix = out / "regen_refined"
    portfolio_prefix = out / "regen_refined_portfolio"
    final_prefix = out / "regen_final_205"

    lines = [
        "@echo off",
        "setlocal enabledelayedexpansion",
        "echo Reproducing GOLD_MOCHIPOYO_RR12_REFINED_205",
        f"if not exist {q(out)} mkdir {q(out)}",
        "",
        "echo [1/9] scan candidates",
        "python scripts/scan_mochipoyo_multi_tf_candidates.py "
        f"--symbol GOLD --m1-csv {q(args.m1_csv)} --m5-csv {q(args.m5_csv)} --m15-csv {q(args.m15_csv)} "
        f"--h1-csv {q(args.h1_csv)} --h4-csv {q(args.h4_csv)} --d1-csv {q(args.d1_csv)} --output-csv {q(candidates)} || exit /b 1",
        "",
        "echo [2/9] filter events",
        f"python scripts/filter_mochipoyo_candidate_events.py --input-csv {q(candidates)} --output-csv {q(events)} || exit /b 1",
        "",
        "echo [3/9] filter touch range",
        f"python scripts/filter_mochipoyo_events_by_touch_range.py --events-csv {q(events)} --m1-csv {q(args.m1_csv)} --m5-csv {q(args.m5_csv)} --output-csv {q(touch_events)} || exit /b 1",
        "",
        "echo [4/9] backtest RR1.2",
        f"python scripts/backtest_mochipoyo_gold_events_first_touch.py --events-csv {q(touch_events)} --m1-csv {q(args.m1_csv)} --m5-csv {q(args.m5_csv)} --output-csv {q(backtest)} --rr 1.2 || exit /b 1",
        "",
        "echo [5/9] extract positive slices",
        f"python scripts/extract_mochipoyo_positive_slices.py --backtest-csv {q(backtest)} --output-prefix {q(positive_prefix)} || exit /b 1",
        "",
        "echo [6/9] validate monthly",
        f"python scripts/validate_mochipoyo_selected_monthly.py --selected-trades-csv {q(str(positive_prefix) + '_trades.csv')} --output-prefix {q(monthly_prefix)} || exit /b 1",
        "",
        "echo [7/9] refine filters",
        f"python scripts/refine_mochipoyo_gold_rr12_filters.py --backtest-csv {q(str(monthly_prefix) + '_passed_trades.csv')} --output-prefix {q(refined_prefix)} || exit /b 1",
        "",
        "echo [8/9] build refined portfolio",
        f"python scripts/build_mochipoyo_refined_portfolio.py --backtest-csv {q(str(monthly_prefix) + '_passed_trades.csv')} --leaderboard-csv {q(str(refined_prefix) + '_leaderboard.csv')} --output-prefix {q(portfolio_prefix)} || exit /b 1",
        "",
        "echo [9/9] exclude weak slice",
        f"python scripts/exclude_mochipoyo_portfolio_slices.py --portfolio-csv {q(str(portfolio_prefix) + '_portfolio.csv')} --output-prefix {q(final_prefix)} --exclude-slice {q('GOLD_H4_M15_DAYTRADE|A|SELL')} || exit /b 1",
        "",
        f"echo Final regenerated CSV: {str(final_prefix)}_portfolio.csv",
        "echo done",
    ]
    cmd_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("make_gold_mochipoyo_rr12_reproduce_commands")
    print(f"cmd_file: {cmd_file}")
    print(f"final_csv: {final_prefix}_portfolio.csv")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
