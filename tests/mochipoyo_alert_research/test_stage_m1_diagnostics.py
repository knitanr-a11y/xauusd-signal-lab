from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mochipoyo_alert_research" / "collect_events_once.py"
SPEC = importlib.util.spec_from_file_location("mochipoyo_collect_events_once", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StageM1DiagnosticTests(unittest.TestCase):
    def test_request_label_never_contains_worker_host(self) -> None:
        label = MODULE.request_label(4, 500)
        self.assertEqual(label, "<configured-worker>/events?after_id=4&limit=500")
        self.assertNotIn("workers.dev", label)

    def test_http_error_classifies_rejected_token(self) -> None:
        message = str(MODULE._http_failure(403, "Forbidden"))
        self.assertIn("READ_TOKEN was rejected", message)
        self.assertIn("Cloudflare HTTP 403", message)

    def test_http_error_classifies_bad_path(self) -> None:
        message = str(MODULE._http_failure(404, "Not Found"))
        self.assertIn("Worker URL or /events path was not found", message)

    def test_atomic_diagnostic_json_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "logs" / "latest_collection_error.json"
            MODULE.atomic_write_json(path, {"status": "FAIL", "secrets_logged": False})
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "FAIL")
            self.assertFalse(payload["secrets_logged"])
            self.assertFalse(path.with_suffix(path.suffix + ".tmp").exists())


if __name__ == "__main__":
    unittest.main()
