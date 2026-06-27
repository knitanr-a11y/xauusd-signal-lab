from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import xgboost
from xgboost import XGBRegressor

TIME_COLUMNS = [
    "time_server_hour_sin",
    "time_server_hour_cos",
    "time_weekday_sin",
    "time_weekday_cos",
]
REQUIRED_EVENT_COLUMNS = {
    "decision_time",
    "candidate_id",
    "candidate_definition_version",
    "candidate_family",
    "direction",
    "proposal_strength",
    "exit_time",
    "strong_r",
    "extreme_r",
}


@dataclass(frozen=True)
class Segment:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    validation_eligible_decisions: int
    test_eligible_decisions: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )


def deterministic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        path,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
        float_format="%.12g",
        lineterminator="\n",
    )


def deterministic_csv_gzip(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0
        ) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                frame.to_csv(
                    text,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_versions(contract: dict[str, Any]) -> None:
    expected = contract["runtime_versions"]
    actual = {
        "python_major_minor": ".".join(platform.python_version().split(".")[:2]),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
    }
    mismatches: dict[str, Any] = {}
    allowed_python = [str(value) for value in expected["python_major_minor"]]
    if actual["python_major_minor"] not in allowed_python:
        mismatches["python_major_minor"] = {
            "expected": allowed_python,
            "actual": actual["python_major_minor"],
        }
    for key in ["numpy", "pandas", "scikit_learn", "xgboost"]:
        if str(actual[key]) != str(expected[key]):
            mismatches[key] = {"expected": expected[key], "actual": actual[key]}
    if mismatches:
        raise RuntimeError(f"Pinned runtime version mismatch: {mismatches}")


def segment_events(
    events: pd.DataFrame,
    start: str,
    end: str,
    kind: str,
    purge: pd.Timedelta,
) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    lower = start_ts if kind == "train" else start_ts + purge
    upper = end_ts - purge if kind in {"train", "validation"} else end_ts
    selected = events.loc[
        (events["decision_time"] >= lower) & (events["decision_time"] < upper)
    ].copy()
    if kind in {"train", "validation"}:
        selected = selected.loc[selected["exit_time"] <= end_ts].copy()
    return selected


def count_eligible_decisions(
    features: pd.DataFrame,
    start: str,
    end: str,
    kind: str,
    purge: pd.Timedelta,
) -> int:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    lower = start_ts if kind == "train" else start_ts + purge
    upper = end_ts - purge if kind in {"train", "validation"} else end_ts
    return int(
        (
            (features["decision_time"] >= lower)
            & (features["decision_time"] < upper)
        ).sum()
    )


def build_segment(
    events: pd.DataFrame,
    features: pd.DataFrame,
    fold: dict[str, str],
    purge: pd.Timedelta,
) -> Segment:
    return Segment(
        train=segment_events(
            events, fold["train_start"], fold["train_end"], "train", purge
        ),
        validation=segment_events(
            events,
            fold["validation_start"],
            fold["validation_end"],
            "validation",
            purge,
        ),
        test=segment_events(
            events, fold["test_start"], fold["test_end"], "test", purge
        ),
        validation_eligible_decisions=count_eligible_decisions(
            features,
            fold["validation_start"],
            fold["validation_end"],
            "validation",
            purge,
        ),
        test_eligible_decisions=count_eligible_decisions(
            features, fold["test_start"], fold["test_end"], "test", purge
        ),
    )


def matrix(
    frame: pd.DataFrame,
    feature_columns: list[str],
    candidate_ids: list[str],
) -> np.ndarray:
    market = frame[feature_columns].to_numpy(dtype=np.float32)
    candidate = np.column_stack(
        [
            (frame["candidate_id"] == candidate_id).to_numpy(dtype=np.float32)
            for candidate_id in candidate_ids
        ]
    )
    return np.hstack([market, candidate])


def mse(y_true: np.ndarray | pd.Series, y_pred: np.ndarray) -> float:
    return float(
        np.mean(
            (
                np.asarray(y_true, dtype=float)
                - np.asarray(y_pred, dtype=float)
            )
            ** 2
        )
    )


def affine_calibration(
    raw_score: np.ndarray, target: np.ndarray
) -> tuple[float, float]:
    x = np.asarray(raw_score, dtype=float)
    y = np.asarray(target, dtype=float)
    variance = float(np.var(x))
    if variance <= 1e-12:
        slope = 0.0
    else:
        slope = float(np.cov(x, y, bias=True)[0, 1] / variance)
        slope = min(max(slope, 0.0), 2.0)
    intercept = float(np.mean(y) - slope * np.mean(x))
    return intercept, slope


def threshold_for_coverage(
    validation_scores: np.ndarray,
    eligible_decisions: int,
    coverage: float,
) -> float:
    if eligible_decisions <= 0 or len(validation_scores) == 0:
        raise ValueError(
            "Validation scores and eligible-decision count must be positive"
        )
    count = max(1, int(math.ceil(coverage * eligible_decisions)))
    ordered = np.sort(np.asarray(validation_scores, dtype=float))[::-1]
    value = float(ordered[min(count, len(ordered)) - 1])
    return max(value, 0.0)


def profit_factor(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=float)
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    if negative > 0:
        return positive / negative
    return float("inf") if positive > 0 else None


def maximum_drawdown(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return 0.0
    equity = np.cumsum(values)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    return float(np.max(peaks[1:] - equity))


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    frame = frame.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    )
    strong = frame["strong_r"].to_numpy(dtype=float)
    extreme = frame["extreme_r"].to_numpy(dtype=float)
    monthly = (
        frame.assign(month=frame["decision_time"].dt.to_period("M").astype(str))
        .groupby("month", sort=True)["strong_r"]
        .sum()
    )
    remove_count = max(1, int(math.ceil(len(strong) * 0.05))) if len(strong) else 0
    return {
        "trades": int(len(frame)),
        "unique_decisions": int(frame["decision_time"].nunique()),
        "long_trades": int((frame["direction"] == "LONG").sum()),
        "short_trades": int((frame["direction"] == "SHORT").sum()),
        "strong_total_r": float(strong.sum()),
        "strong_mean_r": float(strong.mean()) if len(strong) else None,
        "strong_profit_factor": profit_factor(strong),
        "extreme_total_r": float(extreme.sum()),
        "extreme_mean_r": float(extreme.mean()) if len(extreme) else None,
        "extreme_profit_factor": profit_factor(extreme),
        "strong_maximum_drawdown_r": maximum_drawdown(strong),
        "positive_months": int((monthly > 0).sum()),
        "negative_months": int((monthly < 0).sum()),
        "strong_top_five_removed_total_r": (
            float(strong.sum() - np.sort(strong)[-5:].sum())
            if len(strong) >= 5
            else 0.0
        ),
        "strong_top_five_percent_removed_total_r": (
            float(strong.sum() - np.sort(strong)[-remove_count:].sum())
            if remove_count
            else 0.0
        ),
    }


def deduplicate_decisions(
    frame: pd.DataFrame, score_column: str
) -> pd.DataFrame:
    return (
        frame.sort_values(
            ["decision_time", score_column, "candidate_id"],
            ascending=[True, False, True],
            kind="mergesort",
        )
        .drop_duplicates("decision_time", keep="first")
        .sort_values("decision_time", kind="mergesort")
        .copy()
    )


def one_position(frame: pd.DataFrame) -> pd.DataFrame:
    accepted: list[int] = []
    active_exit = pd.Timestamp.min
    for row in frame.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).itertuples():
        if row.decision_time >= active_exit:
            accepted.append(row.Index)
            active_exit = row.exit_time
    return (
        frame.loc[accepted]
        .sort_values("decision_time", kind="mergesort")
        .copy()
    )


def validate_inputs(
    events: pd.DataFrame,
    features: pd.DataFrame,
    columns_contract: dict[str, Any],
) -> tuple[list[str], list[str]]:
    missing = sorted(REQUIRED_EVENT_COLUMNS - set(events.columns))
    if missing:
        raise ValueError(f"Event registry missing required columns: {missing}")
    market_columns = list(columns_contract["market_feature_columns"])
    label_columns = set(columns_contract["label_only_columns"])
    missing_market = sorted(set(market_columns) - set(events.columns))
    if missing_market:
        raise ValueError(f"Event registry missing market columns: {missing_market}")
    if label_columns & set(market_columns):
        raise ValueError("Label-only columns leaked into market feature columns")
    if events.duplicated(["decision_time", "candidate_id"]).any():
        raise ValueError("Duplicate candidate events")
    if events[["decision_time", "exit_time"]].isna().any().any():
        raise ValueError("Null event timestamps")
    if not (events["exit_time"] >= events["decision_time"]).all():
        raise ValueError("Event exit before decision")
    if not events["direction"].isin(["LONG", "SHORT"]).all():
        raise ValueError("Unexpected direction")
    values = events[
        market_columns + ["strong_r", "extreme_r"]
    ].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite model feature or target")
    if features["decision_time"].duplicated().any():
        raise ValueError("Duplicate feature decision_time")
    if not features["decision_time"].is_monotonic_increasing:
        raise ValueError("Feature decisions are not increasing")
    candidate_ids = sorted(str(value) for value in events["candidate_id"].unique())
    return market_columns, candidate_ids


def build_model(parameters: dict[str, Any]) -> XGBRegressor:
    return XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        verbosity=0,
        n_jobs=int(parameters["n_jobs"]),
        random_state=int(parameters["random_state"]),
        subsample=float(parameters["subsample"]),
        colsample_bytree=float(parameters["colsample_bytree"]),
        n_estimators=int(parameters["n_estimators"]),
        max_depth=int(parameters["max_depth"]),
        learning_rate=float(parameters["learning_rate"]),
        min_child_weight=float(parameters["min_child_weight"]),
        reg_lambda=float(parameters["reg_lambda"]),
        max_bin=int(parameters["max_bin"]),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    core = load_json(args.core_contract)
    validate_versions(core)
    columns_contract = load_json(args.columns_contract)
    events = pd.read_csv(
        args.event_registry,
        parse_dates=[
            "decision_time",
            "entry_time",
            "exit_bar_open_time",
            "exit_time",
        ],
    )
    features = pd.read_csv(
        args.feature_registry,
        usecols=["decision_time"],
        parse_dates=["decision_time"],
    )
    market_columns, all_candidate_ids = validate_inputs(
        events, features, columns_contract
    )

    expected_sha = core.get("reference_input_sha256", {}).get("event_registry")
    if (
        args.enforce_reference_sha
        and expected_sha
        and sha256_file(args.event_registry) != expected_sha
    ):
        raise ValueError(
            "Event registry SHA256 differs from the reference audit input"
        )

    feature_sets = {
        "FULL": market_columns,
        "NO_TIME": [
            column for column in market_columns if column not in TIME_COLUMNS
        ],
    }
    purge = pd.Timedelta(hours=int(core["walk_forward"]["purge_hours"]))
    coverages = core["policies"]["coverage_per_direction"]
    parameters = core["estimator"]["parameters"]
    feature_set_order = list(core["estimator"]["feature_set_order"])

    output_dir: Path = args.output_dir
    models_dir = output_dir / "research_models"
    models_dir.mkdir(parents=True, exist_ok=True)

    prediction_parts: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []
    for fold in core["walk_forward"]["folds"]:
        fold_id = fold["fold"]
        segment = build_segment(events, features, fold, purge)
        for direction in ["LONG", "SHORT"]:
            train = segment.train.loc[
                segment.train["direction"] == direction
            ].copy()
            validation = segment.validation.loc[
                segment.validation["direction"] == direction
            ].copy()
            test = segment.test.loc[
                segment.test["direction"] == direction
            ].copy()
            direction_ids = set(
                events.loc[events["direction"] == direction, "candidate_id"]
            )
            candidate_ids = [
                value for value in all_candidate_ids if value in direction_ids
            ]
            if min(len(train), len(validation), len(test)) == 0:
                raise ValueError(f"Empty fold segment: {fold_id} {direction}")

            candidates: list[
                tuple[float, int, str, XGBRegressor, np.ndarray]
            ] = []
            for feature_set_name in feature_set_order:
                feature_columns = feature_sets[feature_set_name]
                model = build_model(parameters)
                model.fit(
                    matrix(train, feature_columns, candidate_ids),
                    train["strong_r"].to_numpy(dtype=float),
                )
                validation_raw = model.predict(
                    matrix(validation, feature_columns, candidate_ids)
                )
                validation_mse = mse(validation["strong_r"], validation_raw)
                candidates.append(
                    (
                        validation_mse,
                        feature_set_order.index(feature_set_name),
                        feature_set_name,
                        model,
                        validation_raw,
                    )
                )
                diagnostics.append(
                    {
                        "fold": fold_id,
                        "direction": direction,
                        "record_type": "FEATURE_SET_CANDIDATE",
                        "feature_set": feature_set_name,
                        "train_events": int(len(train)),
                        "validation_events": int(len(validation)),
                        "test_events": int(len(test)),
                        "validation_raw_mse": validation_mse,
                    }
                )

            (
                _,
                _,
                selected_name,
                selected_model,
                validation_raw,
            ) = min(candidates, key=lambda value: (value[0], value[1]))
            selected_columns = feature_sets[selected_name]
            test_raw = selected_model.predict(
                matrix(test, selected_columns, candidate_ids)
            )
            intercept, slope = affine_calibration(
                validation_raw,
                validation["strong_r"].to_numpy(dtype=float),
            )
            validation_score = intercept + slope * validation_raw
            test_score = intercept + slope * test_raw

            selected_model_path = (
                models_dir / f"{fold_id}_{direction}_strong_r_regressor.ubj"
            )
            selected_model.save_model(selected_model_path)
            model_manifest = {
                "fold": fold_id,
                "direction": direction,
                "feature_set": selected_name,
                "feature_columns": selected_columns,
                "candidate_ids": candidate_ids,
                "calibration_intercept": intercept,
                "calibration_slope": slope,
                "model_sha256": sha256_file(selected_model_path),
                "deployable": False,
                "reason": (
                    "Research fold artifact only. No approved final model exists."
                ),
            }
            write_json(
                models_dir / f"{fold_id}_{direction}_manifest.json",
                model_manifest,
            )

            output = test.copy()
            output["fold"] = fold_id
            output["selected_feature_set"] = selected_name
            output["raw_predicted_strong_r"] = test_raw
            output["predicted_strong_r"] = test_score
            output["calibration_intercept"] = intercept
            output["calibration_slope"] = slope
            for policy_name, coverage in coverages.items():
                threshold = threshold_for_coverage(
                    validation_score,
                    segment.validation_eligible_decisions,
                    float(coverage),
                )
                output[f"threshold_{policy_name}"] = threshold
                output[f"pass_{policy_name}"] = (
                    (output["predicted_strong_r"] >= threshold)
                    & (output["predicted_strong_r"] > 0.0)
                )
            prediction_parts.append(output)
            diagnostics.append(
                {
                    "fold": fold_id,
                    "direction": direction,
                    "record_type": "SELECTED",
                    "feature_set": selected_name,
                    "train_events": int(len(train)),
                    "validation_events": int(len(validation)),
                    "test_events": int(len(test)),
                    "validation_eligible_decisions": (
                        segment.validation_eligible_decisions
                    ),
                    "test_eligible_decisions": segment.test_eligible_decisions,
                    "validation_raw_mse": mse(
                        validation["strong_r"], validation_raw
                    ),
                    "validation_calibrated_mse": mse(
                        validation["strong_r"], validation_score
                    ),
                    "test_raw_mse": mse(test["strong_r"], test_raw),
                    "test_calibrated_mse": mse(test["strong_r"], test_score),
                    "calibration_intercept": intercept,
                    "calibration_slope": slope,
                }
            )

    predictions = (
        pd.concat(prediction_parts, ignore_index=True)
        .sort_values(["decision_time", "candidate_id"], kind="mergesort")
        .reset_index(drop=True)
    )

    metric_rows: list[dict[str, Any]] = []
    fold_ids = [fold["fold"] for fold in core["walk_forward"]["folds"]]
    for fold_id in fold_ids + ["AGGREGATE_OOS"]:
        fold_frame = (
            predictions
            if fold_id == "AGGREGATE_OOS"
            else predictions.loc[predictions["fold"] == fold_id]
        )
        for policy_name in coverages:
            raw = fold_frame.loc[
                fold_frame[f"pass_{policy_name}"]
            ].copy()
            dedup = deduplicate_decisions(raw, "predicted_strong_r")
            positioned = one_position(dedup)
            for view_name, view in [
                ("RAW", raw),
                ("DEDUP", dedup),
                ("ONE_POSITION", positioned),
            ]:
                row = metrics(view)
                row.update(
                    {
                        "fold": fold_id,
                        "policy": policy_name,
                        "view": view_name,
                    }
                )
                metric_rows.append(row)
    policy_metrics = pd.DataFrame(metric_rows)
    diagnostics_frame = pd.DataFrame(diagnostics)

    predictions_path = output_dir / "mlr1_meta_core_oos_predictions_v1.csv.gz"
    metrics_path = output_dir / "mlr1_meta_core_policy_metrics_v1.csv"
    diagnostics_path = output_dir / "mlr1_meta_core_diagnostics_v1.csv"
    deterministic_csv_gzip(predictions, predictions_path)
    deterministic_csv(policy_metrics, metrics_path)
    deterministic_csv(diagnostics_frame, diagnostics_path)

    conservative = policy_metrics.loc[
        (policy_metrics["fold"] == "AGGREGATE_OOS")
        & (policy_metrics["policy"] == "conservative")
        & (policy_metrics["view"] == "ONE_POSITION")
    ].iloc[0].to_dict()
    fold_strong = {
        fold_id: float(
            policy_metrics.loc[
                (policy_metrics["fold"] == fold_id)
                & (policy_metrics["policy"] == "conservative")
                & (policy_metrics["view"] == "ONE_POSITION"),
                "strong_total_r",
            ].iloc[0]
        )
        for fold_id in fold_ids
    }
    positive_values = [
        value for value in fold_strong.values() if value > 0
    ]
    positive_fold_share = (
        max(positive_values) / sum(positive_values)
        if positive_values
        else None
    )
    gate = core["promotion_gate"]
    gate_result = {
        "minimum_total_test_trades": int(conservative["trades"])
        >= int(gate["minimum_total_test_trades"]),
        "minimum_trades_per_direction": (
            int(conservative["long_trades"])
            >= int(gate["minimum_trades_per_direction"])
            and int(conservative["short_trades"])
            >= int(gate["minimum_trades_per_direction"])
        ),
        "minimum_positive_test_folds": sum(
            value > 0 for value in fold_strong.values()
        )
        >= int(gate["minimum_positive_test_folds"]),
        "minimum_strong_profit_factor": float(
            conservative["strong_profit_factor"]
        )
        >= float(gate["minimum_strong_profit_factor"]),
        "minimum_strong_mean_r": float(conservative["strong_mean_r"])
        >= float(gate["minimum_strong_mean_r"]),
        "maximum_strong_drawdown_r": float(
            conservative["strong_maximum_drawdown_r"]
        )
        <= float(gate["maximum_strong_drawdown_r"]),
        "top_five_removed_nonnegative": float(
            conservative["strong_top_five_removed_total_r"]
        )
        >= 0.0,
        "maximum_single_positive_fold_share": (
            positive_fold_share is not None
            and positive_fold_share
            <= float(gate["maximum_single_positive_fold_share"])
        ),
        "extreme_cost_total_r_positive": float(
            conservative["extreme_total_r"]
        )
        > 0.0,
    }
    all_passed = all(gate_result.values())
    summary = {
        "system_id": core["system_id"],
        "stage": "META_MODEL_RESEARCH_CORE",
        "version": core["version"],
        "status": (
            "RESEARCH_CORE_REPLAY_COMPLETE_NOT_DEPLOYABLE"
            if not all_passed
            else "RESEARCH_GATE_PASSED_MANUAL_REVIEW_REQUIRED"
        ),
        "input": {
            "event_registry": str(args.event_registry),
            "event_registry_sha256": sha256_file(args.event_registry),
            "feature_registry": str(args.feature_registry),
            "feature_registry_sha256": sha256_file(args.feature_registry),
            "columns_contract": str(args.columns_contract),
            "columns_contract_sha256": sha256_file(args.columns_contract),
            "event_rows": int(len(events)),
            "market_feature_count": int(len(market_columns)),
            "candidate_count": int(len(all_candidate_ids)),
        },
        "architecture": {
            "target": "strong_r",
            "estimator": "XGBRegressor",
            "separate_long_short": True,
            "candidate_id_one_hot": True,
            "feature_set_selection": (
                "FULL versus NO_TIME by validation MSE only"
            ),
            "calibration": (
                "validation-only nonnegative affine calibration; "
                "slope clipped to [0,2]"
            ),
            "classifier_in_decision_path": False,
            "reason_classifier_removed": (
                "Historical ML-06 selected classifier weight 0.0 in all "
                "eight fold-direction fits."
            ),
        },
        "conservative_one_position": conservative,
        "fold_conservative_strong_r": fold_strong,
        "largest_positive_fold_share": positive_fold_share,
        "promotion_gate": gate_result,
        "all_promotion_gates_passed": all_passed,
        "model_promoted": False,
        "deployment_blocked": True,
        "outputs": {
            "oos_predictions_sha256": sha256_file(predictions_path),
            "policy_metrics_sha256": sha256_file(metrics_path),
            "diagnostics_sha256": sha256_file(diagnostics_path),
            "research_model_artifacts": int(
                len(list(models_dir.glob("*.ubj")))
            ),
        },
        "controls": {
            "audit_only": True,
            "live_inference_implemented": False,
            "shadow_ready": False,
            "live_ready": False,
            "final_signal": False,
            "mt5_order": False,
            "discord": False,
        },
    }
    summary_path = output_dir / "mlr1_meta_core_summary_v1.json"
    write_json(summary_path, summary)
    write_json(
        output_dir / "DEPLOYMENT_BLOCKED.json",
        {
            "blocked": True,
            "reason": (
                "Research models are fold artifacts only. "
                "No final promoted model exists."
            ),
            "summary_sha256": sha256_file(summary_path),
            "forbidden_actions": [
                "live inference",
                "shadow signal",
                "Discord notification",
                "final signal",
                "MT5 order",
            ],
        },
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the frozen GML1 candidate meta-model research core"
    )
    parser.add_argument("--event-registry", type=Path, required=True)
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--columns-contract", type=Path, required=True)
    parser.add_argument("--core-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enforce-reference-sha", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
