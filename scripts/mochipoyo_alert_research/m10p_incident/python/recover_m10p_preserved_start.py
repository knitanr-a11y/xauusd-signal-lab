from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
MR = THIS.parents[2]
COMMON = MR / "common" / "python"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

import bounded_csv_source_adapter as adapter
import run_bounded_adapter_loop as base

PROJECT = "MOCHIPOYO_ALERT_RESEARCH"
STAGE = "M10P_PRESERVED_START_RECOVERY_AFTER_STATUS_PUBLICATION_RACE"
EXPECTED_START = "2026.07.24 23:56:00"
RECOVERY_VERSION = "M10P_PRESERVED_START_RECOVERY_V1_DELETE_SHARE_AND_STATUS_RETRY"


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


def process_inventory() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "$ErrorActionPreference='Stop'; "
        "$rows = Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match '(?i)run_bounded_adapter_loop(?:_v[0-9]+)?\\.py.*--loop\\s+M10P(?:\\s|$)' } | "
        "Select-Object ProcessId,Name,CreationDate,CommandLine; "
        "@($rows) | ConvertTo-Json -Depth 4 -Compress",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    if completed.returncode != 0:
        raise RuntimeError(f"M10P process inventory failed: {completed.stderr[-4000:]}")
    text = completed.stdout.strip()
    if not text:
        return []
    parsed = json.loads(text)
    return parsed if isinstance(parsed, list) else [parsed]


def is_windows_share_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) in {5, 32, 33}:
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(token in text for token in (
        "access is denied",
        "アクセスが拒否",
        "permissionerror",
        "sharing violation",
        "winerror 5",
        "winerror 32",
        "winerror 33",
    ))


def robust_status_atomic_json(path: Path, payload: Any) -> None:
    """Publish operational status without terminating a research loop on a reader race.

    The dashboard now uses FILE_SHARE_DELETE, but this retry also protects against
    antivirus/indexer handles. Only status telemetry uses this patched function.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    deadline = time.monotonic() + 15.0
    last_error: BaseException | None = None
    while True:
        try:
            os.replace(temporary, path)
            return
        except Exception as exc:
            if not is_windows_share_error(exc):
                temporary.unlink(missing_ok=True)
                raise
            last_error = exc
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
    temporary.unlink(missing_ok=True)
    print(
        f"[M10P STATUS WARNING] publication skipped after retry; loop remains alive: "
        f"{type(last_error).__name__}: {last_error}",
        file=sys.stderr,
    )


def verify_and_record(root: Path) -> Path:
    runtime = root / "m10p_runtime" / "m10p_runtime_manifest.json"
    state = root / "m10p_runtime" / "m10p_runtime_state.json"
    receipt = root / "m10p_runtime" / "m10p_runtime_start_receipt.json"
    lock = root / "m10p_runtime" / "m10p_shadow_loop.lock"
    status = root / "logs" / "m10p" / "latest_m10p_shadow_loop_status.json"
    summary = root / "outputs" / "M10P" / "LATEST" / "01_summary.json"
    runtime_copy = root / "outputs" / "M10P" / "LATEST" / "05_runtime_manifest_copy.json"
    trade = root / "outputs" / "M10P" / "LATEST" / "03_trade_ledger.csv"

    required = (runtime, state, receipt, status, summary, runtime_copy, trade)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"required M10P recovery evidence missing: {missing}")
    if lock.exists():
        raise RuntimeError("M10P lock exists; recovery must not start a second process")

    processes = process_inventory()
    if processes:
        raise RuntimeError(f"existing M10P bounded loop process found: {processes}")

    runtime_payload = load_json(runtime)
    state_payload = load_json(state)
    receipt_payload = load_json(receipt)
    status_payload = load_json(status)
    summary_payload = load_json(summary)

    starts = {
        "adapter_expected": adapter.EXPECTED_STARTS.get("M10P"),
        "runtime": runtime_payload.get("prospective_start_server_time"),
        "state": state_payload.get("prospective_start_server_time"),
        "start_receipt": receipt_payload.get("prospective_start_server_time"),
        "loop_status": status_payload.get("prospective_start_server_time"),
        "latest_summary": summary_payload.get("prospective_start_server_time"),
    }
    if set(starts.values()) != {EXPECTED_START}:
        raise RuntimeError(f"M10P preserved start mismatch: {starts}")

    if runtime.read_bytes() != runtime_copy.read_bytes():
        raise RuntimeError("M10P runtime differs from LATEST runtime copy")
    if runtime_payload.get("stage") != "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW":
        raise RuntimeError("unexpected M10P runtime stage")
    if runtime_payload.get("runtime_status") != "FROZEN_FRESH_START":
        raise RuntimeError("M10P runtime is not frozen fresh start")
    if runtime_payload.get("audit_only") is not True:
        raise RuntimeError("M10P runtime is not audit-only")
    if runtime_payload.get("reset_allowed") is not False or runtime_payload.get("historical_backfill_allowed") is not False:
        raise RuntimeError("unsafe M10P runtime flags")
    if receipt_payload.get("status") != "PASS" or receipt_payload.get("reset_allowed") is not False:
        raise RuntimeError("M10P start receipt integrity failed")
    if state_payload.get("status") != "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY":
        raise RuntimeError("M10P state was not a successful research cycle")
    if summary_payload.get("status") != "PASS_FRESH_PROSPECTIVE_AUDIT_ONLY":
        raise RuntimeError("M10P LATEST summary was not PASS")

    metrics = summary_payload.get("metrics", {})
    for key in ("candidate_match_count", "accepted_count", "resolved_count", "open_count", "entry_data_gap_count", "exit_data_gap_count"):
        if int(state_payload.get(key, -1)) != int(metrics.get(key, -2)):
            raise RuntimeError(f"M10P state/summary count mismatch: {key}")
    if int(metrics.get("entry_data_gap_count", -1)) != 0 or int(metrics.get("exit_data_gap_count", -1)) != 0:
        raise RuntimeError("M10P data gap exists at recovery preflight")

    last_error = str(status_payload.get("last_error", ""))
    if status_payload.get("status") != "BLOCKED":
        raise RuntimeError("M10P incident status is not BLOCKED")
    required_error_tokens = (
        "PermissionError",
        "WinError 5",
        "latest_m10p_shadow_loop_status.json.tmp",
        "os.replace",
    )
    if not all(token in last_error for token in required_error_tokens):
        raise RuntimeError("M10P stop cause is not the reviewed status-publication race")
    if int(status_payload.get("successful_cycles", 0)) < 1:
        raise RuntimeError("M10P has no successful pre-incident cycles")
    if status_payload.get("runtime_or_start_modified") is not False:
        raise RuntimeError("M10P blocked status reports runtime/start modification")

    output_root = root / "outputs" / "M10P_PRESERVED_START_RECOVERY"
    archive = output_root / "archive" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)
    preflight = {
        "project": PROJECT,
        "stage": STAGE,
        "status": "PASS_PRESERVED_START_RECOVERY_PREFLIGHT_AUTHORIZED",
        "recovery_version": RECOVERY_VERSION,
        "built_at_utc": utc_text(),
        "preserved_start_server_time": EXPECTED_START,
        "starts_verified": starts,
        "incident": {
            "classification": "OPERATIONAL_STATUS_PUBLICATION_RACE_NOT_RESEARCH_FAILURE",
            "status_before_recovery": status_payload.get("status"),
            "successful_cycles_before_stop": status_payload.get("successful_cycles"),
            "failed_terminal_cycles_before_stop": status_payload.get("failed_terminal_cycles"),
            "last_error": last_error,
        },
        "latest_metrics_before_recovery": metrics,
        "integrity": {
            "runtime_sha256": sha256_file(runtime),
            "latest_runtime_copy_sha256": sha256_file(runtime_copy),
            "runtime_copy_exact_match": True,
            "lock_absent": True,
            "existing_m10p_bounded_process_count": 0,
            "runtime_or_start_modified": False,
            "historical_backfill_before_start": False,
        },
        "recovery_policy": {
            "initializer_run": False,
            "BAT01_run": False,
            "preserve_existing_runtime_state_and_start": True,
            "deterministic_post_start_rebuild": True,
            "status_publication_retry_seconds": 15,
            "status_publication_failure_does_not_terminate_research_loop": True,
            "dashboard_windows_FILE_SHARE_DELETE_required": True,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        },
    }
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10P preserved-start recovery preflight. The immutable 2026.07.24 23:56:00 start, runtime, state and evidence were verified. BAT01 was not used. This recovery only restarts the stopped operational loop after a status JSON publication race.\n",
        encoding="utf-8",
    )
    (archive / "01_recovery_preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for source, name in (
        (runtime, "10_runtime_manifest_before_recovery.json"),
        (state, "11_runtime_state_before_recovery.json"),
        (receipt, "12_start_receipt.json"),
        (status, "13_blocked_loop_status.json"),
        (summary, "14_latest_summary_before_recovery.json"),
        (runtime_copy, "15_latest_runtime_copy.json"),
        (trade, "16_latest_trade_ledger_before_recovery.csv"),
    ):
        shutil.copy2(source, archive / name)
    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)
    return latest


def main() -> int:
    root = local_root()
    latest = verify_and_record(root)
    print(f"[M10P RECOVERY PREFLIGHT PASS] preserved start={EXPECTED_START}")
    print(f"[M10P RECOVERY EVIDENCE] {latest}")
    print("[M10P RECOVERY] starting preserved-start bounded loop; BAT01 was not used")

    base.atomic_json = robust_status_atomic_json
    base.TRANSIENT_TOKENS = tuple(base.TRANSIENT_TOKENS) + (
        "access is denied",
        "アクセスが拒否",
        "winerror 5",
    )
    sys.argv = [
        str(THIS),
        "--loop",
        "M10P",
        "--interval-seconds",
        "60",
        "--compat-process-marker",
        RECOVERY_VERSION,
    ]
    return base.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[M10P RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] M10P runtime/start/state/evidence and the other eight loops were not changed.", file=sys.stderr)
        raise SystemExit(2)
