#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
QUANTILES = {
    "q80": 0.80,
    "q85": 0.85,
    "q90": 0.90,
    "q925": 0.925,
    "q95": 0.95,
    "q975": 0.975,
    "q99": 0.99,
}
POINT_SIZE = 0.01
MIN_TOTAL_TRADES = 12
MIN_YEAR_TRADES = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--top", type=int, default=200)
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    return parser.parse_args()


def corrected_outcome(
    decision_dt: pd.Timestamp,
    atr: float,
    market: dict[str, Any],
    point_size: float,
) -> dict[str, Any] | None:
    result = base.simulate_long(decision_dt, atr, market)
    if result is None:
        return None
    spread_points = float(result["entry_spread"])
    spread_price = spread_points * float(point_size)
    result["entry_spread_points"] = spread_points
    result["entry_spread_price"] = spread_price
    result["spread_adjusted_pnl"] = float(result["gross_pnl"] - spread_price)
    result["spread_adjusted_r"] = float(result["spread_adjusted_pnl"] / atr)
    result.pop("entry_spread", None)
    return result


def precompute_outcomes(
    ctx: pd.DataFrame,
    market: dict[str, Any],
    point_size: float,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    test_rows = ctx[
        ctx.h4_trend.eq(-1)
        & ctx.time.ge(f"{min(YEARS)}-01-01")
        & ctx.time.lt(f"{max(YEARS) + 1}-01-01")
    ]
    outcomes: dict[int, dict[str, Any]] = {}
    spreads: list[float] = []
    for index, row in test_rows.iterrows():
        result = corrected_outcome(
            pd.Timestamp(row.time),
            float(row.atr_prev),
            market,
            point_size,
        )
        if result is not None:
            outcomes[int(index)] = result
            spreads.append(float(result["entry_spread_price"]))
    return outcomes, {
        "h4_down_decision_rows": int(len(test_rows)),
        "triggered_and_fully_resolved_rows": int(len(outcomes)),
        "point_size": float(point_size),
        "median_entry_spread_price": float(np.median(spreads)) if spreads else None,
        "max_entry_spread_price": float(np.max(spreads)) if spreads else None,
        "latest_m1_time": str(market["m1"].time.max()),
        "latest_m5_time": str(market["m5"].time.max()),
    }


def pf_number(value: float | None, total_r: float) -> float:
    if value is None:
        return 9.0 if total_r > 0 else 0.0
    return float(value)


def fit_year(
    ctx: pd.DataFrame,
    frame: pd.DataFrame,
    target: pd.Series,
    outcomes: dict[int, dict[str, Any]],
    params_spec: dict[str, Any],
    year: int,
) -> dict[str, Any]:
    window = base.year_windows(year)
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
    reasons: list[str] = []
    if int(fit.sum()) == 0:
        reasons.append("FIT_EMPTY")
    if int(cal.sum()) == 0:
        reasons.append("CAL_EMPTY")
    if int(fit.sum()) > 0 and target.loc[fit].nunique() < 2:
        reasons.append("FIT_TARGET_SINGLE_CLASS")
    result: dict[str, Any] = {
        "year": year,
        "fit_start": str(window["fit_start"]),
        "cal_start": str(window["cal_start"]),
        "test_start": str(window["test_start"]),
        "test_end_exclusive": str(window["test_end"]),
        "fit_n": int(fit.sum()),
        "cal_n": int(cal.sum()),
        "positive_fit": int(target.loc[fit].sum()) if fit.any() else 0,
        "positive_cal": int(target.loc[cal].sum()) if cal.any() else 0,
        "test_decision_n": int(test.sum()),
        "status": "READY" if not reasons else "SKIPPED",
        "skip_reasons": reasons,
        "thresholds": {},
    }
    if reasons:
        return result

    params = {key: value for key, value in params_spec.items() if key != "name"}
    params.update({"objective": "binary", "n_jobs": 1, "verbosity": -1})
    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], target.loc[fit])
    cal_scores = model.predict_proba(frame.loc[cal])[:, 1]
    test_index = ctx.index[test]
    test_scores = model.predict_proba(frame.loc[test_index])[:, 1]
    score_by_index = {
        int(index): float(score)
        for index, score in zip(test_index, test_scores)
    }

    for name, quantile in QUANTILES.items():
        threshold = float(np.quantile(cal_scores, quantile))
        selected = [
            index for index, score in score_by_index.items()
            if score >= threshold
        ]
        trades: list[dict[str, Any]] = []
        for index in selected:
            template = outcomes.get(index)
            if template is None:
                continue
            trade = dict(template)
            trade["ml_score"] = score_by_index[index]
            trade["context_index"] = index
            trade["year"] = year
            trades.append(trade)
        dedup = base.deduplicate(trades)
        portfolio = base.non_overlapping(dedup)
        result["thresholds"][name] = {
            "threshold": threshold,
            "selected_decisions": int(len(selected)),
            "triggered_resolved_raw": int(len(trades)),
            "raw": base.summarize_trades(trades),
            "standalone_non_overlap": base.summarize_trades(portfolio),
            "trades": portfolio,
        }
    return result


def aggregate(
    variant_name: str,
    params_name: str,
    feature_count: int,
    yearly: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for quantile in QUANTILES:
        combined: list[dict[str, Any]] = []
        per_year: dict[str, Any] = {}
        valid_years = 0
        for year_result in yearly:
            year = str(year_result["year"])
            threshold_result = year_result.get("thresholds", {}).get(quantile)
            if not threshold_result:
                per_year[year] = {
                    "status": year_result["status"],
                    "skip_reasons": year_result["skip_reasons"],
                    "fit_n": year_result["fit_n"],
                    "cal_n": year_result["cal_n"],
                    "positive_fit": year_result["positive_fit"],
                    "positive_cal": year_result["positive_cal"],
                }
                continue
            valid_years += 1
            combined.extend(threshold_result["trades"])
            per_year[year] = {
                "status": year_result["status"],
                "fit_n": year_result["fit_n"],
                "cal_n": year_result["cal_n"],
                "positive_fit": year_result["positive_fit"],
                "positive_cal": year_result["positive_cal"],
                "threshold": threshold_result["threshold"],
                "selected_decisions": threshold_result["selected_decisions"],
                "triggered_resolved_raw": threshold_result["triggered_resolved_raw"],
                "standalone_non_overlap": threshold_result["standalone_non_overlap"],
            }
        metrics = base.summarize_trades(combined)
        year_metrics = [
            value["standalone_non_overlap"]
            for value in per_year.values()
            if value.get("standalone_non_overlap")
        ]
        year_net_r = [float(value["spread_adjusted_total_r"]) for value in year_metrics]
        year_trades = [int(value["trades"]) for value in year_metrics]
        worst_year_r = min(year_net_r) if year_net_r else 0.0
        min_year_trades = min(year_trades) if year_trades else 0
        pf = pf_number(
            metrics["spread_adjusted_profit_factor"],
            metrics["spread_adjusted_total_r"],
        )
        score = (
            metrics["spread_adjusted_total_r"]
            - metrics["spread_adjusted_max_drawdown_r"]
            + 0.20 * worst_year_r
            + 0.03 * min(metrics["trades"], 50)
            + 0.15 * min(pf, 3.0)
        )
        research_pass = bool(
            valid_years == len(YEARS)
            and metrics["trades"] >= MIN_TOTAL_TRADES
            and min_year_trades >= MIN_YEAR_TRADES
            and metrics["spread_adjusted_total_r"] > 0
            and pf >= 1.20
            and metrics["spread_adjusted_max_drawdown_r"] <= 8.0
            and worst_year_r >= -2.0
            and metrics["largest_win_share_of_positive_pnl"] <= 0.55
        )
        rows.append({
            "model_key": f"{variant_name}|{params_name}|{quantile}",
            "feature_variant": variant_name,
            "feature_count": int(feature_count),
            "param_set": params_name,
            "quantile": quantile,
            "aggregate": metrics,
            "valid_years": valid_years,
            "minimum_year_trades": min_year_trades,
            "worst_year_spread_adjusted_r": float(worst_year_r),
            "robust_score": float(score),
            "research_pass": research_pass,
            "yearly": per_year,
        })
    return rows


def baseline_summary(
    outcomes: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    combined: list[dict[str, Any]] = []
    for year in YEARS:
        rows = []
        for context_index, value in outcomes.items():
            if pd.Timestamp(value["decision_dt"]).year != year:
                continue
            row = dict(value)
            row["ml_score"] = 0.0
            row["context_index"] = int(context_index)
            row["year"] = year
            rows.append(row)
        rows = base.non_overlapping(base.deduplicate(rows))
        result[str(year)] = base.summarize_trades(rows)
        combined.extend(rows)
    result["aggregate"] = base.summarize_trades(combined)
    return result


def top_unique(rows: list[dict[str, Any]], key, limit: int) -> list[dict[str, Any]]:
    return sorted(rows, key=key)[:limit]


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage305_stage280_corrected_cost_walkforward.json"
    )
    ctx, features = prepare(candle_dir)
    eligible = ctx[ctx.h4_trend.ne(0)].copy()
    target = target_series(eligible)
    market = base.build_market_arrays(candle_dir)
    outcomes, outcome_meta = precompute_outcomes(
        eligible, market, float(args.point_size)
    )
    variants = feature_variants(features)

    leaderboard: list[dict[str, Any]] = []
    fit_count = 0
    for variant_name, columns in variants.items():
        frame = build_variant_frame(eligible, columns)
        for params_spec in PARAM_SETS:
            yearly = [
                fit_year(
                    eligible,
                    frame,
                    target,
                    outcomes,
                    params_spec,
                    year,
                )
                for year in YEARS
            ]
            fit_count += len(YEARS)
            leaderboard.extend(
                aggregate(
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
    per_quantile = {
        name: top_unique(
            [row for row in leaderboard if row["quantile"] == name],
            key=lambda row: (
                not row["research_pass"],
                -row["robust_score"],
            ),
            limit=10,
        )
        for name in QUANTILES
    }
    top_by_trades = top_unique(
        leaderboard,
        key=lambda row: (
            -row["aggregate"]["trades"],
            -row["aggregate"]["spread_adjusted_total_r"],
        ),
        limit=30,
    )
    top_by_net_r = top_unique(
        leaderboard,
        key=lambda row: (
            -row["aggregate"]["spread_adjusted_total_r"],
            row["aggregate"]["spread_adjusted_max_drawdown_r"],
        ),
        limit=30,
    )

    report = {
        "status": "GOLD_V3_305_STAGE280_CORRECTED_COST_WALKFORWARD_READY",
        "mode": "AUDIT_ONLY_RESEARCH_NEW_MODEL_EVALUATION",
        "decision": "RESEARCH_CANDIDATES_FOUND" if passes else "NO_RESEARCH_CANDIDATE_PASSED",
        "corrections_from_stage304": {
            "spread_interpretation": "MT5 spread column treated as points",
            "point_size": float(args.point_size),
            "price_cost_formula": "spread_points * point_size",
            "test_years": list(YEARS),
            "year_2024": "excluded because current history did not provide a valid pre-2024 fit/calibration population",
            "additional_quantiles": list(QUANTILES),
            "full_views": ["overall", "per_quantile", "top_by_trades", "top_by_net_r", "trigger_only_baseline"],
        },
        "contract": {
            "direction": "LONG_ONLY_WHEN_PRIOR_CLOSED_H4_TREND_IS_DOWN",
            "trigger": "M5 close above prior six M5 highs and body_signed >= 0.20 within 60 minutes",
            "entry": "next exact M5 open",
            "tp_atr": base.TP_ATR,
            "sl_atr": base.SL_ATR,
            "max_holding_minutes": base.MAX_HOLD_MINUTES,
            "outcome": "M1 first touch; same M1 SL priority; otherwise time exit",
            "primary_portfolio_view": "standalone max one open position",
        },
        "search": {
            "feature_variants": len(variants),
            "parameter_sets": len(PARAM_SETS),
            "quantiles": list(QUANTILES),
            "walkforward_years": list(YEARS),
            "evaluated_model_year_fits": fit_count,
            "evaluated_configurations": len(leaderboard),
        },
        "outcome_precompute": outcome_meta,
        "trigger_only_baseline": baseline_summary(outcomes),
        "research_gate": {
            "minimum_total_trades": MIN_TOTAL_TRADES,
            "minimum_trades_each_year": MIN_YEAR_TRADES,
            "minimum_spread_adjusted_profit_factor": 1.20,
            "maximum_spread_adjusted_drawdown_r": 8.0,
            "minimum_worst_year_r": -2.0,
            "maximum_largest_win_share": 0.55,
        },
        "research_pass_count": len(passes),
        "research_passes": passes[:100],
        "leaderboard": leaderboard[: max(1, args.top)],
        "top_by_quantile": per_quantile,
        "top_by_trades": top_by_trades,
        "top_by_net_r": top_by_net_r,
        "promotion": {
            "performed": False,
            "stage280_production_state": "UNCHANGED_BLOCKED",
            "requires_followup": "review corrected walk-forward results before freezing any new model",
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
        "note": "This evaluates approximate candidates as new research models, not as recovered Stage280 artifacts.",
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
