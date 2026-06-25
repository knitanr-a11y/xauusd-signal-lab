from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/replay/nine_candidate_local_replay.py"
SPEC = importlib.util.spec_from_file_location("nine_candidate_local_replay", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class NineCandidateLocalReplayTests(unittest.TestCase):
    def test_metrics(self) -> None:
        df = pd.DataFrame({
            "r_value": [1.0, -1.0, 0.5],
            "decision_close_time": ["2023-01-01", "2023-01-02", "2023-01-03"],
        })
        result = MODULE.compute_metrics(df)
        self.assertEqual(result["trades"], 3)
        self.assertAlmostEqual(result["profit_factor"], 1.5)
        self.assertAlmostEqual(result["total_r"], 0.5)

    def test_rci_increasing_is_positive_100(self) -> None:
        values = pd.Series(np.arange(30.0))
        result = MODULE.rci(values, 18)
        self.assertAlmostEqual(result.iloc[-1], 100.0)

    def test_semicolon_csv_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            path.write_text("a;b\n1;2\n", encoding="utf-8")
            df = MODULE.read_csv_auto(path)
            self.assertEqual(df.columns.tolist(), ["a", "b"])

    def test_same_bar_sl_priority(self) -> None:
        m1 = pd.DataFrame({
            "bar_open_time": [pd.Timestamp("2023-01-01 00:00:00")],
            "open": [100.0],
            "high": [102.0],
            "low": [98.0],
            "close": [100.0],
            "spread": [0],
        })
        trade = MODULE.evaluate_trade(
            m1,
            pd.Timestamp("2023-01-01 00:00:00"),
            1.0,
            "LONG",
            1,
        )
        self.assertIsNotNone(trade)
        self.assertEqual(trade["outcome"], "SL")
        self.assertEqual(trade["r_value"], -1.0)


if __name__ == "__main__":
    unittest.main()
