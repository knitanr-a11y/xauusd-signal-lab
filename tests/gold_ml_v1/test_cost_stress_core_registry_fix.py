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

    def test_completed_cost_stress_phase_is_preserved(self) -> None:
        pass_record = json.loads(
            (
                ROOT
                / "config/gold_ml_v1/cost_stress_raw_reconstructed_pass_20260625.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(pass_record["candidate_stress_gate"]["pass"], 9)
        self.assertEqual(pass_record["candidate_stress_gate"]["fail"], 0)
        self.assertEqual(pass_record["raw_baseline_parity_checks"], 1687)
        self.assertTrue(
            (
                ROOT
                / "scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat"
            ).exists()
        )

    def test_root_launcher_uses_phase_selected_upload_path(self) -> None:
        launcher = (ROOT / "RUN_GOLD_ML_V1_NEXT.bat").read_text(encoding="utf-8")
        self.assertIn("CURRENT_UPLOAD_PATH.txt", launcher)
        self.assertIn("explorer.exe /select", launcher)
        self.assertIn("pause", launcher.lower())
        self.assertNotIn(
            "outputs\\gold_ml_v1\\cost_stress_raw_reconstructed\\UPLOAD_THIS",
            launcher,
        )

    def test_upload_file_uses_configured_phase_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            next_output = repo / "outputs/gold_ml_v1/next_action"
            phase_output = repo / "outputs/gold_ml_v1/example_phase"
            next_output.mkdir(parents=True)
            phase_output.mkdir(parents=True)
            (next_output / "LATEST_NEXT_ACTION.txt").write_text(
                "status=FAIL\nexit_code=4\n", encoding="utf-8"
            )
            (next_output / "FULL_CONSOLE_LOG.txt").write_text(
                "console marker\n", encoding="utf-8"
            )
            (phase_output / "LATEST_RUN_SUMMARY.txt").write_text(
                "summary marker\n", encoding="utf-8"
            )
            (phase_output / "RUN_ERROR.txt").write_text(
                "trace marker\n", encoding="utf-8"
            )
            config = {
                "upload_output_dir": "outputs/gold_ml_v1/example_phase",
                "upload_filename": "UPLOAD_THIS_GOLD_ML_V1.txt",
                "upload_sections": [
                    {
                        "title": "SUMMARY",
                        "path": "outputs/gold_ml_v1/example_phase/LATEST_RUN_SUMMARY.txt",
                        "max_lines": 20,
                    },
                    {
                        "title": "ERROR",
                        "path": "outputs/gold_ml_v1/example_phase/RUN_ERROR.txt",
                        "max_lines": 20,
                    },
                ],
            }
            path = write_upload_file(
                repo,
                4,
                action_id="TEST-UPLOAD-FILE",
                runner="runner.bat",
                error="example",
                config=config,
                mapping={
                    "REPO_ROOT": str(repo),
                    "USER_HOME": str(repo),
                    "MQL5_FILES": str(repo),
                    "RAW_HISTORY_DIR": str(repo),
                    "BATCH023_ZIP": str(repo / "batch.zip"),
                },
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("console marker", text)
            self.assertIn("summary marker", text)
            self.assertIn("trace marker", text)
            self.assertEqual(
                path,
                phase_output / "UPLOAD_THIS_GOLD_ML_V1.txt",
            )
            current_path = (next_output / "CURRENT_UPLOAD_PATH.txt").read_text(
                encoding="utf-8"
            ).strip()
            self.assertEqual(Path(current_path), path.resolve())


if __name__ == "__main__":
    unittest.main()
