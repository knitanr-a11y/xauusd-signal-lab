from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from feature_snapshot_builder import (
    FEATURE_TIMEFRAMES,
    FeatureContractError,
    rebuild_feature_snapshots,
)


def eligible_raw_alert_ids(connection: sqlite3.Connection) -> list[int]:
    annotations_exist = (
        connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='raw_alert_annotations'"
        ).fetchone()
        is not None
    )
    exclusion = ""
    if annotations_exist:
        exclusion = """
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_alert_annotations a
                WHERE a.raw_alert_id = r.cloudflare_id
                  AND a.annotation_type = 'CONNECTION_TEST'
            )
        """
    rows = connection.execute(
        f"SELECT r.cloudflare_id FROM raw_alerts r "
        f"{exclusion} ORDER BY r.cloudflare_id"
    ).fetchall()
    return [int(row[0]) for row in rows]


def validate_current_alignment_coverage(
    connection: sqlite3.Connection,
) -> int:
    eligible_ids = eligible_raw_alert_ids(connection)
    rows = connection.execute(
        "SELECT raw_alert_id, timeframe FROM mt5_alignment "
        "ORDER BY raw_alert_id, timeframe"
    ).fetchall()
    aligned_ids = {int(row[0]) for row in rows}
    if aligned_ids != set(eligible_ids):
        missing = sorted(set(eligible_ids) - aligned_ids)
        extra = sorted(aligned_ids - set(eligible_ids))
        raise FeatureContractError(
            "Stage M4 alignment is stale or incomplete relative to current "
            f"raw alerts: missing={missing[:10]} extra={extra[:10]}"
        )

    expected_timeframes = set(FEATURE_TIMEFRAMES)
    timeframes_by_alert: dict[int, set[str]] = {}
    for row in rows:
        timeframes_by_alert.setdefault(int(row[0]), set()).add(str(row[1]))
    incomplete = {
        alert_id: sorted(expected_timeframes - timeframes)
        for alert_id, timeframes in timeframes_by_alert.items()
        if timeframes != expected_timeframes
    }
    if incomplete:
        raise FeatureContractError(
            "Stage M4 timeframe coverage is incomplete: "
            f"{list(incomplete.items())[:5]}"
        )

    expected_rows = len(eligible_ids) * len(FEATURE_TIMEFRAMES)
    if len(rows) != expected_rows:
        raise FeatureContractError(
            f"Stage M4 alignment row count is incomplete: "
            f"{len(rows)} != {expected_rows}"
        )
    return len(eligible_ids)


def rebuild_current_feature_snapshots(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    current_eligible_count = validate_current_alignment_coverage(connection)
    result = rebuild_feature_snapshots(
        connection,
        mt5_files_root=mt5_files_root,
        built_at_utc=built_at_utc,
    )
    if int(result["eligible_alert_count"]) != current_eligible_count:
        raise FeatureContractError(
            "feature builder eligible count changed after Stage M4 "
            "coverage validation"
        )
    return result
