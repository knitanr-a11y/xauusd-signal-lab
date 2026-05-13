#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC multi-strategy signal detection helpers.

This module is intentionally pure-Python/pandas and does not call MT5.  It is
used by scripts/run_btc_multi_strategy_dry_run_cycle.py to keep BTC strategy
scanning fast: CSV files are read once, indicators are calculated once, and all
strategy detectors run on the same joined M15/H1/H4/D1 frame.

Design rules:
- confirmed-time join only: higher timeframe rows are joined with
  context_time <= M15 signal time.
- default live payload should use latest confirmed M15 only; historical rows are
  exported for audit but not sent unless explicitly requested by the caller.
- SELL_EARLY_LOW_BREAK is observe-only by default.
- no MT5 order_send, no Discord, no state mutation here.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

BTC_MULTI_STRATEGY_VERSION = "btc_multi_strategy_signals_v1"

STRATEGY_PULLBACK_SELL = "BTC_H1_PULLBACK_REJECT_M15_LOW_BREAK_RR2_72H"
STRATEGY_D1_LOW_BREAK_SELL = "BTC_D1_4D_LOW_BREAK_M15_CONTINUATION_RR2_72H"
STRATEGY_BULL_STACK_BUY = "BTC_BULL_STACK_M15_HIGH_BREAK_RR2_72H"
STRATEGY_EARLY_SELL_OBSERVE = "BTC_H4H1_BEAR_M15_EARLY_LOW_BREAK_OBSERVE_RR2_72H"

DEFAULT_STRATEGY_TRADE_ENABLED: dict[str, bool] = {
    STRATEGY_PULLBACK_SELL: True,
    STRATEGY_D1_LOW_BREAK_SELL: True,
    STRATEGY_BULL_STACK_BUY: True,
    STRATEGY_EARLY_SELL_OBSERVE: False,
}

STRATEGY_SLOT_BY_ID: dict[str, str] = {
    STRATEGY_PULLBACK_SELL: "SELL_PULLBACK_REJECT",
    STRATEGY_D1_LOW_BREAK_SELL: "SELL_D1_LOW_BREAK",
    STRATEGY_BULL_STACK_BUY: "BUY_BULL_STACK_BREAK",
    STRATEGY_EARLY_SELL_OBSERVE: "SELL_EARLY_LOW_BREAK",
}

OUTPUT_COLUMNS = [
    "schema_version",
    "strategy_id",
    "strategy_slot",
    "strategy_alias",
    "condition_id",
    "direction",
    "candidate_rank",
    "trade_enabled",
    "observe_only",
    "signal_time",
    "entry_time",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "rr",
    "horizon_hours",
    "sl_distance_usd",
    "tp_distance_usd",
    "spread_cost_usd",
    "base_lot",
    "lot_multiplier",
    "lot",
    "lot_status",
    "broker_symbol",
    "symbol",
    "signal_key",
    "order_key",
    "payload_key",
    "reason",
]


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


def clean_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return float(default)


def read_ohlc_csv(path: str | Path, *, sep: str = "auto", tail_bars: int | None = None) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    read_kwargs: dict[str, Any] = {"encoding": "utf-8-sig"}
    if sep and sep != "auto":
        read_kwargs["sep"] = sep
    else:
        read_kwargs["sep"] = None
        read_kwargs["engine"] = "python"
    df = pd.read_csv(windows_long_path(p), **read_kwargs)
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "time" not in df.columns:
        raise ValueError(f"CSV requires time column: {p}; columns={list(df.columns)}")
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise ValueError(f"CSV requires {col} column: {p}; columns={list(df.columns)}")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time", "open", "high", "low", "close"]).copy()
    df = df.sort_values("time").drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
    if tail_bars and int(tail_bars) > 0 and len(df) > int(tail_bars):
        df = df.tail(int(tail_bars)).reset_index(drop=True)
    return df


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.astype(float).ewm(span=int(span), adjust=False, min_periods=max(2, int(span) // 2)).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(int(period), min_periods=max(2, int(period) // 2)).mean()


def add_indicators(df: pd.DataFrame, *, prefix: str = "") -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = ema(out["close"], 20)
    out["ema50"] = ema(out["close"], 50)
    out["atr14"] = atr(out, 14)
    macd_fast = ema(out["close"], 12)
    macd_slow = ema(out["close"], 26)
    out["macd"] = macd_fast - macd_slow
    out["macd_signal"] = ema(out["macd"], 9)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["macd_hist_delta"] = out["macd_hist"] - out["macd_hist"].shift(1)
    rng = (out["high"] - out["low"]).replace(0, pd.NA)
    out["range"] = out["high"] - out["low"]
    out["close_pos"] = ((out["close"] - out["low"]) / rng).astype(float)
    out["ema20_slope3"] = out["ema20"] - out["ema20"].shift(3)
    out["prev_high_12"] = out["high"].shift(1).rolling(12, min_periods=12).max()
    out["prev_low_6"] = out["low"].shift(1).rolling(6, min_periods=6).min()
    out["prev_low_24"] = out["low"].shift(1).rolling(24, min_periods=24).min()
    out["prev_low_48"] = out["low"].shift(1).rolling(48, min_periods=48).min()
    out["prev_d1_low_4"] = out["low"].shift(1).rolling(4, min_periods=4).min()
    if prefix:
        rename = {c: f"{prefix}_{c}" for c in out.columns if c != "time"}
        out = out.rename(columns=rename)
    return out


def asof_join(base: pd.DataFrame, context: pd.DataFrame, *, prefix: str) -> pd.DataFrame:
    ctx = context.copy().sort_values("time")
    ctx = ctx.rename(columns={"time": f"{prefix}_time"})
    return pd.merge_asof(
        base.sort_values("time"),
        ctx.sort_values(f"{prefix}_time"),
        left_on="time",
        right_on=f"{prefix}_time",
        direction="backward",
        allow_exact_matches=True,
    )


@dataclass(frozen=True)
class StrategyParams:
    base_lot: float = 0.01
    spread_cost_usd: float = 22.5
    rr: float = 2.0
    horizon_hours: int = 72
    broker_symbol: str = "BTCUSD#"
    symbol: str = "BTC"


def safe_price(direction: str, entry: float, sl_distance: float, tp_distance: float) -> tuple[float, float]:
    d = direction.upper()
    if d == "BUY":
        return round(entry - sl_distance, 2), round(entry + tp_distance, 2)
    if d == "SELL":
        return round(entry + sl_distance, 2), round(entry - tp_distance, 2)
    raise ValueError(f"invalid direction: {direction}")


def key_time_text(value: Any) -> str:
    ts = pd.Timestamp(value)
    return ts.strftime("%Y%m%d_%H%M")


def build_candidate_row(
    row: pd.Series,
    *,
    strategy_id: str,
    direction: str,
    candidate_rank: str,
    trade_enabled: bool,
    reason: str,
    sl_distance: float,
    params: StrategyParams,
    lot_multiplier: float = 1.0,
) -> dict[str, Any]:
    entry_time = pd.Timestamp(row["time"])
    entry = clean_float(row["close"], 0.0)
    tp_distance = sl_distance * float(params.rr)
    sl, tp = safe_price(direction, entry, sl_distance, tp_distance)
    strategy_slot = STRATEGY_SLOT_BY_ID[strategy_id]
    lot = round(float(params.base_lot) * float(lot_multiplier), 8) if trade_enabled else 0.0
    key_base = f"BTC_MULTI_{params.broker_symbol}_{strategy_slot}_{direction.upper()}_{key_time_text(entry_time)}"
    return {
        "schema_version": BTC_MULTI_STRATEGY_VERSION,
        "strategy_id": strategy_id,
        "strategy_slot": strategy_slot,
        "strategy_alias": strategy_slot,
        "condition_id": strategy_id,
        "direction": direction.upper(),
        "candidate_rank": candidate_rank,
        "trade_enabled": bool(trade_enabled),
        "observe_only": not bool(trade_enabled),
        "signal_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_time": entry_time.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_price_reference": round(entry, 2),
        "sl_price": sl,
        "tp_price": tp,
        "rr": float(params.rr),
        "horizon_hours": int(params.horizon_hours),
        "sl_distance_usd": float(sl_distance),
        "tp_distance_usd": float(tp_distance),
        "spread_cost_usd": float(params.spread_cost_usd),
        "base_lot": float(params.base_lot),
        "lot_multiplier": float(lot_multiplier),
        "lot": lot,
        "lot_status": "CALCULATED_BASE_LOT" if trade_enabled else "OBSERVE_ONLY_NO_LOT",
        "broker_symbol": params.broker_symbol,
        "symbol": params.symbol,
        "signal_key": f"{key_base}_SIGNAL",
        "order_key": f"{key_base}_ORDER",
        "payload_key": f"{key_base}_PAYLOAD",
        "reason": reason,
    }


def mask_pullback_sell(df: pd.DataFrame) -> pd.Series:
    h1_extension = (df["h1_ema20"] - df["h1_close"]) / df["h1_atr14"].replace(0, pd.NA)
    return (
        (df["d1_close"] < df["d1_ema20"])
        & (df["h4_close"] < df["h4_ema50"])
        & (df["h4_macd_hist"] < 0)
        & (df["h1_close"] < df["h1_ema20"])
        & (df["h1_ema20"] < df["h1_ema50"])
        & (h1_extension <= 1.60)
        & (df["close"] < df["prev_low_6"])
        & (df["close_pos"] <= 0.40)
        & (df["macd_hist"] < 0)
    ).fillna(False)


def mask_d1_low_break_sell(df: pd.DataFrame) -> pd.Series:
    return (
        (df["d1_close"] < df["d1_prev_d1_low_4"])
        & (df["h4_macd_hist"] < 0)
        & (df["h4_close"] < df["h4_ema20"])
        & (df["low"] < df["prev_low_24"])
        & (df["close_pos"] <= 0.50)
        & (df["macd_hist"] < 0)
    ).fillna(False)


def mask_bull_stack_buy(df: pd.DataFrame) -> pd.Series:
    range_atr = df["range"] / df["atr14"].replace(0, pd.NA)
    return (
        (df["d1_close"] > df["d1_ema20"])
        & (df["h4_close"] > df["h4_ema20"])
        & (df["h4_ema20"] > df["h4_ema50"])
        & (df["h1_close"] > df["h1_ema20"])
        & (df["h1_ema20"] > df["h1_ema50"])
        & (df["high"] > df["prev_high_12"])
        & (df["close_pos"] >= 0.50)
        & (df["macd_hist"] > 0)
        & (range_atr >= 0.70)
    ).fillna(False)


def mask_early_sell(df: pd.DataFrame) -> pd.Series:
    return (
        (df["d1_close"] < df["d1_ema20"])
        & (df["h4_close"] < df["h4_ema50"])
        & (df["h4_macd_hist"] < 0)
        & (df["h1_close"] < df["h1_ema50"])
        & (df["h1_macd_hist"] < 0)
        & (df["low"] < df["prev_low_48"])
        & (df["close_pos"] <= 0.45)
        & (df["macd_hist"] < 0)
        & (df["macd_hist_delta"] < 0)
    ).fillna(False)


def detect_candidates(joined: pd.DataFrame, *, params: StrategyParams, trade_enabled: dict[str, bool] | None = None) -> pd.DataFrame:
    enabled = dict(DEFAULT_STRATEGY_TRADE_ENABLED)
    if trade_enabled:
        enabled.update(trade_enabled)
    rows: list[dict[str, Any]] = []

    strategy_specs = [
        (STRATEGY_PULLBACK_SELL, "SELL", "CORE", 1000.0, mask_pullback_sell, "H1/H4/D1 bearish pullback rejection + M15 low break"),
        (STRATEGY_D1_LOW_BREAK_SELL, "SELL", "CORE", 1500.0, mask_d1_low_break_sell, "D1 4-day low break continuation + H4/M15 bearish confirmation"),
        (STRATEGY_BULL_STACK_BUY, "BUY", "CORE", 1500.0, mask_bull_stack_buy, "D1/H4/H1 bullish stack + M15 high break"),
        (STRATEGY_EARLY_SELL_OBSERVE, "SELL", "OBSERVE", 500.0, mask_early_sell, "H4/H1 bearish early M15 low break observe-only"),
    ]
    for strategy_id, direction, rank, sl_distance, mask_func, reason in strategy_specs:
        mask = mask_func(joined)
        if not mask.any():
            continue
        for _, row in joined.loc[mask].iterrows():
            rows.append(
                build_candidate_row(
                    row,
                    strategy_id=strategy_id,
                    direction=direction,
                    candidate_rank=rank,
                    trade_enabled=bool(enabled.get(strategy_id, False)),
                    reason=reason,
                    sl_distance=float(sl_distance),
                    params=params,
                    lot_multiplier=1.0,
                )
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    out = out.sort_values(["entry_time", "strategy_slot"]).reset_index(drop=True)
    return out.reindex(columns=OUTPUT_COLUMNS)


def latest_m15_time(m15: pd.DataFrame, *, latest_confirmed_policy: str = "last") -> pd.Timestamp | None:
    if m15.empty:
        return None
    policy = str(latest_confirmed_policy or "last").strip().lower()
    if policy in {"second_last", "previous"}:
        if len(m15) < 2:
            return None
        return pd.Timestamp(m15.iloc[-2]["time"])
    if policy != "last":
        raise ValueError(f"unknown latest_confirmed_policy: {latest_confirmed_policy}")
    return pd.Timestamp(m15.iloc[-1]["time"])


def filter_live_candidates(candidates: pd.DataFrame, *, latest_time: pd.Timestamp | None, live_lookback_bars: int = 1, m15: pd.DataFrame | None = None) -> pd.DataFrame:
    if candidates.empty or latest_time is None:
        return candidates.iloc[0:0].copy()
    times: set[pd.Timestamp] = {pd.Timestamp(latest_time)}
    if m15 is not None and live_lookback_bars > 1:
        eligible_times = list(pd.to_datetime(m15["time"], errors="coerce").dropna())
        if eligible_times:
            tail = eligible_times[-int(live_lookback_bars):]
            times = {pd.Timestamp(t) for t in tail}
    work = candidates.copy()
    work["_entry_time_dt"] = pd.to_datetime(work["entry_time"], errors="coerce")
    out = work[work["_entry_time_dt"].isin(times)].drop(columns=["_entry_time_dt"], errors="ignore")
    return out.reset_index(drop=True)


def build_joined_frame(
    *,
    m15_csv: str | Path,
    h1_csv: str | Path,
    h4_csv: str | Path,
    d1_csv: str | Path,
    csv_sep: str = "auto",
    tail_m15: int | None = 20000,
    tail_h1: int | None = 5000,
    tail_h4: int | None = 3000,
    tail_d1: int | None = 1000,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    m15_raw = read_ohlc_csv(m15_csv, sep=csv_sep, tail_bars=tail_m15)
    h1_raw = read_ohlc_csv(h1_csv, sep=csv_sep, tail_bars=tail_h1)
    h4_raw = read_ohlc_csv(h4_csv, sep=csv_sep, tail_bars=tail_h4)
    d1_raw = read_ohlc_csv(d1_csv, sep=csv_sep, tail_bars=tail_d1)

    m15 = add_indicators(m15_raw)
    h1 = add_indicators(h1_raw, prefix="h1")
    h4 = add_indicators(h4_raw, prefix="h4")
    d1 = add_indicators(d1_raw, prefix="d1")

    joined = asof_join(m15, h1, prefix="h1")
    joined = asof_join(joined, h4, prefix="h4")
    joined = asof_join(joined, d1, prefix="d1")
    return joined, {"m15": m15, "h1": h1, "h4": h4, "d1": d1}


def candidate_count_by_strategy(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    if candidates.empty:
        return []
    g = candidates.groupby(["strategy_slot", "strategy_id", "direction", "trade_enabled"], dropna=False).size().reset_index(name="count")
    return g.to_dict(orient="records")


def ensure_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.reindex(columns=OUTPUT_COLUMNS)
