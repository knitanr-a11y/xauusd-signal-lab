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
FUNNEL_SCRIPT = SCRIPT_DIR / "audit_ml_native_candidate_condition_funnels.py"
FEATURE_CONTRACT = ROOT / "config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

CANONICAL_SPEC = importlib.util.spec_from_file_location(
    "mlr1_ml_native_candidates_for_funnel_test", CANONICAL_SCRIPT
)
CANONICAL = importlib.util.module_from_spec(CANONICAL_SPEC)
assert CANONICAL_SPEC.loader is not None
sys.modules[CANONICAL_SPEC.name] = CANONICAL
CANONICAL_SPEC.loader.exec_module(CANONICAL)

FUNNEL_SPEC = importlib.util.spec_from_file_location(
    "mlr1_ml05a_condition_funnels", FUNNEL_SCRIPT
)
FUNNEL = importlib.util.module_from_spec(FUNNEL_SPEC)
assert FUNNEL_SPEC.loader is not None
sys.modules[FUNNEL_SPEC.name] = FUNNEL
FUNNEL_SPEC.loader.exec_module(FUNNEL)


class Mlr1Ml05aConditionFunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
        cls.model_columns = contract["model_feature_columns"]

    def make_frame(self, rows: int = 512) -> pd.DataFrame:
        rng = np.random.default_rng(20260627)
        values = rng.normal(0.0, 0.8, size=(rows, len(self.model_columns)))
        frame = pd.DataFrame(values, columns=self.model_columns)
        frame.insert(
            0,
            "decision_time",
            pd.date_range("2023-12-29 00:15:00", periods=rows, freq="15min"),
        )
        return frame

    def test_only_label_free_cli_inputs_are_supported(self) -> None:
        option_strings = {
            option
            for action in FUNNEL.build_parser()._actions
            for option in action.option_strings
        }
        self.assertNotIn("--label-registry", option_strings)
        self.assertNotIn("--outcome-registry", option_strings)
        self.assertNotIn("--performance", option_strings)
        self.assertEqual(
            option_strings,
            {
                "-h",
                "--help",
                "--feature-registry",
                "--feature-contract",
                "--candidate-contract",
                "--density-audit",
                "--output-dir",
            },
        )

    def test_failed_final_states_match_immutable_v1_generator(self) -> None:
        frame = self.make_frame()
        definitions = FUNNEL.failed_candidate_condition_steps(frame)
        canonical = {
            item["candidate_id"]: item["state"].fillna(False).astype(bool)
            for item in CANONICAL.candidate_states(frame)
            if item["candidate_id"] in FUNNEL.FAILED_CANDIDATE_IDS
        }
        for candidate_id in FUNNEL.FAILED_CANDIDATE_IDS:
            cumulative = pd.Series(True, index=frame.index, dtype=bool)
            for step in definitions[candidate_id]["steps"]:
                cumulative &= step["condition"]
            pd.testing.assert_series_equal(cumulative, canonical[candidate_id])

    def test_final_onset_counts_match_immutable_v1_generator(self) -> None:
        frame = self.make_frame()
        _, summary = FUNNEL.build_condition_funnel(frame)
        actual = {
            item["candidate_id"]: item["onset_proposals"]
            for item in summary["candidate_counts"]
        }
        expected = {}
        for item in CANONICAL.candidate_states(frame):
            if item["candidate_id"] in FUNNEL.FAILED_CANDIDATE_IDS:
                expected[item["candidate_id"]] = int(
                    CANONICAL.onset(item["state"], frame["decision_time"]).sum()
                )
        self.assertEqual(actual, expected)

    def test_funnel_has_full_snapshot_year_direction_and_onset_rows(self) -> None:
        frame = self.make_frame()
        funnel, _ = FUNNEL.build_condition_funnel(frame)
        self.assertEqual(set(funnel["direction"]), {"LONG", "SHORT"})
        self.assertIn("FULL_SNAPSHOT", set(funnel["scope_type"]))
        self.assertIn("CALENDAR_YEAR", set(funnel["scope_type"]))
        self.assertEqual(
            set(funnel.loc[funnel["stage_type"] == "ONSET", "stage_name"]),
            {"FALSE_TO_TRUE_ONSET"},
        )
        self.assertEqual(
            set(
                funnel.loc[
                    funnel["scope_type"] == "CALENDAR_YEAR", "calendar_year"
                ]
                .dropna()
                .astype(int)
            ),
            {2023, 2024},
        )

    def test_gap_resets_onset_state(self) -> None:
        decision_time = pd.Series(
            pd.to_datetime(
                [
                    "2024-01-01 00:15:00",
                    "2024-01-01 00:30:00",
                    "2024-01-01 01:00:00",
                ]
            )
        )
        state = pd.Series([True, True, True])
        self.assertEqual(
            CANONICAL.onset(state, decision_time).tolist(),
            [True, False, True],
        )


if __name__ == "__main__":
    unittest.main()
