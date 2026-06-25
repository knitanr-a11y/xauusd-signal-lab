from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARDRAILS = ROOT / "config/gold_ml_v1/exploration_guardrails_20260625.json"
CURRENT_STATE = ROOT / "config/gold_ml_v1/current_state_snapshot_20260624.json"
NEXT_ACTION = ROOT / "config/gold_ml_v1/next_local_action.json"
COST_STRESS = ROOT / "config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json"
COST_STRESS_PASS = ROOT / "config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json"
PROSPECTIVE = ROOT / "config/gold_ml_v1/fresh_prospective_confirmation_20260625.json"
AGENTS = ROOT / "AGENTS.md"
START_HERE = ROOT / "START_HERE_GOLD_ML_V1_NEXT_CHAT.md"
ONE_CLICK_HANDOFF_V2 = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md"
TRIPLE_CHECK = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md"
CORE_FIX_HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_CORE_REGISTRY_FIX_USER_RERUN_NEXT_20260625.md"
PASS_HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASS_FRESH_PROSPECTIVE_NEXT_20260625.md"


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = json.loads(GUARDRAILS.read_text(encoding="utf-8"))
        self.state = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        self.action = json.loads(NEXT_ACTION.read_text(encoding="utf-8"))
        self.cost_stress = json.loads(COST_STRESS.read_text(encoding="utf-8"))
        self.cost_stress_pass = json.loads(COST_STRESS_PASS.read_text(encoding="utf-8"))
        self.prospective = json.loads(PROSPECTIVE.read_text(encoding="utf-8"))
        self.agents = AGENTS.read_text(encoding="utf-8")
        self.start_here = START_HERE.read_text(encoding="utf-8")
        self.handoff = ONE_CLICK_HANDOFF_V2.read_text(encoding="utf-8")
        self.triple_check = TRIPLE_CHECK.read_text(encoding="utf-8")
        self.core_fix_handoff = CORE_FIX_HANDOFF.read_text(encoding="utf-8")
        self.pass_handoff = PASS_HANDOFF.read_text(encoding="utf-8")

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
        self.assertEqual(
            self.prospective["cutoff_mt5_server_close"],
            "2026-06-23 18:15:00",
        )

    def test_search_multiplicity_and_candidate_pool_are_protected(self) -> None:
        rules = self.guardrails["exploration_rules"]
        pool = self.guardrails["current_candidate_pool"]
        self.assertTrue(rules["predeclare_search_space"])
        self.assertTrue(rules["record_every_attempted_rule_and_parameter_cell"])
        self.assertTrue(rules["record_total_search_count_and_search_multiplicity"])
        self.assertTrue(rules["report_all_survivors_and_failures_not_only_best"])
        self.assertEqual(rules["candidate_pool_silent_removal"], "forbidden")
        self.assertEqual(rules["simple_metric_sum_across_same_lineage"], "forbidden")
        self.assertEqual(
            rules["post_hoc_threshold_change_after_validation_test_or_2026"],
            "forbidden",
        )
        self.assertEqual(len(pool["frozen_accumulated_ids"]), 9)
        self.assertEqual(len(pool["research_only_ids"]), 3)
        self.assertEqual(pool["silent_add_remove_or_relabel"], "forbidden")
        self.assertTrue(pool["separate_research_must_not_modify_current_nine"])
        self.assertEqual(
            self.cost_stress["candidate_pool"]["frozen_accumulated_ids"],
            pool["frozen_accumulated_ids"],
        )
        self.assertEqual(
            self.prospective["candidate_pool"]["frozen_accumulated_ids"],
            pool["frozen_accumulated_ids"],
        )
        self.assertEqual(
            self.prospective["candidate_pool"]["silent_add_remove_replace_or_relabel"],
            "forbidden",
        )

    def test_data_leakage_and_bridge_use_are_blocked(self) -> None:
        rules = self.guardrails["data_and_evaluation_rules"]
        self.assertTrue(rules["closed_bars_only"])
        self.assertEqual(rules["lookahead"], "forbidden")
        self.assertEqual(rules["future_label_or_exit_data_in_features"], "forbidden")
        self.assertEqual(rules["missing_rows_or_losses_silent_exclusion"], "forbidden")
        self.assertTrue(rules["raw_reconstructed_and_warmup_bridge_rows_must_be_separate"])
        self.assertEqual(rules["warmup_bridge_rows_live_use"], "forbidden")
        population = self.cost_stress["population_contract"]
        self.assertEqual(population["primary"], "RAW_RECONSTRUCTED")
        self.assertEqual(population["secondary_separate_only"], "WARMUP_BRIDGE_EXACT")
        self.assertEqual(population["bridge_primary_population_use"], "forbidden")
        self.assertTrue(population["fixed_trade_population"])
        self.assertEqual(
            self.cost_stress["registry_contract"]["authoritative_input"],
            "*_warmup_bridge_core_registry.csv",
        )
        self.assertFalse(
            self.cost_stress["registry_contract"]["entry_price_or_exit_price_required"]
        )
        causality = self.prospective["causality_contract"]
        self.assertFalse(causality["candidate_generation_uses_future_exit_information"])
        self.assertTrue(causality["unresolved_candidates_preserved"])
        self.assertTrue(causality["suppressed_parent_events_recorded"])
        self.assertEqual(
            causality["missing_rows_or_losses_silent_exclusion"], "forbidden"
        )

    def test_governance_references_verified_pass_and_prospective_contract(self) -> None:
        guardrail_path = "config/gold_ml_v1/exploration_guardrails_20260625.json"
        v2_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md"
        cost_path = "config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json"
        pass_path = "config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json"
        prospective_path = "config/gold_ml_v1/fresh_prospective_confirmation_20260625.json"
        pass_handoff_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_PASS_FRESH_PROSPECTIVE_NEXT_20260625.md"
        self.assertEqual(self.state["exploration_guardrails"], guardrail_path)
        self.assertEqual(self.state["authoritative_handoff"], v2_path)
        self.assertIn(guardrail_path, self.agents)
        self.assertIn(v2_path, self.agents)
        self.assertIn(cost_path, self.agents)
        self.assertIn(pass_path, self.agents)
        self.assertIn(pass_handoff_path, self.agents)
        self.assertIn(guardrail_path, self.start_here)
        self.assertIn(v2_path, self.start_here)
        self.assertTrue(self.state["audit_only"])
        self.assertFalse(self.state["execution_switches"]["new_exploration"])
        self.assertTrue(PROSPECTIVE.exists())
        self.assertEqual(prospective_path, "config/gold_ml_v1/fresh_prospective_confirmation_20260625.json")

    def test_cost_stress_pass_and_fresh_prospective_action_are_fail_closed(self) -> None:
        self.assertEqual(self.cost_stress_pass["status"], "PASS")
        self.assertEqual(self.cost_stress_pass["raw_baseline_parity_checks"], 1687)
        self.assertEqual(self.cost_stress_pass["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(self.cost_stress_pass["candidate_stress_gate"]["fail"], 0)
        self.assertEqual(self.action["mode"], "bat")
        self.assertEqual(
            self.action["runner"],
            "scripts/gold_ml_v1/prospective/windows/run_fresh_prospective_confirmation.bat",
        )
        self.assertEqual(
            self.action["upload_output_dir"],
            "outputs/gold_ml_v1/fresh_prospective_confirmation",
        )
        required_paths = {item["path"] for item in self.action["required_paths"]}
        for filename in (
            "goldsharp_m1.csv",
            "goldsharp_m15.csv",
            "goldsharp_h1.csv",
            "goldsharp_h4.csv",
            "goldsharp_d1.csv",
        ):
            self.assertIn(f"{{MQL5_FILES}}/{filename}", required_paths)
        self.assertFalse(self.action["automatic_next_phase"])
        self.assertFalse(self.action["automatic_promotion"])
        self.assertFalse(self.action["automatic_registration"])
        self.assertFalse(self.action["live_ready"])
        self.assertFalse(self.action["final_signal"])
        self.assertFalse(self.action["mt5_order"])


if __name__ == "__main__":
    unittest.main()
