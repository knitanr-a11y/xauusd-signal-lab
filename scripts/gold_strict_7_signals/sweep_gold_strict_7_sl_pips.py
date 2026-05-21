#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Sweep deeper SL settings for GOLD strict-7 without changing live specs.

Research-only script.

What this does:
- Keeps entry conditions, TP, cooldown, sessions and no-future context exactly as current strict-7 specs.
- Changes only sl_pips for one strategy at a time.
- Re-evaluates outcomes on M1 first-touch path using the same conservative in-bar priority as the main backtest.
- Writes comparison CSVs for PF / win-rate / total R / monthly robustness.

No Discord send.
No MT5 call.
No order_send.
No OpenAI call.
No runtime ledger mutation.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gold_strict_7_signal_specs import (  # noqa: E402
    DEFAULT_BROKER_SYMBOL,
    GOLD_PIP_SIZE,
    GoldStrictSignalSpec,
    get_signal_specs,
    validate_signal_specs,
)
from run_gold_strict_7_backtest_from_csv import (  # noqa: E402
    DEFAULT_MQL5_FILES_DIR,
    add_indicators,
    attach_strict_context,
    build_monthly,
    build_summary,
    clean_float,
    detect_spec_candidates,
    evaluated_only,
    evaluate_candidates,
    profit_factor,
    read_ohlc_csv,
    resolve_csv_paths,
    summarize_group,
    time_text,
    windows_long_path,
    write_csv,
    write_json,
)

SCHEMA_VERSION = "gold_strict_7_sl_depth_sweep_v1"
DEFAULT_OUT_DIR = Path("data/research_results/gold_strict_7_sl_depth_sweep")

SUMMARY_COLUMNS = [
    "strategy_id",
    "candidate_family",
    "direction",
    "session",
    "baseline_sl_pips",
    "test_sl_pips",
    "sl_delta_pips",
    "sl_price_distance",
    "tp_pips",
    "rr",
    "is_baseline",
    "evaluated_trade_count",
    "win_count",
    "loss_count",
    "breakeven_count",
    "win_rate",
    "profit_factor",
    "total_r",
    "avg_r",
    "max_drawdown_r",
    "max_losing_streak",
    "avg_holding_minutes",
    "median_holding_minutes",
    "months_with_trades",
    "negative_month_count",
    "worst_month_total_r",
    "best_month_total_r",
    "monthly_pf_min",
    "monthly_pf_median",
    "loss_to_win_count",
    "loss_to_breakeven_count",
    "loss_to_timeout_or_other_count",
    "win_to_loss_count",
    "same_outcome_count",
    "changed_outcome_count",
    "baseline_total_r",
    "delta_total_r_vs_baseline",
    "baseline_profit_factor",
    "delta_pf_vs_baseline",
    "baseline_win_rate",
    "delta_win_rate_vs_baseline",
]


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def parse_float_list(text: str) -> list[float]:
    vals: list[float] = []
    for part in str(text).replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        vals.append(float(part))
    return sorted(set(vals))


def default_sl_grid_for_spec(spec: GoldStrictSignalSpec) -> list[float]:
    base = float(spec.sl_pips)
    if math.isclose(base, 7.5):
        return [7.5, 10.0, 12.5, 15.0, 20.0]
    if math.isclose(base, 10.0):
        return [10.0, 12.5, 15.0, 20.0, 25.0]
    if math.isclose(base, 37.5):
        return [37.5, 45.0, 50.0, 60.0]
    return [base, round(base * 1.25, 2), round(base * 1.5, 2), round(base * 2.0, 2)]


def build_sl_grid(specs: list[GoldStrictSignalSpec], args: argparse.Namespace) -> dict[str, list[float]]:
    grid: dict[str, list[float]] = {spec.strategy_id: default_sl_grid_for_spec(spec) for spec in specs}
    overrides = [x for x in args.override if x]
    for item in overrides:
        if "=" not in item:
            raise SystemExit(f"--override must be STRATEGY_ID=7.5,10,12.5 style; got: {item}")
        strategy_id, vals = item.split("=", 1)
        strategy_id = strategy_id.strip()
        if strategy_id not in grid:
            raise SystemExit(f"unknown strategy_id in --override: {strategy_id}")
        grid[strategy_id] = parse_float_list(vals)
    if args.only_strategy:
        allowed = set(args.only_strategy)
        unknown = sorted(allowed - set(grid.keys()))
        if unknown:
            raise SystemExit(f"unknown --only-strategy values: {unknown}")
        grid = {k: v for k, v in grid.items() if k in allowed}
    return grid


def load_frames(args: argparse.Namespace) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    paths = resolve_csv_paths(args)
    raw = {
        "M1": read_ohlc_csv(paths["M1"], tail_bars=args.tail_m1),
        "M5": read_ohlc_csv(paths["M5"], tail_bars=args.tail_m5),
        "H1": read_ohlc_csv(paths["H1"], tail_bars=args.tail_h1),
        "H4": read_ohlc_csv(paths["H4"], tail_bars=args.tail_h4),
        "D1": read_ohlc_csv(paths["D1"], tail_bars=args.tail_d1),
    }
    frames = {tf: add_indicators(df, tf) for tf, df in raw.items()}
    ctx = attach_strict_context(frames["M5"], frames["H1"], frames["H4"], frames["D1"])
    return frames, ctx


def monthly_robustness(monthly: pd.DataFrame) -> dict[str, Any]:
    if monthly.empty:
        return {
            "negative_month_count": 0,
            "worst_month_total_r": None,
            "best_month_total_r": None,
            "monthly_pf_min": None,
            "monthly_pf_median": None,
        }
    total_r = pd.to_numeric(monthly.get("total_r", pd.Series(dtype=float)), errors="coerce").dropna()
    pf = pd.to_numeric(monthly.get("profit_factor", pd.Series(dtype=float)), errors="coerce").replace([float("inf"), -float("inf")], pd.NA).dropna()
    return {
        "negative_month_count": int((total_r < 0).sum()) if not total_r.empty else 0,
        "worst_month_total_r": None if total_r.empty else float(total_r.min()),
        "best_month_total_r": None if total_r.empty else float(total_r.max()),
        "monthly_pf_min": None if pf.empty else float(pf.min()),
        "monthly_pf_median": None if pf.empty else float(pf.median()),
    }


def outcome_change_stats(base_trades: pd.DataFrame, test_trades: pd.DataFrame) -> dict[str, int]:
    if base_trades.empty or test_trades.empty:
        return {
            "loss_to_win_count": 0,
            "loss_to_breakeven_count": 0,
            "loss_to_timeout_or_other_count": 0,
            "win_to_loss_count": 0,
            "same_outcome_count": 0,
            "changed_outcome_count": 0,
        }
    left = base_trades[["trade_id", "outcome"]].rename(columns={"outcome": "baseline_outcome"})
    right = test_trades[["trade_id", "outcome"]].rename(columns={"outcome": "test_outcome"})
    joined = left.merge(right, on="trade_id", how="inner")
    b = joined["baseline_outcome"].astype(str).str.upper()
    t = joined["test_outcome"].astype(str).str.upper()
    return {
        "loss_to_win_count": int(((b == "LOSS") & (t == "WIN")).sum()),
        "loss_to_breakeven_count": int(((b == "LOSS") & (t == "BREAKEVEN")).sum()),
        "loss_to_timeout_or_other_count": int(((b == "LOSS") & (~t.isin(["LOSS", "WIN", "BREAKEVEN"]))).sum()),
        "win_to_loss_count": int(((b == "WIN") & (t == "LOSS")).sum()),
        "same_outcome_count": int((b == t).sum()),
        "changed_outcome_count": int((b != t).sum()),
    }


def first_summary_row(summary: pd.DataFrame) -> dict[str, Any]:
    if summary.empty:
        return {}
    return summary.iloc[0].to_dict()


def evaluate_variant(
    *,
    base_spec: GoldStrictSignalSpec,
    test_sl_pips: float,
    candidates: pd.DataFrame,
    m1: pd.DataFrame,
    broker_symbol: str,
    inbar_priority: str,
    m1_coverage_policy: str,
) -> tuple[GoldStrictSignalSpec, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    mod_spec = replace(base_spec, sl_pips=float(test_sl_pips))
    trades, dropped_before_m1, post_counts = evaluate_candidates(
        {mod_spec.strategy_id: candidates},
        [mod_spec],
        m1,
        broker_symbol=broker_symbol,
        inbar_priority=inbar_priority,
        m1_coverage_policy=m1_coverage_policy,
    )
    summary = build_summary(trades)
    monthly = build_monthly(trades)
    meta = {
        "dropped_before_first_m1": int(sum(dropped_before_m1.values())),
        "post_cooldown_signals_before_m1_filter": int(sum(post_counts.values())),
    }
    return mod_spec, trades, summary, monthly, meta


def metric_float(row: dict[str, Any], key: str) -> float | None:
    return clean_float(row.get(key), None)


def build_result_row(
    *,
    base_spec: GoldStrictSignalSpec,
    mod_spec: GoldStrictSignalSpec,
    summary: pd.DataFrame,
    monthly: pd.DataFrame,
    baseline_summary_row: dict[str, Any],
    baseline_trades: pd.DataFrame,
    test_trades: pd.DataFrame,
) -> dict[str, Any]:
    s = first_summary_row(summary)
    robust = monthly_robustness(monthly)
    changes = outcome_change_stats(evaluated_only(baseline_trades), evaluated_only(test_trades))
    total_r = metric_float(s, "total_r")
    pf = metric_float(s, "profit_factor")
    win_rate = metric_float(s, "win_rate")
    base_total_r = metric_float(baseline_summary_row, "total_r")
    base_pf = metric_float(baseline_summary_row, "profit_factor")
    base_wr = metric_float(baseline_summary_row, "win_rate")
    return {
        "strategy_id": mod_spec.strategy_id,
        "candidate_family": mod_spec.family,
        "direction": mod_spec.direction,
        "session": mod_spec.session,
        "baseline_sl_pips": float(base_spec.sl_pips),
        "test_sl_pips": float(mod_spec.sl_pips),
        "sl_delta_pips": float(mod_spec.sl_pips - base_spec.sl_pips),
        "sl_price_distance": float(mod_spec.sl_price_distance),
        "tp_pips": float(mod_spec.tp_pips),
        "rr": float(mod_spec.rr),
        "is_baseline": bool(math.isclose(float(base_spec.sl_pips), float(mod_spec.sl_pips))),
        "evaluated_trade_count": int(s.get("evaluated_trade_count", 0) or 0),
        "win_count": int(s.get("win_count", 0) or 0),
        "loss_count": int(s.get("loss_count", 0) or 0),
        "breakeven_count": int(s.get("breakeven_count", 0) or 0),
        "win_rate": win_rate,
        "profit_factor": pf,
        "total_r": total_r,
        "avg_r": metric_float(s, "avg_r"),
        "max_drawdown_r": metric_float(s, "max_drawdown_r"),
        "max_losing_streak": int(s.get("max_losing_streak", 0) or 0),
        "avg_holding_minutes": metric_float(s, "avg_holding_minutes"),
        "median_holding_minutes": metric_float(s, "median_holding_minutes"),
        "months_with_trades": int(s.get("months_with_trades", 0) or 0),
        **robust,
        **changes,
        "baseline_total_r": base_total_r,
        "delta_total_r_vs_baseline": None if total_r is None or base_total_r is None else float(total_r - base_total_r),
        "baseline_profit_factor": base_pf,
        "delta_pf_vs_baseline": None if pf is None or base_pf is None else float(pf - base_pf),
        "baseline_win_rate": base_wr,
        "delta_win_rate_vs_baseline": None if win_rate is None or base_wr is None else float(win_rate - base_wr),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sweep GOLD strict-7 SL pips depth by strategy.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--gold-m1-csv", default="")
    p.add_argument("--gold-m5-csv", default="")
    p.add_argument("--gold-h1-csv", default="")
    p.add_argument("--gold-h4-csv", default="")
    p.add_argument("--gold-d1-csv", default="")
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--m1-coverage-policy", choices=["drop", "keep_no_path"], default="drop")
    p.add_argument("--tail-m1", type=int, default=0)
    p.add_argument("--tail-m5", type=int, default=0)
    p.add_argument("--tail-h1", type=int, default=0)
    p.add_argument("--tail-h4", type=int, default=0)
    p.add_argument("--tail-d1", type=int, default=0)
    p.add_argument("--only-strategy", action="append", default=[], help="Limit sweep to one strategy_id. Can be repeated.")
    p.add_argument("--override", action="append", default=[], help="Override grid: STRATEGY_ID=7.5,10,12.5. Can be repeated.")
    p.add_argument("--write-trades", action="store_true", help="Write one combined trades CSV for all variants. Can be large.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    specs = get_signal_specs()
    grid = build_sl_grid(specs, args)
    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    mkdirp(out_dir)

    print("=" * 100, flush=True)
    print("GOLD strict 7 SL depth sweep", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"out_dir: {out_dir}", flush=True)
    print(f"inbar_priority: {args.inbar_priority}", flush=True)
    print(f"m1_coverage_policy: {args.m1_coverage_policy}", flush=True)
    print("Safety: research only. No Discord, no MT5, no order_send, no OpenAI.", flush=True)
    print("=" * 100, flush=True)

    frames, ctx = load_frames(args)
    m1 = frames["M1"]
    candidates_by_spec: dict[str, pd.DataFrame] = {}
    for spec in specs:
        if spec.strategy_id not in grid:
            continue
        cand = detect_spec_candidates(ctx, spec)
        candidates_by_spec[spec.strategy_id] = cand
        print(f"raw candidates {spec.strategy_id}: {len(cand)}", flush=True)

    result_rows: list[dict[str, Any]] = []
    monthly_rows: list[pd.DataFrame] = []
    all_variant_trades: list[pd.DataFrame] = []
    baseline_by_strategy: dict[str, tuple[pd.DataFrame, dict[str, Any]]] = {}

    for spec in specs:
        if spec.strategy_id not in grid:
            continue
        cand = candidates_by_spec.get(spec.strategy_id, pd.DataFrame())
        base_mod, base_trades, base_summary, base_monthly, _ = evaluate_variant(
            base_spec=spec,
            test_sl_pips=float(spec.sl_pips),
            candidates=cand,
            m1=m1,
            broker_symbol=str(args.broker_symbol),
            inbar_priority=str(args.inbar_priority),
            m1_coverage_policy=str(args.m1_coverage_policy),
        )
        baseline_by_strategy[spec.strategy_id] = (base_trades, first_summary_row(base_summary))
        for test_sl in grid[spec.strategy_id]:
            mod_spec, trades, summary, monthly, meta = evaluate_variant(
                base_spec=spec,
                test_sl_pips=float(test_sl),
                candidates=cand,
                m1=m1,
                broker_symbol=str(args.broker_symbol),
                inbar_priority=str(args.inbar_priority),
                m1_coverage_policy=str(args.m1_coverage_policy),
            )
            base_trades_for_strategy, base_summary_row = baseline_by_strategy[spec.strategy_id]
            row = build_result_row(
                base_spec=spec,
                mod_spec=mod_spec,
                summary=summary,
                monthly=monthly,
                baseline_summary_row=base_summary_row,
                baseline_trades=base_trades_for_strategy,
                test_trades=trades,
            )
            row.update(meta)
            result_rows.append(row)
            if not monthly.empty:
                tmp_monthly = monthly.copy()
                tmp_monthly.insert(4, "baseline_sl_pips", float(spec.sl_pips))
                tmp_monthly.insert(5, "test_sl_pips", float(mod_spec.sl_pips))
                tmp_monthly.insert(6, "rr", float(mod_spec.rr))
                monthly_rows.append(tmp_monthly)
            if args.write_trades and not trades.empty:
                tmp_trades = trades.copy()
                tmp_trades.insert(4, "baseline_sl_pips", float(spec.sl_pips))
                tmp_trades.insert(5, "test_sl_pips", float(mod_spec.sl_pips))
                all_variant_trades.append(tmp_trades)
            print(
                f"{spec.strategy_id} SL {spec.sl_pips:.1f}->{mod_spec.sl_pips:.1f} "
                f"trades={row['evaluated_trade_count']} WR={row['win_rate']} PF={row['profit_factor']} totalR={row['total_r']} deltaR={row['delta_total_r_vs_baseline']}",
                flush=True,
            )

    result = pd.DataFrame(result_rows, columns=SUMMARY_COLUMNS + ["dropped_before_first_m1", "post_cooldown_signals_before_m1_filter"])
    if not result.empty:
        result = result.sort_values(["strategy_id", "test_sl_pips"], kind="mergesort").reset_index(drop=True)
    monthly_all = pd.concat(monthly_rows, ignore_index=True, sort=False) if monthly_rows else pd.DataFrame()
    trades_all = pd.concat(all_variant_trades, ignore_index=True, sort=False) if all_variant_trades else pd.DataFrame()

    summary_csv = out_dir / "gold_strict_7_sl_depth_sweep_summary.csv"
    monthly_csv = out_dir / "gold_strict_7_sl_depth_sweep_monthly.csv"
    trades_csv = out_dir / "gold_strict_7_sl_depth_sweep_trades.csv"
    json_path = out_dir / "gold_strict_7_sl_depth_sweep_summary.json"
    write_csv(result, summary_csv)
    write_csv(monthly_all, monthly_csv)
    if args.write_trades:
        write_csv(trades_all, trades_csv)

    best_by_total_r = pd.DataFrame()
    best_by_pf = pd.DataFrame()
    if not result.empty:
        best_by_total_r = result.sort_values(["strategy_id", "total_r", "profit_factor"], ascending=[True, False, False], kind="mergesort").groupby("strategy_id", as_index=False).head(1)
        best_by_pf = result.sort_values(["strategy_id", "profit_factor", "total_r"], ascending=[True, False, False], kind="mergesort").groupby("strategy_id", as_index=False).head(1)
        write_csv(best_by_total_r, out_dir / "gold_strict_7_sl_depth_sweep_best_by_total_r.csv")
        write_csv(best_by_pf, out_dir / "gold_strict_7_sl_depth_sweep_best_by_pf.csv")

    summary_json = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "script": "scripts/gold_strict_7_signals/sweep_gold_strict_7_sl_pips.py",
        "grid": grid,
        "outputs": {
            "summary_csv": str(summary_csv),
            "monthly_csv": str(monthly_csv),
            "trades_csv": str(trades_csv) if args.write_trades else "NOT_WRITTEN_USE_--write-trades",
            "best_by_total_r_csv": str(out_dir / "gold_strict_7_sl_depth_sweep_best_by_total_r.csv"),
            "best_by_pf_csv": str(out_dir / "gold_strict_7_sl_depth_sweep_best_by_pf.csv"),
            "summary_json": str(json_path),
        },
        "rows": {
            "ctx_m5_rows": int(len(ctx)),
            "m1_rows": int(len(m1)),
            "summary_rows": int(len(result)),
            "monthly_rows": int(len(monthly_all)),
            "trades_rows": int(len(trades_all)) if args.write_trades else 0,
        },
        "no_future_contract": {
            "entry_conditions_changed": False,
            "tp_changed": False,
            "cooldown_changed": False,
            "only_sl_pips_changed": True,
            "higher_timeframe_rule": "H1/H4/D1 context_close_time <= M5 close_time",
            "inbar_priority": str(args.inbar_priority),
        },
        "safety": {"discord_send": False, "mt5_calls": False, "order_send": False, "openai_calls": False, "runtime_state_mutation": False},
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(json_path, summary_json)

    print("=" * 100, flush=True)
    print(json.dumps({
        "cycle_ok": True,
        "summary_csv": str(summary_csv),
        "monthly_csv": str(monthly_csv),
        "best_by_total_r": best_by_total_r[["strategy_id", "test_sl_pips", "rr", "evaluated_trade_count", "win_rate", "profit_factor", "total_r", "delta_total_r_vs_baseline"]].to_dict("records") if not best_by_total_r.empty else [],
        "best_by_pf": best_by_pf[["strategy_id", "test_sl_pips", "rr", "evaluated_trade_count", "win_rate", "profit_factor", "total_r", "delta_total_r_vs_baseline"]].to_dict("records") if not best_by_pf.empty else [],
    }, ensure_ascii=False, indent=2, default=str), flush=True)
    print("=" * 100, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
