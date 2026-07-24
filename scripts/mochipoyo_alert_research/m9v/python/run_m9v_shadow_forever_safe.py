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

THIS = Path(__file__).resolve()
ONE_SHOT = THIS.parent / "run_m9v_shadow_once.py"
STOP_NAME = "STOP_M9V_SHADOW_LOOP"
LOCK_NAME = "m9v_shadow_loop.lock"


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


class Lock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(f"M9V loop lock already exists: {self.path}") from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "started_at_utc": utc_text(), "audit_only": True, "discord_send": False, "mt5_order": False}, handle, indent=2)
            handle.write("\n")
        self.acquired = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False


def parse_args() -> argparse.Namespace:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    runtime_dir = local_root / "m9v_runtime"
    log_dir = local_root / "logs" / "m9v"
    parser = argparse.ArgumentParser(description="Run M9V fresh GOLD multi-timeframe audit shadow forever safely.")
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--stop-file", type=Path, default=runtime_dir / STOP_NAME)
    parser.add_argument("--lock-file", type=Path, default=runtime_dir / LOCK_NAME)
    parser.add_argument("--runtime-manifest", type=Path, default=runtime_dir / "m9v_runtime_manifest.json")
    parser.add_argument("--log", type=Path, default=log_dir / "m9v_shadow_forever.log")
    parser.add_argument("--status", type=Path, default=log_dir / "latest_m9v_shadow_loop_status.json")
    return parser.parse_args()


def run_cycle(args: argparse.Namespace, number: int) -> int:
    env = dict(os.environ)
    env["M9V_RUNTIME_MANIFEST"] = str(args.runtime_manifest)
    completed = subprocess.run([sys.executable, str(ONE_SHOT)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, env=env)
    stamp = utc_text()
    append_log(args.log, f"\n===== M9V cycle {number} {stamp} exit={completed.returncode} =====\n")
    if completed.stdout:
        append_log(args.log, completed.stdout)
        print(completed.stdout.rstrip())
    if completed.stderr:
        append_log(args.log, "[stderr]\n" + completed.stderr)
        print(completed.stderr.rstrip(), file=sys.stderr)
    return int(completed.returncode)


def main() -> int:
    args = parse_args()
    if args.interval_seconds < 60 or args.interval_seconds > 3600:
        print("[M9V LOOP BLOCKED] interval must be 60..3600 seconds", file=sys.stderr)
        return 2
    if args.max_cycles < 0:
        print("[M9V LOOP BLOCKED] max-cycles must be non-negative", file=sys.stderr)
        return 2
    if not ONE_SHOT.is_file() or not args.runtime_manifest.is_file():
        print(f"[M9V LOOP BLOCKED] one-shot or runtime manifest missing: {ONE_SHOT} {args.runtime_manifest}", file=sys.stderr)
        return 2
    args.stop_file.unlink(missing_ok=True)
    cycles = ok = failed = 0
    last_rc: int | None = None
    started = utc_text()
    try:
        with Lock(args.lock_file):
            print("=" * 68)
            print("M9V GOLD multi-timeframe prospective shadow - AUDIT ONLY")
            print(f"Runtime: {args.runtime_manifest}")
            print("M8C / M7C / collector: separate and unchanged")
            print("Discord / MT5 orders: OFF")
            print("Contract exit 2: STOP FAIL-CLOSED")
            print("=" * 68)
            while True:
                if args.stop_file.exists():
                    stop_reason = "STOP_FILE"
                    break
                cycles += 1
                last_rc = run_cycle(args, cycles)
                if last_rc == 0:
                    ok += 1
                else:
                    failed += 1
                payload = {
                    "status": "RUNNING" if last_rc == 0 else "ERROR",
                    "stage": "M9V_GOLD_MULTI_TIMEFRAME_FRESH_PROSPECTIVE_SHADOW",
                    "audit_only": True,
                    "started_at_utc": started,
                    "updated_at_utc": utc_text(),
                    "cycles": cycles,
                    "successful_cycles": ok,
                    "failed_cycles": failed,
                    "last_exit_code": last_rc,
                    "runtime_manifest": str(args.runtime_manifest),
                    "stop_file": str(args.stop_file),
                    "lock_file": str(args.lock_file),
                    "discord_send": False,
                    "mt5_order": False,
                    "m8c_reset": False,
                }
                atomic_json(args.status, payload)
                if last_rc == 2:
                    payload["status"] = "BLOCKED"
                    payload["stop_reason"] = "FAIL_CLOSED_CONTRACT_BLOCK"
                    atomic_json(args.status, payload)
                    print("[M9V LOOP BLOCKED] Contract/data integrity failed closed. Loop stopped.", file=sys.stderr)
                    return 2
                if args.max_cycles and cycles >= args.max_cycles:
                    stop_reason = "MAX_CYCLES"
                    break
                deadline = time.monotonic() + args.interval_seconds
                while time.monotonic() < deadline:
                    if args.stop_file.exists():
                        break
                    time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
                if args.stop_file.exists():
                    stop_reason = "STOP_FILE"
                    break
            atomic_json(args.status, {
                "status": "STOPPED",
                "stage": "M9V_GOLD_MULTI_TIMEFRAME_FRESH_PROSPECTIVE_SHADOW",
                "audit_only": True,
                "started_at_utc": started,
                "updated_at_utc": utc_text(),
                "cycles": cycles,
                "successful_cycles": ok,
                "failed_cycles": failed,
                "last_exit_code": last_rc,
                "stop_reason": stop_reason,
                "discord_send": False,
                "mt5_order": False,
                "m8c_reset": False,
            })
            return 0
    except Exception as exc:
        print(f"[M9V LOOP BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
