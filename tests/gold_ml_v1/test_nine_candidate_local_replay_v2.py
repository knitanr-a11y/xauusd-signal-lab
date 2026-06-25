from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/replay/nine_candidate_local_replay_v2.py"
SPEC = importlib.util.spec_from_file_location("nine_candidate_local_replay_v2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def raw_frame(times: list[str], close_start: float = 100.0) -> pd.DataFrame:
    count = len(times)
    close = np.arange(close_start, close_start + count, dtype=float)
    return pd.DataFrame(
        {
            "time": times,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "tick_volume": [10] * count,
            "spread": [20] * count,
            "real_volume": [0] * count,
        }
    )


class ReplayV2Tests(unittest.TestCase):
    def test_atr_is_simple_14_true_range_mean(self) -> None:
        rows = 20
        frame = pd.DataFrame(
            {
                "open": np.arange(100.0, 100.0 + rows),
                "high": np.arange(101.0, 101.0 + rows),
                "low": np.arange(99.0, 99.0 + rows),
                "close": np.arange(100.0, 100.0 + rows),
            }
        )
        atr = MODULE.atr_simple_rolling(frame, 14)
        self.assertTrue(atr.iloc[:13].isna().all())
        self.assertAlmostEqual(float(atr.iloc[13]), 2.0)
        self.assertAlmostEqual(float(atr.iloc[-1]), 2.0)

    def test_goldsharp_prehistory_only_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical_path = root / "historical.csv"
            live_path = root / "live.csv"
            raw_frame(["2023-01-03 00:00:00", "2023-01-03 04:00:00"]).to_csv(
                historical_path, index=False
            )
            raw_frame(
                [
                    "2022-12-31 20:00:00",
                    "2023-01-03 00:00:00",
                    "2023-01-03 04:00:00",
                    "2023-01-03 08:00:00",
                ],
                close_start=99.0,
            ).assign(
                open=[99.0, 100.0, 101.0, 102.0],
                high=[100.0, 101.0, 102.0, 103.0],
                low=[98.0, 99.0, 100.0, 101.0],
                close=[99.0, 100.0, 101.0, 102.0],
            ).to_csv(live_path, index=False)
            combined, audit = MODULE.load_historical_with_live_prehistory(
                historical_path, live_path, "H4"
            )
            self.assertEqual(len(combined), 3)
            self.assertEqual(audit["goldsharp_prehistory_rows_used_for_warmup"], 1)
            self.assertEqual(audit["goldsharp_post_historical_rows_used"], 0)
            self.assertEqual(combined.iloc[0]["source"], "goldsharp_warmup")
            self.assertTrue((combined.iloc[1:]["source"] == "historical").all())

    def test_overlap_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical_path = root / "historical.csv"
            live_path = root / "live.csv"
            historical = raw_frame(["2023-01-03 00:00:00"])
            live = historical.copy()
            live.loc[0, "close"] += 0.01
            historical.to_csv(historical_path, index=False)
            live.to_csv(live_path, index=False)
            with self.assertRaises(ValueError):
                MODULE.load_historical_with_live_prehistory(
                    historical_path, live_path, "H4"
                )

    def test_complete_horizon_mask_requires_entry_and_final_minute(self) -> None:
        decisions = pd.Series(
            [pd.Timestamp("2023-01-03 01:00:00"), pd.Timestamp("2023-01-03 02:00:00")]
        )
        m1_times = {
            pd.Timestamp("2023-01-03 01:00:00"),
            pd.Timestamp("2023-01-03 06:59:00"),
            pd.Timestamp("2023-01-03 02:00:00"),
        }
        mask = MODULE._complete_horizon_mask(decisions, m1_times, 6)
        self.assertEqual(mask.tolist(), [True, False])


if __name__ == "__main__":
    unittest.main()
