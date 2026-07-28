from __future__ import annotations

import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import bounded_csv_source_adapter as adapter

_CACHE: dict[str, dict[str, Any]] = {}


def _cache_key(local_root: Path) -> str:
    return str(local_root.resolve())


def _journal_stats(local_root: Path) -> dict[str, tuple[int, int]]:
    root = adapter.journal_root(local_root)
    output: dict[str, tuple[int, int]] = {}
    for timeframe, filename in adapter.FILE_MAP.items():
        path = root / filename
        if not path.is_file():
            raise adapter.AdapterIntegrityError(f"bounded CSV adapter journal missing: {timeframe} {path}")
        stat = path.stat()
        output[timeframe] = (stat.st_size, stat.st_mtime_ns)
    return output


def verify_journals(local_root: Path) -> dict[str, Any]:
    manifest_file = adapter.manifest_path(local_root)
    manifest = adapter.load_json(manifest_file)
    expected_all = manifest.get("journals")
    if not isinstance(expected_all, dict):
        raise adapter.AdapterIntegrityError("bounded CSV adapter journal fingerprints are missing")

    cache_key = _cache_key(local_root)
    manifest_sha = adapter.sha256_file(manifest_file)
    stats = _journal_stats(local_root)
    cached = _CACHE.get(cache_key)
    if (
        cached is not None
        and cached.get("manifest_sha256") == manifest_sha
        and cached.get("journal_stats") == stats
    ):
        return dict(cached["verified"])

    root = adapter.journal_root(local_root)
    verified: dict[str, Any] = {}
    for timeframe, filename in adapter.FILE_MAP.items():
        path = root / filename
        expected = expected_all.get(timeframe)
        if not isinstance(expected, dict):
            raise adapter.AdapterIntegrityError(f"bounded CSV adapter journal fingerprint missing: {timeframe}")
        stat_size, stat_mtime_ns = stats[timeframe]
        expected_size = int(expected.get("size_bytes", -1))
        if stat_size != expected_size:
            raise adapter.AdapterIntegrityError(
                f"bounded CSV adapter journal size changed outside verified update: "
                f"{timeframe} current={stat_size} expected={expected_size}"
            )
        current_sha = adapter.sha256_file(path)
        expected_sha = str(expected.get("sha256", ""))
        if current_sha != expected_sha:
            raise adapter.AdapterIntegrityError(
                f"bounded CSV adapter journal SHA256 changed outside verified update: {timeframe}"
            )
        verified[timeframe] = {
            "path": str(path),
            "size_bytes": stat_size,
            "mtime_ns": stat_mtime_ns,
            "sha256": current_sha,
            "row_count": expected.get("row_count"),
            "first_server_open": expected.get("first_server_open"),
            "last_server_open": expected.get("last_server_open"),
        }
    _CACHE[cache_key] = {
        "manifest_sha256": manifest_sha,
        "journal_stats": stats,
        "verified": dict(verified),
    }
    return verified


def _source_unchanged(local_root: Path, source_root: Path) -> bool:
    manifest = adapter.load_json(adapter.manifest_path(local_root))
    previous = manifest.get("last_source_signatures", {})
    try:
        current = adapter._source_stat_signatures(source_root)
    except adapter.AdapterTransientError:
        return False
    return all(
        timeframe in previous
        and int(previous[timeframe].get("size_bytes", -1)) == int(current[timeframe]["size_bytes"])
        and int(previous[timeframe].get("mtime_ns", -1)) == int(current[timeframe]["mtime_ns"])
        for timeframe in adapter.FILE_MAP
    )


def _transaction_targets(local_root: Path) -> list[Path]:
    targets = [adapter.manifest_path(local_root), adapter.status_path(local_root)]
    root = adapter.journal_root(local_root)
    targets.extend(root / filename for filename in adapter.FILE_MAP.values())
    return targets


def _backup_transaction(local_root: Path) -> tuple[Path, dict[str, bool]]:
    transaction = adapter.adapter_root(local_root) / f".journal_transaction_{os.getpid()}_{time.time_ns()}"
    transaction.mkdir(parents=True, exist_ok=False)
    existed: dict[str, bool] = {}
    for index, target in enumerate(_transaction_targets(local_root)):
        key = str(target)
        existed[key] = target.is_file()
        if target.is_file():
            shutil.copy2(target, transaction / f"{index:02d}.backup")
    return transaction, existed


def _restore_transaction(local_root: Path, transaction: Path, existed: dict[str, bool]) -> None:
    for index, target in enumerate(_transaction_targets(local_root)):
        backup = transaction / f"{index:02d}.backup"
        if existed.get(str(target), False):
            if not backup.is_file():
                raise adapter.AdapterIntegrityError(f"bounded CSV rollback backup missing: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".rollback")
            shutil.copy2(backup, temporary)
            os.replace(temporary, target)
        else:
            target.unlink(missing_ok=True)
    _CACHE.pop(_cache_key(local_root), None)


@contextmanager
def _no_inner_lock(*args: Any, **kwargs: Any) -> Iterator[None]:
    yield


def install_verified_adapter_hooks() -> None:
    if getattr(adapter, "_journal_integrity_v2_installed", False):
        return
    original_migrate = adapter.migrate
    original_ensure_updated = adapter.ensure_updated
    original_validate_loop = adapter.validate_loop
    original_update_lock = adapter.update_lock

    def verified_migrate(local_root: Path, source_root: Path, point: float, retry_window_seconds: float = 90.0):
        receipt = original_migrate(local_root, source_root, point, retry_window_seconds)
        verify_journals(local_root)
        return receipt

    def verified_ensure_updated(local_root: Path, source_root: Path, point: float, retry_window_seconds: float = 90.0):
        with original_update_lock(local_root, timeout_seconds=retry_window_seconds):
            verify_journals(local_root)
            if _source_unchanged(local_root, source_root):
                return adapter.journal_root(local_root)
            transaction, existed = _backup_transaction(local_root)
            saved_lock = adapter.update_lock
            adapter.update_lock = _no_inner_lock
            try:
                result = original_ensure_updated(local_root, source_root, point, retry_window_seconds)
                _CACHE.pop(_cache_key(local_root), None)
                verify_journals(local_root)
                return result
            except Exception:
                _restore_transaction(local_root, transaction, existed)
                verify_journals(local_root)
                raise
            finally:
                adapter.update_lock = saved_lock
                shutil.rmtree(transaction, ignore_errors=True)

    def verified_validate_loop(local_root: Path, loop: str, source_root: Path, point: float):
        runtime = original_validate_loop(local_root, loop, source_root, point)
        verify_journals(local_root)
        return runtime

    adapter.migrate = verified_migrate
    adapter.ensure_updated = verified_ensure_updated
    adapter.validate_loop = verified_validate_loop
    adapter._journal_integrity_v2_installed = True
