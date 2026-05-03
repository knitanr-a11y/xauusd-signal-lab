from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "btc_spread_revalidation_trades.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_spread_filtered_adoption_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btc_spread_filtered_adoption_trades.csv"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_case_from_rule_name(rule_name: Any) -> tuple[float | None, float | None, int | None]:
    match = re.search(r"_rr([0-9.]+)_risk([0-9.]+)_max([0-9]+)$", str(rule_name))
    if not match:
        return None, None, None
    return float(match.group(1)), float(match.group(2)), int(match.group(3))


def pf(r: pd.Series) -> float | None:
    values = pd.to_numeric(r, errors="coerce").dropna()
    wins = values[values > 0].sum()
    losses = -values[values < 0].sum()
    if losses <= 0:
        return None
    return float(wins / losses)


def max_dd(r: pd.Series) -> float:
    values = pd.to_numeric(r, errors="coerce").fillna(0.0)
    if values.empty:
        return 0.0
    equity = values.cumsum()
    dd = equity - equity.cummax()
    return float(abs(dd.min()))


def max_consecutive_losses(results: pd.Series) -> int:
    streak = 0
    best = 0
    for value in results.astype(str):
        if value == "loss":
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return int(best)


def summarize_trades(trades: pd.DataFrame, *, prefix: str) -> dict[str, Any]:
    if trades.empty:
        return {
            f"{prefix}_trades": 0,
            f"{prefix}_wins": 0,
            f"{prefix}_losses": 0,
            f"{prefix}_win_rate": None,
            f"{prefix}_total_r": 0.0,
            f"{prefix}_avg_r": None,
            f"{prefix}_pf": None,
            f"{prefix}_max_dd_r": 0.0,
            f"{prefix}_max_consecutive_losses": 0,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    return {
        f"{prefix}_trades": int(len(trades)),
        f"{prefix}_wins": wins,
        f"{prefix}_losses": losses,
        f"{prefix}_win_rate": float(wins / len(trades)),
        f"{prefix}_total_r": float(r.sum()),
        f"{prefix}_avg_r": float(r.mean()),
        f"{prefix}_pf": pf(r),
        f"{prefix}_max_dd_r": max_dd(r),
        f"{prefix}_max_consecutive_losses": max_consecutive_losses(trades["result"]),
    }


def month_count(trades: pd.DataFrame) -> float | None:
    if trades.empty or "entry_time" not in trades.columns:
        return None
    times = pd.to_datetime(trades["entry_time"], errors="coerce").dropna()
    if times.empty:
        return None
    months = times.dt.to_period("M").nunique()
    return float(months) if months else None


def add_case_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    parsed = out["rule_name"].apply(parse_case_from_rule_name)
    out["rr"] = parsed.apply(lambda x: x[0])
    out["risk_atr"] = parsed.apply(lambda x: x[1])
    out["max_bars"] = parsed.apply(lambda x: x[2])
    return out


def filter_value_width(
    trades: pd.DataFrame,
    *,
    min_net_tp_pips: float,
    max_spread_to_sl_ratio: float,
    min_effective_rr: float,
) -> pd.DataFrame:
    cond = (
        (pd.to_numeric(trades["net_tp_after_spread_pips"], errors="coerce") >= min_net_tp_pips)
        & (pd.to_numeric(trades["spread_to_sl_ratio"], errors="coerce") < max_spread_to_sl_ratio)
        & (pd.to_numeric(trades["effective_rr_after_spread"], errors="coerce") >= min_effective_rr)
    )
    out = trades.loc[cond].copy()
    out["value_filter_min_net_tp_pips"] = min_net_tp_pips
    out["value_filter_max_spread_to_sl_ratio"] = max_spread_to_sl_ratio
    out["value_filter_min_effective_rr"] = min_effective_rr
    return out


def summarize_by_case(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    keys = ["rule_name", "base_rule_name", "base_tf", "rr", "risk_atr", "max_bars"]
    rows: list[dict[str, Any]] = []
    grouped = before.groupby(keys, dropna=False, sort=False)
    for key_values, before_case in grouped:
        mask = pd.Series(True, index=after.index)
        for key, value in zip(keys, key_values):
            if pd.isna(value):
                mask &= after[key].isna()
            else:
                mask &= after[key] == value
        after_case = after.loc[mask].copy()
        row = {key: value for key, value in zip(keys, key_values)}
        row.update(summarize_trades(before_case, prefix="before_filter"))
        row.update(summarize_trades(after_case, prefix="after_filter"))
        row["removed_trades"] = int(len(before_case) - len(after_case))
        row["removed_rate"] = float(row["removed_trades"] / len(before_case)) if len(before_case) else None
        row["before_months"] = month_count(before_case)
        row["after_months"] = month_count(after_case)
        row["after_trades_per_month"] = (
            float(len(after_case) / row["after_months"]) if row.get("after_months") else None
        )
        metrics_source = after_case
        for col in [
            "gross_tp_pips",
            "gross_sl_pips",
            "net_tp_after_spread_pips",
            "sl_with_spread_pips",
            "spread_to_sl_ratio",
            "spread_to_tp_ratio",
            "effective_rr_after_spread",
            "assumed_spread_price",
            "mode_spread_price",
        ]:
            row[f"avg_{col}"] = float(pd.to_numeric(metrics_source[col], errors="coerce").mean()) if not metrics_source.empty and col in metrics_source.columns else None
        row["pf_change_after_filter"] = (
            None
            if row.get("before_filter_pf") is None or row.get("after_filter_pf") is None
            else float(row["after_filter_pf"] - row["before_filter_pf"])
        )
        row["total_r_change_after_filter"] = float(row.get("after_filter_total_r", 0.0) - row.get("before_filter_total_r", 0.0))
        row["adoption_candidate"] = bool(
            row.get("after_filter_trades", 0) >= 30
            and (row.get("after_filter_pf") or 0) >= 1.5
            and (row.get("after_filter_total_r") or 0) > 0
            and (row.get("avg_net_tp_after_spread_pips") or 0) >= 5.0
            and (row.get("avg_spread_to_sl_ratio") or 999) < 0.5
            and (row.get("avg_effective_rr_after_spread") or 0) >= 1.0
        )
        rows.append(row)
    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary = summary.sort_values(
            ["adoption_candidate", "after_filter_pf", "after_filter_total_r", "after_filter_trades"],
            ascending=[False, False, False, False],
            kind="mergesort",
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize BTC spread-aware revalidation trades after value-width filters.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--min-net-tp-pips", type=float, default=5.0)
    parser.add_argument("--max-spread-to-sl-ratio", type=float, default=0.50)
    parser.add_argument("--min-effective-rr", type=float, default=1.0)
    parser.add_argument("--base-rule-filter", default="", help="Optional substring filter, e.g. BTC_SCALP or BTC_RUNNER.")
    args = parser.parse_args()

    trades_csv = resolve_path(args.trades_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)

    trades = pd.read_csv(trades_csv)
    trades = add_case_columns(trades)
    net = trades[trades["scenario"].astype(str).str.contains("net", na=False)].copy()
    if args.base_rule_filter:
        net = net[net["rule_name"].astype(str).str.contains(args.base_rule_filter, na=False)].copy()

    filtered = filter_value_width(
        net,
        min_net_tp_pips=args.min_net_tp_pips,
        max_spread_to_sl_ratio=args.max_spread_to_sl_ratio,
        min_effective_rr=args.min_effective_rr,
    )
    summary = summarize_by_case(net, filtered)

    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_trades.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_summary, index=False, encoding="utf-8-sig")
    filtered.to_csv(out_trades, index=False, encoding="utf-8-sig")

    display_cols = [
        "rule_name",
        "base_tf",
        "before_filter_trades",
        "after_filter_trades",
        "removed_trades",
        "after_filter_win_rate",
        "after_filter_total_r",
        "after_filter_avg_r",
        "after_filter_pf",
        "before_filter_pf",
        "pf_change_after_filter",
        "after_filter_max_dd_r",
        "after_filter_max_consecutive_losses",
        "after_trades_per_month",
        "avg_net_tp_after_spread_pips",
        "avg_sl_with_spread_pips",
        "avg_spread_to_sl_ratio",
        "avg_effective_rr_after_spread",
        "adoption_candidate",
    ]
    print("Project root:", PROJECT_ROOT)
    print("Trades CSV:", trades_csv)
    print("Net trades before filter:", len(net))
    print("Net trades after filter:", len(filtered))
    print("Filters:", f"net_tp_pips >= {args.min_net_tp_pips}", f"spread_to_sl < {args.max_spread_to_sl_ratio}", f"effective_rr >= {args.min_effective_rr}")
    print("Saved summary:", out_summary)
    print("Saved filtered trades:", out_trades)
    print("\nTop filtered candidates:")
    print(summary[display_cols].head(30).to_string(index=False) if not summary.empty else "No summary.")
    print("\nOriginal-like BTC M5 rows:")
    if summary.empty:
        print("No summary.")
    else:
        mask = summary["rule_name"].astype(str).str.contains("BTC_SCALP_H1_M5_REENTRY_FILTERED_rr2.0_risk0.8", regex=False, na=False)
        print(summary.loc[mask, display_cols].to_string(index=False) if mask.any() else "No original-like rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
