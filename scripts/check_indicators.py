from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_indicators.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_SYMBOLS, DEFAULT_TIMEFRAMES, RAW_DATA_DIR
from src.data_loader import find_csv_files, load_ohlc_csv
from src.indicators import add_basic_indicators, indicator_null_summary


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def print_indicator_report(path: Path) -> None:
    print("=" * 100)
    print(f"file: {path}")

    df = load_ohlc_csv(path)
    out = add_basic_indicators(df)

    indicator_cols = [
        "ema_20",
        "ema_50",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "macd_hist_diff",
        "true_range",
        "atr_14",
    ]

    print(f"rows: {len(out)}")
    print(f"start_time: {out['time'].iloc[0] if len(out) else None}")
    print(f"end_time: {out['time'].iloc[-1] if len(out) else None}")
    print(f"indicator_nulls: {indicator_null_summary(out)}")

    usable = out.dropna(subset=indicator_cols)
    print(f"fully_usable_rows_after_indicator_warmup: {len(usable)}")

    display_cols = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "ema_20",
        "ema_50",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "atr_14",
        "spread",
    ]

    print("\nfirst fully usable rows head(3):")
    if usable.empty:
        print("No fully usable rows. Check indicator periods or source data length.")
    else:
        print(usable[display_cols].head(3).to_string(index=False))

    print("\nlast rows tail(5):")
    print(out[display_cols].tail(5).to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate and inspect initial indicators for MT5 OHLC CSV files.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Directory containing raw CSV files. Default: data/raw",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated symbols. Default comes from src/config.py",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default=",".join(DEFAULT_TIMEFRAMES),
        help="Comma-separated timeframes. Default: m15,h1",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all CSV files in the data directory instead of expected symbol/timeframe names.",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return 1

    if args.all:
        files = sorted(data_dir.glob("*.csv"))
    else:
        symbols = parse_csv_list(args.symbols)
        timeframes = parse_csv_list(args.timeframes)
        files = find_csv_files(data_dir, symbols, timeframes)

    if not files:
        print(f"No CSV files found in: {data_dir}")
        print("Run with --all if your broker symbol names differ from config defaults.")
        return 1

    for path in files:
        print_indicator_report(path)

    print("=" * 100)
    print("Indicator check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
