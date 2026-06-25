from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

EXPECTED_PACKAGE_SHA256 = "d1e9ab8cbeb7d73c8cf75f688bad39af0d64982901fbcd4474c1b230802b53b9"
PACKAGE_ROOT_NAME = "gold_ml_v1_batch023_local_replay_20260625"
EXPECTED_SUBDIR = f"{PACKAGE_ROOT_NAME}/expected"
REQUIRED_CANDIDATES = [
    "GML1-PROV-007",
    "GML1-PROV-008",
    "GML1-WATCH-022-B",
    "GML1-PROV-010",
    "GML1-PROV-015",
    "GML1-PROV-020",
    "GML1-WATCH-021-A",
    "GML1-WATCH-021-B",
    "GML1-WATCH-021-C",
]
EXPECTED_FILES = [f"{candidate}_exact_trade_registry.csv" for candidate in REQUIRED_CANDIDATES]
RAW_HASHES = {
    "gold_v3_2023_2026_m1.csv": "dec61b435ceb1df687baced57862de214793e0270e30c67d84f510f9f119b9d2",
    "gold_v3_2023_2026_m5.csv": "c47c0a136e8a953bf219bfbcb80a79ccacac3afb04a0ed6e825843eba143948d",
    "gold_v3_2023_2026_m15.csv": "e327bedd180dae6429ed658ea714bc1229fb026262124248cdd5fff38fdeaa28",
    "gold_v3_2023_2026_h1.csv": "fb9d4ad228c02383a14ac86309f7306a799b0ef8d076f015a72b70daaddafc4a",
    "gold_v3_2023_2026_h4.csv": "5cd0d4427c752bd3feffd17b91fbd1ed3cd35ee5210887fa1726f01184367913",
    "gold_v3_2023_2026_d1.csv": "58d9b8e6716b3dedf4d310b3de5a914ab062c50578bae54dc85a2c8fddf689f6",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_default_zip() -> Path | None:
    candidates = [
        Path.home() / "Downloads" / "GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip",
        Path.home() / "Desktop" / "GOLD_ML_V1_BATCH023_NINE_CANDIDATE_LOCAL_REPLAY_20260625.zip",
    ]
    return next((path for path in candidates if path.exists()), None)


def verify_raw(raw_dir: Path, allow_hash_mismatch: bool) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    missing: list[str] = []
    mismatched: list[str] = []
    for filename, expected_hash in RAW_HASHES.items():
        path = raw_dir / filename
        if not path.exists():
            missing.append(filename)
            continue
        actual_hash = sha256_file(path)
        match = actual_hash == expected_hash
        if not match:
            mismatched.append(filename)
        audits.append(
            {
                "filename": filename,
                "bytes": path.stat().st_size,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "sha256_match": match,
            }
        )
    if missing:
        raise FileNotFoundError(f"Missing raw CSV files: {missing}")
    if mismatched and not allow_hash_mismatch:
        raise RuntimeError(
            "Raw CSV SHA256 mismatch. This Batch023 implementation is frozen to the audited raw snapshot. "
            f"Mismatched files: {mismatched}. Use --allow-raw-hash-mismatch only for a separately reviewed run."
        )
    return audits


def verify_package_zip(zip_path: Path) -> str:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    actual_hash = sha256_file(zip_path)
    if actual_hash != EXPECTED_PACKAGE_SHA256:
        raise RuntimeError(
            f"Batch023 ZIP SHA256 mismatch: expected={EXPECTED_PACKAGE_SHA256} actual={actual_hash}"
        )
    with zipfile.ZipFile(zip_path) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise RuntimeError(f"Corrupt ZIP member: {corrupt}")
        names = set(archive.namelist())
        missing = [f"{EXPECTED_SUBDIR}/{name}" for name in EXPECTED_FILES if f"{EXPECTED_SUBDIR}/{name}" not in names]
        if missing:
            raise RuntimeError(f"Batch023 ZIP is missing expected registries: {missing}")
    return actual_hash


def load_reconstruction_module() -> Any:
    script_path = Path(__file__).with_name("batch023_warmup_bridge_reconstruction.py")
    spec = importlib.util.spec_from_file_location("batch023_warmup_bridge_reconstruction", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def backup_previous_output(output_dir: Path) -> Path | None:
    if not output_dir.exists() or not any(output_dir.iterdir()):
        output_dir.mkdir(parents=True, exist_ok=True)
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = output_dir.parent / f"{output_dir.name}_previous_{timestamp}"
    shutil.move(str(output_dir), str(backup))
    output_dir.mkdir(parents=True, exist_ok=True)
    return backup


def write_latest_summary(
    output_dir: Path,
    exit_code: int,
    package_hash: str,
    raw_audit: list[dict[str, Any]],
    backup_dir: Path | None,
) -> None:
    parity_path = output_dir / "warmup_bridge_parity_report.csv"
    lines = [
        "GOLD_ML_V1 Batch023 Local Warmup Bridge",
        f"status={'PASS' if exit_code == 0 else 'FAIL'}",
        f"exit_code={exit_code}",
        f"run_time_local={datetime.now().isoformat(timespec='seconds')}",
        f"batch023_zip_sha256={package_hash}",
        f"previous_output_backup={backup_dir or ''}",
        "audit_only=true",
        "live_ready=false",
        "warmup_bridge_rows_live_forbidden=true",
        "",
        "Raw SHA256:",
    ]
    for row in raw_audit:
        lines.append(f"{row['filename']}={row['actual_sha256']} match={row['sha256_match']}")
    lines.extend(["", f"parity_report={parity_path}"])
    if parity_path.exists():
        lines.extend(["", parity_path.read_text(encoding="utf-8")])
    (output_dir / "LATEST_RUN_SUMMARY.txt").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    raw_dir = args.raw_dir.resolve()
    zip_path = args.zip_path or locate_default_zip()
    if zip_path is None:
        raise FileNotFoundError(
            "Batch023 ZIP was not found in Downloads or Desktop. Pass --zip explicitly."
        )
    zip_path = zip_path.resolve()
    output_dir = args.output_dir.resolve()

    raw_audit = verify_raw(raw_dir, args.allow_raw_hash_mismatch)
    package_hash = verify_package_zip(zip_path)
    backup_dir = backup_previous_output(output_dir)

    with tempfile.TemporaryDirectory(prefix="gml1b23bridge_") as temp_name:
        temp_root = Path(temp_name)
        expected_dir = temp_root / "expected"
        expected_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            for filename in EXPECTED_FILES:
                member = f"{EXPECTED_SUBDIR}/{filename}"
                target = expected_dir / filename
                with archive.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)

        module = load_reconstruction_module()
        exit_code = int(module.run(raw_dir, expected_dir, output_dir))

    metadata = {
        "status": "PASS" if exit_code == 0 else "FAIL",
        "exit_code": exit_code,
        "run_time_local": datetime.now().isoformat(timespec="seconds"),
        "raw_dir": str(raw_dir),
        "batch023_zip": str(zip_path),
        "batch023_zip_sha256": package_hash,
        "output_dir": str(output_dir),
        "previous_output_backup": str(backup_dir) if backup_dir else None,
        "raw_audit": raw_audit,
        "policy": {
            "audit_only": True,
            "raw_time": "bar-open time in MT5 server time",
            "warmup_bridge_exact_live_use": False,
            "raw_only_parity": False,
        },
    }
    (output_dir / "local_run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_latest_summary(output_dir, exit_code, package_hash, raw_audit, backup_dir)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Batch023 warmup bridge locally")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--zip", dest="zip_path", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/gold_ml_v1/batch023_warmup_bridge_local"),
    )
    parser.add_argument("--allow-raw-hash-mismatch", action="store_true")
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "LOCAL_RUN_ERROR.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
