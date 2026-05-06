#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a de-duplicated refined portfolio from the RR1.2 filter leaderboard.

Inputs:
- trade-level backtest CSV:
  data/results/mochipoyo/selected/gold_mochipoyo_passed_backtest_rr12.csv
- leaderboard CSV produced by refine_mochipoyo_gold_rr12_filters.py

Why this exists:
The filter leaderboard often contains overlapping filters. Adding all top filters
without de-duplication double-counts the same trade. This script reconstructs
supported filter names, unions matching trades, removes duplicate trade rows, and
applies a chronological cooldown to create a portfolio candidate for review.

Supported filter name patterns include:
- ALL
- direction=SELL
- slice=GOLD_H4_M5_SCALP|B|SELL
- total_score>=9.0
- context_score>=6.0
- base_score>=3.0
- token=context_retrace_to_ema_band
- token=context_retrace_to_ema_band|total_score>=9.0
- token=context_retrace_to_ema_band|context_score>=6.0
- token_all=tokenA+tokenB
- direction=SELL|token=tokenA
- direction=SELL|context_score>=6.0
- slice=...|total_score>=9.0
- slice=...|context_score>=6.0

This script does not adopt signals. It prepares review CSVs only.
"""

from __future__ import annotations

import argparse
import json
import re
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


def stats(df: pd.DataFrame) -> dict:
    wins = int((df["outcome"] == "WIN").sum()) if len(df) else 0
    losses = int((df["outcome"] == "LOSS").sum()) if len(df) else 0
    timeouts = int((df["outcome"] == "TIMEOUT").sum()) if len(df) else 0
    resolved = wins + losses
    gp = float(df.loc[df["r_result"] > 0, "r_result"].sum()) if len(df) else 0.0
    gl = float(-df.loc[df["r_result"] < 0, "r_result"].sum()) if len(df) else 0.0
    return {
        "trades": int(len(df)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate_resolved": wins / resolved if resolved else None,
        "total_r": float(df["r_result"].sum()) if len(df) else 0.0,
        "avg_r": float(df["r_result"].mean()) if len(df) else None,
        "pf": gp / gl if gl > 0 else None,
        "max_dd_r": max_drawdown_r(df["r_result"]) if len(df) else 0.0,
        "max_consecutive_losses": max_consecutive_losses(df["outcome"]) if len(df) else 0,
    }


def monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for month, g in df.groupby("entry_month", sort=True):
        row = {"entry_month": month}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def apply_name_filter(df: pd.DataFrame, name: str) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    parts = str(name).split("|")

    # Special first part may include slice with pipe characters, so handle slice= separately.
    if name.startswith("slice="):
        # Slice names are exactly pair|rank|direction and may be followed by |score condition.
        m = re.match(r"^slice=([^|]+\|[^|]+\|[^|]+)(?:\|(.*))?$", name)
        if not m:
            return df.iloc[0:0].copy()
        selected_slice = m.group(1)
        rest = m.group(2)
        mask &= df["selected_slice"] == selected_slice
        parts = rest.split("|") if rest else []
    elif name.startswith("token_all="):
        token_part = parts[0].replace("token_all=", "", 1)
        for tok in token_part.split("+"):
            if tok:
                mask &= contains_token(df["reason_text"], tok)
        parts = parts[1:]
    else:
        parts = parts if name != "ALL" else []

    for part in parts:
        if not part:
            continue
        if part.startswith("direction="):
            mask &= df["direction"].astype(str) == part.replace("direction=", "", 1)
        elif part.startswith("token="):
            mask &= contains_token(df["reason_text"], part.replace("token=", "", 1))
        elif part.startswith("total_score>="):
            mask &= df["total_score"] >= float(part.replace("total_score>=", "", 1))
        elif part.startswith("context_score>="):
            mask &= df["context_score"] >= float(part.replace("context_score>=", "", 1))
        elif part.startswith("base_score>="):
            mask &= df["base_score"] >= float(part.replace("base_score>=", "", 1))
        elif part.startswith("known_any_strong_tokens"):
            # This synthetic filter is intentionally not reconstructed here because the exact token set
            # is generated in the refiner. Skip by returning empty unless it has a score and is handled elsewhere.
            return df.iloc[0:0].copy()
        else:
            # Unknown pattern: fail closed.
            return df.iloc[0:0].copy()

    return df[mask].sort_values("entry_time", kind="mergesort").copy()


def trade_identity_columns(df: pd.DataFrame) -> list[str]:
    preferred = ["entry_time", "pair_name", "candidate_rank", "direction", "entry_price", "base_time", "signal_time"]
    return [c for c in preferred if c in df.columns]


def dedupe_exact(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    cols = trade_identity_columns(df)
    if not cols:
        return df.drop_duplicates().sort_values("entry_time").reset_index(drop=True)
    return df.drop_duplicates(subset=cols, keep="first").sort_values("entry_time").reset_index(drop=True)


def cooldown_portfolio(df: pd.DataFrame, cooldown_minutes: int, by_direction: bool) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    sort_cols = ["entry_time", "pf_filter", "total_r_filter", "total_score", "context_score", "base_score"]
    ascending = [True, False, False, False, False, False]
    sort_cols = [c for c in sort_cols if c in df.columns]
    ascending = ascending[: len(sort_cols)]
    work = df.sort_values(sort_cols, ascending=ascending).copy()
    kept = []
    last_by_key: dict[str, pd.Timestamp] = {}
    for idx, row in work.iterrows():
        key = str(row.get("direction", "ALL")) if by_direction else "ALL"
        t = pd.Timestamp(row["entry_time"])
        last = last_by_key.get(key)
        if last is None or t >= last + pd.Timedelta(minutes=cooldown_minutes):
            kept.append(idx)
            last_by_key[key] = t
    return work.loc[kept].sort_values("entry_time").reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build refined Mochipoyo portfolio from filter leaderboard.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--leaderboard-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_refined_portfolio")
    p.add_argument("--min-filter-trades", type=int, default=30)
    p.add_argument("--min-filter-pf", type=float, default=1.50)
    p.add_argument("--min-filter-total-r", type=float, default=8.0)
    p.add_argument("--max-filter-dd-r", type=float, default=8.0)
    p.add_argument("--max-filters", type=int, default=20)
    p.add_argument("--portfolio-cooldown-minutes", type=int, default=60)
    p.add_argument("--cooldown-by-direction", action="store_true", default=True)
    p.add_argument("--no-cooldown-by-direction", dest="cooldown_by_direction", action="store_false")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.backtest_csv)
    leaderboard_path = Path(args.leaderboard_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    df = df.sort_values("entry_time", kind="mergesort").reset_index(drop=True)

    lb = pd.read_csv(leaderboard_path, encoding="utf-8-sig")
    lb = lb[(lb["trades"] >= args.min_filter_trades) & (lb["pf"] >= args.min_filter_pf) & (lb["total_r"] >= args.min_filter_total_r) & (lb["max_dd_r"] <= args.max_filter_dd_r)].copy()
    lb = lb.sort_values(["pf", "total_r", "max_dd_r", "trades"], ascending=[False, False, True, False]).head(args.max_filters).reset_index(drop=True)

    parts = []
    coverage_rows = []
    for rank, row in lb.iterrows():
        name = str(row["name"])
        g = apply_name_filter(df, name)
        if g.empty:
            continue
        g = g.copy()
        g["source_filter_name"] = name
        g["source_filter_rank"] = int(rank + 1)
        g["pf_filter"] = float(row["pf"])
        g["total_r_filter"] = float(row["total_r"])
        parts.append(g)
        cov = {"source_filter_rank": int(rank + 1), "source_filter_name": name}
        cov.update(stats(g.sort_values("entry_time")))
        coverage_rows.append(cov)

    union = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    union_exact = dedupe_exact(union)
    portfolio = cooldown_portfolio(union_exact, args.portfolio_cooldown_minutes, args.cooldown_by_direction)

    selected_filters_csv = prefix.with_name(prefix.name + "_selected_filters.csv")
    union_csv = prefix.with_name(prefix.name + "_union_exact_deduped.csv")
    portfolio_csv = prefix.with_name(prefix.name + "_portfolio.csv")
    portfolio_month_csv = prefix.with_name(prefix.name + "_portfolio_by_month.csv")
    coverage_csv = prefix.with_name(prefix.name + "_filter_coverage.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    lb.to_csv(selected_filters_csv, index=False, encoding="utf-8-sig")
    union_exact.to_csv(union_csv, index=False, encoding="utf-8-sig")
    portfolio.to_csv(portfolio_csv, index=False, encoding="utf-8-sig")
    monthly_stats(portfolio).to_csv(portfolio_month_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage_rows).to_csv(coverage_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source_backtest_csv": str(src),
        "source_leaderboard_csv": str(leaderboard_path),
        "input_trades": int(len(df)),
        "selected_filters": int(len(lb)),
        "union_rows_before_exact_dedupe": int(len(union)),
        "union_rows_after_exact_dedupe": int(len(union_exact)),
        "portfolio_rows_after_cooldown": int(len(portfolio)),
        "filter_selection": {
            "min_filter_trades": args.min_filter_trades,
            "min_filter_pf": args.min_filter_pf,
            "min_filter_total_r": args.min_filter_total_r,
            "max_filter_dd_r": args.max_filter_dd_r,
            "max_filters": args.max_filters,
        },
        "portfolio_cooldown_minutes": args.portfolio_cooldown_minutes,
        "cooldown_by_direction": args.cooldown_by_direction,
        "union_stats": stats(union_exact.sort_values("entry_time")),
        "portfolio_stats": stats(portfolio.sort_values("entry_time")),
        "files": {
            "selected_filters_csv": str(selected_filters_csv),
            "union_csv": str(union_csv),
            "portfolio_csv": str(portfolio_csv),
            "portfolio_month_csv": str(portfolio_month_csv),
            "coverage_csv": str(coverage_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("build_mochipoyo_refined_portfolio")
    print(f"input_trades: {len(df)}")
    print(f"selected_filters: {len(lb)}")
    print(f"union_rows_before_exact_dedupe: {len(union)}")
    print(f"union_rows_after_exact_dedupe: {len(union_exact)}")
    print(f"portfolio_rows_after_cooldown: {len(portfolio)}")
    print(f"selected_filters_csv: {selected_filters_csv}")
    print(f"union_csv: {union_csv}")
    print(f"portfolio_csv: {portfolio_csv}")
    print(f"portfolio_month_csv: {portfolio_month_csv}")
    print(f"coverage_csv: {coverage_csv}")
    print(f"summary_json: {summary_json}")
    print("portfolio_stats:")
    print(json.dumps(summary["portfolio_stats"], ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
