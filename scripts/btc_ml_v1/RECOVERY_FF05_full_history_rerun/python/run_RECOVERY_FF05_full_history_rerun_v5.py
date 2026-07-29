from __future__ import annotations

import argparse
import fnmatch
import glob as glob_module
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL_LOADER = (
    ROOT
    / "scripts"
    / "btc_ml_v1"
    / "FF05_candidate_rebuild_search"
    / "python"
    / "run_FF05_candidate_rebuild_search.py"
)
LOCAL_BASE = (
    Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
    / "xauusd_signal_lab"
    / "btc_ml_v1"
    / "outputs"
)
MERGE_ROOT = LOCAL_BASE / "RECOVERY_FF05_full_history_merge"
MERGED_DIR = MERGE_ROOT / "MERGED_FULL_HISTORY"
MERGE_LATEST = MERGE_ROOT / "LATEST"
DEFAULT_OUTPUT = LOCAL_BASE / "RECOVERY_FF05_full_history_rerun"
ORIGINAL_PUBLIC = (
    "00_READ_ME_FIRST.txt",
    "01_search_summary.json",
    "02_search_report.txt",
    "03_all_108_cells.csv",
    "04_oos_segment_metrics.csv",
    "05_trade_ledger.csv",
    "06_weekly_block_matrix.csv",
    "07_bootstrap_familywise.csv",
    "08_input_manifest.csv",
    "09_selected_candidate.json",
    "10_preregistration_copy.json",
    "11_self_tests.csv",
)
PROVENANCE = "12_recovery_input_provenance.json"
TARGET_FILENAMES = {
    "M5": "btcusdsharp_m5.csv",
    "M15": "btcusdsharp_m15.csv",
    "H1": "btcusdsharp_h1.csv",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def load_merge_contract() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, Path]]:
    required = {
        "summary": MERGE_LATEST / "01_merge_summary.json",
        "manifest": MERGE_LATEST / "03_merge_manifest.csv",
        "cutoff": MERGE_LATEST / "05_cutoff_coverage.csv",
    }
    for label, path in required.items():
        if not path.is_file():
            raise FileNotFoundError(f"required merge {label} missing: {path}")

    summary = json.loads(required["summary"].read_text(encoding="utf-8-sig"))
    if summary.get("overall_status") != "READY_FULL_HISTORY_MERGED":
        raise RuntimeError(f"merge status is not ready: {summary.get('overall_status')}")
    if not bool(summary.get("merge_complete")):
        raise RuntimeError("merge_complete is false")
    if summary.get("reference_and_current_time_domain") != "SAME_RAW_MT5_BROKER_SERVER_WALL_CLOCK":
        raise RuntimeError("merged history time domain is not frozen")

    manifest = pd.read_csv(required["manifest"])
    cutoff = pd.read_csv(required["cutoff"])
    expected_timeframes = set(TARGET_FILENAMES)
    if set(manifest["timeframe"].astype(str)) != expected_timeframes:
        raise RuntimeError("merge manifest timeframes are not exactly M5/M15/H1")
    if set(cutoff["timeframe"].astype(str)) != expected_timeframes:
        raise RuntimeError("cutoff coverage timeframes are not exactly M5/M15/H1")
    if not cutoff["coverage_from_oos_start"].astype(bool).all():
        raise RuntimeError("full OOS coverage is not proven for all timeframes")

    direct_paths: dict[str, Path] = {}
    for row in manifest.to_dict(orient="records"):
        timeframe = str(row["timeframe"])
        path = Path(str(row["merged_path"])).resolve()
        expected_path = (MERGED_DIR / TARGET_FILENAMES[timeframe]).resolve()
        if path != expected_path:
            raise RuntimeError(f"unexpected merged path for {timeframe}: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"merged CSV missing for {timeframe}: {path}")
        actual_sha = sha256_path(path)
        if actual_sha != str(row["merged_sha256"]):
            raise RuntimeError(
                f"merged SHA mismatch for {timeframe}: "
                f"expected={row['merged_sha256']} actual={actual_sha}"
            )
        direct_paths[timeframe] = path
    return summary, manifest, cutoff, direct_paths


def load_original_module():
    if not ORIGINAL_LOADER.is_file():
        raise FileNotFoundError(f"FF05 loader missing: {ORIGINAL_LOADER}")
    spec = importlib.util.spec_from_file_location("ff05_original_direct_v5", ORIGINAL_LOADER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load original FF05 module: {ORIGINAL_LOADER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "main", None)):
        raise RuntimeError("original FF05 module has no callable main")
    return module


def _pattern_targets(pattern: str, direct_paths: dict[str, Path]) -> list[Path]:
    normalized = str(pattern).replace("\\", "/").lower()
    basename = Path(normalized).name
    matched: list[Path] = []
    for timeframe, path in direct_paths.items():
        filename = TARGET_FILENAMES[timeframe].lower()
        if (
            fnmatch.fnmatch(filename, basename)
            or filename in normalized
            or (timeframe.lower() in normalized and "btc" in normalized and ".csv" in normalized)
        ):
            matched.append(path)
    return sorted(set(matched), key=lambda item: str(item).lower())


class DirectPathPatch:
    """Force all BTC M5/M15/H1 discovery APIs to expose only verified merged files."""

    def __init__(self, direct_paths: dict[str, Path]) -> None:
        self.direct_paths = direct_paths
        self._path_rglob = Path.rglob
        self._path_glob = Path.glob
        self._glob = glob_module.glob
        self._iglob = glob_module.iglob
        self._os_walk = os.walk

    def __enter__(self) -> "DirectPathPatch":
        direct_paths = self.direct_paths
        original_rglob = self._path_rglob
        original_glob_method = self._path_glob
        original_glob = self._glob
        original_iglob = self._iglob
        original_walk = self._os_walk

        def patched_rglob(path_self: Path, pattern: str):
            matched = _pattern_targets(str(pattern), direct_paths)
            if matched:
                return iter(matched)
            return original_rglob(path_self, pattern)

        def patched_path_glob(path_self: Path, pattern: str):
            matched = _pattern_targets(str(pattern), direct_paths)
            if matched:
                return iter(matched)
            return original_glob_method(path_self, pattern)

        def patched_glob(pathname: str, *args, **kwargs):
            matched = _pattern_targets(str(pathname), direct_paths)
            if matched:
                return [str(path) for path in matched]
            return original_glob(pathname, *args, **kwargs)

        def patched_iglob(pathname: str, *args, **kwargs):
            matched = _pattern_targets(str(pathname), direct_paths)
            if matched:
                return iter(str(path) for path in matched)
            return original_iglob(pathname, *args, **kwargs)

        def patched_walk(top, *args, **kwargs) -> Iterator[tuple[str, list[str], list[str]]]:
            yielded_direct = False
            for dirpath, dirnames, filenames in original_walk(top, *args, **kwargs):
                filtered = [
                    filename
                    for filename in filenames
                    if filename.lower() not in {name.lower() for name in TARGET_FILENAMES.values()}
                ]
                yield dirpath, dirnames, filtered
            if not yielded_direct:
                yielded_direct = True
                yield (
                    str(MERGED_DIR),
                    [],
                    [path.name for path in direct_paths.values()],
                )

        Path.rglob = patched_rglob  # type: ignore[method-assign]
        Path.glob = patched_path_glob  # type: ignore[method-assign]
        glob_module.glob = patched_glob  # type: ignore[assignment]
        glob_module.iglob = patched_iglob  # type: ignore[assignment]
        os.walk = patched_walk  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        Path.rglob = self._path_rglob  # type: ignore[method-assign]
        Path.glob = self._path_glob  # type: ignore[method-assign]
        glob_module.glob = self._glob  # type: ignore[assignment]
        glob_module.iglob = self._iglob  # type: ignore[assignment]
        os.walk = self._os_walk  # type: ignore[assignment]


def run_original(module, output_root: Path, direct_paths: dict[str, Path]) -> int:
    old_argv = sys.argv[:]
    sys.argv = [str(ORIGINAL_LOADER), "--output-root", str(output_root)]
    os.environ["BTC_FF05_RECOVERY_MODE"] = "DIRECT_VERIFIED_MERGED_PATHS_V5"
    os.environ["BTC_FF05_DIRECT_M5"] = str(direct_paths["M5"])
    os.environ["BTC_FF05_DIRECT_M15"] = str(direct_paths["M15"])
    os.environ["BTC_FF05_DIRECT_H1"] = str(direct_paths["H1"])
    try:
        with DirectPathPatch(direct_paths):
            try:
                result = module.main()
            except SystemExit as exc:
                result = exc.code
        return int(result or 0)
    finally:
        sys.argv = old_argv


def validate_outputs(
    latest: Path,
    merge_manifest: pd.DataFrame,
    direct_paths: dict[str, Path],
) -> tuple[dict[str, Any], pd.DataFrame]:
    missing = [name for name in ORIGINAL_PUBLIC if not (latest / name).is_file()]
    if missing:
        raise RuntimeError(f"FF05 outputs missing: {missing}")
    summary = json.loads((latest / "01_search_summary.json").read_text(encoding="utf-8-sig"))
    if not bool(summary.get("search_complete")):
        raise RuntimeError(f"FF05 search is incomplete: {summary.get('fatal_error')}")
    if int(summary.get("cells_evaluated", -1)) != 108:
        raise RuntimeError("FF05 did not evaluate exactly 108 cells")

    used = pd.read_csv(latest / "08_input_manifest.csv")
    if set(used["timeframe"].astype(str)) != set(TARGET_FILENAMES):
        raise RuntimeError("FF05 input manifest timeframes are not exactly M5/M15/H1")
    expected_by_tf = {
        str(row["timeframe"]): row for row in merge_manifest.to_dict(orient="records")
    }
    for row in used.to_dict(orient="records"):
        timeframe = str(row["timeframe"])
        source_path = Path(str(row["source_path"])).resolve()
        if source_path != direct_paths[timeframe].resolve():
            raise RuntimeError(
                f"FF05 did not use direct merged path for {timeframe}: {source_path}"
            )
        expected = expected_by_tf[timeframe]
        if str(row["source_sha256_before"]) != str(expected["merged_sha256"]):
            raise RuntimeError(f"FF05 source SHA is not merged history for {timeframe}")
        if not bool(row["stable_exact_copy"]):
            raise RuntimeError(f"FF05 stable snapshot failed for {timeframe}")
        if int(row["rows_available_by_cutoff"]) <= 0:
            raise RuntimeError(f"no cutoff rows for {timeframe}")
    return summary, used


def rebuild_package(latest: Path, provenance: dict[str, Any]) -> None:
    (latest / PROVENANCE).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    package = latest / "99_UPLOAD_PACKAGE.zip"
    package.unlink(missing_ok=True)
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in (*ORIGINAL_PUBLIC, PROVENANCE):
            archive.write(latest / name, name)


def write_error_package(output_root: Path, exc: BaseException) -> None:
    latest = output_root / "LATEST"
    if latest.exists():
        import shutil
        shutil.rmtree(latest)
    latest.mkdir(parents=True, exist_ok=True)
    error = {
        "stage": "RECOVERY_FF05_FULL_HISTORY_RERUN_V5",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": "BLOCKED_RECOVERY_RERUN_ERROR",
        "fatal_error": f"{type(exc).__name__}: {exc}",
        "performance_result_accepted": False,
        "next_stage_authorized": False,
    }
    (latest / "00_READ_ME_FIRST.txt").write_text(
        "RECOVERY_FF05 direct full-history rerun failed.\n"
        "Upload 99_UPLOAD_PACKAGE.zip and stop.\n",
        encoding="utf-8",
    )
    (latest / "01_recovery_rerun_error.json").write_text(
        json.dumps(error, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with zipfile.ZipFile(latest / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(latest / "00_READ_ME_FIRST.txt", "00_READ_ME_FIRST.txt")
        archive.write(latest / "01_recovery_rerun_error.json", "01_recovery_rerun_error.json")


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        merge_summary, merge_manifest, cutoff, direct_paths = load_merge_contract()
        module = load_original_module()
        original_exit = run_original(module, output_root, direct_paths)
        latest = output_root / "LATEST"
        search_summary, used_manifest = validate_outputs(
            latest,
            merge_manifest,
            direct_paths,
        )
        provenance = {
            "schema_version": "btc_recovery_ff05_full_history_rerun_v5",
            "stage": "RECOVERY_FF05_FULL_HISTORY_RERUN",
            "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "input_mode": "DIRECT_VERIFIED_MERGED_PATHS_NO_DISCOVERY",
            "original_ff05_exit_code": original_exit,
            "original_ff05_overall_status": search_summary.get("overall_status"),
            "original_ff05_selection_status": search_summary.get("selection_status"),
            "original_ff05_survivor_cells": search_summary.get("survivor_cells"),
            "original_ff05_cells_evaluated": search_summary.get("cells_evaluated"),
            "merged_history_status": merge_summary.get("overall_status"),
            "direct_input_paths": {
                timeframe: str(path) for timeframe, path in direct_paths.items()
            },
            "direct_input_sha256": {
                str(row["timeframe"]): str(row["merged_sha256"])
                for row in merge_manifest.to_dict(orient="records")
            },
            "ff05_used_only_direct_verified_merged_history": True,
            "oos_coverage_proven": {
                str(row["timeframe"]): bool(row["coverage_from_oos_start"])
                for row in cutoff.to_dict(orient="records")
            },
            "raw_broker_server_cutoff_inclusive": merge_summary.get(
                "raw_broker_server_cutoff_inclusive"
            ),
            "csv_time": "BAR_OPEN_TIME",
            "time_domain": "SAME_RAW_MT5_BROKER_SERVER_WALL_CLOCK",
            "fresh_losses_used_for_tuning": False,
            "source_files_modified": False,
            "performance_rerun_executed": True,
            "result_requires_chatgpt_review": True,
            "next_stage_authorized": False,
        }
        rebuild_package(latest, provenance)
        print(
            json.dumps(
                {
                    "overall_status": search_summary.get("overall_status"),
                    "selection_status": search_summary.get("selection_status"),
                    "survivor_cells": search_summary.get("survivor_cells"),
                    "upload_package": str(latest / "99_UPLOAD_PACKAGE.zip"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if original_exit == 0 else 2
    except Exception as exc:
        write_error_package(output_root, exc)
        print(f"[RECOVERY_FF05_RERUN_V5] FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
