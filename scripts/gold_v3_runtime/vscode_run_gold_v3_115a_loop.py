#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path


def find_mt5_files_dir() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if p.name == "Files":
            return p
    return Path.cwd()


def main() -> int:
    mt5_files = find_mt5_files_dir()
    sys.argv = [
        "gold_v3_115a_queue_loop.py",
        "--mt5-files-dir",
        str(mt5_files),
        "--loop",
        "--target-second",
        "5",
        "--retention-days",
        "31",
    ]
    import gold_v3_115a_queue_loop as runner
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
