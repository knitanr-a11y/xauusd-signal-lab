from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/build_resolved_prospective_labels.py"
SPEC = importlib.util.spec_from_file_location("mlr1_prospective_labels", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProspectiveResolvedLabelTests(unittest.TestCase):
    def contract(self) -> dict:
        return {
            "target_atr": 1.5,
            "protective_atr": 1.0,
            "horizon_hours": 6,
            "strong_cost": {
                "spread_multiplier": 2.0,
                "entry_slippage_price": 0.1,
                "exit_slippage_price": 0.1,
            },
            "extreme_cost": {
                "spread_multiplier": 3.0,
                "entry_slippage_price": 0.2,
                "exit_slippage_price": 0.2,
            },
            "resolved_only": True,
        }

    def m1(self, minutes: int = 360) -> pd.DataFrame:
        return pd.DataFrame({
            "time": pd.date_range("2026-01-01 00:00:00", periods=minutes, freq="1min"),
            "open": np.full(minutes, 100.0),
            "high": np.full(minutes, 100.2),
            "low": np.full(minutes, 99.8),
            "close": np.full(minutes, 100.0),
            "spread": np.full(minutes, 10.0),
        })

    def test_long_target_and_stress_cost(self) -> None:
        m1 = self.m1()
        m1.loc[1, "high"] = 102.0
        result = MODULE.ExactM1Labeler(m1, self.contract()).label(
            pd.Timestamp("2026-01-01 00:00:00"), "LONG", 1.0
        )
        self.assertEqual(result["outcome"], "TARGET")
        self.assertAlmostEqual(result["base_r"], 1.5)
        self.assertAlmostEqual(result["strong_r"], 1.2)
        self.assertAlmostEqual(result["extreme_r"], 0.9)

    def test_short_protective_uses_ask_path(self) -> None:
        m1 = self.m1()
        m1.loc[2, "high"] = 101.0
        result = MODULE.ExactM1Labeler(m1, self.contract()).label(
            pd.Timestamp("2026-01-01 00:00:00"), "SHORT", 1.0
        )
        self.assertEqual(result["outcome"], "PROTECTIVE")
        self.assertAlmostEqual(result["fill_price"], 101.0)
        self.assertAlmostEqual(result["base_r"], -1.0)

    def test_same_m1_collision_is_protective(self) -> None:
        m1 = self.m1()
        m1.loc[0, "high"] = 102.0
        m1.loc[0, "low"] = 98.0
        result = MODULE.ExactM1Labeler(m1, self.contract()).label(
            pd.Timestamp("2026-01-01 00:00:00"), "LONG", 1.0
        )
        self.assertEqual(result["outcome"], "PROTECTIVE")
        self.assertTrue(result["same_m1_collision"])

    def test_time_exit_uses_last_eligible_close(self) -> None:
        result = MODULE.ExactM1Labeler(self.m1(360), self.contract()).label(
            pd.Timestamp("2026-01-01 00:00:00"), "LONG", 1.0
        )
        self.assertEqual(result["outcome"], "TIME")
        self.assertEqual(result["holding_minutes"], 360)
        self.assertEqual(result["exit_time"], pd.Timestamp("2026-01-01 06:00:00"))

    def test_unobserved_horizon_remains_unresolved(self) -> None:
        result = MODULE.ExactM1Labeler(self.m1(10), self.contract()).label(
            pd.Timestamp("2026-01-01 00:00:00"), "LONG", 1.0
        )
        self.assertFalse(result["resolved"])
        self.assertEqual(result["reason"], "HORIZON_NOT_OBSERVED")

    def test_many_candidates_share_one_label_without_dedup(self) -> None:
        m1 = self.m1()
        m1.loc[1, "high"] = 102.0
        features = pd.DataFrame({
            "decision_time": pd.to_datetime(["2026-01-01 00:00:00"]),
            "label_m15_atr14_price": [1.0],
        })
        proposals = pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2026-01-01 00:00:00", "2026-01-01 00:00:00"
            ]),
            "candidate_id": ["A", "B"],
            "direction": ["LONG", "LONG"],
        })
        labels, unresolved, resolved_events, unresolved_events = (
            MODULE.build_resolved_registry(
                features, proposals, MODULE.ExactM1Labeler(m1, self.contract())
            )
        )
        self.assertEqual(len(labels), 1)
        self.assertEqual(len(resolved_events), 2)
        self.assertEqual(len(unresolved), 0)
        self.assertEqual(len(unresolved_events), 0)


if __name__ == "__main__":
    unittest.main()
