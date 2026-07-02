from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc10r_safe_risk_overlay.py"
spec = importlib.util.spec_from_file_location("btc10r_safe_risk_overlay", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_fixed_profile_contract() -> None:
    assert module.PROFILE_ID == "BTC10R_DEMO_FIXED_LOT_002_001_AFTER_2L_V1"
    assert module.NORMAL_LOT == 0.02
    assert module.THROTTLED_LOT == 0.01
    assert module.MAX_ALLOWED_LOT == 0.05
    assert module.LOSS_STREAK_TRIGGER == 2


def test_only_resolved_exits_before_entry_update_streak() -> None:
    trades = pd.DataFrame(
        {
            "entry_time": pd.to_datetime(
                [
                    "2026-01-01 00:00",
                    "2026-01-01 01:00",
                    "2026-01-01 03:00",
                    "2026-01-01 06:00",
                    "2026-01-01 08:00",
                ]
            ),
            "exit_time": pd.to_datetime(
                [
                    "2026-01-01 05:00",
                    "2026-01-01 02:00",
                    "2026-01-01 07:00",
                    "2026-01-01 06:30",
                    "2026-01-01 09:00",
                ]
            ),
            "risk_pips": [100.0] * 5,
            "pnl_pips": [-100.0, -100.0, 225.0, 225.0, -100.0],
        }
    )

    result = module.apply_overlay(trades)

    assert result["assigned_lot"].tolist() == [0.02, 0.02, 0.02, 0.01, 0.02]
    assert result["resolved_loss_streak_before_entry"].tolist() == [0, 0, 1, 2, 0]


def test_overlay_rejects_nonpositive_risk() -> None:
    trades = pd.DataFrame(
        {
            "entry_time": pd.to_datetime(["2026-01-01 00:00"]),
            "exit_time": pd.to_datetime(["2026-01-01 01:00"]),
            "risk_pips": [0.0],
            "pnl_pips": [10.0],
        }
    )

    try:
        module.apply_overlay(trades)
    except ValueError as exc:
        assert "risk_pips must be positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")
