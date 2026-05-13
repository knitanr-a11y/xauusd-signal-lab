#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""GOLD ALT PF signal pack dry-run cycle.

This strategy pack is intentionally integrated as a multi-strategy sidecar slot.
It does not mutate Mochipoyo production state, does not send Discord, and does
not place MT5 orders.

Scope:
- Evaluate the latest confirmed M15 candle only.
- Emit at most one selected signal for the latest M15 close_time.
- OPEN_POSITION intents are emitted only for trade_enabled signals.
- OBSERVE_ONLY intents are emitted for observe candidates and are skipped by the
  existing multi-strategy autotrade adapter.
- Same-direction same-M15 candidates are resolved by priority inside this pack.
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

STRATEGY_SLOT = "GOLD_ALT_PF_SIGNAL_PACK"
STRATEGY_ID = "GOLD_ALT_PF_SIGNAL_PACK_V1"
SYMBOL = "GOLD"

TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}
CSV_FILES = {"M15": "goldsharp_m15.csv", "H1": "goldsharp_h1.csv", "H4": "goldsharp_h4.csv", "D1": "goldsharp_d1.csv"}

CANDIDATE_COLUMNS = [
    "detected_at_utc", "strategy_slot", "strategy_id", "signal_id", "direction", "rank", "trade_enabled",
    "priority", "signal_time", "signal_close_time", "entry_price_reference", "sl_price", "tp_price", "risk_price",
    "reward_price", "rr", "tp_usd", "sl_usd", "tp_pips", "sl_pips", "max_hold_hours", "condition_pass",
    "condition_reason", "h1_close", "h1_ema20", "h1_ema50", "h4_close", "h4_ema20", "h4_ema50",
    "d1_close", "d1_ema20", "m15_close", "m15_ema20", "m15_ema50", "m15_rsi14", "m15_macd_hist",
    "m15_macd_hist_prev",
]
SELECTED_COLUMNS = CANDIDATE_COLUMNS + ["selection_reason", "signal_key"]
REJECT_COLUMNS = CANDIDATE_COLUMNS + ["reject_reason"]
LEDGER_COLUMNS = [
    "created_at_utc", "status", "strategy_slot", "strategy_id", "signal_id", "signal_key", "direction", "rank",
    "trade_enabled", "intent_type", "signal_close_time", "entry_price_reference", "sl_price", "tp_price", "risk_price",
    "reward_price", "rr", "tp_pips", "sl_pips",
]
CYCLE_LOG_COLUMNS = [
    "cycle_start_utc", "cycle_end_utc", "cycle_ok", "strategy_slot", "strategy_id", "csv_dir", "out_dir",
    "latest_m15_close_time", "candidate_count", "passed_candidate_count", "selected_signal_id", "signal_found", "rank",
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
    max_hold_hours: float


SPECS: list[SignalSpec] = [
    SignalSpec("SELL_STRICT_D1_EMA20_REJECT_TP20_SL12", "SELL", "CORE", True, 10, 20.0, 12.0, 48.0),
    SignalSpec("SELL_PB_EMA20_REJECT_TP20_SL12", "SELL", "STANDARD", True, 20, 20.0, 12.0, 48.0),
    SignalSpec("SELL_EMA50_PULLBACK_REACCEL_TP20_SL12", "SELL", "STANDARD", True, 30, 20.0, 12.0, 48.0),
    SignalSpec("SELL_LOW12_BREAK_STRONG_TP20_SL10", "SELL", "FREQUENCY", True, 40, 20.0, 10.0, 48.0),
    SignalSpec("SELL_BB_UPPER_REENTRY_TP30_SL15", "SELL", "OBSERVE", False, 50, 30.0, 15.0, 48.0),
    SignalSpec("BUY_RSI_RECOVER_CLOSE_GT_EMA50_TP25_SL12", "BUY", "OBSERVE", False, 60, 25.0, 12.0, 48.0),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD ALT PF signal pack dry-run cycle.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_alt_pf_signal_pack"))
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--max-lot-per-trade", type=float, default=0.01)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--tail-m15", type=int, default=5000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=1500)
    p.add_argument("--tail-d1", type=int, default=800)
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


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def write_csv(df: pd.DataFrame, path: Path, columns: list[str] | None = None) -> None:
    ensure_parent_dir(path)
    if columns is not None:
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
    df["close_time"] = df["time"] + pd.to_timedelta(TIMEFRAME_MINUTES[timeframe], unit="m")
    return df.reset_index(drop=True)


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]).abs(), (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["atr14"] = atr(out, 14)
    out["macd"] = ema(out["close"], 6) - ema(out["close"], 13)
    out["macd_signal"] = ema(out["macd"], 4)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["rsi14"] = rsi(out["close"], 14)
    mid = out["close"].rolling(20, min_periods=20).mean()
    sd = out["close"].rolling(20, min_periods=20).std()
    out["bb_upper20"] = mid + 2.0 * sd
    out["body"] = (out["close"] - out["open"]).abs()
    out["range"] = (out["high"] - out["low"]).replace(0, np.nan)
    out["body_ratio"] = out["body"] / out["range"]
    out["lower12_prev"] = out["low"].shift(1).rolling(12, min_periods=12).min()
    return out


def latest_context_row(df: pd.DataFrame, close_time: pd.Timestamp) -> pd.Series | None:
    eligible = df[df["close_time"] <= close_time].copy()
    if eligible.empty:
        return None
    return eligible.sort_values("close_time", kind="mergesort").iloc[-1]


def sf(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def bool_down(row: pd.Series | None, *, strict: bool = False) -> bool:
    if row is None:
        return False
    close, e20, e50 = sf(row.get("close")), sf(row.get("ema20")), sf(row.get("ema50"))
    return (e20 < e50 and close < e50) if strict else (close < e50 or e20 < e50)


def bool_up(row: pd.Series | None, *, strict: bool = False) -> bool:
    if row is None:
        return False
    close, e20, e50 = sf(row.get("close")), sf(row.get("ema20")), sf(row.get("ema50"))
    return (e20 > e50 and close > e50) if strict else (close > e50 or e20 > e50)


def m15_rejects_ema20(row: pd.Series) -> bool:
    close, open_, high, e20 = sf(row.get("close")), sf(row.get("open")), sf(row.get("high")), sf(row.get("ema20"))
    hist, hist_prev = sf(row.get("macd_hist")), sf(row.get("macd_hist_prev"))
    return math.isfinite(e20) and close < e20 and (open_ >= e20 or high >= e20) and hist < 0 and hist < hist_prev


def compute_context(frames: dict[str, pd.DataFrame], latest_m15_close: pd.Timestamp) -> dict[str, pd.Series | None]:
    return {"H1": latest_context_row(frames["H1"], latest_m15_close), "H4": latest_context_row(frames["H4"], latest_m15_close), "D1": latest_context_row(frames["D1"], latest_m15_close)}


def condition_for_spec(spec: SignalSpec, m15: pd.Series, prev: pd.Series | None, ctx: dict[str, pd.Series | None]) -> tuple[bool, str]:
    h1, h4, d1 = ctx["H1"], ctx["H4"], ctx["D1"]
    close, open_, high = sf(m15.get("close")), sf(m15.get("open")), sf(m15.get("high"))
    e20, e50 = sf(m15.get("ema20")), sf(m15.get("ema50"))
    hist, hist_prev = sf(m15.get("macd_hist")), sf(m15.get("macd_hist_prev"))
    rsi14, lower12, bb_upper, body_ratio = sf(m15.get("rsi14")), sf(m15.get("lower12_prev")), sf(m15.get("bb_upper20")), sf(m15.get("body_ratio"))
    prev_rsi = sf(prev.get("rsi14")) if prev is not None else float("nan")
    prev_close = sf(prev.get("close")) if prev is not None else float("nan")
    prev_bb_upper = sf(prev.get("bb_upper20")) if prev is not None else float("nan")
    h1_down, h4_down, d1_down = bool_down(h1), bool_down(h4, strict=True), bool_down(d1)
    d1_below_ema20 = d1 is not None and sf(d1.get("close")) < sf(d1.get("ema20"))
    h1_up = bool_up(h1, strict=True)
    sid = spec.signal_id
    if sid == "SELL_STRICT_D1_EMA20_REJECT_TP20_SL12":
        return h1_down and h4_down and d1_below_ema20 and m15_rejects_ema20(m15), "H1/H4 down + D1 close<EMA20 + M15 EMA20 reject + MACD hist down"
    if sid == "SELL_PB_EMA20_REJECT_TP20_SL12":
        h1_pullback = h1_down and h1 is not None and sf(h1.get("high")) >= sf(h1.get("ema20"))
        return h4_down and h1_pullback and m15_rejects_ema20(m15), "H4 down + H1 pullback + M15 EMA20 reject + MACD hist down"
    if sid == "SELL_EMA50_PULLBACK_REACCEL_TP20_SL12":
        ema50_pullback = math.isfinite(e50) and high >= e50 and close < e20 < e50
        return h4_down and h1_down and d1_down and ema50_pullback and hist < 0 and hist < hist_prev, "H1/H4/D1 down + M15 EMA50 pullback + close<EMA20<EMA50 + MACD hist down"
    if sid == "SELL_LOW12_BREAK_STRONG_TP20_SL10":
        strong_break = math.isfinite(lower12) and close < lower12 and close < open_ and body_ratio >= 0.45
        return h4_down and h1_down and d1_down and strong_break and hist < hist_prev, "H1/H4/D1 down + M15 lower12 break + strong bearish body + MACD hist down"
    if sid == "SELL_BB_UPPER_REENTRY_TP30_SL15":
        reentry = math.isfinite(bb_upper) and math.isfinite(prev_bb_upper) and high >= bb_upper and prev_close >= prev_bb_upper and close < bb_upper
        return h4_down and h1_down and reentry and 30 <= rsi14 <= 55 and hist < hist_prev, "OBSERVE: H4/H1 down + BB upper reentry + RSI 30-55 + MACD hist down"
    if sid == "BUY_RSI_RECOVER_CLOSE_GT_EMA50_TP25_SL12":
        recover = math.isfinite(prev_rsi) and prev_rsi <= 45 and rsi14 > prev_rsi and close > e50 and close > open_
        return h1_up and recover and hist > hist_prev, "OBSERVE: H1 up + RSI recover + close>EMA50 + bullish candle + MACD hist up"
    return False, "UNKNOWN_SPEC"


def pips_from_usd(value: float) -> float:
    return float(value) * 10.0


def build_candidate_row(now: str, spec: SignalSpec, m15: pd.Series, ctx: dict[str, pd.Series | None], condition_pass: bool, condition_reason: str) -> dict[str, Any]:
    entry = sf(m15.get("close"))
    sl = entry + spec.sl_usd if spec.direction == "SELL" else entry - spec.sl_usd
    tp = entry - spec.tp_usd if spec.direction == "SELL" else entry + spec.tp_usd
    risk, reward = abs(entry - sl), abs(tp - entry)
    rr = reward / risk if risk > 0 else float("nan")
    h1, h4, d1 = ctx["H1"], ctx["H4"], ctx["D1"]
    return {
        "detected_at_utc": now, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "signal_id": spec.signal_id,
        "direction": spec.direction, "rank": spec.rank, "trade_enabled": bool(spec.trade_enabled), "priority": int(spec.priority),
        "signal_time": str(pd.Timestamp(m15["time"])), "signal_close_time": str(pd.Timestamp(m15["close_time"])),
        "entry_price_reference": round(entry, 3), "sl_price": round(sl, 3), "tp_price": round(tp, 3),
        "risk_price": round(risk, 3), "reward_price": round(reward, 3), "rr": round(rr, 6) if math.isfinite(rr) else "",
        "tp_usd": float(spec.tp_usd), "sl_usd": float(spec.sl_usd), "tp_pips": pips_from_usd(spec.tp_usd),
        "sl_pips": pips_from_usd(spec.sl_usd), "max_hold_hours": float(spec.max_hold_hours), "condition_pass": bool(condition_pass),
        "condition_reason": condition_reason,
        "h1_close": sf(h1.get("close")) if h1 is not None else "", "h1_ema20": sf(h1.get("ema20")) if h1 is not None else "", "h1_ema50": sf(h1.get("ema50")) if h1 is not None else "",
        "h4_close": sf(h4.get("close")) if h4 is not None else "", "h4_ema20": sf(h4.get("ema20")) if h4 is not None else "", "h4_ema50": sf(h4.get("ema50")) if h4 is not None else "",
        "d1_close": sf(d1.get("close")) if d1 is not None else "", "d1_ema20": sf(d1.get("ema20")) if d1 is not None else "",
        "m15_close": sf(m15.get("close")), "m15_ema20": sf(m15.get("ema20")), "m15_ema50": sf(m15.get("ema50")),
        "m15_rsi14": sf(m15.get("rsi14")), "m15_macd_hist": sf(m15.get("macd_hist")), "m15_macd_hist_prev": sf(m15.get("macd_hist_prev")),
    }


def select_signal(candidates: pd.DataFrame) -> tuple[dict[str, Any] | None, pd.DataFrame]:
    passed = candidates[candidates["condition_pass"].astype(bool)].copy() if not candidates.empty else pd.DataFrame()
    if passed.empty:
        rejected = candidates.copy()
        rejected["reject_reason"] = "CONDITION_NOT_MET"
        return None, rejected
    passed = passed.sort_values(["priority", "signal_close_time"], ascending=[True, True], kind="mergesort").reset_index(drop=True)
    selected = passed.iloc[0].to_dict()
    selected["selection_reason"] = "SELECTED_LOWEST_PRIORITY_ON_LATEST_M15"
    selected["signal_key"] = f"{STRATEGY_ID}|{selected['signal_id']}|{selected['signal_close_time']}|{selected['direction']}"
    rejected = candidates.copy()
    rejected["reject_reason"] = ["" if bool(r.get("condition_pass", False)) and str(r.get("signal_id")) == str(selected["signal_id"]) else ("PRIORITY_LOST_TO_" + str(selected["signal_id"]) if bool(r.get("condition_pass", False)) else "CONDITION_NOT_MET") for _, r in rejected.iterrows()]
    return selected, rejected


def build_order_intent(selected: dict[str, Any], *, base_lot: float, max_lot: float) -> dict[str, Any]:
    intent_type = "OPEN_POSITION" if bool(selected.get("trade_enabled", False)) else "OBSERVE_ONLY"
    effective_lot = min(float(base_lot), float(max_lot)) if intent_type == "OPEN_POSITION" else 0.0
    return {
        "schema_version": "gold_alt_pf_signal_pack_order_intent_v1", "dry_run": True, "intent_type": intent_type,
        "created_at_utc": utc_now_text(), "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID,
        "condition_id": selected["signal_id"], "signal_id": selected["signal_id"], "signal_key": selected["signal_key"],
        "symbol": SYMBOL, "direction": selected["direction"], "rank": selected["rank"], "trade_enabled": bool(selected.get("trade_enabled", False)),
        "entry_type": "MARKET_REFERENCE_M15_CLOSE", "signal_time": selected["signal_close_time"], "entry_price_reference": selected["entry_price_reference"],
        "sl_price": selected["sl_price"], "tp_price": selected["tp_price"], "risk_price": selected["risk_price"], "reward_price": selected["reward_price"],
        "rr": selected["rr"], "max_hold_hours": selected["max_hold_hours"], "tp_pips": selected["tp_pips"], "sl_pips": selected["sl_pips"],
        "lot": {"base_lot": float(base_lot), "lot_multiplier": 1.0 if intent_type == "OPEN_POSITION" else 0.0, "effective_lot": float(effective_lot)},
        "notes": {"pips_conversion": "GOLD 1.0 USD = 10 pips", "selection_reason": selected.get("selection_reason", "")},
    }


def build_no_signal_result(now: str, args: argparse.Namespace, latest_close: str, candidate_count: int, reason: str) -> dict[str, Any]:
    return {"schema_version": "gold_alt_pf_signal_pack_scan_v1", "scan_time_utc": now, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "cycle_ok": True, "signal_found": False, "rank": "", "trade_enabled": False, "duplicate": False, "signal_key": "", "reason": reason, "latest_m15_close_time": latest_close, "candidate_count": int(candidate_count), "latest_candidate_entry_time": "", "out_dir": str(args.out_dir)}


def main() -> int:
    args = parse_args()
    started = datetime.now(UTC)
    cycle_start, now = utc_now_text(), utc_now_text()
    mkdir_path(args.out_dir)
    try:
        frames = {
            "M15": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["M15"], "M15", tail_bars=args.tail_m15, csv_sep=args.csv_sep)),
            "H1": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["H1"], "H1", tail_bars=args.tail_h1, csv_sep=args.csv_sep)),
            "H4": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["H4"], "H4", tail_bars=args.tail_h4, csv_sep=args.csv_sep)),
            "D1": add_indicators(read_ohlc_csv(args.csv_dir / CSV_FILES["D1"], "D1", tail_bars=args.tail_d1, csv_sep=args.csv_sep)),
        }
        m15_df = frames["M15"].sort_values("close_time", kind="mergesort").reset_index(drop=True)
        if m15_df.empty:
            result = build_no_signal_result(now, args, "", 0, "NO_M15_ROWS")
            write_json(args.out_dir / "latest_scan_result.json", result)
            return 1
        idx = -2 if args.latest_confirmed_policy == "second_last" and len(m15_df) >= 2 else -1
        m15 = m15_df.iloc[idx].copy()
        prev = m15_df.iloc[idx - 1].copy() if len(m15_df) >= abs(idx) + 1 else None
        m15["macd_hist_prev"] = prev.get("macd_hist") if prev is not None else np.nan
        latest_close_ts = pd.Timestamp(m15["close_time"])
        latest_close = latest_close_ts.strftime("%Y-%m-%d %H:%M:%S")
        ctx = compute_context(frames, latest_close_ts)
        rows = []
        for spec in SPECS:
            ok, reason = condition_for_spec(spec, m15, prev, ctx)
            rows.append(build_candidate_row(now, spec, m15, ctx, ok, reason))
        candidates = pd.DataFrame(rows)
        selected, rejected = select_signal(candidates)
        write_csv(candidates, args.out_dir / "alt_pf_signal_candidates_latest.csv", CANDIDATE_COLUMNS)
        write_csv(pd.DataFrame([selected]) if selected else pd.DataFrame(columns=SELECTED_COLUMNS), args.out_dir / "alt_pf_signal_selected_latest.csv", SELECTED_COLUMNS)
        write_csv(rejected, args.out_dir / "alt_pf_signal_rejected_latest.csv", REJECT_COLUMNS)
        passed_count = int(candidates["condition_pass"].astype(bool).sum()) if not candidates.empty else 0
        if selected is None:
            result = build_no_signal_result(now, args, latest_close, len(candidates), "NO_SIGNAL_ON_LATEST_CONFIRMED_M15")
            write_json(args.out_dir / "latest_scan_result.json", result)
            if path_exists(args.out_dir / "order_intent_dry_run.json"):
                try:
                    Path(windows_long_path(args.out_dir / "order_intent_dry_run.json")).unlink()
                except Exception:
                    pass
            append_csv_row(args.out_dir / "dry_run_cycle_log.csv", {"cycle_start_utc": cycle_start, "cycle_end_utc": utc_now_text(), "cycle_ok": True, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "csv_dir": str(args.csv_dir), "out_dir": str(args.out_dir), "latest_m15_close_time": latest_close, "candidate_count": len(candidates), "passed_candidate_count": passed_count, "selected_signal_id": "", "signal_found": False, "rank": "", "trade_enabled": False, "intent_type": "", "signal_key": "", "reason": result["reason"], "order_intent_path": "", "total_seconds": round((datetime.now(UTC) - started).total_seconds(), 3)}, CYCLE_LOG_COLUMNS)
            write_json(args.out_dir / "latest_dry_run_cycle_result.json", {"cycle_ok": True, "latest_scan_result": result})
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
            return 1
        intent = build_order_intent(selected, base_lot=args.base_lot, max_lot=args.max_lot_per_trade)
        write_json(args.out_dir / "order_intent_dry_run.json", intent)
        ledger_status = "DRY_RUN_SIGNAL_CREATED" if intent["intent_type"] == "OPEN_POSITION" else "OBSERVE_ONLY_CREATED"
        append_csv_row(args.out_dir / "signal_ledger.csv", {"created_at_utc": now, "status": ledger_status, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "signal_id": selected["signal_id"], "signal_key": selected["signal_key"], "direction": selected["direction"], "rank": selected["rank"], "trade_enabled": bool(selected["trade_enabled"]), "intent_type": intent["intent_type"], "signal_close_time": selected["signal_close_time"], "entry_price_reference": selected["entry_price_reference"], "sl_price": selected["sl_price"], "tp_price": selected["tp_price"], "risk_price": selected["risk_price"], "reward_price": selected["reward_price"], "rr": selected["rr"], "tp_pips": selected["tp_pips"], "sl_pips": selected["sl_pips"]}, LEDGER_COLUMNS)
        result = {"schema_version": "gold_alt_pf_signal_pack_scan_v1", "scan_time_utc": now, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "cycle_ok": True, "signal_found": True, "selected_signal_id": selected["signal_id"], "rank": selected["rank"], "trade_enabled": bool(selected["trade_enabled"]), "duplicate": False, "signal_key": selected["signal_key"], "reason": "SIGNAL_FOUND_ON_LATEST_CONFIRMED_M15", "latest_m15_close_time": latest_close, "candidate_count": int(len(candidates)), "passed_candidate_count": passed_count, "latest_candidate_entry_time": selected["signal_close_time"], "direction": selected["direction"], "entry_price_reference": selected["entry_price_reference"], "sl_price": selected["sl_price"], "tp_price": selected["tp_price"], "risk_price": selected["risk_price"], "reward_price": selected["reward_price"], "rr": selected["rr"], "tp_pips": selected["tp_pips"], "sl_pips": selected["sl_pips"], "intent_type": intent["intent_type"], "order_intent_path": str(args.out_dir / "order_intent_dry_run.json"), "out_dir": str(args.out_dir)}
        write_json(args.out_dir / "latest_scan_result.json", result)
        append_csv_row(args.out_dir / "dry_run_cycle_log.csv", {"cycle_start_utc": cycle_start, "cycle_end_utc": utc_now_text(), "cycle_ok": True, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "csv_dir": str(args.csv_dir), "out_dir": str(args.out_dir), "latest_m15_close_time": latest_close, "candidate_count": len(candidates), "passed_candidate_count": passed_count, "selected_signal_id": selected["signal_id"], "signal_found": True, "rank": selected["rank"], "trade_enabled": bool(selected["trade_enabled"]), "intent_type": intent["intent_type"], "signal_key": selected["signal_key"], "reason": result["reason"], "order_intent_path": str(args.out_dir / "order_intent_dry_run.json"), "total_seconds": round((datetime.now(UTC) - started).total_seconds(), 3)}, CYCLE_LOG_COLUMNS)
        write_json(args.out_dir / "latest_dry_run_cycle_result.json", {"schema_version": "gold_alt_pf_signal_pack_dry_run_cycle_v1", "cycle_ok": True, "latest_scan_result": result, "selected": selected})
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 0 if bool(selected["trade_enabled"]) else 1
    except Exception as exc:
        error = {"schema_version": "gold_alt_pf_signal_pack_scan_v1", "scan_time_utc": now, "strategy_slot": STRATEGY_SLOT, "strategy_id": STRATEGY_ID, "cycle_ok": False, "signal_found": False, "rank": "", "trade_enabled": False, "duplicate": False, "signal_key": "", "reason": "ERROR", "error": repr(exc), "out_dir": str(args.out_dir)}
        write_json(args.out_dir / "latest_scan_result.json", error)
        write_json(args.out_dir / "latest_dry_run_cycle_result.json", {"cycle_ok": False, "latest_scan_result": error})
        print(json.dumps(error, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
