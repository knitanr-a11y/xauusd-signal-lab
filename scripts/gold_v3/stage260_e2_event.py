"""Stage260 E2 causal event, matched-control, and placebo construction."""
from __future__ import annotations
import math
from typing import Any
import numpy as np
import pandas as pd
from stage260_e2_common import AuditContractError, E2Config, TP_VALUES

def _event_state_for_side(g: pd.DataFrame, side: str, level_col: str, cfg: E2Config, level_shift_atr: float, require_reclaim: bool) -> dict[str, Any] | None:
    direction = 'LONG' if side == 'LOW' else 'SHORT'
    base_level = float(g[level_col].iloc[0])
    if math.isnan(base_level):
        return None
    state: dict[str, Any] | None = None
    for idx, row in g.iterrows():
        atr = row.get('h1_atr14')
        if pd.isna(atr) or atr <= 0 or pd.isna(row.get('regime')) or pd.isna(row.get('atr_band')):
            continue
        level = base_level + level_shift_atr * float(atr)
        min_pen = cfg.min_penetration_atr * float(atr)
        reclaim_buffer = cfg.reclaim_buffer_atr * float(atr)
        breach = row['low'] <= level - min_pen if side == 'LOW' else row['high'] >= level + min_pen
        outside_close = row['close'] < level if side == 'LOW' else row['close'] > level
        reclaimed = row['close'] >= level + reclaim_buffer if side == 'LOW' else row['close'] <= level - reclaim_buffer
        if state is None:
            if not breach:
                continue
            state = {'first_breach_open_time': row['time'], 'first_breach_decision_time': row['decision_time'], 'outside_close_seen': bool(outside_close), 'outside_bar_count': 1, 'max_penetration': max(0.0, level - row['low']) if side == 'LOW' else max(0.0, row['high'] - level)}
            if not require_reclaim:
                return _make_event(row, idx, state, side, direction, base_level, level, cfg, level_shift_atr, 'BREACH_ONLY')
        else:
            elapsed = (row['decision_time'] - state['first_breach_decision_time']).total_seconds() / 60
            if breach:
                state['outside_bar_count'] += 1
                state['outside_close_seen'] = bool(state['outside_close_seen'] or outside_close)
                pen = max(0.0, level - row['low']) if side == 'LOW' else max(0.0, row['high'] - level)
                state['max_penetration'] = max(float(state['max_penetration']), float(pen))
            if elapsed > cfg.max_reclaim_minutes:
                if reclaimed:
                    state = None
                continue
            persistent = bool(state['outside_close_seen'] or state['outside_bar_count'] >= 2)
            if reclaimed and persistent:
                return _make_event(row, idx, state, side, direction, base_level, level, cfg, level_shift_atr, 'SWEEP_RECLAIM')
    return None

def _make_event(row: pd.Series, row_index: int, state: dict[str, Any], side: str, direction: str, base_level: float, shifted_level: float, cfg: E2Config, level_shift_atr: float, population: str) -> dict[str, Any]:
    reclaim_minutes = (row['decision_time'] - state['first_breach_decision_time']).total_seconds() / 60
    return {'population': population, 'session_id': int(row['session_id']), 'level_side': side, 'direction': direction, 'previous_level': float(base_level), 'effective_level': float(shifted_level), 'level_shift_atr': float(level_shift_atr), 'first_breach_open_time': state['first_breach_open_time'], 'first_breach_decision_time': state['first_breach_decision_time'], 'decision_time': row['decision_time'], 'confirmation_open_time': row['time'], 'confirmation_row_index': int(row_index), 'entry_time': row['decision_time'], 'reclaim_minutes': float(reclaim_minutes), 'outside_close_seen': bool(state['outside_close_seen']), 'outside_bar_count': int(state['outside_bar_count']), 'penetration_usd': float(state['max_penetration']), 'penetration_atr': float(state['max_penetration'] / row['h1_atr14']), 'h1_atr14': float(row['h1_atr14']), 'h1_atr50': float(row['h1_atr50']) if pd.notna(row['h1_atr50']) else math.nan, 'h1_atr_ratio': float(row['h1_atr_ratio']) if pd.notna(row['h1_atr_ratio']) else math.nan, 'h1_atr_percentile': float(row['h1_atr_percentile']) if pd.notna(row['h1_atr_percentile']) else math.nan, 'atr_band': str(row['atr_band']), 'regime': str(row['regime']), 'session_start': row['session_start'], 'session_end_close_observed': row['session_end_close'], 'expected_session_duration_minutes': row['expected_duration_from_prior_sessions'], 'observed_shortened_session': bool(row['observed_shortened_session']), 'previous_session_shortened': bool(row['previous_session_shortened']) if pd.notna(row['previous_session_shortened']) else False, 'weekday': int(row['decision_time'].weekday()), 'server_hour': int(row['decision_time'].hour), 'server_minute': int(row['decision_time'].minute), 'month': row['decision_time'].strftime('%Y-%m'), 'quarter': f"{row['decision_time'].year}Q{row['decision_time'].quarter}", 'half': f"{row['decision_time'].year}H{(1 if row['decision_time'].month <= 6 else 2)}", 'definition_min_penetration_atr': cfg.min_penetration_atr, 'definition_reclaim_buffer_atr': cfg.reclaim_buffer_atr, 'definition_max_reclaim_minutes': cfg.max_reclaim_minutes}

def detect_e2_events(m1: pd.DataFrame, cfg: E2Config, level_shift_atr: float=0.0, require_reclaim: bool=True) -> pd.DataFrame:
    events: list[dict[str, Any]] = []
    for _, raw_g in m1.groupby('session_id', sort=True):
        if raw_g['previous_session_high'].isna().all():
            continue
        session_start = raw_g['session_start'].iloc[0]
        safe_start = session_start + pd.Timedelta(minutes=cfg.opening_ban_minutes)
        g = raw_g[raw_g['time'] >= safe_start].copy()
        if g.empty:
            continue
        for side, level_col in (('LOW', 'previous_session_low'), ('HIGH', 'previous_session_high')):
            event = _event_state_for_side(g, side, level_col, cfg, level_shift_atr, require_reclaim)
            if event is not None:
                events.append(event)
    out = pd.DataFrame(events)
    if out.empty:
        return out
    return out.sort_values(['entry_time', 'direction'], kind='stable').reset_index(drop=True)

def add_entry_prices(events: pd.DataFrame, m1: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    lookup = m1[['time', 'open']].rename(columns={'time': 'entry_time', 'open': 'entry_price'})
    out = events.merge(lookup, on='entry_time', how='left', validate='many_to_one')
    out['entry_available'] = out['entry_price'].notna()
    return out

def add_live_safe_flags(events: pd.DataFrame, cfg: E2Config, horizon_minutes: int) -> pd.DataFrame:
    out = events.copy()
    if out.empty:
        return out
    required = {'entry_time', 'session_start', 'session_end_close_observed', 'expected_session_duration_minutes', 'entry_available'}
    missing = sorted(required - set(out.columns))
    if missing:
        raise AuditContractError(f'time-gate input missing columns: {missing}')
    out['horizon_minutes'] = int(horizon_minutes)
    out['planned_horizon_end'] = out['entry_time'] + pd.to_timedelta(horizon_minutes, unit='m')
    out['crosses_mt5_date_change'] = out['entry_time'].dt.date != out['planned_horizon_end'].dt.date
    out['crosses_weekend'] = (out['entry_time'].dt.weekday >= 4) & (out['planned_horizon_end'].dt.weekday != out['entry_time'].dt.weekday)
    expected_end = out['session_start'] + pd.to_timedelta(out['expected_session_duration_minutes'], unit='m')
    expected_safe_end = expected_end - pd.to_timedelta(cfg.closing_ban_minutes, unit='m')
    out['expected_safe_end_from_prior_sessions'] = expected_safe_end
    out['known_schedule_available'] = out['expected_session_duration_minutes'].notna()
    out['crosses_expected_safe_end'] = out['known_schedule_available'] & (out['planned_horizon_end'] > expected_safe_end)
    observed_safe_end = out['session_end_close_observed'] - pd.to_timedelta(cfg.closing_ban_minutes, unit='m')
    out['crosses_observed_safe_end'] = out['planned_horizon_end'] > observed_safe_end
    out['live_reproducible_time_gate'] = out['entry_available'] & out['known_schedule_available'] & ~out['crosses_mt5_date_change'] & ~out['crosses_weekend'] & ~out['crosses_expected_safe_end']
    out['outcome_path_complete'] = ~out['crosses_observed_safe_end']
    return out

def filter_live_evaluable(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    required = {'live_reproducible_time_gate', 'outcome_path_complete'}
    missing = sorted(required - set(events.columns))
    if missing:
        raise AuditContractError(f'evaluable filter missing columns: {missing}')
    return events[events['live_reproducible_time_gate'] & events['outcome_path_complete']].copy()

def dedup_fixed_horizon(events: pd.DataFrame, horizon_minutes: int) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    kept: list[int] = []
    active_until: pd.Timestamp | None = None
    for idx, row in events.sort_values('entry_time').iterrows():
        if active_until is not None and row['entry_time'] < active_until:
            continue
        kept.append(idx)
        active_until = row['entry_time'] + pd.Timedelta(minutes=horizon_minutes)
    return events.loc[kept].sort_values('entry_time').reset_index(drop=True)

def build_control_pool(m1: pd.DataFrame, events: pd.DataFrame, cfg: E2Config) -> pd.DataFrame:
    """Create causal non-event anchors near the corresponding previous level."""
    event_keys = set(zip(events.get('entry_time', []), events.get('direction', [])))
    rows: list[dict[str, Any]] = []
    for idx, row in m1.iterrows():
        if pd.isna(row.get('h1_atr14')) or row['h1_atr14'] <= 0 or pd.isna(row.get('regime')):
            continue
        if row['time'] < row['session_start'] + pd.Timedelta(minutes=cfg.opening_ban_minutes):
            continue
        next_time = row['decision_time']
        for side, direction, level_col in (('LOW', 'LONG', 'previous_session_low'), ('HIGH', 'SHORT', 'previous_session_high')):
            if (next_time, direction) in event_keys or pd.isna(row[level_col]):
                continue
            level = float(row[level_col])
            distance = abs(float(row['close']) - level) / float(row['h1_atr14'])
            if distance > cfg.control_near_level_atr:
                continue
            currently_outside = row['close'] < level if side == 'LOW' else row['close'] > level
            if currently_outside:
                continue
            rows.append({'population': 'MATCHED_CONTROL_POOL', 'session_id': int(row['session_id']), 'level_side': side, 'direction': direction, 'decision_time': next_time, 'entry_time': next_time, 'confirmation_row_index': int(idx), 'previous_level': level, 'effective_level': level, 'distance_to_level_atr': float(distance), 'h1_atr14': float(row['h1_atr14']), 'h1_atr_percentile': float(row['h1_atr_percentile']), 'atr_band': str(row['atr_band']), 'regime': str(row['regime']), 'session_start': row['session_start'], 'session_end_close_observed': row['session_end_close'], 'expected_session_duration_minutes': row['expected_duration_from_prior_sessions'], 'observed_shortened_session': bool(row['observed_shortened_session']), 'weekday': int(next_time.weekday()), 'server_hour': int(next_time.hour), 'server_minute': int(next_time.minute), 'month': next_time.strftime('%Y-%m'), 'quarter': f'{next_time.year}Q{next_time.quarter}', 'half': f'{next_time.year}H{(1 if next_time.month <= 6 else 2)}'})
    pool = pd.DataFrame(rows)
    if pool.empty:
        return pool
    return add_entry_prices(pool, m1)

def match_controls(events: pd.DataFrame, pool: pd.DataFrame, random_seed: int=260) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One-to-one matching without replacement on the locked exact strata."""
    if events.empty or pool.empty:
        return (pd.DataFrame(), events.copy())
    rng = np.random.default_rng(random_seed)
    available = set(pool.index.tolist())
    matches: list[dict[str, Any]] = []
    unmatched: list[int] = []
    for event_id, event in events.reset_index(drop=True).iterrows():
        candidates = pool.loc[list(available)] if available else pool.iloc[0:0]
        candidates = candidates[(candidates['weekday'] == event['weekday']) & (candidates['server_hour'] == event['server_hour']) & (candidates['atr_band'] == event['atr_band']) & (candidates['regime'] == event['regime']) & (candidates['direction'] == event['direction']) & (candidates['quarter'] == event['quarter'])].copy()
        if candidates.empty:
            unmatched.append(event_id)
            continue
        target_distance = abs(float(event.get('penetration_atr', 0.0)))
        candidates['date_distance_days'] = (candidates['entry_time'] - event['entry_time']).abs().dt.total_seconds() / 86400
        candidates['atr_distance'] = (candidates['h1_atr_percentile'] - event['h1_atr_percentile']).abs()
        candidates['level_distance_gap'] = (candidates['distance_to_level_atr'] - target_distance).abs()
        candidates['random_tie'] = rng.random(len(candidates))
        chosen_idx = candidates.sort_values(['date_distance_days', 'atr_distance', 'level_distance_gap', 'random_tie'], kind='stable').index[0]
        available.remove(chosen_idx)
        chosen = pool.loc[chosen_idx].to_dict()
        chosen.update({'event_id': int(event_id), 'pair_id': int(event.get('pair_id', event_id)), 'matched_event_entry_time': event['entry_time'], 'matched_control_index': int(chosen_idx)})
        matches.append(chosen)
    unmatched_df = events.reset_index(drop=True).loc[unmatched].copy() if unmatched else events.iloc[0:0].copy()
    return (pd.DataFrame(matches), unmatched_df)

def shifted_time_placebo(events: pd.DataFrame, m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    out = events.copy()
    out['population'] = f'PLACEBO_TIME_{minutes:+d}M'
    out['entry_time'] = out['entry_time'] + pd.to_timedelta(minutes, unit='m')
    out['decision_time'] = out['entry_time']
    out = out.drop(columns=['entry_price', 'entry_available'], errors='ignore')
    return add_entry_prices(out, m1)

def reverse_direction_placebo(events: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    out['population'] = 'PLACEBO_DIRECTION_REVERSED'
    out['direction'] = out['direction'].map({'LONG': 'SHORT', 'SHORT': 'LONG'})
    out['level_side'] = out['level_side'].map({'LOW': 'HIGH', 'HIGH': 'LOW'})
    return out

def random_flag_placebo(events: pd.DataFrame, pool: pd.DataFrame, seed: int) -> pd.DataFrame:
    if events.empty or pool.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    chosen: list[pd.DataFrame] = []
    for keys, g in events.groupby(['half', 'direction'], dropna=False):
        candidates = pool[(pool['half'] == keys[0]) & (pool['direction'] == keys[1])]
        if candidates.empty:
            continue
        n = min(len(g), len(candidates))
        idx = rng.choice(candidates.index.to_numpy(), size=n, replace=False)
        chosen.append(candidates.loc[idx])
    if not chosen:
        return pd.DataFrame()
    out = pd.concat(chosen, ignore_index=True)
    out['population'] = 'PLACEBO_RANDOM_FLAG_EQUAL_COUNT'
    return out

def _matched_placebo(events: pd.DataFrame, pool: pd.DataFrame, *, population_name: str, seed: int, weekday_mode: str='same', regime_mode: str='same', random_date: bool=False) -> pd.DataFrame:
    """Build a one-to-one placebo anchor set from the causal eligible pool."""
    if events.empty or pool.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    available = set(pool.index.tolist())
    chosen_rows: list[dict[str, Any]] = []
    for fallback_id, event in events.reset_index(drop=True).iterrows():
        candidates = pool.loc[list(available)] if available else pool.iloc[0:0]
        mask = (candidates['server_hour'] == event['server_hour']) & (candidates['atr_band'] == event['atr_band']) & (candidates['direction'] == event['direction']) & (candidates['quarter'] == event['quarter'])
        if weekday_mode == 'same':
            mask &= candidates['weekday'] == event['weekday']
        elif weekday_mode == 'different':
            mask &= candidates['weekday'] != event['weekday']
        else:
            raise ValueError(weekday_mode)
        if regime_mode == 'same':
            mask &= candidates['regime'] == event['regime']
        elif regime_mode == 'different':
            mask &= candidates['regime'] != event['regime']
        else:
            raise ValueError(regime_mode)
        candidates = candidates[mask].copy()
        if candidates.empty:
            continue
        candidates['random_key'] = rng.random(len(candidates))
        if random_date:
            chosen_idx = candidates.sort_values('random_key', kind='stable').index[0]
        else:
            candidates['date_distance_days'] = (candidates['entry_time'] - event['entry_time']).abs().dt.total_seconds() / 86400
            chosen_idx = candidates.sort_values(['date_distance_days', 'random_key'], kind='stable').index[0]
        available.remove(chosen_idx)
        item = pool.loc[chosen_idx].to_dict()
        item['population'] = population_name
        item['pair_id'] = int(event.get('pair_id', fallback_id))
        chosen_rows.append(item)
    return pd.DataFrame(chosen_rows)

def randomized_date_placebo(events: pd.DataFrame, pool: pd.DataFrame, seed: int) -> pd.DataFrame:
    return _matched_placebo(events, pool, population_name='PLACEBO_DATE_RANDOMIZED', seed=seed, weekday_mode='same', regime_mode='same', random_date=True)

def weekday_swap_placebo(events: pd.DataFrame, pool: pd.DataFrame, seed: int) -> pd.DataFrame:
    return _matched_placebo(events, pool, population_name='PLACEBO_WEEKDAY_SWAPPED', seed=seed, weekday_mode='different', regime_mode='same', random_date=False)

def wrong_regime_placebo(events: pd.DataFrame, pool: pd.DataFrame, seed: int) -> pd.DataFrame:
    return _matched_placebo(events, pool, population_name='PLACEBO_WRONG_REGIME', seed=seed, weekday_mode='same', regime_mode='different', random_date=False)
