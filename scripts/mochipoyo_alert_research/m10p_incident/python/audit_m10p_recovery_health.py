from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT = "MOCHIPOYO_ALERT_RESEARCH"
STAGE = "M10P_PRESERVED_START_RECOVERY_HEALTH_AUDIT"
EXPECTED_START = "2026.07.24 23:56:00"


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def local_root() -> Path:
    value = os.environ.get("LOCALAPPDATA", "").strip()
    if not value:
        raise RuntimeError("LOCALAPPDATA unavailable")
    return Path(value) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_alive(pid: int) -> bool | None:
    if pid <= 0:
        return False
    if os.name != "nt":
        return None
    query = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(query, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return ctypes.windll.kernel32.GetLastError() == 5


def main() -> int:
    root = local_root()
    paths = {
        "runtime": root / "m10p_runtime" / "m10p_runtime_manifest.json",
        "state": root / "m10p_runtime" / "m10p_runtime_state.json",
        "start_receipt": root / "m10p_runtime" / "m10p_runtime_start_receipt.json",
        "lock": root / "m10p_runtime" / "m10p_shadow_loop.lock",
        "status": root / "logs" / "m10p" / "latest_m10p_shadow_loop_status.json",
        "summary": root / "outputs" / "M10P" / "LATEST" / "01_summary.json",
        "runtime_copy": root / "outputs" / "M10P" / "LATEST" / "05_runtime_manifest_copy.json",
        "trade": root / "outputs" / "M10P" / "LATEST" / "03_trade_ledger.csv",
        "recovery_preflight": root / "outputs" / "M10P_PRESERVED_START_RECOVERY" / "LATEST" / "01_recovery_preflight.json",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"M10P recovery health evidence missing: {missing}")

    runtime = load_json(paths["runtime"])
    state = load_json(paths["state"])
    receipt = load_json(paths["start_receipt"])
    lock = load_json(paths["lock"])
    status = load_json(paths["status"])
    summary = load_json(paths["summary"])
    preflight = load_json(paths["recovery_preflight"])

    starts = {
        runtime.get("prospective_start_server_time"),
        state.get("prospective_start_server_time"),
        receipt.get("prospective_start_server_time"),
        status.get("prospective_start_server_time"),
        summary.get("prospective_start_server_time"),
        preflight.get("preserved_start_server_time"),
    }
    if starts != {EXPECTED_START}:
        raise RuntimeError(f"M10P start changed during recovery: {starts}")
    if paths["runtime"].read_bytes() != paths["runtime_copy"].read_bytes():
        raise RuntimeError("M10P runtime copy mismatch after recovery")
    if status.get("status") != "RUNNING":
        raise RuntimeError(f"M10P recovery loop is not RUNNING: {status.get('status')}")
    if int(status.get("successful_cycles", 0)) < 1:
        raise RuntimeError("M10P recovery has no successful cycle")
    if int(status.get("failed_terminal_cycles", 0)) != 0:
        raise RuntimeError("M10P recovery session has a terminal failure")
    if status.get("runtime_or_start_modified") is not False:
        raise RuntimeError("M10P recovery status reports runtime/start modification")
    if summary.get("status") != "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY":
        raise RuntimeError("M10P post-recovery summary is not PASS")
    if state.get("status") != "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY":
        raise RuntimeError("M10P post-recovery state is not PASS")
    if preflight.get("status") != "PASS_PRESERVED_START_RECOVERY_PREFLIGHT_AUTHORIZED":
        raise RuntimeError("M10P recovery preflight receipt is not PASS")

    pid = int(lock.get("pid", 0) or 0)
    alive = process_alive(pid)
    if alive is False:
        raise RuntimeError(f"M10P recovery lock PID is not alive: {pid}")

    metrics = summary.get("metrics", {})
    for key in ("candidate_match_count", "accepted_count", "resolved_count", "open_count", "entry_data_gap_count", "exit_data_gap_count"):
        if int(state.get(key, -1)) != int(metrics.get(key, -2)):
            raise RuntimeError(f"M10P post-recovery state/summary mismatch: {key}")
    if int(metrics.get("entry_data_gap_count", -1)) != 0 or int(metrics.get("exit_data_gap_count", -1)) != 0:
        raise RuntimeError("M10P post-recovery data gap detected")

    output_root = root / "outputs" / "M10P_RECOVERY_HEALTH"
    archive = output_root / "archive" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)
    result = {
        "project": PROJECT,
        "stage": STAGE,
        "status": "PASS_M10P_PRESERVED_START_RECOVERY_HEALTHY_RUNNING_AUDIT_ONLY",
        "built_at_utc": utc_text(),
        "preserved_start_server_time": EXPECTED_START,
        "process": {"pid": pid, "alive": alive, "lock_present": True},
        "loop_status": {
            "status": status.get("status"),
            "started_at_utc": status.get("started_at_utc"),
            "updated_at_utc": status.get("updated_at_utc"),
            "cycles": status.get("cycles"),
            "successful_cycles": status.get("successful_cycles"),
            "waiting_transient_cycles": status.get("waiting_transient_cycles"),
            "failed_terminal_cycles": status.get("failed_terminal_cycles"),
        },
        "metrics": metrics,
        "integrity": {
            "runtime_sha256": sha256_file(paths["runtime"]),
            "runtime_copy_sha256": sha256_file(paths["runtime_copy"]),
            "runtime_copy_exact_match": True,
            "runtime_or_start_modified": False,
            "historical_backfill_before_start": False,
            "entry_data_gap_count": metrics.get("entry_data_gap_count"),
            "exit_data_gap_count": metrics.get("exit_data_gap_count"),
        },
        "safety": {
            "BAT01_run": False,
            "runtime_reset": False,
            "start_reset": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        },
    }
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10P preserved-start recovery health audit. PASS means the original start is unchanged and the recovered loop is running after at least one successful deterministic post-start cycle.\n",
        encoding="utf-8",
    )
    (archive / "01_health_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for key, name in (
        ("runtime", "10_runtime_manifest.json"),
        ("state", "11_runtime_state.json"),
        ("start_receipt", "12_start_receipt.json"),
        ("lock", "13_loop_lock.json"),
        ("status", "14_loop_status.json"),
        ("summary", "15_latest_summary.json"),
        ("runtime_copy", "16_latest_runtime_copy.json"),
        ("trade", "17_latest_trade_ledger.csv"),
        ("recovery_preflight", "18_recovery_preflight.json"),
    ):
        shutil.copy2(paths[key], archive / name)
    package = archive / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(item for item in archive.iterdir() if item.is_file() and item.name != package.name):
            handle.write(path, path.name)
    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    print("[M10P RECOVERY HEALTH] PASS_M10P_PRESERVED_START_RECOVERY_HEALTHY_RUNNING_AUDIT_ONLY")
    print(f"[M10P RECOVERY HEALTH PACKAGE] {latest / package.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10P RECOVERY HEALTH BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] No loop, runtime, start, state, lock, journal, snapshot, Discord or MT5 order was changed.")
        raise SystemExit(2)
