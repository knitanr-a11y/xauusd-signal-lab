#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize GOLD/BTC Mochipoyo portfolios in dollars and pips.

Default conversion:
- GOLD: 1 dollar = 10 pips
- BTC : 10 dollars = 1 pip

GOLD dollar PnL estimate:
- Prefer pnl_price / price_pnl columns if present.
- Else use r_result * risk_distance-like column.
- Else infer WIN/LOSS/TIMEOUT from rr and risk distance.

BTC dollar PnL estimate:
- Prefer net_price_result if present.
- Else use net_r_after_spread * net_sl_after_spread_price.
- Else use net_r_after_spread * gross_sl_distance_price as fallback.

This is a price-move summary, not lot-size monetary PnL.
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


def pick_first_existing(df: pd.DataFrame, names: list[str]) -> str | None:
    for n in names:
        if n in df.columns:
            return n
    return None


def read_trades(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
        df["entry_month"] = df["entry_time"].dt.strftime("%Y-%m")
    return df


def infer_gold_dollars(df: pd.DataFrame, default_rr: float) -> tuple[pd.Series, str]:
    pnl_col = pick_first_existing(df, ["pnl_price", "price_pnl", "dollar_result", "result_price", "price_result"])
    if pnl_col:
        return pd.to_numeric(df[pnl_col], errors="coerce").fillna(0.0), pnl_col

    r_col = pick_first_existing(df, ["r_result", "gross_r_result"])
    risk_col = pick_first_existing(df, ["risk_distance", "risk_distance_price", "gross_risk_distance_price", "gross_sl_distance_price"])
    if r_col and risk_col:
        r = pd.to_numeric(df[r_col], errors="coerce").fillna(0.0)
        risk = pd.to_numeric(df[risk_col], errors="coerce").fillna(0.0).abs()
        return r * risk, f"{r_col}*{risk_col}"

    # Last fallback: infer from outcome and SL/TP distances.
    if {"entry_price", "sl_price", "tp_price", "outcome"}.issubset(df.columns):
        entry = pd.to_numeric(df["entry_price"], errors="coerce")
        sl = pd.to_numeric(df["sl_price"], errors="coerce")
        tp = pd.to_numeric(df["tp_price"], errors="coerce")
        risk = (entry - sl).abs()
        reward = (tp - entry).abs().fillna(default_rr * risk)
        outcome = df["outcome"].astype(str)
        dollars = pd.Series(0.0, index=df.index)
        dollars[outcome == "WIN"] = reward[outcome == "WIN"]
        dollars[outcome == "LOSS"] = -risk[outcome == "LOSS"]
        return dollars.fillna(0.0), "inferred_from_entry_sl_tp_outcome"

    raise RuntimeError("Cannot infer GOLD dollar result. Need r_result+risk_distance or entry/sl/tp/outcome columns.")


def infer_btc_dollars(df: pd.DataFrame) -> tuple[pd.Series, str]:
    pnl_col = pick_first_existing(df, ["net_price_result", "net_dollar_result", "net_pnl_price", "price_pnl_net"])
    if pnl_col:
        return pd.to_numeric(df[pnl_col], errors="coerce").fillna(0.0), pnl_col

    r_col = pick_first_existing(df, ["net_r_after_spread"])
    risk_col = pick_first_existing(df, ["net_sl_after_spread_price", "gross_sl_distance_price", "gross_risk_distance_price"])
    if r_col and risk_col:
        r = pd.to_numeric(df[r_col], errors="coerce").fillna(0.0)
        risk = pd.to_numeric(df[risk_col], errors="coerce").fillna(0.0).abs()
        return r * risk, f"{r_col}*{risk_col}"

    raise RuntimeError("Cannot infer BTC dollar result. Need net_r_after_spread and net_sl_after_spread_price/gross_sl_distance_price.")


def summarize(df: pd.DataFrame, dollars: pd.Series, pips_per_dollar: float, label: str, source_method: str) -> dict:
    dollars = pd.to_numeric(dollars, errors="coerce").fillna(0.0)
    pips = dollars * pips_per_dollar
    wins = int((df.get("outcome", pd.Series(index=df.index, dtype=str)).astype(str) == "WIN").sum()) if len(df) else 0
    losses = int((df.get("outcome", pd.Series(index=df.index, dtype=str)).astype(str) == "LOSS").sum()) if len(df) else 0
    timeouts = int((df.get("outcome", pd.Series(index=df.index, dtype=str)).astype(str) == "TIMEOUT").sum()) if len(df) else 0
    gp = float(dollars[dollars > 0].sum())
    gl = float(-dollars[dollars < 0].sum())
    return {
        "label": label,
        "rows": int(len(df)),
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "source_method": source_method,
        "pips_per_dollar": pips_per_dollar,
        "total_dollars": float(dollars.sum()),
        "total_pips": float(pips.sum()),
        "avg_dollars": float(dollars.mean()) if len(df) else None,
        "avg_pips": float(pips.mean()) if len(df) else None,
        "gross_profit_dollars": gp,
        "gross_loss_dollars": gl,
        "pf_by_dollars": gp / gl if gl > 0 else None,
        "max_dd_dollars": max_dd(dollars),
        "max_dd_pips": max_dd(pips),
        "max_consecutive_losses": max_loss_streak(df["outcome"]) if "outcome" in df.columns else None,
    }


def monthly_summary(df: pd.DataFrame, dollars: pd.Series, pips_per_dollar: float, label: str) -> pd.DataFrame:
    if "entry_month" not in df.columns:
        return pd.DataFrame()
    work = df.copy()
    work["_dollars"] = pd.to_numeric(dollars, errors="coerce").fillna(0.0)
    work["_pips"] = work["_dollars"] * pips_per_dollar
    rows = []
    for month, g in work.groupby("entry_month", sort=True):
        gp = float(g.loc[g["_dollars"] > 0, "_dollars"].sum())
        gl = float(-g.loc[g["_dollars"] < 0, "_dollars"].sum())
        rows.append({
            "label": label,
            "entry_month": month,
            "trades": int(len(g)),
            "wins": int((g["outcome"].astype(str) == "WIN").sum()) if "outcome" in g.columns else None,
            "losses": int((g["outcome"].astype(str) == "LOSS").sum()) if "outcome" in g.columns else None,
            "timeouts": int((g["outcome"].astype(str) == "TIMEOUT").sum()) if "outcome" in g.columns else None,
            "total_dollars": float(g["_dollars"].sum()),
            "total_pips": float(g["_pips"].sum()),
            "pf_by_dollars": gp / gl if gl > 0 else None,
            "max_dd_dollars": max_dd(g["_dollars"]),
            "max_dd_pips": max_dd(g["_pips"]),
        })
    return pd.DataFrame(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Summarize Mochipoyo GOLD/BTC portfolios in dollars and pips.")
    p.add_argument("--gold-csv", required=True)
    p.add_argument("--btc-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/mochipoyo_gold_btc_pips_summary")
    p.add_argument("--gold-pips-per-dollar", type=float, default=10.0, help="GOLD: default 1 dollar = 10 pips")
    p.add_argument("--btc-pips-per-dollar", type=float, default=0.1, help="BTC: default 10 dollars = 1 pip")
    p.add_argument("--gold-rr", type=float, default=1.2)
    args = p.parse_args()

    gold = read_trades(args.gold_csv)
    btc = read_trades(args.btc_csv)
    gold_dollars, gold_method = infer_gold_dollars(gold, args.gold_rr)
    btc_dollars, btc_method = infer_btc_dollars(btc)

    gold_sum = summarize(gold, gold_dollars, args.gold_pips_per_dollar, "GOLD", gold_method)
    btc_sum = summarize(btc, btc_dollars, args.btc_pips_per_dollar, "BTC", btc_method)
    combined = {
        "label": "COMBINED_GOLD_BTC",
        "total_dollars_simple_sum": gold_sum["total_dollars"] + btc_sum["total_dollars"],
        "total_pips_symbol_converted_sum": gold_sum["total_pips"] + btc_sum["total_pips"],
        "note": "Combined pips are a simple sum after symbol-specific conversion; GOLD/BTC pips are not the same market unit.",
    }

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json = prefix.with_name(prefix.name + ".summary.json")
    summary_csv = prefix.with_name(prefix.name + ".csv")
    month_csv = prefix.with_name(prefix.name + "_by_month.csv")

    pd.DataFrame([gold_sum, btc_sum]).to_csv(summary_csv, index=False, encoding="utf-8-sig")
    months = pd.concat([
        monthly_summary(gold, gold_dollars, args.gold_pips_per_dollar, "GOLD"),
        monthly_summary(btc, btc_dollars, args.btc_pips_per_dollar, "BTC"),
    ], ignore_index=True)
    months.to_csv(month_csv, index=False, encoding="utf-8-sig")

    payload = {"gold": gold_sum, "btc": btc_sum, "combined": combined, "files": {"summary_csv": str(summary_csv), "month_csv": str(month_csv)}}
    summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("summarize_mochipoyo_portfolio_pips")
    print("GOLD:")
    print(json.dumps(gold_sum, ensure_ascii=False, indent=2))
    print("BTC:")
    print(json.dumps(btc_sum, ensure_ascii=False, indent=2))
    print("COMBINED:")
    print(json.dumps(combined, ensure_ascii=False, indent=2))
    print(f"summary_csv: {summary_csv}")
    print(f"month_csv: {month_csv}")
    print(f"summary_json: {summary_json}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
