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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from mochipoyo_alert_research.config import default_local_root  # noqa: E402

STATUS_NAME = "latest_loop_status.json"
LOG_NAME = "collector_forever.log"
STOP_NAME = "STOP_COLLECTOR_LOOP"
LOCK_NAME = "collector_loop.lock"


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
            descriptor = os.open(
                self.path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise RuntimeError(
                f"collector loop lock already exists: {self.path}. "
                "Do not start a second collector. If no collector window is running, "
                "delete the stale lock manually."
            ) from exc
        payload = {
            "pid": os.getpid(),
            "started_at_utc": utc_now_text(),
            "audit_only": True,
            "discord_send": False,
            "mt5_order": False,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    local_root = default_local_root()
    parser = argparse.ArgumentParser(
        description="Run the Mochipoyo read-only Cloudflare collector repeatedly."
    )
    parser.add_argument("--env", type=Path, default=local_root / ".env")
    parser.add_argument("--db", type=Path, default=local_root / "mochipoyo_alerts.sqlite3")
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="0 means run until STOP_COLLECTOR_LOOP or Ctrl+C.",
    )
    parser.add_argument("--stop-file", type=Path, default=local_root / STOP_NAME)
    parser.add_argument("--lock-file", type=Path, default=local_root / LOCK_NAME)
    parser.add_argument("--log", type=Path, default=local_root / "logs" / LOG_NAME)
    parser.add_argument(
        "--status",
        type=Path,
        default=local_root / "logs" / STATUS_NAME,
    )
    parser.add_argument(
        "--collector-script",
        type=Path,
        default=SCRIPT_DIR / "collect_events_once.py",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if args.interval_seconds < 1.0 or args.interval_seconds > 3600.0:
        raise ValueError("--interval-seconds must be between 1 and 3600")
    if args.limit < 1 or args.limit > 5000:
        raise ValueError("--limit must be between 1 and 5000")
    if args.max_cycles < 0:
        raise ValueError("--max-cycles must be non-negative")
    if not args.env.is_file():
        raise ValueError(f"local Cloudflare configuration was not found: {args.env}")
    if not args.collector_script.is_file():
        raise ValueError(f"collector script was not found: {args.collector_script}")


def collector_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(args.collector_script),
        "--env",
        str(args.env),
        "--db",
        str(args.db),
        "--limit",
        str(args.limit),
    ]


def run_cycle(args: argparse.Namespace, cycle_number: int) -> int:
    started = utc_now_text()
    completed = subprocess.run(
        collector_command(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    finished = utc_now_text()
    header = (
        f"\n===== cycle {cycle_number} | {started} -> {finished} "
        f"| exit={completed.returncode} =====\n"
    )
    append_log(args.log, header)
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_args(args)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    args.db.parent.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.status.parent.mkdir(parents=True, exist_ok=True)

    cycles = 0
    successful_cycles = 0
    failed_cycles = 0
    last_exit_code: int | None = None
    stop_reason = "UNKNOWN"
    started_at = utc_now_text()

    lock = ExclusiveLoopLock(args.lock_file)
    try:
        lock.__enter__()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    try:
        print("=" * 60)
        print("Mochipoyo Cloudflare collector loop - AUDIT ONLY")
        print(f"Interval      : {args.interval_seconds:g} seconds")
        print(f"Maximum cycles: {'FOREVER' if args.max_cycles == 0 else args.max_cycles}")
        print(f"Stop file     : {args.stop_file}")
        print("Discord send  : OFF")
        print("MT5 orders    : OFF")
        print("Live ready    : OFF")
        print("Final signal  : OFF")
        print("=" * 60)

        if args.stop_file.exists():
            stop_reason = "STOP_FILE_PRESENT_AT_START"
            print("[STOP] Stop file already exists. No collection cycle was run.")
        else:
            while True:
                if args.stop_file.exists():
                    stop_reason = "STOP_FILE"
                    break

                cycles += 1
                print(f"\n[CYCLE {cycles}] {utc_now_text()}")
                last_exit_code = run_cycle(args, cycles)
                if last_exit_code == 0:
                    successful_cycles += 1
                else:
                    failed_cycles += 1
                    print(
                        "[WARN] Collection cycle failed. The loop will continue; "
                        "the one-shot collector preserves the cursor on failure.",
                        file=sys.stderr,
                    )

                status = {
                    "status": "RUNNING",
                    "audit_only": True,
                    "dry_run": True,
                    "live_ready": False,
                    "final_signal": False,
                    "discord_send": False,
                    "mt5_order": False,
                    "started_at_utc": started_at,
                    "updated_at_utc": utc_now_text(),
                    "interval_seconds": args.interval_seconds,
                    "max_cycles": args.max_cycles,
                    "cycles": cycles,
                    "successful_cycles": successful_cycles,
                    "failed_cycles": failed_cycles,
                    "last_exit_code": last_exit_code,
                    "stop_file": str(args.stop_file),
                    "lock_file": str(args.lock_file),
                    "database_path": str(args.db),
                    "log_path": str(args.log),
                }
                atomic_write_json(args.status, status)

                if args.max_cycles and cycles >= args.max_cycles:
                    stop_reason = "MAX_CYCLES"
                    break

                print(
                    f"[WAIT] Next read-only collection in "
                    f"{args.interval_seconds:g} seconds."
                )
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
        final_status = {
            "status": "STOPPED",
            "audit_only": True,
            "dry_run": True,
            "live_ready": False,
            "final_signal": False,
            "discord_send": False,
            "mt5_order": False,
            "started_at_utc": started_at,
            "stopped_at_utc": utc_now_text(),
            "stop_reason": stop_reason,
            "interval_seconds": args.interval_seconds,
            "max_cycles": args.max_cycles,
            "cycles": cycles,
            "successful_cycles": successful_cycles,
            "failed_cycles": failed_cycles,
            "last_exit_code": last_exit_code,
            "database_path": str(args.db),
            "log_path": str(args.log),
        }
        try:
            atomic_write_json(args.status, final_status)
        except Exception:
            pass
        lock.__exit__(None, None, None)

    print(
        f"[STOPPED] reason={stop_reason} cycles={cycles} "
        f"success={successful_cycles} failed={failed_cycles}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
