from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import log_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

OUTCOME_ORDER = ["PROTECTIVE", "TARGET", "TIME"]
POLICY_COVERAGE = {"conservative": 0.0025, "standard": 0.005, "high_coverage": 0.01}


@dataclass(frozen=True)
class Segment:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp
    start_embargo_hours: int
    end_purge_hours: int


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json_canonical(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def deterministic_csv_gzip(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw_handle,
            compresslevel=9,
            mtime=0,
        ) as gzip_handle:
            with io.TextIOWrapper(gzip_handle, encoding="utf-8", newline="") as text_handle:
                df.to_csv(
                    text_handle,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def profit_factor(values: np.ndarray) -> float | None:
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses == 0:
        return None if gains == 0 else float("inf")
    return gains / losses


def max_drawdown(values: np.ndarray) -> float:
    equity = np.concatenate([[0.0], np.cumsum(values)])
    peaks = np.maximum.accumulate(equity)
    return float(np.max(peaks - equity))


def max_losing_streak(values: np.ndarray) -> int:
    best = current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def trading_metrics(frame: pd.DataFrame, r_col: str = "strong_r") -> dict[str, Any]:
    values = frame[r_col].to_numpy(dtype=float)
    if len(values) == 0:
        return {
            "trades": 0,
            "positive_rate": None,
            "mean_r": None,
            "total_r": 0.0,
            "profit_factor": None,
            "maximum_drawdown_r": 0.0,
            "maximum_losing_streak": 0,
            "gross_positive_r": 0.0,
            "gross_negative_r_abs": 0.0,
            "top5_removed_total_r": 0.0,
            "top5pct_removed_total_r": 0.0,
        }
    top5_count = min(5, len(values))
    top_pct_count = max(1, int(math.ceil(0.05 * len(values))))
    order = np.argsort(values)[::-1]
    return {
        "trades": int(len(values)),
        "positive_rate": float(np.mean(values > 0)),
        "mean_r": float(np.mean(values)),
        "total_r": float(np.sum(values)),
        "profit_factor": profit_factor(values),
        "gross_positive_r": float(values[values > 0].sum()),
        "gross_negative_r_abs": float(-values[values < 0].sum()),
        "maximum_drawdown_r": max_drawdown(values),
        "maximum_losing_streak": max_losing_streak(values),
        "top5_removed_total_r": (
            float(np.delete(values, order[:top5_count]).sum())
            if len(values) > top5_count
            else 0.0
        ),
        "top5pct_removed_total_r": (
            float(np.delete(values, order[:top_pct_count]).sum())
            if len(values) > top_pct_count
            else 0.0
        ),
    }


def apply_one_open(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    accepted: list[int] = []
    occupied_until: pd.Timestamp | None = None
    for idx, row in frame.sort_values(["decision_time"], kind="mergesort").iterrows():
        decision = pd.Timestamp(row["decision_time"])
        if occupied_until is not None and decision < occupied_until:
            continue
        accepted.append(idx)
        occupied_until = pd.Timestamp(row["exit_time"])
    return frame.loc[accepted].sort_values("decision_time", kind="mergesort").copy()


def segment_mask(frame: pd.DataFrame, segment: Segment) -> pd.Series:
    effective_start = segment.start + pd.Timedelta(hours=segment.start_embargo_hours)
    effective_end = segment.end - pd.Timedelta(hours=segment.end_purge_hours)
    mask = (frame["decision_time"] >= effective_start) & (
        frame["decision_time"] < effective_end
    )
    if segment.end_purge_hours > 0:
        mask &= frame["exit_time"] <= segment.end
    return mask


def multiclass_brier(
    y_true: np.ndarray,
    probs: np.ndarray,
    classes: Iterable[str],
) -> float:
    classes = list(classes)
    onehot = np.zeros_like(probs, dtype=float)
    index = {name: i for i, name in enumerate(classes)}
    for row, label in enumerate(y_true):
        onehot[row, index[str(label)]] = 1.0
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def score_classifier(
    model: Pipeline,
    X: np.ndarray,
    class_mean_r: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    probs = model.predict_proba(X)
    classes = [str(value) for value in model.named_steps["model"].classes_]
    means = np.array([class_mean_r[name] for name in classes], dtype=float)
    return probs @ means, probs


def validation_threshold(scores: np.ndarray, coverage: float) -> float:
    if len(scores) == 0:
        return float("inf")
    return float(np.quantile(scores, 1.0 - coverage, method="higher"))


def choose_logistic(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    c_grid: list[float],
) -> tuple[Pipeline, float, list[dict[str, float]]]:
    rows: list[dict[str, float]] = []
    best: tuple[float, float, Pipeline] | None = None
    labels = OUTCOME_ORDER
    for c_value in c_grid:
        model = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=c_value,
                        solver="lbfgs",
                        max_iter=2000,
                        random_state=0,
                    ),
                ),
            ]
        )
        model.fit(X_train, y_train)
        probs = model.predict_proba(X_val)
        classes = [str(value) for value in model.named_steps["model"].classes_]
        aligned = np.zeros((len(probs), len(labels)), dtype=float)
        for column, name in enumerate(classes):
            aligned[:, labels.index(name)] = probs[:, column]
        loss = float(log_loss(y_val, aligned, labels=labels))
        brier = multiclass_brier(y_val, aligned, labels)
        rows.append(
            {
                "C": c_value,
                "validation_log_loss": loss,
                "validation_brier": brier,
            }
        )
        key = (loss, c_value)
        if best is None or key < (best[0], best[1]):
            best = (loss, c_value, model)
    assert best is not None
    return best[2], best[1], rows


def choose_ridge(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    alpha_grid: list[float],
) -> tuple[Pipeline, float, list[dict[str, float]]]:
    rows: list[dict[str, float]] = []
    best: tuple[float, float, Pipeline] | None = None
    for alpha in alpha_grid:
        model = Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=alpha)),
            ]
        )
        model.fit(X_train, y_train)
        prediction = model.predict(X_val)
        mse = float(mean_squared_error(y_val, prediction))
        mae = float(mean_absolute_error(y_val, prediction))
        rows.append(
            {
                "alpha": alpha,
                "validation_mse": mse,
                "validation_mae": mae,
            }
        )
        key = (mse, alpha)
        if best is None or key < (best[0], best[1]):
            best = (mse, alpha, model)
    assert best is not None
    return best[2], best[1], rows


def run_direction_fold(
    data: pd.DataFrame,
    feature_cols: list[str],
    direction: str,
    fold: dict[str, Any],
    c_grid: list[float],
    alpha_grid: list[float],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    pd.DataFrame,
    pd.DataFrame,
]:
    directional = data.loc[data["direction"] == direction].copy()
    segments = {
        "train": Segment(
            "train",
            pd.Timestamp(fold["train_start"]),
            pd.Timestamp(fold["train_end"]),
            0,
            int(fold["purge_hours"]),
        ),
        "validation": Segment(
            "validation",
            pd.Timestamp(fold["validation_start"]),
            pd.Timestamp(fold["validation_end"]),
            int(fold["embargo_hours"]),
            int(fold["purge_hours"]),
        ),
        "test": Segment(
            "test",
            pd.Timestamp(fold["test_start"]),
            pd.Timestamp(fold["test_end"]),
            int(fold["embargo_hours"]),
            int(fold.get("test_end_purge_hours", 0)),
        ),
    }
    split = {
        name: directional.loc[segment_mask(directional, segment)].copy()
        for name, segment in segments.items()
    }
    for name, frame in split.items():
        if frame.empty:
            raise ValueError(f"{fold['fold_id']} {direction} {name} is empty")

    X = {
        name: frame[feature_cols].to_numpy(dtype=float)
        for name, frame in split.items()
    }
    y_class = {
        name: frame["outcome"].to_numpy(dtype=str)
        for name, frame in split.items()
    }
    y_r = {
        name: frame["strong_r"].to_numpy(dtype=float)
        for name, frame in split.items()
    }

    class_model, chosen_c, logistic_grid = choose_logistic(
        X["train"],
        y_class["train"],
        X["validation"],
        y_class["validation"],
        c_grid,
    )
    class_mean_r = (
        split["train"].groupby("outcome")["strong_r"].mean().to_dict()
    )
    missing_classes = set(OUTCOME_ORDER) - set(class_mean_r)
    if missing_classes:
        raise ValueError(f"Missing training outcome classes: {missing_classes}")
    cls_val_score, _ = score_classifier(
        class_model,
        X["validation"],
        class_mean_r,
    )
    cls_test_score, cls_test_probs = score_classifier(
        class_model,
        X["test"],
        class_mean_r,
    )

    ridge_model, chosen_alpha, ridge_grid = choose_ridge(
        X["train"],
        y_r["train"],
        X["validation"],
        y_r["validation"],
        alpha_grid,
    )
    ridge_val_score = ridge_model.predict(X["validation"])
    ridge_test_score = ridge_model.predict(X["test"])

    fold_metrics: list[dict[str, Any]] = []

    train_class_rates = (
        split["train"]["outcome"].value_counts(normalize=True).to_dict()
    )
    unconditional_probs = np.column_stack(
        [
            np.full(
                len(split["test"]),
                float(train_class_rates.get(name, 0.0)),
            )
            for name in OUTCOME_ORDER
        ]
    )
    unconditional_mean_r = float(split["train"]["strong_r"].mean())
    unconditional_r_pred = np.full(
        len(split["test"]),
        unconditional_mean_r,
        dtype=float,
    )
    fold_metrics.append(
        {
            "fold_id": fold["fold_id"],
            "direction": direction,
            "model": "unconditional_class_rate",
            "train_rows": len(split["train"]),
            "validation_rows": len(split["validation"]),
            "test_rows": len(split["test"]),
            "selected_hyperparameter": None,
            "test_log_loss": float(
                log_loss(
                    y_class["test"],
                    unconditional_probs,
                    labels=OUTCOME_ORDER,
                )
            ),
            "test_brier": multiclass_brier(
                y_class["test"],
                unconditional_probs,
                OUTCOME_ORDER,
            ),
            "test_mse": None,
            "test_mae": None,
            "train_class_mean_r": json.dumps(
                train_class_rates,
                sort_keys=True,
            ),
            "validation_grid": None,
        }
    )
    fold_metrics.append(
        {
            "fold_id": fold["fold_id"],
            "direction": direction,
            "model": "unconditional_mean_r",
            "train_rows": len(split["train"]),
            "validation_rows": len(split["validation"]),
            "test_rows": len(split["test"]),
            "selected_hyperparameter": unconditional_mean_r,
            "test_log_loss": None,
            "test_brier": None,
            "test_mse": float(
                mean_squared_error(y_r["test"], unconditional_r_pred)
            ),
            "test_mae": float(
                mean_absolute_error(y_r["test"], unconditional_r_pred)
            ),
            "train_class_mean_r": None,
            "validation_grid": None,
        }
    )

    test_probs_aligned = np.zeros(
        (len(split["test"]), len(OUTCOME_ORDER)),
        dtype=float,
    )
    class_names = [
        str(value) for value in class_model.named_steps["model"].classes_
    ]
    for column, name in enumerate(class_names):
        test_probs_aligned[:, OUTCOME_ORDER.index(name)] = cls_test_probs[:, column]
    fold_metrics.append(
        {
            "fold_id": fold["fold_id"],
            "direction": direction,
            "model": "multinomial_logistic",
            "train_rows": len(split["train"]),
            "validation_rows": len(split["validation"]),
            "test_rows": len(split["test"]),
            "selected_hyperparameter": chosen_c,
            "test_log_loss": float(
                log_loss(
                    y_class["test"],
                    test_probs_aligned,
                    labels=OUTCOME_ORDER,
                )
            ),
            "test_brier": multiclass_brier(
                y_class["test"],
                test_probs_aligned,
                OUTCOME_ORDER,
            ),
            "test_mse": None,
            "test_mae": None,
            "train_class_mean_r": json.dumps(
                class_mean_r,
                sort_keys=True,
            ),
            "validation_grid": json.dumps(
                logistic_grid,
                sort_keys=True,
            ),
        }
    )
    fold_metrics.append(
        {
            "fold_id": fold["fold_id"],
            "direction": direction,
            "model": "ridge_strong_r",
            "train_rows": len(split["train"]),
            "validation_rows": len(split["validation"]),
            "test_rows": len(split["test"]),
            "selected_hyperparameter": chosen_alpha,
            "test_log_loss": None,
            "test_brier": None,
            "test_mse": float(
                mean_squared_error(y_r["test"], ridge_test_score)
            ),
            "test_mae": float(
                mean_absolute_error(y_r["test"], ridge_test_score)
            ),
            "train_class_mean_r": None,
            "validation_grid": json.dumps(
                ridge_grid,
                sort_keys=True,
            ),
        }
    )

    policy_metrics: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    for model_name, val_score, test_score in [
        ("multinomial_logistic", cls_val_score, cls_test_score),
        ("ridge_strong_r", ridge_val_score, ridge_test_score),
    ]:
        base = split["test"][
            [
                "decision_time",
                "direction",
                "outcome",
                "exit_time",
                "base_r",
                "strong_r",
                "extreme_r",
            ]
        ].copy()
        base["fold_id"] = fold["fold_id"]
        base["model"] = model_name
        base["score"] = test_score
        for policy_name, coverage in POLICY_COVERAGE.items():
            threshold = validation_threshold(val_score, coverage)
            raw_mask = (test_score >= threshold) & (test_score > 0.0)
            candidates = base.loc[raw_mask].copy()
            accepted = apply_one_open(candidates)
            candidate_indices = set(candidates.index)
            accepted_indices = set(accepted.index)
            base[f"{policy_name}_selected_raw"] = [
                idx in candidate_indices for idx in base.index
            ]
            base[f"{policy_name}_accepted_one_open"] = [
                idx in accepted_indices for idx in base.index
            ]
            metrics = trading_metrics(accepted, "strong_r")
            extreme = trading_metrics(accepted, "extreme_r")
            policy_metrics.append(
                {
                    "fold_id": fold["fold_id"],
                    "direction": direction,
                    "model": model_name,
                    "policy": policy_name,
                    "coverage_target": coverage,
                    "validation_threshold": threshold,
                    "test_rows": len(base),
                    "raw_signals": len(candidates),
                    "accepted_trades": len(accepted),
                    **{f"strong_{key}": value for key, value in metrics.items()},
                    **{f"extreme_{key}": value for key, value in extreme.items()},
                }
            )
        prediction_rows.append(base)

    baseline = apply_one_open(split["test"])
    strong = trading_metrics(baseline, "strong_r")
    extreme = trading_metrics(baseline, "extreme_r")
    policy_metrics.append(
        {
            "fold_id": fold["fold_id"],
            "direction": direction,
            "model": "always_trade_one_open",
            "policy": "all_available",
            "coverage_target": 1.0,
            "validation_threshold": None,
            "test_rows": len(split["test"]),
            "raw_signals": len(split["test"]),
            "accepted_trades": len(baseline),
            **{f"strong_{key}": value for key, value in strong.items()},
            **{f"extreme_{key}": value for key, value in extreme.items()},
        }
    )

    coefficient_rows: list[dict[str, Any]] = []
    logistic = class_model.named_steps["model"]
    scaler = class_model.named_steps["scale"]
    for class_index, class_name in enumerate(logistic.classes_):
        for feature_index, (feature, coefficient) in enumerate(
            zip(feature_cols, logistic.coef_[class_index])
        ):
            coefficient_rows.append(
                {
                    "fold_id": fold["fold_id"],
                    "direction": direction,
                    "model": "multinomial_logistic",
                    "target": str(class_name),
                    "feature": feature,
                    "standardized_coefficient": float(coefficient),
                    "feature_train_mean": float(scaler.mean_[feature_index]),
                    "feature_train_scale": float(scaler.scale_[feature_index]),
                }
            )
    ridge = ridge_model.named_steps["model"]
    ridge_scaler = ridge_model.named_steps["scale"]
    for feature_index, (feature, coefficient) in enumerate(
        zip(feature_cols, ridge.coef_)
    ):
        coefficient_rows.append(
            {
                "fold_id": fold["fold_id"],
                "direction": direction,
                "model": "ridge_strong_r",
                "target": "strong_r",
                "feature": feature,
                "standardized_coefficient": float(coefficient),
                "feature_train_mean": float(ridge_scaler.mean_[feature_index]),
                "feature_train_scale": float(ridge_scaler.scale_[feature_index]),
            }
        )

    return (
        fold_metrics,
        policy_metrics,
        pd.concat(prediction_rows, ignore_index=True),
        pd.DataFrame(coefficient_rows),
    )


def aggregate_policy_metrics(policy_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = ["direction", "model", "policy"]
    for key, group in policy_df.groupby(keys, sort=True, dropna=False):
        direction, model, policy = key
        accepted = int(group["accepted_trades"].sum())
        strong_loss = float(group["strong_gross_negative_r_abs"].sum())
        extreme_loss = float(group["extreme_gross_negative_r_abs"].sum())
        rows.append(
            {
                "direction": direction,
                "model": model,
                "policy": policy,
                "folds": int(len(group)),
                "positive_strong_folds": int((group["strong_total_r"] > 0).sum()),
                "test_rows": int(group["test_rows"].sum()),
                "raw_signals": int(group["raw_signals"].sum()),
                "accepted_trades": accepted,
                "strong_total_r_sum": float(group["strong_total_r"].sum()),
                "strong_mean_r_weighted": (
                    float(group["strong_total_r"].sum() / accepted)
                    if accepted
                    else None
                ),
                "strong_profit_factor_aggregate": (
                    float(group["strong_gross_positive_r"].sum() / strong_loss)
                    if strong_loss > 0
                    else None
                ),
                "extreme_total_r_sum": float(group["extreme_total_r"].sum()),
                "extreme_profit_factor_aggregate": (
                    float(group["extreme_gross_positive_r"].sum() / extreme_loss)
                    if extreme_loss > 0
                    else None
                ),
                "sum_of_fold_top5_removed_total_r": float(
                    group["strong_top5_removed_total_r"].sum()
                ),
                "maximum_fold_drawdown_r": float(
                    group["strong_maximum_drawdown_r"].max()
                ),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run GML1-MLR1 ML-04 deterministic and linear baselines"
    )
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--label-registry", type=Path, required=True)
    parser.add_argument("--feature-contract", type=Path, required=True)
    parser.add_argument("--ml04-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    contract = load_json(args.ml04_contract)
    feature_contract = load_json(args.feature_contract)
    if sha256_file(args.feature_registry) != contract["input_sha256"][
        "feature_registry"
    ]:
        raise ValueError("Feature registry SHA256 mismatch")
    if sha256_file(args.label_registry) != contract["input_sha256"][
        "label_registry"
    ]:
        raise ValueError("Label registry SHA256 mismatch")
    feature_cols = feature_contract["model_feature_columns"]

    features = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    labels = pd.read_csv(
        args.label_registry,
        parse_dates=["decision_time", "exit_time"],
    )
    if len(feature_cols) != contract["model_feature_count"]:
        raise ValueError("Feature-count contract mismatch")
    merged = labels.merge(
        features[["decision_time"] + feature_cols],
        on="decision_time",
        how="inner",
        validate="many_to_one",
    )
    if len(merged) != len(labels):
        raise ValueError("Feature/label join lost rows")
    if not np.isfinite(merged[feature_cols].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite model features")

    fold_rows: list[dict[str, Any]] = []
    policy_rows: list[dict[str, Any]] = []
    predictions: list[pd.DataFrame] = []
    coefficients: list[pd.DataFrame] = []
    for fold in contract["folds"]:
        for direction in ["LONG", "SHORT"]:
            fold_metrics, policy_metrics, prediction, coefficient = run_direction_fold(
                merged,
                feature_cols,
                direction,
                fold,
                [float(value) for value in contract["logistic_c_grid"]],
                [float(value) for value in contract["ridge_alpha_grid"]],
            )
            fold_rows.extend(fold_metrics)
            policy_rows.extend(policy_metrics)
            predictions.append(prediction)
            coefficients.append(coefficient)

    fold_df = pd.DataFrame(fold_rows).sort_values(
        ["fold_id", "direction", "model"]
    ).reset_index(drop=True)
    policy_df = pd.DataFrame(policy_rows).sort_values(
        ["fold_id", "direction", "model", "policy"]
    ).reset_index(drop=True)
    prediction_df = pd.concat(predictions, ignore_index=True).sort_values(
        ["fold_id", "direction", "model", "decision_time"]
    ).reset_index(drop=True)
    coefficient_df = pd.concat(coefficients, ignore_index=True).sort_values(
        ["fold_id", "direction", "model", "target", "feature"]
    ).reset_index(drop=True)
    aggregate = aggregate_policy_metrics(policy_df)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fold_path = args.output_dir / "mlr1_ml04_fold_metrics.csv"
    policy_path = args.output_dir / "mlr1_ml04_policy_metrics.csv"
    prediction_path = args.output_dir / "mlr1_ml04_test_predictions.csv.gz"
    coefficient_path = args.output_dir / "mlr1_ml04_coefficients.csv.gz"
    fold_df.to_csv(
        fold_path,
        index=False,
        lineterminator="\n",
        float_format="%.12g",
    )
    policy_df.to_csv(
        policy_path,
        index=False,
        lineterminator="\n",
        float_format="%.12g",
    )
    deterministic_csv_gzip(prediction_df, prediction_path)
    deterministic_csv_gzip(coefficient_df, coefficient_path)

    summary = {
        "system_id": "GML1-MLR1",
        "stage": "ML-04",
        "status": "BASELINE_RESULTS_BUILT_AUDIT_ONLY",
        "input_sha256": contract["input_sha256"],
        "rows": {
            "features": len(features),
            "labels": len(labels),
            "merged": len(merged),
        },
        "aggregate_policy_metrics": aggregate,
        "outputs": {
            "fold_metrics": {
                "path": str(fold_path),
                "sha256": sha256_file(fold_path),
            },
            "policy_metrics": {
                "path": str(policy_path),
                "sha256": sha256_file(policy_path),
            },
            "test_predictions": {
                "path": str(prediction_path),
                "sha256": sha256_file(prediction_path),
            },
            "coefficients": {
                "path": str(coefficient_path),
                "sha256": sha256_file(coefficient_path),
            },
        },
        "controls": {
            "audit_only": True,
            "calibrated": False,
            "model_promoted": False,
            "live_ready": False,
        },
    }
    write_json_canonical(args.output_dir / "mlr1_ml04_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
