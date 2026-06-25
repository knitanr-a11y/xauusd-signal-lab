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
PROSPECTIVE_FIRST_RUN = ROOT / "config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json"
MONITOR = ROOT / "config/gold_ml_v1/prospective_monitoring_20260625.json"
MONITOR_INIT = ROOT / "config/gold_ml_v1/prospective_monitoring_initialization_pass_20260625.json"
BATCH024_AUTH = ROOT / "config/gold_ml_v1/exploration_batch024_authorization_20260625.json"
BATCH024 = ROOT / "config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json"
BATCH024_CI = ROOT / "config/gold_ml_v1/exploration_batch024_ci_pass_20260625.json"
AGENTS = ROOT / "AGENTS.md"
START_HERE = ROOT / "START_HERE_GOLD_ML_V1_NEXT_CHAT.md"
ONE_CLICK_HANDOFF_V2 = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md"
PASS_HANDOFF = ROOT / "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_BATCH024_CI_PASS_USER_RUN_NEXT_20260625.md"


class ExplorationGuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guardrails = json.loads(GUARDRAILS.read_text(encoding="utf-8"))
        self.state = json.loads(CURRENT_STATE.read_text(encoding="utf-8"))
        self.action = json.loads(NEXT_ACTION.read_text(encoding="utf-8"))
        self.cost_stress = json.loads(COST_STRESS.read_text(encoding="utf-8"))
        self.cost_stress_pass = json.loads(COST_STRESS_PASS.read_text(encoding="utf-8"))
        self.prospective = json.loads(PROSPECTIVE.read_text(encoding="utf-8"))
        self.prospective_first_run = json.loads(
            PROSPECTIVE_FIRST_RUN.read_text(encoding="utf-8")
        )
        self.monitor = json.loads(MONITOR.read_text(encoding="utf-8"))
        self.monitor_init = json.loads(MONITOR_INIT.read_text(encoding="utf-8"))
        self.batch024_auth = json.loads(BATCH024_AUTH.read_text(encoding="utf-8"))
        self.batch024 = json.loads(BATCH024.read_text(encoding="utf-8"))
        self.batch024_ci = json.loads(BATCH024_CI.read_text(encoding="utf-8"))
        self.agents = AGENTS.read_text(encoding="utf-8")
        self.start_here = START_HERE.read_text(encoding="utf-8")
        self.handoff = ONE_CLICK_HANDOFF_V2.read_text(encoding="utf-8")
        self.pass_handoff = PASS_HANDOFF.read_text(encoding="utf-8")

    def test_frozen_period_split_is_consistent(self) -> None:
        periods = self.guardrails["period_contract"]
        self.assertEqual(periods["2023"], "EXPLORATION_ONLY")
        self.assertEqual(periods["2024"], "VALIDATION_ONLY_NO_RETUNE")
        self.assertEqual(periods["2025"], "FINAL_TEST_ONLY_NO_RETUNE")
        self.assertEqual(periods["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE")
        for year in ("2023", "2024", "2025", "2026"):
            self.assertEqual(self.batch024["period_contract"][year], periods[year])
        self.assertEqual(
            self.prospective["cutoff_mt5_server_close"],
            periods["fresh_prospective_cutoff_mt5_server_close"],
        )
        self.assertEqual(
            self.monitor["cutoff_mt5_server_close"],
            periods["fresh_prospective_cutoff_mt5_server_close"],
        )

    def test_existing_candidate_pool_is_immutable(self) -> None:
        pool = self.guardrails["current_candidate_pool"]
        frozen = pool["frozen_accumulated_ids"]
        self.assertEqual(len(frozen), 9)
        self.assertEqual(self.cost_stress["candidate_pool"]["frozen_accumulated_ids"], frozen)
        self.assertEqual(self.prospective["candidate_pool"]["frozen_accumulated_ids"], frozen)
        self.assertEqual(self.monitor["candidate_pool"]["frozen_accumulated_ids"], frozen)
        self.assertEqual(self.batch024["existing_frozen_nine"], frozen)
        self.assertEqual(self.batch024["existing_pool_change"], "FORBIDDEN")
        self.assertTrue(self.batch024_auth["existing_frozen_nine_must_remain_unchanged"])
        self.assertFalse(self.action["existing_frozen_nine_modified"])
        self.assertFalse(self.state["exploration_batch024"]["existing_frozen_nine_modified"])

    def test_search_space_multiplicity_is_predeclared(self) -> None:
        rules = self.guardrails["exploration_rules"]
        self.assertTrue(rules["predeclare_search_space"])
        self.assertTrue(rules["record_every_attempted_rule_and_parameter_cell"])
        self.assertTrue(rules["record_total_search_count_and_search_multiplicity"])
        self.assertTrue(rules["report_all_survivors_and_failures_not_only_best"])
        self.assertEqual(rules["candidate_pool_silent_removal"], "forbidden")
        self.assertEqual(rules["simple_metric_sum_across_same_lineage"], "forbidden")
        self.assertEqual(self.batch024["search_space"]["full_cartesian_cell_count"], 36)
        self.assertEqual(self.batch024["multiplicity_contract"]["attempted_cells"], 36)
        self.assertTrue(self.batch024["search_space"]["all_cells_must_be_reported"])
        self.assertEqual(
            self.batch024["multiplicity_contract"]["best_cell_only_reporting"],
            "forbidden",
        )
        self.assertEqual(
            self.batch024["multiplicity_contract"]["same_lineage_metric_pooling"],
            "forbidden",
        )

    def test_authorization_is_scoped_and_prerequisites_passed(self) -> None:
        self.assertEqual(
            self.batch024_auth["status"], "EXPLICIT_USER_AUTHORIZATION_RECORDED"
        )
        self.assertEqual(
            self.batch024_auth["authorized_scope"],
            "EXPLORATION_BATCH024_M15_H1_PULLBACK_ONLY",
        )
        self.assertEqual(self.cost_stress_pass["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(self.cost_stress_pass["candidate_stress_gate"]["fail"], 0)
        self.assertEqual(self.prospective_first_run["status"], "PASS")
        self.assertEqual(self.monitor_init["status"], "PASS")
        self.assertEqual(self.batch024_ci["status"], "PASS")
        self.assertEqual(self.batch024_ci["attempted_cells"], 36)
        self.assertEqual(self.action["authorized_exploration_scope"], "BATCH024_ONLY")
        self.assertTrue(self.action["new_exploration_allowed"])
        self.assertEqual(
            self.state["candidate_pool"]["authorized_exploration_scope"],
            "BATCH024_ONLY",
        )
        self.assertTrue(self.state["execution_switches"]["new_exploration"])

    def test_data_leakage_and_bridge_use_remain_blocked(self) -> None:
        rules = self.guardrails["data_and_evaluation_rules"]
        self.assertTrue(rules["closed_bars_only"])
        self.assertEqual(rules["lookahead"], "forbidden")
        self.assertEqual(rules["future_label_or_exit_data_in_features"], "forbidden")
        self.assertEqual(rules["missing_rows_or_losses_silent_exclusion"], "forbidden")
        self.assertEqual(rules["warmup_bridge_rows_live_use"], "forbidden")
        self.assertEqual(self.batch024["input_contract"]["lookahead"], "forbidden")
        self.assertEqual(
            self.batch024["input_contract"]["warmup_bridge_use"], "forbidden"
        )
        self.assertTrue(self.batch024["input_contract"]["confirmed_h1_asof_join"])
        self.assertTrue(self.batch024["signal_contract"]["exact_m1_entry_required"])
        self.assertEqual(
            self.batch024["signal_contract"]["same_m1_tp_sl_priority"], "SL"
        )

    def test_batch024_action_is_one_click_and_fail_closed(self) -> None:
        self.assertEqual(self.action["mode"], "bat")
        self.assertEqual(
            self.action["runner"],
            "scripts/gold_ml_v1/exploration/windows/run_batch024_pullback_exploration.bat",
        )
        self.assertEqual(
            self.action["upload_output_dir"],
            "outputs/gold_ml_v1/exploration_batch024_m15_h1_pullback",
        )
        required = {item["path"] for item in self.action["required_paths"]}
        self.assertIn("{RAW_HISTORY_DIR}/gold_v3_2023_2026_m1.csv", required)
        self.assertIn("{RAW_HISTORY_DIR}/gold_v3_2023_2026_m15.csv", required)
        self.assertIn("{RAW_HISTORY_DIR}/gold_v3_2023_2026_h1.csv", required)
        self.assertFalse(self.action["automatic_next_phase"])
        self.assertFalse(self.action["automatic_accumulation"])
        self.assertFalse(self.action["automatic_promotion"])
        self.assertFalse(self.action["automatic_registration"])
        self.assertFalse(self.action["live_ready"])
        self.assertFalse(self.action["final_signal"])
        self.assertFalse(self.action["mt5_order"])
        self.assertFalse(self.action["discord"])

    def test_governance_references_current_handoff(self) -> None:
        guardrail_path = "config/gold_ml_v1/exploration_guardrails_20260625.json"
        v2_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_ONE_CLICK_WORKFLOW_V2_20260625.md"
        batch_path = "config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json"
        ci_path = "config/gold_ml_v1/exploration_batch024_ci_pass_20260625.json"
        handoff_path = "docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_EXPLORATION_BATCH024_CI_PASS_USER_RUN_NEXT_20260625.md"
        self.assertEqual(self.state["exploration_guardrails"], guardrail_path)
        self.assertEqual(self.state["authoritative_handoff"], v2_path)
        self.assertEqual(self.state["latest_phase_handoff"], handoff_path)
        for path in (guardrail_path, v2_path, batch_path, ci_path, handoff_path):
            self.assertIn(path, self.agents)
        self.assertIn(guardrail_path, self.start_here)
        self.assertIn(v2_path, self.start_here)
        self.assertIn(batch_path, self.start_here)
        self.assertIn(ci_path, self.start_here)
        self.assertIn("36", self.pass_handoff)
        self.assertIn("RESEARCH_ONLY", self.pass_handoff)
        self.assertTrue(self.state["audit_only"])


if __name__ == "__main__":
    unittest.main()
