from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

EXPECTED_ZIP_SHA256 = "d1e9ab8cbeb7d73c8cf75f688bad39af0d64982901fbcd4474c1b230802b53b9"
SUPPORT_FILES = {
    "GML1-PROV-015_parent_event_registry_all_available.csv": {
        "sha256": "1b16b9200eaccab701c32614fb9240ed30e753d40b61b6c9e25e69a765e7b180",
        "rows": 254,
    },
    "GML1-WATCH-014-A_54_feature_registry.csv": {
        "sha256": "81695541d57e8aef16ebd6732d3b7829516524e2a7539ef995abca17f1cc0f65",
        "rows": 225,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", errors="strict") as f:
        count = sum(1 for _ in f)
    return max(0, count - 1)


def find_one(root: Path, filename: str) -> Path:
    matches = [p for p in root.rglob(filename) if p.is_file()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {filename}, found {len(matches)}")
    return matches[0]


def install(zip_path: Path, repo_root: Path) -> None:
    actual_zip_hash = sha256_file(zip_path)
    if actual_zip_hash != EXPECTED_ZIP_SHA256:
        raise RuntimeError(
            f"Batch023 ZIP SHA mismatch: expected={EXPECTED_ZIP_SHA256} actual={actual_zip_hash}"
        )

    expected_manifest_path = repo_root / "config/gold_ml_v1/replay/nine_candidate_expected_sha256_20260625.json"
    if not expected_manifest_path.exists():
        raise RuntimeError(f"Missing repository manifest: {expected_manifest_path}")
    manifest = json.loads(expected_manifest_path.read_text(encoding="utf-8"))
    required = {
        item["filename"]: {"sha256": item["sha256"], "rows": item["rows"]}
        for item in manifest["expected_registries"].values()
    }
    required.update(SUPPORT_FILES)

    target = repo_root / "config/gold_ml_v1/registries"
    target.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="gml1_batch023_") as tmp:
        temp_root = Path(tmp)
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"Corrupt ZIP member: {bad}")
            archive.extractall(temp_root)

        installed = []
        for filename, expected in required.items():
            source = find_one(temp_root, filename)
            actual_hash = sha256_file(source)
            actual_rows = count_csv_rows(source)
            if actual_hash != expected["sha256"]:
                raise RuntimeError(
                    f"SHA mismatch for {filename}: expected={expected['sha256']} actual={actual_hash}"
                )
            if actual_rows != expected["rows"]:
                raise RuntimeError(
                    f"Row mismatch for {filename}: expected={expected['rows']} actual={actual_rows}"
                )
            destination = target / filename
            shutil.copy2(source, destination)
            installed.append({
                "filename": filename,
                "sha256": actual_hash,
                "rows": actual_rows,
                "destination": str(destination),
            })

    report_path = target / "BATCH023_INSTALLED_ARTIFACTS.json"
    report_path.write_text(
        json.dumps({
            "status": "PASS",
            "source_zip": str(zip_path.resolve()),
            "source_zip_sha256": actual_zip_hash,
            "installed": installed,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Installed {len(installed)} verified files into {target}")
    print(report_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    args = parser.parse_args()
    try:
        install(args.zip_path.resolve(), args.repo_root.resolve())
        return 0
    except Exception as exc:
        print(f"INSTALL FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
