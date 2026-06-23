#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score

from gold_v3_289_feature_core import load_gold, m1_arrays
from gold_v3_289_stage280_features import build_stage280_context

EXP_THRESHOLD = 0.5927349103795366
EXP_FIXTURE = 0.5949591748604749
EXP_AUC = 0.6904307891978236
EXP_FIT_N = 4974
EXP_CAL_N = 1809
EXP_TEST_N = 1606
EXP_TEST_POS = 65
FIXTURE_TIME = pd.Timestamp("2026-06-19 08:00:00")
TEST_END_EXCLUSIVE = pd.Timestamp("2026-06-19 13:00:00")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def prepare(candle_dir: Path):
    ctx = build_stage280_context(
        candle_dir, include_next=False, tail_only=False
    ).sort_values("time").reset_index(drop=True)
    raw = load_gold(candle_dir, tail_only=False)
    mt, mo, mh, ml, mc, *_ = m1_arrays(raw["M1"])
    event_dir: list[int] = []
    future_valid: list[bool] = []
    for row in ctx.itertuples(index=False):
        atr = float(row.atr_prev) if pd.notna(row.atr_prev) else np.nan
        timestamp = np.datetime64(row.time)
        start = np.searchsorted(mt, timestamp, side="left")
        end = np.searchsorted(
            mt, timestamp + np.timedelta64(240, "m"), side="left"
        )
        valid = bool(
            np.isfinite(atr)
            and atr > 0
            and start < len(mt)
            and mt[start] == timestamp
            and end > start
            and end - start >= 180
        )
        future_valid.append(valid)
        if not valid:
            event_dir.append(0)
            continue
        entry = float(mo[start])
        high = float(mh[start:end].max())
        low = float(ml[start:end].min())
        final = float(mc[end - 1])
        long_mfe = (high - entry) / atr
        long_mae = (entry - low) / atr
        long_final = (final - entry) / atr
        short_mfe = (entry - low) / atr
        short_mae = (high - entry) / atr
        short_final = (entry - final) / atr
        long_ok = (
            long_mfe >= 2.0
            and long_final >= 0.75
            and long_mae <= 1.25
            and long_mfe >= 1.5 * max(long_mae, 0.05)
        )
        short_ok = (
            short_mfe >= 2.0
            and short_final >= 0.75
            and short_mae <= 1.25
            and short_mfe >= 1.5 * max(short_mae, 0.05)
        )
        if long_ok and not short_ok:
            event_dir.append(1)
        elif short_ok and not long_ok:
            event_dir.append(-1)
        elif long_ok and short_ok:
            event_dir.append(
                1 if long_mfe - long_mae > short_mfe - short_mae else -1
            )
        else:
            event_dir.append(0)
    ctx["future_valid"] = np.asarray(future_valid, dtype=bool)
    ctx["event_dir"] = np.asarray(event_dir, dtype="int8")
    ctx["event_onset"] = False
    for direction in (1, -1):
        mask = ctx.event_dir.eq(direction)
        previous = (
            mask.shift(1, fill_value=False)
            | mask.shift(2, fill_value=False)
            | mask.shift(3, fill_value=False)
        )
        ctx.loc[mask & ~previous, "event_onset"] = True
    meta = {
        "time",
        "atr_prev",
        "future_valid",
        "event_dir",
        "event_onset",
        "h4_trend",
        "d1_trend",
    }
    raw_features = [column for column in ctx.columns if column not in meta]
    bad_suffixes = (
        "_open",
        "_high",
        "_low",
        "_close",
        "_ema20",
        "_ema50",
        "_atr14",
    )
    raw_features = [
        column for column in raw_features if not column.endswith(bad_suffixes)
    ]
    engineered = [
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
    ]
    features = list(dict.fromkeys(raw_features + engineered))
    return ctx, features


def build_frame(
    ctx: pd.DataFrame,
    features: list[str],
    *,
    normalize: bool,
    swap_wicks: bool,
    relative_align: bool,
    include_volume_spread: bool,
    include_engineered: bool,
):
    x = ctx.copy()
    direction = (-pd.to_numeric(ctx.h4_trend, errors="coerce")).astype(float)
    raw = [
        column
        for column in ctx.columns
        if column
        not in {
            "time",
            "atr_prev",
            "future_valid",
            "event_dir",
            "event_onset",
            "h4_trend",
            "d1_trend",
        }
    ]
    converted: dict[str, pd.Series] = {}
    for column in raw:
        values = pd.to_numeric(x[column], errors="coerce")
        if any(
            token in column
            for token in [
                "ret",
                "dist_ema",
                "ema20_slope",
                "ema50_slope",
                "body_signed",
            ]
        ):
            converted[column] = values * direction if normalize else values
        elif "_pos" in column:
            centered = 2 * values - 1
            converted[column] = centered * direction if normalize else centered
    if converted:
        converted_frame = pd.DataFrame(converted, index=x.index)
        x = pd.concat(
            [x.drop(columns=list(converted_frame.columns)), converted_frame], axis=1
        )
    if normalize and swap_wicks:
        for lower in [column for column in raw if column.endswith("lower_wick_ratio")]:
            upper = lower.replace("lower_wick_ratio", "upper_wick_ratio")
            if upper not in ctx.columns:
                continue
            original_lower = pd.to_numeric(ctx[lower], errors="coerce")
            original_upper = pd.to_numeric(ctx[upper], errors="coerce")
            x[lower] = original_lower.where(direction.eq(1), original_upper)
            x[upper] = original_upper.where(direction.eq(1), original_lower)

    def value(column: str) -> pd.Series:
        source = x[column] if column in x.columns else pd.Series(np.nan, index=x.index)
        return pd.to_numeric(source, errors="coerce")

    engineered = pd.DataFrame(
        {
            "countermove_60": -value("m1_ret60_atr"),
            "countermove_120": -value("m1_ret120_atr"),
            "turn_5": value("m1_ret5_atr"),
            "turn_15": value("m1_ret15_atr"),
            "turn_30": value("m1_ret30_atr"),
            "turn_accel_5v30": value("m1_ret5_atr")
            - (value("m1_ret30_atr") - value("m1_ret5_atr")) / 5,
            "turn_accel_15v60": value("m1_ret15_atr")
            - (value("m1_ret60_atr") - value("m1_ret15_atr")) / 3,
            "m5_turn_accel": value("m5_ret3_atr")
            - (value("m5_ret12_atr") - value("m5_ret3_atr")) / 3,
            "m15_turn_accel": value("m15_ret1_atr")
            - (value("m15_ret4_atr") - value("m15_ret1_atr")) / 3,
            "m1_reject_wick": value("m1_lower_wick_ratio")
            - value("m1_upper_wick_ratio"),
            "m5_reject_wick": value("m5_lower_wick_ratio")
            - value("m5_upper_wick_ratio"),
            "m15_reject_wick": value("m15_lower_wick_ratio")
            - value("m15_upper_wick_ratio"),
            "h4_align": pd.to_numeric(x.h4_trend, errors="coerce")
            * (direction if normalize and relative_align else 1),
            "d1_align": pd.to_numeric(x.d1_trend, errors="coerce")
            * (direction if normalize and relative_align else 1),
        },
        index=x.index,
    )
    x = pd.concat(
        [x.drop(columns=list(engineered.columns), errors="ignore"), engineered],
        axis=1,
    )
    selected = list(features)
    if not include_volume_spread:
        selected = [
            column
            for column in selected
            if "vol" not in column and "spread" not in column
        ]
    if not include_engineered:
        selected = [column for column in selected if column not in engineered.columns]
    return (
        x.reindex(columns=selected)
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
        .astype("float32")
    )


def train_variant(
    name: str,
    z: pd.DataFrame,
    features: list[str],
    frame_options: dict[str, bool],
    *,
    recompute_onset_after_filter: bool,
):
    working = z.copy()
    reversal_direction = (-working.h4_trend).astype("int8")
    if recompute_onset_after_filter:
        reversal_label = working.event_dir.eq(reversal_direction)
        previous = (
            reversal_label.shift(1, fill_value=False)
            | reversal_label.shift(2, fill_value=False)
            | reversal_label.shift(3, fill_value=False)
        )
        target = (reversal_label & ~previous).astype(int)
    else:
        target = (
            working.event_onset & working.event_dir.eq(reversal_direction)
        ).astype(int)
    frame = build_frame(working, features, **frame_options)
    fit = working.time.ge("2024-01-01") & working.time.lt("2025-07-01")
    calibration = working.time.ge("2025-07-01") & working.time.lt("2026-01-01")
    test = working.time.ge("2026-01-01") & working.time.lt(TEST_END_EXCLUSIVE)
    positives = int(target[fit].sum())
    weight = min(max((int(fit.sum()) - max(positives, 1)) / max(positives, 1), 1), 25)
    model = LGBMClassifier(
        objective="binary",
        n_estimators=220,
        learning_rate=0.03,
        num_leaves=15,
        max_depth=5,
        min_child_samples=60,
        subsample=0.85,
        colsample_bytree=0.8,
        reg_alpha=1,
        reg_lambda=6,
        random_state=281,
        n_jobs=1,
        verbosity=-1,
        scale_pos_weight=weight,
    )
    model.fit(frame.loc[fit], target.loc[fit])
    calibration_score = model.predict_proba(frame.loc[calibration])[:, 1]
    threshold = float(np.quantile(calibration_score, 0.95))
    fixture_mask = working.time.eq(FIXTURE_TIME)
    fixture = (
        float(model.predict_proba(frame.loc[fixture_mask])[:, 1][0])
        if fixture_mask.any()
        else np.nan
    )
    test_score = model.predict_proba(frame.loc[test])[:, 1]
    auc = (
        float(roc_auc_score(target.loc[test], test_score))
        if target.loc[test].nunique() == 2
        else np.nan
    )
    distance = (
        abs(threshold - EXP_THRESHOLD)
        + abs(fixture - EXP_FIXTURE)
        + abs(auc - EXP_AUC)
    )
    return {
        "variant": name,
        "features": int(frame.shape[1]),
        "fit_n": int(fit.sum()),
        "cal_n": int(calibration.sum()),
        "test_n": int(test.sum()),
        "positive_fit": positives,
        "positive_test": int(target.loc[test].sum()),
        "threshold": threshold,
        "fixture_score": fixture,
        "test_auc": auc,
        "distance": float(distance),
        "frame_options": frame_options,
        "recompute_onset_after_filter": recompute_onset_after_filter,
    }


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage298_stage280_model_variant_diagnostic.json"
    )
    ctx, features = prepare(candle_dir)
    z = ctx[ctx.h4_trend.ne(0) & ctx.future_valid].copy()
    variants = [
        (
            "normalized_swap_relative_global_onset",
            dict(
                normalize=True,
                swap_wicks=True,
                relative_align=True,
                include_volume_spread=True,
                include_engineered=True,
            ),
            False,
        ),
        (
            "normalized_swap_relative_filtered_onset",
            dict(
                normalize=True,
                swap_wicks=True,
                relative_align=True,
                include_volume_spread=True,
                include_engineered=True,
            ),
            True,
        ),
        (
            "raw_direction_global_onset",
            dict(
                normalize=False,
                swap_wicks=False,
                relative_align=False,
                include_volume_spread=True,
                include_engineered=True,
            ),
            False,
        ),
        (
            "raw_direction_filtered_onset",
            dict(
                normalize=False,
                swap_wicks=False,
                relative_align=False,
                include_volume_spread=True,
                include_engineered=True,
            ),
            True,
        ),
        (
            "normalized_no_wick_swap_global_onset",
            dict(
                normalize=True,
                swap_wicks=False,
                relative_align=True,
                include_volume_spread=True,
                include_engineered=True,
            ),
            False,
        ),
        (
            "normalized_raw_align_global_onset",
            dict(
                normalize=True,
                swap_wicks=True,
                relative_align=False,
                include_volume_spread=True,
                include_engineered=True,
            ),
            False,
        ),
        (
            "normalized_no_volume_spread_global_onset",
            dict(
                normalize=True,
                swap_wicks=True,
                relative_align=True,
                include_volume_spread=False,
                include_engineered=True,
            ),
            False,
        ),
        (
            "normalized_raw_features_only_global_onset",
            dict(
                normalize=True,
                swap_wicks=True,
                relative_align=True,
                include_volume_spread=True,
                include_engineered=False,
            ),
            False,
        ),
    ]
    results = [
        train_variant(
            name,
            z,
            features,
            options,
            recompute_onset_after_filter=recompute,
        )
        for name, options, recompute in variants
    ]
    results.sort(key=lambda row: row["distance"])
    report = {
        "status": "GOLD_V3_298_STAGE280_MODEL_VARIANT_DIAGNOSTIC_READY",
        "expected": {
            "fit_n": EXP_FIT_N,
            "cal_n": EXP_CAL_N,
            "test_n": EXP_TEST_N,
            "test_positives": EXP_TEST_POS,
            "threshold": EXP_THRESHOLD,
            "fixture_score": EXP_FIXTURE,
            "test_auc": EXP_AUC,
        },
        "population": {
            "rows": int(len(z)),
            "first": str(z.time.min()),
            "last": str(z.time.max()),
        },
        "ranking": results,
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
