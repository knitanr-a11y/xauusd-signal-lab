from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGE = "FRESH_LOOP_MASS_STOP_DIAGNOSTIC_AUDIT_ONLY"

TARGETS = (
    {
        "name": "M9V",
        "process_marker": "run_m9v_shadow_forever_safe",
        "lock_rel": Path("m9v_runtime") / "m9v_shadow_loop.lock",
        "runtime_rel": Path("m9v_runtime") / "m9v_runtime_manifest.json",
        "state_rel": None,
        "status_rel": Path("logs") / "m9v" / "latest_m9v_shadow_loop_status.json",
        "log_rel": Path("logs") / "m9v" / "m9v_shadow_forever.log",
        "output_summary_rel": Path("outputs") / "M9V" / "LATEST" / "01_summary.json",
    },
    {
        "name": "M9Y",
        "process_marker": "run_m9y_shadow_forever_safe.py",
        "lock_rel": Path("m9y_runtime") / "m9y_shadow_loop.lock",
        "runtime_rel": Path("m9y_runtime") / "m9y_runtime_manifest.json",
        "state_rel": None,
        "status_rel": Path("logs") / "m9y" / "latest_m9y_shadow_loop_status.json",
        "log_rel": Path("logs") / "m9y" / "m9y_shadow_forever.log",
        "output_summary_rel": Path("outputs") / "M9Y" / "LATEST" / "01_summary.json",
    },
    {
        "name": "M10B",
        "process_marker": "m10b_runtime.py",
        "lock_rel": Path("m10b_runtime") / "m10b_shadow_loop.lock",
        "runtime_rel": Path("m10b_runtime") / "m10b_runtime_manifest.json",
        "state_rel": None,
        "status_rel": None,
        "log_rel": None,
        "output_summary_rel": Path("outputs") / "M10B" / "LATEST" / "01_summary.json",
    },
    {
        "name": "M10E",
        "process_marker": "m10e_runtime.py",
        "lock_rel": Path("m10e_runtime") / "m10e_shadow_loop.lock",
        "runtime_rel": Path("m10e_runtime") / "m10e_runtime_manifest.json",
        "state_rel": None,
        "status_rel": None,
        "log_rel": None,
        "output_summary_rel": Path("outputs") / "M10E" / "LATEST" / "01_summary.json",
    },
    {
        "name": "M10P",
        "process_marker": "m10p_guarded_runtime.py",
        "lock_rel": Path("m10p_runtime") / "m10p_shadow_loop.lock",
        "runtime_rel": Path("m10p_runtime") / "m10p_runtime_manifest.json",
        "state_rel": Path("m10p_runtime") / "m10p_runtime_state.json",
        "status_rel": None,
        "log_rel": None,
        "output_summary_rel": Path("outputs") / "M10P" / "LATEST" / "01_summary.json",
    },
    {
        "name": "M10P2",
        "process_marker": "m10p2_guarded_runtime.py",
        "lock_rel": Path("m10p2_runtime") / "m10p2_shadow_loop.lock",
        "runtime_rel": Path("m10p2_runtime") / "m10p2_runtime_manifest.json",
        "state_rel": Path("m10p2_runtime") / "m10p2_runtime_state.json",
        "status_rel": None,
        "log_rel": None,
        "output_summary_rel": Path("outputs") / "M10P2" / "LATEST" / "01_summary.json",
    },
    {
        "name": "M10W19",
        "process_marker": "m10w19_runtime.py",
        "lock_rel": Path("m10w19_runtime") / "m10w19_shadow_loop.lock",
        "runtime_rel": Path("m10w19_runtime") / "m10w19_runtime_manifest.json",
        "state_rel": Path("m10w19_runtime") / "m10w19_runtime_state.json",
        "status_rel": None,
        "log_rel": None,
        "output_summary_rel": Path("outputs") / "M10W19" / "LATEST" / "01_summary.json",
    },
)

GOLD_FILES = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def load_json_safe(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"_non_object": True}
    except Exception as exc:
        return {"_read_error": f"{type(exc).__name__}: {exc}"}


def file_info(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return row
    stat = path.stat()
    row.update(
        {
            "size_bytes": stat.st_size,
            "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    return row


def tail_lines(path: Path, count: int = 120) -> list[str]:
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.readlines()[-count:]
    except Exception as exc:
        return [f"[TAIL READ ERROR] {type(exc).__name__}: {exc}\n"]


def running_processes(marker: str) -> list[dict[str, Any]]:
    if os.name != "nt":
        raise RuntimeError("This diagnostic is intended for the Windows operator environment.")
    escaped = marker.replace("'", "''")
    ps = (
        "$self=$PID; "
        "$rows=Get-CimInstance Win32_Process | Where-Object { "
        "$_.ProcessId -ne $self -and $_.CommandLine -and $_.CommandLine -like '*"
        + escaped
        + "*' }; "
        "$rows | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
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
    return [payload] if isinstance(payload, dict) else list(payload)


def last_csv_row(path: Path) -> dict[str, Any]:
    info = file_info(path)
    if not path.is_file():
        return info
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            buffer = bytearray()
            while position > 0 and len(buffer) < 65536:
                position -= 1
                handle.seek(position)
                byte = handle.read(1)
                if byte == b"\n" and buffer:
                    break
                if byte not in (b"\r", b"\n"):
                    buffer.extend(byte)
            line = bytes(reversed(buffer)).decode("utf-8-sig", errors="replace").strip()
        fields = next(csv.reader([line])) if line else []
        info["last_row_text"] = line
        info["last_server_open"] = fields[0].strip() if fields else None
    except Exception as exc:
        info["last_row_error"] = f"{type(exc).__name__}: {exc}"
    return info


def classify(processes: list[dict[str, Any]], lock_exists: bool, runtime_exists: bool) -> str:
    if processes:
        return "RUNNING"
    if not runtime_exists:
        return "STOPPED_RUNTIME_MISSING"
    if lock_exists:
        return "STOPPED_STALE_LOCK_POSSIBLE"
    return "STOPPED_NO_LOCK"


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        print("[DIAGNOSTIC BLOCKED] LOCALAPPDATA unavailable", file=sys.stderr)
        return 2

    root = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = root / "outputs" / "FRESH_LOOP_DIAGNOSTIC"
    archive = output_root / "archive" / utc_stamp()
    archive.mkdir(parents=True, exist_ok=False)

    summary: dict[str, Any] = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_READ_ONLY_DIAGNOSTIC",
        "built_at_utc": utc_text(),
        "root": str(root),
        "mutations_performed": False,
        "locks_removed": False,
        "processes_started_or_stopped": False,
        "runtime_or_start_modified": False,
        "loops": {},
        "feed": {},
    }

    log_files: list[str] = []
    try:
        for target in TARGETS:
            name = str(target["name"])
            processes = running_processes(str(target["process_marker"]))
            lock = root / Path(target["lock_rel"])
            runtime = root / Path(target["runtime_rel"])
            state = root / Path(target["state_rel"]) if target["state_rel"] else None
            status = root / Path(target["status_rel"]) if target["status_rel"] else None
            logfile = root / Path(target["log_rel"]) if target["log_rel"] else None
            output_summary = root / Path(target["output_summary_rel"])

            runtime_payload = load_json_safe(runtime) if runtime.is_file() else None
            state_payload = load_json_safe(state) if state and state.is_file() else None
            status_payload = load_json_safe(status) if status and status.is_file() else None
            output_payload = load_json_safe(output_summary) if output_summary.is_file() else None

            row = {
                "classification": classify(processes, lock.is_file(), runtime.is_file()),
                "process_marker": target["process_marker"],
                "processes": processes,
                "lock": {**file_info(lock), "content": load_json_safe(lock) if lock.is_file() else None},
                "runtime": {**file_info(runtime), "selected": {
                    "stage": (runtime_payload or {}).get("stage"),
                    "runtime_status": (runtime_payload or {}).get("runtime_status"),
                    "prospective_start_server_time": (runtime_payload or {}).get("prospective_start_server_time"),
                    "reset_allowed": (runtime_payload or {}).get("reset_allowed"),
                    "historical_backfill_allowed": (runtime_payload or {}).get("historical_backfill_allowed"),
                }},
                "state": None if state is None else {**file_info(state), "payload": state_payload},
                "status": None if status is None else {**file_info(status), "payload": status_payload},
                "latest_output_summary": {**file_info(output_summary), "selected": {
                    "stage": (output_payload or {}).get("stage"),
                    "status": (output_payload or {}).get("status"),
                    "built_at_utc": (output_payload or {}).get("built_at_utc"),
                    "prospective_start_server_time": (output_payload or {}).get("prospective_start_server_time"),
                    "latest_server_open": (output_payload or {}).get("latest_server_open"),
                }},
            }

            if logfile is not None:
                log_name = f"{name}_log_tail.txt"
                (archive / log_name).write_text("".join(tail_lines(logfile)), encoding="utf-8")
                row["log"] = file_info(logfile)
                row["log_tail_file"] = log_name
                log_files.append(log_name)
            summary["loops"][name] = row

        metadata_path = root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
        metadata = load_json_safe(metadata_path) if metadata_path.is_file() else None
        data_root_text = str((metadata or {}).get("mt5_files_root", "") or "")
        data_root = Path(data_root_text) if data_root_text else None
        summary["feed"]["metadata"] = {**file_info(metadata_path), "mt5_files_root": data_root_text}
        if data_root is not None:
            summary["feed"]["data_root_exists"] = data_root.is_dir()
            summary["feed"]["files"] = {
                tf: last_csv_row(data_root / filename) for tf, filename in GOLD_FILES.items()
            }

        counts: dict[str, int] = {}
        for row in summary["loops"].values():
            key = str(row["classification"])
            counts[key] = counts.get(key, 0) + 1
        summary["classification_counts"] = counts
        summary["interpretation"] = {
            "STOPPED_STALE_LOCK_POSSIBLE": "No matching loop process was found but a lock remains. Use the existing forced-reboot recovery BAT; never delete manually.",
            "STOPPED_NO_LOCK": "The process exited and its finally block removed the lock. Inspect status/log/output timestamps for the cycle error.",
            "RUNNING": "A matching process command line is currently present.",
            "diagnostic_only": True,
        }

        (archive / "00_READ_ME_FIRST.txt").write_text(
            "Read-only diagnostic for stopped M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19 loops. "
            "No lock, runtime manifest, start, state, output, process, MT5 file or monitor was modified.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (archive / "02_audit.log").write_text(
            "\n".join(
                [
                    "status=PASS_READ_ONLY_DIAGNOSTIC",
                    *(f"{name}={row['classification']}" for name, row in summary["loops"].items()),
                    f"classification_counts={json.dumps(counts, ensure_ascii=False, sort_keys=True)}",
                    "mutations_performed=false",
                    "locks_removed=false",
                    "processes_started_or_stopped=false",
                    "runtime_or_start_modified=false",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        import shutil
        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_audit.log", *log_files]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        print("[FRESH LOOP DIAGNOSTIC PASS]")
        for name, row in summary["loops"].items():
            print(f"  {name}: {row['classification']}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        (archive / "diagnostic_error.txt").write_text(
            f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
        )
        print(f"[DIAGNOSTIC BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No loop, lock, runtime, start or state was intentionally modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
