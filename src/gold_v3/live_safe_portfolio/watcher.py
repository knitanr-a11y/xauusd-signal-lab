from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from .engine import SafePortfolioEngine
from .io import read_candidates, read_resolutions
from .state import SQLiteStateStore


@dataclass(frozen=True)
class WatchResult:
    candidate_files: int
    resolution_files: int
    decisions: int


def _claim(path: Path) -> Path:
    claimed = path.with_suffix(path.suffix + ".processing")
    path.replace(claimed)
    return claimed


def _archive(claimed: Path, archive_dir: Path, outcome: str) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    original_name = claimed.name.removesuffix(".processing")
    target = archive_dir / f"{original_name}.{outcome}"
    counter = 1
    while target.exists():
        target = archive_dir / f"{original_name}.{outcome}.{counter}"
        counter += 1
    claimed.replace(target)


def process_inbox_once(engine: SafePortfolioEngine, store: SQLiteStateStore,
                       inbox: str | Path, archive: str | Path) -> WatchResult:
    inbox_dir = Path(inbox)
    archive_dir = Path(archive)
    candidate_dir = inbox_dir / "candidates"
    resolution_dir = inbox_dir / "resolutions"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    resolution_dir.mkdir(parents=True, exist_ok=True)
    resolution_files = candidate_files = decisions = 0

    for path in sorted(resolution_dir.glob("*.jsonl")):
        claimed = _claim(path)
        try:
            for resolution in read_resolutions(claimed):
                store.add_resolution(resolution)
            _archive(claimed, archive_dir / "resolutions", "ok")
            resolution_files += 1
        except Exception:
            _archive(claimed, archive_dir / "resolutions", "error")
            raise

    for path in sorted(candidate_dir.glob("*.jsonl")):
        claimed = _claim(path)
        try:
            decisions += len(engine.process_batch(read_candidates(claimed)))
            _archive(claimed, archive_dir / "candidates", "ok")
            candidate_files += 1
        except Exception:
            _archive(claimed, archive_dir / "candidates", "error")
            raise
    return WatchResult(candidate_files, resolution_files, decisions)


def watch_forever(engine: SafePortfolioEngine, store: SQLiteStateStore,
                  inbox: str | Path, archive: str | Path,
                  poll_seconds: float) -> None:
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be positive")
    while True:
        process_inbox_once(engine, store, inbox, archive)
        time.sleep(poll_seconds)
