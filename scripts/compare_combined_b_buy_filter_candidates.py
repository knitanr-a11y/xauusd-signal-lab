from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

# Allow running as: python scripts/compare_combined_b_buy_filter_candidates.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_combined_failure_modes import apply_preset_defaults
from scripts.run_combined_backtest import (
    add_combined_signal_columns,
    attach_signal_sources_to_trades,
    attach_jst_trade_times,
    build_base_dataframe,
    build_paths,
    parse_float_range,
    parse_int_csv,
)
from scripts.run_combined_backtest_with_a_filters import apply_a_filters
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


@dataclass(frozen=True)
class BBuyFilterCandidate:
    name: str
    description: str
    remove_func: Callable[[pd.DataFrame], pd.Series]


def _false_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(False, index=df.index)


def _b_buy_risk(df: pd.DataFrame) -> pd.Series:
    if "b_buy_risk_atr_ratio" not in df.columns:
        raise ValueError("b_buy_risk_atr_ratio is required. It is created by add_combined_signal_columns().")
    return pd.to_numeric(df["b_buy_risk_atr_ratio"], errors="coerce")


def _b_macd_abs(df: pd.DataFrame) -> pd.Series:
    if "b_macd_hist_delta_abs" not in df.columns:
        raise ValueError("b_macd_hist_delta_abs is required. It is created by add_combined_signal_columns().")
    return pd.to_numeric(df["b_macd_hist_delta_abs"], errors="coerce")


def _jst_hour(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["jst_hour"], errors="coerce")


def build_candidates() -> list[BBuyFilterCandidate]:
    def baseline(df: pd.DataFrame) -> pd.Series:
        return _false_mask(df)

    def risk_0928_1241(df: pd.DataFrame) -> pd.Series:
        risk = _b_buy_risk(df)
        return risk.gt(0.928) & risk.le(1.241)

    def risk_1241_24_and_macd_0375_0742(df: pd.DataFrame) -> pd.Series:
        risk = _b_buy_risk(df)
        macd = _b_macd_abs(df)
        return risk.gt(1.241) & risk.le(2.4) & macd.gt(0.375) & macd.le(0.742)

    def macd_060_0742(df: pd.DataFrame) -> pd.Series:
        macd = _b_macd_abs(df)
        return macd.gt(0.60) & macd.le(0.742)

    def macd_gt_10(df: pd.DataFrame) -> pd.Series:
        macd = _b_macd_abs(df)
        return macd.gt(1.0)

    def hour22_and_macd_gt_0742(df: pd.DataFrame) -> pd.Series:
        return _jst_hour(df).eq(22) & _b_macd_abs(df).gt(0.742)

    def risk_0928_1241_or_combo(df: pd.DataFrame) -> pd.Series:
        return risk_0928_1241(df) | risk_1241_24_and_macd_0375_0742(df)

    return [
        BBuyFilterCandidate(
            name="gold_ab_v3_baseline",
            description="Current gold_ab_v3. No extra B BUY filter.",
            remove_func=baseline,
        ),
        BBuyFilterCandidate(
            name="b_buy_exclude_risk_0_928_to_1_241",
            description="Exclude B BUY when risk_atr_ratio is > 0.928 and <= 1.241.",
            remove_func=risk_0928_1241,
        ),
        BBuyFilterCandidate(
            name="b_buy_exclude_risk_1_241_to_2_4_and_macd_0_375_to_0_742",
            description="Exclude B BUY when risk_atr_ratio is > 1.241 and <= 2.4 AND macd_hist_delta_abs is > 0.375 and <= 0.742.",
            remove_func=risk_1241_24_and_macd_0375_0742,
        ),
        BBuyFilterCandidate(
            name="b_buy_exclude_macd_0_60_to_0_742",
            description="Exclude B BUY when macd_hist_delta_abs is > 0.60 and <= 0.742.",
            remove_func=macd_060_0742,
        ),
        BBuyFilterCandidate(
            name="b_buy_exclude_macd_gt_1_0",
            description="Exclude B BUY when macd_hist_delta_abs is > 1.0.",
            remove_func=macd_gt_10,
        ),
        BBuyFilterCandidate(
            name="b_buy_exclude_hour_22_and_macd_gt_0_742",
            description="Exclude B BUY at JST hour 22 when macd_hist_delta_abs is > 0.742.",
            remove_func=hour22_and_macd_gt_0742,
        ),
        BBuyFilterCandidate(
            name="b_buy_exclude_risk_0_928_to_1_241_or_combo",
            description="Exclude B BUY risk 0.928-1.241 OR risk 1.241-2.4 with macd 0.375-0.742.",
            remove_func=risk_0928_1241_or_combo,
        ),
    ]


def apply_b_buy_candidate(combined_df: pd.DataFrame, candidate: BBuyFilterCandidate) -> pd.DataFrame:
    out = combined_df.copy()
    b_buy = out["b_buy_signal_filtered"].astype(bool)
    remove = candidate.remove_func(out).fillna(False).astype(bool) & b_buy

    out["b_buy_candidate_name"] = candidate.name
    out["b_buy_candidate_filtered_out"] = remove
    out["b_buy_signal_filtered"] = b_buy & ~remove

    combined_buy = out["a_buy_signal_filtered"].astype(bool) | out["b_buy_signal_filtered"].astype(bool)
    combined_sell = out["a_sell_signal_filtered"].astype(bool) | out["b_sell_signal_filtered"].astype(bool)
    conflict = combined_buy & combined_sell

    out["combined_signal_conflict"] = conflict
    out["combined_buy_signal"] = combined_buy & ~conflict
    out["combined_sell_signal"] = combined_sell & ~conflict

    a_buy = out["a_buy_signal_filtered"].astype(bool)
    a_sell = out["a_sell_signal_filtered"].astype(bool)
    b_buy = out["b_buy_signal_filtered"].astype(bool)
    b_sell = out["b_sell_signal_filtered"].astype(bool)

    out["combined_signal_source"] = "NONE"
    out.loc[out["combined_buy_signal"] & a_buy & ~b_buy, "combined_signal_source"] = "A"
    out.loc[out["combined_sell_signal"] & a_sell & ~b_sell, "combined_signal_source"] = "A"
    out.loc[out["combined_buy_signal"] & b_buy & ~a_buy, "combined_signal_source"] = "B"
    out.loc[out["combined_sell_signal"] & b_sell & ~a_sell, "combined_signal_source"] = "B"
    out.loc[out["combined_buy_signal"] & a_buy & b_buy, "combined_signal_source"] = "A+B"
    out.loc[out["combined_sell_signal"] & a_sell & b_sell, "combined_signal_source"] = "A+B"

    out["combined_signal_side"] = "NONE"
    out.loc[out["combined_buy_signal"], "combined_signal_side"] = "BUY"
    out.loc[out["combined_sell_signal"], "combined_signal_side"] = "SELL"

    out["hidden_bullish_divergence"] = out["combined_buy_signal"]
    out["hidden_bearish_divergence"] = out["combined_sell_signal"]
    return out


def summarize_source_breakdown(trades: pd.DataFrame) -> dict[str, object]:
    row: dict[str, object] = {}
    for source in ["A", "B", "A+B"]:
        if trades.empty or "combined_signal_source" not in trades.columns:
            group = trades.iloc[0:0]
        else:
            group = trades[trades["combined_signal_source"].eq(source)]
        summary = summarize_trades(group)
        prefix = source.lower().replace("+", "_")
        row[f"{prefix}_trades"] = summary["trades"]
        row[f"{prefix}_win_rate"] = summary["win_rate"]
        row[f"{prefix}_total_r"] = summary["total_r"]
        row[f"{prefix}_profit_factor"] = summary["profit_factor"]
    return row


def summarize_b_buy_breakdown(trades: pd.DataFrame) -> dict[str, object]:
    if trades.empty:
        b_buy = trades.iloc[0:0]
    else:
        b_buy = trades[trades["combined_signal_source"].eq("B") & trades["side"].eq("BUY")]
    summary = summarize_trades(b_buy)
    return {
        "b_buy_trades": summary["trades"],
        "b_buy_win_rate": summary["win_rate"],
        "b_buy_total_r": summary["total_r"],
        "b_buy_profit_factor": summary["profit_factor"],
        "b_buy_max_drawdown_r": summary["max_drawdown_r"],
    }


def run_candidate(
    *,
    args: argparse.Namespace,
    baseline_combined_df: pd.DataFrame,
    candidate: BBuyFilterCandidate,
    settings: BacktestSettings,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidate_df = apply_b_buy_candidate(baseline_combined_df, candidate)
    trades = run_simple_hidden_divergence_backtest(candidate_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = attach_signal_sources_to_trades(trades, candidate_df)
    if not trades.empty:
        trades["candidate"] = candidate.name

    summary = summarize_trades(trades)
    row: dict[str, object] = {
        "candidate": candidate.name,
        "description": candidate.description,
        "a_buy_signals": int(candidate_df["a_buy_signal_filtered"].sum()),
        "a_sell_signals": int(candidate_df["a_sell_signal_filtered"].sum()),
        "b_buy_signals": int(candidate_df["b_buy_signal_filtered"].sum()),
        "b_sell_signals": int(candidate_df["b_sell_signal_filtered"].sum()),
        "b_buy_filtered_out": int(candidate_df["b_buy_candidate_filtered_out"].sum()),
        "combined_buy_signals": int(candidate_df["combined_buy_signal"].sum()),
        "combined_sell_signals": int(candidate_df["combined_sell_signal"].sum()),
        "conflicts_skipped": int(candidate_df["combined_signal_conflict"].sum()),
    }
    row.update(summary)
    row.update(summarize_source_breakdown(trades))
    row.update(summarize_b_buy_breakdown(trades))
    return candidate_df, trades, row


def build_baseline_combined_df(args: argparse.Namespace, symbol: str) -> pd.DataFrame:
    m15_path, h1_path = build_paths(args.data_dir, symbol)
    if not m15_path.exists():
        raise FileNotFoundError(f"M15 file not found: {m15_path}")
    if not h1_path.exists():
        raise FileNotFoundError(f"H1 file not found: {h1_path}")

    base_df = build_base_dataframe(args, m15_path=m15_path, h1_path=h1_path)
    filtered_base_df = apply_a_filters(base_df, args=args)
    return add_combined_signal_columns(
        filtered_base_df,
        a_buy_hours=parse_int_csv(args.a_buy_jst_hours),
        a_sell_hours=parse_int_csv(args.a_sell_jst_hours),
        b_buy_hours=parse_int_csv(args.b_buy_jst_hours),
        b_sell_hours=parse_int_csv(args.b_sell_jst_hours),
        enabled_models={item.upper() for item in args.models.split(",") if item.strip()},
        b_exclude_risk_atr_range=parse_float_range(args.b_exclude_risk_atr_range),
        b_exclude_macd_hist_delta_abs_range=parse_float_range(args.b_exclude_macd_hist_delta_abs_range),
        sl_buffer_atr=args.sl_buffer_atr,
    )


def print_table(title: str, df: pd.DataFrame) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare combined A+B backtests with B BUY filter candidates.")
    parser.add_argument("--preset", type=str, default="gold_ab_v3", help="Preset to use. Default: gold_ab_v3")
    parser.add_argument("--data-dir", type=Path, default=RAW_DATA_DIR, help="Directory containing raw CSV files.")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols. Default: from preset")
    parser.add_argument("--models", type=str, default=None, help="Enabled models. Default: from preset")
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
        print(f"preset: {args.preset}")
        print("target: combined A+B with extra B BUY candidate filters")
        print(f"B BUY JST hours: {args.b_buy_jst_hours}")
        print(f"B SELL JST hours: {args.b_sell_jst_hours}")
        print(f"existing B exclude risk_atr_range: {args.b_exclude_risk_atr_range or 'NONE'}")
        print(f"existing B exclude macd_hist_delta_abs_range: {args.b_exclude_macd_hist_delta_abs_range or 'NONE'}")

        baseline_combined_df = build_baseline_combined_df(args, symbol=symbol)
        symbol_rows: list[dict[str, object]] = []

        for candidate in candidates:
            _candidate_df, trades, row = run_candidate(
                args=args,
                baseline_combined_df=baseline_combined_df,
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
            "b_buy_filtered_out",
            "a_trades",
            "a_win_rate",
            "a_total_r",
            "a_profit_factor",
            "b_trades",
            "b_win_rate",
            "b_total_r",
            "b_profit_factor",
            "b_buy_trades",
            "b_buy_win_rate",
            "b_buy_total_r",
            "b_buy_profit_factor",
            "b_buy_max_drawdown_r",
            "a_buy_signals",
            "a_sell_signals",
            "b_buy_signals",
            "b_sell_signals",
            "combined_buy_signals",
            "combined_sell_signals",
            "description",
        ]
        available_cols = [col for col in ordered_cols if col in summary_df.columns]
        summary_df = summary_df[available_cols].sort_values(["total_r", "profit_factor"], ascending=[False, False]).reset_index(drop=True)
        print_table("COMBINED_A_B_WITH_B_BUY_FILTER_CANDIDATES_SORTED_BY_TOTAL_R", summary_df)

    if args.save:
        RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = RESULTS_DATA_DIR / "combined_ab_b_buy_filter_candidate_comparison.csv"
        pd.DataFrame(all_rows).to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nsaved_combined_ab_b_buy_filter_candidate_summary: {summary_path}")
        if all_trades:
            trades_path = RESULTS_DATA_DIR / "combined_ab_b_buy_filter_candidate_trades.csv"
            pd.concat(all_trades, ignore_index=True).to_csv(trades_path, index=False, encoding="utf-8-sig")
            print(f"saved_combined_ab_b_buy_filter_candidate_trades: {trades_path}")

    print("=" * 120)
    print("Combined B BUY filter candidate comparison completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
