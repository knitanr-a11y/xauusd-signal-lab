from __future__ import annotations

import csv
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "mochipoyo_alert_research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from db import open_database  # noqa: E402
from source_outcome_builder import (  # noqa: E402
    OutcomeContractError,
    rebuild_source_outcomes,
)

SCHEMA = SCRIPT_DIR / "schema.sql"
TIMEFRAMES = ("M5", "M15", "H1", "H4", "D1")
HEADER = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
]


def insert_raw_alert(
    connection: sqlite3.Connection,
    *,
    raw_id: int,
    ticker: str,
    event: str,
    fired_at_utc: str,
    price: float,
) -> None:
    row_json = json.dumps(
        {
            "id": raw_id,
            "ticker": ticker,
            "event": event,
            "fired_at_utc": fired_at_utc,
            "close_price": price,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    connection.execute(
        """
        INSERT INTO raw_alerts (
            cloudflare_id, event_key, event_key_origin, received_at_utc,
            source, strategy, event, exchange_name, ticker, timeframe,
            bar_time_utc, fired_at_utc, open_price, high_price, low_price,
            close_price, message, worker_raw_json, worker_raw_json_origin,
            collector_source_row_json, payload_sha256, downloaded_at_utc
        ) VALUES (
            ?, ?, 'DERIVED_CLOUDFLARE_ID', ?, 'tradingview', 'mochipoyo',
            ?, 'VANTAGE', ?, '15', ?, ?, ?, ?, ?, ?, ?, ?,
            'COLLECTOR_SOURCE_ROW_FALLBACK', ?, ?, ?
        )
        """,
        (
            raw_id,
            f"cloudflare:{raw_id}",
            fired_at_utc,
            event,
            ticker,
            fired_at_utc,
            fired_at_utc,
            price,
            price,
            price,
            price,
            event,
            row_json,
            row_json,
            f"sha-{raw_id}",
            fired_at_utc,
        ),
    )


def add_stage_m4_m5_coverage(
    connection: sqlite3.Connection,
    *,
    raw_id: int,
    episode_id: str,
) -> None:
    for timeframe in TIMEFRAMES:
        connection.execute(
            """
            INSERT INTO mt5_alignment (
                raw_alert_id, timeframe, tv_event_time_utc,
                mt5_server_time, estimated_mt5_time_utc,
                selected_offset_hours, time_diff_seconds,
                tv_close_price, mt5_close_price, price_diff,
                alignment_status, diagnostics_json
            ) VALUES (?, ?, '2026-07-19T00:00:00Z',
                      '2026.07.19 03:00:00', '2026-07-19T00:00:00Z',
                      3, 0, 1, 1, 0, 'ALIGNED_CLOSED_BAR', '{}')
            """,
            (raw_id, timeframe),
        )
        atr = 2.0 if timeframe == "M5" else 4.0
        feature_json = json.dumps(
            {"volatility": {"atr14": atr}},
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            """
            INSERT INTO feature_snapshots (
                snapshot_id, source_event_id, episode_id,
                snapshot_time_utc, knowledge_cutoff_utc, timeframe,
                latest_closed_bar_time, features_json, future_fields_present
            ) VALUES (?, ?, ?, '2026-07-19T00:00:00Z',
                      '2026-07-19T00:00:00Z', ?,
                      '2026-07-19T00:00:00Z', ?, 0)
            """,
            (f"{raw_id}:{timeframe}", raw_id, episode_id, timeframe, feature_json),
        )


def write_m1(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)


def build_fixture(tmp_path: Path) -> sqlite3.Connection:
    connection = open_database(tmp_path / "test.sqlite3", SCHEMA)

    alerts = [
        (2, "XAUUSD", "LONG", "2026-07-19T00:00:01Z", 100.0),
        (3, "XAUUSD", "LONG", "2026-07-19T00:02:01Z", 102.0),
        (4, "XAUUSD", "LONG_EXIT", "2026-07-19T00:05:00Z", 104.0),
        (5, "BTCUSD", "SHORT", "2026-07-19T01:00:00Z", 200.0),
        (6, "BTCUSD", "SHORT_EXIT", "2026-07-19T01:03:00Z", 195.0),
        (7, "XAUUSD", "LONG", "2026-07-19T02:00:00Z", 110.0),
    ]
    for raw_id, ticker, event, fired_at, price in alerts:
        insert_raw_alert(
            connection,
            raw_id=raw_id,
            ticker=ticker,
            event=event,
            fired_at_utc=fired_at,
            price=price,
        )

    connection.execute(
        """
        INSERT INTO episodes VALUES (
            'XAUUSD:LONG:2', 'XAUUSD', 'LONG', 2,
            '2026-07-19T00:00:01Z', 4, '2026-07-19T00:05:00Z',
            'CLOSED', 0, 0
        )
        """
    )
    connection.execute(
        """
        INSERT INTO episodes VALUES (
            'BTCUSD:SHORT:5', 'BTCUSD', 'SHORT', 5,
            '2026-07-19T01:00:00Z', 6, '2026-07-19T01:03:00Z',
            'CLOSED', 0, 0
        )
        """
    )
    connection.execute(
        """
        INSERT INTO episodes VALUES (
            'XAUUSD:LONG:7', 'XAUUSD', 'LONG', 7,
            '2026-07-19T02:00:00Z', NULL, NULL,
            'OPEN', 1, 0
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO episode_events (
            episode_id, raw_alert_id, event_role, reentry_index
        ) VALUES (?, ?, ?, ?)
        """,
        [
            ("XAUUSD:LONG:2", 2, "PRIMARY_ALERT", None),
            ("XAUUSD:LONG:2", 3, "REENTRY_ALERT", 1),
            ("XAUUSD:LONG:2", 4, "EXIT_ALERT", None),
            ("BTCUSD:SHORT:5", 5, "PRIMARY_ALERT", None),
            ("BTCUSD:SHORT:5", 6, "EXIT_ALERT", None),
            ("XAUUSD:LONG:7", 7, "PRIMARY_ALERT", None),
        ],
    )

    episode_by_raw = {
        2: "XAUUSD:LONG:2",
        3: "XAUUSD:LONG:2",
        4: "XAUUSD:LONG:2",
        5: "BTCUSD:SHORT:5",
        6: "BTCUSD:SHORT:5",
        7: "XAUUSD:LONG:7",
    }
    for raw_id, episode_id in episode_by_raw.items():
        add_stage_m4_m5_coverage(
            connection,
            raw_id=raw_id,
            episode_id=episode_id,
        )
    connection.commit()

    write_m1(
        tmp_path / "goldsharp_m1.csv",
        [
            ["2026.07.19 03:00:00", 100, 100.2, 99.8, 100, 1, 0, 0],
            ["2026.07.19 03:01:00", 100, 101, 99.5, 100.5, 1, 0, 0],
            ["2026.07.19 03:02:00", 101, 103, 100, 102, 1, 0, 0],
            ["2026.07.19 03:03:00", 102, 106, 101, 105, 1, 0, 0],
            ["2026.07.19 03:04:00", 105, 107, 103, 104, 1, 0, 0],
            # The extreme values below are on the EXIT minute and must be excluded.
            ["2026.07.19 03:05:00", 104, 120, 90, 100, 1, 0, 0],
            ["2026.07.19 05:00:00", 110, 111, 109, 110, 1, 0, 0],
        ],
    )
    write_m1(
        tmp_path / "btcusdsharp_m1.csv",
        [
            ["2026.07.19 04:00:00", 200, 201, 199, 200, 1, 0, 0],
            ["2026.07.19 04:01:00", 200, 202, 196, 197, 1, 0, 0],
            ["2026.07.19 04:02:00", 197, 198, 190, 192, 1, 0, 0],
            # This EXIT-minute range must not contaminate SHORT MFE/MAE.
            ["2026.07.19 04:03:00", 195, 220, 180, 200, 1, 0, 0],
        ],
    )
    return connection


def test_source_outcomes_are_causal_and_keep_open_entries_unresolved(
    tmp_path: Path,
) -> None:
    connection = build_fixture(tmp_path)
    try:
        result = rebuild_source_outcomes(
            connection,
            mt5_files_root=tmp_path,
            built_at_utc="2026-07-19T03:00:00Z",
        )
        assert result["episode_count"] == 3
        assert result["closed_episode_count"] == 2
        assert result["open_episode_count"] == 1
        assert result["virtual_entry_count"] == 4
        assert result["resolved_entry_count"] == 3
        assert result["open_entry_count"] == 1
        assert result["future_path_violation_count"] == 0

        metrics = connection.execute(
            """
            SELECT * FROM outcome_path_metrics
            ORDER BY source_entry_alert_id
            """
        ).fetchall()
        assert len(metrics) == 3

        primary_long = metrics[0]
        assert primary_long["source_entry_alert_id"] == 2
        assert primary_long["path_bar_count"] == 4
        assert primary_long["mfe_price_units"] == pytest.approx(7.0)
        assert primary_long["mae_price_units"] == pytest.approx(0.5)

        reentry_long = metrics[1]
        assert reentry_long["source_entry_alert_id"] == 3
        assert reentry_long["path_bar_count"] == 2
        assert reentry_long["mfe_price_units"] == pytest.approx(5.0)
        assert reentry_long["mae_price_units"] == pytest.approx(1.0)

        primary_short = metrics[2]
        assert primary_short["source_entry_alert_id"] == 5
        assert primary_short["mfe_price_units"] == pytest.approx(10.0)
        assert primary_short["mae_price_units"] == pytest.approx(2.0)

        assert connection.execute(
            """
            SELECT COUNT(*) FROM outcomes
            WHERE result_r IS NOT NULL OR result_usd IS NOT NULL
            """
        ).fetchone()[0] == 0
        assert connection.execute(
            """
            SELECT COUNT(*) FROM virtual_entries
            WHERE status = 'OPEN_SOURCE_EPISODE'
            """
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM outcomes"
        ).fetchone()[0] == 3
    finally:
        connection.close()


def test_stale_m5_coverage_fails_before_replacing_previous_outcomes(
    tmp_path: Path,
) -> None:
    connection = build_fixture(tmp_path)
    try:
        rebuild_source_outcomes(
            connection,
            mt5_files_root=tmp_path,
            built_at_utc="2026-07-19T03:00:00Z",
        )
        previous_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT entry_id FROM outcomes ORDER BY entry_id"
            ).fetchall()
        ]

        connection.execute(
            """
            DELETE FROM feature_snapshots
            WHERE source_event_id = 7 AND timeframe = 'D1'
            """
        )
        connection.commit()

        with pytest.raises(OutcomeContractError, match="Stage M5"):
            rebuild_source_outcomes(
                connection,
                mt5_files_root=tmp_path,
                built_at_utc="2026-07-19T04:00:00Z",
            )
        after_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT entry_id FROM outcomes ORDER BY entry_id"
            ).fetchall()
        ]
        assert after_ids == previous_ids
    finally:
        connection.close()


def test_rebuild_is_deterministic_and_preserves_run_history(
    tmp_path: Path,
) -> None:
    connection = build_fixture(tmp_path)
    try:
        first = rebuild_source_outcomes(
            connection,
            mt5_files_root=tmp_path,
            built_at_utc="2026-07-19T03:00:00Z",
        )
        first_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT entry_id FROM virtual_entries ORDER BY entry_id"
            ).fetchall()
        ]
        second = rebuild_source_outcomes(
            connection,
            mt5_files_root=tmp_path,
            built_at_utc="2026-07-19T04:00:00Z",
        )
        second_ids = [
            str(row[0])
            for row in connection.execute(
                "SELECT entry_id FROM virtual_entries ORDER BY entry_id"
            ).fetchall()
        ]
        assert first["virtual_entry_count"] == second["virtual_entry_count"]
        assert first_ids == second_ids
        assert connection.execute(
            "SELECT COUNT(*) FROM source_outcome_build_runs"
        ).fetchone()[0] == 2
    finally:
        connection.close()
