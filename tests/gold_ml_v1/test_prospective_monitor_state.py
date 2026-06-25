from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MONITOR_DIR = ROOT / "scripts/gold_ml_v1/monitoring"
if str(MONITOR_DIR) not in sys.path:
    sys.path.insert(0, str(MONITOR_DIR))

from prospective_monitor_state import (  # noqa: E402
    append_run_history,
    input_continuity_snapshot,
    load_previous_monitor,
    reconcile_candidates,
    reconcile_parent_events,
)


def bar_frame(count: int = 3) -> pd.DataFrame:
    opens = pd.date_range("2026-06-25 10:00:00", periods=count, freq="min")
    return pd.DataFrame(
        {
            "bar_open_time": opens,
            "bar_close_time": opens + pd.Timedelta(minutes=1),
            "open": [100.0 + index for index in range(count)],
            "high": [100.5 + index for index in range(count)],
            "low": [99.5 + index for index in range(count)],
            "close": [100.2 + index for index in range(count)],
            "tick_volume": [10 + index for index in range(count)],
            "spread": [2 for _ in range(count)],
            "real_volume": [0 for _ in range(count)],
        }
    )


def candidate_row(
    candidate_id: str,
    decision: str,
    resolution_state: str,
    outcome: str,
    exit_time: str | None,
    r_value: float | None,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "lineage_id": "M15_H4_BREAKOUT_FILTER_LINEAGE",
        "decision_close_time": pd.Timestamp(decision),
        "entry_time": pd.Timestamp(decision),
        "entry_price": 100.0,
        "risk_price": 1.0,
        "stop_price": 99.0,
        "target_price": 101.0,
        "horizon_end_time": pd.Timestamp(decision) + pd.Timedelta(hours=6),
        "prospective_state": resolution_state,
        "resolution_state": resolution_state,
        "outcome": outcome,
        "exit_time": pd.Timestamp(exit_time) if exit_time else pd.NaT,
        "exit_price": 101.0 if outcome == "TP" else None,
        "r_value": r_value,
        "current_r": r_value if r_value is not None else 0.25,
        "latest_observed_close_time": pd.Timestamp("2026-06-25 12:00:00"),
        "direction": "LONG",
        "candidate_rule_state": "FROZEN_RULE_MATCH",
    }


class ProspectiveMonitorStateTests(unittest.TestCase):
    def test_input_continuity_allows_append_and_blocks_mutation(self) -> None:
        first = bar_frame(3)
        continuity, advanced = input_continuity_snapshot({"M1": first}, None)
        self.assertTrue(advanced)
        previous_state = {"input_continuity": continuity}

        same_continuity, same_advanced = input_continuity_snapshot(
            {"M1": first.copy()}, previous_state
        )
        self.assertFalse(same_advanced)
        self.assertEqual(
            same_continuity["files"]["M1"]["canonical_full_hash"],
            continuity["files"]["M1"]["canonical_full_hash"],
        )

        appended = bar_frame(4)
        _, appended_advanced = input_continuity_snapshot(
            {"M1": appended}, previous_state
        )
        self.assertTrue(appended_advanced)

        mutated = appended.copy()
        mutated.loc[1, "close"] = 999.0
        with self.assertRaisesRegex(ValueError, "historical closed-bar prefix changed"):
            input_continuity_snapshot({"M1": mutated}, previous_state)

        with self.assertRaisesRegex(ValueError, "input truncated"):
            input_continuity_snapshot({"M1": first.iloc[:2]}, previous_state)

    def test_candidate_unresolved_to_resolved_and_new_candidate(self) -> None:
        previous = pd.DataFrame(
            [
                candidate_row(
                    "GML1-PROV-007",
                    "2026-06-25 10:00:00",
                    "UNRESOLVED",
                    "OPEN",
                    None,
                    None,
                )
            ]
        )
        current = pd.DataFrame(
            [
                candidate_row(
                    "GML1-PROV-007",
                    "2026-06-25 10:00:00",
                    "RESOLVED",
                    "TP",
                    "2026-06-25 10:30:00",
                    1.0,
                ),
                candidate_row(
                    "GML1-PROV-008",
                    "2026-06-25 11:00:00",
                    "UNRESOLVED",
                    "OPEN",
                    None,
                    None,
                ),
            ]
        )
        ledger, new_rows, resolved_rows = reconcile_candidates(previous, current)
        self.assertEqual(len(ledger), 2)
        self.assertEqual(new_rows["candidate_id"].tolist(), ["GML1-PROV-008"])
        self.assertEqual(resolved_rows["candidate_id"].tolist(), ["GML1-PROV-007"])

    def test_candidate_disappearance_and_resolved_rewrite_fail_closed(self) -> None:
        resolved = pd.DataFrame(
            [
                candidate_row(
                    "GML1-PROV-007",
                    "2026-06-25 10:00:00",
                    "RESOLVED",
                    "TP",
                    "2026-06-25 10:30:00",
                    1.0,
                )
            ]
        )
        empty = pd.DataFrame(columns=resolved.columns)
        with self.assertRaisesRegex(ValueError, "disappeared"):
            reconcile_candidates(resolved, empty)

        rewritten = resolved.copy()
        rewritten.loc[0, "outcome"] = "SL"
        rewritten.loc[0, "r_value"] = -1.0
        rewritten.loc[0, "exit_price"] = 99.0
        with self.assertRaisesRegex(ValueError, "resolved field changed"):
            reconcile_candidates(resolved, rewritten)

    def test_parent_suppressed_to_accepted_is_allowed(self) -> None:
        previous = pd.DataFrame(
            [
                {
                    "parent_lineage": "M15_H4_PARENT",
                    "decision_close_time": pd.Timestamp("2026-06-25 11:00:00"),
                    "admission_state": "SUPPRESSED_BY_FROZEN_NON_OVERLAP",
                    "upper_wick_frac": 0.1,
                }
            ]
        )
        current = pd.DataFrame(
            [
                {
                    "parent_lineage": "M15_H4_PARENT",
                    "decision_close_time": pd.Timestamp("2026-06-25 11:00:00"),
                    "admission_state": "ACCEPTED_PARENT_EVENT",
                    "upper_wick_frac": 0.1,
                    "resolution_state": "UNRESOLVED",
                    "prospective_state": "UNRESOLVED",
                    "outcome": "OPEN",
                    "entry_time": pd.Timestamp("2026-06-25 11:00:00"),
                }
            ]
        )
        ledger, new_rows, transitions = reconcile_parent_events(previous, current)
        self.assertEqual(len(ledger), 1)
        self.assertTrue(new_rows.empty)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions.iloc[0]["admission_state"], "ACCEPTED_PARENT_EVENT")

    def test_accepted_parent_cannot_regress_to_suppressed(self) -> None:
        accepted = pd.DataFrame(
            [
                {
                    "parent_lineage": "M15_H4_PARENT",
                    "decision_close_time": pd.Timestamp("2026-06-25 11:00:00"),
                    "admission_state": "ACCEPTED_PARENT_EVENT",
                    "resolution_state": "UNRESOLVED",
                    "prospective_state": "UNRESOLVED",
                    "outcome": "OPEN",
                    "entry_time": pd.Timestamp("2026-06-25 11:00:00"),
                }
            ]
        )
        suppressed = pd.DataFrame(
            [
                {
                    "parent_lineage": "M15_H4_PARENT",
                    "decision_close_time": pd.Timestamp("2026-06-25 11:00:00"),
                    "admission_state": "SUPPRESSED_BY_FROZEN_NON_OVERLAP",
                }
            ]
        )
        with self.assertRaisesRegex(ValueError, "regressed"):
            reconcile_parent_events(accepted, suppressed)

    def test_partial_state_and_duplicate_run_id_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            (output_dir / "monitor_candidate_ledger.csv").write_text(
                "candidate_id,decision_close_time\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Partial monitor state"):
                load_previous_monitor(output_dir)

        history = pd.DataFrame(
            [{"run_id": "R1", "run_time_local": pd.Timestamp("2026-06-25 10:00:00")}]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate run_id"):
            append_run_history(
                history,
                {"run_id": "R1", "run_time_local": pd.Timestamp("2026-06-25 11:00:00")},
            )

    def test_monitor_config_keeps_all_execution_switches_off(self) -> None:
        config = json.loads(
            (
                ROOT / "config/gold_ml_v1/prospective_monitoring_20260625.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(len(config["candidate_pool"]["frozen_accumulated_ids"]), 9)
        self.assertTrue(
            all(value is False for value in config["execution_switches"].values())
        )
        self.assertFalse(config["run_contract"]["background_task_installed"])
        self.assertEqual(
            config["ledger_contract"]["allowed_candidate_transition"],
            "UNRESOLVED_TO_RESOLVED",
        )


if __name__ == "__main__":
    unittest.main()
