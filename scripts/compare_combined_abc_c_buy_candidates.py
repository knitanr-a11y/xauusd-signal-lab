from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_combined_abc_c_buy_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c_signal_trades import build_c_signal_df, enrich_c_trades
from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped
from scripts.run_combined_backtest import (
    add_combined_signal_columns,
    attach_jst_trade_times,
    build_base_dataframe,
    build_paths,
    parse_float_range,
    parse_int_csv,
)
from scripts.run_combined_backtest_with_a_filters import apply_a_filters, apply_b_buy_extra_filters
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


@dataclass(frozen=True)
class CombinedABCCandidate:
    name: str
    description: str
    c_keep_func: Callable[[pd.DataFrame], pd.Series] | None


def _false_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(False, index=df.index)


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def _buy_breakout_atr(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c_buy_breakout_distance_atr"], errors="coerce")


def _h1_gap_buy_atr(df: pd.DataFrame) -> pd.Series:
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    return h1_gap / atr


def _c_buy_base(df: pd.DataFrame) -> pd.Series:
    return df["c_buy_signal_filtered"].fillna(False).astype(bool)


def build_candidates() -> list[CombinedABCCandidate]:
    broad_good_hours = {1, 4, 5, 11, 12, 13, 15, 16, 18, 21, 22, 23}

    def no_c(df: pd.DataFrame) -> pd.Series:
        return _false_mask(df)

    def c_buy_broad_good_hours(df: pd.DataFrame) -> pd.Series:
        return _c_buy_base(df) & _jst_hour(df).isin(broad_good_hours)

    def c_buy_h1_gap_filtered(df: pd.DataFrame) -> pd.Series:
        h1_gap = _h1_gap_buy_atr(df)
        return _c_buy_base(df) & _buy_breakout_atr(df).le(0.411) & h1_gap.gt(1.721) & h1_gap.le(3.112)

    def c_buy_broad_hours_no_13(df: pd.DataFrame) -> pd.Series:
        # In the C BUY standalone comparison, 13h was only slightly positive.
        hours = broad_good_hours - {13}
        return _c_buy_base(df) & _jst_hour(df).isin(hours)

    def c_buy_broad_hours_no_13_16_23(df: pd.DataFrame) -> pd.Series:
        # 16h and 23h were weaker than 1/5/11/15/18/21/22 in the best candidate hour breakdown.
        hours = broad_good_hours - {13, 16, 23}
        return _c_buy_base(df) & _jst_hour(df).isin(hours)

    return [
        CombinedABCCandidate(
            name="gold_ab_v4_baseline",
            description="Frozen AB baseline. C disabled.",
            c_keep_func=no_c,
        ),
        CombinedABCCandidate(
            name="gold_ab_v4_plus_c_buy_broad_good_hours",
            description="AB v4 + C BUY at broad positive hours from standalone C BUY diagnostics.",
            c_keep_func=c_buy_broad_good_hours,
        ),
        CombinedABCCandidate(
            name="gold_ab_v4_plus_c_buy_h1_gap_filtered",
            description="AB v4 + C BUY with breakout <= 0.411 ATR and H1 EMA gap 1.721-3.112 ATR.",
            c_keep_func=c_buy_h1_gap_filtered,
        ),
        CombinedABCCandidate(
            name="gold_ab_v4_plus_c_buy_broad_hours_no_13",
            description="AB v4 + C BUY broad positive hours excluding JST 13.",
            c_keep_func=c_buy_broad_hours_no_13,
        ),
        CombinedABCCandidate(
            name="gold_ab_v4_plus_c_buy_broad_hours_no_13_16_23",
            description="AB v4 + C BUY broad positive hours excluding JST 13,16,23.",
            c_keep_func=c_buy_broad_hours_no_13_16_23,
        ),
    ]


def attach_combined_sources_to_trades(trades: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    cols = [
        "combined_signal_source",
        "combined_signal_side",
        "a_buy_signal_filtered",
        "a_sell_signal_filtered",
        "b_buy_signal_filtered",
        "b_sell_signal_filtered",
        "c_buy_signal_candidate",
    ]
    available = [col for col in cols if col in df.columns]
    features = df[available].copy()
    features["signal_index"] = df.index
    return trades.merge(features, on="signal_index", how="left")


def build_ab_v4_combined_df(args: argparse.Namespace, symbol: str) -> pd.DataFrame:
    m15_path, h1_path = build_paths(args.data_dir, symbol)
    if not m15_path.exists():
        raise FileNotFoundError(f"M15 file not found: {m15_path}")
    if not h1_path.exists():
        raise FileNotFoundError(f"H1 file not found: {h1_path}")

    base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)
    filtered_base_df = apply_a_filters(base_df, args=args)
    combined_df = add_combined_signal_columns(
        filtered_base_df,
        a_buy_hours=parse_int_csv(args.a_buy_jst_hours),
        a_sell_hours=parse_int_csv(args.a_sell_jst_hours),
        b_buy_hours=parse_int_csv(args.b_buy_jst_hours),
        b_sell_hours=parse_int_csv(args.b_sell_jst_hours),
        enabled_models={"A", "B"},
        b_exclude_risk_atr_range=parse_float_range(args.b_exclude_risk_atr_range),
        b_exclude_macd_hist_delta_abs_range=parse_float_range(args.b_exclude_macd_hist_delta_abs_range),
        sl_buffer_atr=args.sl_buffer_atr,
    )
    combined_df = apply_b_buy_extra_filters(combined_df, args=args)
    return combined_df


def apply_abc_candidate(ab_df: pd.DataFrame, c_df: pd.DataFrame, candidate: CombinedABCCandidate) -> pd.DataFrame:
    out = ab_df.copy()
    c_keep = candidate.c_keep_func(c_df).fillna(False).astype(bool) if candidate.c_keep_func is not None else _false_mask(c_df)

    out["c_buy_signal_candidate"] = c_keep
    out["c_sell_signal_candidate"] = False
    out["abc_candidate_name"] = candidate.name

    a_buy = out["a_buy_signal_filtered"].fillna(False).astype(bool)
    a_sell = out["a_sell_signal_filtered"].fillna(False).astype(bool)
    b_buy = out["b_buy_signal_filtered"].fillna(False).astype(bool)
    b_sell = out["b_sell_signal_filtered"].fillna(False).astype(bool)
    c_buy = out["c_buy_signal_candidate"].fillna(False).astype(bool)
    c_sell = out["c_sell_signal_candidate"].fillna(False).astype(bool)

    combined_buy = a_buy | b_buy | c_buy
    combined_sell = a_sell | b_sell | c_sell
    conflict = combined_buy & combined_sell

    out["combined_signal_conflict"] = conflict
    out["combined_buy_signal"] = combined_buy & ~conflict
    out["combined_sell_signal"] = combined_sell & ~conflict

    source = pd.Series("NONE", index=out.index, dtype="object")
    buy_sources = a_buy.astype(int) + b_buy.astype(int) + c_buy.astype(int)
    sell_sources = a_sell.astype(int) + b_sell.astype(int) + c_sell.astype(int)

    source.loc[out["combined_buy_signal"] & a_buy & ~b_buy & ~c_buy] = "A"
    source.loc[out["combined_buy_signal"] & b_buy & ~a_buy & ~c_buy] = "B"
    source.loc[out["combined_buy_signal"] & c_buy & ~a_buy & ~b_buy] = "C"
    source.loc[out["combined_buy_signal"] & buy_sources.gt(1)] = "MIXED"

    source.loc[out["combined_sell_signal"] & a_sell & ~b_sell & ~c_sell] = "A"
    source.loc[out["combined_sell_signal"] & b_sell & ~a_sell & ~c_sell] = "B"
    source.loc[out["combined_sell_signal"] & c_sell & ~a_sell & ~b_sell] = "C"
    source.loc[out["combined_sell_signal"] & sell_sources.gt(1)] = "MIXED"
    out["combined_signal_source"] = source

    out["combined_signal_side"] = "NONE"
    out.loc[out["combined_buy_signal"], "combined_signal_side"] = "BUY"
    out.loc[out["combined_sell_signal"], "combined_signal_side"] = "SELL"

    # Existing backtest engine consumes hidden divergence columns.
    out["hidden_bullish_divergence"] = out["combined_buy_signal"]
    out["hidden_bearish_divergence"] = out["combined_sell_signal"]
    return out


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
    return row


def run_candidate(
    *,
    args: argparse.Namespace,
    ab_df: pd.DataFrame,
    c_df: pd.DataFrame,
    candidate: CombinedABCCandidate,
    settings: BacktestSettings,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidate_df = apply_abc_candidate(ab_df, c_df, candidate)
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
        "a_buy_signals": int(candidate_df["a_buy_signal_filtered"].sum()),
        "a_sell_signals": int(candidate_df["a_sell_signal_filtered"].sum()),
        "b_buy_signals": int(candidate_df["b_buy_signal_filtered"].sum()),
        "b_sell_signals": int(candidate_df["b_sell_signal_filtered"].sum()),
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
    parser = argparse.ArgumentParser(description="Compare combined AB v4 + C BUY candidate backtests.")
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
    parser.add_argument("--c-sell-jst-hours", type=str, default=None, help="Base C SELL JST hours. Default: all, but not used in C BUY comparison")
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
        print("target: combined AB v4 + C BUY candidates")

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
            "a_win_rate",
            "a_total_r",
            "a_profit_factor",
            "b_trades",
            "b_win_rate",
            "b_total_r",
            "b_profit_factor",
            "c_trades",
            "c_win_rate",
            "c_total_r",
            "c_profit_factor",
            "mixed_trades",
            "mixed_total_r",
            "c_buy_signals",
            "combined_buy_signals",
            "combined_sell_signals",
            "description",
        ]
        available = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("COMBINED_AB_V4_PLUS_C_BUY_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

        if not summary_df.empty:
            best_name = str(summary_df.iloc[0]["candidate"])
            best_trades = symbol_trade_map.get(best_name, pd.DataFrame())
            if not best_trades.empty:
                print_table("BEST_COMBINED_CANDIDATE_BY_SOURCE", summarize_grouped(best_trades, ["combined_signal_source"]))
                print_table("BEST_COMBINED_CANDIDATE_BY_MONTH", summarize_grouped(best_trades, ["jst_entry_month"]))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "combined_abc_c_buy_candidate_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_combined_abc_c_buy_candidate_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "combined_abc_c_buy_candidate_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_combined_abc_c_buy_candidate_trades: {trades_path}")

    print("=" * 120)
    print("Combined AB v4 + C BUY candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
