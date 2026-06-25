from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/replay/fast_m1_engine_hotfix.py"
SPEC = importlib.util.spec_from_file_location("fast_m1_engine_hotfix", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@dataclass
class Engine:
    times: np.ndarray
    opens: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    spreads: np.ndarray

    @property
    def latest_close(self) -> pd.Timestamp:
        return pd.Timestamp(self.times[-1] + 60_000_000_000)


class FastM1EngineHotfixTests(unittest.TestCase):
    def test_neither_sl_nor_tp_uses_time_exit(self) -> None:
        times = pd.DatetimeIndex([
            "2023-01-03 01:00:00",
            "2023-01-03 01:01:00",
            "2023-01-03 01:02:00",
        ]).asi8
        engine = Engine(
            times=times,
            opens=np.array([100.0, 100.1, 100.2]),
            highs=np.array([100.3, 100.4, 100.5]),
            lows=np.array([99.7, 99.8, 99.9]),
            closes=np.array([100.1, 100.2, 100.25]),
            spreads=np.array([0.0, 0.0, 0.0]),
        )
        trade = MODULE.evaluate_fast_m1_no_infinity(
            engine,
            pd.Timestamp("2023-01-03 01:00:00"),
            atr=10.0,
            horizon_hours=0.05,
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade["outcome"], "TIME_POS")
        self.assertEqual(trade["exit_time"], pd.Timestamp("2023-01-03 01:03:00"))

    def test_same_bar_collision_is_sl_first(self) -> None:
        times = pd.DatetimeIndex([
            "2023-01-03 01:00:00",
            "2023-01-03 01:01:00",
        ]).asi8
        engine = Engine(
            times=times,
            opens=np.array([100.0, 100.0]),
            highs=np.array([102.0, 100.0]),
            lows=np.array([98.0, 100.0]),
            closes=np.array([100.0, 100.0]),
            spreads=np.array([0.0, 0.0]),
        )
        trade = MODULE.evaluate_fast_m1_no_infinity(
            engine,
            pd.Timestamp("2023-01-03 01:00:00"),
            atr=1.0,
            horizon_hours=0.03,
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade["outcome"], "SL")
        self.assertEqual(trade["r_value"], -1.0)


if __name__ == "__main__":
    unittest.main()
