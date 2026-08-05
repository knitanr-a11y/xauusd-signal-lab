#!/usr/bin/env python3
"""Install the frozen BTC day-open matched-pair Shadow V1 package."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts/btc_ai_v1/shadow_day_open_matched_pair_v1"
DEPLOYMENT_MANIFEST = REPO_ROOT / "config/btc_ai_v1/shadow_day_open_matched_pair_v1/deployment_manifest_20260805.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    deployment = json.loads(DEPLOYMENT_MANIFEST.read_text(encoding="utf-8"))
    chunks = []
    for part in deployment["parts"]:
        path = REPO_ROOT / part["path"]
        data = path.read_bytes()
        if sha256_bytes(data) != part["sha256"] or len(data) != part["size"]:
            raise RuntimeError(f"package part verification failed: {path}")
        chunks.append(data)
    archive = b"".join(chunks)
    if sha256_bytes(archive) != deployment["archive_sha256"]:
        raise RuntimeError("assembled package SHA256 mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "shadow.zip"
        archive_path.write_bytes(archive)
        with zipfile.ZipFile(archive_path) as bundle:
            for member in bundle.infolist():
                target = (REPO_ROOT / member.filename).resolve()
                if REPO_ROOT not in target.parents and target != REPO_ROOT:
                    raise RuntimeError(f"unsafe archive member: {member.filename}")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                incoming = bundle.read(member)
                if target.exists():
                    if target.read_bytes() != incoming:
                        raise RuntimeError(f"refusing to overwrite non-identical frozen file: {target}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(incoming)
    runtime = REPO_ROOT / "scripts/btc_ai_v1/shadow_day_open_matched_pair_v1.py"
    check = subprocess.run([sys.executable, str(runtime), "verify-frozen"], cwd=REPO_ROOT)
    if check.returncode != 0:
        raise RuntimeError("installed frozen asset verification failed")
    print("SHADOW_V1_PACKAGE_INSTALLED_AND_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
