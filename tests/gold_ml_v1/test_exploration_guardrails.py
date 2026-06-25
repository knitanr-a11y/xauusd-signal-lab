from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARDRAILS = ROOT / "config/gold_ml_v1/exploration_guardrails_20260625.json"
CURRENT_STATE = ROOT / "config/gold_ml_v1/current_state_snapshot_20260624.json"
NEXT_ACTION = ROOT / "config/gold_ml_v1/next_local_action.json"
AGENTS = ROOT / "AGENTS.md"
HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_20260625.md"


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = json.loads(GUARDRAILS.read_text(encoding="utf-8"))
        self.state = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        self.action = json.loads(NEXT_ACTION.read_text(encoding="utf-8"))
        self.agents = AGENTS.read_text(encoding="utf-8")
        self.handoff = HANDOFF.read_text(encoding="utf-8")

    def test_frozen_period_split(self) -> None:
        periods = self.guardrails["period_contract"]
        self.assertEqual(periods["2023"], "EXPLORATION_ONLY")
        self.assertEqual(periods["2024"], "VALIDATION_ONLY_NO_RETUNE")
        self.assertEqual(periods["2025"], "FINAL_TEST_ONLY_NO_RETUNE")
        self.assertEqual(periods["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE")
        self.assertEqual(
            periods["fresh_prospective_cutoff_mt5_server_close"],
            "2026-06-23 18:15:00",
        )

    def test_search_multiplicity_and_candidate_pool_are_protected(self) -> None:
        rules = self.guardrails["exploration_rules"]
        self.assertTrue(rules["predeclare_search_space"])
        self.assertTrue(rules["record_every_attempted_rule_and_parameter_cell"])
        self.assertTrue(rules["record_total_search_count_and_search_multiplicity"])
        self.assertEqual(rules["candidate_pool_silent_removal"], "forbidden")
        self.assertEqual(rules["simple_metric_sum_across_same_lineage"], "forbidden")
        self.assertEqual(
            rules["post_hoc_threshold_change_after_validation_test_or_2026"],
            "forbidden",
        )

    def test_guardrails_are_referenced_by_governance_files(self) -> None:
        expected = "config/gold_ml_v1/exploration_guardrails_20260625.json"
        self.assertEqual(self.state["exploration_guardrails"], expected)
        self.assertIn(expected, self.agents)
        self.assertTrue(self.state["audit_only"])
        self.assertTrue(self.action["audit_only"])
        self.assertFalse(self.action["live_ready"])

    def test_one_click_handoff_requires_predeclared_cost_grid(self) -> None:
        self.assertIn("RUN_GOLD_ML_V1_NEXT.bat", self.handoff)
        self.assertIn("predeclare", self.handoff.lower())
        self.assertIn("search", self.handoff.lower())
        self.assertIn("2026", self.handoff)


if __name__ == "__main__":
    unittest.main()
