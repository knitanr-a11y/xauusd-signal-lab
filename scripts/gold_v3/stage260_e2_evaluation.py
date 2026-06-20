"""Stage260 E2 full-horizon path, first-touch, cost, and segment evaluation."""
from __future__ import annotations
import math
from typing import Any, Sequence
import numpy as np
import pandas as pd
from stage260_e2_common import COSTS, TP_VALUES

def _directional_values(path: pd.DataFrame, direction: str, entry: float) -> tuple[np.ndarray, np.ndarray]:
    if direction == 'LONG':
        favorable = path['high'].to_numpy(float) - entry
        adverse = entry - path['low'].to_numpy(float)
    elif direction == 'SHORT':
        favorable = entry - path['low'].to_numpy(float)
        adverse = path['high'].to_numpy(float) - entry
    else:
        raise ValueError(direction)
    return (favorable, adverse)

def evaluate_anchor_paths(events: pd.DataFrame, m1: pd.DataFrame, horizon_minutes: int) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    indexed = m1.set_index('time', drop=False)
    rows: list[dict[str, Any]] = []
    for event_id, row in events.reset_index(drop=True).iterrows():
        start = row['entry_time']
        end = start + pd.Timedelta(minutes=horizon_minutes)
        path = indexed.loc[(indexed.index >= start) & (indexed.index < end)].copy()
        if path.empty or path.index[0] != start:
            continue
        expected_bars = horizon_minutes
        complete = len(path) >= expected_bars and path.index[-1] == start + pd.Timedelta(minutes=horizon_minutes - 1)
        if not complete:
            continue
        entry = float(row['entry_price'])
        favorable, adverse = _directional_values(path, str(row['direction']), entry)
        mfe = float(np.max(favorable))
        mae = float(np.max(adverse))
        base: dict[str, Any] = {'event_id': int(event_id), 'pair_id': int(row.get('pair_id', event_id)), 'entry_time': start, 'direction': row['direction'], 'level_side': row.get('level_side'), 'population': row.get('population', 'UNKNOWN'), 'session_id': row.get('session_id'), 'weekday': row.get('weekday', start.weekday()), 'server_hour': row.get('server_hour', start.hour), 'month': row.get('month', start.strftime('%Y-%m')), 'quarter': row.get('quarter', f'{start.year}Q{start.quarter}'), 'half': row.get('half', f'{start.year}H{(1 if start.month <= 6 else 2)}'), 'regime': row.get('regime'), 'entry_price': entry, 'horizon_minutes': int(horizon_minutes), 'mfe': mfe, 'mae': mae, 'mfe_mae_ratio': float(mfe / mae) if mae > 0 else math.inf, 'path_end_time': path.index[-1] + pd.Timedelta(minutes=1), 'path_complete': True, 'recovery_after_adverse_2_5': _recovery_after_adverse(path, row['direction'], entry, 2.5), 'recovery_after_adverse_5': _recovery_after_adverse(path, row['direction'], entry, 5.0)}
        for target in TP_VALUES:
            hit_idx = np.flatnonzero(favorable >= target)
            base[f'reach_{int(target)}'] = bool(len(hit_idx))
            base[f'minutes_to_{int(target)}'] = None if not len(hit_idx) else int(hit_idx[0] + 1)
        rows.append(base)
    return pd.DataFrame(rows)

def _recovery_after_adverse(path: pd.DataFrame, direction: str, entry: float, adverse_trigger: float) -> bool:
    favorable, adverse = _directional_values(path, direction, entry)
    hit = np.flatnonzero(adverse >= adverse_trigger)
    if not len(hit):
        return False
    first = int(hit[0])
    return bool(np.any(favorable[first:] >= 0.0))

def simulate_first_touch(events: pd.DataFrame, m1: pd.DataFrame, horizon_minutes: int, tp: float, sl: float) -> pd.DataFrame:
    """Simulate TP/SL while keeping MFE/MAE evaluation separate.

    Same-M1 TP+SL is resolved as SL. Timeout is marked to the horizon's final
    close. MFE/MAE are not calculated here and are never truncated at exit.
    """
    if events.empty:
        return pd.DataFrame()
    indexed = m1.set_index('time', drop=False)
    rows: list[dict[str, Any]] = []
    for event_id, row in events.reset_index(drop=True).iterrows():
        start = row['entry_time']
        path = indexed.loc[(indexed.index >= start) & (indexed.index < start + pd.Timedelta(minutes=horizon_minutes))]
        if len(path) < horizon_minutes:
            continue
        entry = float(row['entry_price'])
        result = 'TIMEOUT'
        exit_minutes = horizon_minutes
        gross = None
        for pos, (_, bar) in enumerate(path.iterrows(), start=1):
            if row['direction'] == 'LONG':
                tp_hit = bar['high'] >= entry + tp
                sl_hit = bar['low'] <= entry - sl
            else:
                tp_hit = bar['low'] <= entry - tp
                sl_hit = bar['high'] >= entry + sl
            if sl_hit:
                result = 'SL'
                exit_minutes = pos
                gross = -sl
                break
            if tp_hit:
                result = 'TP'
                exit_minutes = pos
                gross = tp
                break
        if gross is None:
            final_close = float(path['close'].iloc[-1])
            gross = final_close - entry if row['direction'] == 'LONG' else entry - final_close
        item = {'event_id': int(event_id), 'pair_id': int(row.get('pair_id', event_id)), 'entry_time': start, 'direction': row['direction'], 'level_side': row.get('level_side'), 'population': row.get('population', 'UNKNOWN'), 'session_id': row.get('session_id'), 'weekday': row.get('weekday', start.weekday()), 'server_hour': row.get('server_hour', start.hour), 'month': row.get('month', start.strftime('%Y-%m')), 'quarter': row.get('quarter', f'{start.year}Q{start.quarter}'), 'half': row.get('half', f'{start.year}H{(1 if start.month <= 6 else 2)}'), 'regime': row.get('regime'), 'horizon_minutes': int(horizon_minutes), 'tp': float(tp), 'sl': float(sl), 'result': result, 'exit_minutes': int(exit_minutes), 'gross_pnl': float(gross)}
        for cost in COSTS:
            item[f'net_pnl_cost{int(cost)}'] = float(gross - cost)
        rows.append(item)
    return pd.DataFrame(rows)

def period_label(ts: pd.Timestamp) -> str:
    if ts.year == 2025 and ts.month <= 6:
        return '2025_H1_DISCOVERY'
    if ts.year == 2025:
        return '2025_H2_SELECTION'
    if ts.year == 2026:
        return '2026_FIXED_VALIDATION'
    return 'OTHER'

def segmented_summaries(df: pd.DataFrame, *, pnl_col: str | None=None, fixed_columns: Sequence[str]=()) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    x = df.copy()
    x['period_contract'] = pd.to_datetime(x['entry_time']).map(period_label)
    dimensions = ('month', 'quarter', 'period_contract', 'direction', 'regime', 'server_hour')
    rows: list[dict[str, Any]] = []
    for dim in dimensions:
        if dim not in x.columns:
            continue
        group_cols = [*fixed_columns, dim]
        for keys, g in x.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            item = dict(zip(group_cols, keys))
            item['segment_type'] = dim
            item['segment_value'] = str(item.pop(dim))
            item.update(summary_stats(g, pnl_col))
            rows.append(item)
    return pd.DataFrame(rows)

def summary_stats(df: pd.DataFrame, pnl_col: str | None=None) -> dict[str, Any]:
    if df.empty:
        return {'count': 0}
    result: dict[str, Any] = {'count': int(len(df))}
    for col in ('mfe', 'mae', 'mfe_mae_ratio'):
        if col in df.columns:
            s = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
            result[f'{col}_mean'] = None if s.empty else float(s.mean())
            result[f'{col}_median'] = None if s.empty else float(s.median())
    for target in TP_VALUES:
        col = f'reach_{int(target)}'
        if col in df.columns:
            result[f'{col}_rate'] = float(df[col].mean())
    for col in ('recovery_after_adverse_2_5', 'recovery_after_adverse_5'):
        if col in df.columns:
            result[f'{col}_rate'] = float(df[col].mean())
    if pnl_col and pnl_col in df.columns:
        pnl = pd.to_numeric(df[pnl_col], errors='coerce').dropna()
        wins = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        result.update({'pnl': float(pnl.sum()), 'expectancy': float(pnl.mean()) if len(pnl) else None, 'pf': float(wins / losses) if losses > 0 else math.inf if wins > 0 else None, 'max_dd': maximum_drawdown(pnl), 'max_losing_streak': maximum_losing_streak(pnl)})
    return result

def maximum_drawdown(pnl: pd.Series) -> float:
    equity = pnl.cumsum()
    peak = equity.cummax().clip(lower=0)
    return float((peak - equity).max()) if len(equity) else 0.0

def maximum_losing_streak(pnl: pd.Series) -> int:
    best = cur = 0
    for value in pnl:
        if value < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)

def paired_bootstrap_difference(event_values: pd.Series, control_values: pd.Series, seed: int=260) -> dict[str, Any]:
    e = pd.to_numeric(event_values, errors='coerce').to_numpy(float)
    c = pd.to_numeric(control_values, errors='coerce').to_numpy(float)
    valid = np.isfinite(e) & np.isfinite(c)
    d = e[valid] - c[valid]
    if len(d) < 5:
        return {'n': int(len(d)), 'mean_difference': None, 'ci95_low': None, 'ci95_high': None}
    rng = np.random.default_rng(seed)
    samples = np.array([rng.choice(d, size=len(d), replace=True).mean() for _ in range(2000)])
    return {'n': int(len(d)), 'mean_difference': float(d.mean()), 'ci95_low': float(np.quantile(samples, 0.025)), 'ci95_high': float(np.quantile(samples, 0.975))}
