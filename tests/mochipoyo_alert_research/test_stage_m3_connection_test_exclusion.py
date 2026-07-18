from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mochipoyo_alert_research.db import open_database  # noqa: E402
from mochipoyo_alert_research.episode_builder import rebuild_episodes  # noqa: E402

CONFIRM_SCRIPT = (
    ROOT
    / "scripts"
    / "mochipoyo_alert_research"
    / "confirm_connection_test_alert_once.py"
)
SCHEMA = ROOT / "scripts" / "mochipoyo_alert_research" / "schema.sql"
spec = importlib.util.spec_from_file_location(
    "confirm_connection_test_alert_once", CONFIRM_SCRIPT
)
assert spec and spec.loader
confirm_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = confirm_module
spec.loader.exec_module(confirm_module)


def insert_alert(
    connection,
    alert_id: int,
    event: str,
    fired_at: str,
    message: str,
) -> None:
    source = {
        "id": alert_id,
        "ticker": "XAUUSD",
        "event": event,
        "fired_at_utc": fired_at,
        "message": message,
    }
    canonical = json.dumps(source, sort_keys=True, separators=(",", ":"))
    connection.execute(
        """
        INSERT INTO raw_alerts (
            cloudflare_id, event_key, event_key_origin, received_at_utc,
            source, strategy, event, exchange_name, ticker, timeframe,
            bar_time_utc, fired_at_utc, open_price, high_price, low_price,
            close_price, message, worker_raw_json, worker_raw_json_origin,
            collector_source_row_json, payload_sha256, downloaded_at_utc
        ) VALUES (?, ?, 'DERIVED_CLOUDFLARE_ID', ?, 'tradingview', 'mochipoyo',
                  ?, 'VANTAGE', 'XAUUSD', '15', ?, ?, 1, 1, 1, 1,
                  ?, ?, 'COLLECTOR_SOURCE_ROW_FALLBACK', ?, ?, ?)
        """,
        (
            alert_id,
            f"cloudflare:{alert_id}",
            fired_at,
            event,
            fired_at,
            fired_at,
            message,
            canonical,
            canonical,
            f"sha-{alert_id}",
            fired_at,
        ),
    )


def test_only_id1_is_excluded_and_real_alerts_split_into_two_episodes() -> None:
    temp = tempfile.TemporaryDirectory()
    connection = open_database(Path(temp.name) / "test.sqlite3", SCHEMA)
    try:
        insert_alert(
            connection,
            1,
            "LONG",
            "2026-07-15T00:00:01Z",
            "test long sign 4000.00",
        )
        insert_alert(connection, 4, "SHORT", "2026-07-15T09:45:00Z", "short sign")
        insert_alert(
            connection,
            6,
            "SHORT_EXIT",
            "2026-07-15T15:45:00Z",
            "15 SHORT EXIT",
        )
        insert_alert(connection, 7, "LONG", "2026-07-15T17:15:01Z", "long sign")
        insert_alert(
            connection,
            9,
            "LONG_EXIT",
            "2026-07-15T18:15:00Z",
            "15 LONG EXIT",
        )
        connection.commit()

        confirmation = confirm_module.confirm_connection_test_alert(
            connection,
            raw_alert_id=1,
            confirmed_at_utc="2026-07-18T06:30:00Z",
        )
        result = rebuild_episodes(
            connection,
            built_at_utc="2026-07-18T06:31:00Z",
        )

        assert confirmation["connection_test_alert_count"] == 1
        assert result.raw_alert_count == 5
        assert result.eligible_raw_alert_count == 4
        assert result.excluded_connection_test_count == 1
        assert result.episode_count == 2
        assert result.closed_episode_count == 2
        assert result.reentry_count == 0
        assert result.anomaly_count == 0
        assert result.ignored_opposite_count == 0

        episodes = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT episode_id, primary_alert_id, exit_alert_id
                FROM episodes
                ORDER BY primary_alert_id
                """
            )
        ]
        assert episodes == [
            ("XAUUSD:SHORT:4", 4, 6),
            ("XAUUSD:LONG:7", 7, 9),
        ]
        assert connection.execute(
            "SELECT COUNT(*) FROM raw_alerts"
        ).fetchone()[0] == 5
        assert connection.execute(
            "SELECT COUNT(*) FROM raw_alert_annotations WHERE raw_alert_id = 1"
        ).fetchone()[0] == 1
    finally:
        connection.close()
        temp.cleanup()


def test_confirmation_refuses_a_non_test_message() -> None:
    temp = tempfile.TemporaryDirectory()
    connection = open_database(Path(temp.name) / "test.sqlite3", SCHEMA)
    try:
        insert_alert(connection, 1, "LONG", "2026-07-15T00:00:01Z", "long sign")
        connection.commit()
        try:
            confirm_module.confirm_connection_test_alert(
                connection,
                raw_alert_id=1,
                confirmed_at_utc="2026-07-18T06:30:00Z",
            )
        except RuntimeError as exc:
            assert "not explicitly marked as a test" in str(exc)
        else:
            raise AssertionError("non-test alert was incorrectly annotated")
    finally:
        connection.close()
        temp.cleanup()
