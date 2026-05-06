#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate monthly stability of selected Mochipoyo slices.

Input:
- selected trades CSV produced by extract_mochipoyo_positive_slices.py

Output:
- monthly stats CSV per selected_slice/month
- slice stability CSV with pass/fail style metrics
- optional de-duplicated portfolio CSV using one event per time window
- JSON summary

This script does not adopt signals. It only checks whether apparently positive
slices are stable enough to deserve deeper backtesting.
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
    resolved = wins + losses
    gp = float(g.loc[g["r_result"] > 0, "r_result"].sum())
    gl = float(-g.loc[g["r_result"] < 0, "r_result"].sum())
    return {
        "trades": int(len(g)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate_resolved": wins / resolved if resolved else None,
        "total_r": float(g["r_result"].sum()),
        "avg_r": float(g["r_result"].mean()) if len(g) else None,
        "pf": gp / gl if gl > 0 else None,
        "max_dd_r": max_drawdown_r(g["r_result"]),
        "max_consecutive_losses": max_consecutive_losses(g["outcome"]),
    }


def monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(["selected_slice", "entry_month"], sort=True, dropna=False):
        selected_slice, entry_month = key
        row = {"selected_slice": selected_slice, "entry_month": entry_month}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def slice_stability(month_df: pd.DataFrame, selected_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows = []
    for selected_slice, g in month_df.groupby("selected_slice", sort=True):
        trade_g = selected_df[selected_df["selected_slice"] == selected_slice].sort_values("entry_time")
        all_stats = stats(trade_g)
        active_months = int(len(g))
        positive_months = int((g["total_r"] > 0).sum())
        negative_months = int((g["total_r"] < 0).sum())
        flat_months = int((g["total_r"] == 0).sum())
        worst_month_r = float(g["total_r"].min()) if active_months else 0.0
        best_month_r = float(g["total_r"].max()) if active_months else 0.0
        median_month_r = float(g["total_r"].median()) if active_months else 0.0
        positive_month_ratio = positive_months / active_months if active_months else 0.0
        pass_basic = (
            all_stats["trades"] >= args.min_trades
            and all_stats["total_r"] >= args.min_total_r
            and (all_stats["pf"] is not None and all_stats["pf"] >= args.min_pf)
            and all_stats["max_dd_r"] <= args.max_dd_r
        )
        pass_monthly = (
            active_months >= args.min_active_months
            and positive_month_ratio >= args.min_positive_month_ratio
            and worst_month_r >= -args.max_worst_month_loss_r
        )
        row = {
            "selected_slice": selected_slice,
            **all_stats,
            "active_months": active_months,
            "positive_months": positive_months,
            "negative_months": negative_months,
            "flat_months": flat_months,
            "positive_month_ratio": positive_month_ratio,
            "worst_month_r": worst_month_r,
            "best_month_r": best_month_r,
            "median_month_r": median_month_r,
            "pass_basic": bool(pass_basic),
            "pass_monthly": bool(pass_monthly),
            "pass_overall": bool(pass_basic and pass_monthly),
        }
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["pass_overall", "total_r", "positive_month_ratio", "pf"], ascending=[False, False, False, False], na_position="last")
    return out


def dedupe_portfolio(df: pd.DataFrame, cooldown_minutes: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.sort_values(["entry_time", "total_score", "context_score", "base_score"], ascending=[True, False, False, False]).copy()
    kept_idx = []
    last_entry_by_direction: dict[str, pd.Timestamp] = {}
    for idx, row in work.iterrows():
        direction = str(row.get("direction", ""))
        t = pd.Timestamp(row["entry_time"])
        last = last_entry_by_direction.get(direction)
        if last is None or t >= last + pd.Timedelta(minutes=cooldown_minutes):
            kept_idx.append(idx)
            last_entry_by_direction[direction] = t
    return work.loc[kept_idx].sort_values("entry_time").reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate monthly stability of selected Mochipoyo slices.")
    p.add_argument("--selected-trades-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_monthly_validated")
    p.add_argument("--min-trades", type=int, default=30)
    p.add_argument("--min-total-r", type=float, default=2.0)
    p.add_argument("--min-pf", type=float, default=1.05)
    p.add_argument("--max-dd-r", type=float, default=15.0)
    p.add_argument("--min-active-months", type=int, default=3)
    p.add_argument("--min-positive-month-ratio", type=float, default=0.5)
    p.add_argument("--max-worst-month-loss-r", type=float, default=8.0)
    p.add_argument("--portfolio-cooldown-minutes", type=int, default=60)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    src = Path(args.selected_trades_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    df = df.sort_values("entry_time").reset_index(drop=True)

    m = monthly_stats(df)
    s = slice_stability(m, df, args)
    passed = s[s["pass_overall"]].copy() if len(s) else s
    passed_keys = set(passed["selected_slice"].tolist()) if len(passed) else set()
    passed_trades = df[df["selected_slice"].isin(passed_keys)].copy()
    portfolio = dedupe_portfolio(passed_trades, args.portfolio_cooldown_minutes)

    monthly_csv = prefix.with_name(prefix.name + "_by_month.csv")
    stability_csv = prefix.with_name(prefix.name + "_stability.csv")
    passed_trades_csv = prefix.with_name(prefix.name + "_passed_trades.csv")
    portfolio_csv = prefix.with_name(prefix.name + "_portfolio_deduped.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    m.to_csv(monthly_csv, index=False, encoding="utf-8-sig")
    s.to_csv(stability_csv, index=False, encoding="utf-8-sig")
    passed_trades.to_csv(passed_trades_csv, index=False, encoding="utf-8-sig")
    portfolio.to_csv(portfolio_csv, index=False, encoding="utf-8-sig")

    portfolio_stats = stats(portfolio.sort_values("entry_time")) if len(portfolio) else {}
    passed_stats = stats(passed_trades.sort_values("entry_time")) if len(passed_trades) else {}
    summary = {
        "source": str(src),
        "input_trades": int(len(df)),
        "input_slices": int(df["selected_slice"].nunique()),
        "passed_slices": int(len(passed)),
        "passed_trades": int(len(passed_trades)),
        "portfolio_trades_after_dedupe": int(len(portfolio)),
        "filters": {
            "min_trades": args.min_trades,
            "min_total_r": args.min_total_r,
            "min_pf": args.min_pf,
            "max_dd_r": args.max_dd_r,
            "min_active_months": args.min_active_months,
            "min_positive_month_ratio": args.min_positive_month_ratio,
            "max_worst_month_loss_r": args.max_worst_month_loss_r,
            "portfolio_cooldown_minutes": args.portfolio_cooldown_minutes,
        },
        "passed_stats": passed_stats,
        "portfolio_stats": portfolio_stats,
        "files": {
            "monthly_csv": str(monthly_csv),
            "stability_csv": str(stability_csv),
            "passed_trades_csv": str(passed_trades_csv),
            "portfolio_csv": str(portfolio_csv),
        },
        "passed_slices": passed.where(pd.notna(passed), None).to_dict("records") if len(passed) else [],
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("validate_mochipoyo_selected_monthly")
    print(f"source: {src}")
    print(f"input_trades: {len(df)}")
    print(f"input_slices: {df['selected_slice'].nunique()}")
    print(f"passed_slices: {len(passed)}")
    print(f"passed_trades: {len(passed_trades)}")
    print(f"portfolio_trades_after_dedupe: {len(portfolio)}")
    print(f"monthly_csv: {monthly_csv}")
    print(f"stability_csv: {stability_csv}")
    print(f"passed_trades_csv: {passed_trades_csv}")
    print(f"portfolio_csv: {portfolio_csv}")
    print(f"summary_json: {summary_json}")
    print("stability:")
    if len(s):
        print(s[["selected_slice", "trades", "total_r", "pf", "max_dd_r", "active_months", "positive_months", "positive_month_ratio", "worst_month_r", "pass_overall"]].to_string(index=False))
    else:
        print("empty")
    print("portfolio_stats:")
    print(json.dumps(portfolio_stats, ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
