#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find a matching Mochipoyo notification row and render Discord preview.

This helper is for local dry-run verification only:
- no Discord send
- no order placement
- no AI API call

It searches notification_ledger_to_send.csv files, selects the latest matching
row, writes that single row to a temporary CSV, then runs the same formatting path
used by send_mochipoyo_discord_messages.py so AI history warning text can be
checked safely.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError

from send_mochipoyo_discord_messages import load_input_rows, maybe_apply_ai_history_warnings, safe_print, write_csv, write_text  # type: ignore
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


def read_csv_empty_ok(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def normalize_symbol(value: Any) -> str:
    text = clean_str(value).upper()
    if text.startswith("XAUUSD") or text.startswith("GOLD"):
        return "GOLD"
    if text.startswith("BTC"):
        return "BTC"
    return text


def infer_from_pipe_key(*values: Any) -> dict[str, str]:
    for value in values:
        text = clean_str(value)
        if "|" not in text:
            continue
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 4:
            return {
                "symbol": normalize_symbol(parts[0]),
                "pair_name": parts[1],
                "strategy_id": parts[1],
                "candidate_rank": parts[2],
                "direction": parts[3].upper(),
            }
    return {}


def row_value(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index:
            value = clean_str(row.get(name))
            if value:
                return value
    return default


def row_context(row: pd.Series) -> dict[str, str]:
    inferred = infer_from_pipe_key(
        row_value(row, ["order_key"]),
        row_value(row, ["payload_key"]),
        row_value(row, ["signal_key"]),
    )
    pair_name = row_value(row, ["pair_name", "strategy_key", "strategy_id", "router_strategy_id"], inferred.get("pair_name", ""))
    return {
        "symbol": normalize_symbol(row_value(row, ["symbol", "broker_symbol"], inferred.get("symbol", ""))),
        "pair_name": pair_name,
        "strategy_id": row_value(row, ["strategy_id", "strategy_key"], pair_name),
        "candidate_rank": row_value(row, ["candidate_rank"], inferred.get("candidate_rank", "")),
        "direction": row_value(row, ["direction", "order_type"], inferred.get("direction", "")).upper(),
        "entry_time": row_value(row, ["entry_time", "signal_close_time", "sent_at", "created_at_utc"]),
        "entry_price": row_value(row, ["entry_price", "price", "current_execution_price"]),
        "payload_key": row_value(row, ["payload_key"]),
    }


def matches(ctx: dict[str, str], args: argparse.Namespace) -> bool:
    if args.symbol and normalize_symbol(ctx.get("symbol")) != normalize_symbol(args.symbol):
        return False
    if args.pair_name and clean_str(ctx.get("pair_name")) != clean_str(args.pair_name):
        return False
    if args.strategy_id and clean_str(ctx.get("strategy_id")) != clean_str(args.strategy_id):
        return False
    if args.direction and clean_str(ctx.get("direction")).upper() != clean_str(args.direction).upper():
        return False
    if args.candidate_rank and clean_str(ctx.get("candidate_rank")) != clean_str(args.candidate_rank):
        return False
    return True


def parse_iter_name(path: Path) -> str:
    for part in path.parts:
        if part.lower().startswith("iter_"):
            return part
    return ""


def find_matches(args: argparse.Namespace) -> pd.DataFrame:
    root = Path(args.root)
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return pd.DataFrame()
    files = list(root.rglob(args.file_name))
    files = sorted(files, key=lambda pth: pth.stat().st_mtime if pth.exists() else 0, reverse=True)
    for path in files:
        if path.exists() and path.stat().st_size <= 0:
            continue
        df = read_csv_empty_ok(path)
        if df.empty:
            continue
        for row_index, row in df.iterrows():
            ctx = row_context(row)
            if not matches(ctx, args):
                continue
            rows.append({
                "file_path": str(path),
                "iter_name": parse_iter_name(path),
                "last_write_time": pd.Timestamp.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "file_size": int(path.stat().st_size),
                "row_index_1based": int(row_index) + 1,
                **ctx,
                "_source_row_json": row.to_json(force_ascii=False),
            })
            if args.max_search_results > 0 and len(rows) >= args.max_search_results:
                return pd.DataFrame(rows)
    return pd.DataFrame(rows)


def restore_row(row_json: str) -> pd.DataFrame:
    data = json.loads(row_json)
    return pd.DataFrame([data])


def main() -> int:
    p = argparse.ArgumentParser(description="Find matching notification row and render AI history warning preview.")
    p.add_argument("--root", default="data/runtime_logs/gold/2026/05/week_20/mochipoyo_gold/loop")
    p.add_argument("--file-name", default="notification_ledger_to_send.csv")
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--pair-name", default="GOLD_H4_M15_DAYTRADE")
    p.add_argument("--strategy-id", default="")
    p.add_argument("--direction", default="BUY")
    p.add_argument("--candidate-rank", default="")
    p.add_argument("--max-search-results", type=int, default=20)
    p.add_argument("--match-index", type=int, default=1, help="1-based match index after latest-first sorting.")
    p.add_argument("--style", choices=["compact", "detailed"], default="compact")
    p.add_argument("--preview-txt", default="data/runtime_logs/trade_ai_review/test_ai_history_discord_preview.txt")
    p.add_argument("--preview-json", default="data/runtime_logs/trade_ai_review/test_ai_history_discord_preview.json")
    p.add_argument("--selected-input-csv", default="data/runtime_logs/trade_ai_review/selected_ai_history_warning_preview_input.csv")
    p.add_argument("--found-csv", default="data/runtime_logs/trade_ai_review/found_ai_history_warning_preview_matches.csv")
    p.add_argument("--ai-history-tag-summary-csv", default="data/runtime_logs/trade_ai_review/trade_ai_tag_summary.csv")
    p.add_argument("--ai-history-max-tags", type=int, default=4)
    p.add_argument("--disable-ai-history-warning", dest="enable_ai_history_warning", action="store_false")
    p.set_defaults(enable_ai_history_warning=True)
    args = p.parse_args()

    matches_df = find_matches(args)
    found_public = matches_df.drop(columns=["_source_row_json"], errors="ignore")
    if args.found_csv:
        out_path = Path(args.found_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        found_public.to_csv(windows_long_path(out_path), index=False, encoding="utf-8-sig")

    print("preview_ai_history_warning_for_notification_match")
    print(f"root: {args.root}")
    print(f"matches: {len(matches_df)}")
    if args.found_csv:
        print(f"found_csv: {args.found_csv}")
    if matches_df.empty:
        print("status: NO_MATCH")
        return 1

    idx = max(1, int(args.match_index)) - 1
    if idx >= len(matches_df):
        print(f"status: MATCH_INDEX_OUT_OF_RANGE match_index={args.match_index} matches={len(matches_df)}")
        return 2

    selected = matches_df.iloc[idx]
    selected_df = restore_row(clean_str(selected.get("_source_row_json")))
    selected_input = Path(args.selected_input_csv)
    selected_input.parent.mkdir(parents=True, exist_ok=True)
    write_csv(selected_df, selected_input)

    # Reuse the real send-message data path, but never send.
    fake_args = argparse.Namespace(
        enable_ai_history_warning=bool(args.enable_ai_history_warning),
        ai_history_tag_summary_csv=args.ai_history_tag_summary_csv,
        ai_history_max_tags=int(args.ai_history_max_tags),
    )
    preview_txt = Path(args.preview_txt)
    preview_json = Path(args.preview_json)
    preview_txt.parent.mkdir(parents=True, exist_ok=True)
    render_df = load_input_rows(selected_input, args.symbol, 5)
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
            "ai_history_warning_status": val(row, "ai_history_warning_status", ""),
            "ai_history_warning_severity": val(row, "ai_history_warning_severity", ""),
            "ai_history_warning_tags": val(row, "ai_history_warning_tags", ""),
            "message": messages[i - 1] if i - 1 < len(messages) else "",
        })
    write_text(preview_json, json.dumps({
        "selected_match": {k: v for k, v in selected.to_dict().items() if k != "_source_row_json"},
        "ai_history_warning": warning_report,
        "records": records,
    }, ensure_ascii=False, indent=2))

    print("status: OK")
    print(f"selected_file: {selected.get('file_path')}")
    print(f"selected_iter: {selected.get('iter_name')}")
    print(f"selected_entry_time: {selected.get('entry_time')}")
    print(f"selected_entry_price: {selected.get('entry_price')}")
    print(f"selected_input_csv: {selected_input}")
    print(f"ai_history_warning_status: {warning_report.get('ai_history_warning_status')}")
    print(f"ai_history_warning_rows_warn: {warning_report.get('ai_history_warning_rows_warn')}")
    print(f"preview_txt: {preview_txt}")
    print(f"preview_json: {preview_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
