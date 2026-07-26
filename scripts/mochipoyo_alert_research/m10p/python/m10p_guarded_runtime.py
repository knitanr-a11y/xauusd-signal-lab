from __future__ import annotations

import bisect
import math
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import m10p_runtime as impl

EXPECTED_LIVE_FILE_MAP = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}

_original_valid = impl.valid
_original_once = impl.once
_original_build_ledgers = impl.build_ledgers
_original_metrics = impl.metrics
_last_candidate_count = 0


def guarded_valid(contract):
    _original_valid(contract)
    if contract.get("data", {}).get("live_file_map") != EXPECTED_LIVE_FILE_MAP:
        raise impl.E("M10P live file map differs from frozen M10B/M10E source contract")


def guarded_build_ledgers(candidates, m1, point):
    global _last_candidate_count
    _last_candidate_count = len(candidates)
    return _original_build_ledgers(candidates, m1, point)


def guarded_metrics(trades):
    result = _original_metrics(trades)
    result["candidate_match_count"] = _last_candidate_count
    return result


def observed_feed_health(root: Path) -> dict[str, dict[str, float | int | str]]:
    """Validate feed freshness in observed M1 trading bars, not wall-clock weekend time.

    The original limits are preserved exactly in trading-time terms:
    M5=10 observed M1 bars, M15=30, H1=120, H4=480, D1=2880.
    Missing market-closed minutes do not consume the allowance.
    """
    latest = {}
    for tf, filename in EXPECTED_LIVE_FILE_MAP.items():
        path = root / filename
        if not path.is_file():
            raise impl.E(f"required live CSV missing during runtime: {path}")
        latest[tf] = impl.pt(str(impl.v.tail_snapshot(path)["last_server_open"]))

    m1_time = latest["M1"]
    m1_bars = impl.load_bars_retry(root / EXPECTED_LIVE_FILE_MAP["M1"])
    m1_times = [bar.time for bar in m1_bars]
    end_index = bisect.bisect_right(m1_times, m1_time)
    if end_index == 0 or m1_times[end_index - 1] != m1_time:
        raise impl.E("M1 tail snapshot is not present in stable M1 read")

    details: dict[str, dict[str, float | int | str]] = {}
    for tf, time_value in latest.items():
        wall_seconds = (m1_time - time_value).total_seconds()
        if wall_seconds < 0:
            raise impl.E(f"live feed out-of-order during M10P cycle: {tf} wall_lag={wall_seconds}s")
        start_index = bisect.bisect_right(m1_times, time_value, hi=end_index)
        observed_m1_bars = end_index - start_index
        limit_bars = int(impl.LAG[tf] // 60)
        details[tf] = {
            "last_server_open": impl.ft(time_value),
            "wall_lag_seconds": wall_seconds,
            "observed_m1_bars_after_tf": observed_m1_bars,
            "allowed_observed_m1_bars": limit_bars,
        }
        if observed_m1_bars > limit_bars:
            raise impl.E(
                f"live feed stale during M10P cycle: {tf} "
                f"observed_m1_bars={observed_m1_bars} limit={limit_bars} "
                f"wall_lag={wall_seconds}s"
            )
    return details


def current_feed_guard() -> None:
    local_root, root, point = impl.env()
    contract = impl.js(impl.CONTRACT)
    guarded_valid(contract)
    _, runtime_path, _, _ = impl.runtime_paths(local_root)
    if not runtime_path.is_file():
        raise impl.E("M10P runtime missing; run BAT01 once first")
    runtime = impl.js(runtime_path)
    if str(root) != str(runtime.get("data_root", "")):
        raise impl.E(f"M10P data_root changed after start freeze: {root}")
    frozen_point = float(runtime.get("point", "nan"))
    if not math.isfinite(frozen_point) or abs(float(point) - frozen_point) > 1e-12:
        raise impl.E(f"M10P XAUUSD point changed after start freeze: current={point} frozen={frozen_point}")
    observed_feed_health(root)


def guarded_once() -> int:
    current_feed_guard()
    return _original_once()


impl.valid = guarded_valid
impl.build_ledgers = guarded_build_ledgers
impl.metrics = guarded_metrics
impl.once = guarded_once

if __name__ == "__main__":
    raise SystemExit(impl.main())
