from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc9_m15_prevday_breakout_candidate.py"
spec = importlib.util.spec_from_file_location("btc9_m15_prevday_breakout_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_candidate_contract_is_frozen() -> None:
    assert module.H1_TREND_SEPARATION_ATR == 0.5
    assert module.CLOSE_LOCATION == 0.85
    assert module.STOP_ATR_BUFFER == 0.1
    assert module.RISK_CAP_PIPS == 100.0
    assert module.TARGET_R == 1.1
    assert module.MIN_REWARD_PIPS == 50.0


def test_previous_day_levels_are_not_available_before_next_utc_day() -> None:
    m15 = pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2025-01-01 23:45", "2025-01-02 00:00", "2025-01-02 00:15"]
            )
        }
    )
    d1 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00"]),
            "high": [110.0],
            "low": [90.0],
        }
    )

    aligned = module.align_previous_day(m15, d1)

    assert pd.isna(aligned.iloc[0]["previous_day_high"])
    assert aligned.iloc[1]["previous_day_high"] == 110.0
    assert aligned.iloc[2]["previous_day_low"] == 90.0


def test_period_split_keeps_post_2026_entry_only() -> None:
    assert module.period_for_entry(pd.Timestamp("2024-08-01"))[0] == "TRAIN"
    assert module.period_for_entry(pd.Timestamp("2025-02-01"))[0] == "DEV"
    assert module.period_for_entry(pd.Timestamp("2025-07-01"))[0] == "VALIDATION"
    period, end = module.period_for_entry(pd.Timestamp("2026-01-01"))
    assert period == "POST_2026_ENTRY_ONLY"
    assert end is None


def test_same_m5_bar_is_sl_first() -> None:
    m5 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:15"]),
            "high": [110.0],
            "low": [90.0],
        }
    )
    plan = pd.Series(
        {
            "entry_m5_idx": 0,
            "direction": "LONG",
            "stop_chart": 95.0,
            "target_chart": 105.0,
            "risk_pips": 10.0,
            "reward_pips": 11.0,
        }
    )

    result = module.simulate(m5, plan, pd.Timestamp("2025-02-01"))

    assert result["exit_reason"] == "SL"
    assert result["pnl_pips"] == -10.0
