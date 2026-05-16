#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Export detailed trade cases for one AI hypothesis tag.

Use this after summarize_trade_ai_review_ledger.py finds a SUSPECT/WATCH tag.
It joins:
- deterministic trade_outcome_ledger.csv
- trade_ai_review_ledger.jsonl
- optional trade_feature_snapshot.csv

The output is a case list, not a rule-change decision. It is meant to compare
winning and losing examples for a tag before considering any filter or warning.
"""
from __future__ import annotations

import argparse
from typing import Any

import pandas as pd

from trade_ai_review_utils import (
    clean_float,
    clean_str,
    read_csv,
    read_jsonl,
    utc_now_text,
    write_csv,
    write_json,
)

NON_INFORMATIVE_TAGS = {
    "",
    "-",
    "none",
    "null",
    "n/a",
    "na",
    "unknown",
    "unclear",
    "no_clear_positive_tag",
    "no_positive_tag",
    "no_risk_tag",
    "no_clear_risk_tag",
}
OPEN_OUTCOMES = {"OPEN", "UNKNOWN", "UNMATCHED_OPEN_OR_MISSING_HISTORY", "NOT_EXECUTED", "NO_MT5_POSITION_MATCH"}
TAG_GROUP_FIELDS = {
    "risk": "possible_risk_tags",
    "positive": "possible_positive_tags",
    "execution": "execution_issue_tags",
    "system": "system_issue_tags",
}

OUTPUT_COLUMNS = [
    "created_at_utc",
    "tag_name",
    "tag_group",
    "symbol",
    "strategy_key",
    "strategy_id",
    "trade_id",
    "order_key",
    "payload_key",
    "direction",
    "outcome",
    "profit_r",
    "net_profit",
    "entry_time",
    "entry_price",
    "sl_price",
    "tp_price",
    "close_time",
    "close_price",
    "close_reason",
    "holding_minutes",
    "match_status",
    "execution_status",
    "pre_entry_quality_score",
    "post_entry_explanation_score",
    "risk_category",
    "issue_category",
    "avoidable_hypothesis",
    "confidence",
    "possible_risk_tags",
    "possible_positive_tags",
    "execution_issue_tags",
    "system_issue_tags",
    "pre_entry_observable_reasons",
    "post_entry_outcome_explanation",
    "ai_notes",
    "m15_atr14_at_entry",
    "m15_signal_candle_range_atr_ratio",
    "entry_position_in_m15_range_100_pct",
    "m15_ema20_distance_atr",
    "m15_ema50_distance_atr",
    "m15_ema200_distance_atr",
    "m15_trend_20_direction",
    "m15_trend_50_direction",
    "m15_trend_100_direction",
    "h1_trend_20_direction",
    "h4_trend_20_direction",
    "m5_first_touch_outcome",
    "m5_mfe_r",
    "m5_mae_r",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export detailed cases for one AI review tag.")
    p.add_argument("--trade-outcome-csv", required=True)
    p.add_argument("--ai-review-jsonl", required=True)
    p.add_argument("--tag-name", required=True, help="Example: ema_distance_too_large")
    p.add_argument("--tag-group", default="", choices=["", "risk", "positive", "execution", "system"])
    p.add_argument("--feature-snapshot-csv", default="", help="Optional trade_feature_snapshot.csv")
    p.add_argument("--symbol", default="")
    p.add_argument("--strategy-id", default="")
    p.add_argument("--output-csv", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--include-open-trades", action="store_true")
    p.add_argument("--keep-non-informative-tags", action="store_true")
    return p.parse_args()


def canonical_tag_name(tag: Any) -> str:
    return clean_str(tag).strip().lower().replace(" ", "_").replace("-", "_")


def normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [canonical_tag_name(x) for x in value if canonical_tag_name(x)]
    if isinstance(value, str):
        return [canonical_tag_name(x) for x in value.replace(";", ",").split(",") if canonical_tag_name(x)]
    text = canonical_tag_name(value)
    return [text] if text else []


def tag_is_informative(tag: str, *, keep: bool) -> bool:
    if keep:
        return bool(tag)
    return canonical_tag_name(tag) not in NON_INFORMATIVE_TAGS


def is_closed_row(row: dict[str, Any] | pd.Series, *, include_open: bool) -> bool:
    if include_open:
        return True
    outcome = clean_str(row.get("outcome")).upper()
    match_status = clean_str(row.get("match_status")).upper()
    execution_status = clean_str(row.get("execution_status")).upper()
    if outcome in OPEN_OUTCOMES:
        return False
    if execution_status and execution_status != "EXECUTED":
        return False
    if match_status and match_status != "MATCHED":
        return False
    return True


def list_to_text(value: Any) -> str:
    if isinstance(value, list):
        return " || ".join(clean_str(x) for x in value if clean_str(x))
    return clean_str(value)


def build_outcome_indexes(df: pd.DataFrame) -> dict[str, dict[str, pd.Series]]:
    indexes: dict[str, dict[str, pd.Series]] = {"trade_id": {}, "order_key": {}, "payload_key": {}}
    for _, row in df.iterrows():
        for key in indexes:
            value = clean_str(row.get(key))
            if value:
                indexes[key][value] = row
    return indexes


def lookup_row(indexes: dict[str, dict[str, pd.Series]], *keys: tuple[str, str]) -> pd.Series | None:
    for key_name, key_value in keys:
        value = clean_str(key_value)
        if value and value in indexes.get(key_name, {}):
            return indexes[key_name][value]
    return None


def main() -> int:
    args = parse_args()
    target_tag = canonical_tag_name(args.tag_name)
    outcomes = read_csv(args.trade_outcome_csv)
    snapshots = read_csv(args.feature_snapshot_csv) if args.feature_snapshot_csv else pd.DataFrame()
    outcome_indexes = build_outcome_indexes(outcomes)
    snapshot_indexes = build_outcome_indexes(snapshots) if not snapshots.empty else {"trade_id": {}, "order_key": {}, "payload_key": {}}
    review_rows = read_jsonl(args.ai_review_jsonl)
    now = utc_now_text()
    rows: list[dict[str, Any]] = []

    for review in review_rows:
        matched_groups: list[str] = []
        for group, field in TAG_GROUP_FIELDS.items():
            if args.tag_group and group != args.tag_group:
                continue
            tags = [t for t in normalize_tags(review.get(field)) if tag_is_informative(t, keep=args.keep_non_informative_tags)]
            if target_tag in tags:
                matched_groups.append(group)
        if not matched_groups:
            continue
        outcome_row = lookup_row(
            outcome_indexes,
            ("trade_id", clean_str(review.get("trade_id"))),
            ("order_key", clean_str(review.get("order_key"))),
            ("payload_key", clean_str(review.get("payload_key"))),
        )
        if outcome_row is None:
            continue
        if not is_closed_row(outcome_row, include_open=args.include_open_trades):
            continue
        if args.symbol and clean_str(outcome_row.get("symbol")).upper() != clean_str(args.symbol).upper():
            continue
        if args.strategy_id and clean_str(outcome_row.get("strategy_id")) != clean_str(args.strategy_id):
            continue
        snapshot_row = lookup_row(
            snapshot_indexes,
            ("trade_id", clean_str(outcome_row.get("trade_id"))),
            ("order_key", clean_str(outcome_row.get("order_key"))),
            ("payload_key", clean_str(outcome_row.get("payload_key"))),
        ) if snapshot_indexes else None
        for group in matched_groups:
            out: dict[str, Any] = {
                "created_at_utc": now,
                "tag_name": target_tag,
                "tag_group": group,
                "symbol": clean_str(outcome_row.get("symbol")),
                "strategy_key": clean_str(outcome_row.get("strategy_key")),
                "strategy_id": clean_str(outcome_row.get("strategy_id")),
                "trade_id": clean_str(outcome_row.get("trade_id")),
                "order_key": clean_str(outcome_row.get("order_key")),
                "payload_key": clean_str(outcome_row.get("payload_key")),
                "direction": clean_str(outcome_row.get("direction")),
                "outcome": clean_str(outcome_row.get("outcome")),
                "profit_r": clean_float(outcome_row.get("profit_r")),
                "net_profit": clean_float(outcome_row.get("net_profit")),
                "entry_time": clean_str(outcome_row.get("entry_time")),
                "entry_price": clean_float(outcome_row.get("entry_price")),
                "sl_price": clean_float(outcome_row.get("sl_price")),
                "tp_price": clean_float(outcome_row.get("tp_price")),
                "close_time": clean_str(outcome_row.get("close_time")),
                "close_price": clean_float(outcome_row.get("close_price")),
                "close_reason": clean_str(outcome_row.get("close_reason")),
                "holding_minutes": clean_float(outcome_row.get("holding_minutes")),
                "match_status": clean_str(outcome_row.get("match_status")),
                "execution_status": clean_str(outcome_row.get("execution_status")),
                "pre_entry_quality_score": clean_float(review.get("pre_entry_quality_score")),
                "post_entry_explanation_score": clean_float(review.get("post_entry_explanation_score")),
                "risk_category": clean_str(review.get("risk_category")),
                "issue_category": clean_str(review.get("issue_category")),
                "avoidable_hypothesis": clean_str(review.get("avoidable_hypothesis")),
                "confidence": clean_float(review.get("confidence")),
                "possible_risk_tags": list_to_text(review.get("possible_risk_tags")),
                "possible_positive_tags": list_to_text(review.get("possible_positive_tags")),
                "execution_issue_tags": list_to_text(review.get("execution_issue_tags")),
                "system_issue_tags": list_to_text(review.get("system_issue_tags")),
                "pre_entry_observable_reasons": list_to_text(review.get("pre_entry_observable_reasons")),
                "post_entry_outcome_explanation": list_to_text(review.get("post_entry_outcome_explanation")),
                "ai_notes": clean_str(review.get("notes")),
            }
            if snapshot_row is not None:
                for col in OUTPUT_COLUMNS:
                    if col not in out and col in snapshot_row.index:
                        out[col] = snapshot_row.get(col)
            rows.append({col: out.get(col, "") for col in OUTPUT_COLUMNS})

    out_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if not out_df.empty:
        out_df["profit_r_sort"] = pd.to_numeric(out_df["profit_r"], errors="coerce")
        out_df = out_df.sort_values(["outcome", "profit_r_sort", "entry_time"], ascending=[True, True, True]).drop(columns=["profit_r_sort"])
    write_csv(out_df, args.output_csv)
    summary = {
        "script": "export_trade_ai_tag_cases.py",
        "created_at_utc": now,
        "trade_outcome_csv": args.trade_outcome_csv,
        "ai_review_jsonl": args.ai_review_jsonl,
        "feature_snapshot_csv": args.feature_snapshot_csv,
        "tag_name": target_tag,
        "tag_group": args.tag_group,
        "symbol": args.symbol,
        "strategy_id": args.strategy_id,
        "output_csv": args.output_csv,
        "rows_out": int(len(out_df)),
        "outcome_counts": out_df["outcome"].value_counts(dropna=False).to_dict() if not out_df.empty else {},
    }
    if args.output_json:
        write_json(args.output_json, summary)
    print("export_trade_ai_tag_cases")
    print(f"tag_name: {target_tag}")
    print(f"rows_out: {summary['rows_out']}")
    print(f"output_csv: {args.output_csv}")
    if args.output_json:
        print(f"output_json: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
