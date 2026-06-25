from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/gold_ml_v1/replay/goldsharp_live_source_preflight.py"
SPEC = importlib.util.spec_from_file_location("goldsharp_live_source_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_frame(times: list[str]) -> pd.DataFrame:
    return pd.DataFrame({
        "time": times,
        "open": [100.0] * len(times),
        "high": [101.0] * len(times),
        "low": [99.0] * len(times),
        "close": [100.5] * len(times),
        "tick_volume": [10] * len(times),
        "spread": [20] * len(times),
        "real_volume": [0] * len(times),
    })


class GoldsharpLiveSourcePreflightTests(unittest.TestCase):
    def test_partition_only_new_goldsharp_rows_are_operational(self) -> None:
        historical = make_frame(["2026-06-23 18:14:00", "2026-06-23 18:15:00"])
        live = make_frame([
            "2026-06-23 18:15:00",
            "2026-06-23 18:16:00",
            "2026-06-23 18:17:00",
        ])
        historical["time"] = pd.to_datetime(historical["time"])
        live["time"] = pd.to_datetime(live["time"])
        result = MODULE.partition_live_rows(historical, live)
        self.assertEqual(result["live_overlap_or_backfill_rows"], 1)
        self.assertEqual(result["live_operational_rows_after_historical_max"], 2)
        self.assertEqual(result["historical_rows_eligible_for_new_live_signal"], 0)
        self.assertEqual(result["live_rows_eligible_for_new_live_signal"], 2)

    def test_end_to_end_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical_dir = root / "historical"
            live_dir = root / "live"
            output_dir = root / "output"
            historical_dir.mkdir()
            live_dir.mkdir()
            for tf in MODULE.TIMEFRAMES:
                make_frame(["2026-06-23 18:14:00", "2026-06-23 18:15:00"]).to_csv(
                    historical_dir / MODULE.HISTORICAL_NAMES[tf], index=False
                )
                make_frame(["2026-06-23 18:15:00", "2026-06-23 18:16:00"]).to_csv(
                    live_dir / MODULE.LIVE_NAMES[tf], index=False
                )
            code = MODULE.run(historical_dir, live_dir, output_dir)
            self.assertEqual(code, 0)
            report = pd.read_csv(output_dir / "goldsharp_live_source_preflight.csv")
            self.assertEqual(len(report), 5)
            self.assertTrue((report["live_operational_rows_after_historical_max"] == 1).all())


if __name__ == "__main__":
    unittest.main()
