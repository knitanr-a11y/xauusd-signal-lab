from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/build_candidate_event_registry.py"
SPEC = importlib.util.spec_from_file_location("mlr1_ml05b_builder", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Mlr1Ml05bCandidateEventTests(unittest.TestCase):
    def make_proposals(self) -> pd.DataFrame:
        return pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2024-01-01 00:15:00",
                "2024-01-01 00:15:00",
                "2024-01-01 00:30:00",
            ]),
            "candidate_id": ["A-L", "B-L", "A-S"],
            "candidate_definition_version": ["v1", "v2-density", "v1"],
            "candidate_family": ["A", "B", "A"],
            "direction": ["LONG", "LONG", "SHORT"],
            "proposal_strength": [1.0, 1.0, 1.0],
            "f1": [0.1, 0.2, 0.3],
            "f2": [1.1, 1.2, 1.3],
        })

    def make_labels(self) -> pd.DataFrame:
        return pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2024-01-01 00:15:00",
                "2024-01-01 00:30:00",
            ]),
            "direction": ["LONG", "SHORT"],
            "entry_time": pd.to_datetime([
                "2024-01-01 00:15:00",
                "2024-01-01 00:30:00",
            ]),
            "entry_bid_open": [2000.0, 2001.0],
            "entry_spread_points": [2.0, 2.0],
            "entry_price": [2000.02, 2001.0],
            "label_atr14_price": [2.0, 2.0],
            "target_price": [2003.02, 1998.0],
            "protective_price": [1998.02, 2003.0],
            "outcome": ["TARGET", "PROTECTIVE"],
            "exit_bar_open_time": pd.to_datetime([
                "2024-01-01 00:29:00",
                "2024-01-01 00:44:00",
            ]),
            "exit_time": pd.to_datetime([
                "2024-01-01 00:30:00",
                "2024-01-01 00:45:00",
            ]),
            "exit_bid_close": [2003.0, 2003.0],
            "exit_ask_close": [2003.02, 2003.02],
            "exit_spread_points": [2.0, 2.0],
            "fill_price": [2003.02, 2003.0],
            "base_r": [1.5, -1.0],
            "strong_r": [1.3, -1.2],
            "extreme_r": [1.1, -1.4],
            "same_m1_collision": [False, False],
            "holding_minutes": [15.0, 15.0],
        })

    def event_contract(self) -> dict:
        return {
            "candidate_ids": ["A-L", "B-L", "A-S"],
            "model_feature_count": 2,
            "forbidden_model_input_columns": [
                "entry_time", "outcome", "exit_time", "base_r",
                "strong_r", "extreme_r", "holding_minutes",
            ],
        }

    def label_contract(self, labels: pd.DataFrame) -> dict:
        return {
            "output_columns": labels.columns.tolist(),
            "directions": ["LONG", "SHORT"],
            "outcome_classes": ["TARGET", "PROTECTIVE", "TIME"],
        }

    def test_many_candidates_can_share_one_resolved_label(self) -> None:
        proposals = self.make_proposals()
        labels = self.make_labels()
        events, summary = MODULE.build_candidate_events(
            proposals, labels, self.event_contract(), self.label_contract(labels)
        )
        self.assertEqual(len(events), 3)
        shared = events.loc[
            events["decision_time"] == pd.Timestamp("2024-01-01 00:15:00")
        ]
        self.assertEqual(len(shared), 2)
        self.assertEqual(set(shared["outcome"]), {"TARGET"})
        self.assertTrue(summary["proposal_row_retention_exact"])

    def test_unmatched_proposal_fails_closed(self) -> None:
        proposals = self.make_proposals()
        proposals.loc[2, "decision_time"] = pd.Timestamp("2024-01-01 00:45:00")
        labels = self.make_labels()
        with self.assertRaises(ValueError):
            MODULE.build_candidate_events(
                proposals, labels, self.event_contract(), self.label_contract(labels)
            )

    def test_duplicate_label_key_fails_closed(self) -> None:
        proposals = self.make_proposals()
        labels = pd.concat(
            [self.make_labels(), self.make_labels().iloc[[0]]], ignore_index=True
        )
        with self.assertRaises(ValueError):
            MODULE.build_candidate_events(
                proposals, labels, self.event_contract(), self.label_contract(labels)
            )

    def test_result_columns_are_not_model_inputs(self) -> None:
        proposals = self.make_proposals()
        labels = self.make_labels()
        _, summary = MODULE.build_candidate_events(
            proposals, labels, self.event_contract(), self.label_contract(labels)
        )
        model_inputs = set(summary["model_input_columns"])
        self.assertTrue(
            {"candidate_id", "direction", "proposal_strength", "f1", "f2"}
            <= model_inputs
        )
        self.assertTrue(
            {"outcome", "exit_time", "base_r", "strong_r", "extreme_r"}
            .isdisjoint(model_inputs)
        )

    def test_one_open_and_dedup_are_not_applied(self) -> None:
        proposals = self.make_proposals()
        labels = self.make_labels()
        events, summary = MODULE.build_candidate_events(
            proposals, labels, self.event_contract(), self.label_contract(labels)
        )
        self.assertEqual(len(events), len(proposals))
        self.assertEqual(summary["decisions_with_multiple_candidates"], 1)
        self.assertEqual(summary["maximum_candidates_same_decision"], 2)

    def test_deterministic_gzip(self) -> None:
        frame = self.make_proposals()
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.csv.gz"
            second = Path(tmp) / "second.csv.gz"
            MODULE.deterministic_csv_gzip(frame, first)
            MODULE.deterministic_csv_gzip(frame, second)
            self.assertEqual(MODULE.sha256_file(first), MODULE.sha256_file(second))


if __name__ == "__main__":
    unittest.main()
