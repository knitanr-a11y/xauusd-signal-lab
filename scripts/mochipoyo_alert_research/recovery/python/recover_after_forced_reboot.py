from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TARGETS = (
    {
        "name": "collector",
        "process_marker": "run_collect_events_forever.py",
        "lock_rel": Path("collector_loop.lock"),
    },
    {
        "name": "M7C",
        "process_marker": "run_m7c_prospective_shadow_forever_safe.py",
        "lock_rel": Path("m7c_shadow_loop.lock"),
    },
    {
        "name": "M9V",
        "process_marker": "run_m9v_shadow_forever_safe",
        "lock_rel": Path("m9v_runtime") / "m9v_shadow_loop.lock",
    },
    {
        "name": "M9Y",
        "process_marker": "run_m9y_shadow_forever_safe.py",
        "lock_rel": Path("m9y_runtime") / "m9y_shadow_loop.lock",
    },
    {
        "name": "M10B",
        "process_marker": "m10b_runtime.py",
        "lock_rel": Path("m10b_runtime") / "m10b_shadow_loop.lock",
    },
    {
        "name": "M10E",
        "process_marker": "m10e_runtime.py",
        "lock_rel": Path("m10e_runtime") / "m10e_shadow_loop.lock",
    },
)


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def running_processes(marker: str) -> list[dict[str, Any]]:
    if os.name != "nt":
        raise RuntimeError("forced-reboot recovery is intended for the Windows operator environment")
    escaped = marker.replace("'", "''")
    script = (
        "$self=$PID; "
        "$rows=Get-CimInstance Win32_Process | Where-Object { "
        "$_.ProcessId -ne $self -and $_.CommandLine -and $_.CommandLine -like '*"
        + escaped
        + "*' }; "
        "$rows | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"process check failed for {marker}: {completed.stderr.strip()}")
    text = completed.stdout.strip()
    if not text:
        return []
    payload = json.loads(text)
    if isinstance(payload, dict):
        return [payload]
    return list(payload)


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        print("[RECOVERY BLOCKED] LOCALAPPDATA unavailable", file=sys.stderr)
        return 2
    root = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    archive = root / "reboot_recovery" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)
    actions: list[dict[str, Any]] = []

    try:
        # First verify that none of the protected loops is currently running.
        # This avoids ever deleting a live lock from an active monitor.
        running: dict[str, list[dict[str, Any]]] = {}
        for target in TARGETS:
            processes = running_processes(str(target["process_marker"]))
            if processes:
                running[str(target["name"])] = processes
        if running:
            (archive / "blocked_running_processes.json").write_text(
                json.dumps(running, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raise RuntimeError(
                "one or more protected loops are still running; recovery will not touch any lock: "
                + ", ".join(sorted(running))
            )

        for target in TARGETS:
            name = str(target["name"])
            lock = root / Path(target["lock_rel"])
            row: dict[str, Any] = {
                "name": name,
                "lock": str(lock),
                "lock_existed": lock.is_file(),
                "archived": False,
                "removed": False,
            }
            if lock.is_file():
                destination = archive / f"{name}_{lock.name}"
                shutil.copy2(lock, destination)
                row["archived"] = True
                row["archive_path"] = str(destination)
                lock.unlink()
                row["removed"] = True
            actions.append(row)

        receipt = {
            "status": "PASS_STALE_LOCK_RECOVERY_ONLY",
            "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "root": str(root),
            "actions": actions,
            "runtime_or_start_deleted": False,
            "runtime_or_start_reset": False,
            "database_deleted_or_reset": False,
            "m8c_modified": False,
            "m9v_modified_or_reset": False,
            "m9y_modified_or_reset": False,
            "m10b_modified_or_reset": False,
            "m10e_modified_or_reset": False,
            "next_restart_order": [
                "1) Ensure MT5 and the CSV-producing terminal/export are running and updating again.",
                "2) run_collect_events_cloudflare_forever.bat",
                "3) run_m7c_prospective_shadow_forever.bat",
                "4) m8c/bat/02_run_forward_shadow_forever.bat",
                "5) m9v/bat/03_run_shadow_forever.bat",
                "6) m9y/bat/03_run_shadow_forever.bat",
                "7) m10b/bat/03_run_shadow_forever.bat",
                "8) m10e/bat/03_run_shadow_forever.bat",
            ],
            "never_run_after_reboot": [
                "M7C initializer/runtime reset",
                "M8C initializer/runtime reset",
                "M9V BAT00/BAT01",
                "M9Y BAT01",
                "M10B BAT01",
                "M10E BAT01",
            ],
            "data_gap_note": "M10E, M10B, M9V and M9Y forward evidence is valid only for bars actually present in the restored MT5 raw CSVs. A permanent PC-off CSV gap is unobserved forward time and must never be silently counted or reconstructed from future outcomes.",
        }
        (archive / "recovery_receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("[REBOOT RECOVERY PASS] stale-lock audit/recovery completed")
        for row in actions:
            if row["removed"]:
                print(f"[RECOVERED] {row['name']}: archived and removed stale lock")
            else:
                print(f"[OK] {row['name']}: no stale lock present")
        print(f"[RECEIPT] {archive / 'recovery_receipt.json'}")
        print("[SAFE] No runtime manifest, prospective start, SQLite DB, M8C state, or output history was reset.")
        return 0
    except Exception as exc:
        print(f"[REBOOT RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Recovery did not intentionally reset any runtime/start/database.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
