from __future__ import annotations

from pathlib import Path

from scripts.mochipoyo_alert_research.db import open_database
from scripts.mochipoyo_alert_research.episode_builder import rebuild_episodes


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "mochipoyo_alert_research"
SCHEMA_PATH = SCRIPT_DIR / "schema.sql"


def insert_raw_alert(
    connection,
    *,
    raw_id: int,
    event: str,
    fired_at_utc: str,
) -> None:
    connection.execute(
        """
        INSERT INTO raw_alerts (
            cloudflare_id, event_key, event_key_origin, received_at_utc,
            source, strategy, event, exchange_name, ticker, timeframe,
            bar_time_utc, fired_at_utc, open_price, high_price, low_price,
            close_price, message, worker_raw_json, worker_raw_json_origin,
            collector_source_row_json, payload_sha256, downloaded_at_utc
        ) VALUES (?, ?, 'WORKER', ?, 'tradingview', 'mochipoyo', ?,
                  'TEST', 'BTCUSD', '15', ?, ?, 100.0, 101.0, 99.0,
                  100.0, '', '{}', 'WORKER_FIELD', '{}', ?, ?)
        """,
        (
            raw_id,
            f"event-{raw_id}",
            fired_at_utc,
            event,
            fired_at_utc,
            fired_at_utc,
            f"sha-{raw_id}",
            fired_at_utc,
        ),
    )
    connection.commit()


def test_rebuild_preserves_downstream_episode_foreign_keys(tmp_path: Path) -> None:
    database_path = tmp_path / "mochipoyo.sqlite3"
    connection = open_database(database_path, SCHEMA_PATH)
    try:
        insert_raw_alert(
            connection,
            raw_id=1,
            event="LONG",
            fired_at_utc="2026-07-20T00:00:00Z",
        )
        rebuild_episodes(connection, built_at_utc="2026-07-20T00:01:00Z")

        episode_id = "BTCUSD:LONG:1"
        connection.execute(
            """
            INSERT INTO feature_snapshots (
                snapshot_id, source_event_id, episode_id, snapshot_time_utc,
                knowledge_cutoff_utc, timeframe, latest_closed_bar_time,
                features_json, future_fields_present
            ) VALUES ('snapshot-1', 1, ?, '2026-07-20T00:00:00Z',
                      '2026-07-19T23:45:00Z', 'M15',
                      '2026-07-19T23:45:00Z', '{}', 0)
            """,
            (episode_id,),
        )
        connection.commit()

        insert_raw_alert(
            connection,
            raw_id=2,
            event="LONG_EXIT",
            fired_at_utc="2026-07-20T00:15:00Z",
        )

        connection.execute("PRAGMA defer_foreign_keys = ON")
        result = rebuild_episodes(connection, built_at_utc="2026-07-20T00:16:00Z")

        episode = connection.execute(
            "SELECT episode_status, exit_alert_id FROM episodes WHERE episode_id = ?",
            (episode_id,),
        ).fetchone()
        snapshot = connection.execute(
            "SELECT episode_id FROM feature_snapshots WHERE snapshot_id = 'snapshot-1'"
        ).fetchone()

        assert result.closed_episode_count == 1
        assert episode is not None
        assert episode["episode_status"] == "CLOSED"
        assert episode["exit_alert_id"] == 2
        assert snapshot is not None
        assert snapshot["episode_id"] == episode_id
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()
