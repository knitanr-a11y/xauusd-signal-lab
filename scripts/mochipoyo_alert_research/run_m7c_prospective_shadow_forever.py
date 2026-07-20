from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import default_local_root


SCRIPT_DIR = Path(__file__).resolve().parent
STATUS_NAME = "latest_m7c_shadow_loop_status.json"
LOG_NAME = "m7c_shadow_forever.log"
STOP_NAME = "STOP_M7C_SHADOW_LOOP"
LOCK_NAME = "m7c_shadow_loop.lock"
ONE_SHOT = SCRIPT_DIR / "build_m7c_prospective_shadow_once.py"


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
                "Do not start a second M7C monitor. If no M7C window is running, "
                "delete the stale lock manually."
            ) from exc
        payload = {
            "pid": os.getpid(),
            "started_at_utc": utc_now_text(),
            "audit_only": True,
            "entry_gate": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        }
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        self.acquired = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.acquired:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self.acquired = False


def parse_args() -> argparse.Namespace:
    local = default_local_root()
    parser = argparse.ArgumentParser(
        description="Run the M7C prospective shadow audit repeatedly."
    )
    parser.add_argument("--env", type=Path, default=local / ".env")
    parser.add_argument("--db", type=Path, default=local / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--interval-seconds", type=float, default=300.0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--stop-file", type=Path, default=local / STOP_NAME)
    parser.add_argument("--lock-file", type=Path, default=local / LOCK_NAME)
    parser.add_argument("--log", type=Path, default=local / "logs" / LOG_NAME)
    parser.add_argument("--status", type=Path, default=local / "logs" / STATUS_NAME)
    return parser.parse_args()


def run_cycle(args: argparse.Namespace, cycle_number: int) -> int:
    command = [
        sys.executable,
        str(ONE_SHOT),
        "--env",
        str(args.env),
        "--db",
        str(args.db),
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


def main() -> int:
    args = parse_args()
    if args.interval_seconds < 60 or args.interval_seconds > 3600:
        print("[ERROR] --interval-seconds must be between 60 and 3600.")
        return 2
    if args.max_cycles < 0:
        print("[ERROR] --max-cycles must be non-negative.")
        return 2
    if not args.env.is_file():
        print(f"[ERROR] Local Mochipoyo .env was not found: {args.env}")
        return 2
    if not args.db.is_file():
        print(f"[ERROR] Mochipoyo SQLite database was not found: {args.db}")
        return 2
    if not ONE_SHOT.is_file():
        print(f"[ERROR] M7C one-shot wrapper was not found: {ONE_SHOT}")
        return 2

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.status.parent.mkdir(parents=True, exist_ok=True)
    if args.stop_file.exists():
        args.stop_file.unlink()

    cycles = successful = failed = 0
    last_exit_code: int | None = None
    stop_reason = "UNKNOWN"
    started_at = utc_now_text()

    try:
        with ExclusiveLoopLock(args.lock_file):
            print("=" * 60)
            print("Mochipoyo M7C prospective shadow loop - AUDIT ONLY")
            print(f"Interval       : {args.interval_seconds:g} seconds")
            print("Collector      : SEPARATE EXISTING COLLECTOR MUST REMAIN RUNNING")
            print("Formula refit  : OFF")
            print("Historical scan: OFF")
            print("Entry gate     : OFF")
            print("Discord send   : OFF")
            print("MT5 orders     : OFF")
            print("Live ready     : OFF")
            print("Final signal   : OFF")
            print("=" * 60)

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
                    print(
                        "[WARN] M7C audit cycle failed closed. The loop will continue "
                        "without changing the frozen formula.",
                        file=sys.stderr,
                    )

                atomic_write_json(
                    args.status,
                    {
                        "status": "RUNNING",
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
                        "stop_file": str(args.stop_file),
                        "lock_file": str(args.lock_file),
                        "log_path": str(args.log),
                    },
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
        try:
            atomic_write_json(
                args.status,
                {
                    "status": "STOPPED",
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
                    "stopped_at_utc": utc_now_text(),
                    "stop_reason": stop_reason,
                    "cycles": cycles,
                    "successful_cycles": successful,
                    "failed_cycles": failed,
                    "last_exit_code": last_exit_code,
                    "log_path": str(args.log),
                },
            )
        except Exception:
            pass

    print(
        f"[STOPPED] reason={stop_reason} cycles={cycles} "
        f"success={successful} failed={failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
