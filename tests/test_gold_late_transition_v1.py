from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.gold_late_transition_v1 import shadow_runtime as runtime


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def make_environment(tmp_path: Path, initial_end_minute: int = 30):
    repo = tmp_path / "repo"
    local_config = repo / "config" / "gold_late_transition_v1" / "local_config.json"
    v19_config = repo / "config" / "gold_wave_shadow_v19" / "local_config.json"
    v19_state = tmp_path / "v19_state"
    late_state = tmp_path / "late_state"
    m1_path = tmp_path / "m1.csv"
    t0 = pd.Timestamp("2026-08-03 01:00:00")

    m1 = pd.DataFrame(
        {
            "time": pd.date_range(t0, periods=initial_end_minute + 1, freq="min"),
            "open": 3300.0,
            "high": 3300.5,
            "low": 3299.5,
            "close": 3300.0,
        }
    )
    m1.to_csv(m1_path, index=False)
    scores = pd.DataFrame(
        [
            {"origin_id": 1, "entry_time": t0, "chosen_side": "LONG", "chosen_rank": 0.50, "wave_state": "BALANCED", "schedule": "SEMIANNUAL_EXPANDING"},
            {"origin_id": 2, "entry_time": t0 + pd.Timedelta(minutes=15), "chosen_side": "LONG", "chosen_rank": 0.50, "wave_state": "BALANCED", "schedule": "SEMIANNUAL_EXPANDING"},
            {"origin_id": 3, "entry_time": t0 + pd.Timedelta(minutes=30), "chosen_side": "LONG", "chosen_rank": 0.50, "wave_state": "BALANCED", "schedule": "SEMIANNUAL_EXPANDING"},
        ]
    )
    (v19_state / "outputs").mkdir(parents=True)
    scores.to_csv(v19_state / "outputs" / "shadow_score_ledger.csv", index=False)
    write_json(
        v19_config,
        {
            "shadow_id": runtime.V19_SHADOW_ID,
            "contract_version": runtime.V19_CONTRACT_VERSION,
            "state_dir": str(v19_state),
            "discord": {"enabled": True, "webhook_url": "https://discord.com/api/webhooks/test/test"},
            "data_sources": {"M1": [str(m1_path)], "M15": [str(m1_path)]},
        },
    )
    write_json(
        v19_state / "runtime_state.json",
        {
            "activated": True,
            "status": "READY",
            "last_processed_decision_time": str(t0 + pd.Timedelta(minutes=30)),
            "latest_session_guarded_decision_time": str(t0 + pd.Timedelta(minutes=30)),
            "open_trade": None,
            "counters": {"accepted_trades": 0},
        },
    )
    write_json(
        local_config,
        {
            "shadow_id": runtime.SHADOW_ID,
            "contract_version": runtime.CONTRACT_VERSION,
            "state_dir": str(late_state),
            "poll_seconds": 1,
            "v19": {"config_path": str(v19_config)},
            "discord": {"enabled": False, "webhook_source": "V19_LOCAL_CONFIG"},
        },
    )
    return local_config, v19_state, late_state, m1_path, t0, scores


def test_signal_zone_is_frozen_sub_p90_late_or_correction():
    assert runtime.selected_zone("LONG", 0.899, "IMPULSE_LATE") == "NON_IE_SUBP90_IMPULSE_LATE"
    assert runtime.selected_zone("SHORT", 0.4, "CORRECTION_EARLY") == "NON_IE_SUBP90_CORRECTION_EARLY"
    assert runtime.selected_zone("LONG", 0.90, "IMPULSE_LATE") is None
    assert runtime.selected_zone("LONG", 0.50, "IMPULSE_EARLY") is None


def test_v19_first_p90_is_consumed_once_per_causal_episode():
    state = runtime.RuntimeState()
    t0 = pd.Timestamp("2026-08-03 01:00")
    rows = [
        {"entry_time": t0, "chosen_side": "LONG", "chosen_rank": 0.89, "wave_state": "IMPULSE_EARLY"},
        {"entry_time": t0 + pd.Timedelta(minutes=15), "chosen_side": "LONG", "chosen_rank": 0.91, "wave_state": "IMPULSE_EARLY"},
        {"entry_time": t0 + pd.Timedelta(minutes=30), "chosen_side": "LONG", "chosen_rank": 0.99, "wave_state": "IMPULSE_EARLY"},
        {"entry_time": t0 + pd.Timedelta(minutes=45), "chosen_side": "LONG", "chosen_rank": 0.20, "wave_state": "BALANCED"},
        {"entry_time": t0 + pd.Timedelta(minutes=60), "chosen_side": "LONG", "chosen_rank": 0.95, "wave_state": "IMPULSE_EARLY"},
    ]
    assert [runtime.update_v19_episode(state, row) for row in rows] == [False, True, False, False, True]



def test_v19_episode_id_from_frozen_ledger_is_authoritative():
    state = runtime.RuntimeState()
    t0 = pd.Timestamp("2026-08-03 01:00")
    first = {"entry_time": t0, "chosen_side": "SHORT", "chosen_rank": 0.91, "wave_state": "IMPULSE_EARLY", "wave_early_episode_id": 10}
    same = {"entry_time": t0 + pd.Timedelta(minutes=30), "chosen_side": "SHORT", "chosen_rank": 0.99, "wave_state": "IMPULSE_EARLY", "wave_early_episode_id": 10}
    next_episode = {"entry_time": t0 + pd.Timedelta(minutes=45), "chosen_side": "SHORT", "chosen_rank": 0.95, "wave_state": "IMPULSE_EARLY", "wave_early_episode_id": 11}
    assert runtime.update_v19_episode(state, first)
    assert not runtime.update_v19_episode(state, same)
    assert runtime.update_v19_episode(state, next_episode)

def test_same_m1_collision_is_sl_first_and_horizon_exits_before_range():
    row = {"origin_id": 1, "entry_time": pd.Timestamp("2026-08-03 01:00"), "chosen_side": "LONG", "chosen_rank": 0.5, "wave_state": "IMPULSE_LATE"}
    position = runtime.position_from_row("CHALLENGER", row, 0, 3300.0, "NON_IE_SUBP90_IMPULSE_LATE")
    assert runtime.resolve_on_bar(position, 1, 3300.0, 3330.0, 3280.0) == (-10.0, "SL")
    # Even though the boundary bar range would hit TP, the open TIME exit happens first.
    pnl, reason = runtime.resolve_on_bar(position, 480, 3301.0, 3350.0, 3250.0)
    assert reason == "TIME"
    assert abs(pnl - 0.7) < 1e-9


def test_bootstrap_and_live_v19_preemption_have_exact_order(tmp_path: Path):
    config_path, v19_state, late_state, m1_path, t0, scores = make_environment(tmp_path)
    runtime.bootstrap(config_path, activate=True)

    extended = pd.DataFrame(
        {
            "time": pd.date_range(t0, periods=91, freq="min"),
            "open": 3300.0,
            "high": 3300.5,
            "low": 3299.5,
            "close": 3300.0,
        }
    )
    extended.to_csv(m1_path, index=False)
    future = pd.DataFrame(
        [
            {"origin_id": 4, "entry_time": t0 + pd.Timedelta(minutes=45), "chosen_side": "LONG", "chosen_rank": 0.60, "wave_state": "IMPULSE_LATE", "schedule": "SEMIANNUAL_EXPANDING"},
            {"origin_id": 5, "entry_time": t0 + pd.Timedelta(minutes=60), "chosen_side": "LONG", "chosen_rank": 0.95, "wave_state": "IMPULSE_EARLY", "schedule": "SEMIANNUAL_EXPANDING"},
        ]
    )
    pd.concat([scores, future], ignore_index=True).to_csv(v19_state / "outputs" / "shadow_score_ledger.csv", index=False)
    write_json(
        v19_state / "runtime_state.json",
        {
            "activated": True,
            "status": "READY",
            "last_processed_decision_time": str(t0 + pd.Timedelta(minutes=60)),
            "latest_session_guarded_decision_time": str(t0 + pd.Timedelta(minutes=60)),
            "open_trade": {"direction": "LONG", "entry_time": str(t0 + pd.Timedelta(minutes=60))},
            "counters": {"accepted_trades": 1},
        },
    )
    state = runtime.process_iteration(config_path, recovery_cutoff=t0 + pd.Timedelta(minutes=30))
    assert state.counters["accepted_trades"] == 1
    assert state.counters["v19_preemptions"] == 1
    assert state.open_position is not None and state.open_position.system == "V19"
    candidates = pd.read_csv(late_state / "outputs" / "shadow_candidate_ledger.csv")
    trades = pd.read_csv(late_state / "outputs" / "shadow_trade_ledger.csv")
    assert candidates.decision.tolist() == ["ACCEPTED"]
    assert trades.exit_reason.tolist() == ["V19_PREEMPT"]
    assert trades.exit_time.iloc[0].startswith(str(t0 + pd.Timedelta(minutes=60)))


def test_backlog_at_process_start_is_recovery_only(tmp_path: Path):
    config_path, v19_state, late_state, m1_path, t0, scores = make_environment(tmp_path)
    runtime.bootstrap(config_path, activate=True)
    extended = pd.DataFrame(
        {
            "time": pd.date_range(t0, periods=61, freq="min"),
            "open": 3300.0,
            "high": 3300.5,
            "low": 3299.5,
            "close": 3300.0,
        }
    )
    extended.to_csv(m1_path, index=False)
    future = pd.DataFrame(
        [
            {"origin_id": 4, "entry_time": t0 + pd.Timedelta(minutes=45), "chosen_side": "SHORT", "chosen_rank": 0.60, "wave_state": "CORRECTION_EARLY", "schedule": "SEMIANNUAL_EXPANDING"},
            {"origin_id": 5, "entry_time": t0 + pd.Timedelta(minutes=60), "chosen_side": "SHORT", "chosen_rank": 0.55, "wave_state": "CORRECTION_EARLY", "schedule": "SEMIANNUAL_EXPANDING"},
        ]
    )
    pd.concat([scores, future], ignore_index=True).to_csv(v19_state / "outputs" / "shadow_score_ledger.csv", index=False)
    write_json(
        v19_state / "runtime_state.json",
        {
            "activated": True,
            "status": "READY",
            "last_processed_decision_time": str(t0 + pd.Timedelta(minutes=60)),
            "latest_session_guarded_decision_time": str(t0 + pd.Timedelta(minutes=60)),
            "open_trade": None,
            "counters": {"accepted_trades": 0},
        },
    )
    state = runtime.process_iteration(config_path, recovery_cutoff=t0 + pd.Timedelta(minutes=60))
    assert state.counters["accepted_trades"] == 0
    assert state.counters["recovery_replay_events"] == 1
    recovery = pd.read_csv(late_state / "outputs" / "recovery_replay_ledger.csv")
    assert recovery.reason.tolist() == ["RECOVERY_REPLAY_NOT_TRADED"]


def test_future_score_rows_beyond_v19_cursor_fail_closed(tmp_path: Path):
    config_path, v19_state, _late_state, _m1_path, t0, scores = make_environment(tmp_path)
    future = pd.DataFrame(
        [
            {
                "origin_id": 99,
                "entry_time": t0 + pd.Timedelta(minutes=45),
                "chosen_side": "LONG",
                "chosen_rank": 0.50,
                "wave_state": "IMPULSE_LATE",
                "schedule": "SEMIANNUAL_EXPANDING",
            }
        ]
    )
    pd.concat([scores, future], ignore_index=True).to_csv(
        v19_state / "outputs" / "shadow_score_ledger.csv", index=False
    )
    try:
        runtime.bootstrap(config_path, activate=True)
    except RuntimeError as exc:
        assert "contains rows beyond its last processed decision" in str(exc)
    else:
        raise AssertionError("Future unprocessed score rows must fail closed")
