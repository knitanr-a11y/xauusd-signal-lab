from __future__ import annotations

import bisect
import csv
import hashlib
import io
import json
import math
import os
import shutil
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

TIME_FORMAT = "%Y.%m.%d %H:%M:%S"
HEADER = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
FILE_MAP = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}
SOURCE_CAPS = {"M1": 150000, "M5": 90000, "M15": 30000, "H1": 20000, "H4": 10000, "D1": 5000}
APPEND_LOOKBACK_BARS = 20
OVERLAP_CHECK_ROWS = 4096
MIN_OVERLAP_ROWS = 20
ADAPTER_VERSION = "BOUNDED_CSV_SOURCE_ADAPTER_V1"
EXPECTED_STARTS = {
    "M9V": "2026.07.24 11:04:00",
    "M9Y": "2026.07.24 12:45:00",
    "M10B": "2026.07.24 20:54:00",
    "M10E": "2026.07.24 22:06:00",
    "M10P": "2026.07.24 23:56:00",
    "M10P2": "2026.07.27 01:39:00",
    "M10W19": "2026.07.28 02:31:00",
}
RUNTIME_SPECS = {
    "M9V": (Path("m9v_runtime") / "m9v_runtime_manifest.json", ("M1", "M5", "M15", "H1", "H4", "D1")),
    "M9Y": (Path("m9y_runtime") / "m9y_runtime_manifest.json", ("M1", "M5", "M15", "H1", "H4")),
    "M10B": (Path("m10b_runtime") / "m10b_runtime_manifest.json", ("M1", "M5", "M15", "H1", "H4", "D1")),
    "M10E": (Path("m10e_runtime") / "m10e_runtime_manifest.json", ("M1", "M5", "M15", "H1", "H4", "D1")),
    "M10P": (Path("m10p_runtime") / "m10p_runtime_manifest.json", ("M1", "M5", "M15", "H1", "H4", "D1")),
    "M10P2": (Path("m10p2_runtime") / "m10p2_runtime_manifest.json", ("M1", "M5", "M15", "H1", "H4", "D1")),
    "M10W19": (Path("m10w19_runtime") / "m10w19_runtime_manifest.json", ("M1", "M15", "H1", "H4", "D1")),
}

Row = tuple[str, ...]


class AdapterError(RuntimeError):
    pass


class AdapterTransientError(AdapterError):
    pass


class AdapterIntegrityError(AdapterError):
    pass


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterIntegrityError(f"cannot read JSON: {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AdapterIntegrityError(f"JSON object required: {path}")
    return payload


def adapter_root(local_root: Path) -> Path:
    return local_root / "bounded_csv_source_adapter"


def journal_root(local_root: Path) -> Path:
    return adapter_root(local_root) / "journal"


def manifest_path(local_root: Path) -> Path:
    return adapter_root(local_root) / "adapter_manifest.json"


def receipt_path(local_root: Path) -> Path:
    return adapter_root(local_root) / "migration_receipt.json"


def status_path(local_root: Path) -> Path:
    return adapter_root(local_root) / "latest_update_status.json"


def source_environment(local_root: Path) -> tuple[Path, float]:
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    if not metadata_path.is_file():
        raise AdapterIntegrityError(f"M8B symbol metadata missing: {metadata_path}")
    metadata = load_json(metadata_path)
    source_root = Path(str(metadata.get("mt5_files_root", "")))
    point = float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))
    if not source_root.is_dir() or not math.isfinite(point) or point <= 0:
        raise AdapterIntegrityError(f"MT5 source root or XAUUSD point unavailable: {source_root} point={point}")
    return source_root, point


def _is_retryable_os_error(exc: BaseException) -> bool:
    if isinstance(exc, (PermissionError, FileNotFoundError)):
        return True
    if isinstance(exc, OSError):
        return getattr(exc, "winerror", None) in {2, 3, 5, 32, 33}
    return False


def _parse_csv_bytes(data: bytes, path: Path) -> tuple[list[Row], list[datetime]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AdapterIntegrityError(f"CSV is not UTF-8: {path}") from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise AdapterIntegrityError(f"empty CSV: {path}") from exc
    header = [value.strip() for value in header]
    if header != HEADER:
        raise AdapterIntegrityError(f"unexpected header in {path.name}: {header}")
    rows: list[Row] = []
    times: list[datetime] = []
    previous: datetime | None = None
    for line_number, raw in enumerate(reader, start=2):
        if not raw or all(not value.strip() for value in raw):
            continue
        if len(raw) != len(HEADER):
            raise AdapterIntegrityError(f"unexpected column count in {path.name} line {line_number}: {len(raw)}")
        row = tuple(value.strip() for value in raw)
        try:
            current = parse_time(row[0])
        except ValueError as exc:
            raise AdapterIntegrityError(f"invalid MT5 timestamp in {path.name} line {line_number}: {row[0]}") from exc
        if previous is not None and current <= previous:
            relation = "duplicate" if current == previous else "non-ascending"
            raise AdapterIntegrityError(f"{relation} timestamp in {path.name}: {row[0]}")
        previous = current
        rows.append(row)
        times.append(current)
    if not rows:
        raise AdapterIntegrityError(f"CSV has no data rows: {path}")
    return rows, times


def _read_stable_source(path: Path, deadline: float) -> tuple[bytes, list[Row], list[datetime], dict[str, Any]]:
    last_detail = "unread"
    while True:
        try:
            first = path.read_bytes()
            first_stat = path.stat()
            time.sleep(0.15)
            second = path.read_bytes()
            second_stat = path.stat()
            stable = (
                first == second
                and first_stat.st_size == second_stat.st_size
                and first_stat.st_mtime_ns == second_stat.st_mtime_ns
            )
            if stable:
                rows, times = _parse_csv_bytes(second, path)
                signature = {
                    "size_bytes": second_stat.st_size,
                    "mtime_ns": second_stat.st_mtime_ns,
                    "sha256": hashlib.sha256(second).hexdigest(),
                    "row_count": len(rows),
                    "first_server_open": rows[0][0],
                    "last_server_open": rows[-1][0],
                }
                return second, rows, times, signature
            last_detail = "source changed during double read"
        except Exception as exc:
            if not _is_retryable_os_error(exc):
                if isinstance(exc, AdapterError):
                    raise
                raise AdapterIntegrityError(f"source read failed: {path}: {type(exc).__name__}: {exc}") from exc
            last_detail = f"{type(exc).__name__}: {exc}"
        if time.monotonic() >= deadline:
            raise AdapterTransientError(f"stable source read unavailable for {path.name}: {last_detail}")
        time.sleep(1.0)


def _write_journal_atomic(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _read_journal(path: Path) -> tuple[list[Row], list[datetime]]:
    if not path.is_file():
        raise AdapterIntegrityError(f"journal missing: {path}")
    return _parse_csv_bytes(path.read_bytes(), path)


def _journal_info(path: Path, rows: list[Row]) -> dict[str, Any]:
    return {
        "path": str(path),
        "row_count": len(rows),
        "first_server_open": rows[0][0],
        "last_server_open": rows[-1][0],
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


@contextmanager
def update_lock(local_root: Path, timeout_seconds: float = 90.0) -> Iterator[None]:
    path = adapter_root(local_root) / "adapter_update.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    deadline = time.monotonic() + timeout_seconds
    locked = False
    while not locked:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except (OSError, BlockingIOError):
            if time.monotonic() >= deadline:
                handle.close()
                raise AdapterTransientError("bounded CSV adapter update lock remained busy for 90 seconds")
            time.sleep(0.25)
    try:
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _runtime_inventory(local_root: Path, source_root: Path, point: float) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory: dict[str, Any] = {}
    coverage: dict[str, Any] = {}
    for loop, (relative, used_timeframes) in RUNTIME_SPECS.items():
        path = local_root / relative
        if not path.is_file():
            raise AdapterIntegrityError(f"{loop} runtime manifest missing: {path}")
        runtime = load_json(path)
        start = str(runtime.get("prospective_start_server_time", ""))
        if start != EXPECTED_STARTS[loop]:
            raise AdapterIntegrityError(f"{loop} prospective start changed: expected {EXPECTED_STARTS[loop]} got {start}")
        frozen = runtime.get("frozen_row_prefixes")
        if not isinstance(frozen, dict):
            raise AdapterIntegrityError(f"{loop} frozen_row_prefixes missing")
        runtime_data_root = runtime.get("data_root")
        if runtime_data_root and str(Path(str(runtime_data_root))) != str(source_root):
            raise AdapterIntegrityError(f"{loop} source data_root changed: {runtime_data_root} != {source_root}")
        if "point" in runtime:
            frozen_point = float(runtime.get("point", "nan"))
            if not math.isfinite(frozen_point) or abs(frozen_point - point) > 1e-12:
                raise AdapterIntegrityError(f"{loop} XAUUSD point changed: frozen={frozen_point} current={point}")
        anchors: dict[str, str] = {}
        for tf in used_timeframes:
            item = frozen.get(tf)
            if not isinstance(item, dict):
                raise AdapterIntegrityError(f"{loop} frozen prefix missing: {tf}")
            anchor = str(item.get("last_server_open", ""))
            if not anchor:
                raise AdapterIntegrityError(f"{loop} frozen last_server_open missing: {tf}")
            anchors[tf] = anchor
        inventory[loop] = {
            "runtime_path": str(path),
            "runtime_sha256": sha256_file(path),
            "stage": runtime.get("stage"),
            "runtime_contract_version": runtime.get("runtime_contract_version"),
            "prospective_start_server_time": start,
            "reset_allowed": runtime.get("reset_allowed"),
            "historical_backfill_allowed": runtime.get("historical_backfill_allowed"),
            "used_timeframes": list(used_timeframes),
        }
        if runtime.get("reset_allowed") is not False or runtime.get("historical_backfill_allowed") is not False:
            raise AdapterIntegrityError(f"unsafe runtime flags for {loop}")
        coverage[loop] = {"start": start, "anchors": anchors}
    return inventory, coverage


def migrate(local_root: Path, source_root: Path, point: float, retry_window_seconds: float = 90.0) -> dict[str, Any]:
    final_root = adapter_root(local_root)
    if final_root.exists():
        raise AdapterIntegrityError(f"adapter already exists; migration is one-time and must not be rerun: {final_root}")
    inventory, coverage = _runtime_inventory(local_root, source_root, point)
    deadline = time.monotonic() + retry_window_seconds
    source_rows: dict[str, list[Row]] = {}
    source_times: dict[str, list[datetime]] = {}
    source_signatures: dict[str, Any] = {}
    for tf, filename in FILE_MAP.items():
        _, rows, times, signature = _read_stable_source(source_root / filename, deadline)
        source_rows[tf] = rows
        source_times[tf] = times
        source_signatures[tf] = signature

    m1_times = source_times["M1"]
    for loop, item in coverage.items():
        start_dt = parse_time(str(item["start"]))
        start_index = bisect.bisect_left(m1_times, start_dt)
        if start_index >= len(m1_times) or m1_times[start_index] != start_dt:
            raise AdapterIntegrityError(f"{loop} exact prospective start is absent from current M1 source: {item['start']}")
        if start_index < 10:
            raise AdapterIntegrityError(f"{loop} has fewer than 10 pre-start M1 context rows")
        item["m1_exact_start_index"] = start_index
        item["m1_pre_start_context_rows"] = start_index
        for tf, anchor_text in item["anchors"].items():
            anchor = parse_time(anchor_text)
            index = bisect.bisect_left(source_times[tf], anchor)
            if index >= len(source_times[tf]) or source_times[tf][index] != anchor:
                raise AdapterIntegrityError(f"{loop} frozen anchor absent after bounded rebuild: {tf} {anchor_text}")
            item.setdefault("anchor_indices", {})[tf] = index

    temp_root = local_root / f"bounded_csv_source_adapter.migrating.{utc_stamp()}"
    if temp_root.exists():
        raise AdapterIntegrityError(f"unexpected migration temp path already exists: {temp_root}")
    temp_journal = temp_root / "journal"
    temp_journal.mkdir(parents=True, exist_ok=False)
    journal_info: dict[str, Any] = {}
    try:
        for tf, filename in FILE_MAP.items():
            path = temp_journal / filename
            _write_journal_atomic(path, source_rows[tf])
            info = _journal_info(path, source_rows[tf])
            info["path"] = str(final_root / "journal" / filename)
            journal_info[tf] = info
        created = utc_text()
        manifest = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "adapter_version": ADAPTER_VERSION,
            "status": "PASS_MIGRATED_PRESERVED_START_AUDIT_ONLY",
            "created_at_utc": created,
            "updated_at_utc": created,
            "source_model": "BOUNDED_REWRITE_WITH_20_BAR_REFRESH_OVERLAP",
            "source_root": str(source_root),
            "xauusd_point": point,
            "file_map": FILE_MAP,
            "source_caps": SOURCE_CAPS,
            "append_lookback_bars": APPEND_LOOKBACK_BARS,
            "canonical_header": HEADER,
            "journal_root": str(final_root / "journal"),
            "runtime_inventory": inventory,
            "loop_coverage": coverage,
            "last_source_signatures": source_signatures,
            "journals": journal_info,
            "historical_backfill_before_starts": False,
            "pre_start_rows_context_only": True,
            "nearest_m1_fallback": False,
            "runtime_manifests_modified": False,
            "prospective_starts_modified": False,
        }
        receipt = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "FRESH_LOOP_BOUNDED_CSV_PRESERVED_START_MIGRATION_AUDIT_ONLY",
            "status": "PASS_MIGRATION_READY_FOR_REVIEW",
            "created_at_utc": created,
            "adapter_version": ADAPTER_VERSION,
            "source_root": str(source_root),
            "xauusd_point": point,
            "runtime_manifest_sha256s": {loop: item["runtime_sha256"] for loop, item in inventory.items()},
            "immutable_starts": EXPECTED_STARTS,
            "loop_coverage": coverage,
            "journal_fingerprints": journal_info,
            "runtime_manifests_modified": False,
            "prospective_starts_modified": False,
            "historical_backfill_before_starts": False,
            "candidate_eligibility_before_start": False,
            "discord_send": False,
            "mt5_order": False,
        }
        atomic_json(temp_root / "adapter_manifest.json", manifest)
        atomic_json(temp_root / "migration_receipt.json", receipt)
        os.replace(temp_root, final_root)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    return load_json(final_root / "migration_receipt.json")


def _validate_manifest_identity(manifest: dict[str, Any], source_root: Path, point: float) -> None:
    if manifest.get("adapter_version") != ADAPTER_VERSION or manifest.get("status") != "PASS_MIGRATED_PRESERVED_START_AUDIT_ONLY":
        raise AdapterIntegrityError("bounded CSV adapter manifest is not a migrated PASS manifest")
    if str(Path(str(manifest.get("source_root", "")))) != str(source_root):
        raise AdapterIntegrityError(f"bounded CSV source root changed: {manifest.get('source_root')} != {source_root}")
    frozen_point = float(manifest.get("xauusd_point", "nan"))
    if not math.isfinite(frozen_point) or abs(frozen_point - point) > 1e-12:
        raise AdapterIntegrityError(f"bounded CSV adapter XAUUSD point changed: {frozen_point} != {point}")
    if manifest.get("file_map") != FILE_MAP or manifest.get("canonical_header") != HEADER:
        raise AdapterIntegrityError("bounded CSV adapter file-map/header contract changed")


def validate_loop(local_root: Path, loop: str, source_root: Path, point: float) -> dict[str, Any]:
    if loop not in RUNTIME_SPECS:
        raise AdapterIntegrityError(f"unsupported adapter loop: {loop}")
    manifest = load_json(manifest_path(local_root))
    receipt = load_json(receipt_path(local_root))
    _validate_manifest_identity(manifest, source_root, point)
    if receipt.get("status") != "PASS_MIGRATION_READY_FOR_REVIEW" or receipt.get("adapter_version") != ADAPTER_VERSION:
        raise AdapterIntegrityError("bounded CSV migration receipt is not PASS")
    relative, _ = RUNTIME_SPECS[loop]
    runtime_path = local_root / relative
    runtime = load_json(runtime_path)
    current_hash = sha256_file(runtime_path)
    frozen_hash = str(manifest.get("runtime_inventory", {}).get(loop, {}).get("runtime_sha256", ""))
    if current_hash != frozen_hash:
        raise AdapterIntegrityError(f"{loop} runtime manifest changed after adapter migration")
    start = str(runtime.get("prospective_start_server_time", ""))
    if start != EXPECTED_STARTS[loop]:
        raise AdapterIntegrityError(f"{loop} prospective start changed after adapter migration")
    if str(manifest.get("loop_coverage", {}).get(loop, {}).get("start", "")) != start:
        raise AdapterIntegrityError(f"{loop} migration coverage/start mismatch")
    root = journal_root(local_root)
    for tf, filename in FILE_MAP.items():
        if not (root / filename).is_file():
            raise AdapterIntegrityError(f"adapter journal missing: {tf} {root / filename}")
    return runtime


def _source_stat_signatures(source_root: Path) -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for tf, filename in FILE_MAP.items():
        path = source_root / filename
        try:
            stat = path.stat()
        except Exception as exc:
            if _is_retryable_os_error(exc):
                raise AdapterTransientError(f"source temporarily unavailable: {path}: {type(exc).__name__}: {exc}") from exc
            raise AdapterIntegrityError(f"cannot stat source: {path}: {type(exc).__name__}: {exc}") from exc
        signatures[tf] = {"size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
    return signatures


def _update_one_journal(path: Path, source_rows: list[Row], source_times: list[datetime]) -> tuple[dict[str, Any], int]:
    journal_rows, journal_times = _read_journal(path)
    journal_last = journal_times[-1]
    source_last = source_times[-1]
    if source_last < journal_last:
        raise AdapterTransientError(
            f"source rebuild has not caught up to journal tail for {path.name}: source={source_rows[-1][0]} journal={journal_rows[-1][0]}"
        )
    source_last_index = bisect.bisect_left(source_times, journal_last)
    if source_last_index >= len(source_times) or source_times[source_last_index] != journal_last:
        raise AdapterIntegrityError(f"journal tail overlap missing from bounded source: {path.name} {journal_rows[-1][0]}")
    source_first = source_times[0]
    journal_overlap_start = max(0, len(journal_rows) - OVERLAP_CHECK_ROWS)
    journal_overlap_start = max(journal_overlap_start, bisect.bisect_left(journal_times, source_first))
    overlap_count = len(journal_rows) - journal_overlap_start
    if overlap_count < MIN_OVERLAP_ROWS:
        raise AdapterIntegrityError(f"insufficient bounded-source overlap for {path.name}: {overlap_count}")
    source_by_time = {value: index for index, value in enumerate(source_times)}
    for row, value in zip(journal_rows[journal_overlap_start:], journal_times[journal_overlap_start:]):
        source_index = source_by_time.get(value)
        if source_index is None:
            raise AdapterIntegrityError(f"overlap timestamp missing from bounded source: {path.name} {row[0]}")
        if source_rows[source_index] != row:
            raise AdapterIntegrityError(f"overlap canonical row changed: {path.name} {row[0]}")
    new_rows = source_rows[source_last_index + 1 :]
    if new_rows:
        combined = journal_rows + new_rows
        _write_journal_atomic(path, combined)
        return _journal_info(path, combined), len(new_rows)
    return _journal_info(path, journal_rows), 0


def ensure_updated(local_root: Path, source_root: Path, point: float, retry_window_seconds: float = 90.0) -> Path:
    if not manifest_path(local_root).is_file() or not receipt_path(local_root).is_file():
        raise AdapterIntegrityError("bounded CSV adapter migration has not been completed and reviewed")
    deadline = time.monotonic() + retry_window_seconds
    with update_lock(local_root, timeout_seconds=retry_window_seconds):
        manifest = load_json(manifest_path(local_root))
        _validate_manifest_identity(manifest, source_root, point)
        try:
            quick = _source_stat_signatures(source_root)
        except AdapterTransientError:
            quick = {}
        previous = manifest.get("last_source_signatures", {})
        unchanged = bool(quick) and all(
            tf in previous
            and int(previous[tf].get("size_bytes", -1)) == int(quick[tf]["size_bytes"])
            and int(previous[tf].get("mtime_ns", -1)) == int(quick[tf]["mtime_ns"])
            for tf in FILE_MAP
        )
        if unchanged:
            return journal_root(local_root)

        source_rows: dict[str, list[Row]] = {}
        source_times: dict[str, list[datetime]] = {}
        stable_signatures: dict[str, Any] = {}
        for tf, filename in FILE_MAP.items():
            _, rows, times, signature = _read_stable_source(source_root / filename, deadline)
            source_rows[tf] = rows
            source_times[tf] = times
            stable_signatures[tf] = signature

        appended: dict[str, int] = {}
        journals: dict[str, Any] = {}
        root = journal_root(local_root)
        for tf, filename in FILE_MAP.items():
            info, count = _update_one_journal(root / filename, source_rows[tf], source_times[tf])
            journals[tf] = info
            appended[tf] = count

        updated = utc_text()
        manifest["updated_at_utc"] = updated
        manifest["last_source_signatures"] = stable_signatures
        manifest["journals"] = journals
        manifest["last_append_counts"] = appended
        atomic_json(manifest_path(local_root), manifest)
        atomic_json(status_path(local_root), {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "BOUNDED_CSV_SOURCE_ADAPTER_UPDATE_AUDIT_ONLY",
            "status": "PASS",
            "updated_at_utc": updated,
            "appended_rows": appended,
            "source_latest": {tf: item["last_server_open"] for tf, item in stable_signatures.items()},
            "journal_latest": {tf: item["last_server_open"] for tf, item in journals.items()},
            "runtime_or_start_modified": False,
            "historical_backfill_before_starts": False,
        })
        return root


def frozen_prefix_compatibility(runtime: dict[str, Any], file_map: dict[str, str]):
    frozen = runtime.get("frozen_row_prefixes")
    if not isinstance(frozen, dict):
        raise AdapterIntegrityError("runtime frozen_row_prefixes missing")
    by_filename: dict[str, dict[str, Any]] = {}
    for tf, filename in file_map.items():
        item = frozen.get(tf)
        if not isinstance(item, dict):
            raise AdapterIntegrityError(f"runtime frozen prefix missing: {tf}")
        by_filename[str(filename)] = item

    def compatibility(path: Path, row_count: int) -> dict[str, Any]:
        item = by_filename.get(path.name)
        if item is None:
            raise AdapterIntegrityError(f"unexpected CSV in frozen-prefix compatibility check: {path.name}")
        expected = int(item.get("row_count", 0))
        if int(row_count) != expected:
            raise AdapterIntegrityError(f"unexpected frozen row-count request for {path.name}: {row_count} != {expected}")
        return dict(item)

    return compatibility
