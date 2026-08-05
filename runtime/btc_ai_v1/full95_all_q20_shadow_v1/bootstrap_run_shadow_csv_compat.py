#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "shadow_full95_all_q20_v1.py"
REQUIRED = ["time", "open", "high", "low", "close"]
_REAL_READ_CSV = pd.read_csv


def _detect_delimiter(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = next((line for line in handle if line.strip()), "")
    counts = {delimiter: header.count(delimiter) for delimiter in [";", ",", "\t"]}
    delimiter = max(counts, key=counts.get)
    if counts[delimiter] == 0:
        raise ValueError(f"unsupported CSV delimiter/header: {path}: {header.strip()!r}")
    return delimiter


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized: dict[Any, str] = {}
    for column in frame.columns:
        name = str(column).strip().lstrip("\ufeff").strip("<>").strip().lower().replace(" ", "_")
        normalized[column] = name
    frame = frame.rename(columns=normalized)
    if "date" in frame.columns and "time" in frame.columns:
        frame["time"] = frame["date"].astype(str).str.strip() + " " + frame["time"].astype(str).str.strip()
    elif "time" not in frame.columns:
        for alias in ["datetime", "date_time", "timestamp"]:
            if alias in frame.columns:
                frame = frame.rename(columns={alias: "time"})
                break
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"CSV_COLUMNS_MISMATCH missing={missing}, detected={list(frame.columns)}")
    frame = frame[REQUIRED].copy()
    for column in REQUIRED[1:]:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float64")
    return frame


def compat_read_csv(filepath_or_buffer: Any, *args: Any, **kwargs: Any) -> pd.DataFrame:
    usecols = kwargs.get("usecols")
    if not isinstance(filepath_or_buffer, (str, Path)) or set(usecols or []) != set(REQUIRED):
        return _REAL_READ_CSV(filepath_or_buffer, *args, **kwargs)
    path = Path(filepath_or_buffer)
    delimiter = _detect_delimiter(path)
    retry = dict(kwargs)
    retry.pop("usecols", None)
    retry.pop("dtype", None)
    retry["sep"] = delimiter
    retry["encoding"] = "utf-8-sig"
    frame = _REAL_READ_CSV(filepath_or_buffer, *args, **retry)
    return _normalize_columns(frame)


def main() -> int:
    if not SCRIPT.is_file():
        raise SystemExit(f"materialized shadow script not found: {SCRIPT}")
    pd.read_csv = compat_read_csv
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.argv = [str(SCRIPT), *sys.argv[1:]]
    runpy.run_path(str(SCRIPT), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
