from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT = "MOCHIPOYO_ALERT_RESEARCH"
STAGE = "M10P_BLOCKED_DIAGNOSTIC_READ_ONLY"


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def local_root() -> Path:
    value = os.environ.get("LOCALAPPDATA", "").strip()
    if not value:
        raise RuntimeError("LOCALAPPDATA unavailable")
    return Path(value) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "MISSING"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON_NOT_OBJECT"
    return payload, None


def file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    stat = path.stat()
    payload: dict[str, Any] = {
        "exists": True,
        "path": str(path),
        "is_file": path.is_file(),
        "size_bytes": stat.st_size,
        "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if path.is_file():
        payload["sha256"] = sha256_file(path)
    return payload


def copy_if_file(source: Path, destination: Path) -> bool:
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def tail_text(path: Path, max_bytes: int = 300_000) -> str:
    if not path.is_file():
        return f"MISSING: {path}\n"
    with path.open("rb") as handle:
        size = path.stat().st_size
        if size > max_bytes:
            handle.seek(size - max_bytes)
        raw = handle.read()
    return raw.decode("utf-8", errors="replace")


def process_inventory() -> dict[str, Any]:
    if os.name != "nt":
        return {"status": "NOT_WINDOWS", "rows": []}
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "$ErrorActionPreference='Stop'; "
        "$rows = Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match '(?i)(--loop\\s+M10P|m10p_guarded_runtime|m10p_runtime\\.py)' } | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine; "
        "@($rows) | ConvertTo-Json -Depth 4 -Compress",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except Exception as exc:
        return {"status": "QUERY_FAILED", "error": f"{type(exc).__name__}: {exc}", "rows": []}
    if completed.returncode != 0:
        return {
            "status": "QUERY_FAILED",
            "returncode": completed.returncode,
            "stderr": completed.stderr[-8000:],
            "rows": [],
        }
    text = completed.stdout.strip()
    if not text:
        return {"status": "PASS", "rows": []}
    try:
        parsed = json.loads(text)
    except Exception as exc:
        return {"status": "PARSE_FAILED", "error": f"{type(exc).__name__}: {exc}", "raw": text[-12000:], "rows": []}
    rows = parsed if isinstance(parsed, list) else [parsed]
    return {"status": "PASS", "rows": rows}


def main() -> int:
    root = local_root()
    output_root = root / "outputs" / "M10P_BLOCKED_DIAGNOSTIC"
    archive = output_root / "archive" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)

    sources = {
        "loop_status": root / "logs" / "m10p" / "latest_m10p_shadow_loop_status.json",
        "loop_log": root / "logs" / "m10p" / "m10p_bounded_adapter_forever.log",
        "runtime_manifest": root / "m10p_runtime" / "m10p_runtime_manifest.json",
        "runtime_state": root / "m10p_runtime" / "m10p_runtime_state.json",
        "start_receipt": root / "m10p_runtime" / "m10p_runtime_start_receipt.json",
        "lock": root / "m10p_runtime" / "m10p_shadow_loop.lock",
        "latest_summary": root / "outputs" / "M10P" / "LATEST" / "01_summary.json",
        "latest_candidate_ledger": root / "outputs" / "M10P" / "LATEST" / "02_candidate_ledger.csv",
        "latest_trade_ledger": root / "outputs" / "M10P" / "LATEST" / "03_trade_ledger.csv",
        "latest_overlap_ledger": root / "outputs" / "M10P" / "LATEST" / "04_overlap_skip_ledger.csv",
        "latest_runtime_copy": root / "outputs" / "M10P" / "LATEST" / "05_runtime_manifest_copy.json",
        "latest_data_quality": root / "outputs" / "M10P" / "LATEST" / "06_data_quality.json",
        "latest_audit_log": root / "outputs" / "M10P" / "LATEST" / "07_audit.log",
    }

    status_payload, status_error = read_json(sources["loop_status"])
    runtime_payload, runtime_error = read_json(sources["runtime_manifest"])
    state_payload, state_error = read_json(sources["runtime_state"])
    receipt_payload, receipt_error = read_json(sources["start_receipt"])
    summary_payload, summary_error = read_json(sources["latest_summary"])
    processes = process_inventory()

    summary = {
        "project": PROJECT,
        "stage": STAGE,
        "status": "PASS_DIAGNOSTIC_PACKAGE_CREATED_READ_ONLY",
        "built_at_utc": utc_text(),
        "observed_dashboard_condition": {
            "loop": "M10P",
            "health": "BLOCKED",
            "lock_expected_from_dashboard": False,
            "dashboard_age_minutes_at_report": 47,
            "accepted_count_at_report": 1,
            "resolved_count_at_report": 0,
            "open_count_at_report": 1,
        },
        "current_observation": {
            "loop_status": status_payload,
            "loop_status_read_error": status_error,
            "runtime_manifest": runtime_payload,
            "runtime_manifest_read_error": runtime_error,
            "runtime_state": state_payload,
            "runtime_state_read_error": state_error,
            "start_receipt": receipt_payload,
            "start_receipt_read_error": receipt_error,
            "latest_summary": summary_payload,
            "latest_summary_read_error": summary_error,
            "lock_present": sources["lock"].is_file(),
            "matching_process_inventory": processes,
        },
        "file_inventory": {name: file_info(path) for name, path in sources.items()},
        "mutations": {
            "m10p_process_start_or_stop": False,
            "initializer_run": False,
            "runtime_or_state_write": False,
            "start_write": False,
            "lock_write_or_delete": False,
            "journal_or_snapshot_write": False,
            "m10p_latest_write": False,
            "other_loop_modified": False,
            "discord_send": False,
            "mt5_order": False,
        },
    }

    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10P blocked-state diagnostic package. This collector is read-only with respect to all monitors, runtimes, starts, locks, journals, snapshots, and M10P evidence. It only writes this separate diagnostic package. Do not run any initializer or restart M10P until this package is reviewed.\n",
        encoding="utf-8",
    )
    (archive / "01_diagnostic_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (archive / "02_loop_log_tail.txt").write_text(tail_text(sources["loop_log"]), encoding="utf-8")
    (archive / "03_process_inventory.json").write_text(
        json.dumps(processes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    copy_map = {
        "10_loop_status.json": "loop_status",
        "11_runtime_manifest.json": "runtime_manifest",
        "12_runtime_state.json": "runtime_state",
        "13_start_receipt.json": "start_receipt",
        "14_latest_summary.json": "latest_summary",
        "15_latest_candidate_ledger.csv": "latest_candidate_ledger",
        "16_latest_trade_ledger.csv": "latest_trade_ledger",
        "17_latest_overlap_ledger.csv": "latest_overlap_ledger",
        "18_latest_runtime_copy.json": "latest_runtime_copy",
        "19_latest_data_quality.json": "latest_data_quality",
        "20_latest_audit.log": "latest_audit_log",
    }
    copied: list[str] = []
    missing: list[str] = []
    for destination_name, source_name in copy_map.items():
        if copy_if_file(sources[source_name], archive / destination_name):
            copied.append(destination_name)
        else:
            missing.append(source_name)

    (archive / "21_copy_manifest.json").write_text(
        json.dumps({"copied": copied, "missing": missing}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    package = archive / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(item for item in archive.iterdir() if item.is_file() and item.name != package.name):
            handle.write(path, path.name)

    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    latest_package = latest / package.name
    print("[M10P DIAGNOSTIC PASS] read-only package created")
    print(f"[M10P DIAGNOSTIC STATUS] {(status_payload or {}).get('status', status_error or 'UNKNOWN')}")
    print(f"[M10P DIAGNOSTIC LOCK] {'PRESENT' if sources['lock'].is_file() else 'ABSENT'}")
    print(f"[M10P DIAGNOSTIC PACKAGE] {latest_package}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10P DIAGNOSTIC BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No monitor, runtime, start, lock, journal, snapshot, Discord, or MT5 order was changed.", file=sys.stderr)
        raise SystemExit(2)
