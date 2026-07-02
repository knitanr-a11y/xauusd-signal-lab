from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
MODULE_PATH = SCRIPT_DIR / "btc3_video_ema_method_exploration.py"
RUNNER_PATH = SCRIPT_DIR / "run_btc3_video_ema_user_contract.py"

spec = importlib.util.spec_from_file_location("btc3_video_ema_method_exploration", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

runner_spec = importlib.util.spec_from_file_location("run_btc3_video_ema_user_contract", RUNNER_PATH)
assert runner_spec and runner_spec.loader
runner = importlib.util.module_from_spec(runner_spec)
sys.modules[runner_spec.name] = runner
runner_spec.loader.exec_module(runner)


def test_h4_decision_uses_bar_close_not_open() -> None:
    rows = 220
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=rows, freq="4h"),
            "open": range(rows),
            "high": [value + 2 for value in range(rows)],
            "low": [value - 2 for value in range(rows)],
            "close": [value + 1 for value in range(rows)],
            "tick_volume": [1] * rows,
            "spread": [3000] * rows,
            "real_volume": [0] * rows,
        }
    )
    output = module._add_h4_features(frame)
    assert output.loc[0, "decision_time"] == frame.loc[0, "time"] + pd.Timedelta(hours=4)


def test_target_selection_skips_near_and_sub_rr_levels() -> None:
    selected = module._select_targets(
        [100.0, 600.0, 900.0, 1200.0, 1500.0],
        direction="LONG",
        entry_bid=0.0,
        spread_usd=30.0,
        risk_net_usd=1000.0,
        atr14=500.0,
    )
    assert selected is not None
    assert selected["tp1"] == 1200.0
    assert selected["tp1_net_usd"] == 1170.0
    assert selected["tp2"] == 1500.0


def test_short_target_includes_spread() -> None:
    selected = module._select_targets(
        [9400.0, 8500.0, 8000.0],
        direction="SHORT",
        entry_bid=10000.0,
        spread_usd=30.0,
        risk_net_usd=500.0,
        atr14=500.0,
    )
    assert selected is not None
    assert selected["tp1_net_usd"] == 570.0


def test_post_2026_period_is_entry_only() -> None:
    period, end = module._period_for_entry(pd.Timestamp("2026-01-01 00:00:00"))
    assert period == "POST_2026_ENTRY_ONLY"
    assert end is None


def test_official_runner_forces_pre_entry_only_ema200_invalidation(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(args: Namespace) -> dict[str, object]:
        captured["close_on_ema200_invalidation"] = args.close_on_ema200_invalidation
        return {}

    monkeypatch.setattr(runner.engine, "run", fake_run)
    args = Namespace(close_on_ema200_invalidation=True)
    result = runner.run(args)

    assert captured["close_on_ema200_invalidation"] is False
    assert result["pre_entry_ema200_invalidation_only"] is True
    assert result["post_entry_exit_contract"] == "STRUCTURAL_SL_TP_ONLY_NO_EMA200_EXIT"
