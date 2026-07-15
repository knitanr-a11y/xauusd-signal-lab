from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_btc_youtube_candidates_dry_run_cycle.py"
spec = importlib.util.spec_from_file_location("run_btc_youtube_candidates_dry_run_cycle", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def frame_at(entry_time: str) -> pd.DataFrame:
    return pd.DataFrame([{"entry_time": entry_time, "signal_key": "test"}])


def test_summer_broker_clock_is_inferred_as_utc_plus_3() -> None:
    offset, ages = module.infer_broker_utc_offset_hours(
        pd.Timestamp("2026-07-15 07:25:00"),
        now_utc=pd.Timestamp("2026-07-15 04:29:00", tz="UTC"),
    )
    assert offset == 3.0
    assert ages["3.0"] == 4.0


def test_valid_server_time_signal_is_not_treated_as_three_hours_in_future() -> None:
    result = module.filter_fresh(
        frame_at("2026-07-15 07:25:00"),
        broker_utc_offset_hours=3.0,
        now_utc=pd.Timestamp("2026-07-15 04:29:00", tz="UTC"),
    )
    assert len(result) == 1


def test_winter_broker_clock_is_inferred_as_utc_plus_2() -> None:
    offset, ages = module.infer_broker_utc_offset_hours(
        pd.Timestamp("2026-01-15 06:25:00"),
        now_utc=pd.Timestamp("2026-01-15 04:29:00", tz="UTC"),
    )
    assert offset == 2.0
    assert ages["2.0"] == 4.0


def test_stale_server_time_signal_is_still_rejected() -> None:
    result = module.filter_fresh(
        frame_at("2026-07-15 06:00:00"),
        broker_utc_offset_hours=3.0,
        now_utc=pd.Timestamp("2026-07-15 04:29:00", tz="UTC"),
    )
    assert result.empty
