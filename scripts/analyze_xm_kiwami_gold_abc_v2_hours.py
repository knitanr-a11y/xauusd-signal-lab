from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import summarize_trades

DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "goldsharp_xm_kiwami_gold_abc_v2_backtest_trades.csv"


def _normalize_source_col(df: pd.DataFrame) -> str:
    if "combined_signal_source" in df.columns:
        return "combined_signal_source"
    if "signal_source" in df.columns:
        return "signal_source"
    raise ValueError("source column not found. Expected combined_signal_source or signal_source.")


def _ensure_jst_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "jst_entry_time" in out.columns:
        out["jst_entry_time"] = pd.to_datetime(out["jst_entry_time"], errors="coerce")
        out["jst_entry_hour"] = out["jst_entry_time"].dt.hour
        out["jst_entry_month"] = out["jst_entry_time"].dt.to_period("M").astype(str)
    elif "jst_entry_hour" not in out.columns:
        raise ValueError("jst_entry_time or jst_entry_hour column not found.")
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
    parser = argparse.ArgumentParser(description="Analyze XM KIWAMI GOLD ABC v2 trades by JST hour/source/month.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--focus-hours", type=str, default="13,21,22")
    args = parser.parse_args()

    trades_csv = args.trades_csv
    if not trades_csv.is_absolute():
        trades_csv = PROJECT_ROOT / trades_csv

    if not trades_csv.exists():
        print(f"Trades CSV not found: {trades_csv}")
        print("Run first:")
        print("python scripts/run_preset_backtest.py --preset xm_kiwami_gold_abc_v2 --data-dir data/raw/xm_kiwami --save")
        return 1

    trades = pd.read_csv(trades_csv)
    trades = _ensure_jst_columns(trades)
    source_col = _normalize_source_col(trades)
    focus_hours = {int(x.strip()) for x in args.focus_hours.split(",") if x.strip()}

    print(f"Loaded: {trades_csv}")
    print(f"Rows  : {len(trades)}")
    print(f"Focus : {sorted(focus_hours)} JST")

    print_table("OVERALL", pd.DataFrame([summarize_trades(trades)]))
    print_table("BY SOURCE", summarize_grouped(trades, [source_col]), [source_col])
    print_table("BY JST HOUR", summarize_grouped(trades, ["jst_entry_hour"]), ["jst_entry_hour"])
    print_table("BY JST HOUR x SOURCE", summarize_grouped(trades, ["jst_entry_hour", source_col]), ["jst_entry_hour", source_col])
    print_table("BY MONTH", summarize_grouped(trades, ["jst_entry_month"]), ["jst_entry_month"])
    print_table("BY MONTH x SOURCE", summarize_grouped(trades, ["jst_entry_month", source_col]), ["jst_entry_month", source_col])

    focus = trades[trades["jst_entry_hour"].isin(focus_hours)].copy()
    print_table(
        f"FOCUS HOURS {sorted(focus_hours)} - BY JST HOUR x SOURCE",
        summarize_grouped(focus, ["jst_entry_hour", source_col]),
        ["jst_entry_hour", source_col],
    )
    print_table(
        f"FOCUS HOURS {sorted(focus_hours)} - BY MONTH x JST HOUR x SOURCE",
        summarize_grouped(focus, ["jst_entry_month", "jst_entry_hour", source_col]),
        ["jst_entry_month", "jst_entry_hour", source_col],
    )

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
    available_cols = [c for c in cols if c in focus.columns]
    print("\n" + "=" * 120)
    print(f"FOCUS HOURS {sorted(focus_hours)} - TRADES")
    print("=" * 120)
    if focus.empty:
        print("No trades.")
    else:
        print(focus.sort_values(["jst_entry_time", source_col])[available_cols].to_string(index=False))

    out_dir = PROJECT_ROOT / "data" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "goldsharp_xm_kiwami_gold_abc_v2_hour_source_summary.csv"
    summarize_grouped(trades, ["jst_entry_hour", source_col]).to_csv(out_path, index=False, encoding="utf-8-sig")
    print("\nSaved summary:", out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
