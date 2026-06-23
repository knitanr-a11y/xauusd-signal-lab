from __future__ import annotations

from datetime import datetime, timedelta


def interval_overlaps_hours(
    entry_dt: datetime,
    max_holding_minutes: int,
    blocked_hours: tuple[int, ...],
) -> bool:
    """Check entry-known planned holding overlap with blocked server hours."""
    if max_holding_minutes <= 0:
        raise ValueError("max_holding_minutes must be positive")
    blocked = set(blocked_hours)
    current = entry_dt
    end = entry_dt + timedelta(minutes=max_holding_minutes)
    while current <= end:
        if current.hour in blocked:
            return True
        current += timedelta(minutes=1)
    return False
