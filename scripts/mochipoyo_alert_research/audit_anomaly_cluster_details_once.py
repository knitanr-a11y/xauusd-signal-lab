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


def build_report(connection: sqlite3.Connection, database_path: Path) -> dict[str, Any]:
    related_rows = connection.execute(
        """
        SELECT DISTINCT related_episode_id
        FROM episode_build_anomalies
        WHERE related_episode_id IS NOT NULL
        ORDER BY related_episode_id
        """
    ).fetchall()
    related_episode_ids = [str(row["related_episode_id"]) for row in related_rows]

    clusters: list[dict[str, Any]] = []
    for episode_id in related_episode_ids:
        episode = connection.execute(
            """
            SELECT episode_id, ticker, direction, primary_alert_id, started_at_utc,
                   exit_alert_id, exited_at_utc, episode_status, sequence_anomaly
            FROM episodes
            WHERE episode_id = ?
            """,
            (episode_id,),
        ).fetchone()
        if episode is None:
            continue

        event_rows = connection.execute(
            """
            SELECT
                ee.event_role,
                ee.reentry_index,
                r.cloudflare_id,
                r.event_key_origin,
                r.worker_raw_json_origin,
                r.received_at_utc,
                r.source,
                r.strategy,
                r.event,
                r.exchange_name,
                r.ticker,
                r.timeframe,
                r.bar_time_utc,
                r.fired_at_utc,
                r.open_price,
                r.high_price,
                r.low_price,
                r.close_price,
                r.message
            FROM episode_events ee
            JOIN raw_alerts r ON r.cloudflare_id = ee.raw_alert_id
            WHERE ee.episode_id = ?
            ORDER BY r.cloudflare_id ASC
            """,
            (episode_id,),
        ).fetchall()

        events = []
        for row in event_rows:
            events.append(
                {
                    "event_role": str(row["event_role"]),
                    "reentry_index": (
                        None if row["reentry_index"] is None else int(row["reentry_index"])
                    ),
                    "raw_alert_id": int(row["cloudflare_id"]),
                    "event_key_origin": str(row["event_key_origin"]),
                    "worker_raw_json_origin": str(row["worker_raw_json_origin"]),
                    "received_at_utc": str(row["received_at_utc"]),
                    "source": str(row["source"]),
                    "strategy": str(row["strategy"]),
                    "event": str(row["event"]),
                    "exchange_name": (
                        None if row["exchange_name"] is None else str(row["exchange_name"])
                    ),
                    "ticker": str(row["ticker"]),
                    "timeframe": None if row["timeframe"] is None else str(row["timeframe"]),
                    "bar_time_utc": str(row["bar_time_utc"]),
                    "fired_at_utc": str(row["fired_at_utc"]),
                    "open_price": row["open_price"],
                    "high_price": row["high_price"],
                    "low_price": row["low_price"],
                    "close_price": row["close_price"],
                    "message": None if row["message"] is None else str(row["message"]),
                }
            )

        anomaly_rows = connection.execute(
            """
            SELECT anomaly_id, raw_alert_id, event, state_before, reason, created_at_utc
            FROM episode_build_anomalies
            WHERE related_episode_id = ?
            ORDER BY raw_alert_id ASC
            """,
            (episode_id,),
        ).fetchall()
        anomalies = [
            {
                "anomaly_id": int(row["anomaly_id"]),
                "raw_alert_id": int(row["raw_alert_id"]),
                "event": str(row["event"]),
                "state_before": str(row["state_before"]),
                "reason": str(row["reason"]),
                "created_at_utc": str(row["created_at_utc"]),
            }
            for row in anomaly_rows
        ]

        clusters.append(
            {
                "episode": {
                    "episode_id": str(episode["episode_id"]),
                    "ticker": str(episode["ticker"]),
                    "direction": str(episode["direction"]),
                    "primary_alert_id": int(episode["primary_alert_id"]),
                    "started_at_utc": str(episode["started_at_utc"]),
                    "exit_alert_id": (
                        None if episode["exit_alert_id"] is None else int(episode["exit_alert_id"])
                    ),
                    "exited_at_utc": (
                        None if episode["exited_at_utc"] is None else str(episode["exited_at_utc"])
                    ),
                    "episode_status": str(episode["episode_status"]),
                    "sequence_anomaly": bool(episode["sequence_anomaly"]),
                },
                "anomalies": anomalies,
                "events": events,
            }
        )

    return {
        "status": "PASS",
        "stage": "M3_ANOMALY_CLUSTER_DETAIL_AUDIT",
        "audit_only": True,
        "dry_run": True,
        "database_write_performed": False,
        "raw_alerts_modified": False,
        "derived_tables_modified": False,
        "raw_json_included": False,
        "secrets_included": False,
        "generated_at_utc": utc_now_text(),
        "related_episode_count": len(clusters),
        "clusters": clusters,
        "database_path": str(database_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only detail audit for episodes referenced by Stage M3 anomalies."
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
        else database_path.parent / "logs" / "latest_anomaly_cluster_detail_audit.json"
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
