from __future__ import annotations

import csv
import json
import math
import sqlite3
from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mt5_csv_contract import EXPECTED_HEADER, FILE_MAP, parse_mt5_time, parse_utc

CONTRACT_VERSION = "MOCHIPOYO_M6C_M5_ENTRY_TIMING_V1"
ENTRY_ID_PREFIX = "M6A:"
VARIANTS = (
    "SOURCE_NEXT_M1_OPEN_REFERENCE",
    "M5_FIRST_DIRECTIONAL_BODY_CLOSE",
    "M5_TWO_BAR_BREAK_CLOSE",
    "M5_PULLBACK_THEN_TWO_BAR_BREAK_CLOSE",
    "M5_SECOND_BOTTOM_TOP_BREAK_CLOSE",
)
PIVOT_LEFT = 2
PIVOT_RIGHT = 2


class EntryTimingContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class Bar:
    server_open: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float


@dataclass(frozen=True)
class SourceEntry:
    entry_id: str
    episode_id: str
    ticker: str
    direction: str
    entry_role: str
    source_entry_alert_id: int
    source_entry_time_utc: datetime
    source_entry_price: float
    episode_status: str
    source_exit_alert_id: int | None
    source_exit_time_utc: datetime | None


@dataclass(frozen=True)
class Candidate:
    variant: str
    detected: bool
    entry_time_utc: datetime | None
    entry_price: float | None
    trigger_time_utc: datetime | None
    diagnostics: dict[str, Any]


def iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _finite(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise EntryTimingContractError(f"non-finite {label}")
    return result


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS m5_entry_timing_candidates (
            source_entry_id TEXT NOT NULL REFERENCES virtual_entries(entry_id),
            variant TEXT NOT NULL,
            contract_version TEXT NOT NULL,
            source_entry_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
            episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
            entry_role TEXT NOT NULL CHECK (entry_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')),
            source_entry_time_utc TEXT NOT NULL,
            source_entry_price REAL NOT NULL,
            candidate_detected INTEGER NOT NULL CHECK (candidate_detected IN (0, 1)),
            candidate_entry_time_utc TEXT,
            candidate_entry_price REAL,
            trigger_time_utc TEXT,
            entry_delay_seconds REAL,
            price_improvement_atr_m5 REAL,
            diagnostics_json TEXT NOT NULL,
            future_entry_fields_used INTEGER NOT NULL CHECK (future_entry_fields_used = 0),
            approved_for_trading INTEGER NOT NULL CHECK (approved_for_trading = 0),
            PRIMARY KEY (source_entry_id, variant)
        );

        CREATE TABLE IF NOT EXISTS m5_entry_timing_outcomes (
            source_entry_id TEXT NOT NULL,
            variant TEXT NOT NULL,
            source_exit_time_utc TEXT NOT NULL,
            mt5_exit_reference_time_utc TEXT NOT NULL,
            mt5_exit_reference_price REAL NOT NULL,
            return_price_units REAL NOT NULL,
            return_atr_m5 REAL NOT NULL,
            mfe_price_units REAL NOT NULL,
            mae_price_units REAL NOT NULL,
            mfe_atr_m5 REAL NOT NULL,
            mae_atr_m5 REAL NOT NULL,
            path_bar_count INTEGER NOT NULL,
            path_gap_count INTEGER NOT NULL,
            time_to_mfe_seconds REAL NOT NULL,
            time_to_mae_seconds REAL NOT NULL,
            favorable_first_status TEXT NOT NULL,
            expansion_class TEXT NOT NULL,
            positive_exit INTEGER NOT NULL CHECK (positive_exit IN (0, 1)),
            future_path_violation_count INTEGER NOT NULL CHECK (future_path_violation_count = 0),
            diagnostics_json TEXT NOT NULL,
            PRIMARY KEY (source_entry_id, variant),
            FOREIGN KEY (source_entry_id, variant)
                REFERENCES m5_entry_timing_candidates(source_entry_id, variant)
        );

        CREATE TABLE IF NOT EXISTS m5_entry_timing_cohorts (
            dimension TEXT NOT NULL,
            dimension_value TEXT NOT NULL,
            resolved_count INTEGER NOT NULL,
            detected_count INTEGER NOT NULL,
            missed_count INTEGER NOT NULL,
            positive_exit_count INTEGER NOT NULL,
            expansion_count INTEGER NOT NULL,
            positive_exit_ratio REAL,
            expansion_ratio REAL,
            mean_return_atr_m5 REAL,
            mean_mfe_atr_m5 REAL,
            mean_mae_atr_m5 REAL,
            mean_entry_delay_seconds REAL,
            mean_price_improvement_atr_m5 REAL,
            mean_delta_return_vs_reference_atr_m5 REAL,
            mean_delta_mae_vs_reference_atr_m5 REAL,
            sample_status TEXT NOT NULL,
            generated_at_utc TEXT NOT NULL,
            PRIMARY KEY (dimension, dimension_value)
        );

        CREATE TABLE IF NOT EXISTS m5_entry_timing_build_runs (
            build_id INTEGER PRIMARY KEY AUTOINCREMENT,
            built_at_utc TEXT NOT NULL,
            contract_version TEXT NOT NULL,
            source_entry_count INTEGER NOT NULL,
            closed_source_entry_count INTEGER NOT NULL,
            open_source_entry_count INTEGER NOT NULL,
            candidate_row_count INTEGER NOT NULL,
            detected_candidate_count INTEGER NOT NULL,
            outcome_row_count INTEGER NOT NULL,
            cohort_row_count INTEGER NOT NULL,
            future_entry_violation_count INTEGER NOT NULL CHECK (future_entry_violation_count = 0),
            future_path_violation_count INTEGER NOT NULL CHECK (future_path_violation_count = 0),
            approved_for_trading INTEGER NOT NULL CHECK (approved_for_trading = 0),
            audit_only INTEGER NOT NULL CHECK (audit_only = 1)
        );
        """
    )
    connection.commit()


def _entry_role(entry_type: str) -> str:
    if entry_type == "SOURCE_PRIMARY_ALERT_IMMEDIATE":
        return "PRIMARY_ALERT"
    if entry_type == "SOURCE_REENTRY_ALERT_IMMEDIATE":
        return "REENTRY_ALERT"
    raise EntryTimingContractError(f"unsupported M6A entry type: {entry_type}")


def _read_source_entries(connection: sqlite3.Connection) -> list[SourceEntry]:
    rows = connection.execute(
        """
        SELECT
            v.entry_id,
            v.episode_id,
            v.entry_type,
            v.entry_index,
            v.entry_time_utc,
            v.entry_price,
            e.ticker,
            e.direction,
            e.episode_status,
            e.exit_alert_id,
            exit_raw.fired_at_utc AS exit_time_utc,
            CASE
                WHEN v.entry_type = 'SOURCE_PRIMARY_ALERT_IMMEDIATE'
                    THEN e.primary_alert_id
                WHEN v.entry_type = 'SOURCE_REENTRY_ALERT_IMMEDIATE'
                    THEN (
                        SELECT ee.raw_alert_id
                        FROM episode_events ee
                        WHERE ee.episode_id = v.episode_id
                          AND ee.event_role = 'REENTRY_ALERT'
                          AND ee.reentry_index = v.entry_index
                    )
                ELSE NULL
            END AS source_entry_alert_id
        FROM virtual_entries v
        JOIN episodes e ON e.episode_id = v.episode_id
        LEFT JOIN raw_alerts exit_raw ON exit_raw.cloudflare_id = e.exit_alert_id
        WHERE v.entry_id LIKE ?
        ORDER BY e.primary_alert_id, v.entry_index, v.entry_id
        """,
        (ENTRY_ID_PREFIX + "%",),
    ).fetchall()
    output: list[SourceEntry] = []
    for row in rows:
        source_id = row["source_entry_alert_id"]
        if source_id is None:
            raise EntryTimingContractError(
                f"cannot resolve source event for {row['entry_id']}"
            )
        status = str(row["episode_status"])
        exit_id = None if row["exit_alert_id"] is None else int(row["exit_alert_id"])
        exit_time = (
            None
            if row["exit_time_utc"] is None
            else parse_utc(str(row["exit_time_utc"]))
        )
        if status == "CLOSED" and (exit_id is None or exit_time is None):
            raise EntryTimingContractError(
                f"closed episode lacks source exit: {row['episode_id']}"
            )
        if status == "OPEN" and (exit_id is not None or exit_time is not None):
            raise EntryTimingContractError(
                f"open episode unexpectedly has exit: {row['episode_id']}"
            )
        output.append(
            SourceEntry(
                entry_id=str(row["entry_id"]),
                episode_id=str(row["episode_id"]),
                ticker=str(row["ticker"]),
                direction=str(row["direction"]),
                entry_role=_entry_role(str(row["entry_type"])),
                source_entry_alert_id=int(source_id),
                source_entry_time_utc=parse_utc(str(row["entry_time_utc"])),
                source_entry_price=_finite(
                    row["entry_price"], label=f"source entry price {row['entry_id']}"
                ),
                episode_status=status,
                source_exit_alert_id=exit_id,
                source_exit_time_utc=exit_time,
            )
        )
    return output


def _eligible_source_event_ids(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(
        """
        SELECT raw_alert_id
        FROM episode_events
        WHERE event_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')
        ORDER BY raw_alert_id
        """
    ).fetchall()
    return [int(row[0]) for row in rows]


def _validate_upstream(
    connection: sqlite3.Connection,
    entries: list[SourceEntry],
) -> dict[str, int]:
    if not entries:
        raise EntryTimingContractError("Stage M6A source entries do not exist")
    expected_ids = _eligible_source_event_ids(connection)
    actual_ids = sorted(entry.source_entry_alert_id for entry in entries)
    if actual_ids != expected_ids:
        raise EntryTimingContractError(
            "Stage M6A virtual entries are stale relative to Stage M3 episode events"
        )

    m6a_outcome_rows = int(
        connection.execute(
            "SELECT COUNT(*) FROM outcome_path_metrics WHERE entry_id LIKE ?",
            (ENTRY_ID_PREFIX + "%",),
        ).fetchone()[0]
        or 0
    )
    closed_count = sum(1 for entry in entries if entry.episode_status == "CLOSED")
    open_count = len(entries) - closed_count
    if m6a_outcome_rows != closed_count:
        raise EntryTimingContractError(
            "Stage M6A outcome rows are stale or incomplete "
            f"({m6a_outcome_rows} != {closed_count})"
        )

    feature_rows = connection.execute(
        """
        SELECT source_event_id, timeframe, future_fields_present
        FROM feature_snapshots
        WHERE source_event_id IN (
            SELECT raw_alert_id FROM episode_events
            WHERE event_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')
        )
        ORDER BY source_event_id, timeframe
        """
    ).fetchall()
    by_id: dict[int, set[str]] = defaultdict(set)
    future_count = 0
    for row in feature_rows:
        by_id[int(row["source_event_id"])].add(str(row["timeframe"]))
        future_count += int(row["future_fields_present"] or 0)
    expected_tfs = {"M5", "M15", "H1", "H4", "D1"}
    if set(by_id) != set(expected_ids):
        raise EntryTimingContractError("Stage M5 entry feature coverage is stale")
    if any(values != expected_tfs for values in by_id.values()):
        raise EntryTimingContractError("Stage M5 entry feature timeframes are incomplete")
    if future_count:
        raise EntryTimingContractError(
            f"Stage M5 contains {future_count} future-field violations"
        )
    return {
        "source_entry_count": len(entries),
        "closed_source_entry_count": closed_count,
        "open_source_entry_count": open_count,
    }


def _offset(connection: sqlite3.Connection, raw_alert_id: int) -> float:
    row = connection.execute(
        """
        SELECT selected_offset_hours, alignment_status
        FROM mt5_alignment
        WHERE raw_alert_id = ? AND timeframe = 'M5'
        """,
        (raw_alert_id,),
    ).fetchone()
    if row is None or str(row["alignment_status"]) != "ALIGNED_CLOSED_BAR":
        raise EntryTimingContractError(
            f"missing valid M5 alignment for raw alert {raw_alert_id}"
        )
    return _finite(row["selected_offset_hours"], label="selected MT5 offset")


def _atr_m5(connection: sqlite3.Connection, raw_alert_id: int) -> float:
    row = connection.execute(
        """
        SELECT features_json, future_fields_present
        FROM feature_snapshots
        WHERE source_event_id = ? AND timeframe = 'M5'
        """,
        (raw_alert_id,),
    ).fetchone()
    if row is None or int(row["future_fields_present"] or 0) != 0:
        raise EntryTimingContractError(
            f"missing safe M5 feature snapshot for raw alert {raw_alert_id}"
        )
    payload = json.loads(str(row["features_json"]))
    atr = _finite(payload["volatility"]["atr14"], label="M5 ATR14")
    if atr <= 0:
        raise EntryTimingContractError("M5 ATR14 must be positive")
    return atr


def load_bars(path: Path) -> tuple[list[datetime], list[Bar]]:
    if not path.is_file():
        raise EntryTimingContractError(f"missing CSV: {path.name}")
    opens: list[datetime] = []
    bars: list[Bar] = []
    previous: datetime | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise EntryTimingContractError(f"unexpected header: {path.name}")
        for line_number, row in enumerate(reader, start=2):
            try:
                server_open = parse_mt5_time(row["time"])
                bar = Bar(
                    server_open=server_open,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                )
            except Exception as exc:
                raise EntryTimingContractError(
                    f"invalid row in {path.name} at line {line_number}"
                ) from exc
            if previous is not None and server_open <= previous:
                raise EntryTimingContractError(
                    f"non-ascending timestamps in {path.name}"
                )
            previous = server_open
            opens.append(server_open)
            bars.append(bar)
    if not bars:
        raise EntryTimingContractError(f"CSV has no rows: {path.name}")
    return opens, bars


def _utc_open(bar: Bar, offset_hours: float) -> datetime:
    return bar.server_open - timedelta(hours=offset_hours)


def _m5_window(
    opens: list[datetime],
    bars: list[Bar],
    *,
    source_time_utc: datetime,
    end_time_utc: datetime,
    offset_hours: float,
) -> list[tuple[datetime, datetime, Bar]]:
    source_server = source_time_utc + timedelta(hours=offset_hours)
    end_server = end_time_utc + timedelta(hours=offset_hours)
    left = max(0, bisect_right(opens, source_server - timedelta(minutes=5)) - 2)
    right = bisect_left(opens, end_server)
    output: list[tuple[datetime, datetime, Bar]] = []
    for bar in bars[left:right]:
        utc_open = _utc_open(bar, offset_hours)
        utc_close = utc_open + timedelta(minutes=5)
        if utc_close <= source_time_utc:
            continue
        if utc_close >= end_time_utc:
            continue
        output.append((utc_open, utc_close, bar))
    return output


def _candidate(
    variant: str,
    detected: bool,
    *,
    entry_time_utc: datetime | None = None,
    entry_price: float | None = None,
    trigger_time_utc: datetime | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> Candidate:
    return Candidate(
        variant=variant,
        detected=detected,
        entry_time_utc=entry_time_utc,
        entry_price=entry_price,
        trigger_time_utc=trigger_time_utc,
        diagnostics={} if diagnostics is None else diagnostics,
    )


def _detect_first_directional(
    direction: str,
    window: list[tuple[datetime, datetime, Bar]],
) -> Candidate:
    for _, close_time, bar in window:
        aligned = (
            bar.close_price > bar.open_price
            if direction == "LONG"
            else bar.close_price < bar.open_price
        )
        if aligned:
            return _candidate(
                "M5_FIRST_DIRECTIONAL_BODY_CLOSE",
                True,
                entry_time_utc=close_time,
                entry_price=bar.close_price,
                trigger_time_utc=close_time,
                diagnostics={"trigger": "first post-alert directional M5 body close"},
            )
    return _candidate(
        "M5_FIRST_DIRECTIONAL_BODY_CLOSE",
        False,
        diagnostics={"reason": "no directional M5 body closed before source exit"},
    )


def _two_bar_break(
    direction: str,
    window: list[tuple[datetime, datetime, Bar]],
    *,
    require_pullback: bool,
    source_price: float,
) -> Candidate:
    variant = (
        "M5_PULLBACK_THEN_TWO_BAR_BREAK_CLOSE"
        if require_pullback
        else "M5_TWO_BAR_BREAK_CLOSE"
    )
    pullback_seen = False
    for index, (_, close_time, bar) in enumerate(window):
        if direction == "LONG" and bar.close_price < source_price:
            pullback_seen = True
        elif direction == "SHORT" and bar.close_price > source_price:
            pullback_seen = True
        if index < 2:
            continue
        previous = [window[index - 2][2], window[index - 1][2]]
        broken = (
            bar.close_price > max(item.high_price for item in previous)
            if direction == "LONG"
            else bar.close_price < min(item.low_price for item in previous)
        )
        if broken and (pullback_seen or not require_pullback):
            return _candidate(
                variant,
                True,
                entry_time_utc=close_time,
                entry_price=bar.close_price,
                trigger_time_utc=close_time,
                diagnostics={
                    "trigger": "M5 close beyond previous two completed bars",
                    "pullback_required": require_pullback,
                    "pullback_seen": pullback_seen,
                },
            )
    return _candidate(
        variant,
        False,
        diagnostics={
            "reason": "trigger not completed before source exit",
            "pullback_required": require_pullback,
            "pullback_seen": pullback_seen,
        },
    )


def _confirmed_pivots(
    direction: str,
    window: list[tuple[datetime, datetime, Bar]],
) -> list[dict[str, Any]]:
    pivots: list[dict[str, Any]] = []
    for pivot_index in range(PIVOT_LEFT, len(window) - PIVOT_RIGHT):
        bar = window[pivot_index][2]
        left = [window[i][2] for i in range(pivot_index - PIVOT_LEFT, pivot_index)]
        right = [
            window[i][2]
            for i in range(pivot_index + 1, pivot_index + PIVOT_RIGHT + 1)
        ]
        if direction == "LONG":
            is_pivot = all(bar.low_price <= item.low_price for item in left + right)
            price = bar.low_price
            pivot_type = "LOW"
        else:
            is_pivot = all(bar.high_price >= item.high_price for item in left + right)
            price = bar.high_price
            pivot_type = "HIGH"
        if not is_pivot:
            continue
        confirmation_index = pivot_index + PIVOT_RIGHT
        pivots.append(
            {
                "pivot_index": pivot_index,
                "confirmation_index": confirmation_index,
                "pivot_price": price,
                "pivot_type": pivot_type,
                "pivot_time_utc": iso_z(window[pivot_index][0]),
                "confirmation_time_utc": iso_z(window[confirmation_index][1]),
            }
        )
    return pivots


def _detect_second_bottom_top(
    direction: str,
    window: list[tuple[datetime, datetime, Bar]],
) -> Candidate:
    variant = "M5_SECOND_BOTTOM_TOP_BREAK_CLOSE"
    pivots = _confirmed_pivots(direction, window)
    for first_index in range(len(pivots)):
        first = pivots[first_index]
        for second_index in range(first_index + 1, len(pivots)):
            second = pivots[second_index]
            structurally_valid = (
                second["pivot_price"] >= first["pivot_price"]
                if direction == "LONG"
                else second["pivot_price"] <= first["pivot_price"]
            )
            if not structurally_valid:
                continue
            left_index = int(first["pivot_index"])
            right_index = int(second["pivot_index"])
            if right_index - left_index < 2:
                continue
            between = [window[i][2] for i in range(left_index, right_index + 1)]
            neckline = (
                max(item.high_price for item in between)
                if direction == "LONG"
                else min(item.low_price for item in between)
            )
            start = int(second["confirmation_index"]) + 1
            for trigger_index in range(start, len(window)):
                bar = window[trigger_index][2]
                broken = (
                    bar.close_price > neckline
                    if direction == "LONG"
                    else bar.close_price < neckline
                )
                if not broken:
                    continue
                close_time = window[trigger_index][1]
                return _candidate(
                    variant,
                    True,
                    entry_time_utc=close_time,
                    entry_price=bar.close_price,
                    trigger_time_utc=close_time,
                    diagnostics={
                        "trigger": "second confirmed bottom/top then neckline close break",
                        "pivot_left_bars": PIVOT_LEFT,
                        "pivot_right_confirmation_bars": PIVOT_RIGHT,
                        "first_pivot": first,
                        "second_pivot": second,
                        "neckline": neckline,
                        "second_pivot_rule": (
                            "higher_or_equal_low"
                            if direction == "LONG"
                            else "lower_or_equal_high"
                        ),
                    },
                )
    return _candidate(
        variant,
        False,
        diagnostics={
            "reason": "no causal second-bottom/top neckline break before source exit",
            "pivot_left_bars": PIVOT_LEFT,
            "pivot_right_confirmation_bars": PIVOT_RIGHT,
            "confirmed_pivot_count": len(pivots),
        },
    )


def _reference_candidate(
    entry: SourceEntry,
    m1_opens: list[datetime],
    m1_bars: list[Bar],
    *,
    offset_hours: float,
    analysis_end_utc: datetime,
) -> Candidate:
    source_server_minute = floor_minute(entry.source_entry_time_utc) + timedelta(
        hours=offset_hours
    )
    index = bisect_right(m1_opens, source_server_minute)
    if index >= len(m1_bars):
        return _candidate(
            "SOURCE_NEXT_M1_OPEN_REFERENCE",
            False,
            diagnostics={"reason": "no M1 bar strictly after source event minute"},
        )
    bar = m1_bars[index]
    utc_open = _utc_open(bar, offset_hours)
    if utc_open >= analysis_end_utc:
        return _candidate(
            "SOURCE_NEXT_M1_OPEN_REFERENCE",
            False,
            diagnostics={"reason": "next M1 bar is not before analysis end"},
        )
    return _candidate(
        "SOURCE_NEXT_M1_OPEN_REFERENCE",
        True,
        entry_time_utc=utc_open,
        entry_price=bar.open_price,
        trigger_time_utc=utc_open,
        diagnostics={
            "trigger": "first MT5 M1 open strictly after source event minute",
            "same_source_minute_excluded": True,
        },
    )


def _gap_count(path: list[tuple[datetime, Bar]]) -> int:
    return sum(
        1
        for (previous_time, _), (current_time, _) in zip(path, path[1:])
        if int((current_time - previous_time).total_seconds()) != 60
    )


def _exit_reference(
    m1_opens: list[datetime],
    m1_bars: list[Bar],
    *,
    exit_time_utc: datetime,
    offset_hours: float,
) -> tuple[datetime, float]:
    exit_server_minute = floor_minute(exit_time_utc) + timedelta(hours=offset_hours)
    index = bisect_left(m1_opens, exit_server_minute) - 1
    if index < 0:
        raise EntryTimingContractError("no closed M1 bar before source exit")
    bar = m1_bars[index]
    return _utc_open(bar, offset_hours) + timedelta(minutes=1), bar.close_price


def _measure_outcome(
    entry: SourceEntry,
    candidate: Candidate,
    *,
    atr_m5: float,
    offset_hours: float,
    m1_opens: list[datetime],
    m1_bars: list[Bar],
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    if (
        entry.source_exit_time_utc is None
        or candidate.entry_time_utc is None
        or candidate.entry_price is None
    ):
        raise EntryTimingContractError("resolved timing outcome lacks entry/exit")
    exit_reference_time, exit_reference_price = _exit_reference(
        m1_opens,
        m1_bars,
        exit_time_utc=entry.source_exit_time_utc,
        offset_hours=offset_hours,
    )
    if candidate.entry_time_utc >= exit_reference_time:
        raise EntryTimingContractError(
            f"candidate {candidate.variant} occurs at/after exit reference"
        )

    entry_server = candidate.entry_time_utc + timedelta(hours=offset_hours)
    exit_server = exit_reference_time + timedelta(hours=offset_hours)
    left = bisect_left(m1_opens, entry_server)
    right = bisect_left(m1_opens, exit_server)
    path: list[tuple[datetime, Bar]] = []
    future_count = 0
    for bar in m1_bars[left:right]:
        utc_open = _utc_open(bar, offset_hours)
        if utc_open < candidate.entry_time_utc or utc_open >= exit_reference_time:
            future_count += 1
            continue
        path.append((utc_open, bar))
    if future_count:
        raise EntryTimingContractError(
            f"future/path boundary violation for {entry.entry_id} {candidate.variant}"
        )

    direction_sign = 1.0 if entry.direction == "LONG" else -1.0
    return_value = direction_sign * (exit_reference_price - candidate.entry_price)
    favorable_value = candidate.entry_price
    adverse_value = candidate.entry_price
    favorable_time = candidate.entry_time_utc
    adverse_time = candidate.entry_time_utc

    for utc_open, bar in path:
        if entry.direction == "LONG":
            if bar.high_price > favorable_value:
                favorable_value = bar.high_price
                favorable_time = utc_open
            if bar.low_price < adverse_value:
                adverse_value = bar.low_price
                adverse_time = utc_open
        else:
            if bar.low_price < favorable_value:
                favorable_value = bar.low_price
                favorable_time = utc_open
            if bar.high_price > adverse_value:
                adverse_value = bar.high_price
                adverse_time = utc_open

    if entry.direction == "LONG":
        mfe = favorable_value - candidate.entry_price
        mae = candidate.entry_price - adverse_value
    else:
        mfe = candidate.entry_price - favorable_value
        mae = adverse_value - candidate.entry_price
    mfe = max(0.0, mfe)
    mae = max(0.0, mae)

    return_atr = return_value / atr_m5
    mfe_atr = mfe / atr_m5
    mae_atr = mae / atr_m5
    if favorable_time < adverse_time:
        first = "FAVORABLE_FIRST"
    elif adverse_time < favorable_time:
        first = "ADVERSE_FIRST"
    else:
        first = "SAME_TIME"
    expansion = "EXPANDED_1ATR" if mfe_atr >= 1.0 else "NO_1ATR_EXPANSION"
    positive = int(return_atr > 0.0)
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "price_basis": "MT5_ONLY_FOR_VARIANT_COMPARISON",
        "source_event_same_minute_excluded_for_reference": True,
        "candidate_entry_basis": (
            "NEXT_M1_OPEN"
            if candidate.variant == "SOURCE_NEXT_M1_OPEN_REFERENCE"
            else "CLOSED_M5_TRIGGER_BAR_CLOSE"
        ),
        "exit_reference_basis": "LAST_FULLY_CLOSED_M1_CLOSE_BEFORE_SOURCE_EXIT_MINUTE",
        "source_exit_time_utc": iso_z(entry.source_exit_time_utc),
        "mt5_exit_reference_time_utc": iso_z(exit_reference_time),
        "entry_time_utc": iso_z(candidate.entry_time_utc),
        "post_entry_data_used_for_outcome_measurement": True,
        "future_data_used_for_entry_trigger": False,
        "fixed_tp_sl_applied": False,
        "entry_gate_enabled": False,
        "approved_for_trading": False,
    }
    summary = {
        "source_entry_id": entry.entry_id,
        "variant": candidate.variant,
        "ticker": entry.ticker,
        "direction": entry.direction,
        "entry_role": entry.entry_role,
        "return_atr_m5": return_atr,
        "mfe_atr_m5": mfe_atr,
        "mae_atr_m5": mae_atr,
        "entry_delay_seconds": (
            candidate.entry_time_utc - entry.source_entry_time_utc
        ).total_seconds(),
        "positive_exit": positive,
        "expansion_count": int(mfe_atr >= 1.0),
    }
    row = (
        entry.entry_id,
        candidate.variant,
        iso_z(entry.source_exit_time_utc),
        iso_z(exit_reference_time),
        exit_reference_price,
        return_value,
        return_atr,
        mfe,
        mae,
        mfe_atr,
        mae_atr,
        len(path),
        _gap_count(path),
        (favorable_time - candidate.entry_time_utc).total_seconds(),
        (adverse_time - candidate.entry_time_utc).total_seconds(),
        first,
        expansion,
        positive,
        0,
        json.dumps(
            diagnostics,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    return summary, row


def _sample_status(count: int) -> str:
    if count < 5:
        return "VERY_SMALL_SAMPLE"
    if count < 20:
        return "SMALL_SAMPLE"
    if count < 50:
        return "OBSERVATION_SAMPLE"
    return "RULE_DESIGN_SAMPLE"


def _mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def _cohorts(
    candidate_summaries: list[dict[str, Any]],
    outcome_summaries: list[dict[str, Any]],
    *,
    built_at_utc: str,
) -> tuple[list[dict[str, Any]], list[tuple[Any, ...]]]:
    outcome_by_key = {
        (item["source_entry_id"], item["variant"]): item
        for item in outcome_summaries
    }
    reference_by_source = {
        item["source_entry_id"]: item
        for item in outcome_summaries
        if item["variant"] == "SOURCE_NEXT_M1_OPEN_REFERENCE"
    }
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidate_summaries:
        enriched = dict(candidate)
        enriched["outcome"] = outcome_by_key.get(
            (candidate["source_entry_id"], candidate["variant"])
        )
        dimensions = {
            "variant": candidate["variant"],
            "ticker_variant": f"{candidate['ticker']}|{candidate['variant']}",
            "direction_variant": f"{candidate['direction']}|{candidate['variant']}",
            "entry_role_variant": f"{candidate['entry_role']}|{candidate['variant']}",
        }
        for dimension, value in dimensions.items():
            grouped[(dimension, value)].append(enriched)

    output: list[dict[str, Any]] = []
    rows: list[tuple[Any, ...]] = []
    for key in sorted(grouped):
        items = grouped[key]
        detected = [item for item in items if item["detected"]]
        outcomes = [item["outcome"] for item in detected if item["outcome"] is not None]
        positive = sum(int(item["positive_exit"]) for item in outcomes)
        expansions = sum(int(item["expansion_count"]) for item in outcomes)
        delta_returns: list[float] = []
        delta_maes: list[float] = []
        for outcome in outcomes:
            reference = reference_by_source.get(outcome["source_entry_id"])
            if reference is None:
                continue
            delta_returns.append(
                float(outcome["return_atr_m5"]) - float(reference["return_atr_m5"])
            )
            delta_maes.append(
                float(outcome["mae_atr_m5"]) - float(reference["mae_atr_m5"])
            )
        delays = [
            float(item["entry_delay_seconds"])
            for item in detected
            if item["entry_delay_seconds"] is not None
        ]
        improvements = [
            float(item["price_improvement_atr_m5"])
            for item in detected
            if item["price_improvement_atr_m5"] is not None
        ]
        resolved_count = len(outcomes)
        record = {
            "dimension": key[0],
            "dimension_value": key[1],
            "resolved_count": resolved_count,
            "detected_count": len(detected),
            "missed_count": len(items) - len(detected),
            "positive_exit_count": positive,
            "expansion_count": expansions,
            "positive_exit_ratio": (
                None if resolved_count == 0 else positive / resolved_count
            ),
            "expansion_ratio": (
                None if resolved_count == 0 else expansions / resolved_count
            ),
            "mean_return_atr_m5": _mean(
                [float(item["return_atr_m5"]) for item in outcomes]
            ),
            "mean_mfe_atr_m5": _mean(
                [float(item["mfe_atr_m5"]) for item in outcomes]
            ),
            "mean_mae_atr_m5": _mean(
                [float(item["mae_atr_m5"]) for item in outcomes]
            ),
            "mean_entry_delay_seconds": _mean(delays),
            "mean_price_improvement_atr_m5": _mean(improvements),
            "mean_delta_return_vs_reference_atr_m5": _mean(delta_returns),
            "mean_delta_mae_vs_reference_atr_m5": _mean(delta_maes),
            "sample_status": _sample_status(resolved_count),
        }
        output.append(record)
        rows.append(
            (
                record["dimension"],
                record["dimension_value"],
                record["resolved_count"],
                record["detected_count"],
                record["missed_count"],
                record["positive_exit_count"],
                record["expansion_count"],
                record["positive_exit_ratio"],
                record["expansion_ratio"],
                record["mean_return_atr_m5"],
                record["mean_mfe_atr_m5"],
                record["mean_mae_atr_m5"],
                record["mean_entry_delay_seconds"],
                record["mean_price_improvement_atr_m5"],
                record["mean_delta_return_vs_reference_atr_m5"],
                record["mean_delta_mae_vs_reference_atr_m5"],
                record["sample_status"],
                built_at_utc,
            )
        )
    return output, rows


def rebuild_m5_entry_timing_audit(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    ensure_schema(connection)
    entries = _read_source_entries(connection)
    upstream = _validate_upstream(connection, entries)

    cache: dict[str, dict[str, Any]] = {}
    for ticker in sorted({entry.ticker for entry in entries}):
        m1_name = FILE_MAP[ticker]["M1"]
        m5_name = FILE_MAP[ticker]["M5"]
        m1_opens, m1_bars = load_bars(mt5_files_root / m1_name)
        m5_opens, m5_bars = load_bars(mt5_files_root / m5_name)
        cache[ticker] = {
            "m1_name": m1_name,
            "m1_opens": m1_opens,
            "m1_bars": m1_bars,
            "m5_name": m5_name,
            "m5_opens": m5_opens,
            "m5_bars": m5_bars,
        }

    candidate_rows: list[tuple[Any, ...]] = []
    candidate_summaries: list[dict[str, Any]] = []
    outcome_rows: list[tuple[Any, ...]] = []
    outcome_summaries: list[dict[str, Any]] = []

    for entry in entries:
        data = cache[entry.ticker]
        offset_hours = _offset(connection, entry.source_entry_alert_id)
        atr_m5 = _atr_m5(connection, entry.source_entry_alert_id)

        if entry.episode_status == "CLOSED":
            assert entry.source_exit_time_utc is not None
            analysis_end = entry.source_exit_time_utc
        else:
            latest_m5 = data["m5_bars"][-1]
            analysis_end = (
                _utc_open(latest_m5, offset_hours)
                + timedelta(minutes=5, seconds=1)
            )

        window = _m5_window(
            data["m5_opens"],
            data["m5_bars"],
            source_time_utc=entry.source_entry_time_utc,
            end_time_utc=analysis_end,
            offset_hours=offset_hours,
        )
        reference = _reference_candidate(
            entry,
            data["m1_opens"],
            data["m1_bars"],
            offset_hours=offset_hours,
            analysis_end_utc=analysis_end,
        )
        if not reference.detected or reference.entry_price is None:
            raise EntryTimingContractError(
                f"MT5 reference entry is unavailable for {entry.entry_id}"
            )
        comparison_reference_price = reference.entry_price
        candidates = [
            reference,
            _detect_first_directional(entry.direction, window),
            _two_bar_break(
                entry.direction,
                window,
                require_pullback=False,
                source_price=comparison_reference_price,
            ),
            _two_bar_break(
                entry.direction,
                window,
                require_pullback=True,
                source_price=comparison_reference_price,
            ),
            _detect_second_bottom_top(entry.direction, window),
        ]
        if tuple(candidate.variant for candidate in candidates) != VARIANTS:
            raise EntryTimingContractError("variant order/coverage changed")

        for candidate in candidates:
            entry_delay = (
                None
                if candidate.entry_time_utc is None
                else (
                    candidate.entry_time_utc - entry.source_entry_time_utc
                ).total_seconds()
            )
            improvement = None
            if candidate.entry_price is not None:
                improvement = (
                    (comparison_reference_price - candidate.entry_price) / atr_m5
                    if entry.direction == "LONG"
                    else (candidate.entry_price - comparison_reference_price) / atr_m5
                )
            diagnostics = {
                "contract_version": CONTRACT_VERSION,
                "source_entry_event_identity": "WEBHOOK_SQLITE_SOURCE_EVENT_ID",
                "chart_label_redraw_required": False,
                "source_entry_alert_id": entry.source_entry_alert_id,
                "source_entry_time_utc": iso_z(entry.source_entry_time_utc),
                "source_tradingview_price_reference": entry.source_entry_price,
                "mt5_reference_entry_price": comparison_reference_price,
                "analysis_end_utc": iso_z(analysis_end),
                "m1_csv": data["m1_name"],
                "m5_csv": data["m5_name"],
                "selected_offset_hours": offset_hours,
                "closed_m5_bars_scanned": len(window),
                "closed_bars_only": True,
                "future_relative_to_candidate_entry_used": False,
                "outcome_used_for_candidate_detection": False,
                "thresholds_optimized_on_current_sample": False,
                "approved_for_trading": False,
                **candidate.diagnostics,
            }
            candidate_rows.append(
                (
                    entry.entry_id,
                    candidate.variant,
                    CONTRACT_VERSION,
                    entry.source_entry_alert_id,
                    entry.episode_id,
                    entry.ticker,
                    entry.direction,
                    entry.entry_role,
                    iso_z(entry.source_entry_time_utc),
                    entry.source_entry_price,
                    int(candidate.detected),
                    None
                    if candidate.entry_time_utc is None
                    else iso_z(candidate.entry_time_utc),
                    candidate.entry_price,
                    None
                    if candidate.trigger_time_utc is None
                    else iso_z(candidate.trigger_time_utc),
                    entry_delay,
                    improvement,
                    json.dumps(
                        diagnostics,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    0,
                    0,
                )
            )
            candidate_summary = {
                "source_entry_id": entry.entry_id,
                "source_entry_alert_id": entry.source_entry_alert_id,
                "ticker": entry.ticker,
                "direction": entry.direction,
                "entry_role": entry.entry_role,
                "variant": candidate.variant,
                "detected": candidate.detected,
                "candidate_entry_time_utc": (
                    None
                    if candidate.entry_time_utc is None
                    else iso_z(candidate.entry_time_utc)
                ),
                "candidate_entry_price": candidate.entry_price,
                "entry_delay_seconds": entry_delay,
                "price_improvement_atr_m5": improvement,
                "episode_status": entry.episode_status,
            }
            candidate_summaries.append(candidate_summary)

            if entry.episode_status != "CLOSED" or not candidate.detected:
                continue
            summary, outcome_row = _measure_outcome(
                entry,
                candidate,
                atr_m5=atr_m5,
                offset_hours=offset_hours,
                m1_opens=data["m1_opens"],
                m1_bars=data["m1_bars"],
            )
            outcome_summaries.append(summary)
            outcome_rows.append(outcome_row)

    expected_candidate_rows = len(entries) * len(VARIANTS)
    if len(candidate_rows) != expected_candidate_rows:
        raise EntryTimingContractError(
            f"candidate row count changed: {len(candidate_rows)} != {expected_candidate_rows}"
        )

    current_entries = _read_source_entries(connection)
    _validate_upstream(connection, current_entries)
    if [entry.entry_id for entry in current_entries] != [entry.entry_id for entry in entries]:
        raise EntryTimingContractError(
            "source entry set changed during M6C build; rerun M6C"
        )

    cohorts, cohort_rows = _cohorts(
        candidate_summaries,
        outcome_summaries,
        built_at_utc=built_at_utc,
    )

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DELETE FROM m5_entry_timing_cohorts")
        connection.execute("DELETE FROM m5_entry_timing_outcomes")
        connection.execute("DELETE FROM m5_entry_timing_candidates")
        connection.executemany(
            """
            INSERT INTO m5_entry_timing_candidates (
                source_entry_id, variant, contract_version,
                source_entry_alert_id, episode_id, ticker, direction, entry_role,
                source_entry_time_utc, source_entry_price,
                candidate_detected, candidate_entry_time_utc,
                candidate_entry_price, trigger_time_utc,
                entry_delay_seconds, price_improvement_atr_m5,
                diagnostics_json, future_entry_fields_used, approved_for_trading
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            candidate_rows,
        )
        connection.executemany(
            """
            INSERT INTO m5_entry_timing_outcomes (
                source_entry_id, variant, source_exit_time_utc,
                mt5_exit_reference_time_utc, mt5_exit_reference_price,
                return_price_units, return_atr_m5,
                mfe_price_units, mae_price_units, mfe_atr_m5, mae_atr_m5,
                path_bar_count, path_gap_count,
                time_to_mfe_seconds, time_to_mae_seconds,
                favorable_first_status, expansion_class, positive_exit,
                future_path_violation_count, diagnostics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            outcome_rows,
        )
        connection.executemany(
            """
            INSERT INTO m5_entry_timing_cohorts (
                dimension, dimension_value,
                resolved_count, detected_count, missed_count,
                positive_exit_count, expansion_count,
                positive_exit_ratio, expansion_ratio,
                mean_return_atr_m5, mean_mfe_atr_m5, mean_mae_atr_m5,
                mean_entry_delay_seconds, mean_price_improvement_atr_m5,
                mean_delta_return_vs_reference_atr_m5,
                mean_delta_mae_vs_reference_atr_m5,
                sample_status, generated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            cohort_rows,
        )
        connection.execute(
            """
            INSERT INTO m5_entry_timing_build_runs (
                built_at_utc, contract_version,
                source_entry_count, closed_source_entry_count, open_source_entry_count,
                candidate_row_count, detected_candidate_count,
                outcome_row_count, cohort_row_count,
                future_entry_violation_count, future_path_violation_count,
                approved_for_trading, audit_only
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 1)
            """,
            (
                built_at_utc,
                CONTRACT_VERSION,
                upstream["source_entry_count"],
                upstream["closed_source_entry_count"],
                upstream["open_source_entry_count"],
                len(candidate_rows),
                sum(1 for item in candidate_summaries if item["detected"]),
                len(outcome_rows),
                len(cohort_rows),
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    variant_summary = [
        row for row in cohorts if row["dimension"] == "variant"
    ]
    ticker_variant_summary = [
        row for row in cohorts if row["dimension"] == "ticker_variant"
    ]
    direction_variant_summary = [
        row for row in cohorts if row["dimension"] == "direction_variant"
    ]
    entry_role_variant_summary = [
        row for row in cohorts if row["dimension"] == "entry_role_variant"
    ]
    open_candidates = [
        item for item in candidate_summaries if item["episode_status"] == "OPEN"
    ]
    missed_candidates = [
        item
        for item in candidate_summaries
        if not item["detected"] and item["episode_status"] == "CLOSED"
    ]
    return {
        "contract_version": CONTRACT_VERSION,
        **upstream,
        "variant_count": len(VARIANTS),
        "variants": list(VARIANTS),
        "candidate_row_count": len(candidate_rows),
        "detected_candidate_count": sum(
            1 for item in candidate_summaries if item["detected"]
        ),
        "missed_candidate_count": sum(
            1 for item in candidate_summaries if not item["detected"]
        ),
        "outcome_row_count": len(outcome_rows),
        "cohort_row_count": len(cohort_rows),
        "future_entry_violation_count": 0,
        "future_path_violation_count": 0,
        "variant_summary": variant_summary,
        "ticker_variant_summary": ticker_variant_summary,
        "direction_variant_summary": direction_variant_summary,
        "entry_role_variant_summary": entry_role_variant_summary,
        "closed_missed_candidates": missed_candidates,
        "open_source_candidates": open_candidates,
        "price_basis_contract": {
            "variant_comparison": "MT5_ONLY",
            "reference_entry": "first M1 open strictly after source event minute",
            "m5_candidate_entry": "closed trigger M5 bar close",
            "exit_reference": "last fully closed M1 close before source EXIT minute",
            "reason": (
                "Avoid mixing TradingView source prices with MT5 delayed-entry prices "
                "inside the paired entry-timing comparison."
            ),
        },
        "candidate_detection_uses_outcomes": False,
        "thresholds_optimized_on_current_sample": False,
        "approved_for_trading": False,
    }
