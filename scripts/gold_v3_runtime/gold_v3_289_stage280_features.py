#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from gold_v3_289_feature_core import add_indicators,decision_times as _decision_times,load_gold,m1_arrays as _m1_arrays,merge_closed

def build_stage280_context(candle_dir: Path, include_next: bool = True) -> pd.DataFrame:
    raw = load_gold(candle_dir, tail_only=True)
    m1 = raw["M1"]
    m5 = add_indicators(raw["M5"], [1, 3, 6, 12, 24, 48])
    m15 = add_indicators(raw["M15"], [1, 2, 4, 8, 16])
    h1 = add_indicators(raw["H1"], [1, 2, 4, 8, 16])
    h4 = add_indicators(raw["H4"], [1, 2, 3, 6, 12])
    d1 = add_indicators(raw["D1"], [1, 2, 5, 10, 20])
    h1["atr_prev"] = h1.atr14.shift(1)
    base = _decision_times(raw["H1"], 60, include_next).merge(h1[["time", "atr_prev"]], on="time", how="left")
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
    raw = [c for c in ctx.columns if c not in {"time", "atr_prev", "h4_trend", "d1_trend"}]
    for c in raw:
        if any(p in c for p in ["ret", "dist_ema", "ema20_slope", "ema50_slope", "body_signed"]): x[c] = pd.to_numeric(x[c], errors="coerce")
        elif "_pos" in c: x[c] = 2 * pd.to_numeric(x[c], errors="coerce") - 1
    def g(c: str): return pd.to_numeric(x.get(c, np.nan), errors="coerce")
    x["countermove_60"]=-g("m1_ret60_atr"); x["countermove_120"]=-g("m1_ret120_atr")
    x["turn_5"]=g("m1_ret5_atr"); x["turn_15"]=g("m1_ret15_atr"); x["turn_30"]=g("m1_ret30_atr")
    x["turn_accel_5v30"]=g("m1_ret5_atr")-(g("m1_ret30_atr")-g("m1_ret5_atr"))/5
    x["turn_accel_15v60"]=g("m1_ret15_atr")-(g("m1_ret60_atr")-g("m1_ret15_atr"))/3
    x["m5_turn_accel"]=g("m5_ret3_atr")-(g("m5_ret12_atr")-g("m5_ret3_atr"))/3
    x["m15_turn_accel"]=g("m15_ret1_atr")-(g("m15_ret4_atr")-g("m15_ret1_atr"))/3
    x["m1_reject_wick"]=g("m1_lower_wick_ratio")-g("m1_upper_wick_ratio")
    x["m5_reject_wick"]=g("m5_lower_wick_ratio")-g("m5_upper_wick_ratio")
    x["m15_reject_wick"]=g("m15_lower_wick_ratio")-g("m15_upper_wick_ratio")
    x["h4_align"]=x.h4_trend; x["d1_align"]=x.d1_trend
    return x.reindex(columns=features).replace([np.inf,-np.inf],np.nan).fillna(0).astype("float32")
