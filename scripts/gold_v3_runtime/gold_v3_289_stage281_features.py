#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from gold_v3_289_feature_core import add_indicators,decision_times as _decision_times,load_gold,m1_arrays as _m1_arrays,merge_closed

def build_stage281_context(candle_dir: Path, include_next: bool = True, tail_only: bool = True) -> pd.DataFrame:
    raw = load_gold(candle_dir, tail_only=tail_only)
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
    base_features = [c for c in features if c in x.columns]
    out = x[base_features].copy()
    for c in base_features:
        if any(k in c for k in ["ret", "dist_ema", "ema20_slope", "ema50_slope", "body_signed"]):
            out[c] = pd.to_numeric(out[c], errors="coerce")
        elif "_pos" in c:
            out[c] = 2 * pd.to_numeric(out[c], errors="coerce") - 1
    out["countermove_30"] = -pd.to_numeric(out.get("m1_ret30", np.nan), errors="coerce")
    out["countermove_60"] = -pd.to_numeric(out.get("m1_ret60", np.nan), errors="coerce")
    out["countermove_120"] = -pd.to_numeric(out.get("m1_ret120", np.nan), errors="coerce")
    out["turn_accel_m1"] = pd.to_numeric(out.get("m1_ret15", 0), errors="coerce") - (pd.to_numeric(out.get("m1_ret60", 0), errors="coerce") - pd.to_numeric(out.get("m1_ret15", 0), errors="coerce")) / 3
    out["turn_accel_m5"] = pd.to_numeric(out.get("m5_ret3_atr", 0), errors="coerce") - (pd.to_numeric(out.get("m5_ret12_atr", 0), errors="coerce") - pd.to_numeric(out.get("m5_ret3_atr", 0), errors="coerce")) / 3
    out["turn_accel_m15"] = pd.to_numeric(out.get("m15_ret1_atr", 0), errors="coerce") - (pd.to_numeric(out.get("m15_ret4_atr", 0), errors="coerce") - pd.to_numeric(out.get("m15_ret1_atr", 0), errors="coerce")) / 3
    out["h4_align"] = x.h4_trend
    out["d1_align"] = x.d1_trend
    return out.reindex(columns=features).replace([np.inf, -np.inf], np.nan).fillna(0).astype("float32")
