from __future__ import annotations

import csv
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "mochipoyo_alert_research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alert_entry_timing_builder import (  # noqa: E402
    Bar,
    EntryTimingContractError,
    _detect_first_directional,
    _detect_second_bottom_top,
    _two_bar_break,
    rebuild_m5_entry_timing_audit,
)
from mt5_csv_contract import EXPECTED_HEADER  # noqa: E402


def _window(rows: list[tuple[float, float, float, float]]):
    base = datetime(2026, 7, 15, 9, 45)
    result = []
    for index, (open_price, high, low, close) in enumerate(rows):
        utc_open = base + timedelta(minutes=5 * index)
        result.append(
            (
                utc_open,
                utc_open + timedelta(minutes=5),
                Bar(utc_open + timedelta(hours=3), open_price, high, low, close),
            )
        )
    return result


def test_closed_m5_triggers_are_directional_and_causal() -> None:
    window = _window(
        [
            (100.0, 100.2, 99.0, 99.2),
            (99.2, 99.8, 99.0, 99.6),
            (99.6, 101.2, 99.5, 101.0),
        ]
    )
    first = _detect_first_directional("LONG", window)
    assert first.detected is True
    assert first.entry_time_utc == window[1][1]

    plain = _two_bar_break(
        "LONG", window, require_pullback=False, source_price=100.0
    )
    pullback = _two_bar_break(
        "LONG", window, require_pullback=True, source_price=100.0
    )
    assert plain.detected is True
    assert pullback.detected is True
    assert plain.entry_time_utc == window[2][1]
    assert pullback.entry_time_utc == window[2][1]


def test_second_bottom_requires_confirmed_pivots_and_neckline_break() -> None:
    rows = [
        (100.0, 100.5, 99.8, 100.1),
        (100.1, 100.2, 99.0, 99.3),
        (99.3, 100.0, 99.2, 99.8),
        (99.8, 100.4, 99.5, 100.1),
        (100.1, 100.2, 99.3, 99.5),
        (99.5, 100.1, 99.4, 99.9),
        (99.9, 100.3, 99.7, 100.0),
        (100.0, 100.8, 99.9, 100.6),
    ]
    candidate = _detect_second_bottom_top("LONG", _window(rows))
    assert candidate.detected is True
    assert candidate.entry_time_utc == _window(rows)[7][1]
    assert candidate.diagnostics["second_pivot_rule"] == "higher_or_equal_low"


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPECTED_HEADER)
        writer.writerows(rows)


def _make_csvs(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 7, 15, 12, 40)
    m1_rows: list[list[object]] = []
    previous_close = 100.0
    for index in range(56):
        server_open = start + timedelta(minutes=index)
        if index < 10:
            close = 100.0 - 0.05 * index
        elif index < 25:
            close = 99.5 + 0.12 * (index - 10)
        else:
            close = 101.3 + 0.02 * (index - 25)
        high = max(previous_close, close) + 0.05
        low = min(previous_close, close) - 0.05
        m1_rows.append(
            [
                server_open.strftime("%Y.%m.%d %H:%M:%S"),
                previous_close,
                high,
                low,
                close,
                100,
                0,
                0,
            ]
        )
        previous_close = close
    _write_csv(root / "goldsharp_m1.csv", m1_rows)

    m5_rows: list[list[object]] = []
    for start_index in range(0, 55, 5):
        group = m1_rows[start_index : start_index + 5]
        m5_rows.append(
            [
                group[0][0],
                group[0][1],
                max(float(row[2]) for row in group),
                min(float(row[3]) for row in group),
                group[-1][4],
                500,
                0,
                0,
            ]
        )
    _write_csv(root / "goldsharp_m5.csv", m5_rows)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY,
            fired_at_utc TEXT,
            close_price REAL
        );
        CREATE TABLE episodes (
            episode_id TEXT PRIMARY KEY,
            ticker TEXT,
            direction TEXT,
            episode_status TEXT,
            exit_alert_id INTEGER,
            primary_alert_id INTEGER
        );
        CREATE TABLE episode_events (
            episode_id TEXT,
            raw_alert_id INTEGER,
            event_role TEXT,
            reentry_index INTEGER,
            PRIMARY KEY (episode_id, raw_alert_id)
        );
        CREATE TABLE virtual_entries (
            entry_id TEXT PRIMARY KEY,
            episode_id TEXT,
            entry_type TEXT,
            entry_index INTEGER,
            entry_time_utc TEXT,
            entry_price REAL,
            status TEXT
        );
        CREATE TABLE outcome_path_metrics (
            entry_id TEXT PRIMARY KEY
        );
        CREATE TABLE feature_snapshots (
            source_event_id INTEGER,
            timeframe TEXT,
            features_json TEXT,
            future_fields_present INTEGER
        );
        CREATE TABLE mt5_alignment (
            raw_alert_id INTEGER,
            timeframe TEXT,
            selected_offset_hours REAL,
            alignment_status TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO raw_alerts VALUES (10, '2026-07-15T09:45:00Z', 100.0)"
    )
    connection.execute(
        "INSERT INTO raw_alerts VALUES (11, '2026-07-15T10:30:00Z', 102.0)"
    )
    connection.execute(
        """
        INSERT INTO episodes VALUES (
            'XAUUSD:LONG:10', 'XAUUSD', 'LONG', 'CLOSED', 11, 10
        )
        """
    )
    connection.execute(
        """
        INSERT INTO episode_events VALUES (
            'XAUUSD:LONG:10', 10, 'PRIMARY_ALERT', NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO virtual_entries VALUES (
            'M6A:XAUUSD:LONG:10:PRIMARY:10',
            'XAUUSD:LONG:10',
            'SOURCE_PRIMARY_ALERT_IMMEDIATE',
            0,
            '2026-07-15T09:45:00Z',
            100.0,
            'RESOLVED_SOURCE_EXIT'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO outcome_path_metrics VALUES (
            'M6A:XAUUSD:LONG:10:PRIMARY:10'
        )
        """
    )
    payload = json.dumps({"volatility": {"atr14": 1.0}})
    for timeframe in ("M5", "M15", "H1", "H4", "D1"):
        connection.execute(
            "INSERT INTO feature_snapshots VALUES (10, ?, ?, 0)",
            (timeframe, payload),
        )
    connection.execute(
        """
        INSERT INTO mt5_alignment VALUES (
            10, 'M5', 3.0, 'ALIGNED_CLOSED_BAR'
        )
        """
    )
    connection.commit()
    return connection


def test_integrated_m6c_rebuild_and_stale_guard(tmp_path: Path) -> None:
    _make_csvs(tmp_path)
    connection = _connection()
    result = rebuild_m5_entry_timing_audit(
        connection,
        mt5_files_root=tmp_path,
        built_at_utc="2026-07-19T00:00:00Z",
    )
    assert result["candidate_row_count"] == 5
    assert result["future_entry_violation_count"] == 0
    assert result["future_path_violation_count"] == 0
    reference = connection.execute(
        """
        SELECT *
        FROM m5_entry_timing_candidates
        WHERE variant = 'SOURCE_NEXT_M1_OPEN_REFERENCE'
        """
    ).fetchone()
    assert reference is not None
    assert reference["candidate_entry_time_utc"] == "2026-07-15T09:46:00Z"
    assert reference["approved_for_trading"] == 0

    previous_count = connection.execute(
        "SELECT COUNT(*) FROM m5_entry_timing_candidates"
    ).fetchone()[0]

    connection.execute(
        "INSERT INTO raw_alerts VALUES (12, '2026-07-15T11:00:00Z', 103.0)"
    )
    connection.execute(
        """
        INSERT INTO episode_events VALUES (
            'XAUUSD:LONG:10', 12, 'REENTRY_ALERT', 1
        )
        """
    )
    connection.commit()
    try:
        rebuild_m5_entry_timing_audit(
            connection,
            mt5_files_root=tmp_path,
            built_at_utc="2026-07-19T01:00:00Z",
        )
    except EntryTimingContractError:
        pass
    else:
        raise AssertionError("stale M6A coverage should fail closed")

    assert (
        connection.execute(
            "SELECT COUNT(*) FROM m5_entry_timing_candidates"
        ).fetchone()[0]
        == previous_count
    )
