from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/replay/nine_candidate_local_replay_v3.py"
SPEC = importlib.util.spec_from_file_location("nine_candidate_local_replay_v3", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ReplayV3Tests(unittest.TestCase):
    def test_horizon_eligibility_does_not_require_exact_final_minute(self) -> None:
        decisions = pd.Series([
            pd.Timestamp("2023-01-06 21:00:00"),
            pd.Timestamp("2023-01-09 04:00:00"),
        ])
        m1_times = {
            pd.Timestamp("2023-01-06 21:00:00"),
            pd.Timestamp("2023-01-06 23:56:00"),
            pd.Timestamp("2023-01-09 04:00:00"),
            pd.Timestamp("2023-01-11 04:00:00"),
        }
        mask = MODULE.complete_horizon_mask_v3(decisions, m1_times, 48)
        self.assertEqual(mask.tolist(), [True, True])

    def test_time_exit_uses_last_available_close_before_weekend_gap(self) -> None:
        times = pd.to_datetime([
            "2023-01-06 21:00:00",
            "2023-01-06 21:01:00",
            "2023-01-06 23:56:00",
        ])
        frame = pd.DataFrame({
            "bar_open_time": times,
            "bar_close_time": times + pd.Timedelta(minutes=1),
            "open": [100.0, 100.0, 100.0],
            "high": [100.2, 100.2, 100.2],
            "low": [99.8, 99.8, 99.8],
            "close": [100.0, 100.0, 100.1],
            "spread": [0, 0, 0],
        })
        trade = MODULE.evaluate_trade_v3(
            frame,
            pd.Timestamp("2023-01-06 21:00:00"),
            atr_at_decision=10.0,
            direction="LONG",
            horizon_hours=48,
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade["exit_time"], pd.Timestamp("2023-01-06 23:57:00"))
        self.assertAlmostEqual(trade["exit_price"], 100.1)
        self.assertEqual(trade["outcome"], "TIME_POS")

    def test_same_bar_sl_priority_remains_frozen(self) -> None:
        times = pd.to_datetime(["2023-01-03 01:00:00"])
        frame = pd.DataFrame({
            "bar_open_time": times,
            "bar_close_time": times + pd.Timedelta(minutes=1),
            "open": [100.0],
            "high": [102.0],
            "low": [98.0],
            "close": [100.0],
            "spread": [0],
        })
        trade = MODULE.evaluate_trade_v3(
            frame,
            pd.Timestamp("2023-01-03 01:00:00"),
            atr_at_decision=1.0,
            direction="LONG",
            horizon_hours=6,
        )
        self.assertIsNotNone(trade)
        assert trade is not None
        self.assertEqual(trade["outcome"], "SL")
        self.assertEqual(trade["r_value"], -1.0)


if __name__ == "__main__":
    unittest.main()
