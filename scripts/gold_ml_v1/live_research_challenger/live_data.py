from __future__ import annotations

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


def _delimiter(path: Path, encoding: str) -> str:
    with path.open("r", encoding=encoding, errors="strict") as handle:
        line = handle.readline()
    counts = {",": line.count(","), ";": line.count(";"), "\t": line.count("\t")}
    delimiter, count = max(counts.items(), key=lambda item: item[1])
    if count <= 0:
        raise ValueError(f"Could not detect delimiter for {path}")
    return delimiter


def _read_delimited(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-16", "cp932"):
        try:
            return pd.read_csv(
                path,
                sep=_delimiter(path, encoding),
                encoding=encoding,
                engine="c",
            )
        except Exception as exc:
            errors.append(f"{encoding}:{type(exc).__name__}:{exc}")
    raise ValueError(f"Could not parse {path}: {' | '.join(errors)}")


def read_closed_bars(path: Path, timeframe: str) -> pd.DataFrame:
    if timeframe not in TF_DELTA:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = _read_delimited(path)
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


def read_live_bars(root: Path) -> dict[str, pd.DataFrame]:
    bars = {
        timeframe: read_closed_bars(root / filename, timeframe)
        for timeframe, filename in FILE_BY_TF.items()
    }
    minimums = {"M1": 2, "M5": 2, "M15": 500, "H1": 200, "H4": 200, "D1": 100}
    for timeframe, minimum in minimums.items():
        if len(bars[timeframe]) < minimum:
            raise ValueError(
                f"{timeframe}: {len(bars[timeframe])} rows; at least {minimum} required"
            )
    return bars
