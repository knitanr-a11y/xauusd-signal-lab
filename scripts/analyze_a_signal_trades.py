from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_a_signal_trades.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.divergence import add_hidden_divergence_flags, hidden_divergence_summary
from src.indicators import add_basic_indicators
from src.presets import get_preset
from src.pullback import add_pullback_candidates
from src.swings import add_swing_points
from src.time_utils import add_time_columns, convert_server_time_to_jst
from src.timeframe_merge import merge_confirmed_h1_context


def parse_int_csv(value: str | None) -> set[int] | None:
    if value is None or value.strip() == "":
        return None
    values: set[int] = set()
    for item in value.split(","):
        text = item.strip()
        if text == "":
            continue
        hour = int(text)
        if hour < 0 or hour > 23:
            raise ValueError(f"Hour must be 0-23: {hour}")
        values.add(hour)
    return values


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def print_dict(title: str, data: dict[str, object]) -> None:
    print(f"\n{title}:")
    for key, value in data.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def build_a_signal_df(args: argparse.Namespace, symbol: str) -> pd.DataFrame:
    preset = get_preset(args.preset)
    m15_path, h1_path = build_paths(args.data_dir, symbol)

    print("=" * 120)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
    print(f"preset: {preset.name}")
    print(f"A BUY JST hours: {args.a_buy_jst_hours}")
    print(f"A SELL JST hours: {args.a_sell_jst_hours}")
    print(f"rr: {args.rr}")
    print(f"sl_buffer_atr: {args.sl_buffer_atr}")
    print(f"early_loss_bars: {args.early_loss_bars}")

    if not m15_path.exists():
        raise FileNotFoundError(f"M15 file not found: {m15_path}")
    if not h1_path.exists():
        raise FileNotFoundError(f"H1 file not found: {h1_path}")

    m15 = add_basic_indicators(load_ohlc_csv(m15_path))
    h1 = add_basic_indicators(load_ohlc_csv(h1_path))
    merged = merge_confirmed_h1_context(m15, h1)
    swings = add_swing_points(merged, left=preset.swing_left, right=preset.swing_right)
    candidates = add_pullback_candidates(
        swings,
        near_atr_multiplier=preset.near_atr,
        close_tolerance_atr_multiplier=preset.close_tolerance_atr,
    )
    with_a = add_hidden_divergence_flags(candidates)
    out = add_time_columns(
        with_a,
        time_col="time",
        server_timezone=preset.server_timezone,
        fallback_server_utc_offset_hours=preset.server_utc_offset,
        use_fixed_offset=preset.use_fixed_offset,
    )

    # B-signal generation creates macd_histogram_delta in src.reacceleration.
    # A diagnostics does not need B signals, so create the same diagnostic column here
    # when it is absent. This keeps the A route independent and prevents a hidden
    # dependency on add_reacceleration_signals().
    if "macd_histogram_delta" not in out.columns and "macd_hist" in out.columns:
        out["macd_histogram_delta"] = out["macd_hist"] - out["macd_hist"].shift(1)

    print_dict("A_hidden_divergence_summary_unfiltered", hidden_divergence_summary(out))

    a_buy_hours = parse_int_csv(args.a_buy_jst_hours)
    a_sell_hours = parse_int_csv(args.a_sell_jst_hours)

    a_buy = out["hidden_bullish_divergence"].astype(bool)
    a_sell = out["hidden_bearish_divergence"].astype(bool)
    hours = out["jst_hour"].astype(int)

    if a_buy_hours is not None:
        a_buy = a_buy & hours.isin(a_buy_hours)
    if a_sell_hours is not None:
        a_sell = a_sell & hours.isin(a_sell_hours)

    conflict = a_buy & a_sell
    out["a_buy_signal_filtered"] = a_buy & ~conflict
    out["a_sell_signal_filtered"] = a_sell & ~conflict
    out["a_signal_conflict"] = conflict
    out["a_signal_filtered"] = out["a_buy_signal_filtered"] | out["a_sell_signal_filtered"]
    out["a_signal_side_filtered"] = "NONE"
    out.loc[out["a_buy_signal_filtered"], "a_signal_side_filtered"] = "BUY"
    out.loc[out["a_sell_signal_filtered"], "a_signal_side_filtered"] = "SELL"

    print_dict(
        "A_signal_summary_filtered",
        {
            "a_buy_filtered": int(out["a_buy_signal_filtered"].sum()),
            "a_sell_filtered": int(out["a_sell_signal_filtered"].sum()),
            "conflicts_skipped": int(out["a_signal_conflict"].sum()),
            "a_total_filtered": int(out["a_signal_filtered"].sum()),
        },
    )

    # Map filtered A into the existing backtest engine signal columns.
    out["original_hidden_bullish_divergence"] = out["hidden_bullish_divergence"]
    out["original_hidden_bearish_divergence"] = out["hidden_bearish_divergence"]
    out["hidden_bullish_divergence"] = out["a_buy_signal_filtered"]
    out["hidden_bearish_divergence"] = out["a_sell_signal_filtered"]

    return out


def attach_jst_trade_times(trades: pd.DataFrame, preset_name: str) -> pd.DataFrame:
    if trades.empty:
        return trades
    preset = get_preset(preset_name)
    out = trades.copy()
    for col in ["signal_time", "entry_time", "exit_time", "h1_time"]:
        if col in out.columns:
            out[f"jst_{col}"] = convert_server_time_to_jst(
                out[col],
                server_timezone=preset.server_timezone,
                fallback_server_utc_offset_hours=preset.server_utc_offset,
                use_fixed_offset=preset.use_fixed_offset,
            )
    return out


def _choose_side_value(out: pd.DataFrame, side_col: str, buy_col: str, sell_col: str, target_col: str) -> None:
    out[target_col] = pd.NA
    if buy_col in out.columns:
        out.loc[out[side_col].eq("BUY"), target_col] = out.loc[out[side_col].eq("BUY"), buy_col]
    if sell_col in out.columns:
        out.loc[out[side_col].eq("SELL"), target_col] = out.loc[out[side_col].eq("SELL"), sell_col]
    out[target_col] = pd.to_numeric(out[target_col], errors="coerce")


def _numeric_series(out: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column in out.columns:
        return pd.to_numeric(out[column], errors="coerce")
    return pd.Series(default, index=out.index, dtype="float64")


def enrich_a_trades(trades: pd.DataFrame, signal_df: pd.DataFrame, early_loss_bars: int) -> pd.DataFrame:
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
        "buy_pullback_candidate",
        "sell_pullback_candidate",
        "pullback_side",
        "last_confirmed_swing_low_time",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_low_macd",
        "last_confirmed_swing_high_time",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_high_macd",
        "bullish_hidden_price_delta",
        "bullish_hidden_macd_delta",
        "bearish_hidden_price_delta",
        "bearish_hidden_macd_delta",
        "original_hidden_bullish_divergence",
        "original_hidden_bearish_divergence",
        "a_buy_signal_filtered",
        "a_sell_signal_filtered",
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

    out["risk_atr_ratio"] = out["risk"] / out["signal_atr_14"]

    # How far entry is from the reference swing stop before ATR buffer.
    out["buy_entry_to_swing_low"] = out["entry_price"] - out["signal_last_confirmed_swing_low_price"]
    out["sell_swing_high_to_entry"] = out["signal_last_confirmed_swing_high_price"] - out["entry_price"]
    _choose_side_value(out, "side", "buy_entry_to_swing_low", "sell_swing_high_to_entry", "entry_to_reference_swing")
    out["entry_to_reference_swing_atr"] = out["entry_to_reference_swing"] / out["signal_atr_14"]

    # A divergence strength: price still made a valid higher-low / lower-high, while MACD exceeded the prior swing in the opposite direction.
    _choose_side_value(out, "side", "signal_bullish_hidden_price_delta", "signal_bearish_hidden_price_delta", "hidden_price_delta")
    _choose_side_value(out, "side", "signal_bullish_hidden_macd_delta", "signal_bearish_hidden_macd_delta", "hidden_macd_delta")
    out["hidden_price_delta_atr"] = out["hidden_price_delta"] / out["signal_atr_14"]
    out["hidden_macd_delta_abs"] = out["hidden_macd_delta"].abs()

    # MACD and H1 context at the signal candle.
    out["macd_hist_delta_abs"] = _numeric_series(out, "signal_macd_histogram_delta").abs()
    out["macd_line_signal_gap"] = _numeric_series(out, "signal_macd_line") - _numeric_series(out, "signal_macd_signal")
    out["macd_line_signal_gap_abs"] = out["macd_line_signal_gap"].abs()
    out["h1_close_ema20_gap"] = _numeric_series(out, "signal_h1_close") - _numeric_series(out, "signal_h1_ema_20")
    out["h1_close_ema20_gap_atr"] = out["h1_close_ema20_gap"].abs() / out["signal_atr_14"]
    out["h1_ema_gap"] = _numeric_series(out, "signal_h1_ema_20") - _numeric_series(out, "signal_h1_ema_50")
    out["h1_ema_gap_atr"] = out["h1_ema_gap"].abs() / out["signal_atr_14"]

    # Side-aware H1 alignment. Positive means the H1 EMA20/EMA50 gap supports the trade side.
    out["h1_ema_gap_side_signed"] = out["h1_ema_gap"]
    out.loc[out["side"].eq("SELL"), "h1_ema_gap_side_signed"] = -out.loc[out["side"].eq("SELL"), "h1_ema_gap"]
    out["h1_ema_gap_side_signed_atr"] = out["h1_ema_gap_side_signed"] / out["signal_atr_14"]

    return out


def summarize_grouped(trades: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if trades.empty:
        return pd.DataFrame()
    for key, group in trades.groupby(group_cols, dropna=False):
        summary = summarize_trades(group)
        if not isinstance(key, tuple):
            key = (key,)
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


def print_section(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    if max_rows is not None:
        df = df.head(max_rows)
    print(df.to_string(index=False))


def print_a_diagnostics(trades: pd.DataFrame) -> None:
    print_dict("A_trade_summary", summarize_trades(trades))

    print_section("A_summary_by_side", summarize_grouped(trades, ["side"]))
    print_section("A_summary_by_side_and_jst_entry_hour", summarize_grouped(trades, ["side", "jst_entry_time_hour"]))
    print_section("A_summary_by_jst_entry_hour", summarize_grouped(trades, ["jst_entry_time_hour"]))
    print_section("A_summary_by_h1_trend", summarize_grouped(trades, ["signal_h1_trend"]))
    print_section("A_summary_by_side_and_h1_trend", summarize_grouped(trades, ["side", "signal_h1_trend"]))
    print_section("A_summary_by_month", summarize_grouped(trades.assign(jst_month=trades["jst_entry_time"].dt.to_period("M").astype(str)), ["jst_month"]))
    print_section("A_early_loss_summary", summarize_grouped(trades, ["early_loss"]))
    print_section("A_early_loss_by_side", summarize_grouped(trades, ["side", "early_loss"]))

    print("\nA_win_loss_feature_means:")
    feature_cols = [
        "risk",
        "signal_atr_14",
        "risk_atr_ratio",
        "entry_to_reference_swing_atr",
        "hidden_price_delta_atr",
        "hidden_macd_delta_abs",
        "macd_hist_delta_abs",
        "macd_line_signal_gap_abs",
        "h1_close_ema20_gap_atr",
        "h1_ema_gap_atr",
        "h1_ema_gap_side_signed_atr",
        "bars_held",
    ]
    rows = []
    for result, group in trades.groupby("result", dropna=False):
        row = {"result": result, "trades": len(group)}
        for col in feature_cols:
            if col in group.columns:
                row[col] = pd.to_numeric(group[col], errors="coerce").mean()
        rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))

    for col in [
        "risk_atr_ratio",
        "entry_to_reference_swing_atr",
        "hidden_price_delta_atr",
        "hidden_macd_delta_abs",
        "macd_hist_delta_abs",
        "macd_line_signal_gap_abs",
        "h1_close_ema20_gap_atr",
        "h1_ema_gap_atr",
        "h1_ema_gap_side_signed_atr",
        "bars_held",
    ]:
        print_section(f"A_quartile_by_{col}", summarize_numeric_bins(trades, col, bins=4))

    losing = trades[trades["result"].eq("loss")].copy()
    display_cols = [
        "side",
        "signal_time",
        "jst_entry_time",
        "entry_price",
        "sl",
        "tp",
        "risk",
        "r",
        "bars_held",
        "early_loss",
        "signal_h1_trend",
        "risk_atr_ratio",
        "entry_to_reference_swing_atr",
        "hidden_price_delta_atr",
        "hidden_macd_delta_abs",
        "macd_hist_delta_abs",
        "h1_close_ema20_gap_atr",
        "h1_ema_gap_side_signed_atr",
    ]
    available = [col for col in display_cols if col in losing.columns]
    print_section("Recent_A_losses_tail_30", losing[available].tail(30))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze A hidden-divergence win/loss characteristics for improvement.")
    parser.add_argument("--preset", type=str, default="gold_ab_v2", help="Preset to use for base settings. Default: gold_ab_v2")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None, help="Override A BUY JST hours. Default: from preset")
    parser.add_argument("--a-sell-jst-hours", type=str, default=None, help="Override A SELL JST hours. Default: from preset")
    parser.add_argument("--rr", type=float, default=None, help="Override RR. Default: from preset")
    parser.add_argument("--sl-buffer-atr", type=float, default=None, help="Override SL buffer ATR. Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true", help="If set, same-bar TP/SL is treated as win. Default is conservative loss.")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Optional maximum bars to hold a trade.")
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Losses closed within this many bars are flagged as early losses. Default: 2")
    parser.add_argument("--save", action="store_true", help="Save enriched A trades to data/results.")
    args = parser.parse_args()

    preset = get_preset(args.preset)
    if args.symbols is None:
        args.symbols = preset.symbols
    if args.a_buy_jst_hours is None:
        args.a_buy_jst_hours = preset.a_buy_jst_hours
    if args.a_sell_jst_hours is None:
        args.a_sell_jst_hours = preset.a_sell_jst_hours
    if args.rr is None:
        args.rr = preset.rr
    if args.sl_buffer_atr is None:
        args.sl_buffer_atr = preset.sl_buffer_atr
    if args.max_bars_in_trade is None:
        args.max_bars_in_trade = preset.max_bars_in_trade

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1
    if args.early_loss_bars <= 0:
        print(f"early-loss-bars must be positive: {args.early_loss_bars}")
        return 1

    symbols = [item.strip().lower() for item in args.symbols.split(",") if item.strip()]
    if not symbols:
        print("No symbols provided.")
        return 1

    for symbol in symbols:
        signal_df = build_a_signal_df(args, symbol=symbol)
        settings = BacktestSettings(
            rr=args.rr,
            sl_buffer_atr_multiplier=args.sl_buffer_atr,
            conservative_same_bar=not args.same_bar_win,
            max_bars_in_trade=args.max_bars_in_trade,
        )
        trades = run_simple_hidden_divergence_backtest(signal_df, settings=settings)
        trades = attach_jst_trade_times(trades, preset_name=args.preset)
        trades = enrich_a_trades(trades, signal_df, early_loss_bars=args.early_loss_bars)
        trades["jst_entry_time_hour"] = trades["jst_entry_time"].dt.hour

        print_a_diagnostics(trades)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol}_a_signal_diagnostics_trades.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_a_diagnostic_trades: {out_path}")

    print("=" * 120)
    print("A signal diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
