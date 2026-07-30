from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR02_canonical_source_event_ledger"
    / "python"
    / "run_bcr02_canonical_source_event_ledger.py"
)

spec = importlib.util.spec_from_file_location("bcr02_module", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_state_machine_core_paths() -> None:
    assert module.role_for("IDLE", "LONG") == (
        "PRIMARY_LONG", "PRIMARY_ALERT", "ACTIVE_LONG"
    )
    assert module.role_for("ACTIVE_LONG", "LONG") == (
        "REENTRY_LONG", "REENTRY_ALERT", "ACTIVE_LONG"
    )
    assert module.role_for("ACTIVE_LONG", "SHORT") == (
        "OPPOSITE_ALERT_IGNORED", "OPPOSITE_ALERT_IGNORED", "ACTIVE_LONG"
    )
    assert module.role_for("ACTIVE_LONG", "LONG_EXIT") == (
        "LONG_EXIT", "EXIT_ALERT", "IDLE"
    )
    assert module.role_for("ACTIVE_SHORT", "SHORT_EXIT") == (
        "SHORT_EXIT", "EXIT_ALERT", "IDLE"
    )


def test_connection_test_is_excluded_from_state() -> None:
    alerts = [
        {
            "cloudflare_id": "1",
            "event_key": "cloudflare:1",
            "payload_sha256": "a",
            "ticker": "XAUUSD",
            "event": "LONG",
            "exchange_name": "VANTAGE",
            "timeframe": "15",
            "bar_time_utc": "2026-07-15T00:00:00Z",
            "fired_at_utc": "2026-07-15T00:00:01Z",
            "received_at_utc": "2026-07-15T00:00:02Z",
            "downloaded_at_utc": "2026-07-18T00:00:00Z",
            "open_price": "1",
            "high_price": "1",
            "low_price": "1",
            "close_price": "1",
        },
        {
            "cloudflare_id": "2",
            "event_key": "cloudflare:2",
            "payload_sha256": "b",
            "ticker": "XAUUSD",
            "event": "SHORT",
            "exchange_name": "VANTAGE",
            "timeframe": "15",
            "bar_time_utc": "2026-07-20T15:00:00Z",
            "fired_at_utc": "2026-07-20T15:00:01Z",
            "received_at_utc": "2026-07-20T15:00:02Z",
            "downloaded_at_utc": "2026-07-20T15:00:03Z",
            "open_price": "1",
            "high_price": "1",
            "low_price": "1",
            "close_price": "1",
        },
    ]
    annotations = [
        {
            "raw_alert_id": "1",
            "annotation_type": "CONNECTION_TEST",
            "confirmed_by": "USER",
            "reason": "test",
            "created_at_utc": "2026-07-18T00:00:00Z",
        }
    ]
    seed, research, checks = module.build_ledger(alerts, annotations)
    assert seed[0]["source_state_after"] == "IDLE"
    assert research[0]["source_state_before"] == "IDLE"
    assert research[0]["source_transition"] == "PRIMARY_SHORT"
    assert checks["connection_test_ids"] == [1]


def test_parity_detects_exact_match() -> None:
    research = [
        {
            "raw_alert_id": 64,
            "ticker": "BTCUSD",
            "bar_time_utc": "2026-07-20T16:00:00Z",
            "source_transition": "LONG_EXIT",
            "source_state_before": "ACTIVE_LONG",
            "source_state_after": "IDLE",
            "event_role": "EXIT_ALERT",
        }
    ]
    comparison = [
        {
            "raw_alert_id": "64",
            "ticker": "BTCUSD",
            "source_decision_time_utc": "2026-07-20T16:00:00Z",
            "source_transition": "LONG_EXIT",
            "source_state_before": "ACTIVE_LONG",
            "source_state_after": "IDLE",
            "event_role": "EXIT_ALERT",
        }
    ]
    rows, checks = module.parity_rows(research, comparison)
    assert rows[0]["all_match"] is True
    assert checks["m7c_parity_all_match"] is True
