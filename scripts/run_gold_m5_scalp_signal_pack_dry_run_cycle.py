#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD M5 scalp signal pack dry-run cycle.

This runner is a multi-strategy sidecar slot. It only evaluates the latest
confirmed M5 candle and emits at most one OPEN_POSITION dry-run intent.

Implemented signals only:
- M5_BUY_DUMP_FADE_L48_W45_TP8_SL5_H120_MT5_13_20
- M5_SELL_H1S_H4N_E50_REJECT_MACD_TP3_SL2_H30_MT5_13_20
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

STRATEGY_SLOT = "GOLD_M5_SCALP_SIGNAL_PACK"
STRATEGY_ID = "GOLD_M5_SCALP_SIGNAL_PACK_V1"
SYMBOL = "GOLD"
TF_MIN = {"M5": 5, "H1": 60, "H4": 240}
CSV_FILES = {"M5": "goldsharp_m5.csv", "H1": "goldsharp_h1.csv", "H4": "goldsharp_h4.csv"}

CANDIDATE_COLUMNS = [
    "detected_at_utc", "strategy_slot", "strategy_id", "signal_id", "direction", "rank", "trade_enabled",
    "priority", "signal_time", "signal_close_time", "entry_price_reference", "sl_price", "tp_price", "risk_price",
    "reward_price", "rr", "tp_usd", "sl_usd", "tp_pips", "sl_pips", "max_hold_minutes", "condition_pass",
    "condition_reason", "h1_close", "h1_ema20", "h1_ema50", "h4_close", "h4_ema20", "h4_ema50",
    "m5_open", "m5_high", "m5_low", "m5_close", "m5_ema20", "m5_ema50", "m5_rsi14", "m5_macd_hist",
    "m5_macd_hist_prev", "m5_lower_wick_ratio", "m5_body_ratio", "m5_lower48_prev", "mt5_hour",
]
SELECTED_COLUMNS = CANDIDATE_COLUMNS + ["selection_reason", "signal_key"]
REJECT_COLUMNS = CANDIDATE_COLUMNS + ["reject_reason"]
LEDGER_COLUMNS = [
    "created_at_utc", "status", "strategy_slot", "strategy_id", "signal_id", "signal_key", "direction", "rank",
    "trade_enabled", "intent_type", "signal_close_time", "entry_price_reference", "sl_price", "tp_price", "risk_price",
    "reward_price", "rr", "tp_pips", "sl_pips", "max_hold_minutes",
]
CYCLE_LOG_COLUMNS = [
    "cycle_start_utc", "cycle_end_utc", "cycle_ok", "strategy_slot", "strategy_id", "csv_dir", "out_dir",
    "latest_m5_close_time", "candidate_count", "passed_candidate_count", "selected_signal_id", "signal_found", "rank",
    "trade_enabled", "intent_type", "signal_key", "reason", "order_intent_path", "total_seconds",
]


@dataclass(frozen=True)
class SignalSpec:
    signal_id: str
    direction: str
    rank: str
    trade_enabled: bool
    priority: int
    tp_usd: float
    sl_usd: float
    max_hold_minutes: int


SPECS = [
    SignalSpec("M5_BUY_DUMP_FADE_L48_W45_TP8_SL5_H120_MT5_13_20", "BUY", "CORE", True, 10, 8.0, 5.0, 120),
    SignalSpec("M5_SELL_H1S_H4N_E50_REJECT_MACD_TP3_SL2_H30_MT5_13_20", "SELL", "STANDARD", True, 20, 3.0, 2.0, 30),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD M5 scalp signal pack dry-run cycle.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_m5_scalp_signal_pack"))
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--max-lot-per-trade", type=float, default=0.01)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--tail-m5", type=int, default=20000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=1500)
    return p.parse_args()


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


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def path_exists(path: Path) -> bool:
    return Path(windows_long_path(path)).exists()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    ensure_parent_dir(path)
    if df.empty:
        df = pd.DataFrame(columns=columns)
    else:
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        df = df[columns]
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        windows_long_path(path), mode="a", header=not path_exists(path), index=False, encoding="utf-8-sig"
    )


def sniff_sep(path: Path) -> str:
    sample = Path(windows_long_path(path)).read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_ohlc_csv(path: Path, timeframe: str, *, tail_bars: int, csv_sep: str) -> pd.DataFrame:
    if not path_exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    sep = sniff_sep(path) if csv_sep == "auto" else csv_sep
    df = pd.read_csv(windows_long_path(path), sep=sep, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"datetime": "time", "date": "time", "timestamp": "time", "tickvolume": "tick_volume", "tick volume": "tick_volume", "volume": "tick_volume"})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing columns in {path}: {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df.sort_values("time", kind="mergesort").drop_duplicates(subset=["time"], keep="last")
    if tail_bars > 0:
        df = df.tail(int(tail_bars)).copy()
    df["close_time"] = df["time"] + pd.to_timedelta(TF_MIN[timeframe], unit="m")
    return df.reset_index(drop=True)


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["macd"] = ema(out["close"], 6) - ema(out["close"], 13)
    out["macd_signal"] = ema(out["macd"], 4)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["rsi14"] = rsi(out["close"], 14)
    candle_range = (out["high"] - out["low"]).replace(0, np.nan)
    lower_body = out[["open", "close"]].min(axis=1)
    upper_body = out[["open", "close"]].max(axis=1)
    out["lower_wick"] = lower_body - out["low"]
    out["upper_wick"] = out["high"] - upper_body
    out["body"] = (out["close"] - out["open"]).abs()
    out["lower_wick_ratio"] = out["lower_wick"] / candle_range
    out["body_ratio"] = out["body"] / candle_range
    out["lower48_prev"] = out["low"].shift(1).rolling(48, min_periods=48).min()
    return out


def sf(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def latest_context_row(df: pd.DataFrame, close_time: pd.Timestamp) -> pd.Series | None:
    eligible = df[df["close_time"] <= close_time].copy()
    if eligible.empty:
        return None
    return eligible.sort_values("close_time", kind="mergesort").iloc[-1]


def strong_down(row: pd.Series | None) -> bool:
    return bool(row is not None and sf(row.get("ema20")) < sf(row.get("ema50")) and sf(row.get("close")) < sf(row.get("ema50")))


def strong_up(row: pd.Series | None) -> bool:
    return bool(row is not None and sf(row.get("ema20")) > sf(row.get("ema50")) and sf(row.get("close")) > sf(row.get("ema50")))


def is_trade_hour(close_time: pd.Timestamp) -> bool:
    hour = int(close_time.hour)
    return 13 <= hour <= 20


def check_condition(spec: SignalSpec, m5: pd.Series, prev: pd.Series | None, ctx: dict[str, pd.Series | None]) -> tuple[bool, str]:
    close_time = pd.Timestamp(m5["close_time"])
    if not is_trade_hour(close_time):
        return False, "OUT_OF_MT5_HOUR_13_20"
    h1, h4 = ctx["H1"], ctx["H4"]
    c, o, h, l = sf(m5.get("close")), sf(m5.get("open")), sf(m5.get("high")), sf(m5.get("low"))
    e20, e50 = sf(m5.get("ema20")), sf(m5.get("ema50"))
    hist = sf(m5.get("macd_hist"))
    hist_prev = sf(m5.get("macd_hist_prev"))
    if spec.signal_id == "M5_BUY_DUMP_FADE_L48_W45_TP8_SL5_H120_MT5_13_20":
        ok = (
            not strong_down(h4)
            and math.isfinite(sf(m5.get("lower48_prev")))
            and l <= sf(m5.get("lower48_prev"))
            and sf(m5.get("lower_wick_ratio")) >= 0.45
            and c > o
            and sf(m5.get("rsi14")) <= 45
            and hist > hist_prev
        )
        return ok, "H4 not strong down + M5 lower48 sweep + lower_wick>=45% + bullish close + RSI<=45 + MACD hist improving"
    if spec.signal_id == "M5_SELL_H1S_H4N_E50_REJECT_MACD_TP3_SL2_H30_MT5_13_20":
        ok = (
            strong_down(h1)
            and not strong_up(h4)
            and math.isfinite(e50)
            and h >= e50
            and c < e20
            and c < o
            and hist < hist_prev
        )
        return ok, "H1 strong down + H4 not strong up + M5 EMA50 touch/reject + close<EMA20 bearish + MACD hist worsening"
    return False, "UNKNOWN_SIGNAL"


def pips_from_usd(value: float) -> float:
    return float(value) * 10.0


def candidate_row(now_text: str, spec: SignalSpec, m5: pd.Series, ctx: dict[str, pd.Series | None], ok: bool, reason: str) -> dict[str, Any]:
    entry = sf(m5.get("close"))
    sl = entry - spec.sl_usd if spec.direction == "BUY" else entry + spec.sl_usd
    tp = entry + spec.tp_usd if spec.direction == "BUY" else entry - spec.tp_usd
    risk, reward = abs(entry - sl), abs(tp - entry)
    h1, h4 = ctx["H1"], ctx["H4"]
    return {
        "detected_at_utc": now_text, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID,
        "signal_id": spec.signal_id, "direction": spec.direction, "rank": spec.rank, "trade_enabled": spec.trade_enabled,
        "priority": spec.priority, "signal_time": str(pd.Timestamp(m5["time"])), "signal_close_time": str(pd.Timestamp(m5["close_time"])),
        "entry_price_reference": round(entry, 3), "sl_price": round(sl, 3), "tp_price": round(tp, 3),
        "risk_price": round(risk, 3), "reward_price": round(reward, 3), "rr": round(reward / risk, 6) if risk > 0 else "",
        "tp_usd": spec.tp_usd, "sl_usd": spec.sl_usd, "tp_pips": pips_from_usd(spec.tp_usd), "sl_pips": pips_from_usd(spec.sl_usd),
        "max_hold_minutes": spec.max_hold_minutes, "condition_pass": bool(ok), "condition_reason": reason,
        "h1_close": sf(h1.get("close")) if h1 is not None else "", "h1_ema20": sf(h1.get("ema20")) if h1 is not None else "", "h1_ema50": sf(h1.get("ema50")) if h1 is not None else "",
        "h4_close": sf(h4.get("close")) if h4 is not None else "", "h4_ema20": sf(h4.get("ema20")) if h4 is not None else "", "h4_ema50": sf(h4.get("ema50")) if h4 is not None else "",
        "m5_open": sf(m5.get("open")), "m5_high": sf(m5.get("high")), "m5_low": sf(m5.get("low")), "m5_close": sf(m5.get("close")),
        "m5_ema20": sf(m5.get("ema20")), "m5_ema50": sf(m5.get("ema50")), "m5_rsi14": sf(m5.get("rsi14")),
        "m5_macd_hist": sf(m5.get("macd_hist")), "m5_macd_hist_prev": sf(m5.get("macd_hist_prev")),
        "m5_lower_wick_ratio": sf(m5.get("lower_wick_ratio")), "m5_body_ratio": sf(m5.get("body_ratio")),
        "m5_lower48_prev": sf(m5.get("lower48_prev")), "mt5_hour": int(pd.Timestamp(m5["close_time"]).hour),
    }


def select_signal(candidates: pd.DataFrame) -> tuple[dict[str, Any] | None, pd.DataFrame]:
    passed = candidates[candidates["condition_pass"].astype(bool)].copy() if not candidates.empty else pd.DataFrame()
    if passed.empty:
        rejected = candidates.copy()
        rejected["reject_reason"] = "CONDITION_NOT_MET"
        return None, rejected
    passed = passed.sort_values(["priority", "signal_close_time"], ascending=[True, True], kind="mergesort")
    selected = passed.iloc[0].to_dict()
    selected["selection_reason"] = "SELECTED_LOWEST_PRIORITY_ON_LATEST_M5"
    selected["signal_key"] = f"{STRATEGY_ID}|{selected['signal_id']}|{selected['signal_close_time']}|{selected['direction']}"
    rejected = candidates.copy()
    rejected["reject_reason"] = ["" if bool(r.get("condition_pass", False)) and str(r.get("signal_id")) == str(selected["signal_id"]) else ("PRIORITY_LOST_TO_" + str(selected["signal_id"]) if bool(r.get("condition_pass", False)) else "CONDITION_NOT_MET") for _, r in rejected.iterrows()]
    return selected, rejected


def build_intent(selected: dict[str, Any], base_lot: float, max_lot: float) -> dict[str, Any]:
    lot = min(float(base_lot), float(max_lot))
    return {
        "schema_version": "gold_m5_scalp_signal_pack_order_intent_v1", "dry_run": True, "intent_type": "OPEN_POSITION",
        "created_at_utc": utc_now_text(), "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID,
        "condition_id": selected["signal_id"], "signal_id": selected["signal_id"], "signal_key": selected["signal_key"],
        "symbol": SYMBOL, "direction": selected["direction"], "rank": selected["rank"], "trade_enabled": True,
        "entry_type": "MARKET_REFERENCE_M5_CLOSE", "signal_time": selected["signal_close_time"],
        "entry_price_reference": selected["entry_price_reference"], "sl_price": selected["sl_price"], "tp_price": selected["tp_price"],
        "risk_price": selected["risk_price"], "reward_price": selected["reward_price"], "rr": selected["rr"],
        "max_hold_minutes": selected["max_hold_minutes"], "max_hold_hours": round(float(selected["max_hold_minutes"]) / 60.0, 6),
        "tp_pips": selected["tp_pips"], "sl_pips": selected["sl_pips"],
        "lot": {"base_lot": float(base_lot), "lot_multiplier": 1.0, "effective_lot": float(lot)},
        "notes": {"pips_conversion": "GOLD 1.0 USD = 10 pips", "selection_reason": selected.get("selection_reason", "")},
    }


def no_signal_result(now_text: str, args: argparse.Namespace, latest_close: str, candidate_count: int, passed_count: int, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "gold_m5_scalp_signal_pack_scan_v1", "scan_time_utc": now_text,
        "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "cycle_ok": True, "signal_found": False,
        "rank": "", "trade_enabled": False, "duplicate": False, "signal_key": "", "reason": reason,
        "latest_m5_close_time": latest_close, "candidate_count": int(candidate_count), "passed_candidate_count": int(passed_count),
        "latest_candidate_entry_time": "", "out_dir": str(args.out_dir),
    }


def main() -> int:
    args = parse_args()
    started = datetime.now(UTC)
    cycle_start = utc_now_text()
    now_text = utc_now_text()
    mkdir_path(args.out_dir)
    try:
        frames = {
            "M5": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["M5"], "M5", tail_bars=args.tail_m5, csv_sep=args.csv_sep)),
            "H1": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["H1"], "H1", tail_bars=args.tail_h1, csv_sep=args.csv_sep)),
            "H4": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["H4"], "H4", tail_bars=args.tail_h4, csv_sep=args.csv_sep)),
        }
        m5_df = frames["M5"].sort_values("close_time", kind="mergesort").reset_index(drop=True)
        if m5_df.empty:
            raise RuntimeError("NO_M5_ROWS")
        idx = -2 if args.latest_confirmed_policy == "second_last" and len(m5_df) >= 2 else -1
        m5 = m5_df.iloc[idx].copy()
        prev = m5_df.iloc[idx - 1].copy() if len(m5_df) >= abs(idx) + 1 else None
        m5["macd_hist_prev"] = prev.get("macd_hist") if prev is not None else np.nan
        latest_close_ts = pd.Timestamp(m5["close_time"])
        latest_close = latest_close_ts.strftime("%Y-%m-%d %H:%M:%S")
        ctx = {"H1": latest_context_row(frames["H1"], latest_close_ts), "H4": latest_context_row(frames["H4"], latest_close_ts)}
        rows = []
        for spec in SPECS:
            ok, reason = check_condition(spec, m5, prev, ctx)
            rows.append(candidate_row(now_text, spec, m5, ctx, ok, reason))
        candidates = pd.DataFrame(rows)
        selected, rejected = select_signal(candidates)
        passed_count = int(candidates["condition_pass"].astype(bool).sum()) if not candidates.empty else 0
        write_csv(candidates, args.out_dir / "m5_scalp_candidates_latest.csv", CANDIDATE_COLUMNS)
        write_csv(pd.DataFrame([selected]) if selected else pd.DataFrame(columns=SELECTED_COLUMNS), args.out_dir / "m5_scalp_selected_latest.csv", SELECTED_COLUMNS)
        write_csv(rejected, args.out_dir / "m5_scalp_rejected_latest.csv", REJECT_COLUMNS)
        if selected is None:
            result = no_signal_result(now_text, args, latest_close, len(candidates), passed_count, "NO_SIGNAL_ON_LATEST_CONFIRMED_M5")
            if path_exists(args.out_dir / "order_intent_dry_run.json"):
                try:
                    Path(windows_long_path(args.out_dir / "order_intent_dry_run.json")).unlink()
                except Exception:
                    pass
            write_json(args.out_dir / "latest_scan_result.json", result)
            write_json(args.out_dir / "latest_dry_run_cycle_result.json", {"cycle_ok": True, "latest_scan_result": result})
            append_csv_row(args.out_dir / "dry_run_cycle_log.csv", {"cycle_start_utc": cycle_start, "cycle_end_utc": utc_now_text(), "cycle_ok": True, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "csv_dir": str(args.csv_dir), "out_dir": str(args.out_dir), "latest_m5_close_time": latest_close, "candidate_count": len(candidates), "passed_candidate_count": passed_count, "selected_signal_id": "", "signal_found": False, "rank": "", "trade_enabled": False, "intent_type": "", "signal_key": "", "reason": result["reason"], "order_intent_path": "", "total_seconds": round((datetime.now(UTC)-started).total_seconds(),3)}, CYCLE_LOG_COLUMNS)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
            return 0
        intent = build_intent(selected, args.base_lot, args.max_lot_per_trade)
        write_json(args.out_dir / "order_intent_dry_run.json", intent)
        append_csv_row(args.out_dir / "signal_ledger.csv", {"created_at_utc": now_text, "status": "DRY_RUN_SIGNAL_CREATED", "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "signal_id": selected["signal_id"], "signal_key": selected["signal_key"], "direction": selected["direction"], "rank": selected["rank"], "trade_enabled": True, "intent_type": "OPEN_POSITION", "signal_close_time": selected["signal_close_time"], "entry_price_reference": selected["entry_price_reference"], "sl_price": selected["sl_price"], "tp_price": selected["tp_price"], "risk_price": selected["risk_price"], "reward_price": selected["reward_price"], "rr": selected["rr"], "tp_pips": selected["tp_pips"], "sl_pips": selected["sl_pips"], "max_hold_minutes": selected["max_hold_minutes"]}, LEDGER_COLUMNS)
        result = {"schema_version": "gold_m5_scalp_signal_pack_scan_v1", "scan_time_utc": now_text, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "cycle_ok": True, "signal_found": True, "selected_signal_id": selected["signal_id"], "rank": selected["rank"], "trade_enabled": True, "duplicate": False, "signal_key": selected["signal_key"], "reason": "SIGNAL_FOUND_ON_LATEST_CONFIRMED_M5", "latest_m5_close_time": latest_close, "candidate_count": int(len(candidates)), "passed_candidate_count": passed_count, "latest_candidate_entry_time": selected["signal_close_time"], "direction": selected["direction"], "entry_price_reference": selected["entry_price_reference"], "sl_price": selected["sl_price"], "tp_price": selected["tp_price"], "risk_price": selected["risk_price"], "reward_price": selected["reward_price"], "rr": selected["rr"], "tp_pips": selected["tp_pips"], "sl_pips": selected["sl_pips"], "max_hold_minutes": selected["max_hold_minutes"], "intent_type": "OPEN_POSITION", "order_intent_path": str(args.out_dir / "order_intent_dry_run.json"), "out_dir": str(args.out_dir)}
        write_json(args.out_dir / "latest_scan_result.json", result)
        write_json(args.out_dir / "latest_dry_run_cycle_result.json", {"schema_version": "gold_m5_scalp_signal_pack_dry_run_cycle_v1", "cycle_ok": True, "latest_scan_result": result, "selected": selected})
        append_csv_row(args.out_dir / "dry_run_cycle_log.csv", {"cycle_start_utc": cycle_start, "cycle_end_utc": utc_now_text(), "cycle_ok": True, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "csv_dir": str(args.csv_dir), "out_dir": str(args.out_dir), "latest_m5_close_time": latest_close, "candidate_count": len(candidates), "passed_candidate_count": passed_count, "selected_signal_id": selected["signal_id"], "signal_found": True, "rank": selected["rank"], "trade_enabled": True, "intent_type": "OPEN_POSITION", "signal_key": selected["signal_key"], "reason": result["reason"], "order_intent_path": str(args.out_dir / "order_intent_dry_run.json"), "total_seconds": round((datetime.now(UTC)-started).total_seconds(),3)}, CYCLE_LOG_COLUMNS)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 0
    except Exception as exc:
        error = {"schema_version": "gold_m5_scalp_signal_pack_scan_v1", "scan_time_utc": now_text, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "cycle_ok": False, "signal_found": False, "rank": "", "trade_enabled": False, "duplicate": False, "signal_key": "", "reason": "ERROR", "error": repr(exc), "out_dir": str(args.out_dir)}
        write_json(args.out_dir / "latest_scan_result.json", error)
        write_json(args.out_dir / "latest_dry_run_cycle_result.json", {"cycle_ok": False, "latest_scan_result": error})
        print(json.dumps(error, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
