from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_combined_c_buy_component.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_c_signal_trades import build_c_signal_df, enrich_c_trades
from scripts.analyze_combined_failure_modes import (
    apply_preset_defaults,
    drawdown_segments,
    loss_streaks,
    summarize_grouped,
    summarize_numeric_bins,
)
from scripts.compare_combined_abc_c_buy_candidates import (
    apply_abc_candidate,
    build_ab_v4_combined_df,
    build_candidates,
)
from scripts.run_combined_backtest import attach_jst_trade_times
from src.backtest import BacktestSettings, run_simple_hidden_divergence_backtest, summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


def print_dict(title: str, data: dict[str, object]) -> None:
    print(f"\n{title}:")
    for key, value in data.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.6f}")
        else:
            print(f"  {key}: {value}")


def print_section(title: str, df: pd.DataFrame, max_rows: int | None = None) -> None:
    print(f"\n{title}:")
    if df.empty:
        print("No data.")
        return
    if max_rows is not None:
        df = df.head(max_rows)
    print(df.to_string(index=False))


def add_equity_columns(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades
    out = trades.copy().reset_index(drop=True)
    out["trade_no"] = out.index + 1
    out["equity_r"] = pd.to_numeric(out["r"], errors="coerce").fillna(0.0).cumsum()
    out["equity_peak_r"] = out["equity_r"].cummax().clip(lower=0.0)
    out["drawdown_r"] = out["equity_peak_r"] - out["equity_r"]
    return out


def attach_combined_features(trades: pd.DataFrame, combined_df: pd.DataFrame) -> pd.DataFrame:
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
        "jst_hour",
    ]
    available = [col for col in cols if col in combined_df.columns]
    features = combined_df[available].copy()
    features["signal_index"] = combined_df.index
    return trades.merge(features, on="signal_index", how="left")


def build_candidate_backtest(args: argparse.Namespace, symbol: str, candidate_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ab_df = build_ab_v4_combined_df(args, symbol=symbol)
    c_df = build_c_signal_df(args, symbol=symbol)
    candidates = {candidate.name: candidate for candidate in build_candidates()}
    if candidate_name not in candidates:
        available = ", ".join(sorted(candidates.keys()))
        raise ValueError(f"Unknown candidate: {candidate_name}. Available: {available}")

    candidate = candidates[candidate_name]
    combined_df = apply_abc_candidate(ab_df, c_df, candidate)

    settings = BacktestSettings(
        rr=args.rr,
        sl_buffer_atr_multiplier=args.sl_buffer_atr,
        conservative_same_bar=not args.same_bar_win,
        max_bars_in_trade=args.max_bars_in_trade,
    )
    trades = run_simple_hidden_divergence_backtest(combined_df, settings=settings)
    trades = attach_jst_trade_times(trades, args=args)
    trades = attach_combined_features(trades, combined_df)
    if not trades.empty:
        trades["candidate"] = candidate_name
        trades["jst_entry_hour"] = trades["jst_entry_time"].dt.hour
        trades["jst_entry_month"] = trades["jst_entry_time"].dt.to_period("M").astype(str)
    trades = add_equity_columns(trades)
    return combined_df, c_df, trades


def enrich_c_component_trades(c_trades: pd.DataFrame, c_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if c_trades.empty:
        return c_trades
    enriched = enrich_c_trades(
        c_trades,
        c_df,
        early_loss_bars=args.early_loss_bars,
        long_hold_bars=args.long_hold_bars,
    )
    # enrich_c_trades merges columns and may not preserve combined labels if already present; keep them stable.
    if "combined_signal_source_x" in enriched.columns and "combined_signal_source" not in enriched.columns:
        enriched["combined_signal_source"] = enriched["combined_signal_source_x"]
    if "jst_entry_time" in enriched.columns:
        enriched["jst_entry_hour"] = enriched["jst_entry_time"].dt.hour
        enriched["jst_entry_month"] = enriched["jst_entry_time"].dt.to_period("M").astype(str)
    enriched = add_equity_columns(enriched)
    return enriched


def candidate_filter_summary(c_trades: pd.DataFrame) -> pd.DataFrame:
    if c_trades.empty:
        return pd.DataFrame()

    base = summarize_trades(c_trades)
    risk = pd.to_numeric(c_trades.get("risk_atr_ratio", pd.Series(index=c_trades.index)), errors="coerce")
    breakout = pd.to_numeric(c_trades.get("breakout_distance_atr", pd.Series(index=c_trades.index)), errors="coerce")
    range_width = pd.to_numeric(c_trades.get("signal_c_previous_range_width_atr", pd.Series(index=c_trades.index)), errors="coerce")
    macd_delta = pd.to_numeric(c_trades.get("signal_c_macd_hist_delta", pd.Series(index=c_trades.index)), errors="coerce")
    h1_gap = pd.to_numeric(c_trades.get("h1_ema_gap_side_signed_atr", pd.Series(index=c_trades.index)), errors="coerce")
    hour = pd.to_numeric(c_trades.get("jst_entry_hour", pd.Series(index=c_trades.index)), errors="coerce")

    checks: list[tuple[str, pd.Series]] = [
        ("remove_hour_0", hour.eq(0)),
        ("remove_hour_4", hour.eq(4)),
        ("remove_hour_17", hour.eq(17)),
        ("remove_hour_19", hour.eq(19)),
        ("remove_weak_hours_0_4_17_19", hour.isin([0, 4, 17, 19])),
        ("remove_risk_gt_4_44", risk.gt(4.44)),
        ("remove_risk_gt_3_452", risk.gt(3.452)),
        ("remove_breakout_gt_0_710", breakout.gt(0.710)),
        ("remove_breakout_0_411_to_0_710", breakout.gt(0.411) & breakout.le(0.710)),
        ("remove_range_width_2_414_to_2_930", range_width.gt(2.414) & range_width.le(2.930)),
        ("remove_macd_delta_le_0_235", macd_delta.le(0.235)),
        ("remove_h1_gap_0_511_to_1_721", h1_gap.gt(0.511) & h1_gap.le(1.721)),
        ("remove_long_hold_losses_posttrade_reference", c_trades.get("long_hold_loss", pd.Series(False, index=c_trades.index)).fillna(False).astype(bool)),
    ]

    rows: list[dict[str, object]] = []
    for name, remove in checks:
        remove = remove.fillna(False).astype(bool)
        removed = c_trades[remove]
        kept = c_trades[~remove]
        kept_summary = summarize_trades(kept)
        removed_summary = summarize_trades(removed)
        rows.append(
            {
                "candidate": name,
                "base_trades": base["trades"],
                "base_total_r": base["total_r"],
                "base_profit_factor": base["profit_factor"],
                "kept_trades": kept_summary["trades"],
                "kept_win_rate": kept_summary["win_rate"],
                "kept_total_r": kept_summary["total_r"],
                "kept_profit_factor": kept_summary["profit_factor"],
                "kept_max_drawdown_r": kept_summary["max_drawdown_r"],
                "removed_trades": removed_summary["trades"],
                "removed_wins": removed_summary["wins"],
                "removed_losses": removed_summary["losses"],
                "removed_win_rate": removed_summary["win_rate"],
                "removed_total_r": removed_summary["total_r"],
                "removed_profit_factor": removed_summary["profit_factor"],
                "delta_total_r_if_removed": kept_summary["total_r"] - base["total_r"],
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["delta_total_r_if_removed", "kept_profit_factor", "kept_max_drawdown_r"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def print_c_component_diagnostics(all_trades: pd.DataFrame, c_trades: pd.DataFrame) -> None:
    print_dict("combined_candidate_summary", summarize_trades(all_trades))
    print_section("combined_summary_by_source", summarize_grouped(all_trades, ["combined_signal_source"]))
    print_section("combined_summary_by_month", summarize_grouped(all_trades, ["jst_entry_month"]))

    print_dict("C_component_summary", summarize_trades(c_trades))
    print_section("C_component_by_jst_hour", summarize_grouped(c_trades, ["jst_entry_hour"]))
    print_section("C_component_by_month", summarize_grouped(c_trades, ["jst_entry_month"]))
    print_section("C_component_early_loss", summarize_grouped(c_trades, ["early_loss"]))
    print_section("C_component_long_hold_loss", summarize_grouped(c_trades, ["long_hold_loss"]))

    for col in [
        "risk_atr_ratio",
        "breakout_distance_atr",
        "signal_c_previous_range_width_atr",
        "signal_c_macd_hist_delta",
        "h1_ema_gap_side_signed_atr",
        "bars_held",
    ]:
        print_section(f"C_component_quartile_by_{col}", summarize_numeric_bins(c_trades, col, bins=4))

    print_section("C_component_candidate_filter_summary_posttrade", candidate_filter_summary(c_trades))
    print_section("C_component_drawdown_segments", drawdown_segments(c_trades), max_rows=10)
    print_section("C_component_loss_streaks", loss_streaks(c_trades), max_rows=10)

    display_cols = [
        "trade_no",
        "side",
        "jst_entry_time",
        "entry_price",
        "sl",
        "tp",
        "risk",
        "result",
        "r",
        "bars_held",
        "early_loss",
        "long_hold_loss",
        "risk_atr_ratio",
        "breakout_distance_atr",
        "signal_c_previous_range_width_atr",
        "signal_c_macd_hist_delta",
        "h1_ema_gap_side_signed_atr",
        "equity_r",
        "drawdown_r",
    ]
    available = [col for col in display_cols if col in c_trades.columns]
    print_section("C_component_losses_tail_50", c_trades[c_trades["result"].eq("loss")][available].tail(50))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze the C BUY component inside the best AB v4 + C BUY candidate.")
    parser.add_argument("--preset", type=str, default="gold_ab_v4", help="Preset context. Default: gold_ab_v4")
    parser.add_argument("--candidate", type=str, default="gold_ab_v4_plus_c_buy_broad_hours_no_13_16_23", help="Combined ABC candidate to analyze.")
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
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Default: 2")
    parser.add_argument("--long-hold-bars", type=int, default=20, help="Default: 20")
    parser.add_argument("--save", action="store_true", help="Save enriched all trades and C trades CSVs to data/results.")
    args = apply_preset_defaults(parser.parse_args())

    if not args.data_dir.exists():
        print(f"Data directory not found: {args.data_dir}")
        return 1

    symbols = [item.strip().lower() for item in args.symbols.split(",") if item.strip()]
    if not symbols:
        print("No symbols provided.")
        return 1

    for symbol in symbols:
        print("=" * 120)
        print(f"symbol: {symbol}")
        print(f"preset_context: {args.preset}")
        print(f"candidate: {args.candidate}")
        print("target: executed C component inside combined AB+C candidate")

        combined_df, c_df, all_trades = build_candidate_backtest(args, symbol=symbol, candidate_name=args.candidate)
        c_component = all_trades[all_trades["combined_signal_source"].eq("C")].copy()
        c_component = enrich_c_component_trades(c_component, c_df, args=args)
        print_c_component_diagnostics(all_trades, c_component)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            all_path = RESULTS_DATA_DIR / f"{symbol}_combined_abc_{args.candidate}_all_trades.csv"
            c_path = RESULTS_DATA_DIR / f"{symbol}_combined_abc_{args.candidate}_c_component_trades.csv"
            all_trades.to_csv(all_path, index=False, encoding="utf-8-sig")
            c_component.to_csv(c_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_all_trades: {all_path}")
            print(f"saved_c_component_trades: {c_path}")

    print("=" * 120)
    print("Combined C BUY component diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
