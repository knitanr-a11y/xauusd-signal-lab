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
VERSION = "1.0.0"

TABLES = {
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
    "episodes", "episode_events", "episode_build_anomalies",
    "episode_build_runs", "mt5_alignment", "feature_snapshots",
    "virtual_entries", "outcomes",
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
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    st = path.stat()
    return {
        "path": str(path), "exists": True, "bytes": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)


def write_json(path: Path, obj: Any) -> None:
    write_text(
        path,
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
    )


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="raise")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c) for c in columns})
    os.replace(tmp, path)


class RunLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.held = False

    def __enter__(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            age = max(0.0, time.time() - self.path.stat().st_mtime)
            if age > 21600:
                self.path.unlink(missing_ok=True)
            else:
                raise RuntimeError(f"BCR01 lock already exists: {self.path}")
        fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(
                fd,
                json.dumps(
                    {"pid": os.getpid(), "created_at_utc": now(), "stage": STAGE}
                ).encode("utf-8"),
            )
        finally:
            os.close(fd)
        self.held = True
        return self

    def __exit__(self, *args: Any) -> None:
        if self.held:
            self.path.unlink(missing_ok=True)
            self.held = False


def connect_ro(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(r["name"]) for r in conn.execute(f"PRAGMA table_info({table})")]


def rows(conn: sqlite3.Connection, table: str, order: str) -> list[dict[str, Any]]:
    cols = TABLES[table]
    return [
        dict(r)
        for r in conn.execute(
            f"SELECT {', '.join(cols)} FROM {table} ORDER BY {order}"
        )
    ]


def validate(
    state: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    ids = [int(r["cloudflare_id"]) for r in alerts]
    keys = [str(r["event_key"]) for r in alerts]
    id_set = set(ids)
    hash_errors: list[dict[str, Any]] = []
    json_errors: list[dict[str, Any]] = []
    identity_errors: list[dict[str, Any]] = []

    for row in alerts:
        source = str(row["collector_source_row_json"])
        actual = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if actual != str(row["payload_sha256"]):
            hash_errors.append(
                {"id": row["cloudflare_id"], "expected": row["payload_sha256"],
                 "actual": actual}
            )
        try:
            obj = json.loads(source)
        except Exception as exc:
            json_errors.append(
                {"id": row["cloudflare_id"], "error": f"{type(exc).__name__}: {exc}"}
            )
            continue
        if not isinstance(obj, dict):
            json_errors.append({"id": row["cloudflare_id"], "error": "not object"})
            continue
        checks = {
            "id": int(obj.get("id", -1)) == int(row["cloudflare_id"]),
            "event": str(obj.get("event", "")) == str(row["event"]),
            "ticker": str(obj.get("ticker", "")) == str(row["ticker"]),
            "bar_time_utc": str(obj.get("bar_time_utc", ""))
            == str(row["bar_time_utc"]),
            "fired_at_utc": str(obj.get("fired_at_utc", ""))
            == str(row["fired_at_utc"]),
            "received_at_utc": str(obj.get("received_at_utc", ""))
            == str(row["received_at_utc"]),
        }
        if not all(checks.values()):
            identity_errors.append({"id": row["cloudflare_id"], "checks": checks})

    cloudflare = [r for r in runs if str(r["source_mode"]) == "CLOUDFLARE"]
    regressions: list[dict[str, Any]] = []
    previous: int | None = None
    for row in cloudflare:
        cursor = int(row["cursor_after"])
        if previous is not None and cursor < previous:
            regressions.append(
                {"run_id": row["run_id"], "previous": previous, "cursor": cursor}
            )
        previous = cursor

    state_map = {str(r["state_key"]): str(r["state_value"]) for r in state}
    last_id = int(state_map.get("last_successful_id", "0"))
    max_id = max(ids, default=0)
    result = {
        "raw_alert_rows": len(alerts),
        "raw_alert_id_min": min(ids, default=0),
        "raw_alert_id_max": max_id,
        "raw_alert_duplicate_ids": len(ids) - len(set(ids)),
        "raw_alert_duplicate_event_keys": len(keys) - len(set(keys)),
        "payload_sha256_mismatches": hash_errors,
        "collector_source_json_parse_errors": json_errors,
        "collector_source_identity_mismatches": identity_errors,
        "annotation_orphans": [
            int(r["raw_alert_id"])
            for r in annotations
            if int(r["raw_alert_id"]) not in id_set
        ],
        "collection_run_duplicate_ids": len(runs)
        - len({str(r["run_id"]) for r in runs}),
        "collection_run_invalid_statuses": [
            str(r["status"])
            for r in runs
            if str(r["status"]) not in {"PASS", "PASS_EMPTY", "FAIL"}
        ],
        "cloudflare_cursor_regressions": regressions,
        "last_successful_id": last_id,
        "cursor_equals_max_raw_id": last_id == max_id,
        "forbidden_tables_exported": [],
        "outcome_tables_read": False,
        "performance_interpretation_performed": False,
    }
    bad = {
        k: v
        for k, v in result.items()
        if k in {
            "raw_alert_duplicate_ids", "raw_alert_duplicate_event_keys",
            "payload_sha256_mismatches", "collector_source_json_parse_errors",
            "collector_source_identity_mismatches", "annotation_orphans",
            "collection_run_duplicate_ids", "collection_run_invalid_statuses",
            "cloudflare_cursor_regressions",
        } and bool(v)
    }
    if not result["cursor_equals_max_raw_id"]:
        bad["cursor_equals_max_raw_id"] = False
    if bad:
        raise RuntimeError(f"source integrity checks failed: {bad}")
    return result


def capture(db: Path) -> tuple[Any, ...]:
    conn = connect_ro(db)
    try:
        journal = str(conn.execute("PRAGMA journal_mode").fetchone()[0])
        version = int(conn.execute("PRAGMA data_version").fetchone()[0])
        conn.execute("BEGIN")
        actual_tables = {
            str(r["name"])
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        missing = sorted(set(TABLES) - actual_tables)
        if missing:
            raise RuntimeError(f"required tables missing: {missing}")

        schema: dict[str, Any] = {}
        for table, expected in TABLES.items():
            actual = table_columns(conn, table)
            if actual != expected:
                raise RuntimeError(
                    f"schema mismatch for {table}: expected={expected} actual={actual}"
                )
            schema[table] = {"columns": actual, "column_count": len(actual)}

        state = rows(conn, "collector_state", "state_key")
        alerts = rows(conn, "raw_alerts", "cloudflare_id")
        annotations = rows(conn, "raw_alert_annotations", "raw_alert_id")
        runs = rows(conn, "collection_runs", "started_at_utc, run_id")
        checks = validate(state, alerts, annotations, runs)
        context = {
            "journal_mode": journal,
            "data_version_before_transaction": version,
            "actual_table_names": sorted(actual_tables),
            "forbidden_tables_present_but_not_read_or_exported": sorted(
                FORBIDDEN & actual_tables
            ),
        }
        conn.rollback()
        return context, schema, state, alerts, annotations, runs, checks
    finally:
        conn.close()


def error_zip(root: Path, db: Path, exc: Exception) -> Path:
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
            "stage": STAGE, "status": "BLOCKED_BCR01_SOURCE_SNAPSHOT_ERROR",
            "generated_at_utc": now(), "source_database_path": str(db),
            "error_type": type(exc).__name__, "error": str(exc),
            "source_runtime_modified": False, "outcomes_opened": False,
            "performance_interpretation_performed": False,
        },
    )
    package = staging / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(staging / "00_READ_ME_FIRST.txt", "00_READ_ME_FIRST.txt")
        z.write(staging / "01_snapshot_error.json", "01_snapshot_error.json")
    if latest.exists():
        shutil.rmtree(latest)
    os.replace(staging, latest)
    return latest / package.name


def build(db: Path, root: Path) -> Path:
    if not db.is_file():
        raise FileNotFoundError(f"source database not found: {db}")
    root.mkdir(parents=True, exist_ok=True)
    with RunLock(root / ".bcr01_run.lock"):
        started = now()
        before = {
            "db": meta(db), "wal": meta(Path(str(db) + "-wal")),
            "shm": meta(Path(str(db) + "-shm")),
        }
        context, schema, state, alerts, annotations, runs, checks = capture(db)
        after = {
            "db": meta(db), "wal": meta(Path(str(db) + "-wal")),
            "shm": meta(Path(str(db) + "-shm")),
        }

        max_id = int(checks["raw_alert_id_max"])
        snapshot_id = (
            f"BCR01_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_RAWMAX{max_id}"
        )
        run_dir = root / snapshot_id
        staging = root / (snapshot_id + "_STAGING")
        if run_dir.exists():
            raise FileExistsError(f"output exists: {run_dir}")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)

        manifest_cols = [
            c for c in TABLES["raw_alerts"]
            if c not in {"worker_raw_json", "collector_source_row_json"}
        ]
        write_csv(staging / "03_collector_state.csv", TABLES["collector_state"], state)
        write_csv(staging / "04_raw_alerts_manifest.csv", manifest_cols, alerts)
        with (staging / "05_raw_alerts_payloads.jsonl").open(
            "w", encoding="utf-8", newline="\n"
        ) as f:
            for row in alerts:
                f.write(
                    json.dumps(
                        row, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), default=str
                    ) + "\n"
                )
        write_csv(
            staging / "06_raw_alert_annotations.csv",
            TABLES["raw_alert_annotations"], annotations,
        )
        write_csv(staging / "07_collection_runs.csv", TABLES["collection_runs"], runs)

        summary = {
            "project": "BTC_CANDIDATE_RESEARCH_REDESIGN",
            "stage": STAGE, "version": VERSION,
            "status": "READY_OUTCOME_BLIND_SOURCE_SNAPSHOT",
            "snapshot_id": snapshot_id, "started_at_utc": started,
            "finished_at_utc": now(), "source_database_path": str(db.resolve()),
            "source_database_open_mode": "READ_ONLY_URI_MODE_RO_QUERY_ONLY",
            "sqlite_snapshot_contract": "CONSISTENT_READ_TRANSACTION",
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
                "before": before, "after": after,
                "note": "Consistency comes from the read-only SQLite transaction, "
                "not from copying or hashing the live DB/WAL/SHM files.",
            },
        )
        missing = [name for name in MEMBERS if not (staging / name).is_file()]
        if missing:
            raise RuntimeError(f"missing outputs: {missing}")

        os.replace(staging, run_dir)
        package = run_dir / "99_UPLOAD_PACKAGE.zip"
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
            for name in MEMBERS:
                z.write(run_dir / name, name)
        with zipfile.ZipFile(package, "r") as z:
            if z.namelist() != MEMBERS:
                raise RuntimeError(f"ZIP layout mismatch: {z.namelist()}")

        latest_staging = root / "LATEST_STAGING"
        latest = root / "LATEST"
        if latest_staging.exists():
            shutil.rmtree(latest_staging)
        shutil.copytree(run_dir, latest_staging)
        if latest.exists():
            shutil.rmtree(latest)
        os.replace(latest_staging, latest)
        return latest / package.name


def parse_args() -> argparse.Namespace:
    local = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-db", type=Path,
        default=local / "xauusd_signal_lab" / "mochipoyo_alert_research"
        / "mochipoyo_alerts.sqlite3",
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=local / "xauusd_signal_lab" / "btc_ml_v1" / "outputs"
        / "BCR01_outcome_blind_source_snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        package = build(args.source_db, args.output_root)
    except Exception as exc:
        try:
            package = error_zip(args.output_root, args.source_db, exc)
            print(f"[BCR01] ERROR PACKAGE: {package}", file=sys.stderr)
        except Exception:
            pass
        print(f"[BCR01] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"[BCR01] READY: {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
