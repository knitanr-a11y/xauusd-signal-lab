from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/run_reacceleration_backtest.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import (
    BacktestSettings,
    run_simple_hidden_divergence_backtest,
    summarize_by_entry_hour,
    summarize_by_hour,
    summarize_by_month,
    summarize_by_side,
    summarize_trades,
)
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.divergence import add_hidden_divergence_flags, hidden_divergence_summary
from src.indicators import add_basic_indicators
from src.pullback import add_pullback_candidates, pullback_summary
from src.reacceleration import (
    ReaccelerationSettings,
    add_reacceleration_signals,
    reacceleration_summary,
)
from src.swings import add_swing_points, swing_summary
from src.time_utils import (
    DEFAULT_MT5_SERVER_TIMEZONE,
    add_time_columns,
    convert_server_time_to_jst,
    server_to_jst_delta_hours,
)
from src.timeframe_merge import merge_confirmed_h1_context


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def parse_int_csv(value: str | None) -> set[int] | None:
    if value is None or value.strip() == "":
        return None

    hours: set[int] = set()
    for item in value.split(","):
        text = item.strip()
        if text == "":
            continue
        hour = int(text)
        if hour < 0 or hour > 23:
            raise ValueError(f"Hour must be 0-23: {hour}")
        hours.add(hour)
    return hours


def print_summary_dict(title: str, summary: dict[str, object]) -> None:
    print(f"\n{title}:")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def build_b_signal_dataframe(
    m15_path: Path,
    h1_path: Path,
    near_atr_multiplier: float,
    close_tolerance_atr_multiplier: float,
    swing_left: int,
    swing_right: int,
    recent_pullback_bars: int,
    require_ema20_reclaim: bool,
    require_macd_signal_alignment: bool,
    require_histogram_acceleration: bool,
    server_timezone: str,
    server_utc_offset: int,
    use_fixed_offset: bool,
):
    m15 = add_basic_indicators(load_ohlc_csv(m15_path))
    h1 = add_basic_indicators(load_ohlc_csv(h1_path))
    merged = merge_confirmed_h1_context(m15, h1)
    swings = add_swing_points(merged, left=swing_left, right=swing_right)
    candidates = add_pullback_candidates(
        swings,
        near_atr_multiplier=near_atr_multiplier,
        close_tolerance_atr_multiplier=close_tolerance_atr_multiplier,
    )

    # Keep A-signal columns for overlap diagnostics, but trade only B-signal below.
    with_a = add_hidden_divergence_flags(candidates)
    with_time = add_time_columns(
        with_a,
        time_col="time",
        server_timezone=server_timezone,
        fallback_server_utc_offset_hours=server_utc_offset,
        use_fixed_offset=use_fixed_offset,
    )

    settings = ReaccelerationSettings(
        recent_pullback_bars=recent_pullback_bars,
        require_macd_signal_alignment=require_macd_signal_alignment,
        require_histogram_acceleration=require_histogram_acceleration,
        require_ema20_reclaim=require_ema20_reclaim,
    )
    out = add_reacceleration_signals(with_time, settings=settings)

    # Reuse the existing backtest engine by mapping B-signal columns into the
    # hidden-divergence signal column names expected by run_simple_hidden_divergence_backtest.
    out["original_hidden_bullish_divergence"] = out["hidden_bullish_divergence"]
    out["original_hidden_bearish_divergence"] = out["hidden_bearish_divergence"]
    out["hidden_bullish_divergence"] = out["buy_reacceleration_signal"]
    out["hidden_bearish_divergence"] = out["sell_reacceleration_signal"]
    out["signal_model"] = "B_REACCELERATION"

    return out


def attach_jst_trade_times(trades, args: argparse.Namespace):
    if trades.empty:
        return trades

    out = trades.copy()
    for col in ["signal_time", "entry_time", "exit_time", "h1_time"]:
        if col in out.columns:
            out[f"jst_{col}"] = convert_server_time_to_jst(
                out[col],
                server_timezone=args.server_timezone,
                fallback_server_utc_offset_hours=args.server_utc_offset,
                use_fixed_offset=args.use_fixed_offset,
            )
    return out


def apply_trade_filters(
    trades,
    allowed_jst_hours: set[int] | None,
    allowed_sides: set[str] | None,
    allowed_buy_jst_hours: set[int] | None,
    allowed_sell_jst_hours: set[int] | None,
):
    if trades.empty:
        return trades

    out = trades.copy()

    if allowed_sides is not None:
        out = out[out["side"].isin(allowed_sides)].copy()

    hour_required = (
        allowed_jst_hours is not None
        or allowed_buy_jst_hours is not None
        or allowed_sell_jst_hours is not None
    )
    if hour_required and "jst_entry_time" not in out.columns:
        raise ValueError("jst_entry_time is required for JST hour filters")

    if allowed_jst_hours is not None:
        out = out[out["jst_entry_time"].dt.hour.isin(allowed_jst_hours)].copy()

    if allowed_buy_jst_hours is not None or allowed_sell_jst_hours is not None:
        hours = out["jst_entry_time"].dt.hour
        buy_mask = out["side"].eq("BUY")
        sell_mask = out["side"].eq("SELL")

        keep_mask = True
        if allowed_buy_jst_hours is not None:
            keep_mask = keep_mask & ((~buy_mask) | hours.isin(allowed_buy_jst_hours))
        if allowed_sell_jst_hours is not None:
            keep_mask = keep_mask & ((~sell_mask) | hours.isin(allowed_sell_jst_hours))

        out = out[keep_mask].copy()

    return out.reset_index(drop=True)


def print_time_conversion_info(args: argparse.Namespace) -> None:
    if args.use_fixed_offset:
        print(f"time_conversion_mode: fixed offset UTC+{args.server_utc_offset}")
        print(f"JST conversion: server_time + {server_to_jst_delta_hours(args.server_utc_offset)} hours")
    else:
        print("time_conversion_mode: timezone-aware DST")
        print(f"server_timezone: {args.server_timezone}")
        print("JST conversion: automatic DST-aware conversion to Asia/Tokyo")


def print_trade_report(title: str, trades) -> None:
    print("\n" + "-" * 120)
    print(title)
    print_summary_dict("backtest_summary", summarize_trades(trades))

    print("\nsummary_by_side:")
    by_side = summarize_by_side(trades)
    if by_side.empty:
        print("No trades.")
    else:
        print(by_side.to_string(index=False))

    print("\nsummary_by_jst_month:")
    by_jst_month = summarize_by_month(trades, time_col="jst_entry_time", label="jst_entry_month")
    if by_jst_month.empty:
        print("No trades.")
    else:
        print(by_jst_month.to_string(index=False))

    print("\nsummary_by_jst_entry_hour:")
    by_jst_hour = summarize_by_hour(trades, time_col="jst_entry_time", label="jst_entry_hour")
    if by_jst_hour.empty:
        print("No trades.")
    else:
        print(by_jst_hour.to_string(index=False))


def print_backtest_report(symbol: str, m15_path: Path, h1_path: Path, args: argparse.Namespace) -> None:
    allowed_jst_hours = parse_int_csv(args.allowed_jst_hours)
    allowed_buy_jst_hours = parse_int_csv(args.allowed_buy_jst_hours)
    allowed_sell_jst_hours = parse_int_csv(args.allowed_sell_jst_hours)

    allowed_sides = {side.upper() for side in parse_csv_list(args.allowed_sides)} if args.allowed_sides else None
    if allowed_sides is not None:
        invalid = allowed_sides - {"BUY", "SELL"}
        if invalid:
            raise ValueError(f"allowed_sides must be BUY and/or SELL: {invalid}")

    has_any_filter = (
        allowed_jst_hours is not None
        or allowed_sides is not None
        or allowed_buy_jst_hours is not None
        or allowed_sell_jst_hours is not None
    )

    print("=" * 120)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
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
    print(f"allowed_jst_hours: {sorted(allowed_jst_hours) if allowed_jst_hours is not None else 'ALL'}")
    print(f"allowed_buy_jst_hours: {sorted(allowed_buy_jst_hours) if allowed_buy_jst_hours is not None else 'ALL'}")
    print(f"allowed_sell_jst_hours: {sorted(allowed_sell_jst_hours) if allowed_sell_jst_hours is not None else 'ALL'}")
    print(f"allowed_sides: {sorted(allowed_sides) if allowed_sides is not None else 'ALL'}")
    print_time_conversion_info(args)

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    signal_df = build_b_signal_dataframe(
        m15_path=m15_path,
        h1_path=h1_path,
        near_atr_multiplier=args.near_atr,
        close_tolerance_atr_multiplier=args.close_tolerance_atr,
        swing_left=args.swing_left,
        swing_right=args.swing_right,
        recent_pullback_bars=args.recent_pullback_bars,
        require_ema20_reclaim=not args.no_ema20_reclaim,
        require_macd_signal_alignment=not args.no_macd_signal_alignment,
        require_histogram_acceleration=not args.no_histogram_acceleration,
        server_timezone=args.server_timezone,
        server_utc_offset=args.server_utc_offset,
        use_fixed_offset=args.use_fixed_offset,
    )

    print_summary_dict("pullback_summary", pullback_summary(signal_df))
    print_summary_dict("swing_summary", swing_summary(signal_df))
    print_summary_dict("original_A_hidden_divergence_summary", hidden_divergence_summary(signal_df.rename(columns={
        "hidden_bullish_divergence": "mapped_bull",
        "hidden_bearish_divergence": "mapped_bear",
        "original_hidden_bullish_divergence": "hidden_bullish_divergence",
        "original_hidden_bearish_divergence": "hidden_bearish_divergence",
    })))
    print_summary_dict("B_reacceleration_summary", reacceleration_summary(signal_df))

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    all_trades = run_simple_hidden_divergence_backtest(signal_df, settings=settings)
    all_trades = attach_jst_trade_times(all_trades, args=args)
    filtered_trades = apply_trade_filters(
        all_trades,
        allowed_jst_hours=allowed_jst_hours,
        allowed_sides=allowed_sides,
        allowed_buy_jst_hours=allowed_buy_jst_hours,
        allowed_sell_jst_hours=allowed_sell_jst_hours,
    )

    print_trade_report("B_REACCELERATION_ALL_TRADES", all_trades)

    if has_any_filter:
        print_trade_report("B_REACCELERATION_FILTERED_TRADES", filtered_trades)

    print("\nsummary_by_server_entry_hour baseline:")
    by_hour = summarize_by_entry_hour(all_trades)
    if by_hour.empty:
        print("No trades.")
    else:
        print(by_hour.to_string(index=False))

    display_cols = [
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
    ]

    print("\nrecent trades tail(20) baseline:")
    if all_trades.empty:
        print("No trades.")
    else:
        print(all_trades[display_cols].tail(20).to_string(index=False))

    if has_any_filter:
        print("\nrecent trades tail(20) filtered:")
        if filtered_trades.empty:
            print("No trades.")
        else:
            print(filtered_trades[display_cols].tail(20).to_string(index=False))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        base_path = RESULTS_DATA_DIR / f"{symbol.lower()}_reacceleration_backtest_trades_all.csv"
        all_trades.to_csv(base_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_all_trades: {base_path}")
        if has_any_filter:
            filtered_path = RESULTS_DATA_DIR / f"{symbol.lower()}_reacceleration_backtest_trades_filtered.csv"
            filtered_trades.to_csv(filtered_path, index=False, encoding="utf-8-sig")
            print(f"saved_filtered_trades: {filtered_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run EMA20 reclaim + MACD reacceleration B-signal backtest.")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default="gold", help="Comma-separated symbols. Default: gold")
    parser.add_argument("--near-atr", type=float, default=0.30, help="ATR multiplier for EMA20 proximity. Default: 0.30")
    parser.add_argument("--close-tolerance-atr", type=float, default=0.50, help="ATR multiplier for close tolerance. Default: 0.50")
    parser.add_argument("--swing-left", type=int, default=3, help="Left bars for swing detection. Default: 3")
    parser.add_argument("--swing-right", type=int, default=2, help="Right bars for swing detection. Default: 2")
    parser.add_argument("--recent-pullback-bars", type=int, default=6, help="Recent pullback lookback bars. Default: 6")
    parser.add_argument("--no-ema20-reclaim", action="store_true", help="Do not require close to cross/reclaim EMA20 from the prior bar.")
    parser.add_argument("--no-macd-signal-alignment", action="store_true", help="Do not require MACD line vs signal alignment.")
    parser.add_argument("--no-histogram-acceleration", action="store_true", help="Do not require MACD histogram acceleration.")
    parser.add_argument("--rr", type=float, default=1.5, help="Risk reward ratio. Default: 1.5")
    parser.add_argument("--sl-buffer-atr", type=float, default=0.05, help="SL buffer ATR multiplier. Default: 0.05")
    parser.add_argument("--server-timezone", type=str, default=DEFAULT_MT5_SERVER_TIMEZONE, help="IANA timezone for MT5 server time. Default: Europe/Athens")
    parser.add_argument("--server-utc-offset", type=int, default=3, help="Fallback fixed UTC offset hours. Used only with --use-fixed-offset.")
    parser.add_argument("--use-fixed-offset", action="store_true", help="Use fixed UTC offset instead of DST-aware timezone conversion.")
    parser.add_argument("--allowed-jst-hours", type=str, default=None, help="Comma-separated JST entry hours to keep for all sides.")
    parser.add_argument("--allowed-buy-jst-hours", type=str, default=None, help="Comma-separated JST entry hours to keep for BUY trades only.")
    parser.add_argument("--allowed-sell-jst-hours", type=str, default=None, help="Comma-separated JST entry hours to keep for SELL trades only.")
    parser.add_argument("--allowed-sides", type=str, default=None, help="Comma-separated sides to keep: BUY,SELL. Example: BUY")
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
    print("Reacceleration backtest completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
