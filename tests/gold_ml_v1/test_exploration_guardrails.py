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
        self.contract = load("config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_20260625.json")
        self.audit = load("config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_pre_admission_audit_20260625.json")
        self.stack = load("config/gold_ml_v1/provisional_candidate_stack_20260624.json")

    def test_time_and_frozen_periods(self) -> None:
        self.assertEqual(self.contract["time_contract"]["csv_time"], "MT5 server bar-open time")
        self.assertEqual(self.state["period_contract"]["2023"], "EXPLORATION_ONLY")
        self.assertEqual(self.state["period_contract"]["2024"], "VALIDATION_ONLY_NO_RETUNE")
        self.assertEqual(self.state["period_contract"]["2025"], "FINAL_TEST_ONLY_NO_RETUNE")
        self.assertEqual(self.state["period_contract"]["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE")

    def test_candidate_is_provisional_not_accumulated(self) -> None:
        self.assertEqual(self.stack["accumulated_candidate_total"], 9)
        self.assertIn("GML1-PROV-030-A", self.stack["provisional_research_only_ids"])
        accumulated = (
            self.stack["core_accumulated_ids"]
            + self.stack["user_authorized_accumulated_ids"]
            + self.stack["validation_admitted_accumulated_ids"]
        )
        self.assertNotIn("GML1-PROV-030-A", accumulated)
        self.assertFalse(self.state["candidate_pool"]["existing_frozen_nine_modified"])

    def test_corrected_pre_admission_contract(self) -> None:
        self.assertEqual(self.audit["status"], "PASS_CORRECTED_DEPLOYABLE_ORDERING")
        self.assertEqual(self.audit["corrected_pre_admission_rows"], 247)
        self.assertEqual(self.audit["corrected_cost_stress"]["pass"], 12)
        self.assertEqual(self.audit["corrected_cost_stress"]["fail"], 0)
        self.assertEqual(
            self.contract["canonical_reproduction"]["candidate_trades_sha256"],
            "47912c3131f6917ecae31c13a797568aacca1a08a8b655721d5527e295e579c3",
        )
        self.assertEqual(self.contract["canonical_reproduction"]["candidate_trade_rows"], 247)

    def test_current_action_is_local_audit_only(self) -> None:
        self.assertEqual(self.action["mode"], "bat")
        self.assertTrue(self.action["runner"].endswith("reproduce_prov030a.bat"))
        self.assertTrue(self.action["local_reproduction_allowed"])
        self.assertFalse(self.action["local_exploration_allowed"])
        self.assertFalse(self.action["existing_frozen_nine_modified"])
        for key in (
            "live_ready", "final_signal", "mt5_order", "discord", "ai_api", "live_hook",
            "automatic_accumulation", "automatic_promotion", "automatic_registration",
        ):
            self.assertFalse(self.action[key])


if __name__ == "__main__":
    unittest.main()
