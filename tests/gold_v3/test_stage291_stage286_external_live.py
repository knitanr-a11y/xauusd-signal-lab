from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RUNTIME = Path(__file__).resolve().parents[2] / "scripts" / "gold_v3_runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from gold_v3_291_stage286_external_live import (
    find_live_trigger,
    validate_external_pair,
)


def write_m15(path: Path, *, start: str, periods: int, offset: float = 0.0):
    times = pd.date_range(start, periods=periods, freq="15min")
    rows = []
    for index, time in enumerate(times):
        close = 100.0 + offset + index * 0.5
        rows.append(
            {
                "time": time.strftime("%Y.%m.%d %H:%M:%S"),
                "open": close - 0.2,
                "high": close + 0.4,
                "low": close - 0.5,
                "close": close,
                "tick_volume": 1000 + index,
                "spread": 10,
                "real_volume": 0,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_external_pair_uses_exact_files_and_aligns_latest(tmp_path):
    write_m15(
        tmp_path / "us500cashsharp_m15.csv",
        start="2026-01-01 00:00:00",
        periods=30,
    )
    write_m15(
        tmp_path / "us100cashsharp_m15.csv",
        start="2026-01-01 00:00:00",
        periods=30,
        offset=100.0,
    )
    pair = validate_external_pair(tmp_path)
    assert pair.latest_time == pd.Timestamp("2026-01-01 07:15:00")
    assert pair.sp.ret4_atr.notna().sum() > 0
    assert pair.nq.ret4_atr.notna().sum() > 0
    assert pair.checks[-1]["check"] == "US500_US100_M15_ALIGNMENT"


def test_external_pair_blocks_latest_time_mismatch(tmp_path):
    write_m15(
        tmp_path / "us500cashsharp_m15.csv",
        start="2026-01-01 00:00:00",
        periods=30,
    )
    write_m15(
        tmp_path / "us100cashsharp_m15.csv",
        start="2026-01-01 00:00:00",
        periods=29,
    )
    with pytest.raises(ValueError, match="latest M15 mismatch"):
        validate_external_pair(tmp_path)


def test_live_trigger_uses_closed_trigger_bar_close_without_future_row():
    times = pd.date_range("2026-01-01 10:00:00", periods=4, freq="5min")
    m5 = pd.DataFrame(
        {
            "time": times,
            "open": [101.0, 101.2, 101.0, 100.8],
            "high": [101.4, 101.4, 101.2, 100.9],
            "low": [100.8, 100.9, 100.7, 99.8],
            "close": [101.2, 101.0, 100.9, 100.0],
            "body_signed": [0.5, -0.4, -0.1, -0.8],
            "ema20": [100.9, 100.95, 100.85, 100.6],
        }
    )
    trigger, planned_entry, reference = find_live_trigger(
        m5, pd.Timestamp("2026-01-01 10:10:00"), 60
    )
    assert trigger == pd.Timestamp("2026-01-01 10:15:00")
    assert planned_entry == pd.Timestamp("2026-01-01 10:20:00")
    assert reference == 100.0
