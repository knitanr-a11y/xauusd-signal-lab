from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_c2_signal_trades.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped, summarize_numeric_bins
from scripts.run_combined_backtest import attach_jst_trade_times, build_base_dataframe, build_paths, parse_int_csv
from scripts.run_combined_backtest_with_a_filters import apply_a_filters
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.range_compression_breakout import (
    RangeCompressionBreakoutSettings,
    add_range_compression_breakout_signals,
    range_compression_breakout_summary,
)


def print_dict(title: str, data: dict[str, object]) -> None:
    print(f"\n{title}:")
    for key, value in data.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def print_section(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    if max_rows is not None:
        df = df.head(max_rows)
    print(df.to_string(index=False))


def build_c2_signal_df(args: argparse.Namespace, symbol: str) -> pd.DataFrame:
    m15_path, h1_path = build_paths(args.data_dir, symbol)
    if not m15_path.exists():
        raise FileNotFoundError(f"M15 file not found: {m15_path}")
    if not h1_path.exists():
        raise FileNotFoundError(f"H1 file not found: {h1_path}")

    base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)
    base_df = apply_a_filters(base_df, args=args)

    settings = RangeCompressionBreakoutSettings(
        range_lookback_bars=args.c2_range_lookback_bars,
        max_range_width_atr=args.c2_max_range_width_atr,
        min_breakout_atr=args.c2_min_breakout_atr,
        max_breakout_atr=args.c2_max_breakout_atr,
        require_h1_trend=not args.c2_no_h1_trend,
        require_m15_ema_alignment=not args.c2_no_m15_ema_alignment,
        require_close_beyond_ema20=not args.c2_no_close_beyond_ema20,
        require_macd_hist_direction=not args.c2_no_macd_hist_direction,
        require_macd_hist_acceleration=not args.c2_no_macd_hist_acceleration,
        avoid_ab_overlap=not args.c2_allow_ab_overlap,
    )
    out = add_range_compression_breakout_signals(base_df, settings=settings)

    buy_hours = parse_int_csv(args.c2_buy_jst_hours)
    sell_hours = parse_int_csv(args.c2_sell_jst_hours)
    hours = pd.to_numeric(out["jst_hour"], errors="coerce").astype("Int64")

    buy = out["c2_buy_signal"].astype(bool)
    sell = out["c2_sell_signal"].astype(bool)
    if args.c2_disable_buy:
        buy = pd.Series(False, index=out.index)
    if args.c2_disable_sell:
        sell = pd.Series(False, index=out.index)
    if buy_hours is not None:
        buy = buy & hours.isin(buy_hours)
    if sell_hours is not None:
        sell = sell & hours.isin(sell_hours)

    conflict = buy & sell
    out["c2_buy_signal_filtered"] = buy & ~conflict
    out["c2_sell_signal_filtered"] = sell & ~conflict
    out["c2_signal_filtered_conflict"] = conflict
    out["c2_signal_filtered"] = out["c2_buy_signal_filtered"] | out["c2_sell_signal_filtered"]
    out["c2_signal_side_filtered"] = "NONE"
    out.loc[out["c2_buy_signal_filtered"], "c2_signal_side_filtered"] = "BUY"
    out.loc[out["c2_sell_signal_filtered"], "c2_signal_side_filtered"] = "SELL"

    out["original_hidden_bullish_divergence"] = out["hidden_bullish_divergence"]
    out["original_hidden_bearish_divergence"] = out["hidden_bearish_divergence"]
    out["hidden_bullish_divergence"] = out["c2_buy_signal_filtered"]
    out["hidden_bearish_divergence"] = out["c2_sell_signal_filtered"]
    return out


def enrich_c2_trades(trades: pd.DataFrame, signal_df: pd.DataFrame, early_loss_bars: int, long_hold_bars: int) -> pd.DataFrame:
    if trades.empty:
        return trades

    feature_cols = [
        "time",
        "jst_time",
        "jst_hour",
        "open",
        "high",
        "low",
        "close",
        "ema_20",
        "ema_50",
        "atr_14",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "c2_macd_hist_delta",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "c2_previous_range_high",
        "c2_previous_range_low",
        "c2_previous_range_width",
        "c2_previous_range_width_atr",
        "c2_range_compressed",
        "c2_buy_breakout_distance",
        "c2_sell_breakout_distance",
        "c2_buy_breakout_distance_atr",
        "c2_sell_breakout_distance_atr",
        "c2_buy_signal_filtered",
        "c2_sell_signal_filtered",
        "buy_reacceleration_signal",
        "sell_reacceleration_signal",
        "original_hidden_bullish_divergence",
        "original_hidden_bearish_divergence",
    ]
    available = [col for col in feature_cols if col in signal_df.columns]
    signal_features = signal_df[available].copy()
    signal_features["signal_index"] = signal_df.index
    signal_features = signal_features.add_prefix("signal_")
    signal_features = signal_features.rename(columns={"signal_signal_index": "signal_index"})
    out = trades.merge(signal_features, on="signal_index", how="left")

    out["win"] = out["result"].eq("win")
    out["loss"] = out["result"].eq("loss")
    out["early_loss"] = out["loss"] & (pd.to_numeric(out["bars_held"], errors="coerce") <= early_loss_bars)
    out["long_hold_loss"] = out["loss"] & (pd.to_numeric(out["bars_held"], errors="coerce") >= long_hold_bars)
    out["risk_atr_ratio"] = pd.to_numeric(out["risk"], errors="coerce") / pd.to_numeric(out["signal_atr_14"], errors="coerce")

    out["breakout_distance_atr"] = pd.NA
    out.loc[out["side"].eq("BUY"), "breakout_distance_atr"] = out.loc[out["side"].eq("BUY"), "signal_c2_buy_breakout_distance_atr"]
    out.loc[out["side"].eq("SELL"), "breakout_distance_atr"] = out.loc[out["side"].eq("SELL"), "signal_c2_sell_breakout_distance_atr"]
    out["breakout_distance_atr"] = pd.to_numeric(out["breakout_distance_atr"], errors="coerce")

    h1_gap = pd.to_numeric(out.get("signal_h1_ema_20", pd.Series(index=out.index)), errors="coerce") - pd.to_numeric(
        out.get("signal_h1_ema_50", pd.Series(index=out.index)), errors="coerce"
    )
    out["h1_ema_gap_side_signed_atr"] = h1_gap / pd.to_numeric(out["signal_atr_14"], errors="coerce")
    out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed_atr"] = -out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed_atr"]

    out["ab_overlap_at_signal"] = False
    for col in [
        "signal_original_hidden_bullish_divergence",
        "signal_original_hidden_bearish_divergence",
        "signal_buy_reacceleration_signal",
        "signal_sell_reacceleration_signal",
    ]:
        if col in out.columns:
            out["ab_overlap_at_signal"] = out["ab_overlap_at_signal"] | out[col].fillna(False).astype(bool)

    if "jst_entry_time" in out.columns:
        out["jst_entry_hour"] = out["jst_entry_time"].dt.hour
        out["jst_entry_month"] = out["jst_entry_time"].dt.to_period("M").astype(str)
    return out


def print_c2_diagnostics(trades: pd.DataFrame) -> None:
    print_dict("C2_trade_summary", summarize_trades(trades))
    print_section("C2_summary_by_side", summarize_grouped(trades, ["side"]))
    print_section("C2_summary_by_jst_entry_hour", summarize_grouped(trades, ["jst_entry_hour"]))
    print_section("C2_summary_by_side_and_jst_entry_hour", summarize_grouped(trades, ["side", "jst_entry_hour"]))
    print_section("C2_summary_by_h1_trend", summarize_grouped(trades, ["signal_h1_trend"]))
    print_section("C2_summary_by_month", summarize_grouped(trades, ["jst_entry_month"]))
    print_section("C2_early_loss_by_side", summarize_grouped(trades, ["side", "early_loss"]))
    print_section("C2_long_hold_loss_by_side", summarize_grouped(trades, ["side", "long_hold_loss"]))
    print_section("C2_ab_overlap_summary", summarize_grouped(trades, ["ab_overlap_at_signal"]))

    for col in [
        "risk_atr_ratio",
        "breakout_distance_atr",
        "signal_c2_previous_range_width_atr",
        "signal_c2_macd_hist_delta",
        "h1_ema_gap_side_signed_atr",
        "bars_held",
    ]:
        print_section(f"C2_quartile_by_{col}", summarize_numeric_bins(trades, col, bins=4))

    display_cols = [
        "side",
        "signal_time",
        "jst_entry_time",
        "entry_price",
        "sl",
        "tp",
        "risk",
        "result",
        "r",
        "bars_held",
        "early_loss",
        "long_hold_loss",
        "risk_atr_ratio",
        "breakout_distance_atr",
        "signal_c2_previous_range_width_atr",
        "signal_c2_macd_hist_delta",
        "h1_ema_gap_side_signed_atr",
        "ab_overlap_at_signal",
    ]
    available = [col for col in display_cols if col in trades.columns]
    print_section("C2_recent_losses_tail_60", trades[trades["result"].eq("loss")][available].tail(60))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze C2 range-compression breakout signal trades.")
    parser.add_argument("--preset", type=str, default="gold_abc_v1", help="Preset context. Default: gold_abc_v1")
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
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None)

    parser.add_argument("--c2-range-lookback-bars", type=int, default=12)
    parser.add_argument("--c2-max-range-width-atr", type=float, default=2.50)
    parser.add_argument("--c2-min-breakout-atr", type=float, default=0.0)
    parser.add_argument("--c2-max-breakout-atr", type=float, default=None)
    parser.add_argument("--c2-buy-jst-hours", type=str, default=None)
    parser.add_argument("--c2-sell-jst-hours", type=str, default=None)
    parser.add_argument("--c2-disable-buy", action="store_true", default=True)
    parser.add_argument("--c2-enable-buy", dest="c2_disable_buy", action="store_false")
    parser.add_argument("--c2-disable-sell", action="store_true")
    parser.add_argument("--c2-no-h1-trend", action="store_true")
    parser.add_argument("--c2-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c2-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c2-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c2-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c2-allow-ab-overlap", action="store_true")
    parser.add_argument("--early-loss-bars", type=int, default=2)
    parser.add_argument("--long-hold-bars", type=int, default=20)
    parser.add_argument("--save", action="store_true")
    args = apply_preset_defaults(parser.parse_args())

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = [item.strip().lower() for item in args.symbols.split(",") if item.strip()]
    if not symbols:
        print("No symbols provided.")
        return 1

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset_context: {args.preset}")
        print("target: C2 range-compression breakout standalone")
        print(f"c2_range_lookback_bars: {args.c2_range_lookback_bars}")
        print(f"c2_max_range_width_atr: {args.c2_max_range_width_atr}")
        print(f"c2_disable_buy: {args.c2_disable_buy}")
        print(f"c2_disable_sell: {args.c2_disable_sell}")

        signal_df = build_c2_signal_df(args, symbol=symbol)
        print_dict("C2_signal_summary_before_side_hour_filter", range_compression_breakout_summary(signal_df))
        print_dict(
            "C2_signal_summary_after_side_hour_filter",
            {
                "c2_buy_filtered": int(signal_df["c2_buy_signal_filtered"].sum()),
                "c2_sell_filtered": int(signal_df["c2_sell_signal_filtered"].sum()),
                "c2_total_filtered": int(signal_df["c2_signal_filtered"].sum()),
                "c2_conflicts_skipped": int(signal_df["c2_signal_filtered_conflict"].sum()),
            },
        )

        settings = BacktestSettings(
            rr=args.rr,
            sl_buffer_atr_multiplier=args.sl_buffer_atr,
            conservative_same_bar=not args.same_bar_win,
            max_bars_in_trade=args.max_bars_in_trade,
        )
        trades = run_simple_hidden_divergence_backtest(signal_df, settings=settings)
        trades = attach_jst_trade_times(trades, args=args)
        trades = enrich_c2_trades(trades, signal_df, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)
        print_c2_diagnostics(trades)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol}_c2_signal_trades_{args.preset}.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_c2_signal_trades: {out_path}")

    print("=" * 120)
    print("C2 range-compression breakout diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
