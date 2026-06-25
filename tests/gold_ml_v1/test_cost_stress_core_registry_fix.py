from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/gold_ml_v1/cost_stress"))
sys.path.insert(0, str(ROOT / "scripts/gold_ml_v1"))

from cost_stress_contract import BRIDGE
from cost_stress_engine import recover_risk
from cost_stress_reports import bridge_candidate_summary, bridge_trade_audit
from run_next_local import write_upload_file


class CoreRegistryFixTests(unittest.TestCase):
    def test_risk_fallback(self) -> None:
        row = pd.Series(
            {"r_value": 0.25, "candidate_id": "T", "entry_time": "2026-01-01"}
        )
        self.assertEqual(recover_risk(row, 2.5), 2.5)

    def test_bridge_core_report(self) -> None:
        frame = pd.DataFrame(
            {
                "candidate_id": ["GML1-PROV-010", "GML1-PROV-010"],
                "lineage_id": [
                    "H1_D1_BREAKOUT_FILTER_LINEAGE",
                    "H1_D1_BREAKOUT_FILTER_LINEAGE",
                ],
                "decision_close_time": pd.to_datetime(
                    ["2023-01-04 01:00:00", "2023-01-05 01:00:00"]
                ),
                "entry_time": pd.to_datetime(
                    ["2023-01-04 01:00:00", "2023-01-05 01:00:00"]
                ),
                "exit_time": pd.to_datetime(
                    ["2023-01-04 02:00:00", "2023-01-05 02:00:00"]
                ),
                "r_value": [1.0, -1.0],
                "direction": ["LONG", "LONG"],
                "trade_core_source": [BRIDGE, BRIDGE],
            }
        )
        audit = bridge_trade_audit(frame)
        summary = bridge_candidate_summary(audit)
        self.assertEqual(
            summary.iloc[0]["stress_gate_status"], "NOT_ELIGIBLE_AUDIT_ONLY"
        )
        self.assertEqual(summary.iloc[0]["trade_count"], 2)

    def test_completed_phase_bat_and_root_upload_behavior(self) -> None:
        pass_record = json.loads(
            (
                ROOT
                / "config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(pass_record["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(pass_record["candidate_stress_gate"]["fail"], 0)
        self.assertTrue(
            (
                ROOT
                / "scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat"
            ).exists()
        )
        launcher = (ROOT / "RUN_GOLD_ML_V1_NEXT.bat").read_text(encoding="utf-8")
        self.assertIn("UPLOAD_THIS_GOLD_ML_V1.txt", launcher)
        self.assertIn("explorer.exe /select", launcher)
        self.assertIn("pause", launcher.lower())

    def test_upload_file_collects_only_diagnostic_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            next_output = repo / "outputs/gold_ml_v1/next_action"
            cost_output = repo / "outputs/gold_ml_v1/cost_stress_raw_reconstructed"
            next_output.mkdir(parents=True)
            cost_output.mkdir(parents=True)
            (next_output / "LATEST_NEXT_ACTION.txt").write_text(
                "status=FAIL\nexit_code=4\n", encoding="utf-8"
            )
            (next_output / "FULL_CONSOLE_LOG.txt").write_text(
                "console marker\n", encoding="utf-8"
            )
            (cost_output / "LATEST_RUN_SUMMARY.txt").write_text(
                "summary marker\n", encoding="utf-8"
            )
            (cost_output / "COST_STRESS_RUN_ERROR.txt").write_text(
                "trace marker\n", encoding="utf-8"
            )
            path = write_upload_file(
                repo,
                4,
                action_id="TEST-UPLOAD-FILE",
                runner="runner.bat",
                error="example",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("console marker", text)
            self.assertIn("summary marker", text)
            self.assertIn("trace marker", text)
            self.assertEqual(
                path,
                cost_output / "UPLOAD_THIS_GOLD_ML_V1.txt",
            )
            self.assertTrue(
                (next_output / "PASTE_ME_GOLD_ML_V1.txt").exists()
            )


if __name__ == "__main__":
    unittest.main()
