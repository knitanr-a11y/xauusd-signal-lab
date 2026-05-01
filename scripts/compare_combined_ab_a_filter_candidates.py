from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_combined_ab_a_filter_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_combined_backtest import (
    add_combined_signal_columns,
    attach_signal_sources_to_trades,
    attach_jst_trade_times,
    build_base_dataframe,
    build_paths,
    parse_float_range,
    parse_int_csv,
)
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset
from src.time_utils import DEFAULT_MT5_SERVER_TIMEZONE


@dataclass(frozen=True)
class CombinedCandidate:
    name: str
    description: str
    a_filter_func: Callable[[pd.DataFrame], tuple[pd.Series, pd.Series]]


def _true_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


def _side_hour_allowed_mask(
    df: pd.DataFrame,
    *,
    buy_hours: set[int] | None,
    sell_hours: set[int] | None,
) -> tuple[pd.Series, pd.Series]:
    hours = pd.to_numeric(df["jst_hour"], errors="coerce").astype("Int64")
    buy = pd.Series(True, index=df.index)
    sell = pd.Series(True, index=df.index)
    if buy_hours is not None:
        buy = hours.isin(buy_hours)
    if sell_hours is not None:
        sell = hours.isin(sell_hours)
    return buy.fillna(False).astype(bool), sell.fillna(False).astype(bool)


def _hidden_price_delta_atr_masks(df: pd.DataFrame, minimum: float) -> tuple[pd.Series, pd.Series]:
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    buy_value = pd.to_numeric(df["bullish_hidden_price_delta"], errors="coerce") / atr
    sell_value = pd.to_numeric(df["bearish_hidden_price_delta"], errors="coerce") / atr
    return (buy_value > minimum).fillna(False), (sell_value > minimum).fillna(False)


def _h1_ema_gap_side_signed_atr_masks(df: pd.DataFrame, maximum: float) -> tuple[pd.Series, pd.Series]:
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    buy_value = h1_gap / atr
    sell_value = (-h1_gap) / atr
    return (buy_value <= maximum).fillna(False), (sell_value <= maximum).fillna(False)


def build_candidates(args: argparse.Namespace) -> list[CombinedCandidate]:
    baseline_buy_hours = parse_int_csv(args.a_buy_jst_hours)
    baseline_sell_hours = parse_int_csv(args.a_sell_jst_hours)
    buy_13 = {13}
    sell_2_19 = {2, 19}
    hidden_min = args.hidden_price_delta_atr_min
    h1_max = args.h1_ema_gap_side_signed_atr_max

    def baseline(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        return _true_mask(df), _true_mask(df)

    def exclude_hidden_price_delta(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        return _hidden_price_delta_atr_masks(df, minimum=hidden_min)

    def strict_candidate_2(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        buy_hour_mask, sell_hour_mask = _side_hour_allowed_mask(df, buy_hours=buy_13, sell_hours=sell_2_19)
        buy_hidden_mask, sell_hidden_mask = _hidden_price_delta_atr_masks(df, minimum=hidden_min)
        buy_h1_mask, sell_h1_mask = _h1_ema_gap_side_signed_atr_masks(df, maximum=h1_max)
        return buy_hour_mask & buy_hidden_mask & buy_h1_mask, sell_hour_mask & sell_hidden_mask & sell_h1_mask

    def buy_13_sell_baseline(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        return _side_hour_allowed_mask(df, buy_hours=buy_13, sell_hours=baseline_sell_hours)

    def exclude_h1_overextension(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        return _h1_ema_gap_side_signed_atr_masks(df, maximum=h1_max)

    def exclude_both_numeric(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        buy_hidden_mask, sell_hidden_mask = _hidden_price_delta_atr_masks(df, minimum=hidden_min)
        buy_h1_mask, sell_h1_mask = _h1_ema_gap_side_signed_atr_masks(df, maximum=h1_max)
        return buy_hidden_mask & buy_h1_mask, sell_hidden_mask & sell_h1_mask

    return [
        CombinedCandidate(
            name="gold_ab_v2_baseline",
            description="Current gold_ab_v2: A baseline + B v2 filters.",
            a_filter_func=baseline,
        ),
        CombinedCandidate(
            name=f"a_exclude_hidden_price_delta_atr_le_{hidden_min:g}",
            description=f"A candidate 1: exclude A when side-aware hidden_price_delta_atr <= {hidden_min:g}; B unchanged.",
            a_filter_func=exclude_hidden_price_delta,
        ),
        CombinedCandidate(
            name="a_buy_13_sell_2_19_exclude_hidden_and_h1",
            description=(
                "A candidate 2: BUY 13 only, SELL 2/19 only, "
                f"exclude hidden_price_delta_atr <= {hidden_min:g}, "
                f"exclude h1_ema_gap_side_signed_atr > {h1_max:g}; B unchanged."
            ),
            a_filter_func=strict_candidate_2,
        ),
        CombinedCandidate(
            name="a_buy_13_only_sell_baseline",
            description="A side-hour test: BUY 13 only, SELL baseline hours; B unchanged.",
            a_filter_func=buy_13_sell_baseline,
        ),
        CombinedCandidate(
            name=f"a_exclude_h1_ema_gap_side_signed_atr_gt_{h1_max:g}",
            description=f"A numeric test: exclude A when side-aware h1_ema_gap_atr > {h1_max:g}; B unchanged.",
            a_filter_func=exclude_h1_overextension,
        ),
        CombinedCandidate(
            name="a_exclude_hidden_price_delta_and_h1_overextension",
            description="A numeric test: apply both numeric exclusions; B unchanged.",
            a_filter_func=exclude_both_numeric,
        ),
    ]


def apply_a_candidate_to_base_df(base_df: pd.DataFrame, candidate: CombinedCandidate) -> pd.DataFrame:
    out = base_df.copy()
    buy_keep, sell_keep = candidate.a_filter_func(out)
    out["hidden_bullish_divergence"] = out["hidden_bullish_divergence"].astype(bool) & buy_keep.fillna(False).astype(bool)
    out["hidden_bearish_divergence"] = out["hidden_bearish_divergence"].astype(bool) & sell_keep.fillna(False).astype(bool)
    out["a_candidate_name"] = candidate.name
    out["a_candidate_buy_keep"] = buy_keep.fillna(False).astype(bool)
    out["a_candidate_sell_keep"] = sell_keep.fillna(False).astype(bool)
    return out


def summarize_source_breakdown(trades: pd.DataFrame) -> dict[str, object]:
    row: dict[str, object] = {}
    for source in ["A", "B", "A+B"]:
        group = trades[trades.get("combined_signal_source", pd.Series(index=trades.index, dtype="object")).eq(source)] if not trades.empty else trades
        summary = summarize_trades(group)
        prefix = source.lower().replace("+", "_")
        row[f"{prefix}_trades"] = summary["trades"]
        row[f"{prefix}_win_rate"] = summary["win_rate"]
        row[f"{prefix}_total_r"] = summary["total_r"]
        row[f"{prefix}_profit_factor"] = summary["profit_factor"]
        row[f"{prefix}_max_drawdown_r"] = summary["max_drawdown_r"]
    return row


def summarize_side_breakdown(trades: pd.DataFrame) -> dict[str, object]:
    row: dict[str, object] = {}
    for side in ["BUY", "SELL"]:
        group = trades[trades["side"].eq(side)] if not trades.empty and "side" in trades.columns else trades.iloc[0:0]
        summary = summarize_trades(group)
        prefix = side.lower()
        row[f"{prefix}_trades"] = summary["trades"]
        row[f"{prefix}_win_rate"] = summary["win_rate"]
        row[f"{prefix}_total_r"] = summary["total_r"]
        row[f"{prefix}_profit_factor"] = summary["profit_factor"]
        row[f"{prefix}_max_drawdown_r"] = summary["max_drawdown_r"]
    return row


def run_candidate(
    *,
    args: argparse.Namespace,
    base_df: pd.DataFrame,
    candidate: CombinedCandidate,
    settings: BacktestSettings,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    a_candidate_df = apply_a_candidate_to_base_df(base_df, candidate)

    combined_df = add_combined_signal_columns(
        a_candidate_df,
        a_buy_hours=parse_int_csv(args.a_buy_jst_hours),
        a_sell_hours=parse_int_csv(args.a_sell_jst_hours),
        b_buy_hours=parse_int_csv(args.b_buy_jst_hours),
        b_sell_hours=parse_int_csv(args.b_sell_jst_hours),
        enabled_models={"A", "B"},
        b_exclude_risk_atr_range=parse_float_range(args.b_exclude_risk_atr_range),
        b_exclude_macd_hist_delta_abs_range=parse_float_range(args.b_exclude_macd_hist_delta_abs_range),
        sl_buffer_atr=args.sl_buffer_atr,
    )

    trades = run_simple_hidden_divergence_backtest(combined_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = attach_signal_sources_to_trades(trades, combined_df)
    if not trades.empty:
        trades["candidate"] = candidate.name

    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "a_buy_signals": int(combined_df["a_buy_signal_filtered"].sum()),
        "a_sell_signals": int(combined_df["a_sell_signal_filtered"].sum()),
        "b_buy_signals": int(combined_df["b_buy_signal_filtered"].sum()),
        "b_sell_signals": int(combined_df["b_sell_signal_filtered"].sum()),
        "combined_buy_signals": int(combined_df["combined_buy_signal"].sum()),
        "combined_sell_signals": int(combined_df["combined_sell_signal"].sum()),
        "conflicts_skipped": int(combined_df["combined_signal_conflict"].sum()),
    }
    row.update(summary)
    row.update(summarize_source_breakdown(trades))
    row.update(summarize_side_breakdown(trades))
    return combined_df, trades, row


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare combined A+B results when A filter candidates are applied.")
    parser.add_argument("--preset", type=str, default="gold_ab_v2", help="Preset to use. Default: gold_ab_v2")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--near-atr", type=float, default=None, help="ATR multiplier for EMA20 proximity. Default: from preset")
    parser.add_argument("--close-tolerance-atr", type=float, default=None, help="ATR multiplier for close tolerance. Default: from preset")
    parser.add_argument("--swing-left", type=int, default=None, help="Left bars for swing detection. Default: from preset")
    parser.add_argument("--swing-right", type=int, default=None, help="Right bars for swing detection. Default: from preset")
    parser.add_argument("--recent-pullback-bars", type=int, default=None, help="B signal recent pullback lookback bars. Default: from preset")
    parser.add_argument("--no-ema20-reclaim", action="store_true", help="B signal: do not require EMA20 reclaim/cross from prior bar.")
    parser.add_argument("--no-macd-signal-alignment", action="store_true", help="B signal: do not require MACD line vs signal alignment.")
    parser.add_argument("--no-histogram-acceleration", action="store_true", help="B signal: do not require histogram acceleration.")
    parser.add_argument("--rr", type=float, default=None, help="Override RR. Default: from preset")
    parser.add_argument("--sl-buffer-atr", type=float, default=None, help="Override SL buffer ATR. Default: from preset")
    parser.add_argument("--server-timezone", type=str, default=None, help="IANA timezone for MT5 server time. Default: from preset")
    parser.add_argument("--server-utc-offset", type=int, default=None, help="Fallback fixed UTC offset hours. Default: from preset")
    parser.add_argument("--use-fixed-offset", action="store_true", help="Use fixed UTC offset instead of DST-aware timezone conversion.")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None, help="Baseline A BUY signal JST hours. Default: from preset")
    parser.add_argument("--a-sell-jst-hours", type=str, default=None, help="Baseline A SELL signal JST hours. Default: from preset")
    parser.add_argument("--b-buy-jst-hours", type=str, default=None, help="B BUY signal JST hours. Default: from preset")
    parser.add_argument("--b-sell-jst-hours", type=str, default=None, help="B SELL signal JST hours. Default: from preset")
    parser.add_argument("--b-exclude-risk-atr-range", type=str, default=None, help="Exclude B signals with estimated risk/ATR inside range. Default: from preset")
    parser.add_argument("--b-exclude-macd-hist-delta-abs-range", type=str, default=None, help="Exclude B signals with abs MACD histogram delta inside range. Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true", help="If set, same-bar TP/SL is treated as win. Default is conservative loss.")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Optional maximum bars to hold a trade. Default: from preset")
    parser.add_argument("--hidden-price-delta-atr-min", type=float, default=0.271, help="A candidate threshold. Default: 0.271")
    parser.add_argument("--h1-ema-gap-side-signed-atr-max", type=float, default=3.267, help="A candidate threshold. Default: 3.267")
    parser.add_argument("--save", action="store_true", help="Save comparison CSVs to data/results.")
    args = parser.parse_args()

    preset = get_preset(args.preset)
    if args.symbols is None:
        args.symbols = preset.symbols
    if args.near_atr is None:
        args.near_atr = preset.near_atr
    if args.close_tolerance_atr is None:
        args.close_tolerance_atr = preset.close_tolerance_atr
    if args.swing_left is None:
        args.swing_left = preset.swing_left
    if args.swing_right is None:
        args.swing_right = preset.swing_right
    if args.recent_pullback_bars is None:
        args.recent_pullback_bars = preset.recent_pullback_bars
    if args.rr is None:
        args.rr = preset.rr
    if args.sl_buffer_atr is None:
        args.sl_buffer_atr = preset.sl_buffer_atr
    if args.server_timezone is None:
        args.server_timezone = preset.server_timezone or DEFAULT_MT5_SERVER_TIMEZONE
    if args.server_utc_offset is None:
        args.server_utc_offset = preset.server_utc_offset
    if not args.use_fixed_offset:
        args.use_fixed_offset = preset.use_fixed_offset
    if args.a_buy_jst_hours is None:
        args.a_buy_jst_hours = preset.a_buy_jst_hours
    if args.a_sell_jst_hours is None:
        args.a_sell_jst_hours = preset.a_sell_jst_hours
    if args.b_buy_jst_hours is None:
        args.b_buy_jst_hours = preset.b_buy_jst_hours
    if args.b_sell_jst_hours is None:
        args.b_sell_jst_hours = preset.b_sell_jst_hours
    if args.b_exclude_risk_atr_range is None:
        args.b_exclude_risk_atr_range = preset.b_exclude_risk_atr_range
    if args.b_exclude_macd_hist_delta_abs_range is None:
        args.b_exclude_macd_hist_delta_abs_range = preset.b_exclude_macd_hist_delta_abs_range
    if args.max_bars_in_trade is None:
        args.max_bars_in_trade = preset.max_bars_in_trade

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
    candidates = build_candidates(args)

    all_rows: list[dict[str, object]] = []
    all_trades: list[pd.DataFrame] = []

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset: {args.preset}")
        print(f"A baseline BUY JST hours: {args.a_buy_jst_hours}")
        print(f"A baseline SELL JST hours: {args.a_sell_jst_hours}")
        print(f"B BUY JST hours: {args.b_buy_jst_hours}")
        print(f"B SELL JST hours: {args.b_sell_jst_hours}")
        print(f"B exclude risk_atr_range: {args.b_exclude_risk_atr_range}")
        print(f"B exclude macd_hist_delta_abs_range: {args.b_exclude_macd_hist_delta_abs_range}")
        print(f"A hidden_price_delta_atr_min: {args.hidden_price_delta_atr_min}")
        print(f"A h1_ema_gap_side_signed_atr_max: {args.h1_ema_gap_side_signed_atr_max}")

        m15_path, h1_path = build_paths(args.data_dir, symbol)
        if not m15_path.exists():
            print(f"M15 file not found: {m15_path}")
            continue
        if not h1_path.exists():
            print(f"H1 file not found: {h1_path}")
            continue

        base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)

        symbol_rows: list[dict[str, object]] = []
        for candidate in candidates:
            _combined_df, trades, row = run_candidate(
                args=args,
                base_df=base_df,
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
            "trades",
            "wins",
            "losses",
            "win_rate",
            "average_r",
            "total_r",
            "profit_factor",
            "max_consecutive_losses",
            "max_drawdown_r",
            "a_buy_signals",
            "a_sell_signals",
            "b_buy_signals",
            "b_sell_signals",
            "combined_buy_signals",
            "combined_sell_signals",
            "conflicts_skipped",
            "a_trades",
            "a_win_rate",
            "a_total_r",
            "a_profit_factor",
            "b_trades",
            "b_win_rate",
            "b_total_r",
            "b_profit_factor",
            "a_b_trades",
            "a_b_total_r",
            "buy_trades",
            "buy_win_rate",
            "buy_total_r",
            "buy_profit_factor",
            "sell_trades",
            "sell_win_rate",
            "sell_total_r",
            "sell_profit_factor",
            "description",
        ]
        available_cols = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available_cols].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("COMBINED_A_B_WITH_A_FILTER_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "combined_ab_a_filter_candidate_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_combined_ab_a_filter_candidate_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "combined_ab_a_filter_candidate_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_combined_ab_a_filter_candidate_trades: {trades_path}")

    print("=" * 120)
    print("Combined A+B A-filter candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
