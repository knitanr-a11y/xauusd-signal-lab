from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_swings.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.indicators import add_basic_indicators
from src.swings import add_swing_points, swing_summary


def build_path(data_dir: Path, symbol: str, timeframe: str) -> Path:
    return data_dir / f"{symbol.lower()}_{timeframe.lower()}.csv"


def print_swing_report(path: Path, left: int, right: int) -> None:
    print("=" * 100)
    print(f"file: {path}")
    print(f"swing_left: {left}")
    print(f"swing_right: {right}")

    if not path.exists():
        print(f"File not found: {path}")
        return

    df = add_basic_indicators(load_ohlc_csv(path))
    out = add_swing_points(df, left=left, right=right)
    summary = swing_summary(out)

    print(f"rows: {summary['rows']}")
    print(f"swing_high_count: {summary['swing_high_count']}")
    print(f"swing_low_count: {summary['swing_low_count']}")
    print(f"rows_with_confirmed_high: {summary['rows_with_confirmed_high']}")
    print(f"rows_with_confirmed_low: {summary['rows_with_confirmed_low']}")
    print(f"high_lookahead_violations: {summary['high_lookahead_violations']}")
    print(f"low_lookahead_violations: {summary['low_lookahead_violations']}")

    swing_cols = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "macd_line",
        "swing_high",
        "swing_high_price",
        "swing_high_confirm_time",
        "swing_high_usable_time",
        "swing_low",
        "swing_low_price",
        "swing_low_confirm_time",
        "swing_low_usable_time",
    ]

    last_cols = [
        "time",
        "close",
        "last_confirmed_swing_high_time",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_high_confirm_time",
        "last_confirmed_swing_high_macd",
        "last_confirmed_swing_low_time",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_low_confirm_time",
        "last_confirmed_swing_low_macd",
    ]

    recent_swings = out[out["swing_high"] | out["swing_low"]].tail(20)
    print("\nrecent raw swing points tail(20):")
    if recent_swings.empty:
        print("No swing points found.")
    else:
        print(recent_swings[swing_cols].to_string(index=False))

    print("\nlast confirmed swing state tail(20):")
    print(out[last_cols].tail(20).to_string(index=False))


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check confirmed swing high/low detection.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Directory containing raw CSV files. Default: data/raw",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="gold,btcusd",
        help="Comma-separated symbols to check. Default: gold,btcusd",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default="m15",
        help="Comma-separated timeframes to check. Default: m15",
    )
    parser.add_argument("--left", type=int, default=3, help="Left bars for swing detection. Default: 3")
    parser.add_argument("--right", type=int, default=2, help="Right bars for swing detection. Default: 2")
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return 1

    symbols = parse_csv_list(args.symbols)
    timeframes = parse_csv_list(args.timeframes)

    for symbol in symbols:
        for timeframe in timeframes:
            path = build_path(data_dir, symbol, timeframe)
            print_swing_report(path, left=args.left, right=args.right)

    print("=" * 100)
    print("Swing check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
