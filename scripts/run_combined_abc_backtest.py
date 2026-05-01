from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/run_combined_abc_backtest.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c_signal_trades import build_c_signal_df
from scripts.compare_combined_abc_c_buy_candidates import (
    apply_abc_candidate,
    attach_combined_sources_to_trades,
    build_ab_v4_combined_df,
    summarize_source_breakdown,
)
from scripts.run_combined_backtest import (
    parse_csv_list,
    print_summary_dict,
    print_trade_report,
)
from scripts.run_combined_backtest_with_a_filters import parse_float_quad
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_by_entry_hour, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RuntimeABCCandidate:
    name: str
    description: str
    c_keep_func: Callable[[pd.DataFrame], pd.Series]


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def _h1_gap_buy_atr(df: pd.DataFrame) -> pd.Series:
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    return h1_gap / atr


def parse_int_set(value: str | None) -> set[int] | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return set()
    return {int(item.strip()) for item in stripped.split(",") if item.strip()}


def build_runtime_candidate(args: argparse.Namespace) -> RuntimeABCCandidate:
    c_buy_hours = parse_int_set(args.c_buy_jst_hours)
    c_sell_hours = parse_int_set(args.c_sell_jst_hours)

    if c_sell_hours:
        raise ValueError("gold_abc_v1 runner currently supports C BUY only. C SELL must be empty.")

    def c_keep(df: pd.DataFrame) -> pd.Series:
        keep = df["c_buy_signal_filtered"].fillna(False).astype(bool)
        if c_buy_hours is not None:
            keep = keep & _jst_hour(df).isin(c_buy_hours)
        if args.c_buy_h1_ema_gap_atr_max is not None:
            keep = keep & _h1_gap_buy_atr(df).le(float(args.c_buy_h1_ema_gap_atr_max))
        return keep.fillna(False).astype(bool)

    return RuntimeABCCandidate(
        name=args.preset_name,
        description="Runtime ABC preset candidate from preset arguments.",
        c_keep_func=c_keep,
    )


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def print_abc_summary(combined_df: pd.DataFrame, trades: pd.DataFrame) -> None:
    print_summary_dict(
        "ABC_signal_summary_filtered",
        {
            "a_buy_signals": int(combined_df["a_buy_signal_filtered"].sum()),
            "a_sell_signals": int(combined_df["a_sell_signal_filtered"].sum()),
            "b_buy_signals": int(combined_df["b_buy_signal_filtered"].sum()),
            "b_sell_signals": int(combined_df["b_sell_signal_filtered"].sum()),
            "c_buy_signals": int(combined_df["c_buy_signal_candidate"].sum()),
            "combined_buy_signals": int(combined_df["combined_buy_signal"].sum()),
            "combined_sell_signals": int(combined_df["combined_sell_signal"].sum()),
            "conflicts_skipped": int(combined_df["combined_signal_conflict"].sum()),
        },
    )
    print_trade_report("COMBINED_A_B_C_TRADES", trades)
    print_summary_dict("summary_by_source_flat", summarize_source_breakdown(trades))

    print_table("summary_by_source", _summary_grouped(trades, ["combined_signal_source"]))
    if "jst_entry_month" in trades.columns:
        print_table("summary_by_month", _summary_grouped(trades, ["jst_entry_month"]))
    print("\nsummary_by_server_entry_hour:")
    by_hour = summarize_by_entry_hour(trades)
    if by_hour.empty:
        print("No trades.")
    else:
        print(by_hour.to_string(index=False))


def _summary_grouped(trades: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
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


def print_recent_trades(trades: pd.DataFrame) -> None:
    display_cols = [
        "combined_signal_source",
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
    available = [col for col in display_cols if col in trades.columns]
    print("\nrecent trades tail(30):")
    if trades.empty:
        print("No trades.")
    else:
        print(trades[available].tail(30).to_string(index=False))


def run_symbol(args: argparse.Namespace, symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    ab_df = build_ab_v4_combined_df(args, symbol=symbol)
    c_df = build_c_signal_df(args, symbol=symbol)
    runtime_candidate = build_runtime_candidate(args)

    # Reuse the candidate applier shape from comparison scripts.
    from scripts.compare_combined_abc_c_buy_candidates import CombinedABCCandidate

    candidate = CombinedABCCandidate(
        name=runtime_candidate.name,
        description=runtime_candidate.description,
        c_keep_func=runtime_candidate.c_keep_func,
    )
    combined_df = apply_abc_candidate(ab_df, c_df, candidate)

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    trades = run_simple_hidden_divergence_backtest(combined_df, settings=settings)
    trades = attach_combined_sources_to_trades(trades, combined_df)
    from scripts.run_combined_backtest import attach_jst_trade_times

    trades = attach_jst_trade_times(trades, args=args)
    if not trades.empty:
        trades["jst_entry_hour"] = trades["jst_entry_time"].dt.hour
        trades["jst_entry_month"] = trades["jst_entry_time"].dt.to_period("M").astype(str)
    return combined_df, trades


def main() -> int:
    parser = argparse.ArgumentParser(description="Run combined A+B+C preset backtest.")
    parser.add_argument("--preset-name", type=str, default="gold_abc_v1")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--symbols", type=str, default="gold")
    parser.add_argument("--models", type=str, default="A,B,C")
    parser.add_argument("--near-atr", type=float, default=0.30)
    parser.add_argument("--close-tolerance-atr", type=float, default=0.50)
    parser.add_argument("--swing-left", type=int, default=3)
    parser.add_argument("--swing-right", type=int, default=2)
    parser.add_argument("--recent-pullback-bars", type=int, default=6)
    parser.add_argument("--no-ema20-reclaim", action="store_true")
    parser.add_argument("--no-macd-signal-alignment", action="store_true")
    parser.add_argument("--no-histogram-acceleration", action="store_true")
    parser.add_argument("--rr", type=float, default=1.5)
    parser.add_argument("--sl-buffer-atr", type=float, default=0.05)
    parser.add_argument("--server-timezone", type=str, default=DEFAULT_MT5_SERVER_TIMEZONE)
    parser.add_argument("--server-utc-offset", type=int, default=3)
    parser.add_argument("--use-fixed-offset", action="store_true")
    parser.add_argument("--a-buy-jst-hours", type=str, default="7,13")
    parser.add_argument("--a-sell-jst-hours", type=str, default="2,13,19")
    parser.add_argument("--a-exclude-hidden-price-delta-atr-lte", type=float, default=None)
    parser.add_argument("--b-buy-jst-hours", type=str, default="20,21,22,23")
    parser.add_argument("--b-sell-jst-hours", type=str, default="10")
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None)
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None)
    parser.add_argument("--b-buy-exclude-risk-atr-range", type=str, default=None)
    parser.add_argument("--b-buy-exclude-risk-atr-macd-hist-delta-abs-combo", type=str, default=None)
    parser.add_argument("--c-breakout-lookback-bars", type=int, default=12)
    parser.add_argument("--c-min-breakout-atr", type=float, default=0.0)
    parser.add_argument("--c-max-breakout-atr", type=float, default=None)
    parser.add_argument("--c-buy-jst-hours", type=str, default="1,5,11,12,15,18,21,22")
    parser.add_argument("--c-sell-jst-hours", type=str, default="")
    parser.add_argument("--c-buy-h1-ema-gap-atr-max", type=float, default=3.623)
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = parse_csv_list(args.symbols)
    if not symbols:
        print("No symbols provided.")
        return 1

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset: {args.preset_name}")
        print(f"models: {args.models}")
        print(f"C BUY JST hours: {args.c_buy_jst_hours or 'NONE'}")
        print(f"C SELL JST hours: {args.c_sell_jst_hours or 'NONE'}")
        print(f"C breakout lookback bars: {args.c_breakout_lookback_bars}")
        print(f"C BUY H1 EMA gap ATR max: {args.c_buy_h1_ema_gap_atr_max}")

        combined_df, trades = run_symbol(args, symbol=symbol)
        print_abc_summary(combined_df, trades)
        print_recent_trades(trades)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol.lower()}_{args.preset_name}_backtest_trades.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_trades: {out_path}")

    print("=" * 120)
    print("Combined A+B+C backtest completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
