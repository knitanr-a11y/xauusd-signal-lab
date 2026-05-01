from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/validate_preset_period_splits.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_combined_abcc2_backtest import run_symbol as run_abcc2_symbol
from scripts.run_combined_abc_backtest import run_symbol as run_abc_symbol
from scripts.run_combined_backtest import parse_csv_list
from src.backtest import summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def summarize_subset(trades: pd.DataFrame, label: str) -> dict[str, object]:
    row = {"split": label}
    row.update(summarize_trades(trades))
    if not trades.empty and "jst_entry_time" in trades.columns:
        row["from_jst"] = trades["jst_entry_time"].min()
        row["to_jst"] = trades["jst_entry_time"].max()
    else:
        row["from_jst"] = pd.NaT
        row["to_jst"] = pd.NaT
    return row


def summarize_by_source(trades: pd.DataFrame, split_label: str) -> pd.DataFrame:
    if trades.empty or "combined_signal_source" not in trades.columns:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for source, group in trades.groupby("combined_signal_source", dropna=False):
        row = {"split": split_label, "source": source}
        row.update(summarize_trades(group))
        rows.append(row)
    return pd.DataFrame(rows)


def filter_by_jst_range(trades: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    if trades.empty:
        return trades
    if "jst_entry_time" not in trades.columns:
        raise ValueError("trades must contain jst_entry_time")
    out = trades.copy()
    t = pd.to_datetime(out["jst_entry_time"])
    if start:
        out = out[t >= pd.Timestamp(start)]
        t = pd.to_datetime(out["jst_entry_time"])
    if end:
        # end is exclusive if a date string is provided. This makes month boundaries clean.
        out = out[t < pd.Timestamp(end)]
    return out


def build_default_splits(trades: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    if trades.empty:
        return [("all", trades)]
    out = trades.copy()
    out["jst_entry_month"] = pd.to_datetime(out["jst_entry_time"]).dt.to_period("M").astype(str)

    splits: list[tuple[str, pd.DataFrame]] = [("all", out)]

    # Simple chronological 70/30 split by trade count.
    ordered = out.sort_values("jst_entry_time", kind="mergesort").reset_index(drop=True)
    cut = int(len(ordered) * 0.70)
    if cut > 0 and cut < len(ordered):
        splits.append(("train_like_first_70pct_by_trade", ordered.iloc[:cut].copy()))
        splits.append(("test_like_last_30pct_by_trade", ordered.iloc[cut:].copy()))

    # Calendar split that matches the current research concern.
    splits.append(("dev_2025_06_to_2026_01", filter_by_jst_range(out, "2025-06-01", "2026-02-01")))
    splits.append(("holdout_2026_02_to_2026_05", filter_by_jst_range(out, "2026-02-01", "2026-05-01")))

    # Quarter-ish recent splits.
    splits.append(("recent_2026_03_to_2026_05", filter_by_jst_range(out, "2026-03-01", "2026-05-01")))
    splits.append(("recent_2026_04", filter_by_jst_range(out, "2026-04-01", "2026-05-01")))

    # Monthly splits.
    for month, group in out.groupby("jst_entry_month", dropna=False):
        splits.append((f"month_{month}", group.copy()))

    return splits


def run_preset(args: argparse.Namespace, symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    enabled = {item.strip().upper() for item in args.models.split(",") if item.strip()}
    if "C2" in enabled:
        return run_abcc2_symbol(args, symbol=symbol)
    if "C" in enabled:
        return run_abc_symbol(args, symbol=symbol)
    raise ValueError("validate_preset_period_splits currently supports presets containing C or C2")


def apply_preset_defaults_for_validation(args: argparse.Namespace) -> argparse.Namespace:
    preset = get_preset(args.preset)
    args.preset_name = preset.name
    args.symbols = args.symbols or preset.symbols
    args.models = args.models or preset.models
    args.near_atr = preset.near_atr if args.near_atr is None else args.near_atr
    args.close_tolerance_atr = preset.close_tolerance_atr if args.close_tolerance_atr is None else args.close_tolerance_atr
    args.swing_left = preset.swing_left if args.swing_left is None else args.swing_left
    args.swing_right = preset.swing_right if args.swing_right is None else args.swing_right
    args.recent_pullback_bars = preset.recent_pullback_bars if args.recent_pullback_bars is None else args.recent_pullback_bars
    args.rr = preset.rr if args.rr is None else args.rr
    args.sl_buffer_atr = preset.sl_buffer_atr if args.sl_buffer_atr is None else args.sl_buffer_atr
    args.server_timezone = preset.server_timezone if args.server_timezone is None else args.server_timezone
    args.server_utc_offset = preset.server_utc_offset if args.server_utc_offset is None else args.server_utc_offset
    args.a_buy_jst_hours = preset.a_buy_jst_hours if args.a_buy_jst_hours is None else args.a_buy_jst_hours
    args.a_sell_jst_hours = preset.a_sell_jst_hours if args.a_sell_jst_hours is None else args.a_sell_jst_hours
    args.a_exclude_hidden_price_delta_atr_lte = preset.a_exclude_hidden_price_delta_atr_lte if args.a_exclude_hidden_price_delta_atr_lte is None else args.a_exclude_hidden_price_delta_atr_lte
    args.b_buy_jst_hours = preset.b_buy_jst_hours if args.b_buy_jst_hours is None else args.b_buy_jst_hours
    args.b_sell_jst_hours = preset.b_sell_jst_hours if args.b_sell_jst_hours is None else args.b_sell_jst_hours
    args.b_exclude_risk_atr_range = preset.b_exclude_risk_atr_range if args.b_exclude_risk_atr_range is None else args.b_exclude_risk_atr_range
    args.b_exclude_macd_hist_delta_abs_range = preset.b_exclude_macd_hist_delta_abs_range if args.b_exclude_macd_hist_delta_abs_range is None else args.b_exclude_macd_hist_delta_abs_range
    args.b_buy_exclude_risk_atr_range = preset.b_buy_exclude_risk_atr_range if args.b_buy_exclude_risk_atr_range is None else args.b_buy_exclude_risk_atr_range
    args.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo = preset.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo if args.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo is None else args.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo

    args.c_breakout_lookback_bars = preset.c_breakout_lookback_bars if args.c_breakout_lookback_bars is None else args.c_breakout_lookback_bars
    args.c_min_breakout_atr = 0.0 if args.c_min_breakout_atr is None else args.c_min_breakout_atr
    args.c_max_breakout_atr = preset.c_max_breakout_atr if hasattr(preset, "c_max_breakout_atr") and args.c_max_breakout_atr is None else args.c_max_breakout_atr
    args.c_buy_jst_hours = preset.c_buy_jst_hours if args.c_buy_jst_hours is None else args.c_buy_jst_hours
    args.c_sell_jst_hours = preset.c_sell_jst_hours if args.c_sell_jst_hours is None else args.c_sell_jst_hours
    args.c_buy_h1_ema_gap_atr_max = preset.c_buy_h1_ema_gap_atr_max if args.c_buy_h1_ema_gap_atr_max is None else args.c_buy_h1_ema_gap_atr_max

    args.c2_range_lookback_bars = preset.c2_range_lookback_bars if args.c2_range_lookback_bars is None else args.c2_range_lookback_bars
    args.c2_max_range_width_atr = preset.c2_max_range_width_atr if args.c2_max_range_width_atr is None else args.c2_max_range_width_atr
    args.c2_min_breakout_atr = preset.c2_min_breakout_atr if args.c2_min_breakout_atr is None else args.c2_min_breakout_atr
    args.c2_max_breakout_atr = preset.c2_max_breakout_atr if args.c2_max_breakout_atr is None else args.c2_max_breakout_atr
    args.c2_buy_jst_hours = preset.c2_buy_jst_hours if args.c2_buy_jst_hours is None else args.c2_buy_jst_hours
    args.c2_sell_jst_hours = preset.c2_sell_jst_hours if args.c2_sell_jst_hours is None else args.c2_sell_jst_hours
    args.c2_disable_buy = preset.c2_disable_buy if args.c2_disable_buy is None else args.c2_disable_buy
    args.c2_disable_sell = preset.c2_disable_sell if args.c2_disable_sell is None else args.c2_disable_sell
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a fixed preset across period splits to check overfitting robustness.")
    parser.add_argument("--preset", type=str, default="gold_abc_v2")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--symbols", type=str, default=None)
    parser.add_argument("--models", type=str, default=None)
    parser.add_argument("--near-atr", type=float, default=None)
    parser.add_argument("--close-tolerance-atr", type=float, default=None)
    parser.add_argument("--swing-left", type=int, default=None)
    parser.add_argument("--swing-right", type=int, default=None)
    parser.add_argument("--recent-pullback-bars", type=int, default=None)
    parser.add_argument("--no-ema20-reclaim", action="store_true")
    parser.add_argument("--no-macd-signal-alignment", action="store_true")
    parser.add_argument("--no-histogram-acceleration", action="store_true")
    parser.add_argument("--rr", type=float, default=None)
    parser.add_argument("--sl-buffer-atr", type=float, default=None)
    parser.add_argument("--server-timezone", type=str, default=None)
    parser.add_argument("--server-utc-offset", type=int, default=None)
    parser.add_argument("--use-fixed-offset", action="store_true")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None)
    parser.add_argument("--a-sell-jst-hours", type=str, default=None)
    parser.add_argument("--a-exclude-hidden-price-delta-atr-lte", type=float, default=None)
    parser.add_argument("--b-buy-jst-hours", type=str, default=None)
    parser.add_argument("--b-sell-jst-hours", type=str, default=None)
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None)
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None)
    parser.add_argument("--b-buy-exclude-risk-atr-range", type=str, default=None)
    parser.add_argument("--b-buy-exclude-risk-atr-macd-hist-delta-abs-combo", type=str, default=None)
    parser.add_argument("--c-breakout-lookback-bars", type=int, default=None)
    parser.add_argument("--c-min-breakout-atr", type=float, default=None)
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
    parser.add_argument("--start", type=str, default=None, help="Optional custom JST start, e.g. 2026-02-01")
    parser.add_argument("--end", type=str, default=None, help="Optional custom JST end exclusive, e.g. 2026-05-01")
    parser.add_argument("--save", action="store_true")
    args = apply_preset_defaults_for_validation(parser.parse_args())

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = parse_csv_list(args.symbols)
    if not symbols:
        print("No symbols provided.")
        return 1

    all_summary_rows: list[dict[str, object]] = []
    all_source_rows: list[pd.DataFrame] = []

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset: {args.preset}")
        print("target: fixed-preset period split validation")

        _df, trades = run_preset(args, symbol=symbol)
        if trades.empty:
            print("No trades.")
            continue
        trades = trades.sort_values("jst_entry_time", kind="mergesort").reset_index(drop=True)

        splits = build_default_splits(trades)
        if args.start or args.end:
            splits.append((f"custom_{args.start or 'BEGIN'}_to_{args.end or 'END'}", filter_by_jst_range(trades, args.start, args.end)))

        summary_rows: list[dict[str, object]] = []
        for label, split_trades in splits:
            row = summarize_subset(split_trades, label)
            row["symbol"] = symbol
            summary_rows.append(row)
            source_df = summarize_by_source(split_trades, label)
            if not source_df.empty:
                source_df["symbol"] = symbol
                all_source_rows.append(source_df)

        summary_df = pd.DataFrame(summary_rows)
        ordered_cols = [
            "symbol",
            "split",
            "from_jst",
            "to_jst",
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
        summary_df = summary_df[[col for col in ordered_cols if col in summary_df.columns]]
        print_table("PERIOD_SPLIT_SUMMARY", summary_df)
        all_summary_rows.extend(summary_rows)

    if all_source_rows:
        source_all = pd.concat(all_source_rows, ignore_index=True)
        ordered_source_cols = [
            "symbol",
            "split",
            "source",
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
        source_all = source_all[[col for col in ordered_source_cols if col in source_all.columns]]
        print_table("PERIOD_SPLIT_BY_SOURCE", source_all)

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / f"{args.preset}_period_split_summary.csv"
        pd.DataFrame(all_summary_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_period_split_summary: {summary_path}")
        if all_source_rows:
            source_path = RESULTS_DATA_DIR / f"{args.preset}_period_split_by_source.csv"
            pd.concat(all_source_rows, ignore_index=True).to_csv(source_path, index=False, encoding="utf-8-sig")
            print(f"saved_period_split_by_source: {source_path}")

    print("=" * 120)
    print("Fixed-preset period split validation completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
