#!/usr/bin/env python3
"""Verify and install the GOLD_ML_V1 exact handoff artifact bundle.

Audit-only utility. It does not generate signals or change candidate logic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_files(locator: dict) -> dict[str, str]:
    result: dict[str, str] = {}
    for filename, digest in locator["trade_registries"].values():
        result[filename] = digest
    for value in locator["prov015_parent_events"].values():
        result[value[0]] = value[1]
    for value in locator["watch014"].values():
        result[value[0]] = value[1]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--locator",
        type=Path,
        default=Path("config/gold_ml_v1/exact_artifact_locator_20260625.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("config/gold_ml_v1/registries"),
    )
    args = parser.parse_args()

    locator = json.loads(args.locator.read_text(encoding="utf-8"))
    bundle = args.bundle.resolve()
    expected_bundle_sha = locator["bundle"]["sha256"]
    actual_bundle_sha = sha256_file(bundle)
    if actual_bundle_sha != expected_bundle_sha:
        raise SystemExit(
            f"bundle SHA256 mismatch: expected={expected_bundle_sha} actual={actual_bundle_sha}"
        )

    expected = expected_files(locator)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        missing = sorted(set(expected) - names)
        if missing:
            raise SystemExit(f"bundle is missing required files: {missing}")
        for filename, expected_sha in expected.items():
            if Path(filename).name != filename:
                raise SystemExit(f"unsafe archive member: {filename}")
            destination = output_dir / filename
            with archive.open(filename) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            actual_sha = sha256_file(destination)
            if actual_sha != expected_sha:
                destination.unlink(missing_ok=True)
                raise SystemExit(
                    f"artifact SHA256 mismatch for {filename}: "
                    f"expected={expected_sha} actual={actual_sha}"
                )

    installed = {
        "status": "PASS",
        "audit_only": True,
        "bundle": str(bundle),
        "bundle_sha256": actual_bundle_sha,
        "output_dir": str(output_dir),
        "installed_files": expected,
    }
    report = output_dir / "installation_manifest.json"
    report.write_text(json.dumps(installed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(installed, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
