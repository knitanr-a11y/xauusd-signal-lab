from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts/gold_ml_v1/exploration"
if str(MODULE) not in sys.path:
    sys.path.insert(0, str(MODULE))

import run_batch024_local_reproduction as reproduce


class Batch024LocalReproductionTests(unittest.TestCase):
    def test_frozen_result_records_open_time_contract_and_zero_survivors(self) -> None:
        frozen = json.loads(
            (ROOT / "config/gold_ml_v1/exploration_batch024_assistant_result_20260625.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(frozen["time_contract"]["csv_time"], "MT5 server naive bar-open time")
        self.assertEqual(frozen["time_contract"]["M15_close"], "time + 15 minutes")
        self.assertEqual(frozen["attempted_cells"], 36)
        self.assertEqual(frozen["survivor_count"], 0)
        self.assertEqual(len(frozen["canonical_output_hashes"]), 4)

    def test_canonical_writer_and_hash_comparison_pass_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            raw = root / "raw"
            raw.mkdir()
            config_path = root / "config.json"
            config_path.write_text("{}\n", encoding="utf-8")

            attempts = pd.DataFrame([{"candidate_id": "X", "value": 1.25}])
            years = pd.DataFrame([{"candidate_id": "X", "year": 2023, "mean_r": 0.1}])
            trades = pd.DataFrame(
                [{"candidate_id": "X", "decision_close_time": pd.Timestamp("2023-01-01 00:15:00"), "r_value": 1.5}]
            )
            survivors = pd.DataFrame(columns=attempts.columns)
            result = {
                "attempt_registry": attempts,
                "year_metrics": years,
                "trade_registry": trades,
                "survivors": survivors,
            }

            expected = {}
            for name, frame in {
                "exploration_attempt_registry.csv": attempts,
                "exploration_year_metrics.csv": years,
                "exploration_trade_registry.csv": trades,
                "exploration_survivors.csv": survivors,
            }.items():
                path = root / name
                reproduce.write_canonical_csv(frame, path)
                expected[name] = hashlib.sha256(path.read_bytes()).hexdigest()

            frozen_path = root / "frozen.json"
            frozen_path.write_text(
                json.dumps(
                    {
                        "attempted_cells": 1,
                        "year_metric_rows": 1,
                        "signal_audit_rows": 1,
                        "survivor_count": 0,
                        "canonical_output_hashes": expected,
                        "time_contract": {"csv_time": "bar-open"},
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(reproduce, "run_exploration", return_value=result):
                self.assertEqual(reproduce.run(raw, config_path, frozen_path, output), 0)

            broken = json.loads(frozen_path.read_text(encoding="utf-8"))
            broken["canonical_output_hashes"]["exploration_trade_registry.csv"] = "0" * 64
            frozen_path.write_text(json.dumps(broken), encoding="utf-8")
            with patch.object(reproduce, "run_exploration", return_value=result):
                with self.assertRaises(RuntimeError):
                    reproduce.run(raw, config_path, frozen_path, output)


if __name__ == "__main__":
    unittest.main()
