#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run GOLD multi-strategy dry-run wrapper with a robust fast M15 parser patch.

Compatibility wrapper around scripts/run_gold_multi_strategy_mochipoyo_loop_dry_run.py.
It patches only lightweight runtime behavior:
- robust latest confirmed M15 timestamp parsing
- router path/cmd wiring for GOLD_ALT_PF_SIGNAL_PACK

Signal detection itself remains inside each strategy runner.
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
    names = [
        filename,
        filename.lower(),
        filename.upper(),
        filename.replace("m15", "M15"),
        filename.replace("M15", "m15"),
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
    text = ""
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            text = raw.decode(enc, errors="strict")
            break
        except Exception:
            text = raw.decode("utf-8", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()][-max_lines:]


def _split_row(line: str) -> list[str]:
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


_base_build_paths = base.build_paths
_base_build_router_cmd = base.build_router_cmd


def build_paths_with_alt(out_dir: Path) -> dict[str, Path]:
    paths = _base_build_paths(out_dir)
    paths["alt_out_dir"] = out_dir / "alt_pf_signal_pack"
    return paths


def build_router_cmd_with_alt(args, paths: dict[str, Path]) -> list[str]:
    cmd = _base_build_router_cmd(args, paths)
    if "--alt-out-dir" not in cmd:
        cmd.extend(["--alt-out-dir", str(paths["alt_out_dir"])])
    return cmd


base.read_latest_confirmed_m15_close_time_fast = robust_read_latest_confirmed_m15_close_time_fast
base.build_paths = build_paths_with_alt
base.build_router_cmd = build_router_cmd_with_alt


if __name__ == "__main__":
    raise SystemExit(base.main())
