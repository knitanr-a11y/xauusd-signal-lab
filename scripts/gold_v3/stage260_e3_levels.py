from __future__ import annotations

import math
from bisect import bisect_left, bisect_right, insort
from typing import Any, Iterable

import numpy as np
import pandas as pd

from stage260_event_audit_utils import true_range

def causal_percentile(values: Iterable[float], window: int, min_periods: int) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    out = np.full(len(arr), np.nan, dtype=float)
    sorted_hist: list[float] = []
    queue: list[float] = []
    q_start = 0
    for i, v in enumerate(arr):
        if np.isfinite(v) and len(sorted_hist) >= min_periods:
            out[i] = bisect_right(sorted_hist, float(v)) / len(sorted_hist)
        queue.append(float(v))
        if np.isfinite(v):
            insort(sorted_hist, float(v))
        if len(queue) - q_start > window:
            old = queue[q_start]
            q_start += 1
            if np.isfinite(old):
                j = bisect_left(sorted_hist, old)
                if j >= len(sorted_hist) or sorted_hist[j] != old:
                    raise AssertionError('causal percentile removal mismatch')
                sorted_hist.pop(j)
        if q_start > 4096:
            queue = queue[q_start:]
            q_start = 0
    return out

def make_h1_with_atr(h1: pd.DataFrame) -> pd.DataFrame:
    x = h1.copy().reset_index(drop=True)
    x['h1_index'] = np.arange(len(x), dtype=int)
    x['h1_tr'] = true_range(x)
    x['h1_atr14'] = x['h1_tr'].rolling(14, min_periods=14).mean()
    x['h1_atr50'] = x['h1_tr'].rolling(50, min_periods=50).mean()
    x['h1_atr_pct'] = causal_percentile(x['h1_atr14'].to_numpy(), 1000, 200)
    x['h1_atr_band'] = pd.cut(
        x['h1_atr_pct'], [-np.inf, .2, .4, .6, .8, np.inf],
        labels=['P00_20', 'P20_40', 'P40_60', 'P60_80', 'P80_100']
    ).astype('string')
    return x

def build_confirmed_reactions(h1: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    hi = h1['high'].to_numpy(float)
    lo = h1['low'].to_numpy(float)
    cl = h1['close'].to_numpy(float)
    atr = h1['h1_atr14'].to_numpy(float)
    for i in range(2, len(h1) - 2):
        if not np.isfinite(atr[i]):
            continue
        window_hi = hi[i-2:i+3]
        window_lo = lo[i-2:i+3]
        confirm_time = pd.Timestamp(h1['source_close_time'].iloc[i+2])
        pivot_time = pd.Timestamp(h1['source_close_time'].iloc[i])
        if hi[i] >= np.max(window_hi) and np.any(cl[i+1:i+3] <= hi[i] - .25 * atr[i]):
            rows.append({
                'side': 'RESISTANCE', 'price': float(hi[i]), 'pivot_index': i,
                'pivot_time': pivot_time, 'confirm_time': confirm_time,
                'pivot_atr14': float(atr[i]),
            })
        if lo[i] <= np.min(window_lo) and np.any(cl[i+1:i+3] >= lo[i] + .25 * atr[i]):
            rows.append({
                'side': 'SUPPORT', 'price': float(lo[i]), 'pivot_index': i,
                'pivot_time': pivot_time, 'confirm_time': confirm_time,
                'pivot_atr14': float(atr[i]),
            })
    return pd.DataFrame(rows).sort_values(['confirm_time', 'side', 'price']).reset_index(drop=True)

def _cluster_from_arrays(prices: np.ndarray, pivot_ns: np.ndarray, confirm_ns: np.ndarray,
                         tol: float, min_touches: int) -> dict[str, Any] | None:
    if len(prices) < min_touches:
        return None
    med=float(np.median(prices))
    mask=np.abs(prices-med)<=tol
    pp=prices[mask]; pt=pivot_ns[mask]; ct=confirm_ns[mask]
    if len(pp)<min_touches:
        return None
    order=np.argsort(pt,kind='stable'); pp=pp[order]; pt=pt[order]; ct=ct[order]
    keep=[]; last=-10**30; min_gap=12*3600*10**9
    for k,t in enumerate(pt):
        if not keep or int(t)-int(last)>=min_gap:
            keep.append(k); last=int(t)
    if len(keep)<min_touches:
        return None
    pp=pp[keep]; pt=pt[keep]; ct=ct[keep]
    if int(pt[-1])-int(pt[0])<24*3600*10**9:
        return None
    med=float(np.median(pp)); final=np.abs(pp-med)<=tol
    pp=pp[final]; pt=pt[final]; ct=ct[final]
    if len(pp)<min_touches:
        return None
    return {'level':med,'touch_count':int(len(pp)),
            'first_touch_time':pd.Timestamp(int(pt.min())),
            'last_touch_time':pd.Timestamp(int(pt.max())),
            'latest_confirm_time':pd.Timestamp(int(ct.max())),
            'touch_span_hours':float((int(pt.max())-int(pt.min()))/3.6e12),
            'max_deviation':float(np.max(np.abs(pp-med)))}

def _best_level_arrays(prices: np.ndarray, pivot_idx: np.ndarray, pivot_ns: np.ndarray, confirm_ns: np.ndarray,
                       side: str, current_index: int, current_close: float, current_atr: float,
                       context_ns: int, min_touches: int) -> dict[str, Any] | None:
    if len(prices)==0 or not np.isfinite(current_atr) or current_atr<=0:
        return None
    lo=current_index-480
    eligible=(pivot_idx>=lo)&(pivot_idx<=current_index)&(confirm_ns<=context_ns-4*3600*10**9)
    if side=='RESISTANCE': eligible &= prices>current_close
    else: eligible &= prices<current_close
    if not eligible.any(): return None
    pr=prices[eligible]; pt=pivot_ns[eligible]; ct=confirm_ns[eligible]
    tol=.15*current_atr
    seeds=np.unique(pr)
    if side=='RESISTANCE': seeds=np.sort(seeds)
    else: seeds=np.sort(seeds)[::-1]
    best=None
    for seed in seeds:
        m=np.abs(pr-seed)<=tol
        if int(m.sum())<min_touches: continue
        item=_cluster_from_arrays(pr[m],pt[m],ct[m],tol,min_touches)
        if item is None: continue
        level=float(item['level'])
        if side=='RESISTANCE' and level<=current_close: continue
        if side=='SUPPORT' and level>=current_close: continue
        item={**item,'distance':abs(level-current_close),'side':side}
        if best is None or item['distance']<best['distance']:
            best=item
        if best is not None and abs(seed-current_close)>best['distance']+tol:
            break
    return best

def build_level_context(h1: pd.DataFrame, reactions: pd.DataFrame, min_touches: int = 3) -> pd.DataFrame:
    rows=[]
    start_time=pd.Timestamp('2025-01-01')
    arrays={}
    for side in ['RESISTANCE','SUPPORT']:
        z=reactions[reactions.side.eq(side)].sort_values('pivot_index')
        arrays[side]=(z.price.to_numpy(float),z.pivot_index.to_numpy(int),
                      z.pivot_time.astype('int64').to_numpy(),z.confirm_time.astype('int64').to_numpy())
    for _,r in h1.iterrows():
        context_time=pd.Timestamp(r['source_close_time'])
        if context_time<start_time or not np.isfinite(r['h1_atr14']):
            continue
        context_ns=int(context_time.value); idx=int(r['h1_index']); close=float(r['close']); atr=float(r['h1_atr14'])
        res=_best_level_arrays(*arrays['RESISTANCE'],'RESISTANCE',idx,close,atr,context_ns,min_touches)
        sup=_best_level_arrays(*arrays['SUPPORT'],'SUPPORT',idx,close,atr,context_ns,min_touches)
        out={'level_context_time':context_time,'h1_context_close':close,'h1_atr14_level_context':atr}
        for prefix,item in [('res',res),('sup',sup)]:
            if item is None:
                out.update({f'{prefix}_level':np.nan,f'{prefix}_touch_count':np.nan,f'{prefix}_quality':pd.NA,
                            f'{prefix}_first_touch_time':pd.NaT,f'{prefix}_last_touch_time':pd.NaT,
                            f'{prefix}_latest_confirm_time':pd.NaT,f'{prefix}_touch_span_hours':np.nan,
                            f'{prefix}_max_deviation':np.nan})
            else:
                tc=int(item['touch_count']); quality='T3' if tc==3 else 'T4' if tc==4 else 'T5P'
                out.update({f'{prefix}_level':float(item['level']),f'{prefix}_touch_count':tc,f'{prefix}_quality':quality,
                            f'{prefix}_first_touch_time':item['first_touch_time'],f'{prefix}_last_touch_time':item['last_touch_time'],
                            f'{prefix}_latest_confirm_time':item['latest_confirm_time'],f'{prefix}_touch_span_hours':float(item['touch_span_hours']),
                            f'{prefix}_max_deviation':float(item['max_deviation'])})
        rows.append(out)
    return pd.DataFrame(rows).sort_values('level_context_time').reset_index(drop=True)

def build_m15_context(m15: pd.DataFrame, levels: pd.DataFrame, h1c: pd.DataFrame, h4c: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    x = m15.copy().sort_values('time').reset_index(drop=True)
    x['decision_time'] = x['source_close_time']
    x['prev8_close_max'] = x['close'].shift(1).rolling(8, min_periods=8).max()
    x['prev8_close_min'] = x['close'].shift(1).rolling(8, min_periods=8).min()
    x['prev8_contiguous'] = (x['time'] - x['time'].shift(8)) == pd.Timedelta(minutes=120)
    x = pd.merge_asof(
        x.sort_values('time'), levels.sort_values('level_context_time'),
        left_on='time', right_on='level_context_time', direction='backward', allow_exact_matches=True,
    )
    x = pd.merge_asof(
        x.sort_values('decision_time'), h1c.sort_values('source_close_time'),
        left_on='decision_time', right_on='source_close_time', direction='backward', allow_exact_matches=True,
        suffixes=('', '_h1src'),
    )
    x = pd.merge_asof(
        x.sort_values('decision_time'), h4c.sort_values('source_close_time'),
        left_on='decision_time', right_on='source_close_time', direction='backward', allow_exact_matches=True,
        suffixes=('', '_h4src'),
    )
    if (x['level_context_time'] > x['time']).fillna(False).any():
        raise AssertionError('level lookahead detected')
    if (x['source_close_time_h1src'] > x['decision_time']).fillna(False).any():
        raise AssertionError('H1 lookahead detected')
    if (x['source_close_time_h4src'] > x['decision_time']).fillna(False).any():
        raise AssertionError('H4 lookahead detected')
    entry_map = m1[['time', 'open']].rename(columns={'time': 'decision_time', 'open': 'entry_price'})
    x = x.merge(entry_map, on='decision_time', how='left', validate='many_to_one')
    x['weekday'] = x['decision_time'].dt.weekday
    x['server_hour'] = x['decision_time'].dt.hour
    x['month'] = x['decision_time'].dt.strftime('%Y-%m')
    x['quarter'] = x['decision_time'].dt.year.astype(str) + 'Q' + x['decision_time'].dt.quarter.astype(str)
    x['half'] = x['decision_time'].dt.year.astype(str) + 'H' + np.where(x['decision_time'].dt.month <= 6, '1', '2')
    return x.sort_values('decision_time').reset_index(drop=True)

def detect_breakouts(x: pd.DataFrame, *, min_touches: int = 3, level_shift_atr: float = 0.0,
                     population: str = 'E3_TRUE') -> pd.DataFrame:
    valid = (
        x['entry_price'].notna() & x['h1_atr14'].notna() & x['h4_atr_band'].notna()
        & x['prev8_contiguous']
    )
    res_level = x['res_level'] + level_shift_atr * x['h1_atr14']
    sup_level = x['sup_level'] - level_shift_atr * x['h1_atr14']
    long_mask = (
        valid & x['res_level'].notna() & x['res_touch_count'].ge(min_touches)
        & (x['close'] >= res_level + .10 * x['h1_atr14'])
        & (x['close'] > x['open'])
        & (x['prev8_close_max'] < res_level + .05 * x['h1_atr14'])
    )
    short_mask = (
        valid & x['sup_level'].notna() & x['sup_touch_count'].ge(min_touches)
        & (x['close'] <= sup_level - .10 * x['h1_atr14'])
        & (x['close'] < x['open'])
        & (x['prev8_close_min'] > sup_level - .05 * x['h1_atr14'])
    )
    rows: list[dict[str, Any]] = []
    common = [
        'time', 'decision_time', 'open', 'high', 'low', 'close', 'entry_price',
        'weekday', 'server_hour', 'month', 'quarter', 'half',
        'h1_atr14', 'h1_atr_pct', 'h1_atr_band', 'h4_atr14', 'h4_atr_pct', 'h4_atr_band',
        'level_context_time',
    ]
    for idx in np.flatnonzero(long_mask.to_numpy()):
        r = x.iloc[idx]
        rows.append({
            **{c: r.get(c) for c in common}, 'm15_index': int(idx), 'direction': 'LONG',
            'level': float(res_level.iloc[idx]), 'raw_level': float(r['res_level']),
            'touch_count': int(r['res_touch_count']), 'level_quality': str(r['res_quality']),
            'first_touch_time': r['res_first_touch_time'], 'last_touch_time': r['res_last_touch_time'],
            'latest_confirm_time': r['res_latest_confirm_time'], 'population': population,
        })
    for idx in np.flatnonzero(short_mask.to_numpy()):
        r = x.iloc[idx]
        rows.append({
            **{c: r.get(c) for c in common}, 'm15_index': int(idx), 'direction': 'SHORT',
            'level': float(sup_level.iloc[idx]), 'raw_level': float(r['sup_level']),
            'touch_count': int(r['sup_touch_count']), 'level_quality': str(r['sup_quality']),
            'first_touch_time': r['sup_first_touch_time'], 'last_touch_time': r['sup_last_touch_time'],
            'latest_confirm_time': r['sup_latest_confirm_time'], 'population': population,
        })
    raw = pd.DataFrame(rows)
    if raw.empty:
        return raw
    raw = raw.sort_values('decision_time').reset_index(drop=True)
    keep: list[int] = []
    recent: dict[str, list[tuple[pd.Timestamp, float]]] = {'LONG': [], 'SHORT': []}
    for i, r in raw.iterrows():
        direction = str(r['direction']); t = pd.Timestamp(r['decision_time']); level = float(r['level']); atr = float(r['h1_atr14'])
        recent[direction] = [(tt, ll) for tt, ll in recent[direction] if t - tt < pd.Timedelta(hours=24)]
        duplicate = any(abs(level - ll) <= .15 * atr for tt, ll in recent[direction])
        if not duplicate:
            keep.append(i); recent[direction].append((t, level))
    z = raw.iloc[keep].copy().reset_index(drop=True)
    z['breakout_id'] = np.arange(1, len(z) + 1)
    return z

def complete_retest_acceptance(breakouts: pd.DataFrame, x: pd.DataFrame, population: str = 'E3_TRUE') -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    retest_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []
    for _, b in breakouts.iterrows():
        i = int(b['m15_index'])
        if i + 8 >= len(x):
            continue
        retest_idx: int | None = None
        invalid_reason: str | None = None
        for j in range(i + 1, min(i + 9, len(x))):
            if pd.Timestamp(x['time'].iloc[j]) != pd.Timestamp(x['time'].iloc[j-1]) + pd.Timedelta(minutes=15):
                invalid_reason = 'GAP_BEFORE_RETEST'; break
            atr = float(x['h1_atr14'].iloc[j]) if np.isfinite(x['h1_atr14'].iloc[j]) else math.nan
            if not np.isfinite(atr):
                invalid_reason = 'NO_CAUSAL_ATR'; break
            level = float(b['level'])
            close = float(x['close'].iloc[j])
            if b['direction'] == 'LONG':
                if close <= level - .05 * atr:
                    invalid_reason = 'CLOSE_BACK_THROUGH_BEFORE_RETEST'; break
                if float(x['low'].iloc[j]) <= level + .05 * atr:
                    retest_idx = j; break
            else:
                if close >= level + .05 * atr:
                    invalid_reason = 'CLOSE_BACK_THROUGH_BEFORE_RETEST'; break
                if float(x['high'].iloc[j]) >= level - .05 * atr:
                    retest_idx = j; break
        if retest_idx is None:
            failed_rows.append({**b.to_dict(), 'failure_stage': 'NO_VALID_FIRST_RETEST', 'failure_reason': invalid_reason or 'TIMEOUT'})
            continue
        rr = {**b.to_dict(), 'retest_m15_index': int(retest_idx),
              'retest_time': x['decision_time'].iloc[retest_idx],
              'retest_open_time': x['time'].iloc[retest_idx],
              'retest_close': float(x['close'].iloc[retest_idx])}
        retest_rows.append(rr)
        accepted_idx: int | None = None
        invalid_reason = None
        for j in range(retest_idx, min(retest_idx + 4, len(x))):
            if j > retest_idx and pd.Timestamp(x['time'].iloc[j]) != pd.Timestamp(x['time'].iloc[j-1]) + pd.Timedelta(minutes=15):
                invalid_reason = 'GAP_BEFORE_ACCEPTANCE'; break
            atr = float(x['h1_atr14'].iloc[j]) if np.isfinite(x['h1_atr14'].iloc[j]) else math.nan
            if not np.isfinite(atr):
                invalid_reason = 'NO_CAUSAL_ATR'; break
            level = float(b['level']); close = float(x['close'].iloc[j]); prev_close = float(x['close'].iloc[j-1])
            if b['direction'] == 'LONG':
                if close <= level - .05 * atr:
                    invalid_reason = 'CLOSE_BACK_THROUGH_BEFORE_ACCEPTANCE'; break
                if close >= level + .05 * atr and close > prev_close:
                    accepted_idx = j; break
            else:
                if close >= level + .05 * atr:
                    invalid_reason = 'CLOSE_BACK_THROUGH_BEFORE_ACCEPTANCE'; break
                if close <= level - .05 * atr and close < prev_close:
                    accepted_idx = j; break
        if accepted_idx is None:
            failed_rows.append({**rr, 'failure_stage': 'NO_VALID_REACCEPTANCE', 'failure_reason': invalid_reason or 'TIMEOUT'})
            continue
        row = x.iloc[accepted_idx]
        event_rows.append({
            **b.to_dict(), 'retest_m15_index': int(retest_idx), 'accept_m15_index': int(accepted_idx),
            'retest_time': x['decision_time'].iloc[retest_idx], 'decision_time': row['decision_time'],
            'entry_time': row['decision_time'], 'entry_price': row['entry_price'],
            'weekday': int(row['weekday']), 'server_hour': int(row['server_hour']),
            'month': row['month'], 'quarter': row['quarter'], 'half': row['half'],
            'h1_atr14': row['h1_atr14'], 'h1_atr_pct': row['h1_atr_pct'], 'h1_atr_band': row['h1_atr_band'],
            'h4_atr14': row['h4_atr14'], 'h4_atr_pct': row['h4_atr_pct'], 'h4_atr_band': row['h4_atr_band'],
            'accept_close': float(row['close']), 'population': population,
        })
    retests = pd.DataFrame(retest_rows)
    events = pd.DataFrame(event_rows)
    failures = pd.DataFrame(failed_rows)
    if events.empty:
        return retests, events, failures
    events = events[events['entry_price'].notna()].sort_values('entry_time').reset_index(drop=True)
    keep = []; active_until = pd.Timestamp.min
    for i, t in enumerate(events['entry_time']):
        if pd.Timestamp(t) >= active_until:
            keep.append(i); active_until = pd.Timestamp(t) + pd.Timedelta(minutes=120)
    events = events.iloc[keep].copy().reset_index(drop=True)
    events['pair_id'] = np.arange(1, len(events) + 1)
    return retests, events, failures
