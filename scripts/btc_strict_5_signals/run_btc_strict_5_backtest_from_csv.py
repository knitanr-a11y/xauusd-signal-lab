#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC strict five-candidate no-future backtest from MT5 CSVs.

Research only. No Discord, no MT5 call, no order_send, no OpenAI call, and no
runtime ledger mutation.

Baseline strict-5 rules intentionally do NOT use D1. M15 is the signal
timeframe, M5 is used only after the entry time for spread-aware first-touch
outcome simulation, and H1/H4 context is joined only after each context candle
has closed (context_close_time <= M15 close time).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from btc_strict_5_signal_specs import (  # noqa: E402
    BTC_PIP_SIZE,
    BTC_POINT_SIZE,
    DEFAULT_BROKER_SYMBOL,
    DEFAULT_SYMBOL,
    BtcStrictSignalSpec,
    FROZEN_M15_ATR14_Q30,
    FROZEN_M15_ATR14_Q80,
    FROZEN_M15_BB_WIDTH_Q40,
    get_signal_specs,
    validate_signal_specs,
)

SCHEMA_VERSION = "btc_strict_5_backtest_v1"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/btc_strict_5_signal_candidates")
TF_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}


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


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") > sample.count(",") else ","


def read_ohlc_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    df = pd.read_csv(windows_long_path(p), sep=sniff_sep(p), encoding="utf-8-sig")
    need = ["time", "open", "high", "low", "close"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"{p}: missing columns {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "spread" not in df.columns:
        df["spread"] = 0.0
    df = df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").drop_duplicates("time").reset_index(drop=True)
    df["spread_price"] = df["spread"].fillna(0.0) * BTC_POINT_SIZE
    return df


def ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [(df["high"] - df["low"]).abs(), (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


def macd_hist(s: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(s, 12) - ema(s, 26)
    sig = ema(line, 9)
    hist = line - sig
    return line, sig, hist


def bb_width(df: pd.DataFrame, period: int = 20, mult: float = 2.0) -> pd.Series:
    ma = df["close"].rolling(period).mean()
    sd = df["close"].rolling(period).std(ddof=0)
    return ((ma + mult * sd) - (ma - mult * sd)) / ma.replace(0, np.nan)


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    sma = tp.rolling(period).mean()
    mad = (tp - sma).abs().rolling(period).mean()
    return (tp - sma) / (0.015 * mad.replace(0, np.nan))


def add_indicators(df: pd.DataFrame, *, include_donchian: bool = False) -> pd.DataFrame:
    d = df.copy().sort_values("time").reset_index(drop=True)
    for n in [20, 50, 100, 200]:
        d[f"ema{n}"] = ema(d["close"], n)
        d[f"ema{n}_slope3"] = d[f"ema{n}"].diff(3)
    d["atr14"] = atr(d, 14)
    d["atr50"] = atr(d, 50)
    d["range"] = d["high"] - d["low"]
    d["range_atr14"] = d["range"] / d["atr14"].replace(0, np.nan)
    d["body"] = d["close"] - d["open"]
    d["body_atr14"] = d["body"].abs() / d["atr14"].replace(0, np.nan)
    denom = (d["high"] - d["low"]).replace(0, np.nan)
    d["trigger_close_pos"] = (d["close"] - d["low"]) / denom
    d["rsi14"] = rsi(d["close"], 14)
    d["rsi14_delta"] = d["rsi14"].diff()
    d["macd"], d["macd_signal"], d["macd_hist"] = macd_hist(d["close"])
    d["macd_delta"] = d["macd_hist"].diff()
    d["bb_width"] = bb_width(d)
    d["cci20"] = cci(d)
    d["hour"] = d["time"].dt.hour
    if include_donchian:
        for n in [32, 64, 96]:
            d[f"donch_low{n}"] = d["low"].rolling(n).min().shift(1)
            d[f"donch_high{n}"] = d["high"].rolling(n).max().shift(1)
    return d


def prefix_context(df: pd.DataFrame, *, prefix: str, tf: str) -> pd.DataFrame:
    keep = [
        "time", "open", "high", "low", "close", "ema20", "ema50", "ema100", "ema200",
        "ema20_slope3", "ema50_slope3", "ema200_slope3", "atr14", "atr50", "range_atr14",
        "body_atr14", "rsi14", "rsi14_delta", "macd_hist", "macd_delta", "bb_width", "cci20",
    ]
    cols = [c for c in keep if c in df.columns]
    out = df[cols].copy()
    out[f"{prefix}_time"] = out["time"]
    out[f"{prefix}_close_time"] = out["time"] + pd.to_timedelta(TF_MINUTES[tf], unit="m")
    out = out.drop(columns=["time"])
    out = out.rename(columns={c: f"{prefix}_{c}" for c in out.columns if c not in {f"{prefix}_time", f"{prefix}_close_time"}})
    return out.sort_values(f"{prefix}_close_time").reset_index(drop=True)


def join_confirmed_context(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    out = m15.copy().sort_values("time").reset_index(drop=True)
    out["base_close_time"] = out["time"] + pd.to_timedelta(15, unit="m")
    for ctx, prefix, tf in [(h1, "h1", "H1"), (h4, "h4", "H4")]:
        ctx_pref = prefix_context(ctx, prefix=prefix, tf=tf)
        out = pd.merge_asof(
            out.sort_values("base_close_time"),
            ctx_pref,
            left_on="base_close_time",
            right_on=f"{prefix}_close_time",
            direction="backward",
        ).sort_values("time", kind="mergesort").reset_index(drop=True)
        out[f"{prefix}_confirmed_ok"] = out[f"{prefix}_close_time"] <= out["base_close_time"]
        out[f"{prefix}_close_lag_minutes"] = (out["base_close_time"] - out[f"{prefix}_close_time"]).dt.total_seconds() / 60.0
    out["strict_no_future_ok"] = out[["h1_confirmed_ok", "h4_confirmed_ok"]].all(axis=1)
    return out


def time_text(x: Any) -> str:
    ts = pd.to_datetime(x, errors="coerce")
    if pd.isna(ts):
        return ""
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def id_time_text(x: Any) -> str:
    return pd.Timestamp(x).strftime("%Y%m%d_%H%M")


def detect_signals(ctx: pd.DataFrame, specs: list[BtcStrictSignalSpec]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    prev = ctx.shift(1)
    for spec in specs:
        cb = spec.candidate_base
        if cb == "BTC_SELL_DONCH64_H1MACD_RANGE_M15_00_06":
            cond = ((ctx["close"] < ctx["donch_low64"]) & (ctx["close"] < ctx["open"]) & (ctx["trigger_close_pos"] < 0.35) & (ctx["h1_macd_hist"] < 0.0) & (ctx["range_atr14"].between(0.8, 2.0)) & (ctx["hour"].between(0, 6)))
            reason = "DONCH64_STRONG_LOW_CLOSE_H1_MACD_NEG_RANGE_0P8_2P0_HOUR_00_06"
        elif cb == "BTC_SELL_DONCH96_BBWIDTH_LOW_EMA200":
            cond = ((ctx["close"] < ctx["donch_low96"]) & (ctx["close"] < ctx["ema200"]) & (ctx["bb_width"] <= FROZEN_M15_BB_WIDTH_Q40))
            reason = "DONCH96_BREAK_CLOSE_LT_EMA200_BBWIDTH_Q40"
        elif cb == "BTC_BUY_RSI40_RECLAIM_EMA200_BBLOW_12_23":
            cond = ((prev["rsi14"] < 40.0) & (ctx["rsi14"] >= 40.0) & (ctx["close"] > ctx["open"]) & (ctx["close"] > ctx["ema200"]) & (ctx["bb_width"] <= FROZEN_M15_BB_WIDTH_Q40) & (ctx["hour"].between(12, 23)))
            reason = "RSI40_RECLAIM_BULL_CLOSE_GT_EMA200_BBWIDTH_Q40_HOUR_12_23"
        elif cb == "BTC_BUY_CCI_RECLAIM_H4BULL_BBLOW_19_23":
            cond = ((prev["cci20"] < -100.0) & (ctx["cci20"] >= -100.0) & (ctx["close"] > ctx["open"]) & (ctx["h4_ema20"] > ctx["h4_ema50"]) & (ctx["bb_width"] <= FROZEN_M15_BB_WIDTH_Q40) & (ctx["hour"].between(19, 23)))
            reason = "CCI_NEG100_RECLAIM_H4_EMA20_GT_EMA50_BBWIDTH_Q40_HOUR_19_23"
        elif cb == "BTC_SELL_DONCH32_H1SLOPE_ATR30_80_00_06":
            cond = ((ctx["close"] < ctx["donch_low32"]) & (ctx["h1_ema20_slope3"] < 0.0) & (ctx["atr14"].between(FROZEN_M15_ATR14_Q30, FROZEN_M15_ATR14_Q80)) & (ctx["hour"].between(0, 6)))
            reason = "DONCH32_BREAK_H1_EMA20_SLOPE_DOWN_ATR14_Q30_Q80_HOUR_00_06"
        else:
            raise ValueError(f"unsupported candidate_base: {cb}")
        mask = cond.fillna(False) & ctx["strict_no_future_ok"].fillna(False)
        for idx, r in ctx.loc[mask].iterrows():
            signal_time = pd.Timestamp(r["time"])
            entry_time = signal_time + pd.to_timedelta(15, unit="m")
            rows.append({
                "spec": spec, "source_index": int(idx), "signal_id": f"{cb}_{id_time_text(signal_time)}",
                "trade_id": f"{spec.strategy_id}_{id_time_text(signal_time)}", "strategy_id": spec.strategy_id,
                "candidate_base": cb, "candidate_family": spec.family, "direction": spec.direction,
                "signal_time": signal_time, "base_close_time": r["base_close_time"], "entry_time": entry_time,
                "h1_time": r.get("h1_time"), "h1_close_time": r.get("h1_close_time"), "h1_confirmed_ok": bool(r.get("h1_confirmed_ok", False)), "h1_close_lag_minutes": r.get("h1_close_lag_minutes"),
                "h4_time": r.get("h4_time"), "h4_close_time": r.get("h4_close_time"), "h4_confirmed_ok": bool(r.get("h4_confirmed_ok", False)), "h4_close_lag_minutes": r.get("h4_close_lag_minutes"),
                "strict_no_future_ok": bool(r.get("strict_no_future_ok", False)), "trigger_hour": int(r.get("hour", -1)),
                "trigger_close_pos": r.get("trigger_close_pos"), "trigger_range_atr14": r.get("range_atr14"), "trigger_body_atr14": r.get("body_atr14"), "trigger_atr14": r.get("atr14"),
                "trigger_bb_width": r.get("bb_width"), "trigger_rsi14": r.get("rsi14"), "trigger_cci20": r.get("cci20"), "trigger_macd_hist": r.get("macd_hist"), "trigger_macd_delta": r.get("macd_delta"),
                "trigger_ema200_slope3": r.get("ema200_slope3"), "h1_macd_hist": r.get("h1_macd_hist"), "h1_ema20_slope3": r.get("h1_ema20_slope3"), "h4_ema20": r.get("h4_ema20"), "h4_ema50": r.get("h4_ema50"), "reason": reason,
            })
    return pd.DataFrame(rows).sort_values(["entry_time", "strategy_id"]).reset_index(drop=True) if rows else pd.DataFrame()


def evaluate_one(sig: pd.Series, m5: pd.DataFrame, entry_lookup: dict[pd.Timestamp, pd.Series]) -> dict[str, Any]:
    spec: BtcStrictSignalSpec = sig["spec"]
    entry_time = pd.Timestamp(sig["entry_time"])
    horizon_end = entry_time + pd.to_timedelta(spec.horizon_minutes, unit="m")
    base = {k: sig.get(k, "") for k in ["signal_id", "trade_id", "strategy_id", "candidate_base", "candidate_family", "direction", "reason"]}
    base.update({
        "created_at_utc": utc_now_text(), "schema_version": SCHEMA_VERSION, "broker_symbol": DEFAULT_BROKER_SYMBOL, "symbol": DEFAULT_SYMBOL,
        "trigger_timeframe": "M15", "outcome_timeframe": "M5", "signal_time": time_text(sig["signal_time"]), "base_close_time": time_text(sig["base_close_time"]), "entry_time": time_text(entry_time),
        "tp_price_distance": spec.tp_price_distance, "sl_price_distance": spec.sl_price_distance, "tp_pips": spec.tp_pips, "sl_pips": spec.sl_pips, "rr": spec.rr,
        "horizon_m15": spec.horizon_m15, "horizon_minutes": spec.horizon_minutes, "horizon_end_time_exclusive": time_text(horizon_end),
        "strict_no_future_ok": bool(sig["strict_no_future_ok"]), "h1_time": time_text(sig["h1_time"]), "h1_close_time": time_text(sig["h1_close_time"]), "h1_confirmed_ok": bool(sig["h1_confirmed_ok"]), "h1_close_lag_minutes": sig.get("h1_close_lag_minutes"),
        "h4_time": time_text(sig["h4_time"]), "h4_close_time": time_text(sig["h4_close_time"]), "h4_confirmed_ok": bool(sig["h4_confirmed_ok"]), "h4_close_lag_minutes": sig.get("h4_close_lag_minutes"), "d1_used": False,
        "trigger_hour": sig.get("trigger_hour"), "trigger_close_pos": sig.get("trigger_close_pos"), "trigger_range_atr14": sig.get("trigger_range_atr14"), "trigger_body_atr14": sig.get("trigger_body_atr14"), "trigger_atr14": sig.get("trigger_atr14"),
        "trigger_bb_width": sig.get("trigger_bb_width"), "trigger_rsi14": sig.get("trigger_rsi14"), "trigger_cci20": sig.get("trigger_cci20"), "trigger_macd_hist": sig.get("trigger_macd_hist"), "trigger_macd_delta": sig.get("trigger_macd_delta"), "trigger_ema200_slope3": sig.get("trigger_ema200_slope3"),
        "h1_macd_hist": sig.get("h1_macd_hist"), "h1_ema20_slope3": sig.get("h1_ema20_slope3"), "h4_ema20": sig.get("h4_ema20"), "h4_ema50": sig.get("h4_ema50"),
    })
    er = entry_lookup.get(entry_time)
    if er is None:
        return {**base, "outcome": "NO_M5_PATH", "close_reason": "NO_M5_ENTRY_ROW", "net_profit_r": np.nan, "profit_r": np.nan, "bars_checked_m5": 0, "same_bar_conflict": False}
    entry_bid = float(er["open"])
    entry_spread = float(er.get("spread_price", 0.0) or 0.0)
    entry_ask = entry_bid + entry_spread
    if spec.direction == "BUY":
        entry_exec = entry_ask; tp = entry_exec + spec.tp_price_distance; sl = entry_exec - spec.sl_price_distance
    else:
        entry_exec = entry_bid; tp = entry_exec - spec.tp_price_distance; sl = entry_exec + spec.sl_price_distance
    path = m5[(m5["time"] >= entry_time) & (m5["time"] < horizon_end)].copy()
    if path.empty:
        return {**base, "entry_bid": entry_bid, "entry_ask": entry_ask, "entry_spread_price": entry_spread, "entry_spread_pips": entry_spread / BTC_PIP_SIZE, "tp_price": tp, "sl_price": sl, "outcome": "NO_M5_PATH", "close_reason": "NO_M5_PATH_AFTER_ENTRY", "net_profit_r": np.nan, "profit_r": np.nan, "bars_checked_m5": 0, "same_bar_conflict": False}
    outcome = "HORIZON_EXIT"; close_reason = "HORIZON_EXIT"; close_time = pd.Timestamp(path.iloc[-1]["time"]); close_bid = float(path.iloc[-1]["close"]); close_ask = close_bid + float(path.iloc[-1].get("spread_price", 0.0) or 0.0); conflict = False
    for _, b in path.iterrows():
        hi, lo, bt = float(b["high"]), float(b["low"]), pd.Timestamp(b["time"])
        sp = float(b.get("spread_price", 0.0) or 0.0)
        if spec.direction == "BUY":
            hit_sl, hit_tp = lo <= sl, hi >= tp
            if hit_sl and hit_tp:
                outcome="LOSS"; close_reason="SL_FIRST_SAME_M5_BAR"; close_time=bt; close_bid=sl; close_ask=sl+sp; conflict=True; break
            if hit_sl:
                outcome="LOSS"; close_reason="SL_FIRST"; close_time=bt; close_bid=sl; close_ask=sl+sp; break
            if hit_tp:
                outcome="WIN"; close_reason="TP_FIRST"; close_time=bt; close_bid=tp; close_ask=tp+sp; break
        else:
            hit_sl, hit_tp = (hi + sp) >= sl, (lo + sp) <= tp
            if hit_sl and hit_tp:
                outcome="LOSS"; close_reason="SL_FIRST_SAME_M5_BAR"; close_time=bt; close_bid=sl-sp; close_ask=sl; conflict=True; break
            if hit_sl:
                outcome="LOSS"; close_reason="SL_FIRST"; close_time=bt; close_bid=sl-sp; close_ask=sl; break
            if hit_tp:
                outcome="WIN"; close_reason="TP_FIRST"; close_time=bt; close_bid=tp-sp; close_ask=tp; break
    if spec.direction == "BUY":
        profit_price = spec.tp_price_distance if outcome == "WIN" else -spec.sl_price_distance if outcome == "LOSS" else close_bid - entry_ask
        mfe_price = float(path["high"].max()) - entry_ask; mae_price = float(path["low"].min()) - entry_ask
    else:
        profit_price = spec.tp_price_distance if outcome == "WIN" else -spec.sl_price_distance if outcome == "LOSS" else entry_bid - close_ask
        mfe_price = entry_bid - float(path["low"].min()); mae_price = entry_bid - float(path["high"].max())
    r = profit_price / spec.sl_price_distance
    return {**base, "entry_bid": entry_bid, "entry_ask": entry_ask, "entry_spread_points_raw": float(er.get("spread", 0.0) or 0.0), "entry_spread_price": entry_spread, "entry_spread_pips": entry_spread / BTC_PIP_SIZE, "tp_price": tp, "sl_price": sl, "outcome": outcome, "close_reason": close_reason, "close_time": time_text(close_time), "close_bid": close_bid, "close_ask": close_ask, "profit_price_net": profit_price, "profit_pips_net": profit_price / BTC_PIP_SIZE, "net_profit_r": r, "profit_r": r, "mfe_price": mfe_price, "mae_price": mae_price, "mfe_r": mfe_price / spec.sl_price_distance, "mae_r": mae_price / spec.sl_price_distance, "holding_minutes": (pd.Timestamp(close_time) - entry_time).total_seconds() / 60.0, "bars_checked_m5": int(len(path)), "same_bar_conflict": conflict}


def evaluate_signals(signals: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    lookup = {pd.Timestamp(r["time"]): r for _, r in m5.iterrows()}
    return pd.DataFrame([evaluate_one(row, m5, lookup) for _, row in signals.iterrows()]) if not signals.empty else pd.DataFrame()


def perf(g: pd.DataFrame) -> dict[str, Any]:
    ev = g[g["outcome"].isin(["WIN", "LOSS", "HORIZON_EXIT"])].copy()
    r = pd.to_numeric(ev["net_profit_r"], errors="coerce").dropna().to_numpy(dtype=float)
    pos = float(r[r > 0].sum()) if len(r) else 0.0; neg_abs = float(-r[r < 0].sum()) if len(r) else 0.0
    pf = math.inf if neg_abs == 0 and pos > 0 else (pos / neg_abs if neg_abs > 0 else 0.0)
    eq = np.r_[0.0, np.cumsum(r)] if len(r) else np.array([0.0]); dd = np.maximum.accumulate(eq) - eq
    max_ls = cur = 0
    for x in r:
        if x < 0: cur += 1; max_ls = max(max_ls, cur)
        else: cur = 0
    return {"signal_count": int(len(g)), "evaluated_trade_count": int(len(ev)), "trade_count": int(len(ev)), "win_count": int((r > 0).sum()), "loss_count": int((r < 0).sum()), "win_rate": float((r > 0).mean()) if len(r) else 0.0, "total_r": float(r.sum()) if len(r) else 0.0, "avg_r": float(r.mean()) if len(r) else 0.0, "profit_factor": pf, "max_drawdown_r": float(dd.max()) if len(dd) else 0.0, "max_losing_streak": int(max_ls)}


def build_summary(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, g in trades.groupby(["strategy_id", "candidate_base", "candidate_family", "direction"], dropna=False):
        d = dict(zip(["strategy_id", "candidate_base", "candidate_family", "direction"], keys)); d.update(perf(g)); d["first_entry_time"] = g["entry_time"].min(); d["last_entry_time"] = g["entry_time"].max(); d["strict_no_future_all_ok"] = bool(g["strict_no_future_ok"].all()); rows.append(d)
    return pd.DataFrame(rows).sort_values("strategy_id") if rows else pd.DataFrame()


def build_monthly(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty: return pd.DataFrame()
    d = trades.copy(); d["entry_month"] = pd.to_datetime(d["entry_time"]).dt.strftime("%Y-%m")
    rows = []
    for keys, g in d.groupby(["strategy_id", "candidate_base", "candidate_family", "direction", "entry_month"], dropna=False):
        row = dict(zip(["strategy_id", "candidate_base", "candidate_family", "direction", "entry_month"], keys)); row.update(perf(g)); rows.append(row)
    return pd.DataFrame(rows).sort_values(["strategy_id", "entry_month"]) if rows else pd.DataFrame()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest BTC strict 5 from CSV. Research only; no MT5/order/Discord/API calls.")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--m5-file", default="btcusdsharp_m5.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default=DEFAULT_BROKER_SYMBOL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    return p.parse_args()


def choose_path(root: Path, explicit: str, filename: str) -> Path:
    return Path(explicit) if explicit else root / filename


def main() -> int:
    args = parse_args(); validate_signal_specs(); args.out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"m15": choose_path(args.mql5_files_dir, args.m15_csv, args.m15_file), "m5": choose_path(args.mql5_files_dir, args.m5_csv, args.m5_file), "h1": choose_path(args.mql5_files_dir, args.h1_csv, args.h1_file), "h4": choose_path(args.mql5_files_dir, args.h4_csv, args.h4_file)}
    print("BTC strict 5 backtest from CSV")
    print("d1_csv=NOT_USED d1_used=false")
    for k, v in paths.items(): print(f"{k}_csv={v}")
    m15 = add_indicators(read_ohlc_csv(paths["m15"]), include_donchian=True); m5 = read_ohlc_csv(paths["m5"]); h1 = add_indicators(read_ohlc_csv(paths["h1"])); h4 = add_indicators(read_ohlc_csv(paths["h4"]))
    ctx = join_confirmed_context(m15, h1, h4); specs = get_signal_specs(); signals = detect_signals(ctx, specs); trades = evaluate_signals(signals, m5)
    summary = build_summary(trades); monthly = build_monthly(trades)
    trade_csv = args.out_dir / "btc_strict_5_backtest_trades.csv"; summary_csv = args.out_dir / "btc_strict_5_backtest_summary.csv"; monthly_csv = args.out_dir / "btc_strict_5_backtest_monthly.csv"; run_json = args.out_dir / "btc_strict_5_backtest_run_summary.json"
    write_csv(trades.drop(columns=["spec"], errors="ignore"), trade_csv); write_csv(summary, summary_csv); write_csv(monthly, monthly_csv)
    run = {"schema_version": SCHEMA_VERSION, "created_at_utc": utc_now_text(), "cycle_ok": True, "research_only": True, "orders_sent": False, "discord_sent": False, "openai_called": False, "d1_used": False, "d1_csv": "NOT_USED", "input_paths": {k: str(v) for k, v in paths.items()}, "outputs": {"trades_csv": str(trade_csv), "summary_csv": str(summary_csv), "monthly_csv": str(monthly_csv)}, "rows": {"m15": len(m15), "m5": len(m5), "h1": len(h1), "h4": len(h4), "signals": len(signals), "trades": len(trades)}, "strict_no_future_ng_rows": int((~trades["strict_no_future_ok"].fillna(False)).sum()) if not trades.empty else 0}
    write_json(run_json, run)
    print(summary[["strategy_id", "trade_count", "win_rate", "total_r", "profit_factor", "max_drawdown_r", "max_losing_streak"]].to_string(index=False) if not summary.empty else "NO TRADES")
    print(f"trades_csv={trade_csv}")
    print(f"summary_csv={summary_csv}")
    print(f"monthly_csv={monthly_csv}")
    print(f"run_summary_json={run_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
