#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refine GOLD Mochipoyo RR1.2 backtest filters.

Input:
- trade-level backtest CSV, usually:
  data/results/mochipoyo/selected/gold_mochipoyo_passed_backtest_rr12.csv

This script searches practical post-filters over:
- pair/rank/direction selected slice
- total_score/context_score/base_score thresholds
- reason_text tokens
- one-token and two-token combinations

It evaluates each filter by:
- trades, wins/losses/timeouts
- total R, PF, max DD, max consecutive losses
- monthly active count and positive month ratio
- worst month R

It writes a leaderboard and the best filter's trades for manual review.
It does not adopt signals, send notifications, or change candidate generation.
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class FilterSpec:
    name: str
    selected_slices: tuple[str, ...] = ()
    directions: tuple[str, ...] = ()
    min_total_score: float | None = None
    min_context_score: float | None = None
    min_base_score: float | None = None
    require_tokens_all: tuple[str, ...] = ()
    require_tokens_any: tuple[str, ...] = ()


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
    wins = int((df["outcome"] == "WIN").sum())
    losses = int((df["outcome"] == "LOSS").sum())
    timeouts = int((df["outcome"] == "TIMEOUT").sum())
    resolved = wins + losses
    gp = float(df.loc[df["r_result"] > 0, "r_result"].sum())
    gl = float(-df.loc[df["r_result"] < 0, "r_result"].sum())
    return {
        "trades": int(len(df)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate_resolved": wins / resolved if resolved else None,
        "total_r": float(df["r_result"].sum()),
        "avg_r": float(df["r_result"].mean()) if len(df) else None,
        "pf": gp / gl if gl > 0 else None,
        "max_dd_r": max_drawdown_r(df["r_result"]),
        "max_consecutive_losses": max_consecutive_losses(df["outcome"]),
        "avg_total_score": float(df["total_score"].mean()) if "total_score" in df.columns and len(df) else None,
        "avg_context_score": float(df["context_score"].mean()) if "context_score" in df.columns and len(df) else None,
        "avg_base_score": float(df["base_score"].mean()) if "base_score" in df.columns and len(df) else None,
    }


def monthly_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "active_months": 0,
            "positive_months": 0,
            "negative_months": 0,
            "positive_month_ratio": None,
            "worst_month_r": None,
            "best_month_r": None,
            "median_month_r": None,
        }
    g = df.groupby("entry_month", sort=True)["r_result"].sum()
    active = int(len(g))
    pos = int((g > 0).sum())
    neg = int((g < 0).sum())
    return {
        "active_months": active,
        "positive_months": pos,
        "negative_months": neg,
        "positive_month_ratio": pos / active if active else None,
        "worst_month_r": float(g.min()) if active else None,
        "best_month_r": float(g.max()) if active else None,
        "median_month_r": float(g.median()) if active else None,
    }


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def apply_filter(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if spec.selected_slices:
        mask &= df["selected_slice"].isin(spec.selected_slices)
    if spec.directions:
        mask &= df["direction"].isin(spec.directions)
    if spec.min_total_score is not None:
        mask &= df["total_score"] >= spec.min_total_score
    if spec.min_context_score is not None:
        mask &= df["context_score"] >= spec.min_context_score
    if spec.min_base_score is not None:
        mask &= df["base_score"] >= spec.min_base_score
    for token in spec.require_tokens_all:
        mask &= contains_token(df["reason_text"], token)
    if spec.require_tokens_any:
        token_mask = pd.Series(False, index=df.index)
        for token in spec.require_tokens_any:
            token_mask |= contains_token(df["reason_text"], token)
        mask &= token_mask
    return df[mask].sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def tokens_from_reason_text(df: pd.DataFrame, min_count: int) -> list[str]:
    counts: dict[str, int] = {}
    for text in df["reason_text"].fillna("").astype(str):
        for token in text.split(";"):
            token = token.strip()
            if token:
                counts[token] = counts.get(token, 0) + 1
    return sorted([t for t, c in counts.items() if c >= min_count])


def build_specs(df: pd.DataFrame, args: argparse.Namespace) -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    selected_slices = sorted(df["selected_slice"].dropna().astype(str).unique().tolist())
    directions = sorted(df["direction"].dropna().astype(str).unique().tolist())
    tokens = tokens_from_reason_text(df, args.min_token_count)

    # Baselines.
    specs.append(FilterSpec(name="ALL"))
    for direction in directions:
        specs.append(FilterSpec(name=f"direction={direction}", directions=(direction,)))
    for s in selected_slices:
        specs.append(FilterSpec(name=f"slice={s}", selected_slices=(s,)))

    # Score-only filters.
    for t in args.total_score_grid:
        specs.append(FilterSpec(name=f"total_score>={t}", min_total_score=t))
    for c in args.context_score_grid:
        specs.append(FilterSpec(name=f"context_score>={c}", min_context_score=c))
    for b in args.base_score_grid:
        specs.append(FilterSpec(name=f"base_score>={b}", min_base_score=b))

    # Token-only filters.
    for token in tokens:
        specs.append(FilterSpec(name=f"token={token}", require_tokens_all=(token,)))

    # Token + scores.
    for token in tokens:
        for c in args.context_score_grid:
            specs.append(FilterSpec(name=f"token={token}|context_score>={c}", require_tokens_all=(token,), min_context_score=c))
        for t in args.total_score_grid:
            specs.append(FilterSpec(name=f"token={token}|total_score>={t}", require_tokens_all=(token,), min_total_score=t))

    # Two-token AND filters. Limit to top tokens by observed single-token usefulness later is hard here,
    # so keep only tokens with reasonable count and cap combinations.
    token_pairs = list(itertools.combinations(tokens, 2))[: args.max_token_pairs]
    for a, b in token_pairs:
        specs.append(FilterSpec(name=f"token_all={a}+{b}", require_tokens_all=(a, b)))

    # Slice + score filters.
    for s in selected_slices:
        for t in args.total_score_grid:
            specs.append(FilterSpec(name=f"slice={s}|total_score>={t}", selected_slices=(s,), min_total_score=t))
        for c in args.context_score_grid:
            specs.append(FilterSpec(name=f"slice={s}|context_score>={c}", selected_slices=(s,), min_context_score=c))

    # Direction + high-value token/score filters.
    for direction in directions:
        for token in tokens:
            specs.append(FilterSpec(name=f"direction={direction}|token={token}", directions=(direction,), require_tokens_all=(token,)))
        for c in args.context_score_grid:
            specs.append(FilterSpec(name=f"direction={direction}|context_score>={c}", directions=(direction,), min_context_score=c))

    # Known interesting guide-like filters from current diagnostics.
    known = [
        "context_retrace_to_ema_band",
        "context_pullback_to_ema_band",
        "granville_sell_3",
        "granville_buy_3",
        "base_rci9_lower_zone",
        "context_rci_turn_down",
        "base_ema_bear",
        "context_regular_bearish",
    ]
    known = [t for t in known if t in tokens]
    if known:
        specs.append(FilterSpec(name="known_any_strong_tokens", require_tokens_any=tuple(known)))
        for t in args.total_score_grid:
            specs.append(FilterSpec(name=f"known_any_strong_tokens|total_score>={t}", require_tokens_any=tuple(known), min_total_score=t))
        for c in args.context_score_grid:
            specs.append(FilterSpec(name=f"known_any_strong_tokens|context_score>={c}", require_tokens_any=tuple(known), min_context_score=c))

    # De-duplicate by serialized spec.
    uniq: dict[str, FilterSpec] = {}
    for spec in specs:
        key = json.dumps(asdict(spec), ensure_ascii=False, sort_keys=True)
        uniq[key] = spec
    return list(uniq.values())


def evaluate_specs(df: pd.DataFrame, specs: Iterable[FilterSpec], args: argparse.Namespace) -> pd.DataFrame:
    rows = []
    for spec in specs:
        g = apply_filter(df, spec)
        if len(g) < args.min_trades:
            continue
        st = stats(g)
        mo = monthly_stats(g)
        row = asdict(spec)
        row.update(st)
        row.update(mo)
        row["passes_basic"] = bool(
            st["trades"] >= args.min_trades
            and st["total_r"] >= args.min_total_r
            and st["pf"] is not None
            and st["pf"] >= args.min_pf
            and st["max_dd_r"] <= args.max_dd_r
        )
        row["passes_monthly"] = bool(
            mo["active_months"] >= args.min_active_months
            and mo["positive_month_ratio"] is not None
            and mo["positive_month_ratio"] >= args.min_positive_month_ratio
            and mo["worst_month_r"] is not None
            and mo["worst_month_r"] >= -args.max_worst_month_loss_r
        )
        row["passes_overall"] = bool(row["passes_basic"] and row["passes_monthly"])
        rows.append(row)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values(
        ["passes_overall", "pf", "total_r", "max_dd_r", "trades"],
        ascending=[False, False, False, True, False],
        na_position="last",
    )
    return out.reset_index(drop=True)


def parse_float_grid(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refine GOLD Mochipoyo RR1.2 filters.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_refined")
    p.add_argument("--min-trades", type=int, default=30)
    p.add_argument("--min-total-r", type=float, default=2.0)
    p.add_argument("--min-pf", type=float, default=1.20)
    p.add_argument("--max-dd-r", type=float, default=15.0)
    p.add_argument("--min-active-months", type=int, default=3)
    p.add_argument("--min-positive-month-ratio", type=float, default=0.50)
    p.add_argument("--max-worst-month-loss-r", type=float, default=8.0)
    p.add_argument("--min-token-count", type=int, default=20)
    p.add_argument("--max-token-pairs", type=int, default=300)
    p.add_argument("--total-score-grid", type=parse_float_grid, default="6,6.5,7,7.5,8,8.5,9,9.5,10")
    p.add_argument("--context-score-grid", type=parse_float_grid, default="3,3.5,4,4.5,5,5.5,6,6.5,7")
    p.add_argument("--base-score-grid", type=parse_float_grid, default="1,1.5,2,2.5,3,3.5,4")
    p.add_argument("--top-trades-filter-rank", type=int, default=1)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.backtest_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    df = df.sort_values("entry_time", kind="mergesort").reset_index(drop=True)

    specs = build_specs(df, args)
    leaderboard = evaluate_specs(df, specs, args)

    leaderboard_csv = prefix.with_name(prefix.name + "_leaderboard.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    best_trades_csv = prefix.with_name(prefix.name + "_best_trades.csv")
    best_month_csv = prefix.with_name(prefix.name + "_best_by_month.csv")

    leaderboard.to_csv(leaderboard_csv, index=False, encoding="utf-8-sig")

    best_record = {}
    if not leaderboard.empty:
        rank_idx = max(0, min(args.top_trades_filter_rank - 1, len(leaderboard) - 1))
        best = leaderboard.iloc[rank_idx]
        best_spec = FilterSpec(
            name=str(best["name"]),
            selected_slices=tuple(json.loads(best["selected_slices"].replace("'", '"'))) if isinstance(best["selected_slices"], str) and best["selected_slices"].startswith("[") else tuple(best["selected_slices"] if isinstance(best["selected_slices"], (list, tuple)) else ()),
            directions=tuple(json.loads(best["directions"].replace("'", '"'))) if isinstance(best["directions"], str) and best["directions"].startswith("[") else tuple(best["directions"] if isinstance(best["directions"], (list, tuple)) else ()),
            min_total_score=None if pd.isna(best.get("min_total_score")) else float(best.get("min_total_score")),
            min_context_score=None if pd.isna(best.get("min_context_score")) else float(best.get("min_context_score")),
            min_base_score=None if pd.isna(best.get("min_base_score")) else float(best.get("min_base_score")),
            require_tokens_all=tuple(json.loads(best["require_tokens_all"].replace("'", '"'))) if isinstance(best["require_tokens_all"], str) and best["require_tokens_all"].startswith("[") else tuple(best["require_tokens_all"] if isinstance(best["require_tokens_all"], (list, tuple)) else ()),
            require_tokens_any=tuple(json.loads(best["require_tokens_any"].replace("'", '"'))) if isinstance(best["require_tokens_any"], str) and best["require_tokens_any"].startswith("[") else tuple(best["require_tokens_any"] if isinstance(best["require_tokens_any"], (list, tuple)) else ()),
        )
        # Safer reconstruction: find original spec by name.
        spec_by_name = {s.name: s for s in specs}
        best_spec = spec_by_name.get(str(best["name"]), best_spec)
        best_trades = apply_filter(df, best_spec)
        best_trades.to_csv(best_trades_csv, index=False, encoding="utf-8-sig")
        month_rows = []
        for month, g in best_trades.groupby("entry_month", sort=True):
            row = {"entry_month": month}
            row.update(stats(g.sort_values("entry_time")))
            month_rows.append(row)
        best_month = pd.DataFrame(month_rows)
        best_month.to_csv(best_month_csv, index=False, encoding="utf-8-sig")
        best_record = leaderboard.head(20).where(pd.notna(leaderboard.head(20)), None).to_dict("records")
    else:
        pd.DataFrame().to_csv(best_trades_csv, index=False, encoding="utf-8-sig")
        pd.DataFrame().to_csv(best_month_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "input_trades": int(len(df)),
        "generated_specs": int(len(specs)),
        "evaluated_specs_kept": int(len(leaderboard)),
        "filters": {
            "min_trades": args.min_trades,
            "min_total_r": args.min_total_r,
            "min_pf": args.min_pf,
            "max_dd_r": args.max_dd_r,
            "min_active_months": args.min_active_months,
            "min_positive_month_ratio": args.min_positive_month_ratio,
            "max_worst_month_loss_r": args.max_worst_month_loss_r,
        },
        "files": {
            "leaderboard_csv": str(leaderboard_csv),
            "best_trades_csv": str(best_trades_csv),
            "best_month_csv": str(best_month_csv),
        },
        "top_filters": best_record,
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("refine_mochipoyo_gold_rr12_filters")
    print(f"source: {src}")
    print(f"input_trades: {len(df)}")
    print(f"generated_specs: {len(specs)}")
    print(f"evaluated_specs_kept: {len(leaderboard)}")
    print(f"leaderboard_csv: {leaderboard_csv}")
    print(f"best_trades_csv: {best_trades_csv}")
    print(f"best_month_csv: {best_month_csv}")
    print(f"summary_json: {summary_json}")
    print("top filters:")
    if leaderboard.empty:
        print("empty")
    else:
        cols = [
            "name", "trades", "win_rate_resolved", "total_r", "pf", "max_dd_r", "max_consecutive_losses",
            "active_months", "positive_month_ratio", "worst_month_r", "passes_overall",
        ]
        print(leaderboard[cols].head(20).to_string(index=False))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
