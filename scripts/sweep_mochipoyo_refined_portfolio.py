#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sweep refined Mochipoyo portfolio builder settings.

Purpose:
The refined leaderboard can look very strong if only one exact filter setting is used.
This script checks robustness by sweeping:
- min filter PF
- min filter total R
- max filter DD
- max number of filters
- portfolio cooldown minutes

It reconstructs filters from the leaderboard using the same supported patterns as
build_mochipoyo_refined_portfolio.py, unions matching trades, exact-dedupes, applies
cooldown, and reports each portfolio's performance.

This script does not adopt signals. It only produces robustness diagnostics.
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


def monthly_stability(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "active_months": 0,
            "positive_months": 0,
            "positive_month_ratio": None,
            "worst_month_r": None,
            "best_month_r": None,
            "median_month_r": None,
        }
    g = df.groupby("entry_month")["r_result"].sum()
    active = int(len(g))
    positive = int((g > 0).sum())
    return {
        "active_months": active,
        "positive_months": positive,
        "positive_month_ratio": positive / active if active else None,
        "worst_month_r": float(g.min()) if active else None,
        "best_month_r": float(g.max()) if active else None,
        "median_month_r": float(g.median()) if active else None,
    }


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def apply_name_filter(df: pd.DataFrame, name: str) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    parts = str(name).split("|")
    if name == "ALL":
        return df.copy()

    if name.startswith("slice="):
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
        parts = parts

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
            return df.iloc[0:0].copy()
        else:
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


def cooldown_portfolio(df: pd.DataFrame, cooldown_minutes: int, by_direction: bool = True) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    sort_cols = ["entry_time", "pf_filter", "total_r_filter", "total_score", "context_score", "base_score"]
    sort_cols = [c for c in sort_cols if c in df.columns]
    ascending = [True] + [False] * (len(sort_cols) - 1)
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


def build_portfolio(df: pd.DataFrame, lb: pd.DataFrame, max_filters: int, cooldown_minutes: int) -> tuple[pd.DataFrame, int, int, int]:
    selected = lb.head(max_filters).copy()
    parts = []
    for rank, row in selected.iterrows():
        g = apply_name_filter(df, str(row["name"]))
        if g.empty:
            continue
        g = g.copy()
        g["source_filter_name"] = str(row["name"])
        g["source_filter_rank"] = int(rank + 1)
        g["pf_filter"] = float(row["pf"])
        g["total_r_filter"] = float(row["total_r"])
        parts.append(g)
    union = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    exact = dedupe_exact(union)
    port = cooldown_portfolio(exact, cooldown_minutes, by_direction=True)
    return port, int(len(union)), int(len(exact)), int(len(selected))


def parse_float_list(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def parse_int_list(text: str) -> list[int]:
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sweep refined Mochipoyo portfolio robustness.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--leaderboard-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_refined_sweep")
    p.add_argument("--min-filter-trades", type=int, default=30)
    p.add_argument("--min-filter-pf-grid", type=parse_float_list, default="1.2,1.3,1.4,1.5,1.6,1.8,2.0")
    p.add_argument("--min-filter-total-r-grid", type=parse_float_list, default="6,8,10,12,14")
    p.add_argument("--max-filter-dd-r-grid", type=parse_float_list, default="4,6,8,10")
    p.add_argument("--max-filters-grid", type=parse_int_list, default="5,10,15,20,30")
    p.add_argument("--cooldown-minutes-grid", type=parse_int_list, default="30,60,120,240")
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

    raw_lb = pd.read_csv(leaderboard_path, encoding="utf-8-sig")
    rows = []
    best_portfolio = pd.DataFrame()
    best_key = None
    best_score_tuple = None

    for min_pf in args.min_filter_pf_grid:
        for min_total_r in args.min_filter_total_r_grid:
            for max_dd in args.max_filter_dd_r_grid:
                lb = raw_lb[
                    (raw_lb["trades"] >= args.min_filter_trades)
                    & (raw_lb["pf"] >= min_pf)
                    & (raw_lb["total_r"] >= min_total_r)
                    & (raw_lb["max_dd_r"] <= max_dd)
                ].copy()
                if lb.empty:
                    continue
                lb = lb.sort_values(["pf", "total_r", "max_dd_r", "trades"], ascending=[False, False, True, False]).reset_index(drop=True)
                for max_filters in args.max_filters_grid:
                    for cooldown in args.cooldown_minutes_grid:
                        port, union_before, union_after, selected_filters = build_portfolio(df, lb, max_filters, cooldown)
                        st = stats(port)
                        mo = monthly_stability(port)
                        row = {
                            "min_filter_pf": min_pf,
                            "min_filter_total_r": min_total_r,
                            "max_filter_dd_r": max_dd,
                            "max_filters": max_filters,
                            "cooldown_minutes": cooldown,
                            "available_filters": int(len(lb)),
                            "selected_filters": selected_filters,
                            "union_rows_before_exact_dedupe": union_before,
                            "union_rows_after_exact_dedupe": union_after,
                        }
                        row.update(st)
                        row.update(mo)
                        rows.append(row)
                        score_tuple = (
                            st["pf"] or 0.0,
                            st["total_r"],
                            -(st["max_dd_r"]),
                            st["trades"],
                        )
                        if best_score_tuple is None or score_tuple > best_score_tuple:
                            best_score_tuple = score_tuple
                            best_key = row.copy()
                            best_portfolio = port.copy()

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["pf", "total_r", "max_dd_r", "trades"], ascending=[False, False, True, False], na_position="last")

    sweep_csv = prefix.with_name(prefix.name + "_leaderboard.csv")
    best_portfolio_csv = prefix.with_name(prefix.name + "_best_portfolio.csv")
    best_month_csv = prefix.with_name(prefix.name + "_best_by_month.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    result.to_csv(sweep_csv, index=False, encoding="utf-8-sig")
    best_portfolio.to_csv(best_portfolio_csv, index=False, encoding="utf-8-sig")
    monthly_stability_df = pd.DataFrame()
    if not best_portfolio.empty:
        month_rows = []
        for month, g in best_portfolio.groupby("entry_month", sort=True):
            r = {"entry_month": month}
            r.update(stats(g.sort_values("entry_time")))
            month_rows.append(r)
        monthly_stability_df = pd.DataFrame(month_rows)
    monthly_stability_df.to_csv(best_month_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source_backtest_csv": str(src),
        "source_leaderboard_csv": str(leaderboard_path),
        "input_trades": int(len(df)),
        "sweep_rows": int(len(result)),
        "best_settings_and_stats": best_key,
        "files": {
            "sweep_csv": str(sweep_csv),
            "best_portfolio_csv": str(best_portfolio_csv),
            "best_month_csv": str(best_month_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("sweep_mochipoyo_refined_portfolio")
    print(f"input_trades: {len(df)}")
    print(f"sweep_rows: {len(result)}")
    print(f"sweep_csv: {sweep_csv}")
    print(f"best_portfolio_csv: {best_portfolio_csv}")
    print(f"best_month_csv: {best_month_csv}")
    print(f"summary_json: {summary_json}")
    print("top sweep results:")
    if result.empty:
        print("empty")
    else:
        cols = [
            "min_filter_pf", "min_filter_total_r", "max_filter_dd_r", "max_filters", "cooldown_minutes",
            "trades", "win_rate_resolved", "total_r", "pf", "max_dd_r", "max_consecutive_losses",
            "active_months", "positive_month_ratio", "worst_month_r",
        ]
        print(result[cols].head(20).to_string(index=False))
    print("best_settings_and_stats:")
    print(json.dumps(best_key, ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
