#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract BTC Mochipoyo slices that are positive after spread.

BTC adoption decisions must use net_r_after_spread, not gross_r_result.
This script selects pair/rank/direction slices by net metrics and writes:
- selected trades CSV
- selected slice summary CSV
- selected slice x month CSV
- JSON summary
"""
from __future__ import annotations

import argparse
import json
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
    if "gross_r_result" in g.columns:
        gp2 = float(g.loc[g["gross_r_result"] > 0, "gross_r_result"].sum()) if len(g) else 0.0
        gl2 = float(-g.loc[g["gross_r_result"] < 0, "gross_r_result"].sum()) if len(g) else 0.0
        out["gross_total_r"] = float(g["gross_r_result"].sum()) if len(g) else 0.0
        out["gross_pf"] = gp2 / gl2 if gl2 > 0 else None
    for c in ["spread_to_sl_ratio", "effective_rr_after_spread", "gross_sl_distance_price"]:
        if c in g.columns and len(g):
            out["avg_" + c] = float(pd.to_numeric(g[c], errors="coerce").mean())
    return out


def grouped(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(keys, sort=True, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = {k: v for k, v in zip(keys, key)}
        row.update(stats(g.sort_values("entry_time")))
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["net_total_r", "net_pf", "trades"], ascending=[False, False, False], na_position="last")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Extract BTC Mochipoyo positive net slices.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/btc_selected/btc_mochipoyo_positive_net")
    p.add_argument("--min-trades", type=int, default=20)
    p.add_argument("--min-net-total-r", type=float, default=2.0)
    p.add_argument("--min-net-pf", type=float, default=1.10)
    p.add_argument("--max-net-dd-r", type=float, default=15.0)
    args = p.parse_args()

    src = Path(args.backtest_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)

    slices = grouped(df, ["pair_name", "candidate_rank", "direction"])
    selected = slices[
        (slices["trades"] >= args.min_trades)
        & (slices["net_total_r"] >= args.min_net_total_r)
        & (slices["net_pf"] >= args.min_net_pf)
        & (slices["net_max_dd_r"] <= args.max_net_dd_r)
    ].copy()
    selected["selected_slice"] = selected.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1) if len(selected) else []
    keys = set(selected["selected_slice"].tolist()) if len(selected) else set()
    trades = df[df["selected_slice"].isin(keys)].copy()
    month = grouped(trades, ["selected_slice", "entry_month"]) if len(trades) else pd.DataFrame()

    trades_csv = prefix.with_name(prefix.name + "_trades.csv")
    slices_csv = prefix.with_name(prefix.name + "_slices.csv")
    month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    trades.to_csv(trades_csv, index=False, encoding="utf-8-sig")
    selected.to_csv(slices_csv, index=False, encoding="utf-8-sig")
    month.to_csv(month_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "input_trades": int(len(df)),
        "selected_slices": int(len(selected)),
        "selected_trades": int(len(trades)),
        "filters": {
            "min_trades": args.min_trades,
            "min_net_total_r": args.min_net_total_r,
            "min_net_pf": args.min_net_pf,
            "max_net_dd_r": args.max_net_dd_r,
        },
        "files": {"trades_csv": str(trades_csv), "slices_csv": str(slices_csv), "month_csv": str(month_csv)},
        "selected_slice_records": selected.where(pd.notna(selected), None).to_dict("records"),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("extract_mochipoyo_btc_positive_net_slices")
    print(f"source: {src}")
    print(f"input_trades: {len(df)}")
    print(f"selected_slices: {len(selected)}")
    print(f"selected_trades: {len(trades)}")
    print(f"trades_csv: {trades_csv}")
    print(f"slices_csv: {slices_csv}")
    print(f"month_csv: {month_csv}")
    print(f"summary_json: {summary_json}")
    print("selected_slices:")
    if len(selected):
        print(selected[["selected_slice", "trades", "win_rate", "net_total_r", "net_pf", "net_max_dd_r", "avg_spread_to_sl_ratio", "avg_effective_rr_after_spread"]].to_string(index=False))
    else:
        print("none")
    print("done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
