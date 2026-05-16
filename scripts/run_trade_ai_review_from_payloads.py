#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run OpenAI trade AI reviews from JSONL payloads.

This script writes AI hypothesis reviews only. It must not be used to directly
change strategy rules. The model output is validated and normalized so that
should_change_strategy_from_this_single_trade is always False.

Environment:
- OPENAI_API_KEY must be set unless --dry-run is used.
- OPENAI_MODEL can be used as a default model.

Operational note:
- Use --overwrite when switching from dry-run to real API output so placeholder
  records do not remain mixed with model-generated reviews.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

from trade_ai_review_utils import (
    ALLOWED_ISSUE_CATEGORIES,
    ALLOWED_RISK_CATEGORIES,
    PROMPT_VERSION,
    REVIEW_SCHEMA_VERSION,
    TAG_TAXONOMY_VERSION,
    append_jsonl,
    clean_float,
    clean_str,
    read_jsonl,
    utc_now_text,
    write_json,
    write_jsonl,
)

DEFAULT_MODEL = "gpt-5-mini"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run OpenAI trade AI reviews from payload JSONL.")
    p.add_argument("--payload-jsonl", required=True)
    p.add_argument("--output-jsonl", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    p.add_argument("--max-items", type=int, default=0, help="0 = all")
    p.add_argument("--dry-run", action="store_true", help="Write deterministic placeholder reviews without calling OpenAI.")
    p.add_argument("--overwrite", action="store_true", help="Overwrite output JSONL instead of appending. Recommended when re-running or switching dry-run/API modes.")
    p.add_argument("--temperature", type=float, default=0.0)
    return p.parse_args()


def extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end + 1]
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("model response is not a JSON object")
    return obj


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [clean_str(x) for x in value if clean_str(x)]
    if isinstance(value, str):
        parts = [x.strip() for x in value.replace(";", ",").split(",")]
        return [x for x in parts if x]
    return [clean_str(value)] if clean_str(value) else []


def normalize_review(review: dict[str, Any], payload: dict[str, Any], *, model: str, run_mode: str, raw_response: str = "") -> dict[str, Any]:
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    risk_category = clean_str(review.get("risk_category"), "unclear")
    issue_category = clean_str(review.get("issue_category"), "unclear")
    if risk_category not in ALLOWED_RISK_CATEGORIES:
        risk_category = "unclear"
    if issue_category not in ALLOWED_ISSUE_CATEGORIES:
        issue_category = "unclear"
    out = {
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "tag_taxonomy_version": TAG_TAXONOMY_VERSION,
        "created_at_utc": utc_now_text(),
        "model": model,
        "run_mode": run_mode,
        "trade_id": clean_str(review.get("trade_id"), clean_str(payload.get("trade_id"), clean_str(trade.get("trade_id"), clean_str(compact.get("trade_id"))))),
        "order_key": clean_str(review.get("order_key"), clean_str(payload.get("order_key"), clean_str(trade.get("order_key"), clean_str(compact.get("order_key"))))),
        "payload_key": clean_str(review.get("payload_key"), clean_str(payload.get("payload_key"), clean_str(trade.get("payload_key"), clean_str(compact.get("payload_key"))))),
        "symbol": clean_str(review.get("symbol"), clean_str(trade.get("symbol"), clean_str(compact.get("symbol")))),
        "strategy_id": clean_str(review.get("strategy_id"), clean_str(trade.get("strategy_id"), clean_str(compact.get("strategy_id")))),
        "direction": clean_str(review.get("direction"), clean_str(trade.get("direction"), clean_str(compact.get("direction")))).upper(),
        "outcome": clean_str(review.get("outcome"), clean_str(trade.get("outcome"), clean_str(compact.get("outcome")))).upper(),
        "profit_r": clean_float(review.get("profit_r"), clean_float(trade.get("profit_r"), clean_float(compact.get("profit_r")))),
        "review_role": "HYPOTHESIS_TAGGING_ONLY",
        "single_trade_warning": "DO_NOT_CHANGE_RULE_FROM_SINGLE_CASE",
        "pre_entry_quality_score": int(clean_float(review.get("pre_entry_quality_score"), 0) or 0),
        "post_entry_explanation_score": int(clean_float(review.get("post_entry_explanation_score"), 0) or 0),
        "possible_risk_tags": normalize_list(review.get("possible_risk_tags")),
        "possible_positive_tags": normalize_list(review.get("possible_positive_tags")),
        "execution_issue_tags": normalize_list(review.get("execution_issue_tags")),
        "system_issue_tags": normalize_list(review.get("system_issue_tags")),
        "risk_category": risk_category,
        "issue_category": issue_category,
        "avoidable_hypothesis": clean_str(review.get("avoidable_hypothesis"), "unknown") if clean_str(review.get("avoidable_hypothesis"), "unknown") in {"yes", "no", "unknown"} else "unknown",
        "should_change_strategy_from_this_single_trade": False,
        "confidence": max(0.0, min(1.0, clean_float(review.get("confidence"), 0.0) or 0.0)),
        "pre_entry_observable_reasons": normalize_list(review.get("pre_entry_observable_reasons")),
        "post_entry_outcome_explanation": normalize_list(review.get("post_entry_outcome_explanation")),
        "notes": clean_str(review.get("notes")),
        "raw_response": raw_response,
    }
    return out


def dry_run_review(payload: dict[str, Any], *, model: str) -> dict[str, Any]:
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    outcome = clean_str(trade.get("outcome"), clean_str(compact.get("outcome"))).upper()
    tags: list[str] = []
    range_atr = clean_float(compact.get("m15_signal_candle_range_atr_ratio"))
    entry_pos = clean_float(compact.get("entry_position_in_m15_range_100_pct"))
    if range_atr is not None and range_atr >= 1.5:
        tags.append("m15_signal_candle_large")
    if entry_pos is not None and entry_pos >= 85:
        tags.append("near_recent_high")
    if entry_pos is not None and entry_pos <= 15:
        tags.append("near_recent_low")
    review = {
        "trade_id": clean_str(trade.get("trade_id"), clean_str(compact.get("trade_id"))),
        "order_key": clean_str(trade.get("order_key"), clean_str(compact.get("order_key"))),
        "payload_key": clean_str(trade.get("payload_key"), clean_str(compact.get("payload_key"))),
        "symbol": clean_str(trade.get("symbol"), clean_str(compact.get("symbol"))),
        "strategy_id": clean_str(trade.get("strategy_id"), clean_str(compact.get("strategy_id"))),
        "direction": clean_str(trade.get("direction"), clean_str(compact.get("direction"))).upper(),
        "outcome": outcome,
        "profit_r": clean_float(trade.get("profit_r"), clean_float(compact.get("profit_r"))),
        "pre_entry_quality_score": 50,
        "post_entry_explanation_score": 50,
        "possible_risk_tags": tags,
        "possible_positive_tags": [],
        "execution_issue_tags": [],
        "system_issue_tags": [],
        "risk_category": "unclear_loss" if "LOSS" in outcome else "unclear",
        "issue_category": "unclear",
        "avoidable_hypothesis": "unknown",
        "confidence": 0.25,
        "pre_entry_observable_reasons": ["dry-run placeholder review; no model call"],
        "post_entry_outcome_explanation": [],
        "notes": "dry-run placeholder",
    }
    return normalize_review(review, payload, model=model, run_mode="DRY_RUN", raw_response="DRY_RUN_PLACEHOLDER")


def call_openai(payload: dict[str, Any], *, model: str, temperature: float) -> tuple[dict[str, Any], str]:
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"openai package import failed: {exc!r}") from exc
    client = OpenAI()
    system_prompt = clean_str(payload.get("system_prompt"))
    user_prompt = clean_str(payload.get("user_prompt"))
    # Use Chat Completions for broad compatibility with the current Python SDK.
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content or "{}"
    return extract_json(text), text


def main() -> int:
    args = parse_args()
    payloads = read_jsonl(args.payload_jsonl)
    if args.max_items and args.max_items > 0:
        payloads = payloads[: int(args.max_items)]
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, payload in enumerate(payloads, start=1):
        try:
            if args.dry_run:
                review = dry_run_review(payload, model=args.model)
            else:
                raw_review, raw_response = call_openai(payload, model=args.model, temperature=args.temperature)
                review = normalize_review(raw_review, payload, model=args.model, run_mode="OPENAI_API", raw_response=raw_response)
            rows.append(review)
        except Exception as exc:
            err = {
                "created_at_utc": utc_now_text(),
                "row_index": i,
                "trade_id": clean_str(payload.get("trade_id")),
                "order_key": clean_str(payload.get("order_key")),
                "run_mode": "DRY_RUN" if args.dry_run else "OPENAI_API",
                "error": repr(exc),
            }
            errors.append(err)
    if args.overwrite:
        written = write_jsonl(args.output_jsonl, rows)
    else:
        written = append_jsonl(args.output_jsonl, rows)
    summary = {
        "script": "run_trade_ai_review_from_payloads.py",
        "created_at_utc": utc_now_text(),
        "payload_jsonl": args.payload_jsonl,
        "output_jsonl": args.output_jsonl,
        "output_mode": "overwrite" if args.overwrite else "append",
        "model": args.model,
        "dry_run": bool(args.dry_run),
        "run_mode": "DRY_RUN" if args.dry_run else "OPENAI_API",
        "rows_in": int(len(payloads)),
        "rows_written": int(written),
        "error_rows": int(len(errors)),
        "errors": errors,
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "tag_taxonomy_version": TAG_TAXONOMY_VERSION,
    }
    if args.output_json:
        write_json(args.output_json, summary)
    print("run_trade_ai_review_from_payloads")
    print(f"rows_in: {summary['rows_in']}")
    print(f"rows_written: {summary['rows_written']}")
    print(f"error_rows: {summary['error_rows']}")
    print(f"dry_run: {summary['dry_run']}")
    print(f"run_mode: {summary['run_mode']}")
    print(f"output_mode: {summary['output_mode']}")
    print(f"model: {summary['model']}")
    print(f"output_jsonl: {args.output_jsonl}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
