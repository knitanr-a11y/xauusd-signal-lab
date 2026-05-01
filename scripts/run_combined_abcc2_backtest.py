from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/run_combined_abcc2_backtest.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c2_signal_trades import build_c2_signal_df
from scripts.compare_combined_abc_v1_c2_sell_candidates import (
    CombinedABCC2Candidate,
    apply_c2_candidate,
    attach_sources_to_trades,
    summarize_source_breakdown,
)
from scripts.run_combined_abc_backtest import run_symbol as run_gold_abc_symbol
from scripts.run_combined_backtest import (
    attach_jst_trade_times,
    parse_csv_list,
    print_summary_dict,
    print_trade_report,
)
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_by_entry_hour, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def parse_int_set(value: str | None) -> set[int] | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "":
        return set()
    return {int(item.strip()) for item in stripped.split(",") if item.strip()}


def build_runtime_c2_candidate(args: argparse.Namespace) -> CombinedABCC2Candidate:
    c2_buy_hours = parse_int_set(args.c2_buy_jst_hours)
    c2_sell_hours = parse_int_set(args.c2_sell_jst_hours)

    if c2_buy_hours and not args.c2_disable_buy:
        raise ValueError("This runner currently supports C2 SELL only. C2 BUY must be disabled or empty.")

    def c2_keep(df: pd.DataFrame) -> pd.Series:
        keep = df["c2_sell_signal_filtered"].fillna(False).astype(bool)
        if args.c2_disable_sell:
            keep = pd.Series(False, index=df.index)
        if c2_sell_hours is not None:
            keep = keep & _jst_hour(df).isin(c2_sell_hours)
        return keep.fillna(False).astype(bool)

    return CombinedABCC2Candidate(
        name=args.preset_name,
        description="Runtime ABCC2 preset candidate from preset arguments.",
        c2_keep_func=c2_keep,
    )


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


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def print_abcc2_summary(combined_df: pd.DataFrame, trades: pd.DataFrame) -> None:
    print_summary_dict(
        "ABCC2_signal_summary_filtered",
        {
            "a_buy_signals": int(combined_df["a_buy_signal_filtered"].sum()),
            "a_sell_signals": int(combined_df["a_sell_signal_filtered"].sum()),
            "b_buy_signals": int(combined_df["b_buy_signal_filtered"].sum()),
            "b_sell_signals": int(combined_df["b_sell_signal_filtered"].sum()),
            "c_buy_signals": int(combined_df["c_buy_signal_candidate"].sum()),
            "c2_sell_signals": int(combined_df["c2_sell_signal_candidate"].sum()),
            "combined_buy_signals": int(combined_df["combined_buy_signal"].sum()),
            "combined_sell_signals": int(combined_df["combined_sell_signal"].sum()),
            "conflicts_skipped": int(combined_df["combined_signal_conflict"].sum()),
        },
    )
    print_trade_report("COMBINED_A_B_C_C2_TRADES", trades)
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
    abc_df, _abc_trades = run_gold_abc_symbol(args, symbol=symbol)
    c2_df = build_c2_signal_df(args, symbol=symbol)
    candidate = build_runtime_c2_candidate(args)
    combined_df = apply_c2_candidate(abc_df, c2_df, candidate)

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    trades = run_simple_hidden_divergence_backtest(combined_df, settings=settings)
    trades = attach_sources_to_trades(trades, combined_df)
    trades = attach_jst_trade_times(trades, args=args)
    if not trades.empty:
        trades["jst_entry_hour"] = trades["jst_entry_time"].dt.hour
        trades["jst_entry_month"] = trades["jst_entry_time"].dt.to_period("M").astype(str)
    return combined_df, trades


def apply_preset_c2_defaults(args: argparse.Namespace) -> argparse.Namespace:
    preset = get_preset(args.preset_name)
    if args.models is None:
        args.models = preset.models
    if args.c_breakout_lookback_bars is None:
        args.c_breakout_lookback_bars = preset.c_breakout_lookback_bars or 12
    if args.c_buy_jst_hours is None:
        args.c_buy_jst_hours = preset.c_buy_jst_hours
    if args.c_sell_jst_hours is None:
        args.c_sell_jst_hours = preset.c_sell_jst_hours
    if args.c_buy_h1_ema_gap_atr_max is None:
        args.c_buy_h1_ema_gap_atr_max = preset.c_buy_h1_ema_gap_atr_max
    if args.c2_range_lookback_bars is None:
        args.c2_range_lookback_bars = preset.c2_range_lookback_bars or 12
    if args.c2_max_range_width_atr is None:
        args.c2_max_range_width_atr = preset.c2_max_range_width_atr or 2.50
    if args.c2_min_breakout_atr is None:
        args.c2_min_breakout_atr = preset.c2_min_breakout_atr or 0.0
    if args.c2_max_breakout_atr is None:
        args.c2_max_breakout_atr = preset.c2_max_breakout_atr
    if args.c2_buy_jst_hours is None:
        args.c2_buy_jst_hours = preset.c2_buy_jst_hours
    if args.c2_sell_jst_hours is None:
        args.c2_sell_jst_hours = preset.c2_sell_jst_hours
    args.c2_disable_buy = preset.c2_disable_buy if args.c2_disable_buy is None else args.c2_disable_buy
    args.c2_disable_sell = preset.c2_disable_sell if args.c2_disable_sell is None else args.c2_disable_sell
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Run combined A+B+C+C2 preset backtest.")
    parser.add_argument("--preset-name", type=str, default="gold_abc_v2")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--symbols", type=str, default="gold")
    parser.add_argument("--models", type=str, default=None)
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
    parser.add_argument("--c-breakout-lookback-bars", type=int, default=None)
    parser.add_argument("--c-min-breakout-atr", type=float, default=0.0)
    parser.add_argument("--c-max-breakout-atr", type=float, default=None)
    parser.add_argument("--c-buy-jst-hours", type=str, default=None)
    parser.add_argument("--c-sell-jst-hours", type=str, default=None)
    parser.add_argument("--c-buy-h1-ema-gap-atr-max", type=float, default=None)
    parser.add_argument("--c-no-h1-trend", action="store_true")
    parser.add_argument("--c-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c-allow-ab-overlap", action="store_true")
    parser.add_argument("--c2-range-lookback-bars", type=int, default=None)
    parser.add_argument("--c2-max-range-width-atr", type=float, default=None)
    parser.add_argument("--c2-min-breakout-atr", type=float, default=None)
    parser.add_argument("--c2-max-breakout-atr", type=float, default=None)
    parser.add_argument("--c2-buy-jst-hours", type=str, default=None)
    parser.add_argument("--c2-sell-jst-hours", type=str, default=None)
    parser.add_argument("--c2-disable-buy", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--c2-disable-sell", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--c2-no-h1-trend", action="store_true")
    parser.add_argument("--c2-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c2-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c2-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c2-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c2-allow-ab-overlap", action="store_true")
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None)
    parser.add_argument("--save", action="store_true")
    args = apply_preset_c2_defaults(parser.parse_args())

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
        print(f"C BUY H1 EMA gap ATR max: {args.c_buy_h1_ema_gap_atr_max}")
        print(f"C2 BUY JST hours: {args.c2_buy_jst_hours or 'NONE'}")
        print(f"C2 SELL JST hours: {args.c2_sell_jst_hours or 'NONE'}")
        print(f"C2 range lookback bars: {args.c2_range_lookback_bars}")
        print(f"C2 max range width ATR: {args.c2_max_range_width_atr}")

        combined_df, trades = run_symbol(args, symbol=symbol)
        print_abcc2_summary(combined_df, trades)
        print_recent_trades(trades)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol.lower()}_{args.preset_name}_backtest_trades.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_trades: {out_path}")

    print("=" * 120)
    print("Combined A+B+C+C2 backtest completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
