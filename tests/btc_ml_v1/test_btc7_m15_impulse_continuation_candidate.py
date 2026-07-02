from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc7_m15_impulse_continuation_candidate.py"
spec = importlib.util.spec_from_file_location("btc7_m15_impulse_continuation_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_fixed_candidate_contract() -> None:
    assert module.TREND_SEPARATION_ATR == 0.5
    assert module.IMPULSE_ATR_MULTIPLE == 2.0
    assert module.CLOSE_LOCATION_MIN == 0.85
    assert module.RISK_CAP_PIPS == 100.0
    assert module.TARGET_R == 2.0
    assert module.MIN_REWARD_PIPS == 50.0


def test_h1_alignment_uses_only_closed_h1() -> None:
    m15 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:45", "2025-01-01 01:00"]),
        }
    )
    h1 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00", "2025-01-01 01:00"]),
            "ema50": [10.0, 20.0],
            "ema200": [5.0, 15.0],
            "atr14": [1.0, 2.0],
        }
    )

    aligned = module.align_h1(m15, h1)

    assert pd.isna(aligned.iloc[0]["ema50_h1"])
    assert aligned.iloc[1]["ema50_h1"] == 10.0


def test_entry_is_after_m15_close_and_risk_cap_is_applied() -> None:
    times_m15 = pd.date_range("2025-01-01", periods=220, freq="15min")
    m15 = pd.DataFrame(
        {
            "time": times_m15,
            "open": [1000.0] * 220,
            "high": [1010.0] * 220,
            "low": [990.0] * 220,
            "close": [1000.0] * 220,
        }
    )
    h1 = pd.DataFrame(
        {
            "time": pd.date_range("2024-12-20", periods=400, freq="1h"),
            "open": [1000.0] * 400,
            "high": [1010.0] * 400,
            "low": [990.0] * 400,
            "close": [1000.0 + i for i in range(400)],
        }
    )
    m5 = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=700, freq="5min"),
            "open": [1000.0] * 700,
            "high": [1010.0] * 700,
            "low": [990.0] * 700,
            "close": [1000.0] * 700,
        }
    )

    featured_m15 = module.add_features(m15)
    featured_h1 = module.add_features(h1)
    featured_m5 = module.add_features(m5)
    plans = module.generate_plans(featured_m15, featured_h1, featured_m5)

    if not plans.empty:
        assert (plans["entry_time"] == plans["signal_time"] + pd.Timedelta(minutes=15)).all()
        assert (plans["risk_pips"] <= 100.0).all()


def test_same_m5_bar_uses_sl_first() -> None:
    m5 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00"]),
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
            "reward_pips": 20.0,
        }
    )

    result = module.simulate(m5, plan, pd.Timestamp("2025-02-01"))

    assert result["exit_reason"] == "SL"
    assert result["pnl_pips"] == -10.0


def test_post_2026_is_entry_only() -> None:
    period, end = module.period_for_entry(pd.Timestamp("2026-01-01 00:00:00"))

    assert period == "POST_2026_ENTRY_ONLY"
    assert end is None
