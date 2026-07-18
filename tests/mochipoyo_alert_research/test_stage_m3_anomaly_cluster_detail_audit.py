from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "mochipoyo_alert_research"
    / "audit_anomaly_cluster_details_once.py"
)
spec = importlib.util.spec_from_file_location("audit_anomaly_cluster_details_once", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_detail_audit_is_read_only_and_includes_messages(tmp_path: Path) -> None:
    db_path = tmp_path / "audit.sqlite3"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY,
            event_key_origin TEXT NOT NULL,
            worker_raw_json_origin TEXT NOT NULL,
            received_at_utc TEXT NOT NULL,
            source TEXT NOT NULL,
            strategy TEXT NOT NULL,
            event TEXT NOT NULL,
            exchange_name TEXT,
            ticker TEXT NOT NULL,
            timeframe TEXT,
            bar_time_utc TEXT NOT NULL,
            fired_at_utc TEXT NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            message TEXT
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
            sequence_anomaly INTEGER NOT NULL
        );
        CREATE TABLE episode_events (
            episode_id TEXT NOT NULL,
            raw_alert_id INTEGER NOT NULL,
            event_role TEXT NOT NULL,
            reentry_index INTEGER
        );
        CREATE TABLE episode_build_anomalies (
            anomaly_id INTEGER PRIMARY KEY,
            raw_alert_id INTEGER NOT NULL,
            event TEXT NOT NULL,
            state_before TEXT NOT NULL,
            reason TEXT NOT NULL,
            related_episode_id TEXT,
            created_at_utc TEXT NOT NULL
        );
        """
    )
    connection.execute(
        """
        INSERT INTO raw_alerts VALUES (
            1, 'DERIVED_CLOUDFLARE_ID', 'COLLECTOR_SOURCE_ROW_FALLBACK',
            '2026-07-15T00:00:02Z', 'tradingview', 'mochipoyo', 'LONG',
            'VANTAGE', 'XAUUSD', '15', '2026-07-15T00:00:00Z',
            '2026-07-15T00:00:01Z', 3999, 4001, 3998, 4000,
            'connectivity test long'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO episodes VALUES (
            'XAUUSD:LONG:1', 'XAUUSD', 'LONG', 1, '2026-07-15T00:00:01Z',
            NULL, NULL, 'OPEN', 1
        )
        """
    )
    connection.execute(
        "INSERT INTO episode_events VALUES ('XAUUSD:LONG:1', 1, 'PRIMARY_ALERT', NULL)"
    )
    connection.execute(
        """
        INSERT INTO episode_build_anomalies VALUES (
            1, 1, 'LONG', 'ACTIVE_SHORT', 'OPPOSITE_ENTRY_BEFORE_EXIT',
            'XAUUSD:LONG:1', '2026-07-18T00:00:00Z'
        )
        """
    )
    connection.commit()

    before = connection.total_changes
    report = module.build_report(connection, db_path)
    after = connection.total_changes
    connection.close()

    assert before == after
    assert report["database_write_performed"] is False
    assert report["raw_json_included"] is False
    assert report["secrets_included"] is False
    assert report["related_episode_count"] == 1
    event = report["clusters"][0]["events"][0]
    assert event["message"] == "connectivity test long"
    assert event["event_key_origin"] == "DERIVED_CLOUDFLARE_ID"
