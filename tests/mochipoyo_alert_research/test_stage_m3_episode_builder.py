from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mochipoyo_alert_research.db import open_database  # noqa: E402
from mochipoyo_alert_research.episode_builder import rebuild_episodes  # noqa: E402

SCHEMA = ROOT / "scripts" / "mochipoyo_alert_research" / "schema.sql"


def insert_alert(connection, alert_id: int, ticker: str, event: str, fired_at: str) -> None:
    source = {
        "id": alert_id,
        "ticker": ticker,
        "event": event,
        "fired_at_utc": fired_at,
    }
    canonical = json.dumps(source, sort_keys=True, separators=(",", ":"))
    connection.execute(
        """
        INSERT INTO raw_alerts (
            cloudflare_id, event_key, event_key_origin, received_at_utc,
            source, strategy, event, exchange_name, ticker, timeframe,
            bar_time_utc, fired_at_utc, open_price, high_price, low_price,
            close_price, message, worker_raw_json, worker_raw_json_origin,
            collector_source_row_json, payload_sha256, downloaded_at_utc
        ) VALUES (?, ?, 'DERIVED_CLOUDFLARE_ID', ?, 'tradingview', 'mochipoyo',
                  ?, 'VANTAGE', ?, '15', ?, ?, NULL, NULL, NULL, NULL,
                  '', ?, 'COLLECTOR_SOURCE_ROW_FALLBACK', ?, ?, ?)
        """,
        (
            alert_id,
            f"cloudflare:{alert_id}",
            fired_at,
            event,
            ticker,
            fired_at,
            fired_at,
            canonical,
            canonical,
            f"sha-{alert_id}",
            fired_at,
        ),
    )


def make_connection():
    temp = tempfile.TemporaryDirectory()
    connection = open_database(Path(temp.name) / "test.sqlite3", SCHEMA)
    return temp, connection


def test_reentry_and_exit_are_attached_to_one_episode() -> None:
    temp, connection = make_connection()
    try:
        insert_alert(connection, 1, "XAUUSD", "LONG", "2026-07-18T00:00:00Z")
        insert_alert(connection, 2, "XAUUSD", "LONG", "2026-07-18T00:15:00Z")
        insert_alert(connection, 3, "XAUUSD", "LONG_EXIT", "2026-07-18T00:30:00Z")
        connection.commit()
        result = rebuild_episodes(connection, built_at_utc="2026-07-18T01:00:00Z")
        assert result.episode_count == 1
        assert result.closed_episode_count == 1
        assert result.reentry_count == 1
        roles = [
            row["event_role"]
            for row in connection.execute(
                "SELECT event_role FROM episode_events ORDER BY raw_alert_id"
            )
        ]
        assert roles == ["PRIMARY_ALERT", "REENTRY_ALERT", "EXIT_ALERT"]
    finally:
        connection.close()
        temp.cleanup()


def test_opposite_direction_does_not_switch_before_exit() -> None:
    temp, connection = make_connection()
    try:
        insert_alert(connection, 1, "BTCUSD", "LONG", "2026-07-18T00:00:00Z")
        insert_alert(connection, 2, "BTCUSD", "SHORT", "2026-07-18T00:15:00Z")
        insert_alert(connection, 3, "BTCUSD", "SHORT_EXIT", "2026-07-18T00:30:00Z")
        insert_alert(connection, 4, "BTCUSD", "LONG_EXIT", "2026-07-18T00:45:00Z")
        insert_alert(connection, 5, "BTCUSD", "SHORT", "2026-07-18T01:00:00Z")
        connection.commit()
        result = rebuild_episodes(connection, built_at_utc="2026-07-18T02:00:00Z")
        assert result.episode_count == 2
        assert result.closed_episode_count == 1
        assert result.open_episode_count == 1
        assert result.ignored_opposite_count == 2
        reasons = [
            row["reason"]
            for row in connection.execute(
                "SELECT reason FROM episode_build_anomalies ORDER BY raw_alert_id"
            )
        ]
        assert reasons == [
            "OPPOSITE_ENTRY_BEFORE_EXIT",
            "OPPOSITE_EXIT_BEFORE_ACTIVE_EXIT",
        ]
    finally:
        connection.close()
        temp.cleanup()


def test_ticker_states_are_independent() -> None:
    temp, connection = make_connection()
    try:
        insert_alert(connection, 1, "XAUUSD", "LONG", "2026-07-18T00:00:00Z")
        insert_alert(connection, 2, "BTCUSD", "SHORT", "2026-07-18T00:01:00Z")
        insert_alert(connection, 3, "XAUUSD", "LONG_EXIT", "2026-07-18T00:15:00Z")
        insert_alert(connection, 4, "BTCUSD", "SHORT_EXIT", "2026-07-18T00:16:00Z")
        connection.commit()
        result = rebuild_episodes(connection, built_at_utc="2026-07-18T02:00:00Z")
        assert result.episode_count == 2
        assert result.closed_episode_count == 2
        assert result.anomaly_count == 0
    finally:
        connection.close()
        temp.cleanup()


def test_rebuild_is_deterministic_and_preserves_run_history() -> None:
    temp, connection = make_connection()
    try:
        insert_alert(connection, 1, "XAUUSD", "LONG", "2026-07-18T00:00:00Z")
        connection.commit()
        first = rebuild_episodes(connection, built_at_utc="2026-07-18T01:00:00Z")
        first_id = connection.execute("SELECT episode_id FROM episodes").fetchone()[0]
        second = rebuild_episodes(connection, built_at_utc="2026-07-18T02:00:00Z")
        second_id = connection.execute("SELECT episode_id FROM episodes").fetchone()[0]
        assert first == second
        assert first_id == second_id == "XAUUSD:LONG:1"
        assert connection.execute("SELECT COUNT(*) FROM episode_build_runs").fetchone()[0] == 2
        assert connection.execute(
            "SELECT future_entry_fields_used FROM episode_build_runs ORDER BY build_id DESC LIMIT 1"
        ).fetchone()[0] == 0
    finally:
        connection.close()
        temp.cleanup()
