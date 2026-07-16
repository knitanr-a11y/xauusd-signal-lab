from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mochipoyo_alert_research.db import (  # noqa: E402
    ImmutableCollisionError,
    open_database,
    state_int,
    store_page,
)
from mochipoyo_alert_research.redact import redact_text, redact_url  # noqa: E402

SCHEMA = ROOT / "scripts" / "mochipoyo_alert_research" / "schema.sql"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "events_page_1.json"


class StageM1CollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "collector.sqlite3"
        self.connection = open_database(self.db_path, SCHEMA)
        self.events = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"]

    def tearDown(self) -> None:
        self.connection.close()
        self.temp.cleanup()

    def test_first_page_is_atomic_and_advances_cursor(self) -> None:
        result = store_page(
            self.connection,
            self.events,
            after_id_before=0,
            downloaded_at_utc="2026-07-15T10:00:00Z",
        )
        self.assertEqual(result.inserted_count, 3)
        self.assertEqual(result.duplicate_count, 0)
        self.assertEqual(result.cursor_after, 4)
        self.assertEqual(state_int(self.connection, "last_successful_id"), 4)
        count = self.connection.execute("SELECT COUNT(*) FROM raw_alerts").fetchone()[0]
        self.assertEqual(count, 3)

    def test_exact_replay_is_idempotent(self) -> None:
        store_page(self.connection, self.events, after_id_before=0)
        result = store_page(self.connection, self.events, after_id_before=0)
        self.assertEqual(result.inserted_count, 0)
        self.assertEqual(result.duplicate_count, 3)
        count = self.connection.execute("SELECT COUNT(*) FROM raw_alerts").fetchone()[0]
        self.assertEqual(count, 3)

    def test_changed_payload_collision_rolls_back_and_preserves_cursor(self) -> None:
        store_page(self.connection, self.events, after_id_before=0)
        changed = copy.deepcopy(self.events)
        changed[-1]["close_price"] = 9999.0
        with self.assertRaises(ImmutableCollisionError):
            store_page(self.connection, changed, after_id_before=0)
        self.assertEqual(state_int(self.connection, "last_successful_id"), 4)
        price = self.connection.execute(
            "SELECT close_price FROM raw_alerts WHERE cloudflare_id = 4"
        ).fetchone()[0]
        self.assertEqual(price, 4027.37)

    def test_page_with_old_id_is_rejected_before_write(self) -> None:
        with self.assertRaises(ValueError):
            store_page(self.connection, self.events, after_id_before=2)
        count = self.connection.execute("SELECT COUNT(*) FROM raw_alerts").fetchone()[0]
        self.assertEqual(count, 0)

    def test_fixture_cli_writes_resumes_and_deduplicates_without_remote_secret(self) -> None:
        cli_db = Path(self.temp.name) / "cli.sqlite3"
        env_path = Path(self.temp.name) / ".env"
        env_path.write_text("", encoding="utf-8")
        empty_fixture = Path(self.temp.name) / "events_empty_after_4.json"
        empty_fixture.write_text(
            json.dumps({"ok": True, "latest_id": 4, "events": []}),
            encoding="utf-8",
        )
        script = ROOT / "scripts" / "mochipoyo_alert_research" / "collect_events_once.py"

        def run_cli(fixture: Path, *, after_id: int | None = None) -> dict[str, object]:
            command = [
                sys.executable,
                str(script),
                "--env",
                str(env_path),
                "--db",
                str(cli_db),
                "--fixture",
                str(fixture),
            ]
            if after_id is not None:
                command.extend(["--after-id", str(after_id)])
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

        first = run_cli(FIXTURE)
        self.assertEqual(first["after_id_before"], 0)
        self.assertEqual(first["inserted_count"], 3)
        self.assertEqual(first["duplicate_count"], 0)
        self.assertEqual(first["cursor_after"], 4)
        self.assertFalse(first["live_ready"])
        self.assertFalse(first["final_signal"])

        resumed = run_cli(empty_fixture)
        self.assertEqual(resumed["status"], "PASS_EMPTY")
        self.assertEqual(resumed["after_id_before"], 4)
        self.assertEqual(resumed["response_count"], 0)
        self.assertEqual(resumed["inserted_count"], 0)
        self.assertEqual(resumed["cursor_after"], 4)

        replay = run_cli(FIXTURE, after_id=0)
        self.assertEqual(replay["after_id_before"], 0)
        self.assertEqual(replay["inserted_count"], 0)
        self.assertEqual(replay["duplicate_count"], 3)
        self.assertEqual(replay["cursor_after"], 4)

        with sqlite3.connect(cli_db) as connection:
            count = connection.execute("SELECT COUNT(*) FROM raw_alerts").fetchone()[0]
            cursor = connection.execute(
                "SELECT state_value FROM collector_state WHERE state_key = 'last_successful_id'"
            ).fetchone()[0]
        self.assertEqual(count, 3)
        self.assertEqual(int(cursor), 4)

    def test_redaction_does_not_expose_token(self) -> None:
        token = "very-secret-read-token"
        text = redact_text(f"Authorization: Bearer {token}", (token,))
        self.assertNotIn(token, text)
        url = redact_url(f"https://example.workers.dev/events?token={token}&limit=5")
        self.assertNotIn(token, url)
        self.assertIn("%3Credacted%3E", url)


if __name__ == "__main__":
    unittest.main()
