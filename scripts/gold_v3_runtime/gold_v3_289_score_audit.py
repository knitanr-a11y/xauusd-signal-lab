#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single-run read-only Stage289 model score audit."""
from pathlib import Path
import argparse
from gold_v3_289_candidates import detect_candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--lookback-hours", type=int, default=96)
    args = parser.parse_args()
    rows, _ = detect_candidates(Path(args.candle_dir), args.lookback_hours)
    rows.to_csv(args.output_csv, index=False, encoding="utf-8-sig")
    print(args.output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
