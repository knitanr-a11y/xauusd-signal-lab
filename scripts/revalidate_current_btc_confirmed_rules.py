from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from build_latest_btc_mtf_signal_payload_from_csv import (
    add_entry_hour,
    detect_btc_scalp_m5_reentry_filtered,
)
from build_latest_signal_payload_from_csv import detect_btc_runner
from confirmed_time_join import join_context_confirmed, join_h1_confirmed_for_btc_m15
from search_btc_mtf_extra_edges import add_indicators, max_consecutive_losses, max_drawdown_r, profit_factor
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_M5_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m5.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_H4_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h4.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_current_rules_confirmed_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btc_current_rules_confirmed_trades.csv"


@dataclass(frozen=True)
class RuleConfig:
    name: str
    base_tf: str
    rr: float
    risk_atr: float
    max_bars: int
    cooldown_bars: int
    min_start_idx: int
    apply_value_filters: bool


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_int_set(value: str) -> set[int]:
    return {int(x.strip()) for x in str(value).split(",") if x.strip()}


def spread_price(row: pd.Series, *, point_size: float) -> float:
    try:
        return max(0.0, float(row.get("spread", 0.0) or 0.0) * point_size)
    except Exception:
        return 0.0


def effective_value_metrics(*, risk: float, rr: float, spread: float, pip_size: float) -> dict[str, float]:
    gross_tp_price = rr * risk
    gross_sl_price = risk
    net_tp_price = gross_tp_price - spread
    sl_with_spread_price = gross_sl_price + spread
    return {
        "gross_tp_pips": gross_tp_price / pip_size if pip_size > 0 else np.nan,
        "gross_sl_pips": gross_sl_price / pip_size if pip_size > 0 else np.nan,
        "net_tp_after_spread_pips": net_tp_price / pip_size if pip_size > 0 else np.nan,
        "sl_with_spread_pips": sl_with_spread_price / pip_size if pip_size > 0 else np.nan,
        "spread_to_sl_ratio": spread / gross_sl_price if gross_sl_price > 0 else np.nan,
        "effective_rr_after_spread": net_tp_price / sl_with_spread_price if sl_with_spread_price > 0 else np.nan,
    }


def passes_value_filters(metrics: dict[str, float], *, min_net_tp_pips: float, max_spread_to_sl_ratio: float, min_effective_rr: float) -> bool:
    return (
        float(metrics.get("net_tp_after_spread_pips", np.nan)) >= min_net_tp_pips
        and float(metrics.get("spread_to_sl_ratio", np.nan)) < max_spread_to_sl_ratio
        and float(metrics.get("effective_rr_after_spread", np.nan)) >= min_effective_rr
    )


def first_touch_trade(
    df: pd.DataFrame,
    *,
    signal_idx: int,
    side: str,
    config: RuleConfig,
    point_size: float,
    pip_size: float,
    min_net_tp_pips: float,
    max_spread_to_sl_ratio: float,
    min_effective_rr: float,
    inbar_priority: str,
) -> dict[str, Any] | None:
    entry_idx = signal_idx + 1
    if entry_idx >= len(df):
        return None

    signal_row = df.iloc[signal_idx]
    entry_row = df.iloc[entry_idx]
    entry_mid = float(entry_row["open"])
    spread = spread_price(entry_row, point_size=point_size)
    atr = float(signal_row.get("atr14", np.nan))
    if not np.isfinite(entry_mid) or not np.isfinite(atr) or atr <= 0:
        return None

    risk = atr * config.risk_atr
    if risk <= 0:
        return None

    metrics = effective_value_metrics(risk=risk, rr=config.rr, spread=spread, pip_size=pip_size)
    if config.apply_value_filters and not passes_value_filters(
        metrics,
        min_net_tp_pips=min_net_tp_pips,
        max_spread_to_sl_ratio=max_spread_to_sl_ratio,
        min_effective_rr=min_effective_rr,
    ):
        return None

    side = str(side).upper()
    if side == "BUY":
        entry = entry_mid + spread / 2.0
        sl = entry - risk
        tp = entry + config.rr * risk
    else:
        entry = entry_mid - spread / 2.0
        sl = entry + risk
        tp = entry - config.rr * risk

    exit_idx = min(entry_idx + config.max_bars, len(df) - 1)
    exit_reason = "timeout"
    exit_price = float(df.at[exit_idx, "close"])
    exit_spread = spread_price(df.iloc[exit_idx], point_size=point_size)
    exit_price = exit_price - exit_spread / 2.0 if side == "BUY" else exit_price + exit_spread / 2.0
    r_value = (exit_price - entry) / risk if side == "BUY" else (entry - exit_price) / risk

    for j in range(entry_idx, min(entry_idx + config.max_bars, len(df) - 1) + 1):
        row = df.iloc[j]
        current_spread = spread_price(row, point_size=point_size)
        high_mid = float(row["high"])
        low_mid = float(row["low"])
        bid_high = high_mid - current_spread / 2.0
        bid_low = low_mid - current_spread / 2.0
        ask_high = high_mid + current_spread / 2.0
        ask_low = low_mid + current_spread / 2.0

        if side == "BUY":
            hit_tp = bid_high >= tp
            hit_sl = bid_low <= sl
        else:
            hit_tp = ask_low <= tp
            hit_sl = ask_high >= sl

        if hit_tp and hit_sl:
            exit_idx = j
            if inbar_priority.upper() == "TP":
                exit_price = tp
                exit_reason = "tp_same_bar"
                r_value = config.rr
            else:
                exit_price = sl
                exit_reason = "sl_same_bar"
                r_value = -1.0
            break
        if hit_sl:
            exit_idx = j
            exit_price = sl
            exit_reason = "sl"
            r_value = -1.0
            break
        if hit_tp:
            exit_idx = j
            exit_price = tp
            exit_reason = "tp"
            r_value = config.rr
            break

    return {
        "rule_name": config.name,
        "base_tf": config.base_tf,
        "side": side,
        "signal_idx": signal_idx,
        "signal_time": df.at[signal_idx, "time"],
        "entry_idx": entry_idx,
        "entry_time": df.at[entry_idx, "time"],
        "exit_idx": exit_idx,
        "exit_time": df.at[exit_idx, "time"],
        "entry_price": entry,
        "entry_mid_price": entry_mid,
        "entry_spread_price": spread,
        "sl": sl,
        "tp": tp,
        "risk": risk,
        "rr": config.rr,
        "risk_atr": config.risk_atr,
        "max_bars": config.max_bars,
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "bars_held": exit_idx - entry_idx + 1,
        "r": float(r_value),
        "result": "win" if r_value > 0 else "loss" if r_value < 0 else "breakeven",
        "entry_hour": int(pd.Timestamp(df.at[entry_idx, "time"]).hour),
        **metrics,
    }


def summarize(trades: pd.DataFrame, config: RuleConfig) -> dict[str, Any]:
    if trades.empty:
        return {
            "rule_name": config.name,
            "base_tf": config.base_tf,
            "rr": config.rr,
            "risk_atr": config.risk_atr,
            "max_bars": config.max_bars,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "max_dd_r": 0.0,
            "trades_per_month": None,
            "avg_net_tp_pips": None,
            "avg_spread_to_sl_ratio": None,
            "avg_effective_rr_after_spread": None,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    span_days = max(1, (pd.Timestamp(trades["entry_time"].max()) - pd.Timestamp(trades["entry_time"].min())).days)
    months = max(1.0, span_days / 30.4375)
    return {
        "rule_name": config.name,
        "base_tf": config.base_tf,
        "rr": config.rr,
        "risk_atr": config.risk_atr,
        "max_bars": config.max_bars,
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(trades)),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(trades["result"]),
        "max_dd_r": max_drawdown_r(r),
        "trades_per_month": float(len(trades) / months),
        "avg_net_tp_pips": float(pd.to_numeric(trades["net_tp_after_spread_pips"], errors="coerce").mean()),
        "avg_spread_to_sl_ratio": float(pd.to_numeric(trades["spread_to_sl_ratio"], errors="coerce").mean()),
        "avg_effective_rr_after_spread": float(pd.to_numeric(trades["effective_rr_after_spread"], errors="coerce").mean()),
    }


def backtest_current_rule(df: pd.DataFrame, config: RuleConfig, *, exclude_entry_hours: set[int], point_size: float, pip_size: float, min_net_tp_pips: float, max_spread_to_sl_ratio: float, min_effective_rr: float, inbar_priority: str) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    blocked_until = -1
    for idx in range(config.min_start_idx, len(df) - 1):
        if idx <= blocked_until:
            continue
        row = df.iloc[idx]
        signal = None
        if config.name == "BTC_RUNNER_RR2_RISK1_CONFIRMED":
            signal = detect_btc_runner(row)
            if signal is None or signal.get("strategy_label") != "BTC_RUNNER_RR2_RISK1":
                continue
        elif config.name == "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8_CONFIRMED":
            signal = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
            if signal is None or signal.get("strategy_label") != "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8":
                continue
        else:
            raise ValueError(f"Unsupported rule: {config.name}")

        trade = first_touch_trade(
            df,
            signal_idx=idx,
            side=str(signal.get("side")),
            config=config,
            point_size=point_size,
            pip_size=pip_size,
            min_net_tp_pips=min_net_tp_pips,
            max_spread_to_sl_ratio=max_spread_to_sl_ratio,
            min_effective_rr=min_effective_rr,
            inbar_priority=inbar_priority,
        )
        if trade is None:
            continue
        trades.append(trade)
        blocked_until = int(trade["exit_idx"]) + config.cooldown_bars
    return pd.DataFrame(trades)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Revalidate current BTC adopted/candidate rules with confirmed-time MTF joins and spread-aware execution.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--btc-pip-size", type=float, default=10.0)
    parser.add_argument("--min-net-tp-pips", type=float, default=5.0)
    parser.add_argument("--max-spread-to-sl-ratio", type=float, default=0.50)
    parser.add_argument("--min-effective-rr", type=float, default=1.0)
    parser.add_argument("--runner-max-bars", type=int, default=288)
    parser.add_argument("--scalp-max-bars", type=int, default=72)
    parser.add_argument("--runner-cooldown-bars", type=int, default=0)
    parser.add_argument("--scalp-cooldown-bars", type=int, default=0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    args = parser.parse_args()

    m5 = add_indicators(read_ohlc_live_csv(resolve_path(args.m5_csv)))
    m15 = add_indicators(read_ohlc_live_csv(resolve_path(args.m15_csv)))
    h1 = add_indicators(read_ohlc_live_csv(resolve_path(args.h1_csv)))
    h4 = add_indicators(read_ohlc_live_csv(resolve_path(args.h4_csv)))
    print("Rows:", "M5", len(m5), "M15", len(m15), "H1", len(h1), "H4", len(h4))
    print("Ranges:")
    for name, df in [("M5", m5), ("M15", m15), ("H1", h1), ("H4", h4)]:
        print(f"  {name}: {df['time'].min()} -> {df['time'].max()}")

    m5_ctx = join_context_confirmed(m5, base_tf="M5", contexts=[(m15, "m15", "M15"), (h1, "h1", "H1"), (h4, "h4", "H4")])
    m5_ctx = add_entry_hour(m5_ctx)
    m15_ctx = join_h1_confirmed_for_btc_m15(m15, h1)

    exclude_hours = parse_int_set(args.exclude_entry_hours)
    configs = [
        RuleConfig(
            name="BTC_RUNNER_RR2_RISK1_CONFIRMED",
            base_tf="M15",
            rr=2.0,
            risk_atr=1.0,
            max_bars=args.runner_max_bars,
            cooldown_bars=args.runner_cooldown_bars,
            min_start_idx=220,
            apply_value_filters=False,
        ),
        RuleConfig(
            name="BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8_CONFIRMED",
            base_tf="M5",
            rr=2.0,
            risk_atr=0.8,
            max_bars=args.scalp_max_bars,
            cooldown_bars=args.scalp_cooldown_bars,
            min_start_idx=300,
            apply_value_filters=True,
        ),
    ]

    all_trades: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []
    for cfg in configs:
        source_df = m15_ctx if cfg.base_tf == "M15" else m5_ctx
        trades = backtest_current_rule(
            source_df,
            cfg,
            exclude_entry_hours=exclude_hours,
            point_size=args.point_size,
            pip_size=args.btc_pip_size,
            min_net_tp_pips=args.min_net_tp_pips,
            max_spread_to_sl_ratio=args.max_spread_to_sl_ratio,
            min_effective_rr=args.min_effective_rr,
            inbar_priority=args.inbar_priority,
        )
        summaries.append(summarize(trades, cfg))
        if not trades.empty:
            all_trades.append(trades)

    summary_df = pd.DataFrame(summaries)
    trades_df = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    write_csv(resolve_path(args.out_summary), summary_df)
    write_csv(resolve_path(args.out_trades), trades_df)

    print("\n" + "=" * 140)
    print("CURRENT BTC RULES CONFIRMED SUMMARY")
    print("=" * 140)
    print(summary_df.to_string(index=False))
    print("\nSaved summary:", resolve_path(args.out_summary))
    print("Saved trades :", resolve_path(args.out_trades))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
