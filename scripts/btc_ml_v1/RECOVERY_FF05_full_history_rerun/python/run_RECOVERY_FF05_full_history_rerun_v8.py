from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V7_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun_v7.py"

v7_spec = importlib.util.spec_from_file_location("ff05_recovery_direct_v7_for_v8", V7_PATH)
if v7_spec is None or v7_spec.loader is None:
    raise RuntimeError(f"cannot load V7 direct-path rerun module: {V7_PATH}")
v7_module = importlib.util.module_from_spec(v7_spec)
sys.modules[v7_spec.name] = v7_module
try:
    v7_spec.loader.exec_module(v7_module)
except Exception:
    sys.modules.pop(v7_spec.name, None)
    raise

v5_module = v7_module.v5_module
MERGE_RUNNER = (
    v5_module.ROOT
    / "scripts"
    / "btc_ml_v1"
    / "RECOVERY_FF05_full_history_merge"
    / "python"
    / "run_RECOVERY_FF05_full_history_merge.py"
)


def merged_files_ready() -> bool:
    """Return true only when the frozen merge contract and all merged CSVs validate."""
    try:
        v5_module.load_merge_contract()
        return True
    except (FileNotFoundError, RuntimeError, OSError, ValueError):
        return False


def rebuild_merged_history() -> None:
    """
    Recreate verified merged M5/M15/H1 and immediately retain them for FF05.

    The previous workflow treated MERGED_FULL_HISTORY as a durable artifact, but a
    later run found that the CSV payload was no longer present even though the
    merge report remained. V8 closes that lifecycle gap by rebuilding the merge
    inside the same process chain immediately before the direct-path evaluation.
    """
    if not MERGE_RUNNER.is_file():
        raise FileNotFoundError(f"full-history merge runner missing: {MERGE_RUNNER}")

    command = [
        sys.executable,
        str(MERGE_RUNNER),
        "--output-root",
        str(v5_module.MERGE_ROOT),
    ]
    completed = subprocess.run(
        command,
        cwd=v5_module.ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "automatic full-history rebuild failed: "
            f"exit_code={completed.returncode} command={command}"
        )

    # This performs status, time-domain, OOS coverage, path and SHA checks.
    merge_summary, manifest, cutoff, direct_paths = v5_module.load_merge_contract()
    if merge_summary.get("overall_status") != "READY_FULL_HISTORY_MERGED":
        raise RuntimeError(
            f"rebuilt merge status is not ready: {merge_summary.get('overall_status')}"
        )
    if not bool(merge_summary.get("merge_complete")):
        raise RuntimeError("rebuilt merge_complete is false")
    if set(direct_paths) != {"M5", "M15", "H1"}:
        raise RuntimeError(f"rebuilt direct paths are incomplete: {sorted(direct_paths)}")
    if not cutoff["coverage_from_oos_start"].astype(bool).all():
        raise RuntimeError("rebuilt history does not cover OOS start for all timeframes")

    audit = {
        "mode": "AUTO_REBUILD_AND_IMMEDIATE_DIRECT_PATH_EVALUATION_V8",
        "merge_status": merge_summary.get("overall_status"),
        "merged_paths": {key: str(value) for key, value in direct_paths.items()},
        "merged_sha256": {
            str(row["timeframe"]): str(row["merged_sha256"])
            for row in manifest.to_dict(orient="records")
        },
        "oos_coverage": {
            str(row["timeframe"]): bool(row["coverage_from_oos_start"])
            for row in cutoff.to_dict(orient="records")
        },
    }
    print("[RECOVERY_FF05_RERUN_V8] merged history rebuilt and verified")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


def main() -> int:
    if not merged_files_ready():
        print(
            "[RECOVERY_FF05_RERUN_V8] merged CSV payload is missing or invalid; "
            "rebuilding it now"
        )
        rebuild_merged_history()
    else:
        print("[RECOVERY_FF05_RERUN_V8] existing merged history passed validation")

    # V7 already fixes registered-module loading and V6/V5 enforce direct paths.
    return int(v5_module.main())


if __name__ == "__main__":
    raise SystemExit(main())
