#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

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

EXP_PR_AUC = 0.08009367826075599

BASE_PARAMS = {
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
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def target_series(z: pd.DataFrame) -> pd.Series:
    rev_dir = (-pd.to_numeric(z.h4_trend, errors="coerce")).astype("int8")
    return (z.event_onset & z.event_dir.eq(rev_dir)).astype(int)


def apply_directional_reject(frame: pd.DataFrame, z: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    rev_dir = (-pd.to_numeric(z.h4_trend, errors="coerce")).astype(float)
    for prefix in ("m1", "m5", "m15"):
        lower = f"{prefix}_lower_wick_ratio"
        upper = f"{prefix}_upper_wick_ratio"
        reject = f"{prefix}_reject_wick"
        if lower in z.columns and upper in z.columns and reject in out.columns:
            raw = (
                pd.to_numeric(z[lower], errors="coerce")
                - pd.to_numeric(z[upper], errors="coerce")
            )
            out[reject] = (raw * rev_dir).astype("float32")
    return out


def frames(z: pd.DataFrame, features: list[str]) -> dict[str, pd.DataFrame]:
    common = dict(
        normalize=True,
        relative_align=True,
        include_volume_spread=True,
        include_engineered=True,
    )
    no_swap_raw_reject = build_frame(z, features, swap_wicks=False, **common)
    no_swap_directional_reject = apply_directional_reject(
        no_swap_raw_reject, z
    )
    no_raw_wick_features = [
        col
        for col in features
        if not col.endswith("_lower_wick_ratio")
        and not col.endswith("_upper_wick_ratio")
    ]
    no_raw_wicks = build_frame(
        z, no_raw_wick_features, swap_wicks=False, **common
    )
    no_raw_wicks = apply_directional_reject(no_raw_wicks, z)
    swapped = build_frame(z, features, swap_wicks=True, **common)
    raw_align = build_frame(
        z,
        features,
        normalize=True,
        swap_wicks=False,
        relative_align=False,
        include_volume_spread=True,
        include_engineered=True,
    )
    raw_align = apply_directional_reject(raw_align, z)
    no_vol_features = [
        col for col in features if "vol" not in col and "spread" not in col
    ]
    no_vol = build_frame(z, no_vol_features, swap_wicks=False, **common)
    no_vol = apply_directional_reject(no_vol, z)
    return {
        "normalized_no_swap_raw_reject": no_swap_raw_reject,
        "normalized_no_swap_directional_reject": no_swap_directional_reject,
        "normalized_no_swap_directional_reject_no_raw_wicks": no_raw_wicks,
        "normalized_swap_all_wicks": swapped,
        "normalized_no_swap_directional_reject_raw_align": raw_align,
        "normalized_no_swap_directional_reject_no_volume_spread": no_vol,
    }


def fit_one(
    frame_name: str,
    frame: pd.DataFrame,
    z: pd.DataFrame,
    target: pd.Series,
    weight_mode: str,
) -> dict[str, object]:
    fit = z.time.ge("2024-01-01") & z.time.lt("2025-07-01")
    cal = z.time.ge("2025-07-01") & z.time.lt("2026-01-01")
    test_index = z.index[z.time.ge("2026-01-01")][:EXP_TEST_N]
    fixture = z.time.eq(FIXTURE_TIME)

    params = copy.deepcopy(BASE_PARAMS)
    positives = int(target.loc[fit].sum())
    ratio = (int(fit.sum()) - positives) / max(positives, 1)
    if weight_mode == "scale_pos":
        params["scale_pos_weight"] = min(max(ratio, 1.0), 25.0)
    elif weight_mode == "balanced":
        params["class_weight"] = "balanced"
    elif weight_mode == "scale_pos_bagging":
        params["scale_pos_weight"] = min(max(ratio, 1.0), 25.0)
        params["subsample_freq"] = 1

    model = LGBMClassifier(**params)
    model.fit(frame.loc[fit], target.loc[fit])

    cal_score = model.predict_proba(frame.loc[cal])[:, 1]
    threshold = float(np.quantile(cal_score, 0.95))
    fixture_score = float(model.predict_proba(frame.loc[fixture])[:, 1][0])
    test_score = model.predict_proba(frame.loc[test_index])[:, 1]
    test_target = target.loc[test_index]
    auc = float(roc_auc_score(test_target, test_score))
    pr_auc = float(average_precision_score(test_target, test_score))
    distance = (
        abs(threshold - EXP_THRESHOLD)
        + abs(fixture_score - EXP_FIXTURE)
        + abs(auc - EXP_AUC)
        + abs(pr_auc - EXP_PR_AUC)
    )
    return {
        "frame": frame_name,
        "weight_mode": weight_mode,
        "feature_count": int(frame.shape[1]),
        "fit_n": int(fit.sum()),
        "cal_n": int(cal.sum()),
        "test_n": int(len(test_index)),
        "positive_fit": positives,
        "positive_test": int(test_target.sum()),
        "test_last_time": str(z.loc[test_index, "time"].max()),
        "threshold": threshold,
        "fixture_score": fixture_score,
        "test_auc": auc,
        "test_pr_auc": pr_auc,
        "distance": float(distance),
    }


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage299_stage280_wick_weight_diagnostic.json"
    )

    ctx, features = prepare(candle_dir)
    z = ctx[ctx.h4_trend.ne(0) & ctx.future_valid].copy()
    target = target_series(z)

    results = []
    for frame_name, frame in frames(z, features).items():
        for weight_mode in (
            "scale_pos",
            "balanced",
            "none",
            "scale_pos_bagging",
        ):
            results.append(fit_one(frame_name, frame, z, target, weight_mode))
    results.sort(key=lambda row: row["distance"])

    report = {
        "status": "GOLD_V3_299_STAGE280_WICK_WEIGHT_DIAGNOSTIC_READY",
        "expected": {
            "fit_n": EXP_FIT_N,
            "cal_n": EXP_CAL_N,
            "test_n": EXP_TEST_N,
            "test_positives": EXP_TEST_POS,
            "threshold": EXP_THRESHOLD,
            "fixture_score": EXP_FIXTURE,
            "test_auc": EXP_AUC,
            "test_pr_auc": EXP_PR_AUC,
        },
        "population": {
            "rows": int(len(z)),
            "positive_fit": int(
                target[
                    z.time.ge("2024-01-01")
                    & z.time.lt("2025-07-01")
                ].sum()
            ),
        },
        "ranking": results,
        "note": "Diagnostic only. No model or threshold is promoted.",
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
