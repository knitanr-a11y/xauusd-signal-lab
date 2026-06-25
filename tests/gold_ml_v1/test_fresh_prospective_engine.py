from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/gold_ml_v1/prospective"))

from fresh_prospective_engine import (
    CANDIDATE_IDS,
    EvaluationContract,
    ProspectiveM1Engine,
    _candidate_rows,
    candidate_summary,
    read_closed_bars,
)


class FreshProspectiveEngineTests(unittest.TestCase):
    def test_semicolon_reader_drops_only_trailing_partial_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "goldsharp_m1.csv"
            path.write_text(
                "time;open;high;low;close;tick_volume;spread;real_volume\n"
                "2026.06.25 10:00:00;100;101;99;100.5;10;2;0\n"
                "2026.06.25 10:01:00;100.5;101.5;100;101;11;2;0\n"
                "2026.06.25 10:02:00;101;102\n",
                encoding="utf-8",
            )
            frame = read_closed_bars(path, "M1")
            self.assertEqual(len(frame), 2)
            self.assertEqual(
                frame.iloc[-1]["bar_close_time"],
                pd.Timestamp("2026-06-25 10:02:00"),
            )

    def test_non_trailing_invalid_row_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "goldsharp_m1.csv"
            path.write_text(
                "time,open,high,low,close,tick_volume,spread,real_volume\n"
                "2026.06.25 10:00:00,100,101,99,100.5,10,2,0\n"
                "2026.06.25 10:01:00,100.5,101.5,,,,\n"
                "2026.06.25 10:02:00,101,102,100,101.5,12,2,0\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "non-trailing"):
                read_closed_bars(path, "M1")

    def test_same_m1_tp_sl_priority_is_sl(self) -> None:
        frame = pd.DataFrame(
            {
                "bar_open_time": pd.to_datetime(
                    ["2026-06-25 10:00:00", "2026-06-25 10:01:00"]
                ),
                "open": [100.0, 100.0],
                "high": [101.5, 100.5],
                "low": [98.5, 99.5],
                "close": [100.0, 100.0],
                "spread": [0.0, 0.0],
            }
        )
        engine = ProspectiveM1Engine(frame)
        result = engine.evaluate(
            pd.Timestamp("2026-06-25 10:00:00"),
            1.0,
            EvaluationContract(6, "close", "close"),
        )
        self.assertEqual(result["prospective_state"], "RESOLVED")
        self.assertEqual(result["outcome"], "SL")
        self.assertEqual(result["r_value"], -1.0)

    def test_incomplete_horizon_is_unresolved_not_fabricated(self) -> None:
        frame = pd.DataFrame(
            {
                "bar_open_time": pd.to_datetime(
                    ["2026-06-25 10:00:00", "2026-06-25 10:01:00"]
                ),
                "open": [100.0, 100.1],
                "high": [100.2, 100.3],
                "low": [99.8, 99.9],
                "close": [100.1, 100.2],
                "spread": [0.0, 0.0],
            }
        )
        engine = ProspectiveM1Engine(frame)
        result = engine.evaluate(
            pd.Timestamp("2026-06-25 10:00:00"),
            1.0,
            EvaluationContract(6, "close", "close"),
        )
        self.assertEqual(result["prospective_state"], "UNRESOLVED")
        self.assertEqual(result["outcome"], "OPEN")
        self.assertTrue(np.isnan(result["r_value"]))
        self.assertTrue(pd.isna(result["exit_time"]))

    def test_cutoff_is_strictly_greater_than(self) -> None:
        cutoff = pd.Timestamp("2026-06-23 18:15:00")
        accepted = pd.DataFrame(
            {
                "decision_close_time": [
                    cutoff,
                    cutoff + pd.Timedelta(minutes=15),
                ],
                "prospective_state": ["RESOLVED", "UNRESOLVED"],
            }
        )
        selected = _candidate_rows(
            accepted,
            "GML1-PROV-007",
            pd.Series([True, True]),
            cutoff,
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected.iloc[0]["decision_close_time"],
            cutoff + pd.Timedelta(minutes=15),
        )

    def test_empty_observation_preserves_all_nine_candidates(self) -> None:
        empty = pd.DataFrame(
            columns=["candidate_id", "resolution_state", "outcome", "r_value"]
        )
        summary = candidate_summary(empty)
        self.assertEqual(summary["candidate_id"].tolist(), CANDIDATE_IDS)
        self.assertEqual(len(summary), 9)
        self.assertTrue((summary["observation_state"] == "NO_CANDIDATE_YET").all())
        self.assertTrue(
            (
                summary["performance_gate"]
                == "NOT_APPLICABLE_PROSPECTIVE_AUDIT_ONLY"
            ).all()
        )


if __name__ == "__main__":
    unittest.main()

# Temporary branch-only CI trigger. Do not merge.
