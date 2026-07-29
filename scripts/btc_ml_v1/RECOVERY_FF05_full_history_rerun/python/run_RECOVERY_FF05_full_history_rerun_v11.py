from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
V7_PATH = HERE / "run_RECOVERY_FF05_full_history_rerun_v7.py"

spec = importlib.util.spec_from_file_location("ff05_recovery_direct_v7_for_v11", V7_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load V7 direct-path module: {V7_PATH}")
v7_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v7_module
try:
    spec.loader.exec_module(v7_module)
except Exception:
    sys.modules.pop(spec.name, None)
    raise

v5_module = v7_module.v5_module
LOCAL_BASE = v5_module.LOCAL_BASE
MERGE_RUNNER = (
    v5_module.ROOT
    / "scripts"
    / "btc_ml_v1"
    / "RECOVERY_FF05_full_history_merge"
    / "python"
    / "run_RECOVERY_FF05_full_history_merge.py"
)
DEDICATED_MERGE_ROOT = LOCAL_BASE / "RECOVERY_FF05_full_history_merge_V11_DEDICATED"
SNAPSHOT_DIR = LOCAL_BASE / "RECOVERY_FF05_full_history_rerun_INPUT_V11"
LOCK_PATH = LOCAL_BASE / "RECOVERY_FF05_full_history_rerun_V11.lock"
TARGET_FILENAMES = {
    "M5": "btcusdsharp_m5.csv",
    "M15": "btcusdsharp_m15.csv",
    "H1": "btcusdsharp_h1.csv",
}

_snapshot_contract = None
_lock_acquired = False


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_run_lock() -> None:
    global _lock_acquired
    LOCAL_BASE.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        age_seconds = max(0.0, time.time() - LOCK_PATH.stat().st_mtime)
        if age_seconds > 6 * 60 * 60:
            LOCK_PATH.unlink(missing_ok=True)
        else:
            detail = LOCK_PATH.read_text(encoding="utf-8", errors="replace").strip()
            raise RuntimeError(
                "another V11 rerun appears active; refusing concurrent execution: "
                f"lock={LOCK_PATH} detail={detail}"
            )
    fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        payload = json.dumps(
            {"pid": os.getpid(), "created_epoch": time.time(), "version": "V11"},
            ensure_ascii=False,
        ).encode("utf-8")
        os.write(fd, payload)
    finally:
        os.close(fd)
    _lock_acquired = True


def release_run_lock() -> None:
    global _lock_acquired
    if _lock_acquired:
        LOCK_PATH.unlink(missing_ok=True)
        _lock_acquired = False


def run_one_dedicated_merge() -> None:
    if not MERGE_RUNNER.is_file():
        raise FileNotFoundError(f"merge runner missing: {MERGE_RUNNER}")
    if DEDICATED_MERGE_ROOT.exists():
        shutil.rmtree(DEDICATED_MERGE_ROOT)
    DEDICATED_MERGE_ROOT.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(MERGE_RUNNER),
        "--output-root",
        str(DEDICATED_MERGE_ROOT),
    ]
    print("[RECOVERY_FF05_RERUN_V11] running exactly one dedicated merge")
    print(f"[RECOVERY_FF05_RERUN_V11] dedicated_root={DEDICATED_MERGE_ROOT}")
    completed = subprocess.run(command, cwd=v5_module.ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "dedicated full-history merge failed: "
            f"exit_code={completed.returncode} command={command}"
        )


def read_dedicated_merge_contract():
    latest = DEDICATED_MERGE_ROOT / "LATEST"
    merged_dir = DEDICATED_MERGE_ROOT / "MERGED_FULL_HISTORY"
    summary_path = latest / "01_merge_summary.json"
    manifest_path = latest / "03_merge_manifest.csv"
    cutoff_path = latest / "05_cutoff_coverage.csv"
    for path in (summary_path, manifest_path, cutoff_path):
        if not path.is_file():
            raise FileNotFoundError(f"dedicated merge output missing: {path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    manifest = pd.read_csv(manifest_path)
    cutoff = pd.read_csv(cutoff_path)

    if summary.get("overall_status") != "READY_FULL_HISTORY_MERGED":
        raise RuntimeError(f"dedicated merge status is not ready: {summary.get('overall_status')}")
    if not bool(summary.get("merge_complete")):
        raise RuntimeError("dedicated merge_complete is false")
    if summary.get("reference_and_current_time_domain") != "SAME_RAW_MT5_BROKER_SERVER_WALL_CLOCK":
        raise RuntimeError("dedicated merge time domain is not frozen")
    if set(manifest["timeframe"].astype(str)) != set(TARGET_FILENAMES):
        raise RuntimeError("dedicated manifest timeframes are not exactly M5/M15/H1")
    if set(cutoff["timeframe"].astype(str)) != set(TARGET_FILENAMES):
        raise RuntimeError("dedicated cutoff timeframes are not exactly M5/M15/H1")
    if not cutoff["coverage_from_oos_start"].astype(bool).all():
        raise RuntimeError("dedicated history does not cover OOS start for every timeframe")

    direct_paths: dict[str, Path] = {}
    expected_sha: dict[str, str] = {}
    merged_root_norm = os.path.normcase(str(merged_dir.resolve()))
    for row in manifest.to_dict(orient="records"):
        timeframe = str(row["timeframe"])
        path = Path(str(row["merged_path"])).resolve()
        expected_path = (merged_dir / TARGET_FILENAMES[timeframe]).resolve()
        if path != expected_path:
            raise RuntimeError(f"unexpected dedicated merged path for {timeframe}: {path}")
        if not os.path.normcase(str(path)).startswith(merged_root_norm + os.sep):
            raise RuntimeError(f"dedicated merged path escaped workspace: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"dedicated merged CSV missing for {timeframe}: {path}")
        actual = sha256_path(path)
        expected = str(row["merged_sha256"])
        if actual != expected:
            raise RuntimeError(
                f"dedicated merged SHA mismatch for {timeframe}: expected={expected} actual={actual}"
            )
        direct_paths[timeframe] = path
        expected_sha[timeframe] = expected

    return summary, manifest, cutoff, direct_paths, expected_sha


def publish_verified_snapshot():
    run_one_dedicated_merge()
    summary, manifest, cutoff, merged_paths, expected_sha = read_dedicated_merge_contract()

    staging = SNAPSHOT_DIR.with_name(SNAPSHOT_DIR.name + "_STAGING")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    staged: dict[str, Path] = {}
    for timeframe in ("M5", "M15", "H1"):
        source = merged_paths[timeframe]
        target = staging / TARGET_FILENAMES[timeframe]
        with source.open("rb") as source_handle, target.open("wb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
        actual = sha256_path(target)
        if actual != expected_sha[timeframe]:
            raise RuntimeError(
                f"V11 staged snapshot SHA mismatch for {timeframe}: "
                f"expected={expected_sha[timeframe]} actual={actual}"
            )
        staged[timeframe] = target

    if SNAPSHOT_DIR.exists():
        shutil.rmtree(SNAPSHOT_DIR)
    os.replace(staging, SNAPSHOT_DIR)

    snapshot_paths = {
        timeframe: (SNAPSHOT_DIR / TARGET_FILENAMES[timeframe]).resolve()
        for timeframe in ("M5", "M15", "H1")
    }
    for timeframe, path in snapshot_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"V11 published snapshot missing for {timeframe}: {path}")
        actual = sha256_path(path)
        if actual != expected_sha[timeframe]:
            raise RuntimeError(
                f"V11 published snapshot SHA mismatch for {timeframe}: "
                f"expected={expected_sha[timeframe]} actual={actual}"
            )

    print("[RECOVERY_FF05_RERUN_V11] dedicated snapshot published and verified")
    for timeframe in ("M5", "M15", "H1"):
        print(f"  {timeframe}: {snapshot_paths[timeframe]} sha256={expected_sha[timeframe]}")
    return summary, manifest, cutoff, snapshot_paths


def load_v11_snapshot_contract():
    global _snapshot_contract
    if _snapshot_contract is None:
        acquire_run_lock()
        _snapshot_contract = publish_verified_snapshot()

    summary, manifest, cutoff, snapshot_paths = _snapshot_contract
    expected_sha = {
        str(row["timeframe"]): str(row["merged_sha256"])
        for row in manifest.to_dict(orient="records")
    }
    for timeframe, path in snapshot_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"V11 snapshot disappeared for {timeframe}: {path}")
        actual = sha256_path(path)
        if actual != expected_sha[timeframe]:
            raise RuntimeError(
                f"V11 snapshot changed for {timeframe}: "
                f"expected={expected_sha[timeframe]} actual={actual}"
            )
    return summary, manifest, cutoff, snapshot_paths


v5_module.load_merge_contract = load_v11_snapshot_contract


def main() -> int:
    os.environ["BTC_FF05_RECOVERY_MODE"] = "DIRECT_DEDICATED_MERGE_SNAPSHOT_V11"
    try:
        return int(v5_module.main())
    finally:
        release_run_lock()


if __name__ == "__main__":
    raise SystemExit(main())
