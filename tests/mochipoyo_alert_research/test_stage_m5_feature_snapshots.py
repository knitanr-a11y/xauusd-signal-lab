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

from feature_snapshot_builder import (  # noqa: E402
    FEATURE_TIMEFRAMES,
    rebuild_feature_snapshots,
    rci_value,
)
from mt5_csv_contract import (  # noqa: E402
    EXPECTED_HEADER,
    FILE_MAP,
    TIMEFRAME_SECONDS,
)

TEST_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE raw_alerts (
    cloudflare_id INTEGER PRIMARY KEY,
    ticker TEXT NOT NULL,
    event TEXT NOT NULL,
    fired_at_utc TEXT NOT NULL
);
CREATE TABLE episodes (
    episode_id TEXT PRIMARY KEY,
    ticker TEXT,
    direction TEXT,
    primary_alert_id INTEGER,
    started_at_utc TEXT,
    exit_alert_id INTEGER,
    exited_at_utc TEXT,
    episode_status TEXT,
    exit_missing INTEGER,
    sequence_anomaly INTEGER
);
CREATE TABLE episode_events (
    episode_id TEXT NOT NULL,
    raw_alert_id INTEGER NOT NULL,
    event_role TEXT NOT NULL,
    reentry_index INTEGER,
    PRIMARY KEY (episode_id, raw_alert_id)
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
CREATE TABLE feature_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_event_id INTEGER NOT NULL,
    episode_id TEXT,
    snapshot_time_utc TEXT NOT NULL,
    knowledge_cutoff_utc TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    latest_closed_bar_time TEXT NOT NULL,
    features_json TEXT NOT NULL,
    future_fields_present INTEGER NOT NULL DEFAULT 0
);
"""


def write_csv(
    path: Path,
    timeframe: str,
    *,
    append_future_spike: bool = False,
) -> list[dict[str, str]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, 0, 0)
    step = timedelta(seconds=TIMEFRAME_SECONDS[timeframe])
    rows: list[dict[str, str]] = []
    for index in range(80):
        price = 100.0 + index * 0.2
        rows.append(
            {
                "time": (start + index * step).strftime("%Y.%m.%d %H:%M:%S"),
                "open": f"{price:.5f}",
                "high": f"{price + 0.3:.5f}",
                "low": f"{price - 0.2:.5f}",
                "close": f"{price + 0.1:.5f}",
                "tick_volume": str(100 + index),
                "spread": "10",
                "real_volume": "0",
            }
        )
    if append_future_spike:
        rows.append(
            {
                "time": (start + 80 * step).strftime("%Y.%m.%d %H:%M:%S"),
                "open": "999",
                "high": "1000",
                "low": "998",
                "close": "999",
                "tick_volume": "999",
                "spread": "10",
                "real_volume": "0",
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_HEADER)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def make_database(path: Path, root: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(TEST_SCHEMA)
    connection.execute(
        "INSERT INTO raw_alerts VALUES "
        "(2, 'BTCUSD', 'LONG', '2026-01-04T10:00:00Z')"
    )
    connection.execute(
        "INSERT INTO episodes VALUES "
        "('BTCUSD:LONG:2','BTCUSD','LONG',2,'2026-01-04T10:00:00Z',"
        "NULL,NULL,'OPEN',1,0)"
    )
    connection.execute(
        "INSERT INTO episode_events VALUES "
        "('BTCUSD:LONG:2',2,'PRIMARY_ALERT',NULL)"
    )

    offset = 3
    for timeframe in FEATURE_TIMEFRAMES:
        rows = write_csv(root / FILE_MAP["BTCUSD"][timeframe], timeframe)
        selected = rows[69]
        server_open = datetime.strptime(
            selected["time"],
            "%Y.%m.%d %H:%M:%S",
        )
        utc_open = server_open - timedelta(hours=offset)
        utc_close = utc_open + timedelta(
            seconds=TIMEFRAME_SECONDS[timeframe]
        )
        decision = utc_close + timedelta(seconds=17)
        ohlc = {
            name: float(selected[name])
            for name in ("open", "high", "low", "close")
        }
        connection.execute(
            "INSERT INTO mt5_alignment VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                2,
                timeframe,
                decision.strftime("%Y-%m-%dT%H:%M:%SZ"),
                selected["time"],
                utc_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
                3.0,
                17.0,
                float(selected["close"]),
                float(selected["close"]),
                0.0,
                "ALIGNED_CLOSED_BAR",
                json.dumps({"ohlc": ohlc}),
            ),
        )
    connection.commit()
    return connection


def test_rci_is_monotonic_and_tie_safe() -> None:
    assert abs(rci_value([1, 2, 3, 4, 5]) - 100.0) < 1e-12
    assert abs(rci_value([5, 4, 3, 2, 1]) + 100.0) < 1e-12
    assert -100.0 <= rci_value([1, 1, 2, 2, 3]) <= 100.0


def test_feature_snapshots_are_complete_and_causal(tmp_path: Path) -> None:
    root = tmp_path / "Files"
    connection = make_database(tmp_path / "db.sqlite3", root)
    try:
        result = rebuild_feature_snapshots(
            connection,
            mt5_files_root=root,
            built_at_utc="2026-07-19T05:00:00Z",
        )
        assert result["snapshot_count"] == 5
        assert result["future_violation_count"] == 0
        rows = connection.execute(
            "SELECT * FROM feature_snapshots ORDER BY timeframe"
        ).fetchall()
        assert len(rows) == 5
        for row in rows:
            assert row["future_fields_present"] == 0
            assert row["latest_closed_bar_time"] <= row["knowledge_cutoff_utc"]
            payload = json.loads(row["features_json"])
            assert (
                payload["contract"]["proprietary_indicator_reconstruction"]
                is False
            )
            assert payload["contract"]["entry_gate_enabled"] is False
            assert payload["quality"]["warmup_sufficient"] is True
            assert (
                payload["zigzag_proxies"]["short"]
                ["future_relative_to_decision_used"]
                is False
            )
            assert payload["ema"]["alignment"] == "BULLISH_STACK"
            assert payload["rci"]["rci9"] > 99.0
    finally:
        connection.close()


def test_future_append_does_not_change_historical_snapshot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Files"
    connection = make_database(tmp_path / "db.sqlite3", root)
    try:
        rebuild_feature_snapshots(
            connection,
            mt5_files_root=root,
            built_at_utc="2026-07-19T05:00:00Z",
        )
        before = connection.execute(
            "SELECT features_json FROM feature_snapshots WHERE timeframe='M5'"
        ).fetchone()[0]
        write_csv(
            root / FILE_MAP["BTCUSD"]["M5"],
            "M5",
            append_future_spike=True,
        )
        rebuild_feature_snapshots(
            connection,
            mt5_files_root=root,
            built_at_utc="2026-07-19T06:00:00Z",
        )
        after = connection.execute(
            "SELECT features_json FROM feature_snapshots WHERE timeframe='M5'"
        ).fetchone()[0]
        before_payload = json.loads(before)
        after_payload = json.loads(after)
        before_payload["identity"]["built_at_utc"] = "IGNORED"
        after_payload["identity"]["built_at_utc"] = "IGNORED"
        assert before_payload == after_payload
    finally:
        connection.close()


def test_failure_preserves_previous_snapshot_table(tmp_path: Path) -> None:
    root = tmp_path / "Files"
    connection = make_database(tmp_path / "db.sqlite3", root)
    try:
        connection.execute(
            "INSERT INTO feature_snapshots VALUES "
            "('old',2,'BTCUSD:LONG:2','x','x','M5','x','{}',0)"
        )
        connection.commit()
        connection.execute(
            "UPDATE mt5_alignment SET mt5_close_price=999 WHERE timeframe='M5'"
        )
        connection.commit()
        try:
            rebuild_feature_snapshots(
                connection,
                mt5_files_root=root,
                built_at_utc="2026-07-19T05:00:00Z",
            )
            raise AssertionError("expected failure")
        except Exception:
            pass
        assert (
            connection.execute(
                "SELECT snapshot_id FROM feature_snapshots"
            ).fetchone()[0]
            == "old"
        )
    finally:
        connection.close()


def test_dependency_triggers_invalidate_snapshots(tmp_path: Path) -> None:
    root = tmp_path / "Files"
    connection = make_database(tmp_path / "db.sqlite3", root)
    try:
        rebuild_feature_snapshots(
            connection,
            mt5_files_root=root,
            built_at_utc="2026-07-19T05:00:00Z",
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM feature_snapshots"
        ).fetchone()[0] == 5

        connection.execute("DELETE FROM mt5_alignment WHERE timeframe='M5'")
        connection.commit()
        assert connection.execute(
            "SELECT COUNT(*) FROM feature_snapshots"
        ).fetchone()[0] == 4

        connection.execute("DELETE FROM episode_events")
        connection.execute("DELETE FROM episodes")
        connection.commit()
        assert connection.execute(
            "SELECT COUNT(*) FROM feature_snapshots"
        ).fetchone()[0] == 0
    finally:
        connection.close()
