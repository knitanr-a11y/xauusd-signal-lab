from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "xm_kiwami"

EXPECTED_FILES = {
    "GOLD# M15": DATA_DIR / "goldsharp_m15.csv",
    "GOLD# H1": DATA_DIR / "goldsharp_h1.csv",
    "BTCUSD# M15": DATA_DIR / "btcusdsharp_m15.csv",
    "BTCUSD# H1": DATA_DIR / "btcusdsharp_h1.csv",
}

REQUIRED_COLUMNS = ["time", "open", "high", "low", "close", "volume", "spread"]
TIME_FORMATS = ["%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]


@dataclass(frozen=True)
class CsvSummary:
    label: str
    path: Path
    rows: int
    start_time: datetime | None
    end_time: datetime | None
    spread_avg: float | None
    spread_min: float | None
    spread_max: float | None
    columns_ok: bool
    required_missing: list[str]


def parse_time(value: str) -> datetime | None:
    value = value.strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_csv(label: str, path: Path) -> CsvSummary:
    if not path.exists():
        raise FileNotFoundError(f"missing file: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"empty file: {path}")

    times: list[datetime] = []
    spreads: list[float] = []
    rows = 0

    with path.open("r", encoding="cp932", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        required_missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
        columns_ok = len(required_missing) == 0

        for row in reader:
            rows += 1
            t = parse_time(str(row.get("time", "")))
            if t is not None:
                times.append(t)

            spread = to_float(str(row.get("spread", "")))
            if spread is not None:
                spreads.append(spread)

    return CsvSummary(
        label=label,
        path=path,
        rows=rows,
        start_time=min(times) if times else None,
        end_time=max(times) if times else None,
        spread_avg=mean(spreads) if spreads else None,
        spread_min=min(spreads) if spreads else None,
        spread_max=max(spreads) if spreads else None,
        columns_ok=columns_ok,
        required_missing=required_missing,
    )


def fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%Y-%m-%d %H:%M")


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def print_summary(summary: CsvSummary) -> None:
    rel_path = summary.path.relative_to(ROOT)
    print("-" * 80)
    print(f"{summary.label}")
    print(f"file         : {rel_path}")
    print(f"rows         : {summary.rows}")
    print(f"period       : {fmt_dt(summary.start_time)} -> {fmt_dt(summary.end_time)}")
    print(f"spread avg   : {fmt_num(summary.spread_avg)}")
    print(f"spread min   : {fmt_num(summary.spread_min)}")
    print(f"spread max   : {fmt_num(summary.spread_max)}")
    print(f"columns ok   : {summary.columns_ok}")
    if summary.required_missing:
        print(f"missing cols : {', '.join(summary.required_missing)}")


def main() -> int:
    print("XM KIWAMI data verification")
    print(f"repo root: {ROOT}")
    print(f"data dir : {DATA_DIR}")

    has_error = False

    for label, path in EXPECTED_FILES.items():
        try:
            summary = summarize_csv(label, path)
            print_summary(summary)
            if not summary.columns_ok or summary.rows <= 0:
                has_error = True
        except Exception as exc:
            has_error = True
            print("-" * 80)
            print(label)
            print(f"ERROR: {exc}")

    print("-" * 80)
    if has_error:
        print("RESULT: NG - missing/empty/invalid file exists.")
        return 1

    print("RESULT: OK - all XM KIWAMI CSV files are readable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
