from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mochipoyo_alert_research.db import (  # noqa: E402
    normalize_event_row,
    open_database,
    store_page,
)

SCHEMA = ROOT / "scripts" / "mochipoyo_alert_research" / "schema.sql"


def worker_projection_row() -> dict:
    return {
        "id": 5,
        "received_at_utc": "2026-07-18T04:47:00Z",
        "source": "tradingview",
        "strategy": "mochipoyo",
        "event": "LONG",
        "exchange_name": "VANTAGE",
        "ticker": "XAUUSD",
        "timeframe": "15",
        "bar_time_utc": "2026-07-18T04:45:00Z",
        "fired_at_utc": "2026-07-18T04:45:00Z",
        "open_price": 1,
        "high_price": 2,
        "low_price": 0,
        "close_price": 1,
        "message": "fixture",
    }


def test_public_worker_projection_gets_audited_fallback_identity() -> None:
    source = worker_projection_row()
    normalized = normalize_event_row(source)
    assert normalized["event_key"] == "cloudflare:5"
    assert normalized["event_key_origin"] == "DERIVED_CLOUDFLARE_ID"
    assert normalized["worker_raw_json_origin"] == "COLLECTOR_SOURCE_ROW_FALLBACK"
    assert json.loads(normalized["worker_raw_json"]) == source
    assert normalized["worker_raw_json"] == normalized["collector_source_row_json"]


def test_public_worker_projection_is_stored_with_provenance() -> None:
    with tempfile.TemporaryDirectory() as directory:
        connection = open_database(Path(directory) / "collector.sqlite3", SCHEMA)
        try:
            result = store_page(
                connection,
                [worker_projection_row()],
                after_id_before=0,
            )
            assert result.inserted_count == 1
            stored = connection.execute(
                """
                SELECT event_key, event_key_origin, worker_raw_json_origin
                FROM raw_alerts
                """
            ).fetchone()
            assert stored["event_key"] == "cloudflare:5"
            assert stored["event_key_origin"] == "DERIVED_CLOUDFLARE_ID"
            assert stored["worker_raw_json_origin"] == "COLLECTOR_SOURCE_ROW_FALLBACK"
        finally:
            connection.close()


def test_existing_worker_fields_remain_authoritative() -> None:
    source = worker_projection_row()
    source["event_key"] = "worker-key"
    source["raw_json"] = '{"original":true}'
    normalized = normalize_event_row(source)
    assert normalized["event_key"] == "worker-key"
    assert normalized["event_key_origin"] == "WORKER"
    assert normalized["worker_raw_json"] == '{"original":true}'
    assert normalized["worker_raw_json_origin"] == "WORKER_FIELD"


def test_existing_database_is_migrated_without_deletion() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "old.sqlite3"
        connection = sqlite3.connect(database_path)
        connection.executescript(
            """
            CREATE TABLE raw_alerts (
                cloudflare_id INTEGER PRIMARY KEY,
                event_key TEXT NOT NULL UNIQUE,
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
                message TEXT,
                worker_raw_json TEXT NOT NULL,
                collector_source_row_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                downloaded_at_utc TEXT NOT NULL
            );
            """
        )
        connection.close()

        migrated = open_database(database_path, SCHEMA)
        try:
            columns = {
                row["name"] for row in migrated.execute("PRAGMA table_info(raw_alerts)")
            }
            assert "event_key_origin" in columns
            assert "worker_raw_json_origin" in columns
        finally:
            migrated.close()
