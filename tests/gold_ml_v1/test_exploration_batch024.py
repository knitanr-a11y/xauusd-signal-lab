from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "scripts/gold_ml_v1/exploration"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from batch024_pullback_engine import (  # noqa: E402
    Cell,
    DirectionalM1Engine,
    build_cells,
    cell_signal,
    gate_pass,
    metric_row,
    prepare_decisions,
)

CONFIG_PATH = ROOT / "config/gold_ml_v1/exploration_batch024_m15_h1_pullback_20260625.json"
GUARDRAILS_PATH = ROOT / "config/gold_ml_v1/exploration_guardrails_20260625.json"


def m1_frame() -> pd.DataFrame:
    opens = pd.to_datetime(["2023-01-03 10:00:00", "2023-01-03 10:01:00"])
    return pd.DataFrame(
        {
            "bar_open_time": opens,
            "bar_close_time": opens + pd.Timedelta(minutes=1),
            "open": [100.0, 100.0],
            "high": [101.6, 100.4],
            "low": [98.8, 99.6],
            "close": [100.0, 100.0],
            "spread": [10.0, 10.0],
        }
    )


class Batch024ExplorationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.guardrails = json.loads(GUARDRAILS_PATH.read_text(encoding="utf-8"))

    def test_search_space_has_exactly_36_unique_new_ids(self) -> None:
        cells = build_cells(self.config)
        self.assertEqual(len(cells), 36)
        self.assertEqual(len({cell.candidate_id for cell in cells}), 36)
        self.assertTrue(all(cell.candidate_id.startswith("GML1-EXP024-") for cell in cells))
        self.assertTrue(
            set(self.config["existing_frozen_nine"]).isdisjoint(
                {cell.candidate_id for cell in cells}
            )
        )
        combinations = {
            (cell.direction, cell.h1_gap_atr_min, cell.rsi_long_level, cell.trigger_mode)
            for cell in cells
        }
        self.assertEqual(len(combinations), 36)

    def test_year_split_and_existing_pool_are_frozen(self) -> None:
        self.assertEqual(self.config["period_contract"]["2023"], "EXPLORATION_ONLY")
        self.assertEqual(
            self.config["period_contract"]["2024"], "VALIDATION_ONLY_NO_RETUNE"
        )
        self.assertEqual(
            self.config["period_contract"]["2025"], "FINAL_TEST_ONLY_NO_RETUNE"
        )
        self.assertEqual(
            self.config["period_contract"]["2026"], "DIAGNOSTIC_ONLY_NEVER_RETUNE"
        )
        self.assertEqual(
            self.config["existing_frozen_nine"],
            self.guardrails["current_candidate_pool"]["frozen_accumulated_ids"],
        )
        self.assertEqual(self.config["existing_pool_change"], "FORBIDDEN")
        self.assertFalse(self.config["status_contract"]["automatic_accumulation"])
        self.assertFalse(self.config["status_contract"]["automatic_promotion"])
        self.assertTrue(
            all(value is False for value in self.config["execution_switches"].values())
        )

    def test_long_same_m1_tp_sl_uses_sl_priority(self) -> None:
        engine = DirectionalM1Engine(m1_frame())
        result = engine.evaluate(
            pd.Timestamp("2023-01-03 10:00:00"),
            risk=1.0,
            direction="LONG",
            horizon_minutes=60,
            stop_r=1.0,
            target_r=1.5,
        )
        self.assertEqual(result["admission_state"], "ACCEPTED")
        self.assertEqual(result["outcome"], "SL")
        self.assertEqual(result["r_value"], -1.0)
        self.assertAlmostEqual(result["entry_price"], 100.1)

    def test_short_execution_uses_ask_path_and_sl_priority(self) -> None:
        frame = m1_frame().copy()
        frame.loc[0, "high"] = 100.95
        frame.loc[0, "low"] = 98.3
        engine = DirectionalM1Engine(frame)
        result = engine.evaluate(
            pd.Timestamp("2023-01-03 10:00:00"),
            risk=1.0,
            direction="SHORT",
            horizon_minutes=60,
            stop_r=1.0,
            target_r=1.5,
        )
        self.assertEqual(result["outcome"], "SL")
        self.assertAlmostEqual(result["entry_price"], 100.0)
        self.assertEqual(result["r_value"], -1.0)

    def test_signal_logic_is_directionally_symmetric(self) -> None:
        frame = pd.DataFrame(
            {
                "h1_ema20": [102.0, 98.0],
                "h1_ema50": [100.0, 100.0],
                "h1_gap_long": [0.4, -0.4],
                "h1_gap_short": [-0.4, 0.4],
                "m15_rsi14_prev": [34.0, 66.0],
                "m15_rsi14": [36.0, 64.0],
                "low": [99.0, 98.0],
                "high": [102.0, 101.0],
                "close": [101.0, 99.0],
                "m15_ema20": [100.0, 100.0],
            }
        )
        long_cell = Cell("L", "LONG", 0.3, 35, "EMA20_TOUCH_RECLOSE")
        short_cell = Cell("S", "SHORT", 0.3, 35, "EMA20_TOUCH_RECLOSE")
        self.assertEqual(cell_signal(frame, long_cell).tolist(), [True, False])
        self.assertEqual(cell_signal(frame, short_cell).tolist(), [False, True])

    def test_confirmed_h1_asof_never_uses_future_close(self) -> None:
        h1_open = pd.date_range("2022-12-30 00:00:00", periods=80, freq="h")
        h1 = pd.DataFrame(
            {
                "bar_open_time": h1_open,
                "bar_close_time": h1_open + pd.Timedelta(hours=1),
                "open": np.arange(80, dtype=float) + 100,
                "high": np.arange(80, dtype=float) + 101,
                "low": np.arange(80, dtype=float) + 99,
                "close": np.arange(80, dtype=float) + 100.5,
            }
        )
        m15_open = pd.date_range("2023-01-01 00:00:00", periods=160, freq="15min")
        m15 = pd.DataFrame(
            {
                "bar_open_time": m15_open,
                "bar_close_time": m15_open + pd.Timedelta(minutes=15),
                "open": np.linspace(150, 170, 160),
                "high": np.linspace(151, 171, 160),
                "low": np.linspace(149, 169, 160),
                "close": np.linspace(150.5, 170.5, 160),
            }
        )
        decisions = prepare_decisions(m15, h1)
        target = decisions.iloc[50]
        decision_time = pd.Timestamp(target["bar_close_time"])

        h1_check = h1.copy()
        h1_check["ema20"] = h1_check["close"].ewm(
            span=20, adjust=False, min_periods=20
        ).mean()
        eligible = h1_check[h1_check["bar_close_time"] <= decision_time].dropna(
            subset=["ema20"]
        )
        expected = float(eligible.iloc[-1]["ema20"])
        self.assertAlmostEqual(float(target["h1_ema20"]), expected)
        future = h1_check[h1_check["bar_close_time"] > decision_time]
        if not future.empty:
            self.assertNotAlmostEqual(float(target["h1_ema20"]), float(future.iloc[0]["ema20"]))

    def test_gate_is_predeclared_and_2026_has_no_gate(self) -> None:
        metric = {
            "resolved_count": 24,
            "profit_factor": 1.1,
            "profit_factor_state": "FINITE",
            "mean_r": 0.051,
        }
        passed, reason = gate_pass(metric, self.config["gates"]["2023_EXPLORATION"])
        self.assertTrue(passed)
        self.assertEqual(reason, "PASS")
        metric["mean_r"] = 0.05
        passed, reason = gate_pass(metric, self.config["gates"]["2023_EXPLORATION"])
        self.assertFalse(passed)
        self.assertIn("mean_r", reason)
        self.assertEqual(
            self.config["gates"]["2026_DIAGNOSTIC"]["performance_gate"],
            "NOT_APPLICABLE_NEVER_RETUNE",
        )

    def test_metric_row_preserves_suppressed_missing_and_unresolved(self) -> None:
        group = pd.DataFrame(
            [
                {
                    "candidate_id": "X",
                    "admission_state": "ACCEPTED",
                    "resolution_state": "RESOLVED",
                    "outcome": "TP",
                    "r_value": 1.5,
                },
                {
                    "candidate_id": "X",
                    "admission_state": "ACCEPTED",
                    "resolution_state": "UNRESOLVED",
                    "outcome": "OPEN",
                    "r_value": np.nan,
                },
                {
                    "candidate_id": "X",
                    "admission_state": "SUPPRESSED_OPEN_POSITION",
                    "resolution_state": "NOT_EVALUATED",
                },
                {
                    "candidate_id": "X",
                    "admission_state": "ENTRY_M1_MISSING",
                    "resolution_state": "NOT_EVALUATED",
                },
            ]
        )
        metric = metric_row("X", 2023, group)
        self.assertEqual(metric["raw_signal_count"], 4)
        self.assertEqual(metric["accepted_count"], 2)
        self.assertEqual(metric["resolved_count"], 1)
        self.assertEqual(metric["unresolved_count"], 1)
        self.assertEqual(metric["suppressed_count"], 1)
        self.assertEqual(metric["missing_entry_count"], 1)


if __name__ == "__main__":
    unittest.main()
