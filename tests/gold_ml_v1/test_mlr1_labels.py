from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/build_labels.py"
SPEC = importlib.util.spec_from_file_location("mlr1_build_labels", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

STRONG = {
    "spread_multiplier": 2.0,
    "entry_slippage_price": 0.1,
    "exit_slippage_price": 0.1,
}
EXTREME = {
    "spread_multiplier": 3.0,
    "entry_slippage_price": 0.2,
    "exit_slippage_price": 0.2,
}


def arrays(rows: list[dict]) -> dict:
    frame = pd.DataFrame(rows)
    return {
        "m1_times": frame["time"].to_numpy(dtype="datetime64[ns]"),
        "m1_open": frame["open"].to_numpy(float),
        "m1_high": frame["high"].to_numpy(float),
        "m1_low": frame["low"].to_numpy(float),
        "m1_close": frame["close"].to_numpy(float),
        "m1_spread": frame["spread"].to_numpy(int),
        "last_observed_close_time": pd.Timestamp(frame["time"].iloc[-1])
        + pd.Timedelta(minutes=1),
    }


class Mlr1LabelTests(unittest.TestCase):
    def evaluate(self, direction: str, rows: list[dict], **kwargs):
        return MODULE.evaluate_direction(
            direction=direction,
            decision_time=pd.Timestamp(rows[0]["time"]),
            entry_bid_open=kwargs.get("entry_bid_open", rows[0]["open"]),
            entry_spread_points=kwargs.get("entry_spread_points", rows[0]["spread"]),
            atr=kwargs.get("atr", 1.0),
            target_atr=kwargs.get("target_atr", 1.5),
            protective_atr=kwargs.get("protective_atr", 1.0),
            horizon_hours=kwargs.get("horizon_hours", 6),
            strong_cost=STRONG,
            extreme_cost=EXTREME,
            **arrays(rows),
        )

    def test_long_same_m1_collision_is_protective(self) -> None:
        rows = [{
            "time": pd.Timestamp("2024-01-01 00:00:00"),
            "open": 100.0,
            "high": 102.0,
            "low": 98.0,
            "close": 100.0,
            "spread": 10,
        }]
        result = self.evaluate("LONG", rows)
        self.assertEqual(result.outcome, "PROTECTIVE")
        self.assertTrue(result.same_m1_collision)
        self.assertAlmostEqual(result.base_r, -1.0)

    def test_short_same_m1_collision_is_protective(self) -> None:
        rows = [{
            "time": pd.Timestamp("2024-01-01 00:00:00"),
            "open": 100.0,
            "high": 101.1,
            "low": 98.0,
            "close": 100.0,
            "spread": 10,
        }]
        result = self.evaluate("SHORT", rows)
        self.assertEqual(result.outcome, "PROTECTIVE")
        self.assertTrue(result.same_m1_collision)
        self.assertAlmostEqual(result.base_r, -1.0)

    def test_short_uses_reconstructed_ask_for_stop(self) -> None:
        rows = [{
            "time": pd.Timestamp("2024-01-01 00:00:00"),
            "open": 100.0,
            "high": 100.95,
            "low": 100.0,
            "close": 100.5,
            "spread": 10,
        }]
        result = self.evaluate("SHORT", rows)
        self.assertEqual(result.outcome, "PROTECTIVE")
        self.assertFalse(result.same_m1_collision)

    def test_bar_open_at_horizon_is_excluded(self) -> None:
        rows = [
            {
                "time": pd.Timestamp("2024-01-01 00:00:00"),
                "open": 100.0,
                "high": 100.2,
                "low": 99.9,
                "close": 100.0,
                "spread": 10,
            },
            {
                "time": pd.Timestamp("2024-01-01 05:59:00"),
                "open": 100.0,
                "high": 100.2,
                "low": 99.9,
                "close": 100.1,
                "spread": 10,
            },
            {
                "time": pd.Timestamp("2024-01-01 06:00:00"),
                "open": 100.1,
                "high": 103.0,
                "low": 100.0,
                "close": 102.0,
                "spread": 10,
            },
        ]
        result = self.evaluate("LONG", rows)
        self.assertEqual(result.outcome, "TIME")
        self.assertEqual(
            result.exit_bar_open_time, pd.Timestamp("2024-01-01 05:59:00")
        )
        self.assertEqual(result.exit_time, pd.Timestamp("2024-01-01 06:00:00"))

    def test_protective_gap_uses_adverse_m1_open(self) -> None:
        rows = [
            {
                "time": pd.Timestamp("2024-01-01 00:00:00"),
                "open": 100.0,
                "high": 100.2,
                "low": 99.9,
                "close": 100.0,
                "spread": 10,
            },
            {
                "time": pd.Timestamp("2024-01-01 00:01:00"),
                "open": 98.0,
                "high": 98.5,
                "low": 97.5,
                "close": 98.2,
                "spread": 10,
            },
        ]
        result = self.evaluate("LONG", rows)
        self.assertEqual(result.outcome, "PROTECTIVE")
        self.assertAlmostEqual(result.fill_price, 98.0)
        self.assertAlmostEqual(result.base_r, -2.1)

    def test_no_hit_past_snapshot_end_is_unresolved(self) -> None:
        rows = [{
            "time": pd.Timestamp("2024-01-01 00:00:00"),
            "open": 100.0,
            "high": 100.2,
            "low": 99.9,
            "close": 100.0,
            "spread": 10,
        }]
        result = self.evaluate("LONG", rows)
        self.assertFalse(result.resolved)
        self.assertEqual(result.outcome, "UNRESOLVED")

    def test_cost_scenarios_subtract_incremental_cost(self) -> None:
        strong = MODULE.scenario_r(
            base_r=1.5,
            atr=2.0,
            direction="LONG",
            entry_spread_price=0.2,
            exit_spread_price=0.3,
            spread_multiplier=2.0,
            entry_slippage=0.1,
            exit_slippage=0.1,
        )
        extreme = MODULE.scenario_r(
            base_r=1.5,
            atr=2.0,
            direction="SHORT",
            entry_spread_price=0.2,
            exit_spread_price=0.3,
            spread_multiplier=3.0,
            entry_slippage=0.2,
            exit_slippage=0.2,
        )
        self.assertAlmostEqual(strong, 1.3)
        self.assertAlmostEqual(extreme, 1.0)

    def test_deterministic_gzip_output(self) -> None:
        frame = pd.DataFrame({
            "decision_time": pd.to_datetime(["2024-01-01"]),
            "x": [1.0],
        })
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.csv.gz"
            second = Path(tmp) / "b.csv.gz"
            MODULE.deterministic_csv_gzip(frame, first)
            MODULE.deterministic_csv_gzip(frame, second)
            self.assertEqual(
                MODULE.sha256_file(first), MODULE.sha256_file(second)
            )


if __name__ == "__main__":
    unittest.main()
