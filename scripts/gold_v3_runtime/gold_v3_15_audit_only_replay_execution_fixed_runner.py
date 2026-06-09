#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixed runner for GOLD V3 15 audit-only replay execution.

This runner patches the Stage 15 sha256_file helper that originally used
``iter(lambda: f.read(...), b="")``. Python requires the sentinel as a positional
argument: ``iter(lambda: f.read(...), b"")``.

The replay logic remains in gold_v3_15_audit_only_replay_execution.py.
This runner only fixes the helper before delegating to that module's main().
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import gold_v3_15_audit_only_replay_execution as stage15


def fixed_sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


stage15.sha256_file = fixed_sha256_file


if __name__ == "__main__":
    raise SystemExit(stage15.main(sys.argv[1:]))
