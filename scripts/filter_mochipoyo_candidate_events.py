#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter Mochipoyo multi-timeframe candidate STATES into candidate EVENTS.

The multi-timeframe scanner intentionally outputs broad candidate states for audit.
That can produce many rows because a good environment may persist for many candles.
This filter turns those persistent states into reviewable event candidates by applying:

- minimum rank
- optional MACD divergence / hidden divergence requirement
- optional Granville type requirement
- per-pair cooldown in minutes
- optional per-day cap per pair and direction

This script does not calculate outcomes and does not adopt signals.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


RANK_VALUE = {"A": 3, "B": 2, "C": 1, "": 0}

DEFAULT_COOLDOWN_BY_BASE_TF = {
    "M1": 60,
    "M5": 240,
    "M15": 480,
    "H1": 1440,
    "H4": 2880,
    "D1": 10080,
}


def rank_ok(rank: str, min_rank: str) -> bool:
    return RANK_VALUE.get(str(rank), 0) >= RANK_VALUE[min_rank]


def has_any_divergence(row: pd.Series) -> bool:
    return bool(str(row.get("context_macd_div_type", "")).strip()) or bool(str(row.get("base_macd_div_type", "")).strip())


def has_granville(row: pd.Series) -> bool:
    return bool(str(row.get("context_granville_type", "")).strip())


def cooldown_minutes_for_row(row: pd.Series, default_minutes: int) -> int:
    base_tf = str(row.get("base_tf", "")).upper()
    return int(DEFAULT_COOLDOWN_BY_BASE_TF.get(base_tf, default_minutes))


def apply_cooldown(df: pd.DataFrame, default_minutes: int) -> pd.DataFrame:
    kept = []
    for _, group in df.sort_values("signal_close_time").groupby(["pair_name", "direction"], sort=False):
        last_time = None
        for idx, row in group.iterrows():
            t = pd.Timestamp(row["signal_close_time"])
            cd = cooldown_minutes_for_row(row, default_minutes)
            if last_time is None or t >= last_time + pd.Timedelta(minutes=cd):
                kept.append(idx)
                last_time = t
    return df.loc[kept].sort_values("signal_close_time").reset_index(drop=True)


def apply_daily_cap(df: pd.DataFrame, max_per_day: int) -> pd.DataFrame:
    if max_per_day <= 0 or df.empty:
        return df
    work = df.copy()
    work["_date"] = pd.to_datetime(work["signal_close_time"]).dt.date.astype(str)
    kept_parts = []
    for _, group in work.groupby(["_date", "pair_name", "direction"], sort=False):
        g = group.sort_values(["total_score", "context_score", "base_score"], ascending=[False, False, False]).head(max_per_day)
        kept_parts.append(g)
    out = pd.concat(kept_parts, ignore_index=True) if kept_parts else work.iloc[0:0].copy()
    out = out.drop(columns=["_date"], errors="ignore")
    return out.sort_values("signal_close_time").reset_index(drop=True)


def build_summary(df_before: pd.DataFrame, df_after: pd.DataFrame, output_csv: Path) -> dict:
    summary = {
        "input_rows": int(len(df_before)),
        "output_rows": int(len(df_after)),
        "output_csv": str(output_csv),
    }
    if len(df_after):
        summary.update(
            {
                "first_signal_time": str(df_after["signal_time"].min()),
                "last_signal_time": str(df_after["signal_time"].max()),
                "by_pair": df_after["pair_name"].value_counts().to_dict(),
                "by_rank": df_after["candidate_rank"].value_counts().to_dict(),
                "by_direction": df_after["direction"].value_counts().to_dict(),
                "by_pair_rank": {str(k): int(v) for k, v in df_after.groupby(["pair_name", "candidate_rank"]).size().items()},
            }
        )
        audit_cols = [
            "audit_context_confirmed",
            "audit_base_pivot_confirmed",
            "audit_context_pivot_confirmed",
            "audit_entry_after_signal",
        ]
        audit = {}
        for col in audit_cols:
            if col in df_after.columns:
                audit[col.replace("audit_", "") + "_violations"] = int((~df_after[col].astype(bool)).sum())
        summary["audit"] = audit
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Filter broad Mochipoyo candidate states into event candidates.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--summary-json", default=None)
    p.add_argument("--min-rank", choices=["A", "B", "C"], default="B")
    p.add_argument("--require-any-divergence", dest="require_any_divergence", action="store_true", default=True)
    p.add_argument("--no-require-any-divergence", dest="require_any_divergence", action="store_false")
    p.add_argument("--require-granville", dest="require_granville", action="store_true", default=True)
    p.add_argument("--no-require-granville", dest="require_granville", action="store_false")
    p.add_argument("--cooldown-minutes-default", type=int, default=240)
    p.add_argument("--max-per-day-per-pair-direction", type=int, default=6)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json) if args.summary_json else output_csv.with_suffix(".summary.json")

    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    before = df.copy()
    if df.empty:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        summary_json.write_text(json.dumps(build_summary(before, df, output_csv), ensure_ascii=False, indent=2), encoding="utf-8")
        print("input empty")
        return 0

    df["signal_close_time"] = pd.to_datetime(df["signal_close_time"], errors="coerce")
    df = df.dropna(subset=["signal_close_time"])
    df = df[df["candidate_rank"].map(lambda x: rank_ok(str(x), args.min_rank))]

    if args.require_any_divergence:
        df = df[df.apply(has_any_divergence, axis=1)]
    if args.require_granville:
        df = df[df.apply(has_granville, axis=1)]

    df = df.sort_values(["signal_close_time", "pair_name", "direction", "total_score"], ascending=[True, True, True, False]).reset_index(drop=True)
    after_basic = len(df)
    df = apply_cooldown(df, args.cooldown_minutes_default)
    after_cooldown = len(df)
    df = apply_daily_cap(df, args.max_per_day_per_pair_direction)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    summary = build_summary(before, df, output_csv)
    summary.update(
        {
            "filters": {
                "min_rank": args.min_rank,
                "require_any_divergence": args.require_any_divergence,
                "require_granville": args.require_granville,
                "cooldown_minutes_by_base_tf": DEFAULT_COOLDOWN_BY_BASE_TF,
                "cooldown_minutes_default": args.cooldown_minutes_default,
                "max_per_day_per_pair_direction": args.max_per_day_per_pair_direction,
            },
            "rows_after_basic_filters": int(after_basic),
            "rows_after_cooldown": int(after_cooldown),
        }
    )
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("filter_mochipoyo_candidate_events")
    print(f"input_rows: {len(before)}")
    print(f"rows_after_basic_filters: {after_basic}")
    print(f"rows_after_cooldown: {after_cooldown}")
    print(f"output_rows: {len(df)}")
    print(f"output_csv: {output_csv}")
    print(f"summary_json: {summary_json}")
    if len(df):
        print("by_pair:")
        print(df["pair_name"].value_counts().to_string())
        print("by_rank:")
        print(df["candidate_rank"].value_counts().to_string())
        print("by_direction:")
        print(df["direction"].value_counts().to_string())
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
