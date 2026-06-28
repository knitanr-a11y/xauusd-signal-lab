from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.historical_state = load(
            "config/gold_ml_v1/current_state_snapshot_20260624.json"
        )
        self.contract = load(
            "config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_20260625.json"
        )
        self.audit = load(
            "config/gold_ml_v1/provisional_candidate_gml1_prov_030_a_pre_admission_audit_20260625.json"
        )
        self.stack = load(
            "config/gold_ml_v1/provisional_candidate_stack_20260624.json"
        )
        self.current_state = load("config/gold_ml_v1/current_state_20260628.json")
        self.next_action = load("config/gold_ml_v1/next_action_20260628.json")
        self.local_action = load("config/gold_ml_v1/next_local_action.json")

    def test_time_and_frozen_periods(self) -> None:
        self.assertEqual(
            self.contract["time_contract"]["csv_time"],
            "MT5 server bar-open time",
        )
        self.assertEqual(
            self.historical_state["period_contract"]["2023"],
            "EXPLORATION_ONLY",
        )
        self.assertEqual(
            self.historical_state["period_contract"]["2024"],
            "VALIDATION_ONLY_NO_RETUNE",
        )
        self.assertEqual(
            self.historical_state["period_contract"]["2025"],
            "FINAL_TEST_ONLY_NO_RETUNE",
        )
        self.assertEqual(
            self.historical_state["period_contract"]["2026"],
            "DIAGNOSTIC_ONLY_NEVER_RETUNE",
        )

    def test_candidate_is_provisional_not_accumulated(self) -> None:
        self.assertIn(
            "GML1-PROV-030-A",
            self.historical_state["candidate_pool"][
                "provisional_research_only_ids"
            ],
        )
        self.assertEqual(self.stack["accumulated_candidate_total"], 15)
        self.assertNotIn("GML1-PROV-030-A", self.stack["accumulated_ids"])
        self.assertIn(
            "GML1_PROV_030_A", self.current_state["absolute_exclusions"]
        )
        self.assertFalse(
            self.historical_state["candidate_pool"][
                "existing_frozen_nine_modified"
            ]
        )
        self.assertFalse(self.stack["existing_frozen_nine_modified"])

    def test_corrected_pre_admission_contract(self) -> None:
        self.assertEqual(
            self.audit["status"], "PASS_CORRECTED_DEPLOYABLE_ORDERING"
        )
        self.assertEqual(self.audit["corrected_pre_admission_rows"], 247)
        self.assertEqual(self.audit["corrected_cost_stress"]["pass"], 12)
        self.assertEqual(self.audit["corrected_cost_stress"]["fail"], 0)
        self.assertEqual(
            self.contract["canonical_reproduction"]["candidate_trades_sha256"],
            "47912c3131f6917ecae31c13a797568aacca1a08a8b655721d5527e295e579c3",
        )
        self.assertEqual(
            self.contract["canonical_reproduction"]["candidate_trade_rows"],
            247,
        )

    def test_current_four_sleeve_handoff_is_fail_closed(self) -> None:
        self.assertEqual(
            self.current_state["formal_status"],
            "GML1_LIVE_AUDIT_4_SLEEVES_READY_P16_P19_HISTORICAL_ONLY_NEW_DISCOVERY_NEXT",
        )
        self.assertEqual(
            set(self.current_state["live_audit_runtime"]["enabled_sleeves"]),
            {"A_CORE", "B_STATE", "P18", "W024A"},
        )
        self.assertEqual(
            set(self.current_state["live_audit_runtime"]["disabled_sleeves"]),
            {"P16", "P19"},
        )
        self.assertTrue(
            self.current_state["live_audit_runtime"]["first_run_no_backfill"]
        )
        self.assertFalse(
            self.current_state["p16_p19_recovery"]["trained_models_recovered"]
        )
        self.assertFalse(
            self.current_state["p16_p19_recovery"]["inference_code_recovered"]
        )
        for key in (
            "final_signal",
            "discord",
            "mt5_order",
            "automatic_retraining",
            "automatic_promotion",
            "automatic_registration",
        ):
            self.assertFalse(self.current_state["controls"][key])

    def test_current_discovery_action_preserves_label_free_ordering(self) -> None:
        self.assertEqual(
            self.next_action["action_id"],
            "GML1-NEW-INDEPENDENT-CANDIDATE-DISCOVERY-V1",
        )
        self.assertTrue(self.next_action["audit_only"])
        self.assertFalse(
            self.next_action["labels_may_be_inspected_before_density_freeze"]
        )
        self.assertFalse(self.next_action["final_signal"])
        self.assertFalse(self.next_action["discord"])
        self.assertFalse(self.next_action["mt5_order"])
        required_order = self.next_action["required_order"]
        self.assertLess(
            required_order.index(
                "run label-free density regime direction time and overlap audit"
            ),
            required_order.index("join labels only after freeze"),
        )

    def test_local_pointer_is_status_only_and_never_auto_runs(self) -> None:
        self.assertEqual(self.local_action["mode"], "status_only")
        self.assertIsNone(self.local_action["runner"])
        self.assertFalse(self.local_action["local_user_action_required"])
        self.assertFalse(self.local_action["local_exploration_allowed"])
        self.assertFalse(self.local_action["local_reproduction_allowed"])
        self.assertFalse(self.local_action["local_implementation_allowed"])
        self.assertTrue(self.local_action["audit_only"])
        for key in (
            "live_ready",
            "final_signal",
            "mt5_order",
            "discord",
            "ai_api",
            "live_hook",
            "automatic_accumulation",
            "automatic_promotion",
            "automatic_registration",
        ):
            self.assertFalse(self.local_action[key])


if __name__ == "__main__":
    unittest.main()
