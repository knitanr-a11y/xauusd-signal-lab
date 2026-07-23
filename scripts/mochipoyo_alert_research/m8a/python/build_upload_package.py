from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

FILES = [
    "00_READ_ME_FIRST.txt",
    "01_summary.json",
    "02_status.json",
    "03_source_matched.csv",
    "04_missed_source.csv",
    "05_unsupported_reentry.csv",
    "06_extra_candidates.csv",
    "07_pending_source_arrival_grace.csv",
    "08_audit.log",
]


def main() -> int:
    p = argparse.ArgumentParser(description="Build M8A single upload package")
    p.add_argument("--latest-dir", required=True)
    args = p.parse_args()
    latest = Path(args.latest_dir).expanduser().resolve()
    missing = [name for name in FILES if not (latest / name).is_file()]
    if missing:
        print(f"[M8A PACKAGE BLOCKED] missing={missing}")
        return 2
    out = latest / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in FILES:
            zf.write(latest / name, arcname=name)
    print(f"[M8A PACKAGE PASS] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
