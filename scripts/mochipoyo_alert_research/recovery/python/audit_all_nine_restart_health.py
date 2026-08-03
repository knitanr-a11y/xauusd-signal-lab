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
REPO_ROOT = THIS.parents[4]
COMMON = THIS.parents[2] / "common" / "python"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import bounded_csv_journal_integrity as journal_integrity

journal_integrity.install_verified_adapter_hooks()

import bounded_csv_source_adapter as adapter
import migrate_bounded_csv_source_adapter as migration

MAX_SNAPSHOT_AGE_SECONDS = 300.0

LOOPS: dict[str, dict[str, Any]] = {
    "M9V": {
        "process_marker": "run_m9v_shadow_forever_safe",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m9v_runtime") / "m9v_runtime_manifest.json",
        "lock_rel": Path("m9v_runtime") / "m9v_shadow_loop.lock",
        "status_rel": Path("logs") / "m9v" / "latest_m9v_shadow_loop_status.json",
        "log_rel": Path("logs") / "m9v" / "m9v_shadow_forever.log",
        "expected_start": "2026.07.24 11:04:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M9Y": {
        "process_marker": "run_m9y_shadow_forever_safe.py",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m9y_runtime") / "m9y_runtime_manifest.json",
        "lock_rel": Path("m9y_runtime") / "m9y_shadow_loop.lock",
        "status_rel": Path("logs") / "m9y" / "latest_m9y_shadow_loop_status.json",
        "log_rel": Path("logs") / "m9y" / "m9y_shadow_forever.log",
        "expected_start": "2026.07.24 12:45:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M10B": {
        "process_marker": "m10b_runtime.py",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m10b_runtime") / "m10b_runtime_manifest.json",
        "lock_rel": Path("m10b_runtime") / "m10b_shadow_loop.lock",
        "status_rel": Path("logs") / "m10b" / "latest_m10b_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10b" / "m10b_bounded_adapter_forever.log",
        "expected_start": "2026.07.24 20:54:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M10E": {
        "process_marker": "m10e_runtime.py",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m10e_runtime") / "m10e_runtime_manifest.json",
        "lock_rel": Path("m10e_runtime") / "m10e_shadow_loop.lock",
        "status_rel": Path("logs") / "m10e" / "latest_m10e_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10e" / "m10e_bounded_adapter_forever.log",
        "expected_start": "2026.07.24 22:06:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M10P": {
        "process_marker": "m10p_guarded_runtime.py",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m10p_runtime") / "m10p_runtime_manifest.json",
        "lock_rel": Path("m10p_runtime") / "m10p_shadow_loop.lock",
        "status_rel": Path("logs") / "m10p" / "latest_m10p_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10p" / "m10p_bounded_adapter_forever.log",
        "expected_start": "2026.07.24 23:56:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M10P2": {
        "process_marker": "m10p2_guarded_runtime.py",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m10p2_runtime") / "m10p2_runtime_manifest.json",
        "lock_rel": Path("m10p2_runtime") / "m10p2_shadow_loop.lock",
        "status_rel": Path("logs") / "m10p2" / "latest_m10p2_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10p2" / "m10p2_bounded_adapter_forever.log",
        "expected_start": "2026.07.27 01:39:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M10W19": {
        "process_marker": "m10w19_runtime.py",
        "required_process_token": "run_bounded_adapter_loop_v4.py",
        "runtime_rel": Path("m10w19_runtime") / "m10w19_runtime_manifest.json",
        "lock_rel": Path("m10w19_runtime") / "m10w19_shadow_loop.lock",
        "status_rel": Path("logs") / "m10w19" / "latest_m10w19_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10w19" / "m10w19_bounded_adapter_forever.log",
        "expected_start": "2026.07.28 02:31:00",
        "snapshot_version": "BOUNDED_CSV_PER_LOOP_SNAPSHOT_V1",
    },
    "M10W26": {
        "process_marker": "run_m10w26_private_snapshot",
        "required_process_token": "run_m10w26_private_snapshot_v2.py",
        "runtime_rel": Path("m10w26_runtime") / "m10w26_runtime_manifest.json",
        "lock_rel": Path("m10w26_runtime") / "m10w26_shadow_loop.lock",
        "status_rel": Path("logs") / "m10w26" / "latest_m10w26_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10w26" / "m10w26_private_snapshot_forever.log",
        "expected_start": "2026.07.28 15:58:00",
        "snapshot_version": "M10W26_PRIVATE_VERIFIED_SNAPSHOT_V1",
    },
    "M10W34": {
        "process_marker": "run_m10w34_private_snapshot.py",
        "required_process_token": "run_m10w34_private_snapshot.py",
        "runtime_rel": Path("m10w34_runtime") / "m10w34_runtime_manifest.json",
        "lock_rel": Path("m10w34_runtime") / "m10w34_shadow_loop.lock",
        "status_rel": Path("logs") / "m10w34" / "latest_m10w34_shadow_loop_status.json",
        "log_rel": Path("logs") / "m10w34" / "m10w34_private_snapshot_forever.log",
        "expected_start": "2026.07.28 18:19:00",
        "snapshot_version": "M10W34_PRIVATE_VERIFIED_SNAPSHOT_V1",
    },
}


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def parse_utc(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except Exception:
        return None


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}"}
    return payload if isinstance(payload, dict) else {"_read_error": "JSON_NOT_OBJECT"}


def file_info(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        stat = path.stat()
        row.update(
            {
                "size_bytes": stat.st_size,
                "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        )
    return row


def tail(path: Path, lines: int = 160) -> str:
    if not path.is_file():
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return "".join(handle.readlines()[-lines:])
    except Exception as exc:
        return f"[TAIL ERROR] {type(exc).__name__}: {exc}\n"


def expected_runtime_shas(local_root: Path) -> dict[str, str | None]:
    migration_receipt = read_json(adapter.receipt_path(local_root))
    result: dict[str, str | None] = {
        loop: migration_receipt.get("runtime_manifest_sha256s", {}).get(loop)
        for loop in ("M9V", "M9Y", "M10B", "M10E", "M10P", "M10P2", "M10W19")
    }

    w26 = read_json(
        REPO_ROOT
        / "config"
        / "mochipoyo_alert_research"
        / "m10w26_user_local_initial_health_result_20260728.json"
    )
    w34 = read_json(
        REPO_ROOT
        / "config"
        / "mochipoyo_alert_research"
        / "m10w34_user_local_initial_health_result_20260728.json"
    )
    result["M10W26"] = w26.get("runtime", {}).get("runtime_manifest_sha256")
    result["M10W34"] = w34.get("runtime", {}).get("runtime_sha256")
    return result


def process_token_ok(processes: list[dict[str, Any]], token: str) -> bool:
    wanted = token.lower()
    return len(processes) == 1 and wanted in str(processes[0].get("CommandLine", "")).lower()


def snapshot_health(
    local_root: Path,
    loop: str,
    expected_version: str,
    journals: dict[str, Any],
) -> dict[str, Any]:
    directory = adapter.adapter_root(local_root) / "loop_snapshots" / loop
    receipt_path = directory / "00_snapshot_receipt.json"
    receipt = read_json(receipt_path)
    fingerprints = receipt.get("journal_fingerprints", {})
    created = parse_utc(receipt.get("created_at_utc"))
    age_seconds = None if created is None else (datetime.now(UTC) - created).total_seconds()
    fresh = age_seconds is not None and -5.0 <= age_seconds <= MAX_SNAPSHOT_AGE_SECONDS

    files: dict[str, Any] = {}
    all_match = True
    all_not_ahead = True
    for timeframe, filename in adapter.FILE_MAP.items():
        path = directory / filename
        receipt_tf = fingerprints.get(timeframe, {}) if isinstance(fingerprints, dict) else {}
        shared_tf = journals.get(timeframe, {})
        sha = adapter.sha256_file(path) if path.is_file() else None
        size = path.stat().st_size if path.is_file() else None
        matches = (
            path.is_file()
            and sha == receipt_tf.get("sha256")
            and size == receipt_tf.get("size_bytes")
        )
        snapshot_rows = int(receipt_tf.get("row_count", -1) or -1)
        shared_rows = int(shared_tf.get("row_count", -1) or -1)
        snapshot_first = receipt_tf.get("first_server_open")
        shared_first = shared_tf.get("first_server_open")
        snapshot_last = receipt_tf.get("last_server_open")
        shared_last = shared_tf.get("last_server_open")
        not_ahead = (
            snapshot_rows >= 0
            and shared_rows >= snapshot_rows
            and snapshot_first == shared_first
            and isinstance(snapshot_last, str)
            and isinstance(shared_last, str)
            and snapshot_last <= shared_last
        )
        all_match = all_match and matches
        all_not_ahead = all_not_ahead and not_ahead
        files[timeframe] = {
            **file_info(path),
            "sha256": sha,
            "receipt_sha256": receipt_tf.get("sha256"),
            "matches_receipt": matches,
            "snapshot_row_count": snapshot_rows,
            "shared_row_count": shared_rows,
            "snapshot_last_server_open": snapshot_last,
            "shared_last_server_open": shared_last,
            "not_ahead_of_shared_journal": not_ahead,
        }

    unmodified = (
        receipt.get("runtime_or_start_modified") is False
        or receipt.get("runtime_or_start_modified_by_snapshot") is False
    )
    receipt_ok = (
        receipt.get("status") == "PASS_PRIVATE_LOOP_SNAPSHOT"
        and receipt.get("snapshot_version") == expected_version
        and receipt.get("loop") == loop
        and unmodified
        and receipt.get("historical_backfill_before_start") is False
    )
    healthy = receipt_ok and fresh and all_match and all_not_ahead
    return {
        "directory": str(directory),
        "receipt": {**file_info(receipt_path), "payload": receipt},
        "age_seconds": age_seconds,
        "maximum_age_seconds": MAX_SNAPSHOT_AGE_SECONDS,
        "fresh": fresh,
        "all_files_match_receipt": all_match,
        "all_files_not_ahead_of_shared_journal": all_not_ahead,
        "files": files,
        "healthy": healthy,
    }


def main() -> int:
    try:
        local_value = os.environ.get("LOCALAPPDATA", "").strip()
        if not local_value:
            raise RuntimeError("LOCALAPPDATA unavailable")
        local_root = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
        journals = journal_integrity.verify_journals(local_root)
        expected_shas = expected_runtime_shas(local_root)

        output_root = local_root / "outputs" / "ALL_NINE_RESTART_HEALTH"
        archive = output_root / "archive" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)

        loops: dict[str, Any] = {}
        healthy_count = 0
        for loop, spec in LOOPS.items():
            processes = migration.running_processes(str(spec["process_marker"]))
            runtime_path = local_root / Path(spec["runtime_rel"])
            lock_path = local_root / Path(spec["lock_rel"])
            status_path = local_root / Path(spec["status_rel"])
            log_path = local_root / Path(spec["log_rel"])
            output_path = local_root / "outputs" / loop / "LATEST" / "01_summary.json"

            runtime = read_json(runtime_path)
            status = read_json(status_path)
            output = read_json(output_path)
            runtime_sha = adapter.sha256_file(runtime_path) if runtime_path.is_file() else None
            expected_sha = expected_shas.get(loop)
            start = runtime.get("prospective_start_server_time")
            expected_start = str(spec["expected_start"])
            successful = int(status.get("successful_cycles", 0) or 0)
            terminal = int(status.get("failed_terminal_cycles", 0) or 0)
            snapshot = snapshot_health(
                local_root,
                loop,
                str(spec["snapshot_version"]),
                journals,
            )

            checks = {
                "exactly_one_process": len(processes) == 1,
                "required_process_token": process_token_ok(
                    processes, str(spec["required_process_token"])
                ),
                "lock_present": lock_path.is_file(),
                "runtime_present": runtime_path.is_file(),
                "runtime_sha_expected_available": isinstance(expected_sha, str) and bool(expected_sha),
                "runtime_sha_match": runtime_sha == expected_sha,
                "start_match": start == expected_start,
                "status_running": status.get("status") == "RUNNING",
                "successful_cycle": successful >= 1,
                "no_terminal_failure": terminal == 0,
                "latest_output_pass": output.get("status") == "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
                "latest_output_start_match": output.get("prospective_start_server_time") == expected_start,
                "private_snapshot_healthy": snapshot["healthy"],
            }
            healthy = all(checks.values())
            if healthy:
                healthy_count += 1
                classification = "HEALTHY_RUNNING_ALL_NINE_PASS"
            else:
                classification = "REVIEW_REQUIRED_NOT_HEALTHY"

            log_name = f"{loop}_log_tail.txt"
            (archive / log_name).write_text(tail(log_path), encoding="utf-8")
            loops[loop] = {
                "classification": classification,
                "healthy": healthy,
                "checks": checks,
                "process_marker": spec["process_marker"],
                "required_process_token": spec["required_process_token"],
                "processes": processes,
                "lock": file_info(lock_path),
                "runtime": {
                    **file_info(runtime_path),
                    "sha256": runtime_sha,
                    "expected_sha256": expected_sha,
                    "prospective_start_server_time": start,
                    "expected_start": expected_start,
                },
                "status": {**file_info(status_path), "payload": status},
                "latest_output": {**file_info(output_path), "payload": output},
                "private_snapshot": snapshot,
                "log": {**file_info(log_path), "tail_file": log_name},
            }

        all_healthy = healthy_count == len(LOOPS)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "ALL_NINE_FORWARD_LOOPS_RESTART_HEALTH_AUDIT_ONLY",
            "status": (
                "PASS_ALL_NINE_RESTART_HEALTHY_AUDIT_ONLY"
                if all_healthy
                else "REVIEW_REQUIRED_NOT_ALL_NINE_HEALTHY"
            ),
            "built_at_utc": utc_text(),
            "loop_count": len(LOOPS),
            "healthy_count": healthy_count,
            "all_nine_healthy": all_healthy,
            "maximum_snapshot_age_seconds": MAX_SNAPSHOT_AGE_SECONDS,
            "journal_fingerprints_verified": journals,
            "loops": loops,
            "mutations_performed": False,
            "processes_started_or_stopped": False,
            "locks_removed": False,
            "runtime_or_start_modified": False,
            "journal_or_snapshot_modified": False,
            "historical_backfill": False,
        }
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "Read-only post-restart health audit for M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19/M10W26/M10W34.\n"
            "No loop, lock, runtime, start, journal, snapshot, state/history, Discord or MT5 order was modified.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        zip_path = archive / "99_UPLOAD_PACKAGE.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(archive.iterdir()):
                if path.is_file() and path.name != zip_path.name:
                    zf.write(path, path.name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)

        print(
            "[HEALTH PASS] all nine forward loops are healthy"
            if all_healthy
            else f"[HEALTH REVIEW] healthy={healthy_count}/{len(LOOPS)}"
        )
        print("[OUTPUT]", latest)
        print("[SAFE] Read-only audit; no protected runtime/start/lock/journal was changed.")
        return 0 if all_healthy else 3
    except Exception as exc:
        print(f"[HEALTH AUDIT BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No process, lock, runtime, start, journal or snapshot was intentionally changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
