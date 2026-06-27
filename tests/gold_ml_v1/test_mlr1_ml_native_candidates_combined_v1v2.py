from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts/gold_ml_v1/mlr1"
CANONICAL_SCRIPT = SCRIPT_DIR / "build_ml_native_candidate_proposals.py"
COMBINED_SCRIPT = SCRIPT_DIR / "build_ml_native_candidate_proposals_combined_v1v2.py"
FEATURE_CONTRACT = ROOT / "config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json"
V2_CONTRACT = ROOT / "config/gold_ml_v1/mlr1_ml_native_candidate_contract_v2_density_20260627.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

CANONICAL_SPEC = importlib.util.spec_from_file_location(
    "mlr1_canonical_candidates_for_combined_test", CANONICAL_SCRIPT
)
CANONICAL = importlib.util.module_from_spec(CANONICAL_SPEC)
assert CANONICAL_SPEC.loader is not None
sys.modules[CANONICAL_SPEC.name] = CANONICAL
CANONICAL_SPEC.loader.exec_module(CANONICAL)

COMBINED_SPEC = importlib.util.spec_from_file_location(
    "mlr1_combined_candidates", COMBINED_SCRIPT
)
COMBINED = importlib.util.module_from_spec(COMBINED_SPEC)
assert COMBINED_SPEC.loader is not None
sys.modules[COMBINED_SPEC.name] = COMBINED
COMBINED_SPEC.loader.exec_module(COMBINED)


class Mlr1CombinedV1V2CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        feature_contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
        cls.model_columns = feature_contract["model_feature_columns"]
        cls.v2_contract = json.loads(V2_CONTRACT.read_text(encoding="utf-8"))

    def make_frame(self, rows: int = 64) -> pd.DataFrame:
        rng = np.random.default_rng(20260627)
        values = rng.normal(0.0, 0.8, size=(rows, len(self.model_columns)))
        frame = pd.DataFrame(values, columns=self.model_columns)
        frame.insert(
            0,
            "decision_time",
            pd.date_range("2024-01-01 00:15:00", periods=rows, freq="15min"),
        )
        return frame

    def make_zero_frame(self, rows: int = 3) -> pd.DataFrame:
        frame = pd.DataFrame(0.0, index=range(rows), columns=self.model_columns)
        frame.insert(
            0,
            "decision_time",
            pd.date_range("2024-01-01 00:15:00", periods=rows, freq="15min"),
        )
        return frame

    def test_cli_has_no_label_or_performance_input(self) -> None:
        option_strings = {
            option
            for action in COMBINED.build_parser()._actions
            for option in action.option_strings
        }
        self.assertNotIn("--label-registry", option_strings)
        self.assertNotIn("--performance", option_strings)
        self.assertEqual(
            option_strings,
            {
                "-h",
                "--help",
                "--feature-registry",
                "--feature-contract",
                "--v1-candidate-contract",
                "--v2-candidate-contract",
                "--v1-density-audit",
                "--output-dir",
            },
        )

    def test_contract_keeps_same_twelve_ids_and_explicit_versions(self) -> None:
        ids = self.v2_contract["candidate_ids"]
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual(set(ids), COMBINED.ACCEPTED_V1_IDS | COMBINED.REVISED_V2_IDS)
        versions = self.v2_contract["candidate_definition_versions"]
        self.assertEqual({versions[value] for value in COMBINED.ACCEPTED_V1_IDS}, {"v1"})
        self.assertEqual({versions[value] for value in COMBINED.REVISED_V2_IDS}, {"v2-density"})

    def test_accepted_v1_states_are_the_canonical_states(self) -> None:
        frame = self.make_frame()
        canonical = {
            item["candidate_id"]: item["state"].fillna(False).astype(bool)
            for item in CANONICAL.candidate_states(frame)
        }
        combined = {
            item["candidate_id"]: item["state"]
            for item in COMBINED.combined_candidate_states(frame, self.v2_contract)
        }
        for candidate_id in COMBINED.ACCEPTED_V1_IDS:
            pd.testing.assert_series_equal(combined[candidate_id], canonical[candidate_id])

    def test_every_density_v2_state_is_a_pure_broadening_of_v1(self) -> None:
        frame = self.make_frame(rows=512)
        canonical = {
            item["candidate_id"]: item["state"].fillna(False).astype(bool)
            for item in CANONICAL.candidate_states(frame)
        }
        revised = COMBINED.revised_v2_states(frame)
        for candidate_id in COMBINED.REVISED_V2_IDS:
            v2_state = revised[candidate_id]["state"].fillna(False).astype(bool)
            self.assertFalse((canonical[candidate_id] & ~v2_state).any())

    def test_mlc002_v2_removes_only_final_h1_direction_gate(self) -> None:
        frame = self.make_zero_frame()
        frame.loc[0, "m15_bb20_close_location"] = 0.5
        frame.loc[1, "m15_atr14_percentile_lag1_256"] = 0.20
        frame.loc[1, "m15_bb20_width_atr14"] = 2.0
        frame.loc[1, "m15_bb20_close_location"] = 1.1
        frame.loc[1, "m15_body_fraction"] = 0.60
        frame.loc[1, "m15_tick_volume_ratio20_lagbase"] = 1.20
        frame.loc[1, "h1_ema20_ema50_gap_atr14"] = -1.0
        canonical = {
            item["candidate_id"]: item["state"]
            for item in CANONICAL.candidate_states(frame)
        }
        revised = COMBINED.revised_v2_states(frame)
        self.assertFalse(bool(canonical["GML1-MLC-002-L"].iloc[1]))
        self.assertTrue(bool(revised["GML1-MLC-002-L"]["state"].iloc[1]))

    def test_mlc004_and_mlc005_keep_wick_structural_core(self) -> None:
        frame = self.make_zero_frame()
        frame.loc[1, "h1_adx14_scaled"] = 0.10
        frame.loc[1, "h4_adx14_scaled"] = 0.10
        frame.loc[1, "m15_distance_from_prev_low_20_atr14"] = 0.0
        frame.loc[1, "m15_lower_wick_fraction"] = 0.50
        frame.loc[1, "m15_signed_body_atr14"] = -0.20
        frame.loc[1, "m15_atr14_percentile_lag1_256"] = 0.80
        frame.loc[1, "m15_rsi14_centered"] = -0.50
        frame.loc[1, "m15_range_atr14"] = 1.20
        frame.loc[1, "m15_close_location"] = 0.20
        canonical = {
            item["candidate_id"]: item["state"]
            for item in CANONICAL.candidate_states(frame)
        }
        revised = COMBINED.revised_v2_states(frame)
        self.assertFalse(bool(canonical["GML1-MLC-004-L"].iloc[1]))
        self.assertTrue(bool(revised["GML1-MLC-004-L"]["state"].iloc[1]))
        self.assertFalse(bool(canonical["GML1-MLC-005-L"].iloc[1]))
        self.assertTrue(bool(revised["GML1-MLC-005-L"]["state"].iloc[1]))

    def test_output_retains_features_and_definition_version(self) -> None:
        frame = self.make_zero_frame()
        frame.loc[0, "m15_bb20_close_location"] = 0.5
        frame.loc[1, "m15_atr14_percentile_lag1_256"] = 0.20
        frame.loc[1, "m15_bb20_width_atr14"] = 2.0
        frame.loc[1, "m15_bb20_close_location"] = 1.1
        frame.loc[1, "m15_body_fraction"] = 0.60
        frame.loc[1, "m15_tick_volume_ratio20_lagbase"] = 1.20
        proposals = COMBINED.build_proposals(frame, self.model_columns, self.v2_contract)
        self.assertTrue(set(self.model_columns).issubset(proposals.columns))
        self.assertIn("candidate_definition_version", proposals.columns)
        selected = proposals.loc[proposals["candidate_id"] == "GML1-MLC-002-L"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected["candidate_definition_version"].iloc[0], "v2-density")


if __name__ == "__main__":
    unittest.main()
