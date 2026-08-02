from __future__ import annotations

import pandas as pd

from scripts.gold_scalp_state_survival_shadow.shadow_runtime import _advance_resolution, _levels, _new_resolution


def _trade(action="LONG", raw_open=2000.0):
    levels = _levels(raw_open, action)
    return {"action": action, "entry_time": "2026-08-03 01:00:00", **levels}


def test_long_final_target_p75_contract():
    trade = _trade("LONG")
    resolution = _new_resolution(pd.Timestamp(trade["entry_time"]))
    bars = pd.DataFrame([
        {"time": pd.Timestamp("2026-08-03 01:00:00"), "open": 2000.0, "high": trade["final_tp_price"] + 0.1, "low": trade["entry_price"] - 0.1, "close": trade["final_tp_price"]},
    ])
    _advance_resolution(trade, resolution, bars)
    assert resolution["status"] == "CLOSED"
    assert resolution["exit_reason"] == "FINAL_TP"
    assert resolution["pnl"] == 6.25


def test_same_bar_initial_stop_has_priority():
    trade = _trade("LONG")
    resolution = _new_resolution(pd.Timestamp(trade["entry_time"]))
    bars = pd.DataFrame([
        {"time": pd.Timestamp("2026-08-03 01:00:00"), "open": 2000.0, "high": trade["final_tp_price"] + 0.1, "low": trade["sl_price"] - 0.1, "close": trade["entry_price"]},
    ])
    _advance_resolution(trade, resolution, bars)
    assert resolution["exit_reason"] == "SL"
    assert resolution["pnl"] == -5.0


def test_short_spread_is_applied_once_to_entry():
    levels = _levels(2000.0, "SHORT")
    assert levels["entry_price"] == 1999.7
    assert levels["partial_tp_price"] == 1994.7
    assert levels["sl_price"] == 2004.7


def test_episode_rearm_requires_exit_and_two_absent_closed_m15_rows():
    from scripts.gold_scalp_state_survival_shadow.common import SELECTED_STATE_ACTIONS
    from scripts.gold_scalp_state_survival_shadow.shadow_runtime import _initial_state, _update_episode_absence

    state = _initial_state(pd.Timestamp("2026-08-01 00:00:00"))
    selected = next(iter(SELECTED_STATE_ACTIONS))
    episode = state["episodes"][selected]
    episode.update({"armed": False, "position_exited": False, "absence_count": 0})
    _update_episode_absence(state, "OTHER|STATE")
    _update_episode_absence(state, "OTHER|STATE")
    assert episode["absence_count"] == 2
    assert episode["armed"] is False
    episode["position_exited"] = True
    _update_episode_absence(state, selected)
    assert episode["armed"] is False
    _update_episode_absence(state, "OTHER|STATE")
    _update_episode_absence(state, "OTHER|STATE")
    assert episode["armed"] is True


def test_discord_queue_is_persistently_deduplicated(tmp_path, monkeypatch):
    from scripts.gold_scalp_state_survival_shadow import shadow_runtime as runtime

    state = {
        "discord_queue": [{
            "event_id": "event-1",
            "entry_time": "2026-08-03 01:00:00",
            "signal_time": "2026-08-03 00:45:00",
            "state": "S01|UP|LOW|UP|NORM|WEAK",
            "action": "LONG",
            "entry_price": 2000.3,
            "partial_tp_price": 2005.3,
            "final_tp_price": 2010.3,
            "sl_price": 1995.3,
        }]
    }
    config = {
        "discord": {
            "enabled": True,
            "webhook_source": "LOCAL_CONFIG",
            "webhook_url": "https://discord.com/api/webhooks/test/token",
            "attach_chart": False,
        }
    }
    sent = []
    monkeypatch.setattr(runtime, "send", lambda *args, **kwargs: sent.append(args[2]))
    logger = type("Logger", (), {"info": lambda *args, **kwargs: None, "error": lambda *args, **kwargs: None})()
    data = {"M15": pd.DataFrame()}
    config_path = tmp_path / "local_config.json"
    runtime._deliver_discord_queue(state, config, config_path, data, tmp_path, logger)
    assert len(sent) == 1
    assert state["discord_queue"] == []
    state["discord_queue"] = [{
        "event_id": "event-1", "entry_time": "2026-08-03 01:00:00",
        "signal_time": "2026-08-03 00:45:00", "state": "x", "action": "LONG"
    }]
    runtime._deliver_discord_queue(state, config, config_path, data, tmp_path, logger)
    assert len(sent) == 1
    assert state["discord_queue"] == []
