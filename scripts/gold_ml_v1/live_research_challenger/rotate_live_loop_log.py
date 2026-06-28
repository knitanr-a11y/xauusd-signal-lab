from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from live_log_manager import prune_and_compress_short_logs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rotate the GML1 live loop log")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--max-bytes", type=int, default=5 * 1024 * 1024)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    current = output_dir / "live_loop.log"
    now = pd.Timestamp.now().floor("s")
    if current.is_file() and current.stat().st_size >= max(1024, args.max_bytes):
        archive_dir = (
            output_dir
            / "logs"
            / "runtime"
            / now.strftime("%Y")
            / now.strftime("%m")
        )
        archive_dir.mkdir(parents=True, exist_ok=True)
        target = archive_dir / f"live_loop_{now.strftime('%Y-%m-%d_%H%M%S')}.log"
        counter = 1
        while target.exists():
            target = archive_dir / (
                f"live_loop_{now.strftime('%Y-%m-%d_%H%M%S')}_{counter}.log"
            )
            counter += 1
        os.replace(current, target)
    prune_and_compress_short_logs(
        output_dir,
        now.strftime("%Y-%m-%d %H:%M:%S"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
