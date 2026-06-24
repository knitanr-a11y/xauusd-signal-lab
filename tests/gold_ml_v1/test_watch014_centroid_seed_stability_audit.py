from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "gold_ml_v1" / "audit" / "watch014_centroid_seed_stability_audit.py"
SPEC = importlib.util.spec_from_file_location("watch014_audit", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_label_permutation_aligns_to_reference(tmp_path: Path) -> None:
    config = {
        "audit_id": "TEST-WATCH014",
        "audit_only": True,
        "watch_id": "GML1-WATCH-014-A",
        "k": 2,
        "reference_seed": 1,
        "reference_excluded_cluster_ids": [0],
        "seeds": [1, 2],
        "training_end_exclusive": "2024-01-01 00:00:00",
        "feature_columns": ["f1", "f2"],
        "fresh_cutoff_mt5_server_close": "2026-06-23 18:15:00",
        "2026_policy": "diagnostic only",
        "boundaries": {"no_live_signal": True},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    times = pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"])
    features = pd.DataFrame({"decision_close_time": times, "r_value": [1,-1,1,-1], "f1": [-2,-1,1,2], "f2": [-2,-1,1,2]})
    feature_path = tmp_path / "features.csv"
    features.to_csv(feature_path, index=False)
    a1 = tmp_path / "a1.csv"
    a2 = tmp_path / "a2.csv"
    pd.DataFrame({"decision_close_time": times, "cluster_id": [0,0,1,1]}).to_csv(a1,index=False)
    pd.DataFrame({"decision_close_time": times, "cluster_id": [1,1,0,0]}).to_csv(a2,index=False)
    out = tmp_path / "out"
    args = argparse.Namespace(config=config_path, feature_registry=feature_path, assignment=[f"1={a1}",f"2={a2}"], output_dir=out)
    assert MODULE.run(args) == 0
    global_alignment = pd.read_csv(out / "seed_global_alignment.csv")
    train_row = global_alignment[(global_alignment["seed"] == 2) & (global_alignment["window"] == "train_2023")].iloc[0]
    assert train_row["adjusted_rand_vs_reference"] == 1.0
    assert train_row["exact_aligned_membership_fraction"] == 1.0
    membership = pd.read_csv(out / "seed_membership_stability.csv")
    train_membership = membership[(membership["seed"] == 2) & (membership["window"] == "train_2023")]
    assert (train_membership["membership_jaccard"] == 1.0).all()
    summary = json.loads((out / "centroid_seed_stability_summary.json").read_text())
    assert summary["candidate_logic_changed"] is False


def test_assignment_coverage_mismatch_fails(tmp_path: Path) -> None:
    times = pd.Series(pd.to_datetime(["2023-01-01", "2023-01-02"]))
    path = tmp_path / "assignment.csv"
    pd.DataFrame({"decision_close_time": ["2023-01-01"], "cluster_id": [0]}).to_csv(path,index=False)
    try:
        MODULE.load_assignment(path, 1, times, 2)
    except ValueError as exc:
        assert "coverage mismatch" in str(exc)
    else:
        raise AssertionError("coverage mismatch must fail closed")
