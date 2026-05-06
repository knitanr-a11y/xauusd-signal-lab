#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a fixed-filter preset JSON from a Mochipoyo selected_filters CSV.

This freezes the selected filter names so future reproduction does not depend on
leaderboard re-ranking.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--selected-filters-csv", required=True)
    p.add_argument("--output-json", default="config/mochipoyo/gold_mochipoyo_rr12_refined_fixed_filters.json")
    p.add_argument("--candidate-name", default="GOLD_MOCHIPOYO_RR12_REFINED")
    p.add_argument("--exclude-slice", action="append", default=["GOLD_H4_M15_DAYTRADE|A|SELL"])
    p.add_argument("--portfolio-cooldown-minutes", type=int, default=60)
    args = p.parse_args()

    df = pd.read_csv(args.selected_filters_csv, encoding="utf-8-sig")
    if "name" not in df.columns:
        raise RuntimeError(f"selected filters CSV must contain name column: {args.selected_filters_csv}")
    filters = []
    for i, row in df.reset_index(drop=True).iterrows():
        item = {
            "rank": int(i + 1),
            "name": str(row["name"]),
        }
        for col in ["trades", "win_rate_resolved", "total_r", "pf", "max_dd_r", "max_consecutive_losses"]:
            if col in row and pd.notna(row[col]):
                v = row[col]
                item[col] = int(v) if col in ["trades", "max_consecutive_losses"] else float(v)
        filters.append(item)

    preset = {
        "candidate_name": args.candidate_name,
        "version": 1,
        "status": "provisional_review_only",
        "symbol": "GOLD",
        "rr": 1.2,
        "description": "Fixed-filter preset for GOLD Mochipoyo RR1.2 refined candidate. Do not re-rank filters during reproduction.",
        "anti_leak_rules": {
            "context_join": "context_close_time <= base_close_time",
            "pivot_confirmation": "pivot_confirmed_time <= signal_close_time",
            "entry_timing": "entry_time >= signal_close_time",
            "inbar_priority": "SL",
        },
        "portfolio": {
            "cooldown_minutes": args.portfolio_cooldown_minutes,
            "cooldown_by_direction": True,
            "exclude_slices": args.exclude_slice,
        },
        "fixed_filters": filters,
    }

    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(preset, ensure_ascii=False, indent=2), encoding="utf-8")
    print("make_mochipoyo_fixed_filter_preset")
    print(f"selected_filters_csv: {args.selected_filters_csv}")
    print(f"filters: {len(filters)}")
    print(f"output_json: {out}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
