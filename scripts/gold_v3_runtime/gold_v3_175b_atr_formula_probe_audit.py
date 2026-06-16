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

STEP = 'GOLD_V3_175B_ATR_FORMULA_PROBE_AUDIT_ONLY'
FEATURE_FILE = 'gold_v3_live_feature_snapshot.csv'
PERIOD = 14


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


def prep_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x.columns = [str(c).strip() for c in x.columns]
    x['time_dt'] = pd.to_datetime(x['time'], errors='coerce') if 'time' in x.columns else pd.NaT
    for c in ['open','high','low','close']:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x[x['time_dt'].notna()].sort_values('time_dt').reset_index(drop=True)
    return x


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df['close'].shift(1)
    return pd.concat([(df['high']-df['low']).abs(), (df['high']-prev_close).abs(), (df['low']-prev_close).abs()], axis=1).max(axis=1)


def rma_ewm(tr: pd.Series, period: int) -> pd.Series:
    return tr.ewm(alpha=1.0/period, adjust=False, min_periods=period).mean()


def rma_wilder_seed_sma(tr: pd.Series, period: int) -> pd.Series:
    vals = tr.astype(float).to_list()
    out = [float('nan')] * len(vals)
    if len(vals) < period + 1:
        return pd.Series(out, index=tr.index)
    # Seed from the first `period` valid true ranges after the first bar.
    valid = pd.Series(vals).dropna()
    if len(valid) < period:
        return pd.Series(out, index=tr.index)
    seed_pos = valid.index[period-1]
    seed = float(valid.iloc[:period].mean())
    out[seed_pos] = seed
    prev = seed
    for i in range(seed_pos + 1, len(vals)):
        v = vals[i]
        if math.isnan(v):
            out[i] = prev
        else:
            prev = (prev * (period - 1) + float(v)) / period
            out[i] = prev
    return pd.Series(out, index=tr.index)


def add_atr_variants(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    tr = true_range(x)
    x['tr'] = tr
    x['atr_rolling_sma14'] = tr.rolling(PERIOD, min_periods=PERIOD).mean()
    x['atr_ewm_alpha1_14'] = rma_ewm(tr, PERIOD)
    x['atr_wilder_seed_sma14'] = rma_wilder_seed_sma(tr, PERIOD)
    x['range_atr_rolling_sma14'] = (x['high'] - x['low']) / x['atr_rolling_sma14']
    x['range_atr_ewm_alpha1_14'] = (x['high'] - x['low']) / x['atr_ewm_alpha1_14']
    x['range_atr_wilder_seed_sma14'] = (x['high'] - x['low']) / x['atr_wilder_seed_sma14']
    return x


def nearest_index(df: pd.DataFrame, target: pd.Timestamp) -> int | None:
    if df.empty:
        return None
    z = df[df['time_dt'] <= target]
    if z.empty:
        return None
    return int(z.index[-1])


def fnum(v) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else float('nan')
    except Exception:
        return float('nan')


def probe_timeframe(name: str, df: pd.DataFrame, target_time: pd.Timestamp, ea_atr: float, ea_range_atr: float | None, out_rows: list[dict]) -> None:
    x = add_atr_variants(df)
    idx = nearest_index(x, target_time)
    if idx is None:
        out_rows.append({'timeframe':name,'variant':'NO_MATCH','bar_shift':0,'bar_time':'','ea_atr':ea_atr,'py_atr':float('nan'),'atr_abs_diff':float('inf'),'ea_range_atr':ea_range_atr,'py_range_atr':float('nan'),'range_abs_diff':float('inf')})
        return
    atr_cols = ['atr_rolling_sma14','atr_ewm_alpha1_14','atr_wilder_seed_sma14']
    range_map = {'atr_rolling_sma14':'range_atr_rolling_sma14','atr_ewm_alpha1_14':'range_atr_ewm_alpha1_14','atr_wilder_seed_sma14':'range_atr_wilder_seed_sma14'}
    for offset in range(-3,4):
        j = idx + offset
        if j < 0 or j >= len(x):
            continue
        row = x.iloc[j]
        for c in atr_cols:
            py_atr = fnum(row[c])
            py_range = fnum(row[range_map[c]]) if ea_range_atr is not None else float('nan')
            out_rows.append({
                'timeframe': name,
                'variant': c,
                'bar_shift_from_target_match': offset,
                'bar_time': str(row['time_dt']),
                'ea_atr': ea_atr,
                'py_atr': py_atr,
                'atr_abs_diff': abs(ea_atr - py_atr) if math.isfinite(ea_atr) and math.isfinite(py_atr) else float('inf'),
                'ea_range_atr': ea_range_atr if ea_range_atr is not None else '',
                'py_range_atr': py_range if ea_range_atr is not None else '',
                'range_abs_diff': abs(float(ea_range_atr) - py_range) if ea_range_atr is not None and math.isfinite(py_range) else '',
            })


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--feature-csv', default=FEATURE_FILE)
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '175b'
    out.mkdir(parents=True, exist_ok=True)

    feature_path = Path(args.feature_csv)
    if not feature_path.is_absolute():
        feature_path = mt5 / feature_path
    feat = read_csv_any(feature_path)
    h1 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_h1.csv'))
    d1 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_d1.csv'))
    blockers = []
    warnings = []
    rows: list[dict] = []

    if feat.empty:
        blockers.append({'id':'missing_feature_snapshot','path':str(feature_path)})
    if h1.empty:
        blockers.append({'id':'h1_missing'})
    if d1.empty:
        blockers.append({'id':'d1_missing'})
    latest_info = {}
    if not blockers:
        f = feat.tail(1).iloc[0]
        h1_time = pd.to_datetime(f['h1_close_time'], errors='coerce')
        d1_time = pd.to_datetime(f['d1_close_time'], errors='coerce')
        latest_info = {'entry_dt':str(f.get('entry_dt')),'h1_close_time':str(f.get('h1_close_time')),'d1_close_time':str(f.get('d1_close_time'))}
        if pd.isna(h1_time) or pd.isna(d1_time):
            blockers.append({'id':'target_times_not_parseable','latest':latest_info})
        else:
            probe_timeframe('H1', h1, h1_time, fnum(f['h1_atr14']), fnum(f['h1_range_atr']), rows)
            probe_timeframe('D1', d1, d1_time, fnum(f['d1_atr14']), None, rows)
    df = pd.DataFrame(rows)
    save(df, out / 'gold_v3_175b_atr_formula_probe.csv')
    best = pd.DataFrame()
    if not df.empty:
        best = df.sort_values(['timeframe','atr_abs_diff'], ascending=[True, True]).groupby('timeframe', as_index=False).head(5)
        save(best, out / 'gold_v3_175b_best_atr_matches.csv')
    ready = len(blockers) == 0
    status = 'READY' if ready else 'BLOCKED'
    decision = 'ATR_FORMULA_PROBE_READY' if ready else 'ATR_FORMULA_PROBE_BLOCKED'
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
        'probe_rows': int(len(df)),
        'best_rows': int(len(best)),
        'blocker_count': len(blockers),
        'warning_count': len(warnings),
        'source_csv_mutated': False,
        'contract_mutated': False,
        'open_asof_allowed': False,
        'candidate_pool_removed': False,
        'f002_exclusion_bypassed': False,
        'final_live_enabled': False,
        'elapsed_seconds': round(time.time()-t0,2),
    }
    (out / 'gold_v3_175b_summary.json').write_text(json.dumps({**summary,'latest':latest_info,'blockers':blockers,'warnings':warnings}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_175b_decision.csv')
    lines = ['GOLD V3 175B PASTE_ME_ATR_FORMULA_PROBE_AUDIT'] + [f'{k}: {v}' for k,v in summary.items()]
    lines += ['', 'LATEST_TIMES']
    if latest_info:
        for k,v in latest_info.items(): lines.append(f'{k}: {v}')
    else:
        lines.append('NO_LATEST_TIMES')
    lines += ['', 'BEST_ATR_MATCHES', best.to_string(index=False) if not best.empty else 'NO_BEST_MATCHES']
    lines += ['', 'FULL_PROBE', df.to_string(index=False) if not df.empty else 'NO_PROBE']
    lines += ['', 'INTERPRETATION', 'Compares several ATR formula/shift variants against EA-exported iATR-like values. Use the closest variant for Python-side reconciliation, or prefer EA-exported ATR if the EA source is trusted.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    lines += ['', 'WARNINGS', 'NO_WARNINGS' if not warnings else json.dumps(warnings, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2

if __name__ == '__main__':
    raise SystemExit(main())
