from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROPOSAL_METADATA_COLUMNS = [
    "decision_time",
    "candidate_id",
    "candidate_definition_version",
    "candidate_family",
    "direction",
    "proposal_strength",
]
JOIN_KEYS = ["decision_time", "direction"]


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build frozen MLR1 ML-05B raw labeled candidate event registry"
    )
    parser.add_argument("--proposal-registry", type=Path, required=True)
    parser.add_argument("--label-registry", type=Path, required=True)
    parser.add_argument("--label-contract", type=Path, required=True)
    parser.add_argument("--event-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def validate_proposals(
    proposals: pd.DataFrame, event_contract: dict[str, Any]
) -> list[str]:
    missing = sorted(set(PROPOSAL_METADATA_COLUMNS) - set(proposals.columns))
    if missing:
        raise ValueError(f"Proposal registry missing metadata columns: {missing}")
    if proposals.columns[: len(PROPOSAL_METADATA_COLUMNS)].tolist() != PROPOSAL_METADATA_COLUMNS:
        raise ValueError("Proposal metadata column order mismatch")
    if proposals["decision_time"].isna().any():
        raise ValueError("Proposal decision_time contains nulls")
    if proposals.duplicated(["decision_time", "candidate_id"]).any():
        raise ValueError("Duplicate proposal candidate events")
    if not proposals["direction"].isin(["LONG", "SHORT"]).all():
        raise ValueError("Unexpected proposal direction")
    if set(proposals["candidate_id"]) != set(event_contract["candidate_ids"]):
        raise ValueError("Proposal candidate universe mismatch")
    feature_columns = proposals.columns[len(PROPOSAL_METADATA_COLUMNS) :].tolist()
    if len(feature_columns) != int(event_contract["model_feature_count"]):
        raise ValueError(f"Proposal feature count mismatch: {len(feature_columns)}")
    if len(feature_columns) != len(set(feature_columns)):
        raise ValueError("Duplicate proposal feature columns")
    if not np.isfinite(proposals[feature_columns].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite proposal feature values")
    if not np.isfinite(proposals["proposal_strength"].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite proposal strength")
    return feature_columns


def validate_labels(
    labels: pd.DataFrame,
    label_contract: dict[str, Any],
) -> list[str]:
    expected = list(label_contract["output_columns"])
    if labels.columns.tolist() != expected:
        raise ValueError("Label registry column contract mismatch")
    if labels.duplicated(JOIN_KEYS).any():
        raise ValueError("Duplicate label decision_time + direction keys")
    if labels[JOIN_KEYS].isna().any().any():
        raise ValueError("Null label join key")
    if not labels["direction"].isin(label_contract["directions"]).all():
        raise ValueError("Unexpected label direction")
    allowed_outcomes = label_contract.get("outcome_classes", ["TARGET", "PROTECTIVE", "TIME"])
    if not labels["outcome"].isin(allowed_outcomes).all():
        raise ValueError("Unexpected label outcome")
    numeric = [
        "entry_bid_open",
        "entry_spread_points",
        "entry_price",
        "label_atr14_price",
        "target_price",
        "protective_price",
        "exit_bid_close",
        "exit_ask_close",
        "exit_spread_points",
        "fill_price",
        "base_r",
        "strong_r",
        "extreme_r",
        "holding_minutes",
    ]
    if not np.isfinite(labels[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite label numeric values")
    return expected


def build_candidate_events(
    proposals: pd.DataFrame,
    labels: pd.DataFrame,
    event_contract: dict[str, Any],
    label_contract: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    feature_columns = validate_proposals(proposals, event_contract)
    label_columns = validate_labels(labels, label_contract)

    label_payload_columns = [value for value in label_columns if value not in JOIN_KEYS]
    merged = proposals.merge(
        labels,
        on=JOIN_KEYS,
        how="left",
        sort=False,
        validate="many_to_one",
        indicator=True,
    )
    missing = merged.loc[merged["_merge"] != "both", JOIN_KEYS + ["candidate_id"]]
    if len(missing):
        raise ValueError(
            "Unresolved or missing labels for proposal events: "
            + repr(missing.head(10).to_dict(orient="records"))
        )
    merged = merged.drop(columns=["_merge"])
    merged = merged.sort_values(
        ["decision_time", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)

    expected_columns = PROPOSAL_METADATA_COLUMNS + feature_columns + label_payload_columns
    if merged.columns.tolist() != expected_columns:
        raise AssertionError("Candidate event output column order mismatch")
    if len(merged) != len(proposals):
        raise AssertionError("Proposal row retention failure")
    if merged.duplicated(["decision_time", "candidate_id"]).any():
        raise AssertionError("Duplicate candidate event after label join")
    if merged.isna().any().any():
        raise AssertionError("Null value after candidate label join")
    if not (merged["entry_time"] == merged["decision_time"]).all():
        raise AssertionError("Entry time differs from proposal decision time")
    if not (merged["exit_time"] >= merged["entry_time"]).all():
        raise AssertionError("Exit occurs before entry")
    if not merged["holding_minutes"].between(1.0, 360.0, inclusive="both").all():
        raise AssertionError("Holding minutes outside frozen wall-clock horizon")
    calculated_holding = (
        (merged["exit_time"] - merged["entry_time"]).dt.total_seconds() / 60.0
    )
    if not np.allclose(calculated_holding, merged["holding_minutes"], atol=1e-9):
        raise AssertionError("Holding-minute timestamp mismatch")

    is_long = merged["direction"].eq("LONG")
    is_short = merged["direction"].eq("SHORT")
    geometry_checks = {
        "long_target_above_entry": bool(
            (merged.loc[is_long, "target_price"] > merged.loc[is_long, "entry_price"]).all()
        ),
        "long_protective_below_entry": bool(
            (merged.loc[is_long, "protective_price"] < merged.loc[is_long, "entry_price"]).all()
        ),
        "short_target_below_entry": bool(
            (merged.loc[is_short, "target_price"] < merged.loc[is_short, "entry_price"]).all()
        ),
        "short_protective_above_entry": bool(
            (merged.loc[is_short, "protective_price"] > merged.loc[is_short, "entry_price"]).all()
        ),
    }
    if not all(geometry_checks.values()):
        raise AssertionError(f"Direction geometry failure: {geometry_checks}")

    candidate_counts = []
    for candidate_id in event_contract["candidate_ids"]:
        subset = merged.loc[merged["candidate_id"] == candidate_id]
        candidate_counts.append({
            "candidate_id": candidate_id,
            "candidate_definition_version": str(subset["candidate_definition_version"].iloc[0]),
            "candidate_family": str(subset["candidate_family"].iloc[0]),
            "direction": str(subset["direction"].iloc[0]),
            "events": int(len(subset)),
            "years": sorted(int(value) for value in subset["decision_time"].dt.year.unique()),
        })

    by_decision = merged.groupby("decision_time", sort=True)
    per_decision = by_decision.size()
    directions_per_decision = by_decision["direction"].nunique()
    pair_counter: Counter[tuple[str, str]] = Counter()
    import itertools
    for ids in by_decision["candidate_id"].apply(lambda values: sorted(set(values))):
        pair_counter.update(itertools.combinations(ids, 2))

    model_input_columns = [
        "candidate_id",
        "candidate_definition_version",
        "candidate_family",
        "direction",
        "proposal_strength",
    ] + feature_columns
    label_only_columns = label_payload_columns
    forbidden_model_inputs = set(event_contract["forbidden_model_input_columns"])
    if forbidden_model_inputs & set(model_input_columns):
        raise AssertionError("Label-only or future-result columns leaked into model inputs")

    summary = {
        "candidate_counts": candidate_counts,
        "event_rows": int(len(merged)),
        "event_columns": int(len(merged.columns)),
        "unique_decisions": int(merged["decision_time"].nunique()),
        "direction_counts": {
            str(key): int(value)
            for key, value in merged["direction"].value_counts().sort_index().items()
        },
        "outcome_class_counts_for_join_audit_only": {
            str(key): int(value)
            for key, value in merged["outcome"].value_counts().sort_index().items()
        },
        "same_m1_collisions": int(merged["same_m1_collision"].astype(bool).sum()),
        "first_decision": str(merged["decision_time"].min()),
        "last_decision": str(merged["decision_time"].max()),
        "first_exit": str(merged["exit_time"].min()),
        "last_exit": str(merged["exit_time"].max()),
        "holding_minutes_min": float(merged["holding_minutes"].min()),
        "holding_minutes_max": float(merged["holding_minutes"].max()),
        "decisions_with_multiple_candidates": int((per_decision > 1).sum()),
        "maximum_candidates_same_decision": int(per_decision.max()),
        "same_direction_multi_candidate_decisions": int(
            ((per_decision > 1) & (directions_per_decision == 1)).sum()
        ),
        "long_short_conflict_decisions": int((directions_per_decision > 1).sum()),
        "candidate_pair_overlap_counts": [
            {"candidate_a": pair[0], "candidate_b": pair[1], "decisions": int(count)}
            for pair, count in sorted(pair_counter.items(), key=lambda item: (-item[1], item[0]))
        ],
        "model_input_columns": model_input_columns,
        "model_input_column_count": len(model_input_columns),
        "label_only_columns": label_only_columns,
        "label_only_column_count": len(label_only_columns),
        "geometry_checks": geometry_checks,
        "proposal_row_retention_exact": True,
        "missing_label_events": 0,
        "duplicate_candidate_events": 0,
        "duplicate_label_keys": 0,
        "all_values_nonnull": True,
        "entry_equals_decision": True,
        "exit_not_before_entry": True,
        "holding_timestamp_match": True,
    }
    return merged, summary


def main() -> int:
    args = build_parser().parse_args()
    event_contract = json.loads(args.event_contract.read_text(encoding="utf-8"))
    label_contract = json.loads(args.label_contract.read_text(encoding="utf-8"))

    proposal_sha = sha256_file(args.proposal_registry)
    label_sha = sha256_file(args.label_registry)
    if proposal_sha != event_contract["proposal_registry_sha256"]:
        raise ValueError("Proposal registry SHA256 mismatch")
    if label_sha != event_contract["label_registry_sha256"]:
        raise ValueError("Label registry SHA256 mismatch")
    if label_contract["validated_full_snapshot"]["label_registry_sha256"] != label_sha:
        raise ValueError("Label contract SHA identity mismatch")

    proposals = pd.read_csv(args.proposal_registry, parse_dates=["decision_time"])
    labels = pd.read_csv(
        args.label_registry,
        parse_dates=["decision_time", "entry_time", "exit_bar_open_time", "exit_time"],
    )
    events, summary = build_candidate_events(proposals, labels, event_contract, label_contract)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    event_path = args.output_dir / "mlr1_candidate_event_registry_v1.csv.gz"
    columns_path = args.output_dir / "mlr1_candidate_event_columns_v1.json"
    summary_path = args.output_dir / "mlr1_candidate_event_summary_v1.json"

    deterministic_csv_gzip(events, event_path)
    columns_payload = {
        "system_id": "GML1-MLR1",
        "stage": "ML-05B",
        "version": "v1",
        "metadata_columns": ["decision_time"],
        "candidate_context_columns": [
            "candidate_id",
            "candidate_definition_version",
            "candidate_family",
            "direction",
            "proposal_strength",
        ],
        "market_feature_columns": summary["model_input_columns"][5:],
        "model_input_columns": summary["model_input_columns"],
        "label_only_columns": summary["label_only_columns"],
        "join_keys": JOIN_KEYS,
        "rule": "Outcome, R, fill, exit, holding and collision columns are targets or audit metadata only and must never be model inputs.",
    }
    write_json(columns_path, columns_payload)

    summary.update({
        "system_id": "GML1-MLR1",
        "stage": "ML-05B",
        "version": "v1",
        "status": "RAW_CANDIDATE_EVENT_REGISTRY_BUILT_AUDIT_ONLY",
        "proposal_registry_sha256": proposal_sha,
        "label_registry_sha256": label_sha,
        "label_contract_sha256": sha256_file(args.label_contract),
        "event_contract_sha256": sha256_file(args.event_contract),
        "event_registry_path": str(event_path),
        "event_registry_sha256": sha256_file(event_path),
        "columns_path": str(columns_path),
        "columns_sha256": sha256_file(columns_path),
        "labels_joined": True,
        "candidate_performance_calculated": False,
        "one_open_applied": False,
        "dedup_applied": False,
        "candidate_definitions_changed": False,
        "audit_only": True,
        "model_trained": False,
        "model_promoted": False,
        "shadow_ready": False,
        "live_ready": False,
        "final_signal": False,
        "mt5_order": False,
        "discord": False,
    })
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
