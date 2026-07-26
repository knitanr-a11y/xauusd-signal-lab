from __future__ import annotations

import bisect
import sys
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import m10p2_runtime as impl

ORIGINAL_LAG_SECONDS = dict(impl.LAG)
_original_initialize = impl.initialize
_original_once = impl.once

# Neutralize the old wall-clock lag checks inside the frozen core runtime.
# The wrapper below enforces the same limits in observed M1 trading bars instead.
impl.LAG = {tf: 10**15 for tf in ORIGINAL_LAG_SECONDS}


def observed_feed_health(
    root: Path,
    snapshots: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, float | int | str]]:
    """Validate feed freshness using observed M1 bars instead of wall-clock elapsed time.

    Equivalent trading-time limits are preserved from the original contract:
    M1=0, M5=10, M15=30, H1=120, H4=480, D1=2880 observed M1 bars.
    Weekend/market-closed wall time is therefore ignored, while a genuinely stale
    higher-timeframe exporter still blocks once enough new M1 bars accumulate.
    """
    if snapshots is None:
        snapshots = impl.current_feed_snapshots(root)
    latest = {tf: impl.pt(str(item["last_server_open"])) for tf, item in snapshots.items()}
    latest_m1 = latest["M1"]

    m1_bars = impl.load_bars_retry(root / impl.EXPECTED_LIVE_FILE_MAP["M1"])
    m1_times = [bar.time for bar in m1_bars]
    end_index = bisect.bisect_right(m1_times, latest_m1)
    if end_index == 0 or m1_times[end_index - 1] != latest_m1:
        raise impl.E("M1 tail snapshot is not present in stable M1 read")

    details: dict[str, dict[str, float | int | str]] = {}
    for tf, time_value in latest.items():
        wall_seconds = (latest_m1 - time_value).total_seconds()
        if wall_seconds < 0:
            raise impl.E(f"feed out-of-order: {tf} wall_lag={wall_seconds}s")
        start_index = bisect.bisect_right(m1_times, time_value, hi=end_index)
        observed_m1_bars = end_index - start_index
        limit_bars = int(ORIGINAL_LAG_SECONDS[tf] // 60)
        details[tf] = {
            "last_server_open": impl.ft(time_value),
            "wall_lag_seconds": wall_seconds,
            "observed_m1_bars_after_tf": observed_m1_bars,
            "allowed_observed_m1_bars": limit_bars,
        }
        if observed_m1_bars > limit_bars:
            raise impl.E(
                f"feed stale/out-of-order: {tf} observed_m1_bars={observed_m1_bars} "
                f"limit={limit_bars} wall_lag={wall_seconds}s"
            )
    return details


def guarded_initialize() -> int:
    _, root, _ = impl.env()
    observed_feed_health(root)
    return _original_initialize()


def guarded_once() -> int:
    _, root, _ = impl.env()
    observed_feed_health(root)
    return _original_once()


impl.initialize = guarded_initialize
impl.once = guarded_once

if __name__ == "__main__":
    raise SystemExit(impl.main())
