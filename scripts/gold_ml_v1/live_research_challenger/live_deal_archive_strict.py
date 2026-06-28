from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import live_deal_archive as base
from live_store import atomic_write_text

_original_archive_captures = base.archive_captures


def _utc_text(deal: dict[str, Any]) -> str:
    milliseconds = int(deal.get("time_msc") or 0)
    if milliseconds > 0:
        seconds = milliseconds / 1000.0
    else:
        text = str(deal.get("time") or "").strip()
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return ""
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _strict_capture(capture: base.DealCapture) -> tuple[base.DealCapture | None, str | None]:
    normalized: list[dict[str, Any]] = []
    exit_count = 0
    for source in capture.deals:
        deal = dict(source)
        deal["time"] = _utc_text(deal)
        entry = int(deal.get("entry") if deal.get("entry") is not None else -1)
        if entry in {1, 2, 3}:
            exit_count += 1
        normalized.append(deal)
    if not normalized:
        return None, f"position {capture.position_ticket}: no MT5 deals returned"
    if exit_count == 0:
        return None, f"position {capture.position_ticket}: no closing MT5 deal returned"
    return base.DealCapture(capture.position_ticket, tuple(normalized)), None


def archive_captures(
    output_dir: Path,
    ledger,
    captures: Iterable[base.DealCapture],
    captured_at: str,
    *,
    net_tolerance: float = 0.01,
):
    valid: list[base.DealCapture] = []
    strict_incomplete: list[str] = []
    for capture in captures:
        converted, error = _strict_capture(capture)
        if error:
            strict_incomplete.append(error)
        elif converted is not None:
            valid.append(converted)
    status = _original_archive_captures(
        output_dir,
        ledger,
        valid,
        captured_at,
        net_tolerance=net_tolerance,
    )
    status["incomplete"] = strict_incomplete + list(status.get("incomplete", []))
    status["time_basis"] = "UTC_FROM_MT5_TIME_MSC"
    atomic_write_text(
        output_dir / "trades" / "deal_archive_status.json",
        json.dumps({"updated_at": captured_at, **status}, ensure_ascii=False, indent=2),
    )
    return status


base.archive_captures = archive_captures
