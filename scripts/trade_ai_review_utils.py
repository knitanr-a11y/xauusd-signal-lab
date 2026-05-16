#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for the trade AI review journal pipeline.

This module intentionally stays self-contained and conservative:
- no MT5 dependency
- no OpenAI dependency
- UTF-8-SIG CSV output for Excel/Windows compatibility
- Windows long-path handling
- tolerant CSV time/column normalization

The AI review pipeline treats AI output as hypothesis tags only. Deterministic
facts such as PnL, R, MFE/MAE and timestamps must be computed by Python scripts
before any model is called.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

REVIEW_SCHEMA_VERSION = "trade_ai_review_v1"
PROMPT_VERSION = "trade_ai_review_prompt_v1"
TAG_TAXONOMY_VERSION = "trade_ai_tag_taxonomy_v1"
FEATURE_SNAPSHOT_VERSION = "trade_feature_snapshot_v1"
OUTCOME_LEDGER_SCHEMA_VERSION = "trade_outcome_ledger_v1"
TAG_SUMMARY_SCHEMA_VERSION = "trade_ai_tag_summary_v1"

UTC_TEXT_FORMAT = "%Y-%m-%d %H:%M:%S"

COMMON_TAGS = [
    "entry_after_extended_move",
    "m15_signal_candle_large",
    "near_recent_high",
    "near_recent_low",
    "against_h1_context",
    "against_h4_context",
    "low_volatility_fake_break",
    "high_volatility_chase",
    "poor_pullback_structure",
    "late_breakout",
    "range_edge_entry",
    "ema_distance_too_large",
    "macd_late_signal",
]

GOLD_TAGS = [
    "gold_h1_reversal_zone",
    "gold_london_ny_whipsaw",
    "gold_news_like_spike",
    "gold_fast_mean_reversion",
    "gold_near_daily_key_level",
]

BTC_TAGS = [
    "btc_spread_sensitive",
    "btc_weekend_thin_move",
    "btc_fast_reversal_after_break",
    "btc_slippage_sensitive",
    "btc_low_liquidity_chop",
    "btc_large_wick_reversal",
]

EXECUTION_SYSTEM_TAGS = [
    "wide_spread_at_entry",
    "entry_slippage_large",
    "close_slippage_large",
    "order_price_mismatch",
    "tp_sl_distance_invalid",
    "duplicate_context",
    "position_overlap_issue",
    "mt5_execution_delay",
    "missing_history_data",
]

ALLOWED_RISK_CATEGORIES = {
    "acceptable_loss",
    "bad_loss",
    "unclear_loss",
    "system_error_loss",
    "execution_loss",
    "good_win",
    "bad_win",
    "unclear",
}

ALLOWED_ISSUE_CATEGORIES = {
    "signal_quality_issue",
    "market_structure_issue",
    "execution_issue",
    "risk_setting_issue",
    "system_issue",
    "unclear",
}


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


def ensure_parent_dir(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime(UTC_TEXT_FORMAT)


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding=encoding, newline="") as f:
        f.write(text)


def read_text(path: str | Path, encoding: str = "utf-8") -> str:
    with open(windows_long_path(path), "r", encoding=encoding) as f:
        return f.read()


def write_json(path: str | Path, obj: Any) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=json_default))


def read_json_or_empty(path: str | Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def json_default(obj: Any) -> Any:
    if isinstance(obj, (pd.Timestamp, datetime)):
        if getattr(obj, "tzinfo", None) is not None:
            return obj.tz_convert(None).strftime(UTC_TEXT_FORMAT) if hasattr(obj, "tz_convert") else obj.astimezone(UTC).strftime(UTC_TEXT_FORMAT)
        return obj.strftime(UTC_TEXT_FORMAT)
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent_dir(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def read_csv(path: str | Path, *, sep: str | None = None) -> pd.DataFrame:
    if sep is not None:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=sep)
    # Try automatic separator detection first. If it fails, fall back to comma.
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")
    except Exception:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")


def append_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> int:
    ensure_parent_dir(path)
    count = 0
    with open(windows_long_path(path), "a", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=json_default) + "\n")
            count += 1
    return count


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> int:
    ensure_parent_dir(path)
    count = 0
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=json_default) + "\n")
            count += 1
    return count


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


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


def clean_float(x: Any, default: float | None = None) -> float | None:
    if x is None or x == "":
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    try:
        v = float(x)
    except Exception:
        return default
    if not math.isfinite(v):
        return default
    return v


def clean_int(x: Any, default: int = 0) -> int:
    if x is None or x == "":
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    try:
        return int(float(x))
    except Exception:
        return default


def clean_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    text = clean_str(x).lower()
    return text in {"true", "1", "yes", "y", "ok", "sent"}


def parse_time_any(x: Any, *, default: pd.Timestamp | None = None) -> pd.Timestamp | None:
    if x is None or x == "":
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    try:
        ts = pd.to_datetime(x, errors="coerce")
    except Exception:
        return default
    if pd.isna(ts):
        return default
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is not None:
            return ts.tz_convert(None)
        return ts
    return pd.Timestamp(ts)


def time_to_text(x: Any) -> str:
    ts = parse_time_any(x)
    if ts is None:
        return clean_str(x)
    return ts.strftime(UTC_TEXT_FORMAT)


def first_existing(row_or_df: Any, names: Iterable[str]) -> str | None:
    if isinstance(row_or_df, pd.DataFrame):
        cols = set(str(c) for c in row_or_df.columns)
        for name in names:
            if name in cols:
                return name
        lowered = {str(c).lower(): str(c) for c in row_or_df.columns}
        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]
        return None
    index = getattr(row_or_df, "index", [])
    cols = set(str(c) for c in index)
    for name in names:
        if name in cols:
            return name
    lowered = {str(c).lower(): str(c) for c in index}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def row_get(row: pd.Series, names: Iterable[str], default: Any = "") -> Any:
    col = first_existing(row, names)
    if col is None:
        return default
    value = row.get(col, default)
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    return value


def normalize_direction(text: Any) -> str:
    s = clean_str(text).upper()
    if s in {"BUY", "LONG", "0"}:
        return "BUY"
    if s in {"SELL", "SHORT", "1"}:
        return "SELL"
    if "BUY" in s or "LONG" in s:
        return "BUY"
    if "SELL" in s or "SHORT" in s:
        return "SELL"
    return s


def normalize_symbol_from_broker(symbol: Any) -> str:
    text = clean_str(symbol).upper()
    if not text:
        return ""
    for sep in ["#", ".", "_"]:
        if sep in text:
            text = text.split(sep)[0]
    if text.startswith("XAUUSD"):
        return "GOLD"
    return text


def side_price_distance(direction: str, entry: float | None, price: float | None) -> float | None:
    if entry is None or price is None:
        return None
    d = normalize_direction(direction)
    if d == "BUY":
        return float(price) - float(entry)
    if d == "SELL":
        return float(entry) - float(price)
    return None


def stop_distance(direction: str, entry: float | None, sl: float | None) -> float | None:
    if entry is None or sl is None:
        return None
    d = normalize_direction(direction)
    if d == "BUY":
        return float(entry) - float(sl)
    if d == "SELL":
        return float(sl) - float(entry)
    return None


def take_distance(direction: str, entry: float | None, tp: float | None) -> float | None:
    if entry is None or tp is None:
        return None
    d = normalize_direction(direction)
    if d == "BUY":
        return float(tp) - float(entry)
    if d == "SELL":
        return float(entry) - float(tp)
    return None


def profit_r_from_prices(direction: str, entry: float | None, sl: float | None, close: float | None) -> float | None:
    sd = stop_distance(direction, entry, sl)
    pdist = side_price_distance(direction, entry, close)
    if sd is None or pdist is None or abs(sd) <= 1e-12:
        return None
    return float(pdist) / abs(float(sd))


def classify_outcome(profit: float | None, profit_r: float | None, *, small_r: float = 0.10, small_profit_abs: float = 0.0) -> str:
    if profit_r is not None:
        if profit_r >= small_r:
            return "WIN"
        if profit_r <= -small_r:
            return "LOSS"
        if profit_r > 0:
            return "SMALL_WIN"
        if profit_r < 0:
            return "SMALL_LOSS"
        return "BREAKEVEN"
    if profit is None:
        return "UNKNOWN"
    if profit > small_profit_abs:
        return "WIN"
    if profit < -small_profit_abs:
        return "LOSS"
    return "BREAKEVEN"


def infer_close_reason(direction: str, close_price: float | None, sl: float | None, tp: float | None, *, tolerance: float = 1e-6) -> str:
    if close_price is None:
        return "UNKNOWN"
    d = normalize_direction(direction)
    if sl is not None and abs(float(close_price) - float(sl)) <= tolerance:
        return "SL"
    if tp is not None and abs(float(close_price) - float(tp)) <= tolerance:
        return "TP"
    # Some brokers close with small slippage. Use side-aware nearest level if close is beyond a level.
    if d == "BUY":
        if sl is not None and float(close_price) <= float(sl) + tolerance:
            return "SL"
        if tp is not None and float(close_price) >= float(tp) - tolerance:
            return "TP"
    if d == "SELL":
        if sl is not None and float(close_price) >= float(sl) - tolerance:
            return "SL"
        if tp is not None and float(close_price) <= float(tp) + tolerance:
            return "TP"
    return "UNKNOWN"


def canonical_trade_id(row: pd.Series | dict[str, Any]) -> str:
    if isinstance(row, dict):
        getter = row.get
    else:
        getter = row.get
    for key in ["trade_id", "order_key", "payload_key", "signal_key"]:
        value = clean_str(getter(key, ""))
        if value:
            return value
    parts = [
        clean_str(getter("symbol", "")),
        clean_str(getter("strategy_id", "")),
        clean_str(getter("direction", "")),
        clean_str(getter("entry_time", "")),
    ]
    raw = "|".join(parts)
    safe = re.sub(r"[^A-Za-z0-9_.|:-]+", "_", raw).strip("_")
    return safe or f"trade_{utc_stamp()}"


def asdict_obj(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "_asdict"):
        src = obj._asdict()
    elif isinstance(obj, dict):
        src = obj
    else:
        src = {"value": str(obj)}
    out: dict[str, Any] = {}
    for key, value in src.items():
        try:
            json.dumps(value, default=json_default)
            out[str(key)] = value
        except Exception:
            out[str(key)] = str(value)
    return out


def asdict_list(items: Any) -> list[dict[str, Any]]:
    if items is None:
        return []
    return [asdict_obj(item) for item in list(items)]


def normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    col_map: dict[str, str] = {}
    candidates = {
        "time": ["time", "Time", "datetime", "date", "Date", "timestamp", "close_time", "signal_close_time"],
        "open": ["open", "Open", "OPEN"],
        "high": ["high", "High", "HIGH"],
        "low": ["low", "Low", "LOW"],
        "close": ["close", "Close", "CLOSE"],
        "tick_volume": ["tick_volume", "volume", "Volume", "tickvol", "real_volume"],
    }
    for target, names in candidates.items():
        col = first_existing(out, names)
        if col is not None:
            col_map[col] = target
    out = out.rename(columns=col_map)
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"OHLCV CSV missing required columns {missing}; columns={list(df.columns)}")
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out = out.dropna(subset=["time"]).copy()
    for col in ["open", "high", "low", "close", "tick_volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close"]).copy()
    out = out.sort_values("time").drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
    return out


def add_indicators(df: pd.DataFrame, *, macd_fast: int = 6, macd_slow: int = 13, macd_signal: int = 4) -> pd.DataFrame:
    out = normalize_ohlcv_columns(df)
    if out.empty:
        return out
    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=1).mean()
    out["ema20"] = close.ewm(span=20, adjust=False, min_periods=1).mean()
    out["ema50"] = close.ewm(span=50, adjust=False, min_periods=1).mean()
    out["ema200"] = close.ewm(span=200, adjust=False, min_periods=1).mean()
    ema_fast = close.ewm(span=macd_fast, adjust=False, min_periods=1).mean()
    ema_slow = close.ewm(span=macd_slow, adjust=False, min_periods=1).mean()
    out["macd"] = ema_fast - ema_slow
    out["macd_signal"] = out["macd"].ewm(span=macd_signal, adjust=False, min_periods=1).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["macd_hist_delta"] = out["macd_hist"].diff()
    candle_range = (high - low).replace(0, pd.NA)
    out["body"] = (close - out["open"].astype(float)).abs()
    out["body_ratio"] = (out["body"] / candle_range).fillna(0.0)
    out["close_pos"] = ((close - low) / candle_range).fillna(0.5)
    return out


def record_to_jsonable(row: pd.Series) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.to_dict().items():
        if isinstance(value, pd.Timestamp):
            out[str(key)] = time_to_text(value)
        elif isinstance(value, float):
            out[str(key)] = None if not math.isfinite(value) else value
        elif pd.isna(value):
            out[str(key)] = None
        else:
            out[str(key)] = value
    return out


def bars_to_records(df: pd.DataFrame, *, max_rows: int | None = None) -> list[dict[str, Any]]:
    work = df.copy()
    if max_rows is not None and max_rows >= 0:
        work = work.tail(max_rows)
    keep_cols = [
        c for c in [
            "time", "open", "high", "low", "close", "tick_volume", "atr14",
            "ema20", "ema50", "ema200", "macd", "macd_signal", "macd_hist",
            "macd_hist_delta", "body_ratio", "close_pos",
        ] if c in work.columns
    ]
    return [record_to_jsonable(row) for _, row in work[keep_cols].iterrows()]


def trend_direction(values: pd.Series, *, flat_threshold: float = 1e-9) -> str:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if len(clean) < 2:
        return "UNKNOWN"
    diff = float(clean.iloc[-1] - clean.iloc[0])
    if diff > flat_threshold:
        return "UP"
    if diff < -flat_threshold:
        return "DOWN"
    return "FLAT"


def max_losing_streak(outcomes: Iterable[str]) -> int:
    max_streak = 0
    current = 0
    for outcome in outcomes:
        if clean_str(outcome).upper() in {"LOSS", "SMALL_LOSS"}:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def profit_factor_from_r(values: Iterable[Any]) -> float | None:
    pos = 0.0
    neg = 0.0
    for x in values:
        v = clean_float(x)
        if v is None:
            continue
        if v > 0:
            pos += v
        elif v < 0:
            neg += abs(v)
    if neg <= 1e-12:
        return None if pos <= 1e-12 else float("inf")
    return pos / neg
