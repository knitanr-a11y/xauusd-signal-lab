#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Forever-aligned GOLD DISC8 live decision audit loop.

This script is intentionally audit-only.
It does NOT call OpenAI, send Discord, or place MT5 orders.

Purpose:
- Build a single shared DISC8 candidate decision ledger.
- Keep notification and autotrade future entrypoints thin.
- Avoid divergent detection/gate logic between notification and autotrade.

Current safety note:
The operational runtime gate JSON requires a validated pre-send tagger. Until that
exists, detected candidates are written as PENDING_TAGGER, not ALLOW. This prevents
accidental connection to Discord/MT5 before tag-gate parity is validated.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_MANIFEST_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.json")
DEFAULT_GATE_RULES_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_live_decision_audit")
SCHEMA_VERSION = "gold_disc8_live_decision_audit_v1_pending_tagger_common_ledger"

CANDIDATE_COLUMNS = [
    "created_at", "schema_version", "decision_key", "decision", "dispatch_ready",
    "strategy_id", "direction", "entry_time", "entry_price", "tp_price", "sl_price",
    "tp_pips", "sl_pips", "rr", "condition_count", "matched_conditions", "failed_conditions",
    "gate_status", "gate_block_hits", "gate_watch_hits", "requires_pre_send_tagger",
    "tagger_status", "strict_no_future_ok", "context_h1_close_time", "context_h4_close_time", "context_d1_close_time",
    "wall_clock_signal_time_local_est", "wall_clock_signal_age_minutes", "reason",
]

LEDGER_COLUMNS = CANDIDATE_COLUMNS + ["ledger_appended_at", "loop_iteration"]

LOOP_SUMMARY_COLUMNS = [
    "loop_started_at", "loop_iteration", "scheduled_for", "started_at", "finished_at", "elapsed_seconds",
    "success", "csv_dir", "scan_recent_bars", "bar_offset", "max_signal_age_minutes", "candidates_detected",
    "allow_count", "pending_tagger_count", "block_count", "watch_count", "ledger_rows_appended",
    "m15_rows", "h1_rows", "h4_rows", "d1_rows", "latest_m15_time", "summary_json", "candidates_csv",
]


@dataclass(frozen=True)
class Condition:
    feature: str
    op: str
    threshold: float
    source_text: str


def now() -> datetime:
    return datetime.now()


def ts_text(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")


def safe_file_ts(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y%m%d_%H%M%S")


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


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    p = resolve_repo_path(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON not found: {p}")
    with open(windows_long_path(p), "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON root must be object: {p}")
    return obj


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def append_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        return
    mkdirp(path.parent)
    exists = path.exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def weekly_dir(base_dir: Path, dt: datetime) -> Path:
    iso = dt.isocalendar()
    return base_dir / f"{dt.year:04d}" / f"{dt.month:02d}" / f"week_{iso.week:02d}"


def clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    s = str(value).strip()
    return s if s else default


def as_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def safe_div(a: Any, b: Any) -> float | None:
    x = as_float(a)
    y = as_float(b)
    if x is None or y is None or abs(y) <= 1e-12:
        return None
    return x / y


def read_ohlc_csv(path: Path, *, tail: int = 0) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"OHLC CSV not found: {path}")
    # MT5 exports in this project have used both semicolon and comma. sep=None handles both.
    df = pd.read_csv(windows_long_path(path), sep=None, engine="python", encoding="utf-8-sig")
    if df.empty:
        raise RuntimeError(f"OHLC CSV is empty: {path}")
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        if key in {"time", "datetime", "date", "timestamp"}:
            rename[col] = "time"
        elif key in {"open", "o"}:
            rename[col] = "open"
        elif key in {"high", "h"}:
            rename[col] = "high"
        elif key in {"low", "l"}:
            rename[col] = "low"
        elif key in {"close", "c"}:
            rename[col] = "close"
        elif key in {"tick_volume", "volume", "vol"}:
            rename[col] = "volume"
    df = df.rename(columns=rename)
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing OHLC columns in {path}: {missing}; columns={list(df.columns)}")
    out = df[required + (["volume"] if "volume" in df.columns else [])].copy()
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    if tail and len(out) > tail:
        out = out.tail(tail).reset_index(drop=True)
    return out


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prev_close = out["close"].shift(1)
    tr = pd.concat([
        (out["high"] - out["low"]).abs(),
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=3).mean()
    for span in [50, 200]:
        out[f"ema{span}"] = out["close"].ewm(span=span, adjust=False, min_periods=span // 3).mean()
        out[f"dist_ema{span}_atr"] = (out["close"] - out[f"ema{span}"]) / out["atr14"]
    ema12 = out["close"].ewm(span=12, adjust=False, min_periods=4).mean()
    ema26 = out["close"].ewm(span=26, adjust=False, min_periods=9).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False, min_periods=3).mean()
    out["macd_hist"] = macd - signal
    # ADX14, Wilder-style approximation using rolling smoothing. Good enough for audit; not used to send orders.
    up_move = out["high"].diff()
    down_move = -out["low"].diff()
    plus_dm = pd.Series([u if (pd.notna(u) and pd.notna(d) and u > d and u > 0) else 0.0 for u, d in zip(up_move, down_move)], index=out.index)
    minus_dm = pd.Series([d if (pd.notna(u) and pd.notna(d) and d > u and d > 0) else 0.0 for u, d in zip(up_move, down_move)], index=out.index)
    atr_sum = tr.rolling(14, min_periods=3).sum()
    plus_di = 100.0 * plus_dm.rolling(14, min_periods=3).sum() / atr_sum
    minus_di = 100.0 * minus_dm.rolling(14, min_periods=3).sum() / atr_sum
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).abs().replace(0, pd.NA)) * 100.0
    out["adx14"] = dx.rolling(14, min_periods=3).mean()
    for n in [4, 8, 16, 32, 48, 72, 96]:
        hi = out["high"].rolling(n, min_periods=max(2, min(n, 5))).max().shift(1)
        lo = out["low"].rolling(n, min_periods=max(2, min(n, 5))).min().shift(1)
        out[f"donch_pos_{n}"] = (out["close"] - lo) / (hi - lo).replace(0, pd.NA)
        out[f"ret_{n}_atr"] = (out["close"] - out["close"].shift(n)) / out["atr14"]
    return out


def with_context_close_time(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    delta = {"h1": pd.Timedelta(hours=1), "h4": pd.Timedelta(hours=4), "d1": pd.Timedelta(days=1)}[timeframe]
    out = df.copy()
    out[f"{timeframe}_close_time"] = out["time"] + delta
    return out


def prefix_context(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    keep = [c for c in df.columns if c not in {"open", "high", "low", "close", "volume"}]
    out = df[keep].copy()
    rename = {}
    for col in out.columns:
        if col == "time":
            rename[col] = f"{prefix}_open_time"
        elif col == f"{prefix}_close_time":
            rename[col] = f"{prefix}_close_time"
        elif not col.startswith(prefix + "_"):
            rename[col] = f"{prefix}_{col}"
    return out.rename(columns=rename)


def attach_context(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    out = m15.copy().sort_values("time").reset_index(drop=True)
    for prefix, ctx in [("h1", h1), ("h4", h4), ("d1", d1)]:
        pref = prefix_context(with_context_close_time(ctx, prefix), prefix).sort_values(f"{prefix}_close_time")
        out = pd.merge_asof(
            out.sort_values("time"), pref,
            left_on="time", right_on=f"{prefix}_close_time",
            direction="backward", allow_exact_matches=True,
        )
    return out.reset_index(drop=True)


def extract_conditions(text: str) -> list[Condition]:
    # Examples inside Japanese full-width parens: （h4_donch_pos_32 > 0.9956）
    conds: list[Condition] = []
    for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)", text):
        feature, op, threshold = match.group(1), match.group(2), float(match.group(3))
        conds.append(Condition(feature=feature, op=op, threshold=threshold, source_text=match.group(0)))
    return conds


def compare_value(value: Any, op: str, threshold: float) -> bool:
    x = as_float(value)
    if x is None:
        return False
    if op == ">":
        return x > threshold
    if op == ">=":
        return x >= threshold
    if op == "<":
        return x < threshold
    if op == "<=":
        return x <= threshold
    return False


def get_feature(row: pd.Series, feature: str) -> Any:
    # Manifest uses unprefixed M15 features and prefixed HTF features.
    if feature in row.index:
        return row[feature]
    # A few source rules may use m15_ prefix; map to unprefixed live M15 columns.
    if feature.startswith("m15_") and feature[4:] in row.index:
        return row[feature[4:]]
    return None


def parse_manifest(manifest_json: dict[str, Any]) -> list[dict[str, Any]]:
    strategies = manifest_json.get("strategies", [])
    if not isinstance(strategies, list):
        raise RuntimeError("manifest JSON must contain list 'strategies'")
    out = []
    for s in strategies:
        if not isinstance(s, dict) or not bool(s.get("enabled", True)):
            continue
        conditions = extract_conditions(clean(s.get("notification_reason_jp")))
        item = dict(s)
        item["conditions"] = conditions
        out.append(item)
    if not out:
        raise RuntimeError("No enabled DISC8 strategies in manifest")
    return out


def evaluate_strategy(row: pd.Series, strategy: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    matched = []
    failed = []
    for cond in strategy.get("conditions", []):
        value = get_feature(row, cond.feature)
        ok = compare_value(value, cond.op, cond.threshold)
        text = f"{cond.source_text} actual={'' if as_float(value) is None else round(float(value), 6)}"
        if ok:
            matched.append(text)
        else:
            failed.append(text)
    return len(failed) == 0 and len(matched) > 0, matched, failed


def pips_to_price(pips: Any) -> float | None:
    # GOLD project convention in fixed-pip backtests used 10 pips ~= 1.0 USD.
    x = as_float(pips)
    if x is None:
        return None
    return x / 10.0


def make_decision_key(strategy_id: str, direction: str, entry_time: Any) -> str:
    ts = pd.to_datetime(entry_time, errors="coerce")
    t = clean(entry_time) if pd.isna(ts) else pd.Timestamp(ts).floor("5min").strftime("%Y-%m-%d %H:%M:%S")
    return f"GOLD|DISC8|{strategy_id}|{direction}|{t}"


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


def load_pre_send_tags(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if path is None:
        return {}
    p = resolve_repo_path(path)
    if not p.exists():
        raise FileNotFoundError(f"pre-send tag file not found: {p}")
    rows: list[dict[str, Any]] = []
    if p.suffix.lower() == ".jsonl":
        with open(windows_long_path(p), "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
    else:
        rows = pd.read_csv(windows_long_path(p), encoding="utf-8-sig").to_dict("records")
    by_key: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = clean(r.get("decision_key")) or make_decision_key(clean(r.get("strategy_id")), clean(r.get("direction")), r.get("entry_time"))
        by_key.setdefault(key, []).append(r)
    return by_key


def apply_gate(decision_key: str, strategy_id: str, tags_by_key: dict[str, list[dict[str, Any]]], gate_rules: dict[str, Any]) -> tuple[str, list[str], list[str], str]:
    tags = tags_by_key.get(decision_key, [])
    if not tags:
        return "PENDING_TAGGER", [], [], "NO_VALIDATED_PRE_SEND_TAGS_SUPPLIED"
    block_rules = gate_rules.get("block_rules", []) if isinstance(gate_rules.get("block_rules"), list) else []
    watch_rules = gate_rules.get("watch_only_rules", []) if isinstance(gate_rules.get("watch_only_rules"), list) else []
    block_hits = []
    watch_hits = []
    for tag in tags:
        tg = clean(tag.get("tag_group"))
        tn = clean(tag.get("tag_name"))
        sid = clean(tag.get("strategy_id"), strategy_id)
        for r in block_rules:
            if sid == clean(r.get("strategy_id")) and tg == clean(r.get("tag_group")) and tn == clean(r.get("tag_name")):
                block_hits.append(clean(r.get("rule_id")) or f"{sid}:{tg}:{tn}")
        for r in watch_rules:
            if sid == clean(r.get("strategy_id")) and tg == clean(r.get("tag_group")) and tn == clean(r.get("tag_name")):
                watch_hits.append(clean(r.get("rule_id")) or f"{sid}:{tg}:{tn}")
    if block_hits:
        return "BLOCK", sorted(set(block_hits)), sorted(set(watch_hits)), "BLOCK_RULE_MATCH"
    if watch_hits:
        return "WATCH_ONLY", [], sorted(set(watch_hits)), "WATCH_ONLY_RULE_MATCH"
    return "ALLOW", [], [], "NO_BLOCK_OR_WATCH_RULE_MATCH"


def build_feature_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    csv_dir = Path(args.csv_dir)
    m15 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=args.tail_m15))
    h1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=args.tail_h1))
    h4 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=args.tail_h4))
    d1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=args.tail_d1))
    frame = attach_context(m15, h1, h4, d1)
    info = {
        "m15_rows": int(len(m15)), "h1_rows": int(len(h1)), "h4_rows": int(len(h4)), "d1_rows": int(len(d1)),
        "latest_m15_time": "" if frame.empty else str(frame["time"].iloc[-1]),
    }
    return frame, info


def scan_candidates(args: argparse.Namespace, manifest: list[dict[str, Any]], gate_rules: dict[str, Any], tags_by_key: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    frame, info = build_feature_frame(args)
    if frame.empty:
        return [], info
    if args.bar_offset < 0:
        raise RuntimeError("bar_offset must be >= 0")
    end_pos = len(frame) - int(args.bar_offset)
    if end_pos <= 0:
        scan = frame.iloc[0:0].copy()
    else:
        scan = frame.iloc[max(0, end_pos - int(args.scan_recent_bars)):end_pos].copy()
    now_local = pd.Timestamp.now()
    rows: list[dict[str, Any]] = []
    for _, bar in scan.iterrows():
        age_min = minutes_since_local_est(bar.get("time"), mt5_to_local_hours=float(args.mt5_to_local_hours), now_local=now_local)
        if args.max_signal_age_minutes > 0 and age_min is not None and age_min > float(args.max_signal_age_minutes):
            continue
        for strategy in manifest:
            ok, matched, failed = evaluate_strategy(bar, strategy)
            if not ok:
                continue
            sid = clean(strategy.get("strategy_id"))
            direction = clean(strategy.get("direction"))
            entry_price = as_float(bar.get("close"))
            tp_step = pips_to_price(strategy.get("tp_pips"))
            sl_step = pips_to_price(strategy.get("sl_pips"))
            tp_price = ""
            sl_price = ""
            if entry_price is not None and tp_step is not None and sl_step is not None:
                if direction.upper() == "BUY":
                    tp_price = entry_price + tp_step
                    sl_price = entry_price - sl_step
                else:
                    tp_price = entry_price - tp_step
                    sl_price = entry_price + sl_step
            dkey = make_decision_key(sid, direction, bar.get("time"))
            gate_status, block_hits, watch_hits, gate_reason = apply_gate(dkey, sid, tags_by_key, gate_rules)
            dispatch_ready = gate_status == "ALLOW" and bool(tags_by_key.get(dkey))
            decision = gate_status
            reason = gate_reason
            if gate_status == "PENDING_TAGGER":
                decision = "PENDING_TAGGER"
                dispatch_ready = False
                reason = "候補検出済み。ただし検証済みpre-send tagger未供給のため通知/発注禁止。"
            row = {
                "created_at": ts_text(),
                "schema_version": SCHEMA_VERSION,
                "decision_key": dkey,
                "decision": decision,
                "dispatch_ready": bool(dispatch_ready),
                "strategy_id": sid,
                "direction": direction,
                "entry_time": str(bar.get("time")),
                "entry_price": "" if entry_price is None else round(entry_price, 3),
                "tp_price": "" if tp_price == "" else round(float(tp_price), 3),
                "sl_price": "" if sl_price == "" else round(float(sl_price), 3),
                "tp_pips": clean(strategy.get("tp_pips")),
                "sl_pips": clean(strategy.get("sl_pips")),
                "rr": clean(strategy.get("rr")),
                "condition_count": len(strategy.get("conditions", [])),
                "matched_conditions": " | ".join(matched),
                "failed_conditions": " | ".join(failed),
                "gate_status": gate_status,
                "gate_block_hits": " | ".join(block_hits),
                "gate_watch_hits": " | ".join(watch_hits),
                "requires_pre_send_tagger": bool(gate_rules.get("requires_pre_send_tagger", True)),
                "tagger_status": "VALIDATED_TAGS_SUPPLIED" if tags_by_key.get(dkey) else "MISSING_VALIDATED_TAGGER",
                "strict_no_future_ok": True,
                "context_h1_close_time": clean(bar.get("h1_close_time")),
                "context_h4_close_time": clean(bar.get("h4_close_time")),
                "context_d1_close_time": clean(bar.get("d1_close_time")),
                "wall_clock_signal_time_local_est": clean(mt5_time_to_local_est(bar.get("time"), float(args.mt5_to_local_hours))),
                "wall_clock_signal_age_minutes": "" if age_min is None else round(age_min, 3),
                "reason": reason,
            }
            rows.append(row)
    rows = rows[-int(args.max_decisions):] if args.max_decisions and len(rows) > int(args.max_decisions) else rows
    return rows, info


def next_aligned_time(interval_minutes: int, delay_seconds: int) -> datetime:
    n = now()
    base = n.replace(second=0, microsecond=0)
    next_minute = ((base.minute // interval_minutes) + 1) * interval_minutes
    hour_add = next_minute // 60
    next_minute %= 60
    return base.replace(minute=next_minute) + timedelta(hours=hour_add, seconds=delay_seconds)


def sleep_until(target: datetime) -> None:
    while True:
        remaining = (target - now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 1.0))


def run_iteration(args: argparse.Namespace, *, loop_started_at: str, iteration: int, scheduled_for: datetime, latest_dir: Path, loop_summary_csv: Path) -> dict[str, Any]:
    started = now()
    manifest_json = read_json(args.manifest_json)
    gate_rules = read_json(args.gate_rules_json)
    manifest = parse_manifest(manifest_json)
    tags_by_key = load_pre_send_tags(args.pre_send_tags) if args.pre_send_tags else {}
    candidates, info = scan_candidates(args, manifest, gate_rules, tags_by_key)
    candidates_csv = latest_dir / "gold_disc8_live_decision_candidates.csv"
    summary_json = latest_dir / "gold_disc8_live_decision_audit_summary.json"
    ledger_csv = resolve_repo_path(args.out_dir) / "gold_disc8_live_decision_ledger.csv"
    write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
    ledger_rows = []
    for row in candidates:
        lr = dict(row)
        lr["ledger_appended_at"] = ts_text()
        lr["loop_iteration"] = int(iteration)
        ledger_rows.append(lr)
    append_csv(ledger_csv, ledger_rows, LEDGER_COLUMNS)
    finished = now()
    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_NO_SEND_NO_ORDER",
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "loop_started_at": loop_started_at,
        "loop_iteration": int(iteration),
        "scheduled_for": ts_text(scheduled_for),
        "started_at": ts_text(started),
        "finished_at": ts_text(finished),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "csv_dir": str(args.csv_dir),
        "manifest_json": str(args.manifest_json),
        "gate_rules_json": str(args.gate_rules_json),
        "pre_send_tags": "" if not args.pre_send_tags else str(args.pre_send_tags),
        "scan_recent_bars": int(args.scan_recent_bars),
        "bar_offset": int(args.bar_offset),
        "max_signal_age_minutes": float(args.max_signal_age_minutes),
        "candidates_detected": int(len(candidates)),
        "allow_count": int(sum(1 for r in candidates if r.get("decision") == "ALLOW")),
        "pending_tagger_count": int(sum(1 for r in candidates if r.get("decision") == "PENDING_TAGGER")),
        "block_count": int(sum(1 for r in candidates if r.get("decision") == "BLOCK")),
        "watch_count": int(sum(1 for r in candidates if r.get("decision") == "WATCH_ONLY")),
        "dispatch_ready_count": int(sum(1 for r in candidates if bool(r.get("dispatch_ready")))),
        "ledger_rows_appended": int(len(ledger_rows)),
        "candidates_csv": str(candidates_csv),
        "ledger_csv": str(ledger_csv),
        **info,
    }
    write_json(summary_json, summary)
    loop_row = {k: summary.get(k, "") for k in LOOP_SUMMARY_COLUMNS}
    loop_row["success"] = True
    loop_row["summary_json"] = str(summary_json)
    loop_row["candidates_csv"] = str(candidates_csv)
    append_csv(loop_summary_csv, [loop_row], LOOP_SUMMARY_COLUMNS)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GOLD DISC8 live decision audit forever loop.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--gate-rules-json", type=Path, default=DEFAULT_GATE_RULES_JSON)
    p.add_argument("--pre-send-tags", type=Path, default=None, help="Optional validated pre-send tag CSV/JSONL. Without this, decisions remain PENDING_TAGGER.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--interval-minutes", type=int, default=1)
    p.add_argument("--run-delay-seconds", type=int, default=5)
    p.add_argument("--scan-recent-bars", type=int, default=36)
    p.add_argument("--bar-offset", type=int, default=0)
    p.add_argument("--max-signal-age-minutes", type=float, default=15.0)
    p.add_argument("--mt5-to-local-hours", type=float, default=6.0)
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=800)
    p.add_argument("--tail-d1", type=int, default=500)
    p.add_argument("--max-decisions", type=int, default=50)
    p.add_argument("--max-iterations", type=int, default=0)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--stop-on-error", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.interval_minutes <= 0 or 60 % args.interval_minutes != 0:
        raise SystemExit("--interval-minutes must be a positive divisor of 60")
    loop_started_at = ts_text()
    base_out = resolve_repo_path(args.out_dir)
    latest_dir = base_out / "latest"
    loop_base = weekly_dir(base_out, now())
    loop_summary_csv = loop_base / "gold_disc8_live_decision_loop_summary.csv"
    mkdirp(latest_dir)
    mkdirp(loop_base)
    print("=" * 100, flush=True)
    print("GOLD DISC8 live decision audit loop", flush=True)
    print(f"schema_version: {SCHEMA_VERSION}", flush=True)
    print(f"loop_started_at: {loop_started_at}", flush=True)
    print(f"csv_dir: {args.csv_dir}", flush=True)
    print(f"manifest_json: {args.manifest_json}", flush=True)
    print(f"gate_rules_json: {args.gate_rules_json}", flush=True)
    print("Safety: audit-only. No Discord send. No MT5 order send. No OpenAI call.", flush=True)
    print("Without --pre-send-tags, detected candidates are PENDING_TAGGER and dispatch_ready=False.", flush=True)
    print("=" * 100, flush=True)
    iteration = 0
    if args.run_immediately:
        iteration += 1
        try:
            row = run_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=now(), latest_dir=latest_dir, loop_summary_csv=loop_summary_csv)
        except Exception as exc:
            print(f"[ERROR] iteration failed: {type(exc).__name__}: {exc}", flush=True)
            if args.stop_on_error:
                return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0
    while True:
        scheduled = next_aligned_time(int(args.interval_minutes), int(args.run_delay_seconds))
        print(f"[{ts_text()}] next_run_at={ts_text(scheduled)}", flush=True)
        sleep_until(scheduled)
        iteration += 1
        try:
            run_iteration(args, loop_started_at=loop_started_at, iteration=iteration, scheduled_for=scheduled, latest_dir=latest_dir, loop_summary_csv=loop_summary_csv)
        except Exception as exc:
            print(f"[ERROR] iteration failed: {type(exc).__name__}: {exc}", flush=True)
            if args.stop_on_error:
                return 1
        if args.max_iterations and iteration >= args.max_iterations:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
