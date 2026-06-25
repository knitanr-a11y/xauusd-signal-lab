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

from cost_stress_contract import BRIDGE, RAW, Lineage, scenarios_from, validate_config
from cost_stress_engine import M1Engine, recover_risk
from cost_stress_reports import gate_status


class CostStressContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_grid_is_frozen_full_cartesian_product(self) -> None:
        scenarios = scenarios_from(self.config)
        self.assertEqual(len(scenarios), 12)
        self.assertEqual({x.spread_multiplier for x in scenarios}, {1.0, 1.5, 2.0})
        self.assertEqual({x.slippage_points_per_side for x in scenarios}, {0, 5, 10, 20})
        self.assertIn(
            self.config["scenario_grid"]["baseline_scenario_id"],
            {x.scenario_id for x in scenarios},
        )
        self.assertTrue(self.config["scenario_grid"]["grid_frozen_before_execution"])
        self.assertEqual(self.config["scenario_grid"]["post_result_grid_change"], "forbidden")

    def test_candidate_pool_and_populations_are_immutable(self) -> None:
        candidates, lineages = validate_config(self.config)
        self.assertEqual(len(candidates), 9)
        self.assertEqual(set(candidates), set(lineages))
        population = self.config["population_contract"]
        self.assertEqual(population["primary"], RAW)
        self.assertEqual(population["secondary_separate_only"], BRIDGE)
        self.assertEqual(population["bridge_primary_population_use"], "forbidden")
        self.assertTrue(population["fixed_trade_population"])
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
        lineage = Lineage("TEST", 2, "M1_BAR_CLOSE", "LONG")
        baseline = M1Engine(frame).evaluate(
            pd.Timestamp("2026-01-01 00:00:00"), 1.0, lineage, 1.0, 0
        )
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
        metric = {"trade_count": 30, "profit_factor": 1.0, "mean_r": 0.0001}
        self.assertEqual(gate_status(metric, self.config["stress_gate"]), "PASS")

    def test_completed_cost_stress_cannot_be_rerun_by_current_action(self) -> None:
        result = json.loads(PASS_RECORD.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["raw_baseline_parity_checks"], 1687)
        self.assertEqual(result["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(result["candidate_stress_gate"]["fail"], 0)

        action = json.loads(NEXT_ACTION.read_text(encoding="utf-8"))
        self.assertIn(action["mode"], {"bat", "status_only"})
        runner = action.get("runner") or ""
        self.assertNotIn("cost_stress", runner)
        self.assertTrue(action["audit_only"])
        self.assertFalse(action["live_ready"])
        self.assertFalse(action["automatic_promotion"])
        self.assertFalse(action["automatic_registration"])

        implementation = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("RAW_RECONSTRUCTED", implementation)
        self.assertIn("WARMUP_BRIDGE_EXACT", implementation)
        self.assertIn("RUN_GOLD_ML_V1_NEXT.bat", implementation)
        passed = PASS_HANDOFF.read_text(encoding="utf-8")
        self.assertIn("PASS=9", passed)
        self.assertIn("FAIL=0", passed)


if __name__ == "__main__":
    unittest.main()
