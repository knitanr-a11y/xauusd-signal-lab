#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_177_OHLC_ONLY_REBUILD_SEARCH_AUDIT_ONLY'
BENCHMARK_PF = 2.237

# Search thresholds. These are audit/search thresholds only.
MIN_TRAIN_N = 50
MIN_TEST_N = 15
MIN_FULL_N = 100
PRELIM_MIN_PF = 1.00
STRICT_MIN_PF = 1.35

PAIR_BASE_LIMIT = 140
PAIR_RESULT_LIMIT_PER_PROFILE = 250
SINGLE_RESULT_LIMIT_PER_PROFILE = 200
NEAR_MISS_LIMIT_PER_PROFILE = 250


def progress(msg: str) -> None:
    print(f'[177 progress] {msg}', flush=True)


def safe_float(x: Any, default: float = math.nan) -> float:
    try:
        y = float(x)
        return y if math.isfinite(y) else default
    except Exception:
        return default


def normalize_col(c: Any) -> str:
    s = str(c).strip()
    s = s.strip('<>').strip()
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    aliases = {
        'tickvol': 'tick_volume',
        'tick_vol': 'tick_volume',
        'tick_volume': 'tick_volume',
        'vol': 'tick_volume',
        'volume': 'tick_volume',
        'real_volume': 'real_volume',
        'date': 'date',
        'time': 'time',
        'datetime': 'time',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
    }
    return aliases.get(s, s)


def add_dt_column(df: pd.DataFrame) -> pd.DataFrame:
    cols = set(df.columns)
    if 'dt' in cols:
        df['dt'] = pd.to_datetime(df['dt'], errors='coerce')
    elif 'entry_dt' in cols:
        df['dt'] = pd.to_datetime(df['entry_dt'], errors='coerce')
    elif 'datetime' in cols:
        df['dt'] = pd.to_datetime(df['datetime'], errors='coerce')
    elif 'time' in cols and 'date' in cols:
        df['dt'] = pd.to_datetime(df['date'].astype(str).str.strip() + ' ' + df['time'].astype(str).str.strip(), errors='coerce')
    elif 'time' in cols:
        df['dt'] = pd.to_datetime(df['time'], errors='coerce')
    return df


def read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ['utf-8-sig', 'utf-8', 'cp932']:
        for sep in [',', ';', '\t']:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
                if len(df.columns) <= 1:
                    continue
                df.columns = [normalize_col(c) for c in df.columns]
                df = add_dt_column(df)
                text_cols = {'time', 'date', 'entry_dt', 'dt', 'symbol', 'exported_at', 'is_closed'}
                for c in df.columns:
                    if c in text_cols:
                        continue
                    try:
                        df[c] = pd.to_numeric(df[c], errors='raise')
                    except Exception:
                        pass
                if 'dt' in df.columns:
                    df = df[df['dt'].notna()].drop_duplicates('dt').sort_values('dt').reset_index(drop=True)
                    return df
                return df
            except Exception:
                pass
    return pd.DataFrame()


def summarize_raw(tf: str, kind: str, path: Path, df: pd.DataFrame) -> dict[str, Any]:
    row: dict[str, Any] = {
        'tf': tf,
        'source': kind,
        'path': str(path),
        'exists': bool(path.exists()),
        'rows': int(len(df)) if not df.empty else 0,
        'has_dt': bool('dt' in df.columns) if not df.empty else False,
        'has_ohlc': bool({'open', 'high', 'low', 'close'}.issubset(df.columns)) if not df.empty else False,
        'min_dt': '',
        'max_dt': '',
        'pre2025_rows': 0,
        'y2025_rows': 0,
        'y2026plus_rows': 0,
    }
    if not df.empty and 'dt' in df.columns:
        row['min_dt'] = str(df['dt'].min())
        row['max_dt'] = str(df['dt'].max())
        row['pre2025_rows'] = int((df['dt'] < pd.Timestamp('2025-01-01')).sum())
        row['y2025_rows'] = int(((df['dt'] >= pd.Timestamp('2025-01-01')) & (df['dt'] < pd.Timestamp('2026-01-01'))).sum())
        row['y2026plus_rows'] = int((df['dt'] >= pd.Timestamp('2026-01-01')).sum())
    return row


def combine(tf: str, data_dir: Path) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    live_path = data_dir / f'goldsharp_{tf}.csv'
    old_path = data_dir / f'gold#_{tf}.csv'
    live = read_csv_any(live_path)
    old = read_csv_any(old_path)
    diag = [summarize_raw(tf, 'goldsharp', live_path, live), summarize_raw(tf, 'gold#', old_path, old)]

    if live.empty and old.empty:
        return pd.DataFrame(), diag

    parts: list[pd.DataFrame] = []
    # Contract for Stage177:
    # - 2025 uses gold#_*.
    # - 2026+ uses goldsharp_*.
    # - pre-2025 goldsharp_* is warm-up only for indicators.
    if not live.empty and 'dt' in live.columns:
        parts.append(live[live['dt'] < pd.Timestamp('2025-01-01')])
    if not old.empty and 'dt' in old.columns:
        parts.append(old[(old['dt'] >= pd.Timestamp('2025-01-01')) & (old['dt'] < pd.Timestamp('2026-01-01'))])
    if not live.empty and 'dt' in live.columns:
        parts.append(live[live['dt'] >= pd.Timestamp('2026-01-01')])
    if not parts:
        return pd.DataFrame(), diag
    out = pd.concat(parts, ignore_index=True)
    if out.empty:
        return pd.DataFrame(), diag
    return out.drop_duplicates('dt', keep='last').sort_values('dt').reset_index(drop=True), diag


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def rsi_sma(close: pd.Series, p: int = 14) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    ag = g.rolling(p, min_periods=p).mean()
    al = l.rolling(p, min_periods=p).mean()
    rs = ag / al.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(al.ne(0), 100.0)


def rsi_wilder(close: pd.Series, p: int = 14) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    ag = g.ewm(alpha=1 / p, adjust=False, min_periods=p).mean()
    al = l.ewm(alpha=1 / p, adjust=False, min_periods=p).mean()
    rs = ag / al.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(al.ne(0), 100.0)


def add_shifted_bool(x: pd.DataFrame, name: str, ser: pd.Series) -> None:
    vals = ser.astype(float)
    x[name] = vals
    x[f'{name}_prev1'] = vals.shift(1)
    x[f'{name}_prev2'] = vals.shift(2)


def make_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    x = pd.DataFrame({'dt': df['dt']})
    o = pd.to_numeric(df['open'], errors='coerce')
    h = pd.to_numeric(df['high'], errors='coerce')
    l = pd.to_numeric(df['low'], errors='coerce')
    c = pd.to_numeric(df['close'], errors='coerce')
    v = pd.to_numeric(df.get('tick_volume', pd.Series(np.nan, index=df.index)), errors='coerce')
    for name, ser in [('open', o), ('high', h), ('low', l), ('close', c), ('tick_volume', v)]:
        x[f'{prefix}_{name}'] = ser

    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    x[f'{prefix}_ret1'] = c.diff()
    x[f'{prefix}_ret3'] = c.diff(3)
    x[f'{prefix}_ret8'] = c.diff(8)
    x[f'{prefix}_range'] = h - l
    x[f'{prefix}_body'] = c - o
    x[f'{prefix}_body_abs'] = (c - o).abs()
    x[f'{prefix}_upper_wick'] = h - np.maximum(o, c)
    x[f'{prefix}_lower_wick'] = np.minimum(o, c) - l
    x[f'{prefix}_close_gt_open'] = (c > o).astype(int)

    for p in [5, 10, 14, 20, 28, 50, 56, 100, 200]:
        x[f'{prefix}_atr{p}'] = tr.rolling(p, min_periods=p).mean()
        x[f'{prefix}_atr_ewm{p}'] = tr.ewm(span=p, adjust=False, min_periods=p).mean()
        x[f'{prefix}_sma{p}'] = c.rolling(p, min_periods=p).mean()
        x[f'{prefix}_ema{p}'] = c.ewm(span=p, adjust=False, min_periods=p).mean()

    x[f'{prefix}_rsi14_sma'] = rsi_sma(c, 14)
    x[f'{prefix}_rsi14_wilder'] = rsi_wilder(c, 14)
    # Stage177 OHLC-only search follows the live snapshot parity formula.
    x[f'{prefix}_rsi14'] = x[f'{prefix}_rsi14_wilder']

    for p in [14, 20, 28, 50, 56]:
        x[f'{prefix}_range_atr{p}'] = x[f'{prefix}_range'] / x[f'{prefix}_atr{p}']
        x[f'{prefix}_range_atr_ewm{p}'] = x[f'{prefix}_range'] / x[f'{prefix}_atr_ewm{p}']
        x[f'{prefix}_body_atr{p}'] = x[f'{prefix}_body'] / x[f'{prefix}_atr{p}']
        x[f'{prefix}_body_abs_atr{p}'] = x[f'{prefix}_body_abs'] / x[f'{prefix}_atr{p}']

    add_shifted_bool(x, f'{prefix}_ema20_gt_ema50', (x[f'{prefix}_ema20'] > x[f'{prefix}_ema50']).astype(int))
    add_shifted_bool(x, f'{prefix}_ema50_gt_ema100', (x[f'{prefix}_ema50'] > x[f'{prefix}_ema100']).astype(int))
    add_shifted_bool(x, f'{prefix}_ema20_gt_ema100', (x[f'{prefix}_ema20'] > x[f'{prefix}_ema100']).astype(int))
    add_shifted_bool(x, f'{prefix}_close_gt_ema20', (c > x[f'{prefix}_ema20']).astype(int))
    add_shifted_bool(x, f'{prefix}_close_gt_ema50', (c > x[f'{prefix}_ema50']).astype(int))

    x[f'{prefix}_close_ema20_dist_atr28'] = (c - x[f'{prefix}_ema20']) / x[f'{prefix}_atr28']
    x[f'{prefix}_close_sma50_dist_atr28'] = (c - x[f'{prefix}_sma50']) / x[f'{prefix}_atr28']
    x[f'{prefix}_ema20_ema50_dist_atr28'] = (x[f'{prefix}_ema20'] - x[f'{prefix}_ema50']) / x[f'{prefix}_atr28']
    return x


def merge_features(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    base = make_features(m15, 'm15')
    for f in [make_features(h1, 'h1'), make_features(h4, 'h4'), make_features(d1, 'd1')]:
        base = pd.merge_asof(base.sort_values('dt'), f.sort_values('dt'), on='dt', direction='backward')
    base['hour'] = base['dt'].dt.hour
    base['month'] = base['dt'].dt.to_period('M').astype(str)
    base['session_7_22'] = ((base.hour >= 7) & (base.hour <= 22)).astype(int)
    base['session_12_22'] = ((base.hour >= 12) & (base.hour <= 22)).astype(int)
    base['session_15_23'] = ((base.hour >= 15) & (base.hour <= 23)).astype(int)

    base['d1_dist_close_atr14'] = (base.m15_close - base.d1_close) / base.d1_atr14
    base['d1_dist_close_atr28'] = (base.m15_close - base.d1_close) / base.d1_atr28
    base['d1_dist_ema20_atr28'] = (base.m15_close - base.d1_ema20) / base.d1_atr28
    base['d1_dist_sma50_atr28'] = (base.m15_close - base.d1_sma50) / base.d1_atr28
    base['h1_dist_ema20_atr28'] = (base.m15_close - base.h1_ema20) / base.h1_atr28
    base['h4_dist_ema20_atr28'] = (base.m15_close - base.h4_ema20) / base.h4_atr28
    return base


def append_parity_row(rows: list[dict[str, Any]], row_dt: Any, snapshot_col: str, python_col: str, sv: Any, pv: Any) -> None:
    sv_num = pd.to_numeric(pd.Series([sv]), errors='coerce').iloc[0]
    pv_num = pd.to_numeric(pd.Series([pv]), errors='coerce').iloc[0]
    diff = abs(float(sv_num) - float(pv_num)) if pd.notna(sv_num) and pd.notna(pv_num) else np.nan
    rows.append({
        'snapshot_entry_dt': str(row_dt),
        'snapshot_col': snapshot_col,
        'python_col': python_col,
        'snapshot_value': sv_num,
        'python_value': pv_num,
        'abs_diff': diff,
        'match_1e_6': bool(pd.notna(diff) and diff <= 1e-6),
    })


def snapshot_parity(data: pd.DataFrame, snap: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        if snap.empty or 'entry_dt' not in snap.columns:
            return pd.DataFrame(), pd.DataFrame()
        s = snap.copy()
        s['dt'] = pd.to_datetime(s['entry_dt'], errors='coerce')
        s = s[s['dt'].notna()].sort_values('dt')
        if s.empty:
            return pd.DataFrame([{'status': 'SNAPSHOT_DT_PARSE_FAILED'}]), pd.DataFrame()
        row = s.iloc[-1]
        row_dt = row['dt']
        hit = data[data['dt'].eq(row_dt)]
        if hit.empty:
            return pd.DataFrame([{'snapshot_entry_dt': str(row_dt), 'status': 'NO_MATCHING_M15_BAR_IN_COMBINED_OHLC'}]), pd.DataFrame()
        d = hit.iloc[-1]

        pairs = [
            ('m15_open', 'm15_open'),
            ('m15_high', 'm15_high'),
            ('m15_low', 'm15_low'),
            ('m15_close', 'm15_close'),
            ('m15_tick_volume', 'm15_tick_volume'),
            ('m15_rsi14', 'm15_rsi14'),
            ('h1_atr14', 'h1_atr14'),
            ('h1_range_atr', 'h1_range_atr14'),
            ('d1_atr14', 'd1_atr14'),
            ('d1_dist_atr', 'd1_dist_close_atr14'),
        ]
        rows: list[dict[str, Any]] = []
        for snap_col, py_col in pairs:
            if snap_col in row.index and py_col in data.columns:
                append_parity_row(rows, row_dt, snap_col, py_col, row[snap_col], d[py_col])

        if 'h1_up' in row.index:
            sv = int(str(row['h1_up']).lower() in ['true', '1', 'yes', 'y'])
            pv = int(safe_float(d.get('h1_ema20_gt_ema50', -1), -1))
            append_parity_row(rows, row_dt, 'h1_up', 'h1_ema20_gt_ema50', sv, pv)

        alt_rows: list[dict[str, Any]] = []
        alt_map = {
            'm15_rsi14': ['m15_rsi14', 'm15_rsi14_sma', 'm15_rsi14_wilder'],
            'h1_up': [
                'h1_ema20_gt_ema50',
                'h1_ema20_gt_ema50_prev1',
                'h1_ema20_gt_ema50_prev2',
                'h1_ema50_gt_ema100',
                'h1_ema50_gt_ema100_prev1',
                'h1_close_gt_ema20',
                'h1_close_gt_ema20_prev1',
                'h1_close_gt_ema50',
                'h1_close_gt_ema50_prev1',
            ],
            'h1_range_atr': ['h1_range_atr14', 'h1_range_atr28', 'h1_range_atr_ewm14', 'h1_range_atr_ewm28'],
            'd1_dist_atr': ['d1_dist_close_atr14', 'd1_dist_close_atr28', 'd1_dist_ema20_atr28', 'd1_dist_sma50_atr28'],
        }
        for snap_col, py_cols in alt_map.items():
            if snap_col not in row.index:
                continue
            sv_raw = row[snap_col]
            if snap_col == 'h1_up':
                sv_raw = int(str(sv_raw).lower() in ['true', '1', 'yes', 'y'])
            for py_col in py_cols:
                if py_col not in data.columns:
                    continue
                sv_num = pd.to_numeric(pd.Series([sv_raw]), errors='coerce').iloc[0]
                pv_num = pd.to_numeric(pd.Series([d[py_col]]), errors='coerce').iloc[0]
                diff = abs(float(sv_num) - float(pv_num)) if pd.notna(sv_num) and pd.notna(pv_num) else np.nan
                alt_rows.append({
                    'snapshot_entry_dt': str(row_dt),
                    'snapshot_col': snap_col,
                    'python_col': py_col,
                    'snapshot_value': sv_num,
                    'python_value': pv_num,
                    'abs_diff': diff,
                    'match_1e_6': bool(pd.notna(diff) and diff <= 1e-6),
                })
        alt = pd.DataFrame(alt_rows)
        if not alt.empty:
            alt = alt.sort_values(['snapshot_col', 'abs_diff', 'python_col'], ascending=[True, True, True])
        return pd.DataFrame(rows), alt
    except Exception as e:
        return pd.DataFrame([{'status': 'SNAPSHOT_PARITY_EXCEPTION_NON_BLOCKING', 'error': repr(e)}]), pd.DataFrame()


def compute_outcome(entries: pd.DataFrame, m5: pd.DataFrame, direction: str, tp: float, sl: float, horizon_m5: int) -> np.ndarray:
    m5 = m5.sort_values('dt').reset_index(drop=True)
    times = m5['dt'].values.astype('datetime64[ns]')
    et = entries['dt'].values.astype('datetime64[ns]')
    ep = entries.m15_close.values.astype(float)
    idx = np.searchsorted(times, et, side='right')
    highs = m5.high.values.astype(float)
    lows = m5.low.values.astype(float)
    closes = m5.close.values.astype(float)
    out = np.full(len(entries), np.nan, dtype=float)

    for i, j in enumerate(idx):
        end = min(j + horizon_m5, len(m5))
        if j >= len(m5) or end <= j:
            continue
        price = ep[i]
        if direction == 'LONG':
            tpv = price + tp
            slv = price - sl
            ht = highs[j:end] >= tpv
            hs = lows[j:end] <= slv
            hit = ht | hs
            if hit.any():
                k = int(np.argmax(hit))
                out[i] = -sl if hs[k] else tp
            else:
                out[i] = float(max(-sl, min(tp, closes[end - 1] - price)))
        else:
            tpv = price - tp
            slv = price + sl
            ht = lows[j:end] <= tpv
            hs = highs[j:end] >= slv
            hit = ht | hs
            if hit.any():
                k = int(np.argmax(hit))
                out[i] = -sl if hs[k] else tp
            else:
                out[i] = float(max(-sl, min(tp, price - closes[end - 1])))
    return out


def fast_metric(mask: np.ndarray, pnl: np.ndarray, idx: np.ndarray):
    m = mask & idx & np.isfinite(pnl)
    n = int(m.sum())
    if n == 0:
        return None
    x = pnl[m]
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    return n, float(x.sum()), pf, float((x > 0).mean())


def fast_all(mask: np.ndarray, pnl: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray, full_idx: np.ndarray):
    a = fast_metric(mask, pnl, train_idx)
    b = fast_metric(mask, pnl, test_idx)
    c = fast_metric(mask, pnl, full_idx)
    if not a or not b or not c:
        return None
    return {
        'train_n': a[0], 'train_sum': a[1], 'train_pf': a[2], 'train_wr': a[3],
        'test_n': b[0], 'test_sum': b[1], 'test_pf': b[2], 'test_wr': b[3],
        'full_n': c[0], 'full_sum': c[1], 'full_pf': c[2], 'full_wr': c[3],
    }


def month_stats(mask: np.ndarray, pnl: np.ndarray, months: np.ndarray):
    m = mask & np.isfinite(pnl)
    if not m.any():
        return 0, 0
    s = pd.DataFrame({'month': months[m], 'pnl': pnl[m]}).groupby('month').pnl.sum()
    return int(len(s)), int((s < 0).sum())


def pass_prelim(met: dict[str, Any]) -> bool:
    return (
        met['train_n'] >= MIN_TRAIN_N and
        met['test_n'] >= MIN_TEST_N and
        met['full_n'] >= MIN_FULL_N and
        met['train_pf'] >= PRELIM_MIN_PF and
        met['test_pf'] >= PRELIM_MIN_PF
    )


def pass_strict(met: dict[str, Any]) -> bool:
    return (
        met['train_n'] >= MIN_TRAIN_N and
        met['test_n'] >= MIN_TEST_N and
        met['full_n'] >= MIN_FULL_N and
        met['train_pf'] >= STRICT_MIN_PF and
        met['test_pf'] >= STRICT_MIN_PF
    )


def pass_old_benchmark(met: dict[str, Any]) -> bool:
    return (
        met['train_n'] >= MIN_TRAIN_N and
        met['test_n'] >= MIN_TEST_N and
        met['full_n'] >= MIN_FULL_N and
        met['train_pf'] > BENCHMARK_PF and
        met['test_pf'] > BENCHMARK_PF and
        met['full_pf'] > BENCHMARK_PF
    )


def pf_sort_key(row: dict[str, Any]) -> tuple[float, float, float, int]:
    return (
        min(safe_float(row.get('train_pf'), 0.0), safe_float(row.get('test_pf'), 0.0)),
        safe_float(row.get('full_pf'), 0.0),
        safe_float(row.get('test_pf'), 0.0),
        int(row.get('full_n', 0)),
    )


def quality_label(met: dict[str, Any]) -> str:
    if pass_old_benchmark(met):
        return 'BEATS_OLD_PF_2_237'
    if pass_strict(met):
        return 'STRICT_1_35'
    if pass_prelim(met):
        return 'PRELIM_1_00'
    return 'NEAR_MISS'


def make_conditions(data: pd.DataFrame):
    bool_cols: list[str] = []
    for c in data.columns:
        if c in ['dt', 'month', 'hour']:
            continue
        if c.startswith('session_') or c.endswith('_gt_open'):
            bool_cols.append(c)
        elif any(token in c for token in ['_gt_ema', 'close_gt_ema']):
            if pd.api.types.is_numeric_dtype(data[c]) and data[c].dropna().isin([0, 1]).all():
                bool_cols.append(c)
    bool_cols = sorted(set(bool_cols))

    num_cols: list[str] = []
    for c in data.columns:
        if c in ['dt', 'month', 'hour'] or c in bool_cols:
            continue
        if pd.api.types.is_numeric_dtype(data[c]) and data[c].notna().sum() > 1000 and data[c].nunique(dropna=True) > 20:
            if any(k in c for k in ['rsi', 'range_atr', 'body_atr', 'body_abs_atr', 'ret', 'dist', 'atr', 'body', 'wick', 'range']):
                num_cols.append(c)
    num_cols = sorted(set(num_cols))

    conds: list[tuple[str, np.ndarray]] = []
    for c in bool_cols:
        arr = data[c].fillna(0).astype(int).values
        for v in [0, 1]:
            conds.append((f'{c}=={v}', arr == v))

    qs = [.03, .05, .08, .1, .12, .15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .88, .9, .92, .95, .97]
    for c in num_cols:
        s = pd.to_numeric(data[c], errors='coerce').replace([np.inf, -np.inf], np.nan)
        qv = s.dropna().quantile(qs).drop_duplicates()
        arr = s.values.astype(float)
        for _, v in qv.items():
            if np.isfinite(v):
                conds.append((f'{c}>={v:.6g}', arr >= v))
                conds.append((f'{c}<={v:.6g}', arr <= v))
    return conds


def profile_candidates(
    data: pd.DataFrame,
    m5: pd.DataFrame,
    names: list[str],
    masks: list[np.ndarray],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    full_idx: np.ndarray,
    months: np.ndarray,
    direction: str,
    tp: float,
    sl: float,
    h: int,
    profile_no: int,
    profile_total: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    progress(f'profile {profile_no}/{profile_total} {direction} TP={tp} SL={sl} horizon_m5={h}: compute outcomes')
    pnl = compute_outcome(data, m5, direction, tp, sl, h)
    finite = np.isfinite(pnl)

    single_all: list[dict[str, Any]] = []
    prelim_results: list[dict[str, Any]] = []
    near_rows: list[dict[str, Any]] = []

    for name, mask in zip(names, masks):
        met = fast_all(mask, pnl, train_idx, test_idx, full_idx)
        if not met:
            continue
        row = {
            'direction': direction,
            'tp': tp,
            'sl': sl,
            'horizon_m5': h,
            'rule': name,
            'conds': 1,
            'quality': quality_label(met),
            **met,
        }
        single_all.append(row)
        if pass_prelim(met):
            prelim_results.append(row)
        if met['train_n'] >= 20 and met['test_n'] >= 5 and met['full_n'] >= 40:
            near_rows.append(row)

    single_all = sorted(single_all, key=pf_sort_key, reverse=True)
    prelim_results = sorted(prelim_results, key=pf_sort_key, reverse=True)
    near_rows = sorted(near_rows, key=pf_sort_key, reverse=True)

    rule_to_mask = {n: m for n, m in zip(names, masks)}
    pair_base = [r['rule'] for r in single_all[:PAIR_BASE_LIMIT]]
    pairs_all: list[dict[str, Any]] = []
    pairs_tested = 0
    progress(f'profile {profile_no}: singles={len(single_all)} prelim={len(prelim_results)} pair_scan_base={len(pair_base)}')
    for i in range(len(pair_base)):
        m1 = rule_to_mask[pair_base[i]]
        for j in range(i + 1, len(pair_base)):
            pairs_tested += 1
            rule = pair_base[i] + ' & ' + pair_base[j]
            mask = m1 & rule_to_mask[pair_base[j]]
            met = fast_all(mask, pnl, train_idx, test_idx, full_idx)
            if not met:
                continue
            row = {
                'direction': direction,
                'tp': tp,
                'sl': sl,
                'horizon_m5': h,
                'rule': rule,
                'conds': 2,
                'quality': quality_label(met),
                **met,
            }
            if pass_prelim(met):
                pairs_all.append(row)
            if met['train_n'] >= 20 and met['test_n'] >= 5 and met['full_n'] >= 40:
                near_rows.append(row)

    pairs_all = sorted(pairs_all, key=pf_sort_key, reverse=True)
    near_rows = sorted(near_rows, key=pf_sort_key, reverse=True)

    kept = prelim_results[:SINGLE_RESULT_LIMIT_PER_PROFILE] + pairs_all[:PAIR_RESULT_LIMIT_PER_PROFILE]
    near_kept = near_rows[:NEAR_MISS_LIMIT_PER_PROFILE]

    best_single = single_all[0] if single_all else {}
    best_pair = pairs_all[0] if pairs_all else {}
    diag = {
        'profile_no': profile_no,
        'direction': direction,
        'tp': tp,
        'sl': sl,
        'horizon_m5': h,
        'finite_outcomes': int(finite.sum()),
        'train_finite': int((finite & train_idx).sum()),
        'test_finite': int((finite & test_idx).sum()),
        'conditions': len(names),
        'singles_tested': len(single_all),
        'singles_prelim_pass': int(sum(1 for r in prelim_results if r['conds'] == 1)),
        'singles_strict_pass': int(sum(1 for r in single_all if pass_strict(r))),
        'singles_beats_old': int(sum(1 for r in single_all if pass_old_benchmark(r))),
        'pairs_tested': pairs_tested,
        'pairs_prelim_pass': len(pairs_all),
        'pairs_strict_pass': int(sum(1 for r in pairs_all if pass_strict(r))),
        'pairs_beats_old': int(sum(1 for r in pairs_all if pass_old_benchmark(r))),
        'best_single_rule': best_single.get('rule', ''),
        'best_single_train_pf': best_single.get('train_pf', math.nan),
        'best_single_test_pf': best_single.get('test_pf', math.nan),
        'best_single_full_pf': best_single.get('full_pf', math.nan),
        'best_pair_rule': best_pair.get('rule', ''),
        'best_pair_train_pf': best_pair.get('train_pf', math.nan),
        'best_pair_test_pf': best_pair.get('test_pf', math.nan),
        'best_pair_full_pf': best_pair.get('full_pf', math.nan),
    }

    for row in kept + near_kept:
        mask = np.ones(len(data), dtype=bool)
        for part in str(row['rule']).split(' & '):
            mask &= rule_to_mask.get(part, np.zeros(len(data), dtype=bool))
        months_n, neg_m = month_stats(mask & full_idx, pnl, months)
        row['full_months'] = months_n
        row['full_neg_months'] = neg_m
        row['beats_old_pf_2_237'] = bool(pass_old_benchmark(row))
        row['metric_scope'] = 'RAW_SEARCH_ONLY_NO_DEDUP_NO_HEALTH_GATE'
    return kept, near_kept, diag


def make_decision(ready: bool, top: pd.DataFrame, parity_fail: int, blockers: list[dict[str, Any]]) -> str:
    if not ready:
        if any(str(b.get('id', '')).startswith('no_train') or str(b.get('id', '')).startswith('no_test') for b in blockers):
            return 'OHLC_ONLY_REBUILD_SEARCH_BLOCKED_DATA_COVERAGE'
        return 'OHLC_ONLY_REBUILD_SEARCH_BLOCKED'
    parity_suffix = '_PARITY_FAIL_WARN' if parity_fail > 0 else ''
    if top.empty:
        return 'SEARCH_NO_TOP_RULES_EXPAND_177B' + parity_suffix
    if 'beats_old_pf_2_237' in top.columns and bool(top['beats_old_pf_2_237'].fillna(False).any()):
        return 'OHLC_ONLY_CANDIDATE_BEATS_OLD_PF_AUDIT_NEEDS_STAGE178' + parity_suffix
    return 'OHLC_ONLY_CANDIDATES_FOUND_BELOW_OLD_PF_EXPAND_SEARCH' + parity_suffix


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '177'
    out.mkdir(parents=True, exist_ok=True)

    progress('load and combine OHLC: 2025=gold#; 2026+=goldsharp; pre-2025 warmup=goldsharp if available')
    frames: dict[str, pd.DataFrame] = {}
    raw_diag_rows: list[dict[str, Any]] = []
    for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
        frames[tf], diag = combine(tf, data_dir)
        raw_diag_rows.extend(diag)
    source_diag = pd.DataFrame(raw_diag_rows)
    save(source_diag, out / 'gold_v3_177_source_coverage.csv')

    snap = read_csv_any(data_dir / 'gold_v3_live_feature_snapshot.csv')

    blockers: list[dict[str, Any]] = []
    for tf, df in frames.items():
        if df.empty:
            blockers.append({'id': 'missing_combined_ohlc', 'tf': tf})
        else:
            required = {'dt', 'open', 'high', 'low', 'close'}
            miss = sorted(required - set(df.columns))
            if miss:
                blockers.append({'id': 'missing_ohlc_columns', 'tf': tf, 'missing': miss})

    top = pd.DataFrame()
    allout = pd.DataFrame()
    near = pd.DataFrame()
    profile_diag = pd.DataFrame()
    parity = pd.DataFrame()
    parity_alt = pd.DataFrame()
    data = pd.DataFrame()
    coverage_summary: dict[str, Any] = {}

    if not blockers:
        progress('build live-reproducible OHLC features')
        data = merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        save(data.head(500), out / 'gold_v3_177_feature_sample_head500.csv')

        train_idx = ((data.dt >= pd.Timestamp('2025-01-02')) & (data.dt < pd.Timestamp('2026-01-01'))).values
        test_idx = (data.dt >= pd.Timestamp('2026-01-01')).values
        full_idx = (data.dt >= pd.Timestamp('2025-01-02')).values
        months = data.month.values

        coverage_summary = {
            'combined_m15_rows': int(len(data)),
            'combined_m15_min_dt': str(data['dt'].min()) if not data.empty else '',
            'combined_m15_max_dt': str(data['dt'].max()) if not data.empty else '',
            'train_rows': int(train_idx.sum()),
            'test_rows': int(test_idx.sum()),
            'full_rows': int(full_idx.sum()),
        }

        if int(train_idx.sum()) == 0:
            blockers.append({'id': 'no_train_rows_after_combine', 'detail': '2025 gold# rows are missing or not parsed; search cannot evaluate train_pf'})
        if int(test_idx.sum()) == 0:
            blockers.append({'id': 'no_test_rows_after_combine', 'detail': '2026+ goldsharp rows are missing or not parsed; search cannot evaluate test_pf'})
        if int(full_idx.sum()) == 0:
            blockers.append({'id': 'no_full_rows_after_combine', 'detail': 'No 2025+ rows after combine'})

        if not snap.empty:
            progress('compare optional gold_v3_live_feature_snapshot.csv against Python OHLC features')
            parity, parity_alt = snapshot_parity(data, snap)
            save(parity, out / 'gold_v3_177_live_snapshot_parity.csv')
            save(parity_alt, out / 'gold_v3_177_live_snapshot_parity_alternatives.csv')
            if not parity.empty and 'status' in parity.columns and str(parity.iloc[0].get('status', '')).startswith('SNAPSHOT_PARITY_EXCEPTION'):
                progress('snapshot parity failed non-blocking; continue OHLC-only search')

        if not blockers:
            progress('build rule conditions')
            conds = make_conditions(data)
            names = [x[0] for x in conds]
            masks = [x[1] for x in conds]

            profiles: list[tuple[str, float, float, int]] = []
            for direction in ['LONG', 'SHORT']:
                for tp, sl, h in [(8, 4, 36), (10, 5, 48), (12, 6, 48), (15, 7.5, 64), (20, 10, 96), (25, 10, 96), (30, 15, 128), (40, 20, 192)]:
                    profiles.append((direction, tp, sl, h))

            results: list[dict[str, Any]] = []
            near_rows: list[dict[str, Any]] = []
            diag_rows: list[dict[str, Any]] = []

            for pi, (direction, tp, sl, h) in enumerate(profiles, 1):
                kept, near_kept, diag = profile_candidates(
                    data=data,
                    m5=frames['m5'],
                    names=names,
                    masks=masks,
                    train_idx=train_idx,
                    test_idx=test_idx,
                    full_idx=full_idx,
                    months=months,
                    direction=direction,
                    tp=tp,
                    sl=sl,
                    h=h,
                    profile_no=pi,
                    profile_total=len(profiles),
                )
                results.extend(kept)
                near_rows.extend(near_kept)
                diag_rows.append(diag)

            allout = pd.DataFrame(results)
            near = pd.DataFrame(near_rows)
            profile_diag = pd.DataFrame(diag_rows)
            save(profile_diag, out / 'gold_v3_177_profile_diagnostics.csv')

            if not allout.empty:
                top = allout.sort_values(
                    ['beats_old_pf_2_237', 'full_pf', 'test_pf', 'train_pf', 'full_n'],
                    ascending=[False, False, False, False, False],
                ).drop_duplicates(['direction', 'tp', 'sl', 'horizon_m5', 'rule']).head(100).copy()
                save(allout, out / 'gold_v3_177_all_prelim_rules.csv')
                save(top, out / 'gold_v3_177_top100_rules.csv')

            if not near.empty:
                near = near.sort_values(
                    ['beats_old_pf_2_237', 'full_pf', 'test_pf', 'train_pf', 'full_n'],
                    ascending=[False, False, False, False, False],
                ).drop_duplicates(['direction', 'tp', 'sl', 'horizon_m5', 'rule']).head(200).copy()
                save(near, out / 'gold_v3_177_near_miss_top200_rules.csv')
        else:
            progress('data coverage blocker found; skip candidate search and write diagnostics')

    ready = len(blockers) == 0
    snapshot_rows = int(len(snap)) if not snap.empty else 0
    parity_rows = int(len(parity)) if not parity.empty else 0
    parity_fail = int((~parity.get('match_1e_6', pd.Series(dtype=bool))).sum()) if not parity.empty and 'match_1e_6' in parity.columns else 0
    parity_pass = bool(parity_rows > 0 and parity_fail == 0) if snapshot_rows > 0 else None

    best_pf = float(top.iloc[0].full_pf) if ready and not top.empty else math.nan
    best_rule = str(top.iloc[0].rule) if ready and not top.empty else ''
    best_train_pf = float(top.iloc[0].train_pf) if ready and not top.empty else math.nan
    best_test_pf = float(top.iloc[0].test_pf) if ready and not top.empty else math.nan
    best_full_n = int(top.iloc[0].full_n) if ready and not top.empty else 0
    best_full_neg_months = int(top.iloc[0].full_neg_months) if ready and not top.empty and 'full_neg_months' in top.columns else 0
    beats_any = bool((top.get('beats_old_pf_2_237', pd.Series(dtype=bool)).fillna(False)).any()) if not top.empty else False

    decision = make_decision(ready, top, parity_fail, blockers)
    status = 'READY' if ready else 'BLOCKED'

    summary = {
        'step': STEP,
        'status': status,
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'old_pf_benchmark': BENCHMARK_PF,
        'best_full_pf': best_pf,
        'best_train_pf': best_train_pf,
        'best_test_pf': best_test_pf,
        'best_full_n': best_full_n,
        'best_full_neg_months': best_full_neg_months,
        'best_rule': best_rule,
        'top_rows': int(len(top)) if ready else 0,
        'near_miss_rows': int(len(near)) if ready else 0,
        'live_snapshot_detected_rows': snapshot_rows,
        'live_snapshot_parity_rows': parity_rows,
        'live_snapshot_parity_fail_rows': parity_fail,
        'live_snapshot_parity_pass': parity_pass,
        'beats_old_pf_2_237': beats_any,
        **coverage_summary,
        'source_csv_mutated': False,
        'contract_mutated': False,
        'open_asof_allowed': False,
        'candidate_pool_removed': False,
        'f002_exclusion_bypassed': False,
        'final_live_enabled': False,
        'discord_enabled': False,
        'mt5_order_enabled': False,
        'ai_api_enabled': False,
        'live_hook_enabled': False,
        'payload_enabled': False,
        'autotrade_enabled': False,
        'no_signal_discord_notify': False,
        'blocker_count': len(blockers),
        'elapsed_seconds': round(time.time() - t0, 2),
    }

    (out / 'gold_v3_177_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_177_decision.csv')

    lines = ['GOLD V3 177 PASTE_ME_OHLC_ONLY_REBUILD_SEARCH_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += ['', 'LIVE_SNAPSHOT_PARITY', parity.to_string(index=False) if not parity.empty else 'NO_LIVE_SNAPSHOT_PARITY']
    lines += ['', 'LIVE_SNAPSHOT_PARITY_ALTERNATIVES', parity_alt.head(40).to_string(index=False) if not parity_alt.empty else 'NO_LIVE_SNAPSHOT_PARITY_ALTERNATIVES']
    lines += ['', 'PROFILE_DIAGNOSTICS', profile_diag.to_string(index=False) if not profile_diag.empty else 'NO_PROFILE_DIAGNOSTICS']
    lines += ['', 'TOP30_RULES', top.head(30).to_string(index=False) if not top.empty else 'NO_TOP_RULES']
    lines += ['', 'NEAR_MISS_TOP30', near.head(30).to_string(index=False) if not near.empty else 'NO_NEAR_MISS_RULES']
    lines += [
        '',
        'INTERPRETATION',
        'This is an OHLC-only rebuild search. It uses 2025 gold# candles, 2026+ goldsharp candles, and goldsharp pre-2025 only as HTF warmup. Optional live snapshot is used only for parity audit and never as a backtest/search source. Rules are generated only from candle-derived features known at entry time. Outcome columns are used only after entry for audit metrics. Results are audit-only and must still pass spread/slippage/robustness gates before any live payload.',
        'If train_rows is zero, the 2025 gold# source files are missing or not parseable, so train_pf/test_pf/full_pf cannot be evaluated. In that case, do not treat NO_TOP_RULES as a strategy result; fix input coverage first.',
        'If TOP30_RULES is empty while train_rows and test_rows are both positive, check PROFILE_DIAGNOSTICS and NEAR_MISS_TOP30 before changing the candidate pool. LIVE_SNAPSHOT_PARITY failures are warnings for formula/parity audit and do not enable or block live trading by themselves.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
