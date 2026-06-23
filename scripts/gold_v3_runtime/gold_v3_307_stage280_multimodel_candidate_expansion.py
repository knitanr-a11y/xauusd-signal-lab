#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

import gold_v3_304_stage280_approximate_walkforward_backtest as base
import gold_v3_306_stage280_candidate_pool_expansion as stage306
from gold_v3_298_stage280_model_variant_diagnostic import prepare
from gold_v3_299_stage280_wick_weight_diagnostic import target_series
from gold_v3_301_stage280_feature_contract_diagnostic import (
    PARAM_SETS,
    build_variant_frame,
    feature_variants,
)

YEARS = (2025, 2026)
POINT_SIZE = 0.01
ANCHOR_FAMILY = {
    "name": "L_BRK6_60_B20",
    "direction": 1,
    "kind": "BRK",
    "lookback": 6,
    "wait": 60,
    "body": 0.20,
}

MODEL_SPECS: list[dict[str, str]] = [
    {
        "name": "PRIMARY",
        "feature_variant": "m1_m5_m15_h1__timeframe_grouped",
        "param_set": "stage300_near_fixture",
    },
    {
        "name": "DROP_H4",
        "feature_variant": "drop_h4",
        "param_set": "stage300_rank1",
    },
    {
        "name": "DROP_D1",
        "feature_variant": "drop_d1__sorted",
        "param_set": "stage300_near_fixture",
    },
    {
        "name": "ALL_TF",
        "feature_variant": "all_timeframe_grouped",
        "param_set": "stage300_scalar_best",
    },
    {
        "name": "LTF_ONLY",
        "feature_variant": "ltf_only__timeframe_grouped",
        "param_set": "stage300_scalar_best",
    },
    {
        "name": "NO_ENGINEERED",
        "feature_variant": "no_engineered__timeframe_grouped",
        "param_set": "stage300_scalar_best",
    },
]

RULES = (
    "ANY_P80",
    "ANY_P85",
    "ANY_P90",
    "VOTE2_P70",
    "VOTE2_P75",
    "VOTE2_P80",
    "VOTE3_P70",
    "VOTE3_P75",
    "AVG_P70",
    "AVG_P75",
    "TOP2AVG_P75",
    "TOP2AVG_P80",
    "PRIMARY75_OR_VOTE2_80",
    "PRIMARY80_OR_OTHER90",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--point-size", type=float, default=POINT_SIZE)
    parser.add_argument("--top", type=int, default=250)
    return parser.parse_args()


def empirical_percentile(calibration_scores: np.ndarray, values: np.ndarray) -> np.ndarray:
    ordered = np.sort(np.asarray(calibration_scores, dtype=float))
    if not len(ordered):
        return np.zeros(len(values), dtype=float)
    return np.searchsorted(ordered, values, side="right") / float(len(ordered))


def fit_one_year(
    ctx: pd.DataFrame,
    frame: pd.DataFrame,
    target: pd.Series,
    params_spec: dict[str, Any],
    year: int,
) -> dict[str, Any]:
    window = stage306.year_windows(year)
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
    params = {key: value for key, value in params_spec.items() if key != "name"}
    params.update({"objective": "binary", "n_jobs": 1, "verbosity": -1})
    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], target.loc[fit])
    cal_scores = model.predict_proba(frame.loc[cal])[:, 1]
    test_index = ctx.index[test]
    test_scores = model.predict_proba(frame.loc[test_index])[:, 1]
    percentiles = empirical_percentile(cal_scores, test_scores)
    return {
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
        "percentile_by_index": {
            int(index): float(percentile)
            for index, percentile in zip(test_index, percentiles)
        },
    }


def fit_models(ctx: pd.DataFrame, features: list[str], target: pd.Series):
    variants = feature_variants(features)
    params_by_name = {item["name"]: item for item in PARAM_SETS}
    frames: dict[str, pd.DataFrame] = {}
    models: dict[str, dict[int, dict[str, Any]]] = {}
    contract: list[dict[str, Any]] = []

    for spec in MODEL_SPECS:
        variant = spec["feature_variant"]
        if variant not in frames:
            frames[variant] = build_variant_frame(ctx, variants[variant])
        frame = frames[variant]
        year_results = {
            year: fit_one_year(
                ctx,
                frame,
                target,
                params_by_name[spec["param_set"]],
                year,
            )
            for year in YEARS
        }
        models[spec["name"]] = year_results
        contract.append({
            **spec,
            "feature_count": int(frame.shape[1]),
            "year_population": [
                {key: value for key, value in year_results[year].items() if key != "percentile_by_index"}
                for year in YEARS
            ],
        })
    return models, contract


def precompute_outcomes(ctx: pd.DataFrame, candle_dir: Path, point_size: float):
    market = stage306.build_market(candle_dir)
    rows = ctx[
        ctx.h4_trend.eq(-1)
        & ctx.time.ge("2025-01-01")
        & ctx.time.lt("2027-01-01")
    ]
    outcomes: dict[int, dict[str, Any]] = {}
    for index, row in rows.iterrows():
        result = stage306.simulate(
            pd.Timestamp(row.time),
            float(row.atr_prev),
            ANCHOR_FAMILY,
            market,
            point_size,
        )
        if result is not None:
            outcomes[int(index)] = result
    return outcomes, {
        "h4_down_test_rows": int(len(rows)),
        "triggered_and_resolved_rows": int(len(outcomes)),
        "latest_m1_time": str(market["m1"].time.max()),
        "latest_m5_time": str(market["m5"].time.max()),
        "point_size": float(point_size),
    }


def rule_result(rule: str, values: dict[str, float]) -> tuple[bool, float]:
    scores = np.asarray(list(values.values()), dtype=float)
    if not len(scores):
        return False, 0.0
    ordered = np.sort(scores)[::-1]
    top2 = float(ordered[: min(2, len(ordered))].mean())
    primary = values.get("PRIMARY")
    others = [value for name, value in values.items() if name != "PRIMARY"]

    if rule == "ANY_P80":
        passed = float(scores.max()) >= 0.80
    elif rule == "ANY_P85":
        passed = float(scores.max()) >= 0.85
    elif rule == "ANY_P90":
        passed = float(scores.max()) >= 0.90
    elif rule == "VOTE2_P70":
        passed = int((scores >= 0.70).sum()) >= 2
    elif rule == "VOTE2_P75":
        passed = int((scores >= 0.75).sum()) >= 2
    elif rule == "VOTE2_P80":
        passed = int((scores >= 0.80).sum()) >= 2
    elif rule == "VOTE3_P70":
        passed = int((scores >= 0.70).sum()) >= 3
    elif rule == "VOTE3_P75":
        passed = int((scores >= 0.75).sum()) >= 3
    elif rule == "AVG_P70":
        passed = float(scores.mean()) >= 0.70
    elif rule == "AVG_P75":
        passed = float(scores.mean()) >= 0.75
    elif rule == "TOP2AVG_P75":
        passed = len(scores) >= 2 and top2 >= 0.75
    elif rule == "TOP2AVG_P80":
        passed = len(scores) >= 2 and top2 >= 0.80
    elif rule == "PRIMARY75_OR_VOTE2_80":
        passed = (
            primary is not None
            and (
                primary >= 0.75
                or int((scores >= 0.80).sum()) >= 2
            )
        )
    elif rule == "PRIMARY80_OR_OTHER90":
        passed = (
            primary is not None
            and (
                primary >= 0.80
                or (bool(others) and max(others) >= 0.90)
            )
        )
    else:
        raise ValueError(rule)
    return bool(passed), float(top2)


def one_position(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return stage306.one_position(trades)


def pf_value(metrics: dict[str, Any]) -> float:
    return stage306.pf_value(metrics)


def evaluate_configuration(
    subset: tuple[str, ...],
    rule: str,
    models: dict[str, dict[int, dict[str, Any]]],
    outcomes: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    combined: list[dict[str, Any]] = []
    yearly: dict[str, Any] = {}

    for year in YEARS:
        selected_decisions = 0
        raw: list[dict[str, Any]] = []
        for index, template in outcomes.items():
            if pd.Timestamp(template["decision_dt"]).year != year:
                continue
            values = {
                model_name: models[model_name][year]["percentile_by_index"].get(index, 0.0)
                for model_name in subset
            }
            passed, ensemble_score = rule_result(rule, values)
            if not passed:
                continue
            selected_decisions += 1
            trade = dict(template)
            trade["ml_score"] = float(ensemble_score)
            trade["ensemble_score"] = float(ensemble_score)
            trade["source_model"] = max(values, key=values.get)
            trade["model_percentiles"] = values
            trade["context_index"] = int(index)
            trade["year"] = int(year)
            raw.append(trade)
        portfolio = one_position(raw)
        metrics = base.summarize_trades(portfolio)
        yearly[str(year)] = {
            "selected_triggered_raw": int(selected_decisions),
            "standalone_non_overlap": metrics,
        }
        combined.extend(portfolio)

    aggregate = base.summarize_trades(combined)
    minimum_year_trades = min(
        value["standalone_non_overlap"]["trades"] for value in yearly.values()
    )
    worst_year_r = min(
        value["standalone_non_overlap"]["spread_adjusted_total_r"]
        for value in yearly.values()
    )
    pf = pf_value(aggregate)

    balanced = bool(
        aggregate["trades"] >= 140
        and minimum_year_trades >= 40
        and aggregate["win_rate"] >= 0.54
        and pf >= 1.55
        and aggregate["spread_adjusted_max_drawdown_r"] <= 10.0
        and worst_year_r > 0
    )
    high_frequency = bool(
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
        + 0.04 * min(aggregate["trades"], 300)
        + 0.25 * worst_year_r
        + 0.50 * min(pf, 4.0)
    )
    return {
        "ensemble_key": f"{'+'.join(subset)}|{rule}",
        "models": list(subset),
        "rule": rule,
        "aggregate": aggregate,
        "minimum_year_trades": int(minimum_year_trades),
        "worst_year_r": float(worst_year_r),
        "balanced_pass": balanced,
        "high_frequency_pass": high_frequency,
        "robust_score": float(score),
        "yearly": yearly,
    }


def overlap_matrix(
    models: dict[str, dict[int, dict[str, Any]]],
    outcomes: dict[int, dict[str, Any]],
    threshold: float = 0.80,
) -> dict[str, Any]:
    names = [spec["name"] for spec in MODEL_SPECS]
    selected: dict[str, set[tuple[int, int]]] = {}
    for name in names:
        rows: set[tuple[int, int]] = set()
        for year in YEARS:
            scores = models[name][year]["percentile_by_index"]
            for index, score in scores.items():
                if index in outcomes and score >= threshold:
                    rows.add((year, index))
        selected[name] = rows
    matrix: dict[str, Any] = {}
    for left in names:
        matrix[left] = {}
        for right in names:
            union = selected[left] | selected[right]
            inter = selected[left] & selected[right]
            matrix[left][right] = {
                "left_n": len(selected[left]),
                "right_n": len(selected[right]),
                "intersection": len(inter),
                "union": len(union),
                "jaccard": float(len(inter) / len(union)) if union else 0.0,
            }
    return matrix


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage307_stage280_multimodel_candidate_expansion.json"
    )

    ctx, features = prepare(candle_dir)
    eligible = ctx[ctx.h4_trend.ne(0)].copy()
    target = target_series(eligible)
    models, model_contract = fit_models(eligible, features, target)
    outcomes, outcome_meta = precompute_outcomes(
        eligible,
        candle_dir,
        float(args.point_size),
    )

    names = tuple(spec["name"] for spec in MODEL_SPECS)
    results: list[dict[str, Any]] = []
    for size in range(1, len(names) + 1):
        for subset in itertools.combinations(names, size):
            for rule in RULES:
                if rule.startswith("VOTE2") and len(subset) < 2:
                    continue
                if rule.startswith("VOTE3") and len(subset) < 3:
                    continue
                if rule.startswith("TOP2") and len(subset) < 2:
                    continue
                if rule.startswith("PRIMARY") and "PRIMARY" not in subset:
                    continue
                results.append(
                    evaluate_configuration(subset, rule, models, outcomes)
                )

    results.sort(
        key=lambda row: (
            not (row["high_frequency_pass"] or row["balanced_pass"]),
            not row["high_frequency_pass"],
            -row["robust_score"],
            -row["aggregate"]["trades"],
        )
    )
    balanced = [row for row in results if row["balanced_pass"]]
    high_frequency = [row for row in results if row["high_frequency_pass"]]

    report = {
        "status": "GOLD_V3_307_STAGE280_MULTIMODEL_CANDIDATE_EXPANSION_READY",
        "mode": "AUDIT_ONLY_RESEARCH_NEW_MODEL_ENSEMBLES",
        "decision": (
            "HIGH_FREQUENCY_ENSEMBLES_FOUND"
            if high_frequency
            else "BALANCED_ENSEMBLES_FOUND"
            if balanced
            else "NO_MULTIMODEL_ENSEMBLE_PASSED"
        ),
        "goal": "increase independent decision coverage using diverse feature contracts while preserving the audited BRK6 trigger",
        "anchor_execution_contract": {
            "family": ANCHOR_FAMILY,
            "entry": "next exact M5 open",
            "tp_atr": stage306.TP_ATR,
            "sl_atr": stage306.SL_ATR,
            "max_holding_minutes": stage306.MAX_HOLD_MINUTES,
            "outcome": "M1 first touch; same M1 SL priority; otherwise time exit",
            "point_size": float(args.point_size),
        },
        "model_contracts": model_contract,
        "rule_set": list(RULES),
        "search": {
            "model_count": len(MODEL_SPECS),
            "subset_count": int(2 ** len(MODEL_SPECS) - 1),
            "evaluated_ensembles": len(results),
            "walkforward_years": list(YEARS),
            "balanced_pass_count": len(balanced),
            "high_frequency_pass_count": len(high_frequency),
            "balanced_gate": {
                "trades": 140,
                "minimum_each_year": 40,
                "win_rate": 0.54,
                "profit_factor": 1.55,
                "max_dd_r": 10.0,
                "worst_year_r": 0.0,
            },
            "high_frequency_gate": {
                "trades": 180,
                "minimum_each_year": 50,
                "win_rate": 0.52,
                "profit_factor": 1.40,
                "max_dd_r": 14.0,
                "worst_year_r": 0.0,
            },
        },
        "outcome_precompute": outcome_meta,
        "p80_triggered_decision_overlap": overlap_matrix(models, outcomes, 0.80),
        "balanced_ensembles": balanced[:100],
        "high_frequency_ensembles": high_frequency[:100],
        "leaderboard": results[: max(1, args.top)],
        "selection_bias_warning": "Model variants were selected from prior Stage305 research; any passing ensemble remains research-only and requires integrated replay plus shadow validation.",
        "promotion": {
            "performed": False,
            "production_stage280": "UNCHANGED_BLOCKED",
            "stage281": "UNCHANGED",
            "stage286": "UNCHANGED",
            "next_if_pass": "run Stage292 integrated overlap/DD replay before freezing any new ensemble",
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
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
