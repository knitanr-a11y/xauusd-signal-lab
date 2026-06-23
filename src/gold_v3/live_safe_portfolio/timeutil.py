from __future__ import annotations

from datetime import datetime


def parse_dt(value: str | datetime) -> datetime:
    """Parse an ISO-like timestamp without inventing a timezone."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty ISO string")
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc


def dt_to_text(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat(sep=" ")


def ensure_same_awareness(*values: datetime | None) -> None:
    flags = {v.tzinfo is not None for v in values if v is not None}
    if len(flags) > 1:
        raise ValueError("cannot mix timezone-aware and timezone-naive timestamps")
