from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gold_wave_shadow_v19.frozen_router import (  # noqa: E402
    E40_HORIZON,
    active_boundary,
    apply_causal_session_guard,
    score_maturity,
)
from gold_wave_shadow_v19.shadow_runtime import default_state, update_episode  # noqa: E402


def test_active_boundary_is_january_or_july() -> None:
    assert active_boundary(pd.Timestamp("2026-06-30 23:45")) == pd.Timestamp("2026-01-01")
    assert active_boundary(pd.Timestamp("2026-07-01 00:00")) == pd.Timestamp("2026-07-01")
    assert active_boundary(pd.Timestamp("2027-02-15 12:00")) == pd.Timestamp("2027-01-01")


def test_causal_session_guard_excludes_late_origin() -> None:
    m1 = pd.DataFrame({"time": pd.date_range("2026-07-06 01:00", periods=1380, freq="min")})
    origins = pd.DataFrame(
        {
            "entry_time": [pd.Timestamp("2026-07-06 10:00"), pd.Timestamp("2026-07-06 13:00")],
            "entry_idx": [540, 720],
            "origin_id": [1, 2],
        }
    )
    guarded = apply_causal_session_guard(origins, m1)
    assert guarded.origin_id.tolist() == [1]
    assert bool(guarded.session_guard.iloc[0])


def test_score_maturity_requires_exact_contiguous_horizon() -> None:
    m1 = pd.DataFrame({"time": pd.date_range("2026-07-06 01:00", periods=E40_HORIZON + 2, freq="min")})
    rows = pd.DataFrame({"entry_time": [m1.time.iloc[0]], "origin_id": [1]})
    assert score_maturity(rows, m1).iloc[0] == "VALID"
    broken = m1.drop(index=100).reset_index(drop=True)
    assert score_maturity(rows, broken).iloc[0] == "INVALID_GAP"


def test_episode_restarts_after_non_early_state() -> None:
    state = default_state()
    t0 = pd.Timestamp("2026-07-06 10:00")
    first = update_episode(state, "LONG", "IMPULSE_EARLY", t0, None)
    second = update_episode(state, "LONG", "IMPULSE_EARLY", t0 + pd.Timedelta(minutes=15), t0)
    update_episode(state, "LONG", "IMPULSE_MID", t0 + pd.Timedelta(minutes=30), t0 + pd.Timedelta(minutes=15))
    third = update_episode(state, "LONG", "IMPULSE_EARLY", t0 + pd.Timedelta(minutes=45), t0 + pd.Timedelta(minutes=30))
    assert first == second
    assert third != first
