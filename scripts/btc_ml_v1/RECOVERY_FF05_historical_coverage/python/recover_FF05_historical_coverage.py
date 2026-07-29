from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
REFERENCE_PATH = ROOT / "configs" / "btc_ml_v1" / "btc_stacking_reproduction_reference.json"
EXPECTED_PACKAGE = "BTCUSD_HISTORY_CHAT_PACKAGE.zip"
FF05_OUTPUT = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "xauusd_signal_lab" / "btc_ml_v1" / "outputs" / "FF05_candidate_rebuild_search"
DEFAULT_OUTPUT = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "xauusd_signal_lab" / "btc_ml_v1" / "outputs" / "RECOVERY_FF05_historical_coverage"
PUBLIC = (
    "00_READ_ME_FIRST.txt",
    "01_recovery_summary.json",
    "02_recovery_report.txt",
    "03_search_candidates.csv",
    "04_verified_files.csv",
    "05_reference_requirements.json",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--extra-root", action="append", default=[])
    return parser.parse_args()


def likely_roots(extra: list[str]) -> list[Path]:
    user = Path(os.environ.get("USERPROFILE") or Path.home())
    roots = [
        user / "Downloads",
        user / "Desktop",
        user / "Documents",
        Path(r"C:\BTC_REPRO"),
        ROOT,
        Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "xauusd_signal_lab",
    ]
    ff05_manifest = FF05_OUTPUT / "LATEST" / "08_input_manifest.csv"
    if ff05_manifest.is_file():
        try:
            frame = pd.read_csv(ff05_manifest)
            for value in frame.get("source_path", []):
                roots.append(Path(str(value)).parent)
        except Exception:
            pass
    roots.extend(Path(value) for value in extra)
    seen: set[str] = set()
    result: list[Path] = []
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except Exception:
            resolved = root
        key = os.path.normcase(str(resolved))
        if key not in seen and resolved.exists():
            seen.add(key)
            result.append(resolved)
    return result


def discover(roots: list[Path], required_names: list[str]) -> list[Path]:
    found: dict[str, Path] = {}
    for root in roots:
        try:
            for path in root.rglob("BTCUSD_HISTORY_CHAT_PACKAGE*.zip"):
                if path.is_file():
                    found[os.path.normcase(str(path.resolve()))] = path.resolve()
        except Exception:
            pass
        for name in required_names:
            try:
                for path in root.rglob(name):
                    if path.is_file():
                        found[os.path.normcase(str(path.resolve()))] = path.resolve()
            except Exception:
                pass
    return sorted(found.values(), key=lambda item: str(item).lower())


def csv_metadata_from_bytes(data: bytes) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
        handle.write(data)
        temporary = Path(handle.name)
    try:
        frame = pd.read_csv(temporary, usecols=["time"])
        times = pd.to_datetime(frame["time"], errors="coerce")
        return {
            "rows": int(len(frame)),
            "first_time": "" if len(frame) == 0 else str(pd.Timestamp(times.iloc[0])),
            "last_time": "" if len(frame) == 0 else str(pd.Timestamp(times.iloc[-1])),
            "invalid_time_rows": int(times.isna().sum()),
        }
    finally:
        temporary.unlink(missing_ok=True)


def csv_metadata(path: Path) -> dict[str, Any]:
    frame = pd.read_csv(path, usecols=["time"])
    times = pd.to_datetime(frame["time"], errors="coerce")
    return {
        "rows": int(len(frame)),
        "first_time": "" if len(frame) == 0 else str(pd.Timestamp(times.iloc[0])),
        "last_time": "" if len(frame) == 0 else str(pd.Timestamp(times.iloc[-1])),
        "invalid_time_rows": int(times.isna().sum()),
    }


def atomic_latest(source: Path, latest: Path) -> None:
    temporary = latest.parent / f"LATEST.__new__.{os.getpid()}"
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(source, temporary)
    if latest.exists():
        shutil.rmtree(latest)
    os.replace(temporary, latest)


def main() -> int:
    args = parse_args()
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    required = reference["required_csv"]
    required_names = [name for name in required if name != "btcusdsharp_h4_warmup.csv"]
    package_sha = reference["input_packages"][EXPECTED_PACKAGE]["sha256"]
    roots = likely_roots(args.extra_root)
    paths = discover(roots, required_names)

    candidates: list[dict[str, Any]] = []
    verified: dict[str, dict[str, Any]] = {}
    package_matches: list[str] = []
    package_member_bytes: dict[str, bytes] = {}

    for path in paths:
        row: dict[str, Any] = {
            "kind": "ZIP" if path.suffix.lower() == ".zip" else "CSV",
            "path": str(path),
            "filename": path.name,
            "size_bytes": int(path.stat().st_size),
            "sha256": "",
            "exact_reference_match": False,
            "read_error": "",
        }
        try:
            row["sha256"] = sha256_path(path)
            if row["kind"] == "ZIP":
                row["exact_reference_match"] = row["sha256"] == package_sha
                if row["exact_reference_match"]:
                    package_matches.append(str(path))
                    with zipfile.ZipFile(path) as archive:
                        by_base: dict[str, str] = {}
                        accepted = {name.lower() for name in required_names}
                        for name in archive.namelist():
                            base = Path(name).name.lower()
                            if base in accepted:
                                if base in by_base:
                                    raise RuntimeError(f"duplicate member basename in package: {base}")
                                by_base[base] = name
                        for required_name in required_names:
                            member = by_base.get(required_name.lower())
                            if member is not None:
                                package_member_bytes[required_name] = archive.read(member)
            else:
                expected = required.get(path.name)
                if expected is not None:
                    row["exact_reference_match"] = row["sha256"] == expected["sha256"]
                    if row["exact_reference_match"]:
                        verified[path.name] = {
                            "filename": path.name,
                            "source": str(path),
                            "source_type": "INDIVIDUAL_CSV",
                            "sha256": row["sha256"],
                            **csv_metadata(path),
                        }
        except Exception as exc:
            row["read_error"] = f"{type(exc).__name__}: {exc}"
        candidates.append(row)

    for name, data in package_member_bytes.items():
        expected = required[name]
        actual_sha = sha256_bytes(data)
        if actual_sha == expected["sha256"]:
            verified[name] = {
                "filename": name,
                "source": package_matches[0] if package_matches else "",
                "source_type": "EXACT_REFERENCE_ZIP",
                "sha256": actual_sha,
                **csv_metadata_from_bytes(data),
            }

    required_ff05 = ("btcusdsharp_m5.csv", "btcusdsharp_m15.csv", "btcusdsharp_h1.csv")
    ready = all(name in verified for name in required_ff05)
    output_root = Path(args.output_root).expanduser().resolve()
    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f_UTC")
    archive_dir = output_root / "archive" / run_id
    latest = output_root / "LATEST"
    restored = output_root / "RESTORED_EXACT_REFERENCE"
    archive_dir.mkdir(parents=True, exist_ok=False)

    if ready:
        temporary = output_root / f"RESTORED_EXACT_REFERENCE.__new__.{os.getpid()}"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(parents=True)
        for name in required_names:
            if name in package_member_bytes and sha256_bytes(package_member_bytes[name]) == required[name]["sha256"]:
                (temporary / name).write_bytes(package_member_bytes[name])
            elif name in verified:
                shutil.copy2(Path(verified[name]["source"]), temporary / name)
        if restored.exists():
            shutil.rmtree(restored)
        os.replace(temporary, restored)

    ff05_manifest_path = FF05_OUTPUT / "LATEST" / "08_input_manifest.csv"
    ff05_coverage: list[dict[str, Any]] = []
    if ff05_manifest_path.is_file():
        ff05_coverage = pd.read_csv(ff05_manifest_path).to_dict(orient="records")

    status = "READY_EXACT_HISTORY_RECOVERED" if ready else "BLOCKED_EXACT_HISTORY_NOT_FOUND"
    summary = {
        "schema_version": "btc_recovery_ff05_historical_coverage_v1",
        "stage": "RECOVERY_FF05_HISTORICAL_COVERAGE",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": status,
        "search_complete": True,
        "search_roots": [str(root) for root in roots],
        "candidate_paths_found": len(candidates),
        "exact_package_matches": package_matches,
        "verified_required_files": sorted(verified),
        "required_for_ff05": list(required_ff05),
        "restored_history_dir": str(restored) if ready else None,
        "ff05_previous_result_reclassification": "BLOCKED_INCOMPLETE_OOS_COVERAGE_NOT_FORMAL_NO_CANDIDATE",
        "ff05_current_input_coverage": ff05_coverage,
        "performance_rerun_executed": False,
        "source_files_modified": False,
        "next_stage_authorized": False,
    }

    candidate_frame = pd.DataFrame(candidates)
    verified_frame = pd.DataFrame(list(verified.values()))
    (archive_dir / "00_READ_ME_FIRST.txt").write_text(
        "\n".join([
            "RECOVERY_FF05 historical coverage",
            "=================================",
            f"overall_status: {status}",
            "",
            "This recovery searches for the exact frozen BTC history package or exact required CSV hashes.",
            "It does not rerun FF05 and does not alter source files.",
            "Upload only 99_UPLOAD_PACKAGE.zip and stop.",
        ]) + "\n",
        encoding="utf-8",
    )
    (archive_dir / "01_recovery_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    (archive_dir / "02_recovery_report.txt").write_text(
        "\n".join([
            "RECOVERY_FF05 historical coverage",
            "=================================",
            f"overall_status: {status}",
            f"candidate_paths_found: {len(candidates)}",
            f"exact_package_matches: {package_matches or ['NONE']}",
            f"verified_required_files: {sorted(verified) or ['NONE']}",
            "",
            "The submitted FF05 run cannot be finalized as NO_CANDIDATE because OOS01/OOS02 had no M5/M15 coverage.",
            "No performance rerun was executed.",
            "STOP: upload 99_UPLOAD_PACKAGE.zip.",
        ]) + "\n",
        encoding="utf-8",
    )
    candidate_frame.to_csv(archive_dir / "03_search_candidates.csv", index=False, encoding="utf-8-sig")
    verified_frame.to_csv(archive_dir / "04_verified_files.csv", index=False, encoding="utf-8-sig")
    (archive_dir / "05_reference_requirements.json").write_text(
        json.dumps({
            "expected_package": EXPECTED_PACKAGE,
            "expected_package_sha256": package_sha,
            "required_csv": required,
        }, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    package = archive_dir / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in PUBLIC:
            archive.write(archive_dir / name, name)
    atomic_latest(archive_dir, latest)
    print(json.dumps({
        "overall_status": status,
        "upload_package": str(latest / package.name),
        "restored_history_dir": str(restored) if ready else None,
    }, ensure_ascii=False, indent=2))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
