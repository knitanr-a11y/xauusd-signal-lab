from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_b_signal_trades.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.divergence import add_hidden_divergence_flags
from src.indicators import add_basic_indicators
from src.presets import get_preset
from src.pullback import add_pullback_candidates
from src.reacceleration import ReaccelerationSettings, add_reacceleration_signals
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


def build_b_signal_df(args: argparse.Namespace, symbol: str) -> pd.DataFrame:
    preset = get_preset(args.preset)
    m15_path, h1_path = build_paths(args.data_dir, symbol)

    print("=" * 120)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
    print(f"preset: {preset.name}")
    print(f"B BUY JST hours: {args.b_buy_jst_hours}")
    print(f"B SELL JST hours: {args.b_sell_jst_hours}")
    print(f"rr: {args.rr}")
    print(f"sl_buffer_atr: {args.sl_buffer_atr}")

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
    with_time = add_time_columns(
        with_a,
        time_col="time",
        server_timezone=preset.server_timezone,
        fallback_server_utc_offset_hours=preset.server_utc_offset,
        use_fixed_offset=preset.use_fixed_offset,
    )
    b_settings = ReaccelerationSettings(
        recent_pullback_bars=preset.recent_pullback_bars,
        require_macd_signal_alignment=not preset.no_macd_signal_alignment,
        require_histogram_acceleration=not preset.no_histogram_acceleration,
        require_ema20_reclaim=not preset.no_ema20_reclaim,
    )
    out = add_reacceleration_signals(with_time, settings=b_settings)

    b_buy_hours = parse_int_csv(args.b_buy_jst_hours)
    b_sell_hours = parse_int_csv(args.b_sell_jst_hours)

    b_buy = out["buy_reacceleration_signal"].astype(bool)
    b_sell = out["sell_reacceleration_signal"].astype(bool)
    hours = out["jst_hour"].astype(int)

    if b_buy_hours is not None:
        b_buy = b_buy & hours.isin(b_buy_hours)
    if b_sell_hours is not None:
        b_sell = b_sell & hours.isin(b_sell_hours)

    out["b_buy_signal_filtered"] = b_buy
    out["b_sell_signal_filtered"] = b_sell
    out["b_signal_filtered"] = b_buy | b_sell
    out["b_signal_side_filtered"] = "NONE"
    out.loc[b_buy, "b_signal_side_filtered"] = "BUY"
    out.loc[b_sell, "b_signal_side_filtered"] = "SELL"

    # Map B into the existing backtest engine signal columns.
    out["original_hidden_bullish_divergence"] = out["hidden_bullish_divergence"]
    out["original_hidden_bearish_divergence"] = out["hidden_bearish_divergence"]
    out["hidden_bullish_divergence"] = out["b_buy_signal_filtered"]
    out["hidden_bearish_divergence"] = out["b_sell_signal_filtered"]

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


def enrich_b_trades(trades: pd.DataFrame, signal_df: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades

    feature_cols = [
        "time",
        "jst_time",
        "jst_hour",
        "close",
        "ema_20",
        "ema_50",
        "atr_14",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "macd_histogram_delta",
        "close_ema20_delta",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "recent_buy_pullback",
        "recent_sell_pullback",
        "buy_pullback_candidate",
        "sell_pullback_candidate",
        "pullback_side",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_low_macd",
        "last_confirmed_swing_high_macd",
        "original_hidden_bullish_divergence",
        "original_hidden_bearish_divergence",
        "b_buy_signal_filtered",
        "b_sell_signal_filtered",
    ]
    available = [col for col in feature_cols if col in signal_df.columns]
    signal_features = signal_df[available].copy()
    signal_features["signal_index"] = signal_df.index
    signal_features = signal_features.add_prefix("signal_")
    signal_features = signal_features.rename(columns={"signal_signal_index": "signal_index"})

    out = trades.merge(signal_features, on="signal_index", how="left")

    out["win"] = out["result"].eq("win")
    out["loss"] = out["result"].eq("loss")
    out["risk_atr_ratio"] = out["risk"] / out["signal_atr_14"]
    out["abs_close_ema20_delta_atr"] = out["signal_close_ema20_delta"].abs() / out["signal_atr_14"]
    out["macd_hist_delta_abs"] = out["signal_macd_histogram_delta"].abs()
    out["macd_hist_delta_atr"] = out["signal_macd_histogram_delta"].abs() / out["signal_atr_14"]
    out["h1_ema_gap"] = out["signal_h1_ema_20"] - out["signal_h1_ema_50"]
    out["h1_ema_gap_atr"] = out["h1_ema_gap"].abs() / out["signal_atr_14"]

    # How far entry is from the reference swing stop before ATR buffer.
    out["buy_entry_to_swing_low"] = out["entry_price"] - out["signal_last_confirmed_swing_low_price"]
    out["sell_swing_high_to_entry"] = out["signal_last_confirmed_swing_high_price"] - out["entry_price"]
    out["entry_to_reference_swing"] = pd.NA
    out.loc[out["side"].eq("BUY"), "entry_to_reference_swing"] = out.loc[out["side"].eq("BUY"), "buy_entry_to_swing_low"]
    out.loc[out["side"].eq("SELL"), "entry_to_reference_swing"] = out.loc[out["side"].eq("SELL"), "sell_swing_high_to_entry"]
    out["entry_to_reference_swing"] = pd.to_numeric(out["entry_to_reference_swing"], errors="coerce")
    out["entry_to_reference_swing_atr"] = out["entry_to_reference_swing"] / out["signal_atr_14"]

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


def print_b_diagnostics(trades: pd.DataFrame) -> None:
    print_dict("B_trade_summary", summarize_trades(trades))

    print_section("B_summary_by_side", summarize_grouped(trades, ["side"]))
    print_section("B_summary_by_jst_entry_hour", summarize_grouped(trades, ["jst_entry_time_hour"] if "jst_entry_time_hour" in trades.columns else ["signal_jst_hour"]))
    print_section("B_summary_by_month", summarize_grouped(trades.assign(jst_month=trades["jst_entry_time"].dt.to_period("M").astype(str)), ["jst_month"]))

    print("\nB_win_loss_feature_means:")
    feature_cols = [
        "risk",
        "signal_atr_14",
        "risk_atr_ratio",
        "entry_to_reference_swing_atr",
        "abs_close_ema20_delta_atr",
        "macd_hist_delta_abs",
        "macd_hist_delta_atr",
        "h1_ema_gap_atr",
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
        "abs_close_ema20_delta_atr",
        "macd_hist_delta_abs",
        "macd_hist_delta_atr",
        "h1_ema_gap_atr",
        "bars_held",
    ]:
        print_section(f"B_quartile_by_{col}", summarize_numeric_bins(trades, col, bins=4))

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
        "signal_h1_trend",
        "signal_close_ema20_delta",
        "risk_atr_ratio",
        "entry_to_reference_swing_atr",
        "macd_hist_delta_abs",
        "h1_ema_gap_atr",
    ]
    available = [col for col in display_cols if col in losing.columns]
    print_section("Recent_B_losses_tail_20", losing[available].tail(20))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze B-signal win/loss characteristics for improvement.")
    parser.add_argument("--preset", type=str, default="gold_ab_v1", help="Preset to use for base settings. Default: gold_ab_v1")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default="gold", help="Comma-separated symbols. Default: gold")
    parser.add_argument("--b-buy-jst-hours", type=str, default=None, help="Override B BUY JST hours. Default: from preset")
    parser.add_argument("--b-sell-jst-hours", type=str, default=None, help="Override B SELL JST hours. Default: from preset")
    parser.add_argument("--rr", type=float, default=None, help="Override RR. Default: from preset")
    parser.add_argument("--sl-buffer-atr", type=float, default=None, help="Override SL buffer ATR. Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true", help="If set, same-bar TP/SL is treated as win. Default is conservative loss.")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Optional maximum bars to hold a trade.")
    parser.add_argument("--save", action="store_true", help="Save enriched B trades to data/results.")
    args = parser.parse_args()

    preset = get_preset(args.preset)
    if args.b_buy_jst_hours is None:
        args.b_buy_jst_hours = preset.b_buy_jst_hours
    if args.b_sell_jst_hours is None:
        args.b_sell_jst_hours = preset.b_sell_jst_hours
    if args.rr is None:
        args.rr = preset.rr
    if args.sl_buffer_atr is None:
        args.sl_buffer_atr = preset.sl_buffer_atr

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = [item.strip().lower() for item in args.symbols.split(",") if item.strip()]
    for symbol in symbols:
        signal_df = build_b_signal_df(args, symbol=symbol)
        settings = BacktestSettings(
            rr=args.rr,
            sl_buffer_atr_multiplier=args.sl_buffer_atr,
            conservative_same_bar=not args.same_bar_win,
            max_bars_in_trade=args.max_bars_in_trade,
        )
        trades = run_simple_hidden_divergence_backtest(signal_df, settings=settings)
        trades = attach_jst_trade_times(trades, preset_name=args.preset)
        trades = enrich_b_trades(trades, signal_df)
        trades["jst_entry_time_hour"] = trades["jst_entry_time"].dt.hour

        print_b_diagnostics(trades)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol}_b_signal_diagnostics_trades.csv"
            trades.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_b_diagnostic_trades: {out_path}")

    print("=" * 120)
    print("B signal diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
