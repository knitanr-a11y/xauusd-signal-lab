#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import gold_v3_301_stage280_artifact_recovery as recovery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scan-root", action="append", default=[])
    parser.add_argument("--max-results", type=int, default=200)
    return parser.parse_args()


def dedup_existing(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = path.expanduser().resolve()
        key = str(resolved).lower()
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        result.append(resolved)
    return result


def main() -> int:
    args = parse_args()
    repo_start = Path(args.repo_root).expanduser().resolve()
    repo_root = recovery.repo_root_from_git(repo_start)
    extra_roots = dedup_existing([Path(value) for value in args.scan_root])

    original_candidate_roots = recovery.candidate_roots

    def candidate_roots_with_explicit_locations(current_repo_root: Path) -> list[Path]:
        roots = list(original_candidate_roots(current_repo_root))
        for root in extra_roots:
            roots.append(root)
            gold_v3_output = root / "FX_OUTPUTS" / "gold_v3"
            if gold_v3_output.exists():
                roots.append(gold_v3_output)
        return dedup_existing(roots)

    recovery.candidate_roots = candidate_roots_with_explicit_locations
    sys.argv = [
        "gold_v3_301_stage280_artifact_recovery.py",
        "--repo-root",
        str(repo_root),
        "--output",
        str(Path(args.output).expanduser().resolve()),
        "--max-results",
        str(args.max_results),
    ]
    return recovery.main()


if __name__ == "__main__":
    raise SystemExit(main())
