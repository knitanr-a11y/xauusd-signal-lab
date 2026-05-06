#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare post-filter variants for GOLD_MOCHIPOYO_RR12_REFINED.

This script starts from the fixed-preset final portfolio CSV and compares small,
interpretable variants found during manual review.

Variants:
- baseline
- base_ema_aligned
- granville_3_only
- no_granville_2_like
- base_ema_aligned_and_granville_3_only
- base_ema_aligned_and_no_granville_2_like

It does not change source trades. It writes filtered portfolio CSVs, overall
leaderboard, and month-by-variant stats.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


GRANVILLE_3 = {"BUY_3", "SELL_3"}
GRANVILLE_2_TOKENS = ["granville_buy_2_like", "granville_sell_2_like"]


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
    no_data = int((g["outcome"] == "NO_DATA").sum()) if "outcome" in g.columns and len(g) else 0
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


def monthly_stats(df: pd.DataFrame, variant: str) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for month, g in df.groupby("entry_month", sort=True):
        row = {"variant": variant, "entry_month": month}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out = out.dropna(subset=["entry_time"]).sort_values("entry_time", kind="mergesort").reset_index(drop=True)
    out["entry_month"] = out["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in out.columns:
        out["selected_slice"] = out.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    for col in ["direction", "base_ema_order", "context_granville_type", "reason_text"]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].fillna("").astype(str)
    return out


def mask_base_ema_aligned(df: pd.DataFrame) -> pd.Series:
    # Avoid SELL when lower timeframe EMA is still BULL.
    # Avoid BUY when lower timeframe EMA is still BEAR.
    return ~(
        ((df["direction"] == "SELL") & (df["base_ema_order"] == "BULL"))
        | ((df["direction"] == "BUY") & (df["base_ema_order"] == "BEAR"))
    )


def mask_granville_3_only(df: pd.DataFrame) -> pd.Series:
    return df["context_granville_type"].isin(GRANVILLE_3)


def mask_no_granville_2_like(df: pd.DataFrame) -> pd.Series:
    text = df["reason_text"].fillna("").astype(str)
    mask = pd.Series(True, index=df.index)
    for token in GRANVILLE_2_TOKENS:
        mask &= ~text.str.contains(token, regex=False)
    return mask


def build_variants(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    m_base = mask_base_ema_aligned(df)
    m_g3 = mask_granville_3_only(df)
    m_no_g2 = mask_no_granville_2_like(df)
    return {
        "baseline": df.copy(),
        "base_ema_aligned": df[m_base].copy(),
        "granville_3_only": df[m_g3].copy(),
        "no_granville_2_like": df[m_no_g2].copy(),
        "base_ema_aligned_and_granville_3_only": df[m_base & m_g3].copy(),
        "base_ema_aligned_and_no_granville_2_like": df[m_base & m_no_g2].copy(),
    }


def grouped(df: pd.DataFrame, variant: str, key: str) -> pd.DataFrame:
    rows = []
    for v, g in df.groupby(key, sort=True, dropna=False):
        row = {"variant": variant, key: v}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Compare Mochipoyo post-filter variants.")
    p.add_argument("--portfolio-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_variant_compare")
    args = p.parse_args()

    src = Path(args.portfolio_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = ensure_columns(pd.read_csv(src, encoding="utf-8-sig"))
    variants = build_variants(df)

    overall_rows = []
    month_parts = []
    pair_parts = []
    slice_parts = []
    output_files = {}

    for name, g in variants.items():
        g = g.sort_values("entry_time", kind="mergesort").reset_index(drop=True)
        row = {"variant": name}
        row.update(stats(g))
        row["dropped_vs_baseline"] = int(len(df) - len(g))
        overall_rows.append(row)
        month_parts.append(monthly_stats(g, name))
        if not g.empty:
            pair_parts.append(grouped(g, name, "pair_name"))
            slice_parts.append(grouped(g, name, "selected_slice"))
        out_csv = prefix.with_name(prefix.name + f"_{name}.csv")
        g.to_csv(out_csv, index=False, encoding="utf-8-sig")
        output_files[name] = str(out_csv)

    overall = pd.DataFrame(overall_rows).sort_values(["pf", "total_r", "max_dd_r", "trades"], ascending=[False, False, True, False], na_position="last")
    months = pd.concat(month_parts, ignore_index=True) if month_parts else pd.DataFrame()
    pairs = pd.concat(pair_parts, ignore_index=True) if pair_parts else pd.DataFrame()
    slices = pd.concat(slice_parts, ignore_index=True) if slice_parts else pd.DataFrame()

    overall_csv = prefix.with_name(prefix.name + "_overall.csv")
    months_csv = prefix.with_name(prefix.name + "_by_month.csv")
    pairs_csv = prefix.with_name(prefix.name + "_by_pair.csv")
    slices_csv = prefix.with_name(prefix.name + "_by_slice.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    overall.to_csv(overall_csv, index=False, encoding="utf-8-sig")
    months.to_csv(months_csv, index=False, encoding="utf-8-sig")
    pairs.to_csv(pairs_csv, index=False, encoding="utf-8-sig")
    slices.to_csv(slices_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "baseline_rows": int(len(df)),
        "files": {
            "overall_csv": str(overall_csv),
            "months_csv": str(months_csv),
            "pairs_csv": str(pairs_csv),
            "slices_csv": str(slices_csv),
            "variant_csvs": output_files,
        },
        "overall": overall.where(pd.notna(overall), None).to_dict("records"),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("compare_mochipoyo_filter_variants")
    print(f"source: {src}")
    print(f"baseline_rows: {len(df)}")
    print(f"overall_csv: {overall_csv}")
    print(f"months_csv: {months_csv}")
    print(f"pairs_csv: {pairs_csv}")
    print(f"slices_csv: {slices_csv}")
    print(f"summary_json: {summary_json}")
    print("overall:")
    cols = ["variant", "trades", "win_rate_resolved", "total_r", "pf", "max_dd_r", "max_consecutive_losses", "dropped_vs_baseline"]
    print(overall[cols].to_string(index=False))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
