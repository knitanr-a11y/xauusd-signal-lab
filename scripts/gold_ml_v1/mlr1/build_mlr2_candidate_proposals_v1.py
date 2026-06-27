from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ONE_M15 = pd.Timedelta(minutes=15)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )


def deterministic_csv_gzip(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                frame.to_csv(
                    text,
                    index=False,
                    date_format="%Y-%m-%d %H:%M:%S",
                    float_format="%.12g",
                    lineterminator="\n",
                )


def previous_exact(frame: pd.DataFrame, column: str, bars: int = 1) -> pd.Series:
    exact = frame["decision_time"].diff(bars).eq(ONE_M15 * bars)
    return frame[column].shift(bars).where(exact).astype(float)


def cross_up(frame: pd.DataFrame, column: str, level: float) -> pd.Series:
    return (previous_exact(frame, column) <= level) & (frame[column].astype(float) > level)


def cross_down(frame: pd.DataFrame, column: str, level: float) -> pd.Series:
    return (previous_exact(frame, column) >= level) & (frame[column].astype(float) < level)


def onset(state: pd.Series, decision_time: pd.Series) -> pd.Series:
    exact = decision_time.diff().eq(ONE_M15)
    previous = state.shift(1, fill_value=False).where(exact, False)
    return state.fillna(False) & ~previous.fillna(False)


def candidate_definitions(frame: pd.DataFrame) -> list[dict[str, Any]]:
    current = lambda name: frame[name].astype(float)
    previous = lambda name, bars=1: previous_exact(frame, name, bars)
    definitions: list[dict[str, Any]] = []

    definitions.extend(
        [
            {
                "candidate_id": "GML1-MLR2-C001-L",
                "family": "H1_TREND_PULLBACK_RESUMPTION",
                "direction": "LONG",
                "environment": (current("h1_ema20_ema50_gap_atr14") >= 0.08)
                & (current("h1_ema50_ema200_gap_atr14") >= -0.05)
                & (current("h1_adx14_scaled") >= 0.16)
                & (current("h4_ema20_ema50_gap_atr14") >= -0.20),
                "setup": previous("m15_rsi14_centered") <= -0.10,
                "confirmation": cross_up(frame, "m15_rsi14_centered", 0.0)
                & (current("m15_macd_hist_atr14") > previous("m15_macd_hist_atr14"))
                & (current("m15_signed_body_atr14") >= 0.05)
                & (current("m15_close_location") >= 0.52),
            },
            {
                "candidate_id": "GML1-MLR2-C001-S",
                "family": "H1_TREND_PULLBACK_RESUMPTION",
                "direction": "SHORT",
                "environment": (current("h1_ema20_ema50_gap_atr14") <= -0.08)
                & (current("h1_ema50_ema200_gap_atr14") <= 0.05)
                & (current("h1_adx14_scaled") >= 0.16)
                & (current("h4_ema20_ema50_gap_atr14") <= 0.20),
                "setup": previous("m15_rsi14_centered") >= 0.10,
                "confirmation": cross_down(frame, "m15_rsi14_centered", 0.0)
                & (current("m15_macd_hist_atr14") < previous("m15_macd_hist_atr14"))
                & (current("m15_signed_body_atr14") <= -0.05)
                & (current("m15_close_location") <= 0.48),
            },
        ]
    )

    definitions.extend(
        [
            {
                "candidate_id": "GML1-MLR2-C002-L",
                "family": "MULTIBAR_COMPRESSION_BREAKOUT",
                "direction": "LONG",
                "environment": (previous("m15_atr14_percentile_lag1_256") <= 0.35)
                & (previous("m15_atr14_percentile_lag1_256", 2) <= 0.40),
                "setup": previous("m15_bb20_close_location") <= 1.0,
                "confirmation": (current("m15_bb20_close_location") > 1.0)
                & (current("m15_distance_from_prev_high_20_atr14") >= 0.0)
                & (current("m15_body_fraction") >= 0.55)
                & (current("m15_tick_volume_ratio20_lagbase") >= 1.15)
                & (current("h1_ema20_slope4_atr14") >= 0.0)
                & (current("h1_adx14_scaled") >= 0.15),
            },
            {
                "candidate_id": "GML1-MLR2-C002-S",
                "family": "MULTIBAR_COMPRESSION_BREAKOUT",
                "direction": "SHORT",
                "environment": (previous("m15_atr14_percentile_lag1_256") <= 0.35)
                & (previous("m15_atr14_percentile_lag1_256", 2) <= 0.40),
                "setup": previous("m15_bb20_close_location") >= 0.0,
                "confirmation": (current("m15_bb20_close_location") < 0.0)
                & (current("m15_distance_from_prev_low_20_atr14") <= 0.0)
                & (current("m15_body_fraction") >= 0.55)
                & (current("m15_tick_volume_ratio20_lagbase") >= 1.15)
                & (current("h1_ema20_slope4_atr14") <= 0.0)
                & (current("h1_adx14_scaled") >= 0.15),
            },
        ]
    )

    definitions.extend(
        [
            {
                "candidate_id": "GML1-MLR2-C003-L",
                "family": "FAILED_BREAKOUT_RECLAIM",
                "direction": "LONG",
                "environment": current("h4_adx14_scaled") <= 0.35,
                "setup": previous("m15_distance_from_prev_low_20_atr14") <= -0.05,
                "confirmation": (current("m15_distance_from_prev_low_20_atr14") > -0.05)
                & (current("m15_lower_wick_fraction") >= 0.30)
                & (current("m15_close_location") >= 0.60)
                & (current("m15_signed_body_atr14") >= 0.05)
                & (current("m15_rsi14_centered") > previous("m15_rsi14_centered")),
            },
            {
                "candidate_id": "GML1-MLR2-C003-S",
                "family": "FAILED_BREAKOUT_RECLAIM",
                "direction": "SHORT",
                "environment": current("h4_adx14_scaled") <= 0.35,
                "setup": previous("m15_distance_from_prev_high_20_atr14") >= 0.05,
                "confirmation": (current("m15_distance_from_prev_high_20_atr14") < 0.05)
                & (current("m15_upper_wick_fraction") >= 0.30)
                & (current("m15_close_location") <= 0.40)
                & (current("m15_signed_body_atr14") <= -0.05)
                & (current("m15_rsi14_centered") < previous("m15_rsi14_centered")),
            },
        ]
    )

    definitions.extend(
        [
            {
                "candidate_id": "GML1-MLR2-C004-L",
                "family": "ROLLING_EXTREME_RETEST_CONTINUATION",
                "direction": "LONG",
                "environment": (current("h1_ema20_ema50_gap_atr14") >= 0.0)
                & (current("h4_ema20_ema50_gap_atr14") >= 0.0)
                & (current("h1_adx14_scaled") >= 0.12),
                "setup": previous("m15_distance_from_prev_high_50_atr14") >= -0.05,
                "confirmation": (current("m15_distance_from_prev_high_50_atr14") >= -0.50)
                & (current("m15_lower_wick_fraction") >= 0.12)
                & (current("m15_close_location") >= 0.50)
                & (current("m15_signed_body_atr14") >= 0.0),
            },
            {
                "candidate_id": "GML1-MLR2-C004-S",
                "family": "ROLLING_EXTREME_RETEST_CONTINUATION",
                "direction": "SHORT",
                "environment": (current("h1_ema20_ema50_gap_atr14") <= 0.0)
                & (current("h4_ema20_ema50_gap_atr14") <= 0.0)
                & (current("h1_adx14_scaled") >= 0.12),
                "setup": previous("m15_distance_from_prev_low_50_atr14") <= 0.05,
                "confirmation": (current("m15_distance_from_prev_low_50_atr14") <= 0.50)
                & (current("m15_upper_wick_fraction") >= 0.12)
                & (current("m15_close_location") <= 0.50)
                & (current("m15_signed_body_atr14") <= 0.0),
            },
        ]
    )

    definitions.extend(
        [
            {
                "candidate_id": "GML1-MLR2-C005-L",
                "family": "HIGH_VOL_EXHAUSTION_TURN",
                "direction": "LONG",
                "environment": (current("m15_atr14_percentile_lag1_256") >= 0.60)
                & (current("m15_range_atr14") >= 0.80),
                "setup": current("m15_rsi14_centered") <= -0.20,
                "confirmation": (current("m15_lower_wick_fraction") >= 0.25)
                & (current("m15_close_location") >= 0.50)
                & (current("m15_macd_hist_atr14") > previous("m15_macd_hist_atr14"))
                & (current("m15_signed_body_atr14") >= -0.15),
            },
            {
                "candidate_id": "GML1-MLR2-C005-S",
                "family": "HIGH_VOL_EXHAUSTION_TURN",
                "direction": "SHORT",
                "environment": (current("m15_atr14_percentile_lag1_256") >= 0.60)
                & (current("m15_range_atr14") >= 0.80),
                "setup": current("m15_rsi14_centered") >= 0.20,
                "confirmation": (current("m15_upper_wick_fraction") >= 0.25)
                & (current("m15_close_location") <= 0.50)
                & (current("m15_macd_hist_atr14") < previous("m15_macd_hist_atr14"))
                & (current("m15_signed_body_atr14") <= 0.15),
            },
        ]
    )

    for definition in definitions:
        definition["state"] = (
            definition["environment"].fillna(False)
            & definition["setup"].fillna(False)
            & definition["confirmation"].fillna(False)
        )
    return definitions


def build_proposals(
    features: pd.DataFrame, model_columns: list[str]
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frame = features.sort_values("decision_time", kind="mergesort").reset_index(drop=True)
    parts: list[pd.DataFrame] = []
    audit: list[dict[str, Any]] = []
    for definition in candidate_definitions(frame):
        selected = onset(definition["state"], frame["decision_time"])
        proposal = frame.loc[selected, ["decision_time"] + model_columns].copy()
        proposal.insert(1, "candidate_id", definition["candidate_id"])
        proposal.insert(2, "candidate_definition_version", "mlr2-v1")
        proposal.insert(3, "candidate_family", definition["family"])
        proposal.insert(4, "direction", definition["direction"])
        proposal.insert(5, "proposal_strength", 1.0)
        parts.append(proposal)
        years = proposal["decision_time"].dt.year.value_counts().sort_index()
        audit.append(
            {
                "candidate_id": definition["candidate_id"],
                "candidate_family": definition["family"],
                "direction": definition["direction"],
                "events": int(len(proposal)),
                "years": {
                    str(int(year)): int(count) for year, count in years.items()
                },
                "year_count": int(len(years)),
                "first_decision": (
                    None if proposal.empty else str(proposal["decision_time"].min())
                ),
                "last_decision": (
                    None if proposal.empty else str(proposal["decision_time"].max())
                ),
            }
        )
    result = (
        pd.concat(parts, ignore_index=True)
        .sort_values(["decision_time", "candidate_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    return result, audit


def overlap_summary(proposals: pd.DataFrame) -> dict[str, Any]:
    groups = proposals.groupby("decision_time", sort=True)
    sizes = groups.size()
    directions = groups["direction"].nunique()
    pair_counts: dict[tuple[str, str], int] = {}
    for values in groups["candidate_id"].apply(lambda series: sorted(set(series))):
        for pair in combinations(values, 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    return {
        "unique_decisions": int(proposals["decision_time"].nunique()),
        "decisions_with_multiple_candidates": int((sizes > 1).sum()),
        "maximum_candidates_same_decision": int(sizes.max()),
        "same_direction_multi_candidate_decisions": int(
            ((sizes > 1) & (directions == 1)).sum()
        ),
        "long_short_conflict_decisions": int((directions > 1).sum()),
        "candidate_pair_overlap_counts": [
            {
                "candidate_a": pair[0],
                "candidate_b": pair[1],
                "decisions": count,
            }
            for pair, count in sorted(
                pair_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build label-free MLR2 v1 candidate proposals"
    )
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-columns", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    columns_contract = json.loads(args.feature_columns.read_text(encoding="utf-8"))
    model_columns = list(
        columns_contract.get(
            "model_feature_columns", columns_contract["market_feature_columns"]
        )
    )
    features = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    required = set(["decision_time"] + model_columns)
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Feature registry missing columns: {missing}")
    if features["decision_time"].duplicated().any():
        raise ValueError("Duplicate feature decision_time")
    if not features["decision_time"].is_monotonic_increasing:
        raise ValueError("Feature decision_time is not increasing")
    if not np.isfinite(features[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Feature registry contains nonfinite model values")

    proposals, candidate_audit = build_proposals(features, model_columns)
    for item in candidate_audit:
        item["density_pass"] = (
            100 <= item["events"] <= 5000 and item["year_count"] >= 3
        )
    if not all(item["density_pass"] for item in candidate_audit):
        raise AssertionError("At least one MLR2 candidate failed the density gate")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = args.output_dir / "mlr2_candidate_proposals_v1.csv.gz"
    summary_path = args.output_dir / "mlr2_candidate_proposal_summary_v1.json"
    deterministic_csv_gzip(proposals, proposal_path)
    summary = {
        "system_id": "GML1-MLR2",
        "stage": "CANDIDATE_REDESIGN_LABEL_FREE",
        "version": "v1",
        "status": "MLR2_V1_CANDIDATE_PROPOSALS_BUILT_DENSITY_PASS_AUDIT_ONLY",
        "feature_registry_sha256": sha256_file(args.feature_registry),
        "feature_columns_sha256": sha256_file(args.feature_columns),
        "feature_rows": int(len(features)),
        "model_feature_count": int(len(model_columns)),
        "candidate_count": int(len(candidate_audit)),
        "proposal_rows": int(len(proposals)),
        "direction_counts": {
            str(key): int(value)
            for key, value in proposals["direction"].value_counts().sort_index().items()
        },
        "candidate_counts": candidate_audit,
        "overlap": overlap_summary(proposals),
        "proposal_registry_sha256": sha256_file(proposal_path),
        "density_gate": {
            "minimum_events": 100,
            "maximum_events": 5000,
            "minimum_years": 3,
            "all_candidates_pass": True,
        },
        "labels_read": False,
        "candidate_performance_read": False,
        "old_candidate_registry_changed": False,
        "audit_only": True,
        "model_trained": False,
        "model_promoted": False,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
