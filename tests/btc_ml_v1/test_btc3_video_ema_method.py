from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts/btc_ml_v1/research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
MODULE_PATH = SCRIPT_DIR / "btc3_video_ema_method_exploration.py"
RUNNER_PATH = SCRIPT_DIR / "run_btc3_video_ema_user_contract.py"
COMPAT_PATH = SCRIPT_DIR / "mt5_indicator_compat.py"

spec = importlib.util.spec_from_file_location("btc3_video_ema_method_exploration", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

compat_spec = importlib.util.spec_from_file_location("mt5_indicator_compat", COMPAT_PATH)
assert compat_spec and compat_spec.loader
compat = importlib.util.module_from_spec(compat_spec)
sys.modules[compat_spec.name] = compat
compat_spec.loader.exec_module(compat)

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


def test_mt5_ema_uses_sma_seed_then_recursive_formula() -> None:
    actual = compat.mt5_ema([1.0, 2.0, 3.0, 4.0, 5.0], 3)
    expected = np.array([np.nan, np.nan, 2.0, 3.0, 4.0])
    np.testing.assert_allclose(actual, expected, equal_nan=True)


def test_applied_price_formulas_are_explicit() -> None:
    frame = pd.DataFrame({"high": [12.0], "low": [6.0], "close": [10.0]})
    assert compat.applied_price(frame, "close").iloc[0] == 10.0
    assert compat.applied_price(frame, "typical").iloc[0] == pytest.approx(28.0 / 3.0)
    assert compat.applied_price(frame, "weighted").iloc[0] == 9.5
    with pytest.raises(ValueError, match="unsupported EMA applied price"):
        compat.applied_price(frame, "unknown")


def test_runner_requires_explicit_applied_price() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args([])
    args = runner.parse_args(["--ema-applied-price", "typical"])
    assert args.ema_applied_price == "typical"


def test_mt5_atr_uses_wilder_sma_seed() -> None:
    actual = compat.mt5_atr(
        high=[10.0, 12.0, 13.0, 15.0],
        low=[8.0, 9.0, 10.0, 11.0],
        close=[9.0, 11.0, 12.0, 14.0],
        period=3,
    )
    expected = np.array([np.nan, np.nan, 8.0 / 3.0, 28.0 / 9.0])
    np.testing.assert_allclose(actual, expected, equal_nan=True)


def test_h4_warmup_is_mandatory() -> None:
    frame = pd.DataFrame(
        {"time": pd.date_range("2024-01-01", periods=100, freq="4h")}
    )
    with pytest.raises(ValueError, match="Insufficient H4 EMA warm-up"):
        compat.require_h4_warmup(
            frame,
            research_start=pd.Timestamp("2024-07-03"),
            minimum_closed_bars=1500,
        )


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


def test_wick_through_ema200_discards_basis_and_waits_for_next_valid_touch() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2024-10-04 12:00:00", periods=4, freq="4h"),
            "open": [110.0, 114.0, 112.0, 116.0],
            "high": [115.0, 120.0, 118.0, 121.0],
            "low": [108.0, 95.0, 105.0, 114.0],
            "close": [114.0, 115.0, 112.0, 119.0],
            "ema20": [110.0, 110.0, 110.0, 112.0],
            "ema200": [100.0, 100.0, 100.0, 101.0],
            "atr14": [500.0] * 4,
            "cross_long": [True, False, False, False],
            "cross_short": [False, False, False, False],
        }
    )

    setup = runner._generate_setups(frame)[0]

    assert setup.status == "TRIGGERED"
    assert setup.touch_idx == 2
    assert setup.trigger_idx == 3


def test_structural_stop_uses_ema200_below_valid_long_touch() -> None:
    frame = pd.DataFrame(
        {
            "low": [105.0],
            "high": [120.0],
            "ema200": [100.0],
            "atr14": [500.0],
        }
    )

    anchor, buffer_usd, stop = runner._structural_stop(frame, 0, "LONG")

    assert anchor == 100.0
    assert buffer_usd == 50.0
    assert stop == 50.0


def test_official_runner_patches_selected_mt5_price_and_pre_entry_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(args: Namespace) -> dict[str, object]:
        captured["close_on_ema200_invalidation"] = args.close_on_ema200_invalidation
        captured["add_h4_features"] = runner.engine._add_h4_features
        captured["generate_setups"] = runner.engine._generate_setups
        captured["build_plan"] = runner.engine._build_plan
        return {}

    monkeypatch.setattr(runner.engine, "run", fake_run)
    args = Namespace(
        close_on_ema200_invalidation=True,
        ema_applied_price="weighted",
    )
    result = runner.run(args)

    assert captured["close_on_ema200_invalidation"] is False
    assert callable(captured["add_h4_features"])
    assert captured["generate_setups"] is runner._generate_setups
    assert captured["build_plan"] is runner._build_plan
    assert result["indicator_contract"] == "MT5_SMA_SEEDED_EMA_AND_WILDER_ATR"
    assert result["ema_applied_price"] == "weighted"
    assert result["pre_entry_ema200_invalidation_only"] is True
    assert result["post_entry_exit_contract"] == "STRUCTURAL_SL_TP_ONLY_NO_EMA200_EXIT"
