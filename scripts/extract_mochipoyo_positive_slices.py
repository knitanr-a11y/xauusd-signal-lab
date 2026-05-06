#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract positive Mochipoyo backtest slices for deeper review.

This script reads a trade-level first-touch backtest CSV and automatically selects
pair/rank/direction slices that meet minimum trade count, total R, PF, and DD rules.
It writes:
- selected trades CSV
- selected slice summary CSV
- selected slice x month CSV
- JSON summary

No signals are adopted by this script. It only prepares review datasets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def max_drawdown_r(r_values: pd.Series) -> float:
    if r_values.empty:
        return 0.0
    eq = r_values.cumsum()
    peak = eq.cummax()
    return float((peak - eq).max())


def max_consecutive_losses(outcomes: pd.Series) -> int:
    cur = 0
    best = 0
    for x in outcomes.astype(str):
        if x == "LOSS":
            cur += 1
            best = max(best, cur)
        elif x == "WIN":
            cur = 0
    return best


def stats(g: pd.DataFrame) -> dict:
    wins = int((g["outcome"] == "WIN").sum())
    losses = int((g["outcome"] == "LOSS").sum())
    timeouts = int((g["outcome"] == "TIMEOUT").sum())
    no_data = int((g["outcome"] == "NO_DATA").sum())
    resolved = wins + losses
    gp = float(g.loc[g["r_result"] > 0, "r_result"].sum())
    gl = float(-g.loc[g["r_result"] < 0, "r_result"].sum())
    return {
        "trades": int(len(g)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "no_data": no_data,
        "win_rate_resolved": wins / resolved if resolved else None,
        "total_r": float(g["r_result"].sum()),
        "avg_r": float(g["r_result"].mean()) if len(g) else None,
        "pf": gp / gl if gl > 0 else None,
        "max_dd_r": max_drawdown_r(g["r_result"]),
        "max_consecutive_losses": max_consecutive_losses(g["outcome"]),
        "avg_total_score": float(g["total_score"].mean()) if "total_score" in g.columns else None,
        "avg_context_score": float(g["context_score"].mean()) if "context_score" in g.columns else None,
        "avg_base_score": float(g["base_score"].mean()) if "base_score" in g.columns else None,
    }


def grouped_stats(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(keys, dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = {k: v for k, v in zip(keys, key)}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def select_slices(slice_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = slice_df.copy()
    out = out[out["trades"] >= args.min_trades]
    out = out[out["total_r"] >= args.min_total_r]
    out = out[out["pf"] >= args.min_pf]
    out = out[out["max_dd_r"] <= args.max_dd_r]
    out = out.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False])
    if args.top_n > 0:
        out = out.head(args.top_n)
    return out.reset_index(drop=True)


def slice_key(row: pd.Series) -> str:
    return f"{row['pair_name']}|{row['candidate_rank']}|{row['direction']}"


def main() -> int:
    p = argparse.ArgumentParser(description="Extract positive pair/rank/direction slices from Mochipoyo backtest CSV.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_positive")
    p.add_argument("--min-trades", type=int, default=30)
    p.add_argument("--min-total-r", type=float, default=2.0)
    p.add_argument("--min-pf", type=float, default=1.05)
    p.add_argument("--max-dd-r", type=float, default=15.0)
    p.add_argument("--top-n", type=int, default=12)
    args = p.parse_args()

    src = Path(args.backtest_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    df = df.sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")

    slice_df = grouped_stats(df, ["pair_name", "candidate_rank", "direction"])
    selected_slices = select_slices(slice_df, args)
    selected_slices["selected_slice"] = selected_slices.apply(slice_key, axis=1) if len(selected_slices) else []

    selected_keys = set(selected_slices["selected_slice"].tolist()) if len(selected_slices) else set()
    df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    selected_trades = df[df["selected_slice"].isin(selected_keys)].copy()

    month_rows = []
    if len(selected_trades):
        for key, g in selected_trades.groupby(["selected_slice", "entry_month"], dropna=False, sort=True):
            selected_slice, month = key
            row = {"selected_slice": selected_slice, "entry_month": month}
            row.update(stats(g.sort_values("entry_time")))
            month_rows.append(row)
    selected_month = pd.DataFrame(month_rows)
    if len(selected_month):
        selected_month = selected_month.sort_values(["selected_slice", "entry_month"])

    trades_csv = prefix.with_name(prefix.name + "_trades.csv")
    slices_csv = prefix.with_name(prefix.name + "_slices.csv")
    month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    selected_trades.to_csv(trades_csv, index=False, encoding="utf-8-sig")
    selected_slices.to_csv(slices_csv, index=False, encoding="utf-8-sig")
    selected_month.to_csv(month_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "input_trades": int(len(df)),
        "selected_trades": int(len(selected_trades)),
        "selected_slices": int(len(selected_slices)),
        "filters": {
            "min_trades": args.min_trades,
            "min_total_r": args.min_total_r,
            "min_pf": args.min_pf,
            "max_dd_r": args.max_dd_r,
            "top_n": args.top_n,
        },
        "files": {
            "trades_csv": str(trades_csv),
            "slices_csv": str(slices_csv),
            "month_csv": str(month_csv),
        },
        "selected_slice_records": selected_slices.where(pd.notna(selected_slices), None).to_dict("records"),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("extract_mochipoyo_positive_slices")
    print(f"source: {src}")
    print(f"input_trades: {len(df)}")
    print(f"selected_slices: {len(selected_slices)}")
    print(f"selected_trades: {len(selected_trades)}")
    print(f"trades_csv: {trades_csv}")
    print(f"slices_csv: {slices_csv}")
    print(f"month_csv: {month_csv}")
    print(f"summary_json: {summary_json}")
    if len(selected_slices):
        print("selected_slices:")
        print(selected_slices[["selected_slice", "trades", "win_rate_resolved", "total_r", "pf", "max_dd_r", "max_consecutive_losses"]].to_string(index=False))
    else:
        print("selected_slices: none")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
