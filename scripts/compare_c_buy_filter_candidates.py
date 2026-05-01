from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_c_buy_filter_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c_signal_trades import (
    build_c_signal_df,
    enrich_c_trades,
    print_section,
)
from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped
from scripts.run_combined_backtest import attach_jst_trade_times
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


@dataclass(frozen=True)
class CBuyFilterCandidate:
    name: str
    description: str
    keep_func: Callable[[pd.DataFrame], pd.Series]


def _true_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


def _c_buy_base_mask(df: pd.DataFrame) -> pd.Series:
    return df["c_buy_signal_filtered"].fillna(False).astype(bool)


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def _buy_breakout_atr(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c_buy_breakout_distance_atr"], errors="coerce")


def _risk_atr(df: pd.DataFrame) -> pd.Series:
    # This is the same risk approximation used by the backtest for BUY:
    # next-open entry is unknown at signal time, but close-to-swing risk is close enough
    # for filtering candidates before a full backtest rerun.
    entry_proxy = pd.to_numeric(df["close"], errors="coerce")
    swing_low = pd.to_numeric(df["last_confirmed_swing_low_price"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    buffer = atr * 0.05
    return (entry_proxy - (swing_low - buffer)) / atr


def _range_width_atr(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c_previous_range_width_atr"], errors="coerce")


def _h1_gap_side_atr(df: pd.DataFrame) -> pd.Series:
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    return h1_gap / atr


def _macd_delta(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c_macd_hist_delta"], errors="coerce")


def build_candidates() -> list[CBuyFilterCandidate]:
    good_hours = {4, 13, 21, 23}
    broad_good_hours = {1, 4, 5, 11, 12, 13, 15, 16, 18, 21, 22, 23}

    def buy_only(df: pd.DataFrame) -> pd.Series:
        return _true_mask(df)

    def good_hours_only(df: pd.DataFrame) -> pd.Series:
        return _jst_hour(df).isin(good_hours)

    def broad_good_hours_only(df: pd.DataFrame) -> pd.Series:
        return _jst_hour(df).isin(broad_good_hours)

    def breakout_le_0411(df: pd.DataFrame) -> pd.Series:
        return _buy_breakout_atr(df).le(0.411)

    def breakout_le_0156(df: pd.DataFrame) -> pd.Series:
        return _buy_breakout_atr(df).le(0.156)

    def risk_le_444(df: pd.DataFrame) -> pd.Series:
        return _risk_atr(df).le(4.44)

    def risk_le_3452(df: pd.DataFrame) -> pd.Series:
        return _risk_atr(df).le(3.452)

    def breakout_le_0411_and_risk_le_444(df: pd.DataFrame) -> pd.Series:
        return breakout_le_0411(df) & risk_le_444(df)

    def breakout_le_0411_and_risk_le_3452(df: pd.DataFrame) -> pd.Series:
        return breakout_le_0411(df) & risk_le_3452(df)

    def good_hours_breakout_le_0411(df: pd.DataFrame) -> pd.Series:
        return good_hours_only(df) & breakout_le_0411(df)

    def good_hours_breakout_le_0411_risk_le_444(df: pd.DataFrame) -> pd.Series:
        return good_hours_only(df) & breakout_le_0411(df) & risk_le_444(df)

    def broad_hours_breakout_le_0411_risk_le_444(df: pd.DataFrame) -> pd.Series:
        return broad_good_hours_only(df) & breakout_le_0411(df) & risk_le_444(df)

    def good_hours_breakout_le_0411_risk_le_3452(df: pd.DataFrame) -> pd.Series:
        return good_hours_only(df) & breakout_le_0411(df) & risk_le_3452(df)

    def breakout_le_0411_mid_h1_gap(df: pd.DataFrame) -> pd.Series:
        h1 = _h1_gap_side_atr(df)
        return breakout_le_0411(df) & h1.gt(1.721) & h1.le(3.112)

    def breakout_le_0411_macd_delta_mid_or_high(df: pd.DataFrame) -> pd.Series:
        macd = _macd_delta(df)
        return breakout_le_0411(df) & macd.gt(0.235)

    def compressed_range_breakout_le_0411(df: pd.DataFrame) -> pd.Series:
        return breakout_le_0411(df) & _range_width_atr(df).le(2.414)

    return [
        CBuyFilterCandidate(
            name="c_buy_only_baseline",
            description="C BUY only. C SELL disabled.",
            keep_func=buy_only,
        ),
        CBuyFilterCandidate(
            name="c_buy_good_hours_4_13_21_23",
            description="C BUY only at JST hours 4,13,21,23.",
            keep_func=good_hours_only,
        ),
        CBuyFilterCandidate(
            name="c_buy_broad_good_hours",
            description="C BUY only at broadly positive JST hours from first diagnostics.",
            keep_func=broad_good_hours_only,
        ),
        CBuyFilterCandidate(
            name="c_buy_breakout_distance_atr_le_0_411",
            description="C BUY only when breakout_distance_atr <= 0.411.",
            keep_func=breakout_le_0411,
        ),
        CBuyFilterCandidate(
            name="c_buy_breakout_distance_atr_le_0_156",
            description="C BUY only when breakout_distance_atr <= 0.156.",
            keep_func=breakout_le_0156,
        ),
        CBuyFilterCandidate(
            name="c_buy_risk_atr_le_4_44",
            description="C BUY only when estimated risk_atr_ratio <= 4.44.",
            keep_func=risk_le_444,
        ),
        CBuyFilterCandidate(
            name="c_buy_risk_atr_le_3_452",
            description="C BUY only when estimated risk_atr_ratio <= 3.452.",
            keep_func=risk_le_3452,
        ),
        CBuyFilterCandidate(
            name="c_buy_breakout_le_0_411_and_risk_le_4_44",
            description="C BUY only when breakout_distance_atr <= 0.411 and risk_atr_ratio <= 4.44.",
            keep_func=breakout_le_0411_and_risk_le_444,
        ),
        CBuyFilterCandidate(
            name="c_buy_breakout_le_0_411_and_risk_le_3_452",
            description="C BUY only when breakout_distance_atr <= 0.411 and risk_atr_ratio <= 3.452.",
            keep_func=breakout_le_0411_and_risk_le_3452,
        ),
        CBuyFilterCandidate(
            name="c_buy_good_hours_breakout_le_0_411",
            description="C BUY hours 4,13,21,23 and breakout_distance_atr <= 0.411.",
            keep_func=good_hours_breakout_le_0411,
        ),
        CBuyFilterCandidate(
            name="c_buy_good_hours_breakout_le_0_411_risk_le_4_44",
            description="C BUY hours 4,13,21,23, breakout_distance_atr <= 0.411, risk_atr_ratio <= 4.44.",
            keep_func=good_hours_breakout_le_0411_risk_le_444,
        ),
        CBuyFilterCandidate(
            name="c_buy_good_hours_breakout_le_0_411_risk_le_3_452",
            description="C BUY hours 4,13,21,23, breakout_distance_atr <= 0.411, risk_atr_ratio <= 3.452.",
            keep_func=good_hours_breakout_le_0411_risk_le_3452,
        ),
        CBuyFilterCandidate(
            name="c_buy_broad_hours_breakout_le_0_411_risk_le_4_44",
            description="C BUY broad positive hours, breakout_distance_atr <= 0.411, risk_atr_ratio <= 4.44.",
            keep_func=broad_hours_breakout_le_0411_risk_le_444,
        ),
        CBuyFilterCandidate(
            name="c_buy_breakout_le_0_411_h1_gap_1_721_to_3_112",
            description="C BUY breakout_distance_atr <= 0.411 and H1 EMA gap in the best diagnostic quartile.",
            keep_func=breakout_le_0411_mid_h1_gap,
        ),
        CBuyFilterCandidate(
            name="c_buy_breakout_le_0_411_macd_delta_gt_0_235",
            description="C BUY breakout_distance_atr <= 0.411 and MACD histogram delta > 0.235.",
            keep_func=breakout_le_0411_macd_delta_mid_or_high,
        ),
        CBuyFilterCandidate(
            name="c_buy_compressed_range_breakout_le_0_411",
            description="C BUY breakout_distance_atr <= 0.411 and previous range width <= 2.414 ATR.",
            keep_func=compressed_range_breakout_le_0411,
        ),
    ]


def apply_candidate(signal_df: pd.DataFrame, candidate: CBuyFilterCandidate) -> pd.DataFrame:
    out = signal_df.copy()
    base_buy = _c_buy_base_mask(out)
    keep = candidate.keep_func(out).fillna(False).astype(bool)
    out["c_buy_candidate_name"] = candidate.name
    out["c_buy_candidate_keep"] = keep & base_buy
    out["c_buy_signal_candidate"] = base_buy & keep
    out["c_sell_signal_candidate"] = False
    out["hidden_bullish_divergence"] = out["c_buy_signal_candidate"]
    out["hidden_bearish_divergence"] = False
    return out


def run_candidate(
    *,
    args: argparse.Namespace,
    base_signal_df: pd.DataFrame,
    candidate: CBuyFilterCandidate,
    settings: BacktestSettings,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidate_df = apply_candidate(base_signal_df, candidate)
    trades = run_simple_hidden_divergence_backtest(candidate_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = enrich_c_trades(trades, candidate_df, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)
    if not trades.empty:
        trades["candidate"] = candidate.name

    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "c_buy_candidate_signals": int(candidate_df["c_buy_signal_candidate"].sum()),
    }
    row.update(summary)

    # extra diagnostics for the executed trades
    if trades.empty:
        row.update(
            {
                "early_losses": 0,
                "long_hold_losses": 0,
                "avg_risk_atr_ratio": None,
                "avg_breakout_distance_atr": None,
                "avg_range_width_atr": None,
            }
        )
    else:
        row.update(
            {
                "early_losses": int(trades["early_loss"].sum()) if "early_loss" in trades.columns else 0,
                "long_hold_losses": int(trades["long_hold_loss"].sum()) if "long_hold_loss" in trades.columns else 0,
                "avg_risk_atr_ratio": pd.to_numeric(trades["risk_atr_ratio"], errors="coerce").mean() if "risk_atr_ratio" in trades.columns else None,
                "avg_breakout_distance_atr": pd.to_numeric(trades["breakout_distance_atr"], errors="coerce").mean() if "breakout_distance_atr" in trades.columns else None,
                "avg_range_width_atr": pd.to_numeric(trades["signal_c_previous_range_width_atr"], errors="coerce").mean() if "signal_c_previous_range_width_atr" in trades.columns else None,
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
    parser = argparse.ArgumentParser(description="Compare C BUY filter candidates for breakout-continuation C v1.")
    parser.add_argument("--preset", type=str, default="gold_ab_v4", help="Preset context. Default: gold_ab_v4")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--models", type=str, default=None, help="Default: from preset")
    parser.add_argument("--near-atr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--close-tolerance-atr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--swing-left", type=int, default=None, help="Default: from preset")
    parser.add_argument("--swing-right", type=int, default=None, help="Default: from preset")
    parser.add_argument("--recent-pullback-bars", type=int, default=None, help="Default: from preset")
    parser.add_argument("--no-ema20-reclaim", action="store_true")
    parser.add_argument("--no-macd-signal-alignment", action="store_true")
    parser.add_argument("--no-histogram-acceleration", action="store_true")
    parser.add_argument("--rr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--sl-buffer-atr", type=float, default=None, help="Default: from preset")
    parser.add_argument("--server-timezone", type=str, default=None, help="Default: from preset")
    parser.add_argument("--server-utc-offset", type=int, default=None, help="Default: from preset")
    parser.add_argument("--use-fixed-offset", action="store_true")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--a-sell-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--a-exclude-hidden-price-delta-atr-lte", type=float, default=None, help="Default: from preset")
    parser.add_argument("--b-buy-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-sell-jst-hours", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None, help="Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Default: from preset")

    parser.add_argument("--c-breakout-lookback-bars", type=int, default=12, help="Previous N bars for breakout range. Default: 12")
    parser.add_argument("--c-min-breakout-atr", type=float, default=0.0, help="Minimum breakout distance in ATR. Default: 0.0")
    parser.add_argument("--c-max-breakout-atr", type=float, default=None, help="Maximum breakout distance in ATR. Default: None")
    parser.add_argument("--c-buy-jst-hours", type=str, default=None, help="Base C BUY JST hours. Default: all")
    parser.add_argument("--c-sell-jst-hours", type=str, default=None, help="Base C SELL JST hours. Default: all, but disabled in candidate comparison")
    parser.add_argument("--c-no-h1-trend", action="store_true")
    parser.add_argument("--c-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c-allow-ab-overlap", action="store_true")
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Default: 2")
    parser.add_argument("--long-hold-bars", type=int, default=20, help="Default: 20")
    parser.add_argument("--save", action="store_true", help="Save comparison CSVs to data/results.")
    args = apply_preset_defaults(parser.parse_args())

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = [item.strip().lower() for item in args.symbols.split(",") if item.strip()]
    if not symbols:
        print("No symbols provided.")
        return 1

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    candidates = build_candidates()

    all_rows: list[dict[str, object]] = []
    all_trades: list[pd.DataFrame] = []

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset_context: {args.preset}")
        print("target: C BUY candidate comparison; C SELL disabled")
        print(f"c_breakout_lookback_bars: {args.c_breakout_lookback_bars}")
        print(f"base c_buy_jst_hours: {args.c_buy_jst_hours or 'ALL'}")

        base_signal_df = build_c_signal_df(args, symbol=symbol)
        symbol_rows: list[dict[str, object]] = []

        for candidate in candidates:
            _candidate_df, trades, row = run_candidate(
                args=args,
                base_signal_df=base_signal_df,
                candidate=candidate,
                settings=settings,
            )
            row["symbol"] = symbol
            symbol_rows.append(row)
            all_rows.append(row)
            if not trades.empty:
                trades = trades.copy()
                trades["symbol"] = symbol
                all_trades.append(trades)

        summary_df = pd.DataFrame(symbol_rows)
        ordered_cols = [
            "symbol",
            "candidate",
            "c_buy_candidate_signals",
            "trades",
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
            "description",
        ]
        available = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("C_BUY_FILTER_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

        # Detail for the best candidate by total R.
        if not summary_df.empty:
            best_name = str(summary_df.iloc[0]["candidate"])
            best_trades = next((df for df in all_trades if not df.empty and df["candidate"].iloc[0] == best_name), pd.DataFrame())
            if not best_trades.empty:
                print_section("BEST_C_BUY_CANDIDATE_BY_HOUR", summarize_grouped(best_trades, ["jst_entry_hour"]))
                print_section("BEST_C_BUY_CANDIDATE_BY_MONTH", summarize_grouped(best_trades, ["jst_entry_month"]))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "c_buy_filter_candidate_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_c_buy_filter_candidate_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "c_buy_filter_candidate_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_c_buy_filter_candidate_trades: {trades_path}")

    print("=" * 120)
    print("C BUY filter candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
