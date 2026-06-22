#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from gold_v3_289_feature_core import EXTERNAL_FILES,GOLD_FILES,merge_closed,read_candles

def add_external_short_features(ctx: pd.DataFrame, candle_dir: Path) -> pd.DataFrame:
    out = ctx.copy()
    for key, prefix in [("SP_M15", "sp"), ("NQ_M15", "nq")]:
        d = read_candles(candle_dir / EXTERNAL_FILES[key], 6000)
        prev = d.close.shift(1)
        tr = pd.concat([(d.high - d.low).abs(), (d.high - prev).abs(), (d.low - prev).abs()], axis=1).max(axis=1)
        d["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        d["ret4_atr"] = (d.close - d.close.shift(4)) / d.atr14
        out = merge_closed(out, d, f"{prefix}_m15", 15, ["ret4_atr"])
    out["risk_m15_ret4_mean"] = out[["sp_m15_ret4_atr", "nq_m15_ret4_atr"]].mean(axis=1)
    return out

def m5_trigger_frame(candle_dir: Path) -> pd.DataFrame:
    m5 = read_candles(candle_dir / GOLD_FILES["M5"])
    rng = (m5.high - m5.low).replace(0, np.nan)
    m5["body_signed"] = (m5.close - m5.open) / rng
    m5["ema20"] = m5.close.ewm(span=20, adjust=False, min_periods=20).mean()
    return m5

def find_trigger(m5: pd.DataFrame, decision_time: pd.Timestamp, direction: int, kind: str, max_wait_minutes: int = 60):
    times = m5.time.to_numpy("datetime64[ns]")
    start = max(np.searchsorted(times, np.datetime64(decision_time), side="left"), 6)
    end = min(np.searchsorted(times, np.datetime64(decision_time + pd.Timedelta(minutes=max_wait_minutes)), side="left"), len(m5))
    h, l, c = m5.high.to_numpy(float), m5.low.to_numpy(float), m5.close.to_numpy(float)
    body, ema = m5.body_signed.to_numpy(float), m5.ema20.to_numpy(float)
    for k in range(start, end):
        signed = direction * body[k]
        if kind == "BRK6":
            ok = ((c[k] > h[k - 6:k].max()) if direction == 1 else (c[k] < l[k - 6:k].min())) and signed >= 0.20
        elif kind == "EMA20":
            ok = ((c[k] > ema[k] and c[k - 1] <= ema[k - 1] and c[k] > h[k - 1]) if direction == 1 else (c[k] < ema[k] and c[k - 1] >= ema[k - 1] and c[k] < l[k - 1])) and signed >= (0.15 if direction == 1 else 0.12)
        else:
            raise ValueError(kind)
        if ok:
            entry_time = pd.Timestamp(times[k]) + pd.Timedelta(minutes=5)
            next_rows = m5[m5.time.eq(entry_time)]
            entry_price = float(next_rows.iloc[0].open) if len(next_rows) else np.nan
            return pd.Timestamp(times[k]), entry_time, entry_price
    return pd.NaT, pd.NaT, np.nan
