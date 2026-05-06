#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Mochipoyo portfolio from a fixed-filter preset JSON.

This avoids leaderboard re-ranking and uses the exact filter names stored in the
preset. It then exact-dedupes, applies cooldown, and excludes configured weak
slices.
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
        mask &= df["selected_slice"] == m.group(1)
        parts = m.group(2).split("|") if m.group(2) else []
    elif name.startswith("token_all="):
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


def ensure_selected_slice(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "selected_slice" not in out.columns:
        out["selected_slice"] = out.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    return out


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
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset")
    args = p.parse_args()

    df = pd.read_csv(args.backtest_csv, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"])
    df = ensure_selected_slice(df)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    df = df.sort_values("entry_time").reset_index(drop=True)

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
        row = {"source_filter_rank": int(item.get("rank", 9999)), "source_filter_name": name}
        row.update(stats(g.sort_values("entry_time")))
        coverage.append(row)

    union = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    exact = dedupe_exact(union)
    port_cfg = preset.get("portfolio", {})
    port = cooldown(exact, int(port_cfg.get("cooldown_minutes", 60)), bool(port_cfg.get("cooldown_by_direction", True)))
    exclude = set(port_cfg.get("exclude_slices", []))
    removed = port[port["selected_slice"].isin(exclude)].copy()
    final = port[~port["selected_slice"].isin(exclude)].copy().sort_values("entry_time").reset_index(drop=True)

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    union_csv = prefix.with_name(prefix.name + "_union_exact_deduped.csv")
    portfolio_csv = prefix.with_name(prefix.name + "_portfolio_before_exclusions.csv")
    final_csv = prefix.with_name(prefix.name + "_final_portfolio.csv")
    removed_csv = prefix.with_name(prefix.name + "_removed.csv")
    month_csv = prefix.with_name(prefix.name + "_by_month.csv")
    coverage_csv = prefix.with_name(prefix.name + "_filter_coverage.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")

    exact.to_csv(union_csv, index=False, encoding="utf-8-sig")
    port.to_csv(portfolio_csv, index=False, encoding="utf-8-sig")
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
        "portfolio_before_exclusions_rows": int(len(port)),
        "removed_rows": int(len(removed)),
        "final_rows": int(len(final)),
        "final_stats": stats(final.sort_values("entry_time")),
        "removed_stats": stats(removed.sort_values("entry_time")),
        "files": {
            "union_csv": str(union_csv),
            "portfolio_csv": str(portfolio_csv),
            "final_csv": str(final_csv),
            "removed_csv": str(removed_csv),
            "month_csv": str(month_csv),
            "coverage_csv": str(coverage_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("build_mochipoyo_portfolio_from_fixed_preset")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
