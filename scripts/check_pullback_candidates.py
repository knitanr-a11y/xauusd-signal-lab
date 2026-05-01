from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_pullback_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.indicators import add_basic_indicators
from src.pullback import add_pullback_candidates, pullback_counts_by_h1_trend, pullback_summary
from src.timeframe_merge import merge_confirmed_h1_context


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def print_pullback_report(
    symbol: str,
    m15_path: Path,
    h1_path: Path,
    near_atr_multiplier: float,
    close_tolerance_atr_multiplier: float,
) -> None:
    print("=" * 100)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
    print(f"near_atr_multiplier: {near_atr_multiplier}")
    print(f"close_tolerance_atr_multiplier: {close_tolerance_atr_multiplier}")

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    m15 = add_basic_indicators(load_ohlc_csv(m15_path))
    h1 = add_basic_indicators(load_ohlc_csv(h1_path))
    merged = merge_confirmed_h1_context(m15, h1)
    candidates = add_pullback_candidates(
        merged,
        near_atr_multiplier=near_atr_multiplier,
        close_tolerance_atr_multiplier=close_tolerance_atr_multiplier,
    )

    summary = pullback_summary(candidates)
    print(f"rows: {summary['rows']}")
    print(f"buy_pullback_candidates: {summary['buy_pullback_candidates']} ({summary['buy_ratio']:.2%})")
    print(f"sell_pullback_candidates: {summary['sell_pullback_candidates']} ({summary['sell_ratio']:.2%})")
    print(f"both_pullback_candidates: {summary['both_pullback_candidates']}")

    print("\ncounts_by_h1_trend:")
    print(pullback_counts_by_h1_trend(candidates).to_string(index=False))

    display_cols = [
        "time",
        "close",
        "low",
        "high",
        "ema_20",
        "atr_14",
        "h1_time",
        "h1_trend",
        "buy_pullback_candidate",
        "sell_pullback_candidate",
        "pullback_side",
    ]

    buy_examples = candidates[candidates["buy_pullback_candidate"]].tail(10)
    sell_examples = candidates[candidates["sell_pullback_candidate"]].tail(10)

    print("\nrecent BUY pullback candidates tail(10):")
    if buy_examples.empty:
        print("No BUY pullback candidates found.")
    else:
        print(buy_examples[display_cols].to_string(index=False))

    print("\nrecent SELL pullback candidates tail(10):")
    if sell_examples.empty:
        print("No SELL pullback candidates found.")
    else:
        print(sell_examples[display_cols].to_string(index=False))

    print("\nlast rows tail(12):")
    print(candidates[display_cols].tail(12).to_string(index=False))


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check M15 pullback/retracement candidates with confirmed H1 context.")
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
        "--near-atr",
        type=float,
        default=0.30,
        help="ATR multiplier for EMA20 proximity. Default: 0.30",
    )
    parser.add_argument(
        "--close-tolerance-atr",
        type=float,
        default=0.50,
        help="ATR multiplier for close tolerance around EMA20. Default: 0.50",
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
        print_pullback_report(
            symbol=symbol,
            m15_path=m15_path,
            h1_path=h1_path,
            near_atr_multiplier=args.near_atr,
            close_tolerance_atr_multiplier=args.close_tolerance_atr,
        )

    print("=" * 100)
    print("Pullback candidate check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
