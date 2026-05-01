from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import REQUIRED_OHLC_COLUMNS, TIMEFRAME_MINUTES


@dataclass(frozen=True)
class CsvQualityReport:
    path: Path
    timeframe: str | None
    rows: int
    start_time: pd.Timestamp | None
    end_time: pd.Timestamp | None
    duplicate_times: int
    missing_required_columns: list[str]
    null_counts: dict[str, int]
    invalid_ohlc_rows: int
    negative_volume_rows: int
    negative_spread_rows: int
    spread_min: float | None
    spread_max: float | None
    spread_mean: float | None
    interval_anomaly_count: int
    interval_anomaly_examples: list[tuple[str, str, float]]


def infer_timeframe_from_filename(path: Path) -> str | None:
    """Infer timeframe from a file name like xauusd_m15.csv or btcusd_h1.csv."""
    stem = path.stem.lower()
    parts = stem.split("_")
    if not parts:
        return None
    candidate = parts[-1]
    return candidate if candidate in TIMEFRAME_MINUTES else None


def load_ohlc_csv(path: str | Path) -> pd.DataFrame:
    """Load an MT5-exported OHLC CSV.

    Expected columns:
        time, open, high, low, close, volume, spread

    Time format exported by MT5 EA:
        YYYY.MM.DD HH:MM
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_OHLC_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {csv_path}: {missing}")

    df = df[REQUIRED_OHLC_COLUMNS].copy()
    df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M", errors="coerce")

    numeric_cols = ["open", "high", "low", "close", "volume", "spread"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("time", kind="mergesort").reset_index(drop=True)
    return df


def _count_invalid_ohlc_rows(df: pd.DataFrame) -> int:
    required = ["open", "high", "low", "close"]
    if any(col not in df.columns for col in required):
        return 0

    valid = (
        (df["high"] >= df["low"])
        & (df["high"] >= df["open"])
        & (df["high"] >= df["close"])
        & (df["low"] <= df["open"])
        & (df["low"] <= df["close"])
    )
    return int((~valid).sum())


def _interval_anomalies(
    df: pd.DataFrame,
    timeframe: str | None,
    max_examples: int = 10,
) -> tuple[int, list[tuple[str, str, float]]]:
    if timeframe is None or timeframe not in TIMEFRAME_MINUTES:
        return 0, []

    if "time" not in df.columns or len(df) < 2:
        return 0, []

    expected_minutes = TIMEFRAME_MINUTES[timeframe]
    diffs = df["time"].diff().dt.total_seconds().div(60)

    # Weekend gaps and market closures can create large gaps.
    # We still report them as anomalies because they matter for backtesting.
    anomaly_mask = diffs.notna() & (diffs != expected_minutes)
    anomaly_count = int(anomaly_mask.sum())

    examples: list[tuple[str, str, float]] = []
    anomaly_indices = df.index[anomaly_mask].tolist()[:max_examples]
    for idx in anomaly_indices:
        prev_time = df.loc[idx - 1, "time"] if idx > 0 else pd.NaT
        curr_time = df.loc[idx, "time"]
        diff_value = diffs.loc[idx]
        examples.append((str(prev_time), str(curr_time), float(diff_value)))

    return anomaly_count, examples


def build_quality_report(path: str | Path) -> CsvQualityReport:
    csv_path = Path(path)
    timeframe = infer_timeframe_from_filename(csv_path)

    # For a report, we do not want to immediately fail on missing columns.
    raw = pd.read_csv(csv_path)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    missing_columns = [c for c in REQUIRED_OHLC_COLUMNS if c not in raw.columns]

    if missing_columns:
        return CsvQualityReport(
            path=csv_path,
            timeframe=timeframe,
            rows=len(raw),
            start_time=None,
            end_time=None,
            duplicate_times=0,
            missing_required_columns=missing_columns,
            null_counts={},
            invalid_ohlc_rows=0,
            negative_volume_rows=0,
            negative_spread_rows=0,
            spread_min=None,
            spread_max=None,
            spread_mean=None,
            interval_anomaly_count=0,
            interval_anomaly_examples=[],
        )

    df = load_ohlc_csv(csv_path)

    duplicate_times = int(df["time"].duplicated().sum())
    null_counts = {col: int(df[col].isna().sum()) for col in REQUIRED_OHLC_COLUMNS}
    invalid_ohlc_rows = _count_invalid_ohlc_rows(df)
    negative_volume_rows = int((df["volume"] < 0).sum())
    negative_spread_rows = int((df["spread"] < 0).sum())

    spread_non_null = df["spread"].dropna()
    spread_min = float(spread_non_null.min()) if not spread_non_null.empty else None
    spread_max = float(spread_non_null.max()) if not spread_non_null.empty else None
    spread_mean = float(spread_non_null.mean()) if not spread_non_null.empty else None

    interval_count, interval_examples = _interval_anomalies(df, timeframe)

    time_non_null = df["time"].dropna()
    start_time = time_non_null.iloc[0] if not time_non_null.empty else None
    end_time = time_non_null.iloc[-1] if not time_non_null.empty else None

    return CsvQualityReport(
        path=csv_path,
        timeframe=timeframe,
        rows=len(df),
        start_time=start_time,
        end_time=end_time,
        duplicate_times=duplicate_times,
        missing_required_columns=missing_columns,
        null_counts=null_counts,
        invalid_ohlc_rows=invalid_ohlc_rows,
        negative_volume_rows=negative_volume_rows,
        negative_spread_rows=negative_spread_rows,
        spread_min=spread_min,
        spread_max=spread_max,
        spread_mean=spread_mean,
        interval_anomaly_count=interval_count,
        interval_anomaly_examples=interval_examples,
    )


def find_csv_files(raw_data_dir: Path, symbols: Iterable[str], timeframes: Iterable[str]) -> list[Path]:
    """Find expected CSV files such as data/raw/xauusd_m15.csv."""
    files: list[Path] = []
    for symbol in symbols:
        for timeframe in timeframes:
            path = raw_data_dir / f"{symbol.lower()}_{timeframe.lower()}.csv"
            if path.exists():
                files.append(path)
    return files
