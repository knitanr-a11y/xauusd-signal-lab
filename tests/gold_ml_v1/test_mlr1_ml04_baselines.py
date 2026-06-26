from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/run_ml04_baselines.py"
SPEC = importlib.util.spec_from_file_location("mlr1_ml04", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Mlr1Ml04BaselineTests(unittest.TestCase):
    def test_one_open_allows_equality(self) -> None:
        frame = pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2024-01-01 00:00:00",
                "2024-01-01 00:15:00",
                "2024-01-01 01:00:00",
            ]),
            "exit_time": pd.to_datetime([
                "2024-01-01 01:00:00",
                "2024-01-01 00:30:00",
                "2024-01-01 02:00:00",
            ]),
            "strong_r": [1.0, 5.0, 2.0],
        })
        result = MODULE.apply_one_open(frame)
        self.assertEqual(result["strong_r"].tolist(), [1.0, 2.0])

    def test_segment_purge_and_embargo(self) -> None:
        frame = pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2024-01-01 05:59:00",
                "2024-01-01 06:00:00",
                "2024-06-30 17:59:00",
                "2024-06-30 18:00:00",
            ]),
            "exit_time": pd.to_datetime([
                "2024-01-01 06:01:00",
                "2024-01-01 07:00:00",
                "2024-06-30 20:00:00",
                "2024-06-30 20:00:00",
            ]),
        })
        segment = MODULE.Segment(
            "validation",
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-07-01 00:00:00"),
            6,
            6,
        )
        self.assertEqual(
            MODULE.segment_mask(frame, segment).tolist(),
            [False, True, True, False],
        )

    def test_validation_threshold_uses_higher_quantile(self) -> None:
        scores = np.arange(1000, dtype=float)
        self.assertEqual(MODULE.validation_threshold(scores, 0.01), 990.0)

    def test_trading_metrics(self) -> None:
        frame = pd.DataFrame({"strong_r": [2.0, -1.0, 1.0, -2.0]})
        result = MODULE.trading_metrics(frame)
        self.assertEqual(result["trades"], 4)
        self.assertAlmostEqual(result["profit_factor"], 1.0)
        self.assertAlmostEqual(result["total_r"], 0.0)
        self.assertAlmostEqual(result["gross_positive_r"], 3.0)
        self.assertAlmostEqual(result["gross_negative_r_abs"], 3.0)

    def test_perfect_multiclass_brier_is_zero(self) -> None:
        y = np.array(["PROTECTIVE", "TARGET", "TIME"])
        probs = np.eye(3)
        self.assertEqual(
            MODULE.multiclass_brier(y, probs, MODULE.OUTCOME_ORDER),
            0.0,
        )

    def test_deterministic_gzip_output(self) -> None:
        frame = pd.DataFrame({"a": [1.0]})
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.csv.gz"
            second = Path(tmp) / "b.csv.gz"
            MODULE.deterministic_csv_gzip(frame, first)
            MODULE.deterministic_csv_gzip(frame, second)
            self.assertEqual(
                MODULE.sha256_file(first),
                MODULE.sha256_file(second),
            )

    def test_linear_model_selection_runs(self) -> None:
        rng = np.random.default_rng(1)
        X = rng.normal(size=(240, 5))
        y_class = np.array(MODULE.OUTCOME_ORDER * 80)
        _, c_value, c_grid = MODULE.choose_logistic(
            X[:180],
            y_class[:180],
            X[180:],
            y_class[180:],
            [0.01, 0.1],
        )
        self.assertIn(c_value, [0.01, 0.1])
        self.assertEqual(len(c_grid), 2)

        y_r = X[:, 0] * 0.1 + rng.normal(scale=0.1, size=240)
        _, alpha, alpha_grid = MODULE.choose_ridge(
            X[:180],
            y_r[:180],
            X[180:],
            y_r[180:],
            [1.0, 10.0],
        )
        self.assertIn(alpha, [1.0, 10.0])
        self.assertEqual(len(alpha_grid), 2)


if __name__ == "__main__":
    unittest.main()
