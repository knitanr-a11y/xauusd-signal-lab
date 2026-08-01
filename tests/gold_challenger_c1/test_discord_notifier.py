from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.gold_challenger_c1.discord_notifier import default_notifier_state, message  # noqa: E402


def test_notifier_baselines_current_count_without_backfill():
    state = default_notifier_state({"counters": {"accepted_trades": 7}})
    assert state["baseline_accepted_trades"] == 7
    assert state["last_seen_accepted_trades"] == 7
    assert state["sent_entry_notifications"] == 0


def test_message_contains_fixed_observation_fields():
    text = message(
        {
            "chosen_side": "SHORT",
            "decision_dt": "2026-08-01 10:15:00",
            "entry_price": 2400,
            "tp_price": 2380,
            "sl_price": 2410,
            "wave_state": "IMPULSE_LATE",
            "chosen_rank": 0.45,
        }
    )
    assert "SHORT" in text
    assert "IMPULSE_LATE" in text
    assert "< P90" in text
    assert "観測専用" in text
    assert "V19優先" in text
