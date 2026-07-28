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
for directory in (MR / "common" / "python", THIS.parent, RECOVERY):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import bounded_csv_journal_integrity as journal_integrity
journal_integrity.install_verified_adapter_hooks()
import bounded_csv_source_adapter as adapter
import m10w34_runtime as runtime
import migrate_bounded_csv_source_adapter as migration


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def info(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if path.is_file():
        row.update({"size_bytes": path.stat().st_size, "sha256": adapter.sha256_file(path)})
    return row


def checkpoint_tier(resolved: int) -> str:
    if resolved >= 120:
        return "FORMAL_REVIEW_READY"
    if resolved >= 60:
        return "INTERIM_REVIEW_READY"
    if resolved >= 20:
        return "OPERATIONAL_REVIEW_READY"
    return "PRE_OPERATIONAL_ACCUMULATING"


def main() -> int:
    try:
        local_value = os.environ.get("LOCALAPPDATA", "").strip()
        if not local_value:
            raise RuntimeError("LOCALAPPDATA unavailable")
        local = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
        paths = runtime.runtime_paths(local)
        snapshot = adapter.adapter_root(local) / "loop_snapshots" / "M10W34"
        latest_path = local / "outputs" / "M10W34" / "LATEST" / "01_summary.json"
        snapshot_receipt_path = snapshot / "00_snapshot_receipt.json"
        required = [
            paths["runtime"], paths["state"], paths["receipt"], paths["prestart"],
            paths["lock"], paths["loop_status"], latest_path, snapshot_receipt_path,
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"M10W34 checkpoint evidence missing: {missing}")

        runtime_payload = read_json(paths["runtime"])
        state = read_json(paths["state"])
        start_receipt = read_json(paths["receipt"])
        prestart = read_json(paths["prestart"])
        loop_status = read_json(paths["loop_status"])
        latest = read_json(latest_path)
        snapshot_receipt = read_json(snapshot_receipt_path)
        contract = runtime.load_json(runtime.CONTRACT)
        point = float(runtime_payload.get("point", "nan"))
        processes = migration.running_processes("run_m10w34_private_snapshot.py")

        with adapter.update_lock(local, timeout_seconds=90.0):
            journals = journal_integrity.verify_journals(local)
            current_snapshot = runtime.verify_runtime(local, snapshot, point, contract, runtime_payload)
            fingerprints = snapshot_receipt.get("journal_fingerprints", {})
            snapshot_files: dict[str, Any] = {}
            for timeframe, filename in adapter.FILE_MAP.items():
                path = snapshot / filename
                expected = fingerprints.get(timeframe, {}) if isinstance(fingerprints, dict) else {}
                actual_sha = adapter.sha256_file(path) if path.is_file() else None
                actual_size = path.stat().st_size if path.is_file() else None
                not_ahead = False
                if expected.get("last_server_open") and journals[timeframe].get("last_server_open"):
                    not_ahead = runtime.parse_time(str(expected["last_server_open"])) <= runtime.parse_time(str(journals[timeframe]["last_server_open"]))
                snapshot_files[timeframe] = {
                    **info(path),
                    "receipt_sha256": expected.get("sha256"),
                    "receipt_size_bytes": expected.get("size_bytes"),
                    "sha256_match": actual_sha == expected.get("sha256"),
                    "size_match": actual_size == expected.get("size_bytes"),
                    "not_ahead_of_shared_journal": not_ahead,
                }

        start = runtime_payload.get("prospective_start_server_time")
        metrics = latest.get("SNDX1_CAUSAL_NEITHER", {})
        resolved = int(metrics.get("resolved_count", 0) or 0)
        tier = checkpoint_tier(resolved)
        successful = int(loop_status.get("successful_cycles", 0) or 0)
        terminal = int(loop_status.get("failed_terminal_cycles", 0) or 0)
        checks = {
            "exactly_one_process": len(processes) == 1,
            "lock_present": paths["lock"].is_file(),
            "runtime_frozen": runtime_payload.get("runtime_status") == "FROZEN_FRESH_START",
            "runtime_version_match": runtime_payload.get("runtime_contract_version") == runtime.RUNTIME_VERSION,
            "state_start_match": state.get("prospective_start_server_time") == start,
            "start_receipt_match": start_receipt.get("prospective_start_server_time") == start and start_receipt.get("status") == "PASS",
            "prestart_engine_pass": str(prestart.get("status", "")).startswith("PASS_PRESTART_CAUSAL_ENGINE_AUDIT"),
            "loop_running": loop_status.get("status") == "RUNNING",
            "successful_cycle": successful >= 1,
            "no_terminal_failure": terminal == 0,
            "latest_output_pass": latest.get("status") == "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY",
            "latest_output_start_match": latest.get("prospective_start_server_time") == start,
            "snapshot_receipt_pass": snapshot_receipt.get("status") == "PASS_PRIVATE_LOOP_SNAPSHOT",
            "all_snapshot_files_match": all(row["sha256_match"] and row["size_match"] and row["not_ahead_of_shared_journal"] for row in snapshot_files.values()),
            "all_shared_journals_verified": len(journals) == 6,
        }
        passed = all(checks.values())
        status = f"PASS_M10W34_{tier}_AUDIT_ONLY" if passed else "REVIEW_REQUIRED_M10W34_CHECKPOINT"

        output = local / "outputs" / "M10W34_CHECKPOINT"
        archive = output / "archive" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "M10W34_READ_ONLY_CHECKPOINT_AUDIT_ONLY",
            "status": status,
            "built_at_utc": utc_text(),
            "prospective_start_server_time": start,
            "checkpoint_tier": tier,
            "review_gates": {"operational_resolved": 20, "interim_resolved": 60, "formal_resolved": 120},
            "SNDX1_CAUSAL_NEITHER": metrics,
            "review_readiness": latest.get("review_readiness", {}),
            "processes": processes,
            "checks": checks,
            "loop_status": loop_status,
            "runtime": {**info(paths["runtime"]), "payload": runtime_payload},
            "state": {**info(paths["state"]), "payload": state},
            "start_receipt": {**info(paths["receipt"]), "payload": start_receipt},
            "prestart_audit": {**info(paths["prestart"]), "payload": prestart},
            "latest_output_summary": {**info(latest_path), "payload": latest},
            "snapshot_receipt": {**info(snapshot_receipt_path), "payload": snapshot_receipt},
            "snapshot_files": snapshot_files,
            "current_snapshot": current_snapshot,
            "shared_journals": journals,
            "mutations_performed": False,
            "process_started_or_stopped": False,
            "lock_removed": False,
            "runtime_or_start_modified": False,
            "journal_updated": False,
            "automatic_live_promotion": False,
        }
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "Read-only M10W34 checkpoint. It evaluates health and resolved-count review readiness only. It does not initialize, restart, stop, reset, promote, place orders, or alter formulas.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "02_runtime_manifest.json").write_text(json.dumps(runtime_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "03_runtime_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "04_latest_forward_summary.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "05_snapshot_receipt.json").write_text(json.dumps(snapshot_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (archive / "06_audit.log").write_text("\n".join([
            f"status={status}", f"prospective_start_server_time={start}", f"checkpoint_tier={tier}",
            f"resolved_count={resolved}", *(f"{key}={str(value).lower()}" for key, value in checks.items()),
            "mutations_performed=false", "runtime_or_start_modified=false", "automatic_live_promotion=false", "",
        ]), encoding="utf-8")
        with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as package:
            for path in sorted(item for item in archive.iterdir() if item.is_file()):
                package.write(path, path.name)
        latest_dir = output / "LATEST"
        shutil.rmtree(latest_dir, ignore_errors=True)
        shutil.copytree(archive, latest_dir)
        print(f"[M10W34 CHECKPOINT] {status} RESOLVED={resolved}")
        print(f"[OUTPUT] {latest_dir}")
        print("[SAFE] Read-only checkpoint; no process, lock, runtime, start, journal, formula or promotion changed.")
        return 0 if passed else 3
    except Exception as exc:
        print(f"[M10W34 CHECKPOINT BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No intentional process, lock, runtime, start, journal, formula or promotion mutation was performed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
