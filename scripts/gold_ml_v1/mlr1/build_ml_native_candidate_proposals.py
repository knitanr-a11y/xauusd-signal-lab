from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EXPECTED_FEATURE_SHA256 = "81a3c33c61d07eebbb13514965539a05d5f150e2ce521e613e2089be01d94a2b"
ONE_M15 = pd.Timedelta(minutes=15)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_bytes(payload.encode("utf-8"))


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


def current(frame: pd.DataFrame, feature: str) -> pd.Series:
    return frame[feature].astype(float)


def previous_exact(frame: pd.DataFrame, feature: str) -> pd.Series:
    exact = frame["decision_time"].diff().eq(ONE_M15)
    return frame[feature].shift(1).where(exact).astype(float)


def between(series: pd.Series, lower: float, upper: float) -> pd.Series:
    return series.between(lower, upper, inclusive="both")


def onset(state: pd.Series, decision_time: pd.Series) -> pd.Series:
    exact = decision_time.diff().eq(ONE_M15)
    previous_state = state.shift(1, fill_value=False).where(exact, False)
    return state.fillna(False) & ~previous_state.fillna(False)


def candidate_states(frame: pd.DataFrame) -> list[dict[str, Any]]:
    c = lambda name: current(frame, name)
    p = lambda name: previous_exact(frame, name)

    definitions: list[dict[str, Any]] = []

    definitions.append({
        "candidate_id": "GML1-MLC-001-L",
        "family": "HTF_TREND_PULLBACK_RESUMPTION",
        "direction": "LONG",
        "state": (
            (c("h4_ema20_ema50_gap_atr14") >= 0.15)
            & (c("h4_ema50_ema100_gap_atr14") >= 0.0)
            & (c("d1_ema10_ema20_gap_atr14") >= 0.0)
            & (c("h4_adx14_scaled") >= 0.20)
            & (p("m15_rsi14_centered") <= -0.10)
            & (c("m15_rsi14_centered") > -0.10)
            & (c("m15_signed_body_atr14") >= 0.15)
            & (c("m15_close_location") >= 0.60)
        ),
    })
    definitions.append({
        "candidate_id": "GML1-MLC-001-S",
        "family": "HTF_TREND_PULLBACK_RESUMPTION",
        "direction": "SHORT",
        "state": (
            (c("h4_ema20_ema50_gap_atr14") <= -0.15)
            & (c("h4_ema50_ema100_gap_atr14") <= 0.0)
            & (c("d1_ema10_ema20_gap_atr14") <= 0.0)
            & (c("h4_adx14_scaled") >= 0.20)
            & (p("m15_rsi14_centered") >= 0.10)
            & (c("m15_rsi14_centered") < 0.10)
            & (c("m15_signed_body_atr14") <= -0.15)
            & (c("m15_close_location") <= 0.40)
        ),
    })

    definitions.append({
        "candidate_id": "GML1-MLC-002-L",
        "family": "LOW_VOL_BOLLINGER_BREAKOUT",
        "direction": "LONG",
        "state": (
            (c("m15_atr14_percentile_lag1_256") <= 0.30)
            & (c("m15_bb20_width_atr14") <= 2.50)
            & (p("m15_bb20_close_location") <= 1.0)
            & (c("m15_bb20_close_location") > 1.0)
            & (c("m15_body_fraction") >= 0.50)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.15)
            & (c("h1_ema20_ema50_gap_atr14") >= -0.20)
        ),
    })
    definitions.append({
        "candidate_id": "GML1-MLC-002-S",
        "family": "LOW_VOL_BOLLINGER_BREAKOUT",
        "direction": "SHORT",
        "state": (
            (c("m15_atr14_percentile_lag1_256") <= 0.30)
            & (c("m15_bb20_width_atr14") <= 2.50)
            & (p("m15_bb20_close_location") >= 0.0)
            & (c("m15_bb20_close_location") < 0.0)
            & (c("m15_body_fraction") >= 0.50)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.15)
            & (c("h1_ema20_ema50_gap_atr14") <= 0.20)
        ),
    })

    definitions.append({
        "candidate_id": "GML1-MLC-003-L",
        "family": "HIGH_VOL_MOMENTUM_EXPANSION",
        "direction": "LONG",
        "state": (
            (c("m15_atr14_percentile_lag1_256") >= 0.70)
            & (c("m15_range_atr14") >= 1.25)
            & (c("m15_signed_body_atr14") >= 0.60)
            & (c("m15_close_location") >= 0.80)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.20)
            & (c("h1_ema20_ema50_gap_atr14") >= 0.0)
            & (c("h1_ema20_slope4_atr14") >= 0.0)
        ),
    })
    definitions.append({
        "candidate_id": "GML1-MLC-003-S",
        "family": "HIGH_VOL_MOMENTUM_EXPANSION",
        "direction": "SHORT",
        "state": (
            (c("m15_atr14_percentile_lag1_256") >= 0.70)
            & (c("m15_range_atr14") >= 1.25)
            & (c("m15_signed_body_atr14") <= -0.60)
            & (c("m15_close_location") <= 0.20)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.20)
            & (c("h1_ema20_ema50_gap_atr14") <= 0.0)
            & (c("h1_ema20_slope4_atr14") <= 0.0)
        ),
    })

    definitions.append({
        "candidate_id": "GML1-MLC-004-L",
        "family": "LOW_ADX_RANGE_REJECTION",
        "direction": "LONG",
        "state": (
            (c("h1_adx14_scaled") <= 0.20)
            & (c("h4_adx14_scaled") <= 0.25)
            & between(c("m15_distance_from_prev_low_20_atr14"), -0.25, 0.35)
            & (c("m15_lower_wick_fraction") >= 0.35)
            & (c("m15_signed_body_atr14") > 0.0)
            & (c("m15_close_location") >= 0.60)
            & (c("m15_rsi14_centered") <= -0.15)
        ),
    })
    definitions.append({
        "candidate_id": "GML1-MLC-004-S",
        "family": "LOW_ADX_RANGE_REJECTION",
        "direction": "SHORT",
        "state": (
            (c("h1_adx14_scaled") <= 0.20)
            & (c("h4_adx14_scaled") <= 0.25)
            & between(c("m15_distance_from_prev_high_20_atr14"), -0.35, 0.25)
            & (c("m15_upper_wick_fraction") >= 0.35)
            & (c("m15_signed_body_atr14") < 0.0)
            & (c("m15_close_location") <= 0.40)
            & (c("m15_rsi14_centered") >= 0.15)
        ),
    })

    definitions.append({
        "candidate_id": "GML1-MLC-005-L",
        "family": "HIGH_VOL_EXHAUSTION_REVERSAL",
        "direction": "LONG",
        "state": (
            (c("m15_atr14_percentile_lag1_256") >= 0.75)
            & (c("m15_rsi14_centered") <= -0.35)
            & (c("m15_range_atr14") >= 1.00)
            & (c("m15_lower_wick_fraction") >= 0.40)
            & (c("m15_close_location") >= 0.60)
            & (c("m15_signed_body_atr14") >= 0.0)
            & (c("h1_ema20_ema50_gap_atr14") <= 0.0)
        ),
    })
    definitions.append({
        "candidate_id": "GML1-MLC-005-S",
        "family": "HIGH_VOL_EXHAUSTION_REVERSAL",
        "direction": "SHORT",
        "state": (
            (c("m15_atr14_percentile_lag1_256") >= 0.75)
            & (c("m15_rsi14_centered") >= 0.35)
            & (c("m15_range_atr14") >= 1.00)
            & (c("m15_upper_wick_fraction") >= 0.40)
            & (c("m15_close_location") <= 0.40)
            & (c("m15_signed_body_atr14") <= 0.0)
            & (c("h1_ema20_ema50_gap_atr14") >= 0.0)
        ),
    })

    definitions.append({
        "candidate_id": "GML1-MLC-006-L",
        "family": "MULTITIMEFRAME_ROLLING_BREAKOUT",
        "direction": "LONG",
        "state": (
            (c("m15_distance_from_prev_high_50_atr14") >= 0.0)
            & (c("h1_ema20_ema50_gap_atr14") >= 0.10)
            & (c("h4_ema20_ema50_gap_atr14") >= 0.10)
            & (c("h1_adx14_scaled") >= 0.20)
            & (c("m15_body_fraction") >= 0.40)
            & (c("m15_signed_body_atr14") >= 0.20)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.10)
        ),
    })
    definitions.append({
        "candidate_id": "GML1-MLC-006-S",
        "family": "MULTITIMEFRAME_ROLLING_BREAKOUT",
        "direction": "SHORT",
        "state": (
            (c("m15_distance_from_prev_low_50_atr14") <= 0.0)
            & (c("h1_ema20_ema50_gap_atr14") <= -0.10)
            & (c("h4_ema20_ema50_gap_atr14") <= -0.10)
            & (c("h1_adx14_scaled") >= 0.20)
            & (c("m15_body_fraction") >= 0.40)
            & (c("m15_signed_body_atr14") <= -0.20)
            & (c("m15_tick_volume_ratio20_lagbase") >= 1.10)
        ),
    })
    return definitions


def build_proposals(features: pd.DataFrame, model_columns: list[str]) -> pd.DataFrame:
    frame = features.sort_values("decision_time", kind="mergesort").reset_index(drop=True)
    definitions = candidate_states(frame)
    parts: list[pd.DataFrame] = []
    for item in definitions:
        selected = onset(item["state"], frame["decision_time"])
        proposal = frame.loc[selected, ["decision_time"] + model_columns].copy()
        proposal.insert(1, "candidate_id", item["candidate_id"])
        proposal.insert(2, "candidate_family", item["family"])
        proposal.insert(3, "direction", item["direction"])
        proposal.insert(4, "proposal_strength", 1.0)
        parts.append(proposal)
    result = pd.concat(parts, ignore_index=True)
    return result.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)


def proposal_summary(proposals: pd.DataFrame, all_candidate_ids: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for candidate_id in all_candidate_ids:
        subset = proposals.loc[proposals["candidate_id"] == candidate_id]
        years = sorted(pd.to_datetime(subset["decision_time"]).dt.year.unique().tolist())
        rows.append({
            "candidate_id": candidate_id,
            "direction": None if subset.empty else str(subset["direction"].iloc[0]),
            "family": None if subset.empty else str(subset["candidate_family"].iloc[0]),
            "proposals": int(len(subset)),
            "years": years,
            "year_count": len(years),
            "first_decision": None if subset.empty else str(subset["decision_time"].iloc[0]),
            "last_decision": None if subset.empty else str(subset["decision_time"].iloc[-1]),
        })
    per_decision = proposals.groupby("decision_time").size() if len(proposals) else pd.Series(dtype=int)
    return {
        "candidate_counts": rows,
        "total_proposals": int(len(proposals)),
        "unique_decisions": int(proposals["decision_time"].nunique()),
        "decisions_with_multiple_candidates": int((per_decision > 1).sum()),
        "maximum_candidates_same_decision": int(per_decision.max()) if len(per_decision) else 0,
        "direction_counts": proposals["direction"].value_counts().sort_index().to_dict(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build frozen MLR1 ML-native raw candidate proposals")
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-contract", type=Path, required=True)
    parser.add_argument("--candidate-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    candidate_contract = json.loads(args.candidate_contract.read_text(encoding="utf-8"))
    feature_contract = json.loads(args.feature_contract.read_text(encoding="utf-8"))
    if sha256_file(args.feature_registry) != EXPECTED_FEATURE_SHA256:
        raise ValueError("Feature registry SHA256 mismatch")
    if candidate_contract["feature_registry_sha256"] != EXPECTED_FEATURE_SHA256:
        raise ValueError("Candidate contract feature SHA mismatch")

    model_columns = feature_contract["model_feature_columns"]
    features = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    missing = sorted(set(model_columns + ["decision_time"]) - set(features.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    if not np.isfinite(features[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite feature values")

    proposals = build_proposals(features, model_columns)
    expected_ids = candidate_contract["candidate_ids"]
    actual_ids = sorted(proposals["candidate_id"].unique().tolist())
    unexpected = sorted(set(actual_ids) - set(expected_ids))
    if unexpected:
        raise ValueError(f"Unexpected candidate IDs: {unexpected}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "mlr1_ml_native_candidate_proposals_v1.csv.gz"
    deterministic_csv_gzip(proposals, output_path)
    summary = proposal_summary(proposals, expected_ids)
    density = candidate_contract["density_gate"]
    for item in summary["candidate_counts"]:
        item["density_pass"] = (
            density["minimum_per_candidate"] <= item["proposals"] <= density["maximum_per_candidate"]
            and item["year_count"] >= density["minimum_years"]
        )
    summary.update({
        "system_id": "GML1-MLR1",
        "stage": "ML-05A",
        "status": "RAW_PROPOSALS_BUILT_NO_LABELS_AUDIT_ONLY",
        "feature_registry_sha256": EXPECTED_FEATURE_SHA256,
        "candidate_contract_sha256": sha256_file(args.candidate_contract),
        "output_path": str(output_path),
        "output_sha256": sha256_file(output_path),
        "all_density_pass": all(item["density_pass"] for item in summary["candidate_counts"]),
        "labels_joined": False,
        "performance_calculated": False,
        "audit_only": True,
    })
    write_json(args.output_dir / "mlr1_ml_native_candidate_proposal_summary_v1.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
