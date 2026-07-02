from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc9r_m15_prevday_breakout_high_win_candidate.py"
spec = importlib.util.spec_from_file_location("btc9r_m15_prevday_breakout_high_win_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_high_win_contract_is_frozen() -> None:
    assert module.TARGET_R == 0.8
    assert module.MIN_REWARD_PIPS == 50.0
    assert module.MIN_REWARD_PIPS / module.TARGET_R == 62.5


def test_minimum_reward_filters_small_risk_and_recalculates_target() -> None:
    plans = pd.DataFrame(
        [
            {
                "direction": "LONG",
                "entry_time": pd.Timestamp("2025-01-01"),
                "entry_bid": 10000.0,
                "risk_pips": 62.4,
                "reward_pips": 68.64,
                "rr": 1.1,
                "target_chart": 0.0,
            },
            {
                "direction": "LONG",
                "entry_time": pd.Timestamp("2025-01-02"),
                "entry_bid": 10000.0,
                "risk_pips": 62.5,
                "reward_pips": 68.75,
                "rr": 1.1,
                "target_chart": 0.0,
            },
            {
                "direction": "SHORT",
                "entry_time": pd.Timestamp("2025-01-03"),
                "entry_bid": 10000.0,
                "risk_pips": 100.0,
                "reward_pips": 110.0,
                "rr": 1.1,
                "target_chart": 0.0,
            },
        ]
    )

    refined = module.refine_plans(plans)

    assert len(refined) == 2
    long_row = refined.iloc[0]
    short_row = refined.iloc[1]
    assert long_row["reward_pips"] == pytest.approx(50.0)
    assert long_row["target_chart"] == pytest.approx(10530.0)
    assert short_row["reward_pips"] == pytest.approx(80.0)
    assert short_row["target_chart"] == pytest.approx(9170.0)


def test_post_2026_stays_entry_only() -> None:
    period, end = module.base.period_for_entry(pd.Timestamp("2026-01-01"))

    assert period == "POST_2026_ENTRY_ONLY"
    assert end is None
