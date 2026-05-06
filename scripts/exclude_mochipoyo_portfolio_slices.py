#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exclude selected Mochipoyo portfolio slices and recalculate stats.

Use case:
- Start from a reviewed portfolio CSV, e.g.
  data/results/mochipoyo/selected/gold_mochipoyo_rr12_refined_portfolio_portfolio.csv
- Remove weak slice(s), e.g.
  GOLD_H4_M15_DAYTRADE|A|SELL
- Recalculate overall/month/pair/direction/slice stats

This script does not adopt signals or alter source files. It writes new review CSVs.
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
    wins = int((g["outcome"] == "WIN").sum()) if len(g) else 0
    losses = int((g["outcome"] == "LOSS").sum()) if len(g) else 0
    timeouts = int((g["outcome"] == "TIMEOUT").sum()) if len(g) else 0
    no_data = int((g["outcome"] == "NO_DATA").sum()) if "NO_DATA" in set(g["outcome"].astype(str)) else 0
    resolved = wins + losses
    gp = float(g.loc[g["r_result"] > 0, "r_result"].sum()) if len(g) else 0.0
    gl = float(-g.loc[g["r_result"] < 0, "r_result"].sum()) if len(g) else 0.0
    return {
        "trades": int(len(g)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "no_data": no_data,
        "win_rate_resolved": wins / resolved if resolved else None,
        "total_r": float(g["r_result"].sum()) if len(g) else 0.0,
        "avg_r": float(g["r_result"].mean()) if len(g) else None,
        "pf": gp / gl if gl > 0 else None,
        "max_dd_r": max_drawdown_r(g["r_result"]) if len(g) else 0.0,
        "max_consecutive_losses": max_consecutive_losses(g["outcome"]) if len(g) else 0,
        "avg_total_score": float(g["total_score"].mean()) if "total_score" in g.columns and len(g) else None,
        "avg_context_score": float(g["context_score"].mean()) if "context_score" in g.columns and len(g) else None,
        "avg_base_score": float(g["base_score"].mean()) if "base_score" in g.columns and len(g) else None,
    }


def grouped_stats(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(keys, dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = {k: v for k, v in zip(keys, key)}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], na_position="last")
    return out


def ensure_selected_slice(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "selected_slice" not in out.columns:
        out["selected_slice"] = out.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Exclude selected slices from Mochipoyo portfolio and recalculate stats.")
    p.add_argument("--portfolio-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_refined_224_minus_weak")
    p.add_argument(
        "--exclude-slice",
        action="append",
        required=True,
        help="Slice to exclude, e.g. GOLD_H4_M15_DAYTRADE|A|SELL. Can be specified multiple times.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.portfolio_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    df = ensure_selected_slice(df)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    df = df.sort_values("entry_time", kind="mergesort").reset_index(drop=True)

    exclude_set = set(args.exclude_slice)
    removed = df[df["selected_slice"].isin(exclude_set)].copy()
    kept = df[~df["selected_slice"].isin(exclude_set)].copy().sort_values("entry_time", kind="mergesort").reset_index(drop=True)

    kept_csv = prefix.with_name(prefix.name + "_portfolio.csv")
    removed_csv = prefix.with_name(prefix.name + "_removed.csv")
    by_month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    by_pair_csv = prefix.with_name(prefix.name + "_by_pair.csv")
    by_direction_csv = prefix.with_name(prefix.name + "_by_direction.csv")
    by_slice_csv = prefix.with_name(prefix.name + "_by_slice.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    kept.to_csv(kept_csv, index=False, encoding="utf-8-sig")
    removed.to_csv(removed_csv, index=False, encoding="utf-8-sig")
    grouped_stats(kept, ["entry_month"]).to_csv(by_month_csv, index=False, encoding="utf-8-sig")
    grouped_stats(kept, ["pair_name"]).to_csv(by_pair_csv, index=False, encoding="utf-8-sig")
    grouped_stats(kept, ["direction"]).to_csv(by_direction_csv, index=False, encoding="utf-8-sig")
    grouped_stats(kept, ["selected_slice"]).to_csv(by_slice_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "exclude_slices": sorted(exclude_set),
        "input_stats": stats(df.sort_values("entry_time")),
        "removed_stats": stats(removed.sort_values("entry_time")),
        "kept_stats": stats(kept.sort_values("entry_time")),
        "files": {
            "kept_csv": str(kept_csv),
            "removed_csv": str(removed_csv),
            "by_month_csv": str(by_month_csv),
            "by_pair_csv": str(by_pair_csv),
            "by_direction_csv": str(by_direction_csv),
            "by_slice_csv": str(by_slice_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("exclude_mochipoyo_portfolio_slices")
    print(f"source: {src}")
    print(f"exclude_slices: {sorted(exclude_set)}")
    print("input_stats:")
    print(json.dumps(summary["input_stats"], ensure_ascii=False, indent=2))
    print("removed_stats:")
    print(json.dumps(summary["removed_stats"], ensure_ascii=False, indent=2))
    print("kept_stats:")
    print(json.dumps(summary["kept_stats"], ensure_ascii=False, indent=2))
    print(f"kept_csv: {kept_csv}")
    print(f"removed_csv: {removed_csv}")
    print(f"by_month_csv: {by_month_csv}")
    print(f"by_pair_csv: {by_pair_csv}")
    print(f"by_direction_csv: {by_direction_csv}")
    print(f"by_slice_csv: {by_slice_csv}")
    print(f"summary_json: {summary_json}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
