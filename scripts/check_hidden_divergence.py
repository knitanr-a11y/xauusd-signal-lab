from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_hidden_divergence.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.divergence import (
    add_hidden_divergence_flags,
    hidden_divergence_counts_by_h1_trend,
    hidden_divergence_summary,
)
from src.indicators import add_basic_indicators
from src.pullback import add_pullback_candidates, pullback_summary
from src.swings import add_swing_points, swing_summary
from src.timeframe_merge import merge_confirmed_h1_context


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def print_hidden_divergence_report(
    symbol: str,
    m15_path: Path,
    h1_path: Path,
    near_atr_multiplier: float,
    close_tolerance_atr_multiplier: float,
    swing_left: int,
    swing_right: int,
) -> None:
    print("=" * 120)
    print(f"symbol: {symbol}")
    print(f"m15_file: {m15_path}")
    print(f"h1_file: {h1_path}")
    print(f"near_atr_multiplier: {near_atr_multiplier}")
    print(f"close_tolerance_atr_multiplier: {close_tolerance_atr_multiplier}")
    print(f"swing_left: {swing_left}")
    print(f"swing_right: {swing_right}")

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    m15 = add_basic_indicators(load_ohlc_csv(m15_path))
    h1 = add_basic_indicators(load_ohlc_csv(h1_path))

    merged = merge_confirmed_h1_context(m15, h1)
    swings = add_swing_points(merged, left=swing_left, right=swing_right)
    candidates = add_pullback_candidates(
        swings,
        near_atr_multiplier=near_atr_multiplier,
        close_tolerance_atr_multiplier=close_tolerance_atr_multiplier,
    )
    out = add_hidden_divergence_flags(candidates)

    print("\npullback_summary:")
    print(pullback_summary(out))

    print("\nswing_summary:")
    print(swing_summary(out))

    print("\nhidden_divergence_summary:")
    print(hidden_divergence_summary(out))

    print("\nhidden_divergence_counts_by_h1_trend:")
    print(hidden_divergence_counts_by_h1_trend(out).to_string(index=False))

    display_cols = [
        "time",
        "close",
        "low",
        "high",
        "ema_20",
        "atr_14",
        "macd_line",
        "h1_time",
        "h1_trend",
        "pullback_side",
        "last_confirmed_swing_low_time",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_low_macd",
        "last_confirmed_swing_high_time",
        "last_confirmed_swing_high_price",
        "last_confirmed_swing_high_macd",
        "hidden_bullish_divergence",
        "hidden_bearish_divergence",
        "hidden_divergence_side",
        "bullish_hidden_price_delta",
        "bullish_hidden_macd_delta",
        "bearish_hidden_price_delta",
        "bearish_hidden_macd_delta",
    ]

    bullish_examples = out[out["hidden_bullish_divergence"]].tail(15)
    bearish_examples = out[out["hidden_bearish_divergence"]].tail(15)

    print("\nrecent hidden BULLISH divergence tail(15):")
    if bullish_examples.empty:
        print("No hidden bullish divergence found.")
    else:
        print(bullish_examples[display_cols].to_string(index=False))

    print("\nrecent hidden BEARISH divergence tail(15):")
    if bearish_examples.empty:
        print("No hidden bearish divergence found.")
    else:
        print(bearish_examples[display_cols].to_string(index=False))

    print("\nlast rows tail(12):")
    print(out[display_cols].tail(12).to_string(index=False))


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check simplified hidden divergence signals.")
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
    parser.add_argument("--swing-left", type=int, default=3, help="Left bars for swing detection. Default: 3")
    parser.add_argument("--swing-right", type=int, default=2, help="Right bars for swing detection. Default: 2")
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
        print_hidden_divergence_report(
            symbol=symbol,
            m15_path=m15_path,
            h1_path=h1_path,
            near_atr_multiplier=args.near_atr,
            close_tolerance_atr_multiplier=args.close_tolerance_atr,
            swing_left=args.swing_left,
            swing_right=args.swing_right,
        )

    print("=" * 120)
    print("Hidden divergence check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
