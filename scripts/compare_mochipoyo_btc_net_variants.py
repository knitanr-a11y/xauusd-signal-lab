#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare BTC Mochipoyo net post-filter variants.

Input is the fixed-preset final BTC portfolio CSV.
BTC decisions use net_r_after_spread only. Gross metrics are reference only.

Variants:
- baseline
- no_buy_2_like
- no_granville_2_like
- granville_3_only
- spread_to_sl_lte_007
- spread_to_sl_lte_006
- no_buy_2_like_and_spread_lte_007
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

GRANVILLE_3 = {"BUY_3", "SELL_3"}


def max_dd(s: pd.Series) -> float:
    if s.empty:
        return 0.0
    eq = s.cumsum()
    return float((eq.cummax() - eq).max())


def max_loss_streak(outcomes: pd.Series) -> int:
    cur = 0
    best = 0
    for x in outcomes.astype(str):
        if x == "LOSS":
            cur += 1
            best = max(best, cur)
        elif x == "WIN":
            cur = 0
    return best


def calc(g: pd.DataFrame) -> dict:
    wins = int((g["outcome"] == "WIN").sum()) if len(g) else 0
    losses = int((g["outcome"] == "LOSS").sum()) if len(g) else 0
    timeouts = int((g["outcome"] == "TIMEOUT").sum()) if len(g) else 0
    no_data = int((g["outcome"] == "NO_DATA").sum()) if len(g) else 0
    resolved = wins + losses
    gp = float(g.loc[g["net_r_after_spread"] > 0, "net_r_after_spread"].sum()) if len(g) else 0.0
    gl = float(-g.loc[g["net_r_after_spread"] < 0, "net_r_after_spread"].sum()) if len(g) else 0.0
    out = {
        "trades": int(len(g)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "no_data": no_data,
        "win_rate": wins / resolved if resolved else None,
        "net_total_r": float(g["net_r_after_spread"].sum()) if len(g) else 0.0,
        "net_avg_r": float(g["net_r_after_spread"].mean()) if len(g) else None,
        "net_pf": gp / gl if gl > 0 else None,
        "net_max_dd_r": max_dd(g["net_r_after_spread"]) if len(g) else 0.0,
        "max_consecutive_losses": max_loss_streak(g["outcome"]) if len(g) else 0,
    }
    for col in ["spread_to_sl_ratio", "effective_rr_after_spread", "gross_sl_distance_price", "gross_tp_distance_price"]:
        if col in g.columns and len(g):
            out["avg_" + col] = float(pd.to_numeric(g[col], errors="coerce").mean())
    if "gross_r_result" in g.columns and len(g):
        gp2 = float(g.loc[g["gross_r_result"] > 0, "gross_r_result"].sum())
        gl2 = float(-g.loc[g["gross_r_result"] < 0, "gross_r_result"].sum())
        out["gross_total_r"] = float(g["gross_r_result"].sum())
        out["gross_pf"] = gp2 / gl2 if gl2 > 0 else None
    return out


def monthly_stats(df: pd.DataFrame, variant: str) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for month, g in df.groupby("entry_month", sort=True):
        row = {"variant": variant, "entry_month": month}
        row.update(calc(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def grouped(df: pd.DataFrame, variant: str, key: str) -> pd.DataFrame:
    rows = []
    if df.empty or key not in df.columns:
        return pd.DataFrame()
    for v, g in df.groupby(key, sort=True, dropna=False):
        row = {"variant": variant, key: v}
        row.update(calc(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out = out.dropna(subset=["entry_time"]).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    out["entry_month"] = out["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in out.columns:
        out["selected_slice"] = out.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    for col in ["direction", "context_granville_type", "reason_text"]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str)
    if "spread_to_sl_ratio" not in out.columns:
        out["spread_to_sl_ratio"] = pd.NA
    out["spread_to_sl_ratio"] = pd.to_numeric(out["spread_to_sl_ratio"], errors="coerce")
    return out


def contains_token(df: pd.DataFrame, token: str) -> pd.Series:
    return df["reason_text"].fillna("").astype(str).str.contains(token, regex=False)


def build_variants(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    buy_2_like = (df["direction"] == "BUY") & contains_token(df, "granville_buy_2_like")
    any_2_like = contains_token(df, "granville_buy_2_like") | contains_token(df, "granville_sell_2_like")
    g3_only = df["context_granville_type"].isin(GRANVILLE_3)
    spread_lte_007 = df["spread_to_sl_ratio"] <= 0.07
    spread_lte_006 = df["spread_to_sl_ratio"] <= 0.06

    return {
        "baseline": df.copy(),
        "no_buy_2_like": df[~buy_2_like].copy(),
        "no_granville_2_like": df[~any_2_like].copy(),
        "granville_3_only": df[g3_only].copy(),
        "spread_to_sl_lte_007": df[spread_lte_007].copy(),
        "spread_to_sl_lte_006": df[spread_lte_006].copy(),
        "no_buy_2_like_and_spread_lte_007": df[(~buy_2_like) & spread_lte_007].copy(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Compare BTC Mochipoyo net variants.")
    p.add_argument("--portfolio-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/btc_selected/btc_mochipoyo_net_variant_compare")
    args = p.parse_args()

    src = Path(args.portfolio_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = ensure_columns(pd.read_csv(src, encoding="utf-8-sig"))
    variants = build_variants(df)

    overall_rows = []
    month_parts = []
    slice_parts = []
    direction_parts = []
    output_files = {}

    for name, g in variants.items():
        g = g.sort_values("entry_time", kind="mergesort").reset_index(drop=True)
        row = {"variant": name}
        row.update(calc(g))
        row["dropped_vs_baseline"] = int(len(df) - len(g))
        overall_rows.append(row)
        month_parts.append(monthly_stats(g, name))
        slice_parts.append(grouped(g, name, "selected_slice"))
        direction_parts.append(grouped(g, name, "direction"))
        out_csv = prefix.with_name(prefix.name + f"_{name}.csv")
        g.to_csv(out_csv, index=False, encoding="utf-8-sig")
        output_files[name] = str(out_csv)

    overall = pd.DataFrame(overall_rows).sort_values(
        ["net_pf", "net_total_r", "net_max_dd_r", "trades"],
        ascending=[False, False, True, False],
        na_position="last",
    )
    months = pd.concat([x for x in month_parts if not x.empty], ignore_index=True) if month_parts else pd.DataFrame()
    slices = pd.concat([x for x in slice_parts if not x.empty], ignore_index=True) if slice_parts else pd.DataFrame()
    directions = pd.concat([x for x in direction_parts if not x.empty], ignore_index=True) if direction_parts else pd.DataFrame()

    overall_csv = prefix.with_name(prefix.name + "_overall.csv")
    months_csv = prefix.with_name(prefix.name + "_by_month.csv")
    slices_csv = prefix.with_name(prefix.name + "_by_slice.csv")
    directions_csv = prefix.with_name(prefix.name + "_by_direction.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    overall.to_csv(overall_csv, index=False, encoding="utf-8-sig")
    months.to_csv(months_csv, index=False, encoding="utf-8-sig")
    slices.to_csv(slices_csv, index=False, encoding="utf-8-sig")
    directions.to_csv(directions_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "baseline_rows": int(len(df)),
        "files": {
            "overall_csv": str(overall_csv),
            "months_csv": str(months_csv),
            "slices_csv": str(slices_csv),
            "directions_csv": str(directions_csv),
            "variant_csvs": output_files,
        },
        "overall": overall.where(pd.notna(overall), None).to_dict("records"),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("compare_mochipoyo_btc_net_variants")
    print(f"source: {src}")
    print(f"baseline_rows: {len(df)}")
    print(f"overall_csv: {overall_csv}")
    print(f"months_csv: {months_csv}")
    print(f"slices_csv: {slices_csv}")
    print(f"directions_csv: {directions_csv}")
    print(f"summary_json: {summary_json}")
    print("overall:")
    cols = [
        "variant", "trades", "win_rate", "net_total_r", "net_pf", "net_max_dd_r",
        "max_consecutive_losses", "avg_spread_to_sl_ratio", "avg_effective_rr_after_spread", "dropped_vs_baseline",
    ]
    print(overall[cols].to_string(index=False))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
