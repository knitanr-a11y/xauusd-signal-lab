from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = read_json("config/gold_ml_v1/exploration_guardrails_20260625.json")
        self.state = read_json("config/gold_ml_v1/current_state_snapshot_20260624.json")
        self.action = read_json("config/gold_ml_v1/next_local_action.json")
        self.batch = read_json("config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json")

    def test_frozen_years_and_multiplicity(self) -> None:
        expected = {
            "2023": "EXPLORATION_ONLY",
            "2024": "VALIDATION_ONLY_NO_RETUNE",
            "2025": "FINAL_TEST_ONLY_NO_RETUNE",
            "2026": "DIAGNOSTIC_ONLY_NEVER_RETUNE",
        }
        for year, value in expected.items():
            self.assertEqual(self.guardrails["period_contract"][year], value)
            self.assertEqual(self.batch["period_contract"][year], value)
        self.assertEqual(self.batch["search_space"]["full_cartesian_cell_count"], 36)
        self.assertEqual(self.batch["multiplicity_contract"]["attempted_cells"], 36)
        self.assertTrue(self.batch["search_space"]["all_cells_must_be_reported"])

    def test_frozen_nine_and_new_lineage_are_separate(self) -> None:
        frozen = self.guardrails["current_candidate_pool"]["frozen_accumulated_ids"]
        self.assertEqual(len(frozen), 9)
        self.assertEqual(self.batch["existing_frozen_nine"], frozen)
        self.assertEqual(self.batch["existing_pool_change"], "FORBIDDEN")
        self.assertEqual(
            self.batch["new_lineage"]["lineage_id"],
            "M15_H1_TREND_PULLBACK_LINEAGE_EXP024",
        )
        self.assertFalse(self.action["existing_frozen_nine_modified"])

    def test_current_local_action_is_input_packaging_only(self) -> None:
        self.assertEqual(self.action["mode"], "bat")
        self.assertTrue(self.action["runner"].endswith("package_batch024_raw_for_assistant.bat"))
        self.assertEqual(self.action["phase"], "PACKAGE_INPUT_ONLY_NO_LOCAL_EXPLORATION")
        self.assertFalse(self.action["local_exploration_executed"])
        self.assertFalse(self.action["local_exploration_allowed"])
        self.assertTrue(self.action["assistant_exploration_authorized"])
        self.assertTrue(self.action["assistant_exploration_required_before_local_reproduction"])
        self.assertTrue(self.action["primary_upload_path"].endswith(".zip"))
        self.assertEqual(
            self.state["next"],
            "USER_UPLOADS_HASH_VERIFIED_RAW_ZIP_THEN_ASSISTANT_EXECUTES_EXPLORATION",
        )

    def test_leakage_bridge_and_automatic_actions_are_blocked(self) -> None:
        evaluation = self.guardrails["data_and_evaluation_rules"]
        self.assertTrue(evaluation["closed_bars_only"])
        self.assertEqual(evaluation["lookahead"], "forbidden")
        self.assertEqual(evaluation["future_label_or_exit_data_in_features"], "forbidden")
        self.assertEqual(self.batch["input_contract"]["warmup_bridge_use"], "forbidden")
        self.assertTrue(self.batch["input_contract"]["confirmed_h1_asof_join"])
        self.assertEqual(self.batch["signal_contract"]["same_m1_tp_sl_priority"], "SL")
        for key in (
            "automatic_next_phase",
            "automatic_accumulation",
            "automatic_promotion",
            "automatic_registration",
            "live_ready",
            "final_signal",
            "mt5_order",
            "discord",
            "ai_api",
            "live_hook",
        ):
            self.assertFalse(self.action[key])


if __name__ == "__main__":
    unittest.main()
