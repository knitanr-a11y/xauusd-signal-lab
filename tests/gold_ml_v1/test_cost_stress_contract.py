from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "scripts/gold_ml_v1/cost_stress"
CONFIG = ROOT / "config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json"
PASS_RECORD = ROOT / "config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json"
NEXT_ACTION = ROOT / "config/gold_ml_v1/next_local_action.json"
HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_IMPLEMENTED_USER_RUN_NEXT_20260625.md"
PASS_HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASS_FRESH_PROSPECTIVE_NEXT_20260625.md"
sys.path.insert(0, str(MODULE_DIR))

from cost_stress_contract import BRIDGE, RAW, Lineage, scenarios_from, validate_config  # noqa: E402
from cost_stress_engine import M1Engine, recover_risk  # noqa: E402
from cost_stress_reports import gate_status  # noqa: E402


class CostStressContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_grid_is_frozen_full_cartesian_product(self) -> None:
        scenarios = scenarios_from(self.config)
        self.assertEqual(len(scenarios), 12)
        self.assertEqual({item.spread_multiplier for item in scenarios}, {1.0, 1.5, 2.0})
        self.assertEqual({item.slippage_points_per_side for item in scenarios}, {0, 5, 10, 20})
        self.assertIn(
            self.config["scenario_grid"]["baseline_scenario_id"],
            {item.scenario_id for item in scenarios},
        )
        self.assertTrue(self.config["scenario_grid"]["grid_frozen_before_execution"])
        self.assertEqual(self.config["scenario_grid"]["post_result_grid_change"], "forbidden")

    def test_candidate_pool_and_populations_are_immutable(self) -> None:
        candidates, lineages = validate_config(self.config)
        self.assertEqual(len(candidates), 9)
        self.assertEqual(set(candidates), set(lineages))
        self.assertEqual(self.config["population_contract"]["primary"], RAW)
        self.assertEqual(self.config["population_contract"]["secondary_separate_only"], BRIDGE)
        self.assertEqual(self.config["population_contract"]["bridge_primary_population_use"], "forbidden")
        self.assertTrue(self.config["population_contract"]["fixed_trade_population"])
        self.assertTrue(all(value is False for value in self.config["execution_switches"].values()))

    def test_exact_execution_uses_sl_priority_and_adverse_slippage(self) -> None:
        frame = pd.DataFrame(
            {
                "time": ["2026.01.01 00:00:00", "2026.01.01 00:01:00", "2026.01.01 00:02:00"],
                "open": [100.0, 100.0, 100.0],
                "high": [101.2, 100.2, 100.2],
                "low": [99.0, 99.8, 99.8],
                "close": [100.5, 100.0, 100.0],
                "spread": [10, 10, 10],
            }
        )
        engine = M1Engine(frame)
        lineage = Lineage("TEST", 2, "M1_BAR_CLOSE", "LONG")
        baseline = engine.evaluate(pd.Timestamp("2026-01-01 00:00:00"), 1.0, lineage, 1.0, 0)
        self.assertEqual(baseline["outcome_stressed"], "SL")
        self.assertAlmostEqual(baseline["r_value_stressed"], -1.0)
        self.assertEqual(baseline["exit_time_stressed"], pd.Timestamp("2026-01-01 00:01:00"))

        tp_only = frame.copy()
        tp_only.loc[0, "low"] = 99.5
        stressed = M1Engine(tp_only).evaluate(
            pd.Timestamp("2026-01-01 00:00:00"), 1.0, lineage, 2.0, 20
        )
        self.assertEqual(stressed["outcome_stressed"], "TP")
        self.assertAlmostEqual(stressed["entry_reference"], 100.2)
        self.assertAlmostEqual(stressed["entry_fill"], 100.4)
        self.assertAlmostEqual(stressed["exit_fill"], 101.0)
        self.assertAlmostEqual(stressed["r_value_stressed"], 0.6)

    def test_risk_recovery_and_gate_are_predeclared(self) -> None:
        row = pd.Series({"entry_price": 100.1, "exit_price": 101.1, "r_value": 1.0, "candidate_id": "TEST", "entry_time": "2026-01-01"})
        self.assertAlmostEqual(recover_risk(row), 1.0)
        item = {"trade_count": 30, "profit_factor": 1.0, "mean_r": 0.0001}
        self.assertEqual(gate_status(item, self.config["stress_gate"]), "PASS")

    def test_cost_stress_is_completed_and_next_action_advanced(self) -> None:
        pass_record = json.loads(PASS_RECORD.read_text(encoding="utf-8"))
        self.assertEqual(pass_record["status"], "PASS")
        self.assertEqual(pass_record["raw_baseline_parity_checks"], 1687)
        self.assertEqual(pass_record["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(pass_record["candidate_stress_gate"]["fail"], 0)

        action = json.loads(NEXT_ACTION.read_text(encoding="utf-8"))
        self.assertEqual(action["mode"], "bat")
        self.assertIn("prospective", action["runner"])
        self.assertNotIn("cost_stress", action["runner"])
        self.assertFalse(action["new_exploration_allowed"])
        self.assertTrue(action["audit_only"])
        self.assertFalse(action["live_ready"])
        self.assertFalse(action["automatic_promotion"])
        self.assertFalse(action["automatic_registration"])

        implementation_text = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("RAW_RECONSTRUCTED", implementation_text)
        self.assertIn("WARMUP_BRIDGE_EXACT", implementation_text)
        self.assertIn("12", implementation_text)
        self.assertIn("RUN_GOLD_ML_V1_NEXT.bat", implementation_text)

        pass_text = PASS_HANDOFF.read_text(encoding="utf-8")
        self.assertIn("PASS=9", pass_text)
        self.assertIn("FAIL=0", pass_text)
        self.assertIn("Fresh prospective", pass_text)


if __name__ == "__main__":
    unittest.main()
