from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

TIMEFRAME_MINUTES: dict[str, int] = {
    "M5": 5,
    "M15": 15,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


@dataclass(frozen=True)
class BarClock:
    timeframe: str
    open_time: pd.Timestamp
    available_time: pd.Timestamp


def normalize_timeframe(timeframe: str) -> str:
    key = str(timeframe).upper()
    if key not in TIMEFRAME_MINUTES:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return key


def duration(timeframe: str) -> pd.Timedelta:
    key = normalize_timeframe(timeframe)
    return pd.Timedelta(minutes=TIMEFRAME_MINUTES[key])


def available_time(open_time: Any, timeframe: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(open_time)
    if pd.isna(timestamp):
        raise ValueError("open_time is NaT")
    return timestamp + duration(timeframe)


def add_available_time(
    frame: pd.DataFrame,
    timeframe: str,
    *,
    open_column: str = "time",
    output_column: str = "available_time",
) -> pd.DataFrame:
    if open_column not in frame.columns:
        raise KeyError(open_column)
    output = frame.copy()
    output[open_column] = pd.to_datetime(output[open_column], errors="raise")
    output[output_column] = output[open_column] + duration(timeframe)
    return output


def require_strict_time_order(frame: pd.DataFrame, *, time_column: str = "time") -> None:
    if time_column not in frame.columns:
        raise KeyError(time_column)
    times = pd.to_datetime(frame[time_column], errors="raise")
    if len(times) == 0:
        raise ValueError("empty time series")
    if not times.is_monotonic_increasing:
        raise ValueError(f"{time_column} is not ascending")
    duplicated = int(times.duplicated(keep=False).sum())
    if duplicated:
        raise ValueError(f"{time_column} has {duplicated} duplicated rows")


def exact_open_index(
    frame: pd.DataFrame,
    open_time: Any,
    *,
    time_column: str = "time",
) -> int | None:
    require_strict_time_order(frame, time_column=time_column)
    target = pd.Timestamp(open_time)
    matches = frame.index[pd.to_datetime(frame[time_column]) == target]
    if len(matches) == 0:
        return None
    if len(matches) != 1:
        raise ValueError(f"expected one exact open row at {target}, got {len(matches)}")
    return int(matches[0])


def causal_asof(
    decisions: pd.DataFrame,
    source: pd.DataFrame,
    *,
    decision_time_column: str,
    source_open_column: str,
    source_timeframe: str,
    source_available_column: str = "source_available_time",
    allow_equal: bool = True,
    suffixes: tuple[str, str] = ("", "_source"),
) -> pd.DataFrame:
    if decision_time_column not in decisions.columns:
        raise KeyError(decision_time_column)
    if source_open_column not in source.columns:
        raise KeyError(source_open_column)
    left = decisions.copy()
    right = source.copy()
    left[decision_time_column] = pd.to_datetime(left[decision_time_column], errors="raise")
    right[source_open_column] = pd.to_datetime(right[source_open_column], errors="raise")
    right[source_available_column] = right[source_open_column] + duration(source_timeframe)
    left = left.sort_values(decision_time_column)
    right = right.sort_values(source_available_column)
    merged = pd.merge_asof(
        left,
        right,
        left_on=decision_time_column,
        right_on=source_available_column,
        direction="backward",
        allow_exact_matches=allow_equal,
        suffixes=suffixes,
    )
    used = merged[source_available_column].notna()
    if allow_equal:
        invalid = used & (merged[source_available_column] > merged[decision_time_column])
    else:
        invalid = used & (merged[source_available_column] >= merged[decision_time_column])
    if bool(invalid.any()):
        raise RuntimeError("causal_asof selected unavailable source rows")
    return merged


def conservative_htf_asof(
    signal_bars: pd.DataFrame,
    higher: pd.DataFrame,
    *,
    signal_open_column: str = "time",
    higher_open_column: str = "time",
    higher_timeframe: str,
) -> pd.DataFrame:
    """Use only higher-timeframe bars available by the signal bar OPEN.

    This deliberately excludes a higher-timeframe bar that closes at the
    signal bar close. It avoids same-boundary ordering ambiguity.
    """
    decisions = signal_bars.copy()
    decisions["signal_open_decision_time"] = pd.to_datetime(
        decisions[signal_open_column], errors="raise"
    )
    return causal_asof(
        decisions,
        higher,
        decision_time_column="signal_open_decision_time",
        source_open_column=higher_open_column,
        source_timeframe=higher_timeframe,
        source_available_column="higher_available_time",
        allow_equal=True,
    )


def signal_decision_time(signal_open_time: Any, signal_timeframe: str) -> pd.Timestamp:
    return available_time(signal_open_time, signal_timeframe)


def exit_observation_time(bar_open_time: Any, execution_timeframe: str = "M5") -> pd.Timestamp:
    return available_time(bar_open_time, execution_timeframe)
