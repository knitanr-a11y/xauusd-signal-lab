from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mochipoyo_alert_research" / "configure_cloudflare.py"
SPEC = importlib.util.spec_from_file_location("configure_cloudflare", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StageM1LocalConfigTests(unittest.TestCase):
    def test_worker_root_is_normalized_to_events(self) -> None:
        self.assertEqual(
            MODULE.normalize_events_url("https://example.workers.dev"),
            "https://example.workers.dev/events",
        )

    def test_existing_events_path_is_preserved(self) -> None:
        self.assertEqual(
            MODULE.normalize_events_url("https://example.workers.dev/events/"),
            "https://example.workers.dev/events",
        )

    def test_insecure_or_query_urls_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.normalize_events_url("http://example.workers.dev/events")
        with self.assertRaises(ValueError):
            MODULE.normalize_events_url("https://example.workers.dev/events?token=secret")

    def test_local_env_writer_keeps_values_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            MODULE.write_env(
                env_path,
                "https://example.workers.dev/events",
                "test-read-token",
            )
            text = env_path.read_text(encoding="utf-8")
            self.assertIn("MOCHIPOYO_EVENTS_URL=https://example.workers.dev/events", text)
            self.assertIn("MOCHIPOYO_READ_TOKEN=test-read-token", text)
            self.assertNotIn(str(ROOT), str(env_path))


if __name__ == "__main__":
    unittest.main()
