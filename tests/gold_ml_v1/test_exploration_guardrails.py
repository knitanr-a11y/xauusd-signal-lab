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
        self.result = read_json("config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json")

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
        self.assertEqual(self.result["attempted_cells"], 36)
        self.assertEqual(self.result["survivor_count"], 0)

    def test_open_time_contract_and_frozen_nine(self) -> None:
        frozen = self.guardrails["current_candidate_pool"]["frozen_accumulated_ids"]
        self.assertEqual(len(frozen), 9)
        self.assertEqual(self.batch["existing_frozen_nine"], frozen)
        self.assertFalse(self.action["existing_frozen_nine_modified"])
        self.assertEqual(self.result["time_contract"]["csv_time"], "MT5 server naive bar-open time")
        self.assertEqual(self.result["time_contract"]["M1_close"], "time + 1 minute")
        self.assertEqual(self.result["time_contract"]["M15_close"], "time + 15 minutes")
        self.assertEqual(self.result["time_contract"]["H1_close"], "time + 1 hour")

    def test_current_action_is_reproduction_only(self) -> None:
        self.assertEqual(self.action["mode"], "bat")
        self.assertTrue(self.action["runner"].endswith("reproduce_batch024.bat"))
        self.assertEqual(
            self.action["phase"],
            "LOCAL_REPRODUCTION_AGAINST_ASSISTANT_FROZEN_HASHES",
        )
        self.assertFalse(self.action["local_exploration_allowed"])
        self.assertTrue(self.action["local_reproduction_allowed"])
        self.assertTrue(self.action["assistant_result_available"])
        self.assertEqual(self.action["assistant_survivor_count"], 0)
        self.assertFalse(self.action["candidate_selection_performed"])
        self.assertEqual(
            self.state["next"],
            "USER_RUNS_LOCAL_REPRODUCTION_AND_UPLOADS_PARITY_RESULT",
        )
        self.assertTrue(self.state["exploration_batch024"]["local_reproduction_available"])

    def test_leakage_bridge_and_automatic_actions_are_blocked(self) -> None:
        evaluation = self.guardrails["data_and_evaluation_rules"]
        self.assertTrue(evaluation["closed_bars_only"])
        self.assertEqual(evaluation["lookahead"], "forbidden")
        self.assertEqual(evaluation["future_label_or_exit_data_in_features"], "forbidden")
        self.assertEqual(self.batch["input_contract"]["warmup_bridge_use"], "forbidden")
        self.assertTrue(self.batch["input_contract"]["confirmed_h1_asof_join"])
        self.assertEqual(self.batch["signal_contract"]["same_m1_tp_sl_priority"], "SL")
        self.assertTrue(self.result["interpretation"]["zero_survivors_is_valid"])
        self.assertFalse(self.result["interpretation"]["rescue_tuning_performed"])
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
