from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "schema.sql"


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if not base:
        base = os.environ.get("TEMP", "").strip()
    if not base:
        base = tempfile.gettempdir()
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def ensure_annotation_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS episode_source_annotations (
            primary_alert_id INTEGER PRIMARY KEY
                REFERENCES raw_alerts(cloudflare_id),
            annotation_type TEXT NOT NULL
                CHECK (annotation_type IN ('CONNECTION_TEST')),
            confirmed_by TEXT NOT NULL
                CHECK (confirmed_by IN ('USER')),
            reason TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_episode_annotation_type
        ON episode_source_annotations (annotation_type, primary_alert_id);
        """
    )
    connection.commit()


def verify_confirmed_episode(
    connection: sqlite3.Connection, primary_alert_id: int
) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT
            r.cloudflare_id,
            r.ticker,
            r.event,
            r.message,
            r.fired_at_utc,
            e.episode_id,
            e.direction,
            e.episode_status,
            e.sequence_anomaly
        FROM raw_alerts r
        JOIN episodes e ON e.primary_alert_id = r.cloudflare_id
        WHERE r.cloudflare_id = ?
        """,
        (primary_alert_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"primary alert {primary_alert_id} is not present in a built episode"
        )
    expected_episode_id = f"XAUUSD:LONG:{primary_alert_id}"
    message = "" if row["message"] is None else str(row["message"]).strip()
    if str(row["ticker"]) != "XAUUSD":
        raise RuntimeError("confirmed connection test must be XAUUSD")
    if str(row["event"]) != "LONG" or str(row["direction"]) != "LONG":
        raise RuntimeError("confirmed connection test must be a LONG episode")
    if str(row["episode_id"]) != expected_episode_id:
        raise RuntimeError(
            f"unexpected episode identity: {row['episode_id']} != {expected_episode_id}"
        )
    if not message.lower().startswith("test "):
        raise RuntimeError(
            "primary alert message is not explicitly marked as a test; refusing annotation"
        )
    return row


def summary_counts(connection: sqlite3.Connection, *, clean: bool) -> dict[str, int]:
    episode_filter = "" if not clean else """
        WHERE NOT EXISTS (
            SELECT 1
            FROM episode_source_annotations a
            WHERE a.primary_alert_id = e.primary_alert_id
              AND a.annotation_type = 'CONNECTION_TEST'
        )
    """
    episode = connection.execute(
        f"""
        SELECT
            COUNT(*) AS episode_count,
            SUM(CASE WHEN e.episode_status = 'CLOSED' THEN 1 ELSE 0 END) AS closed_count,
            SUM(CASE WHEN e.episode_status = 'OPEN' THEN 1 ELSE 0 END) AS open_count
        FROM episodes e
        {episode_filter}
        """
    ).fetchone()

    clean_join = "" if not clean else """
        AND NOT EXISTS (
            SELECT 1
            FROM episode_source_annotations a
            WHERE a.primary_alert_id = e.primary_alert_id
              AND a.annotation_type = 'CONNECTION_TEST'
        )
    """
    reentry_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM episode_events ee
        JOIN episodes e ON e.episode_id = ee.episode_id
        WHERE ee.event_role = 'REENTRY_ALERT'
        {clean_join}
        """
    ).fetchone()[0]
    ignored_opposite_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM episode_events ee
        JOIN episodes e ON e.episode_id = ee.episode_id
        WHERE ee.event_role IN ('OPPOSITE_ALERT_IGNORED', 'OPPOSITE_EXIT_IGNORED')
        {clean_join}
        """
    ).fetchone()[0]

    if clean:
        anomaly_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM episode_build_anomalies a
            LEFT JOIN episodes e ON e.episode_id = a.related_episode_id
            WHERE e.episode_id IS NULL
               OR NOT EXISTS (
                    SELECT 1
                    FROM episode_source_annotations x
                    WHERE x.primary_alert_id = e.primary_alert_id
                      AND x.annotation_type = 'CONNECTION_TEST'
               )
            """
        ).fetchone()[0]
    else:
        anomaly_count = connection.execute(
            "SELECT COUNT(*) FROM episode_build_anomalies"
        ).fetchone()[0]

    return {
        "episode_count": int(episode["episode_count"] or 0),
        "closed_episode_count": int(episode["closed_count"] or 0),
        "open_episode_count": int(episode["open_count"] or 0),
        "reentry_count": int(reentry_count or 0),
        "anomaly_count": int(anomaly_count or 0),
        "ignored_opposite_count": int(ignored_opposite_count or 0),
    }


def confirm_and_report(
    connection: sqlite3.Connection,
    *,
    primary_alert_id: int,
    confirmed_at_utc: str,
) -> dict[str, Any]:
    ensure_annotation_table(connection)
    source = verify_confirmed_episode(connection, primary_alert_id)
    reason = (
        "User confirmed that the first XAUUSD episode was created only for "
        "Cloudflare/TradingView connection verification."
    )
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            """
            INSERT INTO episode_source_annotations (
                primary_alert_id, annotation_type, confirmed_by, reason, created_at_utc
            ) VALUES (?, 'CONNECTION_TEST', 'USER', ?, ?)
            ON CONFLICT(primary_alert_id) DO UPDATE SET
                annotation_type = excluded.annotation_type,
                confirmed_by = excluded.confirmed_by,
                reason = excluded.reason
            """,
            (primary_alert_id, reason, confirmed_at_utc),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    annotation = connection.execute(
        """
        SELECT primary_alert_id, annotation_type, confirmed_by, reason, created_at_utc
        FROM episode_source_annotations
        WHERE primary_alert_id = ?
        """,
        (primary_alert_id,),
    ).fetchone()
    raw_count = connection.execute("SELECT COUNT(*) FROM raw_alerts").fetchone()[0]
    excluded_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM episodes e
        JOIN episode_source_annotations a
          ON a.primary_alert_id = e.primary_alert_id
        WHERE a.annotation_type = 'CONNECTION_TEST'
        """
    ).fetchone()[0]

    return {
        "status": "PASS",
        "stage": "M3_CONNECTION_TEST_CONFIRMATION",
        "audit_only": True,
        "dry_run": True,
        "database_write_performed": True,
        "annotation_table_modified": True,
        "raw_alerts_modified": False,
        "episodes_modified": False,
        "episode_events_modified": False,
        "anomalies_modified": False,
        "future_entry_fields_used": False,
        "confirmed_at_utc": confirmed_at_utc,
        "raw_alert_count": int(raw_count or 0),
        "all_source_episodes": summary_counts(connection, clean=False),
        "clean_baseline": summary_counts(connection, clean=True),
        "excluded_connection_test_episode_count": int(excluded_count or 0),
        "confirmed_annotation": {
            "primary_alert_id": int(annotation["primary_alert_id"]),
            "episode_id": str(source["episode_id"]),
            "ticker": str(source["ticker"]),
            "direction": str(source["direction"]),
            "message": str(source["message"]),
            "annotation_type": str(annotation["annotation_type"]),
            "confirmed_by": str(annotation["confirmed_by"]),
            "reason": str(annotation["reason"]),
            "created_at_utc": str(annotation["created_at_utc"]),
        },
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Confirm the user-identified XAUUSD connection-test episode."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=default_local_root() / "mochipoyo_alerts.sqlite3",
    )
    parser.add_argument("--primary-alert-id", type=int, default=1)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_path = args.db.expanduser().resolve()
    output_path = (
        args.output.expanduser().resolve()
        if args.output is not None
        else database_path.parent / "logs" / "latest_clean_baseline_result.json"
    )
    if not database_path.is_file():
        print(f"[ERROR] Database not found: {database_path}")
        return 2
    if args.primary_alert_id <= 0:
        print("[ERROR] --primary-alert-id must be positive")
        return 2

    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        try:
            result = confirm_and_report(
                connection,
                primary_alert_id=args.primary_alert_id,
                confirmed_at_utc=utc_now_text(),
            )
        finally:
            connection.close()
        result["database_path"] = str(database_path)
        result["report_path"] = str(output_path)
        atomic_write_json(output_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
