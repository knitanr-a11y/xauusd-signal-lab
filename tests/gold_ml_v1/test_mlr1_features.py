from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/build_features.py"
CONTRACT = ROOT / "config/gold_ml_v1/mlr1_feature_contract_v1_20260627.json"
SPEC = importlib.util.spec_from_file_location("mlr1_build_features", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Mlr1FeatureTests(unittest.TestCase):
    def test_wilder_rma_uses_sma_seed(self) -> None:
        source = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = MODULE.wilder_rma(source, 3)
        self.assertTrue(np.isnan(result.iloc[1]))
        self.assertAlmostEqual(result.iloc[2], 2.0)
        self.assertAlmostEqual(result.iloc[3], 8.0 / 3.0)
        self.assertAlmostEqual(result.iloc[4], 31.0 / 9.0)

    def test_lagged_percentile_does_not_use_current_value(self) -> None:
        a = pd.Series([1.0, 2.0, 3.0, 100.0])
        b = pd.Series([1.0, 2.0, 3.0, -100.0])
        pa = MODULE.lagged_percentile_rank(a, 3)
        pb = MODULE.lagged_percentile_rank(b, 3)
        self.assertAlmostEqual(pa.iloc[3], 1.0)
        self.assertAlmostEqual(pb.iloc[3], 1.0)

    def test_asof_join_never_uses_future_higher_timeframe_bar(self) -> None:
        base = pd.DataFrame({
            "decision_time": pd.to_datetime([
                "2024-01-01 04:00:00",
                "2024-01-01 04:15:00",
            ])
        })
        higher = pd.DataFrame({
            "h1_source_bar_close_time": pd.to_datetime([
                "2024-01-01 04:00:00",
                "2024-01-01 05:00:00",
            ]),
            "h1_marker": [1.0, 2.0],
        })
        result = MODULE._asof_join(base, higher, "h1")
        self.assertEqual(result["h1_marker"].tolist(), [1.0, 1.0])
        self.assertTrue(
            (result["h1_source_bar_close_time"] <= result["decision_time"]).all()
        )

    def test_future_append_does_not_change_existing_timeframe_features(self) -> None:
        count = 330
        times = pd.date_range("2024-01-01", periods=count, freq="15min")
        close = pd.Series(
            2000.0 + np.linspace(0.0, 50.0, count) + np.sin(np.arange(count) / 7.0)
        )
        raw = pd.DataFrame({
            "time": times,
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.6,
            "close": close,
            "tick_volume": 100 + (np.arange(count) % 30),
            "spread": 15 + (np.arange(count) % 4),
            "real_volume": 0,
        })
        first, columns = MODULE.build_timeframe_features(
            raw.iloc[:-1].copy(), "m15", MODULE.TF_PROFILES["m15"]
        )
        changed = raw.copy()
        changed.loc[
            changed.index[-1], ["open", "high", "low", "close"]
        ] = [5000.0, 5100.0, 4900.0, 5050.0]
        second, columns2 = MODULE.build_timeframe_features(
            changed, "m15", MODULE.TF_PROFILES["m15"]
        )
        self.assertEqual(columns, columns2)
        np.testing.assert_allclose(
            first[columns].to_numpy(dtype=float),
            second.loc[first.index, columns].to_numpy(dtype=float),
            equal_nan=True,
        )

    def test_model_feature_names_exclude_absolute_price_metadata(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        model_columns = contract["model_feature_columns"]
        self.assertEqual(len(model_columns), len(set(model_columns)))
        self.assertEqual(len(model_columns), 161)
        forbidden = {
            "entry_m1_bid_open",
            "label_m15_atr14_price",
            "m15_source_bar_open_time",
            "h1_source_bar_open_time",
            "h4_source_bar_open_time",
            "d1_source_bar_open_time",
        }
        self.assertTrue(forbidden.isdisjoint(model_columns))

    def test_deterministic_gzip_output(self) -> None:
        frame = pd.DataFrame({
            "decision_time": pd.to_datetime(["2024-01-01 00:15:00"]),
            "x": [1.25],
        })
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.csv.gz"
            b = Path(tmp) / "b.csv.gz"
            MODULE.deterministic_csv_gzip(frame, a)
            MODULE.deterministic_csv_gzip(frame, b)
            self.assertEqual(MODULE.sha256_file(a), MODULE.sha256_file(b))


if __name__ == "__main__":
    unittest.main()
