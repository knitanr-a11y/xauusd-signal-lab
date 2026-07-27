from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import recover_after_forced_reboot_with_m10p2 as previous
import recover_after_forced_reboot as base

M10W19_PROCESS_MARKER = "m10w19_runtime.py"
M10W19_RUNTIME_REL = Path("m10w19_runtime") / "m10w19_runtime_manifest.json"
M10W19_LOCK_REL = Path("m10w19_runtime") / "m10w19_shadow_loop.lock"


def main() -> int:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if not local:
        print("[RECOVERY BLOCKED] LOCALAPPDATA unavailable", file=sys.stderr)
        return 2
    root = Path(local) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    try:
        running = base.running_processes(M10W19_PROCESS_MARKER)
        if running:
            print("[REBOOT RECOVERY BLOCKED] M10W19 is still running; no recovery action was started.", file=sys.stderr)
            return 2
        rc = previous.main()
        if rc != 0:
            return rc
        runtime = root / M10W19_RUNTIME_REL
        lock = root / M10W19_LOCK_REL
        archive = root / "reboot_recovery_m10w19" / datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
        archive.mkdir(parents=True, exist_ok=False)
        action = {"name":"M10W19","runtime_exists":runtime.is_file(),"lock":str(lock),"lock_existed":lock.is_file(),"archived":False,"removed":False}
        if lock.is_file():
            destination = archive / f"M10W19_{lock.name}"
            shutil.copy2(lock, destination)
            action["archived"] = True
            action["archive_path"] = str(destination)
            lock.unlink()
            action["removed"] = True
        receipt = {
            "status":"PASS_M10W19_STALE_LOCK_RECOVERY_ONLY",
            "created_at_utc":datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "action":action,
            "runtime_or_start_deleted":False,
            "runtime_or_start_reset":False,
            "m10w19_restart":"BAT03_ONLY_IF_RUNTIME_ALREADY_INITIALIZED",
            "m10w19_initializer":"NEVER_RERUN_AFTER_INIT_PASS",
            "prospective_start_preserved":True,
            "data_gap_note":"Permanent PC-off CSV gaps remain unobserved. Exact entry/exit gaps are never repaired from future outcomes."
        }
        (archive / "m10w19_recovery_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("[RECOVERED] M10W19: archived and removed stale lock" if action["removed"] else "[OK] M10W19: no stale lock present")
        print(f"[M10W19 RECEIPT] {archive / 'm10w19_recovery_receipt.json'}")
        print("[SAFE] M10W19 runtime manifest/start/state/history were not reset.")
        return 0
    except Exception as exc:
        print(f"[REBOOT RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] Recovery did not intentionally reset M10W19 or existing monitor runtime/start/state.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
