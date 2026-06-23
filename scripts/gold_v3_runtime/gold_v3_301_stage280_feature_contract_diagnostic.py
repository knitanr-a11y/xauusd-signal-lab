#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

from gold_v3_298_stage280_model_variant_diagnostic import (
    EXP_AUC,
    EXP_CAL_N,
    EXP_FIT_N,
    EXP_FIXTURE,
    EXP_TEST_N,
    EXP_TEST_POS,
    EXP_THRESHOLD,
    FIXTURE_TIME,
    build_frame,
    prepare,
)
from gold_v3_299_stage280_wick_weight_diagnostic import (
    apply_directional_reject,
    target_series,
)

EXP_PR_AUC = 0.08009367826075599
EXPECTED_BUCKETS = {
    "q90": {"n": 120, "hits": 10},
    "q95": {"n": 64, "hits": 8},
    "q975": {"n": 25, "hits": 3},
    "q99": {"n": 11, "hits": 1},
}
QUANTILES = {"q90": 0.90, "q95": 0.95, "q975": 0.975, "q99": 0.99}

PARAM_SETS: list[dict[str, Any]] = [
    {
        "name": "stage300_rank1",
        "n_estimators": 220,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "max_depth": 5,
        "min_child_samples": 60,
        "subsample": 0.85,
        "subsample_freq": 0,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.5,
        "reg_lambda": 6.0,
        "random_state": 281,
        "max_bin": 255,
        "min_split_gain": 0.0,
        "min_child_weight": 0.001,
        "scale_pos_weight": 18.5,
    },
    {
        "name": "stage300_rank2",
        "n_estimators": 200,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "max_depth": 5,
        "min_child_samples": 120,
        "subsample": 0.85,
        "subsample_freq": 0,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.0,
        "reg_lambda": 6.0,
        "random_state": 281,
        "max_bin": 255,
        "min_split_gain": 0.0,
        "min_child_weight": 0.001,
        "scale_pos_weight": 18.5,
    },
    {
        "name": "stage300_scalar_best",
        "n_estimators": 220,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "max_depth": 5,
        "min_child_samples": 120,
        "subsample": 0.85,
        "subsample_freq": 0,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.0,
        "reg_lambda": 6.0,
        "random_state": 281,
        "max_bin": 255,
        "min_split_gain": 0.0,
        "min_child_weight": 0.001,
        "scale_pos_weight": 18.0,
    },
    {
        "name": "stage300_near_fixture",
        "n_estimators": 200,
        "learning_rate": 0.035,
        "num_leaves": 15,
        "max_depth": 5,
        "min_child_samples": 120,
        "subsample": 0.85,
        "subsample_freq": 0,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.0,
        "reg_lambda": 6.0,
        "random_state": 281,
        "max_bin": 255,
        "min_split_gain": 0.0,
        "min_child_weight": 0.001,
        "scale_pos_weight": 18.5,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--top", type=int, default=60)
    return parser.parse_args()


def is_engineered(column: str) -> bool:
    return column in {
        "countermove_60",
        "countermove_120",
        "turn_5",
        "turn_15",
        "turn_30",
        "turn_accel_5v30",
        "turn_accel_15v60",
        "m5_turn_accel",
        "m15_turn_accel",
        "m1_reject_wick",
        "m5_reject_wick",
        "m15_reject_wick",
        "h4_align",
        "d1_align",
    }


def family(column: str) -> str:
    for prefix in ("m1_", "m5_", "m15_", "h1_", "h4_", "d1_"):
        if column.startswith(prefix):
            return prefix[:-1]
    if is_engineered(column):
        return "engineered"
    return "other"


def ordered(columns: list[str], mode: str) -> list[str]:
    if mode == "current":
        return list(columns)
    if mode == "sorted":
        return sorted(columns)
    if mode == "reversed":
        return list(reversed(columns))
    if mode == "timeframe_grouped":
        order = {name: i for i, name in enumerate(["m1", "m5", "m15", "h1", "h4", "d1", "engineered", "other"])}
        return sorted(columns, key=lambda c: (order.get(family(c), 99), c))
    raise ValueError(mode)


def feature_variants(features: list[str]) -> dict[str, list[str]]:
    variants: dict[str, list[str]] = {}

    def add(name: str, columns: list[str]) -> None:
        variants[name] = list(dict.fromkeys(columns))

    add("all_current", features)
    add("all_sorted", ordered(features, "sorted"))
    add("all_reversed", ordered(features, "reversed"))
    add("all_timeframe_grouped", ordered(features, "timeframe_grouped"))

    add("no_raw_wicks", [c for c in features if not c.endswith("_lower_wick_ratio") and not c.endswith("_upper_wick_ratio")])
    add("no_volume", [c for c in features if "vol" not in c])
    add("no_spread", [c for c in features if "spread" not in c])
    add("no_volume_spread", [c for c in features if "vol" not in c and "spread" not in c])
    add("no_engineered", [c for c in features if not is_engineered(c)])
    add("engineered_only", [c for c in features if is_engineered(c)])

    for tf in ("m1", "m5", "m15", "h1", "h4", "d1"):
        add(f"drop_{tf}", [c for c in features if not c.startswith(tf + "_")])

    add("ltf_only", [c for c in features if family(c) in {"m1", "m5", "m15", "engineered"}])
    add("htf_only", [c for c in features if family(c) in {"h1", "h4", "d1", "engineered"}])
    add("m1_m5_m15_h1", [c for c in features if family(c) in {"m1", "m5", "m15", "h1", "engineered"}])
    add("m5_m15_h1_h4_d1", [c for c in features if family(c) in {"m5", "m15", "h1", "h4", "d1", "engineered"}])
    add("m1_m5_m15_h4_d1", [c for c in features if family(c) in {"m1", "m5", "m15", "h4", "d1", "engineered"}])

    base_names = list(variants)
    for name in base_names:
        add(name + "__sorted", ordered(variants[name], "sorted"))
        add(name + "__timeframe_grouped", ordered(variants[name], "timeframe_grouped"))
    return variants


def build_variant_frame(z: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = build_frame(
        z,
        columns,
        normalize=True,
        swap_wicks=False,
        relative_align=True,
        include_volume_spread=True,
        include_engineered=True,
    )
    return apply_directional_reject(frame, z)


def test_populations(ctx: pd.DataFrame) -> dict[str, pd.Index]:
    future_valid = ctx[ctx.h4_trend.ne(0) & ctx.future_valid & ctx.time.ge("2026-01-01")]
    all_non_neutral = ctx[ctx.h4_trend.ne(0) & ctx.time.ge("2026-01-01")]
    return {
        "future_valid_first1606": future_valid.index[:EXP_TEST_N],
        "all_non_neutral_first1606": all_non_neutral.index[:EXP_TEST_N],
        "all_non_neutral_through_fixture_plus4h": all_non_neutral.index[
            all_non_neutral.time.le(FIXTURE_TIME + pd.Timedelta(hours=4))
        ],
    }


def contract_score(result: dict[str, Any]) -> float:
    score = (
        abs(result["threshold"] - EXP_THRESHOLD) / 0.01
        + abs(result["fixture_score"] - EXP_FIXTURE) / 0.03
        + abs(result["test_auc"] - EXP_AUC) / 0.01
        + abs(result["test_pr_auc"] - EXP_PR_AUC) / 0.01
    )
    for name, expected in EXPECTED_BUCKETS.items():
        score += 0.02 * abs(result[name]["n"] - expected["n"])
        score += 0.04 * abs(result[name]["hits"] - expected["hits"])
    score += 0.1 * abs(result["test_n"] - EXP_TEST_N)
    score += 0.2 * abs(result["positive_test"] - EXP_TEST_POS)
    return float(score)


def evaluate(
    variant_name: str,
    frame: pd.DataFrame,
    z_train: pd.DataFrame,
    train_target: pd.Series,
    full_ctx: pd.DataFrame,
    full_frame: pd.DataFrame,
    full_target: pd.Series,
    test_name: str,
    test_index: pd.Index,
    params_spec: dict[str, Any],
) -> dict[str, Any]:
    fit = z_train.time.ge("2024-01-01") & z_train.time.lt("2025-07-01")
    cal = z_train.time.ge("2025-07-01") & z_train.time.lt("2026-01-01")
    fixture = z_train.time.eq(FIXTURE_TIME)

    params = {k: v for k, v in params_spec.items() if k != "name"}
    params.update({"objective": "binary", "n_jobs": 1, "verbosity": -1})
    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], train_target.loc[fit])

    cal_score = model.predict_proba(frame.loc[cal])[:, 1]
    thresholds = {name: float(np.quantile(cal_score, q)) for name, q in QUANTILES.items()}
    fixture_score = float(model.predict_proba(frame.loc[fixture])[:, 1][0])

    usable_test = test_index.intersection(full_frame.index)
    test_score = model.predict_proba(full_frame.loc[usable_test])[:, 1]
    test_target = full_target.loc[usable_test].to_numpy(dtype=int)

    result: dict[str, Any] = {
        "feature_variant": variant_name,
        "feature_count": int(frame.shape[1]),
        "param_set": params_spec["name"],
        "test_population": test_name,
        "fit_n": int(fit.sum()),
        "cal_n": int(cal.sum()),
        "test_n": int(len(usable_test)),
        "positive_fit": int(train_target.loc[fit].sum()),
        "positive_test": int(test_target.sum()),
        "test_first_time": str(full_ctx.loc[usable_test, "time"].min()) if len(usable_test) else None,
        "test_last_time": str(full_ctx.loc[usable_test, "time"].max()) if len(usable_test) else None,
        "threshold": thresholds["q95"],
        "fixture_score": fixture_score,
        "test_auc": float(roc_auc_score(test_target, test_score)) if len(np.unique(test_target)) == 2 else np.nan,
        "test_pr_auc": float(average_precision_score(test_target, test_score)) if len(test_target) else np.nan,
    }
    for name, threshold in thresholds.items():
        selected = test_score >= threshold
        result[name] = {
            "threshold": threshold,
            "n": int(selected.sum()),
            "hits": int(test_target[selected].sum()),
            "rate": float(test_target[selected].mean()) if selected.any() else 0.0,
        }
    result["scalar_distance"] = float(
        abs(result["threshold"] - EXP_THRESHOLD)
        + abs(result["fixture_score"] - EXP_FIXTURE)
        + abs(result["test_auc"] - EXP_AUC)
        + abs(result["test_pr_auc"] - EXP_PR_AUC)
    )
    result["contract_score"] = contract_score(result)
    return result


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage301_stage280_feature_contract_diagnostic.json"
    )

    ctx, features = prepare(candle_dir)
    z_train = ctx[ctx.h4_trend.ne(0) & ctx.future_valid].copy()
    train_target = target_series(z_train)

    full_ctx = ctx[ctx.h4_trend.ne(0)].copy()
    full_target = target_series(full_ctx)
    populations = test_populations(ctx)

    variants = feature_variants(features)
    results: list[dict[str, Any]] = []
    for variant_name, columns in variants.items():
        train_frame = build_variant_frame(z_train, columns)
        full_frame = build_variant_frame(full_ctx, columns)
        for params_spec in PARAM_SETS:
            for test_name, test_index in populations.items():
                results.append(
                    evaluate(
                        variant_name,
                        train_frame,
                        z_train,
                        train_target,
                        full_ctx,
                        full_frame,
                        full_target,
                        test_name,
                        test_index,
                        params_spec,
                    )
                )

    results.sort(key=lambda row: (row["contract_score"], row["scalar_distance"]))
    exact = [
        row
        for row in results
        if row["test_n"] == EXP_TEST_N
        and row["positive_test"] == EXP_TEST_POS
        and abs(row["threshold"] - EXP_THRESHOLD) <= 1e-12
        and abs(row["fixture_score"] - EXP_FIXTURE) <= 1e-12
        and abs(row["test_auc"] - EXP_AUC) <= 1e-12
        and abs(row["test_pr_auc"] - EXP_PR_AUC) <= 1e-12
        and all(
            row[name]["n"] == expected["n"]
            and row[name]["hits"] == expected["hits"]
            for name, expected in EXPECTED_BUCKETS.items()
        )
    ]
    report = {
        "status": "GOLD_V3_301_STAGE280_FEATURE_CONTRACT_DIAGNOSTIC_READY",
        "expected": {
            "fit_n": EXP_FIT_N,
            "cal_n": EXP_CAL_N,
            "test_n": EXP_TEST_N,
            "test_positives": EXP_TEST_POS,
            "threshold": EXP_THRESHOLD,
            "fixture_score": EXP_FIXTURE,
            "test_auc": EXP_AUC,
            "test_pr_auc": EXP_PR_AUC,
            "buckets": EXPECTED_BUCKETS,
        },
        "search": {
            "feature_variants": int(len(variants)),
            "parameter_sets": int(len(PARAM_SETS)),
            "test_populations": list(populations),
            "evaluated_models": int(len(results)),
        },
        "exact_matches": exact,
        "ranking": results[: max(1, args.top)],
        "note": "Diagnostic only. No model or threshold is promoted or written.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
