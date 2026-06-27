from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/build_ml_native_candidate_proposals.py"
FEATURE_CONTRACT = ROOT / "config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json"
CANDIDATE_CONTRACT = ROOT / "config/gold_ml_v1/mlr1_ml_native_candidate_contract_v1_20260627.json"
SPEC = importlib.util.spec_from_file_location("mlr1_ml_native_candidates", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Mlr1MlNativeCandidateTests(unittest.TestCase):
    def test_candidate_manifest_has_six_symmetric_families(self) -> None:
        contract = json.loads(CANDIDATE_CONTRACT.read_text(encoding="utf-8"))
        ids = contract["candidate_ids"]
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual(sum(value.endswith("-L") for value in ids), 6)
        self.assertEqual(sum(value.endswith("-S") for value in ids), 6)

    def test_previous_exact_rejects_gap(self) -> None:
        frame = pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2024-01-01 00:15:00",
                "2024-01-01 00:45:00",
            ]),
            "x": [1.0, 2.0],
        })
        result = MODULE.previous_exact(frame, "x")
        self.assertTrue(np.isnan(result.iloc[1]))

    def test_onset_emits_once_for_contiguous_state(self) -> None:
        decision = pd.Series(pd.date_range("2024-01-01 00:15:00", periods=4, freq="15min"))
        state = pd.Series([False, True, True, False])
        self.assertEqual(MODULE.onset(state, decision).tolist(), [False, True, False, False])

    def test_high_vol_long_proposal_is_generated_once(self) -> None:
        feature_contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
        columns = feature_contract["model_feature_columns"]
        frame = pd.DataFrame(0.0, index=range(3), columns=columns)
        frame.insert(0, "decision_time", pd.date_range("2024-01-01 00:15:00", periods=3, freq="15min"))
        for row in [1, 2]:
            frame.loc[row, "m15_atr14_percentile_lag1_256"] = 0.80
            frame.loc[row, "m15_range_atr14"] = 1.50
            frame.loc[row, "m15_signed_body_atr14"] = 0.70
            frame.loc[row, "m15_close_location"] = 0.90
            frame.loc[row, "m15_tick_volume_ratio20_lagbase"] = 1.30
            frame.loc[row, "h1_ema20_ema50_gap_atr14"] = 0.20
            frame.loc[row, "h1_ema20_slope4_atr14"] = 0.20
        proposals = MODULE.build_proposals(frame, columns)
        selected = proposals.loc[proposals["candidate_id"] == "GML1-MLC-003-L"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected["decision_time"].iloc[0], frame["decision_time"].iloc[1])

    def test_output_keeps_all_model_features(self) -> None:
        feature_contract = json.loads(FEATURE_CONTRACT.read_text(encoding="utf-8"))
        columns = feature_contract["model_feature_columns"]
        frame = pd.DataFrame(0.0, index=range(2), columns=columns)
        frame.insert(0, "decision_time", pd.date_range("2024-01-01", periods=2, freq="15min"))
        proposals = MODULE.build_proposals(frame, columns)
        self.assertTrue(set(columns).issubset(proposals.columns))

    def test_deterministic_gzip(self) -> None:
        frame = pd.DataFrame({"decision_time": pd.to_datetime(["2024-01-01"]), "x": [1.0]})
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.csv.gz"
            second = Path(tmp) / "b.csv.gz"
            MODULE.deterministic_csv_gzip(frame, first)
            MODULE.deterministic_csv_gzip(frame, second)
            self.assertEqual(MODULE.sha256_file(first), MODULE.sha256_file(second))


if __name__ == "__main__":
    unittest.main()
