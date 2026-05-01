from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_h1_context.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.indicators import add_basic_indicators
from src.timeframe_merge import h1_context_summary, merge_confirmed_h1_context


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def print_context_report(symbol: str, m15_path: Path, h1_path: Path) -> None:
    print("=" * 100)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    m15 = add_basic_indicators(load_ohlc_csv(m15_path))
    h1 = add_basic_indicators(load_ohlc_csv(h1_path))

    merged = merge_confirmed_h1_context(m15, h1)
    summary = h1_context_summary(merged)

    print(f"rows: {summary['rows']}")
    print(f"missing_h1_time: {summary['missing_h1_time']}")
    print(f"trend_counts: {summary['trend_counts']}")
    print(f"lookahead_violations: {summary['lookahead_violations']}")

    display_cols = [
        "time",
        "close",
        "ema_20",
        "ema_50",
        "h1_time",
        "h1_close",
        "h1_ema_20",
        "h1_ema_50",
        "h1_trend",
        "h1_buy_env",
        "h1_sell_env",
    ]

    print("\nhead(8):")
    print(merged[display_cols].head(8).to_string(index=False))

    print("\ntail(12):")
    print(merged[display_cols].tail(12).to_string(index=False))

    # Show examples around hour boundaries to verify confirmed-H1 behavior.
    boundary = merged[merged["time"].dt.minute.isin([0, 15, 30, 45])].tail(16)
    print("\nrecent boundary check tail(16):")
    print(boundary[display_cols].to_string(index=False))


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check confirmed H1 context merge into M15 data.")
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
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return 1

    symbols = parse_csv_list(args.symbols)
    if not symbols:
        print("No symbols provided.")
        return 1

    for symbol in symbols:
        m15_path, h1_path = build_paths(data_dir, symbol)
        print_context_report(symbol, m15_path, h1_path)

    print("=" * 100)
    print("H1 context check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
