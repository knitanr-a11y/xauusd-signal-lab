from __future__ import annotations

from pathlib import Path
from typing import Any

import bounded_csv_source_adapter as adapter


def verify_journals(local_root: Path) -> dict[str, Any]:
    manifest = adapter.load_json(adapter.manifest_path(local_root))
    expected_all = manifest.get("journals")
    if not isinstance(expected_all, dict):
        raise adapter.AdapterIntegrityError("bounded CSV adapter journal fingerprints are missing")
    root = adapter.journal_root(local_root)
    verified: dict[str, Any] = {}
    for timeframe, filename in adapter.FILE_MAP.items():
        path = root / filename
        expected = expected_all.get(timeframe)
        if not isinstance(expected, dict):
            raise adapter.AdapterIntegrityError(f"bounded CSV adapter journal fingerprint missing: {timeframe}")
        if not path.is_file():
            raise adapter.AdapterIntegrityError(f"bounded CSV adapter journal missing: {timeframe} {path}")
        stat = path.stat()
        expected_size = int(expected.get("size_bytes", -1))
        if stat.st_size != expected_size:
            raise adapter.AdapterIntegrityError(
                f"bounded CSV adapter journal size changed outside verified update: "
                f"{timeframe} current={stat.st_size} expected={expected_size}"
            )
        current_sha = adapter.sha256_file(path)
        expected_sha = str(expected.get("sha256", ""))
        if current_sha != expected_sha:
            raise adapter.AdapterIntegrityError(
                f"bounded CSV adapter journal SHA256 changed outside verified update: {timeframe}"
            )
        verified[timeframe] = {
            "path": str(path),
            "size_bytes": stat.st_size,
            "sha256": current_sha,
            "row_count": expected.get("row_count"),
            "first_server_open": expected.get("first_server_open"),
            "last_server_open": expected.get("last_server_open"),
        }
    return verified


def install_verified_adapter_hooks() -> None:
    if getattr(adapter, "_journal_integrity_v2_installed", False):
        return
    original_migrate = adapter.migrate
    original_ensure_updated = adapter.ensure_updated
    original_validate_loop = adapter.validate_loop

    def verified_migrate(local_root: Path, source_root: Path, point: float, retry_window_seconds: float = 90.0):
        receipt = original_migrate(local_root, source_root, point, retry_window_seconds)
        verify_journals(local_root)
        return receipt

    def verified_ensure_updated(local_root: Path, source_root: Path, point: float, retry_window_seconds: float = 90.0):
        verify_journals(local_root)
        result = original_ensure_updated(local_root, source_root, point, retry_window_seconds)
        verify_journals(local_root)
        return result

    def verified_validate_loop(local_root: Path, loop: str, source_root: Path, point: float):
        runtime = original_validate_loop(local_root, loop, source_root, point)
        verify_journals(local_root)
        return runtime

    adapter.migrate = verified_migrate
    adapter.ensure_updated = verified_ensure_updated
    adapter.validate_loop = verified_validate_loop
    adapter._journal_integrity_v2_installed = True
