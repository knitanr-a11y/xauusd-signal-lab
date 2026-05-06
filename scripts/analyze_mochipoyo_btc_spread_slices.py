#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze BTC Mochipoyo spread-aware backtest slices.

Primary metric is net_r_after_spread. Gross is reference only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
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


def calc(g: pd.DataFrame, r_col: str = "net_r_after_spread") -> dict:
    wins = int((g["outcome"] == "WIN").sum())
    losses = int((g["outcome"] == "LOSS").sum())
    timeouts = int((g["outcome"] == "TIMEOUT").sum())
    no_data = int((g["outcome"] == "NO_DATA").sum())
    resolved = wins + losses
    gp = float(g.loc[g[r_col] > 0, r_col].sum()) if len(g) else 0.0
    gl = float(-g.loc[g[r_col] < 0, r_col].sum()) if len(g) else 0.0
    out = {
        "trades": int(len(g)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "no_data": no_data,
        "win_rate": wins / resolved if resolved else None,
        "net_total_r": float(g[r_col].sum()) if len(g) else 0.0,
        "net_avg_r": float(g[r_col].mean()) if len(g) else None,
        "net_pf": gp / gl if gl > 0 else None,
        "net_max_dd_r": max_dd(g[r_col]) if len(g) else 0.0,
        "max_consecutive_losses": max_loss_streak(g["outcome"]) if len(g) else 0,
    }
    if "gross_r_result" in g.columns:
        gp2 = float(g.loc[g["gross_r_result"] > 0, "gross_r_result"].sum()) if len(g) else 0.0
        gl2 = float(-g.loc[g["gross_r_result"] < 0, "gross_r_result"].sum()) if len(g) else 0.0
        out["gross_total_r"] = float(g["gross_r_result"].sum()) if len(g) else 0.0
        out["gross_pf"] = gp2 / gl2 if gl2 > 0 else None
    for c in ["spread_to_sl_ratio", "spread_to_tp_ratio", "effective_rr_after_spread", "gross_sl_distance_price", "gross_tp_distance_price"]:
        if c in g.columns and len(g):
            out["avg_" + c] = float(pd.to_numeric(g[c], errors="coerce").replace([np.inf, -np.inf], np.nan).mean())
    return out


def grouped(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(keys, sort=True, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = {k: v for k, v in zip(keys, key)}
        row.update(calc(g.sort_values("entry_time")))
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["net_total_r", "net_pf", "trades"], ascending=[False, False, False], na_position="last")
    return out


def reason_tokens(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    if "reason_text" not in df.columns:
        return pd.DataFrame()
    tokens = set()
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
            row.update(calc(g.sort_values("entry_time")))
            rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["net_total_r", "net_pf", "trades"], ascending=[False, False, False], na_position="last")
    return out


def score_thresholds(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
    rows = []
    grids = {"total_score": [6,7,8,9,10,11,12], "context_score": [3,4,5,6,7,8], "base_score": [1,2,3,4,5]}
    for col, vals in grids.items():
        if col not in df.columns:
            continue
        for v in vals:
            g = df[pd.to_numeric(df[col], errors="coerce") >= v]
            if len(g) >= min_trades:
                row = {"filter": f"{col}>={v}", "score_col": col, "threshold": v}
                row.update(calc(g.sort_values("entry_time")))
                rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["net_total_r", "net_pf", "trades"], ascending=[False, False, False], na_position="last")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--output-dir", default="data/results/mochipoyo/btc_analysis")
    p.add_argument("--min-trades", type=int, default=20)
    args = p.parse_args()

    src = Path(args.backtest_csv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)

    stem = src.stem
    tables = {
        "overall": pd.DataFrame([calc(df)]),
        "by_pair": grouped(df, ["pair_name"]),
        "by_rank": grouped(df, ["candidate_rank"]),
        "by_direction": grouped(df, ["direction"]),
        "by_pair_rank_direction": grouped(df, ["pair_name", "candidate_rank", "direction"]),
        "by_month": grouped(df, ["entry_month"]),
        "by_pair_month": grouped(df, ["pair_name", "entry_month"]),
        "reason_tokens": reason_tokens(df, args.min_trades),
        "score_thresholds": score_thresholds(df, args.min_trades),
    }
    files = {}
    for name, t in tables.items():
        path = out_dir / f"{stem}_{name}.csv"
        t.to_csv(path, index=False, encoding="utf-8-sig")
        files[name] = str(path)

    positive = {}
    for name, t in tables.items():
        if len(t) and "net_total_r" in t.columns:
            positive[name] = int(((t["trades"] >= args.min_trades) & (t["net_total_r"] > 0)).sum())
        else:
            positive[name] = 0

    summary = {"source": str(src), "rows": int(len(df)), "files": files, "overall": tables["overall"].to_dict("records")[0], "positive_slice_counts": positive}
    summary_path = out_dir / f"{stem}_spread_slice_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("analyze_mochipoyo_btc_spread_slices")
    print(f"source: {src}")
    print(f"rows: {len(df)}")
    print(f"output_dir: {out_dir}")
    print(f"summary_json: {summary_path}")
    print("overall:")
    print(tables["overall"].to_string(index=False))
    print("top by_pair_rank_direction:")
    print(tables["by_pair_rank_direction"].head(12).to_string(index=False))
    print("positive slice counts:")
    for k, v in positive.items():
        print(f"{k}: {v}")
    print("done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
