#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Official Discord notifier for BTC strict-5 signals from MT5 candle CSVs.

Official default filter variant:
    buy_h4_context_conservative_v1

This script uses the shared official runtime, so preview / Discord / guarded demo
all use the same conservative default filter path.  Baseline is available only
by explicitly passing --filter-variant baseline.

Safety:
- no Discord send unless --send-discord is passed
- no ledger mutation unless --send-discord or --mark-preview-notified is passed
- no MT5 call
- no order_send
- no AI call
- no D1 read
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT / "scripts"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from btc_strict_5_filter_variants import BTC_STRICT_5_DEFAULT_FILTER_VARIANT, available_filter_variants
from btc_strict_5_official_runtime import build_context_from_csvs, build_filtered_preview
from btc_strict_5_signal_specs import DEFAULT_BROKER_SYMBOL, DEFAULT_SYMBOL, validate_signal_specs
from run_btc_strict_5_backtest_from_csv import DEFAULT_MQL5_FILES_DIR, choose_path, windows_long_path, write_csv
from run_btc_strict_5_discord_notifier_from_csv import build_message, clean_str, json_safe
from run_live_gold_notifier_from_csv import load_env_file, send_discord_message

SCHEMA_VERSION = "btc_strict_5_official_discord_notifier_v1"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_OUT_DIR = Path("data/runtime_logs/btc_strict_5_official_discord_preview")
DEFAULT_LEDGER_CSV = Path("data/runtime_state/btc/strict_5/official_discord_notification_ledger.csv")

LEDGER_COLUMNS = [
    "notified_at_utc", "schema_version", "notification_key", "filter_variant",
    "preview_id", "signal_id", "strategy_id", "candidate_base", "candidate_family",
    "direction", "broker_symbol", "symbol", "signal_time", "base_close_time", "entry_time",
    "tp_price_distance", "sl_price_distance", "tp_pips", "sl_pips", "rr",
    "strict_no_future_ok", "h1_close_time", "h1_confirmed_ok", "h4_close_time", "h4_confirmed_ok",
    "d1_used", "discord_sent", "preview_only_marked", "message_path",
]


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    mkdirp(p.parent)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def load_notified_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except Exception:
        return set()
    if "notification_key" not in df.columns:
        return set()
    return set(df["notification_key"].dropna().astype(str).tolist())


def append_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in LEDGER_COLUMNS})


def notification_key(row: pd.Series, filter_variant: str) -> str:
    return "|".join([
        DEFAULT_SYMBOL,
        "STRICT5",
        "OFFICIAL",
        filter_variant,
        clean_str(row.get("strategy_id")),
        clean_str(row.get("direction")),
        clean_str(row.get("signal_time")),
    ])


def id_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "UNKNOWN_TIME"
    return pd.Timestamp(ts).strftime("%Y%m%d_%H%M")


def message_filename(row: pd.Series, key: str) -> str:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"btc_official_{clean_str(row.get('direction'))}_{id_time_text(row.get('signal_time'))}_{h}.json"


def write_message(out_dir: Path, row: pd.Series, key: str, message: str, filter_variant: str) -> Path:
    message_dir = out_dir / "messages"
    mkdirp(message_dir)
    path = message_dir / message_filename(row, key)
    payload = {
        "created_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "notification_key": key,
        "filter_variant": filter_variant,
        "strategy_id": clean_str(row.get("strategy_id")),
        "candidate_base": clean_str(row.get("candidate_base")),
        "direction": clean_str(row.get("direction")),
        "signal_time": clean_str(row.get("signal_time")),
        "message": message,
        "row": {str(k): json_safe(v) for k, v in row.to_dict().items()},
    }
    write_json(path, payload)
    return path


def ledger_row(row: pd.Series, *, key: str, filter_variant: str, discord_sent: bool, preview_only_marked: bool, message_path: Path) -> dict[str, Any]:
    return {
        "notified_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "notification_key": key,
        "filter_variant": filter_variant,
        "preview_id": row.get("preview_id", ""),
        "signal_id": row.get("signal_id", ""),
        "strategy_id": row.get("strategy_id", ""),
        "candidate_base": row.get("candidate_base", ""),
        "candidate_family": row.get("candidate_family", ""),
        "direction": row.get("direction", ""),
        "broker_symbol": row.get("broker_symbol", ""),
        "symbol": row.get("symbol", ""),
        "signal_time": row.get("signal_time", ""),
        "base_close_time": row.get("base_close_time", ""),
        "entry_time": row.get("entry_time", ""),
        "tp_price_distance": row.get("tp_price_distance", ""),
        "sl_price_distance": row.get("sl_price_distance", ""),
        "tp_pips": row.get("tp_pips", ""),
        "sl_pips": row.get("sl_pips", ""),
        "rr": row.get("rr", ""),
        "strict_no_future_ok": row.get("strict_no_future_ok", ""),
        "h1_close_time": row.get("h1_close_time", ""),
        "h1_confirmed_ok": row.get("h1_confirmed_ok", ""),
        "h4_close_time": row.get("h4_close_time", ""),
        "h4_confirmed_ok": row.get("h4_confirmed_ok", ""),
        "d1_used": row.get("d1_used", ""),
        "discord_sent": bool(discord_sent),
        "preview_only_marked": bool(preview_only_marked),
        "message_path": str(message_path),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Official BTC strict 5 Discord notifier from CSV. No MT5/order/API calls.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=2000)
    p.add_argument("--tail-h4", type=int, default=1000)
    p.add_argument("--filter-variant", default=BTC_STRICT_5_DEFAULT_FILTER_VARIANT, choices=available_filter_variants())
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--preview-csv", default="")
    p.add_argument("--summary-json", default="")
    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--scan-recent-bars", type=int, default=500)
    p.add_argument("--max-signal-age-minutes", type=int, default=0)
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--max-notifications", type=int, default=10)
    p.add_argument("--send-discord", action="store_true")
    p.add_argument("--mark-preview-notified", action="store_true")
    p.add_argument("--allow-duplicate", action="store_true")
    p.add_argument("--discord-webhook-url", default="")
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    out_dir = resolve_repo_path(args.out_dir)
    ledger_csv = resolve_repo_path(args.ledger_csv)
    env_file = resolve_repo_path(args.env_file)
    mkdirp(out_dir)
    load_env_file(env_file)
    webhook_url = args.discord_webhook_url or os.environ.get("BTC_STRICT_5_DISCORD_WEBHOOK_URL", "") or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise SystemExit("--send-discord requires --discord-webhook-url, BTC_STRICT_5_DISCORD_WEBHOOK_URL, or DISCORD_WEBHOOK_URL in .env")
    preview_csv = Path(args.preview_csv) if args.preview_csv else out_dir / "btc_strict_5_official_discord_preview_signals.csv"
    summary_json = Path(args.summary_json) if args.summary_json else out_dir / "btc_strict_5_official_discord_preview_summary.json"
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
        preview = preview.sort_values(["signal_time", "strategy_id"]).reset_index(drop=True)
        preview.insert(1, "official_schema_version", SCHEMA_VERSION)
        preview.insert(2, "filter_variant", args.filter_variant)
        if args.max_notifications and int(args.max_notifications) > 0:
            preview = preview.tail(int(args.max_notifications)).copy()
    write_csv(preview, preview_csv)
    notified_keys = load_notified_keys(ledger_csv)
    ledger_rows: list[dict[str, Any]] = []
    sent_rows = 0
    skipped_duplicates = 0
    message_rows = 0
    for _, row in preview.iterrows():
        key = notification_key(row, args.filter_variant)
        if not args.allow_duplicate and key in notified_keys:
            skipped_duplicates += 1
            continue
        message = build_message(row, key=key) + f"\nfilter_variant: {args.filter_variant}"
        message_path = write_message(out_dir, row, key, message, args.filter_variant)
        message_rows += 1
        print("\n" + "-" * 100, flush=True)
        print(message, flush=True)
        print(f"message_path: {message_path}", flush=True)
        discord_sent = False
        if args.send_discord:
            send_discord_message(webhook_url, message)
            discord_sent = True
            sent_rows += 1
            print("Discord sent: true", flush=True)
        if args.send_discord or args.mark_preview_notified:
            ledger_rows.append(ledger_row(row, key=key, filter_variant=args.filter_variant, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path))
    append_ledger(ledger_csv, ledger_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "filter_variant": args.filter_variant,
        "official_default_filter_variant": BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "is_official_default_variant": args.filter_variant == BTC_STRICT_5_DEFAULT_FILTER_VARIANT,
        "orders_sent": False,
        "discord_sent": bool(args.send_discord and sent_rows > 0),
        "discord_sent_rows": int(sent_rows),
        "openai_called": False,
        "runtime_ledger_mutated": bool(len(ledger_rows) > 0),
        "ledger_rows_appended": int(len(ledger_rows)),
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "inputs": {k: str(v) for k, v in paths.items()},
        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv)},
        "tails": {"m15": int(args.tail_m15), "h1": int(args.tail_h1), "h4": int(args.tail_h4)},
        "rows": {
            "m15": int(len(m15)), "h1": int(len(h1)), "h4": int(len(h4)), "ctx": int(len(ctx)),
            "raw_signals_before_filter": int(len(raw)),
            "signals_excluded_by_filter": int(len(excluded)),
            "preview_rows": int(len(preview)),
            "message_rows": int(message_rows),
            "skipped_duplicates": int(skipped_duplicates),
        },
        "filter_meta": meta,
        "safety": {"mt5_calls": False, "order_send": False, "ai_calls": False, "d1_read": False, "discord_send_requested": bool(args.send_discord)},
    }
    write_json(summary_json, summary)
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
