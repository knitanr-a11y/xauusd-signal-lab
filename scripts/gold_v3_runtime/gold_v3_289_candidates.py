#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 fixed candidate detection from contractually closed live candles."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from gold_v3_289_live_features import (EXTERNAL_FILES,GOLD_FILES,add_external_short_features,build_stage280_context,build_stage281_context,find_trigger,m5_trigger_frame,read_candles,stage280_model_frame,stage281_model_frame)
from gold_v3_289_artifacts import load_frozen_booster
STAGE286_Q90_LOWER=2.162461836828524
STAGE286_SCORE_UPPER=2.992581130893
STAGE286_RISK_UPPER=0.410970621210

def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))

def load_model_contracts() -> tuple[Path, dict[str, Any], Path, dict[str, Any]]:
    mdir = Path(__file__).resolve().with_name('models') / 'gold_v3_289'
    p280m = mdir / 'stage280_rev_long_2026_model.txt'
    p280c = mdir / 'stage280_rev_long_2026_contract.json'
    p281m = mdir / 'stage281_med4h_cont_long_2026_model.txt'
    p281c = mdir / 'stage281_med4h_cont_long_2026_contract.json'
    for p in [p280m,p280c,p281m,p281c]:
        if not p.exists():
            raise FileNotFoundError(p)
    return (p280m, read_json(p280c), p281m, read_json(p281c))

def candidate_id(source: str, entry: pd.Timestamp) -> str:
    return f'{source}|{pd.Timestamp(entry).isoformat()}'

def dedupe_source_candidates(df: pd.DataFrame, source: str, cooldown_minutes: int=0) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = df[df.source.eq(source)].copy()
    if x.empty:
        return x
    x = x.sort_values(['entry_dt', 'ml_score', 'decision_dt'], ascending=[True, False, True]).drop_duplicates('entry_dt', keep='first')
    if cooldown_minutes > 0:
        keep = []
        last = pd.Timestamp.min
        for r in x.sort_values(['decision_dt', 'entry_dt']).itertuples():
            if pd.Timestamp(r.decision_dt) >= last + pd.Timedelta(minutes=cooldown_minutes):
                keep.append(r.Index)
                last = pd.Timestamp(r.decision_dt)
        x = x.loc[keep]
    x['candidate_id'] = [candidate_id(source, t) for t in x.entry_dt]
    return x.sort_values('entry_dt').reset_index(drop=True)

def detect_candidates(cdir: Path, lookback_hours: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    p280m, c280, p281m, c281 = load_model_contracts()
    b280, b281 = (load_frozen_booster(p280m), load_frozen_booster(p281m))
    m5 = m5_trigger_frame(cdir)
    latest_time = max(pd.Timestamp(m5.time.max()), pd.Timestamp(read_candles(cdir / GOLD_FILES['M15'], 4).time.max()))
    cutoff = latest_time - pd.Timedelta(hours=lookback_hours)
    rows: list[dict[str, Any]] = []
    ctx280 = build_stage280_context(cdir, include_next=True)
    recent280 = ctx280[ctx280.time >= cutoff].copy()
    x280 = stage280_model_frame(recent280, list(c280['features']))
    recent280['ml_score'] = b280.predict(x280)
    recent280['score_threshold'] = float(c280['score_threshold'])
    for r in recent280[(recent280.h4_trend == -1) & (recent280.ml_score >= recent280.score_threshold)].itertuples():
        trig, entry, price = find_trigger(m5, pd.Timestamp(r.time), 1, 'BRK6', 60)
        if pd.isna(entry):
            continue
        rows.append({'candidate_id': '', 'source': 'STAGE280', 'priority': 10, 'decision_dt': r.time, 'trigger_dt': trig, 'entry_dt': entry, 'entry_price': price, 'direction': 'LONG', 'direction_num': 1, 'ml_score': r.ml_score, 'score_threshold': r.score_threshold, 'atr_entry': r.atr_prev, 'tp_atr': 1.75, 'sl_atr': 1.0, 'max_holding_minutes': 360, 'candidate_contract': 'REV_LONG_Q95_BRK6_E175_SHADOW_RESEARCH'})
    ctx281 = build_stage281_context(cdir, include_next=True)
    recent281 = ctx281[ctx281.time >= cutoff].copy()
    x281 = stage281_model_frame(recent281, list(c281['features']))
    recent281['ml_score'] = b281.predict(x281)
    recent281['score_threshold'] = float(c281['score_threshold'])
    for r in recent281[(recent281.h4_trend == 1) & (recent281.ml_score >= recent281.score_threshold)].itertuples():
        trig, entry, price = find_trigger(m5, pd.Timestamp(r.time), 1, 'EMA20', 45)
        if pd.isna(entry):
            continue
        rows.append({'candidate_id': '', 'source': 'STAGE281', 'priority': 20, 'decision_dt': r.time, 'trigger_dt': trig, 'entry_dt': entry, 'entry_price': price, 'direction': 'LONG', 'direction_num': 1, 'ml_score': r.ml_score, 'score_threshold': r.score_threshold, 'atr_entry': r.h1_atr14, 'tp_atr': 2.25, 'sl_atr': 1.25, 'max_holding_minutes': 480, 'candidate_contract': 'M15_CONT_LONG_Q85_EMA20_E225_AFTER_BASE_LOSS_72H_SHADOW_NEAR_MISS'})
    external_ready = all(((cdir / name).exists() for name in EXTERNAL_FILES.values()))
    if external_ready:
        short_ctx = add_external_short_features(ctx281, cdir)
        short_recent = short_ctx[short_ctx.time >= cutoff].copy()
        strict = short_recent[(short_recent.h4_trend == 1) & (short_recent.m15_ret8_atr >= STAGE286_Q90_LOWER) & (short_recent.m15_ret8_atr <= STAGE286_SCORE_UPPER) & (short_recent.m15_pos4 >= 0.75) & (short_recent.m15_upper_wick_ratio >= short_recent.m15_lower_wick_ratio) & (short_recent.risk_m15_ret4_mean <= STAGE286_RISK_UPPER)]
        for r in strict.itertuples():
            trig, entry, price = find_trigger(m5, pd.Timestamp(r.time), -1, 'EMA20', 60)
            if pd.isna(entry):
                continue
            rows.append({'candidate_id': '', 'source': 'STAGE286', 'priority': 60, 'decision_dt': r.time, 'trigger_dt': trig, 'entry_dt': entry, 'entry_price': price, 'direction': 'SHORT', 'direction_num': -1, 'ml_score': np.nan, 'score_threshold': np.nan, 'atr_entry': r.h1_atr14, 'tp_atr': 2.25, 'sl_atr': 1.25, 'max_holding_minutes': 480, 'candidate_contract': 'SHORT_EXHAUST_MODERATE_OVERHEAT_SUBDUED_US_EQUITY', 'gold_exhaustion_score': r.m15_ret8_atr, 'risk_m15_ret4_mean': r.risk_m15_ret4_mean})
    out = pd.DataFrame(rows)
    if len(out):
        out['decision_dt'] = pd.to_datetime(out.decision_dt)
        out['trigger_dt'] = pd.to_datetime(out.trigger_dt)
        out['entry_dt'] = pd.to_datetime(out.entry_dt)
        parts = [dedupe_source_candidates(out, 'STAGE280', 0), dedupe_source_candidates(out, 'STAGE281', 120), dedupe_source_candidates(out, 'STAGE286', 120)]
        out = pd.concat([q for q in parts if len(q)], ignore_index=True) if any((len(q) for q in parts)) else pd.DataFrame(columns=out.columns)
        out = out.sort_values(['entry_dt', 'priority', 'candidate_id']).reset_index(drop=True)
    return (out, {'latest_candle_time': str(latest_time), 'stage280_threshold': float(c280['score_threshold']), 'stage281_threshold': float(c281['score_threshold']), 'external_short_ready': external_ready})
