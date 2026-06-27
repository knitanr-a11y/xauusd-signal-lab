from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_ml_native_candidate_proposals as canonical

EXPECTED_FEATURE_SHA256 = canonical.EXPECTED_FEATURE_SHA256
ACCEPTED_V1_IDS = {
    "GML1-MLC-001-L",
    "GML1-MLC-001-S",
    "GML1-MLC-003-L",
    "GML1-MLC-003-S",
    "GML1-MLC-006-L",
    "GML1-MLC-006-S",
}
REVISED_V2_IDS = {
    "GML1-MLC-002-L",
    "GML1-MLC-002-S",
    "GML1-MLC-004-L",
    "GML1-MLC-004-S",
    "GML1-MLC-005-L",
    "GML1-MLC-005-S",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build combined accepted-v1 plus density-v2 MLR1 primary proposals"
    )
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-contract", type=Path, required=True)
    parser.add_argument("--v1-candidate-contract", type=Path, required=True)
    parser.add_argument("--v2-candidate-contract", type=Path, required=True)
    parser.add_argument("--v1-density-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def revised_v2_states(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    c = lambda name: canonical.current(frame, name)
    p = lambda name: canonical.previous_exact(frame, name)
    between = canonical.between
    return {
        "GML1-MLC-002-L": {
            "family": "LOW_VOL_BOLLINGER_BREAKOUT",
            "direction": "LONG",
            "state": (
                (c("m15_atr14_percentile_lag1_256") <= 0.30)
                & (c("m15_bb20_width_atr14") <= 2.50)
                & (p("m15_bb20_close_location") <= 1.0)
                & (c("m15_bb20_close_location") > 1.0)
                & (c("m15_body_fraction") >= 0.50)
                & (c("m15_tick_volume_ratio20_lagbase") >= 1.15)
            ),
        },
        "GML1-MLC-002-S": {
            "family": "LOW_VOL_BOLLINGER_BREAKOUT",
            "direction": "SHORT",
            "state": (
                (c("m15_atr14_percentile_lag1_256") <= 0.30)
                & (c("m15_bb20_width_atr14") <= 2.50)
                & (p("m15_bb20_close_location") >= 0.0)
                & (c("m15_bb20_close_location") < 0.0)
                & (c("m15_body_fraction") >= 0.50)
                & (c("m15_tick_volume_ratio20_lagbase") >= 1.15)
            ),
        },
        "GML1-MLC-004-L": {
            "family": "LOW_ADX_RANGE_REJECTION",
            "direction": "LONG",
            "state": (
                (c("h1_adx14_scaled") <= 0.20)
                & (c("h4_adx14_scaled") <= 0.25)
                & between(c("m15_distance_from_prev_low_20_atr14"), -0.25, 0.35)
                & (c("m15_lower_wick_fraction") >= 0.35)
            ),
        },
        "GML1-MLC-004-S": {
            "family": "LOW_ADX_RANGE_REJECTION",
            "direction": "SHORT",
            "state": (
                (c("h1_adx14_scaled") <= 0.20)
                & (c("h4_adx14_scaled") <= 0.25)
                & between(c("m15_distance_from_prev_high_20_atr14"), -0.35, 0.25)
                & (c("m15_upper_wick_fraction") >= 0.35)
            ),
        },
        "GML1-MLC-005-L": {
            "family": "HIGH_VOL_EXHAUSTION_REVERSAL",
            "direction": "LONG",
            "state": (
                (c("m15_atr14_percentile_lag1_256") >= 0.75)
                & (c("m15_rsi14_centered") <= -0.35)
                & (c("m15_range_atr14") >= 1.00)
                & (c("m15_lower_wick_fraction") >= 0.40)
            ),
        },
        "GML1-MLC-005-S": {
            "family": "HIGH_VOL_EXHAUSTION_REVERSAL",
            "direction": "SHORT",
            "state": (
                (c("m15_atr14_percentile_lag1_256") >= 0.75)
                & (c("m15_rsi14_centered") >= 0.35)
                & (c("m15_range_atr14") >= 1.00)
                & (c("m15_upper_wick_fraction") >= 0.40)
            ),
        },
    }


def combined_candidate_states(
    frame: pd.DataFrame, candidate_contract: dict[str, Any]
) -> list[dict[str, Any]]:
    canonical_by_id = {
        item["candidate_id"]: item for item in canonical.candidate_states(frame)
    }
    revised = revised_v2_states(frame)
    versions = candidate_contract["candidate_definition_versions"]
    result: list[dict[str, Any]] = []

    for candidate_id in candidate_contract["candidate_ids"]:
        version = versions[candidate_id]
        if candidate_id in ACCEPTED_V1_IDS:
            if version != "v1":
                raise ValueError(f"Accepted v1 candidate has wrong version: {candidate_id}")
            source = canonical_by_id[candidate_id]
        elif candidate_id in REVISED_V2_IDS:
            if version != "v2-density":
                raise ValueError(f"Revised candidate has wrong version: {candidate_id}")
            source = revised[candidate_id]
            v1_state = canonical_by_id[candidate_id]["state"].fillna(False)
            v2_state = source["state"].fillna(False)
            narrowed_rows = int((v1_state & ~v2_state).sum())
            if narrowed_rows:
                raise AssertionError(
                    f"Density v2 is not a pure broadening for {candidate_id}: {narrowed_rows} v1 rows removed"
                )
        else:
            raise ValueError(f"Unapproved candidate ID in combined contract: {candidate_id}")

        result.append({
            "candidate_id": candidate_id,
            "candidate_definition_version": version,
            "family": source["family"],
            "direction": source["direction"],
            "state": source["state"].fillna(False).astype(bool),
        })
    return result


def build_proposals(
    features: pd.DataFrame,
    model_columns: list[str],
    candidate_contract: dict[str, Any],
) -> pd.DataFrame:
    frame = features.sort_values("decision_time", kind="mergesort").reset_index(drop=True)
    definitions = combined_candidate_states(frame, candidate_contract)
    parts: list[pd.DataFrame] = []
    for item in definitions:
        selected = canonical.onset(item["state"], frame["decision_time"])
        proposal = frame.loc[selected, ["decision_time"] + model_columns].copy()
        proposal.insert(1, "candidate_id", item["candidate_id"])
        proposal.insert(2, "candidate_definition_version", item["candidate_definition_version"])
        proposal.insert(3, "candidate_family", item["family"])
        proposal.insert(4, "direction", item["direction"])
        proposal.insert(5, "proposal_strength", 1.0)
        parts.append(proposal)
    result = pd.concat(parts, ignore_index=True)
    return result.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)


def proposal_summary(
    proposals: pd.DataFrame,
    candidate_contract: dict[str, Any],
) -> dict[str, Any]:
    candidate_counts: list[dict[str, Any]] = []
    for candidate_id in candidate_contract["candidate_ids"]:
        subset = proposals.loc[proposals["candidate_id"] == candidate_id]
        years = sorted(pd.to_datetime(subset["decision_time"]).dt.year.unique().tolist())
        candidate_counts.append({
            "candidate_id": candidate_id,
            "candidate_definition_version": candidate_contract["candidate_definition_versions"][candidate_id],
            "direction": None if subset.empty else str(subset["direction"].iloc[0]),
            "family": None if subset.empty else str(subset["candidate_family"].iloc[0]),
            "proposals": int(len(subset)),
            "years": years,
            "year_count": len(years),
            "first_decision": None if subset.empty else str(subset["decision_time"].iloc[0]),
            "last_decision": None if subset.empty else str(subset["decision_time"].iloc[-1]),
        })

    by_decision = proposals.groupby("decision_time", sort=True)
    per_decision = by_decision.size()
    directions_per_decision = by_decision["direction"].nunique()
    pair_counter: Counter[tuple[str, str]] = Counter()
    for ids in by_decision["candidate_id"].apply(lambda values: sorted(set(values))):
        pair_counter.update(itertools.combinations(ids, 2))

    direction_counts = {
        str(key): int(value)
        for key, value in proposals["direction"].value_counts().sort_index().items()
    }
    long_count = direction_counts.get("LONG", 0)
    short_count = direction_counts.get("SHORT", 0)
    return {
        "candidate_counts": candidate_counts,
        "total_proposals": int(len(proposals)),
        "unique_decisions": int(proposals["decision_time"].nunique()),
        "decisions_with_multiple_candidates": int((per_decision > 1).sum()),
        "maximum_candidates_same_decision": int(per_decision.max()) if len(per_decision) else 0,
        "same_direction_multi_candidate_decisions": int(((per_decision > 1) & (directions_per_decision == 1)).sum()),
        "long_short_conflict_decisions": int((directions_per_decision > 1).sum()),
        "direction_counts": direction_counts,
        "long_to_short_ratio": None if short_count == 0 else long_count / short_count,
        "candidate_pair_overlap_counts": [
            {"candidate_a": pair[0], "candidate_b": pair[1], "decisions": int(count)}
            for pair, count in sorted(pair_counter.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def _expected_accepted_v1_counts(density_audit: dict[str, Any]) -> dict[str, int]:
    return {
        str(item["candidate_id"]): int(item["proposals"])
        for item in density_audit["accepted_v1_candidates"]
        if item["candidate_id"] in ACCEPTED_V1_IDS
    }


def main() -> int:
    args = build_parser().parse_args()
    feature_sha = canonical.sha256_file(args.feature_registry)
    if feature_sha != EXPECTED_FEATURE_SHA256:
        raise ValueError("Feature registry SHA256 mismatch")

    feature_contract = json.loads(args.feature_contract.read_text(encoding="utf-8"))
    v1_contract = json.loads(args.v1_candidate_contract.read_text(encoding="utf-8"))
    v2_contract = json.loads(args.v2_candidate_contract.read_text(encoding="utf-8"))
    density_audit = json.loads(args.v1_density_audit.read_text(encoding="utf-8"))

    if v1_contract.get("version") != "v1":
        raise ValueError("Source candidate contract is not immutable v1")
    if v2_contract.get("version") != "v2-density":
        raise ValueError("Combined candidate contract is not v2-density")
    if v2_contract["feature_registry_sha256"] != EXPECTED_FEATURE_SHA256:
        raise ValueError("v2 contract feature SHA mismatch")
    if set(v2_contract["candidate_ids"]) != ACCEPTED_V1_IDS | REVISED_V2_IDS:
        raise ValueError("Combined candidate universe is not the frozen twelve-candidate primary universe")
    if len(v2_contract["candidate_ids"]) != 12:
        raise ValueError("Combined candidate IDs are duplicated")
    if density_audit["density_gate"]["labels_joined"] is not False:
        raise ValueError("v1 density audit is not label-free")
    if density_audit["density_gate"]["performance_calculated"] is not False:
        raise ValueError("v1 density audit includes candidate performance")

    model_columns = feature_contract["model_feature_columns"]
    features = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    missing = sorted(set(model_columns + ["decision_time"]) - set(features.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    if not np.isfinite(features[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite feature values")

    proposals = build_proposals(features, model_columns, v2_contract)
    summary = proposal_summary(proposals, v2_contract)

    expected_v1 = _expected_accepted_v1_counts(density_audit)
    actual_v1 = {
        item["candidate_id"]: item["proposals"]
        for item in summary["candidate_counts"]
        if item["candidate_id"] in ACCEPTED_V1_IDS
    }
    if actual_v1 != expected_v1:
        raise AssertionError(
            f"Accepted v1 proposal counts changed: actual={actual_v1}, expected={expected_v1}"
        )

    density = v2_contract["density_gate"]
    for item in summary["candidate_counts"]:
        item["density_pass"] = (
            density["minimum_per_candidate"]
            <= item["proposals"]
            <= density["maximum_per_candidate"]
            and item["year_count"] >= density["minimum_years"]
        )
    all_density_pass = all(item["density_pass"] for item in summary["candidate_counts"])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "mlr1_ml_native_candidate_proposals_combined_v1v2.csv.gz"
    canonical.deterministic_csv_gzip(proposals, output_path)
    summary.update({
        "system_id": "GML1-MLR1",
        "stage": "ML-05A",
        "status": (
            "COMBINED_PRIMARY_DENSITY_ACCEPTED_ML05B_REVIEW_REQUIRED_AUDIT_ONLY"
            if all_density_pass
            else "COMBINED_PRIMARY_DENSITY_FAILED_REDEFINITION_REQUIRED_AUDIT_ONLY"
        ),
        "feature_registry_sha256": feature_sha,
        "feature_contract_sha256": canonical.sha256_file(args.feature_contract),
        "source_v1_candidate_contract_sha256": canonical.sha256_file(args.v1_candidate_contract),
        "v2_candidate_contract_sha256": canonical.sha256_file(args.v2_candidate_contract),
        "v1_density_audit_sha256": canonical.sha256_file(args.v1_density_audit),
        "output_path": str(output_path),
        "output_columns": int(len(proposals.columns)),
        "output_sha256": canonical.sha256_file(output_path),
        "accepted_v1_counts_unchanged": True,
        "all_density_pass": all_density_pass,
        "ml05b_candidate_density_gate_pass": all_density_pass,
        "ml05b_label_join_executed": False,
        "labels_joined": False,
        "candidate_performance_calculated": False,
        "one_open_applied": False,
        "dedup_applied": False,
        "audit_only": True,
        "model_trained": False,
        "model_promoted": False,
        "shadow_ready": False,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    })
    canonical.write_json(
        args.output_dir / "mlr1_ml_native_candidate_proposal_summary_combined_v1v2.json",
        summary,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
