from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

PROJECT = "MOCHIPOYO_ALERT_RESEARCH"
STAGE = "ALL_LOOP_STOP_DIAGNOSTIC_READ_ONLY"
TARGET_NAMES = (
    "M7C",
    "M8C",
    "M8P",
    "M9V",
    "M9Y",
    "M10B",
    "M10E",
    "M10P",
    "M10P2",
    "M10W19",
    "M10W26",
    "M10W34",
)
MAX_TAIL_BYTES = 300_000
MAX_INVENTORY_FILES_PER_DIR = 300


def utc_now_text() -> str:
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


def file_info(path: Path, *, hash_file: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    stat = path.stat()
    result: dict[str, Any] = {
        "exists": True,
        "path": str(path),
        "is_file": path.is_file(),
        "size_bytes": stat.st_size,
        "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if hash_file and path.is_file():
        try:
            result["sha256"] = sha256_file(path)
        except Exception as exc:
            result["sha256_error"] = f"{type(exc).__name__}: {exc}"
    return result


def parse_pid(payload: dict[str, Any] | None) -> int | None:
    try:
        value = int((payload or {}).get("pid"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def process_alive(pid: int | None) -> bool | None:
    if pid is None or pid <= 0 or os.name != "nt":
        return None
    access = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(access, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return ctypes.windll.kernel32.GetLastError() == 5


def safe_tail(path: Path, max_bytes: int = MAX_TAIL_BYTES) -> str:
    if not path.is_file():
        return f"MISSING: {path}\n"
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
            data = handle.read()
        return data.decode("utf-8", errors="replace")
    except Exception as exc:
        return f"READ_ERROR {type(exc).__name__}: {exc}\nPATH: {path}\n"


def powershell_json(script: str, timeout: int = 45) -> dict[str, Any]:
    if os.name != "nt":
        return {"status": "NOT_WINDOWS"}
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except Exception as exc:
        return {"status": "QUERY_FAILED", "error": f"{type(exc).__name__}: {exc}"}
    if completed.returncode != 0:
        return {
            "status": "QUERY_FAILED",
            "returncode": completed.returncode,
            "stderr": completed.stderr[-12000:],
        }
    text = completed.stdout.strip()
    if not text:
        return {"status": "PASS", "rows": []}
    try:
        return {"status": "PASS", "data": json.loads(text)}
    except Exception as exc:
        return {
            "status": "PARSE_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
            "raw": text[-20000:],
        }


def process_inventory() -> dict[str, Any]:
    own_pid = os.getpid()
    pattern = "(?i)(mochipoyo_alert_research|m7c|m8c|m8p|m9v|m9y|m10b|m10e|m10p|m10w19|m10w26|m10w34)"
    script = (
        "$ErrorActionPreference='Stop'; "
        f"$own={own_pid}; "
        f"$pattern='{pattern}'; "
        "$rows=Get-CimInstance Win32_Process | "
        "Where-Object { $_.ProcessId -ne $own -and $_.CommandLine -and "
        "$_.CommandLine -match $pattern -and $_.CommandLine -notmatch 'collect_all_loop_stop_diagnostic' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine; "
        "@($rows) | ConvertTo-Json -Depth 5 -Compress"
    )
    return powershell_json(script)


def system_inventory() -> dict[str, Any]:
    script = (
        "$ErrorActionPreference='Stop'; "
        "$os=Get-CimInstance Win32_OperatingSystem | "
        "Select-Object CSName,Caption,Version,LastBootUpTime,LocalDateTime; "
        "$cs=Get-CimInstance Win32_ComputerSystem | "
        "Select-Object Name,UserName,TotalPhysicalMemory; "
        "[pscustomobject]@{OperatingSystem=$os;ComputerSystem=$cs} | "
        "ConvertTo-Json -Depth 5 -Compress"
    )
    return powershell_json(script)


def iter_files(directory: Path) -> Iterable[Path]:
    if not directory.is_dir():
        return ()
    files: list[Path] = []
    try:
        for path in directory.rglob("*"):
            if path.is_file():
                files.append(path)
                if len(files) >= MAX_INVENTORY_FILES_PER_DIR:
                    break
    except Exception:
        pass
    return files


def status_candidates(root: Path, name: str) -> list[Path]:
    lower = name.lower()
    candidates = [
        root / "logs" / lower / f"latest_{lower}_shadow_loop_status.json",
        root / "logs" / lower / f"latest_{lower}_loop_status.json",
        root / "logs" / lower / "latest_loop_status.json",
    ]
    log_dir = root / "logs" / lower
    if log_dir.is_dir():
        candidates.extend(sorted(log_dir.glob("latest*status*.json")))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def lock_candidates(root: Path, name: str) -> list[Path]:
    lower = name.lower()
    runtime_dir = root / f"{lower}_runtime"
    candidates = [
        runtime_dir / f"{lower}_shadow_loop.lock",
        runtime_dir / f"{lower}_loop.lock",
    ]
    if runtime_dir.is_dir():
        candidates.extend(sorted(runtime_dir.glob("*.lock")))
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def best_existing(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.is_file()]
    if not existing:
        return None
    return max(existing, key=lambda item: item.stat().st_mtime)


def copy_small_text(source: Path, destination: Path, max_bytes: int = 2_000_000) -> bool:
    if not source.is_file():
        return False
    try:
        if source.stat().st_size > max_bytes:
            destination.write_text(safe_tail(source), encoding="utf-8")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return True
    except Exception:
        return False


def loop_observation(root: Path, name: str, evidence_dir: Path) -> dict[str, Any]:
    lower = name.lower()
    output_latest = root / "outputs" / name / "LATEST"
    runtime_dir = root / f"{lower}_runtime"
    log_dir = root / "logs" / lower

    statuses = status_candidates(root, name)
    locks = lock_candidates(root, name)
    status_path = best_existing(statuses)
    lock_path = best_existing(locks)
    status_payload, status_error = read_json(status_path) if status_path else (None, "MISSING")
    lock_payload, lock_error = read_json(lock_path) if lock_path else (None, "MISSING")
    pid = parse_pid(status_payload) or parse_pid(lock_payload)

    summary_paths = [
        output_latest / "01_summary.json",
        output_latest / "summary.json",
    ]
    summary_path = best_existing(summary_paths)
    summary_payload, summary_error = read_json(summary_path) if summary_path else (None, "MISSING")

    observation: dict[str, Any] = {
        "name": name,
        "status_path": str(status_path) if status_path else None,
        "status": status_payload,
        "status_error": status_error,
        "lock_path": str(lock_path) if lock_path else None,
        "lock": lock_payload,
        "lock_error": lock_error,
        "pid": pid,
        "pid_alive": process_alive(pid),
        "summary_path": str(summary_path) if summary_path else None,
        "summary": summary_payload,
        "summary_error": summary_error,
        "directories": {
            "log_dir": file_info(log_dir),
            "runtime_dir": file_info(runtime_dir),
            "output_latest": file_info(output_latest),
        },
        "file_inventory": {},
    }

    loop_evidence = evidence_dir / name
    loop_evidence.mkdir(parents=True, exist_ok=True)

    if status_path:
        copy_small_text(status_path, loop_evidence / "01_status.json")
    if lock_path:
        copy_small_text(lock_path, loop_evidence / "02_lock.json")
    if summary_path:
        copy_small_text(summary_path, loop_evidence / "03_summary.json")

    inventory_dirs = {
        "logs": log_dir,
        "runtime": runtime_dir,
        "latest": output_latest,
    }
    for label, directory in inventory_dirs.items():
        rows: list[dict[str, Any]] = []
        for path in iter_files(directory):
            rows.append(file_info(path, hash_file=path.suffix.lower() in {".json", ".lock"}))
        observation["file_inventory"][label] = rows

    log_files: list[Path] = []
    if log_dir.is_dir():
        for pattern in ("*.log", "*.txt", "*.err", "*.out"):
            log_files.extend(log_dir.glob(pattern))
    if output_latest.is_dir():
        for pattern in ("*.log", "*.txt"):
            log_files.extend(output_latest.glob(pattern))
    unique_logs = sorted({path.resolve() for path in log_files if path.is_file()}, key=lambda item: item.stat().st_mtime, reverse=True)
    for index, path in enumerate(unique_logs[:8], start=1):
        destination = loop_evidence / f"log_tail_{index:02d}_{path.name}.txt"
        destination.write_text(f"SOURCE: {path}\n\n{safe_tail(path)}", encoding="utf-8")

    for index, path in enumerate(sorted(runtime_dir.glob("*.json"))[:20] if runtime_dir.is_dir() else (), start=1):
        copy_small_text(path, loop_evidence / f"runtime_{index:02d}_{path.name}")

    return observation


def root_discovery(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, directory in {
        "logs_children": root / "logs",
        "outputs_children": root / "outputs",
        "root_runtime_children": root,
    }.items():
        rows: list[dict[str, Any]] = []
        if directory.is_dir():
            try:
                for path in sorted(directory.iterdir()):
                    if label == "root_runtime_children" and not (path.is_dir() and path.name.lower().endswith("_runtime")):
                        continue
                    rows.append(file_info(path))
            except Exception as exc:
                rows.append({"error": f"{type(exc).__name__}: {exc}", "path": str(directory)})
        result[label] = rows

    discovered_status: list[dict[str, Any]] = []
    logs_root = root / "logs"
    if logs_root.is_dir():
        try:
            for path in sorted(logs_root.rglob("latest*status*.json"))[:300]:
                payload, error = read_json(path)
                discovered_status.append({"file": file_info(path, hash_file=True), "payload": payload, "error": error})
        except Exception as exc:
            discovered_status.append({"error": f"{type(exc).__name__}: {exc}"})
    result["discovered_status_files"] = discovered_status
    return result


def main() -> int:
    root = local_root()
    output_root = root / "outputs" / "ALL_LOOP_STOP_DIAGNOSTIC"
    archive = output_root / "archive" / utc_stamp()
    evidence_dir = archive / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=False)

    observations = [loop_observation(root, name, evidence_dir) for name in TARGET_NAMES]
    processes = process_inventory()
    system = system_inventory()
    discovery = root_discovery(root)

    summary = {
        "project": PROJECT,
        "stage": STAGE,
        "status": "PASS_DIAGNOSTIC_PACKAGE_CREATED_READ_ONLY",
        "built_at_utc": utc_now_text(),
        "reported_condition": "User reported M8P through M10W34 stopped",
        "local_root": str(root),
        "target_names": list(TARGET_NAMES),
        "loops": observations,
        "process_inventory": processes,
        "system_inventory": system,
        "root_discovery": discovery,
        "mutations": {
            "monitor_start_or_stop": False,
            "initializer_run": False,
            "runtime_state_start_write": False,
            "lock_write_or_delete": False,
            "journal_snapshot_csv_write": False,
            "source_output_write": False,
            "discord_send": False,
            "mt5_order": False,
            "diagnostic_output_only": True,
        },
    }

    (archive / "00_READ_ME_FIRST.txt").write_text(
        "All-loop stop diagnostic package. This collector only reads the local Mochipoyo research root and writes this separate diagnostic package. It does not start, stop, restart, initialize, reset, edit, delete, tune, notify, or place orders. Do not run any initializer or recovery BAT until this package is reviewed.\n",
        encoding="utf-8",
    )
    (archive / "01_diagnostic_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (archive / "02_process_inventory.json").write_text(
        json.dumps(processes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (archive / "03_system_inventory.json").write_text(
        json.dumps(system, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (archive / "04_root_discovery.json").write_text(
        json.dumps(discovery, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    package = archive / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(item for item in archive.rglob("*") if item.is_file() and item != package):
            handle.write(path, path.relative_to(archive))

    latest = output_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    stopped_like = []
    for item in observations:
        status = str((item.get("status") or {}).get("status", item.get("status_error") or "UNKNOWN"))
        if status != "RUNNING" or item.get("pid_alive") is False:
            stopped_like.append(item["name"])

    print("[ALL LOOP DIAGNOSTIC PASS] read-only package created")
    print(f"[ALL LOOP DIAGNOSTIC OBSERVED] stopped_or_unknown={','.join(stopped_like) if stopped_like else 'none'}")
    print(f"[ALL LOOP DIAGNOSTIC PACKAGE] {latest / '99_UPLOAD_PACKAGE.zip'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ALL LOOP DIAGNOSTIC BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No monitor, runtime, start, lock, journal, snapshot, CSV, Discord, or MT5 order was changed.", file=sys.stderr)
        raise SystemExit(2)
