from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pandas as pd


def live_module(name: str):
    repo = Path(__file__).resolve().parents[2]
    module_dir = repo / "scripts/gold_ml_v1/live_research_challenger"
    research_dir = repo / "scripts/gold_ml_v1/research_challenger"
    for path in (str(module_dir), str(research_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module(name)


def bar_frame(close_times: list[str], delta: str) -> pd.DataFrame:
    closes = pd.to_datetime(close_times)
    step = pd.Timedelta(delta)
    return pd.DataFrame(
        {
            "bar_open_time": closes - step,
            "bar_close_time": closes,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "tick_volume": 1,
            "spread": 1,
            "real_volume": 0,
        }
    )


def test_tail_reader_matches_full_reader(tmp_path: Path) -> None:
    live_data = live_module("live_data")
    path = tmp_path / "goldsharp_m1.csv"
    rows = pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=5000, freq="1min").strftime(
                "%Y.%m.%d %H:%M:%S"
            ),
            "open": range(5000),
            "high": range(1, 5001),
            "low": range(5000),
            "close": range(5000),
            "tick_volume": 1,
            "spread": 2,
            "real_volume": 0,
        }
    )
    rows.to_csv(path, index=False)
    full = live_data.read_closed_bars(path, "M1")
    tail = live_data.read_closed_bars(path, "M1", max_rows=1200)
    pd.testing.assert_frame_equal(
        full.tail(1200).reset_index(drop=True),
        tail.reset_index(drop=True),
    )


def test_m15_waits_for_actual_missing_h4_boundary() -> None:
    live_data = live_module("live_data")
    source = bar_frame(
        [
            "2026-06-29 03:30:00",
            "2026-06-29 03:45:00",
            "2026-06-29 04:00:00",
            "2026-06-29 04:15:00",
        ],
        "15min",
    )
    higher = bar_frame(["2026-06-29 00:00:00"], "4h")
    capped, reason = live_data._cap_source_at_missing_higher_boundary(
        source, higher, "M15", "H4"
    )
    assert reason == "M15_WAIT_H4_BOUNDARY"
    assert capped["bar_close_time"].iloc[-1] == pd.Timestamp("2026-06-29 03:45:00")


def test_weekend_gap_without_boundary_does_not_wait() -> None:
    live_data = live_module("live_data")
    source = bar_frame(
        [
            "2026-06-26 23:45:00",
            "2026-06-29 01:15:00",
            "2026-06-29 01:30:00",
        ],
        "15min",
    )
    higher = bar_frame(["2026-06-26 20:00:00"], "4h")
    uncapped, reason = live_data._cap_source_at_missing_higher_boundary(
        source, higher, "M15", "H4"
    )
    assert reason is None
    assert len(uncapped) == len(source)


def test_wall_clock_boundary_wait_does_not_accumulate_runtime() -> None:
    probe = live_module("probe_live_inputs")
    period = 2_000_000_000
    assert probe.wait_nanoseconds_to_next_boundary(10_250_000_000, period) == 1_750_000_000
    assert probe.wait_nanoseconds_to_next_boundary(13_900_000_000, period) == 100_000_000
    assert probe.wait_nanoseconds_to_next_boundary(14_005_000_000, period) == 1_995_000_000


def test_contract_uses_two_second_anchored_lightweight_poll() -> None:
    repo = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (
            repo
            / "config/gold_ml_v1/live_research_challenger/live_runtime_contract_20260628.json"
        ).read_text(encoding="utf-8")
    )
    assert contract["runner"]["default_interval_seconds"] == 2
    assert contract["runner"]["poll_phase"] == "wall_clock_anchored"
    assert contract["runner"]["sleep_from_previous_completion"] is False
    assert contract["runner"]["lightweight_probe_only_when_unchanged"] is True
    assert contract["performance_contract"]["candidate_rules_simplified"] is False
    assert contract["synchronization_contract"]["weekend_gap_boundary_absence_does_not_block"] is True
    assert contract["synchronization_contract"]["m1_written_before_m15"].startswith("retain_m15_cursor")
