#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility wrapper for GOLD V3 13 audit-only runtime script."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    runtime_dir = repo_root / "scripts" / "gold_v3_runtime"
    sys.path.insert(0, str(runtime_dir))
    from gold_v3_13_ranking_decision_template_audit_only import main as runtime_main

    return runtime_main()


if __name__ == "__main__":
    sys.exit(main())
