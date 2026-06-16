#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_175_FEATURE_SNAPSHOT_RECONCILIATION_AUDIT_ONLY'
FEATURE_FILE = 'gold_v3_live_feature_snapshot.csv'
TOLERANCES = {
    'm15_rsi14': 1e-5,
    'h1_atr14': 1e-5,
    'h1_range_atr': 1e-5,
    'd1_atr14': 1e-5,
    'd1_dist_atr': 1e-5,
}


def read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ['utf-8-sig','utf-8','cp932']:
        for sep in [',',';','\t']:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
                if len(df.columns) > 1:
                    return df
            except Exception:
                pass
    return pd.DataFrame()


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def parse_time_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors='coerce')


def prep_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x.columns = [str(c).strip() for c in x.columns]
    x['time_dt'] = parse_time_series(x['time']) if 'time' in x.columns else pd.NaT
    for c in ['open','high','low','close']:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors='coerce')
    return x[x['time_dt'].notna()].sort_values('time_dt').reset_index(drop=True)


def rma(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    diff = close.diff()
    gain = diff.clip(lower=0)
    loss = -diff.clip(upper=0)
    avg_gain = rma(gain, period)
    avg_loss = rma(loss, period)
    rs = avg_gain / avg_loss.replace(0, math.nan)
    out = 100 - (100 / (1 + rs))
    out = out.where(avg_loss.ne(0), 100.0)
    return out


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([(high-low).abs(), (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    return rma(tr, period)


def nearest_at_or_before(df: pd.DataFrame, time_col: str, target: pd.Timestamp) -> pd.Series | None:
    if df.empty:
        return None
    z = df[df[time_col] <= target]
    if z.empty:
        return None
    return z.iloc[-1]


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--feature-csv', default=FEATURE_FILE)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '175'
    out.mkdir(parents=True, exist_ok=True)

    feature_path = Path(args.feature_csv)
    if not feature_path.is_absolute():
        feature_path = mt5 / feature_path
    feat = read_csv_any(feature_path)
    m15 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_m15.csv'))
    h1 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_h1.csv'))
    d1 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_d1.csv'))

    blockers = []
    warnings = []
    rows = []
    latest_info = {}

    if feat.empty:
        blockers.append({'id':'missing_feature_snapshot','path':str(feature_path)})
    elif len(feat) < 1:
        blockers.append({'id':'empty_feature_snapshot','path':str(feature_path)})
    for name, df in [('M15',m15),('H1',h1),('D1',d1)]:
        if df.empty:
            blockers.append({'id':f'{name}_csv_missing_or_unreadable'})
    if not blockers:
        f = feat.tail(1).iloc[0]
        entry_dt = pd.to_datetime(f['entry_dt'], errors='coerce')
        h1_time = pd.to_datetime(f['h1_close_time'], errors='coerce')
        d1_time = pd.to_datetime(f['d1_close_time'], errors='coerce')
        if pd.isna(entry_dt) or pd.isna(h1_time) or pd.isna(d1_time):
            blockers.append({'id':'feature_times_not_parseable','entry_dt':str(f.get('entry_dt')),'h1_close_time':str(f.get('h1_close_time')),'d1_close_time':str(f.get('d1_close_time'))})
        else:
            latest_info = {'entry_dt':str(f['entry_dt']),'h1_close_time':str(f['h1_close_time']),'d1_close_time':str(f['d1_close_time'])}
            m15['rsi14_py'] = rsi(m15['close'], 14)
            h1['atr14_py'] = atr(h1, 14)
            h1['range_atr_py'] = (h1['high'] - h1['low']) / h1['atr14_py']
            h1['h1_up_py'] = h1['close'] > h1['close'].shift(1)
            d1['atr14_py'] = atr(d1, 14)
            m15_row = nearest_at_or_before(m15, 'time_dt', entry_dt)
            h1_row = nearest_at_or_before(h1, 'time_dt', h1_time)
            d1_row = nearest_at_or_before(d1, 'time_dt', d1_time)
            if m15_row is None:
                blockers.append({'id':'matching_m15_row_missing','entry_dt':str(entry_dt)})
            if h1_row is None:
                blockers.append({'id':'matching_h1_row_missing','h1_close_time':str(h1_time)})
            if d1_row is None:
                blockers.append({'id':'matching_d1_row_missing','d1_close_time':str(d1_time)})
            if not blockers:
                values = {
                    'm15_rsi14': float(m15_row['rsi14_py']),
                    'h1_atr14': float(h1_row['atr14_py']),
                    'h1_range_atr': float(h1_row['range_atr_py']),
                    'h1_up': bool(h1_row['h1_up_py']),
                    'd1_atr14': float(d1_row['atr14_py']),
                    'd1_dist_atr': (float(m15_row['close']) - float(d1_row['close'])) / float(d1_row['atr14_py']) if finite(d1_row['atr14_py']) and float(d1_row['atr14_py']) != 0 else float('nan'),
                }
                for key in ['m15_rsi14','h1_atr14','h1_range_atr','d1_atr14','d1_dist_atr']:
                    ea = float(pd.to_numeric(pd.Series([f[key]]), errors='coerce').iloc[0])
                    py = float(values[key])
                    diff = abs(ea - py) if finite(ea) and finite(py) else float('inf')
                    tol = TOLERANCES[key]
                    rows.append({'feature':key,'ea_value':ea,'python_value':py,'abs_diff':diff,'tolerance':tol,'passed':bool(diff <= tol)})
                    if diff > tol:
                        warnings.append({'id':f'{key}_diff_exceeds_tolerance','ea':ea,'python':py,'abs_diff':diff,'tolerance':tol})
                ea_h1up = str(f['h1_up']).strip().lower() in {'true','1','yes','y'}
                py_h1up = bool(values['h1_up'])
                rows.append({'feature':'h1_up','ea_value':ea_h1up,'python_value':py_h1up,'abs_diff':0 if ea_h1up==py_h1up else 1,'tolerance':0,'passed':bool(ea_h1up==py_h1up)})
                if ea_h1up != py_h1up:
                    warnings.append({'id':'h1_up_differs','ea':ea_h1up,'python':py_h1up})

    rec = pd.DataFrame(rows)
    save(rec, out / 'gold_v3_175_feature_reconciliation.csv')
    ready = len(blockers) == 0
    status = 'READY' if ready else 'BLOCKED'
    decision = 'FEATURE_SNAPSHOT_RECONCILIATION_READY' if ready else 'FEATURE_SNAPSHOT_RECONCILIATION_BLOCKED'
    passed_count = int(rec['passed'].sum()) if not rec.empty and 'passed' in rec.columns else 0
    failed_count = int((~rec['passed']).sum()) if not rec.empty and 'passed' in rec.columns else 0
    summary = {
        'step': STEP,
        'status': status,
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        'output_dir': str(out),
        'feature_csv': str(feature_path),
        'audit_only': True,
        'review_only': True,
        'ea_python_reconciliation_rows': int(len(rec)),
        'passed_count': passed_count,
        'failed_count': failed_count,
        'warning_count': len(warnings),
        'blocker_count': len(blockers),
        'source_csv_mutated': False,
        'contract_mutated': False,
        'open_asof_allowed': False,
        'candidate_pool_removed': False,
        'f002_exclusion_bypassed': False,
        'final_live_enabled': False,
        'elapsed_seconds': round(time.time()-t0,2),
    }
    (out / 'gold_v3_175_summary.json').write_text(json.dumps({**summary,'latest':latest_info,'blockers':blockers,'warnings':warnings}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_175_decision.csv')
    lines = ['GOLD V3 175 PASTE_ME_FEATURE_SNAPSHOT_RECONCILIATION_AUDIT'] + [f'{k}: {v}' for k,v in summary.items()]
    lines += ['', 'LATEST_TIMES']
    if latest_info:
        for k,v in latest_info.items(): lines.append(f'{k}: {v}')
    else:
        lines.append('NO_LATEST_TIMES')
    lines += ['', 'RECONCILIATION', rec.to_string(index=False) if not rec.empty else 'NO_RECONCILIATION']
    lines += ['', 'INTERPRETATION', 'Compares EA-exported GOLD V3 feature snapshot against Python recomputation from closed OHLC CSVs. Warnings indicate formula/rounding mismatch and must be reviewed before payload generation.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    lines += ['', 'WARNINGS', 'NO_WARNINGS' if not warnings else json.dumps(warnings, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2

if __name__ == '__main__':
    raise SystemExit(main())
