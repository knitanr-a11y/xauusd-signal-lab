#!/usr/bin/env python3
"""Export the retained GOLD scalp candidate registry."""

from __future__ import annotations

import argparse
import csv
import json
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "config/gold_scalp_retained_candidate_registry/retained_candidate_catalog_20260802.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", action="append", help="Filter by tier; repeatable.")
    parser.add_argument("--status", action="append", help="Filter by status; repeatable.")
    parser.add_argument("--format", choices=("csv", "json"), default="csv")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def load_rows() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Registry not found: {CSV_PATH}")
    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    args = parse_args()
    rows = load_rows()

    if args.tier:
        allowed = set(args.tier)
        rows = [row for row in rows if row["tier"] in allowed]
    if args.status:
        allowed = set(args.status)
        rows = [row for row in rows if row["status"] in allowed]

    if args.format == "json":
        rendered = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    elif rows:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        rendered = buffer.getvalue()
    else:
        rendered = ""

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
