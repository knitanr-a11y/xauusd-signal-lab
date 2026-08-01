from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.gold_challenger_c1.shadow_runtime import (  # noqa: E402
    HORIZON_M1,
    V19Interval,
    V19View,
    _entry_prices,
    default_state,
    process_new_decisions,
    process_open_trade,
    read_csv_records,
)


def view(*intervals: V19Interval, entries=()) -> V19View:
    return V19View(
        ready=True,
        status="READY",
        activated=True,
        parity="PASS",
        last_processed=pd.Timestamp("2026-08-01 12:00"),
        intervals=list(intervals),
        entry_times={pd.Timestamp(x) for x in entries},
        score_ledger=pd.DataFrame(),
        state_root=Path("/v19-read-only"),
        details={},
    )


def m1_frame(start="2026-08-01 10:00", periods=600, open_price=2400.0):
    times = pd.date_range(start, periods=periods, freq="min")
    return pd.DataFrame(
        {
            "time": times,
            "open": np.full(periods, open_price),
            "high": np.full(periods, open_price + 1.0),
            "low": np.full(periods, open_price - 1.0),
        }
    )


def open_trade(side="LONG"):
    entry, tp, sl = _entry_prices(side, 2400.0)
    return {
        "candidate_id": 1,
        "origin_id": 2,
        "decision_dt": pd.Timestamp("2026-08-01 10:00"),
        "entry_dt": pd.Timestamp("2026-08-01 10:00"),
        "entry_idx": 0,
        "side": side,
        "chosen_rank": 0.5,
        "wave_state": "IMPULSE_LATE",
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "last_checked_idx": -1,
    }


def test_same_m1_tp_sl_is_sl_first(tmp_path):
    frame = m1_frame(periods=2)
    frame.loc[0, "high"] = 2425.0
    frame.loc[0, "low"] = 2380.0
    state = default_state()
    state["open_trade"] = open_trade("LONG")
    process_open_trade(state, tmp_path, frame, view())
    row = read_csv_records(tmp_path / "outputs" / "shadow_trade_ledger.csv")[-1]
    assert row["exit_reason"] == "SL"
    assert float(row["pnl"]) == -10.0


def test_time_exit_uses_boundary_open_before_high_low(tmp_path):
    frame = m1_frame(periods=HORIZON_M1 + 1)
    frame.loc[HORIZON_M1, "high"] = 2500.0
    frame.loc[HORIZON_M1, "low"] = 2300.0
    state = default_state()
    state["open_trade"] = open_trade("LONG")
    process_open_trade(state, tmp_path, frame, view())
    row = read_csv_records(tmp_path / "outputs" / "shadow_trade_ledger.csv")[-1]
    assert row["exit_reason"] == "TIME"
    assert abs(float(row["pnl"]) + 0.3) < 1e-9


def test_v19_preempt_only_at_actual_timestamp(tmp_path):
    frame = m1_frame(periods=5)
    state = default_state()
    state["open_trade"] = open_trade("LONG")
    actual = pd.Timestamp(frame.time.iloc[3])
    process_open_trade(state, tmp_path, frame, view(entries=[actual]))
    row = read_csv_records(tmp_path / "outputs" / "shadow_trade_ledger.csv")[-1]
    assert row["exit_reason"] == "V19_PREEMPT"
    assert pd.Timestamp(row["exit_dt"]) == actual


def timeline(decision="2026-08-01 10:15"):
    return pd.DataFrame(
        [
            {
                "decision_dt": pd.Timestamp(decision),
                "origin_id": 10,
                "entry_idx": 15,
                "chosen_side": "LONG",
                "chosen_rank": 0.55,
                "wave_state": "CORRECTION_EARLY",
                "episode_id": 2,
                "previous_decision_dt": pd.Timestamp(decision) - pd.Timedelta(minutes=15),
                "eligible": True,
                "causal_zone": "SUBP90_CORRECTION_EARLY",
                "event_onset": True,
                "candidate_id": 3,
            }
        ]
    )


def test_v19_open_suppresses_candidate(tmp_path):
    frame = m1_frame(periods=16)
    state = default_state()
    state["activated"] = True
    state["last_processed_decision_dt"] = pd.Timestamp("2026-08-01 10:00")
    interval = V19Interval(pd.Timestamp("2026-08-01 10:00"), pd.Timestamp("2026-08-01 10:20"))
    process_new_decisions(state, tmp_path, timeline(), frame, view(interval), allow_new_entries=True)
    assert state["open_trade"] is None
    assert state["counters"]["suppressed_v19_priority"] == 1


def test_recovery_candidate_is_not_backfilled(tmp_path):
    frame = m1_frame(periods=30)
    state = default_state()
    state["activated"] = True
    state["last_processed_decision_dt"] = pd.Timestamp("2026-08-01 10:00")
    process_new_decisions(state, tmp_path, timeline(), frame, view(), allow_new_entries=False)
    assert state["open_trade"] is None
    assert state["counters"]["recovery_replay_not_traded"] == 1


def test_continuous_candidate_is_accepted(tmp_path):
    frame = m1_frame(periods=16)
    state = default_state()
    state["activated"] = True
    state["last_processed_decision_dt"] = pd.Timestamp("2026-08-01 10:00")
    process_new_decisions(state, tmp_path, timeline(), frame, view(), allow_new_entries=True)
    assert state["counters"]["accepted_trades"] == 1
    rows = read_csv_records(tmp_path / "outputs" / "shadow_candidate_ledger.csv")
    assert rows[-1]["status"] == "ACCEPTED"


def test_v19_view_requires_exact_score_cursor_and_ignores_candidate_as_open(tmp_path):
    from scripts.gold_challenger_c1.shadow_runtime import load_v19_view, write_json

    v19_state = tmp_path / "v19_state"
    (v19_state / "outputs").mkdir(parents=True)
    write_json(
        tmp_path / "v19_config.json",
        {
            "shadow_id": "GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW",
            "state_dir": str(v19_state),
            "data_sources": {},
            "discord": {},
        },
    )
    write_json(
        v19_state / "runtime_state.json",
        {
            "activated": True,
            "last_processed_decision_time": "2026-08-01 10:15:00",
            "open_trade": None,
        },
    )
    write_json(v19_state / "runtime_health.json", {"status": "READY", "v19_parity": "PASS"})
    pd.DataFrame(
        [
            {
                "decision_time": "2026-08-01 10:15:00",
                "origin_id": 1,
                "entry_idx": 15,
                "selected_side": "LONG",
                "selected_rank": 0.95,
                "schedule": "SEMIANNUAL_EXPANDING",
            }
        ]
    ).to_csv(v19_state / "outputs" / "shadow_score_ledger.csv", index=False)
    pd.DataFrame([{"entry_time": "2026-07-01 10:00:00"}]).to_csv(
        v19_state / "outputs" / "shadow_candidate_ledger.csv", index=False
    )
    result = load_v19_view({"v19": {"local_config_path": str(tmp_path / "v19_config.json")}})
    assert result.ready
    assert result.last_processed == pd.Timestamp("2026-08-01 10:15:00")
    assert result.score_ledger.chosen_side.tolist() == ["LONG"]
    assert not result.open_at(pd.Timestamp("2026-08-01 10:15:00"))


def test_v19_score_cursor_mismatch_fails_ready(tmp_path):
    from scripts.gold_challenger_c1.shadow_runtime import load_v19_view, write_json

    v19_state = tmp_path / "v19_state"
    (v19_state / "outputs").mkdir(parents=True)
    write_json(tmp_path / "v19_config.json", {"shadow_id": "GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW", "state_dir": str(v19_state), "data_sources": {}, "discord": {}})
    write_json(v19_state / "runtime_state.json", {"activated": True, "last_processed_decision_time": "2026-08-01 10:30:00"})
    write_json(v19_state / "runtime_health.json", {"status": "READY", "v19_parity": "PASS"})
    pd.DataFrame([{"decision_time": "2026-08-01 10:15:00", "selected_side": "SHORT", "selected_rank": 0.50}]).to_csv(v19_state / "outputs" / "shadow_score_ledger.csv", index=False)
    result = load_v19_view({"v19": {"local_config_path": str(tmp_path / "v19_config.json")}})
    assert not result.ready
    assert result.details["score_cursor_match"] is False


def test_stale_single_candidate_is_not_backfilled(tmp_path):
    frame = m1_frame(periods=31)
    state = default_state()
    state["activated"] = True
    state["last_processed_decision_dt"] = pd.Timestamp("2026-08-01 10:00")
    process_new_decisions(state, tmp_path, timeline(), frame, view(), allow_new_entries=True)
    assert state["open_trade"] is None
    assert state["counters"]["recovery_replay_not_traded"] == 1
    rows = read_csv_records(tmp_path / "outputs" / "shadow_candidate_ledger.csv")
    assert rows[-1]["reason"] == "RECOVERY_REPLAY_NOT_TRADED_STALE_M1_CURSOR"


def test_v19_score_ledger_can_reconstruct_chosen_fields_from_directional_ranks(tmp_path):
    from scripts.gold_challenger_c1.shadow_runtime import load_v19_view, write_json

    v19_state = tmp_path / "v19_state"
    (v19_state / "outputs").mkdir(parents=True)
    write_json(tmp_path / "v19_config.json", {"shadow_id": "GOLD_V19_FIRST_P90_IMPULSE_EARLY_SHADOW", "state_dir": str(v19_state), "data_sources": {}, "discord": {}})
    write_json(v19_state / "runtime_state.json", {"activated": True, "last_processed_decision_time": "2026-08-01 10:15:00"})
    write_json(v19_state / "runtime_health.json", {"status": "READY", "v19_parity": "PASS"})
    pd.DataFrame([{"decision_time": "2026-08-01 10:15:00", "rank_long": 0.72, "rank_short": 0.41}]).to_csv(v19_state / "outputs" / "shadow_score_ledger.csv", index=False)
    result = load_v19_view({"v19": {"local_config_path": str(tmp_path / "v19_config.json")}})
    assert result.ready
    assert result.score_ledger.chosen_side.tolist() == ["LONG"]
    assert result.score_ledger.chosen_rank.tolist() == [0.72]
