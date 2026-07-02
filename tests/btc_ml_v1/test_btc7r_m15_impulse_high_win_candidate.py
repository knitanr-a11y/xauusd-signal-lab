from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc7r_m15_impulse_high_win_candidate.py"
spec = importlib.util.spec_from_file_location("btc7r_m15_impulse_high_win_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_high_win_contract_is_frozen() -> None:
    assert module.TREND_AGE_MIN_HOURS == 24.0
    assert module.TREND_AGE_MAX_HOURS == 96.0
    assert module.IMPULSE_ATR_MIN == 2.2
    assert module.TARGET_R == 1.1
    assert module.MIN_REWARD_PIPS == 50.0


def test_run_age_resets_when_trend_condition_breaks() -> None:
    mask = pd.Series([False, True, True, False, True, True, True])

    assert module._run_age(mask).tolist() == [0, 1, 2, 0, 1, 2, 3]


def test_refinement_uses_age_impulse_and_minimum_reward() -> None:
    plans = pd.DataFrame(
        [
            {
                "signal_time": pd.Timestamp("2025-01-01 00:00"),
                "entry_time": pd.Timestamp("2025-01-01 00:15"),
                "direction": "LONG",
                "entry_bid": 10000.0,
                "risk_pips": 50.0,
                "impulse_atr_multiple": 2.2,
                "target_chart": 0.0,
                "reward_pips": 100.0,
                "rr": 2.0,
            },
            {
                "signal_time": pd.Timestamp("2025-01-01 00:15"),
                "entry_time": pd.Timestamp("2025-01-01 00:30"),
                "direction": "LONG",
                "entry_bid": 10000.0,
                "risk_pips": 40.0,
                "impulse_atr_multiple": 2.5,
                "target_chart": 0.0,
                "reward_pips": 80.0,
                "rr": 2.0,
            },
            {
                "signal_time": pd.Timestamp("2025-01-01 00:30"),
                "entry_time": pd.Timestamp("2025-01-01 00:45"),
                "direction": "SHORT",
                "entry_bid": 10000.0,
                "risk_pips": 60.0,
                "impulse_atr_multiple": 2.1,
                "target_chart": 0.0,
                "reward_pips": 120.0,
                "rr": 2.0,
            },
        ]
    )
    ages = pd.DataFrame(
        {
            "signal_time": plans["signal_time"],
            "long_trend_age_hours": [24.0, 48.0, 0.0],
            "short_trend_age_hours": [0.0, 0.0, 96.0],
        }
    )

    refined = module.refine_plans(plans, ages)

    assert len(refined) == 1
    row = refined.iloc[0]
    assert row["reward_pips"] == 55.0
    assert row["rr"] == 1.1
    assert row["target_chart"] == 10580.0


def test_post_2026_remains_entry_only() -> None:
    period, end = module.base.period_for_entry(pd.Timestamp("2026-01-01 00:00:00"))

    assert period == "POST_2026_ENTRY_ONLY"
    assert end is None
