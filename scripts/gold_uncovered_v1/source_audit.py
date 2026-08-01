from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

TRACK_ID = "GOLD_UNCOVERED_V1"
REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "tick_volume", "spread")
VALUE_COLUMNS = ("open", "high", "low", "close", "tick_volume", "spread", "real_volume")
REQUIRED_HISTORICAL = ("M1", "M5", "M15", "H1", "H4")
REQUIRED_SHARP = ("M1", "M5", "H1", "H4")
OVERLAP_TIMEFRAMES = ("M1", "M5", "H1", "H4")


def normalize_name(value: str) -> str:
    return str(value).strip().lower().replace("\ufeff", "")


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def delimiter_for(line: str) -> str:
    counts = {",": line.count(","), ";": line.count(";"), "\t": line.count("\t")}
    delimiter = max(counts, key=counts.get)
    if counts[delimiter] <= 0:
        raise ValueError("Could not determine CSV delimiter")
    return delimiter


def parse_time(value: str) -> datetime:
    text = str(value).strip()
    formats = (
        "%Y.%m.%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d %H:%M",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported time value: {text!r}")


def decimal_value(value: str) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid numeric value: {value!r}") from exc


def reader_for(path: Path):
    handle = path.open("r", encoding="utf-8-sig", newline="")
    first_line = handle.readline()
    if not first_line:
        handle.close()
        raise ValueError(f"Empty CSV: {path}")
    delimiter = delimiter_for(first_line)
    handle.seek(0)
    reader = csv.DictReader(handle, delimiter=delimiter)
    if reader.fieldnames is None:
        handle.close()
        raise ValueError(f"Missing CSV header: {path}")
    original = list(reader.fieldnames)
    normalized = [normalize_name(name) for name in original]
    if len(set(normalized)) != len(normalized):
        handle.close()
        raise ValueError(f"Duplicate normalized columns: {path}: {normalized}")
    name_map = dict(zip(original, normalized))
    return handle, reader, name_map, delimiter


def normalized_row(row: dict[str, str], name_map: dict[str, str]) -> dict[str, str]:
    return {name_map[key]: value for key, value in row.items() if key in name_map}


def inspect_csv(path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
    }
    if not path.exists():
        return report

    report["sha256"] = sha256_file(path)
    report["modified_at_utc"] = datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc
    ).isoformat()

    handle = None
    try:
        handle, reader, name_map, delimiter = reader_for(path)
        columns = list(name_map.values())
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        report["delimiter"] = delimiter
        report["columns"] = columns
        report["schema_ok"] = not missing
        report["missing_columns"] = missing
        if missing:
            return report

        rows = 0
        malformed_rows = 0
        duplicate_times = 0
        nonascending_rows = 0
        invalid_ohlc_rows = 0
        first_time: datetime | None = None
        last_time: datetime | None = None
        previous_time: datetime | None = None
        seen: set[datetime] = set()

        for raw in reader:
            rows += 1
            try:
                row = normalized_row(raw, name_map)
                current_time = parse_time(row["time"])
                if first_time is None:
                    first_time = current_time
                last_time = current_time
                if current_time in seen:
                    duplicate_times += 1
                else:
                    seen.add(current_time)
                if previous_time is not None and current_time <= previous_time:
                    nonascending_rows += 1
                previous_time = current_time

                open_value = decimal_value(row["open"])
                high_value = decimal_value(row["high"])
                low_value = decimal_value(row["low"])
                close_value = decimal_value(row["close"])
                decimal_value(row["tick_volume"])
                decimal_value(row["spread"])
                if "real_volume" in row and str(row["real_volume"]).strip() != "":
                    decimal_value(row["real_volume"])
                if (
                    high_value < max(open_value, close_value)
                    or low_value > min(open_value, close_value)
                    or high_value < low_value
                ):
                    invalid_ohlc_rows += 1
            except Exception:
                malformed_rows += 1

        report.update(
            {
                "rows": rows,
                "first_time": None if first_time is None else first_time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_time": None if last_time is None else last_time.strftime("%Y-%m-%d %H:%M:%S"),
                "duplicate_time_count": duplicate_times,
                "nonascending_row_count": nonascending_rows,
                "strictly_increasing": duplicate_times == 0 and nonascending_rows == 0,
                "malformed_row_count": malformed_rows,
                "invalid_ohlc_row_count": invalid_ohlc_rows,
            }
        )
        return report
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        return report
    finally:
        if handle is not None:
            handle.close()


def find_paths(search_root: Path, reference: dict[str, Any]) -> dict[str, dict[str, list[Path]]]:
    result: dict[str, dict[str, list[Path]]] = {"historical": {}, "sharp": {}}
    terminal_roots = sorted(path for path in search_root.iterdir() if path.is_dir()) if search_root.exists() else []

    for timeframe, spec in reference["historical_sources"].items():
        suffix = Path(str(spec["relative_suffix"]).replace("\\", os.sep))
        found = [terminal / suffix for terminal in terminal_roots if (terminal / suffix).is_file()]
        result["historical"][timeframe] = sorted({path.resolve() for path in found}, key=str)

    for timeframe, spec in reference["sharp_sources"].items():
        filename = str(spec["filename"])
        found = [
            terminal / "MQL5" / "Files" / filename
            for terminal in terminal_roots
            if (terminal / "MQL5" / "Files" / filename).is_file()
        ]
        result["sharp"][timeframe] = sorted({path.resolve() for path in found}, key=str)

    return result


def canonical_signature(row: dict[str, str], columns: Iterable[str]) -> tuple[str, ...]:
    values: list[str] = []
    for column in columns:
        text = str(row.get(column, "")).strip()
        if text == "":
            values.append("")
        else:
            values.append(format(decimal_value(text), "f"))
    return tuple(values)


def load_shared_rows(path: Path, shared_columns: list[str]) -> dict[datetime, tuple[str, ...]]:
    handle = None
    output: dict[datetime, tuple[str, ...]] = {}
    try:
        handle, reader, name_map, _ = reader_for(path)
        columns = set(name_map.values())
        required = {"time", *shared_columns}
        missing = sorted(required - columns)
        if missing:
            raise ValueError(f"Overlap source missing columns {missing}: {path}")
        for raw in reader:
            row = normalized_row(raw, name_map)
            output[parse_time(row["time"])] = canonical_signature(row, shared_columns)
        return output
    finally:
        if handle is not None:
            handle.close()


def compare_overlap(historical: Path, sharp: Path) -> dict[str, Any]:
    historical_report = inspect_csv(historical)
    sharp_report = inspect_csv(sharp)
    common_columns = [
        column
        for column in VALUE_COLUMNS
        if column in historical_report.get("columns", [])
        and column in sharp_report.get("columns", [])
    ]
    report: dict[str, Any] = {
        "historical_path": str(historical),
        "sharp_path": str(sharp),
        "shared_columns": common_columns,
    }
    if not common_columns:
        report["error"] = "NO_SHARED_VALUE_COLUMNS"
        return report

    sharp_rows = load_shared_rows(sharp, common_columns)
    handle = None
    overlap_rows = 0
    mismatch_rows = 0
    first_mismatch: dict[str, Any] | None = None
    try:
        handle, reader, name_map, _ = reader_for(historical)
        for raw in reader:
            row = normalized_row(raw, name_map)
            timestamp = parse_time(row["time"])
            expected = sharp_rows.get(timestamp)
            if expected is None:
                continue
            overlap_rows += 1
            observed = canonical_signature(row, common_columns)
            if observed != expected:
                mismatch_rows += 1
                if first_mismatch is None:
                    first_mismatch = {
                        "time": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "historical": dict(zip(common_columns, observed)),
                        "sharp": dict(zip(common_columns, expected)),
                    }
    finally:
        if handle is not None:
            handle.close()

    report.update(
        {
            "overlap_rows": overlap_rows,
            "mismatch_rows": mismatch_rows,
            "first_mismatch": first_mismatch,
            "exact_overlap": overlap_rows > 0 and mismatch_rows == 0,
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only raw candle source audit for GOLD Uncovered V1")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    reference_path = args.reference.resolve()
    output_path = args.output.resolve()
    reference = read_json(reference_path)
    search_root = expand_path(str(reference["search_root"]))
    located = find_paths(search_root, reference)

    report: dict[str, Any] = {
        "track_id": TRACK_ID,
        "mode": "READ_ONLY_SOURCE_AUDIT_NO_OUTCOMES",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_path": str(reference_path),
        "search_root": str(search_root),
        "prohibited_reads": [
            "V19 local config or state",
            "Challenger C1 local config or state",
            "signal, trade, label or outcome ledgers",
        ],
        "sources": {"historical": {}, "sharp": {}},
        "overlap_checks": {},
        "issues": [],
    }

    selected: dict[str, dict[str, Path]] = {"historical": {}, "sharp": {}}

    for family in ("historical", "sharp"):
        for timeframe, paths in located[family].items():
            inspections = [inspect_csv(path) for path in paths]
            report["sources"][family][timeframe] = {
                "candidate_count": len(paths),
                "candidates": inspections,
            }
            required = (
                timeframe in REQUIRED_HISTORICAL
                if family == "historical"
                else timeframe in REQUIRED_SHARP
            )
            if required and len(paths) != 1:
                report["issues"].append(
                    f"{family.upper()}_{timeframe}_CANDIDATE_COUNT_{len(paths)}"
                )
            if len(paths) == 1:
                selected[family][timeframe] = paths[0]

    for timeframe in REQUIRED_HISTORICAL:
        path = selected["historical"].get(timeframe)
        if path is None:
            continue
        spec = reference["historical_sources"][timeframe]
        inspection = report["sources"]["historical"][timeframe]["candidates"][0]
        if inspection.get("sha256") != spec.get("expected_sha256"):
            report["issues"].append(f"HISTORICAL_{timeframe}_HASH_MISMATCH")
        if int(inspection.get("rows", -1)) != int(spec.get("expected_rows", -2)):
            report["issues"].append(f"HISTORICAL_{timeframe}_ROW_COUNT_MISMATCH")
        if inspection.get("first_time") != spec.get("expected_first_time"):
            report["issues"].append(f"HISTORICAL_{timeframe}_FIRST_TIME_MISMATCH")
        if inspection.get("last_time") != spec.get("expected_last_time"):
            report["issues"].append(f"HISTORICAL_{timeframe}_LAST_TIME_MISMATCH")

    for family, required_frames in (("historical", REQUIRED_HISTORICAL), ("sharp", REQUIRED_SHARP)):
        for timeframe in required_frames:
            source = report["sources"][family].get(timeframe, {})
            candidates = source.get("candidates", [])
            if len(candidates) != 1:
                continue
            inspection = candidates[0]
            if not inspection.get("schema_ok", False):
                report["issues"].append(f"{family.upper()}_{timeframe}_SCHEMA_INVALID")
            if not inspection.get("strictly_increasing", False):
                report["issues"].append(f"{family.upper()}_{timeframe}_TIME_INVALID")
            if int(inspection.get("malformed_row_count", 1)) != 0:
                report["issues"].append(f"{family.upper()}_{timeframe}_MALFORMED_ROWS")
            if int(inspection.get("invalid_ohlc_row_count", 1)) != 0:
                report["issues"].append(f"{family.upper()}_{timeframe}_INVALID_OHLC")

    for timeframe in OVERLAP_TIMEFRAMES:
        old_path = selected["historical"].get(timeframe)
        sharp_path = selected["sharp"].get(timeframe)
        if old_path is None or sharp_path is None:
            report["overlap_checks"][timeframe] = {"status": "NOT_RUN_MISSING_SOURCE"}
            report["issues"].append(f"OVERLAP_{timeframe}_NOT_RUN")
            continue
        comparison = compare_overlap(old_path, sharp_path)
        report["overlap_checks"][timeframe] = comparison
        if not comparison.get("exact_overlap", False):
            report["issues"].append(f"OVERLAP_{timeframe}_MISMATCH_OR_EMPTY")

    report["issues"] = sorted(set(report["issues"]))
    report["status"] = "PASS" if not report["issues"] else "BLOCKED"
    report["next_action"] = (
        "FREEZE_AUTHORITATIVE_SOURCE_MANIFEST"
        if report["status"] == "PASS"
        else "STOP_AND_REVIEW_SOURCE_AUDIT"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print(json.dumps(
        {
            "status": report["status"],
            "output": str(output_path),
            "issue_count": len(report["issues"]),
            "issues": report["issues"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
