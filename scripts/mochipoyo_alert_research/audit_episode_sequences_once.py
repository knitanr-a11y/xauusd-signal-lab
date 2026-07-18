from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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


def event_snapshot(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "raw_alert_id": int(row["cloudflare_id"]),
        "ticker": str(row["ticker"]),
        "event": str(row["event"]),
        "fired_at_utc": str(row["fired_at_utc"]),
        "bar_time_utc": str(row["bar_time_utc"]),
        "close_price": (
            None if row["close_price"] is None else float(row["close_price"])
        ),
    }


def same_ticker_neighbor(
    connection: sqlite3.Connection,
    *,
    ticker: str,
    raw_alert_id: int,
    before: bool,
) -> sqlite3.Row | None:
    operator = "<" if before else ">"
    order = "DESC" if before else "ASC"
    return connection.execute(
        f"""
        SELECT cloudflare_id, ticker, event, fired_at_utc, bar_time_utc, close_price
        FROM raw_alerts
        WHERE ticker = ? AND cloudflare_id {operator} ?
        ORDER BY cloudflare_id {order}
        LIMIT 1
        """,
        (ticker, raw_alert_id),
    ).fetchone()


def episode_sequence(
    connection: sqlite3.Connection, episode_id: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            ee.event_role,
            ee.reentry_index,
            r.cloudflare_id,
            r.ticker,
            r.event,
            r.fired_at_utc,
            r.bar_time_utc,
            r.close_price
        FROM episode_events ee
        JOIN raw_alerts r ON r.cloudflare_id = ee.raw_alert_id
        WHERE ee.episode_id = ?
        ORDER BY r.cloudflare_id ASC
        """,
        (episode_id,),
    ).fetchall()
    return [
        {
            "event_role": str(row["event_role"]),
            "reentry_index": (
                None
                if row["reentry_index"] is None
                else int(row["reentry_index"])
            ),
            **event_snapshot(row),
        }
        for row in rows
    ]


def build_report(
    connection: sqlite3.Connection, database_path: Path
) -> dict[str, Any]:
    required_tables = {
        "raw_alerts",
        "episodes",
        "episode_events",
        "episode_build_anomalies",
    }
    existing_tables = {
        str(row["name"])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    missing = sorted(required_tables - existing_tables)
    if missing:
        raise RuntimeError(
            "Stage M3 tables are missing. Run run_build_episodes_once.bat first: "
            + ", ".join(missing)
        )

    counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM raw_alerts) AS raw_alert_count,
            (SELECT COUNT(*) FROM episodes) AS episode_count,
            (SELECT COUNT(*) FROM episodes WHERE episode_status = 'CLOSED') AS closed_count,
            (SELECT COUNT(*) FROM episodes WHERE episode_status = 'OPEN') AS open_count,
            (SELECT COUNT(*) FROM episode_events WHERE event_role = 'REENTRY_ALERT') AS reentry_count,
            (SELECT COUNT(*) FROM episode_build_anomalies) AS anomaly_count,
            (SELECT COALESCE(MAX(cloudflare_id), 0) FROM raw_alerts) AS latest_raw_id
        """
    ).fetchone()

    episode_rows = connection.execute(
        """
        SELECT
            e.episode_id,
            e.ticker,
            e.direction,
            e.primary_alert_id,
            e.started_at_utc,
            e.exit_alert_id,
            e.exited_at_utc,
            e.episode_status,
            e.exit_missing,
            e.sequence_anomaly,
            SUM(CASE WHEN ee.event_role = 'REENTRY_ALERT' THEN 1 ELSE 0 END) AS reentry_count,
            COUNT(ee.raw_alert_id) AS attached_event_count
        FROM episodes e
        LEFT JOIN episode_events ee ON ee.episode_id = e.episode_id
        GROUP BY
            e.episode_id, e.ticker, e.direction, e.primary_alert_id,
            e.started_at_utc, e.exit_alert_id, e.exited_at_utc,
            e.episode_status, e.exit_missing, e.sequence_anomaly
        ORDER BY e.primary_alert_id ASC
        """
    ).fetchall()
    episodes = [
        {
            "episode_id": str(row["episode_id"]),
            "ticker": str(row["ticker"]),
            "direction": str(row["direction"]),
            "primary_alert_id": int(row["primary_alert_id"]),
            "started_at_utc": str(row["started_at_utc"]),
            "exit_alert_id": (
                None
                if row["exit_alert_id"] is None
                else int(row["exit_alert_id"])
            ),
            "exited_at_utc": (
                None
                if row["exited_at_utc"] is None
                else str(row["exited_at_utc"])
            ),
            "episode_status": str(row["episode_status"]),
            "exit_missing": bool(row["exit_missing"]),
            "sequence_anomaly": bool(row["sequence_anomaly"]),
            "reentry_count": int(row["reentry_count"] or 0),
            "attached_event_count": int(row["attached_event_count"] or 0),
        }
        for row in episode_rows
    ]

    anomaly_rows = connection.execute(
        """
        SELECT
            anomaly_id,
            raw_alert_id,
            ticker,
            event,
            state_before,
            reason,
            related_episode_id,
            created_at_utc
        FROM episode_build_anomalies
        ORDER BY raw_alert_id ASC
        """
    ).fetchall()
    anomalies: list[dict[str, Any]] = []
    for row in anomaly_rows:
        raw_alert_id = int(row["raw_alert_id"])
        ticker = str(row["ticker"])
        current = connection.execute(
            """
            SELECT cloudflare_id, ticker, event, fired_at_utc, bar_time_utc, close_price
            FROM raw_alerts
            WHERE cloudflare_id = ?
            """,
            (raw_alert_id,),
        ).fetchone()
        related_episode_id = (
            None
            if row["related_episode_id"] is None
            else str(row["related_episode_id"])
        )
        anomalies.append(
            {
                "anomaly_id": int(row["anomaly_id"]),
                "reason": str(row["reason"]),
                "state_before": str(row["state_before"]),
                "related_episode_id": related_episode_id,
                "anomalous_event": event_snapshot(current),
                "previous_same_ticker_event": event_snapshot(
                    same_ticker_neighbor(
                        connection,
                        ticker=ticker,
                        raw_alert_id=raw_alert_id,
                        before=True,
                    )
                ),
                "next_same_ticker_event": event_snapshot(
                    same_ticker_neighbor(
                        connection,
                        ticker=ticker,
                        raw_alert_id=raw_alert_id,
                        before=False,
                    )
                ),
                "related_episode_sequence": (
                    []
                    if related_episode_id is None
                    else episode_sequence(connection, related_episode_id)
                ),
            }
        )

    open_episodes = [
        {
            **episode,
            "sequence": episode_sequence(connection, episode["episode_id"]),
        }
        for episode in episodes
        if episode["episode_status"] == "OPEN"
    ]

    return {
        "status": "PASS",
        "stage": "M3_EPISODE_SEQUENCE_AUDIT",
        "audit_only": True,
        "dry_run": True,
        "database_write_performed": False,
        "raw_alerts_modified": False,
        "derived_tables_modified": False,
        "future_entry_fields_used": False,
        "generated_at_utc": utc_now_text(),
        "raw_alert_count": int(counts["raw_alert_count"] or 0),
        "episode_count": int(counts["episode_count"] or 0),
        "closed_episode_count": int(counts["closed_count"] or 0),
        "open_episode_count": int(counts["open_count"] or 0),
        "reentry_count": int(counts["reentry_count"] or 0),
        "anomaly_count": int(counts["anomaly_count"] or 0),
        "latest_raw_id": int(counts["latest_raw_id"] or 0),
        "open_episodes": open_episodes,
        "anomalies": anomalies,
        "episodes": episodes,
        "database_path": str(database_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Stage M3 episode and anomaly audit report."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=default_local_root() / "mochipoyo_alerts.sqlite3",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_path = args.db.expanduser().resolve()
    output_path = (
        args.output.expanduser().resolve()
        if args.output is not None
        else database_path.parent
        / "logs"
        / "latest_episode_sequence_audit.json"
    )
    if not database_path.is_file():
        print(f"[ERROR] Database not found: {database_path}")
        return 2

    try:
        connection = sqlite3.connect(
            f"file:{database_path.as_posix()}?mode=ro",
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            report = build_report(connection, database_path)
        finally:
            connection.close()
        report["report_path"] = str(output_path)
        atomic_write_json(output_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
