#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create review samples from a Mochipoyo final portfolio CSV.

This script extracts representative rows for manual inspection:
- WIN / LOSS / TIMEOUT samples
- high-score WIN / high-score LOSS
- weak-month samples
- loss-streak neighborhood rows

It does not change trades or outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

REVIEW_COLUMNS = [
    "entry_time", "exit_time", "pair_name", "selected_slice", "candidate_rank", "direction",
    "entry_price", "sl_price", "tp_price", "risk_distance", "outcome", "r_result",
    "bars_to_exit", "exit_reason", "total_score", "context_score", "base_score",
    "context_time", "context_close_time", "base_time", "base_close_time", "signal_close_time",
    "context_granville_type", "context_bias", "context_ema_order", "context_rci9", "context_rci14", "context_rci18",
    "context_macd_div_type", "base_ema_order", "base_rci9", "base_rci14", "base_rci18", "base_macd_div_type",
    "reason_text", "source_filter_rank", "source_filter_name",
]


def pick_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in REVIEW_COLUMNS if c in df.columns]
    rest = [c for c in df.columns if c not in cols]
    return df[cols + rest]


def sample_group(df: pd.DataFrame, name: str, n: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    if "entry_month" in out.columns:
        # Try to keep month diversity.
        parts = []
        per_month = max(1, n // max(1, out["entry_month"].nunique()))
        for _, g in out.groupby("entry_month", sort=True):
            parts.append(g.head(per_month))
        sampled = pd.concat(parts, ignore_index=True).head(n) if parts else out.head(n)
    else:
        sampled = out.head(n)
    sampled.insert(0, "review_bucket", name)
    return sampled


def loss_streak_neighborhood(df: pd.DataFrame, window: int) -> pd.DataFrame:
    if df.empty or "outcome" not in df.columns:
        return df.iloc[0:0].copy()
    work = df.sort_values("entry_time").reset_index(drop=True)
    best_start = None
    best_len = 0
    cur_start = None
    cur_len = 0
    for i, x in enumerate(work["outcome"].astype(str)):
        if x == "LOSS":
            if cur_start is None:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
        elif x == "WIN":
            cur_start = None
            cur_len = 0
    if best_start is None:
        return work.iloc[0:0].copy()
    start = max(0, best_start - window)
    end = min(len(work), best_start + best_len + window)
    out = work.iloc[start:end].copy()
    out.insert(0, "review_bucket", f"max_loss_streak_neighborhood_len_{best_len}")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Extract review samples from Mochipoyo final portfolio.")
    p.add_argument("--portfolio-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_review_samples")
    p.add_argument("--sample-per-bucket", type=int, default=12)
    p.add_argument("--weak-month", action="append", default=["2026-03", "2026-04"])
    p.add_argument("--streak-window", type=int, default=3)
    args = p.parse_args()

    df = pd.read_csv(args.portfolio_csv, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    if "exit_time" in df.columns:
        df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)

    n = args.sample_per_bucket
    buckets = []
    buckets.append(sample_group(df[df["outcome"].astype(str) == "WIN"].sort_values("entry_time"), "win_chronological", n))
    buckets.append(sample_group(df[df["outcome"].astype(str) == "LOSS"].sort_values("entry_time"), "loss_chronological", n))
    buckets.append(sample_group(df[df["outcome"].astype(str) == "TIMEOUT"].sort_values("entry_time"), "timeout_chronological", n))

    if "total_score" in df.columns:
        buckets.append(sample_group(df[df["outcome"].astype(str) == "WIN"].sort_values("total_score", ascending=False), "high_score_win", n))
        buckets.append(sample_group(df[df["outcome"].astype(str) == "LOSS"].sort_values("total_score", ascending=False), "high_score_loss", n))

    for month in args.weak_month:
        g = df[df["entry_month"] == month].sort_values("entry_time")
        if not g.empty:
            buckets.append(sample_group(g[g["outcome"].astype(str) == "WIN"], f"weak_month_{month}_win", max(4, n // 2)))
            buckets.append(sample_group(g[g["outcome"].astype(str) == "LOSS"], f"weak_month_{month}_loss", max(4, n // 2)))
            buckets.append(sample_group(g[g["outcome"].astype(str) == "TIMEOUT"], f"weak_month_{month}_timeout", max(3, n // 3)))

    buckets.append(loss_streak_neighborhood(df, args.streak_window))

    review = pd.concat([b for b in buckets if not b.empty], ignore_index=True) if buckets else df.iloc[0:0].copy()
    review = pick_cols(review)

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    review_csv = prefix.with_name(prefix.name + "_review_rows.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    by_bucket_csv = prefix.with_name(prefix.name + "_by_bucket.csv")

    review.to_csv(review_csv, index=False, encoding="utf-8-sig")
    by_bucket = review.groupby("review_bucket", dropna=False).size().reset_index(name="rows") if len(review) else pd.DataFrame(columns=["review_bucket", "rows"])
    by_bucket.to_csv(by_bucket_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": args.portfolio_csv,
        "input_rows": int(len(df)),
        "review_rows": int(len(review)),
        "weak_months": args.weak_month,
        "files": {
            "review_csv": str(review_csv),
            "by_bucket_csv": str(by_bucket_csv),
        },
        "by_bucket": by_bucket.to_dict("records"),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("sample_mochipoyo_review_trades")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
