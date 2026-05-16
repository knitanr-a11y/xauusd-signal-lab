#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render AI history warning preview from trade_outcome_ledger.csv.

Use this when old notification_ledger_to_send.csv files are not available, empty,
or do not contain the historical signal we want to inspect.

This helper is verification-only:
- no Discord send
- no order placement
- no AI API call
- reads existing deterministic outcome ledger + tag summary only
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

from send_mochipoyo_discord_messages import maybe_apply_ai_history_warnings, write_csv, write_text  # type: ignore
from format_mochipoyo_discord_messages import format_row, val  # type: ignore


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def clean_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    s = str(x).strip()
    return s if s else default


def read_csv_empty_ok(path: str | Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()


def normalize_symbol(value: Any) -> str:
    text = clean_str(value).upper()
    if text.startswith("XAUUSD") or text.startswith("GOLD"):
        return "GOLD"
    if text.startswith("BTC"):
        return "BTC"
    return text


def normalize_direction(value: Any) -> str:
    text = clean_str(value).upper()
    if "BUY" in text:
        return "BUY"
    if "SELL" in text:
        return "SELL"
    return text


def to_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def filter_rows(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if args.symbol and "symbol" in out.columns:
        out = out[out["symbol"].map(normalize_symbol) == normalize_symbol(args.symbol)].copy()
    if args.strategy_id:
        strategy_cols = [c for c in ["strategy_id", "strategy_key", "pair_name"] if c in out.columns]
        if strategy_cols:
            mask = pd.Series(False, index=out.index)
            for col in strategy_cols:
                mask = mask | (out[col].astype(str) == str(args.strategy_id))
            out = out[mask].copy()
    if args.direction and "direction" in out.columns:
        out = out[out["direction"].map(normalize_direction) == normalize_direction(args.direction)].copy()
    if args.only_matched:
        if "match_status" in out.columns:
            out = out[out["match_status"].astype(str).str.upper() == "MATCHED"].copy()
        if "execution_status" in out.columns:
            out = out[out["execution_status"].astype(str).str.upper() == "EXECUTED"].copy()
    if args.outcome and "outcome" in out.columns:
        out = out[out["outcome"].astype(str).str.upper() == args.outcome.upper()].copy()
    if args.entry_time_contains and "entry_time" in out.columns:
        out = out[out["entry_time"].astype(str).str.contains(args.entry_time_contains, regex=False, na=False)].copy()
    if "entry_time" in out.columns:
        out["_entry_time_dt"] = pd.to_datetime(out["entry_time"], errors="coerce")
        out = out.sort_values("_entry_time_dt", ascending=not bool(args.latest_first)).drop(columns=["_entry_time_dt"], errors="ignore")
    return out.reset_index(drop=True)


def build_notification_like_row(row: pd.Series) -> dict[str, Any]:
    strategy = clean_str(row.get("strategy_id"), clean_str(row.get("strategy_key"), clean_str(row.get("pair_name"), "UNKNOWN_STRATEGY")))
    symbol = normalize_symbol(row.get("symbol"))
    direction = normalize_direction(row.get("direction"))
    rr = to_float(row.get("rr_planned"))
    if rr is None:
        rr = to_float(row.get("rr"))
    payload_key = clean_str(row.get("payload_key"), clean_str(row.get("order_key"), clean_str(row.get("trade_id"))))
    return {
        "symbol": symbol,
        "broker_symbol": clean_str(row.get("broker_symbol"), symbol),
        "pair_name": clean_str(row.get("pair_name"), strategy),
        "strategy_id": strategy,
        "strategy_key": clean_str(row.get("strategy_key"), strategy),
        "candidate_rank": clean_str(row.get("candidate_rank"), ""),
        "direction": direction,
        "entry_time": clean_str(row.get("entry_time")),
        "signal_close_time": clean_str(row.get("entry_time")),
        "entry_price": row.get("entry_price"),
        "sl_price": row.get("sl_price"),
        "tp_price": row.get("tp_price"),
        "rr": rr,
        "payload_id": clean_str(row.get("trade_id"), payload_key),
        "payload_key": payload_key,
        "order_key": clean_str(row.get("order_key")),
        "reason_text": "historical_outcome_preview;ai_history_warning_test",
        "caution_labels": "NONE",
        "context_granville_type": clean_str(row.get("context_granville_type"), ""),
        "context_ema_order": clean_str(row.get("context_ema_order"), ""),
        "base_ema_order": clean_str(row.get("base_ema_order"), ""),
        "total_score": row.get("total_score", ""),
        "context_score": row.get("context_score", ""),
        "base_score": row.get("base_score", ""),
        "outcome": clean_str(row.get("outcome")),
        "profit_r": row.get("profit_r", ""),
        "match_status": clean_str(row.get("match_status")),
        "execution_status": clean_str(row.get("execution_status")),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Render AI history warning preview from trade outcome ledger.")
    p.add_argument("--trade-outcome-csv", default="data/runtime_logs/trade_ai_review/trade_outcome_ledger.csv")
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--strategy-id", default="GOLD_H4_M15_DAYTRADE")
    p.add_argument("--direction", default="BUY")
    p.add_argument("--outcome", default="", help="Optional WIN/LOSS filter.")
    p.add_argument("--entry-time-contains", default="", help="Optional substring, e.g. 2026-05-07 16:00.")
    p.add_argument("--latest-first", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--match-index", type=int, default=1, help="1-based index after sorting/filtering.")
    p.add_argument("--only-matched", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--style", choices=["compact", "detailed"], default="compact")
    p.add_argument("--preview-txt", default="data/runtime_logs/trade_ai_review/test_ai_history_discord_preview.txt")
    p.add_argument("--preview-json", default="data/runtime_logs/trade_ai_review/test_ai_history_discord_preview.json")
    p.add_argument("--selected-input-csv", default="data/runtime_logs/trade_ai_review/selected_ai_history_warning_outcome_preview_input.csv")
    p.add_argument("--found-csv", default="data/runtime_logs/trade_ai_review/found_ai_history_warning_outcome_preview_matches.csv")
    p.add_argument("--ai-history-tag-summary-csv", default="data/runtime_logs/trade_ai_review/trade_ai_tag_summary.csv")
    p.add_argument("--ai-history-max-tags", type=int, default=4)
    p.add_argument("--disable-ai-history-warning", dest="enable_ai_history_warning", action="store_false")
    p.set_defaults(enable_ai_history_warning=True)
    args = p.parse_args()

    outcome_df = read_csv_empty_ok(args.trade_outcome_csv)
    matches = filter_rows(outcome_df, args)
    public_matches = matches.copy()
    if args.found_csv:
        found_path = Path(args.found_csv)
        found_path.parent.mkdir(parents=True, exist_ok=True)
        public_matches.to_csv(windows_long_path(found_path), index=False, encoding="utf-8-sig")

    print("preview_ai_history_warning_from_trade_outcome")
    print(f"trade_outcome_csv: {args.trade_outcome_csv}")
    print(f"matches: {len(matches)}")
    if args.found_csv:
        print(f"found_csv: {args.found_csv}")
    if matches.empty:
        print("status: NO_MATCH")
        return 1

    idx = max(1, int(args.match_index)) - 1
    if idx >= len(matches):
        print(f"status: MATCH_INDEX_OUT_OF_RANGE match_index={args.match_index} matches={len(matches)}")
        return 2

    selected = matches.iloc[idx]
    notif_row = build_notification_like_row(selected)
    selected_df = pd.DataFrame([notif_row])
    selected_input = Path(args.selected_input_csv)
    selected_input.parent.mkdir(parents=True, exist_ok=True)
    write_csv(selected_df, selected_input)

    fake_args = argparse.Namespace(
        enable_ai_history_warning=bool(args.enable_ai_history_warning),
        ai_history_tag_summary_csv=args.ai_history_tag_summary_csv,
        ai_history_max_tags=int(args.ai_history_max_tags),
    )
    preview_txt = Path(args.preview_txt)
    preview_json = Path(args.preview_json)
    preview_txt.parent.mkdir(parents=True, exist_ok=True)
    render_df = selected_df.copy()
    render_df, warning_report = maybe_apply_ai_history_warnings(render_df, fake_args, preview_txt.parent)

    messages = [format_row(row, args.style) for _, row in render_df.iterrows()]
    write_text(preview_txt, ("\n\n" + "=" * 40 + "\n\n").join(messages).strip() + "\n")
    records = []
    for i, (_, row) in enumerate(render_df.iterrows(), start=1):
        records.append({
            "index": i,
            "symbol": val(row, "symbol"),
            "direction": val(row, "direction"),
            "pair_name": val(row, "pair_name"),
            "entry_time": val(row, "entry_time"),
            "outcome": val(row, "outcome", ""),
            "profit_r": val(row, "profit_r", ""),
            "ai_history_warning_status": val(row, "ai_history_warning_status", ""),
            "ai_history_warning_severity": val(row, "ai_history_warning_severity", ""),
            "ai_history_warning_tags": val(row, "ai_history_warning_tags", ""),
            "message": messages[i - 1] if i - 1 < len(messages) else "",
        })
    write_text(preview_json, json.dumps({
        "selected_outcome_row": selected.to_dict(),
        "selected_notification_like_row": notif_row,
        "ai_history_warning": warning_report,
        "records": records,
    }, ensure_ascii=False, indent=2))

    print("status: OK")
    print(f"selected_trade_id: {clean_str(selected.get('trade_id'))}")
    print(f"selected_entry_time: {clean_str(selected.get('entry_time'))}")
    print(f"selected_direction: {clean_str(selected.get('direction'))}")
    print(f"selected_outcome: {clean_str(selected.get('outcome'))}")
    print(f"selected_profit_r: {clean_str(selected.get('profit_r'))}")
    print(f"selected_input_csv: {selected_input}")
    print(f"ai_history_warning_status: {warning_report.get('ai_history_warning_status')}")
    print(f"ai_history_warning_rows_warn: {warning_report.get('ai_history_warning_rows_warn')}")
    print(f"preview_txt: {preview_txt}")
    print(f"preview_json: {preview_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
