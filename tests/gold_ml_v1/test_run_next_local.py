from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/run_next_local.py"
SPEC = importlib.util.spec_from_file_location("run_next_local", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RunNextLocalTests(unittest.TestCase):
    def test_status_only_writes_success_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            repo_root = Path(temp_name)
            config_dir = repo_root / "config/gold_ml_v1"
            config_dir.mkdir(parents=True)
            config = {
                "action_id": "TEST_STATUS",
                "mode": "status_only",
                "title": "Test status",
                "message": "No action required",
            }
            (config_dir / "next_local_action.json").write_text(
                json.dumps(config), encoding="utf-8"
            )

            loaded = MODULE.load_json(config_dir / "next_local_action.json")
            exit_code = MODULE.run_action(repo_root, loaded)

            self.assertEqual(exit_code, 0)
            summary = repo_root / "outputs/gold_ml_v1/next_action/LATEST_NEXT_ACTION.txt"
            self.assertTrue(summary.exists())
            text = summary.read_text(encoding="utf-8")
            self.assertIn("action_id=TEST_STATUS", text)
            self.assertIn("status=PASS", text)
            self.assertIn("exit_code=0", text)

    def test_detects_mql5_files_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            repo_root = Path(temp_name) / "MQL5" / "Files" / "repo-parent" / "repo"
            repo_root.mkdir(parents=True)
            detected = MODULE.detect_mql5_files(repo_root)
            self.assertEqual(detected, Path(temp_name) / "MQL5" / "Files")


if __name__ == "__main__":
    unittest.main()
