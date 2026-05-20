#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Discord preview/notifier for GOLD strict 7 signals from live CSVs.

Default behavior is safe:
- no Discord send unless --send-discord is passed
- no ledger mutation unless --send-discord or --mark-dry-run-notified is passed
- no MT5 order send
- no AI call
- H1/H4/D1 context is joined only with closed context candles

Notification text intentionally keeps strategy rule/internal name near the
bottom as reference information, and the title does not include "strict 7".
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for path in [SCRIPT_DIR, SCRIPTS_DIR, REPO_ROOT]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from gold_strict_7_signal_specs import DEFAULT_SYMBOL, GoldStrictSignalSpec, get_signal_specs, validate_signal_specs  # noqa: E402
from run_gold_strict_7_backtest_from_csv import (  # noqa: E402
    add_indicators,
    apply_cooldown,
    attach_strict_context,
    detect_spec_candidates,
    read_ohlc_csv,
)
from run_live_gold_notifier_from_csv import load_env_file, send_discord_message  # noqa: E402

DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_strict_7_discord_preview")
DEFAULT_LEDGER_CSV = Path("data/runtime_state/gold/strict_7/discord_notification_ledger.csv")
SCHEMA_VERSION = "gold_strict_7_discord_notifier_v4_text_tidy"

PREVIEW_COLUMNS = [
    "created_at",
    "schema_version",
    "notification_key",
    "strategy_id",
    "candidate_family",
    "direction",
    "session",
    "entry_time",
    "entry_price",
    "tp_price",
    "sl_price",
    "tp_pips",
    "sl_pips",
    "rr",
    "strict_no_future_ok",
    "context_h1_close_time",
    "context_h4_close_time",
    "context_d1_close_time",
    "trigger_close_pos",
    "trigger_range_atr",
    "trigger_rsi14",
    "trigger_stoch_k",
    "trigger_stoch_d",
    "trigger_cci20",
    "trigger_bb_pos",
    "trigger_kc_pos",
    "reason",
    "discord_sent",
    "dry_run",
    "message_path",
]

LEDGER_COLUMNS = [
    "notified_at",
    "schema_version",
    "notification_key",
    "strategy_id",
    "candidate_family",
    "direction",
    "session",
    "entry_time",
    "entry_price",
    "tp_price",
    "sl_price",
    "tp_pips",
    "sl_pips",
    "rr",
    "discord_sent",
    "dry_run",
    "message_path",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def safe_float(value: Any) -> float | None:
    try:
        x = float(value)
    except Exception:
        return None
    if pd.isna(x):
        return None
    return x


def fmt_price(value: Any) -> str:
    x = safe_float(value)
    if x is None:
        return "N/A"
    return f"{x:.2f}"


def fmt_num(value: Any, digits: int = 2) -> str:
    x = safe_float(value)
    if x is None:
        return "N/A"
    return f"{x:.{digits}f}"


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


def time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return clean_str(value)
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


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
        "SELL_KC_CCI150_LONDON_TP100_SL10": "SELL KC+CCI150 London",
        "BUY_SWEEP_RECLAIM_RSI_TP150_SL10": "BUY Sweep Reclaim + RSI",
        "BUY_STOCH_BB_KTURN_NY_TP150_SL10": "BUY Stoch+BB K>D NY",
        "SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5": "SELL H1trend+Donchian48+MACD+range",
        "SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120": "SELL H1trend+Donchian96 CD120",
        "SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60": "SELL H1trend+Donchian96 CD60",
        "BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5": "BUY BB+RSI30+rejection0.65",
    }
    return mapping.get(strategy_id, strategy_id)


def risk_watch_tags(strategy_id: str) -> list[str]:
    if strategy_id == "BUY_STOCH_BB_KTURN_NY_TP150_SL10":
        return ["poor_pullback_structure", "macd_late_signal", "entry_after_extended_move"]
    if strategy_id == "BUY_SWEEP_RECLAIM_RSI_TP150_SL10":
        return ["poor_pullback_structure", "high_volatility_chase", "m15_signal_candle_large"]
    if strategy_id == "BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5":
        return ["high_volatility_chase", "m15_signal_candle_large", "range_edge_entry"]
    if "DONCHIAN96" in strategy_id:
        return ["m15_signal_candle_large", "macd_late_signal", "poor_pullback_structure", "near_recent_low"]
    if strategy_id == "SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5":
        return ["m15_signal_candle_large", "ema_distance_too_large"]
    if strategy_id == "SELL_KC_CCI150_LONDON_TP100_SL10":
        return ["ema_distance_too_large", "against_h1_context"]
    return []


def notification_key(row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    return "|".join([DEFAULT_SYMBOL, "STRICT7", spec.strategy_id, spec.direction, time_text(row.get("close_time"))])


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


def calc_prices(row: pd.Series, spec: GoldStrictSignalSpec) -> tuple[float, float, float]:
    entry = float(row["close"])
    if spec.direction == "BUY":
        tp = entry + spec.tp_price_distance
        sl = entry - spec.sl_price_distance
    else:
        tp = entry - spec.tp_price_distance
        sl = entry + spec.sl_price_distance
    return entry, tp, sl


def build_message(row: pd.Series, spec: GoldStrictSignalSpec, *, notification_key_value: str) -> str:
    entry, tp, sl = calc_prices(row, spec)
    side_icon = "🟢" if spec.direction == "BUY" else "🔴"
    watch_tags = risk_watch_tags(spec.strategy_id)
    lines = [
        f"{side_icon} **GOLD {spec.direction} シグナル**",
        "",
        f"方向: {spec.direction}",
        f"Session: {spec.session}",
        "",
        f"価格目安: Entry {fmt_price(entry)} / TP {fmt_price(tp)} / SL {fmt_price(sl)}",
        f"値幅: TP {fmt_num(spec.tp_pips, 1)} pips / SL {fmt_num(spec.sl_pips, 1)} pips / RR {fmt_num(spec.rr, 2)}",
        "価格注記: M5確定足終値ベース。実約定・スプレッドでズレあり。",
        "",
        "AIタグ監視対象: " + (", ".join(watch_tags) if watch_tags else "なし"),
        "AI注記: この通知時点ではAI発注判定なし。タグは後続評価で蓄積。",
        "",
        "時刻:",
        f"entry_time目安: {time_text(row.get('close_time'))}",
        "",
        "No-future監査:",
        "H1/H4/D1は確定足のみ",
        f"H1 close: {time_text(row.get('h1_close_time'))}",
        f"H4 close: {time_text(row.get('h4_close_time'))}",
        f"D1 close: {time_text(row.get('d1_close_time'))}",
        "",
        "確認用:",
        f"ルール: {strategy_display_name(spec.strategy_id)}",
        f"内部名: {spec.strategy_id}",
        f"reason: {clean_str(row.get('reason'))}",
        f"key: {notification_key_value}",
    ]
    return "\n".join(lines)


def row_to_preview(row: pd.Series, spec: GoldStrictSignalSpec, *, key: str, message_path: Path, discord_sent: bool, dry_run: bool) -> dict[str, Any]:
    entry, tp, sl = calc_prices(row, spec)
    return {
        "created_at": now_str(),
        "schema_version": SCHEMA_VERSION,
        "notification_key": key,
        "strategy_id": spec.strategy_id,
        "candidate_family": spec.family,
        "direction": spec.direction,
        "session": spec.session,
        "entry_time": time_text(row.get("close_time")),
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "tp_pips": spec.tp_pips,
        "sl_pips": spec.sl_pips,
        "rr": spec.rr,
        "strict_no_future_ok": bool(row.get("strict_no_future_ok", False)),
        "context_h1_close_time": time_text(row.get("h1_close_time")),
        "context_h4_close_time": time_text(row.get("h4_close_time")),
        "context_d1_close_time": time_text(row.get("d1_close_time")),
        "trigger_close_pos": safe_float(row.get("close_pos")),
        "trigger_range_atr": safe_float(row.get("range_atr")),
        "trigger_rsi14": safe_float(row.get("rsi14")),
        "trigger_stoch_k": safe_float(row.get("stoch_k20")),
        "trigger_stoch_d": safe_float(row.get("stoch_d3")),
        "trigger_cci20": safe_float(row.get("cci20")),
        "trigger_bb_pos": safe_float(row.get("bb_pos20")),
        "trigger_kc_pos": safe_float(row.get("kc_pos20_1p5")),
        "reason": clean_str(row.get("reason")),
        "discord_sent": bool(discord_sent),
        "dry_run": bool(dry_run),
        "message_path": str(message_path),
    }


def message_filename(key: str, row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    key_hash = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"gold_strict7_{spec.direction}_{id_time_text(row.get('close_time'))}_{key_hash}.json"


def write_message(out_dir: Path, key: str, message: str, row: pd.Series, spec: GoldStrictSignalSpec) -> Path:
    message_dir = out_dir / "messages"
    mkdirp(message_dir)
    path = message_dir / message_filename(key, row, spec)
    payload = {
        "created_at": now_str(),
        "schema_version": SCHEMA_VERSION,
        "notification_key": key,
        "strategy_id": spec.strategy_id,
        "direction": spec.direction,
        "entry_time": time_text(row.get("close_time")),
        "message": message,
        "row": {str(k): json_safe(v) for k, v in row.to_dict().items()},
    }
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return path


def write_preview_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PREVIEW_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in PREVIEW_COLUMNS})


def resolve_csv_paths(args: argparse.Namespace) -> dict[str, Path]:
    csv_dir = Path(args.csv_dir)
    return {
        "M5": Path(args.gold_m5_csv) if args.gold_m5_csv else csv_dir / "goldsharp_m5.csv",
        "H1": Path(args.gold_h1_csv) if args.gold_h1_csv else csv_dir / "goldsharp_h1.csv",
        "H4": Path(args.gold_h4_csv) if args.gold_h4_csv else csv_dir / "goldsharp_h4.csv",
        "D1": Path(args.gold_d1_csv) if args.gold_d1_csv else csv_dir / "goldsharp_d1.csv",
    }


def load_context(paths: dict[str, Path], args: argparse.Namespace) -> pd.DataFrame:
    m5 = add_indicators(read_ohlc_csv(paths["M5"], tail_bars=args.tail_m5), "M5")
    h1 = add_indicators(read_ohlc_csv(paths["H1"], tail_bars=args.tail_h1), "H1")
    h4 = add_indicators(read_ohlc_csv(paths["H4"], tail_bars=args.tail_h4), "H4")
    d1 = add_indicators(read_ohlc_csv(paths["D1"], tail_bars=args.tail_d1), "D1")
    return attach_strict_context(m5, h1, h4, d1)


def collect_signals(ctx: pd.DataFrame, specs: list[GoldStrictSignalSpec], args: argparse.Namespace) -> list[tuple[pd.Timestamp, GoldStrictSignalSpec, pd.Series]]:
    if ctx.empty:
        return []
    end_idx = len(ctx) - 1 - int(args.bar_offset)
    if end_idx < 0:
        return []
    end_close_time = pd.Timestamp(ctx.iloc[end_idx]["close_time"])
    start_close_time = end_close_time - pd.Timedelta(minutes=5 * max(1, int(args.scan_recent_bars) - 1))
    items: list[tuple[pd.Timestamp, GoldStrictSignalSpec, pd.Series]] = []
    for spec in specs:
        raw = detect_spec_candidates(ctx, spec)
        if raw.empty:
            continue
        cooled = apply_cooldown(raw, spec)
        if cooled.empty:
            continue
        mask = (pd.to_datetime(cooled["close_time"], errors="coerce") >= start_close_time) & (pd.to_datetime(cooled["close_time"], errors="coerce") <= end_close_time)
        recent = cooled[mask.fillna(False)].copy()
        for _, row in recent.iterrows():
            items.append((pd.Timestamp(row["close_time"]), spec, row))
    items.sort(key=lambda x: (x[0], x[1].strategy_id))
    if args.max_notifications > 0:
        items = items[-int(args.max_notifications):]
    return items


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GOLD Discord preview/notifier from live CSVs.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--gold-m5-csv", default="")
    p.add_argument("--gold-h1-csv", default="")
    p.add_argument("--gold-h4-csv", default="")
    p.add_argument("--gold-d1-csv", default="")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    p.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    p.add_argument("--scan-recent-bars", type=int, default=300)
    p.add_argument("--bar-offset", type=int, default=1, help="1 means ignore the latest M5 row as potentially forming.")
    p.add_argument("--tail-m5", type=int, default=20000)
    p.add_argument("--tail-h1", type=int, default=5000)
    p.add_argument("--tail-h4", type=int, default=2000)
    p.add_argument("--tail-d1", type=int, default=1000)
    p.add_argument("--max-notifications", type=int, default=10)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--send-discord", action="store_true")
    p.add_argument("--mark-dry-run-notified", action="store_true")
    p.add_argument("--discord-webhook-url", default="")
    p.add_argument("--allow-duplicate", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    validate_signal_specs()
    specs = get_signal_specs()
    out_dir = resolve_path(args.out_dir)
    ledger_csv = resolve_path(args.ledger_csv)
    env_file = resolve_path(args.env_file)
    mkdirp(out_dir)
    load_env_file(env_file)

    paths = resolve_csv_paths(args)
    ctx = load_context(paths, args)
    notified_keys = load_notified_keys(ledger_csv)
    signals = collect_signals(ctx, specs, args)

    webhook_url = args.discord_webhook_url or os.environ.get("GOLD_STRICT_7_DISCORD_WEBHOOK_URL", "") or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise SystemExit("--send-discord requires --discord-webhook-url, GOLD_STRICT_7_DISCORD_WEBHOOK_URL, or DISCORD_WEBHOOK_URL in .env")

    preview_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    skipped_duplicates = 0

    print("=" * 100, flush=True)
    print("GOLD Discord notifier", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"out_dir: {out_dir}", flush=True)
    print(f"ledger_csv: {ledger_csv}", flush=True)
    print(f"env_file: {env_file} exists={env_file.exists()}", flush=True)
    for tf, p in paths.items():
        print(f"{tf}: {p}", flush=True)
    print(f"ctx_rows: {len(ctx)}", flush=True)
    if not ctx.empty:
        print(f"ctx_first_close_time: {time_text(ctx['close_time'].iloc[0])}", flush=True)
        print(f"ctx_last_close_time: {time_text(ctx['close_time'].iloc[-1])}", flush=True)
    print(f"scan_recent_bars: {args.scan_recent_bars}", flush=True)
    print(f"bar_offset: {args.bar_offset}", flush=True)
    print(f"raw_recent_signals_after_cooldown: {len(signals)}", flush=True)
    print(f"already_notified_keys: {len(notified_keys)}", flush=True)
    print(f"send_discord: {bool(args.send_discord)}", flush=True)
    print(f"dry_run: {bool(args.dry_run)}", flush=True)
    print("=" * 100, flush=True)

    for _, spec, row in signals:
        key = notification_key(row, spec)
        if not args.allow_duplicate and key in notified_keys:
            skipped_duplicates += 1
            continue
        message = build_message(row, spec, notification_key_value=key)
        message_path = write_message(out_dir, key, message, row, spec)
        discord_sent = False
        print("\n" + "-" * 100, flush=True)
        print(message, flush=True)
        print(f"message_path: {message_path}", flush=True)
        if args.send_discord:
            send_discord_message(webhook_url, message)
            discord_sent = True
            print("Discord sent: true", flush=True)
        preview = row_to_preview(row, spec, key=key, message_path=message_path, discord_sent=discord_sent, dry_run=bool(args.dry_run))
        preview_rows.append(preview)
        if args.send_discord or args.mark_dry_run_notified:
            ledger_rows.append({
                "notified_at": now_str(),
                "schema_version": SCHEMA_VERSION,
                **{col: preview.get(col, "") for col in LEDGER_COLUMNS if col not in {"notified_at", "schema_version"}},
            })

    preview_csv = out_dir / "gold_strict_7_discord_preview_signals.csv"
    summary_json = out_dir / "gold_strict_7_discord_preview_summary.json"
    write_preview_csv(preview_csv, preview_rows)
    append_ledger(ledger_csv, ledger_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_str(),
        "cycle_ok": True,
        "csv_paths": {tf: str(p) for tf, p in paths.items()},
        "out_dir": str(out_dir),
        "preview_csv": str(preview_csv),
        "ledger_csv": str(ledger_csv),
        "ctx_rows": int(len(ctx)),
        "scan_recent_bars": int(args.scan_recent_bars),
        "bar_offset": int(args.bar_offset),
        "raw_recent_signals_after_cooldown": int(len(signals)),
        "preview_rows": int(len(preview_rows)),
        "skipped_duplicates": int(skipped_duplicates),
        "ledger_rows_appended": int(len(ledger_rows)),
        "send_discord": bool(args.send_discord),
        "dry_run": bool(args.dry_run),
        "safety": {
            "discord_send": bool(args.send_discord),
            "mt5_calls": False,
            "order_send": False,
            "ai_calls": False,
            "live_runtime_state_mutation": bool(len(ledger_rows) > 0),
        },
    }
    with open(windows_long_path(summary_json), "w", encoding="utf-8", newline="") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    print("\n" + "=" * 100, flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    print("=" * 100, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
