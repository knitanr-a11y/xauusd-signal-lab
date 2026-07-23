from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

INTERVAL_SECONDS = 300


def znow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    here = Path(__file__).resolve().parent
    worker = here / "run_forward_shadow_once.py"
    cycles = successful = failed = 0
    last_code = None
    started = znow()
    while True:
        cycles += 1
        proc = subprocess.run([sys.executable, str(worker)], check=False)
        last_code = proc.returncode
        if last_code == 0:
            successful += 1
        else:
            failed += 1
        status = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "M8C_EXTRA_LOSS_REDUCTION_GATE_FORWARD_SHADOW",
            "status": "RUNNING" if last_code == 0 else "BLOCKED",
            "started_at_utc": started,
            "updated_at_utc": znow(),
            "cycles": cycles,
            "successful_cycles": successful,
            "failed_cycles": failed,
            "last_exit_code": last_code,
            "interval_seconds": INTERVAL_SECONDS,
            "audit_only": True,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
        }
        root = Path.home() / "AppData" / "Local" / "xauusd_signal_lab" / "mochipoyo_alert_research" / "runtime" / "m8c"
        root.mkdir(parents=True, exist_ok=True)
        (root / "m8c_loop_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if last_code != 0:
            print(f"[M8C LOOP BLOCKED] exit_code={last_code}; no automatic reinitialization")
            return last_code
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
