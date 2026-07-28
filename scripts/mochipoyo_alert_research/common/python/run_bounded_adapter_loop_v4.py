from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bounded_csv_journal_integrity as journal_integrity

journal_integrity.install_verified_adapter_hooks()

import bounded_csv_source_adapter as adapter
import m9v_bounded_start_bootstrap
import run_bounded_adapter_loop as runner


SNAPSHOT_VERSION = "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1"


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def selected_loop() -> str:
    try:
        index = sys.argv.index("--loop")
        loop = sys.argv[index + 1]
    except (ValueError, IndexError) as exc:
        raise RuntimeError("--loop is required before V4 snapshot bootstrap") from exc
    if loop not in runner.LOOPS:
        raise RuntimeError(f"unsupported V4 loop: {loop}")
    return loop


def transient_io(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        return getattr(exc, "winerror", None) in {5, 32, 33}
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(token in text for token in (
        "permission denied",
        "permissionerror",
        "access is denied",
        "アクセスが拒否",
        "sharing violation",
        "winerror 5",
        "winerror 32",
        "winerror 33",
    ))


def snapshot_base(local_root: Path) -> Path:
    return adapter.adapter_root(local_root) / "loop_snapshots"


def snapshot_path(local_root: Path, loop: str) -> Path:
    return snapshot_base(local_root) / loop


def materialize_snapshot(local_root: Path, loop: str, timeout_seconds: float) -> Path:
    """Copy verified shared journals to a private per-loop read snapshot.

    Shared journals are write targets for the bounded-source adapter. On Windows,
    replacing a shared journal can fail while another Python process has that same
    path open for strategy reads. Every loop therefore reads only its own private
    snapshot. Snapshot creation is serialized with journal updates by the existing
    adapter lock and every copied file is checked against the adapter manifest.
    """
    base = snapshot_base(local_root)
    base.mkdir(parents=True, exist_ok=True)
    target = snapshot_path(local_root, loop)
    temporary = base / f".{loop}.tmp_{os.getpid()}_{time.time_ns()}"
    temporary.mkdir(parents=True, exist_ok=False)

    try:
        with adapter.update_lock(local_root, timeout_seconds=timeout_seconds):
            verified = journal_integrity.verify_journals(local_root)
            shared = adapter.journal_root(local_root)
            for timeframe, filename in adapter.FILE_MAP.items():
                source = shared / filename
                destination = temporary / filename
                shutil.copy2(source, destination)
                expected = verified[timeframe]
                if destination.stat().st_size != int(expected["size_bytes"]):
                    raise adapter.AdapterIntegrityError(
                        f"private snapshot size mismatch: {loop} {timeframe}"
                    )
                if adapter.sha256_file(destination) != str(expected["sha256"]):
                    raise adapter.AdapterIntegrityError(
                        f"private snapshot SHA256 mismatch: {loop} {timeframe}"
                    )

            receipt: dict[str, Any] = {
                "project": "MOCHIPOYO_ALERT_RESEARCH",
                "status": "PASS_PRIVATE_LOOP_SNAPSHOT",
                "snapshot_version": SNAPSHOT_VERSION,
                "loop": loop,
                "created_at_utc": utc_text(),
                "source_manifest_sha256": adapter.sha256_file(adapter.manifest_path(local_root)),
                "journal_fingerprints": {
                    timeframe: {
                        "row_count": details.get("row_count"),
                        "first_server_open": details.get("first_server_open"),
                        "last_server_open": details.get("last_server_open"),
                        "size_bytes": details.get("size_bytes"),
                        "sha256": details.get("sha256"),
                    }
                    for timeframe, details in verified.items()
                },
                "runtime_or_start_modified": False,
                "historical_backfill_before_start": False,
            }
            (temporary / "00_snapshot_receipt.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            if target.exists():
                shutil.rmtree(target)
            os.replace(temporary, target)
        return target
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


LOOP = selected_loop()
_original_ensure_updated = adapter.ensure_updated


def ensure_updated_with_private_snapshot(
    local_root: Path,
    source_root: Path,
    point: float,
    retry_window_seconds: float = 90.0,
) -> Path:
    try:
        _original_ensure_updated(local_root, source_root, point, retry_window_seconds)
        return materialize_snapshot(local_root, LOOP, retry_window_seconds)
    except (adapter.AdapterIntegrityError, adapter.AdapterTransientError):
        raise
    except Exception as exc:
        if transient_io(exc):
            raise adapter.AdapterTransientError(
                f"private/shared journal Windows file contention: {type(exc).__name__}: {exc}"
            ) from exc
        raise


adapter.ensure_updated = ensure_updated_with_private_snapshot
runner.BUILDERS["M9V"] = m9v_bounded_start_bootstrap.build_m9v_runner


if __name__ == "__main__":
    raise SystemExit(runner.main())
