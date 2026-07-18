from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mochipoyo_alert_research" / "run_collect_events_forever.py"
spec = importlib.util.spec_from_file_location("run_collect_events_forever", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class StageM2CollectorLoopTests(unittest.TestCase):
    def test_lock_is_exclusive_and_removed_on_clean_exit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "collector.lock"
            with module.ExclusiveLoopLock(lock_path):
                self.assertTrue(lock_path.is_file())
                with self.assertRaises(RuntimeError):
                    with module.ExclusiveLoopLock(lock_path):
                        pass
            self.assertFalse(lock_path.exists())

    def test_stop_file_present_at_start_runs_no_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_path = root / ".env"
            env_path.write_text("configured=true\n", encoding="utf-8")
            stop_path = root / "STOP_COLLECTOR_LOOP"
            stop_path.write_text("stop\n", encoding="utf-8")
            sentinel = root / "collector_was_called"
            dummy = root / "dummy.py"
            dummy.write_text(
                "from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('called', encoding='utf-8')\n",
                encoding="utf-8",
            )
            status_path = root / "latest_status.json"
            exit_code = module.main(
                [
                    "--env", str(env_path),
                    "--db", str(root / "test.sqlite3"),
                    "--collector-script", str(dummy),
                    "--stop-file", str(stop_path),
                    "--lock-file", str(root / "loop.lock"),
                    "--log", str(root / "loop.log"),
                    "--status", str(status_path),
                    "--max-cycles", "1",
                    "--interval-seconds", "1",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertFalse(sentinel.exists())
            status = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(status["stop_reason"], "STOP_FILE_PRESENT_AT_START")
            self.assertEqual(status["cycles"], 0)

    def test_failed_cycle_does_not_prevent_next_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_path = root / ".env"
            env_path.write_text("configured=true\n", encoding="utf-8")
            counter = root / "counter.txt"
            dummy = root / "dummy.py"
            dummy.write_text(
                "from pathlib import Path\n"
                "import sys\n"
                f"path = Path({str(counter)!r})\n"
                "count = int(path.read_text() if path.exists() else '0') + 1\n"
                "path.write_text(str(count), encoding='utf-8')\n"
                "print('{\"status\":\"FAIL_TEST\"}')\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            status_path = root / "latest_status.json"
            exit_code = module.main(
                [
                    "--env", str(env_path),
                    "--db", str(root / "test.sqlite3"),
                    "--collector-script", str(dummy),
                    "--stop-file", str(root / "STOP_COLLECTOR_LOOP"),
                    "--lock-file", str(root / "loop.lock"),
                    "--log", str(root / "loop.log"),
                    "--status", str(status_path),
                    "--max-cycles", "2",
                    "--interval-seconds", "1",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(counter.read_text(encoding="utf-8"), "2")
            status = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(status["stop_reason"], "MAX_CYCLES")
            self.assertEqual(status["cycles"], 2)
            self.assertEqual(status["failed_cycles"], 2)
            self.assertEqual(status["successful_cycles"], 0)


if __name__ == "__main__":
    unittest.main()
