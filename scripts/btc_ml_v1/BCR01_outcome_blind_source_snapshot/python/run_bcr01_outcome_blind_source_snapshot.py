from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "BCR01_OUTCOME_BLIND_SOURCE_SNAPSHOT"
VERSION = "1.0.1"

TABLES: dict[str, list[str]] = {
    "collector_state": ["state_key", "state_value", "updated_at_utc"],
    "raw_alerts": [
        "cloudflare_id", "event_key", "event_key_origin", "received_at_utc",
        "source", "strategy", "event", "exchange_name", "ticker", "timeframe",
        "bar_time_utc", "fired_at_utc", "open_price", "high_price", "low_price",
        "close_price", "message", "worker_raw_json", "worker_raw_json_origin",
        "collector_source_row_json", "payload_sha256", "downloaded_at_utc",
    ],
    "raw_alert_annotations": [
        "raw_alert_id", "annotation_type", "confirmed_by", "reason", "created_at_utc",
    ],
    "collection_runs": [
        "run_id", "started_at_utc", "finished_at_utc", "after_id_before",
        "requested_limit", "response_count", "inserted_count", "duplicate_count",
        "max_response_id", "cursor_after", "status", "source_mode",
        "events_url_redacted", "error_type", "error_message_redacted",
    ],
}
FORBIDDEN = {
    "episodes", "episode_events", "episode_build_anomalies", "episode_build_runs",
    "mt5_alignment", "feature_snapshots", "virtual_entries", "outcomes",
}
MEMBERS = [
    "00_READ_ME_FIRST.txt", "01_snapshot_summary.json",
    "02_source_schema_manifest.json", "03_collector_state.csv",
    "04_raw_alerts_manifest.csv", "05_raw_alerts_payloads.jsonl",
    "06_raw_alert_annotations.csv", "07_collection_runs.csv",
    "08_integrity_checks.json", "09_runtime_file_observation.json",
]


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
    )


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
    os.replace(temporary, path)


class RunLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.held = False

    def __enter__(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            age_seconds = max(0.0, time.time() - self.path.stat().st_mtime)
            if age_seconds > 21600:
                self.path.unlink(missing_ok=True)
            else:
                raise RuntimeError(f"BCR01 lock already exists: {self.path}")
        descriptor = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(
                descriptor,
                json.dumps(
                    {"pid": os.getpid(), "created_at_utc": now(), "stage": STAGE}
                ).encode("utf-8"),
            )
        finally:
            os.close(descriptor)
        self.held = True
        return self

    def __exit__(self, *_: Any) -> None:
        if self.held:
            self.path.unlink(missing_ok=True)
            self.held = False


def connect_ro(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        database.resolve().as_uri() + "?mode=ro", uri=True, timeout=30
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table})")
    ]


def validate_schema_columns(table: str, expected: list[str], physical: list[str]) -> dict[str, Any]:
    missing = sorted(set(expected) - set(physical))
    unexpected = sorted(set(physical) - set(expected))
    duplicates = sorted({column for column in physical if physical.count(column) > 1})
    if missing or unexpected or duplicates or len(physical) != len(expected):
        raise RuntimeError(
            f"schema mismatch for {table}: missing={missing} unexpected={unexpected} "
            f"duplicate={duplicates} expected_count={len(expected)} actual_count={len(physical)} "
            f"physical_order={physical}"
        )
    return {
        "physical_columns": physical,
        "export_columns": expected,
        "column_count": len(physical),
        "physical_order_matches_export_order": physical == expected,
        "column_set_exact": True,
    }


def read_rows(
    connection: sqlite3.Connection, table: str, order_by: str
) -> list[dict[str, Any]]:
    columns = TABLES[table]
    query = f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order_by}"
    return [dict(row) for row in connection.execute(query)]


def validate_integrity(
    state: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    ids = [int(row["cloudflare_id"]) for row in alerts]
    event_keys = [str(row["event_key"]) for row in alerts]
    id_set = set(ids)
    hash_errors: list[dict[str, Any]] = []
    json_errors: list[dict[str, Any]] = []
    identity_errors: list[dict[str, Any]] = []

    for row in alerts:
        source_json = str(row["collector_source_row_json"])
        actual_hash = hashlib.sha256(source_json.encode("utf-8")).hexdigest()
        if actual_hash != str(row["payload_sha256"]):
            hash_errors.append(
                {
                    "id": row["cloudflare_id"],
                    "expected": row["payload_sha256"],
                    "actual": actual_hash,
                }
            )
        try:
            source = json.loads(source_json)
        except Exception as exc:
            json_errors.append(
                {"id": row["cloudflare_id"], "error": f"{type(exc).__name__}: {exc}"}
            )
            continue
        if not isinstance(source, dict):
            json_errors.append({"id": row["cloudflare_id"], "error": "not object"})
            continue
        checks = {
            "id": int(source.get("id", -1)) == int(row["cloudflare_id"]),
            "event": str(source.get("event", "")) == str(row["event"]),
            "ticker": str(source.get("ticker", "")) == str(row["ticker"]),
            "bar_time_utc": str(source.get("bar_time_utc", "")) == str(row["bar_time_utc"]),
            "fired_at_utc": str(source.get("fired_at_utc", "")) == str(row["fired_at_utc"]),
            "received_at_utc": str(source.get("received_at_utc", "")) == str(row["received_at_utc"]),
        }
        if not all(checks.values()):
            identity_errors.append({"id": row["cloudflare_id"], "checks": checks})

    cloudflare_runs = [row for row in runs if str(row["source_mode"]) == "CLOUDFLARE"]
    cursor_regressions: list[dict[str, Any]] = []
    previous_cursor: int | None = None
    for row in cloudflare_runs:
        cursor = int(row["cursor_after"])
        if previous_cursor is not None and cursor < previous_cursor:
            cursor_regressions.append(
                {"run_id": row["run_id"], "previous": previous_cursor, "cursor": cursor}
            )
        previous_cursor = cursor

    state_map = {str(row["state_key"]): str(row["state_value"]) for row in state}
    last_successful_id = int(state_map.get("last_successful_id", "0"))
    max_raw_id = max(ids, default=0)
    result: dict[str, Any] = {
        "raw_alert_rows": len(alerts),
        "raw_alert_id_min": min(ids, default=0),
        "raw_alert_id_max": max_raw_id,
        "raw_alert_duplicate_ids": len(ids) - len(set(ids)),
        "raw_alert_duplicate_event_keys": len(event_keys) - len(set(event_keys)),
        "payload_sha256_mismatches": hash_errors,
        "collector_source_json_parse_errors": json_errors,
        "collector_source_identity_mismatches": identity_errors,
        "annotation_orphans": [
            int(row["raw_alert_id"])
            for row in annotations
            if int(row["raw_alert_id"]) not in id_set
        ],
        "collection_run_duplicate_ids": len(runs)
        - len({str(row["run_id"]) for row in runs}),
        "collection_run_invalid_statuses": [
            str(row["status"])
            for row in runs
            if str(row["status"]) not in {"PASS", "PASS_EMPTY", "FAIL"}
        ],
        "cloudflare_cursor_regressions": cursor_regressions,
        "last_successful_id": last_successful_id,
        "cursor_equals_max_raw_id": last_successful_id == max_raw_id,
        "forbidden_tables_exported": [],
        "outcome_tables_read": False,
        "performance_interpretation_performed": False,
    }
    failure_keys = {
        "raw_alert_duplicate_ids",
        "raw_alert_duplicate_event_keys",
        "payload_sha256_mismatches",
        "collector_source_json_parse_errors",
        "collector_source_identity_mismatches",
        "annotation_orphans",
        "collection_run_duplicate_ids",
        "collection_run_invalid_statuses",
        "cloudflare_cursor_regressions",
    }
    failures = {
        key: value for key, value in result.items() if key in failure_keys and bool(value)
    }
    if not result["cursor_equals_max_raw_id"]:
        failures["cursor_equals_max_raw_id"] = False
    if failures:
        raise RuntimeError(f"source integrity checks failed: {failures}")
    return result


def capture(database: Path) -> tuple[Any, ...]:
    connection = connect_ro(database)
    try:
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        data_version = int(connection.execute("PRAGMA data_version").fetchone()[0])
        connection.execute("BEGIN")
        actual_tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing_tables = sorted(set(TABLES) - actual_tables)
        if missing_tables:
            raise RuntimeError(f"required tables missing: {missing_tables}")

        schema: dict[str, Any] = {}
        for table, expected_columns in TABLES.items():
            physical_columns = table_columns(connection, table)
            schema[table] = validate_schema_columns(
                table, expected_columns, physical_columns
            )

        state = read_rows(connection, "collector_state", "state_key")
        alerts = read_rows(connection, "raw_alerts", "cloudflare_id")
        annotations = read_rows(connection, "raw_alert_annotations", "raw_alert_id")
        runs = read_rows(connection, "collection_runs", "started_at_utc, run_id")
        checks = validate_integrity(state, alerts, annotations, runs)
        context = {
            "journal_mode": journal_mode,
            "data_version_before_transaction": data_version,
            "actual_table_names": sorted(actual_tables),
            "forbidden_tables_present_but_not_read_or_exported": sorted(
                FORBIDDEN & actual_tables
            ),
            "schema_validation": "EXACT_COLUMN_SET_PHYSICAL_ORDER_MAY_DIFFER",
        }
        connection.rollback()
        return context, schema, state, alerts, annotations, runs, checks
    finally:
        connection.close()


def create_error_package(root: Path, database: Path, exc: Exception) -> Path:
    staging = root / "LATEST_ERROR_STAGING"
    latest = root / "LATEST"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=False)
    write_text(
        staging / "00_READ_ME_FIRST.txt",
        "BCR01 failed. No source snapshot or candidate conclusion is accepted.\n",
    )
    write_json(
        staging / "01_snapshot_error.json",
        {
            "stage": STAGE,
            "version": VERSION,
            "status": "BLOCKED_BCR01_SOURCE_SNAPSHOT_ERROR",
            "generated_at_utc": now(),
            "source_database_path": str(database),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "source_runtime_modified": False,
            "outcomes_opened": False,
            "performance_interpretation_performed": False,
        },
    )
    package = staging / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(staging / "00_READ_ME_FIRST.txt", "00_READ_ME_FIRST.txt")
        archive.write(staging / "01_snapshot_error.json", "01_snapshot_error.json")
    if latest.exists():
        shutil.rmtree(latest)
    os.replace(staging, latest)
    return latest / package.name


def build(database: Path, root: Path) -> Path:
    if not database.is_file():
        raise FileNotFoundError(f"source database not found: {database}")
    root.mkdir(parents=True, exist_ok=True)
    with RunLock(root / ".bcr01_run.lock"):
        started_at = now()
        before = {
            "db": meta(database),
            "wal": meta(Path(str(database) + "-wal")),
            "shm": meta(Path(str(database) + "-shm")),
        }
        context, schema, state, alerts, annotations, runs, checks = capture(database)
        after = {
            "db": meta(database),
            "wal": meta(Path(str(database) + "-wal")),
            "shm": meta(Path(str(database) + "-shm")),
        }

        max_raw_id = int(checks["raw_alert_id_max"])
        snapshot_id = (
            f"BCR01_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_RAWMAX{max_raw_id}"
        )
        run_directory = root / snapshot_id
        staging = root / f"{snapshot_id}_STAGING"
        if run_directory.exists():
            raise FileExistsError(f"output exists: {run_directory}")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        manifest_columns = [
            column
            for column in TABLES["raw_alerts"]
            if column not in {"worker_raw_json", "collector_source_row_json"}
        ]
        write_csv(staging / "03_collector_state.csv", TABLES["collector_state"], state)
        write_csv(staging / "04_raw_alerts_manifest.csv", manifest_columns, alerts)
        with (staging / "05_raw_alerts_payloads.jsonl").open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            for row in alerts:
                handle.write(
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    )
                    + "\n"
                )
        write_csv(
            staging / "06_raw_alert_annotations.csv",
            TABLES["raw_alert_annotations"],
            annotations,
        )
        write_csv(staging / "07_collection_runs.csv", TABLES["collection_runs"], runs)

        summary = {
            "project": "BTC_CANDIDATE_RESEARCH_REDESIGN",
            "stage": STAGE,
            "version": VERSION,
            "status": "READY_OUTCOME_BLIND_SOURCE_SNAPSHOT",
            "snapshot_id": snapshot_id,
            "started_at_utc": started_at,
            "finished_at_utc": now(),
            "source_database_path": str(database.resolve()),
            "source_database_open_mode": "READ_ONLY_URI_MODE_RO_QUERY_ONLY",
            "sqlite_snapshot_contract": "CONSISTENT_READ_TRANSACTION",
            "schema_validation": "EXACT_COLUMN_SET_PHYSICAL_ORDER_MAY_DIFFER",
            "raw_alert_rows": len(alerts),
            "raw_alert_id_min": checks["raw_alert_id_min"],
            "raw_alert_id_max": checks["raw_alert_id_max"],
            "collector_state_rows": len(state),
            "collection_run_rows": len(runs),
            "annotation_rows": len(annotations),
            "last_successful_id": checks["last_successful_id"],
            "exported_tables": list(TABLES),
            "forbidden_tables_not_read_or_exported": sorted(FORBIDDEN),
            "outcomes_opened": False,
            "performance_interpretation_performed": False,
            "candidate_formula_designed": False,
            "source_runtime_modified": False,
            "collector_stopped_or_restarted": False,
            "script_sha256": sha256(Path(__file__).resolve()),
        }
        write_text(
            staging / "00_READ_ME_FIRST.txt",
            "BTC Candidate Research BCR01 — outcome-blind source snapshot\n\n"
            f"Status: {summary['status']}\nSnapshot: {snapshot_id}\n\n"
            "Only collector_state, raw_alerts, raw_alert_annotations and "
            "collection_runs were read and exported.\n"
            "Outcome-bearing tables were not read or exported.\n"
            "Collector and M7C were not stopped, restarted or modified.\n",
        )
        write_json(staging / "01_snapshot_summary.json", summary)
        write_json(
            staging / "02_source_schema_manifest.json",
            {"snapshot_context": context, "allowlisted_tables": schema},
        )
        write_json(staging / "08_integrity_checks.json", checks)
        write_json(
            staging / "09_runtime_file_observation.json",
            {
                "before": before,
                "after": after,
                "note": "Consistency comes from the read-only SQLite transaction, "
                "not from copying or hashing the live DB/WAL/SHM files.",
            },
        )
        missing_outputs = [
            member for member in MEMBERS if not (staging / member).is_file()
        ]
        if missing_outputs:
            raise RuntimeError(f"missing outputs: {missing_outputs}")

        os.replace(staging, run_directory)
        package = run_directory / "99_UPLOAD_PACKAGE.zip"
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
            for member in MEMBERS:
                archive.write(run_directory / member, member)
        with zipfile.ZipFile(package, "r") as archive:
            if archive.namelist() != MEMBERS:
                raise RuntimeError(f"ZIP layout mismatch: {archive.namelist()}")

        latest_staging = root / "LATEST_STAGING"
        latest = root / "LATEST"
        if latest_staging.exists():
            shutil.rmtree(latest_staging)
        shutil.copytree(run_directory, latest_staging)
        if latest.exists():
            shutil.rmtree(latest)
        os.replace(latest_staging, latest)
        return latest / package.name


def parse_args() -> argparse.Namespace:
    local_root = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-db",
        type=Path,
        default=local_root
        / "xauusd_signal_lab"
        / "mochipoyo_alert_research"
        / "mochipoyo_alerts.sqlite3",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=local_root
        / "xauusd_signal_lab"
        / "btc_ml_v1"
        / "outputs"
        / "BCR01_outcome_blind_source_snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        package = build(args.source_db, args.output_root)
    except Exception as exc:
        try:
            error_package = create_error_package(args.output_root, args.source_db, exc)
            print(f"[BCR01] ERROR PACKAGE: {error_package}", file=sys.stderr)
        except Exception:
            pass
        print(f"[BCR01] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"[BCR01] READY: {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
