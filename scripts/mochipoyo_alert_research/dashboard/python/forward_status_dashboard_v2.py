from __future__ import annotations

from pathlib import Path
from typing import Any

import forward_status_dashboard as base


DASHBOARD_VERSION = "M9V_PLUS_FORWARD_STATUS_DASHBOARD_V2_NULL_SAFE_PID"


def safe_gate_text(count: Any, gates: tuple[int, ...]) -> str:
    normalized = base.integer(count, default=0)
    reached = [gate for gate in gates if normalized >= gate]
    upcoming = next((gate for gate in gates if normalized < gate), None)
    if not reached:
        return f"WAIT -> {gates[0]}"
    if upcoming is None:
        return f"FORMAL {gates[-1]} REACHED"
    return f"REACHED {reached[-1]} -> NEXT {upcoming}"


def safe_health_text(
    status_payload: dict[str, Any] | None,
    lock_path: Path,
) -> tuple[str, str]:
    status = str((status_payload or {}).get("status", "NO_STATUS"))
    status_pid = base.integer((status_payload or {}).get("pid"), default=0)
    fallback_pid = base.integer(base.lock_pid(lock_path), default=0)
    pid = status_pid if status_pid > 0 else fallback_pid
    alive = base.process_alive(pid if pid > 0 else None)
    lock_exists = lock_path.is_file()

    if "BLOCKED" in status or "FAIL" in status:
        health = "BLOCKED"
    elif status == "WAITING_TRANSIENT_SOURCE":
        health = "WAITING"
    elif status == "RUNNING" and lock_exists and alive is not False:
        health = "RUNNING"
    elif status == "RUNNING":
        health = "CHECK"
    elif lock_exists and alive is True:
        health = "RUNNING?"
    else:
        health = status[:12]

    details = f"lock={'Y' if lock_exists else 'N'} pid={pid if pid > 0 else '-'}"
    return health, details


base.gate_text = safe_gate_text
base.health_text = safe_health_text


if __name__ == "__main__":
    raise SystemExit(base.main())
