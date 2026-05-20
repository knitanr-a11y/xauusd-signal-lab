#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build official BTC strict-5 signal preview CSV from MT5 candle CSVs.

Official default filter variant:
    buy_h4_context_conservative_v1

This is the preview counterpart of the official guarded demo connector.
It uses the shared official runtime, so preview / Discord / guarded demo can stay
aligned.

Safety:
- no Discord send
- no MT5 call
- no order_send
- no AI call
- no D1 read
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT / "scripts"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from btc_strict_5_filter_variants import BTC_STRICT_5_DEFAULT_FILTER_VARIANT, available_filter_variants
from btc_strict_5_official_runtime import build_context_from_csvs, build_filtered_preview
from btc_strict_5_signal_specs import DEFAULT_BROKER_SYMBOL, DEFAULT_SYMBOL, validate_signal_specs
from run_btc_strict_5_backtest_from_csv import DEFAULT_MQL5_FILES_DIR, choose_path, windows_long_path, write_csv

SCHEMA_VERSION = "btc_strict_5_official_preview_v1"
DEFAULT_OUT_DIR = Path("data/research_results/btc_strict_5_official_signal_candidates")


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build official BTC strict 5 preview CSV. No Discord/MT5/order/API calls.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--tail-m15", type=int, default=0)
    p.add_argument("--tail-h1", type=int, default=0)
    p.add_argument("--tail-h4", type=int, default=0)
    p.add_argument("--filter-variant", default=BTC_STRICT_5_DEFAULT_FILTER_VARIANT, choices=available_filter_variants())
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--preview-csv", default="")
    p.add_argument("--summary-json", default="")
    p.add_argument("--scan-recent-bars", type=int, default=500)
    p.add_argument("--max-signal-age-minutes", type=int, default=0)
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_csv = Path(args.preview_csv) if args.preview_csv else out_dir / "btc_strict_5_official_signal_preview.csv"
    summary_json = Path(args.summary_json) if args.summary_json else out_dir / "btc_strict_5_official_signal_preview_summary.json"
    if not preview_csv.is_absolute():
        preview_csv = REPO_ROOT / preview_csv
    if not summary_json.is_absolute():
        summary_json = REPO_ROOT / summary_json
    paths = {
        "m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file),
        "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file),
        "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file),
    }
    m15, h1, h4, ctx = build_context_from_csvs(
        m15_csv=paths["m15"], h1_csv=paths["h1"], h4_csv=paths["h4"],
        tail_m15=args.tail_m15, tail_h1=args.tail_h1, tail_h4=args.tail_h4,
    )
    preview, raw, excluded, meta = build_filtered_preview(
        m15=m15,
        ctx=ctx,
        filter_variant=args.filter_variant,
        scan_recent_bars=args.scan_recent_bars,
        max_signal_age_minutes=args.max_signal_age_minutes,
        latest_only=args.latest_only,
        broker_symbol=args.broker_symbol,
        symbol=args.symbol,
    )
    if not preview.empty:
        preview.insert(1, "official_schema_version", SCHEMA_VERSION)
        preview.insert(2, "filter_variant", args.filter_variant)
    write_csv(preview, preview_csv)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "filter_variant": args.filter_variant,
        "official_default_filter_variant": BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "is_official_default_variant": args.filter_variant == BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "research_preview_only": True,
        "orders_sent": False,
        "discord_sent": False,
        "openai_called": False,
        "runtime_ledger_mutated": False,
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "inputs": {k: str(v) for k, v in paths.items()},
        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json)},
        "tails": {"m15": int(args.tail_m15), "h1": int(args.tail_h1), "h4": int(args.tail_h4)},
        "rows": {"m15": int(len(m15)), "h1": int(len(h1)), "h4": int(len(h4)), "ctx": int(len(ctx)), "raw_signals_before_filter": int(len(raw)), "signals_excluded_by_filter": int(len(excluded)), "preview_rows": int(len(preview))},
        "filter_meta": meta,
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
