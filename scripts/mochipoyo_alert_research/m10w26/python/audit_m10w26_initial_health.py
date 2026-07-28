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
MR = THIS.parents[2]
RECOVERY = MR / "recovery" / "python"
for directory in (MR / "common" / "python", MR / "m10w26" / "python", RECOVERY):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import bounded_csv_journal_integrity as journal_integrity
journal_integrity.install_verified_adapter_hooks()
import bounded_csv_source_adapter as adapter
import m10w26_runtime as base
import m10w26_runtime_v2 as runtime_v2
import migrate_bounded_csv_source_adapter as migration


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}
    return payload if isinstance(payload, dict) else {"_error": "JSON_NOT_OBJECT"}


def info(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        stat = path.stat()
        result.update({"size_bytes": stat.st_size, "sha256": adapter.sha256_file(path)})
    return result


def tail(path: Path, lines: int = 160) -> str:
    if not path.is_file():
        return ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return "".join(handle.readlines()[-lines:])


def main() -> int:
    try:
        local_value = os.environ.get("LOCALAPPDATA", "").strip()
        if not local_value:
            raise RuntimeError("LOCALAPPDATA unavailable")
        local_root = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
        paths = base.runtime_paths(local_root)
        snapshot = adapter.adapter_root(local_root) / "loop_snapshots" / "M10W26"
        runtime_path = paths["runtime"]
        state_path = paths["state"]
        start_receipt_path = paths["receipt"]
        prestart_path = paths["directory"] / "m10w26_prestart_causal_engine_audit.json"
        latest_summary_path = local_root / "outputs" / "M10W26" / "LATEST" / "01_summary.json"
        snapshot_receipt_path = snapshot / "00_snapshot_receipt.json"
        required = [runtime_path, state_path, start_receipt_path, prestart_path, paths["lock"], paths["loop_status"], latest_summary_path, snapshot_receipt_path]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"M10W26 initial health evidence missing: {missing}")

        runtime_payload = read_json(runtime_path)
        state = read_json(state_path)
        start_receipt = read_json(start_receipt_path)
        prestart = read_json(prestart_path)
        loop_status = read_json(paths["loop_status"])
        latest_summary = read_json(latest_summary_path)
        snapshot_receipt = read_json(snapshot_receipt_path)
        point = float(runtime_payload.get("point", "nan"))
        contract = base.load_json(base.CONTRACT)
        processes = migration.running_processes("run_m10w26_private_snapshot_v2.py")

        with adapter.update_lock(local_root, timeout_seconds=90.0):
            journals = journal_integrity.verify_journals(local_root)
            runtime_v2.verify_implementation_freeze(runtime_payload)
            current_snapshot = base.verify_runtime(local_root, snapshot, point, contract, runtime_payload)
            fingerprints = snapshot_receipt.get("journal_fingerprints", {})
            snapshot_files: dict[str, Any] = {}
            for timeframe, filename in adapter.FILE_MAP.items():
                path = snapshot / filename
                expected = fingerprints.get(timeframe, {}) if isinstance(fingerprints, dict) else {}
                actual_sha = adapter.sha256_file(path) if path.is_file() else None
                actual_size = path.stat().st_size if path.is_file() else None
                snapshot_files[timeframe] = {
                    **info(path),
                    "receipt_sha256": expected.get("sha256"),
                    "receipt_size_bytes": expected.get("size_bytes"),
                    "sha256_match": actual_sha == expected.get("sha256"),
                    "size_match": actual_size == expected.get("size_bytes"),
                    "not_ahead_of_shared_journal": (
                        base.parse_time(str(expected.get("last_server_open")))
                        <= base.parse_time(str(journals[timeframe].get("last_server_open")))
                    ) if expected.get("last_server_open") and journals[timeframe].get("last_server_open") else False,
                }

        start = runtime_payload.get("prospective_start_server_time")
        successful = int(loop_status.get("successful_cycles", 0) or 0)
        terminal = int(loop_status.get("failed_terminal_cycles", 0) or 0)
        checks = {
            "exactly_one_v2_process": len(processes) == 1,
            "lock_present": paths["lock"].is_file(),
            "runtime_version_v2": runtime_payload.get("runtime_contract_version") == runtime_v2.RUNTIME_VERSION,
            "runtime_frozen": runtime_payload.get("runtime_status") == "FROZEN_FRESH_START",
            "state_start_match": state.get("prospective_start_server_time") == start,
            "start_receipt_match": start_receipt.get("prospective_start_server_time") == start and start_receipt.get("status") == "PASS",
            "prestart_engine_pass": str(prestart.get("status", "")).startswith("PASS_PRESTART_CAUSAL_ENGINE_AUDIT"),
            "loop_running": loop_status.get("status") == "RUNNING",
            "successful_cycle": successful >= 1,
            "no_terminal_failure": terminal == 0,
            "latest_output_pass": latest_summary.get("status") == "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
            "latest_output_start_match": latest_summary.get("prospective_start_server_time") == start,
            "snapshot_receipt_pass": snapshot_receipt.get("status") == "PASS_PRIVATE_LOOP_SNAPSHOT" and snapshot_receipt.get("snapshot_version") == "M10W26_PRIVATE_VERIFIED_SNAPSHOT_V1",
            "all_snapshot_files_match": all(row["sha256_match"] and row["size_match"] and row["not_ahead_of_shared_journal"] for row in snapshot_files.values()),
            "all_shared_journals_verified": len(journals) == 6,
        }
        passed = all(checks.values())
        output_root = local_root / "outputs" / "M10W26_INITIAL_HEALTH"
        archive = output_root / "archive" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "M10W26_INITIAL_PRIVATE_SNAPSHOT_HEALTH_AUDIT_ONLY",
            "status": "PASS_M10W26_INITIAL_HEALTHY_RUNNING_AUDIT_ONLY" if passed else "REVIEW_REQUIRED_M10W26_INITIAL_HEALTH",
            "built_at_utc": utc_text(),
            "prospective_start_server_time": start,
            "processes": processes,
            "checks": checks,
            "loop_status": loop_status,
            "runtime": {**info(runtime_path), "payload": runtime_payload},
            "state": {**info(state_path), "payload": state},
            "start_receipt": {**info(start_receipt_path), "payload": start_receipt},
            "prestart_audit": {**info(prestart_path), "payload": prestart},
            "latest_output_summary": {**info(latest_summary_path), "payload": latest_summary},
            "snapshot_receipt": {**info(snapshot_receipt_path), "payload": snapshot_receipt},
            "snapshot_files": snapshot_files,
            "current_snapshot": current_snapshot,
            "shared_journals": journals,
            "mutations_performed": False,
            "process_started_or_stopped": False,
            "lock_removed": False,
            "runtime_or_start_modified": False,
            "journal_updated": False,
        }
        (archive / "00_READ_ME_FIRST.txt").write_text("Read-only initial health audit for the new M10W26 audit-only private-snapshot shadow. It does not start, stop, reset, initialize or mutate any loop.\n", encoding="utf-8")
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "02_runtime_manifest.json").write_text(json.dumps(runtime_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "03_runtime_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "04_prestart_causal_engine_audit.json").write_text(json.dumps(prestart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "05_snapshot_receipt.json").write_text(json.dumps(snapshot_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "06_loop_log_tail.txt").write_text(tail(paths["log"]), encoding="utf-8")
        (archive / "07_audit.log").write_text("\n".join([
            f"status={summary['status']}", f"prospective_start_server_time={start}",
            *(f"{key}={str(value).lower()}" for key, value in checks.items()),
            "mutations_performed=false", "runtime_or_start_modified=false", "journal_updated=false", "",
        ]), encoding="utf-8")
        names = [path for path in archive.iterdir() if path.is_file()]
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as package:
            for path in sorted(names):
                package.write(path, path.name)
        latest = output_root / "LATEST"
        shutil.rmtree(latest, ignore_errors=True)
        shutil.copytree(archive, latest)
        print(f"[M10W26 HEALTH] {summary['status']}")
        print(f"[OUTPUT] {latest}")
        print("[SAFE] Read-only audit; no process, lock, runtime, start or journal was modified.")
        return 0 if passed else 3
    except Exception as exc:
        print(f"[M10W26 HEALTH BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No intentional process, lock, runtime, start or journal mutation was performed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
