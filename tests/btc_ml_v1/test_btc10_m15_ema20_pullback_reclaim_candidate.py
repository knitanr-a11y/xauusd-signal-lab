from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc10_m15_ema20_pullback_reclaim_candidate.py"
spec = importlib.util.spec_from_file_location("btc10_m15_ema20_pullback_reclaim_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_fixed_contract() -> None:
    assert module.RECENT_STOP_BARS == 8
    assert module.H1_TREND_SEPARATION_ATR_MIN == 0.5
    assert module.CLOSE_LOCATION_MIN == 0.6
    assert module.TARGET_R == 2.25
    assert module.MIN_RISK_PIPS == 62.5
    assert module.MIN_REWARD_PIPS == 140.625
    assert module.RISK_CAP_PIPS == 120.0
    assert module.COOLDOWN_M15_BARS == 12


def test_candidate_id() -> None:
    assert module.CANDIDATE_ID == "BTC10_M15_EMA20_PULLBACK_RECLAIM_H1_TREND_R225"


def test_base_simulation_uses_sl_first() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00"]),
            "high": [102.0],
            "low": [98.0],
        }
    )
    plan = pd.Series(
        {
            "direction": "LONG",
            "entry_m5_idx": 0,
            "stop_chart": 99.0,
            "target_chart": 101.0,
            "risk_pips": 10.0,
            "reward_pips": 22.5,
        }
    )

    result = module.base.simulate(frame, plan, pd.Timestamp("2025-02-01"))

    assert result["exit_reason"] == "SL"
    assert result["pnl_pips"] == -10.0
