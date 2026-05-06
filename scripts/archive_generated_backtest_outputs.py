#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archive generated backtest/report output files so they are not accidentally
picked up by later candidate-search, live-notifier, or audit scripts.

This script is intentionally conservative:
- default mode is dry-run
- it moves files, never deletes them
- it only scans known generated-output directories
- it never touches MQL5/Files source CSVs, scripts, docs, or raw market-data inputs
- it supports Windows long paths via the \\?\ prefix
- it continues with warnings if a file disappeared between planning and moving

Typical usage from repository root:

    python scripts/archive_generated_backtest_outputs.py
    python scripts/archive_generated_backtest_outputs.py --apply

Optional:

    python scripts/archive_generated_backtest_outputs.py --apply --label before_confirmed_time_research
    python scripts/archive_generated_backtest_outputs.py --apply --include-parquet
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DEFAULT_SCAN_DIRS = [
    "data/results",
    "results",
    "reports",
    "outputs",
]

# Do not scan these directories even if they exist under an output tree.
EXCLUDED_DIR_PARTS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "_archive",
    "archive",
    "runtime_logs",  # keep live-loop health logs in place unless explicitly handled elsewhere
}

# Generated files that are safe to archive. CSV is the main target.
DEFAULT_EXTENSIONS = {
    ".csv",
    ".json",
    ".txt",
    ".log",
    ".html",
    ".png",
    ".jpg",
    ".jpeg",
}

OPTIONAL_EXTENSIONS = {
    ".parquet",
    ".pkl",
    ".pickle",
}

# Extra safety: do not move these even if they appear in an output directory.
# Add exact file names here if a future script stores required configs under data/results.
PROTECTED_FILE_NAMES = {
    ".gitkeep",
    "README.md",
}


@dataclass(frozen=True)
class ArchiveItem:
    source: str
    destination: str
    size_bytes: int
    suffix: str


@dataclass(frozen=True)
class MoveResult:
    source: str
    destination: str
    status: str
    message: str


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def to_windows_long_path(path: Path) -> str:
    """Return a Windows extended-length path when running on Windows.

    Python/shutil can fail with WinError 3 when the final archive path becomes
    too long. The \\?\ prefix lets Windows APIs handle paths beyond the old
    MAX_PATH limit in most normal cases.
    """
    resolved = str(path.resolve())
    if os.name != "nt":
        return resolved
    if resolved.startswith("\\\\?\\"):
        return resolved
    if resolved.startswith("\\\\"):
        # UNC path: \\server\share -> \\?\UNC\server\share
        return "\\\\?\\UNC\\" + resolved.lstrip("\\")
    return "\\\\?\\" + resolved


def is_under_excluded_dir(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part in EXCLUDED_DIR_PARTS for part in rel.parts)


def unique_destination(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    for idx in range(1, 10_000):
        candidate = parent / f"{stem}__dup{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique destination for {dest}")


def iter_generated_files(
    root: Path,
    scan_dirs: Iterable[str],
    extensions: set[str],
) -> Iterable[Path]:
    for scan_dir_str in scan_dirs:
        scan_dir = (root / scan_dir_str).resolve()
        if not scan_dir.exists() or not scan_dir.is_dir():
            continue

        for path in scan_dir.rglob("*"):
            if not path.is_file():
                continue
            if is_under_excluded_dir(path, root):
                continue
            if path.name in PROTECTED_FILE_NAMES:
                continue
            if path.suffix.lower() not in extensions:
                continue
            yield path


def build_archive_plan(
    root: Path,
    archive_root: Path,
    scan_dirs: list[str],
    extensions: set[str],
) -> list[ArchiveItem]:
    items: list[ArchiveItem] = []
    for src in sorted(iter_generated_files(root, scan_dirs, extensions)):
        rel = src.relative_to(root)
        dest = unique_destination(archive_root / rel)
        items.append(
            ArchiveItem(
                source=str(rel).replace("\\", "/"),
                destination=str(dest.relative_to(root)).replace("\\", "/"),
                size_bytes=src.stat().st_size,
                suffix=src.suffix.lower(),
            )
        )
    return items


def write_manifest(
    root: Path,
    archive_root: Path,
    items: list[ArchiveItem],
    move_results: list[MoveResult],
) -> None:
    archive_root.mkdir(parents=True, exist_ok=True)

    csv_path = archive_root / "archive_manifest.csv"
    json_path = archive_root / "archive_manifest.json"
    results_csv_path = archive_root / "archive_move_results.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source", "destination", "size_bytes", "suffix"],
        )
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))

    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(item) for item in items], f, ensure_ascii=False, indent=2)

    with results_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source", "destination", "status", "message"],
        )
        writer.writeheader()
        for result in move_results:
            writer.writerow(asdict(result))

    print(f"manifest_csv: {csv_path.relative_to(root)}")
    print(f"manifest_json: {json_path.relative_to(root)}")
    print(f"move_results_csv: {results_csv_path.relative_to(root)}")


def move_one(root: Path, item: ArchiveItem) -> MoveResult:
    src = root / item.source
    dest = root / item.destination

    if not src.exists():
        return MoveResult(item.source, item.destination, "missing_source", "source file did not exist at move time")

    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Use extended-length paths on Windows to avoid WinError 3 from deep archive paths.
        shutil.move(to_windows_long_path(src), to_windows_long_path(dest))
        return MoveResult(item.source, item.destination, "moved", "")
    except FileNotFoundError as exc:
        # Keep going. This commonly happens if a previous partial run already moved the file,
        # or if Windows path handling failed for a deep path.
        return MoveResult(item.source, item.destination, "failed_file_not_found", repr(exc))
    except OSError as exc:
        return MoveResult(item.source, item.destination, "failed_os_error", repr(exc))


def apply_archive(root: Path, items: list[ArchiveItem]) -> list[MoveResult]:
    results: list[MoveResult] = []
    for item in items:
        result = move_one(root, item)
        results.append(result)
        if result.status != "moved":
            print(f"WARNING {result.status}: {result.source} -> {result.destination} :: {result.message}")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive generated backtest/report outputs into _archive/backtest_outputs/.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually move files. Without this flag, only prints the plan.",
    )
    parser.add_argument(
        "--label",
        default="generated_backtest_outputs",
        help="Archive run label. Used in destination folder name.",
    )
    parser.add_argument(
        "--include-parquet",
        action="store_true",
        help="Also archive .parquet/.pkl/.pickle files. Off by default because they may be reusable feature stores.",
    )
    parser.add_argument(
        "--scan-dir",
        action="append",
        default=None,
        help="Directory to scan, relative to repo root. Can be specified multiple times.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root_from_script()

    scan_dirs = args.scan_dir if args.scan_dir else DEFAULT_SCAN_DIRS
    extensions = set(DEFAULT_EXTENSIONS)
    if args.include_parquet:
        extensions |= OPTIONAL_EXTENSIONS

    safe_label = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in args.label).strip("_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Keep this path reasonably short. Windows users often run this repo under a very deep
    # MQL5\Files path, and a long archive prefix can push files over MAX_PATH.
    archive_root = root / "_archive" / "bt" / f"{timestamp}_{safe_label}"

    items = build_archive_plan(root, archive_root, scan_dirs, extensions)

    print("archive_generated_backtest_outputs")
    print(f"repo_root: {root}")
    print(f"mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"scan_dirs: {scan_dirs}")
    print(f"extensions: {sorted(extensions)}")
    print(f"archive_root: {archive_root.relative_to(root)}")
    print(f"files_to_archive: {len(items)}")

    total_size = sum(item.size_bytes for item in items)
    print(f"total_size_bytes: {total_size}")

    for item in items[:200]:
        print(f"MOVE {item.source} -> {item.destination}")
    if len(items) > 200:
        print(f"... omitted {len(items) - 200} additional files")

    if not args.apply:
        print("DRY-RUN only. Add --apply to move files.")
        return 0

    move_results = apply_archive(root, items)
    write_manifest(root, archive_root, items, move_results)

    moved = sum(1 for r in move_results if r.status == "moved")
    failed = sum(1 for r in move_results if r.status.startswith("failed"))
    missing = sum(1 for r in move_results if r.status == "missing_source")

    print(f"moved: {moved}")
    print(f"missing_source: {missing}")
    print(f"failed: {failed}")
    print("done")

    # Missing sources are not fatal because a previous partial run may already have moved them.
    # Real OS failures are reported but do not crash halfway through the archive operation.
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
