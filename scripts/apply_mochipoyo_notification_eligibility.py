#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply notification eligibility to Mochipoyo minimal scanner CSVs.

This is a safe post-processing step after --enable-risk-enrich.
It does not send Discord messages and does not place orders.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

try:
    from scripts.mochipoyo_notification_filter import NotificationEligibilityConfig, apply_notification_eligibility, split_notification_eligible
except ModuleNotFoundError:
    from mochipoyo_notification_filter import NotificationEligibilityConfig, apply_notification_eligibility, split_notification_eligible  # type: ignore


def output_paths(input_csv: Path, out_dir: Path) -> tuple[Path, Path, Path]:
    stem = input_csv.stem
    if stem.startswith("minimal_candidates_normalized_"):
        pair_suffix = stem.replace("minimal_candidates_normalized_", "")
    elif stem.startswith("minimal_candidates_risk_ok_"):
        pair_suffix = stem.replace("minimal_candidates_risk_ok_", "")
    else:
        pair_suffix = stem
    enriched = out_dir / f"minimal_candidates_notification_marked_{pair_suffix}.csv"
    ok = out_dir / f"minimal_candidates_notification_ok_{pair_suffix}.csv"
    ng = out_dir / f"minimal_candidates_notification_ng_{pair_suffix}.csv"
    return enriched, ok, ng


def process_one(input_csv: Path, out_dir: Path, config: NotificationEligibilityConfig) -> dict[str, object]:
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    marked = apply_notification_eligibility(df, config=config)
    ok, ng = split_notification_eligible(marked)
    marked_path, ok_path, ng_path = output_paths(input_csv, out_dir)
    marked.to_csv(marked_path, index=False, encoding="utf-8-sig")
    ok.to_csv(ok_path, index=False, encoding="utf-8-sig")
    ng.to_csv(ng_path, index=False, encoding="utf-8-sig")
    return {
        "input_csv": str(input_csv),
        "marked_csv": str(marked_path),
        "notification_ok_csv": str(ok_path),
        "notification_ng_csv": str(ng_path),
        "rows": int(len(marked)),
        "notification_ok": int(len(ok)),
        "notification_ng": int(len(ng)),
    }


def collect_inputs(args: argparse.Namespace) -> list[Path]:
    if args.input_csv:
        return [Path(args.input_csv)]
    in_dir = Path(args.input_dir)
    if args.risk_ok_only:
        pattern = "minimal_candidates_risk_ok_*.csv"
    else:
        pattern = "minimal_candidates_normalized_*.csv"
    return sorted(in_dir.glob(pattern))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply Mochipoyo notification eligibility filters to minimal scanner outputs.")
    p.add_argument("--input-csv", default=None, help="Single CSV to process.")
    p.add_argument("--input-dir", default=None, help="Directory containing minimal scanner CSVs.")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--risk-ok-only", action="store_true", help="When using --input-dir, process minimal_candidates_risk_ok_*.csv instead of normalized files.")
    p.add_argument("--btc-max-spread-to-sl-ratio", type=float, default=0.07)
    p.add_argument("--btc-min-effective-rr-after-spread", type=float, default=1.0)
    args = p.parse_args()
    if not args.input_csv and not args.input_dir:
        raise SystemExit("Either --input-csv or --input-dir is required")
    return args


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = NotificationEligibilityConfig(
        btc_max_spread_to_sl_ratio=float(args.btc_max_spread_to_sl_ratio),
        btc_min_effective_rr_after_spread=float(args.btc_min_effective_rr_after_spread),
    )
    inputs = collect_inputs(args)
    rows = []
    for input_csv in inputs:
        rows.append(process_one(input_csv, out_dir, config))
    summary = pd.DataFrame(rows)
    summary_path = out_dir / "notification_eligibility_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False) if not summary.empty else "no input files")
    print(f"summary_csv: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
