from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_ml_native_candidate_proposals as canonical
import build_ml_native_candidate_proposals_combined_v1v2 as combined


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build audit-only prospective candidate proposals from a causal live feature snapshot"
    )
    parser.add_argument("--live-features", type=Path, required=True)
    parser.add_argument("--feature-contract", type=Path, required=True)
    parser.add_argument("--candidate-contract", type=Path, required=True)
    parser.add_argument("--historical-last-decision", type=str, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    feature_contract = json.loads(args.feature_contract.read_text(encoding="utf-8"))
    candidate_contract = json.loads(args.candidate_contract.read_text(encoding="utf-8"))
    if candidate_contract.get("version") != "v2-density":
        raise ValueError("Prospective proposals require the frozen combined v1/v2-density contract")

    model_columns = list(feature_contract["model_feature_columns"])
    features = pd.read_csv(args.live_features, parse_dates=["decision_time"])
    required = set(["decision_time"] + model_columns)
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"Live feature registry missing columns: {missing}")
    if features["decision_time"].duplicated().any():
        raise ValueError("Duplicate live feature decision_time")
    if not features["decision_time"].is_monotonic_increasing:
        raise ValueError("Live feature decision_time is not increasing")
    if not np.isfinite(features[model_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite live model features")

    # Onset must be calculated on the full available live feature history first.
    # Filtering the historical boundary before onset would make the first prospective row incorrect.
    all_proposals = combined.build_proposals(features, model_columns, candidate_contract)
    boundary = pd.Timestamp(args.historical_last_decision)
    prospective = all_proposals.loc[all_proposals["decision_time"] > boundary].copy()
    prospective = prospective.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "mlr1_prospective_candidate_proposals_v1.csv.gz"
    canonical.deterministic_csv_gzip(prospective, output_path)
    counts = [
        {
            "candidate_id": candidate_id,
            "events": int((prospective["candidate_id"] == candidate_id).sum()),
        }
        for candidate_id in candidate_contract["candidate_ids"]
    ]
    summary = {
        "system_id": "GML1-MLR1",
        "stage": "PROSPECTIVE_CAPTURE",
        "status": "PROSPECTIVE_CANDIDATE_PROPOSALS_BUILT_AUDIT_ONLY",
        "historical_last_decision": str(boundary),
        "all_available_feature_rows": int(len(features)),
        "all_candidate_proposals_before_boundary_filter": int(len(all_proposals)),
        "prospective_candidate_events": int(len(prospective)),
        "prospective_unique_decisions": int(prospective["decision_time"].nunique()),
        "prospective_unique_decision_direction_keys": int(
            prospective[["decision_time", "direction"]].drop_duplicates().shape[0]
        ),
        "first_prospective_decision": None if prospective.empty else str(prospective["decision_time"].iloc[0]),
        "last_prospective_decision": None if prospective.empty else str(prospective["decision_time"].iloc[-1]),
        "candidate_counts": counts,
        "output_path": str(output_path),
        "output_sha256": canonical.sha256_file(output_path),
        "labels_joined": False,
        "candidate_performance_calculated": False,
        "candidate_definitions_changed": False,
        "model_loaded": False,
        "prediction_generated": False,
        "audit_only": True,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    }
    canonical.write_json(
        args.output_dir / "mlr1_prospective_candidate_proposal_summary_v1.json",
        summary,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
