from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "mochipoyo_alert_research"
    / "audit_episode_sequences_once.py"
)
spec = importlib.util.spec_from_file_location("audit_episode_sequences_once", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EpisodeSequenceAuditTests(unittest.TestCase):
    def test_read_only_report_contains_open_episode_and_anomaly_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "mochipoyo.sqlite3"
            connection = sqlite3.connect(database_path)
            connection.row_factory = sqlite3.Row
            connection.executescript(
                """
                CREATE TABLE raw_alerts (
                    cloudflare_id INTEGER PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    event TEXT NOT NULL,
                    fired_at_utc TEXT NOT NULL,
                    bar_time_utc TEXT NOT NULL,
                    close_price REAL
                );
                CREATE TABLE episodes (
                    episode_id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    primary_alert_id INTEGER NOT NULL,
                    started_at_utc TEXT NOT NULL,
                    exit_alert_id INTEGER,
                    exited_at_utc TEXT,
                    episode_status TEXT NOT NULL,
                    exit_missing INTEGER NOT NULL,
                    sequence_anomaly INTEGER NOT NULL
                );
                CREATE TABLE episode_events (
                    episode_id TEXT NOT NULL,
                    raw_alert_id INTEGER NOT NULL,
                    event_role TEXT NOT NULL,
                    reentry_index INTEGER
                );
                CREATE TABLE episode_build_anomalies (
                    anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_alert_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    event TEXT NOT NULL,
                    state_before TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    related_episode_id TEXT,
                    created_at_utc TEXT NOT NULL
                );
                """
            )
            connection.executemany(
                "INSERT INTO raw_alerts VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (1, "XAUUSD", "LONG", "t1", "t1", 100.0),
                    (2, "XAUUSD", "SHORT", "t2", "t2", 99.0),
                    (3, "XAUUSD", "LONG_EXIT", "t3", "t3", 101.0),
                    (4, "BTCUSD", "SHORT", "t4", "t4", 50000.0),
                ],
            )
            connection.executemany(
                "INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        "XAUUSD:LONG:1",
                        "XAUUSD",
                        "LONG",
                        1,
                        "t1",
                        3,
                        "t3",
                        "CLOSED",
                        0,
                        1,
                    ),
                    (
                        "BTCUSD:SHORT:4",
                        "BTCUSD",
                        "SHORT",
                        4,
                        "t4",
                        None,
                        None,
                        "OPEN",
                        1,
                        0,
                    ),
                ],
            )
            connection.executemany(
                "INSERT INTO episode_events VALUES (?, ?, ?, ?)",
                [
                    ("XAUUSD:LONG:1", 1, "PRIMARY_ALERT", None),
                    ("XAUUSD:LONG:1", 2, "OPPOSITE_ALERT_IGNORED", None),
                    ("XAUUSD:LONG:1", 3, "EXIT_ALERT", None),
                    ("BTCUSD:SHORT:4", 4, "PRIMARY_ALERT", None),
                ],
            )
            connection.execute(
                """
                INSERT INTO episode_build_anomalies (
                    raw_alert_id, ticker, event, state_before, reason,
                    related_episode_id, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    2,
                    "XAUUSD",
                    "SHORT",
                    "ACTIVE_LONG",
                    "OPPOSITE_ENTRY_BEFORE_EXIT",
                    "XAUUSD:LONG:1",
                    "built",
                ),
            )
            connection.commit()

            before_changes = connection.total_changes
            report = module.build_report(connection, database_path)
            after_changes = connection.total_changes
            connection.close()

            self.assertEqual(before_changes, after_changes)
            self.assertFalse(report["database_write_performed"])
            self.assertEqual(report["open_episode_count"], 1)
            self.assertEqual(report["anomaly_count"], 1)
            anomaly = report["anomalies"][0]
            self.assertEqual(anomaly["anomalous_event"]["raw_alert_id"], 2)
            self.assertEqual(
                anomaly["previous_same_ticker_event"]["raw_alert_id"], 1
            )
            self.assertEqual(anomaly["next_same_ticker_event"]["raw_alert_id"], 3)
            self.assertEqual(
                anomaly["related_episode_sequence"][1]["event_role"],
                "OPPOSITE_ALERT_IGNORED",
            )


if __name__ == "__main__":
    unittest.main()
