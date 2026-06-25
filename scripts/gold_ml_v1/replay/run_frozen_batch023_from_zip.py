from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED_ZIP_SHA256 = "d1e9ab8cbeb7d73c8cf75f688bad39af0d64982901fbcd4474c1b230802b53b9"
PACKAGE_DIRNAME = "gold_ml_v1_batch023_local_replay_20260625"
SCRIPT_NAME = "replay_nine_candidates.py"
REQUIRED_PACKAGE_MEMBERS = [
    f"{PACKAGE_DIRNAME}/BATCH023_STATUS.json",
    f"{PACKAGE_DIRNAME}/PACKAGE_MANIFEST.json",
    f"{PACKAGE_DIRNAME}/config/nine_candidate_replay_config.json",
    f"{PACKAGE_DIRNAME}/{SCRIPT_NAME}",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_default_zip() -> Path:
    candidates = [
        Path.home() / "Downloads" / "GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip",
        Path.home() / "Desktop" / "GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Batch023 ZIP was not found in Downloads or Desktop. Pass --zip explicitly."
    )


def verify_historical_inputs(historical_dir: Path) -> None:
    required = [
        "gold_v3_2023_2026_m1.csv",
        "gold_v3_2023_2026_m15.csv",
        "gold_v3_2023_2026_h1.csv",
        "gold_v3_2023_2026_h4.csv",
        "gold_v3_2023_2026_d1.csv",
    ]
    missing = [name for name in required if not (historical_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing historical files under {historical_dir}: {missing}"
        )


def verify_zip_members(archive: zipfile.ZipFile) -> None:
    members = set(archive.namelist())
    missing = [name for name in REQUIRED_PACKAGE_MEMBERS if name not in members]
    if missing:
        raise RuntimeError(f"Verified ZIP is missing required package members: {missing}")


def run_frozen(
    zip_path: Path,
    historical_dir: Path,
    output_dir: Path,
) -> int:
    zip_path = zip_path.resolve()
    historical_dir = historical_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    verify_historical_inputs(historical_dir)

    actual_sha = sha256_file(zip_path)
    if actual_sha != EXPECTED_ZIP_SHA256:
        raise RuntimeError(
            f"Batch023 ZIP SHA mismatch: expected={EXPECTED_ZIP_SHA256} actual={actual_sha}"
        )

    # The repository path is very deep under MetaQuotes. Extracting below the
    # repository exceeded the classic Windows MAX_PATH limit. Use the short
    # system temporary directory and delete it automatically after execution.
    with tempfile.TemporaryDirectory(prefix="gml1b23_") as temp_name:
        runtime_dir = Path(temp_name)
        with zipfile.ZipFile(zip_path) as archive:
            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise RuntimeError(f"Corrupt ZIP member: {corrupt_member}")
            verify_zip_members(archive)
            archive.extractall(runtime_dir)

        package_root = runtime_dir / PACKAGE_DIRNAME
        frozen_script = package_root / SCRIPT_NAME
        status_file = package_root / "BATCH023_STATUS.json"
        if not frozen_script.exists():
            raise FileNotFoundError(frozen_script)
        if not status_file.exists():
            raise FileNotFoundError(status_file)

        command = [
            sys.executable,
            str(frozen_script),
            "--package-root",
            str(package_root),
            "--raw-dir",
            str(historical_dir),
            "--output-dir",
            str(output_dir / "results"),
            "--mode",
            "raw",
        ]

        metadata = {
            "status": "STARTED",
            "zip_path": str(zip_path),
            "zip_sha256": actual_sha,
            "historical_dir": str(historical_dir),
            "temporary_package_root": str(package_root),
            "frozen_script": str(frozen_script),
            "command": command,
            "policy": {
                "evaluator": "verbatim script extracted from the verified Batch023 ZIP",
                "raw_source": "gold_v3_2023_2026 directory only",
                "goldsharp_in_historical_replay": False,
                "time_contract": "raw CSV time is bar-open time",
                "temporary_extraction": "system TEMP to avoid Windows MAX_PATH",
            },
        }
        (output_dir / "frozen_run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        completed = subprocess.run(
            command,
            cwd=str(package_root),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        (output_dir / "frozen_stdout.txt").write_text(
            completed.stdout, encoding="utf-8"
        )
        (output_dir / "frozen_stderr.txt").write_text(
            completed.stderr, encoding="utf-8"
        )
        print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")

        metadata["status"] = "PASS" if completed.returncode == 0 else "FAIL"
        metadata["exit_code"] = completed.returncode
        (output_dir / "frozen_run_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the original frozen Batch023 evaluator from the verified ZIP"
    )
    parser.add_argument("--historical-dir", type=Path, required=True)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/gold_ml_v1/batch023_frozen_exact_replay"),
    )
    args = parser.parse_args()

    try:
        zip_path = args.zip_path or locate_default_zip()
        return run_frozen(zip_path, args.historical_dir, args.output_dir)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "launcher_error.txt").write_text(
            repr(exc), encoding="utf-8"
        )
        print(f"FROZEN BATCH023 LAUNCH FAILED: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
