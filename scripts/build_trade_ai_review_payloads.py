#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build OpenAI-ready JSONL payloads from trade feature snapshots.

This script does not call OpenAI. It only prepares review requests with an
explicit leak-control contract.

Input:
- trade_feature_snapshot.jsonl from build_trade_feature_snapshots.py

Output:
- trade_ai_review_payloads.jsonl
"""
from __future__ import annotations

import argparse
from typing import Any

from trade_ai_review_utils import (
    BTC_TAGS,
    COMMON_TAGS,
    EXECUTION_SYSTEM_TAGS,
    GOLD_TAGS,
    PROMPT_VERSION,
    REVIEW_SCHEMA_VERSION,
    TAG_TAXONOMY_VERSION,
    clean_float,
    clean_str,
    read_jsonl,
    utc_now_text,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build JSONL payloads for trade AI review.")
    p.add_argument("--feature-snapshot-jsonl", required=True)
    p.add_argument("--output-jsonl", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--max-pre-m15-bars-in-prompt", type=int, default=100)
    p.add_argument("--max-post-m15-bars-in-prompt", type=int, default=20)
    p.add_argument("--max-pre-h1-bars-in-prompt", type=int, default=80)
    p.add_argument("--max-pre-h4-bars-in-prompt", type=int, default=40)
    p.add_argument("--max-pre-d1-bars-in-prompt", type=int, default=30)
    return p.parse_args()


def trim_list(items: list[Any], max_items: int, *, from_tail: bool = True) -> list[Any]:
    if max_items < 0:
        return items
    if len(items) <= max_items:
        return items
    return items[-max_items:] if from_tail else items[:max_items]


def build_system_prompt() -> str:
    return """You are a trading review assistant for a GOLD/BTC demo auto-trading journal.
Your role is HYPOTHESIS_TAGGING_ONLY.
You are not allowed to judge that a strategy should be changed from a single trade.
You must separate pre-entry observable risk from post-entry outcome explanation.
Do not claim that a risk was obvious at entry unless it is supported by pre-entry features.
Post-entry bars may be used only to describe how the trade unfolded, not to invent pre-entry reasons.
Return strict JSON only. Do not include markdown.
""".strip()


def build_user_prompt(payload: dict[str, Any]) -> str:
    return (
        "Review this trade as a hypothesis-tagging record only. "
        "Use the supplied tag taxonomy when possible. "
        "If evidence is weak, say unclear. "
        "Return JSON matching the requested schema.\n\n"
        "IMPORTANT: One trade is not enough to change rules.\n"
        "IMPORTANT: Pre-entry data is for signal quality. Post-entry data is only for explaining the path.\n\n"
        f"TRADE_REVIEW_PAYLOAD_JSON:\n{payload}"
    )


def compact_trade(trade: dict[str, Any]) -> dict[str, Any]:
    keep = [
        "trade_id", "order_key", "payload_key", "signal_key", "symbol", "broker_symbol",
        "strategy_key", "strategy_alias", "strategy_id", "condition_id", "router_strategy_slot",
        "router_strategy_id", "pair_name", "candidate_rank", "direction", "lot", "entry_time",
        "entry_price", "entry_price_reference", "sl_price", "tp_price", "close_time", "close_price",
        "profit", "profit_points", "profit_r", "net_profit", "outcome", "close_reason",
        "holding_minutes", "match_status", "match_method",
    ]
    return {k: trade.get(k) for k in keep if k in trade}


def expected_schema() -> dict[str, Any]:
    return {
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "tag_taxonomy_version": TAG_TAXONOMY_VERSION,
        "created_at_utc": "YYYY-MM-DD HH:MM:SS",
        "trade_id": "string",
        "order_key": "string",
        "payload_key": "string",
        "symbol": "GOLD|BTC|...",
        "strategy_id": "string",
        "direction": "BUY|SELL",
        "outcome": "WIN|LOSS|SMALL_WIN|SMALL_LOSS|BREAKEVEN|OPEN|UNKNOWN",
        "profit_r": "number|null",
        "review_role": "HYPOTHESIS_TAGGING_ONLY",
        "single_trade_warning": "DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE",
        "pre_entry_quality_score": "integer 0-100, lower means worse setup quality",
        "post_entry_explanation_score": "integer 0-100, higher means post-entry path is easy to explain",
        "possible_risk_tags": ["string"],
        "possible_positive_tags": ["string"],
        "execution_issue_tags": ["string"],
        "system_issue_tags": ["string"],
        "risk_category": "acceptable_loss|bad_loss|unclear_loss|system_error_loss|execution_loss|good_win|bad_win|unclear",
        "issue_category": "signal_quality_issue|market_structure_issue|execution_issue|risk_setting_issue|system_issue|unclear",
        "avoidable_hypothesis": "yes|no|unknown",
        "should_change_strategy_from_this_single_trade": False,
        "confidence": "number 0.0-1.0",
        "pre_entry_observable_reasons": ["string"],
        "post_entry_outcome_explanation": ["string"],
        "notes": "short Japanese notes",
    }


def build_payload(snapshot: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    trade = snapshot.get("trade", {}) if isinstance(snapshot.get("trade"), dict) else {}
    compact_features = snapshot.get("compact_features", {}) if isinstance(snapshot.get("compact_features"), dict) else {}
    m15 = snapshot.get("m15", {}) if isinstance(snapshot.get("m15"), dict) else {}
    h1 = snapshot.get("h1", {}) if isinstance(snapshot.get("h1"), dict) else {}
    h4 = snapshot.get("h4", {}) if isinstance(snapshot.get("h4"), dict) else {}
    d1 = snapshot.get("d1", {}) if isinstance(snapshot.get("d1"), dict) else {}
    pre_m15 = trim_list(m15.get("pre_entry_bars", []) or [], args.max_pre_m15_bars_in_prompt, from_tail=True)
    post_m15 = trim_list(m15.get("post_entry_bars", []) or [], args.max_post_m15_bars_in_prompt, from_tail=False)
    return {
        "payload_schema_version": "trade_ai_review_payload_v1",
        "created_at_utc": utc_now_text(),
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "tag_taxonomy_version": TAG_TAXONOMY_VERSION,
        "trade_id": clean_str(trade.get("trade_id"), clean_str(compact_features.get("trade_id"))),
        "order_key": clean_str(trade.get("order_key"), clean_str(compact_features.get("order_key"))),
        "payload_key": clean_str(trade.get("payload_key"), clean_str(compact_features.get("payload_key"))),
        "system_prompt": build_system_prompt(),
        "user_prompt": "",
        "expected_response_schema": expected_schema(),
        "tag_taxonomy": {
            "common_tags": COMMON_TAGS,
            "gold_tags": GOLD_TAGS,
            "btc_tags": BTC_TAGS,
            "execution_system_tags": EXECUTION_SYSTEM_TAGS,
            "tag_meaning": "All tags are hypotheses only. They are not confirmed reasons until enough samples and deterministic stats support them.",
        },
        "review_contract": {
            "review_role": "HYPOTHESIS_TAGGING_ONLY",
            "single_trade_warning": "DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE",
            "should_change_strategy_from_this_single_trade_must_be": False,
            "pre_entry_data_use": "signal_quality_review_only",
            "post_entry_data_use": "outcome_explanation_only",
            "leakage_ban": "Do not use post-entry outcome to invent pre-entry reasons.",
        },
        "trade": compact_trade(trade),
        "compact_features": compact_features,
        "pre_entry_context": {
            "m15_bars": pre_m15,
            "h1_bars": trim_list(h1.get("pre_entry_bars", []) or [], args.max_pre_h1_bars_in_prompt, from_tail=True),
            "h4_bars": trim_list(h4.get("pre_entry_bars", []) or [], args.max_pre_h4_bars_in_prompt, from_tail=True),
            "d1_bars": trim_list(d1.get("pre_entry_bars", []) or [], args.max_pre_d1_bars_in_prompt, from_tail=True),
        },
        "post_entry_context": {
            "m15_bars": post_m15,
            "m5_first_touch_outcome": compact_features.get("m5_first_touch_outcome"),
            "m5_first_touch_time": compact_features.get("m5_first_touch_time"),
            "m5_mfe_r": compact_features.get("m5_mfe_r"),
            "m5_mae_r": compact_features.get("m5_mae_r"),
        },
    }


def main() -> int:
    args = parse_args()
    snapshots = read_jsonl(args.feature_snapshot_jsonl)
    payloads: list[dict[str, Any]] = []
    for snapshot in snapshots:
        payload = build_payload(snapshot, args)
        payload["user_prompt"] = build_user_prompt({
            k: v for k, v in payload.items()
            if k not in {"system_prompt", "user_prompt"}
        })
        payloads.append(payload)
    count = write_jsonl(args.output_jsonl, payloads)
    summary = {
        "script": "build_trade_ai_review_payloads.py",
        "created_at_utc": utc_now_text(),
        "feature_snapshot_jsonl": args.feature_snapshot_jsonl,
        "output_jsonl": args.output_jsonl,
        "rows_in": int(len(snapshots)),
        "rows_out": int(count),
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "tag_taxonomy_version": TAG_TAXONOMY_VERSION,
    }
    if args.output_json:
        write_json(args.output_json, summary)
    print("build_trade_ai_review_payloads")
    print(f"rows_in: {summary['rows_in']}")
    print(f"rows_out: {summary['rows_out']}")
    print(f"output_jsonl: {args.output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
