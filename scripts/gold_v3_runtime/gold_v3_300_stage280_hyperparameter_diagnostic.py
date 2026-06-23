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
    prepare,
)
from gold_v3_299_stage280_wick_weight_diagnostic import frames, target_series

EXP_PR_AUC = 0.08009367826075599
EXPECTED_BUCKETS = {
    "q90": {"n": 120, "hits": 10},
    "q95": {"n": 64, "hits": 8},
    "q975": {"n": 25, "hits": 3},
    "q99": {"n": 11, "hits": 1},
}
QUANTILES = {"q90": 0.90, "q95": 0.95, "q975": 0.975, "q99": 0.99}

BASE_PARAMS: dict[str, Any] = {
    "objective": "binary",
    "n_estimators": 220,
    "learning_rate": 0.03,
    "num_leaves": 15,
    "max_depth": 5,
    "min_child_samples": 60,
    "subsample": 0.85,
    "subsample_freq": 0,
    "colsample_bytree": 0.8,
    "reg_alpha": 1.0,
    "reg_lambda": 6.0,
    "random_state": 281,
    "n_jobs": 1,
    "verbosity": -1,
    "max_bin": 255,
    "min_split_gain": 0.0,
    "min_child_weight": 0.001,
}

FRAME_NAMES = (
    "normalized_no_swap_directional_reject",
    "normalized_no_swap_raw_reject",
    "normalized_no_swap_directional_reject_no_raw_wicks",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--top", type=int, default=50)
    return parser.parse_args()


def config_key(frame_name: str, params: dict[str, Any]) -> str:
    normalized = {
        key: params[key]
        for key in sorted(params)
        if key not in {"n_jobs", "verbosity", "objective"}
    }
    return frame_name + "|" + json.dumps(normalized, sort_keys=True)


def score_contract(result: dict[str, Any]) -> float:
    scalar = (
        abs(result["threshold"] - EXP_THRESHOLD) / 0.01
        + abs(result["fixture_score"] - EXP_FIXTURE) / 0.03
        + abs(result["test_auc"] - EXP_AUC) / 0.01
        + abs(result["test_pr_auc"] - EXP_PR_AUC) / 0.01
    )
    bucket_mismatch = 0
    for name, expected in EXPECTED_BUCKETS.items():
        bucket_mismatch += abs(result[name]["n"] - expected["n"])
        bucket_mismatch += 2 * abs(result[name]["hits"] - expected["hits"])
    return float(scalar + 0.02 * bucket_mismatch)


def evaluate(
    frame_name: str,
    frame: pd.DataFrame,
    z: pd.DataFrame,
    target: pd.Series,
    params: dict[str, Any],
) -> dict[str, Any]:
    fit = z.time.ge("2024-01-01") & z.time.lt("2025-07-01")
    cal = z.time.ge("2025-07-01") & z.time.lt("2026-01-01")
    test_index = z.index[z.time.ge("2026-01-01")][:EXP_TEST_N]
    fixture_mask = z.time.eq(FIXTURE_TIME)

    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], target.loc[fit])

    calibration_score = model.predict_proba(frame.loc[cal])[:, 1]
    test_score = model.predict_proba(frame.loc[test_index])[:, 1]
    test_target = target.loc[test_index].to_numpy(dtype=int)
    fixture_score = float(model.predict_proba(frame.loc[fixture_mask])[:, 1][0])

    bucket_results: dict[str, dict[str, Any]] = {}
    thresholds: dict[str, float] = {}
    for name, quantile in QUANTILES.items():
        threshold = float(np.quantile(calibration_score, quantile))
        thresholds[name] = threshold
        selected = test_score >= threshold
        bucket_results[name] = {
            "threshold": threshold,
            "n": int(selected.sum()),
            "hits": int(test_target[selected].sum()),
            "rate": float(test_target[selected].mean()) if selected.any() else 0.0,
        }

    result: dict[str, Any] = {
        "frame": frame_name,
        "feature_count": int(frame.shape[1]),
        "params": {
            key: value
            for key, value in params.items()
            if key not in {"n_jobs", "verbosity", "objective"}
        },
        "fit_n": int(fit.sum()),
        "cal_n": int(cal.sum()),
        "test_n": int(len(test_index)),
        "positive_fit": int(target.loc[fit].sum()),
        "positive_test": int(test_target.sum()),
        "test_last_time": str(z.loc[test_index, "time"].max()),
        "threshold": thresholds["q95"],
        "fixture_score": fixture_score,
        "test_auc": float(roc_auc_score(test_target, test_score)),
        "test_pr_auc": float(average_precision_score(test_target, test_score)),
        **bucket_results,
    }
    result["scalar_distance"] = float(
        abs(result["threshold"] - EXP_THRESHOLD)
        + abs(result["fixture_score"] - EXP_FIXTURE)
        + abs(result["test_auc"] - EXP_AUC)
        + abs(result["test_pr_auc"] - EXP_PR_AUC)
    )
    result["contract_score"] = score_contract(result)
    result["exact_bucket_counts"] = all(
        result[name]["n"] == expected["n"]
        and result[name]["hits"] == expected["hits"]
        for name, expected in EXPECTED_BUCKETS.items()
    )
    result["exact_scalar_parity"] = all(
        abs(result[key] - expected) <= 1e-12
        for key, expected in {
            "threshold": EXP_THRESHOLD,
            "fixture_score": EXP_FIXTURE,
            "test_auc": EXP_AUC,
            "test_pr_auc": EXP_PR_AUC,
        }.items()
    )
    return result


def add_candidate(
    candidates: dict[str, tuple[str, dict[str, Any]]],
    frame_name: str,
    params: dict[str, Any],
) -> None:
    candidates[config_key(frame_name, params)] = (frame_name, copy.deepcopy(params))


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage300_stage280_hyperparameter_diagnostic.json"
    )

    ctx, features = prepare(candle_dir)
    z = ctx[ctx.h4_trend.ne(0) & ctx.future_valid].copy()
    target = target_series(z)
    available_frames = frames(z, features)
    frame_map = {name: available_frames[name] for name in FRAME_NAMES}

    fit_mask = z.time.ge("2024-01-01") & z.time.lt("2025-07-01")
    positives = int(target.loc[fit_mask].sum())
    ratio = (int(fit_mask.sum()) - positives) / max(positives, 1)

    candidates: dict[str, tuple[str, dict[str, Any]]] = {}
    weight_values = sorted(
        {
            14.0,
            15.0,
            16.0,
            17.0,
            18.0,
            18.5,
            19.0,
            round(float(ratio), 12),
            19.5,
            20.0,
            21.0,
            22.0,
            24.0,
            25.0,
        }
    )
    for frame_name in FRAME_NAMES:
        for weight in weight_values:
            params = copy.deepcopy(BASE_PARAMS)
            params["scale_pos_weight"] = weight
            add_candidate(candidates, frame_name, params)

    evaluated: dict[str, dict[str, Any]] = {}

    def run_pending() -> None:
        for key, (frame_name, params) in list(candidates.items()):
            if key in evaluated:
                continue
            evaluated[key] = evaluate(
                frame_name, frame_map[frame_name], z, target, params
            )

    run_pending()

    best_by_frame: dict[str, dict[str, Any]] = {}
    for frame_name in FRAME_NAMES:
        rows = [row for row in evaluated.values() if row["frame"] == frame_name]
        best_by_frame[frame_name] = min(rows, key=lambda row: row["contract_score"])

    coordinate_values: dict[str, list[Any]] = {
        "n_estimators": [160, 180, 200, 220, 240, 260, 280, 300],
        "learning_rate": [0.02, 0.025, 0.03, 0.035, 0.04, 0.05],
        "num_leaves": [7, 11, 15, 21, 31],
        "max_depth": [3, 4, 5, 6, 7, -1],
        "min_child_samples": [20, 40, 60, 80, 100, 120],
        "reg_alpha": [0.0, 0.5, 1.0, 1.5, 2.0],
        "reg_lambda": [0.0, 2.0, 4.0, 6.0, 8.0, 10.0],
        "colsample_bytree": [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 1.0],
        "random_state": [0, 1, 7, 42, 123, 281, 2026],
        "max_bin": [63, 127, 255, 511],
        "min_split_gain": [0.0, 0.01, 0.05, 0.1],
        "min_child_weight": [0.001, 0.01, 0.1, 1.0],
    }

    for frame_name, best in best_by_frame.items():
        base = copy.deepcopy(BASE_PARAMS)
        base.update(best["params"])
        for parameter, values in coordinate_values.items():
            for value in values:
                params = copy.deepcopy(base)
                params[parameter] = value
                add_candidate(candidates, frame_name, params)
    run_pending()

    top_seeds = sorted(
        evaluated.values(), key=lambda row: row["contract_score"]
    )[:3]
    for seed in top_seeds:
        base = copy.deepcopy(BASE_PARAMS)
        base.update(seed["params"])
        center_weight = float(base.get("scale_pos_weight", ratio))
        center_trees = int(base["n_estimators"])
        center_lr = float(base["learning_rate"])
        for weight in [
            max(1.0, center_weight - 1.0),
            max(1.0, center_weight - 0.5),
            center_weight,
            center_weight + 0.5,
            center_weight + 1.0,
        ]:
            for trees in [max(20, center_trees - 20), center_trees, center_trees + 20]:
                for learning_rate in [
                    max(0.005, center_lr - 0.005),
                    center_lr,
                    center_lr + 0.005,
                ]:
                    params = copy.deepcopy(base)
                    params["scale_pos_weight"] = round(float(weight), 12)
                    params["n_estimators"] = int(trees)
                    params["learning_rate"] = round(float(learning_rate), 6)
                    add_candidate(candidates, seed["frame"], params)
    run_pending()

    ranking = sorted(
        evaluated.values(), key=lambda row: (row["contract_score"], row["scalar_distance"])
    )
    exact = [
        row
        for row in ranking
        if row["exact_scalar_parity"] and row["exact_bucket_counts"]
    ]
    report = {
        "status": "GOLD_V3_300_STAGE280_HYPERPARAMETER_DIAGNOSTIC_READY",
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
        "population": {
            "rows": int(len(z)),
            "positive_fit": positives,
            "scale_pos_ratio": float(ratio),
        },
        "search": {
            "evaluated_models": int(len(evaluated)),
            "frames": list(FRAME_NAMES),
            "strategy": "weight grid -> coordinate search -> local refinement",
        },
        "exact_matches": exact,
        "ranking": ranking[: max(1, args.top)],
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
