from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_c2_sell_filter_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c2_signal_trades import build_c2_signal_df, enrich_c2_trades, print_section
from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped
from scripts.run_combined_backtest import attach_jst_trade_times
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


@dataclass(frozen=True)
class C2SellFilterCandidate:
    name: str
    description: str
    keep_func: Callable[[pd.DataFrame], pd.Series]
    max_bars_in_trade: int | None = None


def _true_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


def _c2_sell_base_mask(df: pd.DataFrame) -> pd.Series:
    return df["c2_sell_signal_filtered"].fillna(False).astype(bool)


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def _range_width_atr(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c2_previous_range_width_atr"], errors="coerce")


def _macd_delta(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c2_macd_hist_delta"], errors="coerce")


def _h1_gap_side_atr(df: pd.DataFrame) -> pd.Series:
    # SELL side signed value: larger positive means H1 EMA20 is sufficiently below EMA50.
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    return -h1_gap / atr


def _breakout_atr(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c2_sell_breakout_distance_atr"], errors="coerce")


def _risk_atr(df: pd.DataFrame) -> pd.Series:
    # Approximate SELL risk at signal close. Full backtest reruns after filtering.
    entry_proxy = pd.to_numeric(df["close"], errors="coerce")
    swing_high = pd.to_numeric(df["last_confirmed_swing_high_price"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    buffer = atr * 0.05
    return ((swing_high + buffer) - entry_proxy) / atr


def build_candidates() -> list[C2SellFilterCandidate]:
    def baseline(df: pd.DataFrame) -> pd.Series:
        return _true_mask(df)

    def good_hours_11_14_17(df: pd.DataFrame) -> pd.Series:
        # Based on first C2 diagnostics: 11,14,17 were positive clusters.
        return _jst_hour(df).isin({11, 14, 17})

    def broad_positive_hours(df: pd.DataFrame) -> pd.Series:
        # Include flat/small positive hours; excludes clearly weak groups from first diagnostics.
        return _jst_hour(df).isin({3, 4, 5, 11, 12, 14, 17, 18, 22})

    def range_gt_203(df: pd.DataFrame) -> pd.Series:
        return _range_width_atr(df).gt(2.03)

    def range_2175_2367(df: pd.DataFrame) -> pd.Series:
        width = _range_width_atr(df)
        return width.gt(2.175) & width.le(2.367)

    def range_203_250(df: pd.DataFrame) -> pd.Series:
        width = _range_width_atr(df)
        return width.gt(2.03) & width.le(2.50)

    def macd_mid(df: pd.DataFrame) -> pd.Series:
        macd = _macd_delta(df)
        return macd.gt(-0.633) & macd.le(-0.256)

    def macd_not_weak(df: pd.DataFrame) -> pd.Series:
        # Avoid the weakest quartiles from first diagnostics: -1.58 to -0.633 and -0.256 to -0.0396.
        macd = _macd_delta(df)
        return macd.le(-0.256) & ~((macd.gt(-1.58)) & (macd.le(-0.633)))

    def h1_gt_2743(df: pd.DataFrame) -> pd.Series:
        return _h1_gap_side_atr(df).gt(2.743)

    def h1_gt_1721(df: pd.DataFrame) -> pd.Series:
        return _h1_gap_side_atr(df).gt(1.721)

    def h1_gt_2743_and_macd_mid(df: pd.DataFrame) -> pd.Series:
        return h1_gt_2743(df) & macd_mid(df)

    def h1_gt_2743_and_range_2175_2367(df: pd.DataFrame) -> pd.Series:
        return h1_gt_2743(df) & range_2175_2367(df)

    def h1_gt_1721_and_range_gt_203(df: pd.DataFrame) -> pd.Series:
        return h1_gt_1721(df) & range_gt_203(df)

    def h1_gt_1721_and_macd_mid(df: pd.DataFrame) -> pd.Series:
        return h1_gt_1721(df) & macd_mid(df)

    def h1_gt_1721_range_gt_203_macd_not_weak(df: pd.DataFrame) -> pd.Series:
        return h1_gt_1721(df) & range_gt_203(df) & macd_not_weak(df)

    def breakout_gt_0965(df: pd.DataFrame) -> pd.Series:
        return _breakout_atr(df).gt(0.965)

    def risk_gt_2256(df: pd.DataFrame) -> pd.Series:
        return _risk_atr(df).gt(2.256)

    return [
        C2SellFilterCandidate(
            name="c2_sell_baseline",
            description="C2 SELL baseline. Range compression breakout SELL only.",
            keep_func=baseline,
        ),
        C2SellFilterCandidate(
            name="c2_sell_baseline_max_bars_20",
            description="C2 SELL baseline with max_bars_in_trade=20.",
            keep_func=baseline,
            max_bars_in_trade=20,
        ),
        C2SellFilterCandidate(
            name="c2_sell_baseline_max_bars_30",
            description="C2 SELL baseline with max_bars_in_trade=30.",
            keep_func=baseline,
            max_bars_in_trade=30,
        ),
        C2SellFilterCandidate(
            name="c2_sell_good_hours_11_14_17",
            description="C2 SELL only at JST entry-similar signal hours 11,14,17.",
            keep_func=good_hours_11_14_17,
        ),
        C2SellFilterCandidate(
            name="c2_sell_broad_positive_hours",
            description="C2 SELL broad non-negative hours from first diagnostics.",
            keep_func=broad_positive_hours,
        ),
        C2SellFilterCandidate(
            name="c2_sell_range_width_atr_gt_2_03",
            description="C2 SELL when previous range width ATR > 2.03.",
            keep_func=range_gt_203,
        ),
        C2SellFilterCandidate(
            name="c2_sell_range_width_atr_2_175_to_2_367",
            description="C2 SELL when previous range width ATR is >2.175 and <=2.367.",
            keep_func=range_2175_2367,
        ),
        C2SellFilterCandidate(
            name="c2_sell_range_width_atr_2_03_to_2_50",
            description="C2 SELL when previous range width ATR is >2.03 and <=2.50.",
            keep_func=range_203_250,
        ),
        C2SellFilterCandidate(
            name="c2_sell_macd_delta_mid_-0_633_to_-0_256",
            description="C2 SELL when MACD hist delta is > -0.633 and <= -0.256.",
            keep_func=macd_mid,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_2_743",
            description="C2 SELL when side-signed H1 EMA gap > 2.743 ATR.",
            keep_func=h1_gt_2743,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_1_721",
            description="C2 SELL when side-signed H1 EMA gap > 1.721 ATR.",
            keep_func=h1_gt_1721,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_2_743_and_macd_mid",
            description="C2 SELL with H1 gap > 2.743 and MACD hist delta > -0.633 <= -0.256.",
            keep_func=h1_gt_2743_and_macd_mid,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_2_743_and_range_2_175_to_2_367",
            description="C2 SELL with H1 gap > 2.743 and range width >2.175 <=2.367 ATR.",
            keep_func=h1_gt_2743_and_range_2175_2367,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_1_721_and_range_gt_2_03",
            description="C2 SELL with H1 gap > 1.721 and range width >2.03 ATR.",
            keep_func=h1_gt_1721_and_range_gt_203,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_1_721_and_macd_mid",
            description="C2 SELL with H1 gap > 1.721 and MACD hist delta > -0.633 <= -0.256.",
            keep_func=h1_gt_1721_and_macd_mid,
        ),
        C2SellFilterCandidate(
            name="c2_sell_h1_gap_gt_1_721_range_gt_2_03_macd_not_weak",
            description="C2 SELL with H1 gap >1.721, range width >2.03, excluding weak MACD delta bands.",
            keep_func=h1_gt_1721_range_gt_203_macd_not_weak,
        ),
        C2SellFilterCandidate(
            name="c2_sell_breakout_distance_atr_gt_0_965",
            description="C2 SELL when breakout distance ATR > 0.965.",
            keep_func=breakout_gt_0965,
        ),
        C2SellFilterCandidate(
            name="c2_sell_risk_atr_gt_2_256",
            description="C2 SELL when estimated risk ATR > 2.256.",
            keep_func=risk_gt_2256,
        ),
    ]


def apply_candidate(signal_df: pd.DataFrame, candidate: C2SellFilterCandidate) -> pd.DataFrame:
    out = signal_df.copy()
    base_sell = _c2_sell_base_mask(out)
    keep = candidate.keep_func(out).fillna(False).astype(bool)
    out["c2_sell_candidate_name"] = candidate.name
    out["c2_sell_candidate_keep"] = keep & base_sell
    out["c2_sell_signal_candidate"] = base_sell & keep
    out["c2_buy_signal_candidate"] = False
    out["hidden_bullish_divergence"] = False
    out["hidden_bearish_divergence"] = out["c2_sell_signal_candidate"]
    return out


def run_candidate(
    *,
    args: argparse.Namespace,
    base_signal_df: pd.DataFrame,
    candidate: C2SellFilterCandidate,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidate_df = apply_candidate(base_signal_df, candidate)
    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=candidate.max_bars_in_trade if candidate.max_bars_in_trade is not None else args.max_bars_in_trade,
    )
    trades = run_simple_hidden_divergence_backtest(candidate_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = enrich_c2_trades(trades, candidate_df, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)
    if not trades.empty:
        trades["candidate"] = candidate.name

    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "c2_sell_candidate_signals": int(candidate_df["c2_sell_signal_candidate"].sum()),
        "max_bars_in_trade": candidate.max_bars_in_trade if candidate.max_bars_in_trade is not None else args.max_bars_in_trade,
    }
    row.update(summary)
    if trades.empty:
        row.update(
            {
                "early_losses": 0,
                "long_hold_losses": 0,
                "avg_risk_atr_ratio": None,
                "avg_breakout_distance_atr": None,
                "avg_range_width_atr": None,
                "avg_h1_gap_side_atr": None,
                "avg_macd_delta": None,
            }
        )
    else:
        row.update(
            {
                "early_losses": int(trades["early_loss"].sum()) if "early_loss" in trades.columns else 0,
                "long_hold_losses": int(trades["long_hold_loss"].sum()) if "long_hold_loss" in trades.columns else 0,
                "avg_risk_atr_ratio": pd.to_numeric(trades.get("risk_atr_ratio", pd.Series(index=trades.index)), errors="coerce").mean(),
                "avg_breakout_distance_atr": pd.to_numeric(trades.get("breakout_distance_atr", pd.Series(index=trades.index)), errors="coerce").mean(),
                "avg_range_width_atr": pd.to_numeric(trades.get("signal_c2_previous_range_width_atr", pd.Series(index=trades.index)), errors="coerce").mean(),
                "avg_h1_gap_side_atr": pd.to_numeric(trades.get("h1_ema_gap_side_signed_atr", pd.Series(index=trades.index)), errors="coerce").mean(),
                "avg_macd_delta": pd.to_numeric(trades.get("signal_c2_macd_hist_delta", pd.Series(index=trades.index)), errors="coerce").mean(),
            }
        )
    return candidate_df, trades, row


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare C2 SELL range-compression breakout filter candidates.")
    parser.add_argument("--preset", type=str, default="gold_abc_v1", help="Preset context. Default: gold_abc_v1")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--symbols", type=str, default=None)
    parser.add_argument("--models", type=str, default=None)
    parser.add_argument("--near-atr", type=float, default=None)
    parser.add_argument("--close-tolerance-atr", type=float, default=None)
    parser.add_argument("--swing-left", type=int, default=None)
    parser.add_argument("--swing-right", type=int, default=None)
    parser.add_argument("--recent-pullback-bars", type=int, default=None)
    parser.add_argument("--no-ema20-reclaim", action="store_true")
    parser.add_argument("--no-macd-signal-alignment", action="store_true")
    parser.add_argument("--no-histogram-acceleration", action="store_true")
    parser.add_argument("--rr", type=float, default=None)
    parser.add_argument("--sl-buffer-atr", type=float, default=None)
    parser.add_argument("--server-timezone", type=str, default=None)
    parser.add_argument("--server-utc-offset", type=int, default=None)
    parser.add_argument("--use-fixed-offset", action="store_true")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None)
    parser.add_argument("--a-sell-jst-hours", type=str, default=None)
    parser.add_argument("--a-exclude-hidden-price-delta-atr-lte", type=float, default=None)
    parser.add_argument("--b-buy-jst-hours", type=str, default=None)
    parser.add_argument("--b-sell-jst-hours", type=str, default=None)
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None)
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None)
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None)

    parser.add_argument("--c2-range-lookback-bars", type=int, default=12)
    parser.add_argument("--c2-max-range-width-atr", type=float, default=2.50)
    parser.add_argument("--c2-min-breakout-atr", type=float, default=0.0)
    parser.add_argument("--c2-max-breakout-atr", type=float, default=None)
    parser.add_argument("--c2-buy-jst-hours", type=str, default=None)
    parser.add_argument("--c2-sell-jst-hours", type=str, default=None)
    parser.add_argument("--c2-disable-buy", action="store_true", default=True)
    parser.add_argument("--c2-enable-buy", dest="c2_disable_buy", action="store_false")
    parser.add_argument("--c2-disable-sell", action="store_true")
    parser.add_argument("--c2-no-h1-trend", action="store_true")
    parser.add_argument("--c2-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c2-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c2-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c2-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c2-allow-ab-overlap", action="store_true")
    parser.add_argument("--early-loss-bars", type=int, default=2)
    parser.add_argument("--long-hold-bars", type=int, default=20)
    parser.add_argument("--save", action="store_true")
    args = apply_preset_defaults(parser.parse_args())

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = [item.strip().lower() for item in args.symbols.split(",") if item.strip()]
    if not symbols:
        print("No symbols provided.")
        return 1

    candidates = build_candidates()
    all_rows: list[dict[str, object]] = []
    all_trades: list[pd.DataFrame] = []

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset_context: {args.preset}")
        print("target: C2 SELL filter candidate comparison")
        print(f"c2_range_lookback_bars: {args.c2_range_lookback_bars}")
        print(f"c2_max_range_width_atr: {args.c2_max_range_width_atr}")

        base_signal_df = build_c2_signal_df(args, symbol=symbol)
        symbol_rows: list[dict[str, object]] = []
        symbol_trade_map: dict[str, pd.DataFrame] = {}

        for candidate in candidates:
            _candidate_df, trades, row = run_candidate(args=args, base_signal_df=base_signal_df, candidate=candidate)
            row["symbol"] = symbol
            symbol_rows.append(row)
            all_rows.append(row)
            symbol_trade_map[candidate.name] = trades
            if not trades.empty:
                trades = trades.copy()
                trades["symbol"] = symbol
                all_trades.append(trades)

        summary_df = pd.DataFrame(symbol_rows)
        ordered_cols = [
            "symbol",
            "candidate",
            "c2_sell_candidate_signals",
            "max_bars_in_trade",
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
            "early_losses",
            "long_hold_losses",
            "avg_risk_atr_ratio",
            "avg_breakout_distance_atr",
            "avg_range_width_atr",
            "avg_h1_gap_side_atr",
            "avg_macd_delta",
            "description",
        ]
        available = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("C2_SELL_FILTER_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

        if not summary_df.empty:
            best_name = str(summary_df.iloc[0]["candidate"])
            best_trades = symbol_trade_map.get(best_name, pd.DataFrame())
            if not best_trades.empty:
                print_section("BEST_C2_SELL_CANDIDATE_BY_HOUR", summarize_grouped(best_trades, ["jst_entry_hour"]))
                print_section("BEST_C2_SELL_CANDIDATE_BY_MONTH", summarize_grouped(best_trades, ["jst_entry_month"]))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "c2_sell_filter_candidate_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_c2_sell_filter_candidate_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "c2_sell_filter_candidate_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_c2_sell_filter_candidate_trades: {trades_path}")

    print("=" * 120)
    print("C2 SELL filter candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
