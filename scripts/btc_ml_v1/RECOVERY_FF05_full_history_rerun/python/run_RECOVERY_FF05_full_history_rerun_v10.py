from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V8_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun_v8.py"

spec = importlib.util.spec_from_file_location("ff05_recovery_direct_v8_for_v10", V8_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load V8 rerun module: {V8_PATH}")
v8_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v8_module
try:
    spec.loader.exec_module(v8_module)
except Exception:
    sys.modules.pop(spec.name, None)
    raise

v5_module = v8_module.v5_module
REAL_LOAD_MERGE_CONTRACT = v5_module.load_merge_contract
SNAPSHOT_DIR = v5_module.DEFAULT_OUTPUT / "VERIFIED_FULL_HISTORY_INPUT"
_merge_rebuild_attempted = False
_snapshot_contract = None


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_real_merge_contract_once():
    """
    Validate the real merge contract without calling the patched snapshot loader.

    V9 called v8_module.merged_files_ready() after replacing
    v5_module.load_merge_contract. That helper then called the replacement again,
    causing an endless rebuild recursion. V10 always calls the captured original
    merge-contract loader and permits at most one automatic rebuild.
    """
    global _merge_rebuild_attempted
    try:
        return REAL_LOAD_MERGE_CONTRACT()
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as first_error:
        if _merge_rebuild_attempted:
            raise RuntimeError(
                "merged history remained invalid after the single permitted rebuild"
            ) from first_error
        _merge_rebuild_attempted = True
        print("[RECOVERY_FF05_RERUN_V10] merged payload missing or invalid; rebuilding once")
        v8_module.rebuild_merged_history()
        try:
            return REAL_LOAD_MERGE_CONTRACT()
        except (FileNotFoundError, RuntimeError, OSError, ValueError) as second_error:
            raise RuntimeError(
                "merged history validation failed after one rebuild; refusing to loop"
            ) from second_error


def build_verified_snapshot():
    summary, manifest, cutoff, merged_paths = load_real_merge_contract_once()

    staging = SNAPSHOT_DIR.with_name(SNAPSHOT_DIR.name + "_STAGING")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    expected_by_tf = {
        str(row["timeframe"]): str(row["merged_sha256"])
        for row in manifest.to_dict(orient="records")
    }
    staged_paths: dict[str, Path] = {}
    for timeframe in ("M5", "M15", "H1"):
        source = Path(merged_paths[timeframe]).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"validated merged source disappeared for {timeframe}: {source}")
        target = staging / source.name
        shutil.copyfile(source, target)
        actual = sha256_path(target)
        expected = expected_by_tf[timeframe]
        if actual != expected:
            raise RuntimeError(
                f"verified snapshot SHA mismatch for {timeframe}: expected={expected} actual={actual}"
            )
        staged_paths[timeframe] = target

    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    os.replace(staging, SNAPSHOT_DIR)

    snapshot_paths = {
        timeframe: (SNAPSHOT_DIR / staged.name).resolve()
        for timeframe, staged in staged_paths.items()
    }
    for timeframe, path in snapshot_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"published snapshot missing for {timeframe}: {path}")
        actual = sha256_path(path)
        expected = expected_by_tf[timeframe]
        if actual != expected:
            raise RuntimeError(
                f"published snapshot SHA mismatch for {timeframe}: expected={expected} actual={actual}"
            )

    print("[RECOVERY_FF05_RERUN_V10] durable verified input snapshot is ready")
    for timeframe in ("M5", "M15", "H1"):
        print(f"  {timeframe}: {snapshot_paths[timeframe]} sha256={expected_by_tf[timeframe]}")
    return summary, manifest, cutoff, snapshot_paths


def load_snapshot_contract():
    global _snapshot_contract
    if _snapshot_contract is None:
        _snapshot_contract = build_verified_snapshot()

    summary, manifest, cutoff, snapshot_paths = _snapshot_contract
    expected_by_tf = {
        str(row["timeframe"]): str(row["merged_sha256"])
        for row in manifest.to_dict(orient="records")
    }
    for timeframe, path in snapshot_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"verified snapshot disappeared for {timeframe}: {path}")
        actual = sha256_path(path)
        expected = expected_by_tf[timeframe]
        if actual != expected:
            raise RuntimeError(
                f"verified snapshot changed for {timeframe}: expected={expected} actual={actual}"
            )
    return summary, manifest, cutoff, snapshot_paths


# Patch only after all calls that need the captured real loader are defined.
v5_module.load_merge_contract = load_snapshot_contract


def main() -> int:
    load_snapshot_contract()
    os.environ["BTC_FF05_RECOVERY_MODE"] = "DIRECT_DURABLE_VERIFIED_SNAPSHOT_V10_SINGLE_REBUILD"
    return int(v5_module.main())


if __name__ == "__main__":
    raise SystemExit(main())
