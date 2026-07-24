from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[4]
INITIALIZER = THIS.parent / "initialize_m9v_runtime_v2.py"
CONTRACT = REPO_ROOT / "config" / "mochipoyo_alert_research" / "m9v_gold_multitimeframe_fresh_prospective_shadow_contract_20260724.json"


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    try:
        if not metadata_path.is_file():
            raise RuntimeError(f"M8B symbol metadata missing: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        mt5_root = Path(str(metadata.get("mt5_files_root", "")))
        point = float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))
        if not mt5_root.is_dir() or not math.isfinite(point):
            raise RuntimeError(f"MT5 Files root or XAUUSD point unavailable: {mt5_root} point={point}")
        runtime_dir = local_root / "m9v_runtime"
        runtime = runtime_dir / "m9v_runtime_manifest.json"
        receipt = runtime_dir / "m9v_runtime_start_receipt.json"
        lock_file = runtime_dir / "m9v_shadow_loop.lock"
        command = [
            sys.executable,
            str(INITIALIZER),
            "--contract", str(CONTRACT),
            "--data-root", str(mt5_root),
            "--runtime-manifest", str(runtime),
            "--receipt", str(receipt),
            "--lock-file", str(lock_file),
            "--stability-seconds", "2",
        ]
        completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
        return int(completed.returncode)
    except Exception as exc:
        print(f"[M9V INIT FAIL_CLOSED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] M8C, M7C and collector remain unchanged.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
