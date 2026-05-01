from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_a_filter_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_a_signal_trades import (
    attach_jst_trade_times,
    build_a_signal_df,
    enrich_a_trades,
    parse_int_csv,
)
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR
from src.presets import get_preset


@dataclass(frozen=True)
class AFilterCandidate:
    name: str
    description: str
    filter_func: Callable[[pd.DataFrame], pd.DataFrame]


def _true_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


def _side_aware_hidden_price_delta_atr(df: pd.DataFrame) -> pd.Series:
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    buy_value = pd.to_numeric(df["bullish_hidden_price_delta"], errors="coerce") / atr
    sell_value = pd.to_numeric(df["bearish_hidden_price_delta"], errors="coerce") / atr
    out = pd.Series(pd.NA, index=df.index, dtype="Float64")
    out.loc[df["a_buy_signal_filtered"].astype(bool)] = buy_value.loc[df["a_buy_signal_filtered"].astype(bool)]
    out.loc[df["a_sell_signal_filtered"].astype(bool)] = sell_value.loc[df["a_sell_signal_filtered"].astype(bool)]
    return pd.to_numeric(out, errors="coerce")


def _side_aware_h1_ema_gap_atr(df: pd.DataFrame) -> pd.Series:
    atr = pd.to_numeric(df["atr_14"], errors="coerce")
    h1_gap = pd.to_numeric(df["h1_ema_20"], errors="coerce") - pd.to_numeric(df["h1_ema_50"], errors="coerce")
    signed = h1_gap.copy()
    signed.loc[df["a_sell_signal_filtered"].astype(bool)] = -signed.loc[df["a_sell_signal_filtered"].astype(bool)]
    return signed / atr


def _apply_hours(
    df: pd.DataFrame,
    *,
    buy_hours: set[int] | None,
    sell_hours: set[int] | None,
) -> pd.Series:
    hours = pd.to_numeric(df["jst_hour"], errors="coerce").astype("Int64")
    buy = df["a_buy_signal_filtered"].astype(bool)
    sell = df["a_sell_signal_filtered"].astype(bool)

    if buy_hours is not None:
        buy = buy & hours.isin(buy_hours)
    if sell_hours is not None:
        sell = sell & hours.isin(sell_hours)

    return buy | sell


def _apply_candidate_to_signal_df(signal_df: pd.DataFrame, candidate: AFilterCandidate) -> pd.DataFrame:
    out = signal_df.copy()
    keep = candidate.filter_func(out).fillna(False).astype(bool)

    buy = out["a_buy_signal_filtered"].astype(bool) & keep
    sell = out["a_sell_signal_filtered"].astype(bool) & keep
    conflict = buy & sell

    out["a_candidate_name"] = candidate.name
    out["a_candidate_keep"] = keep
    out["a_buy_signal_candidate"] = buy & ~conflict
    out["a_sell_signal_candidate"] = sell & ~conflict
    out["a_candidate_conflict"] = conflict

    # The existing backtest engine consumes these two columns.
    out["hidden_bullish_divergence"] = out["a_buy_signal_candidate"]
    out["hidden_bearish_divergence"] = out["a_sell_signal_candidate"]
    return out


def build_candidates(args: argparse.Namespace) -> list[AFilterCandidate]:
    hidden_min = args.hidden_price_delta_atr_min
    h1_max = args.h1_ema_gap_side_signed_atr_max

    baseline_buy_hours = parse_int_csv(args.a_buy_jst_hours)
    baseline_sell_hours = parse_int_csv(args.a_sell_jst_hours)
    buy_13 = {13}
    sell_2_19 = {2, 19}

    def baseline(df: pd.DataFrame) -> pd.Series:
        return _true_mask(df)

    def exclude_weak_hidden_price_delta(df: pd.DataFrame) -> pd.Series:
        value = _side_aware_hidden_price_delta_atr(df)
        return value > hidden_min

    def exclude_overextended_h1_gap(df: pd.DataFrame) -> pd.Series:
        value = _side_aware_h1_ema_gap_atr(df)
        return value <= h1_max

    def exclude_both(df: pd.DataFrame) -> pd.Series:
        return exclude_weak_hidden_price_delta(df) & exclude_overextended_h1_gap(df)

    def buy_13_only_sell_baseline(df: pd.DataFrame) -> pd.Series:
        return _apply_hours(df, buy_hours=buy_13, sell_hours=baseline_sell_hours)

    def buy_baseline_sell_2_19_only(df: pd.DataFrame) -> pd.Series:
        return _apply_hours(df, buy_hours=baseline_buy_hours, sell_hours=sell_2_19)

    def buy_13_sell_2_13_19(df: pd.DataFrame) -> pd.Series:
        return _apply_hours(df, buy_hours=buy_13, sell_hours=baseline_sell_hours)

    def buy_13_sell_2_19(df: pd.DataFrame) -> pd.Series:
        return _apply_hours(df, buy_hours=buy_13, sell_hours=sell_2_19)

    def buy_13_sell_2_19_exclude_both(df: pd.DataFrame) -> pd.Series:
        return buy_13_sell_2_19(df) & exclude_both(df)

    return [
        AFilterCandidate(
            name="baseline",
            description="Preset A hours only.",
            filter_func=baseline,
        ),
        AFilterCandidate(
            name=f"exclude_hidden_price_delta_atr_le_{hidden_min:g}",
            description=f"Exclude A when side-aware hidden_price_delta_atr <= {hidden_min:g}.",
            filter_func=exclude_weak_hidden_price_delta,
        ),
        AFilterCandidate(
            name=f"exclude_h1_ema_gap_side_signed_atr_gt_{h1_max:g}",
            description=f"Exclude A when side-aware h1_ema_gap_atr > {h1_max:g}.",
            filter_func=exclude_overextended_h1_gap,
        ),
        AFilterCandidate(
            name="exclude_hidden_price_delta_and_h1_overextension",
            description="Apply both numeric exclusions.",
            filter_func=exclude_both,
        ),
        AFilterCandidate(
            name="buy_13_only_sell_baseline",
            description="BUY signal hour 13 only; SELL keeps preset hours.",
            filter_func=buy_13_only_sell_baseline,
        ),
        AFilterCandidate(
            name="buy_baseline_sell_2_19_only",
            description="BUY keeps preset hours; SELL signal hours 2 and 19 only.",
            filter_func=buy_baseline_sell_2_19_only,
        ),
        AFilterCandidate(
            name="buy_13_sell_2_13_19",
            description="BUY signal hour 13 only; SELL signal hours 2,13,19.",
            filter_func=buy_13_sell_2_13_19,
        ),
        AFilterCandidate(
            name="buy_13_sell_2_19",
            description="BUY signal hour 13 only; SELL signal hours 2 and 19 only.",
            filter_func=buy_13_sell_2_19,
        ),
        AFilterCandidate(
            name="buy_13_sell_2_19_exclude_both",
            description="BUY 13 + SELL 2,19 + both numeric exclusions.",
            filter_func=buy_13_sell_2_19_exclude_both,
        ),
    ]


def _summary_row(candidate: AFilterCandidate, signal_df: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "candidate_buy_signals": int(signal_df["a_buy_signal_candidate"].sum()),
        "candidate_sell_signals": int(signal_df["a_sell_signal_candidate"].sum()),
        "candidate_total_signals": int((signal_df["a_buy_signal_candidate"] | signal_df["a_sell_signal_candidate"]).sum()),
    }
    row.update(summary)

    if not trades.empty:
        by_side = {}
        for side, group in trades.groupby("side", dropna=False):
            side_summary = summarize_trades(group)
            by_side[str(side)] = side_summary
        for side in ["BUY", "SELL"]:
            side_summary = by_side.get(side, {})
            row[f"{side.lower()}_trades"] = side_summary.get("trades", 0)
            row[f"{side.lower()}_win_rate"] = side_summary.get("win_rate", 0.0)
            row[f"{side.lower()}_total_r"] = side_summary.get("total_r", 0.0)
            row[f"{side.lower()}_profit_factor"] = side_summary.get("profit_factor", None)
            row[f"{side.lower()}_max_drawdown_r"] = side_summary.get("max_drawdown_r", 0.0)
    else:
        for side in ["buy", "sell"]:
            row[f"{side}_trades"] = 0
            row[f"{side}_win_rate"] = 0.0
            row[f"{side}_total_r"] = 0.0
            row[f"{side}_profit_factor"] = None
            row[f"{side}_max_drawdown_r"] = 0.0

    return row


def run_candidate(
    *,
    candidate: AFilterCandidate,
    base_signal_df: pd.DataFrame,
    settings: BacktestSettings,
    preset_name: str,
    early_loss_bars: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidate_signal_df = _apply_candidate_to_signal_df(base_signal_df, candidate)
    trades = run_simple_hidden_divergence_backtest(candidate_signal_df, settings=settings)
    trades = attach_jst_trade_times(trades, preset_name=preset_name)
    trades = enrich_a_trades(trades, candidate_signal_df, early_loss_bars=early_loss_bars)
    if not trades.empty and "jst_entry_time" in trades.columns:
        trades["jst_entry_time_hour"] = trades["jst_entry_time"].dt.hour
    if not trades.empty:
        trades["candidate"] = candidate.name

    row = _summary_row(candidate, candidate_signal_df, trades)
    return candidate_signal_df, trades, row


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare A-signal filter candidates by rerunning backtests per candidate.")
    parser.add_argument("--preset", type=str, default="gold_ab_v2", help="Preset to use. Default: gold_ab_v2")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--a-buy-jst-hours", type=str, default=None, help="Baseline A BUY signal JST hours. Default: from preset")
    parser.add_argument("--a-sell-jst-hours", type=str, default=None, help="Baseline A SELL signal JST hours. Default: from preset")
    parser.add_argument("--rr", type=float, default=None, help="Override RR. Default: from preset")
    parser.add_argument("--sl-buffer-atr", type=float, default=None, help="Override SL buffer ATR. Default: from preset")
    parser.add_argument("--same-bar-win", action="store_true", help="If set, same-bar TP/SL is treated as win. Default is conservative loss.")
    parser.add_argument("--max-bars-in-trade", type=int, default=None, help="Optional maximum bars to hold a trade.")
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Losses closed within this many bars are flagged as early losses. Default: 2")
    parser.add_argument("--hidden-price-delta-atr-min", type=float, default=0.271, help="Candidate threshold from diagnostics. Default: 0.271")
    parser.add_argument("--h1-ema-gap-side-signed-atr-max", type=float, default=3.267, help="Candidate threshold from diagnostics. Default: 3.267")
    parser.add_argument("--save", action="store_true", help="Save comparison CSVs to data/results.")
    args = parser.parse_args()

    preset = get_preset(args.preset)
    if args.symbols is None:
        args.symbols = preset.symbols
    if args.a_buy_jst_hours is None:
        args.a_buy_jst_hours = preset.a_buy_jst_hours
    if args.a_sell_jst_hours is None:
        args.a_sell_jst_hours = preset.a_sell_jst_hours
    if args.rr is None:
        args.rr = preset.rr
    if args.sl_buffer_atr is None:
        args.sl_buffer_atr = preset.sl_buffer_atr
    if args.max_bars_in_trade is None:
        args.max_bars_in_trade = preset.max_bars_in_trade

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1
    if args.early_loss_bars <= 0:
        print(f"early-loss-bars must be positive: {args.early_loss_bars}")
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

    all_summary_rows: list[dict[str, object]] = []
    all_trades: list[pd.DataFrame] = []

    for symbol in symbols:
        print("=" * 120)
        print(f"Comparing A filter candidates for symbol: {symbol}")
        print(f"preset: {args.preset}")
        print(f"baseline A BUY signal JST hours: {args.a_buy_jst_hours}")
        print(f"baseline A SELL signal JST hours: {args.a_sell_jst_hours}")
        print(f"hidden_price_delta_atr_min: {args.hidden_price_delta_atr_min}")
        print(f"h1_ema_gap_side_signed_atr_max: {args.h1_ema_gap_side_signed_atr_max}")

        base_signal_df = build_a_signal_df(args, symbol=symbol)

        symbol_rows: list[dict[str, object]] = []
        for candidate in candidates:
            _candidate_signal_df, trades, row = run_candidate(
                candidate=candidate,
                base_signal_df=base_signal_df,
                settings=settings,
                preset_name=args.preset,
                early_loss_bars=args.early_loss_bars,
            )
            row["symbol"] = symbol
            symbol_rows.append(row)
            all_summary_rows.append(row)
            if not trades.empty:
                trades = trades.copy()
                trades["symbol"] = symbol
                all_trades.append(trades)

        summary_df = pd.DataFrame(symbol_rows)
        ordered_cols = [
            "symbol",
            "candidate",
            "candidate_total_signals",
            "candidate_buy_signals",
            "candidate_sell_signals",
            "trades",
            "wins",
            "losses",
            "win_rate",
            "average_r",
            "total_r",
            "profit_factor",
            "max_consecutive_losses",
            "max_drawdown_r",
            "buy_trades",
            "buy_win_rate",
            "buy_total_r",
            "buy_profit_factor",
            "buy_max_drawdown_r",
            "sell_trades",
            "sell_win_rate",
            "sell_total_r",
            "sell_profit_factor",
            "sell_max_drawdown_r",
            "description",
        ]
        available_cols = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available_cols].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("A_FILTER_CANDIDATE_COMPARISON_SORTED_BY_TOTAL_R", summary_df)

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        all_summary_df = pd.DataFrame(all_summary_rows)
        summary_path = RESULTS_DATA_DIR / "a_filter_candidate_comparison.csv"
        all_summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_a_filter_candidate_summary: {summary_path}")

        if all_trades:
            trades_df = pd.concat(all_trades, ignore_index=True)
            trades_path = RESULTS_DATA_DIR / "a_filter_candidate_trades.csv"
            trades_df.to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_a_filter_candidate_trades: {trades_path}")

    print("=" * 120)
    print("A filter candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
