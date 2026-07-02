from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/btc_ml_v1/research/btc5_video_5m_ema200_nwave_candidate.py"
)
spec = importlib.util.spec_from_file_location("btc5_video_5m_ema200_nwave_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_separate_touch_episodes_remain_valid_until_regime_end() -> None:
    frame = pd.DataFrame(
        {
            "touch200": [False, True, True, False, True, False],
        }
    )
    regime = module.Regime("LONG", 0, 0, 6)

    assert module.touch_events(frame, regime) == [1, 4]


def test_wick_only_touch_is_detected() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=220, freq="5min"),
            "open": [100.0] * 220,
            "high": [101.0] * 220,
            "low": [99.0] * 220,
            "close": [100.0] * 220,
        }
    )
    featured = module.read_m5_from_frame(frame)

    assert bool(featured.iloc[-1]["touch200"])


def test_entry_is_next_m5_open_and_stop_is_30_pips_beyond_c() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=8, freq="5min"),
            "open": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1080.0, 1085.0],
        }
    )
    regime = module.Regime("LONG", 0, 0, 8)
    a = module.Pivot(0, 2, 500.0)
    b = module.Pivot(2, 4, 1500.0)
    c = module.Pivot(4, 6, 900.0)

    plan = module.make_plan(frame, regime, 3, a, b, c, 5, -1.0)

    assert plan is not None
    assert plan["entry_time"] == frame.iloc[6]["time"]
    assert plan["entry_bid"] == 1080.0
    assert plan["stop_chart"] == 600.0


def test_rr_endpoints_are_not_allowed() -> None:
    assert module.RR_MIN == 1.0
    assert module.RR_MAX == 3.0
    assert not (module.RR_MIN < 1.0 < module.RR_MAX)
    assert not (module.RR_MIN < 3.0 < module.RR_MAX)


def test_post_2026_is_entry_only() -> None:
    period, period_end = module.period_for_entry(pd.Timestamp("2026-01-01 00:00:00"))

    assert period == "POST_2026_ENTRY_ONLY"
    assert period_end is None
