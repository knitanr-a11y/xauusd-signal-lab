from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_pullback_segments.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.indicators import add_basic_indicators
from src.pullback import add_pullback_candidates, pullback_summary
from src.pullback_segments import (
    add_hidden_divergence_to_segments,
    build_pullback_segments,
    segment_summary,
)
from src.swings import add_swing_points, swing_summary
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE, add_time_columns
from src.timeframe_merge import merge_confirmed_h1_context


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def print_dict(title: str, data: dict[str, object]) -> None:
    print(f"\n{title}:")
    for key, value in data.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def build_base_dataframe(
    m15_path: Path,
    h1_path: Path,
    near_atr_multiplier: float,
    close_tolerance_atr_multiplier: float,
    swing_left: int,
    swing_right: int,
    server_timezone: str,
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
    return add_time_columns(candidates, time_col="time", server_timezone=server_timezone)


def print_report(symbol: str, m15_path: Path, h1_path: Path, args: argparse.Namespace) -> None:
    print("=" * 120)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
    print(f"near_atr_multiplier: {args.near_atr}")
    print(f"close_tolerance_atr_multiplier: {args.close_tolerance_atr}")
    print(f"swing_left: {args.swing_left}")
    print(f"swing_right: {args.swing_right}")
    print(f"max_gap_bars: {args.max_gap_bars}")
    print(f"min_segment_bars: {args.min_segment_bars}")
    print(f"server_timezone: {args.server_timezone}")

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    df = build_base_dataframe(
        m15_path=m15_path,
        h1_path=h1_path,
        near_atr_multiplier=args.near_atr,
        close_tolerance_atr_multiplier=args.close_tolerance_atr,
        swing_left=args.swing_left,
        swing_right=args.swing_right,
        server_timezone=args.server_timezone,
    )

    segments = build_pullback_segments(
        df,
        max_gap_bars=args.max_gap_bars,
        min_segment_bars=args.min_segment_bars,
    )
    segments = add_hidden_divergence_to_segments(segments)
    segments = add_time_columns(segments, time_col="segment_signal_time", server_timezone=args.server_timezone)

    print_dict("pullback_summary", pullback_summary(df))
    print_dict("swing_summary", swing_summary(df))
    print_dict("segment_summary", segment_summary(segments))

    if segments.empty:
        print("\nNo segments found.")
        return

    by_side = (
        segments.groupby("side", dropna=False)
        .agg(
            segments=("segment_id", "count"),
            hidden=("hidden_divergence", "sum"),
            avg_bars=("segment_bars", "mean"),
            max_bars=("segment_bars", "max"),
        )
        .reset_index()
    )
    print("\nsegments_by_side:")
    print(by_side.to_string(index=False))

    hidden = segments[segments["hidden_divergence"]].copy()
    if hidden.empty:
        print("\nNo hidden divergence segments found.")
        return

    by_jst_hour = (
        hidden.groupby(["side", "jst_hour"], dropna=False)
        .agg(hidden_segments=("segment_id", "count"), avg_bars=("segment_bars", "mean"))
        .reset_index()
        .sort_values(["side", "jst_hour"])
    )
    print("\nhidden_segments_by_side_and_jst_hour:")
    print(by_jst_hour.to_string(index=False))

    cols = [
        "segment_id",
        "side",
        "segment_start_time",
        "segment_end_time",
        "segment_signal_time",
        "jst_time",
        "segment_bars",
        "extreme_time",
        "extreme_price",
        "extreme_macd",
        "h1_trend",
        "last_confirmed_swing_low_time",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_low_macd",
        "last_confirmed_swing_high_time",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_high_macd",
        "hidden_bullish_divergence",
        "hidden_bearish_divergence",
        "bullish_hidden_price_delta",
        "bullish_hidden_macd_delta",
        "bearish_hidden_price_delta",
        "bearish_hidden_macd_delta",
    ]

    print("\nrecent hidden BUY segment tail(15):")
    buy_hidden = hidden[hidden["side"] == "BUY"].tail(15)
    if buy_hidden.empty:
        print("No BUY hidden segments.")
    else:
        print(buy_hidden[cols].to_string(index=False))

    print("\nrecent hidden SELL segment tail(15):")
    sell_hidden = hidden[hidden["side"] == "SELL"].tail(15)
    if sell_hidden.empty:
        print("No SELL hidden segments.")
    else:
        print(sell_hidden[cols].to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check pullback/retracement segments and segment-level hidden divergence.")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default="gold", help="Comma-separated symbols. Default: gold")
    parser.add_argument("--near-atr", type=float, default=0.30, help="ATR multiplier for EMA20 proximity. Default: 0.30")
    parser.add_argument("--close-tolerance-atr", type=float, default=0.50, help="ATR multiplier for close tolerance. Default: 0.50")
    parser.add_argument("--swing-left", type=int, default=3, help="Left bars for swing detection. Default: 3")
    parser.add_argument("--swing-right", type=int, default=2, help="Right bars for swing detection. Default: 2")
    parser.add_argument("--max-gap-bars", type=int, default=1, help="Allowed non-candidate gap bars inside one segment. Default: 1")
    parser.add_argument("--min-segment-bars", type=int, default=1, help="Minimum segment bars. Default: 1")
    parser.add_argument("--server-timezone", type=str, default=DEFAULT_MT5_SERVER_TIMEZONE, help="IANA timezone for MT5 server time. Default: Europe/Athens")
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = parse_csv_list(args.symbols)
    for symbol in symbols:
        m15_path, h1_path = build_paths(args.data_dir, symbol)
        print_report(symbol, m15_path, h1_path, args)

    print("=" * 120)
    print("Pullback segment check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
