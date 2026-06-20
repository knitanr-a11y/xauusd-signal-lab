"""Stage260 E2 shared contracts, CSV parsing, source parity, and causal context."""
from __future__ import annotations
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STATUS = "GOLD_V3_260_E2_EVENT_RUNNER_READY_AUDIT_ONLY"
TIMEFRAME_MINUTES = {"m1": 1, "m5": 5, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}
COSTS = (0.0, 1.0, 2.0, 3.0, 5.0)
TP_VALUES = (5.0, 10.0, 15.0, 20.0, 25.0)
SL_VALUES = (5.0, 10.0, 15.0)
HORIZONS = (60, 120, 180, 240)
REGIMES = ("HIGH", "NORMAL", "TRANSITION")

@dataclass(frozen=True)
class E2Config:
    min_penetration_atr: float = 0.05
    reclaim_buffer_atr: float = 0.02
    max_reclaim_minutes: int = 15
    opening_ban_minutes: int = 60
    closing_ban_minutes: int = 60
    base_horizon_minutes: int = 120
    control_near_level_atr: float = 0.25
    session_gap_minutes: int = 15
    atr_window: int = 14
    atr_slow_window: int = 50
    atr_rank_window: int = 1000
    atr_rank_min_periods: int = 200
    random_seed: int = 260

class AuditContractError(RuntimeError):
    """Raised when a non-negotiable audit contract cannot be satisfied."""

def _normalise_col(name: str) -> str:
    return str(name).strip().lower().replace('<', '').replace('>', '').replace(' ', '_')

def _detect_sep(path: Path) -> str:
    first = path.read_text(encoding='utf-8-sig', errors='replace').splitlines()[0]
    return ';' if first.count(';') > first.count(',') else ','

def read_mt5_csv(path: str | Path, timeframe: str) -> pd.DataFrame:
    """Read an MT5 candle CSV without dropping its latest row.

    Supports either a single datetime column or MT5-style DATE/TIME columns.
    The returned ``time`` is always the candle OPEN timestamp.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    if timeframe not in TIMEFRAME_MINUTES:
        raise ValueError(f'unsupported timeframe: {timeframe}')
    df = pd.read_csv(p, sep=_detect_sep(p), encoding='utf-8-sig')
    if df.empty:
        raise AuditContractError(f'empty CSV: {p}')
    df = df.rename(columns={c: _normalise_col(c) for c in df.columns})
    if 'date' in df.columns and 'time' in df.columns:
        time_text = df['time'].astype(str)
        if time_text.str.fullmatch('\\d{1,2}:\\d{2}(:\\d{2})?').fillna(False).mean() > 0.8:
            ts = pd.to_datetime(df['date'].astype(str) + ' ' + time_text, errors='coerce')
        else:
            ts = pd.to_datetime(df['time'], errors='coerce')
    elif 'datetime' in df.columns:
        ts = pd.to_datetime(df['datetime'], errors='coerce')
    elif 'timestamp' in df.columns:
        ts = pd.to_datetime(df['timestamp'], errors='coerce')
    elif 'time' in df.columns:
        ts = pd.to_datetime(df['time'], errors='coerce')
    else:
        raise AuditContractError(f'no supported time column in {p}: {list(df.columns)}')
    aliases = {'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'tickvol': 'tick_volume', 'tick_volume': 'tick_volume', 'vol': 'volume', 'real_volume': 'real_volume'}
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    required = ['open', 'high', 'low', 'close']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise AuditContractError(f'missing OHLC columns in {p}: {missing}')
    out = pd.DataFrame({'time': ts})
    for c in required:
        out[c] = pd.to_numeric(df[c], errors='coerce')
    for c in ('tick_volume', 'volume', 'real_volume', 'spread'):
        if c in df.columns:
            out[c] = pd.to_numeric(df[c], errors='coerce')
    if out[['time', *required]].isna().any().any():
        bad = int(out[['time', *required]].isna().any(axis=1).sum())
        raise AuditContractError(f'{p} contains {bad} invalid required rows')
    out = out.sort_values('time', kind='stable').reset_index(drop=True)
    if out['time'].duplicated().any():
        dup = out.loc[out['time'].duplicated(keep=False), 'time'].head().astype(str).tolist()
        raise AuditContractError(f'duplicate open timestamps in {p}: {dup}')
    if not out['time'].is_monotonic_increasing:
        raise AuditContractError(f'timestamps not increasing in {p}')
    if (out['high'] < out[['open', 'close', 'low']].max(axis=1)).any():
        raise AuditContractError(f'invalid high values in {p}')
    if (out['low'] > out[['open', 'close', 'high']].min(axis=1)).any():
        raise AuditContractError(f'invalid low values in {p}')
    out['source_open_time'] = out['time']
    out['source_close_time'] = out['time'] + pd.to_timedelta(TIMEFRAME_MINUTES[timeframe], unit='m')
    out.attrs['source_path'] = str(p)
    out.attrs['timeframe'] = timeframe
    out.attrs['latest_row_contract'] = 'closed'
    return out

def source_parity(a: pd.DataFrame, b: pd.DataFrame, timeframe: str, tolerance: float=1e-09) -> dict[str, Any]:
    """Compare separately downloaded sources by timestamp, never by row index."""
    left = a[['time', 'open', 'high', 'low', 'close']].copy()
    right = b[['time', 'open', 'high', 'low', 'close']].copy()
    merged = left.merge(right, on='time', how='outer', suffixes=('_a', '_b'), indicator=True)
    both = merged[merged['_merge'] == 'both'].copy()
    diff_counts: dict[str, int] = {}
    max_abs_diff: dict[str, float | None] = {}
    for col in ('open', 'high', 'low', 'close'):
        d = (both[f'{col}_a'] - both[f'{col}_b']).abs()
        diff_counts[col] = int((d > tolerance).sum())
        max_abs_diff[col] = None if d.empty else float(d.max())
    exact_overlap = int(len(both))
    result = {'timeframe': timeframe, 'rows_a': int(len(a)), 'rows_b': int(len(b)), 'exact_timestamp_overlap': exact_overlap, 'only_a': int((merged['_merge'] == 'left_only').sum()), 'only_b': int((merged['_merge'] == 'right_only').sum()), 'overlap_start': None if both.empty else str(both['time'].min()), 'overlap_end': None if both.empty else str(both['time'].max()), 'ohlc_diff_counts': diff_counts, 'max_abs_diff': max_abs_diff, 'pass': exact_overlap > 0 and sum(diff_counts.values()) == 0, 'join_contract': 'timestamp_exact_not_row_index'}
    return result

def build_session_calendar(m1: pd.DataFrame, gap_minutes: int=15) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reconstruct MT5 sessions from M1 gaps greater than ``gap_minutes``."""
    x = m1.copy()
    gaps = x['time'].diff().dt.total_seconds().div(60)
    x['session_id'] = gaps.gt(gap_minutes).fillna(True).cumsum().astype(int)
    x['gap_from_previous_minutes'] = gaps
    rows: list[dict[str, Any]] = []
    prior_durations_by_weekday: dict[int, list[float]] = {i: [] for i in range(7)}
    prior_all: list[float] = []
    groups = list(x.groupby('session_id', sort=True))
    for pos, (sid, g) in enumerate(groups):
        start = g['time'].iloc[0]
        end_open = g['time'].iloc[-1]
        end_close = g['source_close_time'].iloc[-1]
        duration = (end_close - start).total_seconds() / 60
        weekday = int(start.weekday())
        hist = prior_durations_by_weekday[weekday][-20:] or prior_all[-20:]
        expected = float(np.median(hist)) if hist else math.nan
        shortened = bool(not math.isnan(expected) and duration < 0.85 * expected)
        gap_before = None if pos == 0 else (start - groups[pos - 1][1]['source_close_time'].iloc[-1]).total_seconds() / 60
        rows.append({'session_id': int(sid), 'session_start': start, 'session_end_open': end_open, 'session_end_close': end_close, 'bars': int(len(g)), 'duration_minutes': float(duration), 'weekday': weekday, 'server_date_start': start.date().isoformat(), 'server_date_end': end_close.date().isoformat(), 'gap_before_minutes': gap_before, 'expected_duration_from_prior_sessions': expected, 'observed_shortened_session': shortened, 'crosses_server_date': bool(start.date() != end_close.date()), 'session_high': float(g['high'].max()), 'session_low': float(g['low'].min())})
        prior_durations_by_weekday[weekday].append(duration)
        prior_all.append(duration)
    cal = pd.DataFrame(rows)
    cal['previous_session_id'] = cal['session_id'].shift(1)
    cal['previous_session_high'] = cal['session_high'].shift(1)
    cal['previous_session_low'] = cal['session_low'].shift(1)
    cal['previous_session_start'] = cal['session_start'].shift(1)
    cal['previous_session_end_close'] = cal['session_end_close'].shift(1)
    cal['previous_session_shortened'] = cal['observed_shortened_session'].shift(1)
    return (x, cal)

def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df['close'].shift(1)
    return pd.concat([df['high'] - df['low'], (df['high'] - prev_close).abs(), (df['low'] - prev_close).abs()], axis=1).max(axis=1)

def build_h1_context(h1: pd.DataFrame, cfg: E2Config) -> pd.DataFrame:
    x = h1.copy()
    x['h1_tr'] = true_range(x)
    x['h1_atr14'] = x['h1_tr'].rolling(cfg.atr_window, min_periods=cfg.atr_window).mean()
    x['h1_atr50'] = x['h1_tr'].rolling(cfg.atr_slow_window, min_periods=cfg.atr_slow_window).mean()
    x['h1_atr_ratio'] = x['h1_atr14'] / x['h1_atr50'].replace(0, np.nan)
    x['h1_atr_percentile'] = x['h1_atr14'].rolling(cfg.atr_rank_window, min_periods=cfg.atr_rank_min_periods).rank(pct=True)
    x['atr_band'] = pd.cut(x['h1_atr_percentile'], bins=[-np.inf, 0.2, 0.4, 0.6, 0.8, np.inf], labels=['P00_20', 'P20_40', 'P40_60', 'P60_80', 'P80_100']).astype('string')
    return x[['source_close_time', 'h1_atr14', 'h1_atr50', 'h1_atr_ratio', 'h1_atr_percentile', 'atr_band']].dropna(subset=['h1_atr14'])

def load_regime_timeline(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    df = pd.read_csv(p, sep=_detect_sep(p), encoding='utf-8-sig')
    df = df.rename(columns={c: _normalise_col(c) for c in df.columns})
    time_col = next((c for c in ('decision_time', 'time', 'source_close_time') if c in df.columns), None)
    if time_col is None or 'regime' not in df.columns:
        raise AuditContractError('regime timeline needs decision_time/time and regime')
    out = pd.DataFrame({'regime_time': pd.to_datetime(df[time_col], errors='coerce')})
    out['regime'] = df['regime'].astype(str).str.upper().str.strip()
    if 'source_close_time' in df.columns:
        out['regime_source_close_time'] = pd.to_datetime(df['source_close_time'], errors='coerce')
    else:
        out['regime_source_close_time'] = out['regime_time']
    if out.isna().any().any():
        raise AuditContractError('invalid regime timeline rows')
    invalid = ~out['regime'].isin(REGIMES)
    if invalid.any():
        raise AuditContractError(f"unknown regimes: {sorted(out.loc[invalid, 'regime'].unique())}")
    if (out['regime_source_close_time'] > out['regime_time']).any():
        raise AuditContractError('regime source_close_time exceeds regime decision time')
    if out['regime_time'].duplicated().any():
        raise AuditContractError('duplicate regime timestamps')
    return out.sort_values('regime_time').reset_index(drop=True)

def causal_merge_context(m1_sessions: pd.DataFrame, h1_context: pd.DataFrame, regime: pd.DataFrame) -> pd.DataFrame:
    x = m1_sessions.copy()
    x['decision_time'] = x['source_close_time']
    x = pd.merge_asof(x.sort_values('decision_time'), h1_context.sort_values('source_close_time'), left_on='decision_time', right_on='source_close_time', direction='backward', allow_exact_matches=True, suffixes=('', '_h1'))
    x = pd.merge_asof(x.sort_values('decision_time'), regime.sort_values('regime_time'), left_on='decision_time', right_on='regime_time', direction='backward', allow_exact_matches=True)
    if (x['source_close_time_h1'] > x['decision_time']).fillna(False).any():
        raise AuditContractError('HTF lookahead detected')
    if (x['regime_source_close_time'] > x['decision_time']).fillna(False).any():
        raise AuditContractError('regime lookahead detected')
    return x

def attach_session_levels(m1_ctx: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    keep = ['session_id', 'session_start', 'session_end_close', 'duration_minutes', 'expected_duration_from_prior_sessions', 'observed_shortened_session', 'previous_session_id', 'previous_session_high', 'previous_session_low', 'previous_session_start', 'previous_session_end_close', 'previous_session_shortened']
    if len(keep) != len(set(keep)):
        raise AuditContractError('duplicate session keep columns')
    return m1_ctx.merge(calendar[keep], on='session_id', how='left', validate='many_to_one')
