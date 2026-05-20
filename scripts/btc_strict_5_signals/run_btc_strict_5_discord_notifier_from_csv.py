#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Discord notifier for BTC strict-5 signal previews from MT5 candle CSVs.

This is the BTC counterpart of the GOLD strict-7 Discord notifier.

Safety:
- no Discord send unless --send-discord is passed
- no ledger mutation unless --send-discord or --mark-preview-notified is passed
- no MT5 call
- no order_send
- no OpenAI call
- no D1 read or D1 condition

The signal detection path is shared with the BTC strict-5 backtest/preview code:
- btc_strict_5_signal_specs.py
- run_btc_strict_5_backtest_from_csv.py detect_signals / join_confirmed_context

So the Discord notifier does not duplicate strategy logic.
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
SCRIPTS_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for path in [SCRIPT_DIR, SCRIPTS_DIR, REPO_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from btc_strict_5_signal_specs import (  # noqa: E402
    DEFAULT_BROKER_SYMBOL,
    DEFAULT_SYMBOL,
    get_signal_specs,
    validate_signal_specs,
)
from run_btc_strict_5_backtest_from_csv import (  # noqa: E402
    DEFAULT_MQL5_FILES_DIR,
    add_indicators,
    choose_path,
    detect_signals,
    join_confirmed_context,
    read_ohlc_csv,
    time_text,
    windows_long_path,
)
from run_btc_strict_5_preview_from_csv import (  # noqa: E402
    SCHEMA_VERSION as PREVIEW_SCHEMA_VERSION,
    build_m15_next_open_lookup,
    build_preview_rows,
)
from run_live_gold_notifier_from_csv import load_env_file, send_discord_message  # noqa: E402

SCHEMA_VERSION = "btc_strict_5_discord_notifier_v1"
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_OUT_DIR = Path("data/runtime_logs/btc_strict_5_discord_preview")
DEFAULT_LEDGER_CSV = Path("data/runtime_state/btc/strict_5/discord_notification_ledger.csv")

LEDGER_COLUMNS = [
    "notified_at_utc",
    "schema_version",
    "notification_key",
    "preview_id",
    "signal_id",
    "strategy_id",
    "candidate_base",
    "candidate_family",
    "direction",
    "broker_symbol",
    "symbol",
    "signal_time",
    "base_close_time",
    "entry_time",
    "tp_price_distance",
    "sl_price_distance",
    "tp_pips",
    "sl_pips",
    "rr",
    "strict_no_future_ok",
    "h1_close_time",
    "h1_confirmed_ok",
    "h4_close_time",
    "h4_confirmed_ok",
    "d1_used",
    "discord_sent",
    "preview_only_marked",
    "message_path",
]


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def fmt_price_distance(value: Any) -> str:
    x = safe_float(value)
    if x is None:
        return "N/A"
    return f"{x:.1f}"


def fmt_num(value: Any, digits: int = 2) -> str:
    x = safe_float(value)
    if x is None:
        return "N/A"
    return f"{x:.{digits}f}"


def id_time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "UNKNOWN_TIME"
    return pd.Timestamp(ts).strftime("%Y%m%d_%H%M")


def json_safe(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return time_text(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def strategy_display_name(strategy_id: str) -> str:
    mapping = {
        "BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200_TP1900_SL400_H20H_CD0": "SELL Donchian96 + EMA200下 + BB低ボラ",
        "BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06_TP2500_SL750_H4H_CD0": "SELL Donchian32 + H1 EMA20 slope down + ATR30-80 + 00-06",
        "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23_TP2300_SL650_H20H_CD0": "BUY RSI40 reclaim + EMA200上 + BB低ボラ + 12-23",
        "BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06_TP2400_SL600_H6H_CD0": "SELL Donchian64 strong + H1 MACD下 + range + 00-06",
        "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23_TP2500_SL650_H20H_CD0": "BUY CCI -100 reclaim + H4 bull + BB低ボラ + 19-23",
    }
    return mapping.get(strategy_id, strategy_id)


def notification_key(row: pd.Series) -> str:
    return "|".join([
        DEFAULT_SYMBOL,
        "STRICT5",
        clean_str(row.get("strategy_id")),
        clean_str(row.get("direction")),
        clean_str(row.get("signal_time")),
    ])


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


def message_filename(row: pd.Series, key: str) -> str:
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"btc_strict5_{clean_str(row.get('direction'))}_{id_time_text(row.get('signal_time'))}_{h}.json"


def build_message(row: pd.Series, *, key: str) -> str:
    direction = clean_str(row.get("direction"))
    side_icon = "🟢" if direction == "BUY" else "🔴"
    strategy_id = clean_str(row.get("strategy_id"))
    next_open_available = bool(row.get("next_m15_open_available", False))
    next_open = clean_str(row.get("next_m15_open_price"), "N/A")
    lines = [
        f"{side_icon} **BTC strict 5 {direction} シグナル**",
        "",
        f"ルール: {strategy_display_name(strategy_id)}",
        f"内部名: {strategy_id}",
        f"方向: {direction}",
        "",
        "価格・値幅:",
        f"signal close: {fmt_num(row.get('signal_close_price'), 2)}",
        f"next M15 open: {next_open if next_open_available else '未取得/未確定'}",
        f"TP距離: {fmt_price_distance(row.get('tp_price_distance'))} price / {fmt_num(row.get('tp_pips'), 1)} pips",
        f"SL距離: {fmt_price_distance(row.get('sl_price_distance'))} price / {fmt_num(row.get('sl_pips'), 1)} pips",
        f"RR: {fmt_num(row.get('rr'), 2)}",
        "価格注記: この通知はpreview。実発注時のSL/TPは実約定基準で別途計算する。",
        "",
        "時刻:",
        f"signal_time: {clean_str(row.get('signal_time'))}",
        f"base_close_time: {clean_str(row.get('base_close_time'))}",
        f"entry_time目安: {clean_str(row.get('entry_time'))}",
        "",
        "No-future監査:",
        f"strict_no_future_ok: {bool(row.get('strict_no_future_ok'))}",
        f"H1 close: {clean_str(row.get('h1_close_time'))} / ok={bool(row.get('h1_confirmed_ok'))}",
        f"H4 close: {clean_str(row.get('h4_close_time'))} / ok={bool(row.get('h4_confirmed_ok'))}",
        f"D1 used: {bool(row.get('d1_used'))}",
        "",
        f"reason: {clean_str(row.get('reason'))}",
        f"key: {key}",
    ]
    return "\n".join(lines)


def write_message(out_dir: Path, row: pd.Series, key: str, message: str) -> Path:
    message_dir = out_dir / "messages"
    mkdirp(message_dir)
    path = message_dir / message_filename(row, key)
    payload = {
        "created_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "notification_key": key,
        "strategy_id": clean_str(row.get("strategy_id")),
        "candidate_base": clean_str(row.get("candidate_base")),
        "direction": clean_str(row.get("direction")),
        "signal_time": clean_str(row.get("signal_time")),
        "message": message,
        "row": {str(k): json_safe(v) for k, v in row.to_dict().items()},
    }
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    return path


def ledger_row(row: pd.Series, *, key: str, discord_sent: bool, preview_only_marked: bool, message_path: Path) -> dict[str, Any]:
    return {
        "notified_at_utc": utc_now_text(),
        "schema_version": SCHEMA_VERSION,
        "notification_key": key,
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


def load_preview(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    input_paths = {
        "m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file),
        "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file),
        "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file),
    }
    m15 = add_indicators(read_ohlc_csv(input_paths["m15"]), include_donchian=True)
    h1 = add_indicators(read_ohlc_csv(input_paths["h1"]))
    h4 = add_indicators(read_ohlc_csv(input_paths["h4"]))
    ctx = join_confirmed_context(m15, h1, h4)
    signals = detect_signals(ctx, get_signal_specs())
    if args.scan_recent_bars and int(args.scan_recent_bars) > 0 and not ctx.empty:
        cutoff_idx = max(0, len(ctx) - int(args.scan_recent_bars))
        cutoff_time = pd.Timestamp(ctx.iloc[cutoff_idx]["time"])
        if not signals.empty:
            signals = signals[pd.to_datetime(signals["signal_time"]) >= cutoff_time].copy()
    if args.latest_only and not signals.empty:
        signals = signals.sort_values(["signal_time", "strategy_id"]).tail(1).copy()
    preview = build_preview_rows(
        signals=signals,
        ctx=ctx,
        m15_next_open_lookup=build_m15_next_open_lookup(m15),
        broker_symbol=str(args.broker_symbol),
        symbol=str(args.symbol),
    )
    meta = {
        "input_paths": {k: str(v) for k, v in input_paths.items()},
        "rows": {"m15": int(len(m15)), "h1": int(len(h1)), "h4": int(len(h4)), "preview_rows": int(len(preview))},
    }
    return preview, meta


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BTC strict 5 Discord notifier from CSV. No MT5/order/API calls.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--preview-csv", default="")
    p.add_argument("--summary-json", default="")
    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--scan-recent-bars", type=int, default=500)
    p.add_argument("--latest-only", action="store_true")
    p.add_argument("--max-notifications", type=int, default=10)
    p.add_argument("--send-discord", action="store_true")
    p.add_argument("--mark-preview-notified", action="store_true", help="Append ledger without Discord send. Usually not needed.")
    p.add_argument("--allow-duplicate", action="store_true")
    p.add_argument("--discord-webhook-url", default="")
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    return p.parse_args()


def choose_output_paths(args: argparse.Namespace, out_dir: Path) -> tuple[Path, Path]:
    preview_csv = Path(args.preview_csv) if args.preview_csv else out_dir / "btc_strict_5_discord_preview_signals.csv"
    summary_json = Path(args.summary_json) if args.summary_json else out_dir / "btc_strict_5_discord_preview_summary.json"
    if not preview_csv.is_absolute():
        preview_csv = REPO_ROOT / preview_csv
    if not summary_json.is_absolute():
        summary_json = REPO_ROOT / summary_json
    return preview_csv, summary_json


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    out_dir = resolve_repo_path(args.out_dir)
    ledger_csv = resolve_repo_path(args.ledger_csv)
    env_file = resolve_repo_path(args.env_file)
    mkdirp(out_dir)
    load_env_file(env_file)

    webhook_url = (
        args.discord_webhook_url
        or os.environ.get("BTC_STRICT_5_DISCORD_WEBHOOK_URL", "")
        or os.environ.get("DISCORD_WEBHOOK_URL", "")
    )
    if args.send_discord and not webhook_url:
        raise SystemExit("--send-discord requires --discord-webhook-url, BTC_STRICT_5_DISCORD_WEBHOOK_URL, or DISCORD_WEBHOOK_URL in .env")

    preview, meta = load_preview(args)
    if not preview.empty:
        preview = preview.sort_values(["signal_time", "strategy_id"]).reset_index(drop=True)
        if args.max_notifications and int(args.max_notifications) > 0:
            preview = preview.tail(int(args.max_notifications)).copy()

    notified_keys = load_notified_keys(ledger_csv)
    preview_csv, summary_json = choose_output_paths(args, out_dir)
    mkdirp(preview_csv.parent)
    preview.to_csv(windows_long_path(preview_csv), index=False, encoding="utf-8-sig")

    ledger_rows: list[dict[str, Any]] = []
    sent_rows = 0
    skipped_duplicates = 0
    message_rows = 0

    print("=" * 100, flush=True)
    print("BTC strict 5 Discord notifier", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print("d1_csv=NOT_USED d1_used=false", flush=True)
    print(f"out_dir: {out_dir}", flush=True)
    print(f"ledger_csv: {ledger_csv}", flush=True)
    print(f"send_discord: {bool(args.send_discord)}", flush=True)
    print(f"preview_rows: {len(preview)}", flush=True)
    print(f"already_notified_keys: {len(notified_keys)}", flush=True)
    print("=" * 100, flush=True)

    for _, row in preview.iterrows():
        key = notification_key(row)
        if not args.allow_duplicate and key in notified_keys:
            skipped_duplicates += 1
            continue
        message = build_message(row, key=key)
        message_path = write_message(out_dir, row, key, message)
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
            ledger_rows.append(ledger_row(row, key=key, discord_sent=discord_sent, preview_only_marked=bool(args.mark_preview_notified and not args.send_discord), message_path=message_path))

    append_ledger(ledger_csv, ledger_rows)
    audit = {
        "strict_no_future_ng_rows": int((~preview["strict_no_future_ok"].astype(bool)).sum()) if not preview.empty else 0,
        "h1_confirmed_ng_rows": int((~preview["h1_confirmed_ok"].astype(bool)).sum()) if not preview.empty else 0,
        "h4_confirmed_ng_rows": int((~preview["h4_confirmed_ok"].astype(bool)).sum()) if not preview.empty else 0,
        "d1_used_rows": int(preview["d1_used"].astype(bool).sum()) if not preview.empty else 0,
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "research_preview_only": False,
        "orders_sent": False,
        "discord_sent": bool(args.send_discord and sent_rows > 0),
        "discord_sent_rows": int(sent_rows),
        "openai_called": False,
        "runtime_ledger_mutated": bool(len(ledger_rows) > 0),
        "ledger_rows_appended": int(len(ledger_rows)),
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "input_paths": meta.get("input_paths", {}),
        "outputs": {"preview_csv": str(preview_csv), "summary_json": str(summary_json), "ledger_csv": str(ledger_csv)},
        "scan_recent_bars": int(args.scan_recent_bars),
        "latest_only": bool(args.latest_only),
        "max_notifications": int(args.max_notifications),
        "rows": {**meta.get("rows", {}), "preview_rows_after_max_notifications": int(len(preview)), "message_rows": int(message_rows), "skipped_duplicates": int(skipped_duplicates)},
        "audit": audit,
        "strategy_counts": preview["strategy_id"].value_counts().to_dict() if not preview.empty else {},
        "safety": {
            "mt5_calls": False,
            "order_send": False,
            "ai_calls": False,
            "d1_read": False,
            "discord_send_requested": bool(args.send_discord),
            "ledger_mutation_requires_send_or_mark_preview_notified": True,
        },
    }
    mkdirp(summary_json.parent)
    with open(windows_long_path(summary_json), "w", encoding="utf-8", newline="") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)

    print("\n" + "=" * 100, flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 100, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
