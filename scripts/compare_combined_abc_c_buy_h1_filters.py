from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_combined_abc_c_buy_h1_filters.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c_signal_trades import build_c_signal_df
from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped
from scripts.compare_combined_abc_c_buy_candidates import (
    apply_abc_candidate,
    attach_combined_sources_to_trades,
    build_ab_v4_combined_df,
    CombinedABCCandidate,
)
from scripts.run_combined_backtest import attach_jst_trade_times
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


@dataclass(frozen=True)
class CBuyH1Candidate:
    name: str
    description: str
    keep_func: Callable[[pd.DataFrame], pd.Series]


def _c_buy_base(df: pd.DataFrame) -> pd.Series:
    return df["c_buy_signal_filtered"].fillna(False).astype(bool)


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def _h1_gap_buy_atr(df: pd.DataFrame) -> pd.Series:
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    return h1_gap / atr


def build_candidates() -> list[CBuyH1Candidate]:
    # From the best combined C candidate:
    # broad positive hours, excluding 13, 16, 23 by signal hour.
    base_hours = {1, 4, 5, 11, 12, 15, 18, 21, 22}
    no_4_19_hours = {1, 5, 11, 12, 15, 18, 21, 22}
    tighter_hours = {1, 5, 11, 12, 18, 21, 22}

    def current_candidate(df: pd.DataFrame) -> pd.Series:
        return _c_buy_base(df) & _jst_hour(df).isin(base_hours)

    def h1_le_3623(df: pd.DataFrame) -> pd.Series:
        return current_candidate(df) & _h1_gap_buy_atr(df).le(3.623)

    def h1_le_3500(df: pd.DataFrame) -> pd.Series:
        return current_candidate(df) & _h1_gap_buy_atr(df).le(3.500)

    def h1_le_3112(df: pd.DataFrame) -> pd.Series:
        return current_candidate(df) & _h1_gap_buy_atr(df).le(3.112)

    def h1_1049_to_3623(df: pd.DataFrame) -> pd.Series:
        h1 = _h1_gap_buy_atr(df)
        return current_candidate(df) & h1.gt(1.049) & h1.le(3.623)

    def remove_hour_4(df: pd.DataFrame) -> pd.Series:
        return _c_buy_base(df) & _jst_hour(df).isin(no_4_19_hours)

    def remove_hour_4_h1_le_3623(df: pd.DataFrame) -> pd.Series:
        return remove_hour_4(df) & _h1_gap_buy_atr(df).le(3.623)

    def tighter_hours_h1_le_3623(df: pd.DataFrame) -> pd.Series:
        return _c_buy_base(df) & _jst_hour(df).isin(tighter_hours) & _h1_gap_buy_atr(df).le(3.623)

    return [
        CBuyH1Candidate(
            name="gold_ab_v4_baseline",
            description="AB v4 baseline. C disabled.",
            keep_func=lambda df: pd.Series(False, index=df.index),
        ),
        CBuyH1Candidate(
            name="c_buy_current_no_13_16_23",
            description="AB v4 + current C BUY broad hours excluding signal hours 13,16,23.",
            keep_func=current_candidate,
        ),
        CBuyH1Candidate(
            name="c_buy_current_h1_gap_le_3_623",
            description="Current C BUY candidate plus H1 EMA gap <= 3.623 ATR.",
            keep_func=h1_le_3623,
        ),
        CBuyH1Candidate(
            name="c_buy_current_h1_gap_le_3_500",
            description="Current C BUY candidate plus H1 EMA gap <= 3.500 ATR.",
            keep_func=h1_le_3500,
        ),
        CBuyH1Candidate(
            name="c_buy_current_h1_gap_le_3_112",
            description="Current C BUY candidate plus H1 EMA gap <= 3.112 ATR.",
            keep_func=h1_le_3112,
        ),
        CBuyH1Candidate(
            name="c_buy_current_h1_gap_1_049_to_3_623",
            description="Current C BUY candidate with H1 EMA gap > 1.049 and <= 3.623 ATR.",
            keep_func=h1_1049_to_3623,
        ),
        CBuyH1Candidate(
            name="c_buy_remove_hour_4",
            description="Current C BUY candidate excluding signal hour 4.",
            keep_func=remove_hour_4,
        ),
        CBuyH1Candidate(
            name="c_buy_remove_hour_4_h1_gap_le_3_623",
            description="Current C BUY candidate excluding signal hour 4 and H1 EMA gap <= 3.623 ATR.",
            keep_func=remove_hour_4_h1_le_3623,
        ),
        CBuyH1Candidate(
            name="c_buy_tighter_hours_h1_gap_le_3_623",
            description="C BUY signal hours 1,5,11,12,18,21,22 plus H1 EMA gap <= 3.623 ATR.",
            keep_func=tighter_hours_h1_le_3623,
        ),
    ]


def make_combined_candidate(candidate: CBuyH1Candidate) -> CombinedABCCandidate:
    return CombinedABCCandidate(
        name=candidate.name,
        description=candidate.description,
        c_keep_func=candidate.keep_func,
    )


def summarize_source_breakdown(trades: pd.DataFrame) -> dict[str, object]:
    row: dict[str, object] = {}
    for source in ["A", "B", "C", "MIXED"]:
        group = trades[trades["combined_signal_source"].eq(source)] if not trades.empty and "combined_signal_source" in trades.columns else trades.iloc[0:0]
        summary = summarize_trades(group)
        prefix = source.lower()
        row[f"{prefix}_trades"] = summary["trades"]
        row[f"{prefix}_win_rate"] = summary["win_rate"]
        row[f"{prefix}_total_r"] = summary["total_r"]
        row[f"{prefix}_profit_factor"] = summary["profit_factor"]
        row[f"{prefix}_max_drawdown_r"] = summary["max_drawdown_r"]
    return row


def run_candidate(
    *,
    args: argparse.Namespace,
    ab_df: pd.DataFrame,
    c_df: pd.DataFrame,
    candidate: CBuyH1Candidate,
    settings: BacktestSettings,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    combined_candidate = make_combined_candidate(candidate)
    candidate_df = apply_abc_candidate(ab_df, c_df, combined_candidate)
    trades = run_simple_hidden_divergence_backtest(candidate_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = attach_combined_sources_to_trades(trades, candidate_df)
    if not trades.empty:
        trades["candidate"] = candidate.name
        trades["jst_entry_hour"] = trades["jst_entry_time"].dt.hour
        trades["jst_entry_month"] = trades["jst_entry_time"].dt.to_period("M").astype(str)

    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "c_buy_signals": int(candidate_df["c_buy_signal_candidate"].sum()),
        "combined_buy_signals": int(candidate_df["combined_buy_signal"].sum()),
        "combined_sell_signals": int(candidate_df["combined_sell_signal"].sum()),
        "conflicts_skipped": int(candidate_df["combined_signal_conflict"].sum()),
    }
    row.update(summary)
    row.update(summarize_source_breakdown(trades))
    return candidate_df, trades, row


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare AB v4 + C BUY H1-gap filter candidates.")
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
    parser.add_argument("--b-buy-exclude-risk-atr-range", type=str, default=None, help="Default: from preset")
    parser.add_argument("--b-buy-exclude-risk-atr-macd-hist-delta-abs-combo", type=str, default=None, help="Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Default: from preset")

    parser.add_argument("--c-breakout-lookback-bars", type=int, default=12, help="Previous N bars for breakout range. Default: 12")
    parser.add_argument("--c-min-breakout-atr", type=float, default=0.0, help="Minimum breakout distance in ATR. Default: 0.0")
    parser.add_argument("--c-max-breakout-atr", type=float, default=None, help="Maximum breakout distance in ATR. Default: None")
    parser.add_argument("--c-buy-jst-hours", type=str, default=None, help="Base C BUY JST hours. Default: all")
    parser.add_argument("--c-sell-jst-hours", type=str, default=None, help="Base C SELL JST hours. Default: all")
    parser.add_argument("--c-no-h1-trend", action="store_true")
    parser.add_argument("--c-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c-allow-ab-overlap", action="store_true")
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
        print("target: AB v4 + C BUY H1-gap candidates")

        ab_df = build_ab_v4_combined_df(args, symbol=symbol)
        c_df = build_c_signal_df(args, symbol=symbol)
        symbol_rows: list[dict[str, object]] = []
        symbol_trade_map: dict[str, pd.DataFrame] = {}

        for candidate in candidates:
            _candidate_df, trades, row = run_candidate(
                args=args,
                ab_df=ab_df,
                c_df=c_df,
                candidate=candidate,
                settings=settings,
            )
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
            "trades",
            "wins",
            "losses",
            "win_rate",
            "average_r",
            "total_r",
            "profit_factor",
            "max_consecutive_losses",
            "max_drawdown_r",
            "a_trades",
            "a_total_r",
            "a_profit_factor",
            "b_trades",
            "b_total_r",
            "b_profit_factor",
            "c_trades",
            "c_win_rate",
            "c_total_r",
            "c_profit_factor",
            "c_max_drawdown_r",
            "c_buy_signals",
            "description",
        ]
        available = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("AB_V4_PLUS_C_BUY_H1_FILTER_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

        if not summary_df.empty:
            best_name = str(summary_df.iloc[0]["candidate"])
            best_trades = symbol_trade_map.get(best_name, pd.DataFrame())
            if not best_trades.empty:
                print_table("BEST_CANDIDATE_BY_SOURCE", summarize_grouped(best_trades, ["combined_signal_source"]))
                print_table("BEST_CANDIDATE_BY_MONTH", summarize_grouped(best_trades, ["jst_entry_month"]))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "combined_abc_c_buy_h1_filter_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_combined_abc_c_buy_h1_filter_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "combined_abc_c_buy_h1_filter_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_combined_abc_c_buy_h1_filter_trades: {trades_path}")

    print("=" * 120)
    print("AB v4 + C BUY H1 filter comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
