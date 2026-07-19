from __future__ import annotations

import csv
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "mochipoyo_alert_research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mt5_alignment_builder import (  # noqa: E402
    AlignmentContractError,
    build_mt5_closed_bar_alignment,
)
from mt5_csv_contract import EXPECTED_HEADER, FILE_MAP  # noqa: E402


def write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPECTED_HEADER)
        for timestamp, price in rows:
            writer.writerow(
                [timestamp, price, price, price, price, 1, 0, 0]
            )


def make_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL,
            event TEXT NOT NULL,
            fired_at_utc TEXT NOT NULL,
            bar_time_utc TEXT NOT NULL,
            close_price REAL
        );
        CREATE TABLE raw_alert_annotations (
            raw_alert_id INTEGER PRIMARY KEY,
            annotation_type TEXT NOT NULL
        );
        CREATE TABLE mt5_alignment (
            raw_alert_id INTEGER NOT NULL,
            timeframe TEXT NOT NULL,
            tv_event_time_utc TEXT NOT NULL,
            mt5_server_time TEXT,
            estimated_mt5_time_utc TEXT,
            selected_offset_hours REAL,
            time_diff_seconds REAL,
            tv_close_price REAL,
            mt5_close_price REAL,
            price_diff REAL,
            alignment_status TEXT NOT NULL,
            diagnostics_json TEXT NOT NULL,
            PRIMARY KEY (raw_alert_id, timeframe)
        );
        """
    )
    return connection


def create_fixture_csvs(root: Path) -> None:
    timeframe_seconds = {
        "M5": 300,
        "M15": 900,
        "H1": 3600,
        "H4": 14400,
        "D1": 86400,
    }
    for ticker, files in FILE_MAP.items():
        for timeframe, filename in files.items():
            rows: list[tuple[str, float]] = []
            if timeframe == "M1":
                if ticker == "XAUUSD":
                    for index in range(5):
                        utc_time = datetime(2026, 7, 15, 9 + index, 7)
                        server_time = utc_time + timedelta(hours=3)
                        rows.append(
                            (
                                server_time.strftime("%Y.%m.%d %H:%M:%S"),
                                100.0 + index,
                            )
                        )
                else:
                    rows.append(("2026.07.15 12:00:00", 500.0))
            else:
                current = datetime(2026, 7, 14, 0, 0)
                end = datetime(2026, 7, 15, 18, 0)
                while current <= end:
                    rows.append(
                        (current.strftime("%Y.%m.%d %H:%M:%S"), 200.0)
                    )
                    current += timedelta(seconds=timeframe_seconds[timeframe])
            write_csv(root / filename, rows)


def insert_five_xauusd_alerts(connection: sqlite3.Connection) -> None:
    for index in range(5):
        utc_time = datetime(2026, 7, 15, 9 + index, 7)
        timestamp = utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        connection.execute(
            """
            INSERT INTO raw_alerts (
                cloudflare_id, ticker, event, fired_at_utc,
                bar_time_utc, close_price
            ) VALUES (?, 'XAUUSD', 'LONG', ?, ?, ?)
            """,
            (index + 1, timestamp, timestamp, 100.0 + index),
        )
    connection.commit()


def test_alignment_selects_latest_closed_bar_without_future_leak(
    tmp_path: Path,
) -> None:
    create_fixture_csvs(tmp_path)
    connection = make_database(tmp_path / "alignment.sqlite3")
    insert_five_xauusd_alerts(connection)

    result = build_mt5_closed_bar_alignment(
        connection,
        mt5_files_root=tmp_path,
        built_at_utc="2026-07-19T00:00:00Z",
    )

    assert result["selected_offset"]["offset_hours"] == 3
    assert result["aligned_count"] == 25
    assert result["future_bar_selection_count"] == 0

    m5 = connection.execute(
        """
        SELECT *
        FROM mt5_alignment
        WHERE raw_alert_id = 1 AND timeframe = 'M5'
        """
    ).fetchone()
    assert m5["estimated_mt5_time_utc"] == "2026-07-15T09:05:00Z"
    assert m5["time_diff_seconds"] == 120.0

    h4_diagnostics = connection.execute(
        """
        SELECT diagnostics_json
        FROM mt5_alignment
        WHERE raw_alert_id = 1 AND timeframe = 'H4'
        """
    ).fetchone()[0]
    assert '"same_printed_hour_join_used":false' in h4_diagnostics
    assert '"usage":"AUDIT_CONTEXT_ONLY"' in h4_diagnostics
    connection.close()


def test_failure_preserves_previous_alignment(tmp_path: Path) -> None:
    create_fixture_csvs(tmp_path)
    connection = make_database(tmp_path / "preserve.sqlite3")
    insert_five_xauusd_alerts(connection)
    connection.execute(
        """
        INSERT INTO mt5_alignment (
            raw_alert_id, timeframe, tv_event_time_utc, mt5_server_time,
            estimated_mt5_time_utc, selected_offset_hours,
            time_diff_seconds, tv_close_price, mt5_close_price,
            price_diff, alignment_status, diagnostics_json
        ) VALUES (
            999, 'M5', '2026-01-01T00:00:00Z', NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, 'PREVIOUS', '{}'
        )
        """
    )
    connection.commit()

    write_csv(tmp_path / FILE_MAP["XAUUSD"]["H4"], [])
    try:
        build_mt5_closed_bar_alignment(
            connection,
            mt5_files_root=tmp_path,
            built_at_utc="2026-07-19T00:00:00Z",
        )
        raise AssertionError("expected AlignmentContractError")
    except AlignmentContractError:
        pass

    preserved = connection.execute(
        "SELECT alignment_status FROM mt5_alignment WHERE raw_alert_id = 999"
    ).fetchone()
    assert preserved[0] == "PREVIOUS"
    connection.close()
