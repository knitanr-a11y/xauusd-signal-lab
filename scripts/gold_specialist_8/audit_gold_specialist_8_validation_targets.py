#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Audit GOLD specialist 8 validation targets before AI review.

No OpenAI API call. No MT5 order send. No Discord send.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_STRATEGY_IDS = [
    "BUY_H1_DONCH72_ADX18_STRUCT_RR2_MIN50_CAP220",
    "BUY_H1_DONCH72_ADX10_H4ATR_TP055_RR18_MIN50_CAP220",
    "SELL_H1_DONCH36_ADX10_TP150_SL75_JST20_22",
    "SELL_H1_DONCH72_ADX10_TP50_SL25_JST18_22",
    "BUY_H1_DONCH20_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST01_05",
    "BUY_H1_IMPULSE_M15_EMA20_REJECT_ADX10_H1ATR_TP15_RR2_MIN50_CAP220_JST23_04",
    "SELL_H1H4_TREND_M15_EMA34_REJECT_ADX10_H4ATR_TP075_RR2_MIN50_CAP250_JST10_11",
    "SELL_H1H4_TREND_M15_RSI50_RECLAIM_ADX10_BLEND_STRUCT_H1ATR_RR2_MIN50_CAP240_JST23_04",
]


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(wpath(path), encoding="utf-8-sig")


def read_jsonl_count(path: Path) -> int:
    if not path.exists() or path.is_dir():
        return 0
    count = 0
    with open(wpath(path), "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def counts_by_strategy(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "strategy_id" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["strategy_id"].astype(str).value_counts().to_dict().items()}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit GOLD specialist 8 validation targets before AI review.")
    p.add_argument("--trade-outcome-csv", type=Path, default=Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_validation_trade_outcome_ledger.csv"))
    p.add_argument("--group-csv", type=Path, default=Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_group_trade_ledger_validation.csv"))
    p.add_argument("--component-csv", type=Path, default=Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_component_signal_ledger_validation.csv"))
    p.add_argument("--review-ledger-jsonl", type=Path, default=Path("data/gold_specialist_8/verification/ai_review_validation/trade_ai_review_ledger.jsonl"))
    p.add_argument("--require-all-8", action="store_true")
    p.add_argument("--output-json", type=Path, default=Path("data/gold_specialist_8/verification/ai_review_validation/latest_target_audit.json"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    trade = read_csv_if_exists(args.trade_outcome_csv)
    group = read_csv_if_exists(args.group_csv)
    component = read_csv_if_exists(args.component_csv)
    ledger_rows = read_jsonl_count(args.review_ledger_jsonl)
    trade_counts = counts_by_strategy(trade)
    group_counts = counts_by_strategy(group)
    component_counts = counts_by_strategy(component)
    missing_in_group = [sid for sid in EXPECTED_STRATEGY_IDS if group_counts.get(sid, 0) <= 0]
    present_in_group = [sid for sid in EXPECTED_STRATEGY_IDS if group_counts.get(sid, 0) > 0]
    audit = {
        "trade_outcome_csv": str(args.trade_outcome_csv),
        "group_csv": str(args.group_csv),
        "component_csv": str(args.component_csv),
        "review_ledger_jsonl": str(args.review_ledg er_jsonl) if False else str(args.review_ledger_jsonl),
        "trade_outcome_rows": int(len(trade)),
        "group_rows": int(len(group)),
        "component_rows": int(len(component)),
        "ai_review_rows": int(ledger_rows),
        "expected_strategy_count": len(EXPECTED_STRATEGY_IDS),
        "present_expected_strategy_count_in_group": len(present_in_group),
        "present_expected_strategy_ids_in_group": present_in_group,
        "missing_expected_strategy_ids_in_group": missing_in_group,
        "group_strategy_counts": group_counts,
        "component_strategy_counts": component_counts,
        "trade_outcome_strategy_counts": trade_counts,
        "ok_for_full_group_ai_review": len(missing_in_group) == 0 and len(group) > 0,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(args.output_json), "w", encoding="utf-8", newline="") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2, sort_keys=True)
    print("=" * 80)
    print("GOLD specialist 8 validation target audit - NO API")
    print("=" * 80)
    print(f"trade outcome rows : {audit['trade_outcome_rows']}")
    print(f"group rows         : {audit['group_rows']}")
    print(f"component rows     : {audit['component_rows']}")
    print(f"AI review rows     : {audit['ai_review_rows']}")
    print(f"expected strategies present in GROUP: {len(present_in_group)}/{len(EXPECTED_STRATEGY_IDS)}")
    print("")
    print("GROUP strategy counts:")
    for sid, count in sorted(group_counts.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {count:6d}  {sid}")
    print("")
    if missing_in_group:
        print("MISSING expected strategy_ids in GROUP:")
        for sid in missing_in_group:
            print(f"  - {sid}")
    else:
        print("All 8 expected strategy_ids are present in GROUP.")
    print("")
    print(f"audit json: {args.output_json}")
    if args.require_all_8 and missing_in_group:
        print("[ERROR] require-all-8 is enabled, but not all expected strategy_ids are present.")
        return 8
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
