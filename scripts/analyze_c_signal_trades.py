from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_c_signal_trades.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped, summarize_numeric_bins
from scripts.run_combined_backtest import (
    attach_jst_trade_times,
    build_base_dataframe,
    build_paths,
    parse_int_csv,
)
from scripts.run_combined_backtest_with_a_filters import apply_a_filters
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.breakout_continuation import (
    BreakoutContinuationSettings,
    add_breakout_continuation_signals,
    breakout_continuation_summary,
)
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset


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


def build_c_signal_df(args: argparse.Namespace, symbol: str) -> pd.DataFrame:
    m15_path, h1_path = build_paths(args.data_dir, symbol)
    if not m15_path.exists():
        raise FileNotFoundError(f"M15 file not found: {m15_path}")
    if not h1_path.exists():
        raise FileNotFoundError(f"H1 file not found: {h1_path}")

    base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)
    # Apply A filters only so overlap diagnostics reflect the frozen AB baseline concept.
    # C itself is still backtested independently below.
    base_df = apply_a_filters(base_df, args=args)

    c_settings = BreakoutContinuationSettings(
        breakout_lookback_bars=args.c_breakout_lookback_bars,
        min_breakout_atr=args.c_min_breakout_atr,
        max_breakout_atr=args.c_max_breakout_atr,
        require_h1_trend=not args.c_no_h1_trend,
        require_m15_ema_alignment=not args.c_no_m15_ema_alignment,
        require_close_beyond_ema20=not args.c_no_close_beyond_ema20,
        require_macd_hist_direction=not args.c_no_macd_hist_direction,
        require_macd_hist_acceleration=not args.c_no_macd_hist_acceleration,
        avoid_ab_overlap=not args.c_allow_ab_overlap,
    )
    out = add_breakout_continuation_signals(base_df, settings=c_settings)

    c_buy_hours = parse_int_csv(args.c_buy_jst_hours)
    c_sell_hours = parse_int_csv(args.c_sell_jst_hours)
    hours = pd.to_numeric(out["jst_hour"], errors="coerce").astype("Int64")

    c_buy = out["c_buy_signal"].astype(bool)
    c_sell = out["c_sell_signal"].astype(bool)
    if c_buy_hours is not None:
        c_buy = c_buy & hours.isin(c_buy_hours)
    if c_sell_hours is not None:
        c_sell = c_sell & hours.isin(c_sell_hours)

    conflict = c_buy & c_sell
    out["c_buy_signal_filtered"] = c_buy & ~conflict
    out["c_sell_signal_filtered"] = c_sell & ~conflict
    out["c_signal_filtered_conflict"] = conflict
    out["c_signal_filtered"] = out["c_buy_signal_filtered"] | out["c_sell_signal_filtered"]
    out["c_signal_side_filtered"] = "NONE"
    out.loc[out["c_buy_signal_filtered"], "c_signal_side_filtered"] = "BUY"
    out.loc[out["c_sell_signal_filtered"], "c_signal_side_filtered"] = "SELL"

    # Map C into the existing backtest engine signal columns.
    out["original_hidden_bullish_divergence"] = out["hidden_bullish_divergence"]
    out["original_hidden_bearish_divergence"] = out["hidden_bearish_divergence"]
    out["hidden_bullish_divergence"] = out["c_buy_signal_filtered"]
    out["hidden_bearish_divergence"] = out["c_sell_signal_filtered"]
    return out


def enrich_c_trades(trades: pd.DataFrame, signal_df: pd.DataFrame, early_loss_bars: int, long_hold_bars: int) -> pd.DataFrame:
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
        "c_macd_hist_delta",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "c_previous_range_high",
        "c_previous_range_low",
        "c_previous_range_width",
        "c_previous_range_width_atr",
        "c_buy_breakout_distance",
        "c_sell_breakout_distance",
        "c_buy_breakout_distance_atr",
        "c_sell_breakout_distance_atr",
        "c_buy_signal_filtered",
        "c_sell_signal_filtered",
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
    out.loc[out["side"].eq("BUY"), "breakout_distance_atr"] = out.loc[out["side"].eq("BUY"), "signal_c_buy_breakout_distance_atr"]
    out.loc[out["side"].eq("SELL"), "breakout_distance_atr"] = out.loc[out["side"].eq("SELL"), "signal_c_sell_breakout_distance_atr"]
    out["breakout_distance_atr"] = pd.to_numeric(out["breakout_distance_atr"], errors="coerce")

    h1_gap = pd.to_numeric(out.get("signal_h1_ema_20", pd.Series(index=out.index)), errors="coerce") - pd.to_numeric(
        out.get("signal_h1_ema_50", pd.Series(index=out.index)), errors="coerce"
    )
    out["h1_ema_gap_side_signed_atr"] = h1_gap / pd.to_numeric(out["signal_atr_14"], errors="coerce")
    out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed_atr"] = -out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed_atr"]

    out["ab_overlap_at_signal"] = False
    if "signal_original_hidden_bullish_divergence" in out.columns:
        out["ab_overlap_at_signal"] = out["ab_overlap_at_signal"] | out["signal_original_hidden_bullish_divergence"].fillna(False).astype(bool)
    if "signal_original_hidden_bearish_divergence" in out.columns:
        out["ab_overlap_at_signal"] = out["ab_overlap_at_signal"] | out["signal_original_hidden_bearish_divergence"].fillna(False).astype(bool)
    if "signal_buy_reacceleration_signal" in out.columns:
        out["ab_overlap_at_signal"] = out["ab_overlap_at_signal"] | out["signal_buy_reacceleration_signal"].fillna(False).astype(bool)
    if "signal_sell_reacceleration_signal" in out.columns:
        out["ab_overlap_at_signal"] = out["ab_overlap_at_signal"] | out["signal_sell_reacceleration_signal"].fillna(False).astype(bool)

    if "jst_entry_time" in out.columns:
        out["jst_entry_hour"] = out["jst_entry_time"].dt.hour
        out["jst_entry_month"] = out["jst_entry_time"].dt.to_period("M").astype(str)
    return out


def print_c_diagnostics(trades: pd.DataFrame) -> None:
    print_dict("C_trade_summary", summarize_trades(trades))
    print_section("C_summary_by_side", summarize_grouped(trades, ["side"]))
    print_section("C_summary_by_jst_entry_hour", summarize_grouped(trades, ["jst_entry_hour"]))
    print_section("C_summary_by_side_and_jst_entry_hour", summarize_grouped(trades, ["side", "jst_entry_hour"]))
    print_section("C_summary_by_h1_trend", summarize_grouped(trades, ["signal_h1_trend"]))
    print_section("C_summary_by_month", summarize_grouped(trades, ["jst_entry_month"]))
    print_section("C_early_loss_by_side", summarize_grouped(trades, ["side", "early_loss"]))
    print_section("C_long_hold_loss_by_side", summarize_grouped(trades, ["side", "long_hold_loss"]))
    print_section("C_ab_overlap_summary", summarize_grouped(trades, ["ab_overlap_at_signal"]))

    for col in [
        "risk_atr_ratio",
        "breakout_distance_atr",
        "signal_c_previous_range_width_atr",
        "signal_c_macd_hist_delta",
        "h1_ema_gap_side_signed_atr",
        "bars_held",
    ]:
        print_section(f"C_quartile_by_{col}", summarize_numeric_bins(trades, col, bins=4))

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
        "signal_c_previous_range_width_atr",
        "signal_c_macd_hist_delta",
        "h1_ema_gap_side_signed_atr",
        "ab_overlap_at_signal",
    ]
    available = [col for col in display_cols if col in trades.columns]
    print_section("C_recent_losses_tail_40", trades[trades["result"].eq("loss")][available].tail(40))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze C breakout-continuation signal trades.")
    parser.add_argument("--preset", type=str, default="gold_ab_v4", help="Preset used for shared indicator/settings context. Default: gold_ab_v4")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--models", type=str, default=None, help="Default: from preset")
    parser.add_argument("--near-atr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--close-tolerance-atr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--swing-left", type=int, default=None, help="Default: from preset")
    parser.add_argument("--swing-right", type=int, default=None, help="Default: from preset")
    parser.add_argument("--recent-pullback-bars", type=int, default=None, help="Default: from preset")
    parser.add_argument("--no-ema20-reclaim", action="store_true")
    parser.add_argument("--no-macd-signal-alignment", action="store_true")
    parser.add_argument("--no-histogram-acceleration", action="store_true")
    parser.add_argument("--rr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--sl-buffer-atr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--server-timezone", type=str, default=None, help="Default: from preset")
    parser.add_argument("--server-utc-offset", type=int, default=None, help="Default: from preset")
    parser.add_argument("--use-fixed-offset", action="store_true")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--a-sell-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--a-exclude-hidden-price-delta-atr-lte", type=float, default=None, help="Default: from preset")
    parser.add_argument("--b-buy-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-sell-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None, help="Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Default: from preset")

    parser.add_argument("--c-breakout-lookback-bars", type=int, default=12, help="Previous N bars for breakout range. Default: 12")
    parser.add_argument("--c-min-breakout-atr", type=float, default=0.0, help="Minimum breakout distance in ATR. Default: 0.0")
    parser.add_argument("--c-max-breakout-atr", type=float, default=None, help="Maximum breakout distance in ATR. Default: None")
    parser.add_argument("--c-buy-jst-hours", type=str, default=None, help="C BUY JST hours. Default: all")
    parser.add_argument("--c-sell-jst-hours", type=str, default=None, help="C SELL JST hours. Default: all")
    parser.add_argument("--c-no-h1-trend", action="store_true")
    parser.add_argument("--c-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c-allow-ab-overlap", action="store_true")
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Default: 2")
    parser.add_argument("--long-hold-bars", type=int, default=20, help="Default: 20")
    parser.add_argument("--save", action="store_true", help="Save enriched C trades CSV to data/results.")
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
        print("target: C breakout-continuation standalone")
        print(f"c_breakout_lookback_bars: {args.c_breakout_lookback_bars}")
        print(f"c_min_breakout_atr: {args.c_min_breakout_atr}")
        print(f"c_max_breakout_atr: {args.c_max_breakout_atr}")
        print(f"c_buy_jst_hours: {args.c_buy_jst_hours or 'ALL'}")
        print(f"c_sell_jst_hours: {args.c_sell_jst_hours or 'ALL'}")
        print(f"c_avoid_ab_overlap: {not args.c_allow_ab_overlap}")

        signal_df = build_c_signal_df(args, symbol=symbol)
        print_dict("C_signal_summary_before_hour_filter", breakout_continuation_summary(signal_df))
        print_dict(
            "C_signal_summary_after_hour_filter",
            {
                "c_buy_filtered": int(signal_df["c_buy_signal_filtered"].sum()),
                "c_sell_filtered": int(signal_df["c_sell_signal_filtered"].sum()),
                "c_total_filtered": int(signal_df["c_signal_filtered"].sum()),
                "c_conflicts_skipped": int(signal_df["c_signal_filtered_conflict"].sum()),
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
        trades = enrich_c_trades(trades, signal_df, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)
        print_c_diagnostics(trades)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol}_c_signal_trades_{args.preset}.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_c_signal_trades: {out_path}")

    print("=" * 120)
    print("C breakout-continuation diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
