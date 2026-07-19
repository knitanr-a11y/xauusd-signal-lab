from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import alert_entry_timing_builder as base

BOUNDARY_CONTRACT_VERSION = "MOCHIPOYO_M6C_EXIT_REFERENCE_BOUNDARY_V2"

ClosedCutoffKey = tuple[datetime, datetime, float]


def effective_closed_end(
    source_time_utc: datetime,
    requested_end_utc: datetime,
    offset_hours: float,
    closed_cutoffs: dict[ClosedCutoffKey, datetime],
) -> datetime:
    """Return the strict MT5 exit-reference cutoff for a closed source episode."""
    return closed_cutoffs.get(
        (source_time_utc, requested_end_utc, float(offset_hours)),
        requested_end_utc,
    )


def _build_closed_cutoffs(
    connection: sqlite3.Connection,
    mt5_files_root: Path,
) -> tuple[dict[ClosedCutoffKey, datetime], dict[str, datetime]]:
    entries = base._read_source_entries(connection)
    base._validate_upstream(connection, entries)

    m1_cache: dict[str, tuple[list[datetime], list[base.Bar]]] = {}
    by_window_key: dict[ClosedCutoffKey, datetime] = {}
    by_entry_id: dict[str, datetime] = {}

    for entry in entries:
        if entry.episode_status != "CLOSED":
            continue
        if entry.source_exit_time_utc is None:
            raise base.EntryTimingContractError(
                f"closed entry lacks source exit time: {entry.entry_id}"
            )

        if entry.ticker not in m1_cache:
            filename = base.FILE_MAP[entry.ticker]["M1"]
            m1_cache[entry.ticker] = base.load_bars(mt5_files_root / filename)

        m1_opens, m1_bars = m1_cache[entry.ticker]
        offset_hours = base._offset(connection, entry.source_entry_alert_id)
        exit_reference_time, _ = base._exit_reference(
            m1_opens,
            m1_bars,
            exit_time_utc=entry.source_exit_time_utc,
            offset_hours=offset_hours,
        )
        if exit_reference_time <= entry.source_entry_time_utc:
            raise base.EntryTimingContractError(
                "MT5 exit reference is not after the source entry: "
                f"{entry.entry_id}"
            )

        key = (
            entry.source_entry_time_utc,
            entry.source_exit_time_utc,
            float(offset_hours),
        )
        existing = by_window_key.get(key)
        if existing is not None and existing != exit_reference_time:
            raise base.EntryTimingContractError(
                f"conflicting closed cutoff for {entry.entry_id}"
            )
        by_window_key[key] = exit_reference_time
        by_entry_id[entry.entry_id] = exit_reference_time

    return by_window_key, by_entry_id


def rebuild_m5_entry_timing_audit(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    """Run M6C with a strict pre-exit MT5 reference boundary.

    The original M6C implementation used the source EXIT timestamp as the M5
    search end. When an EXIT arrived a few seconds after a five-minute boundary,
    an M5 close at that boundary was detected even though the MT5 comparison
    exit reference was the same timestamp. Such a candidate has no measurable
    holding interval. It must be recorded as missed, not abort the full audit.
    """
    closed_cutoffs, cutoff_by_entry = _build_closed_cutoffs(
        connection,
        mt5_files_root,
    )

    original_m5_window: Callable[..., Any] = base._m5_window
    original_reference_candidate: Callable[..., Any] = base._reference_candidate

    def boundary_safe_m5_window(
        opens: list[datetime],
        bars: list[base.Bar],
        *,
        source_time_utc: datetime,
        end_time_utc: datetime,
        offset_hours: float,
    ) -> list[tuple[datetime, datetime, base.Bar]]:
        strict_end = effective_closed_end(
            source_time_utc,
            end_time_utc,
            offset_hours,
            closed_cutoffs,
        )
        return original_m5_window(
            opens,
            bars,
            source_time_utc=source_time_utc,
            end_time_utc=strict_end,
            offset_hours=offset_hours,
        )

    def boundary_safe_reference_candidate(
        entry: base.SourceEntry,
        m1_opens: list[datetime],
        m1_bars: list[base.Bar],
        *,
        offset_hours: float,
        analysis_end_utc: datetime,
    ) -> base.Candidate:
        strict_end = cutoff_by_entry.get(entry.entry_id, analysis_end_utc)
        return original_reference_candidate(
            entry,
            m1_opens,
            m1_bars,
            offset_hours=offset_hours,
            analysis_end_utc=strict_end,
        )

    base._m5_window = boundary_safe_m5_window
    base._reference_candidate = boundary_safe_reference_candidate
    try:
        result = base.rebuild_m5_entry_timing_audit(
            connection,
            mt5_files_root=mt5_files_root,
            built_at_utc=built_at_utc,
        )
    finally:
        base._m5_window = original_m5_window
        base._reference_candidate = original_reference_candidate

    return {
        **result,
        "boundary_contract_version": BOUNDARY_CONTRACT_VERSION,
        "closed_episode_cutoff_count": len(cutoff_by_entry),
        "closed_episode_candidate_cutoff": (
            "STRICTLY_BEFORE_MT5_EXIT_REFERENCE_TIME"
        ),
        "candidate_at_or_after_exit_reference_handling": "MISSED_NOT_FATAL",
    }
