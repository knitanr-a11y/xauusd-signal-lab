#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate monthly stability of BTC Mochipoyo positive net slices.

BTC metrics are based on net_r_after_spread. Gross metrics are reference only.
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
    return pd.DataFrame(rows)


def stability(month_df: pd.DataFrame, trades: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows = []
    for selected_slice, m in month_df.groupby("selected_slice", sort=True):
        g = trades[trades["selected_slice"] == selected_slice].sort_values("entry_time")
        s = stats(g)
        active = int(len(m))
        pos = int((m["net_total_r"] > 0).sum())
        neg = int((m["net_total_r"] < 0).sum())
        worst = float(m["net_total_r"].min()) if active else 0.0
        best = float(m["net_total_r"].max()) if active else 0.0
        ratio = pos / active if active else 0.0
        pass_basic = (
            s["trades"] >= args.min_trades
            and s["net_total_r"] >= args.min_net_total_r
            and s["net_pf"] is not None
            and s["net_pf"] >= args.min_net_pf
            and s["net_max_dd_r"] <= args.max_net_dd_r
        )
        pass_monthly = (
            active >= args.min_active_months
            and ratio >= args.min_positive_month_ratio
            and worst >= -args.max_worst_month_loss_r
        )
        row = {
            "selected_slice": selected_slice,
            **s,
            "active_months": active,
            "positive_months": pos,
            "negative_months": neg,
            "positive_month_ratio": ratio,
            "worst_month_net_r": worst,
            "best_month_net_r": best,
            "pass_basic": bool(pass_basic),
            "pass_monthly": bool(pass_monthly),
            "pass_overall": bool(pass_basic and pass_monthly),
        }
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["pass_overall", "net_total_r", "net_pf"], ascending=[False, False, False], na_position="last")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Validate monthly stability of BTC positive net Mochipoyo slices.")
    p.add_argument("--selected-trades-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/btc_selected/btc_mochipoyo_positive_net_monthly_validated")
    p.add_argument("--min-trades", type=int, default=20)
    p.add_argument("--min-net-total-r", type=float, default=2.0)
    p.add_argument("--min-net-pf", type=float, default=1.10)
    p.add_argument("--max-net-dd-r", type=float, default=15.0)
    p.add_argument("--min-active-months", type=int, default=3)
    p.add_argument("--min-positive-month-ratio", type=float, default=0.50)
    p.add_argument("--max-worst-month-loss-r", type=float, default=8.0)
    args = p.parse_args()

    src = Path(args.selected_trades_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)

    month = grouped(df, ["selected_slice", "entry_month"])
    stab = stability(month, df, args)
    passed = stab[stab["pass_overall"]].copy() if len(stab) else stab
    passed_keys = set(passed["selected_slice"].tolist()) if len(passed) else set()
    passed_trades = df[df["selected_slice"].isin(passed_keys)].copy()

    month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    stability_csv = prefix.with_name(prefix.name + "_stability.csv")
    passed_trades_csv = prefix.with_name(prefix.name + "_passed_trades.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    month.to_csv(month_csv, index=False, encoding="utf-8-sig")
    stab.to_csv(stability_csv, index=False, encoding="utf-8-sig")
    passed_trades.to_csv(passed_trades_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "input_trades": int(len(df)),
        "input_slices": int(df["selected_slice"].nunique()),
        "passed_slices": int(len(passed)),
        "passed_trades": int(len(passed_trades)),
        "passed_stats": stats(passed_trades.sort_values("entry_time")) if len(passed_trades) else {},
        "files": {
            "month_csv": str(month_csv),
            "stability_csv": str(stability_csv),
            "passed_trades_csv": str(passed_trades_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("validate_mochipoyo_btc_positive_net_monthly")
    print(f"source: {src}")
    print(f"input_trades: {len(df)}")
    print(f"input_slices: {df['selected_slice'].nunique()}")
    print(f"passed_slices: {len(passed)}")
    print(f"passed_trades: {len(passed_trades)}")
    print(f"month_csv: {month_csv}")
    print(f"stability_csv: {stability_csv}")
    print(f"passed_trades_csv: {passed_trades_csv}")
    print(f"summary_json: {summary_json}")
    print("stability:")
    if len(stab):
        cols = ["selected_slice", "trades", "net_total_r", "net_pf", "net_max_dd_r", "active_months", "positive_months", "positive_month_ratio", "worst_month_net_r", "pass_overall"]
        print(stab[cols].to_string(index=False))
    else:
        print("empty")
    print("passed_stats:")
    print(json.dumps(summary["passed_stats"], ensure_ascii=False, indent=2))
    print("done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
