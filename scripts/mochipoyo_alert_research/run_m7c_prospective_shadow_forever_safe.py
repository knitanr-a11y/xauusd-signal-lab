from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import default_local_root

SCRIPT_DIR = Path(__file__).resolve().parent
ONE_SHOT = SCRIPT_DIR / "build_m7c_prospective_shadow_once.py"
STOP_NAME = "STOP_M7C_SHADOW_LOOP"
LOCK_NAME = "m7c_shadow_loop.lock"


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


class ExclusiveLoopLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self) -> "ExclusiveLoopLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(
                f"M7C shadow loop lock already exists: {self.path}. "
                "Stop the existing M7C window or delete a confirmed stale lock."
            ) from exc
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                {
                    "pid": os.getpid(),
                    "started_at_utc": utc_now_text(),
                    "audit_only": True,
                    "entry_gate": False,
                    "discord_send": False,
                    "mt5_order": False,
                },
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
        self.acquired = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    m7c_dir = local / "logs" / "m7c"
    parser = argparse.ArgumentParser(
        description="Run the M7C prospective shadow audit with contract-block stop behavior."
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=local / "m7c_runtime" / "m7c_prospective_shadow_manifest_runtime.json",
    )
    parser.add_argument("--output-dir", type=Path, default=m7c_dir)
    parser.add_argument("--derived-output-dir", type=Path, default=local / "logs" / "derived")
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--stop-file", type=Path, default=local / STOP_NAME)
    parser.add_argument("--lock-file", type=Path, default=local / LOCK_NAME)
    parser.add_argument("--log", type=Path, default=m7c_dir / "m7c_shadow_forever.log")
    parser.add_argument(
        "--status", type=Path, default=m7c_dir / "latest_m7c_shadow_loop_status.json"
    )
    return parser.parse_args()


def run_cycle(args: argparse.Namespace, cycle_number: int) -> int:
    command = [
        sys.executable,
        str(ONE_SHOT),
        "--env",
        str(args.env),
        "--db",
        str(args.db),
        "--manifest",
        str(args.manifest),
        "--output-dir",
        str(args.output_dir),
        "--derived-output-dir",
        str(args.derived_output_dir),
        "--refresh-upstream-if-stale",
    ]
    started = utc_now_text()
    completed = subprocess.run(
        command,
        cwd=SCRIPT_DIR.parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    finished = utc_now_text()
    append_log(
        args.log,
        f"\n===== M7C cycle {cycle_number} | {started} -> {finished} "
        f"| exit={completed.returncode} =====\n",
    )
    if completed.stdout:
        append_log(args.log, completed.stdout)
        print(completed.stdout.rstrip())
    if completed.stderr:
        append_log(args.log, "[stderr]\n" + completed.stderr)
        print(completed.stderr.rstrip(), file=sys.stderr)
    return int(completed.returncode)


def sleep_until_next_cycle(stop_file: Path, interval_seconds: float) -> bool:
    deadline = time.monotonic() + interval_seconds
    while True:
        if stop_file.exists():
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(1.0, remaining))


def status_payload(
    args: argparse.Namespace,
    *,
    status: str,
    started_at: str,
    cycles: int,
    successful: int,
    failed: int,
    last_exit_code: int | None,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "stage": "M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY",
        "audit_only": True,
        "formula_refit": False,
        "historical_scan": False,
        "entry_gate": False,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
        "started_at_utc": started_at,
        "updated_at_utc": utc_now_text(),
        "interval_seconds": args.interval_seconds,
        "cycles": cycles,
        "successful_cycles": successful,
        "failed_cycles": failed,
        "last_exit_code": last_exit_code,
        "manifest_path": str(args.manifest),
        "output_dir": str(args.output_dir),
        "log_path": str(args.log),
        "stop_file": str(args.stop_file),
        "lock_file": str(args.lock_file),
    }
    if stop_reason is not None:
        payload["stop_reason"] = stop_reason
    return payload


def main() -> int:
    args = parse_args()
    if args.interval_seconds < 60 or args.interval_seconds > 3600:
        print("[ERROR] --interval-seconds must be between 60 and 3600.", file=sys.stderr)
        return 2
    if args.max_cycles < 0:
        print("[ERROR] --max-cycles must be non-negative.", file=sys.stderr)
        return 2
    for path, label in (
        (args.env, "local .env"),
        (args.db, "SQLite database"),
        (args.manifest, "runtime M7C manifest"),
        (ONE_SHOT, "M7C one-shot wrapper"),
    ):
        if not path.is_file():
            print(f"[ERROR] Missing {label}: {path}", file=sys.stderr)
            return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.derived_output_dir.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.status.parent.mkdir(parents=True, exist_ok=True)
    args.stop_file.unlink(missing_ok=True)

    cycles = successful = failed = 0
    last_exit_code: int | None = None
    stop_reason = "UNKNOWN"
    started_at = utc_now_text()

    try:
        with ExclusiveLoopLock(args.lock_file):
            print("=" * 64)
            print("Mochipoyo M7C prospective shadow loop - AUDIT ONLY")
            print(f"Runtime manifest: {args.manifest}")
            print(f"M7C folder      : {args.output_dir}")
            print("Contract exit 2 : STOP AND REQUIRE MANUAL REVIEW")
            print("Discord / MT5   : OFF")
            print("=" * 64)
            while True:
                if args.stop_file.exists():
                    stop_reason = "STOP_FILE"
                    break
                cycles += 1
                print(f"\n[M7C CYCLE {cycles}] {utc_now_text()}")
                last_exit_code = run_cycle(args, cycles)
                if last_exit_code == 0:
                    successful += 1
                else:
                    failed += 1

                if last_exit_code == 2:
                    stop_reason = "FAIL_CLOSED_CONTRACT_BLOCK"
                    atomic_write_json(
                        args.status,
                        status_payload(
                            args,
                            status="BLOCKED",
                            started_at=started_at,
                            cycles=cycles,
                            successful=successful,
                            failed=failed,
                            last_exit_code=last_exit_code,
                            stop_reason=stop_reason,
                        ),
                    )
                    print(
                        "[BLOCKED] M7C contract failed closed. The loop is stopping instead "
                        "of repeating the same invalid cycle.",
                        file=sys.stderr,
                    )
                    break

                atomic_write_json(
                    args.status,
                    status_payload(
                        args,
                        status="RUNNING",
                        started_at=started_at,
                        cycles=cycles,
                        successful=successful,
                        failed=failed,
                        last_exit_code=last_exit_code,
                    ),
                )
                if args.max_cycles and cycles >= args.max_cycles:
                    stop_reason = "MAX_CYCLES"
                    break
                if sleep_until_next_cycle(args.stop_file, args.interval_seconds):
                    stop_reason = "STOP_FILE"
                    break
    except KeyboardInterrupt:
        stop_reason = "CTRL_C"
        print("\n[STOP] Ctrl+C received.")
    except Exception as exc:
        stop_reason = "LOOP_ERROR"
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        if stop_reason != "FAIL_CLOSED_CONTRACT_BLOCK":
            try:
                atomic_write_json(
                    args.status,
                    status_payload(
                        args,
                        status="STOPPED",
                        started_at=started_at,
                        cycles=cycles,
                        successful=successful,
                        failed=failed,
                        last_exit_code=last_exit_code,
                        stop_reason=stop_reason,
                    ),
                )
            except Exception:
                pass

    print(
        f"[STOPPED] reason={stop_reason} cycles={cycles} "
        f"success={successful} failed={failed}"
    )
    return 0 if stop_reason != "LOOP_ERROR" else 1


if __name__ == "__main__":
    raise SystemExit(main())
