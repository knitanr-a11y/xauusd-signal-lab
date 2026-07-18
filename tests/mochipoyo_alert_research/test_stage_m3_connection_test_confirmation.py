from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "mochipoyo_alert_research"
    / "confirm_connection_test_once.py"
)
SCHEMA = ROOT / "scripts" / "mochipoyo_alert_research" / "schema.sql"
spec = importlib.util.spec_from_file_location("confirm_connection_test_once", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def insert_raw(
    connection: sqlite3.Connection,
    *,
    alert_id: int,
    ticker: str,
    event: str,
    message: str,
) -> None:
    connection.execute(
        """
        INSERT INTO raw_alerts (
            cloudflare_id, event_key, event_key_origin, received_at_utc,
            source, strategy, event, exchange_name, ticker, timeframe,
            bar_time_utc, fired_at_utc, open_price, high_price, low_price,
            close_price, message, worker_raw_json, worker_raw_json_origin,
            collector_source_row_json, payload_sha256, downloaded_at_utc
        ) VALUES (
            ?, ?, 'DERIVED_CLOUDFLARE_ID', '2026-07-15T00:00:02Z',
            'tradingview', 'mochipoyo', ?, 'VANTAGE', ?, '15',
            '2026-07-15T00:00:00Z', '2026-07-15T00:00:01Z',
            1.0, 1.0, 1.0, 1.0, ?, '{}',
            'COLLECTOR_SOURCE_ROW_FALLBACK', '{}', ?, '2026-07-15T00:00:03Z'
        )
        """,
        (alert_id, f"cloudflare:{alert_id}", event, ticker, message, str(alert_id)),
    )


def test_confirmed_connection_test_is_excluded_only_from_clean_baseline(
    tmp_path: Path,
) -> None:
    database = tmp_path / "test.sqlite3"
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))

    insert_raw(
        connection,
        alert_id=1,
        ticker="XAUUSD",
        event="LONG",
        message="test long sign 4000.00",
    )
    insert_raw(connection, alert_id=4, ticker="XAUUSD", event="SHORT", message="short")
    insert_raw(
        connection,
        alert_id=6,
        ticker="XAUUSD",
        event="SHORT_EXIT",
        message="short exit",
    )
    insert_raw(connection, alert_id=7, ticker="XAUUSD", event="LONG", message="long")
    insert_raw(
        connection,
        alert_id=9,
        ticker="XAUUSD",
        event="LONG_EXIT",
        message="long exit",
    )
    insert_raw(connection, alert_id=10, ticker="BTCUSD", event="LONG", message="long")

    connection.execute(
        """
        INSERT INTO episodes (
            episode_id, ticker, direction, primary_alert_id, started_at_utc,
            exit_alert_id, exited_at_utc, episode_status, exit_missing,
            sequence_anomaly
        ) VALUES
            ('XAUUSD:LONG:1', 'XAUUSD', 'LONG', 1, '2026-07-15T00:00:01Z',
             9, '2026-07-15T18:15:00Z', 'CLOSED', 0, 1),
            ('BTCUSD:LONG:10', 'BTCUSD', 'LONG', 10, '2026-07-15T20:00:00Z',
             NULL, NULL, 'OPEN', 1, 0)
        """
    )
    connection.executemany(
        """
        INSERT INTO episode_events (
            episode_id, raw_alert_id, event_role, reentry_index
        ) VALUES (?, ?, ?, ?)
        """,
        [
            ("XAUUSD:LONG:1", 1, "PRIMARY_ALERT", None),
            ("XAUUSD:LONG:1", 4, "OPPOSITE_ALERT_IGNORED", None),
            ("XAUUSD:LONG:1", 6, "OPPOSITE_EXIT_IGNORED", None),
            ("XAUUSD:LONG:1", 7, "REENTRY_ALERT", 1),
            ("XAUUSD:LONG:1", 9, "EXIT_ALERT", None),
            ("BTCUSD:LONG:10", 10, "PRIMARY_ALERT", None),
        ],
    )
    connection.executemany(
        """
        INSERT INTO episode_build_anomalies (
            raw_alert_id, ticker, event, state_before, reason,
            related_episode_id, created_at_utc
        ) VALUES (?, 'XAUUSD', ?, 'ACTIVE_LONG', ?, 'XAUUSD:LONG:1',
                  '2026-07-18T00:00:00Z')
        """,
        [
            (4, "SHORT", "OPPOSITE_ENTRY_BEFORE_EXIT"),
            (6, "SHORT_EXIT", "OPPOSITE_EXIT_BEFORE_ACTIVE_EXIT"),
        ],
    )
    connection.commit()

    result = module.confirm_and_report(
        connection,
        primary_alert_id=1,
        confirmed_at_utc="2026-07-18T06:30:00Z",
    )

    assert result["all_source_episodes"] == {
        "episode_count": 2,
        "closed_episode_count": 1,
        "open_episode_count": 1,
        "reentry_count": 1,
        "anomaly_count": 2,
        "ignored_opposite_count": 2,
    }
    assert result["clean_baseline"] == {
        "episode_count": 1,
        "closed_episode_count": 0,
        "open_episode_count": 1,
        "reentry_count": 0,
        "anomaly_count": 0,
        "ignored_opposite_count": 0,
    }
    assert result["excluded_connection_test_episode_count"] == 1
    assert result["raw_alerts_modified"] is False
    assert result["episodes_modified"] is False

    annotation = connection.execute(
        "SELECT * FROM episode_source_annotations WHERE primary_alert_id = 1"
    ).fetchone()
    assert annotation["annotation_type"] == "CONNECTION_TEST"
    assert annotation["confirmed_by"] == "USER"

    # The annotation is keyed to immutable raw identity and survives episode rebuilds.
    connection.execute("DELETE FROM episode_events")
    connection.execute("DELETE FROM episode_build_anomalies")
    connection.execute("DELETE FROM episodes")
    connection.commit()
    assert connection.execute(
        "SELECT COUNT(*) FROM episode_source_annotations WHERE primary_alert_id = 1"
    ).fetchone()[0] == 1
    connection.close()
