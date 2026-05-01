from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as: python scripts/analyze_b_buy_failure_modes.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analyze_combined_failure_modes import (
    add_equity_and_drawdown,
    apply_preset_defaults,
    build_and_backtest,
    drawdown_segments,
    loss_streaks,
    print_dict,
    print_section,
    summarize_grouped,
    summarize_numeric_bins,
)
from src.backtest import summarize_trades
from src.config import RAW_DATA_DIR, RESULTS_DATA_DIR


def _format_range_label(low: float | None, high: float | None) -> str:
    if low is None and high is None:
        return "ALL"
    if low is None:
        return f"<= {high:g}"
    if high is None:
        return f"> {low:g}"
    return f"({low:g}, {high:g}]"


def add_b_buy_diagnostic_flags(trades: pd.DataFrame, early_loss_bars: int) -> pd.DataFrame:
    if trades.empty:
        return trades

    out = trades.copy()
    out["b_buy_is_early_loss"] = out["result"].eq("loss") & (pd.to_numeric(out["bars_held"], errors="coerce") <= early_loss_bars)

    # For B BUY trades, these columns are side-specific and already merged from the signal candle.
    out["b_buy_risk_atr_ratio"] = pd.to_numeric(out.get("b_buy_risk_atr_ratio", out.get("signal_b_buy_risk_atr_ratio")), errors="coerce")
    if "signal_b_buy_risk_atr_ratio" in out.columns:
        out["b_buy_risk_atr_ratio"] = pd.to_numeric(out["signal_b_buy_risk_atr_ratio"], errors="coerce")

    out["b_macd_hist_delta_abs"] = pd.to_numeric(out.get("b_macd_hist_delta_abs", out.get("signal_b_macd_hist_delta_abs")), errors="coerce")
    if "signal_b_macd_hist_delta_abs" in out.columns:
        out["b_macd_hist_delta_abs"] = pd.to_numeric(out["signal_b_macd_hist_delta_abs"], errors="coerce")

    # Side-aware H1 EMA gap. Positive means H1 EMA20 is above EMA50 and supports BUY continuation.
    if "h1_ema_gap_side_signed_atr" not in out.columns:
        h1_gap = pd.to_numeric(out.get("signal_h1_ema_20", pd.Series(index=out.index)), errors="coerce") - pd.to_numeric(
            out.get("signal_h1_ema_50", pd.Series(index=out.index)), errors="coerce"
        )
        out["h1_ema_gap_side_signed_atr"] = h1_gap / pd.to_numeric(out.get("signal_atr_14", out.get("signal_atr")), errors="coerce")

    out["b_buy_hour"] = out["jst_entry_time"].dt.hour if "jst_entry_time" in out.columns else pd.NA

    # Candidate risk buckets based on the suspicious bands found in combined diagnostics.
    risk = pd.to_numeric(out["b_buy_risk_atr_ratio"], errors="coerce")
    out["risk_band_manual"] = "OTHER"
    out.loc[risk.le(0.928), "risk_band_manual"] = "risk <= 0.928"
    out.loc[risk.gt(0.928) & risk.le(1.241), "risk_band_manual"] = "0.928 < risk <= 1.241"
    out.loc[risk.gt(1.241) & risk.le(2.4), "risk_band_manual"] = "1.241 < risk <= 2.4"
    out.loc[risk.gt(2.4), "risk_band_manual"] = "risk > 2.4"

    macd = pd.to_numeric(out["b_macd_hist_delta_abs"], errors="coerce")
    out["macd_delta_band_manual"] = "OTHER"
    out.loc[macd.le(0.157), "macd_delta_band_manual"] = "macd <= 0.157"
    out.loc[macd.gt(0.157) & macd.le(0.375), "macd_delta_band_manual"] = "0.157 < macd <= 0.375"
    out.loc[macd.gt(0.375) & macd.le(0.742), "macd_delta_band_manual"] = "0.375 < macd <= 0.742"
    out.loc[macd.gt(0.742), "macd_delta_band_manual"] = "macd > 0.742"

    h1_gap = pd.to_numeric(out["h1_ema_gap_side_signed_atr"], errors="coerce")
    out["h1_gap_band_manual"] = "OTHER"
    out.loc[h1_gap.le(1.007), "h1 <= 1.007"] = True
    out.loc[h1_gap.le(1.007), "h1_gap_band_manual"] = "h1 <= 1.007"
    out.loc[h1_gap.gt(1.007) & h1_gap.le(2.285), "h1_gap_band_manual"] = "1.007 < h1 <= 2.285"
    out.loc[h1_gap.gt(2.285) & h1_gap.le(3.371), "h1_gap_band_manual"] = "2.285 < h1 <= 3.371"
    out.loc[h1_gap.gt(3.371), "h1_gap_band_manual"] = "h1 > 3.371"

    out["hour_risk_band"] = out["b_buy_hour"].astype(str) + " / " + out["risk_band_manual"].astype(str)
    out["hour_macd_band"] = out["b_buy_hour"].astype(str) + " / " + out["macd_delta_band_manual"].astype(str)
    out["risk_macd_band"] = out["risk_band_manual"].astype(str) + " / " + out["macd_delta_band_manual"].astype(str)
    return out


def candidate_filter_summary(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    checks: list[tuple[str, pd.Series]] = []
    risk = pd.to_numeric(trades["b_buy_risk_atr_ratio"], errors="coerce")
    macd = pd.to_numeric(trades["b_macd_hist_delta_abs"], errors="coerce")
    h1 = pd.to_numeric(trades["h1_ema_gap_side_signed_atr"], errors="coerce")
    hour = pd.to_numeric(trades["b_buy_hour"], errors="coerce")

    checks.extend(
        [
            ("exclude_hour_22", hour.eq(22)),
            ("exclude_hour_21_22", hour.isin([21, 22])),
            ("exclude_risk_0_928_to_1_241", risk.gt(0.928) & risk.le(1.241)),
            ("exclude_risk_gt_2_4", risk.gt(2.4)),
            ("exclude_risk_gt_2_8", risk.gt(2.8)),
            ("exclude_macd_gt_0_742", macd.gt(0.742)),
            ("exclude_macd_gt_1_0", macd.gt(1.0)),
            ("exclude_h1_gt_3_371", h1.gt(3.371)),
            ("exclude_hour_22_or_macd_gt_0_742", hour.eq(22) | macd.gt(0.742)),
            ("exclude_hour_22_and_macd_gt_0_742", hour.eq(22) & macd.gt(0.742)),
            ("exclude_risk_gt_2_4_or_macd_gt_0_742", risk.gt(2.4) | macd.gt(0.742)),
            ("exclude_risk_gt_2_4_and_macd_gt_0_742", risk.gt(2.4) & macd.gt(0.742)),
        ]
    )

    base = summarize_trades(trades)
    rows: list[dict[str, object]] = []
    for name, remove_mask in checks:
        remove_mask = remove_mask.fillna(False).astype(bool)
        removed = trades[remove_mask]
        kept = trades[~remove_mask]
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
        ["delta_total_r_if_removed", "kept_profit_factor", "kept_trades"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def print_b_buy_diagnostics(b_buy: pd.DataFrame, early_loss_bars: int, long_hold_bars: int) -> None:
    print_dict("B_BUY_summary", summarize_trades(b_buy))

    print_section("B_BUY_by_early_loss", summarize_grouped(b_buy, ["b_buy_is_early_loss"]))
    print_section("B_BUY_by_jst_hour", summarize_grouped(b_buy, ["b_buy_hour"]))
    print_section("B_BUY_by_risk_band_manual", summarize_grouped(b_buy, ["risk_band_manual"]))
    print_section("B_BUY_by_macd_delta_band_manual", summarize_grouped(b_buy, ["macd_delta_band_manual"]))
    print_section("B_BUY_by_h1_gap_band_manual", summarize_grouped(b_buy, ["h1_gap_band_manual"]))
    print_section("B_BUY_by_hour_and_risk_band", summarize_grouped(b_buy, ["b_buy_hour", "risk_band_manual"]))
    print_section("B_BUY_by_hour_and_macd_band", summarize_grouped(b_buy, ["b_buy_hour", "macd_delta_band_manual"]))
    print_section("B_BUY_by_risk_and_macd_band", summarize_grouped(b_buy, ["risk_band_manual", "macd_delta_band_manual"]))

    for col in [
        "b_buy_risk_atr_ratio",
        "b_macd_hist_delta_abs",
        "h1_ema_gap_side_signed_atr",
        "risk_atr_ratio",
        "bars_held",
    ]:
        print_section(f"B_BUY_quartile_by_{col}", summarize_numeric_bins(b_buy, col, bins=4))

    print_section("B_BUY_candidate_filter_summary_post_trade", candidate_filter_summary(b_buy))

    dd = drawdown_segments(add_equity_and_drawdown(b_buy))
    print_section("B_BUY_top_drawdown_segments", dd, max_rows=10)

    streaks = loss_streaks(add_equity_and_drawdown(b_buy))
    print_section("B_BUY_top_loss_streaks", streaks, max_rows=10)

    display_cols = [
        "trade_no",
        "jst_entry_time",
        "entry_price",
        "sl",
        "tp",
        "risk",
        "result",
        "r",
        "bars_held",
        "b_buy_is_early_loss",
        "long_hold_loss",
        "b_buy_risk_atr_ratio",
        "b_macd_hist_delta_abs",
        "h1_ema_gap_side_signed_atr",
        "risk_band_manual",
        "macd_delta_band_manual",
        "h1_gap_band_manual",
        "equity_r",
        "drawdown_r",
    ]
    available = [col for col in display_cols if col in b_buy.columns]
    print_section("B_BUY_all_losses", b_buy[b_buy["result"].eq("loss")][available])
    print_section("B_BUY_early_losses", b_buy[b_buy["b_buy_is_early_loss"]][available])

    print(f"\nearly_loss_definition: loss and bars_held <= {early_loss_bars}")
    print(f"long_hold_loss_definition: loss and bars_held >= {long_hold_bars}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze B BUY failure modes for a combined preset, default gold_ab_v3.")
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
    parser.add_argument("--early-loss-bars", type=int, default=2, help="Default: 2")
    parser.add_argument("--long-hold-bars", type=int, default=20, help="Default: 20")
    parser.add_argument("--save", action="store_true", help="Save B BUY diagnostic trades CSV to data/results.")
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
        print(f"preset: {args.preset}")
        print("target: B BUY executed trades only")
        print(f"B BUY JST hours: {args.b_buy_jst_hours}")
        print(f"B SELL JST hours: {args.b_sell_jst_hours}")
        print(f"B exclude risk_atr_range: {args.b_exclude_risk_atr_range or 'NONE'}")
        print(f"B exclude macd_hist_delta_abs_range: {args.b_exclude_macd_hist_delta_abs_range or 'NONE'}")

        _combined_df, trades = build_and_backtest(args, symbol=symbol)
        b_buy = trades[
            trades["combined_signal_source"].eq("B")
            & trades["side"].eq("BUY")
        ].copy()
        b_buy = add_b_buy_diagnostic_flags(b_buy, early_loss_bars=args.early_loss_bars)

        print_b_buy_diagnostics(b_buy, early_loss_bars=args.early_loss_bars, long_hold_bars=args.long_hold_bars)

        if args.save:
            RESULTS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            out_path = RESULTS_DATA_DIR / f"{symbol}_b_buy_failure_modes_{args.preset}.csv"
            b_buy.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"\nsaved_b_buy_failure_modes: {out_path}")

    print("=" * 120)
    print("B BUY failure mode diagnostics completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
