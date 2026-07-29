from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL_RUNNER = (
    ROOT
    / "scripts"
    / "btc_ml_v1"
    / "FF05_candidate_rebuild_search"
    / "python"
    / "run_FF05_candidate_rebuild_search.py"
)
LOCAL_BASE = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "xauusd_signal_lab" / "btc_ml_v1" / "outputs"
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


def ensure_preflight() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    if not ORIGINAL_RUNNER.is_file():
        raise FileNotFoundError(f"FF05 runner not found: {ORIGINAL_RUNNER}")
    summary_path = MERGE_LATEST / "01_merge_summary.json"
    manifest_path = MERGE_LATEST / "03_merge_manifest.csv"
    cutoff_path = MERGE_LATEST / "05_cutoff_coverage.csv"
    for path in (summary_path, manifest_path, cutoff_path):
        if not path.is_file():
            raise FileNotFoundError(f"required merge result missing: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    if summary.get("overall_status") != "READY_FULL_HISTORY_MERGED":
        raise RuntimeError(f"merge status is not ready: {summary.get('overall_status')}")
    if not bool(summary.get("merge_complete")):
        raise RuntimeError("merge_complete is false")
    if summary.get("reference_and_current_time_domain") != "SAME_RAW_MT5_BROKER_SERVER_WALL_CLOCK":
        raise RuntimeError("time domain is not frozen as same raw MT5 broker-server clock")

    manifest = pd.read_csv(manifest_path)
    cutoff = pd.read_csv(cutoff_path)
    expected_timeframes = {"M5", "M15", "H1"}
    if set(manifest["timeframe"].astype(str)) != expected_timeframes:
        raise RuntimeError("merge manifest timeframes are not exactly M5/M15/H1")
    if set(cutoff["timeframe"].astype(str)) != expected_timeframes:
        raise RuntimeError("cutoff coverage timeframes are not exactly M5/M15/H1")
    if not cutoff["coverage_from_oos_start"].astype(bool).all():
        raise RuntimeError("full OOS coverage is not proven for all timeframes")

    for row in manifest.to_dict(orient="records"):
        path = Path(str(row["merged_path"]))
        expected_path = MERGED_DIR / path.name
        if path.resolve() != expected_path.resolve():
            raise RuntimeError(f"unexpected merged path: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"merged CSV missing: {path}")
        actual_sha = sha256_path(path)
        if actual_sha != str(row["merged_sha256"]):
            raise RuntimeError(
                f"merged SHA mismatch for {row['timeframe']}: "
                f"expected={row['merged_sha256']} actual={actual_sha}"
            )
    return summary, manifest, cutoff


def create_isolated_terminal(
    output_root: Path,
    manifest: pd.DataFrame,
) -> tuple[Path, dict[str, str], dict[str, str]]:
    """
    Build a complete isolated Windows profile.

    FF05 discovery may derive the MT5 root from APPDATA or from
    USERPROFILE/Path.home()/AppData/Roaming. The first recovery attempt
    overrode APPDATA only, so Path.home() still resolved to the real user and
    the normal terminal CSV was selected. This layout and environment cover
    both discovery routes without touching the real terminal files.
    """
    profile_root = output_root / "_isolated_profile"
    if profile_root.exists():
        shutil.rmtree(profile_root)

    appdata_roaming = profile_root / "AppData" / "Roaming"
    local_appdata = profile_root / "AppData" / "Local"
    temp_root = local_appdata / "Temp"

    terminal_roots = (
        appdata_roaming
        / "MetaQuotes"
        / "Terminal"
        / "FF05_MERGED_FULL_HISTORY"
        / "MQL5"
        / "Files",
        profile_root
        / "MetaQuotes"
        / "Terminal"
        / "FF05_MERGED_FULL_HISTORY"
        / "MQL5"
        / "Files",
    )
    for files_dir in terminal_roots:
        files_dir.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}
    for row in manifest.to_dict(orient="records"):
        source = Path(str(row["merged_path"]))
        primary_target = terminal_roots[0] / source.name
        for files_dir in terminal_roots:
            target = files_dir / source.name
            shutil.copyfile(source, target)
            os.utime(target, None)
            actual_sha = sha256_path(target)
            if actual_sha != str(row["merged_sha256"]):
                raise RuntimeError(f"isolated copy SHA mismatch: {target}")
        copied[str(row["timeframe"])] = str(primary_target)

    environment_paths = {
        "USERPROFILE": str(profile_root),
        "HOME": str(profile_root),
        "APPDATA": str(appdata_roaming),
        "LOCALAPPDATA": str(local_appdata),
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
    }
    return profile_root, copied, environment_paths


def validate_original_outputs(
    latest: Path,
    isolated_root: Path,
    merge_manifest: pd.DataFrame,
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
    if set(used["timeframe"].astype(str)) != {"M5", "M15", "H1"}:
        raise RuntimeError("FF05 input manifest timeframes are not exactly M5/M15/H1")
    expected_by_tf = {
        str(row["timeframe"]): row for row in merge_manifest.to_dict(orient="records")
    }
    isolated_norm = os.path.normcase(str(isolated_root.resolve()))
    for row in used.to_dict(orient="records"):
        timeframe = str(row["timeframe"])
        expected = expected_by_tf[timeframe]
        source_path = Path(str(row["source_path"])).resolve()
        if not os.path.normcase(str(source_path)).startswith(isolated_norm + os.sep):
            raise RuntimeError(
                f"FF05 used a non-isolated source for {timeframe}: {source_path}"
            )
        if str(row["source_sha256_before"]) != str(expected["merged_sha256"]):
            raise RuntimeError(
                f"FF05 source SHA is not merged history for {timeframe}"
            )
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
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in (*ORIGINAL_PUBLIC, PROVENANCE):
            archive.write(latest / name, name)


def write_error_package(output_root: Path, exc: BaseException) -> None:
    latest = output_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    latest.mkdir(parents=True, exist_ok=True)
    error = {
        "stage": "RECOVERY_FF05_FULL_HISTORY_RERUN",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": "BLOCKED_RECOVERY_RERUN_ERROR",
        "fatal_error": f"{type(exc).__name__}: {exc}",
        "performance_result_accepted": False,
        "next_stage_authorized": False,
    }
    (latest / "00_READ_ME_FIRST.txt").write_text(
        "RECOVERY_FF05 full-history rerun failed.\n"
        "Upload 99_UPLOAD_PACKAGE.zip and stop.\n",
        encoding="utf-8",
    )
    (latest / "01_recovery_rerun_error.json").write_text(
        json.dumps(error, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with zipfile.ZipFile(latest / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(latest / "00_READ_ME_FIRST.txt", "00_READ_ME_FIRST.txt")
        archive.write(
            latest / "01_recovery_rerun_error.json",
            "01_recovery_rerun_error.json",
        )


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    isolated_root: Path | None = None
    try:
        merge_summary, merge_manifest, cutoff = ensure_preflight()
        isolated_root, copied, isolated_environment = create_isolated_terminal(
            output_root,
            merge_manifest,
        )
        environment = os.environ.copy()
        environment.update(isolated_environment)
        environment["BTC_FF05_RECOVERY_MODE"] = "MERGED_FULL_HISTORY_ISOLATED_PROFILE_V2"
        command = [
            sys.executable,
            str(ORIGINAL_RUNNER),
            "--output-root",
            str(output_root),
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=False,
        )
        latest = output_root / "LATEST"
        search_summary, used_manifest = validate_original_outputs(
            latest,
            isolated_root,
            merge_manifest,
        )
        provenance = {
            "schema_version": "btc_recovery_ff05_full_history_rerun_v2",
            "stage": "RECOVERY_FF05_FULL_HISTORY_RERUN",
            "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "original_ff05_exit_code": int(completed.returncode),
            "original_ff05_overall_status": search_summary.get("overall_status"),
            "original_ff05_selection_status": search_summary.get("selection_status"),
            "original_ff05_survivor_cells": search_summary.get("survivor_cells"),
            "original_ff05_cells_evaluated": search_summary.get("cells_evaluated"),
            "merged_history_status": merge_summary.get("overall_status"),
            "merged_history_dir": str(MERGED_DIR),
            "merged_input_sha256": {
                str(row["timeframe"]): str(row["merged_sha256"])
                for row in merge_manifest.to_dict(orient="records")
            },
            "isolated_source_paths": copied,
            "isolated_environment": isolated_environment,
            "ff05_used_only_isolated_merged_history": True,
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
        if isolated_root.exists():
            shutil.rmtree(isolated_root)
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
        return 0 if completed.returncode == 0 else 2
    except Exception as exc:
        if isolated_root is not None and isolated_root.exists():
            shutil.rmtree(isolated_root, ignore_errors=True)
        write_error_package(output_root, exc)
        print(f"[RECOVERY_FF05_RERUN] FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
