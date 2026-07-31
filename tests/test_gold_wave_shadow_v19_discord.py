from pathlib import Path

import pytest

from scripts.gold_wave_shadow_v19 import discord_notifier as notifier


def test_notifier_state_baselines_current_count_without_backfill():
    state = notifier.notifier_state({"counters": {"accepted_trades": 7}})
    assert state["baseline_accepted_trades"] == 7
    assert state["last_seen_accepted_trades"] == 7
    assert state["sent_entry_notifications"] == 0
    assert "NO_BACKFILL" in state["startup_policy"]


def test_long_event_uses_frozen_tp20_sl10(tmp_path: Path):
    runtime = {
        "counters": {"accepted_trades": 1},
        "open_trade": {
            "direction": "LONG",
            "entry_dt": "2026-08-01 10:01:00",
            "entry_price": 3300.25,
        },
    }
    event = notifier.event_from(runtime, tmp_path)
    assert event["side"] == "LONG"
    assert event["entry"] == 3300.25
    assert event["tp"] == 3320.25
    assert event["sl"] == 3290.25


def test_short_entry_message_is_japanese_and_observation_only(tmp_path: Path):
    runtime = {
        "counters": {"accepted_trades": 2},
        "open_trade": {
            "direction": "SHORT",
            "entry_dt": "2026-08-01 11:16:00",
            "entry_price": 3310.0,
        },
    }
    text = notifier.message(notifier.event_from(runtime, tmp_path))
    assert "SHORT" in text
    assert "MT5" in text
    assert "3290.00" in text
    assert "3320.00" in text
    assert "観測専用・実注文なし" in text


def test_duplicate_notifier_process_lock_is_rejected(tmp_path: Path):
    first = notifier.lock_instance(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="already running"):
            notifier.lock_instance(tmp_path)
    finally:
        first.close()
