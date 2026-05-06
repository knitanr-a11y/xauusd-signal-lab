#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a de-duplicated BTC Mochipoyo refined portfolio from a net-filter leaderboard.

BTC uses net_r_after_spread as the primary R column.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def max_dd(s: pd.Series) -> float:
    if s.empty:
        return 0.0
    eq = s.cumsum()
    return float((eq.cummax() - eq).max())


def max_loss_streak(outcomes: pd.Series) -> int:
    cur = best = 0
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
    resolved = wins + losses
    gp = float(g.loc[g["net_r_after_spread"] > 0, "net_r_after_spread"].sum()) if len(g) else 0.0
    gl = float(-g.loc[g["net_r_after_spread"] < 0, "net_r_after_spread"].sum()) if len(g) else 0.0
    out = {
        "trades": int(len(g)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": wins / resolved if resolved else None,
        "net_total_r": float(g["net_r_after_spread"].sum()) if len(g) else 0.0,
        "net_avg_r": float(g["net_r_after_spread"].mean()) if len(g) else None,
        "net_pf": gp / gl if gl > 0 else None,
        "net_max_dd_r": max_dd(g["net_r_after_spread"]) if len(g) else 0.0,
        "max_consecutive_losses": max_loss_streak(g["outcome"]) if len(g) else 0,
    }
    for c in ["spread_to_sl_ratio", "effective_rr_after_spread", "gross_sl_distance_price"]:
        if c in g.columns and len(g):
            out["avg_" + c] = float(pd.to_numeric(g[c], errors="coerce").mean())
    if "gross_r_result" in g.columns and len(g):
        gp2 = float(g.loc[g["gross_r_result"] > 0, "gross_r_result"].sum())
        gl2 = float(-g.loc[g["gross_r_result"] < 0, "gross_r_result"].sum())
        out["gross_total_r"] = float(g["gross_r_result"].sum())
        out["gross_pf"] = gp2 / gl2 if gl2 > 0 else None
    return out


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def apply_filter(df: pd.DataFrame, name: str) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    parts = str(name).split("|")
    if name == "ALL":
        return df.copy()
    if name.startswith("token_all="):
        token_part = parts[0].replace("token_all=", "", 1)
        for tok in token_part.split("+"):
            if tok:
                mask &= contains_token(df["reason_text"], tok)
        parts = parts[1:]
    for part in parts:
        if not part:
            continue
        if part.startswith("direction="):
            mask &= df["direction"].astype(str) == part.replace("direction=", "", 1)
        elif part.startswith("token="):
            mask &= contains_token(df["reason_text"], part.replace("token=", "", 1))
        elif part.startswith("total_score>="):
            mask &= pd.to_numeric(df["total_score"], errors="coerce") >= float(part.replace("total_score>=", "", 1))
        elif part.startswith("context_score>="):
            mask &= pd.to_numeric(df["context_score"], errors="coerce") >= float(part.replace("context_score>=", "", 1))
        elif part.startswith("base_score>="):
            mask &= pd.to_numeric(df["base_score"], errors="coerce") >= float(part.replace("base_score>=", "", 1))
        elif part.startswith("spread_to_sl<="):
            mask &= pd.to_numeric(df["spread_to_sl_ratio"], errors="coerce") <= float(part.replace("spread_to_sl<=", "", 1))
        elif part.startswith("effective_rr>="):
            mask &= pd.to_numeric(df["effective_rr_after_spread"], errors="coerce") >= float(part.replace("effective_rr>=", "", 1))
        else:
            return df.iloc[0:0].copy()
    return df[mask].sort_values("entry_time", kind="mergesort").copy()


def identity_cols(df: pd.DataFrame) -> list[str]:
    cols = ["entry_time", "pair_name", "candidate_rank", "direction", "entry_price", "base_time", "signal_time"]
    return [c for c in cols if c in df.columns]


def dedupe_exact(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    cols = identity_cols(df)
    return df.drop_duplicates(subset=cols, keep="first").sort_values("entry_time").reset_index(drop=True)


def cooldown(df: pd.DataFrame, minutes: int, by_direction: bool) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    sort_cols = ["entry_time", "source_filter_rank", "net_pf_filter", "net_total_r_filter", "total_score"]
    sort_cols = [c for c in sort_cols if c in df.columns]
    ascending = [True, True, False, False, False][:len(sort_cols)]
    work = df.sort_values(sort_cols, ascending=ascending).copy()
    kept = []
    last_by_key: dict[str, pd.Timestamp] = {}
    for idx, row in work.iterrows():
        key = str(row.get("direction", "ALL")) if by_direction else "ALL"
        t = pd.Timestamp(row["entry_time"])
        last = last_by_key.get(key)
        if last is None or t >= last + pd.Timedelta(minutes=minutes):
            kept.append(idx)
            last_by_key[key] = t
    return work.loc[kept].sort_values("entry_time").reset_index(drop=True)


def grouped(df: pd.DataFrame, key: str) -> pd.DataFrame:
    rows = []
    for v, g in df.groupby(key, sort=True, dropna=False):
        row = {key: v}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Build BTC Mochipoyo net refined portfolio.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--leaderboard-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/btc_selected/btc_mochipoyo_net_refined_portfolio")
    p.add_argument("--min-filter-trades", type=int, default=20)
    p.add_argument("--min-filter-net-pf", type=float, default=1.80)
    p.add_argument("--min-filter-net-total-r", type=float, default=5.0)
    p.add_argument("--max-filter-net-dd-r", type=float, default=4.0)
    p.add_argument("--max-filters", type=int, default=20)
    p.add_argument("--portfolio-cooldown-minutes", type=int, default=60)
    p.add_argument("--cooldown-by-direction", action="store_true", default=True)
    p.add_argument("--no-cooldown-by-direction", dest="cooldown_by_direction", action="store_false")
    args = p.parse_args()

    df = pd.read_csv(args.backtest_csv, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)

    lb = pd.read_csv(args.leaderboard_csv, encoding="utf-8-sig")
    lb = lb[(lb["trades"] >= args.min_filter_trades) & (lb["net_pf"] >= args.min_filter_net_pf) & (lb["net_total_r"] >= args.min_filter_net_total_r) & (lb["net_max_dd_r"] <= args.max_filter_net_dd_r)].copy()
    lb = lb.sort_values(["net_pf", "net_total_r", "net_max_dd_r", "trades"], ascending=[False, False, True, False]).head(args.max_filters).reset_index(drop=True)

    parts = []
    coverage = []
    for i, row in lb.iterrows():
        name = str(row["name"])
        g = apply_filter(df, name)
        if g.empty:
            continue
        g = g.copy()
        g["source_filter_rank"] = int(i + 1)
        g["source_filter_name"] = name
        g["net_pf_filter"] = float(row["net_pf"])
        g["net_total_r_filter"] = float(row["net_total_r"])
        parts.append(g)
        cov = {"source_filter_rank": int(i + 1), "source_filter_name": name}
        cov.update(stats(g.sort_values("entry_time")))
        coverage.append(cov)

    union = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    exact = dedupe_exact(union)
    port = cooldown(exact, args.portfolio_cooldown_minutes, args.cooldown_by_direction)

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    selected_filters_csv = prefix.with_name(prefix.name + "_selected_filters.csv")
    union_csv = prefix.with_name(prefix.name + "_union_exact_deduped.csv")
    portfolio_csv = prefix.with_name(prefix.name + "_portfolio.csv")
    month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    coverage_csv = prefix.with_name(prefix.name + "_filter_coverage.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    lb.to_csv(selected_filters_csv, index=False, encoding="utf-8-sig")
    exact.to_csv(union_csv, index=False, encoding="utf-8-sig")
    port.to_csv(portfolio_csv, index=False, encoding="utf-8-sig")
    grouped(port, "entry_month").to_csv(month_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage).to_csv(coverage_csv, index=False, encoding="utf-8-sig")

    summary = {
        "input_trades": int(len(df)),
        "selected_filters": int(len(lb)),
        "union_rows_before_exact_dedupe": int(len(union)),
        "union_rows_after_exact_dedupe": int(len(exact)),
        "portfolio_rows_after_cooldown": int(len(port)),
        "portfolio_stats": stats(port.sort_values("entry_time")),
        "files": {
            "selected_filters_csv": str(selected_filters_csv),
            "union_csv": str(union_csv),
            "portfolio_csv": str(portfolio_csv),
            "month_csv": str(month_csv),
            "coverage_csv": str(coverage_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("build_mochipoyo_btc_net_refined_portfolio")
    print(f"input_trades: {len(df)}")
    print(f"selected_filters: {len(lb)}")
    print(f"union_rows_before_exact_dedupe: {len(union)}")
    print(f"union_rows_after_exact_dedupe: {len(exact)}")
    print(f"portfolio_rows_after_cooldown: {len(port)}")
    print(f"selected_filters_csv: {selected_filters_csv}")
    print(f"union_csv: {union_csv}")
    print(f"portfolio_csv: {portfolio_csv}")
    print(f"month_csv: {month_csv}")
    print(f"coverage_csv: {coverage_csv}")
    print(f"summary_json: {summary_json}")
    print("portfolio_stats:")
    print(json.dumps(summary["portfolio_stats"], ensure_ascii=False, indent=2))
    print("done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
