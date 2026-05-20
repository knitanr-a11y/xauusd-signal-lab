#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Backtest BTC strict-5 variants with AI-derived numeric filters.

This is a deterministic backtest comparison script.  It does NOT call AI.
It does NOT call MT5, Discord, or order_send.

Purpose:
- Take numeric-condition candidates found by
  run_btc_strict_5_ai_tag_numeric_condition_diagnostics.py.
- Apply them to the normal BTC strict-5 backtest path.
- Compare baseline vs filtered variants using the real backtest detector/context,
  not the AI-review snapshot CSV.

Important:
- These are research variants only.
- Do not push any filter into live trading until this script, monthly stats,
  and nearby-threshold stability are reviewed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_btc_strict_5_backtest_from_csv import (  # noqa: E402
    DEFAULT_MQL5_FILES_DIR,
    DEFAULT_OUT_DIR,
    add_indicators,
    build_monthly,
    build_summary,
    detect_signals,
    evaluate_signals,
    get_signal_specs,
    join_confirmed_context,
    read_ohlc_csv,
    validate_signal_specs,
    windows_long_path,
    write_csv,
    write_json,
)

SCHEMA_VERSION = "btc_strict_5_ai_numeric_filter_variant_backtest_v1"
DEFAULT_VARIANT_OUT_DIR = Path("data/research_results/btc_strict_5_ai_numeric_filter_variants")
BUY_CCI_ID = "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0"
BUY_RSI40_ID = "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0"
SELL_DONCH32_ID = "BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06_TP2500_SL750_H4H_CD0"


@dataclass(frozen=True)
class NumericFilter:
    filter_id: str
    strategy_id: str
    feature_name: str
    op: Literal["<=", ">="]
    threshold: float
    source_tag: str
    source_grade: str
    notes: str


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def write_text(path: str | Path, text: str) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def h4_close_vs_ema(ctx_row: pd.Series, ema_col: str) -> float:
    close = pd.to_numeric(ctx_row.get("h4_close"), errors="coerce")
    ema = pd.to_numeric(ctx_row.get(ema_col), errors="coerce")
    atr = pd.to_numeric(ctx_row.get("h4_atr14"), errors="coerce")
    if pd.isna(close) or pd.isna(ema) or pd.isna(atr) or abs(float(atr)) <= 1e-12:
        return np.nan
    return (float(close) - float(ema)) / abs(float(atr))


def m15_feature(ctx_row: pd.Series, feature_name: str) -> float:
    value = pd.to_numeric(ctx_row.get(feature_name), errors="coerce")
    return float(value) if not pd.isna(value) else np.nan


def compute_filter_feature(ctx_row: pd.Series, feature_name: str) -> float:
    if feature_name == "h4_close_vs_ema20_atr":
        return h4_close_vs_ema(ctx_row, "h4_ema20")
    if feature_name == "h4_close_vs_ema50_atr":
        return h4_close_vs_ema(ctx_row, "h4_ema50")
    if feature_name == "m15_signal_candle_close_pos":
        return m15_feature(ctx_row, "trigger_close_pos")
    if feature_name == "m15_signal_candle_range_atr_ratio":
        return m15_feature(ctx_row, "range_atr14")
    if feature_name == "m15_signal_candle_body_ratio":
        return m15_feature(ctx_row, "body_atr14")
    raise KeyError(f"unsupported filter feature: {feature_name}")


def filter_matches(value: float, op: str, threshold: float) -> bool:
    if np.isnan(value):
        return False
    if op == "<=":
        return float(value) <= float(threshold)
    if op == ">=":
        return float(value) >= float(threshold)
    raise ValueError(f"unsupported op: {op}")


def variant_filters(variant: str) -> list[NumericFilter]:
    if variant == "baseline":
        return []
    if variant == "buy_h4_context_conservative_v1":
        return [
            NumericFilter(
                filter_id="BUY_CCI_H4_EMA50_ATR_LE_NEG0232",
                strategy_id=BUY_CCI_ID,
                feature_name="h4_close_vs_ema50_atr",
                op="<=",
                threshold=-0.2321258027,
                source_tag="against_h4_context",
                source_grade="A_NUMERIC_FILTER_CANDIDATE",
                notes="BUY CCI: exclude when confirmed H4 close is materially below EMA50.",
            ),
            NumericFilter(
                filter_id="BUY_RSI40_H4_EMA20_ATR_LE_0272",
                strategy_id=BUY_RSI40_ID,
                feature_name="h4_close_vs_ema20_atr",
                op="<=",
                threshold=0.2718471001,
                source_tag="against_h4_context",
                source_grade="A_NUMERIC_FILTER_CANDIDATE",
                notes="BUY RSI40 conservative: higher precision, smaller exclusion.",
            ),
        ]
    if variant == "buy_h4_context_balanced_v1":
        return [
            NumericFilter(
                filter_id="BUY_CCI_H4_EMA50_ATR_LE_NEG0232",
                strategy_id=BUY_CCI_ID,
                feature_name="h4_close_vs_ema50_atr",
                op="<=",
                threshold=-0.2321258027,
                source_tag="against_h4_context",
                source_grade="A_NUMERIC_FILTER_CANDIDATE",
                notes="BUY CCI: exclude when confirmed H4 close is materially below EMA50.",
            ),
            NumericFilter(
                filter_id="BUY_RSI40_H4_EMA20_ATR_LE_0398",
                strategy_id=BUY_RSI40_ID,
                feature_name="h4_close_vs_ema20_atr",
                op="<=",
                threshold=0.3978123838,
                source_tag="against_h4_context",
                source_grade="A_NUMERIC_FILTER_CANDIDATE",
                notes="BUY RSI40 balanced: larger exclusion, stronger deterministic improvement in diagnostic.",
            ),
        ]
    if variant == "buy_h4_context_plus_donch32_watch_v1":
        return [
            *variant_filters("buy_h4_context_balanced_v1"),
            NumericFilter(
                filter_id="SELL_DONCH32_CLOSE_POS_GE_08996_WATCH",
                strategy_id=SELL_DONCH32_ID,
                feature_name="m15_signal_candle_close_pos",
                op=">=",
                threshold=0.8995949691,
                source_tag="btc_large_wick_reversal",
                source_grade="D_WEAK_TAG_REPRODUCTION_BUT_DETERMINISTIC_IMPROVES",
                notes="WATCH only: AI tag reproduction weak, but deterministic exclusion improved PF/DD in diagnostic.",
            ),
        ]
    raise ValueError(f"unknown variant: {variant}")


def available_variants() -> list[str]:
    return [
        "baseline",
        "buy_h4_context_conservative_v1",
        "buy_h4_context_balanced_v1",
        "buy_h4_context_plus_donch32_watch_v1",
    ]


def apply_filters(signals: pd.DataFrame, ctx: pd.DataFrame, filters: list[NumericFilter]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if signals.empty or not filters:
        kept = signals.copy()
        kept["filter_variant_excluded"] = False
        kept["filter_variant_excluded_by"] = ""
        return kept, pd.DataFrame()
    ctx_by_index = {int(i): row for i, row in ctx.iterrows()}
    by_strategy: dict[str, list[NumericFilter]] = {}
    for f in filters:
        by_strategy.setdefault(f.strategy_id, []).append(f)
    kept_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    for _, sig in signals.iterrows():
        sig_dict = sig.to_dict()
        strategy_id = str(sig.get("strategy_id"))
        row_filters = by_strategy.get(strategy_id, [])
        excluded = False
        reasons: list[str] = []
        feature_values: dict[str, float] = {}
        ctx_row = ctx_by_index.get(int(sig.get("source_index")))
        if ctx_row is not None:
            for f in row_filters:
                value = compute_filter_feature(ctx_row, f.feature_name)
                feature_values[f.feature_name] = value
                if filter_matches(value, f.op, f.threshold):
                    excluded = True
                    reasons.append(f"{f.filter_id}:{f.feature_name} {f.op} {f.threshold} value={value}")
        sig_dict["filter_variant_excluded"] = bool(excluded)
        sig_dict["filter_variant_excluded_by"] = "; ".join(reasons)
        for name, value in feature_values.items():
            sig_dict[f"filter_feature_{name}"] = value
        if excluded:
            excluded_rows.append(sig_dict)
        else:
            kept_rows.append(sig_dict)
    kept = pd.DataFrame(kept_rows)
    excluded_df = pd.DataFrame(excluded_rows)
    if not kept.empty:
        kept = kept.sort_values(["entry_time", "strategy_id"]).reset_index(drop=True)
    if not excluded_df.empty:
        excluded_df = excluded_df.sort_values(["entry_time", "strategy_id"]).reset_index(drop=True)
    return kept, excluded_df


def summarize_exclusions(excluded_signals: pd.DataFrame, trades_all: pd.DataFrame, variant: str) -> pd.DataFrame:
    if excluded_signals.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    excluded_keys = set(excluded_signals["trade_id"].astype(str).tolist()) if "trade_id" in excluded_signals.columns else set()
    # Evaluate excluded trades from the baseline all-trades table so we know what was removed.
    removed_trades = trades_all[trades_all["trade_id"].astype(str).isin(excluded_keys)].copy() if not trades_all.empty else pd.DataFrame()
    for key, g in removed_trades.groupby(["strategy_id", "candidate_base", "direction"], dropna=False):
        strategy_id, candidate_base, direction = key
        r = pd.to_numeric(g["net_profit_r"], errors="coerce").dropna()
        rows.append({
            "variant": variant,
            "strategy_id": strategy_id,
            "candidate_base": candidate_base,
            "direction": direction,
            "excluded_trades": int(len(g)),
            "excluded_total_r": float(r.sum()) if len(r) else 0.0,
            "excluded_avg_r": float(r.mean()) if len(r) else 0.0,
            "excluded_win_rate": float((r > 0).mean()) if len(r) else 0.0,
            "excluded_trade_ids": "|".join(g["trade_id"].astype(str).tolist()),
        })
    return pd.DataFrame(rows)


def add_variant_cols(df: pd.DataFrame, variant: str) -> pd.DataFrame:
    out = df.copy()
    out.insert(0, "variant", variant)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest BTC strict-5 AI numeric filter variants.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--m5-file", default="btcusdsharp_m5.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_VARIANT_OUT_DIR)
    p.add_argument("--variants", default="all", help="Comma-separated variants or all.")
    return p.parse_args()


def choose_path(root: Path, explicit: str, filename: str) -> Path:
    return Path(explicit) if explicit else root / filename


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    variants = available_variants() if args.variants.strip().lower() == "all" else [v.strip() for v in args.variants.split(",") if v.strip()]
    unknown = [v for v in variants if v not in available_variants()]
    if unknown:
        raise SystemExit(f"unknown variants: {unknown}; available={available_variants()}")
    paths = {
        "m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file),
        "m5": choose_path(args.mql5_files_dir, args.m5_csv, args.m5_file),
        "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file),
        "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file),
    }
    print("BTC strict 5 AI numeric filter variant backtest")
    print("d1_csv=NOT_USED d1_used=false")
    for k, v in paths.items():
        print(f"{k}_csv={v}")
    m15 = add_indicators(read_ohlc_csv(paths["m15"]), include_donchian=True)
    m5 = read_ohlc_csv(paths["m5"])
    h1 = add_indicators(read_ohlc_csv(paths["h1"]))
    h4 = add_indicators(read_ohlc_csv(paths["h4"]))
    ctx = join_confirmed_context(m15, h1, h4)
    specs = get_signal_specs()
    all_signals = detect_signals(ctx, specs)
    baseline_trades_all = evaluate_signals(all_signals, m5)

    all_summary: list[pd.DataFrame] = []
    all_monthly: list[pd.DataFrame] = []
    all_removed: list[pd.DataFrame] = []
    variant_rows: list[dict[str, Any]] = []

    for variant in variants:
        filters = variant_filters(variant)
        kept_signals, excluded_signals = apply_filters(all_signals, ctx, filters)
        trades = evaluate_signals(kept_signals, m5)
        summary = add_variant_cols(build_summary(trades), variant)
        monthly = add_variant_cols(build_monthly(trades), variant)
        removed = summarize_exclusions(excluded_signals, baseline_trades_all, variant)
        if not summary.empty:
            all_summary.append(summary)
        if not monthly.empty:
            all_monthly.append(monthly)
        if not removed.empty:
            all_removed.append(removed)
        write_csv(trades.drop(columns=["spec"], errors="ignore"), args.out_dir / f"{variant}_trades.csv")
        write_csv(kept_signals.drop(columns=["spec"], errors="ignore"), args.out_dir / f"{variant}_kept_signals.csv")
        write_csv(excluded_signals.drop(columns=["spec"], errors="ignore"), args.out_dir / f"{variant}_excluded_signals.csv")
        variant_rows.append({
            "variant": variant,
            "filters": [f.__dict__ for f in filters],
            "signals_in": int(len(all_signals)),
            "signals_kept": int(len(kept_signals)),
            "signals_excluded": int(len(excluded_signals)),
            "trades": int(len(trades)),
            "strict_no_future_ng_rows": int((~trades["strict_no_future_ok"].fillna(False)).sum()) if not trades.empty else 0,
            "d1_used": False,
        })

    summary_all = pd.concat(all_summary, ignore_index=True) if all_summary else pd.DataFrame()
    monthly_all = pd.concat(all_monthly, ignore_index=True) if all_monthly else pd.DataFrame()
    removed_all = pd.concat(all_removed, ignore_index=True) if all_removed else pd.DataFrame()
    write_csv(summary_all, args.out_dir / "btc_strict_5_ai_numeric_filter_variant_summary.csv")
    write_csv(monthly_all, args.out_dir / "btc_strict_5_ai_numeric_filter_variant_monthly.csv")
    write_csv(removed_all, args.out_dir / "btc_strict_5_ai_numeric_filter_variant_removed_trades_summary.csv")
    write_json(args.out_dir / "btc_strict_5_ai_numeric_filter_variant_run_summary.json", {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "safety": {
            "ai_called": False,
            "mt5_calls": False,
            "order_send": False,
            "discord_send": False,
            "diagnostic_backtest_only": True,
        },
        "input_paths": {k: str(v) for k, v in paths.items()},
        "outputs": {
            "summary_csv": str(args.out_dir / "btc_strict_5_ai_numeric_filter_variant_summary.csv"),
            "monthly_csv": str(args.out_dir / "btc_strict_5_ai_numeric_filter_variant_monthly.csv"),
            "removed_trades_summary_csv": str(args.out_dir / "btc_strict_5_ai_numeric_filter_variant_removed_trades_summary.csv"),
        },
        "rows": {
            "m15": int(len(m15)),
            "m5": int(len(m5)),
            "h1": int(len(h1)),
            "h4": int(len(h4)),
            "baseline_signals": int(len(all_signals)),
            "baseline_trades": int(len(baseline_trades_all)),
            "summary_rows": int(len(summary_all)),
            "monthly_rows": int(len(monthly_all)),
            "removed_summary_rows": int(len(removed_all)),
        },
        "variants": variant_rows,
    })
    print(summary_all[["variant", "strategy_id", "trade_count", "win_rate", "total_r", "profit_factor", "max_drawdown_r", "max_losing_streak"]].to_string(index=False) if not summary_all.empty else "NO SUMMARY")
    print(f"out_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
