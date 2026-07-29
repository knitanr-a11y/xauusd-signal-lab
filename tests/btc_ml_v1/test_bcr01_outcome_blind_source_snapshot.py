from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR01_outcome_blind_source_snapshot"
    / "python"
    / "run_bcr01_outcome_blind_source_snapshot.py"
)

spec = importlib.util.spec_from_file_location("bcr01_snapshot_module", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def create_source_db(
    path: Path, *, bad_hash: bool = False, extra_column: bool = False
) -> None:
    connection = sqlite3.connect(path)
    raw_extra = ", unexpected_column TEXT" if extra_column else ""
    connection.executescript(
        f"""
        PRAGMA foreign_keys = ON;
        CREATE TABLE collector_state (
            state_key TEXT PRIMARY KEY,
            state_value TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY,
            event_key TEXT NOT NULL UNIQUE,
            event_key_origin TEXT NOT NULL,
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
            worker_raw_json_origin TEXT NOT NULL,
            collector_source_row_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            downloaded_at_utc TEXT NOT NULL
            {raw_extra}
        );
        CREATE TABLE raw_alert_annotations (
            raw_alert_id INTEGER PRIMARY KEY,
            annotation_type TEXT NOT NULL,
            confirmed_by TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        );
        CREATE TABLE collection_runs (
            run_id TEXT PRIMARY KEY,
            started_at_utc TEXT NOT NULL,
            finished_at_utc TEXT NOT NULL,
            after_id_before INTEGER NOT NULL,
            requested_limit INTEGER NOT NULL,
            response_count INTEGER NOT NULL,
            inserted_count INTEGER NOT NULL,
            duplicate_count INTEGER NOT NULL,
            max_response_id INTEGER,
            cursor_after INTEGER NOT NULL,
            status TEXT NOT NULL,
            source_mode TEXT NOT NULL,
            events_url_redacted TEXT,
            error_type TEXT,
            error_message_redacted TEXT
        );
        CREATE TABLE outcomes (
            entry_id TEXT PRIMARY KEY,
            result_r REAL
        );
        """
    )
    source_row = {
        "id": 1,
        "received_at_utc": "2026-07-20T14:55:01Z",
        "source": "tradingview",
        "strategy": "mochipoyo",
        "event": "LONG",
        "ticker": "BTCUSD",
        "bar_time_utc": "2026-07-20T14:45:00Z",
        "fired_at_utc": "2026-07-20T14:55:00Z",
    }
    canonical = json.dumps(
        source_row,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if bad_hash:
        payload_hash = "0" * 64

    connection.execute(
        "INSERT INTO collector_state VALUES (?, ?, ?)",
        ("last_successful_id", "1", "2026-07-20T14:55:02Z"),
    )
    values = [
        1,
        "event-1",
        "WORKER",
        source_row["received_at_utc"],
        "tradingview",
        "mochipoyo",
        "LONG",
        "BINANCE",
        "BTCUSD",
        "15",
        source_row["bar_time_utc"],
        source_row["fired_at_utc"],
        100.0,
        101.0,
        99.0,
        100.5,
        "LONG",
        canonical,
        "COLLECTOR_SOURCE_ROW_FALLBACK",
        canonical,
        payload_hash,
        "2026-07-20T14:55:02Z",
    ]
    if extra_column:
        values.append("unexpected")
    placeholders = ",".join("?" for _ in values)
    connection.execute(
        f"INSERT INTO raw_alerts VALUES ({placeholders})",
        values,
    )
    connection.execute(
        "INSERT INTO collection_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-1",
            "2026-07-20T14:55:01Z",
            "2026-07-20T14:55:02Z",
            0,
            500,
            1,
            1,
            0,
            1,
            1,
            "PASS",
            "CLOUDFLARE",
            "<configured-worker>/events?after_id=0&limit=500",
            None,
            None,
        ),
    )
    connection.commit()
    connection.close()


def test_happy_path_exports_only_allowlisted_tables(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    output = tmp_path / "output"
    create_source_db(source)

    package = module.build(source, output)

    assert package.is_file()
    with zipfile.ZipFile(package, "r") as archive:
        assert archive.namelist() == module.MEMBERS
        summary = json.loads(archive.read("01_snapshot_summary.json"))
        schema = json.loads(archive.read("02_source_schema_manifest.json"))
        checks = json.loads(archive.read("08_integrity_checks.json"))

    assert summary["status"] == "READY_OUTCOME_BLIND_SOURCE_SNAPSHOT"
    assert summary["outcomes_opened"] is False
    assert summary["exported_tables"] == list(module.TABLES)
    assert "outcomes" in schema["snapshot_context"][
        "forbidden_tables_present_but_not_read_or_exported"
    ]
    assert checks["forbidden_tables_exported"] == []
    assert checks["cursor_equals_max_raw_id"] is True


def test_payload_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    create_source_db(source, bad_hash=True)

    with pytest.raises(RuntimeError, match="source integrity checks failed"):
        module.build(source, tmp_path / "output")


def test_unexpected_allowlisted_schema_column_fails_closed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.sqlite3"
    create_source_db(source, extra_column=True)

    with pytest.raises(RuntimeError, match="schema mismatch for raw_alerts"):
        module.build(source, tmp_path / "output")
