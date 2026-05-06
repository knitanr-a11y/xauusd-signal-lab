#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refine BTC Mochipoyo filters using net_r_after_spread.

Input is usually:
  data/results/mochipoyo/btc_selected/btc_mochipoyo_positive_net_monthly_validated_passed_trades.csv

BTC decisions must use net metrics. Gross is only reference.
"""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class FilterSpec:
    name: str
    min_total_score: float | None = None
    min_context_score: float | None = None
    min_base_score: float | None = None
    max_spread_to_sl_ratio: float | None = None
    min_effective_rr_after_spread: float | None = None
    directions: tuple[str, ...] = ()
    require_tokens_all: tuple[str, ...] = ()
    require_tokens_any: tuple[str, ...] = ()


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
    for c in ["spread_to_sl_ratio", "effective_rr_after_spread", "gross_sl_distance_price", "gross_tp_distance_price"]:
        if c in g.columns and len(g):
            out["avg_" + c] = float(pd.to_numeric(g[c], errors="coerce").mean())
    if "gross_r_result" in g.columns and len(g):
        gp2 = float(g.loc[g["gross_r_result"] > 0, "gross_r_result"].sum())
        gl2 = float(-g.loc[g["gross_r_result"] < 0, "gross_r_result"].sum())
        out["gross_total_r"] = float(g["gross_r_result"].sum())
        out["gross_pf"] = gp2 / gl2 if gl2 > 0 else None
    return out


def monthly(g: pd.DataFrame) -> dict:
    if g.empty:
        return {"active_months": 0, "positive_months": 0, "positive_month_ratio": None, "worst_month_net_r": None, "best_month_net_r": None}
    m = g.groupby("entry_month")["net_r_after_spread"].sum()
    active = int(len(m))
    pos = int((m > 0).sum())
    return {
        "active_months": active,
        "positive_months": pos,
        "positive_month_ratio": pos / active if active else None,
        "worst_month_net_r": float(m.min()) if active else None,
        "best_month_net_r": float(m.max()) if active else None,
    }


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def apply_filter(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if spec.directions:
        mask &= df["direction"].astype(str).isin(spec.directions)
    if spec.min_total_score is not None:
        mask &= pd.to_numeric(df["total_score"], errors="coerce") >= spec.min_total_score
    if spec.min_context_score is not None:
        mask &= pd.to_numeric(df["context_score"], errors="coerce") >= spec.min_context_score
    if spec.min_base_score is not None:
        mask &= pd.to_numeric(df["base_score"], errors="coerce") >= spec.min_base_score
    if spec.max_spread_to_sl_ratio is not None and "spread_to_sl_ratio" in df.columns:
        mask &= pd.to_numeric(df["spread_to_sl_ratio"], errors="coerce") <= spec.max_spread_to_sl_ratio
    if spec.min_effective_rr_after_spread is not None and "effective_rr_after_spread" in df.columns:
        mask &= pd.to_numeric(df["effective_rr_after_spread"], errors="coerce") >= spec.min_effective_rr_after_spread
    for token in spec.require_tokens_all:
        mask &= contains_token(df["reason_text"], token)
    if spec.require_tokens_any:
        tmask = pd.Series(False, index=df.index)
        for token in spec.require_tokens_any:
            tmask |= contains_token(df["reason_text"], token)
        mask &= tmask
    return df[mask].sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def tokens(df: pd.DataFrame, min_count: int) -> list[str]:
    counts: dict[str, int] = {}
    for text in df.get("reason_text", pd.Series(dtype=str)).fillna("").astype(str):
        for tok in text.split(";"):
            tok = tok.strip()
            if tok:
                counts[tok] = counts.get(tok, 0) + 1
    return sorted([t for t, c in counts.items() if c >= min_count])


def build_specs(df: pd.DataFrame, args: argparse.Namespace) -> list[FilterSpec]:
    specs: list[FilterSpec] = [FilterSpec(name="ALL")]
    toks = tokens(df, args.min_token_count)
    dirs = sorted(df["direction"].dropna().astype(str).unique().tolist())

    for d in dirs:
        specs.append(FilterSpec(name=f"direction={d}", directions=(d,)))
    for t in args.total_score_grid:
        specs.append(FilterSpec(name=f"total_score>={t}", min_total_score=t))
    for c in args.context_score_grid:
        specs.append(FilterSpec(name=f"context_score>={c}", min_context_score=c))
    for b in args.base_score_grid:
        specs.append(FilterSpec(name=f"base_score>={b}", min_base_score=b))
    for s in args.spread_to_sl_grid:
        specs.append(FilterSpec(name=f"spread_to_sl<={s}", max_spread_to_sl_ratio=s))
    for e in args.effective_rr_grid:
        specs.append(FilterSpec(name=f"effective_rr>={e}", min_effective_rr_after_spread=e))

    for tok in toks:
        specs.append(FilterSpec(name=f"token={tok}", require_tokens_all=(tok,)))
        for c in args.context_score_grid:
            specs.append(FilterSpec(name=f"token={tok}|context_score>={c}", require_tokens_all=(tok,), min_context_score=c))
        for t in args.total_score_grid:
            specs.append(FilterSpec(name=f"token={tok}|total_score>={t}", require_tokens_all=(tok,), min_total_score=t))
        for s in args.spread_to_sl_grid:
            specs.append(FilterSpec(name=f"token={tok}|spread_to_sl<={s}", require_tokens_all=(tok,), max_spread_to_sl_ratio=s))

    for a, b in list(itertools.combinations(toks, 2))[: args.max_token_pairs]:
        specs.append(FilterSpec(name=f"token_all={a}+{b}", require_tokens_all=(a, b)))

    for d in dirs:
        for tok in toks:
            specs.append(FilterSpec(name=f"direction={d}|token={tok}", directions=(d,), require_tokens_all=(tok,)))
        for s in args.spread_to_sl_grid:
            specs.append(FilterSpec(name=f"direction={d}|spread_to_sl<={s}", directions=(d,), max_spread_to_sl_ratio=s))

    uniq: dict[str, FilterSpec] = {}
    for spec in specs:
        uniq[json.dumps(asdict(spec), ensure_ascii=False, sort_keys=True)] = spec
    return list(uniq.values())


def evaluate(df: pd.DataFrame, specs: list[FilterSpec], args: argparse.Namespace) -> pd.DataFrame:
    rows = []
    for spec in specs:
        g = apply_filter(df, spec)
        if len(g) < args.min_trades:
            continue
        st = stats(g)
        mo = monthly(g)
        row = asdict(spec)
        row.update(st)
        row.update(mo)
        row["passes_overall"] = bool(
            st["trades"] >= args.min_trades
            and st["net_total_r"] >= args.min_net_total_r
            and st["net_pf"] is not None
            and st["net_pf"] >= args.min_net_pf
            and st["net_max_dd_r"] <= args.max_net_dd_r
            and mo["active_months"] >= args.min_active_months
            and mo["positive_month_ratio"] is not None
            and mo["positive_month_ratio"] >= args.min_positive_month_ratio
            and mo["worst_month_net_r"] is not None
            and mo["worst_month_net_r"] >= -args.max_worst_month_loss_r
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(["passes_overall", "net_pf", "net_total_r", "net_max_dd_r", "trades"], ascending=[False, False, False, True, False], na_position="last")
    return out


def parse_float_grid(text: str) -> list[float]:
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def main() -> int:
    p = argparse.ArgumentParser(description="Refine BTC Mochipoyo filters by net spread-aware metrics.")
    p.add_argument("--backtest-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/btc_selected/btc_mochipoyo_net_refined")
    p.add_argument("--min-trades", type=int, default=20)
    p.add_argument("--min-net-total-r", type=float, default=2.0)
    p.add_argument("--min-net-pf", type=float, default=1.30)
    p.add_argument("--max-net-dd-r", type=float, default=10.0)
    p.add_argument("--min-active-months", type=int, default=3)
    p.add_argument("--min-positive-month-ratio", type=float, default=0.50)
    p.add_argument("--max-worst-month-loss-r", type=float, default=5.0)
    p.add_argument("--min-token-count", type=int, default=10)
    p.add_argument("--max-token-pairs", type=int, default=200)
    p.add_argument("--total-score-grid", type=parse_float_grid, default="6,7,8,9,10,11,12")
    p.add_argument("--context-score-grid", type=parse_float_grid, default="3,4,5,6,7,8")
    p.add_argument("--base-score-grid", type=parse_float_grid, default="1,2,3,4,5")
    p.add_argument("--spread-to-sl-grid", type=parse_float_grid, default="0.04,0.05,0.06,0.07,0.08")
    p.add_argument("--effective-rr-grid", type=parse_float_grid, default="1.04,1.06,1.08,1.10,1.12")
    args = p.parse_args()

    src = Path(args.backtest_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(src, encoding="utf-8-sig")
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df = df.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")

    specs = build_specs(df, args)
    lb = evaluate(df, specs, args)
    lb_csv = prefix.with_name(prefix.name + "_leaderboard.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    best_csv = prefix.with_name(prefix.name + "_best_trades.csv")
    lb.to_csv(lb_csv, index=False, encoding="utf-8-sig")

    if len(lb):
        best_name = str(lb.iloc[0]["name"])
        spec = next(s for s in specs if s.name == best_name)
        best = apply_filter(df, spec)
    else:
        best = df.iloc[0:0].copy()
    best.to_csv(best_csv, index=False, encoding="utf-8-sig")

    summary = {
        "source": str(src),
        "input_trades": int(len(df)),
        "generated_specs": int(len(specs)),
        "evaluated_specs_kept": int(len(lb)),
        "files": {"leaderboard_csv": str(lb_csv), "best_trades_csv": str(best_csv)},
        "top_filters": lb.head(20).where(pd.notna(lb.head(20)), None).to_dict("records") if len(lb) else [],
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("refine_mochipoyo_btc_net_filters")
    print(f"source: {src}")
    print(f"input_trades: {len(df)}")
    print(f"generated_specs: {len(specs)}")
    print(f"evaluated_specs_kept: {len(lb)}")
    print(f"leaderboard_csv: {lb_csv}")
    print(f"best_trades_csv: {best_csv}")
    print(f"summary_json: {summary_json}")
    print("top filters:")
    if len(lb):
        cols = ["name", "trades", "win_rate", "net_total_r", "net_pf", "net_max_dd_r", "max_consecutive_losses", "active_months", "positive_month_ratio", "worst_month_net_r", "passes_overall"]
        print(lb[cols].head(20).to_string(index=False))
    else:
        print("empty")
    print("done")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
