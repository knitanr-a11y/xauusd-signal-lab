#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build BTC Mochipoyo portfolio from a fixed-filter preset JSON.

BTC uses net_r_after_spread as the primary metric. Gross is reference only.
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


def apply_name_filter(df: pd.DataFrame, name: str) -> pd.DataFrame:
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


def dedupe_exact(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    cols = [c for c in ["entry_time", "pair_name", "candidate_rank", "direction", "entry_price", "base_time", "signal_time"] if c in df.columns]
    return df.drop_duplicates(subset=cols, keep="first").sort_values("entry_time").reset_index(drop=True)


def cooldown(df: pd.DataFrame, minutes: int, by_direction: bool) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.sort_values(["entry_time", "source_filter_rank", "total_score"], ascending=[True, True, False]).copy()
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
    p = argparse.ArgumentParser()
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--preset-json", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/btc_selected/btc_mochipoyo_fixed_preset")
    args = p.parse_args()

    df = pd.read_csv(args.backtest_csv, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    if "selected_slice" not in df.columns:
        df["selected_slice"] = df.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)

    preset = json.loads(Path(args.preset_json).read_text(encoding="utf-8"))
    parts = []
    coverage = []
    for item in preset.get("fixed_filters", []):
        name = str(item["name"])
        g = apply_name_filter(df, name)
        if g.empty:
            continue
        g = g.copy()
        g["source_filter_rank"] = int(item.get("rank", 9999))
        g["source_filter_name"] = name
        parts.append(g)
        cov = {"source_filter_rank": int(item.get("rank", 9999)), "source_filter_name": name}
        cov.update(stats(g.sort_values("entry_time")))
        coverage.append(cov)

    union = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    exact = dedupe_exact(union)
    cfg = preset.get("portfolio", {})
    port = cooldown(exact, int(cfg.get("cooldown_minutes", 60)), bool(cfg.get("cooldown_by_direction", True)))
    exclude = set(cfg.get("exclude_slices", []))
    removed = port[port["selected_slice"].isin(exclude)].copy()
    final = port[~port["selected_slice"].isin(exclude)].copy().sort_values("entry_time").reset_index(drop=True)

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    union_csv = prefix.with_name(prefix.name + "_union_exact_deduped.csv")
    final_csv = prefix.with_name(prefix.name + "_final_portfolio.csv")
    removed_csv = prefix.with_name(prefix.name + "_removed.csv")
    month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    coverage_csv = prefix.with_name(prefix.name + "_filter_coverage.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    exact.to_csv(union_csv, index=False, encoding="utf-8-sig")
    final.to_csv(final_csv, index=False, encoding="utf-8-sig")
    removed.to_csv(removed_csv, index=False, encoding="utf-8-sig")
    grouped(final, "entry_month").to_csv(month_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage).to_csv(coverage_csv, index=False, encoding="utf-8-sig")

    summary = {
        "candidate_name": preset.get("candidate_name"),
        "input_trades": int(len(df)),
        "fixed_filters": int(len(preset.get("fixed_filters", []))),
        "matched_filter_parts_rows": int(len(union)),
        "union_exact_deduped_rows": int(len(exact)),
        "final_rows": int(len(final)),
        "final_stats": stats(final.sort_values("entry_time")),
        "removed_rows": int(len(removed)),
        "removed_stats": stats(removed.sort_values("entry_time")),
        "files": {"union_csv": str(union_csv), "final_csv": str(final_csv), "removed_csv": str(removed_csv), "month_csv": str(month_csv), "coverage_csv": str(coverage_csv)},
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("build_mochipoyo_btc_portfolio_from_fixed_preset")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
