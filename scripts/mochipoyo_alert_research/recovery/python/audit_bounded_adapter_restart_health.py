from __future__ import annotations

import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
COMMON = THIS.parents[2] / "common" / "python"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import bounded_csv_journal_integrity as journal_integrity
journal_integrity.install_verified_adapter_hooks()
import bounded_csv_source_adapter as adapter
import run_bounded_adapter_loop as runner
import migrate_bounded_csv_source_adapter as migration

OUTPUT_NAMES = {loop: loop for loop in runner.LOOPS}
V4_PROCESS_TOKEN = "run_bounded_adapter_loop_v4.py"
V4_SNAPSHOT_VERSION = "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1"
MAX_SNAPSHOT_AGE_SECONDS = 300.0


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def parse_utc(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except Exception:
        return None


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"_error": "JSON_NOT_OBJECT"}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def file_info(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        stat = path.stat()
        row.update({
            "size_bytes": stat.st_size,
            "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return row


def tail(path: Path, lines: int = 120) -> str:
    if not path.is_file():
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return "".join(handle.readlines()[-lines:])
    except Exception as exc:
        return f"[TAIL ERROR] {type(exc).__name__}: {exc}\n"


def process_uses_v4(processes: list[dict[str, Any]]) -> bool:
    return bool(processes) and all(
        V4_PROCESS_TOKEN.lower() in str(row.get("CommandLine", "")).lower()
        for row in processes
    )


def snapshot_health(local_root: Path, loop: str, journals: dict[str, Any]) -> dict[str, Any]:
    directory = adapter.adapter_root(local_root) / "loop_snapshots" / loop
    receipt_path = directory / "00_snapshot_receipt.json"
    receipt = read_json(receipt_path) or {}
    fingerprints = receipt.get("journal_fingerprints", {})
    created = parse_utc(receipt.get("created_at_utc"))
    age_seconds = None if created is None else (datetime.now(UTC) - created).total_seconds()
    fresh = age_seconds is not None and -5.0 <= age_seconds <= MAX_SNAPSHOT_AGE_SECONDS

    files: dict[str, Any] = {}
    all_files_match_receipt = True
    all_snapshots_not_ahead = True
    for timeframe, filename in adapter.FILE_MAP.items():
        path = directory / filename
        current_shared = journals.get(timeframe, {})
        receipt_tf = fingerprints.get(timeframe, {}) if isinstance(fingerprints, dict) else {}
        snapshot_sha = adapter.sha256_file(path) if path.is_file() else None
        snapshot_size = path.stat().st_size if path.is_file() else None
        matches_receipt = (
            path.is_file()
            and snapshot_sha == receipt_tf.get("sha256")
            and snapshot_size == receipt_tf.get("size_bytes")
        )
        snapshot_rows = int(receipt_tf.get("row_count", -1) or -1)
        shared_rows = int(current_shared.get("row_count", -1) or -1)
        snapshot_first = receipt_tf.get("first_server_open")
        shared_first = current_shared.get("first_server_open")
        snapshot_last = receipt_tf.get("last_server_open")
        shared_last = current_shared.get("last_server_open")
        not_ahead = (
            snapshot_rows >= 0
            and shared_rows >= snapshot_rows
            and snapshot_first == shared_first
            and isinstance(snapshot_last, str)
            and isinstance(shared_last, str)
            and snapshot_last <= shared_last
        )
        all_files_match_receipt = all_files_match_receipt and matches_receipt
        all_snapshots_not_ahead = all_snapshots_not_ahead and not_ahead
        files[timeframe] = {
            **file_info(path),
            "sha256": snapshot_sha,
            "receipt_sha256": receipt_tf.get("sha256"),
            "matches_snapshot_receipt": matches_receipt,
            "snapshot_row_count": snapshot_rows,
            "current_shared_row_count": shared_rows,
            "snapshot_last_server_open": snapshot_last,
            "current_shared_last_server_open": shared_last,
            "snapshot_not_ahead_of_shared": not_ahead,
            "equals_current_shared_sha256": snapshot_sha == current_shared.get("sha256"),
        }

    receipt_ok = (
        receipt.get("status") == "PASS_PRIVATE_LOOP_SNAPSHOT"
        and receipt.get("snapshot_version") == V4_SNAPSHOT_VERSION
        and receipt.get("loop") == loop
        and receipt.get("runtime_or_start_modified") is False
        and receipt.get("historical_backfill_before_start") is False
    )
    return {
        "directory": str(directory),
        "receipt": {**file_info(receipt_path), "payload": receipt},
        "snapshot_age_seconds": age_seconds,
        "maximum_allowed_age_seconds": MAX_SNAPSHOT_AGE_SECONDS,
        "fresh": fresh,
        "files": files,
        "receipt_ok": receipt_ok,
        "all_files_match_snapshot_receipt": all_files_match_receipt,
        "all_snapshots_not_ahead_of_current_shared_journal": all_snapshots_not_ahead,
        "healthy": receipt_ok and fresh and all_files_match_receipt and all_snapshots_not_ahead,
    }


def main() -> int:
    try:
        local_value = os.environ.get("LOCALAPPDATA", "").strip()
        if not local_value:
            raise RuntimeError("LOCALAPPDATA unavailable")
        local_root = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
        source_root, point = adapter.source_environment(local_root)
        manifest = adapter.load_json(adapter.manifest_path(local_root))
        receipt = adapter.load_json(adapter.receipt_path(local_root))
        if receipt.get("status") != "PASS_MIGRATION_READY_FOR_REVIEW":
            raise RuntimeError("bounded adapter migration receipt is not PASS")
        journals = journal_integrity.verify_journals(local_root)

        output_root = local_root / "outputs" / "BOUNDED_CSV_SOURCE_ADAPTER_RESTART_HEALTH"
        archive = output_root / "archive" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)

        loops: dict[str, Any] = {}
        healthy = review = blocked = 0
        for loop, spec in runner.LOOPS.items():
            marker = migration.PROCESS_MARKERS[loop]
            processes = migration.running_processes(marker)
            lock_path = local_root / spec["lock_rel"]
            runtime_path = local_root / spec["runtime_rel"]
            status_path = local_root / spec["status_rel"]
            log_path = local_root / spec["log_rel"]
            output_summary_path = local_root / "outputs" / OUTPUT_NAMES[loop] / "LATEST" / "01_summary.json"
            runtime = read_json(runtime_path) or {}
            status = read_json(status_path) or {}
            output = read_json(output_summary_path) or {}
            runtime_sha = adapter.sha256_file(runtime_path) if runtime_path.is_file() else None
            expected_runtime_sha = receipt.get("runtime_manifest_sha256s", {}).get(loop)
            start = runtime.get("prospective_start_server_time")
            expected_start = adapter.EXPECTED_STARTS[loop]
            status_name = str(status.get("status", ""))
            successful = int(status.get("successful_cycles", 0) or 0)
            process_ok = bool(processes)
            process_v4_ok = process_uses_v4(processes)
            lock_ok = lock_path.is_file()
            runtime_ok = runtime_sha == expected_runtime_sha and start == expected_start
            output_ok = (
                output.get("status") == "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY"
                and output.get("prospective_start_server_time") == expected_start
            )
            status_ok = status_name == "RUNNING" and successful >= 1
            waiting_transient = status_name == "WAITING_TRANSIENT_SOURCE"
            private_snapshot = snapshot_health(local_root, loop, journals)
            snapshot_ok = bool(private_snapshot["healthy"])

            if process_ok and process_v4_ok and lock_ok and runtime_ok and status_ok and output_ok and snapshot_ok:
                classification = "HEALTHY_RUNNING_V4_PRIVATE_SNAPSHOT_PASS"
                healthy += 1
            elif process_ok and process_v4_ok and lock_ok and runtime_ok and waiting_transient and snapshot_ok:
                classification = "RUNNING_V4_WAITING_TRANSIENT_REVIEW"
                review += 1
            else:
                classification = "BLOCKED_OR_INCOMPLETE_V4_REVIEW"
                blocked += 1

            log_name = f"{loop}_bounded_log_tail.txt"
            (archive / log_name).write_text(tail(log_path), encoding="utf-8")
            loops[loop] = {
                "classification": classification,
                "process_marker": marker,
                "processes": processes,
                "process_uses_v4": process_v4_ok,
                "lock": file_info(lock_path),
                "runtime": {
                    **file_info(runtime_path),
                    "sha256": runtime_sha,
                    "expected_sha256": expected_runtime_sha,
                    "sha256_match": runtime_sha == expected_runtime_sha,
                    "prospective_start_server_time": start,
                    "expected_start": expected_start,
                    "start_match": start == expected_start,
                },
                "status": {**file_info(status_path), "payload": status},
                "latest_output_summary": {**file_info(output_summary_path), "payload": output},
                "private_snapshot": private_snapshot,
                "log": {**file_info(log_path), "tail_file": log_name},
            }

        all_healthy = healthy == len(runner.LOOPS)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "FRESH_LOOP_BOUNDED_CSV_V4_PRIVATE_SNAPSHOT_RESTART_HEALTH_AUDIT_ONLY",
            "status": "PASS_ALL_SEVEN_V4_PRIVATE_SNAPSHOT_HEALTHY" if all_healthy else "REVIEW_REQUIRED_NOT_ALL_SEVEN_V4_HEALTHY",
            "built_at_utc": utc_text(),
            "source_root": str(source_root),
            "xauusd_point": point,
            "adapter_manifest_status": manifest.get("status"),
            "required_process_token": V4_PROCESS_TOKEN,
            "required_snapshot_version": V4_SNAPSHOT_VERSION,
            "maximum_snapshot_age_seconds": MAX_SNAPSHOT_AGE_SECONDS,
            "journal_fingerprints_verified": journals,
            "classification_counts": {
                "HEALTHY_RUNNING_V4_PRIVATE_SNAPSHOT_PASS": healthy,
                "RUNNING_V4_WAITING_TRANSIENT_REVIEW": review,
                "BLOCKED_OR_INCOMPLETE_V4_REVIEW": blocked,
            },
            "all_seven_healthy": all_healthy,
            "loops": loops,
            "mutations_performed": False,
            "processes_started_or_stopped": False,
            "locks_removed": False,
            "runtime_or_start_modified": False,
            "journal_updated_by_audit": False,
            "restart_or_initializer_run_by_audit": False,
        }
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "Read-only V4 post-restart health audit for M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19.\n"
            "It requires seven V4 processes and verifies each fresh private snapshot against its own receipt and against a current shared journal that may be newer but never older.\n"
            "It does not start/stop loops, remove locks, update journals, reset runtimes or change starts.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "02_adapter_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "03_migration_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "04_audit.log").write_text("\n".join([
            f"status={summary['status']}",
            f"healthy_v4={healthy}",
            f"waiting_transient={review}",
            f"blocked_or_incomplete={blocked}",
            f"all_seven_healthy={str(all_healthy).lower()}",
            "mutations_performed=false",
            "runtime_or_start_modified=false",
            "journal_updated_by_audit=false",
            "",
        ]), encoding="utf-8")
        names = [path.name for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for name in sorted(names):
                zf.write(archive / name, name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[V4 HEALTH AUDIT] {summary['status']} healthy={healthy}/7 waiting={review} blocked={blocked}")
        print("[OUTPUT]", latest)
        print("[SAFE] Read-only audit; no process, lock, journal, snapshot, runtime or start was modified.")
        return 0 if all_healthy else 3
    except Exception as exc:
        print(f"[V4 HEALTH AUDIT BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No intentional process, lock, journal, runtime or start mutation was performed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
