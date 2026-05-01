from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/run_combined_backtest_with_a_filters.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_combined_backtest import (
    add_combined_signal_columns,
    attach_signal_sources_to_trades,
    attach_jst_trade_times,
    build_base_dataframe,
    build_paths,
    combined_signal_summary,
    parse_csv_list,
    parse_float_range,
    parse_int_csv,
    print_summary_dict,
    print_time_conversion_info,
    print_trade_report,
)
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_by_entry_hour
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.divergence import hidden_divergence_summary
from src.pullback import pullback_summary
from src.reacceleration import reacceleration_summary
from src.swings import swing_summary
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE


def parse_float_quad(value: str | None) -> tuple[float, float, float, float] | None:
    if value is None or value.strip() == "":
        return None
    parts = [item.strip() for item in value.split(",") if item.strip()]
    if len(parts) != 4:
        raise ValueError(
            "Quad range must be four comma-separated numbers: "
            "risk_low,risk_high,macd_low,macd_high"
        )
    risk_low, risk_high, macd_low, macd_high = [float(item) for item in parts]
    if risk_low > risk_high:
        raise ValueError(f"risk_low must be <= risk_high: {value}")
    if macd_low > macd_high:
        raise ValueError(f"macd_low must be <= macd_high: {value}")
    return risk_low, risk_high, macd_low, macd_high


def _side_aware_hidden_price_delta_atr(df: pd.DataFrame, side: str) -> pd.Series:
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    if side == "BUY":
        return pd.to_numeric(df["bullish_hidden_price_delta"], errors="coerce") / atr
    if side == "SELL":
        return pd.to_numeric(df["bearish_hidden_price_delta"], errors="coerce") / atr
    raise ValueError(f"Unknown side: {side}")


def apply_a_filters(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Apply A-only candidate filters before A/B combination.

    The filtered A columns are still passed through the existing combined-signal
    builder, so B filters and one-trade-at-a-time backtest behavior remain exactly
    the same as run_combined_backtest.py.
    """
    out = df.copy()

    if args.a_exclude_hidden_price_delta_atr_lte is None:
        out["a_hidden_price_delta_atr_buy"] = _side_aware_hidden_price_delta_atr(out, "BUY")
        out["a_hidden_price_delta_atr_sell"] = _side_aware_hidden_price_delta_atr(out, "SELL")
        out["a_hidden_price_delta_atr_filtered_out"] = False
        return out

    threshold = float(args.a_exclude_hidden_price_delta_atr_lte)
    buy_value = _side_aware_hidden_price_delta_atr(out, "BUY")
    sell_value = _side_aware_hidden_price_delta_atr(out, "SELL")

    buy_signal = out["hidden_bullish_divergence"].astype(bool)
    sell_signal = out["hidden_bearish_divergence"].astype(bool)

    buy_keep = buy_value.gt(threshold).fillna(False)
    sell_keep = sell_value.gt(threshold).fillna(False)

    out["a_hidden_price_delta_atr_buy"] = buy_value
    out["a_hidden_price_delta_atr_sell"] = sell_value
    out["a_hidden_price_delta_atr_filtered_out"] = (buy_signal & ~buy_keep) | (sell_signal & ~sell_keep)

    out["hidden_bullish_divergence"] = buy_signal & buy_keep
    out["hidden_bearish_divergence"] = sell_signal & sell_keep
    out["hidden_divergence_side"] = "NONE"
    out.loc[out["hidden_bullish_divergence"], "hidden_divergence_side"] = "BUY"
    out.loc[out["hidden_bearish_divergence"], "hidden_divergence_side"] = "SELL"
    out["both_hidden_divergences"] = out["hidden_bullish_divergence"] & out["hidden_bearish_divergence"]
    return out


def apply_b_buy_extra_filters(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Apply B BUY-only extra filters after base A/B combination.

    Existing B filters remain in add_combined_signal_columns(). This function only
    removes additional BUY-side B signals and then rebuilds the combined signal
    columns consumed by the backtest engine.
    """
    out = df.copy()
    b_buy = out["b_buy_signal_filtered"].astype(bool)
    remove = pd.Series(False, index=out.index)

    risk = pd.to_numeric(out["b_buy_risk_atr_ratio"], errors="coerce")
    macd = pd.to_numeric(out["b_macd_hist_delta_abs"], errors="coerce")

    risk_range = parse_float_range(args.b_buy_exclude_risk_atr_range)
    if risk_range is not None:
        low, high = risk_range
        remove = remove | (risk.gt(low) & risk.le(high))

    combo = parse_float_quad(args.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo)
    if combo is not None:
        risk_low, risk_high, macd_low, macd_high = combo
        remove = remove | (
            risk.gt(risk_low)
            & risk.le(risk_high)
            & macd.gt(macd_low)
            & macd.le(macd_high)
        )

    remove = remove.fillna(False).astype(bool) & b_buy
    out["b_buy_extra_filtered_out"] = remove
    out["b_buy_signal_filtered"] = b_buy & ~remove

    a_buy = out["a_buy_signal_filtered"].astype(bool)
    a_sell = out["a_sell_signal_filtered"].astype(bool)
    b_buy = out["b_buy_signal_filtered"].astype(bool)
    b_sell = out["b_sell_signal_filtered"].astype(bool)

    combined_buy = a_buy | b_buy
    combined_sell = a_sell | b_sell
    conflict = combined_buy & combined_sell

    out["combined_signal_conflict"] = conflict
    out["combined_buy_signal"] = combined_buy & ~conflict
    out["combined_sell_signal"] = combined_sell & ~conflict

    out["combined_signal_source"] = "NONE"
    out.loc[out["combined_buy_signal"] & a_buy & ~b_buy, "combined_signal_source"] = "A"
    out.loc[out["combined_sell_signal"] & a_sell & ~b_sell, "combined_signal_source"] = "A"
    out.loc[out["combined_buy_signal"] & b_buy & ~a_buy, "combined_signal_source"] = "B"
    out.loc[out["combined_sell_signal"] & b_sell & ~a_sell, "combined_signal_source"] = "B"
    out.loc[out["combined_buy_signal"] & a_buy & b_buy, "combined_signal_source"] = "A+B"
    out.loc[out["combined_sell_signal"] & a_sell & b_sell, "combined_signal_source"] = "A+B"

    out["combined_signal_side"] = "NONE"
    out.loc[out["combined_buy_signal"], "combined_signal_side"] = "BUY"
    out.loc[out["combined_sell_signal"], "combined_signal_side"] = "SELL"

    out["hidden_bullish_divergence"] = out["combined_buy_signal"]
    out["hidden_bearish_divergence"] = out["combined_sell_signal"]
    return out


def print_backtest_report(symbol: str, m15_path: Path, h1_path: Path, args: argparse.Namespace) -> None:
    a_buy_hours = parse_int_csv(args.a_buy_jst_hours)
    a_sell_hours = parse_int_csv(args.a_sell_jst_hours)
    b_buy_hours = parse_int_csv(args.b_buy_jst_hours)
    b_sell_hours = parse_int_csv(args.b_sell_jst_hours)
    b_exclude_risk_atr_range = parse_float_range(args.b_exclude_risk_atr_range)
    b_exclude_macd_hist_delta_abs_range = parse_float_range(args.b_exclude_macd_hist_delta_abs_range)
    b_buy_exclude_risk_atr_range = parse_float_range(args.b_buy_exclude_risk_atr_range)
    b_buy_exclude_combo = parse_float_quad(args.b_buy_exclude_risk_atr_macd_hist_delta_abs_combo)

    enabled_models = {item.upper() for item in parse_csv_list(args.models)}
    invalid_models = enabled_models - {"A", "B"}
    if invalid_models:
        raise ValueError(f"models must contain A and/or B: {invalid_models}")
    if not enabled_models:
        raise ValueError("At least one model must be enabled: A, B, or A,B")

    print("=" * 120)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
    print(f"models: {sorted(enabled_models)}")
    print(f"near_atr_multiplier: {args.near_atr}")
    print(f"close_tolerance_atr_multiplier: {args.close_tolerance_atr}")
    print(f"swing_left: {args.swing_left}")
    print(f"swing_right: {args.swing_right}")
    print(f"recent_pullback_bars: {args.recent_pullback_bars}")
    print(f"require_ema20_reclaim: {not args.no_ema20_reclaim}")
    print(f"require_macd_signal_alignment: {not args.no_macd_signal_alignment}")
    print(f"require_histogram_acceleration: {not args.no_histogram_acceleration}")
    print(f"rr: {args.rr}")
    print(f"sl_buffer_atr_multiplier: {args.sl_buffer_atr}")
    print(f"max_bars_in_trade: {args.max_bars_in_trade}")
    print(f"A BUY JST hours: {sorted(a_buy_hours) if a_buy_hours is not None else 'ALL'}")
    print(f"A SELL JST hours: {sorted(a_sell_hours) if a_sell_hours is not None else 'ALL'}")
    print(f"A exclude hidden_price_delta_atr <=: {args.a_exclude_hidden_price_delta_atr_lte if args.a_exclude_hidden_price_delta_atr_lte is not None else 'NONE'}")
    print(f"B BUY JST hours: {sorted(b_buy_hours) if b_buy_hours is not None else 'ALL'}")
    print(f"B SELL JST hours: {sorted(b_sell_hours) if b_sell_hours is not None else 'ALL'}")
    print(f"B exclude risk_atr_range: {b_exclude_risk_atr_range if b_exclude_risk_atr_range is not None else 'NONE'}")
    print(f"B exclude macd_hist_delta_abs_range: {b_exclude_macd_hist_delta_abs_range if b_exclude_macd_hist_delta_abs_range is not None else 'NONE'}")
    print(f"B BUY extra exclude risk_atr_range: {b_buy_exclude_risk_atr_range if b_buy_exclude_risk_atr_range is not None else 'NONE'}")
    print(f"B BUY extra exclude risk/macd combo: {b_buy_exclude_combo if b_buy_exclude_combo is not None else 'NONE'}")
    print_time_conversion_info(args)

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)
    filtered_base_df = apply_a_filters(base_df, args=args)

    combined_df = add_combined_signal_columns(
        filtered_base_df,
        a_buy_hours=a_buy_hours,
        a_sell_hours=a_sell_hours,
        b_buy_hours=b_buy_hours,
        b_sell_hours=b_sell_hours,
        enabled_models=enabled_models,
        b_exclude_risk_atr_range=b_exclude_risk_atr_range,
        b_exclude_macd_hist_delta_abs_range=b_exclude_macd_hist_delta_abs_range,
        sl_buffer_atr=args.sl_buffer_atr,
    )
    combined_df = apply_b_buy_extra_filters(combined_df, args=args)

    print_summary_dict("pullback_summary", pullback_summary(base_df))
    print_summary_dict("swing_summary", swing_summary(base_df))
    print_summary_dict("A_hidden_divergence_summary_unfiltered_before_a_filters", hidden_divergence_summary(base_df))
    print_summary_dict("A_hidden_divergence_summary_after_a_filters", hidden_divergence_summary(filtered_base_df))
    print_summary_dict(
        "A_filter_summary",
        {
            "a_hidden_price_delta_atr_filtered_out": int(filtered_base_df["a_hidden_price_delta_atr_filtered_out"].sum()),
        },
    )
    print_summary_dict("B_reacceleration_summary_unfiltered", reacceleration_summary(base_df))
    print_summary_dict(
        "B_BUY_extra_filter_summary",
        {
            "b_buy_extra_filtered_out": int(combined_df.get("b_buy_extra_filtered_out", pd.Series(False, index=combined_df.index)).sum()),
        },
    )
    print_summary_dict("combined_signal_summary_filtered", combined_signal_summary(combined_df))

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    trades = run_simple_hidden_divergence_backtest(combined_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = attach_signal_sources_to_trades(trades, combined_df)

    print_trade_report("COMBINED_A_B_TRADES_WITH_A_AND_B_BUY_FILTERS", trades)

    print("\nsummary_by_server_entry_hour:")
    by_hour = summarize_by_entry_hour(trades)
    if by_hour.empty:
        print("No trades.")
    else:
        print(by_hour.to_string(index=False))

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
        "h1_trend",
        "signal_macd",
        "signal_atr",
        "last_swing_low_price",
        "last_swing_high_price",
        "b_buy_risk_atr_ratio",
        "b_sell_risk_atr_ratio",
        "b_macd_hist_delta_abs",
    ]
    available_display_cols = [col for col in display_cols if col in trades.columns]

    print("\nrecent trades tail(30):")
    if trades.empty:
        print("No trades.")
    else:
        print(trades[available_display_cols].tail(30).to_string(index=False))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RESULTS_DATA_DIR / f"{symbol.lower()}_combined_ab_a_b_buy_filtered_backtest_trades.csv"
        trades.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_trades: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run combined A+B backtest with optional A and B BUY filters.")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default="gold", help="Comma-separated symbols. Default: gold")
    parser.add_argument("--models", type=str, default="A,B", help="Enabled models: A, B, or A,B. Default: A,B")
    parser.add_argument("--near-atr", type=float, default=0.30, help="ATR multiplier for EMA20 proximity. Default: 0.30")
    parser.add_argument("--close-tolerance-atr", type=float, default=0.50, help="ATR multiplier for close tolerance. Default: 0.50")
    parser.add_argument("--swing-left", type=int, default=3, help="Left bars for swing detection. Default: 3")
    parser.add_argument("--swing-right", type=int, default=2, help="Right bars for swing detection. Default: 2")
    parser.add_argument("--recent-pullback-bars", type=int, default=6, help="B signal recent pullback lookback bars. Default: 6")
    parser.add_argument("--no-ema20-reclaim", action="store_true", help="B signal: do not require EMA20 reclaim/cross from prior bar.")
    parser.add_argument("--no-macd-signal-alignment", action="store_true", help="B signal: do not require MACD line vs signal alignment.")
    parser.add_argument("--no-histogram-acceleration", action="store_true", help="B signal: do not require histogram acceleration.")
    parser.add_argument("--rr", type=float, default=1.5, help="Risk reward ratio. Default: 1.5")
    parser.add_argument("--sl-buffer-atr", type=float, default=0.05, help="SL buffer ATR multiplier. Default: 0.05")
    parser.add_argument("--server-timezone", type=str, default=DEFAULT_MT5_SERVER_TIMEZONE, help="IANA timezone for MT5 server time. Default: Europe/Athens")
    parser.add_argument("--server-utc-offset", type=int, default=3, help="Fallback fixed UTC offset hours. Used only with --use-fixed-offset.")
    parser.add_argument("--use-fixed-offset", action="store_true", help="Use fixed UTC offset instead of DST-aware timezone conversion.")
    parser.add_argument("--a-buy-jst-hours", type=str, default="7,13", help="A signal BUY JST hours. Default: 7,13")
    parser.add_argument("--a-sell-jst-hours", type=str, default="2,13,19", help="A signal SELL JST hours. Default: 2,13,19")
    parser.add_argument("--a-exclude-hidden-price-delta-atr-lte", type=float, default=None, help="Exclude A signals whose side-aware hidden_price_delta_atr is <= this threshold.")
    parser.add_argument("--b-buy-jst-hours", type=str, default="20,21,22,23", help="B signal BUY JST hours. Default: 20,21,22,23")
    parser.add_argument("--b-sell-jst-hours", type=str, default="10,11", help="B signal SELL JST hours. Default: 10,11")
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None, help="Exclude B signals with estimated risk/ATR inside range, e.g. 1.95,2.49")
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None, help="Exclude B signals with abs MACD histogram delta inside range, e.g. 0.383,0.628")
    parser.add_argument("--b-buy-exclude-risk-atr-range", type=str, default=None, help="Exclude B BUY signals with estimated risk/ATR inside range, e.g. 0.928,1.241")
    parser.add_argument("--b-buy-exclude-risk-atr-macd-hist-delta-abs-combo", type=str, default=None, help="Exclude B BUY signals matching risk/macd combo: risk_low,risk_high,macd_low,macd_high")
    parser.add_argument("--same-bar-win", action="store_true", help="If set, same-bar TP/SL is treated as win. Default is conservative loss.")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Optional maximum bars to hold a trade.")
    parser.add_argument("--save", action="store_true", help="Save trades CSV to data/results.")
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = parse_csv_list(args.symbols)
    if not symbols:
        print("No symbols provided.")
        return 1

    for symbol in symbols:
        m15_path, h1_path = build_paths(args.data_dir, symbol)
        print_backtest_report(symbol=symbol, m15_path=m15_path, h1_path=h1_path, args=args)

    print("=" * 120)
    print("Combined A+B backtest with A and B BUY filters completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
