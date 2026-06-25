from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = read_json("config/gold_ml_v1/exploration_guardrails_20260625.json")
        self.state = read_json("config/gold_ml_v1/current_state_snapshot_20260624.json")
        self.action = read_json("config/gold_ml_v1/next_local_action.json")
        self.batch024 = read_json("config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json")
        self.cost_pass = read_json("config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json")
        self.monitor_init = read_json("config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json")
        self.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.start = (ROOT / "START_HERE_GOLD_ML_V1_NEXT_CHAT.md").read_text(encoding="utf-8")
        self.handoff_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ASSISTANT_EXPLORATION_RAW_UPLOAD_NEXT_20260625.md"
        self.handoff = (ROOT / self.handoff_path).read_text(encoding="utf-8")

    def test_year_contract_and_search_multiplicity(self) -> None:
        periods = self.guardrails["period_contract"]
        self.assertEqual(periods["2023"], "EXPLORATION_ONLY")
        self.assertEqual(periods["2024"], "VALIDATION_ONLY_NO_RETUNE")
        self.assertEqual(periods["2025"], "FINAL_TEST_ONLY_NO_RETUNE")
        self.assertEqual(periods["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE")
        for year in ("2023", "2024", "2025", "2026"):
            self.assertEqual(self.batch024["period_contract"][year], periods[year])
        self.assertEqual(self.batch024["search_space"]["full_cartesian_cell_count"], 36)
        self.assertEqual(self.batch024["multiplicity_contract"]["attempted_cells"], 36)
        self.assertTrue(self.batch024["search_space"]["all_cells_must_be_reported"])

    def test_frozen_nine_remain_unchanged(self) -> None:
        frozen = self.guardrails["current_candidate_pool"]["frozen_accumulated_ids"]
        self.assertEqual(len(frozen), 9)
        self.assertEqual(self.batch024["existing_frozen_nine"], frozen)
        self.assertFalse(self.action["existing_frozen_nine_modified"])
        self.assertFalse(self.state["exploration_batch024"]["existing_frozen_nine_modified"])
        self.assertEqual(self.cost_pass["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(self.cost_pass["candidate_stress_gate"]["fail"], 0)
        self.assertEqual(self.monitor_init["status"], "PASS")

    def test_current_action_only_packages_raw_for_assistant(self) -> None:
        self.assertEqual(self.action["mode"], "bat")
        self.assertEqual(
            self.action["runner"],
            "scripts/gold_ml_v1/exploration/windows/package_batch024_raw_for_assistant.bat",
        )
        self.assertEqual(self.action["phase"], "PACKAGE_INPUT_ONLY_NO_LOCAL_EXPLORATION")
        self.assertFalse(self.action["local_exploration_executed"])
        self.assertFalse(self.action["local_exploration_allowed"])
        self.assertTrue(self.action["assistant_exploration_authorized"])
        self.assertTrue(self.action["assistant_exploration_required_before_local_reproduction"])
        self.assertTrue(self.action["primary_upload_path"].endswith(".zip"))
        required = {item["path"] for item in self.action["required_paths"]}
        for name in ("m1", "m15", "h1"):
            self.assertIn(
                f"{{RAW_HISTORY_DIR}}/gold_v3_2023_2026_{name}.csv", required
            )

    def test_leakage_and_automatic_actions_remain_off(self) -> None:
        rules = self.guardrails["data_and_evaluation_rules"]
        self.assertTrue(rules["closed_bars_only"])
        self.assertEqual(rules["lookahead"], "forbidden")
        self.assertEqual(rules["future_label_or_exit_data_in_features"], "forbidden")
        self.assertEqual(self.batch024["input_contract"]["warmup_bridge_use"], "forbidden")
        self.assertTrue(self.batch024["input_contract"]["confirmed_h1_asof_join"])
        self.assertEqual(self.batch024["signal_contract"]["same_m1_tp_sl_priority"], "SL")
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

    def test_current_state_and_docs_match(self) -> None:
        self.assertEqual(self.state["latest_phase_handoff"], self.handoff_path)
        self.assertFalse(self.state["candidate_pool"]["local_exploration_allowed_now"])
        self.assertTrue(self.state["candidate_pool"]["assistant_exploration_authorized_now"])
        self.assertFalse(self.state["exploration_batch024"]["assistant_result_available"])
        self.assertFalse(self.state["exploration_batch024"]["local_reproduction_available"])
        self.assertIn(self.handoff_path, self.agents)
        self.assertIn(self.handoff_path, self.start)
        self.assertIn("36", self.handoff)
        self.assertIn("RESEARCH_ONLY", self.handoff)
        self.assertIn("local reproduction", self.handoff.lower())


if __name__ == "__main__":
    unittest.main()
