#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare current B_ONLY_SAFE vs stricter H1-close-below-EMA20 variant.

This is research-only. It does not change live scan, ledgers, notifications,
order intents, Mochipoyo flow, or autotrade files.

Purpose
-------
Current B condition allows H1 close to be above EMA20 as long as:
    H1 close < EMA50
    H1 EMA20 < EMA50
    H1 dist_e20_atr_sell <= 1.60

This script compares that current B to a stricter B variant that additionally
requires:
    H1 close < H1 EMA20

The A condition remains unchanged. The final rank logic remains:
    CORE_AB_CONFIRM = A and B
    B_ONLY_SAFE     = B and not A
    A_ONLY_OBSERVE  = A and not B

Entries are next M15 open, matching the main research backtest.
Exits are SELL M1 first-touch with fixed SL/TP.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import (  # noqa: E402
    CONDITION_FAMILY_ID,
    CONDITION_ID_A_ONLY,
    CONDITION_ID_B_ONLY,
    CONDITION_ID_CORE,
    DIRECTION,
    SYMBOL,
    add_indicators,
    attach_context,
    build_data_coverage,
    evaluate_trades,
    load_frames,
    profit_factor,
    max_drawdown_r,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare current B_ONLY_SAFE vs stricter H1 close < EMA20 variant.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_h1h4_bear_ab_bonly_h1_strict_compare"))
    p.add_argument("--start", type=str, default="")
    p.add_argument("--end", type=str, default="")
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


def apply_common_cooldown(signals: pd.DataFrame, cooldown_bars_m15: int) -> pd.DataFrame:
    if signals.empty:
        return signals.copy()
    trade_signals = signals[signals["trade_enabled"]].copy().sort_values("entry_time", kind="mergesort")
    cooldown_minutes = int(cooldown_bars_m15) * 15
    accepted: list[dict[str, Any]] = []
    last_entry_time: pd.Timestamp | None = None
    for _, row in trade_signals.iterrows():
        et = pd.Timestamp(row["entry_time"])
        if last_entry_time is None or et >= last_entry_time + pd.to_timedelta(cooldown_minutes, unit="m"):
            accepted.append(row.to_dict())
            last_entry_time = et
    if not accepted:
        return pd.DataFrame(columns=signals.columns)
    return pd.DataFrame(accepted).sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def build_variant_signals(m15_ctx: pd.DataFrame, args: argparse.Namespace, *, variant: str) -> pd.DataFrame:
    if variant not in {"current_b", "strict_b_h1_close_below_ema20"}:
        raise ValueError(f"unknown variant: {variant}")

    out = m15_ctx.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["m15_prev_low16"] = out["low"].shift(1).rolling(16, min_periods=16).min()
    out["m15_prev_low6"] = out["low"].shift(1).rolling(6, min_periods=6).min()

    a_h1 = (
        (out["h1_close"] < out["h1_ema20"])
        & (out["h1_ema20"] < out["h1_ema50"])
        & (out["h1_ema20_slope3"] < 0)
        & (out["h1_dist_e20_atr_sell"] <= 1.60)
    )
    a_h4 = (out["h4_close"] < out["h4_ema20"]) & (out["h4_ema20"] < out["h4_ema50"])
    d1_bear = out["d1_close"] < out["d1_ema20"]
    a_m15 = (
        (out["low"] < out["m15_prev_low16"])
        & (out["close_pos"] <= 0.45)
        & (out["macd_hist_delta"] < 0)
        & (out["range_atr_ratio"] >= 0.90)
    )

    b_h1 = (
        (out["h1_close"] < out["h1_ema50"])
        & (out["h1_ema20"] < out["h1_ema50"])
        & (out["h1_dist_e20_atr_sell"] <= 1.60)
    )
    if variant == "strict_b_h1_close_below_ema20":
        b_h1 = b_h1 & (out["h1_close"] < out["h1_ema20"])

    b_h4 = out["h4_ema20"] < out["h4_ema50"]
    b_m15 = (
        (out["low"] < out["m15_prev_low6"])
        & (out["close_pos"] <= 0.50)
        & (out["macd_hist"] < 0)
        & (out["macd_hist_delta"] < 0)
    )

    out["a_pass"] = (a_h1 & a_h4 & d1_bear & a_m15).fillna(False)
    out["b_pass"] = (b_h1 & b_h4 & d1_bear & b_m15).fillna(False)
    out["rank"] = np.select(
        [out["a_pass"] & out["b_pass"], out["b_pass"] & ~out["a_pass"], out["a_pass"] & ~out["b_pass"]],
        ["CORE_AB_CONFIRM", "B_ONLY_SAFE", "A_ONLY_OBSERVE"],
        default="NO_SIGNAL",
    )
    out["trade_enabled"] = out["rank"].isin(["CORE_AB_CONFIRM", "B_ONLY_SAFE"])
    out["condition_id"] = np.select(
        [out["rank"].eq("CORE_AB_CONFIRM"), out["rank"].eq("B_ONLY_SAFE"), out["rank"].eq("A_ONLY_OBSERVE")],
        [CONDITION_ID_CORE, CONDITION_ID_B_ONLY, CONDITION_ID_A_ONLY],
        default="",
    )
    out["signal_group"] = out["rank"]
    raw = out[out["rank"] != "NO_SIGNAL"].copy()
    if raw.empty:
        return raw

    if args.start:
        raw = raw[pd.to_datetime(raw["close_time"], errors="coerce") >= pd.Timestamp(args.start)].copy()
    if args.end:
        raw = raw[pd.to_datetime(raw["close_time"], errors="coerce") <= pd.Timestamp(args.end)].copy()
    if raw.empty:
        return raw

    next_open = out[["time", "open"]].rename(columns={"time": "entry_time", "open": "entry_price"})
    raw["entry_time"] = raw["close_time"]
    raw = raw.merge(next_open, on="entry_time", how="left")
    raw = raw[raw["entry_price"].notna()].copy()

    raw["variant"] = variant
    raw["symbol"] = SYMBOL
    raw["direction"] = DIRECTION
    raw["signal_time"] = raw["time"]
    raw["m15_close_time"] = raw["close_time"]
    raw["sl_price"] = raw["entry_price"] + float(args.sl_usd)
    raw["tp_price"] = raw["entry_price"] - float(args.tp_usd)
    raw["risk_price"] = float(args.sl_usd)
    raw["reward_price"] = float(args.tp_usd)
    raw["rr"] = float(args.rr)
    raw["max_hold_hours"] = float(args.horizon_hours)
    raw["base_lot"] = float(args.base_lot)
    raw["lot_multiplier"] = np.select(
        [raw["rank"].eq("CORE_AB_CONFIRM"), raw["rank"].eq("B_ONLY_SAFE")],
        [float(args.core_lot_multiplier), float(args.standard_lot_multiplier)],
        default=0.0,
    )
    raw["effective_lot"] = np.minimum(raw["base_lot"] * raw["lot_multiplier"], float(args.max_lot_per_trade))
    raw.loc[~raw["trade_enabled"], "effective_lot"] = 0.0
    raw["b_h1_close_below_ema20"] = raw["h1_close"] < raw["h1_ema20"]
    return raw.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    eval_df = df[df["outcome"].isin(["WIN", "LOSS", "TIMEOUT"])].copy()
    if eval_df.empty:
        return pd.DataFrame(columns=group_cols + ["trades", "wins", "losses", "timeouts", "win_rate", "total_r", "lot_weighted_r", "avg_r", "pf", "max_dd_r"])
    rows = []
    for key, g in eval_df.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        r = pd.to_numeric(g["realized_r"], errors="coerce")
        wr = pd.to_numeric(g["lot_weighted_r"], errors="coerce")
        row = {col: val for col, val in zip(group_cols, key)}
        row.update({
            "trades": int(len(g)),
            "wins": int((g["outcome"] == "WIN").sum()),
            "losses": int((g["outcome"] == "LOSS").sum()),
            "timeouts": int((g["outcome"] == "TIMEOUT").sum()),
            "win_rate": float((g["outcome"] == "WIN").mean()),
            "total_r": float(r.sum()),
            "lot_weighted_r": float(wr.sum()),
            "avg_r": float(r.mean()),
            "pf": profit_factor(r),
            "max_dd_r": max_drawdown_r(r),
            "first_entry_time": g["entry_time"].min(),
            "last_entry_time": g["entry_time"].max(),
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols, kind="mergesort").reset_index(drop=True)


def build_removed_bonly_table(current: pd.DataFrame, strict: pd.DataFrame) -> pd.DataFrame:
    cur_b = current[current["rank"].eq("B_ONLY_SAFE")].copy()
    strict_keys = set(strict[strict["rank"].eq("B_ONLY_SAFE")]["entry_time"].astype(str))
    removed = cur_b[~cur_b["entry_time"].astype(str).isin(strict_keys)].copy()
    return removed.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")

    frames = load_frames(args.csv_dir)
    write_csv(build_data_coverage(frames), args.out_dir / "data_coverage.csv")
    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m1 = add_indicators(frames["M1"], "M1")
    ctx = attach_context(m15, h1, h4, d1)

    all_trades = []
    cooled_by_variant = {}
    for variant in ["current_b", "strict_b_h1_close_below_ema20"]:
        raw = build_variant_signals(ctx, args, variant=variant)
        write_csv(raw, args.out_dir / f"signals_raw_{variant}.csv")
        cooled = apply_common_cooldown(raw, int(args.cooldown_bars_m15))
        cooled_by_variant[variant] = cooled
        write_csv(cooled, args.out_dir / f"signals_cooldown_{variant}.csv")
        trades = evaluate_trades(cooled, m1, args)
        write_csv(trades, args.out_dir / f"trades_{variant}.csv")
        all_trades.append(trades)

    trades_all = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    write_csv(trades_all, args.out_dir / "trades_compare_all.csv")

    summary_by_variant_rank = summarize(trades_all, ["variant", "rank"])
    summary_by_variant = summarize(trades_all, ["variant"])
    monthly = summarize(trades_all, ["variant", "entry_month"])
    write_csv(summary_by_variant_rank, args.out_dir / "summary_by_variant_rank.csv")
    write_csv(summary_by_variant, args.out_dir / "summary_by_variant.csv")
    write_csv(monthly, args.out_dir / "monthly_by_variant.csv")

    removed = build_removed_bonly_table(cooled_by_variant["current_b"], cooled_by_variant["strict_b_h1_close_below_ema20"])
    removed_eval = evaluate_trades(removed, m1, args) if not removed.empty else removed
    write_csv(removed_eval, args.out_dir / "removed_by_h1_close_below_ema20_filter.csv")
    removed_summary = summarize(removed_eval.assign(variant="removed_by_strict_filter") if not removed_eval.empty else removed_eval, ["variant"])
    write_csv(removed_summary, args.out_dir / "removed_by_h1_filter_summary.csv")

    print("[INFO] summary_by_variant")
    if summary_by_variant.empty:
        print("(empty)")
    else:
        print(summary_by_variant.to_string(index=False))
    print("\n[INFO] summary_by_variant_rank")
    if summary_by_variant_rank.empty:
        print("(empty)")
    else:
        print(summary_by_variant_rank.to_string(index=False))
    print("\n[INFO] removed_by_h1_filter_summary")
    if removed_summary.empty:
        print("(empty)")
    else:
        print(removed_summary.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
