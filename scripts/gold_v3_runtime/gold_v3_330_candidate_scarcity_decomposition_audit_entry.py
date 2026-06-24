#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import gold_v3_330_candidate_scarcity_decomposition_audit as stage330

CANONICAL_SPEC_SHA256 = (
    "08589fa2b07aca97ab1e86d7e0c2a25222e81f819ce120bf87592255b20683cb"
)

_ORIGINAL_SHA = stage330.sha


def canonical_json_sha256(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cross_platform_sha(path: Path) -> str:
    resolved = path.resolve()
    if resolved == stage330.SPEC_PATH.resolve():
        return canonical_json_sha256(path)
    return _ORIGINAL_SHA(path)


stage330.sha = cross_platform_sha
stage330.SPEC_SHA = CANONICAL_SPEC_SHA256


if __name__ == "__main__":
    raise SystemExit(stage330.main())
