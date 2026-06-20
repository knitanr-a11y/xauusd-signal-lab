from __future__ import annotations

from bisect import bisect_left, bisect_right, insort
from pathlib import Path
import math
from typing import Iterable

import numpy as np
import pandas as pd

TF_MIN = {'m1': 1, 'm5': 5, 'm15': 15, 'h1': 60, 'h4': 240}
HORIZONS = [60, 120, 180, 240]
TPS = [5.0, 10.0, 15.0, 20.0, 25.0]
SLS = [5.0, 10.0, 15.0]
COSTS = [0.0, 1.0, 2.0, 3.0, 5.0]
RNG = np.random.default_rng(2600)


def detect_sep(path: Path) -> str:
    first = path.read_text(encoding='utf-8-sig', errors='replace').splitlines()[0]
    return ';' if first.count(';') > first.count(',') else ','


def read_ohlc(path: Path, tf: str, source: str) -> pd.DataFrame:
    sep = detect_sep(path)
    d = pd.read_csv(path, sep=sep, encoding='utf-8-sig')
    d.columns = [str(c).strip().lower() for c in d.columns]
    required = {'time', 'open', 'high', 'low', 'close'}
    missing = required - set(d.columns)
    if missing:
        raise ValueError(f'{path}: missing {sorted(missing)}')
    d['time'] = pd.to_datetime(d['time'], errors='raise')
    for c in ['open', 'high', 'low', 'close']:
        d[c] = pd.to_numeric(d[c], errors='raise')
    d = d.sort_values('time').drop_duplicates('time', keep='last').reset_index(drop=True)
    bad = (d['high'] < d[['open', 'close', 'low']].max(axis=1)) | (d['low'] > d[['open', 'close', 'high']].min(axis=1))
    if bad.any():
        raise ValueError(f'{path}: malformed OHLC rows={int(bad.sum())}')
    d['source'] = source
    d['source_close_time'] = d['time'] + pd.to_timedelta(TF_MIN[tf], unit='m')
    return d


def combine_tf(base: Path, tf: str) -> pd.DataFrame:
    a = read_ohlc(base / f'gold#_{tf}.csv', tf, 'gold#')
    b = read_ohlc(base / f'goldsharp_{tf}.csv', tf, 'goldsharp')
    a['_priority'] = 0
    b['_priority'] = 1
    d = pd.concat([a, b], ignore_index=True)
    d = d.sort_values(['time', '_priority']).drop_duplicates('time', keep='first').drop(columns='_priority').reset_index(drop=True)
    if d['time'].duplicated().any() or not d['time'].is_monotonic_increasing:
        raise AssertionError(f'{tf}: timestamp contract failed')
    return d


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
                    raise AssertionError('causal percentile history removal mismatch')
                sorted_hist.pop(j)
        if q_start > 4096:
            queue = queue[q_start:]
            q_start = 0
    return out


def true_range(d: pd.DataFrame) -> pd.Series:
    pc = d['close'].shift(1)
    return pd.concat([
        d['high'] - d['low'],
        (d['high'] - pc).abs(),
        (d['low'] - pc).abs(),
    ], axis=1).max(axis=1)


def atr_context(d: pd.DataFrame, prefix: str, pct_window: int, pct_min: int) -> pd.DataFrame:
    tr = true_range(d)
    atr14 = tr.rolling(14, min_periods=14).mean()
    atr50 = tr.rolling(50, min_periods=50).mean()
    pct = causal_percentile(atr14.to_numpy(), pct_window, pct_min)
    out = pd.DataFrame({
        'source_close_time': d['source_close_time'],
        f'{prefix}_atr14': atr14,
        f'{prefix}_atr50': atr50,
        f'{prefix}_atr_ratio': atr14 / atr50,
        f'{prefix}_atr_pct': pct,
    })
    out[f'{prefix}_atr_band'] = pd.cut(
        out[f'{prefix}_atr_pct'], [-np.inf, .2, .4, .6, .8, np.inf],
        labels=['P00_20', 'P20_40', 'P40_60', 'P60_80', 'P80_100'],
    ).astype('string')
    return out.dropna(subset=[f'{prefix}_atr14', f'{prefix}_atr_pct']).reset_index(drop=True)


def event_distance_mask(times: pd.Series, event_times: np.ndarray, minutes: int = 30) -> np.ndarray:
    if len(event_times) == 0:
        return np.zeros(len(times), dtype=bool)
    ev = np.sort(event_times.astype('datetime64[ns]'))
    t = times.to_numpy(dtype='datetime64[ns]')
    idx = np.searchsorted(ev, t)
    near = np.zeros(len(t), dtype=bool)
    tol = np.timedelta64(minutes, 'm')
    left_ok = idx > 0
    near[left_ok] |= (t[left_ok] - ev[idx[left_ok] - 1]) <= tol
    right_ok = idx < len(ev)
    near[right_ok] |= (ev[idx[right_ok]] - t[right_ok]) <= tol
    return near


def evaluate_population(pop: pd.DataFrame, name: str, m1: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if pop.empty:
        return pd.DataFrame(), pd.DataFrame()
    highs = m1['high'].to_numpy(float)
    lows = m1['low'].to_numpy(float)
    closes = m1['close'].to_numpy(float)
    pos = {pd.Timestamp(t): i for i, t in enumerate(m1['time'])}
    path_rows: list[dict] = []
    grid_rows: list[dict] = []
    for _, r in pop.iterrows():
        st = pd.Timestamp(r.entry_time)
        p = pos.get(st)
        if p is None or not np.isfinite(float(r.entry_price)):
            continue
        direction = str(r.direction)
        ep = float(r.entry_price)
        for hor in HORIZONS:
            q = p + hor
            if q > len(m1):
                continue
            if pd.Timestamp(m1['time'].iloc[q - 1]) != st + pd.Timedelta(minutes=hor - 1):
                continue
            hi = highs[p:q]; lo = lows[p:q]; cl = closes[p:q]
            if direction == 'LONG':
                fav = hi - ep; adv = ep - lo; timeout = float(cl[-1] - ep)
            else:
                fav = ep - lo; adv = hi - ep; timeout = float(ep - cl[-1])
            base = {
                'population_name': name, 'pair_id': int(r.get('pair_id', 0)),
                'entry_time': st, 'direction': direction, 'half': r.get('half', ''),
                'quarter': r.get('quarter', ''), 'month': r.get('month', ''),
                'server_hour': int(r.get('server_hour', -1)),
                'h1_atr_band': str(r.get('h1_atr_band', '')),
                'h4_atr_band': str(r.get('h4_atr_band', '')),
                'level_quality': str(r.get('level_quality', '')),
                'horizon': hor, 'mfe': float(np.max(fav)), 'mae': float(np.max(adv)),
                'mfe_mae_ratio': float(np.max(fav) / np.max(adv)) if np.max(adv) > 0 else np.inf,
            }
            for t in TPS:
                hit = np.flatnonzero(fav >= t)
                base[f'reach_{int(t)}'] = bool(len(hit))
                base[f'time_to_{int(t)}'] = int(hit[0] + 1) if len(hit) else np.nan
            for threshold in [2.5, 5.0]:
                hit = np.flatnonzero(adv >= threshold)
                if len(hit):
                    if direction == 'LONG':
                        recovered = np.any(highs[p + hit[0]:q] >= ep)
                    else:
                        recovered = np.any(lows[p + hit[0]:q] <= ep)
                    base[f'recover_after_{threshold:g}'] = bool(recovered)
                else:
                    base[f'recover_after_{threshold:g}'] = False
            path_rows.append(base)
            tp_first = {tp: (int(np.flatnonzero(fav >= tp)[0]) if np.any(fav >= tp) else hor + 1) for tp in TPS}
            sl_first = {sl: (int(np.flatnonzero(adv >= sl)[0]) if np.any(adv >= sl) else hor + 1) for sl in SLS}
            for tp in TPS:
                for sl in SLS:
                    ti = tp_first[tp]; si = sl_first[sl]
                    if si <= ti and si <= hor:
                        result = 'SL'; gross = -sl; exit_min = si + 1
                    elif ti < si and ti <= hor:
                        result = 'TP'; gross = tp; exit_min = ti + 1
                    else:
                        result = 'TIMEOUT'; gross = timeout; exit_min = hor
                    z = {
                        'population_name': name, 'pair_id': int(r.get('pair_id', 0)),
                        'entry_time': st, 'direction': direction, 'half': r.get('half', ''),
                        'quarter': r.get('quarter', ''), 'month': r.get('month', ''),
                        'server_hour': int(r.get('server_hour', -1)),
                        'h1_atr_band': str(r.get('h1_atr_band', '')),
                        'h4_atr_band': str(r.get('h4_atr_band', '')),
                        'level_quality': str(r.get('level_quality', '')),
                        'horizon': hor, 'tp': tp, 'sl': sl, 'result': result,
                        'exit_min': int(exit_min), 'gross_pnl': float(gross),
                    }
                    for cost in COSTS:
                        z[f'net_cost{int(cost)}'] = float(gross - cost)
                    grid_rows.append(z)
    return pd.DataFrame(path_rows), pd.DataFrame(grid_rows)


def pf(s: pd.Series) -> float:
    wins = float(s[s > 0].sum()); losses = float(-s[s < 0].sum())
    if losses > 0:
        return wins / losses
    return math.inf if wins > 0 else math.nan


def max_dd(s: pd.Series) -> float:
    if len(s) == 0:
        return 0.0
    eq = s.cumsum().to_numpy(float)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    return float(np.max(peak - eq))


def max_losing_streak(s: pd.Series) -> int:
    best = cur = 0
    for v in s:
        cur = cur + 1 if v < 0 else 0
        best = max(best, cur)
    return int(best)


def summarize_paths(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if paths.empty:
        return pd.DataFrame()
    for key, g in paths.groupby(['population_name', 'horizon']):
        z = {'population_name': key[0], 'horizon': key[1], 'count': len(g),
             'mfe_mean': g.mfe.mean(), 'mfe_median': g.mfe.median(),
             'mae_mean': g.mae.mean(), 'mae_median': g.mae.median(),
             'ratio_median': g.mfe_mae_ratio.replace(np.inf, np.nan).median()}
        for t in TPS:
            z[f'reach_{int(t)}_rate'] = g[f'reach_{int(t)}'].mean()
            z[f'time_to_{int(t)}_median'] = g.loc[g[f'reach_{int(t)}'], f'time_to_{int(t)}'].median()
        rows.append(z)
    return pd.DataFrame(rows)


def summarize_grid(grid: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if grid.empty:
        return pd.DataFrame()
    for key, g in grid.groupby(['population_name', 'horizon', 'tp', 'sl']):
        for cost in COSTS:
            s = g[f'net_cost{int(cost)}']
            rows.append({'population_name': key[0], 'horizon': key[1], 'tp': key[2], 'sl': key[3],
                         'cost': cost, 'count': len(g), 'pnl': s.sum(), 'expectancy': s.mean(),
                         'pf': pf(s), 'max_dd': max_dd(s), 'max_losing_streak': max_losing_streak(s),
                         'win_rate': (s > 0).mean()})
    return pd.DataFrame(rows)


def dedup_custom_population(pop: pd.DataFrame, minutes: int = 120) -> pd.DataFrame:
    if pop.empty:
        return pop.copy()
    pop = pop.sort_values('entry_time').reset_index(drop=True)
    keep = []; active_until = pd.Timestamp.min
    for i, t in enumerate(pop.entry_time):
        if pd.Timestamp(t) >= active_until:
            keep.append(i); active_until = pd.Timestamp(t) + pd.Timedelta(minutes=minutes)
    z = pop.iloc[keep].copy().reset_index(drop=True)
    z['pair_id'] = np.arange(1, len(z) + 1)
    return z


def shift_events(events: pd.DataFrame, minutes: int, m1: pd.DataFrame, name: str) -> pd.DataFrame:
    z = events.copy(); z['entry_time'] = z['entry_time'] + pd.Timedelta(minutes=minutes)
    price_map = m1.set_index('time')['open']; z['entry_price'] = z['entry_time'].map(price_map)
    z = z[z.entry_price.notna()].copy(); z['decision_time'] = z['entry_time']; z['population'] = name
    return dedup_custom_population(z)


def reverse_events(events: pd.DataFrame, name: str) -> pd.DataFrame:
    z = events.copy(); z['direction'] = np.where(z.direction.eq('LONG'), 'SHORT', 'LONG'); z['population'] = name
    return z


def weekday_shift(events: pd.DataFrame, m1: pd.DataFrame, name: str) -> pd.DataFrame:
    z = events.copy(); z['entry_time'] = z['entry_time'] + pd.Timedelta(days=1)
    price_map = m1.set_index('time')['open']; z['entry_price'] = z['entry_time'].map(price_map)
    z = z[z.entry_price.notna()].copy(); z['decision_time'] = z['entry_time']
    z['weekday'] = z['entry_time'].dt.weekday; z['server_hour'] = z['entry_time'].dt.hour
    z['month'] = z['entry_time'].dt.strftime('%Y-%m')
    z['quarter'] = z['entry_time'].dt.year.astype(str) + 'Q' + z['entry_time'].dt.quarter.astype(str)
    z['half'] = z['entry_time'].dt.year.astype(str) + 'H' + np.where(z['entry_time'].dt.month <= 6, '1', '2')
    z['population'] = name
    return dedup_custom_population(z)


def paired_bootstrap(event_paths: pd.DataFrame, control_paths: pd.DataFrame, horizon: int = 120,
                     n_boot: int = 5000, seed: int = 2600) -> pd.DataFrame:
    e = event_paths[event_paths.horizon.eq(horizon)]
    c = control_paths[control_paths.horizon.eq(horizon)]
    p = e.merge(c, on=['pair_id', 'horizon'], suffixes=('_event', '_control'))
    rows = []
    if p.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    for metric in ['mfe', 'mae']:
        diff = p[f'{metric}_event'].to_numpy() - p[f'{metric}_control'].to_numpy()
        boots = np.empty(n_boot)
        for i in range(n_boot):
            boots[i] = rng.choice(diff, size=len(diff), replace=True).mean()
        rows.append({'metric': metric, 'horizon': horizon, 'pairs': len(diff),
                     'mean_difference_event_minus_control': diff.mean(),
                     'ci_low_2_5': np.quantile(boots, .025), 'ci_high_97_5': np.quantile(boots, .975)})
    return pd.DataFrame(rows)
