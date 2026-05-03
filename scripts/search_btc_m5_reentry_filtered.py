from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import pandas as pd

import search_btc_mtf_extra_edges as base
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_M5_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m5.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_H4_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h4.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_m5_reentry_filtered_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btc_m5_reentry_filtered_trades.csv"

DEFAULT_EXCLUDE_ENTRY_HOURS = "8,13,20,21"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 140)
    print(title)
    print("=" * 140)
    print(df.to_string(index=False) if not df.empty else "No data.")


def build_filtered_reentry_rule(df: pd.DataFrame, exclude_entry_hours: set[int]) -> tuple[str, str, pd.Series, pd.Series]:
    original_rules = base.build_rules_m5(df)
    selected = None
    for name, description, buy_mask, sell_mask in original_rules:
        if name == "BTC_SCALP_H1_M5_REENTRY":
            selected = (name, description, buy_mask, sell_mask)
            break
    if selected is None:
        raise RuntimeError("BTC_SCALP_H1_M5_REENTRY rule was not found in base.build_rules_m5().")

    _, description, buy_mask, sell_mask = selected
    entry_hour = df["time"].shift(-1).dt.hour
    hour_ok = ~entry_hour.isin(exclude_entry_hours)
    filtered_buy = buy_mask & hour_ok
    filtered_sell = sell_mask & hour_ok
    rule_name = "BTC_SCALP_H1_M5_REENTRY_FILTERED"
    desc = description + f" / entry_hour除外={sorted(exclude_entry_hours)}"
    return rule_name, desc, filtered_buy, filtered_sell


def main() -> int:
    parser = argparse.ArgumentParser(description="Search filtered BTC M5 reentry candidate using live CSV files.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--exclude-entry-hours", default=DEFAULT_EXCLUDE_ENTRY_HOURS)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--rr-values", default="1.2,1.5,2.0")
    parser.add_argument("--risk-atr-values", default="0.8,1.0,1.2")
    parser.add_argument("--max-bars-values", default="72,144,288")
    parser.add_argument("--cooldown-bars", type=int, default=12)
    parser.add_argument("--start-bar", type=int, default=300)
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--spread-multiplier", type=float, default=1.0)
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    exclude_hours = {int(x.strip()) for x in args.exclude_entry_hours.split(",") if x.strip()}

    rr_values = [float(x.strip()) for x in args.rr_values.split(",") if x.strip()]
    risk_values = [float(x.strip()) for x in args.risk_atr_values.split(",") if x.strip()]
    max_bars_values = [int(x.strip()) for x in args.max_bars_values.split(",") if x.strip()]

    # Patch the base reader so this script works with MQL5 live CSV time format with seconds.
    base.read_ohlc = read_ohlc_live_csv

    m5 = base.add_indicators(base.read_ohlc(m5_csv))
    m15 = base.add_indicators(base.read_ohlc(m15_csv))
    h1 = base.add_indicators(base.read_ohlc(h1_csv))
    h4 = base.add_indicators(base.read_ohlc(h4_csv))
    m5_ctx = base.join_context(m5, [(m15, "m15"), (h1, "h1"), (h4, "h4")])

    rule_base_name, description, buy_mask, sell_mask = build_filtered_reentry_rule(m5_ctx, exclude_hours)

    summaries: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    for rr in rr_values:
        for risk_atr in risk_values:
            for max_bars in max_bars_values:
                rule_name = f"{rule_base_name}_rr{rr}_risk{risk_atr}_max{max_bars}"
                trades = base.backtest_mask(
                    m5_ctx,
                    buy_mask,
                    sell_mask,
                    rule_name=rule_name,
                    rr=rr,
                    risk_atr=risk_atr,
                    max_bars=max_bars,
                    cooldown_bars=args.cooldown_bars,
                    start_bar=args.start_bar,
                    point_size=args.point_size,
                    spread_multiplier=args.spread_multiplier,
                )
                summaries.append(
                    base.summarize_trades(
                        trades,
                        rule_name=rule_name,
                        description=description,
                        base_tf="M5",
                        rr=rr,
                        risk_atr=risk_atr,
                        max_bars=max_bars,
                    )
                )
                if not trades.empty:
                    trades["base_tf"] = "M5"
                    trades["description"] = description
                    frames.append(trades)

    summary = pd.DataFrame(summaries).sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], kind="mergesort")
    trades_out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    write_csv(out_summary, summary)
    write_csv(out_trades, trades_out)

    display_cols = [
        "rule_name",
        "base_tf",
        "trades",
        "buy_trades",
        "sell_trades",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "max_dd_r",
        "trades_per_month",
        "avg_spread_to_risk",
        "description",
    ]

    print("M5 rows:", len(m5), m5_csv, m5["time"].min(), "to", m5["time"].max())
    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print("H4 rows:", len(h4), h4_csv, h4["time"].min(), "to", h4["time"].max())
    print("Exclude entry hours:", sorted(exclude_hours))
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)
    print_table("BTC M5 REENTRY FILTERED SUMMARY", summary[display_cols])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
