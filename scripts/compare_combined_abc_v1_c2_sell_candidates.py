from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_combined_abc_v1_c2_sell_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c2_signal_trades import build_c2_signal_df
from scripts.analyze_combined_failure_modes import apply_preset_defaults, summarize_grouped
from scripts.run_combined_backtest import attach_jst_trade_times
from scripts.run_combined_abc_backtest import run_symbol as run_gold_abc_v1_symbol
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


@dataclass(frozen=True)
class CombinedABCC2Candidate:
    name: str
    description: str
    c2_keep_func: Callable[[pd.DataFrame], pd.Series]


def _false_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(False, index=df.index)


def _c2_sell_base(df: pd.DataFrame) -> pd.Series:
    return df["c2_sell_signal_filtered"].fillna(False).astype(bool)


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def _range_width_atr(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c2_previous_range_width_atr"], errors="coerce")


def _h1_gap_side_atr(df: pd.DataFrame) -> pd.Series:
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    return -h1_gap / atr


def _macd_delta(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["c2_macd_hist_delta"], errors="coerce")


def build_candidates() -> list[CombinedABCC2Candidate]:
    def no_c2(df: pd.DataFrame) -> pd.Series:
        return _false_mask(df)

    def range_2175_2367(df: pd.DataFrame) -> pd.Series:
        width = _range_width_atr(df)
        return _c2_sell_base(df) & width.gt(2.175) & width.le(2.367)

    def broad_positive_hours(df: pd.DataFrame) -> pd.Series:
        return _c2_sell_base(df) & _jst_hour(df).isin({3, 4, 5, 11, 12, 14, 17, 18, 22})

    def h1_gap_gt_2743(df: pd.DataFrame) -> pd.Series:
        return _c2_sell_base(df) & _h1_gap_side_atr(df).gt(2.743)

    def good_hours_11_14_17(df: pd.DataFrame) -> pd.Series:
        return _c2_sell_base(df) & _jst_hour(df).isin({11, 14, 17})

    def macd_mid(df: pd.DataFrame) -> pd.Series:
        macd = _macd_delta(df)
        return _c2_sell_base(df) & macd.gt(-0.633) & macd.le(-0.256)

    def h1_gap_gt_2743_and_range_2175_2367(df: pd.DataFrame) -> pd.Series:
        width = _range_width_atr(df)
        return _c2_sell_base(df) & _h1_gap_side_atr(df).gt(2.743) & width.gt(2.175) & width.le(2.367)

    def h1_gap_gt_2743_and_macd_mid(df: pd.DataFrame) -> pd.Series:
        macd = _macd_delta(df)
        return _c2_sell_base(df) & _h1_gap_side_atr(df).gt(2.743) & macd.gt(-0.633) & macd.le(-0.256)

    return [
        CombinedABCC2Candidate(
            name="gold_abc_v1_baseline",
            description="Frozen gold_abc_v1 baseline. C2 disabled.",
            c2_keep_func=no_c2,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_range_2_175_to_2_367",
            description="gold_abc_v1 + C2 SELL range width ATR >2.175 and <=2.367.",
            c2_keep_func=range_2175_2367,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_broad_positive_hours",
            description="gold_abc_v1 + C2 SELL broad positive signal hours.",
            c2_keep_func=broad_positive_hours,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_h1_gap_gt_2_743",
            description="gold_abc_v1 + C2 SELL H1 side-signed EMA gap >2.743 ATR.",
            c2_keep_func=h1_gap_gt_2743,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_good_hours_11_14_17",
            description="gold_abc_v1 + C2 SELL signal hours 11,14,17.",
            c2_keep_func=good_hours_11_14_17,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_macd_mid",
            description="gold_abc_v1 + C2 SELL MACD hist delta > -0.633 and <= -0.256.",
            c2_keep_func=macd_mid,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_h1_gap_gt_2_743_and_range_2_175_to_2_367",
            description="gold_abc_v1 + C2 SELL H1 gap >2.743 and range width >2.175 <=2.367.",
            c2_keep_func=h1_gap_gt_2743_and_range_2175_2367,
        ),
        CombinedABCC2Candidate(
            name="gold_abc_v1_plus_c2_sell_h1_gap_gt_2_743_and_macd_mid",
            description="gold_abc_v1 + C2 SELL H1 gap >2.743 and MACD hist delta > -0.633 <= -0.256.",
            c2_keep_func=h1_gap_gt_2743_and_macd_mid,
        ),
    ]


def apply_c2_candidate(abc_df: pd.DataFrame, c2_df: pd.DataFrame, candidate: CombinedABCC2Candidate) -> pd.DataFrame:
    out = abc_df.copy()
    c2_sell = candidate.c2_keep_func(c2_df).fillna(False).astype(bool)
    c2_buy = pd.Series(False, index=out.index)

    out["c2_sell_signal_candidate"] = c2_sell
    out["c2_buy_signal_candidate"] = c2_buy
    out["combined_abcc2_candidate_name"] = candidate.name

    existing_buy = out["combined_buy_signal"].fillna(False).astype(bool)
    existing_sell = out["combined_sell_signal"].fillna(False).astype(bool)

    combined_buy = existing_buy | c2_buy
    combined_sell = existing_sell | c2_sell
    conflict = combined_buy & combined_sell

    out["combined_signal_conflict"] = conflict
    out["combined_buy_signal"] = combined_buy & ~conflict
    out["combined_sell_signal"] = combined_sell & ~conflict

    source = out["combined_signal_source"].fillna("NONE").astype("object").copy()
    source.loc[out["combined_sell_signal"] & c2_sell & existing_sell] = "MIXED"
    source.loc[out["combined_sell_signal"] & c2_sell & ~existing_sell] = "C2"
    source.loc[~out["combined_buy_signal"] & ~out["combined_sell_signal"]] = "NONE"
    out["combined_signal_source"] = source

    out["combined_signal_side"] = "NONE"
    out.loc[out["combined_buy_signal"], "combined_signal_side"] = "BUY"
    out.loc[out["combined_sell_signal"], "combined_signal_side"] = "SELL"

    # Existing backtest engine consumes hidden divergence columns.
    out["hidden_bullish_divergence"] = out["combined_buy_signal"]
    out["hidden_bearish_divergence"] = out["combined_sell_signal"]
    return out


def attach_sources_to_trades(trades: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    cols = [
        "combined_signal_source",
        "combined_signal_side",
        "c2_sell_signal_candidate",
        "c2_buy_signal_candidate",
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


def summarize_source_breakdown(trades: pd.DataFrame) -> dict[str, object]:
    row: dict[str, object] = {}
    for source in ["A", "B", "C", "C2", "MIXED"]:
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
    abc_df: pd.DataFrame,
    c2_df: pd.DataFrame,
    candidate: CombinedABCC2Candidate,
    settings: BacktestSettings,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidate_df = apply_c2_candidate(abc_df, c2_df, candidate)
    trades = run_simple_hidden_divergence_backtest(candidate_df, settings=settings)
    trades = attach_sources_to_trades(trades, candidate_df)
    trades = attach_jst_trade_times(trades, args=args)
    if not trades.empty:
        trades["candidate"] = candidate.name
        trades["jst_entry_hour"] = trades["jst_entry_time"].dt.hour
        trades["jst_entry_month"] = trades["jst_entry_time"].dt.to_period("M").astype(str)

    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "c2_sell_signals": int(candidate_df["c2_sell_signal_candidate"].sum()),
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
    parser = argparse.ArgumentParser(description="Compare gold_abc_v1 + C2 SELL candidates.")
    parser.add_argument("--preset", type=str, default="gold_abc_v1")
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
    parser.add_argument("--b-buy-exclude-risk-atr-range", type=str, default=None)
    parser.add_argument("--b-buy-exclude-risk-atr-macd-hist-delta-abs-combo", type=str, default=None)
    parser.add_argument("--c-breakout-lookback-bars", type=int, default=12)
    parser.add_argument("--c-min-breakout-atr", type=float, default=0.0)
    parser.add_argument("--c-max-breakout-atr", type=float, default=None)
    parser.add_argument("--c-buy-jst-hours", type=str, default=None)
    parser.add_argument("--c-sell-jst-hours", type=str, default=None)
    parser.add_argument("--c-buy-h1-ema-gap-atr-max", type=float, default=None)
    parser.add_argument("--c-no-h1-trend", action="store_true")
    parser.add_argument("--c-no-m15-ema-alignment", action="store_true")
    parser.add_argument("--c-no-close-beyond-ema20", action="store_true")
    parser.add_argument("--c-no-macd-hist-direction", action="store_true")
    parser.add_argument("--c-no-macd-hist-acceleration", action="store_true")
    parser.add_argument("--c-allow-ab-overlap", action="store_true")
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
    parser.add_argument("--save", action="store_true")
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
        print("target: gold_abc_v1 + C2 SELL candidates")

        abc_df, _baseline_trades = run_gold_abc_v1_symbol(args, symbol=symbol)
        c2_df = build_c2_signal_df(args, symbol=symbol)

        symbol_rows: list[dict[str, object]] = []
        symbol_trade_map: dict[str, pd.DataFrame] = {}
        for candidate in candidates:
            _candidate_df, trades, row = run_candidate(
                args=args,
                abc_df=abc_df,
                c2_df=c2_df,
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
            "closed_trades",
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
            "c_total_r",
            "c_profit_factor",
            "c2_trades",
            "c2_win_rate",
            "c2_total_r",
            "c2_profit_factor",
            "c2_max_drawdown_r",
            "mixed_trades",
            "mixed_total_r",
            "c2_sell_signals",
            "conflicts_skipped",
            "description",
        ]
        available = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("GOLD_ABC_V1_PLUS_C2_SELL_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

        if not summary_df.empty:
            best_name = str(summary_df.iloc[0]["candidate"])
            best_trades = symbol_trade_map.get(best_name, pd.DataFrame())
            if not best_trades.empty:
                print_table("BEST_CANDIDATE_BY_SOURCE", summarize_grouped(best_trades, ["combined_signal_source"]))
                print_table("BEST_CANDIDATE_BY_MONTH", summarize_grouped(best_trades, ["jst_entry_month"]))

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "combined_abc_v1_c2_sell_candidate_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_combined_abc_v1_c2_sell_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "combined_abc_v1_c2_sell_candidate_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_combined_abc_v1_c2_sell_trades: {trades_path}")

    print("=" * 120)
    print("gold_abc_v1 + C2 SELL candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
