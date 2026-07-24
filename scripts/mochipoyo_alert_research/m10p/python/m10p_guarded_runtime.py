from __future__ import annotations

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

    latest = {}
    for tf, filename in EXPECTED_LIVE_FILE_MAP.items():
        path = root / filename
        if not path.is_file():
            raise impl.E(f"required live CSV missing during runtime: {path}")
        latest[tf] = impl.pt(str(impl.v.tail_snapshot(path)["last_server_open"]))
    m1_time = latest["M1"]
    for tf, time_value in latest.items():
        lag = (m1_time - time_value).total_seconds()
        if lag < 0 or lag > impl.LAG[tf]:
            raise impl.E(f"live feed stale/out-of-order during M10P cycle: {tf} lag={lag}s")


def guarded_once() -> int:
    current_feed_guard()
    return _original_once()


impl.valid = guarded_valid
impl.build_ledgers = guarded_build_ledgers
impl.metrics = guarded_metrics
impl.once = guarded_once

if __name__ == "__main__":
    raise SystemExit(impl.main())
