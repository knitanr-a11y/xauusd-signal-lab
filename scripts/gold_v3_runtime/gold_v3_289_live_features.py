#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared causal feature builders for GOLD V3 Stage289.

All CSV rows are treated as contractually closed. Bar timestamps remain the source
CSV timestamps. Higher-timeframe features become available only after their
nominal close via merge_closed(). No open/in-progress row trimming is performed.
"""
from __future__ import annotations

import base64
import gzip
import math
from collections import deque
from io import StringIO
from pathlib import Path
from typing import Iterable

import lightgbm as lgb
import numpy as np
import pandas as pd

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}

GOLD_FILES = {
    "M1": "goldsharp_m1.csv",
    "M5": "goldsharp_m5.csv",
    "M15": "goldsharp_m15.csv",
    "H1": "goldsharp_h1.csv",
    "H4": "goldsharp_h4.csv",
    "D1": "goldsharp_d1.csv",
}
EXTERNAL_FILES = {
    "SP_M15": "us500cashsharp_m15.csv",
    "NQ_M15": "us100cashsharp_m15.csv",
}


def read_candles(path: Path, tail_rows: int | None = None) -> pd.DataFrame:
    if tail_rows is not None and tail_rows > 0:
        # Parse only the required closed-bar tail. Reading the file stream does not
        # mutate it and avoids materialising multi-year M1 data every live cycle.
        with path.open("r", encoding="utf-8-sig", errors="replace") as fh:
            header = fh.readline()
            lines = deque(fh, maxlen=int(tail_rows))
        df = pd.read_csv(StringIO(header + "".join(lines)))
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"datetime": "time", "date": "time", "timestamp": "time", "volume": "tick_volume", "tickvolume": "tick_volume"})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 0.0
    if "spread" not in df.columns:
        df["spread"] = 0.0
    return df.dropna(subset=required).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)


def add_indicators(df: pd.DataFrame, wins: Iterable[int]) -> pd.DataFrame:
    x = df.copy()
    prev = x.close.shift(1)
    tr = pd.concat([(x.high - x.low).abs(), (x.high - prev).abs(), (x.low - prev).abs()], axis=1).max(axis=1)
    x["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    x["atr50"] = tr.ewm(alpha=1 / 50, adjust=False, min_periods=50).mean()
    x["atr_ratio"] = x.atr14 / x.atr50
    for n in [8, 20, 50, 200]:
        x[f"ema{n}"] = x.close.ewm(span=n, adjust=False, min_periods=n).mean()
        x[f"dist_ema{n}_atr"] = (x.close - x[f"ema{n}"]) / x.atr14
    x["ema20_slope6_atr"] = (x.ema20 - x.ema20.shift(6)) / x.atr14
    x["ema50_slope12_atr"] = (x.ema50 - x.ema50.shift(12)) / x.atr14
    rng = (x.high - x.low).replace(0, np.nan)
    x["body_signed"] = (x.close - x.open) / rng
    x["body_ratio"] = (x.close - x.open).abs() / rng
    x["upper_wick_ratio"] = (x.high - x[["open", "close"]].max(axis=1)) / rng
    x["lower_wick_ratio"] = (x[["open", "close"]].min(axis=1) - x.low) / rng
    x["range_atr"] = rng / x.atr14
    x["vol_ratio20"] = x.tick_volume / x.tick_volume.rolling(20).mean()
    x["spread_usd"] = x.spread * 0.01
    x["spread_ratio20"] = x.spread / x.spread.rolling(20).median().replace(0, np.nan)
    delta = x.close.diff().abs()
    for n in wins:
        hi = x.high.rolling(n).max()
        lo = x.low.rolling(n).min()
        x[f"ret{n}_atr"] = (x.close - x.close.shift(n)) / x.atr14
        x[f"range{n}_atr"] = (hi - lo) / x.atr14
        x[f"pos{n}"] = (x.close - lo) / (hi - lo).replace(0, np.nan)
        x[f"eff{n}"] = (x.close - x.close.shift(n)).abs() / delta.rolling(n).sum().replace(0, np.nan)
        x[f"volratio{n}"] = x.tick_volume.rolling(n).mean() / x.tick_volume.rolling(n).mean().shift(n)
        x[f"spreadmax{n}_usd"] = x.spread.rolling(n).max() * 0.01
    return x


def merge_closed(base: pd.DataFrame, src: pd.DataFrame, prefix: str, minutes: int, cols: list[str]) -> pd.DataFrame:
    s = src[["time"] + cols].copy()
    s["available_time"] = s.time + pd.Timedelta(minutes=minutes)
    s = s.drop(columns="time").rename(columns={c: f"{prefix}_{c}" for c in cols})
    return pd.merge_asof(base.sort_values("time"), s.sort_values("available_time"), left_on="time", right_on="available_time", direction="backward").drop(columns="available_time")


def _decision_times(raw: pd.DataFrame, minutes: int, include_next: bool) -> pd.DataFrame:
    times = raw[["time"]].copy()
    if include_next and len(raw):
        next_time = pd.Timestamp(raw.time.max()) + pd.Timedelta(minutes=minutes)
        if next_time not in set(times.time):
            times = pd.concat([times, pd.DataFrame({"time": [next_time]})], ignore_index=True)
    return times.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def _m1_arrays(m1: pd.DataFrame):
    return (
        m1.time.to_numpy("datetime64[ns]"), m1.open.to_numpy(float), m1.high.to_numpy(float),
        m1.low.to_numpy(float), m1.close.to_numpy(float), m1.tick_volume.to_numpy(float),
        m1.spread.to_numpy(float) * 0.01,
    )


LIVE_TAIL_ROWS = {
    "M1": 30000,
    "M5": 12000,
    "M15": 6000,
    "H1": 3000,
    "H4": 1500,
    "D1": 600,
}


def load_gold(candle_dir: Path, tail_only: bool = True) -> dict[str, pd.DataFrame]:
    return {
        tf: read_candles(candle_dir / name, LIVE_TAIL_ROWS[tf] if tail_only else None)
        for tf, name in GOLD_FILES.items()
    }


def build_stage280_context(candle_dir: Path, include_next: bool = True) -> pd.DataFrame:
    raw = load_gold(candle_dir, tail_only=True)
    m1 = raw["M1"]
    m5 = add_indicators(raw["M5"], [1, 3, 6, 12, 24, 48])
    m15 = add_indicators(raw["M15"], [1, 2, 4, 8, 16])
    h1 = add_indicators(raw["H1"], [1, 2, 4, 8, 16])
    h4 = add_indicators(raw["H4"], [1, 2, 3, 6, 12])
    d1 = add_indicators(raw["D1"], [1, 2, 5, 10, 20])
    h1["atr_prev"] = h1.atr14.shift(1)
    # Decision grid is the H1 open. For live closed-only CSV, append the next H1 open.
    base = _decision_times(raw["H1"], 60, include_next).merge(h1[["time", "atr_prev"]], on="time", how="left")
    # Synthetic next H1 decision uses the just-closed H1 ATR.
    if include_next and len(raw["H1"]):
        tnext = pd.Timestamp(raw["H1"].time.max()) + pd.Timedelta(hours=1)
        base.loc[base.time.eq(tnext), "atr_prev"] = float(h1.iloc[-1].atr14)
    mt, mo, mh, ml, mc, mv, ms = _m1_arrays(m1)
    rows = []
    for r in base.itertuples(index=False):
        a = float(r.atr_prev) if pd.notna(r.atr_prev) else np.nan
        t = np.datetime64(r.time)
        e = np.searchsorted(mt, t, side="left")
        rec = {"time": pd.Timestamp(r.time), "atr_prev": a}
        if not np.isfinite(a) or a <= 0 or e < 121:
            rows.append(rec)
            continue
        for n in [5, 15, 30, 60, 120]:
            c0, c1 = mc[e - n], mc[e - 1]
            hh, ll = mh[e - n:e].max(), ml[e - n:e].min()
            den = hh - ll
            diff = np.abs(np.diff(mc[e - n:e])).sum()
            rec[f"m1_ret{n}_atr"] = (c1 - c0) / a
            rec[f"m1_range{n}_atr"] = (hh - ll) / a
            rec[f"m1_pos{n}"] = (c1 - ll) / den if den > 0 else np.nan
            rec[f"m1_eff{n}"] = abs(c1 - c0) / diff if diff > 0 else np.nan
            prev_vol = mv[e - 2 * n:e - n].mean() if e >= 2 * n else np.nan
            rec[f"m1_volratio{n}"] = mv[e - n:e].mean() / prev_vol if np.isfinite(prev_vol) and prev_vol > 0 else np.nan
            rec[f"m1_spreadmax{n}_usd"] = ms[e - n:e].max()
        k = e - 1
        rng = mh[k] - ml[k]
        rec["m1_body_signed"] = (mc[k] - mo[k]) / rng if rng > 0 else 0.0
        rec["m1_body_ratio"] = abs(mc[k] - mo[k]) / rng if rng > 0 else 0.0
        rec["m1_upper_wick_ratio"] = (mh[k] - max(mo[k], mc[k])) / rng if rng > 0 else 0.0
        rec["m1_lower_wick_ratio"] = (min(mo[k], mc[k]) - ml[k]) / rng if rng > 0 else 0.0
        rec["m1_range_atr"] = rng / a
        rec["m1_vol_ratio20"] = mv[k] / mv[max(0, k - 19):k + 1].mean()
        rec["m1_spread_usd"] = ms[k]
        med = np.median(ms[max(0, k - 19):k + 1])
        rec["m1_spread_ratio20"] = ms[k] / med if med > 0 else np.nan
        rows.append(rec)
    ctx = pd.DataFrame(rows)
    common = ["open", "high", "low", "close", "atr14", "atr_ratio", "ema20", "ema50", "dist_ema8_atr", "dist_ema20_atr", "dist_ema50_atr", "ema20_slope6_atr", "ema50_slope12_atr", "body_signed", "body_ratio", "upper_wick_ratio", "lower_wick_ratio", "range_atr", "vol_ratio20", "spread_usd", "spread_ratio20"]
    for prefix, df, mins, wins in [("m5", m5, 5, [1, 3, 6, 12, 24, 48]), ("m15", m15, 15, [1, 2, 4, 8, 16]), ("h1", h1, 60, [1, 2, 4, 8, 16]), ("h4", h4, 240, [1, 2, 3, 6, 12]), ("d1", d1, 1440, [1, 2, 5, 10, 20])]:
        cols = common.copy()
        for n in wins:
            cols += [f"ret{n}_atr", f"range{n}_atr", f"pos{n}", f"eff{n}", f"volratio{n}", f"spreadmax{n}_usd"]
        ctx = merge_closed(ctx, df, prefix, mins, [c for c in cols if c in df.columns])
    pos = (ctx.h4_close > ctx.h4_ema20) & (ctx.h4_ema20 > ctx.h4_ema50) & (ctx.h4_ema20_slope6_atr > 0) & (ctx.h4_dist_ema20_atr > -0.3)
    neg = (ctx.h4_close < ctx.h4_ema20) & (ctx.h4_ema20 < ctx.h4_ema50) & (ctx.h4_ema20_slope6_atr < 0) & (ctx.h4_dist_ema20_atr < 0.3)
    ctx["h4_trend"] = np.where(pos, 1, np.where(neg, -1, 0)).astype("int8")
    pos = (ctx.d1_close > ctx.d1_ema20) & (ctx.d1_ema20 > ctx.d1_ema50) & (ctx.d1_ema20_slope6_atr > 0) & (ctx.d1_dist_ema20_atr > -0.3)
    neg = (ctx.d1_close < ctx.d1_ema20) & (ctx.d1_ema20 < ctx.d1_ema50) & (ctx.d1_ema20_slope6_atr < 0) & (ctx.d1_dist_ema20_atr < 0.3)
    ctx["d1_trend"] = np.where(pos, 1, np.where(neg, -1, 0)).astype("int8")
    return ctx


def stage280_model_frame(ctx: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    x = ctx.copy()
    d = 1
    raw = [c for c in ctx.columns if c not in {"time", "atr_prev", "h4_trend", "d1_trend"}]
    for c in raw:
        if any(p in c for p in ["ret", "dist_ema", "ema20_slope", "ema50_slope", "body_signed"]):
            x[c] = pd.to_numeric(x[c], errors="coerce") * d
        elif "_pos" in c:
            x[c] = (2 * pd.to_numeric(x[c], errors="coerce") - 1) * d
    def g(c: str):
        return pd.to_numeric(x.get(c, np.nan), errors="coerce")
    x["countermove_60"] = -g("m1_ret60_atr")
    x["countermove_120"] = -g("m1_ret120_atr")
    x["turn_5"] = g("m1_ret5_atr")
    x["turn_15"] = g("m1_ret15_atr")
    x["turn_30"] = g("m1_ret30_atr")
    x["turn_accel_5v30"] = g("m1_ret5_atr") - (g("m1_ret30_atr") - g("m1_ret5_atr")) / 5
    x["turn_accel_15v60"] = g("m1_ret15_atr") - (g("m1_ret60_atr") - g("m1_ret15_atr")) / 3
    x["m5_turn_accel"] = g("m5_ret3_atr") - (g("m5_ret12_atr") - g("m5_ret3_atr")) / 3
    x["m15_turn_accel"] = g("m15_ret1_atr") - (g("m15_ret4_atr") - g("m15_ret1_atr")) / 3
    x["m1_reject_wick"] = g("m1_lower_wick_ratio") - g("m1_upper_wick_ratio")
    x["m5_reject_wick"] = g("m5_lower_wick_ratio") - g("m5_upper_wick_ratio")
    x["m15_reject_wick"] = g("m15_lower_wick_ratio") - g("m15_upper_wick_ratio")
    x["h4_align"] = x.h4_trend
    x["d1_align"] = x.d1_trend
    return x.reindex(columns=features).replace([np.inf, -np.inf], np.nan).fillna(0).astype("float32")


def build_stage281_context(candle_dir: Path, include_next: bool = True) -> pd.DataFrame:
    raw = load_gold(candle_dir, tail_only=True)
    m1 = raw["M1"]
    m5 = add_indicators(raw["M5"], [1, 3, 6, 12, 24])
    m15 = add_indicators(raw["M15"], [1, 2, 4, 8, 16])
    h1 = add_indicators(raw["H1"], [1, 2, 4, 8])
    h4 = add_indicators(raw["H4"], [1, 2, 3, 6])
    d1 = add_indicators(raw["D1"], [1, 2, 5, 10])
    base = _decision_times(raw["M15"], 15, include_next)
    common = ["atr14", "atr_ratio", "dist_ema8_atr", "dist_ema20_atr", "dist_ema50_atr", "ema20_slope6_atr", "ema50_slope12_atr", "body_signed", "body_ratio", "upper_wick_ratio", "lower_wick_ratio", "range_atr", "vol_ratio20", "spread_usd", "spread_ratio20"]
    ctx = base.copy()
    for prefix, df, mins, wins in [("m5", m5, 5, [1, 3, 6, 12, 24]), ("m15", m15, 15, [1, 2, 4, 8, 16]), ("h1", h1, 60, [1, 2, 4, 8]), ("h4", h4, 240, [1, 2, 3, 6]), ("d1", d1, 1440, [1, 2, 5, 10])]:
        cols = common.copy()
        for n in wins:
            cols += [f"ret{n}_atr", f"range{n}_atr", f"pos{n}", f"eff{n}", f"volratio{n}", f"spreadmax{n}_usd"]
        ctx = merge_closed(ctx, df, prefix, mins, [c for c in cols if c in df.columns])
    ctx["h4_trend"] = np.where((ctx.h4_dist_ema20_atr > 0) & (ctx.h4_ema20_slope6_atr > 0) & (ctx.h4_ema50_slope12_atr >= 0), 1, np.where((ctx.h4_dist_ema20_atr < 0) & (ctx.h4_ema20_slope6_atr < 0) & (ctx.h4_ema50_slope12_atr <= 0), -1, 0)).astype("int8")
    ctx["d1_trend"] = np.where((ctx.d1_dist_ema20_atr > 0) & (ctx.d1_ema20_slope6_atr > 0), 1, np.where((ctx.d1_dist_ema20_atr < 0) & (ctx.d1_ema20_slope6_atr < 0), -1, 0)).astype("int8")
    mt, mo, mh, ml, mc, mv, ms = _m1_arrays(m1)
    rows = []
    for r in ctx.itertuples(index=False):
        t = np.datetime64(r.time)
        s = np.searchsorted(mt, t, side="left")
        a = float(r.h1_atr14) if pd.notna(r.h1_atr14) else np.nan
        rec = {}
        if not np.isfinite(a) or a <= 0 or s < 120:
            rows.append(rec)
            continue
        for n in [15, 30, 60, 120]:
            c0, c1 = mc[s - n], mc[s - 1]
            hh, ll = mh[s - n:s].max(), ml[s - n:s].min()
            den = hh - ll
            diff = np.abs(np.diff(mc[s - n:s])).sum()
            prev_vol = mv[s - 2 * n:s - n].mean() if s >= 2 * n else np.nan
            rec[f"m1_ret{n}"] = (c1 - c0) / a
            rec[f"m1_range{n}"] = (hh - ll) / a
            rec[f"m1_pos{n}"] = (c1 - ll) / den if den > 0 else np.nan
            rec[f"m1_eff{n}"] = abs(c1 - c0) / diff if diff > 0 else np.nan
            rec[f"m1_volratio{n}"] = mv[s - n:s].mean() / prev_vol if np.isfinite(prev_vol) and prev_vol > 0 else np.nan
            rec[f"m1_spreadmax{n}"] = ms[s - n:s].max()
        rows.append(rec)
    return pd.concat([ctx.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def stage281_model_frame(ctx: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    x = ctx.copy()
    d = 1
    base_features = [c for c in features if c in x.columns]
    out = x[base_features].copy()
    for c in base_features:
        if any(k in c for k in ["ret", "dist_ema", "ema20_slope", "ema50_slope", "body_signed"]):
            out[c] = pd.to_numeric(out[c], errors="coerce") * d
        elif "_pos" in c:
            out[c] = (2 * pd.to_numeric(out[c], errors="coerce") - 1) * d
    out["countermove_30"] = -pd.to_numeric(out.get("m1_ret30", np.nan), errors="coerce")
    out["countermove_60"] = -pd.to_numeric(out.get("m1_ret60", np.nan), errors="coerce")
    out["countermove_120"] = -pd.to_numeric(out.get("m1_ret120", np.nan), errors="coerce")
    out["turn_accel_m1"] = pd.to_numeric(out.get("m1_ret15", 0), errors="coerce") - (pd.to_numeric(out.get("m1_ret60", 0), errors="coerce") - pd.to_numeric(out.get("m1_ret15", 0), errors="coerce")) / 3
    out["turn_accel_m5"] = pd.to_numeric(out.get("m5_ret3_atr", 0), errors="coerce") - (pd.to_numeric(out.get("m5_ret12_atr", 0), errors="coerce") - pd.to_numeric(out.get("m5_ret3_atr", 0), errors="coerce")) / 3
    out["turn_accel_m15"] = pd.to_numeric(out.get("m15_ret1_atr", 0), errors="coerce") - (pd.to_numeric(out.get("m15_ret4_atr", 0), errors="coerce") - pd.to_numeric(out.get("m15_ret1_atr", 0), errors="coerce")) / 3
    out["h4_align"] = x.h4_trend
    out["d1_align"] = x.d1_trend
    return out.reindex(columns=features).replace([np.inf, -np.inf], np.nan).fillna(0).astype("float32")


def load_booster(path: Path) -> lgb.Booster:
    if path.name.endswith(".txt.gz.b64"):
        model_text = gzip.decompress(base64.b64decode(path.read_text(encoding="ascii"))).decode("utf-8")
        return lgb.Booster(model_str=model_text)
    return lgb.Booster(model_file=str(path))


def add_external_short_features(ctx: pd.DataFrame, candle_dir: Path) -> pd.DataFrame:
    out = ctx.copy()
    for key, prefix in [("SP_M15", "sp"), ("NQ_M15", "nq")]:
        d = read_candles(candle_dir / EXTERNAL_FILES[key], 6000)
        # Stage285 external contract uses Wilder ATR14 and ret4/ATR.
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
