from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "btc6_video_m15_ema200_nwave_candidate.py"
spec = importlib.util.spec_from_file_location("btc6_video_m15_ema200_nwave_candidate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_m15_time_windows_preserve_24h_and_6h() -> None:
    assert module.AB_LOOKBACK_BARS == 96
    assert module.DOUBLE_MAX_SEPARATION_BARS_EQUIVALENT == 24
    assert module.TIMEFRAME_MINUTES == 15


def test_m15_uses_pivot_width_three_and_broad_n_band() -> None:
    assert module.PIVOT_WIDTH == 3
    assert module.N_RETRACE_MIN == 0.236
    assert module.N_RETRACE_MAX == 0.886
    assert module.CANDIDATE_ID == "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886"


def test_m15_simulation_closes_at_m15_bar_end_and_uses_sl_first() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.to_datetime(["2025-01-01 00:00", "2025-01-01 00:15"]),
            "high": [102.0, 102.0],
            "low": [98.0, 98.0],
        }
    )
    plan = pd.Series(
        {
            "direction": "LONG",
            "entry_idx": 0,
            "stop_chart": 99.0,
            "target_chart": 101.0,
            "risk_pips": 10.0,
            "reward_pips": 20.0,
        }
    )

    result = module.simulate(frame, plan, pd.Timestamp("2025-02-01"))

    assert result["exit_reason"] == "SL"
    assert result["pnl_pips"] == -10.0
    assert result["exit_time"] == pd.Timestamp("2025-01-01 00:15")


def test_post_2026_outcomes_remain_entry_only() -> None:
    period, end = module.engine.period_for_entry(pd.Timestamp("2026-01-01 00:00:00"))

    assert period == "POST_2026_ENTRY_ONLY"
    assert end is None


def test_main_serializes_cli_result_and_returns_zero(monkeypatch, capsys, tmp_path: Path) -> None:
    expected = {
        "summary": [
            {
                "trades": np.int64(3),
                "profit_factor": np.float64(2.5),
                "generated_at": pd.Timestamp("2026-07-02 02:15:00"),
            }
        ],
        "contract": {"orders_enabled": False},
    }
    monkeypatch.setattr(module, "run", lambda _m15, _out: expected)

    return_code = module.main(
        ["--m15", str(tmp_path / "m15.csv"), "--out", str(tmp_path / "out")]
    )
    payload = json.loads(capsys.readouterr().out)

    assert return_code == 0
    assert payload["summary"][0]["trades"] == 3
    assert payload["summary"][0]["profit_factor"] == 2.5
    assert payload["summary"][0]["generated_at"] == "2026-07-02T02:15:00"
    assert payload["contract"]["orders_enabled"] is False
