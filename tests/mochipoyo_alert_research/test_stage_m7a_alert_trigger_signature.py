from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import alert_trigger_signature_audit as audit


def _bar(text: str, close: float) -> SimpleNamespace:
    return SimpleNamespace(
        server_open=datetime.strptime(text, "%Y.%m.%d %H:%M:%S"),
        open_price=close - 0.2,
        high_price=close + 0.5,
        low_price=close - 0.5,
        close_price=close,
        tick_volume=100,
        spread=1,
        real_volume=0,
    )


def _payload(index: int, close: float) -> dict[str, object]:
    rci9 = [-90.0, -70.0, 10.0, 85.0][index]
    rci14 = [-80.0, -60.0, 5.0, 75.0][index]
    rci18 = [-70.0, -50.0, 0.0, 65.0][index]
    return {
        "bar": {"close": close},
        "ema": {
            "ema20": close - 1.0,
            "ema30": close - 2.0,
            "ema40": close - 3.0,
            "alignment": "BULLISH_STACK",
            "spread_atr_ratio": 1.0,
            "close_minus_ema20_bps": 1.0,
            "close_minus_ema30_bps": 2.0,
            "close_minus_ema40_bps": 3.0,
            "ema20_slope_3_bars_bps": 0.5,
            "ema30_slope_3_bars_bps": 0.4,
            "ema40_slope_3_bars_bps": 0.3,
        },
        "rci": {"rci9": rci9, "rci14": rci14, "rci18": rci18},
        "macd": {
            "line_bps": float(index),
            "signal_bps": float(index) - 0.2,
            "histogram_bps": 0.2,
            "zero_proximity_atr_ratio": 0.1,
        },
        "volatility": {"atr14": 2.0, "atr14_bps": 10.0, "bar_range_atr_ratio": 0.5},
        "candle": {
            "direction": "UP",
            "body_to_range_ratio": 0.5,
            "upper_wick_to_range_ratio": 0.25,
            "lower_wick_to_range_ratio": 0.25,
        },
        "volume": {"tick_volume_ratio20": 1.0},
        "recent_ranges": {
            "bars_5": {"close_position_0_1": 0.2},
            "bars_10": {"close_position_0_1": 0.3},
            "bars_20": {
                "close_position_0_1": 0.4,
                "distance_to_high_bps": 5.0,
                "distance_to_low_bps": 4.0,
            },
        },
        "zigzag_proxies": {
            "short": {
                "latest_pivot": None,
                "latest_confirmed_high": None,
                "latest_confirmed_low": None,
            },
            "medium": {
                "latest_pivot": None,
                "latest_confirmed_high": None,
                "latest_confirmed_low": None,
            },
        },
    }


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE raw_alerts (
            cloudflare_id INTEGER PRIMARY KEY,
            ticker TEXT NOT NULL,
            event TEXT NOT NULL,
            bar_time_utc TEXT NOT NULL,
            fired_at_utc TEXT NOT NULL
        );
        CREATE TABLE raw_alert_annotations (
            raw_alert_id INTEGER PRIMARY KEY,
            annotation_type TEXT NOT NULL
        );
        CREATE TABLE episode_events (
            raw_alert_id INTEGER PRIMARY KEY,
            event_role TEXT NOT NULL
        );
        CREATE TABLE mt5_alignment (
            raw_alert_id INTEGER NOT NULL,
            timeframe TEXT NOT NULL,
            selected_offset_hours REAL,
            mt5_server_time TEXT,
            alignment_status TEXT NOT NULL,
            diagnostics_json TEXT NOT NULL,
            PRIMARY KEY (raw_alert_id, timeframe)
        );
        CREATE TABLE episode_build_anomalies (anomaly_id INTEGER PRIMARY KEY);
        """
    )
    events = [
        (1, "XAUUSD", "LONG", "2026-07-01T00:15:00Z", "2026-07-01T00:15:01Z", "PRIMARY_ALERT", "2026.07.01 00:00:00"),
        (2, "XAUUSD", "LONG", "2026-07-01T00:30:00Z", "2026-07-01T00:30:01Z", "REENTRY_ALERT", "2026.07.01 00:15:00"),
        (3, "XAUUSD", "LONG_EXIT", "2026-07-01T00:45:00Z", "2026-07-01T00:45:01Z", "EXIT_ALERT", "2026.07.01 00:30:00"),
    ]
    for raw_id, ticker, event, bar_time, fired, role, server_open in events:
        connection.execute(
            "INSERT INTO raw_alerts VALUES (?, ?, ?, ?, ?)",
            (raw_id, ticker, event, bar_time, fired),
        )
        connection.execute(
            "INSERT INTO episode_events VALUES (?, ?)", (raw_id, role)
        )
        connection.execute(
            "INSERT INTO mt5_alignment VALUES (?, 'M15', 0, ?, 'ALIGNED_CLOSED_BAR', '{}')",
            (raw_id, server_open),
        )
    connection.commit()
    return connection


def test_causal_samples_use_previous_closed_bar_and_state(monkeypatch, tmp_path: Path) -> None:
    bars = [
        _bar("2026.06.30 23:45:00", 99.0),
        _bar("2026.07.01 00:00:00", 100.0),
        _bar("2026.07.01 00:15:00", 101.0),
        _bar("2026.07.01 00:30:00", 102.0),
        _bar("2026.07.01 00:45:00", 103.0),
    ]
    monkeypatch.setattr(audit, "MINIMUM_WARMUP_BARS", 1)
    series = SimpleNamespace(
        bars=bars,
        rci={
            9: [-95.0, -90.0, -70.0, 10.0, 85.0],
            14: [-85.0, -80.0, -60.0, 5.0, 75.0],
            18: [-75.0, -70.0, -50.0, 0.0, 65.0],
        },
        macd_histogram=[-0.3, -0.2, -0.1, 0.1, 0.2],
    )
    monkeypatch.setattr(audit, "load_indicator_series", lambda _: series)

    def fake_payload(series_obj, *, selected_index, **kwargs):
        return _payload(selected_index, series_obj.bars[selected_index].close_price)

    monkeypatch.setattr(audit, "build_feature_payload", fake_payload)
    monkeypatch.setitem(audit.FILE_MAP["XAUUSD"], "M15", "goldsharp_m15.csv")

    samples, coverage = audit.build_decision_samples(
        _connection(),
        mt5_files_root=tmp_path,
        built_at_utc="2026-07-01T01:00:00Z",
    )
    assert coverage["eligible_event_count"] == 3
    assert [sample.transition for sample in samples] == [
        "PRIMARY_LONG",
        "REENTRY_LONG",
        "LONG_EXIT",
    ]
    assert [sample.state_before for sample in samples] == [
        "IDLE",
        "ACTIVE_LONG",
        "ACTIVE_LONG",
    ]
    assert samples[0].selected_server_open == datetime(2026, 7, 1, 0, 0)
    assert abs(samples[0].features["current_open_gap_atr"] - 0.4) < 1e-12
    assert samples[1].features["previous_transition"] == "PRIMARY_LONG"


def test_rule_discovery_is_exploratory_only() -> None:
    rows = []
    for index in range(20):
        rows.append(
            audit.DecisionSample(
                ticker="XAUUSD",
                decision_time_utc=datetime(2026, 7, 1, 0, 0),
                selected_server_open=datetime(2026, 7, 1, 0, 0),
                state_before="IDLE",
                transition="PRIMARY_LONG" if index in (1, 2, 3, 4, 5) else "NO_EVENT",
                raw_alert_id=index if index in (1, 2, 3, 4, 5) else None,
                features={"rci9": -90.0 if index in (1, 2, 3, 4, 5) else 20.0},
            )
        )
    report = audit.discover_rules(rows, "PRIMARY_LONG")
    assert report["status"] == "EXPLORATORY_ONLY"
    assert report["exact_internal_condition_identified"] is False
    assert report["historical_candidate_extraction_approved"] is False
    assert report["top_single_rules"][0]["matched_positive"] == 5


def test_stale_raw_alert_set_fails_closed() -> None:
    connection = _connection()
    connection.execute(
        "INSERT INTO raw_alerts VALUES (4, 'XAUUSD', 'SHORT', '2026-07-01T01:00:00Z', '2026-07-01T01:00:01Z')"
    )
    connection.commit()
    try:
        audit.validate_upstream_coverage(connection)
    except audit.TriggerSignatureContractError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale upstream set did not fail closed")
