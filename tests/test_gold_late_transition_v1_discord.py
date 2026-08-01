from pathlib import Path

import pytest

from scripts.gold_late_transition_v1 import discord_notifier as notifier


def test_notifier_state_baselines_current_count_without_backfill():
    state = notifier.notifier_state({"counters": {"accepted_trades": 7}})
    assert state["baseline_accepted_trades"] == 7
    assert state["last_seen_accepted_trades"] == 7
    assert state["sent_entry_notifications"] == 0
    assert "NO_BACKFILL" in state["startup_policy"]


def test_message_contains_frozen_late_transition_contract(tmp_path: Path):
    output = tmp_path / "outputs"
    output.mkdir()
    (output / "shadow_candidate_ledger.csv").write_text(
        "event_id,decision,accepted_trade_count,direction,entry_time,entry_price,tp_price,sl_price,wave_state,chosen_rank\n"
        "x,ACCEPTED,1,SHORT,2026-08-03 10:15:00,3310,3290,3320,CORRECTION_EARLY,0.742\n",
        encoding="utf-8",
    )
    runtime = {"counters": {"accepted_trades": 1}, "open_trade": None}
    text = notifier.message(notifier.event_from(runtime, tmp_path))
    assert "SHORT" in text
    assert "CORRECTION_EARLY" in text
    assert "0.742" in text
    assert "P90未満" in text
    assert "V19発火時はV19を優先" in text
    assert "観測専用・実注文なし" in text


def test_accepted_event_uses_matching_counter_not_last_suppressed_row(tmp_path: Path):
    output = tmp_path / "outputs"
    output.mkdir()
    (output / "shadow_candidate_ledger.csv").write_text(
        "event_id,decision,accepted_trade_count,direction,entry_time\n"
        "a,ACCEPTED,1,LONG,2026-08-03 10:00:00\n"
        "b,SUPPRESSED,,SHORT,2026-08-03 10:15:00\n",
        encoding="utf-8",
    )
    row = notifier.accepted_event(tmp_path, 1)
    assert row["direction"] == "LONG"



def test_configure_reuses_v19_secret_without_copying_it(tmp_path: Path):
    repo = tmp_path / "repo"
    local = repo / "config" / "gold_late_transition_v1" / "local_config.json"
    v19 = repo / "config" / "gold_wave_shadow_v19" / "local_config.json"
    local.parent.mkdir(parents=True)
    v19.parent.mkdir(parents=True)
    v19.write_text(
        '{"shadow_id":"GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW","contract_version":"2026-08-01-v1","state_dir":"x","discord":{"enabled":true,"webhook_url":"https://discord.com/api/webhooks/secret/value"}}',
        encoding="utf-8",
    )
    local.write_text(
        '{"shadow_id":"GOLD_LATE_TRANSITION_VACANCY_V1_SHADOW","contract_version":"2026-08-01-v1","state_dir":"x","v19":{"config_path":"config/gold_wave_shadow_v19/local_config.json"},"discord":{"enabled":false}}',
        encoding="utf-8",
    )
    notifier.configure(local)
    text = local.read_text(encoding="utf-8")
    assert "V19_LOCAL_CONFIG" in text
    assert "secret/value" not in text
    assert "webhook_url" not in text

def test_duplicate_notifier_process_lock_is_rejected(tmp_path: Path):
    first = notifier.lock_instance(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="already running"):
            notifier.lock_instance(tmp_path)
    finally:
        first.close()
