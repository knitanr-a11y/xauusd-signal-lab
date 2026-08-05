#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "runtime" / "btc_ai_v1" / "full95_all_q20_shadow_v1"
FROZEN_MANIFEST = PACKAGE_ROOT / "config" / "frozen_manifest.json"
MATERIALIZER = PACKAGE_ROOT / "bootstrap" / "materialize_assets.py"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def expected_lf_candidate(raw: bytes, expected_hash: str) -> bytes | None:
    candidates = []
    if b"\r\n" in raw:
        candidates.append(raw.replace(b"\r\n", b"\n"))
    if b"\r" in raw:
        candidates.append(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    for candidate in candidates:
        if sha256(candidate) == expected_hash:
            return candidate
    return None


def main() -> int:
    if not PACKAGE_ROOT.is_dir() or not FROZEN_MANIFEST.is_file():
        print(f"PACKAGE_NOT_FOUND: {PACKAGE_ROOT}")
        return 2

    subprocess.run([sys.executable, str(MATERIALIZER)], cwd=str(PACKAGE_ROOT), check=True)

    manifest = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    repaired: list[str] = []
    unresolved: list[dict[str, str]] = []

    for item in manifest["assets"]:
        relative = item["path"]
        expected = item["sha256"]
        path = PACKAGE_ROOT / relative
        if not path.is_file():
            unresolved.append({"path": relative, "reason": "MISSING"})
            continue

        raw = path.read_bytes()
        actual = sha256(raw)
        if actual == expected:
            continue

        candidate = expected_lf_candidate(raw, expected)
        if candidate is None:
            unresolved.append({"path": relative, "expected": expected, "actual": actual})
            continue

        atomic_write(path, candidate)
        if sha256(path.read_bytes()) != expected:
            unresolved.append({"path": relative, "reason": "POST_WRITE_HASH_MISMATCH"})
            continue
        repaired.append(relative)

    if unresolved:
        print("WINDOWS_CHECKOUT_REPAIR_INCOMPLETE")
        print(json.dumps(unresolved, ensure_ascii=False, indent=2))
        return 20

    print(json.dumps({
        "status": "WINDOWS_CHECKOUT_REPAIRED_AND_FROZEN_HASHES_MATCH",
        "repaired_count": len(repaired),
        "repaired_paths": repaired,
        "activation_created": False
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
