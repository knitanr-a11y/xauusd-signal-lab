from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V8_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun_v8.py"

spec = importlib.util.spec_from_file_location("ff05_recovery_direct_v8_for_v9", V8_PATH)
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


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_verified_snapshot():
    """
    Materialize a durable FF05-only input snapshot immediately after merge validation.

    V8 proved that the merge process could rebuild and validate the merged files, but a
    later open of MERGED_FULL_HISTORY failed. V9 copies the verified payload into the
    rerun stage before the frozen FF05 module is loaded, verifies every SHA, and then
    exposes only the snapshot absolute paths to FF05.
    """
    if not v8_module.merged_files_ready():
        print("[RECOVERY_FF05_RERUN_V9] merged payload missing; rebuilding first")
        v8_module.rebuild_merged_history()

    summary, manifest, cutoff, merged_paths = REAL_LOAD_MERGE_CONTRACT()

    staging = SNAPSHOT_DIR.with_name(SNAPSHOT_DIR.name + "_STAGING")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    expected_by_tf = {
        str(row["timeframe"]): str(row["merged_sha256"])
        for row in manifest.to_dict(orient="records")
    }
    snapshot_paths: dict[str, Path] = {}
    for timeframe in ("M5", "M15", "H1"):
        source = Path(merged_paths[timeframe]).resolve()
        target = staging / source.name
        shutil.copyfile(source, target)
        actual = sha256_path(target)
        expected = expected_by_tf[timeframe]
        if actual != expected:
            raise RuntimeError(
                f"verified input snapshot SHA mismatch for {timeframe}: "
                f"expected={expected} actual={actual}"
            )
        snapshot_paths[timeframe] = target

    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    os.replace(staging, SNAPSHOT_DIR)
    snapshot_paths = {
        timeframe: (SNAPSHOT_DIR / path.name).resolve()
        for timeframe, path in snapshot_paths.items()
    }

    for timeframe, path in snapshot_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"verified snapshot missing for {timeframe}: {path}")
        actual = sha256_path(path)
        expected = expected_by_tf[timeframe]
        if actual != expected:
            raise RuntimeError(
                f"post-publish snapshot SHA mismatch for {timeframe}: "
                f"expected={expected} actual={actual}"
            )

    print("[RECOVERY_FF05_RERUN_V9] durable verified input snapshot is ready")
    for timeframe in ("M5", "M15", "H1"):
        print(f"  {timeframe}: {snapshot_paths[timeframe]} sha256={expected_by_tf[timeframe]}")

    return summary, manifest, cutoff, snapshot_paths


_snapshot_contract = None


def load_snapshot_contract():
    global _snapshot_contract
    if _snapshot_contract is None:
        _snapshot_contract = build_verified_snapshot()
    summary, manifest, cutoff, snapshot_paths = _snapshot_contract

    # Recheck on every caller entry so a missing or modified snapshot is never accepted.
    expected_by_tf = {
        str(row["timeframe"]): str(row["merged_sha256"])
        for row in manifest.to_dict(orient="records")
    }
    for timeframe, path in snapshot_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"verified snapshot disappeared for {timeframe}: {path}")
        actual = sha256_path(path)
        if actual != expected_by_tf[timeframe]:
            raise RuntimeError(
                f"verified snapshot changed for {timeframe}: "
                f"expected={expected_by_tf[timeframe]} actual={actual}"
            )
    return summary, manifest, cutoff, snapshot_paths


# Replace the merge-work-folder contract with the durable snapshot contract.
v5_module.load_merge_contract = load_snapshot_contract


def main() -> int:
    load_snapshot_contract()
    os.environ["BTC_FF05_RECOVERY_MODE"] = "DIRECT_DURABLE_VERIFIED_SNAPSHOT_V9"
    return int(v5_module.main())


if __name__ == "__main__":
    raise SystemExit(main())
