#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 resolved-only portfolio state and safe SHADOW diagnosis."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from gold_v3_289_live_features import GOLD_FILES,read_candles
COST=0.60
def utc_now()->str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def read_json(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def empty_observation_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=['candidate_id', 'source', 'priority', 'decision_dt', 'trigger_dt', 'entry_dt', 'entry_price', 'direction', 'direction_num', 'atr_entry', 'tp_atr', 'sl_atr', 'max_holding_minutes', 'tp_price', 'sl_price', 'status', 'exit_dt', 'exit_price', 'exit_reason', 'gross_pnl', 'pnl'])

def load_trade_ledger(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return empty_observation_ledger()
    d = pd.read_csv(path, encoding='utf-8-sig')
    for c in ['decision_dt', 'trigger_dt', 'entry_dt', 'exit_dt']:
        if c in d:
            d[c] = pd.to_datetime(d[c], errors='coerce')
    return d

def resolve_shadow_observations(ledger: pd.DataFrame, cdir: Path) -> pd.DataFrame:
    if ledger.empty:
        return ledger
    m1 = read_candles(cdir / GOLD_FILES['M1'], 30000)
    times = m1.time.to_numpy('datetime64[ns]')
    h, l, o = (m1.high.to_numpy(float), m1.low.to_numpy(float), m1.open.to_numpy(float))
    latest = pd.Timestamp(m1.time.max())
    x = ledger.copy()
    for idx, r in x[x.status.eq('OPEN')].iterrows():
        entry, direction = (pd.Timestamp(r.entry_dt), int(r.direction_num))
        planned = entry + pd.Timedelta(minutes=int(r.max_holding_minutes))
        end_time = min(planned, latest + pd.Timedelta(minutes=1))
        s = np.searchsorted(times, np.datetime64(entry), side='left')
        e = np.searchsorted(times, np.datetime64(end_time), side='left')
        exit_dt = pd.NaT
        exit_price = np.nan
        reason = ''
        for k in range(s, e):
            hit_tp = h[k] >= float(r.tp_price) if direction == 1 else l[k] <= float(r.tp_price)
            hit_sl = l[k] <= float(r.sl_price) if direction == 1 else h[k] >= float(r.sl_price)
            if hit_sl or hit_tp:
                if hit_sl:
                    exit_price, reason = (float(r.sl_price), 'SL')
                else:
                    exit_price, reason = (float(r.tp_price), 'TP')
                exit_dt = pd.Timestamp(times[k])
                break
        if pd.isna(exit_dt) and latest >= planned:
            k = np.searchsorted(times, np.datetime64(planned), side='left')
            if k < len(times):
                exit_dt, exit_price, reason = (planned, float(o[k]), 'TIME')
        if pd.notna(exit_dt):
            gross = direction * (exit_price - float(r.entry_price))
            x.loc[idx, ['status', 'exit_dt', 'exit_price', 'exit_reason', 'gross_pnl', 'pnl']] = ['CLOSED', exit_dt, exit_price, reason, gross, gross - COST]
    return x

def import_base_resolved(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=['entry_dt', 'exit_dt', 'pnl', 'source'])
    d = pd.read_csv(path, encoding='utf-8-sig')
    required = {'entry_dt', 'exit_dt', 'pnl'}
    if not required.issubset(d.columns):
        raise ValueError(f'base resolved ledger missing {sorted(required - set(d.columns))}')
    d['entry_dt'] = pd.to_datetime(d.entry_dt, errors='coerce')
    d['exit_dt'] = pd.to_datetime(d.exit_dt, errors='coerce')
    d['pnl'] = pd.to_numeric(d.pnl, errors='coerce')
    d = d.dropna(subset=['entry_dt', 'exit_dt', 'pnl'])
    d['source'] = 'BASE'
    return d[['entry_dt', 'exit_dt', 'pnl', 'source']].sort_values('exit_dt')

def state_at(t: pd.Timestamp, ledger: pd.DataFrame, base: pd.DataFrame) -> dict[str, Any]:
    resolved_c = ledger[(ledger.status == 'CLOSED') & (ledger.exit_dt <= t)][['entry_dt', 'exit_dt', 'pnl', 'source']].copy() if len(ledger) else pd.DataFrame(columns=['entry_dt', 'exit_dt', 'pnl', 'source'])
    resolved = pd.concat([base[base.exit_dt <= t], resolved_c], ignore_index=True).sort_values('exit_dt')
    vals = resolved.pnl.to_numpy(float) if len(resolved) else np.array([], float)
    curve = np.cumsum(vals)
    equity = float(vals.sum()) if len(vals) else 0.0
    peak = float(max(0.0, curve.max())) if len(curve) else 0.0
    last_loss = resolved[(resolved.source != 'BASE') & (resolved.pnl < 0)].exit_dt.max() if len(resolved) else pd.NaT
    last_base = resolved[resolved.source == 'BASE'].tail(1)
    pending = ledger[(ledger.status == 'OPEN') & (ledger.entry_dt <= t)] if len(ledger) else pd.DataFrame()
    observed_candidates = ledger[ledger.source.isin(['STAGE280', 'STAGE281', 'STAGE286'])] if len(ledger) else pd.DataFrame()
    last_candidate_entry = observed_candidates.entry_dt.max() if len(observed_candidates) else pd.NaT
    return {'equity': equity, 'peak': peak, 'dd': peak - equity, 'last_candidate_loss_exit': last_loss, 'last_base_exit': last_base.exit_dt.iloc[0] if len(last_base) else pd.NaT, 'last_base_pnl': float(last_base.pnl.iloc[0]) if len(last_base) else np.nan, 'pending_candidate_count': int(len(pending)), 'last_candidate_entry': last_candidate_entry, 'base_resolved_count': int((resolved.source == 'BASE').sum()) if len(resolved) else 0}

def evaluate_shadow_eligibility(candidates: pd.DataFrame, ledger: pd.DataFrame, base: pd.DataFrame, base_state_ready: bool=True) -> tuple[pd.DataFrame, pd.DataFrame]:
    if candidates.empty:
        return (pd.DataFrame(), ledger)
    existing = set(ledger.candidate_id.astype(str)) if len(ledger) else set()
    decisions = []
    current = ledger.copy()
    for r in candidates.sort_values(['entry_dt', 'priority']).itertuples(index=False):
        if r.candidate_id in existing:
            continue
        t = pd.Timestamp(r.entry_dt)
        st = state_at(t, current, base)
        reasons = []
        if not base_state_ready:
            reasons.append('BASE_PORTFOLIO_STATE_NOT_CONNECTED')
        if st['pending_candidate_count'] > 0:
            reasons.append('UNRESOLVED_CANDIDATE_ACTIVE')
        if r.source in {'STAGE280', 'STAGE281'} and st['dd'] > 30.0:
            reasons.append('COMBINED_DD_ABOVE_30')
        if r.source == 'STAGE286' and st['dd'] > 10.0:
            reasons.append('SHORT_DD_ABOVE_10')
        if pd.notna(st['last_candidate_entry']) and t < pd.Timestamp(st['last_candidate_entry']) + pd.Timedelta(hours=12):
            reasons.append('SHARED_12H_COOLDOWN')
        if r.source == 'STAGE281':
            if st['base_resolved_count'] == 0:
                reasons.append('BASE_RESOLVED_STATE_MISSING')
            elif not (st['last_base_pnl'] < 0 and t <= pd.Timestamp(st['last_base_exit']) + pd.Timedelta(hours=72)):
                reasons.append('NOT_AFTER_BASE_LOSS_WITHIN_72H')
        if r.source == 'STAGE286' and pd.notna(st['last_candidate_loss_exit']) and (t < pd.Timestamp(st['last_candidate_loss_exit']) + pd.Timedelta(hours=24)):
            reasons.append('SHORT_24H_AFTER_CANDIDATE_LOSS')
        shadow_eligible = len(reasons) == 0
        rec = r._asdict()
        rec.update({'shadow_eligible': shadow_eligible, 'reject_reasons': ';'.join(reasons), 'state_dd': st['dd'], 'state_equity': st['equity'], 'base_resolved_count': st['base_resolved_count']})
        decisions.append(rec)
        existing.add(r.candidate_id)
        if shadow_eligible:
            tp = float(r.entry_price) + int(r.direction_num) * float(r.tp_atr) * float(r.atr_entry)
            sl = float(r.entry_price) - int(r.direction_num) * float(r.sl_atr) * float(r.atr_entry)
            observation = rec.copy()
            observation.update({'tp_price': tp, 'sl_price': sl, 'status': 'OPEN', 'exit_dt': pd.NaT, 'exit_price': np.nan, 'exit_reason': '', 'gross_pnl': np.nan, 'pnl': np.nan})
            current = pd.concat([current, pd.DataFrame([observation])], ignore_index=True)
    return (pd.DataFrame(decisions), current)

def load_runtime_state(path: Path, latest_m5_time: pd.Timestamp, replay_existing: bool) -> tuple[dict[str, Any], bool]:
    if path.exists():
        state = read_json(path)
        return (state, False)
    state = {'initialized_at_utc': utc_now(), 'last_processed_m5_time': str(pd.Timestamp.min if replay_existing else pd.Timestamp(latest_m5_time)), 'bootstrap_mode': 'REPLAY_EXISTING' if replay_existing else 'LATEST_ONLY'}
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    return (state, True)

def update_runtime_state(path: Path, state: dict[str, Any], latest_m5_time: pd.Timestamp) -> None:
    state = dict(state)
    state['last_processed_m5_time'] = str(pd.Timestamp(latest_m5_time))
    state['updated_at_utc'] = utc_now()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
