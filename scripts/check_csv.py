from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/check_csv.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_SYMBOLS, DEFAULT_TIMEFRAMES, RAW_DATA_DIR
from src.data_loader import build_quality_report, find_csv_files, load_ohlc_csv


def print_report(path: Path) -> None:
    report = build_quality_report(path)

    print("=" * 80)
    print(f"file: {report.path}")
    print(f"timeframe: {report.timeframe or 'unknown'}")
    print(f"rows: {report.rows}")
    print(f"start_time: {report.start_time}")
    print(f"end_time: {report.end_time}")
    print(f"duplicate_times: {report.duplicate_times}")

    if report.missing_required_columns:
        print(f"missing_required_columns: {report.missing_required_columns}")
        print("This file cannot be used until required columns are fixed.")
        return

    print(f"null_counts: {report.null_counts}")
    print(f"invalid_ohlc_rows: {report.invalid_ohlc_rows}")
    print(f"negative_volume_rows: {report.negative_volume_rows}")
    print(f"negative_spread_rows: {report.negative_spread_rows}")
    print(
        "spread: "
        f"min={report.spread_min}, "
        f"max={report.spread_max}, "
        f"mean={report.spread_mean}"
    )
    print(f"interval_anomaly_count: {report.interval_anomaly_count}")

    if report.interval_anomaly_examples:
        print("interval_anomaly_examples: prev_time -> curr_time | diff_minutes")
        for prev_time, curr_time, diff_minutes in report.interval_anomaly_examples:
            print(f"  {prev_time} -> {curr_time} | {diff_minutes}")

    df = load_ohlc_csv(path)

    print("\nhead(3):")
    print(df.head(3).to_string(index=False))

    print("\ntail(3):")
    print(df.tail(3).to_string(index=False))


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check MT5-exported OHLC CSV files.")
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
        help="Comma-separated symbols. Default: xauusd,btcusd",
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
        print("Create it and copy MT5 CSV files into it, e.g. data/raw/xauusd_m15.csv")
        return 1

    if args.all:
        files = sorted(data_dir.glob("*.csv"))
    else:
        symbols = parse_csv_list(args.symbols)
        timeframes = parse_csv_list(args.timeframes)
        files = find_csv_files(data_dir, symbols, timeframes)

    if not files:
        print(f"No CSV files found in: {data_dir}")
        print("Expected examples:")
        print("  data/raw/xauusd_m15.csv")
        print("  data/raw/xauusd_h1.csv")
        print("  data/raw/btcusd_m15.csv")
        print("  data/raw/btcusd_h1.csv")
        print("If your broker uses suffixes, either rename copied files or run with --all.")
        return 1

    for path in files:
        print_report(path)

    print("=" * 80)
    print("CSV check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
