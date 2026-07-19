from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "scripts" / "mochipoyo_alert_research"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import alert_entry_timing_builder as base  # noqa: E402
from alert_entry_timing_builder_boundary_safe import (  # noqa: E402
    effective_closed_end,
)


def _bar(hour: int, minute: int, close_price: float) -> base.Bar:
    return base.Bar(
        server_open=datetime(2026, 7, 19, hour, minute),
        open_price=close_price - 0.5,
        high_price=close_price + 1.0,
        low_price=close_price - 1.0,
        close_price=close_price,
    )


def test_m5_close_equal_to_exit_reference_is_excluded() -> None:
    source_time = datetime(2026, 7, 19, 9, 45, 1)
    source_exit = datetime(2026, 7, 19, 10, 0, 2)
    exit_reference = datetime(2026, 7, 19, 10, 0, 0)
    offset = 0.0

    cutoffs = {
        (source_time, source_exit, offset): exit_reference,
    }
    strict_end = effective_closed_end(
        source_time,
        source_exit,
        offset,
        cutoffs,
    )
    assert strict_end == exit_reference

    bars = [
        _bar(9, 45, 100.0),
        _bar(9, 50, 101.0),
        _bar(9, 55, 102.0),
    ]
    opens = [bar.server_open for bar in bars]

    old_window = base._m5_window(
        opens,
        bars,
        source_time_utc=source_time,
        end_time_utc=source_exit,
        offset_hours=offset,
    )
    assert old_window[-1][1] == exit_reference

    corrected_window = base._m5_window(
        opens,
        bars,
        source_time_utc=source_time,
        end_time_utc=strict_end,
        offset_hours=offset,
    )
    assert corrected_window
    assert all(close_time < exit_reference for _, close_time, _ in corrected_window)
    assert len(corrected_window) == len(old_window) - 1


def test_open_episode_end_is_not_changed_without_registered_cutoff() -> None:
    source_time = datetime(2026, 7, 19, 9, 45, 1)
    open_analysis_end = datetime(2026, 7, 19, 12, 0, 1)
    assert (
        effective_closed_end(source_time, open_analysis_end, 3.0, {})
        == open_analysis_end
    )
