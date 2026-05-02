from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import summarize_trades

DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "goldsharp_xm_kiwami_gold_abc_v3_backtest_trades.csv"
DEFAULT_MONTH = "2025-03"


def normalize_source_col(df: pd.DataFrame) -> str:
    if "combined_signal_source" in df.columns:
        return "combined_signal_source"
    if "signal_source" in df.columns:
        return "signal_source"
    raise ValueError("source column not found. Expected combined_signal_source or signal_source.")


def prepare_trades(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in ["signal_time", "entry_time", "exit_time", "jst_entry_time"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")

    if "jst_entry_time" in out.columns:
        out["jst_entry_month"] = out["jst_entry_time"].dt.to_period("M").astype(str)
        out["jst_entry_hour"] = out["jst_entry_time"].dt.hour
        out["jst_entry_date"] = out["jst_entry_time"].dt.strftime("%Y-%m-%d")
    elif "entry_time" in out.columns:
        out["entry_month"] = out["entry_time"].dt.to_period("M").astype(str)
        out["entry_hour"] = out["entry_time"].dt.hour
        out["entry_date"] = out["entry_time"].dt.strftime("%Y-%m-%d")
    else:
        raise ValueError("entry_time/jst_entry_time columns not found.")

    return out


def summarize_grouped(trades: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for key, group in trades.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        summary = summarize_trades(group)
        for col, value in zip(group_cols, key):
            summary[col] = value
        rows.append(summary)

    if not rows:
        return pd.DataFrame()

    ordered = group_cols + [
        "trades",
        "closed_trades",
        "wins",
        "losses",
        "win_rate",
        "average_r",
        "total_r",
        "profit_factor",
        "max_consecutive_losses",
        "max_drawdown_r",
    ]
    return pd.DataFrame(rows)[ordered].reset_index(drop=True)


def print_table(title: str, df: pd.DataFrame, sort_cols: list[str] | None = None) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    if df.empty:
        print("No data.")
        return
    out = df.copy()
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    print(out.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one weak month for XM KIWAMI GOLD ABC v3 trades.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--month", type=str, default=DEFAULT_MONTH)
    args = parser.parse_args()

    trades_csv = args.trades_csv
    if not trades_csv.is_absolute():
        trades_csv = PROJECT_ROOT / trades_csv

    if not trades_csv.exists():
        print(f"Trades CSV not found: {trades_csv}")
        print("Run first:")
        print("python scripts/run_preset_backtest.py --preset xm_kiwami_gold_abc_v3 --data-dir data/raw/xm_kiwami --save")
        return 1

    trades = pd.read_csv(trades_csv)
    trades = prepare_trades(trades)
    source_col = normalize_source_col(trades)

    month_trades = trades[trades["jst_entry_month"] == args.month].copy()

    print(f"Loaded: {trades_csv}")
    print(f"Rows total: {len(trades)}")
    print(f"Target month: {args.month}")
    print(f"Rows month: {len(month_trades)}")

    print_table("MONTH OVERALL", pd.DataFrame([summarize_trades(month_trades)]))
    print_table("MONTH BY SOURCE", summarize_grouped(month_trades, [source_col]), [source_col])
    print_table("MONTH BY SIDE", summarize_grouped(month_trades, ["side"]), ["side"])
    print_table("MONTH BY SOURCE x SIDE", summarize_grouped(month_trades, [source_col, "side"]), [source_col, "side"])
    print_table("MONTH BY JST HOUR", summarize_grouped(month_trades, ["jst_entry_hour"]), ["jst_entry_hour"])
    print_table("MONTH BY JST HOUR x SOURCE", summarize_grouped(month_trades, ["jst_entry_hour", source_col]), ["jst_entry_hour", source_col])
    print_table("MONTH BY DATE", summarize_grouped(month_trades, ["jst_entry_date"]), ["jst_entry_date"])
    print_table("MONTH BY DATE x SOURCE", summarize_grouped(month_trades, ["jst_entry_date", source_col]), ["jst_entry_date", source_col])

    loss_trades = month_trades[month_trades["r"] < 0].copy() if "r" in month_trades.columns else pd.DataFrame()
    print_table("LOSSES BY SOURCE", summarize_grouped(loss_trades, [source_col]), [source_col])
    print_table("LOSSES BY JST HOUR x SOURCE", summarize_grouped(loss_trades, ["jst_entry_hour", source_col]), ["jst_entry_hour", source_col])

    cols = [
        source_col,
        "side",
        "signal_time",
        "entry_time",
        "jst_entry_time",
        "exit_time",
        "entry_price",
        "sl",
        "tp",
        "risk",
        "result",
        "r",
        "exit_reason",
        "bars_held",
    ]
    available_cols = [c for c in cols if c in month_trades.columns]

    print("\n" + "=" * 120)
    print("MONTH TRADES DETAIL")
    print("=" * 120)
    if month_trades.empty:
        print("No trades.")
    else:
        print(month_trades.sort_values(["jst_entry_time", source_col])[available_cols].to_string(index=False))

    out_dir = PROJECT_ROOT / "data" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_out = out_dir / f"goldsharp_xm_kiwami_gold_abc_v3_{args.month}_summary.csv"
    detail_out = out_dir / f"goldsharp_xm_kiwami_gold_abc_v3_{args.month}_trades.csv"

    summary = summarize_grouped(month_trades, ["jst_entry_hour", source_col])
    summary.to_csv(summary_out, index=False, encoding="utf-8-sig")
    month_trades.to_csv(detail_out, index=False, encoding="utf-8-sig")

    print("\nSaved summary:", summary_out)
    print("Saved detail :", detail_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
