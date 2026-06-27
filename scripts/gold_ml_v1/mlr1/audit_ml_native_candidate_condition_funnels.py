from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_ml_native_candidate_proposals as canonical

EXPECTED_FEATURE_SHA256 = canonical.EXPECTED_FEATURE_SHA256
FAILED_FAMILIES = {"MLC-002", "MLC-004", "MLC-005"}
FAILED_CANDIDATE_IDS = (
    "GML1-MLC-002-L",
    "GML1-MLC-002-S",
    "GML1-MLC-004-L",
    "GML1-MLC-004-S",
    "GML1-MLC-005-L",
    "GML1-MLC-005-S",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build label-free ML-05A v1 condition funnels for failed ML-native candidates"
    )
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-contract", type=Path, required=True)
    parser.add_argument("--candidate-contract", type=Path, required=True)
    parser.add_argument("--density-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _step(name: str, rule: str, condition: pd.Series) -> dict[str, Any]:
    return {
        "name": name,
        "rule": rule,
        "condition": condition.fillna(False).astype(bool),
    }


def failed_candidate_condition_steps(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    c = lambda name: canonical.current(frame, name)
    p = lambda name: canonical.previous_exact(frame, name)
    between = canonical.between

    return {
        "GML1-MLC-002-L": {
            "family_code": "MLC-002",
            "family": "LOW_VOL_BOLLINGER_BREAKOUT",
            "direction": "LONG",
            "steps": [
                _step("LOW_ATR_PERCENTILE", "m15_atr14_percentile_lag1_256 <= 0.30", c("m15_atr14_percentile_lag1_256") <= 0.30),
                _step("NARROW_BOLLINGER_WIDTH", "m15_bb20_width_atr14 <= 2.50", c("m15_bb20_width_atr14") <= 2.50),
                _step("PREVIOUS_NOT_ABOVE_UPPER_BAND", "previous_exact(m15_bb20_close_location) <= 1.0", p("m15_bb20_close_location") <= 1.0),
                _step("CURRENT_ABOVE_UPPER_BAND", "m15_bb20_close_location > 1.0", c("m15_bb20_close_location") > 1.0),
                _step("BODY_FRACTION", "m15_body_fraction >= 0.50", c("m15_body_fraction") >= 0.50),
                _step("VOLUME_EXPANSION", "m15_tick_volume_ratio20_lagbase >= 1.15", c("m15_tick_volume_ratio20_lagbase") >= 1.15),
                _step("H1_NOT_STRONGLY_BEARISH", "h1_ema20_ema50_gap_atr14 >= -0.20", c("h1_ema20_ema50_gap_atr14") >= -0.20),
            ],
        },
        "GML1-MLC-002-S": {
            "family_code": "MLC-002",
            "family": "LOW_VOL_BOLLINGER_BREAKOUT",
            "direction": "SHORT",
            "steps": [
                _step("LOW_ATR_PERCENTILE", "m15_atr14_percentile_lag1_256 <= 0.30", c("m15_atr14_percentile_lag1_256") <= 0.30),
                _step("NARROW_BOLLINGER_WIDTH", "m15_bb20_width_atr14 <= 2.50", c("m15_bb20_width_atr14") <= 2.50),
                _step("PREVIOUS_NOT_BELOW_LOWER_BAND", "previous_exact(m15_bb20_close_location) >= 0.0", p("m15_bb20_close_location") >= 0.0),
                _step("CURRENT_BELOW_LOWER_BAND", "m15_bb20_close_location < 0.0", c("m15_bb20_close_location") < 0.0),
                _step("BODY_FRACTION", "m15_body_fraction >= 0.50", c("m15_body_fraction") >= 0.50),
                _step("VOLUME_EXPANSION", "m15_tick_volume_ratio20_lagbase >= 1.15", c("m15_tick_volume_ratio20_lagbase") >= 1.15),
                _step("H1_NOT_STRONGLY_BULLISH", "h1_ema20_ema50_gap_atr14 <= 0.20", c("h1_ema20_ema50_gap_atr14") <= 0.20),
            ],
        },
        "GML1-MLC-004-L": {
            "family_code": "MLC-004",
            "family": "LOW_ADX_RANGE_REJECTION",
            "direction": "LONG",
            "steps": [
                _step("LOW_H1_ADX", "h1_adx14_scaled <= 0.20", c("h1_adx14_scaled") <= 0.20),
                _step("LOW_H4_ADX", "h4_adx14_scaled <= 0.25", c("h4_adx14_scaled") <= 0.25),
                _step("NEAR_PREVIOUS_LOW_20", "-0.25 <= m15_distance_from_prev_low_20_atr14 <= 0.35", between(c("m15_distance_from_prev_low_20_atr14"), -0.25, 0.35)),
                _step("LOWER_WICK_REJECTION", "m15_lower_wick_fraction >= 0.35", c("m15_lower_wick_fraction") >= 0.35),
                _step("POSITIVE_SIGNED_BODY", "m15_signed_body_atr14 > 0.0", c("m15_signed_body_atr14") > 0.0),
                _step("CLOSE_IN_UPPER_40_PERCENT", "m15_close_location >= 0.60", c("m15_close_location") >= 0.60),
                _step("RSI_DEPRESSED", "m15_rsi14_centered <= -0.15", c("m15_rsi14_centered") <= -0.15),
            ],
        },
        "GML1-MLC-004-S": {
            "family_code": "MLC-004",
            "family": "LOW_ADX_RANGE_REJECTION",
            "direction": "SHORT",
            "steps": [
                _step("LOW_H1_ADX", "h1_adx14_scaled <= 0.20", c("h1_adx14_scaled") <= 0.20),
                _step("LOW_H4_ADX", "h4_adx14_scaled <= 0.25", c("h4_adx14_scaled") <= 0.25),
                _step("NEAR_PREVIOUS_HIGH_20", "-0.35 <= m15_distance_from_prev_high_20_atr14 <= 0.25", between(c("m15_distance_from_prev_high_20_atr14"), -0.35, 0.25)),
                _step("UPPER_WICK_REJECTION", "m15_upper_wick_fraction >= 0.35", c("m15_upper_wick_fraction") >= 0.35),
                _step("NEGATIVE_SIGNED_BODY", "m15_signed_body_atr14 < 0.0", c("m15_signed_body_atr14") < 0.0),
                _step("CLOSE_IN_LOWER_40_PERCENT", "m15_close_location <= 0.40", c("m15_close_location") <= 0.40),
                _step("RSI_ELEVATED", "m15_rsi14_centered >= 0.15", c("m15_rsi14_centered") >= 0.15),
            ],
        },
        "GML1-MLC-005-L": {
            "family_code": "MLC-005",
            "family": "HIGH_VOL_EXHAUSTION_REVERSAL",
            "direction": "LONG",
            "steps": [
                _step("HIGH_ATR_PERCENTILE", "m15_atr14_percentile_lag1_256 >= 0.75", c("m15_atr14_percentile_lag1_256") >= 0.75),
                _step("RSI_OVERSOLD", "m15_rsi14_centered <= -0.35", c("m15_rsi14_centered") <= -0.35),
                _step("WIDE_RANGE", "m15_range_atr14 >= 1.00", c("m15_range_atr14") >= 1.00),
                _step("LOWER_WICK_EXHAUSTION", "m15_lower_wick_fraction >= 0.40", c("m15_lower_wick_fraction") >= 0.40),
                _step("CLOSE_RECOVERY", "m15_close_location >= 0.60", c("m15_close_location") >= 0.60),
                _step("NONNEGATIVE_SIGNED_BODY", "m15_signed_body_atr14 >= 0.0", c("m15_signed_body_atr14") >= 0.0),
                _step("H1_NOT_BULLISH", "h1_ema20_ema50_gap_atr14 <= 0.0", c("h1_ema20_ema50_gap_atr14") <= 0.0),
            ],
        },
        "GML1-MLC-005-S": {
            "family_code": "MLC-005",
            "family": "HIGH_VOL_EXHAUSTION_REVERSAL",
            "direction": "SHORT",
            "steps": [
                _step("HIGH_ATR_PERCENTILE", "m15_atr14_percentile_lag1_256 >= 0.75", c("m15_atr14_percentile_lag1_256") >= 0.75),
                _step("RSI_OVERBOUGHT", "m15_rsi14_centered >= 0.35", c("m15_rsi14_centered") >= 0.35),
                _step("WIDE_RANGE", "m15_range_atr14 >= 1.00", c("m15_range_atr14") >= 1.00),
                _step("UPPER_WICK_EXHAUSTION", "m15_upper_wick_fraction >= 0.40", c("m15_upper_wick_fraction") >= 0.40),
                _step("CLOSE_REJECTION", "m15_close_location <= 0.40", c("m15_close_location") <= 0.40),
                _step("NONPOSITIVE_SIGNED_BODY", "m15_signed_body_atr14 <= 0.0", c("m15_signed_body_atr14") <= 0.0),
                _step("H1_NOT_BEARISH", "h1_ema20_ema50_gap_atr14 >= 0.0", c("h1_ema20_ema50_gap_atr14") >= 0.0),
            ],
        },
    }


def _canonical_failed_states(frame: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        item["candidate_id"]: item["state"].fillna(False).astype(bool)
        for item in canonical.candidate_states(frame)
        if item["candidate_id"] in FAILED_CANDIDATE_IDS
    }


def _scope_masks(decision_time: pd.Series) -> list[tuple[str, int | None, pd.Series]]:
    years = decision_time.dt.year
    scopes: list[tuple[str, int | None, pd.Series]] = [
        ("FULL_SNAPSHOT", None, pd.Series(True, index=decision_time.index, dtype=bool))
    ]
    for year in sorted(int(value) for value in years.unique()):
        scopes.append(("CALENDAR_YEAR", year, years.eq(year)))
    return scopes


def build_condition_funnel(features: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = features.sort_values("decision_time", kind="mergesort").reset_index(drop=True)
    if frame["decision_time"].duplicated().any():
        raise ValueError("Duplicate decision_time rows in feature registry")

    definitions = failed_candidate_condition_steps(frame)
    canonical_states = _canonical_failed_states(frame)
    rows: list[dict[str, Any]] = []
    candidate_summary: list[dict[str, Any]] = []

    for candidate_id in FAILED_CANDIDATE_IDS:
        item = definitions[candidate_id]
        cumulative = pd.Series(True, index=frame.index, dtype=bool)
        stages: list[dict[str, Any]] = [{
            "stage_index": 0,
            "stage_type": "BASE",
            "stage_name": "ELIGIBLE_FEATURE_ROWS",
            "rule": "all eligible closed M15 feature rows",
            "condition": pd.Series(True, index=frame.index, dtype=bool),
            "cumulative": cumulative.copy(),
        }]

        for stage_index, step in enumerate(item["steps"], start=1):
            cumulative = cumulative & step["condition"]
            stages.append({
                "stage_index": stage_index,
                "stage_type": "CONDITION",
                "stage_name": step["name"],
                "rule": step["rule"],
                "condition": step["condition"],
                "cumulative": cumulative.copy(),
            })

        canonical_state = canonical_states[candidate_id]
        if not cumulative.equals(canonical_state):
            mismatch = int((cumulative != canonical_state).sum())
            raise AssertionError(f"Final cumulative state mismatch for {candidate_id}: {mismatch} rows")

        onset_mask = canonical.onset(cumulative, frame["decision_time"])
        stages.append({
            "stage_index": len(item["steps"]) + 1,
            "stage_type": "ONSET",
            "stage_name": "FALSE_TO_TRUE_ONSET",
            "rule": "final_state AND NOT previous_exact(final_state); M15 gaps reset previous state",
            "condition": onset_mask,
            "cumulative": onset_mask,
        })

        scopes = _scope_masks(frame["decision_time"])
        for scope_type, year, scope_mask in scopes:
            base_rows = int(scope_mask.sum())
            previous_rows = base_rows
            for stage in stages:
                stage_condition_rows = int((scope_mask & stage["condition"]).sum())
                cumulative_rows = int((scope_mask & stage["cumulative"]).sum())
                removed = previous_rows - cumulative_rows if stage["stage_index"] > 0 else 0
                rows.append({
                    "candidate_id": candidate_id,
                    "family_code": item["family_code"],
                    "candidate_family": item["family"],
                    "direction": item["direction"],
                    "scope_type": scope_type,
                    "calendar_year": year,
                    "stage_index": stage["stage_index"],
                    "stage_type": stage["stage_type"],
                    "stage_name": stage["stage_name"],
                    "rule": stage["rule"],
                    "scope_rows": base_rows,
                    "standalone_condition_true_rows": stage_condition_rows,
                    "cumulative_rows": cumulative_rows,
                    "removed_at_stage": removed,
                    "cumulative_share_of_scope": 0.0 if base_rows == 0 else cumulative_rows / base_rows,
                    "retention_from_previous_stage": 0.0 if previous_rows == 0 else cumulative_rows / previous_rows,
                })
                previous_rows = cumulative_rows

        proposal_times = frame.loc[onset_mask, "decision_time"]
        years = sorted(int(value) for value in proposal_times.dt.year.unique())
        candidate_summary.append({
            "candidate_id": candidate_id,
            "family_code": item["family_code"],
            "candidate_family": item["family"],
            "direction": item["direction"],
            "state_true_rows": int(cumulative.sum()),
            "onset_proposals": int(onset_mask.sum()),
            "years": years,
            "year_count": len(years),
            "first_decision": None if proposal_times.empty else str(proposal_times.iloc[0]),
            "last_decision": None if proposal_times.empty else str(proposal_times.iloc[-1]),
            "canonical_final_state_match": True,
        })

    funnel = pd.DataFrame(rows).sort_values(
        ["candidate_id", "scope_type", "calendar_year", "stage_index"],
        kind="mergesort",
        na_position="first",
    ).reset_index(drop=True)
    return funnel, {"candidate_counts": candidate_summary}


def _expected_failed_counts(density_audit: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in density_audit["failed_v1_candidates"]:
        candidate_id = str(item["candidate_id"])
        if candidate_id in FAILED_CANDIDATE_IDS:
            result[candidate_id] = int(item["proposals"])
    missing = sorted(set(FAILED_CANDIDATE_IDS) - set(result))
    if missing:
        raise ValueError(f"Density audit missing failed candidate counts: {missing}")
    return result


def main() -> int:
    args = build_parser().parse_args()
    feature_sha = canonical.sha256_file(args.feature_registry)
    if feature_sha != EXPECTED_FEATURE_SHA256:
        raise ValueError("Feature registry SHA256 mismatch")

    feature_contract = json.loads(args.feature_contract.read_text(encoding="utf-8"))
    candidate_contract = json.loads(args.candidate_contract.read_text(encoding="utf-8"))
    density_audit = json.loads(args.density_audit.read_text(encoding="utf-8"))

    if candidate_contract["feature_registry_sha256"] != EXPECTED_FEATURE_SHA256:
        raise ValueError("Candidate contract feature SHA mismatch")
    if candidate_contract.get("version") != "v1":
        raise ValueError("This diagnostic is pinned to the immutable v1 candidate contract")
    if set(FAILED_CANDIDATE_IDS) - set(candidate_contract["candidate_ids"]):
        raise ValueError("Candidate contract does not contain every failed v1 candidate")
    if density_audit.get("density_gate", {}).get("labels_joined") is not False:
        raise ValueError("Density audit is not label-free")
    if density_audit.get("density_gate", {}).get("performance_calculated") is not False:
        raise ValueError("Density audit includes performance and is not allowed here")

    model_columns = feature_contract["model_feature_columns"]
    features = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    missing = sorted(set(model_columns + ["decision_time"]) - set(features.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    if not np.isfinite(features[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite feature values")

    funnel, summary = build_condition_funnel(features)
    expected_counts = _expected_failed_counts(density_audit)
    actual_counts = {
        item["candidate_id"]: item["onset_proposals"]
        for item in summary["candidate_counts"]
    }
    if actual_counts != expected_counts:
        raise AssertionError(
            f"Final onset counts do not match frozen v1 density audit: actual={actual_counts}, expected={expected_counts}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "mlr1_ml05a_condition_funnel_v1.csv.gz"
    canonical.deterministic_csv_gzip(funnel, output_path)

    density_gate = density_audit["density_gate"]
    for item in summary["candidate_counts"]:
        item["expected_onset_proposals"] = expected_counts[item["candidate_id"]]
        item["v1_density_pass"] = (
            density_gate["minimum_proposals_per_candidate"]
            <= item["onset_proposals"]
            <= density_gate["maximum_proposals_per_candidate"]
            and item["year_count"] >= density_gate["minimum_calendar_years"]
        )

    summary.update({
        "system_id": "GML1-MLR1",
        "stage": "ML-05A",
        "status": "V1_LABEL_FREE_CONDITION_FUNNEL_BUILT_V2_DEFINITION_PENDING_AUDIT_ONLY",
        "feature_registry_sha256": feature_sha,
        "feature_contract_sha256": canonical.sha256_file(args.feature_contract),
        "candidate_contract_sha256": canonical.sha256_file(args.candidate_contract),
        "density_audit_sha256": canonical.sha256_file(args.density_audit),
        "output_path": str(output_path),
        "output_rows": int(len(funnel)),
        "output_sha256": canonical.sha256_file(output_path),
        "failed_family_codes": sorted(FAILED_FAMILIES),
        "final_onset_counts_match_frozen_v1_audit": True,
        "labels_joined": False,
        "candidate_performance_read": False,
        "ml03_label_registry_read": False,
        "v2_definition_frozen": False,
        "accepted_v1_candidates_changed": False,
        "audit_only": True,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    })
    canonical.write_json(
        args.output_dir / "mlr1_ml05a_condition_funnel_summary_v1.json",
        summary,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
