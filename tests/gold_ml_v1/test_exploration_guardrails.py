from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARDRAILS = ROOT / "config/gold_ml_v1/exploration_guardrails_20260625.json"
CURRENT_STATE = ROOT / "config/gold_ml_v1/current_state_snapshot_20260624.json"
NEXT_ACTION = ROOT / "config/gold_ml_v1/next_local_action.json"
COST_STRESS = ROOT / "config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json"
AGENTS = ROOT / "AGENTS.md"
START_HERE = ROOT / "START_HERE_GOLD_ML_V1_NEXT_CHAT.md"
ONE_CLICK_HANDOFF_V2 = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md"
TRIPLE_CHECK = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_GUARDRAILS_TRIPLE_CHECK_20260625.md"
COST_STRESS_HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_CORE_REGISTRY_FIX_USER_RERUN_NEXT_20260625.md"


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = json.loads(GUARDRAILS.read_text(encoding="utf-8"))
        self.state = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        self.action = json.loads(NEXT_ACTION.read_text(encoding="utf-8"))
        self.cost_stress = json.loads(COST_STRESS.read_text(encoding="utf-8"))
        self.agents = AGENTS.read_text(encoding="utf-8")
        self.start_here = START_HERE.read_text(encoding="utf-8")
        self.handoff = ONE_CLICK_HANDOFF_V2.read_text(encoding="utf-8")
        self.triple_check = TRIPLE_CHECK.read_text(encoding="utf-8")
        self.cost_handoff = COST_STRESS_HANDOFF.read_text(encoding="utf-8")

    def test_frozen_period_split(self) -> None:
        periods = self.guardrails["period_contract"]
        self.assertEqual(periods["2023"], "EXPLORATION_ONLY")
        self.assertEqual(periods["2024"], "VALIDATION_ONLY_NO_RETUNE")
        self.assertEqual(periods["2025"], "FINAL_TEST_ONLY_NO_RETUNE")
        self.assertEqual(periods["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE")
        self.assertEqual(periods["fresh_prospective_cutoff_mt5_server_close"], "2026-06-23 18:15:00")

    def test_search_multiplicity_and_candidate_pool_are_protected(self) -> None:
        rules = self.guardrails["exploration_rules"]
        pool = self.guardrails["current_candidate_pool"]
        self.assertTrue(rules["predeclare_search_space"])
        self.assertTrue(rules["record_every_attempted_rule_and_parameter_cell"])
        self.assertTrue(rules["record_total_search_count_and_search_multiplicity"])
        self.assertTrue(rules["report_all_survivors_and_failures_not_only_best"])
        self.assertEqual(rules["candidate_pool_silent_removal"], "forbidden")
        self.assertEqual(rules["simple_metric_sum_across_same_lineage"], "forbidden")
        self.assertEqual(rules["post_hoc_threshold_change_after_validation_test_or_2026"], "forbidden")
        self.assertEqual(len(pool["frozen_accumulated_ids"]), 9)
        self.assertEqual(len(pool["research_only_ids"]), 3)
        self.assertEqual(pool["silent_add_remove_or_relabel"], "forbidden")
        self.assertTrue(pool["separate_research_must_not_modify_current_nine"])
        self.assertIn("forbidden", pool["new_exploration_before_cost_stress_and_fresh_confirmation"])
        self.assertEqual(self.cost_stress["candidate_pool"]["frozen_accumulated_ids"], pool["frozen_accumulated_ids"])
        self.assertEqual(self.cost_stress["candidate_pool"]["research_only_ids"], pool["research_only_ids"])

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
        self.assertEqual(self.cost_stress["registry_contract"]["authoritative_input"], "*_warmup_bridge_core_registry.csv")
        self.assertFalse(self.cost_stress["registry_contract"]["entry_price_or_exit_price_required"])
        self.assertEqual(self.cost_stress["time_and_execution_contract"]["bridge_execution"]["synthetic_stress_result"], "forbidden")

    def test_guardrails_are_referenced_by_governance_files(self) -> None:
        guardrail_path = "config/gold_ml_v1/exploration_guardrails_20260625.json"
        v2_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md"
        cost_path = "config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json"
        cost_handoff_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_COST_STRESS_CORE_REGISTRY_FIX_USER_RERUN_NEXT_20260625.md"
        self.assertEqual(self.state["exploration_guardrails"], guardrail_path)
        self.assertEqual(self.state["authoritative_handoff"], v2_path)
        self.assertEqual(self.state["latest_phase_handoff"], cost_handoff_path)
        self.assertIn(guardrail_path, self.agents)
        self.assertIn(v2_path, self.agents)
        self.assertIn(cost_path, self.agents)
        self.assertIn(cost_handoff_path, self.agents)
        self.assertIn(guardrail_path, self.start_here)
        self.assertIn(v2_path, self.start_here)
        self.assertIn(cost_handoff_path, self.start_here)
        self.assertTrue(self.state["audit_only"])
        self.assertFalse(self.state["execution_switches"]["new_exploration"])
        self.assertTrue(self.action["audit_only"])
        self.assertFalse(self.action["live_ready"])
        self.assertEqual(self.action["mode"], "bat")
        self.assertEqual(
            self.action["runner"],
            "scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat",
        )

    def test_one_click_and_cost_stress_are_fail_closed(self) -> None:
        self.assertIn("RUN_GOLD_ML_V1_NEXT.bat", self.handoff)
        self.assertIn("fixed-slippage grid", self.handoff)
        self.assertIn("2026: diagnostic only", self.handoff)
        self.assertIn("Every attempted rule", self.triple_check)
        self.assertIn("multiplicity", self.triple_check.lower())
        self.assertIn("No new candidate exploration", self.triple_check)
        self.assertIn("Automatic promotion", self.triple_check)
        self.assertIn("WARMUP_BRIDGE_EXACT", self.handoff)
        self.assertIn("must not be used for exploration", self.handoff)
        self.assertEqual(self.cost_stress["scenario_grid"]["spread_multipliers"], [1.0, 1.5, 2.0])
        self.assertEqual(self.cost_stress["scenario_grid"]["fixed_slippage_points_per_side"], [0, 5, 10, 20])
        self.assertTrue(self.cost_stress["scenario_grid"]["grid_frozen_before_execution"])
        self.assertEqual(self.cost_stress["scenario_grid"]["post_result_grid_change"], "forbidden")
        self.assertIn("INPUT_SCHEMA_ASSUMPTION_BUG", self.cost_handoff)
        self.assertIn("warmup_bridge_core_registry.csv", self.cost_handoff)
        self.assertIn("windows/run_cost_stress_raw_reconstructed.bat", self.cost_handoff)
        self.assertFalse(self.action["automatic_next_phase"])
        self.assertFalse(self.action["automatic_promotion"])
        self.assertFalse(self.action["automatic_registration"])


if __name__ == "__main__":
    unittest.main()
