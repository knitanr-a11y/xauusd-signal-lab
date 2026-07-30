from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "btc_ml_v1"
    / "BCR09_shared_retrospective_value_gate"
    / "python"
    / "run_bcr09_shared_value_gate.py"
)
spec = importlib.util.spec_from_file_location("bcr09", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def row(**kwargs):
    defaults = dict(
        common_eligible=True,
        p_rci9_turn_up=False,
        p_rci9_turn_down=False,
        p_rci9=0.0,
        p_ema_alignment="MIXED",
        p_ret1_bps=0.0,
        p_ema20=100.0,
        p_ema30_slope4=0.0,
        open=100.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_frozen_machine_inventory_and_scenarios() -> None:
    assert list(module.TRACK_A) == [
        "TRACK_A_F1_COVERAGE_FIRST",
        "TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE",
        "TRACK_A_F3_STATE_FIDELITY",
        "TRACK_A_F4_MINIMUM_EXTRA_PARETO",
    ]
    assert module.EXPECTED_BCR07 == {
        "TRACK_B_B1_E0_EMA30_CROSS": (1980, 1980, 0),
        "TRACK_B_B1_E1_STACK_BREAK": (519, 519, 0),
        "TRACK_B_B4_E0_EMA20_TOUCH": (774, 773, 1),
        "TRACK_B_B4_E1_EXTENSION_CONTRACT": (833, 832, 1),
    }
    assert module.SCENARIOS == {
        "C0_OBSERVED_SPREAD": 0.0,
        "C1_10PCT_SPREAD_PER_FILL": 0.1,
        "C2_25PCT_SPREAD_PER_FILL": 0.25,
        "C3_50PCT_SPREAD_PER_FILL": 0.5,
    }


def test_track_a_predicates_are_frozen() -> None:
    assert module.long_entry(row(p_rci9_turn_up=True, p_rci9=-1), "E0Z1P0")
    assert module.long_entry(
        row(p_rci9_turn_up=True, p_rci9=-40, p_ema_alignment="BULLISH_STACK"),
        "E1Z2P0",
    )
    assert module.short_entry(
        row(p_rci9_turn_down=True, p_rci9=1, p_ret1_bps=-0.1),
        "E0Z1P1",
    )
    assert module.short_entry(
        row(p_rci9_turn_down=True, p_rci9=40, p_ema_alignment="BEARISH_STACK"),
        "E1Z2P0",
    )
    assert module.long_exit(row(p_rci9=70, open=101, p_ema20=100), "T70M0P1")
    assert module.long_exit(row(p_rci9=70, p_ema30_slope4=1), "T70M1P0")
    assert not module.long_entry(
        row(common_eligible=False, p_rci9_turn_up=True, p_rci9=-80),
        "E0Z1P0",
    )


def test_common_warmup_requires_row_500_and_contiguous_50() -> None:
    times = pd.date_range("2025-01-01", periods=560, freq="15min")
    close = np.arange(560, dtype=float) + 1000
    frame = pd.DataFrame(
        {
            "server_open": times,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "spread": 2250,
        }
    )
    features = module.build_features(frame)
    assert not features.loc[499, "common_eligible"]
    assert features.loc[500, "common_eligible"]

    frame_gap = frame.drop(index=490).reset_index(drop=True)
    features_gap = module.build_features(frame_gap)
    after_gap = features_gap.index[features_gap.server_open.eq(times[500])][0]
    assert not features_gap.loc[after_gap, "common_eligible"]


def test_drawdown_and_holm_are_deterministic() -> None:
    assert module.max_drawdown(np.array([10.0, -4.0, -9.0, 3.0])) == 13.0
    assert module.max_losing_streak(np.array([1.0, -1.0, -2.0, 0.0, -3.0])) == 2
    adjusted = module.holm_adjust(np.array([0.01, 0.04, 0.03]))
    np.testing.assert_allclose(adjusted, np.array([0.03, 0.06, 0.06]))
