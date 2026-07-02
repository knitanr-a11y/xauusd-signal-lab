from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc10r_m15_ema20_shallow_pullback_strong_close_candidate.py"
spec = importlib.util.spec_from_file_location(
    "btc10r_m15_ema20_shallow_pullback_strong_close_candidate",
    SCRIPT,
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_fixed_contract() -> None:
    assert module.CANDIDATE_ID == "BTC10R_M15_EMA20_SHALLOW_PULLBACK_STRONG_CLOSE_R225"
    assert module.MAX_PULLBACK_DEPTH_ATR == 0.6
    assert module.MIN_DIRECTIONAL_CLOSE_LOCATION == 0.85
    assert module.parent.TARGET_R == 2.25


def test_accepts_shallow_pullback_and_strong_long_close() -> None:
    m15 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00", "2025-01-01 00:15"]),
            "close": [99.6, 101.0],
            "ema20": [100.0, 100.5],
            "atr14": [1.0, 1.0],
        }
    )
    plans = pd.DataFrame(
        [
            {
                "signal_time": pd.Timestamp("2025-01-01 00:15"),
                "entry_time": pd.Timestamp("2025-01-01 00:30"),
                "direction": "LONG",
                "close_location": 0.90,
            }
        ]
    )

    result = module.apply_quality_filters(plans, m15)

    assert len(result) == 1
    assert abs(result.iloc[0]["pullback_depth_atr"] - 0.4) < 1e-12


def test_rejects_deep_pullback_or_weak_close() -> None:
    m15 = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00", "2025-01-01 00:15"]),
            "close": [99.3, 101.0],
            "ema20": [100.0, 100.5],
            "atr14": [1.0, 1.0],
        }
    )
    deep = pd.DataFrame(
        [
            {
                "signal_time": pd.Timestamp("2025-01-01 00:15"),
                "entry_time": pd.Timestamp("2025-01-01 00:30"),
                "direction": "LONG",
                "close_location": 0.90,
            }
        ]
    )
    weak = pd.DataFrame(
        [
            {
                "signal_time": pd.Timestamp("2025-01-01 00:15"),
                "entry_time": pd.Timestamp("2025-01-01 00:30"),
                "direction": "LONG",
                "close_location": 0.84,
            }
        ]
    )

    assert module.apply_quality_filters(deep, m15).empty
    m15.loc[0, "close"] = 99.6
    assert module.apply_quality_filters(weak, m15).empty
