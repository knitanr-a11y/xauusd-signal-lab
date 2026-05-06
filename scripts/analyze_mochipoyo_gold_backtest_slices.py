#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze GOLD Mochipoyo first-touch backtest results by useful slices.

This is a post-backtest analyzer. It does not change signals or outcomes.
It helps identify which subset, if any, is worth deeper validation.

Slices:
- pair_name
- candidate_rank
- direction
- pair_name x rank
- pair_name x direction
- rank x direction
- pair_name x rank x direction
- month
- pair_name x month
- reason token hit/miss
- score thresholds
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


def stats_for_group(g: pd.DataFrame) -> dict:
    wins = int((g["outcome"] == "WIN").sum())
    losses = int((g["outcome"] == "LOSS").sum())
    timeouts = int((g["outcome"] == "TIMEOUT").sum())
    no_data = int((g["outcome"] == "NO_DATA").sum())
    resolved = wins + losses
    gross_profit = float(g.loc[g["r_result"] > 0, "r_result"].sum())
    gross_loss = float(-g.loc[g["r_result"] < 0, "r_result"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else None
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
        "pf": pf,
        "max_dd_r": max_drawdown_r(g["r_result"]),
        "max_consecutive_losses": max_consecutive_losses(g["outcome"]),
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
        row.update(stats_for_group(g.sort_values("entry_time")))
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return out.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], na_position="last")


def score_threshold_stats(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    rows = []
    total_scores = sorted({float(x) for x in df["total_score"].dropna().unique()})
    context_scores = sorted({float(x) for x in df["context_score"].dropna().unique()})
    base_scores = sorted({float(x) for x in df["base_score"].dropna().unique()})

    # Keep grid compact and readable.
    total_grid = [x for x in total_scores if x >= 4.5]
    context_grid = [x for x in context_scores if x >= 3.0]
    base_grid = [x for x in base_scores if x >= 0.0]

    for t in total_grid:
        g = df[df["total_score"] >= t]
        if len(g) >= min_trades:
            row = {"filter": f"total_score>={t}", "min_total_score": t, "min_context_score": None, "min_base_score": None}
            row.update(stats_for_group(g.sort_values("entry_time")))
            rows.append(row)
    for c in context_grid:
        g = df[df["context_score"] >= c]
        if len(g) >= min_trades:
            row = {"filter": f"context_score>={c}", "min_total_score": None, "min_context_score": c, "min_base_score": None}
            row.update(stats_for_group(g.sort_values("entry_time")))
            rows.append(row)
    for b in base_grid:
        g = df[df["base_score"] >= b]
        if len(g) >= min_trades:
            row = {"filter": f"base_score>={b}", "min_total_score": None, "min_context_score": None, "min_base_score": b}
            row.update(stats_for_group(g.sort_values("entry_time")))
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return out.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], na_position="last")


def reason_token_stats(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    tokens = set()
    if "reason_text" not in df.columns:
        return pd.DataFrame()
    for text in df["reason_text"].fillna("").astype(str):
        for tok in text.split(";"):
            tok = tok.strip()
            if tok:
                tokens.add(tok)
    rows = []
    for tok in sorted(tokens):
        g = df[df["reason_text"].fillna("").astype(str).str.contains(tok, regex=False)]
        if len(g) >= min_trades:
            row = {"reason_token": tok}
            row.update(stats_for_group(g.sort_values("entry_time")))
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return out.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], na_position="last")


def write_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def top_records(df: pd.DataFrame, n: int = 20) -> list[dict]:
    if df.empty:
        return []
    return df.head(n).where(pd.notna(df.head(n)), None).to_dict("records")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze Mochipoyo GOLD backtest slices.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--output-dir", default="data/results/mochipoyo/analysis")
    p.add_argument("--min-trades", type=int, default=30)
    p.add_argument("--print-top", type=int, default=12)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.backtest_csv)
    out_dir = Path(args.output_dir)
    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    df = df.sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")

    tables: dict[str, pd.DataFrame] = {
        "overall": pd.DataFrame([stats_for_group(df)]),
        "by_pair": grouped_stats(df, ["pair_name"]),
        "by_rank": grouped_stats(df, ["candidate_rank"]),
        "by_direction": grouped_stats(df, ["direction"]),
        "by_pair_rank": grouped_stats(df, ["pair_name", "candidate_rank"]),
        "by_pair_direction": grouped_stats(df, ["pair_name", "direction"]),
        "by_rank_direction": grouped_stats(df, ["candidate_rank", "direction"]),
        "by_pair_rank_direction": grouped_stats(df, ["pair_name", "candidate_rank", "direction"]),
        "by_month": grouped_stats(df, ["entry_month"]),
        "by_pair_month": grouped_stats(df, ["pair_name", "entry_month"]),
        "score_thresholds": score_threshold_stats(df, args.min_trades),
        "reason_tokens": reason_token_stats(df, args.min_trades),
    }

    for name, table in tables.items():
        write_table(table, out_dir / f"{src.stem}_{name}.csv")

    positive = {}
    for name, table in tables.items():
        if table.empty or "total_r" not in table.columns:
            positive[name] = []
            continue
        cand = table[(table["trades"] >= args.min_trades) & (table["total_r"] > 0)].copy()
        cand = cand.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], na_position="last")
        positive[name] = top_records(cand, args.print_top)

    summary = {
        "source": str(src),
        "rows": int(len(df)),
        "min_trades": args.min_trades,
        "overall": top_records(tables["overall"], 1)[0] if not tables["overall"].empty else {},
        "positive_slices": positive,
        "output_dir": str(out_dir),
    }
    summary_path = out_dir / f"{src.stem}_slice_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("analyze_mochipoyo_gold_backtest_slices")
    print(f"source: {src}")
    print(f"rows: {len(df)}")
    print(f"output_dir: {out_dir}")
    print(f"summary_json: {summary_path}")
    print("overall:")
    print(tables["overall"].to_string(index=False))
    print("top by_pair_rank_direction:")
    top = tables["by_pair_rank_direction"].head(args.print_top)
    print(top.to_string(index=False) if not top.empty else "empty")
    print("positive slice counts:")
    for name, records in positive.items():
        print(f"{name}: {len(records)}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
