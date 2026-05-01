from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_combined_failure_modes.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_combined_backtest import (
    add_combined_signal_columns,
    attach_signal_sources_to_trades,
    attach_jst_trade_times,
    build_base_dataframe,
    build_paths,
    parse_float_range,
    parse_int_csv,
)
from scripts.run_combined_backtest_with_a_filters import apply_a_filters
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE


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
    return pd.DataFrame(rows)[ordered].sort_values(group_cols).reset_index(drop=True)


def summarize_numeric_bins(trades: pd.DataFrame, column: str, bins: int = 4) -> pd.DataFrame:
    if trades.empty or column not in trades.columns:
        return pd.DataFrame()
    values = pd.to_numeric(trades[column], errors="coerce")
    valid = trades[values.notna()].copy()
    if valid.empty or valid[column].nunique(dropna=True) < 2:
        return pd.DataFrame()

    try:
        valid[f"{column}_bin"] = pd.qcut(valid[column], q=bins, duplicates="drop")
    except ValueError:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for bin_value, group in valid.groupby(f"{column}_bin", observed=False, dropna=False):
        summary = summarize_trades(group)
        summary["feature"] = column
        summary["bin"] = str(bin_value)
        summary["min"] = float(group[column].min())
        summary["max"] = float(group[column].max())
        summary["mean"] = float(group[column].mean())
        rows.append(summary)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)[[
        "feature",
        "bin",
        "min",
        "max",
        "mean",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "average_r",
        "total_r",
        "profit_factor",
        "max_drawdown_r",
    ]]


def enrich_combined_trades(trades: pd.DataFrame, combined_df: pd.DataFrame, early_loss_bars: int, long_hold_bars: int) -> pd.DataFrame:
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
        "macd_histogram_delta",
        "h1_time",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "a_buy_signal_filtered",
        "a_sell_signal_filtered",
        "b_buy_signal_filtered",
        "b_sell_signal_filtered",
        "b_buy_risk_atr_ratio",
        "b_sell_risk_atr_ratio",
        "b_macd_hist_delta_abs",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_high_price",
        "bullish_hidden_price_delta",
        "bearish_hidden_price_delta",
        "bullish_hidden_macd_delta",
        "bearish_hidden_macd_delta",
        "a_hidden_price_delta_atr_buy",
        "a_hidden_price_delta_atr_sell",
    ]
    available = [col for col in feature_cols if col in combined_df.columns]
    signal_features = combined_df[available].copy()
    signal_features["signal_index"] = combined_df.index
    signal_features = signal_features.add_prefix("signal_")
    signal_features = signal_features.rename(columns={"signal_signal_index": "signal_index"})

    out = trades.merge(signal_features, on="signal_index", how="left")

    out["win"] = out["result"].eq("win")
    out["loss"] = out["result"].eq("loss")
    out["early_loss"] = out["loss"] & (pd.to_numeric(out["bars_held"], errors="coerce") <= early_loss_bars)
    out["long_hold_loss"] = out["loss"] & (pd.to_numeric(out["bars_held"], errors="coerce") >= long_hold_bars)
    out["risk_atr_ratio"] = pd.to_numeric(out["risk"], errors="coerce") / pd.to_numeric(out["signal_atr_14"], errors="coerce")
    out["macd_hist_delta_abs"] = pd.to_numeric(out.get("signal_macd_histogram_delta", pd.Series(index=out.index)), errors="coerce").abs()

    h1_gap = pd.to_numeric(out.get("signal_h1_ema_20", pd.Series(index=out.index)), errors="coerce") - pd.to_numeric(
        out.get("signal_h1_ema_50", pd.Series(index=out.index)), errors="coerce"
    )
    out["h1_ema_gap_atr"] = h1_gap.abs() / pd.to_numeric(out["signal_atr_14"], errors="coerce")
    out["h1_ema_gap_side_signed_atr"] = h1_gap / pd.to_numeric(out["signal_atr_14"], errors="coerce")
    out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed_atr"] = -out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed_atr"]

    out["a_hidden_price_delta_atr"] = pd.NA
    if "signal_a_hidden_price_delta_atr_buy" in out.columns:
        out.loc[out["side"].eq("BUY"), "a_hidden_price_delta_atr"] = out.loc[out["side"].eq("BUY"), "signal_a_hidden_price_delta_atr_buy"]
    if "signal_a_hidden_price_delta_atr_sell" in out.columns:
        out.loc[out["side"].eq("SELL"), "a_hidden_price_delta_atr"] = out.loc[out["side"].eq("SELL"), "signal_a_hidden_price_delta_atr_sell"]
    out["a_hidden_price_delta_atr"] = pd.to_numeric(out["a_hidden_price_delta_atr"], errors="coerce")

    return out


def add_equity_and_drawdown(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    out = trades.copy().reset_index(drop=True)
    out["trade_no"] = out.index + 1
    out["equity_r"] = pd.to_numeric(out["r"], errors="coerce").fillna(0.0).cumsum()
    out["equity_peak_r"] = out["equity_r"].cummax().clip(lower=0.0)
    out["drawdown_r"] = out["equity_peak_r"] - out["equity_r"]
    out["new_equity_high"] = out["equity_r"].eq(out["equity_peak_r"])
    return out


def drawdown_segments(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty or "drawdown_r" not in trades.columns:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    in_dd = False
    start_idx = 0
    peak_before = 0.0

    for idx, row in trades.iterrows():
        dd = float(row["drawdown_r"])
        if dd > 0 and not in_dd:
            in_dd = True
            start_idx = idx
            peak_before = float(row["equity_peak_r"])
        if in_dd and (dd == 0 or idx == len(trades) - 1):
            end_idx = idx
            segment = trades.iloc[start_idx : end_idx + 1]
            max_dd_idx = segment["drawdown_r"].astype(float).idxmax()
            max_dd_row = trades.loc[max_dd_idx]
            rows.append(
                {
                    "start_trade_no": int(trades.loc[start_idx, "trade_no"]),
                    "end_trade_no": int(trades.loc[end_idx, "trade_no"]),
                    "trades_in_segment": int(end_idx - start_idx + 1),
                    "peak_before_r": peak_before,
                    "max_drawdown_r": float(max_dd_row["drawdown_r"]),
                    "max_dd_trade_no": int(max_dd_row["trade_no"]),
                    "start_jst_entry_time": trades.loc[start_idx, "jst_entry_time"] if "jst_entry_time" in trades.columns else trades.loc[start_idx, "entry_time"],
                    "max_dd_jst_entry_time": max_dd_row["jst_entry_time"] if "jst_entry_time" in trades.columns else max_dd_row["entry_time"],
                    "end_jst_entry_time": trades.loc[end_idx, "jst_entry_time"] if "jst_entry_time" in trades.columns else trades.loc[end_idx, "entry_time"],
                    "source_sequence": "->".join(segment.get("combined_signal_source", pd.Series(index=segment.index, dtype="object")).astype(str).tolist()),
                    "side_sequence": "->".join(segment.get("side", pd.Series(index=segment.index, dtype="object")).astype(str).tolist()),
                    "r_sequence": ",".join(f"{float(v):.1f}" for v in pd.to_numeric(segment["r"], errors="coerce").fillna(0.0).tolist()),
                }
            )
            in_dd = False

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("max_drawdown_r", ascending=False).reset_index(drop=True)


def loss_streaks(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    start_idx: int | None = None
    for idx, row in trades.iterrows():
        is_loss = row["result"] == "loss"
        if is_loss and start_idx is None:
            start_idx = idx
        if start_idx is not None and (not is_loss or idx == len(trades) - 1):
            end_idx = idx if is_loss and idx == len(trades) - 1 else idx - 1
            segment = trades.iloc[start_idx : end_idx + 1]
            rows.append(
                {
                    "start_trade_no": int(trades.loc[start_idx, "trade_no"]),
                    "end_trade_no": int(trades.loc[end_idx, "trade_no"]),
                    "losses": int(len(segment)),
                    "total_r": float(pd.to_numeric(segment["r"], errors="coerce").fillna(0.0).sum()),
                    "start_jst_entry_time": trades.loc[start_idx, "jst_entry_time"] if "jst_entry_time" in trades.columns else trades.loc[start_idx, "entry_time"],
                    "end_jst_entry_time": trades.loc[end_idx, "jst_entry_time"] if "jst_entry_time" in trades.columns else trades.loc[end_idx, "entry_time"],
                    "source_sequence": "->".join(segment.get("combined_signal_source", pd.Series(index=segment.index, dtype="object")).astype(str).tolist()),
                    "side_sequence": "->".join(segment.get("side", pd.Series(index=segment.index, dtype="object")).astype(str).tolist()),
                    "hour_sequence": "->".join(segment["jst_entry_time"].dt.hour.astype(str).tolist()) if "jst_entry_time" in segment.columns else "",
                }
            )
            start_idx = None

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["losses", "total_r"], ascending=[False, True]).reset_index(drop=True)


def print_failure_diagnostics(trades: pd.DataFrame, early_loss_bars: int, long_hold_bars: int) -> None:
    print_dict("combined_failure_mode_summary", summarize_trades(trades))

    print_section("summary_by_source", summarize_grouped(trades, ["combined_signal_source"]))
    print_section("summary_by_source_and_side", summarize_grouped(trades, ["combined_signal_source", "side"]))
    print_section("summary_by_source_and_jst_hour", summarize_grouped(trades, ["combined_signal_source", "jst_entry_hour"]))
    print_section("summary_by_side_and_jst_hour", summarize_grouped(trades, ["side", "jst_entry_hour"]))
    print_section("early_loss_by_source_side", summarize_grouped(trades, ["combined_signal_source", "side", "early_loss"]))
    print_section("long_hold_loss_by_source_side", summarize_grouped(trades, ["combined_signal_source", "side", "long_hold_loss"]))

    for col in [
        "risk_atr_ratio",
        "bars_held",
        "macd_hist_delta_abs",
        "h1_ema_gap_side_signed_atr",
        "a_hidden_price_delta_atr",
    ]:
        print_section(f"quartile_by_{col}", summarize_numeric_bins(trades, col, bins=4))

    dd = drawdown_segments(trades)
    print_section("top_drawdown_segments", dd, max_rows=10)

    streaks = loss_streaks(trades)
    print_section("top_loss_streaks", streaks, max_rows=10)

    losses = trades[trades["result"].eq("loss")].copy()
    display_cols = [
        "trade_no",
        "combined_signal_source",
        "side",
        "jst_entry_time",
        "entry_price",
        "sl",
        "tp",
        "risk",
        "r",
        "bars_held",
        "early_loss",
        "long_hold_loss",
        "risk_atr_ratio",
        "macd_hist_delta_abs",
        "h1_ema_gap_side_signed_atr",
        "a_hidden_price_delta_atr",
        "equity_r",
        "drawdown_r",
    ]
    available = [col for col in display_cols if col in losses.columns]
    print_section("recent_losses_tail_40", losses[available].tail(40))

    print(f"\nearly_loss_definition: loss and bars_held <= {early_loss_bars}")
    print(f"long_hold_loss_definition: loss and bars_held >= {long_hold_bars}")


def build_and_backtest(args: argparse.Namespace, symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    m15_path, h1_path = build_paths(args.data_dir, symbol)
    if not m15_path.exists():
        raise FileNotFoundError(f"M15 file not found: {m15_path}")
    if not h1_path.exists():
        raise FileNotFoundError(f"H1 file not found: {h1_path}")

    base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)
    filtered_base_df = apply_a_filters(base_df, args=args)
    combined_df = add_combined_signal_columns(
        filtered_base_df,
        a_buy_hours=parse_int_csv(args.a_buy_jst_hours),
        a_sell_hours=parse_int_csv(args.a_sell_jst_hours),
        b_buy_hours=parse_int_csv(args.b_buy_jst_hours),
        b_sell_hours=parse_int_csv(args.b_sell_jst_hours),
        enabled_models={item.upper() for item in args.models.split(",") if item.strip()},
        b_exclude_risk_atr_range=parse_float_range(args.b_exclude_risk_atr_range),
        b_exclude_macd_hist_delta_abs_range=parse_float_range(args.b_exclude_macd_hist_delta_abs_range),
        sl_buffer_atr=args.sl_buffer_atr,
    )

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    trades = run_simple_hidden_divergence_backtest(combined_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = attach_signal_sources_to_trades(trades, combined_df)
    trades = enrich_combined_trades(trades, combined_df, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)
    trades = add_equity_and_drawdown(trades)
    if not trades.empty and "jst_entry_time" in trades.columns:
        trades["jst_entry_hour"] = trades["jst_entry_time"].dt.hour
        trades["jst_entry_month"] = trades["jst_entry_time"].dt.to_period("M").astype(str)
    return combined_df, trades


def apply_preset_defaults(args: argparse.Namespace) -> argparse.Namespace:
    preset = get_preset(args.preset)
    if args.symbols is None:
        args.symbols = preset.symbols
    if args.models is None:
        args.models = preset.models
    if args.near_atr is None:
        args.near_atr = preset.near_atr
    if args.close_tolerance_atr is None:
        args.close_tolerance_atr = preset.close_tolerance_atr
    if args.swing_left is None:
        args.swing_left = preset.swing_left
    if args.swing_right is None:
        args.swing_right = preset.swing_right
    if args.recent_pullback_bars is None:
        args.recent_pullback_bars = preset.recent_pullback_bars
    if args.rr is None:
        args.rr = preset.rr
    if args.sl_buffer_atr is None:
        args.sl_buffer_atr = preset.sl_buffer_atr
    if args.server_timezone is None:
        args.server_timezone = preset.server_timezone or DEFAULT_MT5_SERVER_TIMEZONE
    if args.server_utc_offset is None:
        args.server_utc_offset = preset.server_utc_offset
    if not args.use_fixed_offset:
        args.use_fixed_offset = preset.use_fixed_offset
    if args.a_buy_jst_hours is None:
        args.a_buy_jst_hours = preset.a_buy_jst_hours
    if args.a_sell_jst_hours is None:
        args.a_sell_jst_hours = preset.a_sell_jst_hours
    if args.a_exclude_hidden_price_delta_atr_lte is None:
        args.a_exclude_hidden_price_delta_atr_lte = preset.a_exclude_hidden_price_delta_atr_lte
    if args.b_buy_jst_hours is None:
        args.b_buy_jst_hours = preset.b_buy_jst_hours
    if args.b_sell_jst_hours is None:
        args.b_sell_jst_hours = preset.b_sell_jst_hours
    if args.b_exclude_risk_atr_range is None:
        args.b_exclude_risk_atr_range = preset.b_exclude_risk_atr_range
    if args.b_exclude_macd_hist_delta_abs_range is None:
        args.b_exclude_macd_hist_delta_abs_range = preset.b_exclude_macd_hist_delta_abs_range
    if args.max_bars_in_trade is None:
        args.max_bars_in_trade = preset.max_bars_in_trade
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze combined A+B failure modes for a preset.")
    parser.add_argument("--preset", type=str, default="gold_ab_v3", help="Preset to use. Default: gold_ab_v3")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--models", type=str, default=None, help="Enabled models. Default: from preset")
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
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Default: 2")
    parser.add_argument("--long-hold-bars", type=int, default=20, help="Default: 20")
    parser.add_argument("--save", action="store_true", help="Save enriched trades CSV to data/results.")
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
        print(f"preset: {args.preset}")
        print(f"models: {args.models}")
        print(f"A BUY JST hours: {args.a_buy_jst_hours}")
        print(f"A SELL JST hours: {args.a_sell_jst_hours}")
        print(f"A exclude hidden_price_delta_atr <=: {args.a_exclude_hidden_price_delta_atr_lte if args.a_exclude_hidden_price_delta_atr_lte is not None else 'NONE'}")
        print(f"B BUY JST hours: {args.b_buy_jst_hours}")
        print(f"B SELL JST hours: {args.b_sell_jst_hours}")
        print(f"B exclude risk_atr_range: {args.b_exclude_risk_atr_range or 'NONE'}")
        print(f"B exclude macd_hist_delta_abs_range: {args.b_exclude_macd_hist_delta_abs_range or 'NONE'}")

        combined_df, trades = build_and_backtest(args, symbol=symbol)
        print_failure_diagnostics(trades, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol}_combined_failure_modes_{args.preset}.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_failure_mode_trades: {out_path}")

    print("=" * 120)
    print("Combined failure mode diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
