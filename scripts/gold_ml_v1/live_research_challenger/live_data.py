from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH_DIR = Path(__file__).resolve().parents[1] / "research_challenger"
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from raw_engine import (  # noqa: E402
    POINT,
    TF_DELTA,
    atr_simple,
    atr_wilder,
    rci_rank_difference,
    rsi_wilder,
    trailing_percentile_current,
)

FILE_BY_TF = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}


def canonical_column(value: str) -> str:
    return (
        str(value)
        .replace("\ufeff", "")
        .strip()
        .strip("<>")
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _header_format(path: Path) -> tuple[str, str, str]:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-16", "cp932"):
        try:
            with path.open("r", encoding=encoding, errors="strict") as handle:
                header = handle.readline().rstrip("\r\n")
            counts = {",": header.count(","), ";": header.count(";"), "\t": header.count("\t")}
            delimiter, count = max(counts.items(), key=lambda item: item[1])
            if count <= 0:
                raise ValueError("delimiter not detected")
            return encoding, delimiter, header
        except Exception as exc:
            errors.append(f"{encoding}:{type(exc).__name__}:{exc}")
    raise ValueError(f"Could not inspect {path}: {' | '.join(errors)}")


def _read_delimited(path: Path) -> pd.DataFrame:
    encoding, delimiter, _ = _header_format(path)
    return pd.read_csv(path, sep=delimiter, encoding=encoding, engine="c")


def _last_binary_lines(path: Path, line_count: int) -> list[bytes]:
    if line_count <= 0:
        return []
    chunk_size = 1024 * 1024
    with path.open("rb") as handle:
        handle.seek(0, 2)
        position = handle.tell()
        payload = b""
        while position > 0 and payload.count(b"\n") <= line_count:
            read_size = min(chunk_size, position)
            position -= read_size
            handle.seek(position)
            payload = handle.read(read_size) + payload
    lines = payload.splitlines()
    if position > 0 and lines:
        lines = lines[1:]
    return lines[-line_count:]


def _read_delimited_tail(path: Path, max_rows: int) -> pd.DataFrame:
    encoding, delimiter, header = _header_format(path)
    if encoding == "utf-16":
        return pd.read_csv(path, sep=delimiter, encoding=encoding, engine="c").tail(max_rows)
    lines = _last_binary_lines(path, max_rows)
    decoded = [line.decode(encoding, errors="strict") for line in lines]
    decoded = [line for line in decoded if line.strip()]
    if decoded and canonical_column(decoded[0].split(delimiter)[0]) == canonical_column(header.split(delimiter)[0]):
        decoded = decoded[1:]
    text = header + "\n" + "\n".join(decoded)
    return pd.read_csv(io.StringIO(text), sep=delimiter, engine="c")


def read_closed_bars(path: Path, timeframe: str, max_rows: int | None = None) -> pd.DataFrame:
    if timeframe not in TF_DELTA:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = _read_delimited(path) if max_rows is None else _read_delimited_tail(path, max_rows)
    raw.columns = [canonical_column(column) for column in raw.columns]
    aliases = {
        "tickvol": "tick_volume",
        "tickvolume": "tick_volume",
        "tick_vol": "tick_volume",
        "realvolume": "real_volume",
        "real_vol": "real_volume",
    }
    raw = raw.rename(columns={column: aliases.get(column, column) for column in raw.columns})

    if "date" in raw.columns and "time" in raw.columns:
        timestamp_text = raw["date"].astype(str).str.strip() + " " + raw["time"].astype(str).str.strip()
    elif "datetime" in raw.columns:
        timestamp_text = raw["datetime"].astype(str).str.strip()
    elif "timestamp" in raw.columns:
        timestamp_text = raw["timestamp"].astype(str).str.strip()
    elif "time" in raw.columns:
        timestamp_text = raw["time"].astype(str).str.strip()
    else:
        raise ValueError(f"{path}: no time/datetime column")

    required_numeric = ["open", "high", "low", "close", "tick_volume", "spread"]
    missing = [column for column in required_numeric if column not in raw.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")

    frame = pd.DataFrame(index=raw.index)
    frame["bar_open_time"] = pd.to_datetime(timestamp_text, errors="coerce")
    for column in required_numeric:
        frame[column] = pd.to_numeric(raw[column], errors="coerce")
    frame["real_volume"] = (
        pd.to_numeric(raw["real_volume"], errors="coerce")
        if "real_volume" in raw.columns
        else 0.0
    )

    valid = frame[["bar_open_time", *required_numeric]].notna().all(axis=1)
    if not bool(valid.all()):
        first_invalid = int(np.flatnonzero(~valid.to_numpy())[0])
        if bool(valid.iloc[first_invalid:].any()):
            bad_rows = frame.index[~valid].tolist()[:10]
            raise ValueError(f"{path}: invalid non-trailing rows {bad_rows}")
        frame = frame.iloc[:first_invalid].copy()

    if frame.empty:
        raise ValueError(f"{path}: no complete rows")
    if frame["bar_open_time"].duplicated().any():
        raise ValueError(f"{path}: duplicate times")
    if not frame["bar_open_time"].is_monotonic_increasing:
        raise ValueError(f"{path}: time is not monotonic increasing; silent sorting is forbidden")

    frame = frame.reset_index(drop=True)
    frame["bar_close_time"] = frame["bar_open_time"] + TF_DELTA[timeframe]
    frame["timeframe"] = timeframe
    return frame


def probe_latest_bars(root: Path) -> dict[str, dict[str, pd.Timestamp]]:
    result: dict[str, dict[str, pd.Timestamp]] = {}
    for timeframe, filename in FILE_BY_TF.items():
        frame = read_closed_bars(root / filename, timeframe, max_rows=4)
        result[timeframe] = {
            "open": pd.Timestamp(frame["bar_open_time"].iloc[-1]),
            "close": pd.Timestamp(frame["bar_close_time"].iloc[-1]),
        }
    return result


def _cap_source_at_missing_higher_boundary(
    source: pd.DataFrame,
    higher: pd.DataFrame,
    source_timeframe: str,
    higher_timeframe: str,
) -> tuple[pd.DataFrame, str | None]:
    source_close = source["bar_close_time"]
    higher_latest = pd.Timestamp(higher["bar_close_time"].iloc[-1])
    if higher_timeframe == "H4":
        boundary_mask = (
            source_close.dt.minute.eq(0)
            & source_close.dt.hour.mod(4).eq(0)
            & (source_close > higher_latest)
        )
        step = pd.Timedelta(minutes=15)
        reason = "M15_WAIT_H4_BOUNDARY"
    elif higher_timeframe == "D1":
        boundary_mask = (
            source_close.dt.hour.eq(0)
            & source_close.dt.minute.eq(0)
            & (source_close > higher_latest)
        )
        step = pd.Timedelta(hours=1)
        reason = "H1_WAIT_D1_BOUNDARY"
    else:
        raise ValueError(f"Unsupported higher timeframe: {higher_timeframe}")

    boundaries = source_close[boundary_mask]
    if boundaries.empty:
        return source, None
    first_missing_boundary = pd.Timestamp(boundaries.iloc[0])
    capped = source[source_close <= first_missing_boundary - step].copy()
    if capped.empty:
        raise ValueError(
            f"{source_timeframe}: no rows remain before missing {higher_timeframe} boundary"
        )
    capped.attrs["sync_waiting"] = reason
    capped.attrs["missing_boundary"] = first_missing_boundary.strftime("%Y-%m-%d %H:%M:%S")
    return capped, reason


def read_live_bars(
    root: Path,
    m1_since: pd.Timestamp | None = None,
    latest_probe: dict[str, dict[str, pd.Timestamp]] | None = None,
) -> dict[str, pd.DataFrame]:
    probe = latest_probe or probe_latest_bars(root)
    if m1_since is None:
        m1_rows = 20000
    else:
        elapsed_minutes = max(
            0,
            int((probe["M1"]["open"] - pd.Timestamp(m1_since)) / pd.Timedelta(minutes=1)),
        )
        m1_rows = max(2000, elapsed_minutes + 5000)

    bars = {
        "M1": read_closed_bars(root / FILE_BY_TF["M1"], "M1", max_rows=m1_rows),
        "M5": read_closed_bars(root / FILE_BY_TF["M5"], "M5", max_rows=4),
        "M15": read_closed_bars(root / FILE_BY_TF["M15"], "M15"),
        "H1": read_closed_bars(root / FILE_BY_TF["H1"], "H1"),
        "H4": read_closed_bars(root / FILE_BY_TF["H4"], "H4"),
        "D1": read_closed_bars(root / FILE_BY_TF["D1"], "D1"),
    }
    bars["M15"], m15_wait = _cap_source_at_missing_higher_boundary(
        bars["M15"], bars["H4"], "M15", "H4"
    )
    bars["H1"], h1_wait = _cap_source_at_missing_higher_boundary(
        bars["H1"], bars["D1"], "H1", "D1"
    )
    bars["M15"].attrs["sync_waiting"] = m15_wait
    bars["H1"].attrs["sync_waiting"] = h1_wait

    minimums = {"M1": 2, "M5": 2, "M15": 500, "H1": 200, "H4": 200, "D1": 100}
    for timeframe, minimum in minimums.items():
        if len(bars[timeframe]) < minimum:
            raise ValueError(
                f"{timeframe}: {len(bars[timeframe])} rows; at least {minimum} required"
            )
    return bars
