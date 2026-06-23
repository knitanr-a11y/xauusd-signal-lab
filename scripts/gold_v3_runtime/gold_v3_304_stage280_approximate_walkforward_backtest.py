#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

from gold_v3_289_feature_core import GOLD_FILES, read_candles
from gold_v3_298_stage280_model_variant_diagnostic import prepare
from gold_v3_299_stage280_wick_weight_diagnostic import target_series
from gold_v3_301_stage280_feature_contract_diagnostic import (
    PARAM_SETS,
    QUANTILES,
    build_variant_frame,
    feature_variants,
)

YEARS = (2024, 2025, 2026)
TP_ATR = 1.75
SL_ATR = 1.0
MAX_HOLD_MINUTES = 360
TRIGGER_WAIT_MINUTES = 60
MIN_YEAR_TRADES = 4
MIN_TOTAL_TRADES = 18


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--top", type=int, default=100)
    return parser.parse_args()


def profit_factor(values: np.ndarray) -> float | None:
    positive = float(values[values > 0].sum()) if len(values) else 0.0
    negative = float(-values[values < 0].sum()) if len(values) else 0.0
    if negative > 0:
        return positive / negative
    if positive > 0:
        return None
    return 0.0


def max_drawdown(values: np.ndarray) -> float:
    if not len(values):
        return 0.0
    equity = np.concatenate(([0.0], np.cumsum(values, dtype=float)))
    peaks = np.maximum.accumulate(equity)
    return float(np.max(peaks - equity))


def summarize_trades(trades: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda row: (row["entry_dt"], row["decision_dt"]))
    gross = np.asarray([float(row["gross_pnl"]) for row in ordered], dtype=float)
    net = np.asarray([float(row["spread_adjusted_pnl"]) for row in ordered], dtype=float)
    gross_r = np.asarray([float(row["gross_r"]) for row in ordered], dtype=float)
    net_r = np.asarray([float(row["spread_adjusted_r"]) for row in ordered], dtype=float)
    wins = int((net > 0).sum())
    losses = int((net < 0).sum())
    positive_pnl = float(net[net > 0].sum()) if len(net) else 0.0
    largest_win = float(net.max()) if len(net) else 0.0
    concentration = largest_win / positive_pnl if positive_pnl > 0 else 0.0
    return {
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "flats": int(len(ordered) - wins - losses),
        "win_rate": float(wins / len(ordered)) if ordered else 0.0,
        "tp": int(sum(row["exit_reason"] == "TP" for row in ordered)),
        "sl": int(sum(row["exit_reason"] == "SL" for row in ordered)),
        "time": int(sum(row["exit_reason"] == "TIME" for row in ordered)),
        "gross_total_usd": float(gross.sum()) if len(gross) else 0.0,
        "spread_adjusted_total_usd": float(net.sum()) if len(net) else 0.0,
        "gross_avg_usd": float(gross.mean()) if len(gross) else 0.0,
        "spread_adjusted_avg_usd": float(net.mean()) if len(net) else 0.0,
        "gross_profit_factor": profit_factor(gross),
        "spread_adjusted_profit_factor": profit_factor(net),
        "gross_total_r": float(gross_r.sum()) if len(gross_r) else 0.0,
        "spread_adjusted_total_r": float(net_r.sum()) if len(net_r) else 0.0,
        "gross_max_drawdown_usd": max_drawdown(gross),
        "spread_adjusted_max_drawdown_usd": max_drawdown(net),
        "gross_max_drawdown_r": max_drawdown(gross_r),
        "spread_adjusted_max_drawdown_r": max_drawdown(net_r),
        "largest_win_share_of_positive_pnl": float(concentration),
        "first_entry_dt": str(ordered[0]["entry_dt"]) if ordered else None,
        "last_exit_dt": str(ordered[-1]["exit_dt"]) if ordered else None,
    }


def non_overlapping(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    active_until = pd.Timestamp.min
    for row in sorted(
        trades,
        key=lambda item: (
            item["entry_dt"],
            -item["ml_score"],
            item["decision_dt"],
        ),
    ):
        entry = pd.Timestamp(row["entry_dt"])
        if entry < active_until:
            continue
        kept.append(row)
        active_until = pd.Timestamp(row["exit_dt"])
    return kept


def deduplicate(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[pd.Timestamp, dict[str, Any]] = {}
    for row in trades:
        entry = pd.Timestamp(row["entry_dt"])
        current = best.get(entry)
        if current is None or float(row["ml_score"]) > float(current["ml_score"]):
            best[entry] = row
    return sorted(best.values(), key=lambda item: (item["entry_dt"], item["decision_dt"]))


def build_market_arrays(candle_dir: Path) -> dict[str, Any]:
    m5 = read_candles(
        candle_dir / GOLD_FILES["M5"],
        None,
        timeframe="M5",
        require_spread=True,
    ).copy()
    m1 = read_candles(
        candle_dir / GOLD_FILES["M1"],
        None,
        timeframe="M1",
        require_spread=True,
    ).copy()
    m5_range = (m5.high - m5.low).to_numpy(float)
    m5_body = np.divide(
        (m5.close - m5.open).to_numpy(float),
        m5_range,
        out=np.zeros(len(m5), dtype=float),
        where=m5_range > 0,
    )
    return {
        "m5": m5,
        "m5_time": m5.time.to_numpy("datetime64[ns]"),
        "m5_open": m5.open.to_numpy(float),
        "m5_high": m5.high.to_numpy(float),
        "m5_close": m5.close.to_numpy(float),
        "m5_spread": m5.spread.to_numpy(float),
        "m5_body": m5_body,
        "m1": m1,
        "m1_time": m1.time.to_numpy("datetime64[ns]"),
        "m1_high": m1.high.to_numpy(float),
        "m1_low": m1.low.to_numpy(float),
        "m1_close": m1.close.to_numpy(float),
    }


def simulate_long(
    decision_dt: pd.Timestamp,
    atr: float,
    market: dict[str, Any],
) -> dict[str, Any] | None:
    if not math.isfinite(atr) or atr <= 0:
        return None
    m5_time = market["m5_time"]
    start = max(
        int(np.searchsorted(m5_time, np.datetime64(decision_dt), side="left")),
        6,
    )
    limit = np.datetime64(
        decision_dt + pd.Timedelta(minutes=TRIGGER_WAIT_MINUTES)
    )
    end = min(
        int(np.searchsorted(m5_time, limit, side="left")),
        len(m5_time) - 1,
    )
    trigger_index: int | None = None
    for index in range(start, end):
        passed = (
            market["m5_close"][index]
            > market["m5_high"][index - 6:index].max()
            and market["m5_body"][index] >= 0.20
        )
        if passed:
            trigger_index = index
            break
    if trigger_index is None:
        return None
    entry_index = trigger_index + 1
    if entry_index >= len(m5_time):
        return None
    trigger_dt = pd.Timestamp(m5_time[trigger_index])
    entry_dt = pd.Timestamp(m5_time[entry_index])
    if entry_dt != trigger_dt + pd.Timedelta(minutes=5):
        return None
    entry_price = float(market["m5_open"][entry_index])
    entry_spread = max(float(market["m5_spread"][entry_index]), 0.0)
    tp_price = entry_price + TP_ATR * atr
    sl_price = entry_price - SL_ATR * atr

    m1_time = market["m1_time"]
    first = int(np.searchsorted(m1_time, np.datetime64(entry_dt), side="left"))
    horizon = entry_dt + pd.Timedelta(minutes=MAX_HOLD_MINUTES)
    last_exclusive = int(
        np.searchsorted(m1_time, np.datetime64(horizon), side="left")
    )
    if first >= len(m1_time) or pd.Timestamp(m1_time[first]) != entry_dt:
        return None
    if (
        last_exclusive <= first
        or last_exclusive - first < MAX_HOLD_MINUTES - 30
    ):
        return None
    expected_last = horizon - pd.Timedelta(minutes=1)
    if pd.Timestamp(m1_time[last_exclusive - 1]) < expected_last:
        return None

    exit_reason = "TIME"
    exit_price = float(market["m1_close"][last_exclusive - 1])
    exit_dt = pd.Timestamp(m1_time[last_exclusive - 1]) + pd.Timedelta(minutes=1)
    for index in range(first, last_exclusive):
        hit_sl = float(market["m1_low"][index]) <= sl_price
        hit_tp = float(market["m1_high"][index]) >= tp_price
        if hit_sl:
            exit_reason = "SL"
            exit_price = sl_price
            exit_dt = pd.Timestamp(m1_time[index]) + pd.Timedelta(minutes=1)
            break
        if hit_tp:
            exit_reason = "TP"
            exit_price = tp_price
            exit_dt = pd.Timestamp(m1_time[index]) + pd.Timedelta(minutes=1)
            break

    gross_pnl = exit_price - entry_price
    spread_adjusted = gross_pnl - entry_spread
    return {
        "decision_dt": pd.Timestamp(decision_dt),
        "trigger_dt": trigger_dt,
        "entry_dt": entry_dt,
        "exit_dt": exit_dt,
        "entry_price": entry_price,
        "entry_spread": entry_spread,
        "atr_entry": float(atr),
        "tp_price": float(tp_price),
        "sl_price": float(sl_price),
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "gross_pnl": float(gross_pnl),
        "spread_adjusted_pnl": float(spread_adjusted),
        "gross_r": float(gross_pnl / atr),
        "spread_adjusted_r": float(spread_adjusted / atr),
    }


def precompute_outcomes(
    ctx: pd.DataFrame,
    market: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    test_rows = ctx[
        ctx.h4_trend.eq(-1)
        & ctx.time.ge(f"{min(YEARS)}-01-01")
        & ctx.time.lt(f"{max(YEARS) + 1}-01-01")
    ]
    outcomes: dict[int, dict[str, Any]] = {}
    for index, row in test_rows.iterrows():
        result = simulate_long(
            pd.Timestamp(row.time),
            float(row.atr_prev),
            market,
        )
        if result is not None:
            outcomes[int(index)] = result
    return outcomes, {
        "h4_down_decision_rows": int(len(test_rows)),
        "triggered_and_fully_resolved_rows": int(len(outcomes)),
        "latest_m1_time": str(market["m1"].time.max()),
        "latest_m5_time": str(market["m5"].time.max()),
    }


def year_windows(year: int) -> dict[str, pd.Timestamp]:
    test_start = pd.Timestamp(f"{year}-01-01")
    test_end = pd.Timestamp(f"{year + 1}-01-01")
    cal_start = test_start - pd.DateOffset(months=6)
    fit_start = cal_start - pd.DateOffset(months=18)
    return {
        "fit_start": fit_start,
        "cal_start": cal_start,
        "test_start": test_start,
        "test_end": test_end,
    }


def fit_and_backtest_year(
    ctx: pd.DataFrame,
    frame: pd.DataFrame,
    target: pd.Series,
    outcomes: dict[int, dict[str, Any]],
    params_spec: dict[str, Any],
    year: int,
) -> dict[str, Any]:
    window = year_windows(year)
    fit = (
        ctx.future_valid
        & ctx.time.ge(window["fit_start"])
        & ctx.time.lt(window["cal_start"])
    )
    cal = (
        ctx.future_valid
        & ctx.time.ge(window["cal_start"])
        & ctx.time.lt(window["test_start"])
    )
    test = (
        ctx.h4_trend.eq(-1)
        & ctx.time.ge(window["test_start"])
        & ctx.time.lt(window["test_end"])
    )
    result: dict[str, Any] = {
        "year": year,
        "fit_start": str(window["fit_start"]),
        "cal_start": str(window["cal_start"]),
        "test_start": str(window["test_start"]),
        "test_end_exclusive": str(window["test_end"]),
        "fit_n": int(fit.sum()),
        "cal_n": int(cal.sum()),
        "positive_fit": int(target.loc[fit].sum()),
        "positive_cal": int(target.loc[cal].sum()),
        "test_decision_n": int(test.sum()),
        "status": "READY",
        "thresholds": {},
    }
    if (
        fit.sum() == 0
        or cal.sum() == 0
        or target.loc[fit].nunique() < 2
    ):
        result["status"] = "SKIPPED_INSUFFICIENT_TRAINING_POPULATION"
        return result

    params = {
        key: value
        for key, value in params_spec.items()
        if key != "name"
    }
    params.update({"objective": "binary", "n_jobs": 1, "verbosity": -1})
    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], target.loc[fit])
    cal_scores = model.predict_proba(frame.loc[cal])[:, 1]
    test_index = ctx.index[test]
    test_scores = model.predict_proba(frame.loc[test_index])[:, 1]
    score_by_index = dict(
        zip(
            (int(index) for index in test_index),
            (float(value) for value in test_scores),
        )
    )

    for quantile_name, quantile in QUANTILES.items():
        threshold = float(np.quantile(cal_scores, quantile))
        selected_indices = [
            index
            for index, score in score_by_index.items()
            if score >= threshold
        ]
        trades: list[dict[str, Any]] = []
        for index in selected_indices:
            template = outcomes.get(index)
            if template is None:
                continue
            trade = dict(template)
            trade["ml_score"] = score_by_index[index]
            trade["context_index"] = index
            trade["year"] = year
            trades.append(trade)
        deduped = deduplicate(trades)
        portfolio = non_overlapping(deduped)
        result["thresholds"][quantile_name] = {
            "threshold": threshold,
            "selected_decisions": int(len(selected_indices)),
            "triggered_resolved_raw": int(len(trades)),
            "raw": summarize_trades(trades),
            "dedup": summarize_trades(deduped),
            "standalone_non_overlap": summarize_trades(portfolio),
            "standalone_non_overlap_trades": portfolio,
        }
    return result


def aggregate_configuration(
    variant_name: str,
    params_name: str,
    feature_count: int,
    yearly: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for quantile_name in QUANTILES:
        all_trades: list[dict[str, Any]] = []
        per_year: dict[str, Any] = {}
        valid_years = 0
        for year_result in yearly:
            year = str(year_result["year"])
            threshold_result = year_result.get("thresholds", {}).get(
                quantile_name
            )
            if not threshold_result:
                per_year[year] = {"status": year_result["status"]}
                continue
            valid_years += 1
            trades = threshold_result["standalone_non_overlap_trades"]
            all_trades.extend(trades)
            per_year[year] = {
                "status": year_result["status"],
                "threshold": threshold_result["threshold"],
                "selected_decisions": threshold_result["selected_decisions"],
                "triggered_resolved_raw": threshold_result[
                    "triggered_resolved_raw"
                ],
                "standalone_non_overlap": threshold_result[
                    "standalone_non_overlap"
                ],
            }
        metrics = summarize_trades(all_trades)
        year_net_r = [
            float(value["standalone_non_overlap"]["spread_adjusted_total_r"])
            for value in per_year.values()
            if value.get("standalone_non_overlap")
        ]
        year_trades = [
            int(value["standalone_non_overlap"]["trades"])
            for value in per_year.values()
            if value.get("standalone_non_overlap")
        ]
        pf = metrics["spread_adjusted_profit_factor"]
        pf_for_score = (
            float(pf)
            if pf is not None
            else (5.0 if metrics["spread_adjusted_total_r"] > 0 else 0.0)
        )
        worst_year_r = min(year_net_r) if year_net_r else 0.0
        minimum_year_trades = min(year_trades) if year_trades else 0
        robust_score = (
            metrics["spread_adjusted_total_r"]
            - metrics["spread_adjusted_max_drawdown_r"]
            + 0.25 * worst_year_r
            + 0.05 * min(metrics["trades"], 60)
            + 0.25 * min(pf_for_score, 3.0)
        )
        research_pass = bool(
            valid_years == len(YEARS)
            and metrics["trades"] >= MIN_TOTAL_TRADES
            and minimum_year_trades >= MIN_YEAR_TRADES
            and metrics["spread_adjusted_total_r"] > 0
            and pf_for_score >= 1.20
            and metrics["spread_adjusted_max_drawdown_r"] <= 8.0
            and worst_year_r >= -2.0
            and metrics["largest_win_share_of_positive_pnl"] <= 0.55
        )
        rows.append(
            {
                "model_key": (
                    f"{variant_name}|{params_name}|{quantile_name}"
                ),
                "feature_variant": variant_name,
                "feature_count": int(feature_count),
                "param_set": params_name,
                "quantile": quantile_name,
                "aggregate": metrics,
                "valid_years": valid_years,
                "minimum_year_trades": minimum_year_trades,
                "worst_year_spread_adjusted_r": float(worst_year_r),
                "robust_score": float(robust_score),
                "research_pass": research_pass,
                "yearly": per_year,
            }
        )
    return rows


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir
        / "stage304_stage280_approximate_walkforward_backtest.json"
    )
    ctx, features = prepare(candle_dir)
    eligible = ctx[ctx.h4_trend.ne(0)].copy()
    target = target_series(eligible)
    variants = feature_variants(features)
    market = build_market_arrays(candle_dir)
    outcomes, outcome_summary = precompute_outcomes(eligible, market)

    leaderboard: list[dict[str, Any]] = []
    evaluated_fits = 0
    for variant_name, columns in variants.items():
        frame = build_variant_frame(eligible, columns)
        for params_spec in PARAM_SETS:
            yearly = []
            for year in YEARS:
                yearly.append(
                    fit_and_backtest_year(
                        eligible,
                        frame,
                        target,
                        outcomes,
                        params_spec,
                        year,
                    )
                )
                evaluated_fits += 1
            leaderboard.extend(
                aggregate_configuration(
                    variant_name,
                    params_spec["name"],
                    frame.shape[1],
                    yearly,
                )
            )

    leaderboard.sort(
        key=lambda row: (
            not row["research_pass"],
            -row["robust_score"],
            -row["aggregate"]["spread_adjusted_total_r"],
            row["aggregate"]["spread_adjusted_max_drawdown_r"],
        )
    )
    passes = [row for row in leaderboard if row["research_pass"]]
    top = leaderboard[: max(1, args.top)]

    report = {
        "status": (
            "GOLD_V3_304_STAGE280_APPROXIMATE_WALKFORWARD_BACKTEST_READY"
        ),
        "mode": "AUDIT_ONLY_RESEARCH_NEW_MODEL_EVALUATION",
        "decision": (
            "RESEARCH_CANDIDATES_FOUND"
            if passes
            else "NO_RESEARCH_CANDIDATE_PASSED"
        ),
        "contract": {
            "direction": (
                "LONG_ONLY_WHEN_PRIOR_CLOSED_H4_TREND_IS_DOWN"
            ),
            "score_calibration": "prior six months per test year",
            "fit_window": (
                "18 months before calibration window, available history only"
            ),
            "test_years": list(YEARS),
            "trigger": (
                "M5 close above prior six M5 highs and body_signed >= 0.20 "
                "within 60 minutes"
            ),
            "entry": "next exact M5 open",
            "tp_atr": TP_ATR,
            "sl_atr": SL_ATR,
            "max_holding_minutes": MAX_HOLD_MINUTES,
            "outcome": (
                "M1 first touch; same M1 SL priority; otherwise time exit"
            ),
            "primary_portfolio_view": (
                "standalone max one open position"
            ),
            "spread_adjustment": (
                "entry spread subtracted from gross PnL as a conservative "
                "secondary metric"
            ),
        },
        "search": {
            "feature_variants": len(variants),
            "parameter_sets": len(PARAM_SETS),
            "quantiles": list(QUANTILES),
            "walkforward_years": list(YEARS),
            "evaluated_model_year_fits": evaluated_fits,
            "evaluated_configurations": len(leaderboard),
        },
        "outcome_precompute": outcome_summary,
        "research_gate": {
            "minimum_total_trades": MIN_TOTAL_TRADES,
            "minimum_trades_each_year": MIN_YEAR_TRADES,
            "minimum_spread_adjusted_profit_factor": 1.20,
            "maximum_spread_adjusted_drawdown_r": 8.0,
            "minimum_worst_year_r": -2.0,
            "maximum_largest_win_share": 0.55,
        },
        "research_pass_count": len(passes),
        "research_passes": passes[:50],
        "leaderboard": top,
        "historical_reference_only": {
            "original_candidate_trade_counts_2024_2025_2026": [12, 17, 11],
            "original_2026_integrated_drawdown_usd": 76.20,
            "warning": (
                "reference is not recalculated here because the original "
                "model artifact was not recovered"
            ),
        },
        "promotion": {
            "performed": False,
            "stage280_production_state": "UNCHANGED_BLOCKED",
            "requires_followup": (
                "review walk-forward results, then freeze a new model contract "
                "and rerun parity/CI before any activation"
            ),
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
        "note": (
            "Approximate candidates are evaluated as new research models, "
            "not as recovered copies of the missing Stage280 artifact."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
