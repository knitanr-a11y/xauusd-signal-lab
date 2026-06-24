from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "gold_ml_v1"
    / "audit"
    / "candidate_overlap_audit.py"
)
SPEC = importlib.util.spec_from_file_location("candidate_overlap_audit", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


CANDIDATES = [
    ("GML1-PROV-007", "M15-H4", 15, "GML1-PROV-002", "GML1-PROV-002"),
    ("GML1-PROV-008", "M15-H4", 15, "GML1-PROV-002", "GML1-PROV-002"),
    ("GML1-PROV-010", "H1-D1", 60, None, "GML1-PROV-010"),
    ("GML1-PROV-015", "H1-D1", 60, "GML1-PROV-010", "GML1-PROV-010"),
    ("GML1-PROV-020", "H1-D1", 60, "GML1-PROV-015", "GML1-PROV-010"),
    ("GML1-WATCH-014-A", "H1-D1", 60, "GML1-PROV-015", "GML1-PROV-010"),
]


def _write_registry(path: Path, times: list[str], r_values: list[float]) -> None:
    decision = pd.to_datetime(times)
    frame = pd.DataFrame(
        {
            "decision_close_time": decision,
            "entry_time": decision,
            "exit_time": decision + pd.Timedelta(minutes=30),
            "r_value": r_values,
            "direction": "LONG",
            "atr_regime": ["MID"] * len(times),
        }
    )
    frame.to_csv(path, index=False)


def _write_config(path: Path) -> None:
    payload = {
        "audit_id": "TEST-BATCH-015",
        "audit_only": True,
        "fresh_prospective_cutoff_mt5_server_close": "2026-06-23 18:15:00",
        "2026_policy": "diagnostic only",
        "candidates": [
            {
                "candidate_id": cid,
                "lane": lane,
                "direction": "LONG",
                "decision_bar_minutes": minutes,
                "parent_id": parent,
                "lineage_root": root,
                "expected_registry_sha256": None,
            }
            for cid, lane, minutes, parent, root in CANDIDATES
        ],
        "column_aliases": {},
        "reporting_windows": {
            "all": {"timestamp_column": "decision_close_time"},
            "pre_2026": {
                "timestamp_column": "decision_close_time",
                "end_exclusive": "2026-01-01 00:00:00",
            },
            "diagnostic_2026_to_cutoff": {
                "timestamp_column": "decision_close_time",
                "start_inclusive": "2026-01-01 00:00:00",
                "end_inclusive": "2026-06-23 18:15:00",
            },
            "fresh_post_cutoff": {
                "timestamp_column": "decision_close_time",
                "start_exclusive": "2026-06-23 18:15:00",
            },
        },
        "session_buckets": [
            {"name": "A", "start_hour_inclusive": 0, "end_hour_inclusive": 7},
            {"name": "B", "start_hour_inclusive": 8, "end_hour_inclusive": 15},
            {"name": "C", "start_hour_inclusive": 16, "end_hour_inclusive": 23},
        ],
        "redundancy_diagnostic_thresholds": {
            "exact_entry_jaccard_gte": 0.8,
            "fuzzy_entry_jaccard_gte": 0.85,
            "monthly_r_correlation_gte": 0.8,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_end_to_end_overlap_outputs(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    _write_config(config)
    data = {
        "GML1-PROV-007": (["2025-01-01 00:15", "2025-01-01 00:30"], [1.0, -1.0]),
        "GML1-PROV-008": (["2025-01-01 00:15", "2025-01-01 00:45"], [1.0, 1.0]),
        "GML1-PROV-010": (
            ["2025-01-01 01:00", "2025-01-01 02:00", "2025-01-01 03:00"],
            [1.0, -1.0, 1.0],
        ),
        "GML1-PROV-015": (["2025-01-01 01:00", "2025-01-01 02:00"], [1.0, -1.0]),
        "GML1-PROV-020": (["2025-01-01 02:00"], [-1.0]),
        "GML1-WATCH-014-A": (["2025-01-01 01:00"], [1.0]),
    }
    registry_args = []
    for candidate_id, (times, r_values) in data.items():
        path = tmp_path / f"{candidate_id}.csv"
        _write_registry(path, times, r_values)
        registry_args.append(f"{candidate_id}={path}")
    output = tmp_path / "out"
    args = argparse.Namespace(
        config=config,
        registry=registry_args,
        output_dir=output,
        skip_hash_check=False,
    )
    assert MODULE.run(args) == 0

    exact = pd.read_csv(output / "exact_entry_overlap.csv")
    row = exact[
        (exact["window"] == "all")
        & (exact["candidate_a"] == "GML1-PROV-007")
        & (exact["candidate_b"] == "GML1-PROV-008")
    ].iloc[0]
    assert row["matched_count"] == 1
    assert abs(row["jaccard"] - (1 / 3)) < 1e-12

    retention = pd.read_csv(output / "parent_derivative_retention.csv")
    row = retention[
        (retention["window"] == "all")
        & (retention["parent_id"] == "GML1-PROV-010")
        & (retention["child_id"] == "GML1-PROV-015")
    ].iloc[0]
    assert row["parent_trades"] == 3
    assert row["child_trades"] == 2
    assert row["exact_overlap"] == 2
    assert abs(row["retention_vs_parent"] - (2 / 3)) < 1e-12
    assert row["child_contained_fraction"] == 1.0
    assert row["unexpected_child_only"] == 0

    summary = json.loads((output / "independence_summary.json").read_text(encoding="utf-8"))
    assert summary["structural_lineage_group_count"] == 2
    assert (output / "manifest.json").is_file()
    assert (output / "concentration_breakdown.csv").is_file()
    matrix = pd.read_csv(output / "exact_entry_jaccard_matrix_all.csv").set_index("candidate_id")
    assert abs(matrix.loc["GML1-PROV-007", "GML1-PROV-008"] - (1 / 3)) < 1e-12


def test_duplicate_entry_fails_closed(tmp_path: Path) -> None:
    csv_path = tmp_path / "dup.csv"
    _write_registry(csv_path, ["2025-01-01 00:15", "2025-01-01 00:15"], [1.0, -1.0])
    spec = MODULE.CandidateSpec(
        candidate_id="X",
        lane="M15-H4",
        direction="LONG",
        decision_bar_minutes=15,
        parent_id=None,
        lineage_root="X",
        expected_registry_sha256=None,
    )
    try:
        MODULE.load_registry(spec, csv_path, {}, verify_hash=True)
    except ValueError as exc:
        assert "duplicate entry_time" in str(exc)
    else:
        raise AssertionError("duplicate entry_time must fail closed")
