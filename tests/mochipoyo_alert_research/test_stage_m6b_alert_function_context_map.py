from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "mochipoyo_alert_research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from alert_function_context_builder import (  # noqa: E402
    classify_entry_context,
    classify_htf_ema_context,
    classify_m15_range_context,
    classify_m5_rci_context,
    classify_resolved_outcome,
    rebuild_alert_function_context_map,
)


def _feature_payload(
    *,
    timeframe: str,
    ema_alignment: str = "MIXED",
    macd_histogram: float = 0.0,
    rci9: float = 0.0,
    rci14: float = 0.0,
    range_position: float = 0.5,
) -> dict[str, object]:
    return {
        "contract": {
            "future_relative_to_decision_used": False,
        },
        "ema": {
            "alignment": ema_alignment,
        },
        "macd": {
            "histogram": macd_histogram,
        },
        "rci": {
            "rci9": rci9,
            "rci14": rci14,
        },
        "recent_ranges": {
            "bars_20": {
                "close_position_0_1": range_position,
            }
        },
        "volatility": {
            "atr14_bps": 10.0 if timeframe != "D1" else 50.0,
        },
    }


def test_fixed_context_classes_do_not_accept_outcomes() -> None:
    assert (
        classify_entry_context(
            entry_role="PRIMARY_ALERT",
            htf_ema_context="ALIGNED",
            m15_macd_context="ALIGNED",
            m15_range_context="MIDDLE",
        )
        == "A_CONTINUATION_CONTEXT"
    )
    assert (
        classify_entry_context(
            entry_role="PRIMARY_ALERT",
            htf_ema_context="OPPOSED",
            m15_macd_context="ALIGNED",
            m15_range_context="FAVORABLE_EDGE",
        )
        == "B_WAIT_OR_REVERSAL_CONTEXT"
    )
    assert (
        classify_entry_context(
            entry_role="REENTRY_ALERT",
            htf_ema_context="OPPOSED",
            m15_macd_context="OPPOSED",
            m15_range_context="CHASING_EDGE",
        )
        == "C_REENTRY_CONTEXT"
    )


def test_directional_feature_classification() -> None:
    features = {
        "H1": _feature_payload(timeframe="H1", ema_alignment="BULLISH_STACK"),
        "H4": _feature_payload(timeframe="H4", ema_alignment="BULLISH_STACK"),
        "D1": _feature_payload(timeframe="D1", ema_alignment="BEARISH_STACK"),
    }
    context, counts, states = classify_htf_ema_context("LONG", features)
    assert context == "ALIGNED"
    assert counts == {"ALIGNED": 2, "OPPOSED": 1, "MIXED": 0}
    assert states["D1"] == "OPPOSED"

    assert classify_m5_rci_context("LONG", -85.0, -50.0) == "PULLBACK_EXTREME"
    assert classify_m5_rci_context("SHORT", 85.0, 50.0) == "PULLBACK_EXTREME"
    assert classify_m15_range_context("LONG", 0.20) == "FAVORABLE_EDGE"
    assert classify_m15_range_context("SHORT", 0.20) == "CHASING_EDGE"


def test_function_and_exit_labels_are_separate() -> None:
    functional, exit_class, first, _ = classify_resolved_outcome(
        source_return_atr_m5=-0.2,
        mfe_atr_m5=1.5,
        mae_atr_m5=0.5,
        time_to_mfe_seconds=60.0,
        time_to_mae_seconds=120.0,
    )
    assert functional == "CLEAN_EXPANSION"
    assert exit_class == "NONPOSITIVE_EXIT"
    assert first == "FAVORABLE_FIRST"

    functional, exit_class, first, _ = classify_resolved_outcome(
        source_return_atr_m5=0.3,
        mfe_atr_m5=1.5,
        mae_atr_m5=2.0,
        time_to_mfe_seconds=180.0,
        time_to_mae_seconds=60.0,
    )
    assert functional == "VOLATILE_EXPANSION"
    assert exit_class == "POSITIVE_EXIT"
    assert first == "ADVERSE_FIRST"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY
        );
        CREATE TABLE episodes (
            episode_id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL,
            primary_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id)
        );
        CREATE TABLE episode_events (
            episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
            raw_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
            event_role TEXT NOT NULL,
            reentry_index INTEGER,
            PRIMARY KEY (episode_id, raw_alert_id)
        );
        CREATE TABLE virtual_entries (
            entry_id TEXT PRIMARY KEY,
            episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
            entry_type TEXT NOT NULL,
            entry_index INTEGER NOT NULL,
            setup_detected_at_utc TEXT NOT NULL,
            entry_time_utc TEXT NOT NULL,
            entry_price REAL NOT NULL,
            sl_price REAL,
            tp_price REAL,
            status TEXT NOT NULL
        );
        CREATE TABLE feature_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            source_event_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
            timeframe TEXT NOT NULL,
            features_json TEXT NOT NULL,
            future_fields_present INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE outcome_path_metrics (
            entry_id TEXT PRIMARY KEY REFERENCES virtual_entries(entry_id),
            outcome_contract_version TEXT NOT NULL,
            source_return_atr_m5 REAL NOT NULL,
            mfe_atr_m5 REAL NOT NULL,
            mae_atr_m5 REAL NOT NULL,
            source_return_bps REAL NOT NULL,
            mfe_bps REAL NOT NULL,
            mae_bps REAL NOT NULL,
            time_to_mfe_seconds REAL NOT NULL,
            time_to_mae_seconds REAL NOT NULL,
            path_quality_status TEXT NOT NULL
        );
        """
    )
    return connection


def test_integrated_context_map_rebuild() -> None:
    connection = _connection()
    connection.execute("INSERT INTO raw_alerts VALUES (10)")
    connection.execute(
        "INSERT INTO episodes VALUES ('XAUUSD:LONG:10', 'XAUUSD', 'LONG', 10)"
    )
    connection.execute(
        "INSERT INTO episode_events VALUES "
        "('XAUUSD:LONG:10', 10, 'PRIMARY_ALERT', NULL)"
    )
    entry_id = "M6A:XAUUSD:LONG:10:PRIMARY:10"
    connection.execute(
        """
        INSERT INTO virtual_entries VALUES (
            ?, 'XAUUSD:LONG:10', 'SOURCE_PRIMARY_ALERT_IMMEDIATE', 0,
            '2026-07-15T09:45:00Z', '2026-07-15T09:45:00Z',
            3300.0, NULL, NULL, 'RESOLVED_SOURCE_EXIT'
        )
        """,
        (entry_id,),
    )
    connection.execute(
        """
        INSERT INTO outcome_path_metrics VALUES (
            ?, 'MOCHIPOYO_M6A_SOURCE_OUTCOMES_V1',
            0.4, 1.5, 0.5, 4.0, 15.0, 5.0,
            60.0, 120.0, 'FULL_M1_INTERIOR'
        )
        """,
        (entry_id,),
    )

    for timeframe in ("M5", "M15", "H1", "H4", "D1"):
        ema = "BULLISH_STACK" if timeframe in ("H1", "H4") else "MIXED"
        payload = _feature_payload(
            timeframe=timeframe,
            ema_alignment=ema,
            macd_histogram=1.0 if timeframe == "M15" else 0.0,
            range_position=0.5,
        )
        connection.execute(
            "INSERT INTO feature_snapshots VALUES (?, 10, ?, ?, 0)",
            (f"10:{timeframe}", timeframe, json.dumps(payload)),
        )
    connection.commit()

    result = rebuild_alert_function_context_map(
        connection,
        built_at_utc="2026-07-19T00:00:00Z",
    )
    assert result["context_row_count"] == 1
    assert result["resolved_entry_count"] == 1
    row = connection.execute(
        "SELECT * FROM alert_function_contexts WHERE entry_id = ?",
        (entry_id,),
    ).fetchone()
    assert row is not None
    assert row["context_class"] == "A_CONTINUATION_CONTEXT"
    assert row["functional_class"] == "CLEAN_EXPANSION"
    assert row["exit_class"] == "POSITIVE_EXIT"
    assert row["outcome_used_for_context_class"] == 0
    assert row["approved_for_trading"] == 0
    context = json.loads(row["context_json"])
    assert context["contract"]["chart_label_redraw_required_for_event_identity"] is False
    assert context["identity"]["entry_time_jst"] == "2026-07-15T18:45:00+09:00"
