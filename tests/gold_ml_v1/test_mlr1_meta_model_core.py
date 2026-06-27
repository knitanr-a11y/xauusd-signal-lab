from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/run_mlr1_meta_model_research.py"
SPEC = importlib.util.spec_from_file_location("meta_core", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MetaCoreTests(unittest.TestCase):
    def test_affine_calibration_never_uses_negative_slope(self) -> None:
        intercept, slope = MODULE.affine_calibration(
            np.array([0.0, 1.0, 2.0]), np.array([2.0, 1.0, 0.0])
        )
        self.assertEqual(slope, 0.0)
        self.assertAlmostEqual(intercept, 1.0)

    def test_affine_calibration_caps_slope(self) -> None:
        _, slope = MODULE.affine_calibration(
            np.array([0.0, 1.0, 2.0]), np.array([0.0, 10.0, 20.0])
        )
        self.assertEqual(slope, 2.0)

    def test_threshold_uses_eligible_decision_coverage(self) -> None:
        scores = np.array([0.9, 0.8, 0.7, 0.6])
        self.assertAlmostEqual(
            MODULE.threshold_for_coverage(scores, 1000, 0.0025), 0.7
        )

    def test_segment_respects_purge_and_resolved_cutoff(self) -> None:
        frame = pd.DataFrame(
            {
                "decision_time": pd.to_datetime(
                    ["2024-01-01 01:00", "2024-01-01 07:00", "2024-06-30 20:00"]
                ),
                "exit_time": pd.to_datetime(
                    ["2024-01-01 02:00", "2024-01-01 08:00", "2024-07-01 01:00"]
                ),
            }
        )
        selected = MODULE.segment_events(
            frame,
            "2024-01-01",
            "2024-07-01",
            "validation",
            pd.Timedelta(hours=6),
        )
        self.assertEqual(
            selected["decision_time"].tolist(), [pd.Timestamp("2024-01-01 07:00")]
        )

    def test_dedup_prefers_score_then_candidate_id(self) -> None:
        frame = pd.DataFrame(
            {
                "decision_time": pd.to_datetime(["2024-01-01", "2024-01-01"]),
                "candidate_id": ["B", "A"],
                "score": [1.0, 1.0],
            }
        )
        selected = MODULE.deduplicate_decisions(frame, "score")
        self.assertEqual(selected["candidate_id"].iloc[0], "A")

    def test_one_position_blocks_overlap(self) -> None:
        frame = pd.DataFrame(
            {
                "decision_time": pd.to_datetime(
                    ["2024-01-01 00:00", "2024-01-01 00:15", "2024-01-01 01:00"]
                ),
                "exit_time": pd.to_datetime(
                    ["2024-01-01 00:30", "2024-01-01 00:45", "2024-01-01 01:15"]
                ),
                "candidate_id": ["A", "B", "C"],
            }
        )
        selected = MODULE.one_position(frame)
        self.assertEqual(selected["candidate_id"].tolist(), ["A", "C"])

    def test_profit_factor(self) -> None:
        self.assertAlmostEqual(
            MODULE.profit_factor(np.array([2.0, -1.0, 1.0, -1.0])), 1.5
        )


if __name__ == "__main__":
    unittest.main()
