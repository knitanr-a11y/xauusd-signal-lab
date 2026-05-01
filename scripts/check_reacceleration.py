from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as: python scripts/check_reacceleration.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.data_loader import load_ohlc_csv
from src.divergence import add_hidden_divergence_flags, hidden_divergence_summary
from src.indicators import add_basic_indicators
from src.pullback import add_pullback_candidates, pullback_summary
from src.reacceleration import (
    ReaccelerationSettings,
    add_reacceleration_signals,
    reacceleration_counts_by_jst_hour,
    reacceleration_summary,
)
from src.swings import add_swing_points, swing_summary
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE, add_time_columns
from src.timeframe_merge import merge_confirmed_h1_context


def build_paths(data_dir: Path, symbol: str) -> tuple[Path, Path]:
    symbol_lower = symbol.lower()
    return data_dir / f"{symbol_lower}_m15.csv", data_dir / f"{symbol_lower}_h1.csv"


def parse_csv_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def print_summary_dict(title: str, summary: dict[str, object]) -> None:
    print(f"\n{title}:")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def build_signal_dataframe(
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
    hidden = add_hidden_divergence_flags(candidates)
    return add_time_columns(hidden, time_col="time", server_timezone=server_timezone)


def print_report(symbol: str, m15_path: Path, h1_path: Path, args: argparse.Namespace) -> None:
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
    print(f"server_timezone: {args.server_timezone}")

    if not m15_path.exists():
        print(f"M15 file not found: {m15_path}")
        return
    if not h1_path.exists():
        print(f"H1 file not found: {h1_path}")
        return

    df = build_signal_dataframe(
        m15_path=m15_path,
        h1_path=h1_path,
        near_atr_multiplier=args.near_atr,
        close_tolerance_atr_multiplier=args.close_tolerance_atr,
        swing_left=args.swing_left,
        swing_right=args.swing_right,
        server_timezone=args.server_timezone,
    )

    settings = ReaccelerationSettings(
        recent_pullback_bars=args.recent_pullback_bars,
        require_macd_signal_alignment=not args.no_macd_signal_alignment,
        require_histogram_acceleration=not args.no_histogram_acceleration,
        require_ema20_reclaim=not args.no_ema20_reclaim,
    )
    out = add_reacceleration_signals(df, settings=settings)

    print_summary_dict("pullback_summary", pullback_summary(out))
    print_summary_dict("swing_summary", swing_summary(out))
    print_summary_dict("hidden_divergence_summary_A_signal", hidden_divergence_summary(out))
    print_summary_dict("reacceleration_summary_B_signal", reacceleration_summary(out))

    print("\nreacceleration_counts_by_jst_hour:")
    print(reacceleration_counts_by_jst_hour(out).to_string(index=False))

    if "hidden_bullish_divergence" in out.columns and "hidden_bearish_divergence" in out.columns:
        overlap_table = out.assign(
            any_hidden=out["hidden_bullish_divergence"].astype(bool) | out["hidden_bearish_divergence"].astype(bool),
            any_reaccel=out["buy_reacceleration_signal"].astype(bool) | out["sell_reacceleration_signal"].astype(bool),
        )
        print("\nA/B overlap counts:")
        print(
            overlap_table.groupby(["any_hidden", "any_reaccel"], dropna=False)
            .size()
            .reset_index(name="rows")
            .to_string(index=False)
        )

    display_cols = [
        "time",
        "jst_time",
        "close",
        "ema_20",
        "close_ema20_delta",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "macd_histogram_delta",
        "h1_trend",
        "pullback_side",
        "recent_buy_pullback",
        "recent_sell_pullback",
        "hidden_bullish_divergence",
        "hidden_bearish_divergence",
        "buy_reacceleration_signal",
        "sell_reacceleration_signal",
        "reacceleration_side",
    ]

    buy_examples = out[out["buy_reacceleration_signal"]].tail(20)
    sell_examples = out[out["sell_reacceleration_signal"]].tail(20)

    print("\nrecent BUY reacceleration tail(20):")
    if buy_examples.empty:
        print("No BUY reacceleration signals.")
    else:
        print(buy_examples[display_cols].to_string(index=False))

    print("\nrecent SELL reacceleration tail(20):")
    if sell_examples.empty:
        print("No SELL reacceleration signals.")
    else:
        print(sell_examples[display_cols].to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check EMA20 reclaim + MACD reacceleration B-signals.")
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
    print("Reacceleration check completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
