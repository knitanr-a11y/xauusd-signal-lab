#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run GOLD multi-strategy dry-run wrapper with a robust fast M15 parser patch.

This is a small compatibility wrapper around:

    scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run.py

It intentionally does not reimplement signal detection. It imports the existing
wrapper and replaces only read_latest_confirmed_m15_close_time_fast() with a
more defensive parser so that --skip-same-m15-no-signal can be validated safely.

Why this exists:
- The initial fast parser used pandas.read_csv(..., sep=';') first.
- If the MT5 CSV is comma/tab/space separated, pandas can still return a single
  column instead of raising, and timestamp parsing then returns empty.
- The strategy live_scan itself already obtains latest_m15_close_time correctly.
- This patch only fixes the lightweight pre-check timestamp path.

Safety:
- Never passes --send by itself.
- Delegates all order/sender behavior to the existing dry-run wrapper.
- Does not alter BUY/SELL signal detection logic.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.run_gold_multi_strategy_mochipoyo_loop_dry_run as base  # noqa: E402


def _windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def _candidate_files(csv_dir: Path, filename: str) -> list[Path]:
    base_name = filename
    names = [
        base_name,
        base_name.lower(),
        base_name.upper(),
        base_name.replace("m15", "M15"),
        base_name.replace("M15", "m15"),
        "goldsharp_m15.csv",
        "goldsharp_M15.csv",
        "gold_m15.csv",
        "gold_M15.csv",
        "xauusd_m15.csv",
        "xauusd_M15.csv",
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for name in names:
        if not name:
            continue
        p = csv_dir / name
        key = str(p).lower()
        if key not in seen:
            out.append(p)
            seen.add(key)
    return out


def _read_tail_lines(path: Path, max_lines: int = 80) -> list[str]:
    if not Path(_windows_long_path(path)).exists():
        return []
    raw = Path(_windows_long_path(path)).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            text = raw.decode(enc, errors="strict")
            break
        except Exception:
            text = raw.decode("utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-max_lines:]


def _split_row(line: str) -> list[str]:
    # Try CSV dialects first, then a whitespace fallback.
    for delim in (";", ",", "\t"):
        try:
            row = next(csv.reader([line], delimiter=delim))
            if len(row) >= 2:
                return [cell.strip().strip('"') for cell in row]
        except Exception:
            pass
    return [cell.strip().strip('"') for cell in re.split(r"\s+", line) if cell.strip()]


def _parse_dt_from_cells(cells: Iterable[str]) -> datetime | None:
    values = [str(c).strip().strip('"') for c in cells if str(c).strip()]
    candidates: list[str] = []
    if values:
        candidates.append(values[0])
    if len(values) >= 2:
        candidates.append(f"{values[0]} {values[1]}")
    if len(values) >= 3:
        candidates.append(f"{values[0]} {values[1]}:{values[2]}")

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y%m%d %H:%M:%S",
        "%Y%m%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for text in candidates:
        normalized = text.replace("T", " ").strip()
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue
    return None


def robust_read_latest_confirmed_m15_close_time_fast(csv_dir: Path, filename: str, policy: str) -> str:
    csv_dir = Path(csv_dir)
    for path in _candidate_files(csv_dir, filename):
        lines = _read_tail_lines(path)
        if not lines:
            continue
        datetimes: list[datetime] = []
        for line in lines:
            lower = line.lower()
            if "time" in lower and ("open" in lower or "close" in lower):
                continue
            dt = _parse_dt_from_cells(_split_row(line))
            if dt is not None:
                datetimes.append(dt)
        if not datetimes:
            continue
        datetimes = sorted(datetimes)
        idx = -2 if policy == "second_last" and len(datetimes) >= 2 else -1
        close_time = datetimes[idx] + timedelta(minutes=15)
        return close_time.strftime("%Y-%m-%d %H:%M:%S")
    return ""


# Monkey-patch only the lightweight timestamp pre-check. Everything else remains
# the existing wrapper implementation.
base.read_latest_confirmed_m15_close_time_fast = robust_read_latest_confirmed_m15_close_time_fast


if __name__ == "__main__":
    raise SystemExit(base.main())
