from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ORIGINAL_COLLECTOR = SCRIPT_DIR / "collect_events_once.py"
DIAGNOSTIC_NAMES = (
    "latest_collection_result.json",
    "latest_collection_error.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one Mochipoyo collector cycle and organize its diagnostics."
    )
    parser.add_argument("--env", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def relocate_diagnostics(source_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in DIAGNOSTIC_NAMES:
        source = source_dir / name
        if not source.exists():
            continue
        target = output_dir / name
        if target.exists():
            target.unlink()
        source.replace(target)


def main() -> int:
    args = parse_args()
    if not ORIGINAL_COLLECTOR.is_file():
        print(f"[ERROR] Original collector was not found: {ORIGINAL_COLLECTOR}", file=sys.stderr)
        return 2

    local_root = args.env.expanduser().resolve().parent
    legacy_logs = local_root / "logs"
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else legacy_logs / "collector"
    )
    command = [
        sys.executable,
        str(ORIGINAL_COLLECTOR),
        "--env",
        str(args.env),
        "--db",
        str(args.db),
        "--limit",
        str(args.limit),
    ]
    completed = subprocess.run(command, cwd=SCRIPT_DIR.parents[1], check=False)
    try:
        relocate_diagnostics(legacy_logs, output_dir)
    except Exception as exc:
        print(f"[ERROR] Collector diagnostic organization failed: {exc}", file=sys.stderr)
        return 1
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
