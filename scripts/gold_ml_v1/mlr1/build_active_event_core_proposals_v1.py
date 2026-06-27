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


def onset(frame: pd.DataFrame, state: pd.Series) -> pd.Series:
    exact = frame["decision_time"].diff().eq(ONE_M15)
    prior = state.shift(1, fill_value=False).where(exact, False)
    return state.fillna(False) & ~prior.fillna(False)


def definitions(frame: pd.DataFrame) -> list[dict[str, Any]]:
    c = lambda name: frame[name].astype(float)
    p = lambda name, bars=1: previous_exact(frame, name, bars)

    trend_resumption_long = (
        (c("h1_ema20_ema50_gap_atr14") >= 0.08)
        & (c("h1_ema50_ema200_gap_atr14") >= -0.05)
        & (c("h1_adx14_scaled") >= 0.16)
        & (c("h4_ema20_ema50_gap_atr14") >= -0.20)
        & (p("m15_rsi14_centered") <= -0.10)
        & cross_up(frame, "m15_rsi14_centered", 0.0)
        & (c("m15_macd_hist_atr14") > p("m15_macd_hist_atr14"))
        & (c("m15_signed_body_atr14") >= 0.05)
        & (c("m15_close_location") >= 0.52)
    )

    compression_release_short = (
        (p("m15_atr14_percentile_lag1_256") <= 0.35)
        & (p("m15_atr14_percentile_lag1_256", 2) <= 0.40)
        & (p("m15_bb20_close_location") >= 0.0)
        & (c("m15_bb20_close_location") < 0.0)
        & (c("m15_distance_from_prev_low_20_atr14") <= 0.0)
        & (c("m15_body_fraction") >= 0.55)
        & (c("m15_tick_volume_ratio20_lagbase") >= 1.15)
        & (c("h1_ema20_slope4_atr14") <= 0.0)
        & (c("h1_adx14_scaled") >= 0.15)
    )

    exhaustion_long = (
        (c("m15_atr14_percentile_lag1_256") >= 0.75)
        & (c("m15_rsi14_centered") <= -0.35)
        & (c("m15_range_atr14") >= 1.00)
        & (c("m15_lower_wick_fraction") >= 0.40)
    )

    exhaustion_short = (
        (c("m15_atr14_percentile_lag1_256") >= 0.75)
        & (c("m15_rsi14_centered") >= 0.35)
        & (c("m15_range_atr14") >= 1.00)
        & (c("m15_upper_wick_fraction") >= 0.40)
    )

    return [
        {
            "candidate_id": "GML1-EVT-001-L",
            "candidate_family": "TREND_RESUMPTION",
            "direction": "LONG",
            "state": trend_resumption_long,
        },
        {
            "candidate_id": "GML1-EVT-002-S",
            "candidate_family": "COMPRESSION_RELEASE",
            "direction": "SHORT",
            "state": compression_release_short,
        },
        {
            "candidate_id": "GML1-EVT-003-L",
            "candidate_family": "VOLATILITY_EXHAUSTION",
            "direction": "LONG",
            "state": exhaustion_long,
        },
        {
            "candidate_id": "GML1-EVT-003-S",
            "candidate_family": "VOLATILITY_EXHAUSTION",
            "direction": "SHORT",
            "state": exhaustion_short,
        },
    ]


def build_proposals(
    features: pd.DataFrame, model_columns: list[str]
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frame = features.sort_values("decision_time", kind="mergesort").reset_index(drop=True)
    parts: list[pd.DataFrame] = []
    audits: list[dict[str, Any]] = []
    for definition in definitions(frame):
        selected = onset(frame, definition["state"])
        proposal = frame.loc[selected, ["decision_time"] + model_columns].copy()
        proposal.insert(1, "candidate_id", definition["candidate_id"])
        proposal.insert(2, "candidate_definition_version", "event-core-v1")
        proposal.insert(3, "candidate_family", definition["candidate_family"])
        proposal.insert(4, "direction", definition["direction"])
        proposal.insert(5, "proposal_strength", 1.0)
        parts.append(proposal)
        years = proposal["decision_time"].dt.year.value_counts().sort_index()
        audits.append(
            {
                "candidate_id": definition["candidate_id"],
                "candidate_family": definition["candidate_family"],
                "direction": definition["direction"],
                "events": int(len(proposal)),
                "years": {str(int(year)): int(count) for year, count in years.items()},
                "first_decision": None if proposal.empty else str(proposal["decision_time"].min()),
                "last_decision": None if proposal.empty else str(proposal["decision_time"].max()),
            }
        )
    result = (
        pd.concat(parts, ignore_index=True)
        .sort_values(["decision_time", "candidate_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    if result.duplicated(["decision_time", "candidate_id"]).any():
        raise AssertionError("Duplicate active event candidate")
    if result["decision_time"].duplicated().any():
        raise AssertionError("Active event core requires one candidate at most per decision")
    return result, audits


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the active ML-oriented event proposal registry")
    parser.add_argument("--feature-registry", type=Path, required=True)
    parser.add_argument("--feature-columns", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    columns_contract = json.loads(args.feature_columns.read_text(encoding="utf-8"))
    model_columns = list(columns_contract["market_feature_columns"])
    features = pd.read_csv(args.feature_registry, parse_dates=["decision_time"])
    required = set(["decision_time"] + model_columns)
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Feature registry missing columns: {missing}")
    if features["decision_time"].duplicated().any():
        raise ValueError("Duplicate feature decision_time")
    if not features["decision_time"].is_monotonic_increasing:
        raise ValueError("Feature decisions are not increasing")
    if not np.isfinite(features[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite model features")

    proposals, audits = build_proposals(features, model_columns)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = args.output_dir / "gml1_active_event_core_proposals_v1.csv.gz"
    summary_path = args.output_dir / "gml1_active_event_core_proposal_summary_v1.json"
    deterministic_csv_gzip(proposals, proposal_path)
    summary = {
        "system_id": "GML1-EVENT-CORE",
        "version": "v1",
        "status": "ACTIVE_DEVELOPMENT_EVENT_PROPOSALS_BUILT_AUDIT_ONLY",
        "feature_registry_sha256": sha256_file(args.feature_registry),
        "feature_rows": int(len(features)),
        "model_feature_count": int(len(model_columns)),
        "candidate_count": int(len(audits)),
        "proposal_rows": int(len(proposals)),
        "unique_decisions": int(proposals["decision_time"].nunique()),
        "direction_counts": {
            str(key): int(value)
            for key, value in proposals["direction"].value_counts().sort_index().items()
        },
        "candidate_counts": audits,
        "same_time_overlap": 0,
        "proposal_registry_sha256": sha256_file(proposal_path),
        "old_candidate_material_used_at_runtime": False,
        "labels_read": False,
        "performance_read_by_builder": False,
        "audit_only": True,
        "model_promoted": False,
        "live_ready": False,
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
