#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Discord preview/notifier for GOLD strict 7 signals from live CSVs.

Default behavior is safe:
- no Discord send unless --send-discord is passed
- no ledger mutation unless Discord send succeeds or --mark-dry-run-notified is passed
- no MT5 order send
- no OpenAI call at notification time
- H1/H4/D1 context is joined only with closed context candles
- wall-clock freshness guard suppresses stale CSV/signals before notification
- Discord send errors are written to summary JSON before returning non-zero

AI tag scoring:
- uses deterministic numeric rules generated from historical post-trade AI review
- only tags that HIT the current signal are displayed
- if --send-discord is used and rules JSON is missing/invalid, sending is refused
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

from ai_tag_numeric_rule_utils import format_score_for_discord, load_rules_json, score_signal_row  # noqa: E402
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
DEFAULT_AI_TAG_RULES_JSON = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json")
SCHEMA_VERSION = "gold_strict_7_discord_notifier_v8_wall_clock_guard_send_error_summary"
DISCORD_SAFE_MAX_CHARS = 1900

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
    "ai_tag_rule_hit_count",
    "ai_tag_rule_hits",
    "ai_tag_rules_json",
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
    "wall_clock_signal_time_local_est",
    "wall_clock_signal_age_minutes",
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
    "ai_tag_rule_hit_count",
    "ai_tag_rule_hits",
    "ai_tag_rules_json",
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


def mt5_time_to_local_est(value: Any, mt5_to_local_hours: float) -> pd.Timestamp | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts) + pd.Timedelta(hours=float(mt5_to_local_hours))


def minutes_since_local_est(value: Any, *, mt5_to_local_hours: float, now_local: pd.Timestamp) -> float | None:
    local_est = mt5_time_to_local_est(value, mt5_to_local_hours)
    if local_est is None:
        return None
    return float((now_local - local_est).total_seconds() / 60.0)


def truncate_for_discord(message: str) -> str:
    if len(message) <= DISCORD_SAFE_MAX_CHARS:
        return message
    suffix = "\n\n[TRUNCATED] Discord文字数制限回避のため本文を短縮。詳細はmessage_path JSONを確認。"
    return message[: max(0, DISCORD_SAFE_MAX_CHARS - len(suffix))] + suffix


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


def row_for_ai_score(row: pd.Series, spec: GoldStrictSignalSpec) -> dict[str, Any]:
    out = {str(k): json_safe(v) for k, v in row.to_dict().items()}
    out["strategy_id"] = spec.strategy_id
    out["direction"] = spec.direction
    out["m15_signal_candle_close_pos"] = safe_float(row.get("close_pos"))
    out["m15_signal_candle_range_atr_ratio"] = safe_float(row.get("range_atr"))
    out["m15_signal_candle_body_ratio"] = safe_float(row.get("body_ratio"))
    out["m15_macd_hist_at_entry"] = safe_float(row.get("macd_hist"))
    out["m15_macd_hist_delta_at_entry"] = safe_float(row.get("macd_hist_delta"))
    for col in [
        "h1_close_vs_ema20_atr", "h1_close_vs_ema50_atr", "h1_close_vs_ema200_atr",
        "h4_close_vs_ema20_atr", "h4_close_vs_ema50_atr", "d1_close_vs_ema20_atr",
    ]:
        if col in row.index:
            out[col] = safe_float(row.get(col))
    return out


def build_message(row: pd.Series, spec: GoldStrictSignalSpec, *, ai_score: dict[str, Any]) -> str:
    entry, tp, sl = calc_prices(row, spec)
    side_icon = "🟢" if spec.direction == "BUY" else "🔴"
    age = safe_float(row.get("wall_clock_signal_age_minutes"))
    age_line = "" if age is None else f"シグナル経過: {age:.1f}分（MT5+6h換算）"
    lines = [
        f"{side_icon} **GOLD {spec.direction} シグナル**",
        "",
        f"タイプ: {strategy_display_name(spec.strategy_id)}",
        f"Session: {spec.session}",
        f"エントリー目安: {time_text(row.get('close_time'))}",
    ]
    if age_line:
        lines.append(age_line)
    lines.extend([
        "",
        f"価格目安: Entry {fmt_price(entry)} / TP {fmt_price(tp)} / SL {fmt_price(sl)}",
        f"値幅: TP {fmt_num(spec.tp_pips, 1)} pips / SL {fmt_num(spec.sl_pips, 1)} pips / RR {fmt_num(spec.rr, 2)}",
        "価格注記: M5確定足終値ベース。実約定・スプレッドでズレあり。",
        "",
        "AIタグ推定:",
    ])
    lines.extend(format_score_for_discord(ai_score))
    lines.extend([
        "個別AI判定: 未実施（OpenAIは呼ばない）",
        "注記: 過去AI評価タグを数値条件化し、現在シグナルにHITしたものだけ表示。",
    ])
    return truncate_for_discord("\n".join(lines))


def ai_score_hit_text(ai_score: dict[str, Any]) -> str:
    hits = ai_score.get("hits", []) if isinstance(ai_score, dict) else []
    return "|".join(clean_str(h.get("tag_name")) for h in hits if isinstance(h, dict))


def row_to_preview(row: pd.Series, spec: GoldStrictSignalSpec, *, key: str, message_path: Path, discord_sent: bool, dry_run: bool, ai_score: dict[str, Any]) -> dict[str, Any]:
    entry, tp, sl = calc_prices(row, spec)
    hits = ai_score.get("hits", []) if isinstance(ai_score, dict) else []
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
        "ai_tag_rule_hit_count": int(len(hits)),
        "ai_tag_rule_hits": ai_score_hit_text(ai_score),
        "ai_tag_rules_json": ai_score.get("rules_path", "") if isinstance(ai_score, dict) else "",
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
        "wall_clock_signal_time_local_est": clean_str(row.get("wall_clock_signal_time_local_est")),
        "wall_clock_signal_age_minutes": safe_float(row.get("wall_clock_signal_age_minutes")),
        "reason": clean_str(row.get("reason")),
        "discord_sent": bool(discord_sent),
        "dry_run": bool(dry_run),
        "message_path": str(message_path),
    }


def message_filename(key: str, row: pd.Series, spec: GoldStrictSignalSpec) -> str:
    key_hash = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"gold_strict7_{spec.direction}_{id_time_text(row.get('close_time'))}_{key_hash}.json"


def write_message(out_dir: Path, key: str, message: str, row: pd.Series, spec: GoldStrictSignalSpec, ai_score: dict[str, Any]) -> Path:
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
        "ai_tag_score": ai_score,
        "message": message,
        "audit": {
            "strict_no_future_ok": bool(row.get("strict_no_future_ok", False)),
            "h1_close_time": time_text(row.get("h1_close_time")),
            "h4_close_time": time_text(row.get("h4_close_time")),
            "d1_close_time": time_text(row.get("d1_close_time")),
            "wall_clock_signal_time_local_est": clean_str(row.get("wall_clock_signal_time_local_est")),
            "wall_clock_signal_age_minutes": safe_float(row.get("wall_clock_signal_age_minutes")),
            "reason": clean_str(row.get("reason")),
            "internal_name": spec.strategy_id,
        },
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


def collect_signals(ctx: pd.DataFrame, specs: list[GoldStrictSignalSpec], args: argparse.Namespace) -> tuple[list[tuple[pd.Timestamp, GoldStrictSignalSpec, pd.Series]], dict[str, Any]]:
    now_local = pd.Timestamp(datetime.now())
    mt5_to_local_hours = float(args.mt5_to_local_hours)
    max_csv_staleness = int(args.max_csv_staleness_minutes)
    max_signal_age = int(args.max_wall_clock_signal_age_minutes)
    guard = {
        "enabled": True,
        "now_local": now_local.strftime("%Y-%m-%d %H:%M:%S"),
        "mt5_to_local_hours": mt5_to_local_hours,
        "max_csv_staleness_minutes": max_csv_staleness,
        "max_wall_clock_signal_age_minutes": max_signal_age,
        "ctx_last_close_time_mt5": "",
        "ctx_last_close_time_local_est": "",
        "csv_staleness_minutes": None,
        "csv_stale_guard_triggered": False,
        "signals_before_wall_clock_guard": 0,
        "signals_after_wall_clock_guard": 0,
        "signals_filtered_by_wall_clock_age": 0,
    }
    if ctx.empty:
        return [], guard
    last_close = ctx.iloc[-1]["close_time"]
    last_close_local = mt5_time_to_local_est(last_close, mt5_to_local_hours)
    guard["ctx_last_close_time_mt5"] = time_text(last_close)
    guard["ctx_last_close_time_local_est"] = "" if last_close_local is None else last_close_local.strftime("%Y-%m-%d %H:%M:%S")
    if last_close_local is not None:
        guard["csv_staleness_minutes"] = float((now_local - last_close_local).total_seconds() / 60.0)
    if max_csv_staleness > 0 and guard["csv_staleness_minutes"] is not None and float(guard["csv_staleness_minutes"]) > max_csv_staleness:
        guard["csv_stale_guard_triggered"] = True
        return [], guard
    end_idx = len(ctx) - 1 - int(args.bar_offset)
    if end_idx < 0:
        return [], guard
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
    guard["signals_before_wall_clock_guard"] = int(len(items))
    filtered_items: list[tuple[pd.Timestamp, GoldStrictSignalSpec, pd.Series]] = []
    for t, spec, row in items:
        age = minutes_since_local_est(row.get("close_time"), mt5_to_local_hours=mt5_to_local_hours, now_local=now_local)
        if age is None:
            continue
        if max_signal_age > 0 and (age < -2.0 or age > max_signal_age):
            continue
        enriched = row.copy()
        local_est = mt5_time_to_local_est(row.get("close_time"), mt5_to_local_hours)
        enriched["wall_clock_signal_time_local_est"] = "" if local_est is None else local_est.strftime("%Y-%m-%d %H:%M:%S")
        enriched["wall_clock_signal_age_minutes"] = float(age)
        filtered_items.append((t, spec, enriched))
    guard["signals_after_wall_clock_guard"] = int(len(filtered_items))
    guard["signals_filtered_by_wall_clock_age"] = int(len(items) - len(filtered_items))
    filtered_items.sort(key=lambda x: (x[0], x[1].strategy_id))
    if args.max_notifications > 0:
        filtered_items = filtered_items[-int(args.max_notifications):]
    return filtered_items, guard


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
    p.add_argument("--ai-tag-rules-json", type=Path, default=DEFAULT_AI_TAG_RULES_JSON)
    p.add_argument("--scan-recent-bars", type=int, default=300)
    p.add_argument("--bar-offset", type=int, default=1, help="1 means ignore the latest M5 row as potentially forming.")
    p.add_argument("--tail-m5", type=int, default=20000)
    p.add_argument("--tail-h1", type=int, default=5000)
    p.add_argument("--tail-h4", type=int, default=2000)
    p.add_argument("--tail-d1", type=int, default=1000)
    p.add_argument("--max-notifications", type=int, default=10)
    p.add_argument("--max-wall-clock-signal-age-minutes", type=int, default=30, help="Suppress notifications when signal close_time + MT5 offset is older than this many local minutes. 0 disables.")
    p.add_argument("--max-csv-staleness-minutes", type=int, default=15, help="Suppress all notifications when latest M5 close_time + MT5 offset is older than this many local minutes. 0 disables.")
    p.add_argument("--mt5-to-local-hours", type=float, default=6.0, help="Local time offset from MT5 server timestamps. JST=MT5+6 for the current broker setup.")
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
    rules_path = resolve_path(args.ai_tag_rules_json)
    mkdirp(out_dir)
    load_env_file(env_file)
    rules_obj = load_rules_json(rules_path)
    if args.send_discord and not bool(rules_obj.get("cycle_ok", False)):
        raise SystemExit(
            "GOLD AI tag numeric rules JSON is missing or invalid; refusing to send Discord. "
            f"Run scripts\\build_gold_strict_7_ai_tag_numeric_rules.bat first. path={rules_path}"
        )

    paths = resolve_csv_paths(args)
    ctx = load_context(paths, args)
    notified_keys = load_notified_keys(ledger_csv)
    signals, freshness_guard = collect_signals(ctx, specs, args)

    webhook_url = args.discord_webhook_url or os.environ.get("GOLD_STRICT_7_DISCORD_WEBHOOK_URL", "") or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise SystemExit("--send-discord requires --discord-webhook-url, GOLD_STRICT_7_DISCORD_WEBHOOK_URL, or DISCORD_WEBHOOK_URL in .env")

    preview_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    send_errors: list[dict[str, Any]] = []
    skipped_duplicates = 0
    ai_tag_hit_rows = 0
    discord_sent_rows = 0

    print("=" * 100, flush=True)
    print("GOLD Discord notifier", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"out_dir: {out_dir}", flush=True)
    print(f"ledger_csv: {ledger_csv}", flush=True)
    print(f"ai_tag_rules_json: {rules_path} ok={bool(rules_obj.get('cycle_ok', False))} rules={rules_obj.get('rules_count', len(rules_obj.get('rules', [])) if isinstance(rules_obj.get('rules', []), list) else 0)}", flush=True)
    print(f"env_file: {env_file} exists={env_file.exists()}", flush=True)
    for tf, p in paths.items():
        print(f"{tf}: {p}", flush=True)
    print(f"ctx_rows: {len(ctx)}", flush=True)
    if not ctx.empty:
        print(f"ctx_first_close_time: {time_text(ctx['close_time'].iloc[0])}", flush=True)
        print(f"ctx_last_close_time: {time_text(ctx['close_time'].iloc[-1])}", flush=True)
    print(f"scan_recent_bars: {args.scan_recent_bars}", flush=True)
    print(f"bar_offset: {args.bar_offset}", flush=True)
    print(f"wall_clock_freshness_guard: {json.dumps(freshness_guard, ensure_ascii=False, default=str)}", flush=True)
    print(f"raw_recent_signals_after_cooldown: {freshness_guard.get('signals_after_wall_clock_guard', len(signals))}", flush=True)
    print(f"already_notified_keys: {len(notified_keys)}", flush=True)
    print(f"send_discord: {bool(args.send_discord)}", flush=True)
    print(f"dry_run: {bool(args.dry_run)}", flush=True)
    print("=" * 100, flush=True)

    for _, spec, row in signals:
        key = notification_key(row, spec)
        if not args.allow_duplicate and key in notified_keys:
            skipped_duplicates += 1
            continue
        ai_score = score_signal_row(row_for_ai_score(row, spec), rules_obj, strategy_id=spec.strategy_id)
        if int(ai_score.get("hit_count", 0)) > 0:
            ai_tag_hit_rows += 1
        message = build_message(row, spec, ai_score=ai_score)
        message_path = write_message(out_dir, key, message, row, spec, ai_score)
        discord_sent = False
        print("\n" + "-" * 100, flush=True)
        print(message, flush=True)
        print(f"message_path: {message_path}", flush=True)
        if args.send_discord:
            try:
                send_discord_message(webhook_url, message)
                discord_sent = True
                discord_sent_rows += 1
                print("Discord sent: true", flush=True)
            except Exception as exc:
                err = {"notification_key": key, "type": type(exc).__name__, "message": str(exc), "message_path": str(message_path)}
                send_errors.append(err)
                print(f"Discord send error: {err}", flush=True)
        preview = row_to_preview(row, spec, key=key, message_path=message_path, discord_sent=discord_sent, dry_run=bool(args.dry_run), ai_score=ai_score)
        preview_rows.append(preview)
        if (args.send_discord and discord_sent) or args.mark_dry_run_notified:
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
        "cycle_ok": bool(len(send_errors) == 0),
        "reason": "OK" if len(send_errors) == 0 else "DISCORD_SEND_ERROR_SUMMARY_WRITTEN",
        "csv_paths": {tf: str(p) for tf, p in paths.items()},
        "out_dir": str(out_dir),
        "preview_csv": str(preview_csv),
        "ledger_csv": str(ledger_csv),
        "ai_tag_rules_json": str(rules_path),
        "ai_tag_rules_cycle_ok": bool(rules_obj.get("cycle_ok", False)),
        "ai_tag_rules_count": int(rules_obj.get("rules_count", len(rules_obj.get("rules", [])))) if isinstance(rules_obj.get("rules", []), list) else 0,
        "ctx_rows": int(len(ctx)),
        "scan_recent_bars": int(args.scan_recent_bars),
        "bar_offset": int(args.bar_offset),
        "raw_recent_signals_after_cooldown": int(freshness_guard.get("signals_after_wall_clock_guard", len(signals))),
        "raw_recent_signals_before_wall_clock_guard": int(freshness_guard.get("signals_before_wall_clock_guard", 0)),
        "preview_rows": int(len(preview_rows)),
        "ai_tag_hit_rows": int(ai_tag_hit_rows),
        "skipped_duplicates": int(skipped_duplicates),
        "ledger_rows_appended": int(len(ledger_rows)),
        "send_discord": bool(args.send_discord),
        "discord_sent_rows": int(discord_sent_rows),
        "discord_send_error_rows": int(len(send_errors)),
        "discord_send_errors": send_errors,
        "dry_run": bool(args.dry_run),
        "wall_clock_freshness_guard": freshness_guard,
        "safety": {
            "discord_send": bool(args.send_discord),
            "mt5_calls": False,
            "order_send": False,
            "ai_calls": False,
            "requires_valid_ai_tag_rules_on_send": True,
            "live_runtime_state_mutation": bool(len(ledger_rows) > 0),
            "wall_clock_freshness_guard_enabled": True,
            "discord_message_safe_max_chars": int(DISCORD_SAFE_MAX_CHARS),
            "ledger_append_requires_send_success_or_mark_dry_run": True,
        },
    }
    with open(windows_long_path(summary_json), "w", encoding="utf-8", newline="") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    print("\n" + "=" * 100, flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    print("=" * 100, flush=True)
    return 0 if len(send_errors) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())