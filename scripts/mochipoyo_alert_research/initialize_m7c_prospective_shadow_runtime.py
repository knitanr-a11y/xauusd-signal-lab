from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import m7c_prospective_shadow as core

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_TEMPLATE = (
    REPO_ROOT
    / "config"
    / "mochipoyo_alert_research"
    / "m7c_prospective_shadow_manifest_v1.json"
)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze a local M7C start after the collector has caught up."
    )
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--template-manifest", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--runtime-manifest", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--lock-file", required=True, type=Path)
    parser.add_argument("--required-empty-runs", type=int, default=3)
    return parser.parse_args()


def catchup_evidence(
    connection: sqlite3.Connection, required_empty_runs: int
) -> dict[str, Any]:
    max_raw_id = int(
        connection.execute(
            "SELECT COALESCE(MAX(cloudflare_id), 0) FROM raw_alerts"
        ).fetchone()[0]
        or 0
    )
    cursor_row = connection.execute(
        "SELECT state_value FROM collector_state WHERE state_key = 'last_successful_id'"
    ).fetchone()
    cursor = 0 if cursor_row is None else int(cursor_row[0])
    rows = connection.execute(
        """
        SELECT status, response_count, cursor_after, finished_at_utc, run_id
        FROM collection_runs
        WHERE source_mode = 'CLOUDFLARE'
        ORDER BY finished_at_utc DESC, run_id DESC
        LIMIT ?
        """,
        (required_empty_runs,),
    ).fetchall()
    recent = [dict(row) for row in rows]
    if len(recent) < required_empty_runs:
        raise RuntimeError("not enough recent Cloudflare collector runs")
    if any(
        str(row["status"]) != "PASS_EMPTY"
        or int(row["response_count"] or 0) != 0
        or int(row["cursor_after"] or 0) != max_raw_id
        for row in recent
    ):
        raise RuntimeError(
            "collector catch-up is not proven by consecutive PASS_EMPTY runs"
        )
    if cursor != max_raw_id:
        raise RuntimeError(
            f"collector cursor {cursor} differs from latest raw alert ID {max_raw_id}"
        )
    assigned = [
        int(row[0])
        for row in connection.execute(
            "SELECT raw_alert_id FROM episode_events ORDER BY raw_alert_id"
        ).fetchall()
    ]
    aligned = [
        int(row[0])
        for row in connection.execute(
            "SELECT raw_alert_id FROM mt5_alignment WHERE timeframe='M15' ORDER BY raw_alert_id"
        ).fetchall()
    ]
    eligible = [
        int(row[0])
        for row in connection.execute(
            """
            SELECT r.cloudflare_id
            FROM raw_alerts r
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_alert_annotations a
                WHERE a.raw_alert_id=r.cloudflare_id
                  AND a.annotation_type='CONNECTION_TEST'
            )
            ORDER BY r.cloudflare_id
            """
        ).fetchall()
    ]
    if assigned != eligible or aligned != eligible:
        raise RuntimeError("M3/M4 are stale; refresh them before initialization")
    return {
        "required_consecutive_pass_empty_runs": required_empty_runs,
        "latest_raw_alert_id": max_raw_id,
        "collector_cursor": cursor,
        "recent_runs": recent,
    }


def build_runtime_manifest(
    connection: sqlite3.Connection,
    template: dict[str, Any],
    start: datetime,
    evidence: dict[str, Any],
    template_sha256: str,
) -> dict[str, Any]:
    events = core.read_source_events(connection)
    pre_events = [event for event in events if core.floor_15(event.bar_time_utc) <= start]
    transitions = core.replay(pre_events)

    ids: dict[str, list[int]] = defaultdict(list)
    states: dict[str, str] = {}
    latest_ids: dict[str, int] = {}
    for row in transitions:
        ids[row.ticker].append(row.raw_alert_id)
        states[row.ticker] = row.state_after
        latest_ids[row.ticker] = row.raw_alert_id

    by_ticker: dict[str, list[Any]] = defaultdict(list)
    for event in pre_events:
        by_ticker[event.ticker].append(event)

    bootstrap: dict[str, Any] = {}
    for ticker in sorted(template["bootstrap"]):
        ticker_events = sorted(
            by_ticker.get(ticker, []),
            key=lambda row: (row.bar_time_utc, row.fired_at_utc, row.raw_id),
        )
        if not ticker_events or ticker not in states:
            raise RuntimeError(f"cannot freeze bootstrap for {ticker}")
        latest_event = ticker_events[-1]
        bootstrap[ticker] = {
            "state_at_start": states[ticker],
            "latest_raw_alert_id": latest_ids[ticker],
            "offset_hours": float(latest_event.selected_offset_hours),
            "expected_pre_start_raw_alert_ids": ids[ticker],
        }

    runtime = json.loads(json.dumps(template))
    runtime["prospective_start_utc"] = core.iso_z(start)
    runtime["frozen_after_collector_catchup_at_utc"] = core.iso_z(start)
    runtime["bootstrap"] = bootstrap
    runtime["runtime_bootstrap"] = {
        "status": "FROZEN_AFTER_COLLECTOR_CATCHUP",
        "created_at_utc": core.iso_z(start),
        "template_manifest_sha256": template_sha256,
        "collector_catchup_evidence": evidence,
        "pre_start_events_used_for_state_only": True,
        "pre_start_events_scored": False,
        "late_event_at_or_before_start_policy": "FAIL_CLOSED",
    }
    return runtime


def main() -> int:
    args = parse_args()
    try:
        if args.required_empty_runs < 2:
            raise RuntimeError("required empty runs must be at least 2")
        for path, label in (
            (args.db, "SQLite database"),
            (args.template_manifest, "template manifest"),
        ):
            if not path.is_file():
                raise RuntimeError(f"missing {label}: {path}")
        if args.lock_file.exists():
            raise RuntimeError("stop the M7C monitor before initialization")
        if args.runtime_manifest.exists():
            raise RuntimeError(
                "runtime manifest already exists; do not reset an active observation"
            )

        template_bytes = args.template_manifest.read_bytes()
        template = core.load_manifest(args.template_manifest)
        connection = sqlite3.connect(args.db)
        connection.row_factory = sqlite3.Row
        try:
            before = catchup_evidence(connection, args.required_empty_runs)
            start = utc_now()
            runtime = build_runtime_manifest(
                connection,
                template,
                start,
                before,
                hashlib.sha256(template_bytes).hexdigest(),
            )
            after = catchup_evidence(connection, args.required_empty_runs)
            if before["latest_raw_alert_id"] != after["latest_raw_alert_id"]:
                raise RuntimeError("new raw alerts arrived during initialization; rerun")
        finally:
            connection.close()

        atomic_write_json(args.runtime_manifest, runtime)
        receipt = {
            "status": "PASS",
            "stage": "M7C_RUNTIME_BOOTSTRAP_INITIALIZATION_AUDIT_ONLY",
            "audit_only": True,
            "prospective_start_utc": runtime["prospective_start_utc"],
            "runtime_manifest": str(args.runtime_manifest),
            "bootstrap": runtime["bootstrap"],
            "collector_catchup_evidence": after,
            "entry_gate_enabled": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        }
        atomic_write_json(args.receipt, receipt)
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"[M7C_INIT_FAIL_CLOSED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No new runtime start was frozen.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
