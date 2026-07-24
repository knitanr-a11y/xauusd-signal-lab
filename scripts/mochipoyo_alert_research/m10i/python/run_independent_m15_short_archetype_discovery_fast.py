from __future__ import annotations

import bisect
from datetime import timedelta

import run_independent_m15_short_archetype_discovery as impl

_CACHE: dict[tuple[int, float], list] = {}


def cached_selected_closed_index(bars, delta: timedelta, decision):
    key = (id(bars), delta.total_seconds())
    close_times = _CACHE.get(key)
    if close_times is None:
        close_times = [bar.time + delta for bar in bars]
        _CACHE[key] = close_times
    return bisect.bisect_right(close_times, decision) - 1


impl.selected_closed_index = cached_selected_closed_index

if __name__ == "__main__":
    raise SystemExit(impl.main())
