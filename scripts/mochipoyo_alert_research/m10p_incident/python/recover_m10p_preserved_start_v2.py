from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

import recover_m10p_preserved_start as base

RECOVERY_VERSION = "M10P_PRESERVED_START_RECOVERY_V2_SELF_QUERY_EXCLUDED"


def exact_m10p_process_inventory() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "$ErrorActionPreference='Stop'; "
        "$rows = Get-CimInstance Win32_Process | "
        "Where-Object { "
        "$_.Name -notmatch '^(?i:powershell|pwsh)\\.exe$' -and "
        "$_.CommandLine -match '(?i)run_bounded_adapter_loop(?:_v[0-9]+)?\\.py.*--loop\\s+M10P(?:\\s|$)' "
        "} | Select-Object ProcessId,Name,CreationDate,CommandLine; "
        "@($rows) | ConvertTo-Json -Depth 4 -Compress",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"M10P process inventory failed: {completed.stderr[-4000:]}")
    text = completed.stdout.strip()
    if not text:
        return []
    parsed = json.loads(text)
    return parsed if isinstance(parsed, list) else [parsed]


base.process_inventory = exact_m10p_process_inventory
base.RECOVERY_VERSION = RECOVERY_VERSION


if __name__ == "__main__":
    try:
        raise SystemExit(base.main())
    except Exception as exc:
        print(f"[M10P RECOVERY BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] M10P runtime/start/state/evidence and the other eight loops were not changed.", file=sys.stderr)
        raise SystemExit(2)
