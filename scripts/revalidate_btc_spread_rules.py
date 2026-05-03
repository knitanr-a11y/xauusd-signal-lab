from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import search_btc_mtf_extra_edges as mtf
from build_latest_signal_payload_from_csv import add_indicators as add_payload_indicators
from build_latest_signal_payload_from_csv import detect_btc_runner, join_h1
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M5_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m5.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_H4_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h4.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_spread_revalidation_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btc_spread_revalidation_trades.csv"

DEFAULT_EXCLUDE_ENTRY_HOURS = "8,13,20,21"
DEFAULT_FALLBACK_SPREAD_PRICE = 20.0
DEFAULT_PIP_SIZE = 10.0


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_float_list(value: str) -> list[float]:
    return [float(x.strip()) for x in value.split(",") if x.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def parse_int_set(value: str) -> set[int]:
    return {int(x.strip()) for x in value.split(",") if x.strip()}


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def infer_most_frequent_spread_price(
    df: pd.DataFrame,
    *,
    point_size: float,
    round_digits: int,
    exclude_zero: bool = True,
) -> dict[str, Any]:
    if "spread" not in df.columns:
        return {
            "ok": False,
            "reason": "spread column not found",
            "mode_spread_points": None,
            "mode_spread_price": None,
            "sample_count": 0,
            "top_counts": [],
        }
    spread_points = pd.to_numeric(df["spread"], errors="coerce").dropna()
    if exclude_zero:
        spread_points = spread_points[spread_points > 0]
    if spread_points.empty:
        return {
            "ok": False,
            "reason": "no valid spread values",
            "mode_spread_points": None,
            "mode_spread_price": None,
            "sample_count": 0,
            "top_counts": [],
        }
    spread_price = (spread_points.astype(float) * float(point_size)).round(round_digits)
    counts = spread_price.value_counts(dropna=True).sort_values(ascending=False)
    mode_price = float(counts.index[0])
    mode_points = mode_price / float(point_size)
    top_counts = [
        {"spread_price": float(price), "count": int(count)}
        for price, count in counts.head(10).items()
    ]
    return {
        "ok": True,
        "reason": "csv_mode",
        "mode_spread_points": float(mode_points),
        "mode_spread_price": float(mode_price),
        "sample_count": int(len(spread_price)),
        "top_counts": top_counts,
    }


def force_spread_column(df: pd.DataFrame, *, spread_price: float, point_size: float) -> pd.DataFrame:
    out = df.copy()
    if point_size <= 0:
        raise ValueError("point_size must be > 0")
    out["spread"] = float(spread_price) / float(point_size)
    return out


def find_m5_reentry_masks(df: pd.DataFrame, *, exclude_entry_hours: set[int]) -> tuple[pd.Series, pd.Series]:
    rules = mtf.build_rules_m5(df)
    for name, _description, buy_mask, sell_mask in rules:
        if name == "BTC_SCALP_H1_M5_REENTRY":
            entry_hour = df["time"].shift(-1).dt.hour
            hour_ok = ~entry_hour.isin(exclude_entry_hours)
            return buy_mask & hour_ok, sell_mask & hour_ok
    raise RuntimeError("BTC_SCALP_H1_M5_REENTRY not found")


def build_btc_runner_masks(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    buy = []
    sell = []
    for _, row in df.iterrows():
        signal = detect_btc_runner(row)
        buy.append(signal is not None and signal.get("side") == "BUY")
        sell.append(signal is not None and signal.get("side") == "SELL")
    return pd.Series(buy, index=df.index), pd.Series(sell, index=df.index)


def enrich_trades_for_costs(
    trades: pd.DataFrame,
    *,
    scenario: str,
    spread_price: float,
    pip_size: float,
    gross_rr: float,
) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    out = trades.copy()
    out["scenario"] = scenario
    out["assumed_spread_price"] = float(spread_price)
    out["pip_size"] = float(pip_size)
    out["gross_rr"] = float(gross_rr)
    out["risk_pips"] = out["risk"] / pip_size
    out["gross_tp_distance_price"] = out["risk"] * gross_rr
    out["gross_tp_pips"] = out["gross_tp_distance_price"] / pip_size
    out["gross_sl_pips"] = out["risk_pips"]
    out["net_tp_after_spread_price"] = out["gross_tp_distance_price"] - spread_price
    out["sl_with_spread_price"] = out["risk"] + spread_price
    out["net_tp_after_spread_pips"] = out["net_tp_after_spread_price"] / pip_size
    out["sl_with_spread_pips"] = out["sl_with_spread_price"] / pip_size
    out["spread_to_sl_ratio"] = spread_price / out["risk"].replace(0, np.nan)
    out["spread_to_tp_ratio"] = spread_price / out["gross_tp_distance_price"].replace(0, np.nan)
    out["effective_rr_after_spread"] = out["net_tp_after_spread_price"] / out["sl_with_spread_price"].replace(0, np.nan)
    return out


def pf(series: pd.Series) -> float | None:
    r = pd.to_numeric(series, errors="coerce").dropna()
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    if losses <= 0:
        return None
    return float(wins / losses)


def max_dd(series: pd.Series) -> float:
    r = pd.to_numeric(series, errors="coerce").fillna(0.0)
    if r.empty:
        return 0.0
    eq = r.cumsum()
    dd = eq - eq.cummax()
    return float(abs(dd.min()))


def max_losses(results: pd.Series) -> int:
    streak = 0
    best = 0
    for value in results.astype(str):
        if value == "loss":
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return int(best)


def summarize_pair(
    *,
    rule_name: str,
    base_tf: str,
    rr: float,
    risk_atr: float,
    max_bars: int,
    gross: pd.DataFrame,
    net: pd.DataFrame,
    assumed_spread_price: float,
    pip_size: float,
    spread_source: str,
    spread_mode: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "rule_name": rule_name,
        "base_tf": base_tf,
        "rr": rr,
        "risk_atr": risk_atr,
        "max_bars": max_bars,
        "assumed_spread_price": assumed_spread_price,
        "pip_size": pip_size,
        "spread_source": spread_source,
        "spread_mode": spread_mode,
    }
    for prefix, trades in [("gross", gross), ("net", net)]:
        if trades.empty:
            row.update(
                {
                    f"{prefix}_trades": 0,
                    f"{prefix}_wins": 0,
                    f"{prefix}_losses": 0,
                    f"{prefix}_win_rate": None,
                    f"{prefix}_total_r": 0.0,
                    f"{prefix}_avg_r": None,
                    f"{prefix}_pf": None,
                    f"{prefix}_max_dd_r": 0.0,
                    f"{prefix}_max_consecutive_losses": 0,
                }
            )
            continue
        r = pd.to_numeric(trades["r"], errors="coerce")
        wins = int((r > 0).sum())
        losses = int((r < 0).sum())
        row.update(
            {
                f"{prefix}_trades": int(len(trades)),
                f"{prefix}_wins": wins,
                f"{prefix}_losses": losses,
                f"{prefix}_win_rate": float(wins / len(trades)),
                f"{prefix}_total_r": float(r.sum()),
                f"{prefix}_avg_r": float(r.mean()),
                f"{prefix}_pf": pf(r),
                f"{prefix}_max_dd_r": max_dd(r),
                f"{prefix}_max_consecutive_losses": max_losses(trades["result"]),
            }
        )

    cost_source = net if not net.empty else gross
    if cost_source.empty:
        row.update(
            {
                "avg_gross_tp_distance_price": None,
                "avg_gross_sl_distance_price": None,
                "avg_gross_tp_pips": None,
                "avg_gross_sl_pips": None,
                "avg_net_tp_after_spread_price": None,
                "avg_sl_with_spread_price": None,
                "avg_net_tp_after_spread_pips": None,
                "avg_sl_with_spread_pips": None,
                "avg_spread_to_sl_ratio": None,
                "avg_spread_to_tp_ratio": None,
                "avg_effective_rr_after_spread": None,
            }
        )
    else:
        row.update(
            {
                "avg_gross_tp_distance_price": float(cost_source["gross_tp_distance_price"].mean()),
                "avg_gross_sl_distance_price": float(cost_source["risk"].mean()),
                "avg_gross_tp_pips": float(cost_source["gross_tp_pips"].mean()),
                "avg_gross_sl_pips": float(cost_source["gross_sl_pips"].mean()),
                "avg_net_tp_after_spread_price": float(cost_source["net_tp_after_spread_price"].mean()),
                "avg_sl_with_spread_price": float(cost_source["sl_with_spread_price"].mean()),
                "avg_net_tp_after_spread_pips": float(cost_source["net_tp_after_spread_pips"].mean()),
                "avg_sl_with_spread_pips": float(cost_source["sl_with_spread_pips"].mean()),
                "avg_spread_to_sl_ratio": float(cost_source["spread_to_sl_ratio"].mean()),
                "avg_spread_to_tp_ratio": float(cost_source["spread_to_tp_ratio"].mean()),
                "avg_effective_rr_after_spread": float(cost_source["effective_rr_after_spread"].mean()),
            }
        )
    row["pf_drop"] = None if row.get("gross_pf") is None or row.get("net_pf") is None else float(row["gross_pf"] - row["net_pf"])
    row["total_r_drop"] = float(row.get("gross_total_r", 0.0) - row.get("net_total_r", 0.0))
    row["value_width_warning"] = bool(
        (row.get("avg_spread_to_sl_ratio") is not None and row["avg_spread_to_sl_ratio"] >= 0.50)
        or (row.get("avg_effective_rr_after_spread") is not None and row["avg_effective_rr_after_spread"] < 1.0)
        or (row.get("avg_net_tp_after_spread_pips") is not None and row["avg_net_tp_after_spread_pips"] < 5.0)
    )
    return row


def run_case(
    *,
    df: pd.DataFrame,
    buy_mask: pd.Series,
    sell_mask: pd.Series,
    rule_name: str,
    base_tf: str,
    rr: float,
    risk_atr: float,
    max_bars: int,
    cooldown_bars: int,
    start_bar: int,
    point_size: float,
    assumed_spread_price: float,
    pip_size: float,
    spread_source: str,
    spread_mode: str,
) -> tuple[dict[str, Any], pd.DataFrame]:
    gross_df = force_spread_column(df, spread_price=0.0, point_size=point_size)
    net_df = force_spread_column(df, spread_price=assumed_spread_price, point_size=point_size)
    case_name = f"{rule_name}_rr{rr}_risk{risk_atr}_max{max_bars}"
    gross = mtf.backtest_mask(
        gross_df,
        buy_mask,
        sell_mask,
        rule_name=case_name,
        rr=rr,
        risk_atr=risk_atr,
        max_bars=max_bars,
        cooldown_bars=cooldown_bars,
        start_bar=start_bar,
        point_size=point_size,
        spread_multiplier=1.0,
    )
    net = mtf.backtest_mask(
        net_df,
        buy_mask,
        sell_mask,
        rule_name=case_name,
        rr=rr,
        risk_atr=risk_atr,
        max_bars=max_bars,
        cooldown_bars=cooldown_bars,
        start_bar=start_bar,
        point_size=point_size,
        spread_multiplier=1.0,
    )
    gross = enrich_trades_for_costs(gross, scenario="gross_no_spread", spread_price=0.0, pip_size=pip_size, gross_rr=rr)
    net = enrich_trades_for_costs(net, scenario="net_csv_mode_spread", spread_price=assumed_spread_price, pip_size=pip_size, gross_rr=rr)
    summary = summarize_pair(
        rule_name=case_name,
        base_tf=base_tf,
        rr=rr,
        risk_atr=risk_atr,
        max_bars=max_bars,
        gross=gross,
        net=net,
        assumed_spread_price=assumed_spread_price,
        pip_size=pip_size,
        spread_source=spread_source,
        spread_mode=spread_mode,
    )
    combined = pd.concat([gross, net], ignore_index=True) if not gross.empty or not net.empty else pd.DataFrame()
    combined["base_rule_name"] = rule_name
    combined["base_tf"] = base_tf
    combined["spread_source"] = spread_source
    combined["spread_mode"] = spread_mode
    return summary, combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Revalidate BTC rules with CSV-mode spread cost and value-width metrics.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--spread-mode", choices=["csv_mode", "fixed"], default="csv_mode")
    parser.add_argument("--spread-source", choices=["m5", "m15"], default="m5")
    parser.add_argument("--assumed-spread-price", type=float, default=None, help="Used only when --spread-mode fixed, or as fallback if CSV mode cannot be inferred.")
    parser.add_argument("--spread-round-digits", type=int, default=2)
    parser.add_argument("--include-zero-spread-in-mode", action="store_true")
    parser.add_argument("--pip-size", type=float, default=DEFAULT_PIP_SIZE)
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--exclude-entry-hours", default=DEFAULT_EXCLUDE_ENTRY_HOURS)
    parser.add_argument("--rr-values", default="1.5,2.0,2.5,3.0")
    parser.add_argument("--risk-atr-values", default="0.8,1.0,1.2,1.5,2.0,2.5,3.0")
    parser.add_argument("--max-bars-values", default="72,144,288")
    parser.add_argument("--cooldown-bars", type=int, default=12)
    parser.add_argument("--start-bar-m5", type=int, default=300)
    parser.add_argument("--start-bar-m15", type=int, default=220)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    exclude_hours = parse_int_set(args.exclude_entry_hours)
    rr_values = parse_float_list(args.rr_values)
    risk_values = parse_float_list(args.risk_atr_values)
    max_bars_values = parse_int_list(args.max_bars_values)

    m5_raw = read_ohlc_live_csv(m5_csv)
    m15_raw = read_ohlc_live_csv(m15_csv)
    h1_raw = read_ohlc_live_csv(h1_csv)
    h4_raw = read_ohlc_live_csv(h4_csv)

    spread_source_df = m5_raw if args.spread_source == "m5" else m15_raw
    spread_info = infer_most_frequent_spread_price(
        spread_source_df,
        point_size=args.point_size,
        round_digits=args.spread_round_digits,
        exclude_zero=not args.include_zero_spread_in_mode,
    )
    fallback_spread = DEFAULT_FALLBACK_SPREAD_PRICE if args.assumed_spread_price is None else float(args.assumed_spread_price)
    if args.spread_mode == "csv_mode" and spread_info["ok"]:
        assumed_spread_price = float(spread_info["mode_spread_price"])
        effective_spread_mode = "csv_mode"
    elif args.spread_mode == "csv_mode":
        assumed_spread_price = fallback_spread
        effective_spread_mode = f"csv_mode_failed_fallback_fixed:{spread_info['reason']}"
    else:
        assumed_spread_price = fallback_spread
        effective_spread_mode = "fixed"

    # M5 context for BTC_SCALP_H1_M5_REENTRY_FILTERED.
    m5 = mtf.add_indicators(m5_raw)
    m15_mtf = mtf.add_indicators(m15_raw)
    h1_mtf = mtf.add_indicators(h1_raw)
    h4_mtf = mtf.add_indicators(h4_raw)
    m5_ctx = mtf.join_context(m5, [(m15_mtf, "m15"), (h1_mtf, "h1"), (h4_mtf, "h4")])
    m5_buy, m5_sell = find_m5_reentry_masks(m5_ctx, exclude_entry_hours=exclude_hours)

    # M15 context for BTC_RUNNER_RR2_RISK1.
    m15_payload = add_payload_indicators(m15_raw)
    h1_payload = add_payload_indicators(h1_raw)
    runner_df = join_h1(m15_payload, h1_payload)
    runner_buy, runner_sell = build_btc_runner_masks(runner_df)

    summaries: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []

    for rr in rr_values:
        for risk_atr in risk_values:
            for max_bars in max_bars_values:
                summary, trades = run_case(
                    df=m5_ctx,
                    buy_mask=m5_buy,
                    sell_mask=m5_sell,
                    rule_name="BTC_SCALP_H1_M5_REENTRY_FILTERED",
                    base_tf="M5",
                    rr=rr,
                    risk_atr=risk_atr,
                    max_bars=max_bars,
                    cooldown_bars=args.cooldown_bars,
                    start_bar=args.start_bar_m5,
                    point_size=args.point_size,
                    assumed_spread_price=assumed_spread_price,
                    pip_size=args.pip_size,
                    spread_source=args.spread_source,
                    spread_mode=effective_spread_mode,
                )
                summaries.append(summary)
                if not trades.empty:
                    trade_frames.append(trades)

    runner_rr_values = sorted(set([2.0] + rr_values))
    runner_risk_values = sorted(set([1.0, 1.5, 2.0, 2.5, 3.0]))
    for rr in runner_rr_values:
        for risk_atr in runner_risk_values:
            for max_bars in max_bars_values:
                summary, trades = run_case(
                    df=runner_df,
                    buy_mask=runner_buy,
                    sell_mask=runner_sell,
                    rule_name="BTC_RUNNER_RR2_RISK1_REVALIDATED",
                    base_tf="M15",
                    rr=rr,
                    risk_atr=risk_atr,
                    max_bars=max_bars,
                    cooldown_bars=args.cooldown_bars,
                    start_bar=args.start_bar_m15,
                    point_size=args.point_size,
                    assumed_spread_price=assumed_spread_price,
                    pip_size=args.pip_size,
                    spread_source=args.spread_source,
                    spread_mode=effective_spread_mode,
                )
                summaries.append(summary)
                if not trades.empty:
                    trade_frames.append(trades)

    summary_df = pd.DataFrame(summaries)
    if not summary_df.empty:
        for key, value in {
            "spread_mode": effective_spread_mode,
            "spread_source": args.spread_source,
            "spread_sample_count": spread_info.get("sample_count", 0),
            "mode_spread_points": spread_info.get("mode_spread_points"),
            "mode_spread_price": spread_info.get("mode_spread_price"),
            "spread_top_counts": str(spread_info.get("top_counts", [])),
        }.items():
            summary_df[key] = value
        summary_df = summary_df.sort_values(
            ["value_width_warning", "net_pf", "net_total_r", "avg_effective_rr_after_spread", "net_trades"],
            ascending=[True, False, False, False, False],
            kind="mergesort",
        )
    trades_df = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    if not trades_df.empty:
        trades_df["spread_mode"] = effective_spread_mode
        trades_df["spread_source"] = args.spread_source
        trades_df["mode_spread_price"] = spread_info.get("mode_spread_price")

    write_csv(out_summary, summary_df)
    write_csv(out_trades, trades_df)

    display_cols = [
        "rule_name",
        "base_tf",
        "assumed_spread_price",
        "spread_mode",
        "net_trades",
        "net_win_rate",
        "net_total_r",
        "net_avg_r",
        "net_pf",
        "gross_pf",
        "pf_drop",
        "net_max_dd_r",
        "net_max_consecutive_losses",
        "avg_gross_tp_pips",
        "avg_gross_sl_pips",
        "avg_net_tp_after_spread_pips",
        "avg_sl_with_spread_pips",
        "avg_spread_to_sl_ratio",
        "avg_effective_rr_after_spread",
        "value_width_warning",
    ]
    print("Project root:", PROJECT_ROOT)
    print("M5 CSV:", m5_csv)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("H4 CSV:", h4_csv)
    print("Spread mode:", effective_spread_mode)
    print("Spread source:", args.spread_source)
    print("CSV spread mode info:", spread_info)
    print("Assumed spread price used:", assumed_spread_price)
    print("Pip size:", args.pip_size)
    print("Exclude entry hours:", sorted(exclude_hours))
    print("M5 rows:", len(m5_ctx), "M5 filtered raw signals:", int((m5_buy | m5_sell).sum()))
    print("M15 rows:", len(runner_df), "BTC RUNNER raw signals:", int((runner_buy | runner_sell).sum()))
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)
    print("\nTop spread-aware candidates:")
    print(summary_df[display_cols].head(30).to_string(index=False) if not summary_df.empty else "No summary.")
    print("\nOriginal-like rows to inspect:")
    mask = summary_df["rule_name"].astype(str).str.contains("risk0.8_max72|risk1.0_max72", regex=True, na=False)
    print(summary_df.loc[mask, display_cols].head(40).to_string(index=False) if not summary_df.empty and mask.any() else "No original-like rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
