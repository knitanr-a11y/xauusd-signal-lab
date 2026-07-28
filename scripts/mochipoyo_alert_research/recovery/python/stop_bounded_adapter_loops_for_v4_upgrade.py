from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

THIS = Path(__file__).resolve()
COMMON = THIS.parents[2] / "common" / "python"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import run_bounded_adapter_loop as runner
import migrate_bounded_csv_source_adapter as migration


def utc_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    try:
        local_value = os.environ.get("LOCALAPPDATA", "").strip()
        if not local_value:
            raise RuntimeError("LOCALAPPDATA unavailable")
        local_root = Path(local_value) / "xauusd_signal_lab" / "mochipoyo_alert_research"
        actions: dict[str, dict[str, object]] = {}

        for loop, spec in runner.LOOPS.items():
            stop_path = local_root / spec["stop_rel"]
            lock_path = local_root / spec["lock_rel"]
            marker = migration.PROCESS_MARKERS[loop]
            before = migration.running_processes(marker)
            stop_path.parent.mkdir(parents=True, exist_ok=True)
            stop_path.write_text(
                json.dumps({
                    "project": "MOCHIPOYO_ALERT_RESEARCH",
                    "request": "GRACEFUL_STOP_FOR_V4_PRIVATE_SNAPSHOT_UPGRADE",
                    "loop": loop,
                    "requested_at_utc": utc_text(),
                    "runtime_or_start_modified": False,
                    "lock_deleted": False,
                }, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            actions[loop] = {
                "processes_before": before,
                "lock_before": lock_path.is_file(),
                "stop_file": str(stop_path),
            }
            print(f"[STOP REQUESTED] {loop} processes={len(before)} lock={lock_path.is_file()}")

        deadline = time.monotonic() + 180.0
        while True:
            remaining: dict[str, dict[str, object]] = {}
            for loop, spec in runner.LOOPS.items():
                marker = migration.PROCESS_MARKERS[loop]
                processes = migration.running_processes(marker)
                lock_path = local_root / spec["lock_rel"]
                if processes or lock_path.is_file():
                    remaining[loop] = {
                        "processes": processes,
                        "lock_exists": lock_path.is_file(),
                    }
            if not remaining:
                break
            if time.monotonic() >= deadline:
                print("[STOP BLOCKED] Some loops did not stop within 180 seconds:", file=sys.stderr)
                print(json.dumps(remaining, ensure_ascii=False, indent=2), file=sys.stderr)
                print("[SAFE] No process was killed and no lock/runtime/start was deleted.", file=sys.stderr)
                return 2
            time.sleep(1.0)

        receipt_root = local_root / "outputs" / "BOUNDED_CSV_V4_UPGRADE_STOP"
        receipt_root.mkdir(parents=True, exist_ok=True)
        receipt = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "status": "PASS_ALL_SEVEN_STOPPED_GRACEFULLY_FOR_V4_UPGRADE",
            "completed_at_utc": utc_text(),
            "actions": actions,
            "processes_killed": False,
            "locks_deleted": False,
            "runtime_or_start_modified": False,
            "collector_m7c_m8c_modified": False,
            "next": "Fetch/Pull and restart BAT03 in dependency order using V4 private snapshots.",
        }
        (receipt_root / "latest_stop_receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("[STOP PASS] All seven bounded-adapter loops are stopped and all loop locks are absent.")
        print("[SAFE] No process kill, lock deletion, runtime edit, start reset, or collector/M7C/M8C change occurred.")
        return 0
    except Exception as exc:
        print(f"[STOP BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No process was intentionally killed and no runtime/start was changed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
