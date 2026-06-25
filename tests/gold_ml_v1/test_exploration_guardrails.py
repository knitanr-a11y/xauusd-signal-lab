from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load("config/gold_ml_v1/current_state_snapshot_20260624.json")
        self.action = load("config/gold_ml_v1/next_local_action.json")
        self.r24 = load("config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json")
        self.r25 = load("config/gold_ml_v1/exploration_batch025_loss_profile_result_20260625.json")
        self.r26 = load("config/gold_ml_v1/exploration_batch026_shared_loss_tree_result_20260625.json")
        self.r27 = load("config/gold_ml_v1/exploration_batch027_event_families_result_20260625.json")
        self.r28 = load("config/gold_ml_v1/exploration_batch028_breakout_long_result_20260625.json")

    def test_periods_and_time(self) -> None:
        self.assertEqual(self.state["period_contract"]["2023"], "EXPLORATION_ONLY")
        self.assertEqual(self.state["period_contract"]["2024"], "VALIDATION_ONLY_NO_RETUNE")
        self.assertEqual(self.state["period_contract"]["2025"], "FINAL_TEST_ONLY_NO_RETUNE")
        self.assertEqual(self.state["period_contract"]["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE")
        self.assertEqual(self.r24["time_contract"]["csv_time"], "MT5 server naive bar-open time")

    def test_no_new_survivor(self) -> None:
        self.assertEqual(len(self.state["candidate_pool"]["frozen_accumulated_ids"]), 9)
        self.assertFalse(self.state["candidate_pool"]["existing_frozen_nine_modified"])
        self.assertEqual(self.r24["survivor_count"], 0)
        self.assertEqual(self.r25["survivors"], 0)
        self.assertEqual(self.r26["survivors"], 0)
        self.assertEqual(self.r27["survivors"], 0)
        self.assertFalse(self.r28["survivor"])

    def test_local_work_is_disabled(self) -> None:
        self.assertEqual(self.action["mode"], "status_only")
        self.assertIsNone(self.action["runner"])
        self.assertFalse(self.action["local_exploration_allowed"])
        self.assertFalse(self.action["local_reproduction_allowed"])
        self.assertFalse(self.action["local_implementation_allowed"])
        self.assertFalse(self.action["local_user_action_required"])

    def test_research_reset(self) -> None:
        policy = self.state["research_policy_now"]
        self.assertFalse(policy["rescue_failed_batch024_lineage"])
        self.assertTrue(policy["new_independent_base_families_only"])
        self.assertEqual(policy["minimum_2023_count_before_loss_profile_analysis"], 200)
        self.assertFalse(policy["local_implementation_before_survivor"])
        self.assertFalse(self.r28["rescue_tuning"])
        self.assertFalse(self.action["live_ready"])
        self.assertFalse(self.action["mt5_order"])
        self.assertFalse(self.action["automatic_promotion"])


if __name__ == "__main__":
    unittest.main()
