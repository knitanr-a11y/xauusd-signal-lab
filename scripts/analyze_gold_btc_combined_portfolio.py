from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_GOLD_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "gold_abc_extra_overlap_trades.csv"
DEFAULT_BTC_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_value_width_edge_trades.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_btc_combined_portfolio_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "gold_btc_combined_portfolio_trades.csv"
DEFAULT_OUT_MONTHLY = PROJECT_ROOT / "data" / "results" / "gold_btc_combined_portfolio_monthly.csv"

DEFAULT_BTC_RULE = "trend_pull_runner_rr2.0_risk1.0"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def normalize_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["signal_time", "entry_time", "jst_entry_time", "exit_time"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    if "entry_time" not in out.columns and "jst_entry_time" in out.columns:
        out["entry_time"] = out["jst_entry_time"]
    if "jst_entry_time" not in out.columns and "entry_time" in out.columns:
        out["jst_entry_time"] = out["entry_time"]
    return out


def read_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    out = normalize_time_columns(df)
    required = ["side", "r"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    out["side"] = out["side"].astype(str).str.upper().str.strip()
    out["r"] = pd.to_numeric(out["r"], errors="coerce")
    if "result" not in out.columns:
        out["result"] = np.where(out["r"] > 0, "win", np.where(out["r"] < 0, "loss", "breakeven"))
    out["result"] = out["result"].astype(str).str.lower().str.strip()
    for col in ["signal_idx", "entry_idx"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["r", "side"]).copy()
    if "entry_time" in out.columns:
        out = out.dropna(subset=["entry_time"]).copy()
    return out.reset_index(drop=True)


def prepare_gold(df: pd.DataFrame, *, gold_set: str) -> pd.DataFrame:
    out = df.copy()
    if "output_set" in out.columns:
        selected = out[out["output_set"].astype(str).eq(gold_set)].copy()
        if selected.empty:
            available = sorted(out["output_set"].dropna().astype(str).unique().tolist())
            raise ValueError(f"No rows for gold output_set={gold_set}. Available: {available}")
        out = selected
    out["symbol_group"] = "GOLD"
    if "strategy_label" not in out.columns:
        out["strategy_label"] = out.get("rule_name", "GOLD_UNKNOWN")
    out["portfolio_signal_label"] = out["strategy_label"].astype(str)
    out["portfolio_rank"] = np.select(
        [
            out["strategy_label"].astype(str).str.contains("ABC", case=False, na=False),
            out["strategy_label"].astype(str).isin(["GOLD_EXTRA_HIGH_RSI_STOCH", "GOLD_COUNTER_BUY_ONLY"]),
            out["strategy_label"].astype(str).eq("GOLD_EXTRA_BB_BALANCE"),
            out["strategy_label"].astype(str).eq("GOLD_EXTRA_BB_WIDTH"),
        ],
        ["GOLD_ABC", "GOLD_EXTRA_HIGH", "GOLD_EXTRA_STANDARD", "GOLD_EXTRA_WIDTH"],
        default="GOLD_OTHER",
    )
    return out


def prepare_btc(df: pd.DataFrame, *, btc_rule: str) -> pd.DataFrame:
    out = df.copy()
    if "rule_name" not in out.columns:
        raise ValueError("BTC trades CSV must contain rule_name")
    selected = out[out["rule_name"].astype(str).eq(btc_rule)].copy()
    if selected.empty:
        available = sorted(out["rule_name"].dropna().astype(str).unique().tolist())[:20]
        raise ValueError(f"No rows for btc rule_name={btc_rule}. First available: {available}")
    selected["symbol_group"] = "BTC"
    selected["strategy_label"] = "BTC_RUNNER_RR2_RISK1"
    selected["portfolio_signal_label"] = "BTC_RUNNER_RR2_RISK1"
    selected["portfolio_rank"] = "BTC_RUNNER"
    return selected


def profit_factor(r: pd.Series) -> float | None:
    wins = r[r > 0]
    losses = r[r < 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
    if gross_loss_abs <= 0:
        return None
    return gross_win / gross_loss_abs


def max_consecutive_losses(results: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for value in results.astype(str).str.lower():
        if value == "loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def max_drawdown_r(r: pd.Series) -> float:
    equity = pd.to_numeric(r, errors="coerce").fillna(0).cumsum()
    peak = equity.cummax()
    dd = equity - peak
    return float(abs(dd.min())) if len(dd) else 0.0


def summarize(df: pd.DataFrame, *, group_name: str, group_value: str) -> dict[str, object]:
    if df.empty:
        return {
            "group_name": group_name,
            "group_value": group_value,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "max_drawdown_r": 0.0,
            "buy_trades": 0,
            "sell_trades": 0,
            "trades_per_month": None,
        }
    sort_cols = [col for col in ["entry_time", "entry_idx", "signal_time", "signal_idx"] if col in df.columns]
    ordered = df.sort_values(sort_cols, kind="mergesort").copy() if sort_cols else df.copy()
    r = pd.to_numeric(ordered["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = ordered[ordered["side"].eq("BUY")]
    sell = ordered[ordered["side"].eq("SELL")]
    trades_per_month = None
    if "entry_time" in ordered.columns and ordered["entry_time"].notna().any():
        months = max(1.0, (pd.Timestamp(ordered["entry_time"].max()) - pd.Timestamp(ordered["entry_time"].min())).days / 30.4375)
        trades_per_month = float(len(ordered) / months)
    return {
        "group_name": group_name,
        "group_value": group_value,
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(ordered),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(ordered["result"]),
        "max_drawdown_r": max_drawdown_r(r),
        "buy_trades": int(len(buy)),
        "sell_trades": int(len(sell)),
        "buy_win_rate": float((buy["r"] > 0).sum() / len(buy)) if len(buy) else None,
        "sell_win_rate": float((sell["r"] > 0).sum() / len(sell)) if len(sell) else None,
        "trades_per_month": trades_per_month,
    }


def build_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rows.append(summarize(combined, group_name="all", group_value="GOLD_PLUS_BTC"))
    for symbol, group in combined.groupby("symbol_group", dropna=False):
        rows.append(summarize(group.copy(), group_name="symbol", group_value=str(symbol)))
    for rank, group in combined.groupby("portfolio_rank", dropna=False):
        rows.append(summarize(group.copy(), group_name="portfolio_rank", group_value=str(rank)))
    for label, group in combined.groupby("portfolio_signal_label", dropna=False):
        rows.append(summarize(group.copy(), group_name="signal_label", group_value=str(label)))
    return pd.DataFrame(rows)


def build_monthly(combined: pd.DataFrame) -> pd.DataFrame:
    if combined.empty or "entry_time" not in combined.columns:
        return pd.DataFrame()
    out = combined.copy()
    out["entry_month"] = out["entry_time"].dt.to_period("M").astype(str)
    rows: list[dict[str, object]] = []
    for month, group in out.groupby("entry_month", dropna=False):
        rows.append(summarize(group.copy(), group_name="month_all", group_value=str(month)))
        for symbol, sub in group.groupby("symbol_group", dropna=False):
            row = summarize(sub.copy(), group_name="month_symbol", group_value=str(month))
            row["symbol_group"] = symbol
            rows.append(row)
    return pd.DataFrame(rows)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze combined GOLD and BTC signal portfolio.")
    parser.add_argument("--gold-trades-csv", type=Path, default=DEFAULT_GOLD_TRADES_CSV)
    parser.add_argument("--btc-trades-csv", type=Path, default=DEFAULT_BTC_TRADES_CSV)
    parser.add_argument("--gold-output-set", default="combined_high_quality_first")
    parser.add_argument("--btc-rule-name", default=DEFAULT_BTC_RULE)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--out-monthly", type=Path, default=DEFAULT_OUT_MONTHLY)
    args = parser.parse_args()

    gold_path = resolve_path(args.gold_trades_csv)
    btc_path = resolve_path(args.btc_trades_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    out_monthly = resolve_path(args.out_monthly)

    gold = prepare_gold(read_trades(gold_path), gold_set=args.gold_output_set)
    btc = prepare_btc(read_trades(btc_path), btc_rule=args.btc_rule_name)

    combined = pd.concat([gold, btc], ignore_index=True, sort=False)
    sort_cols = [col for col in ["entry_time", "entry_idx", "signal_time", "signal_idx"] if col in combined.columns]
    if sort_cols:
        combined = combined.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
    combined["portfolio_trade_no"] = np.arange(1, len(combined) + 1)
    combined["portfolio_equity_r"] = pd.to_numeric(combined["r"], errors="coerce").fillna(0).cumsum()

    summary = build_summary(combined)
    monthly = build_monthly(combined)

    write_csv(out_summary, summary)
    write_csv(out_trades, combined)
    write_csv(out_monthly, monthly)

    print("Gold trades CSV:", gold_path)
    print("BTC trades CSV:", btc_path)
    print("Gold output_set:", args.gold_output_set)
    print("BTC rule:", args.btc_rule_name)
    print("Gold selected rows:", len(gold))
    print("BTC selected rows:", len(btc))
    print("Combined rows:", len(combined))
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)
    print("Saved monthly:", out_monthly)

    display_cols = [
        "group_name",
        "group_value",
        "trades",
        "buy_trades",
        "sell_trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "max_drawdown_r",
        "trades_per_month",
    ]
    print_table("GOLD + BTC COMBINED PORTFOLIO SUMMARY", summary[display_cols])

    monthly_display_cols = [
        "group_name",
        "group_value",
        "symbol_group",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "pf",
        "max_drawdown_r",
    ]
    monthly_display_cols = [col for col in monthly_display_cols if col in monthly.columns]
    print_table("GOLD + BTC MONTHLY SUMMARY", monthly[monthly_display_cols].tail(36) if not monthly.empty else monthly)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
