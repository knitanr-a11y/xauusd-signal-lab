from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "mochipoyo_alert_research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from feature_snapshot_stage import validate_current_alignment_coverage  # noqa: E402


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL
        );
        CREATE TABLE raw_alert_annotations (
            raw_alert_id INTEGER PRIMARY KEY,
            annotation_type TEXT NOT NULL
        );
        CREATE TABLE mt5_alignment (
            raw_alert_id INTEGER NOT NULL,
            timeframe TEXT NOT NULL,
            PRIMARY KEY (raw_alert_id, timeframe)
        );
        """
    )
    return connection


def insert_complete_alignment(connection: sqlite3.Connection, alert_id: int) -> None:
    connection.executemany(
        "INSERT INTO mt5_alignment VALUES (?, ?)",
        [(alert_id, timeframe) for timeframe in ("M5", "M15", "H1", "H4", "D1")],
    )


def test_current_alignment_guard_accepts_exact_coverage() -> None:
    connection = make_connection()
    try:
        connection.executemany(
            "INSERT INTO raw_alerts VALUES (?, 'BTCUSD')",
            [(1,), (2,)],
        )
        connection.execute(
            "INSERT INTO raw_alert_annotations VALUES (1, 'CONNECTION_TEST')"
        )
        insert_complete_alignment(connection, 2)
        connection.commit()
        assert validate_current_alignment_coverage(connection) == 1
    finally:
        connection.close()


def test_current_alignment_guard_rejects_new_unaligned_alert() -> None:
    connection = make_connection()
    try:
        connection.executemany(
            "INSERT INTO raw_alerts VALUES (?, 'BTCUSD')",
            [(1,), (2,), (3,)],
        )
        connection.execute(
            "INSERT INTO raw_alert_annotations VALUES (1, 'CONNECTION_TEST')"
        )
        insert_complete_alignment(connection, 2)
        connection.commit()
        try:
            validate_current_alignment_coverage(connection)
            raise AssertionError("expected stale Stage M4 alignment failure")
        except Exception as exc:
            assert "stale or incomplete" in str(exc)
    finally:
        connection.close()


def test_current_alignment_guard_rejects_missing_timeframe() -> None:
    connection = make_connection()
    try:
        connection.execute("INSERT INTO raw_alerts VALUES (2, 'XAUUSD')")
        connection.executemany(
            "INSERT INTO mt5_alignment VALUES (2, ?)",
            [(timeframe,) for timeframe in ("M5", "M15", "H1", "H4")],
        )
        connection.commit()
        try:
            validate_current_alignment_coverage(connection)
            raise AssertionError("expected incomplete timeframe failure")
        except Exception as exc:
            assert "timeframe coverage is incomplete" in str(exc)
    finally:
        connection.close()
