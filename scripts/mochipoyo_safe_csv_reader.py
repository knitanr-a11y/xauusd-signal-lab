#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe OHLC CSV reader for Mochipoyo minimal live scanner.

The MQL5 ExportOhlcToCsv EA writes confirmed bars only when
InpIncludeCurrentBar=false, but Python may still read while MT5 is appending a
line.  This reader therefore validates and cleans the input before scanners use
it.

Design notes:
- For the initial comparison-script phase, this implementation may full-read the
  file and then keep the requested tail.  The public API already accepts
  tail_bars so it can later be swapped to a true file-tail reader for live mode.
- The reader does not sort out-of-order data.  If time is not non-decreasing,
  read_status is ERROR with TIME_NOT_ASCENDING.
- Duplicate timestamps are allowed; the last row is kept and conflicts are
  reported in metadata.
"""
from __future__ import annotations

import csv
import time as time_module
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from mochipoyo_minimal_config import get_timeframe_minutes

READ_STATUS_OK = "OK"
READ_STATUS_ERROR = "ERROR"

CSV_NOT_FOUND = "CSV_NOT_FOUND"
CSV_EMPTY = "CSV_EMPTY"
CSV_HEADER_INVALID = "CSV_HEADER_INVALID"
CSV_SEPARATOR_UNKNOWN = "CSV_SEPARATOR_UNKNOWN"
CSV_REQUIRED_COLUMN_MISSING = "CSV_REQUIRED_COLUMN_MISSING"
CSV_PARSE_FAILED = "CSV_PARSE_FAILED"
TIME_NOT_ASCENDING = "TIME_NOT_ASCENDING"
SPREAD_COLUMN_MISSING = "SPREAD_COLUMN_MISSING"
NO_ROWS_AFTER_AS_OF_TIME = "NO_ROWS_AFTER_AS_OF_TIME"

DEFAULT_REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "tick_volume")
OPTIONAL_NUMERIC_COLUMNS = ("spread", "real_volume")
NUMERIC_COLUMNS = ("open", "high", "low", "close", "tick_volume", "spread", "real_volume")
TIME_FORMATS = (
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


@dataclass
class CsvReadResult:
    df: pd.DataFrame
    read_status: str
    error_reason: str | None
    path: str
    timeframe: str
    rows_raw: int = 0
    rows_valid: int = 0
    rows_dropped_parse: int = 0
    rows_dropped_incomplete: int = 0
    duplicate_time_count: int = 0
    duplicate_time_ohlc_conflict_count: int = 0
    latest_time: pd.Timestamp | None = None
    latest_close_time: pd.Timestamp | None = None
    separator: str | None = None

    @property
    def ok(self) -> bool:
        return self.read_status == READ_STATUS_OK


def _empty_result(path: str | Path, timeframe: str, error_reason: str, *, separator: str | None = None) -> CsvReadResult:
    return CsvReadResult(
        df=pd.DataFrame(),
        read_status=READ_STATUS_ERROR,
        error_reason=error_reason,
        path=str(path),
        timeframe=str(timeframe).upper(),
        separator=separator,
    )


def detect_csv_separator(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    sample = p.read_text(encoding="utf-8-sig", errors="replace")[:8192]
    if not sample.strip():
        raise ValueError(CSV_EMPTY)
    first_line = sample.splitlines()[0] if sample.splitlines() else ""
    semi = first_line.count(";")
    comma = first_line.count(",")
    if semi == 0 and comma == 0:
        try:
            return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
        except csv.Error as exc:
            raise ValueError(CSV_SEPARATOR_UNKNOWN) from exc
    if semi >= comma:
        return ";"
    return ","


def _resolve_separator(path: str | Path, csv_sep: str = "auto") -> str:
    if csv_sep and csv_sep != "auto":
        if csv_sep not in {",", ";", "\t"}:
            raise ValueError(CSV_SEPARATOR_UNKNOWN)
        return csv_sep
    return detect_csv_separator(path)


def _normalize_columns(columns: Iterable[object]) -> list[str]:
    normalized = []
    for col in columns:
        c = str(col).strip().lower()
        if c in {"datetime", "timestamp"}:
            c = "time"
        elif c == "tickvolume":
            c = "tick_volume"
        normalized.append(c)
    return normalized


def validate_required_columns(
    columns: Sequence[str],
    required_columns: Sequence[str] = DEFAULT_REQUIRED_COLUMNS,
    requires_spread: bool = False,
) -> tuple[bool, list[str], str | None]:
    colset = {str(c).strip().lower() for c in columns}
    required = [str(c).strip().lower() for c in required_columns]
    missing = [c for c in required if c not in colset]
    if missing:
        return False, missing, CSV_REQUIRED_COLUMN_MISSING
    if requires_spread and "spread" not in colset:
        return False, ["spread"], SPREAD_COLUMN_MISSING
    return True, [], None


def parse_mt5_time(value: object) -> pd.Timestamp | pd.NaT:
    if value is None:
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    for fmt in TIME_FORMATS:
        try:
            return pd.Timestamp(pd.to_datetime(text, format=fmt))
        except Exception:
            pass
    return pd.to_datetime(text, errors="coerce")


def add_close_time(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    out = df.copy()
    minutes = get_timeframe_minutes(timeframe)
    out["close_time"] = out["time"] + pd.to_timedelta(minutes, unit="m")
    return out


def check_time_non_decreasing(df: pd.DataFrame) -> bool:
    if df.empty or "time" not in df.columns:
        return True
    times = pd.to_datetime(df["time"], errors="coerce")
    if times.isna().any():
        return False
    return bool((times.diff().dropna() >= pd.Timedelta(0)).all())


def _count_duplicate_ohlc_conflicts(df: pd.DataFrame) -> int:
    if df.empty or "time" not in df.columns:
        return 0
    ohlc = [c for c in ("open", "high", "low", "close") if c in df.columns]
    if not ohlc:
        return 0
    conflicts = 0
    dup_times = df.loc[df["time"].duplicated(keep=False), "time"].dropna().unique()
    for t in dup_times:
        group = df[df["time"] == t]
        if len(group[ohlc].drop_duplicates()) > 1:
            conflicts += 1
    return conflicts


def drop_duplicate_times_keep_last(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "time" not in df.columns:
        return df.copy()
    return df.drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)


def _read_csv_once(path: Path, sep: str) -> pd.DataFrame:
    # Read as strings first so incomplete/invalid rows can be diagnosed before
    # numeric conversion drops information.
    return pd.read_csv(
        path,
        sep=sep,
        encoding="utf-8-sig",
        dtype=str,
        engine="python",
        on_bad_lines="skip",
    )


def _keep_tail_with_margin(df: pd.DataFrame, tail_bars: int | None) -> pd.DataFrame:
    if tail_bars is None or tail_bars <= 0 or df.empty:
        return df
    # Keep extra rows so parse/drop/duplicate cleanup does not accidentally leave
    # fewer valid rows than requested.
    margin = max(50, int(tail_bars * 0.05))
    keep = tail_bars + margin
    if len(df) <= keep:
        return df
    return df.tail(keep).copy()


def _coerce_and_clean(
    raw: pd.DataFrame,
    timeframe: str,
    required_columns: Sequence[str],
    requires_spread: bool,
    as_of_time: object | None,
    tail_bars: int | None,
) -> tuple[pd.DataFrame, dict[str, object], str | None]:
    meta: dict[str, object] = {
        "rows_raw": int(len(raw)),
        "rows_dropped_parse": 0,
        "rows_dropped_incomplete": 0,
        "duplicate_time_count": 0,
        "duplicate_time_ohlc_conflict_count": 0,
    }

    if raw.empty:
        return pd.DataFrame(), meta, CSV_EMPTY

    df = raw.copy()
    df.columns = _normalize_columns(df.columns)

    ok, missing, reason = validate_required_columns(df.columns, required_columns, requires_spread)
    if not ok:
        meta["missing_columns"] = missing
        return pd.DataFrame(), meta, reason

    # Remove fully empty rows. Count as incomplete.
    before_empty = len(df)
    df = df.dropna(how="all")
    empty_dropped = before_empty - len(df)

    required = [str(c).strip().lower() for c in required_columns]
    if requires_spread and "spread" not in required:
        required.append("spread")

    # Rows missing required raw fields are incomplete. This catches partially
    # appended rows before parsing.
    before_incomplete = len(df)
    for col in required:
        df[col] = df[col].astype(str).str.strip()
    incomplete_mask = pd.Series(False, index=df.index)
    for col in required:
        incomplete_mask = incomplete_mask | df[col].isna() | (df[col].astype(str).str.strip() == "") | (df[col].astype(str).str.lower() == "nan")
    df = df.loc[~incomplete_mask].copy()
    meta["rows_dropped_incomplete"] = int(empty_dropped + (before_incomplete - len(df)))

    if df.empty:
        return pd.DataFrame(), meta, CSV_PARSE_FAILED

    df["time"] = df["time"].map(parse_mt5_time)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    parse_subset = ["time", "open", "high", "low", "close"]
    if "tick_volume" in required:
        parse_subset.append("tick_volume")
    if requires_spread:
        parse_subset.append("spread")

    before_parse = len(df)
    df = df.dropna(subset=parse_subset).copy()
    meta["rows_dropped_parse"] = int(before_parse - len(df))

    if df.empty:
        return pd.DataFrame(), meta, CSV_PARSE_FAILED

    if not check_time_non_decreasing(df):
        return pd.DataFrame(), meta, TIME_NOT_ASCENDING

    duplicate_mask = df["time"].duplicated(keep=False)
    meta["duplicate_time_count"] = int(duplicate_mask.sum())
    meta["duplicate_time_ohlc_conflict_count"] = int(_count_duplicate_ohlc_conflicts(df))
    df = drop_duplicate_times_keep_last(df)

    df = add_close_time(df, timeframe)

    if as_of_time is not None:
        as_of = parse_mt5_time(as_of_time)
        if pd.isna(as_of):
            return pd.DataFrame(), meta, CSV_PARSE_FAILED
        df = df[df["close_time"] <= pd.Timestamp(as_of)].copy()
        if df.empty:
            return pd.DataFrame(), meta, NO_ROWS_AFTER_AS_OF_TIME

    if tail_bars is not None and tail_bars > 0 and len(df) > tail_bars:
        df = df.tail(tail_bars).copy()

    df = df.reset_index(drop=True)
    return df, meta, None


def read_ohlc_csv_safe(
    path: str | Path,
    timeframe: str,
    tail_bars: int | None,
    required_columns: Sequence[str] = DEFAULT_REQUIRED_COLUMNS,
    requires_spread: bool = False,
    as_of_time: object | None = None,
    csv_sep: str = "auto",
    retry_count: int = 3,
    retry_sleep_sec: float = 0.2,
) -> CsvReadResult:
    """Read an MT5 OHLC CSV safely and return data plus metadata.

    The function retries transient read/parse failures a few times because MT5
    may be appending at the exact moment Python reads the file.
    """
    p = Path(path)
    tf = str(timeframe).strip().upper()
    last_result: CsvReadResult | None = None
    attempts = max(1, int(retry_count))

    for attempt in range(attempts):
        sep: str | None = None
        try:
            if not p.exists():
                return _empty_result(p, tf, CSV_NOT_FOUND)
            if p.stat().st_size <= 0:
                last_result = _empty_result(p, tf, CSV_EMPTY)
                raise RuntimeError(CSV_EMPTY)

            sep = _resolve_separator(p, csv_sep)
            raw = _read_csv_once(p, sep)
            if raw.empty and len(raw.columns) == 0:
                last_result = _empty_result(p, tf, CSV_HEADER_INVALID, separator=sep)
                raise RuntimeError(CSV_HEADER_INVALID)

            raw = _keep_tail_with_margin(raw, tail_bars)
            df, meta, error_reason = _coerce_and_clean(
                raw,
                timeframe=tf,
                required_columns=required_columns,
                requires_spread=requires_spread,
                as_of_time=as_of_time,
                tail_bars=tail_bars,
            )
            if error_reason is not None:
                last_result = CsvReadResult(
                    df=pd.DataFrame(),
                    read_status=READ_STATUS_ERROR,
                    error_reason=error_reason,
                    path=str(p),
                    timeframe=tf,
                    rows_raw=int(meta.get("rows_raw", 0)),
                    rows_valid=0,
                    rows_dropped_parse=int(meta.get("rows_dropped_parse", 0)),
                    rows_dropped_incomplete=int(meta.get("rows_dropped_incomplete", 0)),
                    duplicate_time_count=int(meta.get("duplicate_time_count", 0)),
                    duplicate_time_ohlc_conflict_count=int(meta.get("duplicate_time_ohlc_conflict_count", 0)),
                    separator=sep,
                )
                raise RuntimeError(error_reason)

            latest_time = pd.Timestamp(df["time"].iloc[-1]) if not df.empty else None
            latest_close_time = pd.Timestamp(df["close_time"].iloc[-1]) if not df.empty else None
            return CsvReadResult(
                df=df,
                read_status=READ_STATUS_OK,
                error_reason=None,
                path=str(p),
                timeframe=tf,
                rows_raw=int(meta.get("rows_raw", 0)),
                rows_valid=int(len(df)),
                rows_dropped_parse=int(meta.get("rows_dropped_parse", 0)),
                rows_dropped_incomplete=int(meta.get("rows_dropped_incomplete", 0)),
                duplicate_time_count=int(meta.get("duplicate_time_count", 0)),
                duplicate_time_ohlc_conflict_count=int(meta.get("duplicate_time_ohlc_conflict_count", 0)),
                latest_time=latest_time,
                latest_close_time=latest_close_time,
                separator=sep,
            )
        except (FileNotFoundError, ValueError) as exc:
            reason = str(exc) if str(exc) else CSV_PARSE_FAILED
            if reason not in {
                CSV_EMPTY,
                CSV_SEPARATOR_UNKNOWN,
                CSV_NOT_FOUND,
                CSV_REQUIRED_COLUMN_MISSING,
                SPREAD_COLUMN_MISSING,
            }:
                reason = CSV_SEPARATOR_UNKNOWN if reason == CSV_SEPARATOR_UNKNOWN else CSV_PARSE_FAILED
            last_result = _empty_result(p, tf, reason, separator=sep)
        except Exception:
            # Keep the structured last_result if one was set; otherwise report a
            # generic parse failure.
            if last_result is None:
                last_result = _empty_result(p, tf, CSV_PARSE_FAILED, separator=sep)

        if attempt < attempts - 1:
            time_module.sleep(max(0.0, float(retry_sleep_sec)))

    return last_result or _empty_result(p, tf, CSV_PARSE_FAILED)


def read_latest_close_time_safe(
    path: str | Path,
    timeframe: str,
    *,
    required_columns: Sequence[str] = DEFAULT_REQUIRED_COLUMNS,
    requires_spread: bool = False,
    csv_sep: str = "auto",
    retry_count: int = 3,
    retry_sleep_sec: float = 0.2,
) -> CsvReadResult:
    """Read only enough rows to determine the latest valid close_time.

    In this initial implementation it delegates to read_ohlc_csv_safe with a
    small tail.  It preserves the same validation behavior as full reads.
    """
    return read_ohlc_csv_safe(
        path=path,
        timeframe=timeframe,
        tail_bars=10,
        required_columns=required_columns,
        requires_spread=requires_spread,
        as_of_time=None,
        csv_sep=csv_sep,
        retry_count=retry_count,
        retry_sleep_sec=retry_sleep_sec,
    )


__all__ = [
    "CSV_EMPTY",
    "CSV_HEADER_INVALID",
    "CSV_NOT_FOUND",
    "CSV_PARSE_FAILED",
    "CSV_REQUIRED_COLUMN_MISSING",
    "CSV_SEPARATOR_UNKNOWN",
    "CsvReadResult",
    "DEFAULT_REQUIRED_COLUMNS",
    "NO_ROWS_AFTER_AS_OF_TIME",
    "READ_STATUS_ERROR",
    "READ_STATUS_OK",
    "SPREAD_COLUMN_MISSING",
    "TIME_NOT_ASCENDING",
    "add_close_time",
    "check_time_non_decreasing",
    "detect_csv_separator",
    "drop_duplicate_times_keep_last",
    "parse_mt5_time",
    "read_latest_close_time_safe",
    "read_ohlc_csv_safe",
    "validate_required_columns",
]
