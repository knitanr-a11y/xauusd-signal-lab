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

import gold_v3_304_stage280_approximate_walkforward_backtest as base
from gold_v3_298_stage280_model_variant_diagnostic import prepare
from gold_v3_299_stage280_wick_weight_diagnostic import target_series
from gold_v3_301_stage280_feature_contract_diagnostic import (
    PARAM_SETS,
    build_variant_frame,
    feature_variants,
)

YEARS = (2025, 2026)
FEATURE_VARIANT = "m1_m5_m15_h1__timeframe_grouped"
PARAM_SET = "stage300_near_fixture"
QUANTILES = {
    "q60": 0.60,
    "q65": 0.65,
    "q70": 0.70,
    "q75": 0.75,
    "q80": 0.80,
    "q85": 0.85,
    "q90": 0.90,
}
TP_ATR = 1.75
SL_ATR = 1.0
MAX_HOLD_MINUTES = 360
POINT_SIZE = 0.01

FAMILIES: list[dict[str, Any]] = [
    {"name": "L_BRK6_60_B20", "direction": 1, "kind": "BRK", "lookback": 6, "wait": 60, "body": 0.20},
    {"name": "L_BRK3_60_B15", "direction": 1, "kind": "BRK", "lookback": 3, "wait": 60, "body": 0.15},
    {"name": "L_EMA20_60_B15", "direction": 1, "kind": "EMA20", "lookback": 1, "wait": 60, "body": 0.15},
    {"name": "L_BRK6_120_B15", "direction": 1, "kind": "BRK", "lookback": 6, "wait": 120, "body": 0.15},
    {"name": "S_BRK6_60_B20", "direction": -1, "kind": "BRK", "lookback": 6, "wait": 60, "body": 0.20},
    {"name": "S_BRK3_60_B15", "direction": -1, "kind": "BRK", "lookback": 3, "wait": 60, "body": 0.15},
    {"name": "S_EMA20_60_B15", "direction": -1, "kind": "EMA20", "lookback": 1, "wait": 60, "body": 0.15},
    {"name": "S_BRK6_120_B15", "direction": -1, "kind": "BRK", "lookback": 6, "wait": 120, "body": 0.15},
]

POOLS: dict[str, list[str]] = {
    "ANCHOR_LONG": ["L_BRK6_60_B20"],
    "LONG_FAST": ["L_BRK3_60_B15", "L_EMA20_60_B15"],
    "LONG_CORE": ["L_BRK6_60_B20", "L_BRK3_60_B15", "L_EMA20_60_B15"],
    "LONG_ALL": ["L_BRK6_60_B20", "L_BRK3_60_B15", "L_EMA20_60_B15", "L_BRK6_120_B15"],
    "SHORT_ANCHOR": ["S_BRK6_60_B20"],
    "SHORT_FAST": ["S_BRK3_60_B15", "S_EMA20_60_B15"],
    "SHORT_CORE": ["S_BRK6_60_B20", "S_BRK3_60_B15", "S_EMA20_60_B15"],
    "SHORT_ALL": ["S_BRK6_60_B20", "S_BRK3_60_B15", "S_EMA20_60_B15", "S_BRK6_120_B15"],
    "BOTH_ANCHOR": ["L_BRK6_60_B20", "S_BRK6_60_B20"],
    "BOTH_FAST": ["L_BRK3_60_B15", "L_EMA20_60_B15", "S_BRK3_60_B15", "S_EMA20_60_B15"],
    "BOTH_CORE": ["L_BRK6_60_B20", "L_BRK3_60_B15", "L_EMA20_60_B15", "S_BRK6_60_B20", "S_BRK3_60_B15", "S_EMA20_60_B15"],
    "BOTH_BRK": ["L_BRK6_60_B20", "L_BRK3_60_B15", "L_BRK6_120_B15", "S_BRK6_60_B20", "S_BRK3_60_B15", "S_BRK6_120_B15"],
    "BOTH_ALL": [item["name"] for item in FAMILIES],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    parser.add_argument("--top", type=int, default=200)
    return parser.parse_args()


def year_windows(year: int) -> dict[str, pd.Timestamp]:
    test_start = pd.Timestamp(f"{year}-01-01")
    return {
        "fit_start": test_start - pd.DateOffset(months=24),
        "cal_start": test_start - pd.DateOffset(months=6),
        "test_start": test_start,
        "test_end": pd.Timestamp(f"{year + 1}-01-01"),
    }


def build_market(candle_dir: Path) -> dict[str, Any]:
    market = base.build_market_arrays(candle_dir)
    m5 = market["m5"]
    market["m5_low"] = m5.low.to_numpy(float)
    market["m5_ema20"] = m5.close.ewm(span=20, adjust=False).mean().to_numpy(float)
    return market


def trigger_passed(index: int, family: dict[str, Any], market: dict[str, Any]) -> bool:
    direction = int(family["direction"])
    if direction * float(market["m5_body"][index]) < float(family["body"]):
        return False
    close = float(market["m5_close"][index])
    if family["kind"] == "BRK":
        lookback = int(family["lookback"])
        if direction == 1:
            return close > float(np.max(market["m5_high"][index - lookback:index]))
        return close < float(np.min(market["m5_low"][index - lookback:index]))
    ema = market["m5_ema20"]
    previous_close = float(market["m5_close"][index - 1])
    if direction == 1:
        return close > ema[index] and previous_close <= ema[index - 1] and close > market["m5_high"][index - 1]
    return close < ema[index] and previous_close >= ema[index - 1] and close < market["m5_low"][index - 1]


def simulate(
    decision_dt: pd.Timestamp,
    atr: float,
    family: dict[str, Any],
    market: dict[str, Any],
    point_size: float,
) -> dict[str, Any] | None:
    if not math.isfinite(atr) or atr <= 0:
        return None
    direction = int(family["direction"])
    m5_time = market["m5_time"]
    start = max(
        int(np.searchsorted(m5_time, np.datetime64(decision_dt), side="left")),
        int(family["lookback"]),
        1,
    )
    limit = np.datetime64(decision_dt + pd.Timedelta(minutes=int(family["wait"])))
    end = min(int(np.searchsorted(m5_time, limit, side="left")), len(m5_time) - 1)
    trigger_index = None
    for index in range(start, end):
        if trigger_passed(index, family, market):
            trigger_index = index
            break
    if trigger_index is None:
        return None
    entry_index = trigger_index + 1
    trigger_dt = pd.Timestamp(m5_time[trigger_index])
    entry_dt = pd.Timestamp(m5_time[entry_index])
    if entry_dt != trigger_dt + pd.Timedelta(minutes=5):
        return None

    entry_price = float(market["m5_open"][entry_index])
    spread_points = max(float(market["m5_spread"][entry_index]), 0.0)
    spread_price = spread_points * float(point_size)
    tp_price = entry_price + direction * TP_ATR * atr
    sl_price = entry_price - direction * SL_ATR * atr

    m1_time = market["m1_time"]
    first = int(np.searchsorted(m1_time, np.datetime64(entry_dt), side="left"))
    horizon = entry_dt + pd.Timedelta(minutes=MAX_HOLD_MINUTES)
    last_exclusive = int(np.searchsorted(m1_time, np.datetime64(horizon), side="left"))
    if first >= len(m1_time) or pd.Timestamp(m1_time[first]) != entry_dt:
        return None
    if last_exclusive <= first or last_exclusive - first < MAX_HOLD_MINUTES - 30:
        return None
    if pd.Timestamp(m1_time[last_exclusive - 1]) < horizon - pd.Timedelta(minutes=1):
        return None

    exit_reason = "TIME"
    exit_price = float(market["m1_close"][last_exclusive - 1])
    exit_dt = pd.Timestamp(m1_time[last_exclusive - 1]) + pd.Timedelta(minutes=1)
    for index in range(first, last_exclusive):
        if direction == 1:
            hit_sl = float(market["m1_low"][index]) <= sl_price
            hit_tp = float(market["m1_high"][index]) >= tp_price
        else:
            hit_sl = float(market["m1_high"][index]) >= sl_price
            hit_tp = float(market["m1_low"][index]) <= tp_price
        if hit_sl:
            exit_reason, exit_price = "SL", sl_price
            exit_dt = pd.Timestamp(m1_time[index]) + pd.Timedelta(minutes=1)
            break
        if hit_tp:
            exit_reason, exit_price = "TP", tp_price
            exit_dt = pd.Timestamp(m1_time[index]) + pd.Timedelta(minutes=1)
            break

    gross_pnl = direction * (exit_price - entry_price)
    net_pnl = gross_pnl - spread_price
    return {
        "family": family["name"],
        "direction": "LONG" if direction == 1 else "SHORT",
        "direction_num": direction,
        "decision_dt": pd.Timestamp(decision_dt),
        "trigger_dt": trigger_dt,
        "entry_dt": entry_dt,
        "exit_dt": exit_dt,
        "entry_price": entry_price,
        "entry_spread_points": spread_points,
        "entry_spread_price": spread_price,
        "atr_entry": float(atr),
        "tp_price": float(tp_price),
        "sl_price": float(sl_price),
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "gross_pnl": float(gross_pnl),
        "spread_adjusted_pnl": float(net_pnl),
        "gross_r": float(gross_pnl / atr),
        "spread_adjusted_r": float(net_pnl / atr),
    }


def fit_year(ctx, frame, target, params, year: int) -> dict[str, Any]:
    window = year_windows(year)
    fit = ctx.future_valid & ctx.time.ge(window["fit_start"]) & ctx.time.lt(window["cal_start"])
    cal = ctx.future_valid & ctx.time.ge(window["cal_start"]) & ctx.time.lt(window["test_start"])
    test = ctx.time.ge(window["test_start"]) & ctx.time.lt(window["test_end"])
    result = {
        "year": year,
        "fit_start": str(window["fit_start"]),
        "cal_start": str(window["cal_start"]),
        "test_start": str(window["test_start"]),
        "test_end_exclusive": str(window["test_end"]),
        "fit_n": int(fit.sum()),
        "cal_n": int(cal.sum()),
        "positive_fit": int(target.loc[fit].sum()),
        "positive_cal": int(target.loc[cal].sum()),
        "test_n": int(test.sum()),
    }
    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], target.loc[fit])
    cal_scores = model.predict_proba(frame.loc[cal])[:, 1]
    test_index = ctx.index[test]
    test_scores = model.predict_proba(frame.loc[test_index])[:, 1]
    result["scores"] = {int(index): float(score) for index, score in zip(test_index, test_scores)}
    result["thresholds"] = {name: float(np.quantile(cal_scores, q)) for name, q in QUANTILES.items()}
    return result


def precompute(ctx, market, point_size: float):
    test_rows = ctx[ctx.time.ge("2025-01-01") & ctx.time.lt("2027-01-01")]
    outcomes = {family["name"]: {} for family in FAMILIES}
    for family in FAMILIES:
        rows = test_rows[test_rows.h4_trend.eq(-int(family["direction"]))]
        for index, row in rows.iterrows():
            result = simulate(pd.Timestamp(row.time), float(row.atr_prev), family, market, point_size)
            if result is not None:
                outcomes[family["name"]][int(index)] = result
    metadata = {
        "test_rows": int(len(test_rows)),
        "latest_m1_time": str(market["m1"].time.max()),
        "latest_m5_time": str(market["m5"].time.max()),
        "point_size": point_size,
        "triggered_rows_by_family": {name: len(rows) for name, rows in outcomes.items()},
    }
    return outcomes, metadata


def one_position(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = {}
    for row in trades:
        entry = pd.Timestamp(row["entry_dt"])
        current = best.get(entry)
        if current is None or (float(row["ml_score"]), row["family"]) > (float(current["ml_score"]), current["family"]):
            best[entry] = row
    kept = []
    active_until = pd.Timestamp.min
    for row in sorted(best.values(), key=lambda item: (item["entry_dt"], -item["ml_score"], item["family"])):
        entry = pd.Timestamp(row["entry_dt"])
        if entry < active_until:
            continue
        kept.append(row)
        active_until = pd.Timestamp(row["exit_dt"])
    return kept


def pf_value(metrics: dict[str, Any]) -> float:
    value = metrics["spread_adjusted_profit_factor"]
    if value is None:
        return 9.0 if metrics["spread_adjusted_total_r"] > 0 else 0.0
    return float(value)


def build_trade_cache(year_models, outcomes):
    cache = {}
    family_results = []
    for family in FAMILIES:
        name = family["name"]
        for quantile in QUANTILES:
            combined = []
            yearly = {}
            for model in year_models:
                year = int(model["year"])
                threshold = model["thresholds"][quantile]
                selected = []
                for index, template in outcomes[name].items():
                    if pd.Timestamp(template["decision_dt"]).year != year:
                        continue
                    score = model["scores"].get(index)
                    if score is None or score < threshold:
                        continue
                    trade = dict(template)
                    trade["ml_score"] = float(score)
                    trade["context_index"] = index
                    trade["year"] = year
                    selected.append(trade)
                portfolio = one_position(selected)
                cache[(name, quantile, year)] = portfolio
                metrics = base.summarize_trades(portfolio)
                yearly[str(year)] = {"threshold": threshold, "raw": len(selected), "metrics": metrics}
                combined.extend(portfolio)
            aggregate = base.summarize_trades(combined)
            worst_year_r = min(value["metrics"]["spread_adjusted_total_r"] for value in yearly.values())
            minimum_year_trades = min(value["metrics"]["trades"] for value in yearly.values())
            passed = (
                aggregate["trades"] >= 50
                and minimum_year_trades >= 12
                and aggregate["win_rate"] >= 0.52
                and pf_value(aggregate) >= 1.40
                and aggregate["spread_adjusted_max_drawdown_r"] <= 10.0
                and worst_year_r > 0
            )
            family_results.append({
                "candidate_key": f"{name}|{quantile}",
                "family": name,
                "quantile": quantile,
                "aggregate": aggregate,
                "minimum_year_trades": minimum_year_trades,
                "worst_year_r": worst_year_r,
                "research_pass": bool(passed),
                "yearly": yearly,
            })
    family_results.sort(key=lambda row: (not row["research_pass"], -row["aggregate"]["trades"], -row["aggregate"]["spread_adjusted_total_r"]))
    return cache, family_results


def evaluate_pools(cache):
    results = []
    for pool_name, family_names in POOLS.items():
        for quantile in QUANTILES:
            combined = []
            yearly = {}
            for year in YEARS:
                raw = []
                for family_name in family_names:
                    raw.extend(cache[(family_name, quantile, year)])
                portfolio = one_position(raw)
                metrics = base.summarize_trades(portfolio)
                yearly[str(year)] = metrics
                combined.extend(portfolio)
            aggregate = base.summarize_trades(combined)
            worst_year_r = min(value["spread_adjusted_total_r"] for value in yearly.values())
            minimum_year_trades = min(value["trades"] for value in yearly.values())
            pf = pf_value(aggregate)
            balanced = (
                aggregate["trades"] >= 120
                and minimum_year_trades >= 35
                and aggregate["win_rate"] >= 0.55
                and pf >= 1.60
                and aggregate["spread_adjusted_max_drawdown_r"] <= 10.0
                and worst_year_r > 0
            )
            high_frequency = (
                aggregate["trades"] >= 180
                and minimum_year_trades >= 50
                and aggregate["win_rate"] >= 0.52
                and pf >= 1.40
                and aggregate["spread_adjusted_max_drawdown_r"] <= 14.0
                and worst_year_r > 0
            )
            score = (
                aggregate["spread_adjusted_total_r"]
                - aggregate["spread_adjusted_max_drawdown_r"]
                + 0.035 * min(aggregate["trades"], 300)
                + 0.25 * worst_year_r
                + 0.5 * min(pf, 4.0)
            )
            results.append({
                "portfolio_key": f"{pool_name}|{quantile}",
                "pool": pool_name,
                "families": family_names,
                "quantile": quantile,
                "aggregate": aggregate,
                "minimum_year_trades": minimum_year_trades,
                "worst_year_r": worst_year_r,
                "balanced_pass": bool(balanced),
                "high_frequency_pass": bool(high_frequency),
                "robust_score": float(score),
                "yearly": yearly,
            })
    results.sort(key=lambda row: (not (row["high_frequency_pass"] or row["balanced_pass"]), not row["high_frequency_pass"], -row["robust_score"], -row["aggregate"]["trades"]))
    return results


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else candle_dir / "stage306_stage280_candidate_pool_expansion.json"

    ctx, features = prepare(candle_dir)
    eligible = ctx[ctx.h4_trend.ne(0)].copy()
    columns = feature_variants(features)[FEATURE_VARIANT]
    frame = build_variant_frame(eligible, columns)
    target = target_series(eligible)
    params_spec = next(item for item in PARAM_SETS if item["name"] == PARAM_SET)
    params = {key: value for key, value in params_spec.items() if key != "name"}
    params.update({"objective": "binary", "n_jobs": 1, "verbosity": -1})

    year_models = [fit_year(eligible, frame, target, params, year) for year in YEARS]
    market = build_market(candle_dir)
    outcomes, outcome_meta = precompute(eligible, market, float(args.point_size))
    cache, family_results = build_trade_cache(year_models, outcomes)
    pool_results = evaluate_pools(cache)
    balanced = [row for row in pool_results if row["balanced_pass"]]
    high_frequency = [row for row in pool_results if row["high_frequency_pass"]]

    report = {
        "status": "GOLD_V3_306_STAGE280_CANDIDATE_POOL_EXPANSION_READY",
        "mode": "AUDIT_ONLY_RESEARCH_NEW_CANDIDATE_FAMILIES",
        "decision": "HIGH_FREQUENCY_PORTFOLIOS_FOUND" if high_frequency else "BALANCED_PORTFOLIOS_FOUND" if balanced else "NO_EXPANDED_PORTFOLIO_PASSED",
        "goal": "increase frequency using complementary long/short and trigger families rather than only lowering one threshold",
        "model_contract": {
            "feature_variant": FEATURE_VARIANT,
            "feature_count": len(columns),
            "param_set": PARAM_SET,
            "quantiles": QUANTILES,
            "years": list(YEARS),
            "tp_atr": TP_ATR,
            "sl_atr": SL_ATR,
            "max_holding_minutes": MAX_HOLD_MINUTES,
            "entry": "next exact M5 open",
            "outcome": "M1 first touch; same M1 SL priority; otherwise time exit",
            "point_size": float(args.point_size),
        },
        "candidate_families": FAMILIES,
        "candidate_pools": POOLS,
        "yearly_model_population": [{key: value for key, value in model.items() if key != "scores"} for model in year_models],
        "outcome_precompute": outcome_meta,
        "family_pass_count": sum(row["research_pass"] for row in family_results),
        "family_results": family_results,
        "pool_search": {
            "evaluated": len(pool_results),
            "balanced_pass_count": len(balanced),
            "high_frequency_pass_count": len(high_frequency),
            "balanced_gate": {"trades": 120, "minimum_each_year": 35, "win_rate": 0.55, "profit_factor": 1.60, "max_dd_r": 10.0, "worst_year_r": 0.0},
            "high_frequency_gate": {"trades": 180, "minimum_each_year": 50, "win_rate": 0.52, "profit_factor": 1.40, "max_dd_r": 14.0, "worst_year_r": 0.0},
        },
        "balanced_portfolios": balanced,
        "high_frequency_portfolios": high_frequency,
        "portfolio_leaderboard": pool_results[: max(1, args.top)],
        "promotion": {
            "performed": False,
            "production_stage280": "UNCHANGED_BLOCKED",
            "stage281": "UNCHANGED",
            "stage286": "UNCHANGED",
            "next_if_pass": "run overlap and integrated Stage292 portfolio audit before freezing candidates",
        },
        "safety_flags": {"final_signal_changed": False, "mt5_order_enabled": False, "discord_enabled": False, "partial_close_enabled": False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
