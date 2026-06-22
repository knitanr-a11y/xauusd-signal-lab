#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared closed-candle IO and indicator primitives for Stage289.

The live ``goldsharp_*.csv`` contract is authoritative:
- ``time`` is the MT5/server bar-open timestamp.
- only closed bars are written, including the newest valid row.
- Python never guesses/removes a forming bar.

Files can be comma- or semicolon-delimited and can be read while MT5 is
appending. A partially appended trailing row is discarded, while the latest
complete row is retained.
"""
from __future__ import annotations

import csv
from collections import deque
from io import StringIO
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}
GOLD_FILES = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}
EXTERNAL_FILES = {
    "SP_M15": "us500cashsharp_m15.csv",
    "NQ_M15": "us100cashsharp_m15.csv",
}
LIVE_TAIL_ROWS = {
    "M1": 30000,
    "M5": 12000,
    "M15": 6000,
    "H1": 3000,
    "H4": 1500,
    "D1": 600,
}
_TIME_FORMATS = (
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


def _infer_timeframe(path: Path) -> str:
    name = path.name.lower()
    for tf in ("m15", "m1", "m5", "h1", "h4", "d1"):
        if f"_{tf}.csv" in name or name.endswith(f"{tf}.csv"):
            return tf.upper()
    raise ValueError(f"cannot infer timeframe from filename: {path.name}")


def _detect_separator(sample: str) -> str:
    lines = sample.splitlines()
    first = lines[0] if lines else ""
    semi, comma, tab = first.count(";"), first.count(","), first.count("\t")
    if max(semi, comma, tab) > 0:
        if semi >= comma and semi >= tab:
            return ";"
        if tab >= comma:
            return "\t"
        return ","
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error as exc:
        raise ValueError("CSV_SEPARATOR_UNKNOWN") from exc


def _parse_time_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    remaining = pd.Series(True, index=series.index)
    for fmt in _TIME_FORMATS:
        if not remaining.any():
            break
        values = pd.to_datetime(text[remaining], format=fmt, errors="coerce")
        good = values.notna()
        parsed.loc[values.index[good]] = values.loc[good]
        remaining.loc[values.index[good]] = False
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(text[remaining], errors="coerce")
    return parsed


def _read_text_tail(path: Path, tail_rows: int | None) -> tuple[str, int]:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        header = handle.readline()
        if not header:
            raise ValueError(f"{path}: CSV_EMPTY")
        if tail_rows is None or tail_rows <= 0:
            return header + handle.read(), 0
        margin = max(50, int(tail_rows * 0.05))
        lines = deque(handle, maxlen=int(tail_rows) + margin)
    return header + "".join(lines), int(tail_rows)


def read_candles(
    path: Path,
    tail_rows: int | None = None,
    *,
    timeframe: str | None = None,
    require_spread: bool | None = None,
) -> pd.DataFrame:
    """Read one live candle CSV without mutating it.

    The newest complete row is retained. No clock-based open-bar exclusion is
    performed because the exporter contract already excludes open bars.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.stat().st_size <= 0:
        raise ValueError(f"{path}: CSV_EMPTY")

    tf = (timeframe or _infer_timeframe(path)).upper()
    if tf not in TF_MINUTES:
        raise ValueError(f"unsupported timeframe {tf!r}")
    if require_spread is None:
        require_spread = path.name.lower().startswith("goldsharp_")

    text, requested_tail = _read_text_tail(path, tail_rows)
    separator = _detect_separator(text[:8192])
    raw = pd.read_csv(
        StringIO(text),
        sep=separator,
        encoding="utf-8-sig",
        dtype=str,
        engine="python",
        on_bad_lines="skip",
    )
    if raw.empty:
        raise ValueError(f"{path}: CSV_EMPTY")
    raw.columns = [str(column).strip().lower() for column in raw.columns]
    raw = raw.rename(
        columns={
            "datetime": "time",
            "date": "time",
            "timestamp": "time",
            "volume": "tick_volume",
            "tickvolume": "tick_volume",
            "tick volume": "tick_volume",
        }
    )
    required = ["time", "open", "high", "low", "close", "tick_volume"]
    if require_spread:
        required.append("spread")
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(
            f"{path}: missing columns {missing}; columns={list(raw.columns)}"
        )

    work = raw.dropna(how="all").copy()
    incomplete = pd.Series(False, index=work.index)
    for column in required:
        values = work[column].astype(str).str.strip()
        incomplete |= values.eq("") | values.str.lower().isin(
            {"nan", "none", "null"}
        )
    dropped_incomplete = int(incomplete.sum())
    work = work.loc[~incomplete].copy()

    work["time"] = _parse_time_series(work["time"])
    for column in [
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    ]:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    parse_required = ["time", "open", "high", "low", "close", "tick_volume"]
    if require_spread:
        parse_required.append("spread")
    before_parse = len(work)
    work = work.dropna(subset=parse_required).copy()
    dropped_parse = int(before_parse - len(work))
    if work.empty:
        raise ValueError(f"{path}: no valid candle rows")
    if not bool((work["time"].diff().dropna() >= pd.Timedelta(0)).all()):
        raise ValueError(f"{path}: TIME_NOT_ASCENDING")

    duplicate_count = int(work["time"].duplicated(keep=False).sum())
    conflict_count = 0
    if duplicate_count:
        duplicate_rows = work.loc[work["time"].duplicated(keep=False)]
        for _, group in duplicate_rows.groupby("time"):
            if len(group[["open", "high", "low", "close"]].drop_duplicates()) > 1:
                conflict_count += 1
        work = work.drop_duplicates("time", keep="last")

    if "spread" not in work.columns:
        work["spread"] = 0.0
    if "real_volume" not in work.columns:
        work["real_volume"] = 0.0
    if requested_tail > 0 and len(work) > requested_tail:
        work = work.tail(requested_tail)
    work = work.reset_index(drop=True)
    work["close_time"] = work["time"] + pd.to_timedelta(
        TF_MINUTES[tf], unit="m"
    )
    work.attrs.update(
        {
            "path": str(path),
            "timeframe": tf,
            "separator": separator,
            "rows_raw": int(len(raw)),
            "rows_valid": int(len(work)),
            "rows_dropped_incomplete": dropped_incomplete,
            "rows_dropped_parse": dropped_parse,
            "duplicate_time_count": duplicate_count,
            "duplicate_time_ohlc_conflict_count": conflict_count,
            "latest_row_closed_by_contract": True,
        }
    )
    return work


def add_indicators(df: pd.DataFrame, wins: Iterable[int]) -> pd.DataFrame:
    result = df.copy()
    previous_close = result.close.shift(1)
    true_range = pd.concat(
        [
            (result.high - result.low).abs(),
            (result.high - previous_close).abs(),
            (result.low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr14"] = true_range.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    result["atr50"] = true_range.ewm(
        alpha=1 / 50, adjust=False, min_periods=50
    ).mean()
    result["atr_ratio"] = result.atr14 / result.atr50
    for window in [8, 20, 50, 200]:
        result[f"ema{window}"] = result.close.ewm(
            span=window, adjust=False, min_periods=window
        ).mean()
        result[f"dist_ema{window}_atr"] = (
            result.close - result[f"ema{window}"]
        ) / result.atr14
    result["ema20_slope6_atr"] = (
        result.ema20 - result.ema20.shift(6)
    ) / result.atr14
    result["ema50_slope12_atr"] = (
        result.ema50 - result.ema50.shift(12)
    ) / result.atr14
    candle_range = (result.high - result.low).replace(0, np.nan)
    result["body_signed"] = (result.close - result.open) / candle_range
    result["body_ratio"] = (result.close - result.open).abs() / candle_range
    result["upper_wick_ratio"] = (
        result.high - result[["open", "close"]].max(axis=1)
    ) / candle_range
    result["lower_wick_ratio"] = (
        result[["open", "close"]].min(axis=1) - result.low
    ) / candle_range
    result["range_atr"] = candle_range / result.atr14
    result["vol_ratio20"] = (
        result.tick_volume / result.tick_volume.rolling(20).mean()
    )
    result["spread_usd"] = result.spread * 0.01
    result["spread_ratio20"] = (
        result.spread
        / result.spread.rolling(20).median().replace(0, np.nan)
    )
    absolute_delta = result.close.diff().abs()
    for window in wins:
        rolling_high = result.high.rolling(window).max()
        rolling_low = result.low.rolling(window).min()
        result[f"ret{window}_atr"] = (
            result.close - result.close.shift(window)
        ) / result.atr14
        result[f"range{window}_atr"] = (
            rolling_high - rolling_low
        ) / result.atr14
        result[f"pos{window}"] = (
            result.close - rolling_low
        ) / (rolling_high - rolling_low).replace(0, np.nan)
        result[f"eff{window}"] = (
            result.close - result.close.shift(window)
        ).abs() / absolute_delta.rolling(window).sum().replace(0, np.nan)
        result[f"volratio{window}"] = (
            result.tick_volume.rolling(window).mean()
            / result.tick_volume.rolling(window).mean().shift(window)
        )
        result[f"spreadmax{window}_usd"] = (
            result.spread.rolling(window).max() * 0.01
        )
    return result


def merge_closed(
    base: pd.DataFrame,
    source: pd.DataFrame,
    prefix: str,
    minutes: int,
    columns: list[str],
) -> pd.DataFrame:
    """As-of merge using only source rows whose nominal close is known."""
    available = source[["time"] + columns].copy()
    available["available_time"] = available.time + pd.Timedelta(minutes=minutes)
    available = available.drop(columns="time").rename(
        columns={column: f"{prefix}_{column}" for column in columns}
    )
    return pd.merge_asof(
        base.sort_values("time"),
        available.sort_values("available_time"),
        left_on="time",
        right_on="available_time",
        direction="backward",
    ).drop(columns="available_time")


def decision_times(
    raw: pd.DataFrame, minutes: int, include_next: bool
) -> pd.DataFrame:
    times = raw[["time"]].copy()
    if include_next and len(raw):
        next_time = pd.Timestamp(raw.time.max()) + pd.Timedelta(minutes=minutes)
        if next_time not in set(times.time):
            times = pd.concat(
                [times, pd.DataFrame({"time": [next_time]})],
                ignore_index=True,
            )
    return times.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def m1_arrays(m1: pd.DataFrame):
    return (
        m1.time.to_numpy("datetime64[ns]"),
        m1.open.to_numpy(float),
        m1.high.to_numpy(float),
        m1.low.to_numpy(float),
        m1.close.to_numpy(float),
        m1.tick_volume.to_numpy(float),
        m1.spread.to_numpy(float) * 0.01,
    )


def load_gold(
    candle_dir: Path, tail_only: bool = True
) -> dict[str, pd.DataFrame]:
    return {
        timeframe: read_candles(
            candle_dir / filename,
            LIVE_TAIL_ROWS[timeframe] if tail_only else None,
            timeframe=timeframe,
            require_spread=True,
        )
        for timeframe, filename in GOLD_FILES.items()
    }
