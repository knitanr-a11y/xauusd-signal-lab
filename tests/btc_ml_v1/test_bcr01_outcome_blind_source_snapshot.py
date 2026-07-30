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
    path: Path,
    *,
    bad_hash: bool = False,
    extra_column: bool = False,
    migrated_order: bool = False,
) -> None:
    connection = sqlite3.connect(path)
    if migrated_order:
        raw_columns = """
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
            downloaded_at_utc TEXT NOT NULL,
            event_key_origin TEXT NOT NULL,
            worker_raw_json_origin TEXT NOT NULL
        """
    else:
        raw_columns = """
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
        """
    if extra_column:
        raw_columns += ", unexpected_column TEXT"
    connection.executescript(
        f"""
        CREATE TABLE collector_state (
            state_key TEXT PRIMARY KEY,
            state_value TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE raw_alerts ({raw_columns});
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
        CREATE TABLE outcomes (entry_id TEXT PRIMARY KEY, result_r REAL);
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

    logical = {
        "cloudflare_id": 1,
        "event_key": "event-1",
        "event_key_origin": "WORKER",
        "received_at_utc": source_row["received_at_utc"],
        "source": "tradingview",
        "strategy": "mochipoyo",
        "event": "LONG",
        "exchange_name": "BINANCE",
        "ticker": "BTCUSD",
        "timeframe": "15",
        "bar_time_utc": source_row["bar_time_utc"],
        "fired_at_utc": source_row["fired_at_utc"],
        "open_price": 100.0,
        "high_price": 101.0,
        "low_price": 99.0,
        "close_price": 100.5,
        "message": "LONG",
        "worker_raw_json": canonical,
        "worker_raw_json_origin": "COLLECTOR_SOURCE_ROW_FALLBACK",
        "collector_source_row_json": canonical,
        "payload_sha256": payload_hash,
        "downloaded_at_utc": "2026-07-20T14:55:02Z",
    }
    physical_columns = [
        row[1] for row in connection.execute("PRAGMA table_info(raw_alerts)")
    ]
    values = [logical.get(column, "unexpected") for column in physical_columns]
    connection.execute(
        f"INSERT INTO raw_alerts ({', '.join(physical_columns)}) "
        f"VALUES ({','.join('?' for _ in values)})",
        values,
    )
    connection.execute(
        "INSERT INTO collector_state VALUES (?, ?, ?)",
        ("last_successful_id", "1", "2026-07-20T14:55:02Z"),
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


def inspect_package(package: Path) -> tuple[dict, dict, dict]:
    with zipfile.ZipFile(package, "r") as archive:
        assert archive.namelist() == module.MEMBERS
        return (
            json.loads(archive.read("01_snapshot_summary.json")),
            json.loads(archive.read("02_source_schema_manifest.json")),
            json.loads(archive.read("08_integrity_checks.json")),
        )


def test_fresh_schema_order_exports_allowlist_only(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    create_source_db(source)
    summary, schema, checks = inspect_package(
        module.build(source, tmp_path / "output")
    )
    assert summary["status"] == "READY_OUTCOME_BLIND_SOURCE_SNAPSHOT"
    assert summary["outcomes_opened"] is False
    assert (
        schema["allowlisted_tables"]["raw_alerts"][
            "physical_order_matches_export_order"
        ]
        is True
    )
    assert checks["cursor_equals_max_raw_id"] is True


def test_migrated_schema_order_is_accepted_and_export_order_is_canonical(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.sqlite3"
    create_source_db(source, migrated_order=True)
    summary, schema, checks = inspect_package(
        module.build(source, tmp_path / "output")
    )
    raw_schema = schema["allowlisted_tables"]["raw_alerts"]
    assert summary["schema_validation"] == "EXACT_COLUMN_SET_PHYSICAL_ORDER_MAY_DIFFER"
    assert raw_schema["physical_order_matches_export_order"] is False
    assert raw_schema["column_set_exact"] is True
    assert raw_schema["export_columns"] == module.TABLES["raw_alerts"]
    assert checks["cursor_equals_max_raw_id"] is True


def test_payload_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    create_source_db(source, bad_hash=True)
    with pytest.raises(RuntimeError, match="source integrity checks failed"):
        module.build(source, tmp_path / "output")


def test_unexpected_column_still_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    create_source_db(source, extra_column=True)
    with pytest.raises(RuntimeError, match="schema mismatch for raw_alerts"):
        module.build(source, tmp_path / "output")
