#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copy GOLD CSVs from live MT5 MQL5/Files to a research snapshot folder.

This script is read-only with respect to the MT5/MQL5 Files directory.
It only copies files into data/research_csv_snapshots/...

Recommended:
    python scripts/research_copy_gold_csv_snapshot.py ^
      --source-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --snapshot-name gold_cb_20260508_01
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

GOLD_FILES = [
    "goldsharp_h4.csv",
    "goldsharp_h1.csv",
    "goldsharp_m15.csv",
    "goldsharp_m5.csv",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def looks_like_mql5_files(path: Path) -> bool:
    s = str(path.resolve()).replace("\\", "/").lower()
    return "/mql5/files" in s or s.endswith("/mql5/files")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Copy GOLD MT5 CSVs to a research snapshot folder.")
    p.add_argument("--source-dir", type=Path, required=True, help="Live MT5 MQL5/Files directory.")
    p.add_argument(
        "--snapshot-root",
        type=Path,
        default=Path("data/research_csv_snapshots"),
        help="Root folder for research snapshots.",
    )
    p.add_argument(
        "--snapshot-name",
        type=str,
        default="",
        help="Snapshot folder name. Default uses current timestamp.",
    )
    p.add_argument("--overwrite", action="store_true", help="Allow overwriting an existing snapshot folder.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir
    if not source_dir.exists():
        raise FileNotFoundError(f"source-dir not found: {source_dir}")
    if not looks_like_mql5_files(source_dir):
        print(f"[WARN] source-dir does not look like MQL5/Files: {source_dir}")

    snapshot_name = args.snapshot_name.strip() or datetime.now().strftime("gold_cb_%Y%m%d_%H%M%S")
    dest_dir = args.snapshot_root / snapshot_name

    if dest_dir.exists() and not args.overwrite:
        raise FileExistsError(f"snapshot already exists: {dest_dir} ; use --overwrite or another --snapshot-name")

    dest_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for filename in GOLD_FILES:
        src = source_dir / filename
        dst = dest_dir / filename
        if not src.exists():
            raise FileNotFoundError(f"required source CSV not found: {src}")
        shutil.copy2(src, dst)
        rows.append(
            {
                "filename": filename,
                "source_path": str(src),
                "snapshot_path": str(dst),
                "bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
            }
        )
        print(f"[COPIED] {src} -> {dst}")

    manifest = dest_dir / "SNAPSHOT_MANIFEST.csv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as f:
        import csv

        writer = csv.DictWriter(f, fieldnames=["filename", "source_path", "snapshot_path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[INFO] snapshot_dir={dest_dir}")
    print(f"[INFO] manifest={manifest}")
    print("")
    print("Run validation with:")
    print(f'python scripts\\research_gold_cb_fixed_rule_validation.py --csv-dir "{dest_dir}" --out-dir data\\results\\research_gold_cb_fixed_rule_validation')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
