from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import recover_after_forced_reboot as base

M10P2_PROCESS_MARKER = "m10p2_guarded_runtime.py"
M10P2_LOCK_REL = Path("m10p2_runtime") / "m10p2_shadow_loop.lock"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        print("[RECOVERY BLOCKED] LOCALAPPDATA unavailable", file=sys.stderr)
        return 2

    root = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"

    try:
        running = base.running_processes(M10P2_PROCESS_MARKER)
        if running:
            print("[REBOOT RECOVERY BLOCKED] M10P2 is still running; no recovery action was started.", file=sys.stderr)
            return 2

        rc = base.main()
        if rc != 0:
            return rc

        archive = root / "reboot_recovery_m10p2" / utc_stamp()
        archive.mkdir(parents=True, exist_ok=False)
        lock = root / M10P2_LOCK_REL
        action = {
            "name": "M10P2",
            "lock": str(lock),
            "lock_existed": lock.is_file(),
            "archived": False,
            "removed": False,
        }
        if lock.is_file():
            destination = archive / f"M10P2_{lock.name}"
            shutil.copy2(lock, destination)
            action["archived"] = True
            action["archive_path"] = str(destination)
            lock.unlink()
            action["removed"] = True

        receipt = {
            "status": "PASS_M10P2_STALE_LOCK_RECOVERY_ONLY",
            "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action": action,
            "runtime_or_start_deleted": False,
            "runtime_or_start_reset": False,
            "m10p2_modified_or_reset": False,
            "m10p2_restart": "BAT03_ONLY_NEVER_BAT01",
            "prospective_start_preserved": True,
            "data_gap_note": "Permanent PC-off CSV gaps remain unobserved. M10P2 exact scheduled exits missing inside such a gap remain EXIT_DATA_GAP and are never backfilled.",
        }
        (archive / "m10p2_recovery_receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        if action["removed"]:
            print("[RECOVERED] M10P2: archived and removed stale lock")
        else:
            print("[OK] M10P2: no stale lock present")
        print(f"[M10P2 RECEIPT] {archive / 'm10p2_recovery_receipt.json'}")
        print("[SAFE] M10P2 runtime manifest/start/state/history were not reset.")
        return 0
    except Exception as exc:
        print(f"[REBOOT RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Recovery did not intentionally reset M10P2 runtime/start/state.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
