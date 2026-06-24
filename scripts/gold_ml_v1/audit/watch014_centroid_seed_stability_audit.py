#!/usr/bin/env python3
"""Centroid and seed-stability audit for GML1-WATCH-014-A.

This tool does not refit or select a trading candidate. It consumes exact
feature and cluster-assignment registries produced by the frozen research run,
aligns arbitrary cluster labels across seeds, and reports motif stability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import StandardScaler


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def safe_number(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def parse_assignment_args(values: list[str]) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--assignment must be SEED=CSV: {value}")
        raw_seed, raw_path = value.split("=", 1)
        seed = int(raw_seed)
        if seed in result:
            raise ValueError(f"duplicate assignment seed: {seed}")
        result[seed] = Path(raw_path).expanduser()
    return result


def parse_naive(series: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise")
    if getattr(parsed.dt, "tz", None) is not None:
        raise ValueError(f"{name} must be naive MT5 server time")
    if parsed.isna().any():
        raise ValueError(f"{name} contains NaT")
    return parsed


def load_feature_registry(path: Path, config: dict[str, Any]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    required = ["decision_close_time", "r_value", *config["feature_columns"]]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"feature registry missing columns: {missing}")
    frame = frame[required].copy()
    frame["decision_close_time"] = parse_naive(frame["decision_close_time"], "decision_close_time")
    if frame["decision_close_time"].duplicated().any():
        raise ValueError("duplicate decision_close_time in feature registry")
    if not frame["decision_close_time"].is_monotonic_increasing:
        raise ValueError("feature registry must be sorted by decision_close_time")
    for column in ["r_value", *config["feature_columns"]]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not np.isfinite(frame[column].to_numpy(dtype=float)).all():
            raise ValueError(f"non-finite value in {column}")
    return frame


def load_assignment(path: Path, seed: int, feature_times: pd.Series, k: int) -> pd.Series:
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = pd.read_csv(path)
    required = ["decision_close_time", "cluster_id"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(f"assignment seed {seed} missing columns: {missing}")
    raw = raw[required].copy()
    raw["decision_close_time"] = parse_naive(raw["decision_close_time"], "decision_close_time")
    if raw["decision_close_time"].duplicated().any():
        raise ValueError(f"duplicate assignment time for seed {seed}")
    raw["cluster_id"] = pd.to_numeric(raw["cluster_id"], errors="raise").astype(int)
    if not raw["cluster_id"].between(0, k - 1).all():
        raise ValueError(f"cluster_id outside 0..{k - 1} for seed {seed}")
    expected = pd.Index(feature_times)
    observed = pd.Index(raw["decision_close_time"])
    missing_times = expected.difference(observed)
    extra_times = observed.difference(expected)
    if len(missing_times) or len(extra_times):
        raise ValueError(
            f"assignment coverage mismatch seed={seed} missing={len(missing_times)} extra={len(extra_times)}"
        )
    return raw.set_index("decision_close_time")["cluster_id"].reindex(expected).reset_index(drop=True)


def fit_2023_scaler(
    frame: pd.DataFrame, features: list[str], train_end: str
) -> tuple[StandardScaler, np.ndarray, np.ndarray]:
    train_mask = frame["decision_close_time"] < pd.Timestamp(train_end)
    train_mask &= frame["decision_close_time"] >= pd.Timestamp("2023-01-01 00:00:00")
    if int(train_mask.sum()) < 2:
        raise ValueError("insufficient 2023 rows to fit scaler")
    scaler = StandardScaler().fit(frame.loc[train_mask, features].to_numpy(dtype=float))
    transformed = scaler.transform(frame[features].to_numpy(dtype=float))
    return scaler, transformed, train_mask.to_numpy(dtype=bool)


def centroids(matrix: np.ndarray, labels: np.ndarray, k: int) -> np.ndarray:
    result = np.empty((k, matrix.shape[1]), dtype=float)
    for cluster_id in range(k):
        mask = labels == cluster_id
        if not mask.any():
            raise ValueError(f"empty cluster {cluster_id}")
        result[cluster_id] = matrix[mask].mean(axis=0)
    return result


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    denominator = a_norm @ b_norm.T
    numerator = a @ b.T
    return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)


def align_to_reference(reference: np.ndarray, other: np.ndarray) -> dict[int, int]:
    distances = np.linalg.norm(reference[:, None, :] - other[None, :, :], axis=2)
    ref_indices, other_indices = linear_sum_assignment(distances)
    return {int(other_id): int(ref_id) for ref_id, other_id in zip(ref_indices, other_indices)}


def pf(values: pd.Series) -> float:
    gain = float(values[values > 0].sum())
    loss = float(values[values < 0].sum())
    if loss == 0:
        return math.inf if gain > 0 else math.nan
    return gain / abs(loss)


def cluster_metric_rows(frame: pd.DataFrame, labels: np.ndarray, k: int, cutoff: str) -> list[dict[str, Any]]:
    work = frame[["decision_close_time", "r_value"]].copy()
    work["cluster_id"] = labels
    cutoff_ts = pd.Timestamp(cutoff)
    windows = {
        "all": pd.Series(True, index=work.index),
        "pre_2026": work["decision_close_time"] < pd.Timestamp("2026-01-01"),
        "2023": work["decision_close_time"].dt.year == 2023,
        "2024": work["decision_close_time"].dt.year == 2024,
        "2025": work["decision_close_time"].dt.year == 2025,
        "2026_diagnostic_to_cutoff": (work["decision_close_time"].dt.year == 2026)
        & (work["decision_close_time"] <= cutoff_ts),
        "fresh_post_cutoff": work["decision_close_time"] > cutoff_ts,
    }
    rows: list[dict[str, Any]] = []
    for window_name, window_mask in windows.items():
        subset = work.loc[window_mask]
        for cluster_id in range(k):
            group = subset[subset["cluster_id"] == cluster_id]
            rows.append(
                {
                    "window": window_name,
                    "cluster_id": cluster_id,
                    "trades": len(group),
                    "wins": int((group["r_value"] > 0).sum()),
                    "win_rate": float((group["r_value"] > 0).mean()) if len(group) else math.nan,
                    "profit_factor": pf(group["r_value"]),
                    "total_r": float(group["r_value"].sum()),
                }
            )
    return rows


def run(args: argparse.Namespace) -> int:
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("audit_only") is not True:
        raise ValueError("audit_only=true required")
    frame = load_feature_registry(args.feature_registry, config)
    assignments = parse_assignment_args(args.assignment)
    required_seeds = set(config["seeds"])
    if set(assignments) != required_seeds:
        raise ValueError(f"seed set mismatch missing={sorted(required_seeds-set(assignments))} unexpected={sorted(set(assignments)-required_seeds)}")
    labels = {
        seed: load_assignment(path, seed, frame["decision_close_time"], int(config["k"])).to_numpy(dtype=int)
        for seed, path in assignments.items()
    }
    _, matrix, train_mask = fit_2023_scaler(
        frame, config["feature_columns"], config["training_end_exclusive"]
    )
    k = int(config["k"])
    reference_seed = int(config["reference_seed"])
    reference_labels = labels[reference_seed]
    # Alignment and centroid interpretation are frozen to the 2023 training region.
    # Later periods can diagnose persistence but cannot redefine the motifs.
    reference_centroids = centroids(matrix[train_mask], reference_labels[train_mask], k)
    cutoff = pd.Timestamp(config["fresh_cutoff_mt5_server_close"])
    time_values = frame["decision_close_time"]
    stability_windows = {
        "train_2023": train_mask,
        "pre_2026": (time_values < pd.Timestamp("2026-01-01")).to_numpy(dtype=bool),
        "2026_diagnostic_to_cutoff": (
            (time_values >= pd.Timestamp("2026-01-01")) & (time_values <= cutoff)
        ).to_numpy(dtype=bool),
        "fresh_post_cutoff": (time_values > cutoff).to_numpy(dtype=bool),
    }

    alignment_rows: list[dict[str, Any]] = []
    membership_rows: list[dict[str, Any]] = []
    aligned_labels: dict[int, np.ndarray] = {reference_seed: reference_labels.copy()}
    for seed in sorted(labels):
        current_centroids = centroids(matrix[train_mask], labels[seed][train_mask], k)
        mapping = align_to_reference(reference_centroids, current_centroids)
        mapped = np.array([mapping[int(value)] for value in labels[seed]], dtype=int)
        aligned_labels[seed] = mapped
        cosine = cosine_similarity_matrix(reference_centroids, current_centroids)
        for other_cluster, ref_cluster in sorted(mapping.items(), key=lambda item: item[1]):
            for window_name, window_mask in stability_windows.items():
                ref_mask = (reference_labels == ref_cluster) & window_mask
                mapped_mask = (mapped == ref_cluster) & window_mask
                intersection = int(np.logical_and(ref_mask, mapped_mask).sum())
                union = int(np.logical_or(ref_mask, mapped_mask).sum())
                membership_rows.append(
                    {
                        "seed": seed,
                        "window": window_name,
                        "reference_cluster_id": ref_cluster,
                        "source_cluster_id": other_cluster,
                        "reference_members": int(ref_mask.sum()),
                        "source_members": int(mapped_mask.sum()),
                        "membership_jaccard": intersection / union if union else math.nan,
                        "centroid_euclidean_train_2023": float(
                            np.linalg.norm(reference_centroids[ref_cluster] - current_centroids[other_cluster])
                        ),
                        "centroid_cosine_train_2023": float(cosine[ref_cluster, other_cluster]),
                    }
                )
        for window_name, window_mask in stability_windows.items():
            if int(window_mask.sum()) == 0:
                ari = nmi = exact = math.nan
            else:
                ari = adjusted_rand_score(reference_labels[window_mask], mapped[window_mask])
                nmi = normalized_mutual_info_score(reference_labels[window_mask], mapped[window_mask])
                exact = float((reference_labels[window_mask] == mapped[window_mask]).mean())
            alignment_rows.append(
                {
                    "seed": seed,
                    "window": window_name,
                    "adjusted_rand_vs_reference": ari,
                    "normalized_mutual_info_vs_reference": nmi,
                    "exact_aligned_membership_fraction": exact,
                    "mapping_source_to_reference": json.dumps(mapping, sort_keys=True),
                }
            )

    attribution_rows: list[dict[str, Any]] = []
    for cluster_id in range(k):
        values = reference_centroids[cluster_id]
        order = np.argsort(np.abs(values))[::-1]
        for rank, feature_index in enumerate(order, start=1):
            attribution_rows.append(
                {
                    "reference_seed": reference_seed,
                    "cluster_id": cluster_id,
                    "rank_by_abs_centroid_z": rank,
                    "feature": config["feature_columns"][int(feature_index)],
                    "centroid_z": float(values[feature_index]),
                    "abs_centroid_z": float(abs(values[feature_index])),
                    "is_reference_excluded_cluster": cluster_id in config["reference_excluded_cluster_ids"],
                }
            )

    metrics = pd.DataFrame(
        cluster_metric_rows(frame, reference_labels, k, config["fresh_cutoff_mt5_server_close"])
    )
    membership = pd.DataFrame(membership_rows)
    alignment = pd.DataFrame(alignment_rows)
    attribution = pd.DataFrame(attribution_rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.output_dir / "reference_cluster_metrics.csv", index=False)
    membership.to_csv(args.output_dir / "seed_membership_stability.csv", index=False)
    alignment.to_csv(args.output_dir / "seed_global_alignment.csv", index=False)
    attribution.to_csv(args.output_dir / "reference_centroid_feature_attribution.csv", index=False)

    excluded = set(config["reference_excluded_cluster_ids"])
    excluded_stability = membership[
        membership["reference_cluster_id"].isin(excluded)
        & (membership["window"] == "pre_2026")
    ]
    summary = {
        "audit_id": config["audit_id"],
        "status": "OUTPUTS_GENERATED_AUDIT_ONLY",
        "audit_only": True,
        "candidate_logic_changed": False,
        "watch_id": config["watch_id"],
        "reference_seed": reference_seed,
        "reference_excluded_cluster_ids": sorted(excluded),
        "seeds": sorted(labels),
        "mean_excluded_motif_membership_jaccard_nonreference": safe_number(
            excluded_stability.loc[excluded_stability["seed"] != reference_seed, "membership_jaccard"].mean()
        ),
        "min_excluded_motif_membership_jaccard_nonreference": safe_number(
            excluded_stability.loc[excluded_stability["seed"] != reference_seed, "membership_jaccard"].min()
        ),
        "mean_excluded_motif_centroid_cosine_nonreference": safe_number(
            excluded_stability.loc[excluded_stability["seed"] != reference_seed, "centroid_cosine_train_2023"].mean()
        ),
        "interpretation": "Cluster IDs are arbitrary across seeds; aligned centroid and membership stability are diagnostics only.",
        "2026_policy": config["2026_policy"],
        "inputs": {
            "feature_registry": {"path": str(args.feature_registry), "sha256": sha256_file(args.feature_registry)},
            "assignments": {str(seed): {"path": str(path), "sha256": sha256_file(path)} for seed, path in sorted(assignments.items())},
        },
        "boundaries": config["boundaries"],
    }
    dump_json(args.output_dir / "centroid_seed_stability_summary.json", summary)
    manifest = {
        "audit_id": config["audit_id"],
        "config_sha256": sha256_file(args.config),
        "outputs": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(args.output_dir.iterdir())
            if path.is_file() and path.name != "manifest.json"
        },
    }
    dump_json(args.output_dir / "manifest.json", manifest)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/gold_ml_v1/watch014_centroid_seed_stability_audit_20260624.json"))
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--assignment", action="append", default=[], metavar="SEED=CSV")
    parser.add_argument("--output-dir", type=Path, default=Path("FX_OUTPUTS/gold_ml_v1/audits/GML1-BATCH-016-watch014-centroid"))
    return parser


def main() -> int:
    try:
        return run(build_parser().parse_args())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
