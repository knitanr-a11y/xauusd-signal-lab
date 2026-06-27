from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/gold_ml_v1/mlr1/build_live_feature_snapshot.py"


@dataclass(frozen=True)
class FakeBuildResult:
    features: pd.DataFrame
    model_feature_columns: list[str]
    metadata_columns: list[str]
    rejection_summary: dict


FAKE_ENGINE = types.ModuleType("build_features")
FAKE_ENGINE.BuildResult = FakeBuildResult


def fake_read_raw_csv(path: Path, *, columns=None) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["time"] = pd.to_datetime(frame["time"], format="%Y.%m.%d %H:%M:%S")
    return frame[list(columns)] if columns is not None else frame


FAKE_ENGINE.read_raw_csv = fake_read_raw_csv
FAKE_ENGINE.build_dataset_from_frames = None
sys.modules["build_features"] = FAKE_ENGINE

SPEC = importlib.util.spec_from_file_location("mlr1_live_source_adapter", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Mlr1LiveSourceAdapterTests(unittest.TestCase):
    def make_files(self, root: Path) -> dict[str, Path]:
        paths = {}
        for timeframe in MODULE.TIMEFRAMES:
            path = root / f"goldsharp_{timeframe}.csv"
            path.write_text("time,open,high,low,close,tick_volume,spread,real_volume\n", encoding="utf-8")
            paths[timeframe] = path
        return paths

    def test_explicit_same_root_goldsharp_paths_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.make_files(Path(tmp))
            resolved = MODULE.validate_explicit_paths(paths)
            self.assertEqual(set(resolved), set(MODULE.TIMEFRAMES))
            self.assertEqual(len({value.parent for value in resolved.values()}), 1)

    def test_historical_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "gold_v3_2023_2026"
            root.mkdir()
            with self.assertRaises(ValueError):
                MODULE.validate_explicit_paths(self.make_files(root))

    def test_non_goldsharp_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.make_files(root)
            replacement = root / "m15.csv"
            replacement.write_text(paths["m15"].read_text(encoding="utf-8"), encoding="utf-8")
            paths["m15"] = replacement
            with self.assertRaises(ValueError):
                MODULE.validate_explicit_paths(paths)

    def test_different_parent_directories_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a"
            second = root / "b"
            first.mkdir()
            second.mkdir()
            paths = self.make_files(first)
            other = second / "goldsharp_d1.csv"
            other.write_text(paths["d1"].read_text(encoding="utf-8"), encoding="utf-8")
            paths["d1"] = other
            with self.assertRaises(ValueError):
                MODULE.validate_explicit_paths(paths)

    def test_duplicate_explicit_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.make_files(Path(tmp))
            paths["h1"] = paths["m15"]
            with self.assertRaises(ValueError):
                MODULE.validate_explicit_paths(paths)

    def test_timeframe_alignment_rejects_misaligned_bars(self) -> None:
        m15 = pd.DataFrame({"time": pd.to_datetime(["2026-01-01 00:07:00"])})
        h4 = pd.DataFrame({"time": pd.to_datetime(["2026-01-01 02:00:00"])})
        d1 = pd.DataFrame({"time": pd.to_datetime(["2026-01-01 01:00:00"])})
        with self.assertRaises(ValueError):
            MODULE.validate_time_alignment(m15, "m15", Path("goldsharp_m15.csv"))
        with self.assertRaises(ValueError):
            MODULE.validate_time_alignment(h4, "h4", Path("goldsharp_h4.csv"))
        with self.assertRaises(ValueError):
            MODULE.validate_time_alignment(d1, "d1", Path("goldsharp_d1.csv"))

    def test_source_change_during_read_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.make_files(Path(tmp))
            stable = [f"hash-{index}" for index in range(5)]
            changed = stable.copy()
            changed[2] = "changed"
            with mock.patch.object(MODULE, "sha256_file", side_effect=stable + changed):
                with self.assertRaises(RuntimeError):
                    MODULE.read_stable_live_frames(paths)

    def test_build_live_features_rejects_future_higher_timeframe(self) -> None:
        decision = pd.Timestamp("2026-01-01 12:15:00")
        frame = pd.DataFrame({
            "decision_time": [decision],
            "m15_source_bar_close_time": [decision],
            "h1_source_bar_close_time": [decision],
            "h4_source_bar_close_time": [decision + pd.Timedelta(hours=1)],
            "d1_source_bar_close_time": [decision],
            "x": [1.0],
        })
        result = FakeBuildResult(frame, ["x"], [], {})
        MODULE.feature_engine.build_dataset_from_frames = mock.Mock(return_value=result)
        frames = {timeframe: pd.DataFrame() for timeframe in MODULE.TIMEFRAMES}
        with self.assertRaises(AssertionError):
            MODULE.build_live_features(frames, {"timeframe_profiles": {}, "model_feature_columns": ["x"]})

    def test_build_live_features_accepts_finite_causal_result(self) -> None:
        decision = pd.Timestamp("2026-01-01 12:15:00")
        frame = pd.DataFrame({
            "decision_time": [decision],
            "m15_source_bar_close_time": [decision],
            "h1_source_bar_close_time": [decision - pd.Timedelta(minutes=15)],
            "h4_source_bar_close_time": [decision - pd.Timedelta(minutes=15)],
            "d1_source_bar_close_time": [decision - pd.Timedelta(minutes=15)],
            "x": [1.0],
        })
        result = FakeBuildResult(frame, ["x"], [], {"eligible_rows": 1})
        MODULE.feature_engine.build_dataset_from_frames = mock.Mock(return_value=result)
        frames = {timeframe: pd.DataFrame() for timeframe in MODULE.TIMEFRAMES}
        actual = MODULE.build_live_features(
            frames,
            {"timeframe_profiles": {}, "model_feature_columns": ["x"]},
        )
        self.assertEqual(len(actual.features), 1)
        self.assertTrue(np.isfinite(actual.features[["x"]].to_numpy()).all())

    def test_deterministic_gzip(self) -> None:
        frame = pd.DataFrame({"decision_time": pd.to_datetime(["2026-01-01"]), "x": [1.0]})
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.csv.gz"
            second = Path(tmp) / "second.csv.gz"
            MODULE.deterministic_csv_gzip(frame, first)
            MODULE.deterministic_csv_gzip(frame, second)
            self.assertEqual(MODULE.sha256_file(first), MODULE.sha256_file(second))


if __name__ == "__main__":
    unittest.main()
