#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Summarize trade AI review hypothesis tags.

This script treats AI tags as hypotheses only. It joins the AI review ledger with
the deterministic trade outcome ledger, then computes tag-level win rate, avg R,
PF and investigation status.

It never edits strategy rules. It produces investigation candidates only.
"""
from __future__ import annotations

import argparse
from typing import Any

import pandas as pd

from trade_ai_review_utils import (
    BTC_TAGS,
    COMMON_TAGS,
    EXECUTION_SYSTEM_TAGS,
    GOLD_TAGS,
    TAG_SUMMARY_SCHEMA_VERSION,
    TAG_TAXONOMY_VERSION,
    clean_float,
    clean_str,
    max_losing_streak,
    profit_factor_from_r,
    read_csv,
    read_jsonl,
    utc_now_text,
    write_csv,
    write_json,
)

SUMMARY_COLUMNS = [
    "summary_schema_version",
    "tag_taxonomy_version",
    "created_at_utc",
    "updated_at_utc",
    "symbol",
    "strategy_key",
    "strategy_id",
    "tag_name",
    "tag_group",
    "tag_status",
    "trade_count",
    "win_count",
    "loss_count",
    "breakeven_count",
    "win_rate",
    "avg_r",
    "total_r",
    "profit_factor",
    "max_losing_streak",
    "tagged_vs_untagged_win_rate_diff",
    "tagged_vs_untagged_avg_r_diff",
    "overall_win_rate_diff",
    "overall_avg_r_diff",
    "min_sample_pass",
    "should_investigate",
    "investigation_reason",
    "example_win_trade_ids",
    "example_loss_trade_ids",
    "last_seen_trade_time",
]

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

RISK_TAGS = {t.lower() for t in COMMON_TAGS + GOLD_TAGS + BTC_TAGS}
EXECUTION_TAGS = {t.lower() for t in EXECUTION_SYSTEM_TAGS}
OPEN_OUTCOMES = {"OPEN", "UNKNOWN", "UNMATCHED_OPEN_OR_MISSING_HISTORY"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize trade AI review hypothesis tags.")
    p.add_argument("--trade-outcome-csv", required=True)
    p.add_argument("--ai-review-jsonl", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--suspect-win-rate-diff", type=float, default=-0.10, help="Tagged win_rate - overall win_rate threshold")
    p.add_argument("--suspect-avg-r-diff", type=float, default=-0.20, help="Tagged avg_r - overall avg_r threshold")
    p.add_argument("--group-by-symbol", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--group-by-strategy", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--keep-non-informative-tags", action="store_true", help="Do not drop placeholder tags such as unclear/none/unknown.")
    p.add_argument("--include-open-trades", action="store_true", help="Include OPEN/UNKNOWN/unmatched trades in tag summaries. Default excludes them.")
    p.add_argument("--keep-ai-tag-group", action="store_true", help="Do not normalize known risk/execution tags that the model returned in the wrong group.")
    return p.parse_args()


def canonical_tag_name(tag: Any) -> str:
    return clean_str(tag).strip().lower().replace(" ", "_").replace("-", "_")


def is_informative_tag(tag: Any, *, keep_non_informative: bool = False) -> bool:
    if keep_non_informative:
        return bool(clean_str(tag))
    return canonical_tag_name(tag) not in NON_INFORMATIVE_TAGS


def normalize_tag_group(tag_name: str, ai_group: str, *, keep_ai_tag_group: bool = False) -> str:
    if keep_ai_tag_group:
        return ai_group
    tag = canonical_tag_name(tag_name)
    if tag in EXECUTION_TAGS:
        return "execution"
    if tag in RISK_TAGS:
        return "risk"
    return ai_group


def is_win(outcome: Any, profit_r: Any) -> bool:
    text = clean_str(outcome).upper()
    if text in {"WIN", "SMALL_WIN"}:
        return True
    if text in {"LOSS", "SMALL_LOSS", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return False
    r = clean_float(profit_r)
    return bool(r is not None and r > 0)


def is_loss(outcome: Any, profit_r: Any) -> bool:
    text = clean_str(outcome).upper()
    if text in {"LOSS", "SMALL_LOSS"}:
        return True
    if text in {"WIN", "SMALL_WIN", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return False
    r = clean_float(profit_r)
    return bool(r is not None and r < 0)


def is_breakeven(outcome: Any, profit_r: Any) -> bool:
    text = clean_str(outcome).upper()
    if text == "BREAKEVEN":
        return True
    r = clean_float(profit_r)
    return bool(r is not None and abs(r) <= 1e-12)


def is_closed_outcome_row(row: pd.Series) -> bool:
    outcome = clean_str(row.get("outcome")).upper()
    match_status = clean_str(row.get("match_status")).upper()
    if outcome in OPEN_OUTCOMES:
        return False
    if match_status and match_status != "MATCHED":
        return False
    return True


def filter_closed(df: pd.DataFrame, *, include_open: bool = False) -> pd.DataFrame:
    if include_open or df.empty:
        return df.copy()
    if "outcome" not in df.columns and "match_status" not in df.columns:
        return df.copy()
    mask = df.apply(is_closed_outcome_row, axis=1)
    return df[mask].copy()


def first_nonempty_value(df: pd.DataFrame, columns: list[str], default: str = "") -> str:
    if df.empty:
        return default
    for col in columns:
        if col not in df.columns:
            continue
        for value in df[col].tolist():
            text = clean_str(value)
            if text:
                return text
    return default


def last_nonempty_value(df: pd.DataFrame, columns: list[str], default: str = "") -> str:
    if df.empty:
        return default
    for col in columns:
        if col not in df.columns:
            continue
        values = [clean_str(v) for v in df[col].tolist() if clean_str(v)]
        if values:
            return values[-1]
    return default


def normalize_review_rows(
    rows: list[dict[str, Any]],
    *,
    keep_non_informative: bool = False,
    keep_ai_tag_group: bool = False,
) -> pd.DataFrame:
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        for group_name, key in [
            ("possible_risk_tags", "risk"),
            ("possible_positive_tags", "positive"),
            ("execution_issue_tags", "execution"),
            ("system_issue_tags", "system"),
        ]:
            tags = row.get(group_name, [])
            if isinstance(tags, str):
                tags = [x.strip() for x in tags.replace(";", ",").split(",") if x.strip()]
            if not isinstance(tags, list):
                tags = []
            for tag in tags:
                tag_name = canonical_tag_name(tag)
                if not is_informative_tag(tag_name, keep_non_informative=keep_non_informative):
                    continue
                tag_group = normalize_tag_group(tag_name, key, keep_ai_tag_group=keep_ai_tag_group)
                out_rows.append({
                    "trade_id": clean_str(row.get("trade_id")),
                    "order_key": clean_str(row.get("order_key")),
                    "payload_key": clean_str(row.get("payload_key")),
                    "symbol": clean_str(row.get("symbol")),
                    "strategy_id": clean_str(row.get("strategy_id")),
                    "tag_name": tag_name,
                    "tag_group": tag_group,
                    "ai_original_tag_group": key,
                    "review_created_at_utc": clean_str(row.get("created_at_utc")),
                    "risk_category": clean_str(row.get("risk_category")),
                    "issue_category": clean_str(row.get("issue_category")),
                    "confidence": clean_float(row.get("confidence")),
                })
    return pd.DataFrame(out_rows)


def join_reviews_outcomes(tag_df: pd.DataFrame, outcome_df: pd.DataFrame) -> pd.DataFrame:
    if tag_df.empty:
        return tag_df.copy()
    out = tag_df.copy()
    outcome = outcome_df.copy()
    for col in ["trade_id", "order_key", "payload_key"]:
        if col not in outcome.columns:
            outcome[col] = ""
        if col not in out.columns:
            out[col] = ""
    joined_parts: list[pd.DataFrame] = []
    remaining = out.copy()
    for key in ["trade_id", "order_key", "payload_key"]:
        if remaining.empty:
            break
        left = remaining[remaining[key].astype(str).str.len() > 0].copy()
        no_key = remaining[~remaining.index.isin(left.index)].copy()
        right = outcome[outcome[key].astype(str).str.len() > 0].drop_duplicates(subset=[key], keep="last")
        merged = left.merge(right, on=key, how="left", suffixes=("", "_outcome"))
        hit = merged[merged.get("outcome", pd.Series(index=merged.index, dtype=object)).notna()].copy()
        miss = merged[merged.get("outcome", pd.Series(index=merged.index, dtype=object)).isna()].copy()
        keep_cols = list(out.columns)
        if not hit.empty:
            joined_parts.append(hit)
        if not miss.empty:
            miss = miss[[c for c in keep_cols if c in miss.columns]].copy()
        remaining = pd.concat([no_key, miss], ignore_index=True, sort=False)
    if not remaining.empty:
        joined_parts.append(remaining)
    if not joined_parts:
        return out
    return pd.concat(joined_parts, ignore_index=True, sort=False)


def aggregate_base_stats(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "breakeven_count": 0,
            "win_rate": None,
            "avg_r": None,
            "total_r": 0.0,
            "profit_factor": None,
            "max_losing_streak": 0,
        }
    profit_r = pd.to_numeric(df.get("profit_r", pd.Series(dtype=float)), errors="coerce")
    outcomes = df.get("outcome", pd.Series(dtype=object))
    win_mask = [is_win(o, r) for o, r in zip(outcomes, profit_r)]
    loss_mask = [is_loss(o, r) for o, r in zip(outcomes, profit_r)]
    be_mask = [is_breakeven(o, r) for o, r in zip(outcomes, profit_r)]
    n = int(len(df))
    win_count = int(sum(win_mask))
    loss_count = int(sum(loss_mask))
    breakeven_count = int(sum(be_mask))
    return {
        "trade_count": n,
        "win_count": win_count,
        "loss_count": loss_count,
        "breakeven_count": breakeven_count,
        "win_rate": None if n == 0 else win_count / n,
        "avg_r": None if profit_r.dropna().empty else float(profit_r.mean()),
        "total_r": float(profit_r.fillna(0.0).sum()),
        "profit_factor": profit_factor_from_r(profit_r.tolist()),
        "max_losing_streak": max_losing_streak(outcomes.tolist()),
    }


def status_for_tag(stats: dict[str, Any], overall: dict[str, Any], args: argparse.Namespace) -> tuple[str, bool, str]:
    n = int(stats.get("trade_count") or 0)
    if n < int(args.min_sample):
        return "NEW", False, f"sample below min_sample: {n} < {args.min_sample}"
    win_rate = stats.get("win_rate")
    avg_r = stats.get("avg_r")
    overall_wr = overall.get("win_rate")
    overall_avg = overall.get("avg_r")
    reasons: list[str] = []
    if win_rate is not None and overall_wr is not None and (win_rate - overall_wr) <= float(args.suspect_win_rate_diff):
        reasons.append(f"win_rate_diff={win_rate - overall_wr:.4f}")
    if avg_r is not None and overall_avg is not None and (avg_r - overall_avg) <= float(args.suspect_avg_r_diff):
        reasons.append(f"avg_r_diff={avg_r - overall_avg:.4f}")
    pf = stats.get("profit_factor")
    try:
        pf_float = float(pf) if pf is not None else None
    except Exception:
        pf_float = None
    if pf_float is not None and pf_float < 1.0:
        reasons.append(f"profit_factor={pf_float:.4f}")
    if reasons:
        return "SUSPECT", True, "; ".join(reasons)
    return "WATCH", False, "sample pass but deterministic stats do not look worse enough"


def examples(df: pd.DataFrame, *, want_win: bool, limit: int = 5) -> str:
    ids: list[str] = []
    profit_r = pd.to_numeric(df.get("profit_r", pd.Series(dtype=float)), errors="coerce")
    outcomes = df.get("outcome", pd.Series(dtype=object))
    for (_, row), r, outcome in zip(df.iterrows(), profit_r, outcomes):
        ok = is_win(outcome, r) if want_win else is_loss(outcome, r)
        if ok:
            tid = clean_str(row.get("trade_id"), clean_str(row.get("order_key"), clean_str(row.get("payload_key"))))
            if tid and tid not in ids:
                ids.append(tid)
        if len(ids) >= limit:
            break
    return "|".join(ids)


def main() -> int:
    args = parse_args()
    outcome_df_raw = read_csv(args.trade_outcome_csv)
    outcome_df = filter_closed(outcome_df_raw, include_open=bool(args.include_open_trades))
    review_rows = read_jsonl(args.ai_review_jsonl)
    tag_df = normalize_review_rows(
        review_rows,
        keep_non_informative=bool(args.keep_non_informative_tags),
        keep_ai_tag_group=bool(args.keep_ai_tag_group),
    )
    joined = join_reviews_outcomes(tag_df, outcome_df)
    joined = filter_closed(joined, include_open=bool(args.include_open_trades))
    now = utc_now_text()

    group_cols = ["tag_name", "tag_group"]
    if args.group_by_symbol:
        group_cols.insert(0, "symbol")
    if args.group_by_strategy:
        group_cols.insert(1 if args.group_by_symbol else 0, "strategy_id")
    if "strategy_key" not in joined.columns:
        joined["strategy_key"] = ""

    rows: list[dict[str, Any]] = []
    if joined.empty:
        out = pd.DataFrame(columns=SUMMARY_COLUMNS)
    else:
        for group_key, g in joined.groupby(group_cols, dropna=False):
            if not isinstance(group_key, tuple):
                group_key = (group_key,)
            group_values = dict(zip(group_cols, group_key))
            scope = outcome_df.copy()
            if args.group_by_symbol and clean_str(group_values.get("symbol")):
                scope = scope[scope.get("symbol", pd.Series(dtype=object)).astype(str) == clean_str(group_values.get("symbol"))]
            if args.group_by_strategy and clean_str(group_values.get("strategy_id")):
                scope = scope[scope.get("strategy_id", pd.Series(dtype=object)).astype(str) == clean_str(group_values.get("strategy_id"))]
            overall = aggregate_base_stats(scope)
            stats = aggregate_base_stats(g)
            untagged = scope[~scope.get("trade_id", pd.Series(dtype=object)).astype(str).isin(g.get("trade_id", pd.Series(dtype=object)).astype(str).tolist())].copy() if "trade_id" in scope.columns and "trade_id" in g.columns else pd.DataFrame()
            untagged_stats = aggregate_base_stats(untagged)
            tag_status, should_investigate, reason = status_for_tag(stats, overall, args)
            win_rate = stats.get("win_rate")
            avg_r = stats.get("avg_r")
            row = {
                "summary_schema_version": TAG_SUMMARY_SCHEMA_VERSION,
                "tag_taxonomy_version": TAG_TAXONOMY_VERSION,
                "created_at_utc": now,
                "updated_at_utc": now,
                "symbol": clean_str(group_values.get("symbol")),
                "strategy_key": first_nonempty_value(g, ["strategy_key", "strategy_key_outcome"]),
                "strategy_id": clean_str(group_values.get("strategy_id")),
                "tag_name": clean_str(group_values.get("tag_name")),
                "tag_group": clean_str(group_values.get("tag_group")),
                "tag_status": tag_status,
                "trade_count": stats["trade_count"],
                "win_count": stats["win_count"],
                "loss_count": stats["loss_count"],
                "breakeven_count": stats["breakeven_count"],
                "win_rate": win_rate,
                "avg_r": avg_r,
                "total_r": stats["total_r"],
                "profit_factor": stats["profit_factor"],
                "max_losing_streak": stats["max_losing_streak"],
                "tagged_vs_untagged_win_rate_diff": None if win_rate is None or untagged_stats.get("win_rate") is None else win_rate - untagged_stats["win_rate"],
                "tagged_vs_untagged_avg_r_diff": None if avg_r is None or untagged_stats.get("avg_r") is None else avg_r - untagged_stats["avg_r"],
                "overall_win_rate_diff": None if win_rate is None or overall.get("win_rate") is None else win_rate - overall["win_rate"],
                "overall_avg_r_diff": None if avg_r is None or overall.get("avg_r") is None else avg_r - overall["avg_r"],
                "min_sample_pass": int(stats["trade_count"]) >= int(args.min_sample),
                "should_investigate": should_investigate,
                "investigation_reason": reason,
                "example_win_trade_ids": examples(g, want_win=True),
                "example_loss_trade_ids": examples(g, want_win=False),
                "last_seen_trade_time": last_nonempty_value(g, ["close_time", "close_time_outcome", "review_created_at_utc"]),
            }
            rows.append(row)
        out = pd.DataFrame(rows, columns=SUMMARY_COLUMNS).sort_values(
            by=["should_investigate", "tag_status", "trade_count", "avg_r"],
            ascending=[False, True, False, True],
            na_position="last",
        )
    write_csv(out, args.output_csv)
    summary = {
        "script": "summarize_trade_ai_review_ledger.py",
        "created_at_utc": now,
        "trade_outcome_csv": args.trade_outcome_csv,
        "ai_review_jsonl": args.ai_review_jsonl,
        "output_csv": args.output_csv,
        "outcome_rows_raw": int(len(outcome_df_raw)),
        "outcome_rows_used": int(len(outcome_df)),
        "reviews_in": int(len(review_rows)),
        "tag_rows": int(len(tag_df)),
        "summary_rows": int(len(out)),
        "should_investigate_rows": int(out["should_investigate"].fillna(False).sum()) if "should_investigate" in out.columns and not out.empty else 0,
        "min_sample": int(args.min_sample),
        "keep_non_informative_tags": bool(args.keep_non_informative_tags),
        "include_open_trades": bool(args.include_open_trades),
        "keep_ai_tag_group": bool(args.keep_ai_tag_group),
    }
    if args.output_json:
        write_json(args.output_json, summary)
    print("summarize_trade_ai_review_ledger")
    print(f"outcome_rows_raw: {summary['outcome_rows_raw']}")
    print(f"outcome_rows_used: {summary['outcome_rows_used']}")
    print(f"reviews_in: {summary['reviews_in']}")
    print(f"tag_rows: {summary['tag_rows']}")
    print(f"summary_rows: {summary['summary_rows']}")
    print(f"should_investigate_rows: {summary['should_investigate_rows']}")
    print(f"keep_non_informative_tags: {summary['keep_non_informative_tags']}")
    print(f"include_open_trades: {summary['include_open_trades']}")
    print(f"keep_ai_tag_group: {summary['keep_ai_tag_group']}")
    print(f"output_csv: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
