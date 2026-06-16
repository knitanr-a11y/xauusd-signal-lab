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

STEP = 'GOLD_V3_175C_FEATURE_SNAPSHOT_SMA_RECONCILIATION_AUDIT_ONLY'
FEATURE_FILE = 'gold_v3_live_feature_snapshot.csv'
PERIOD = 14
TOL = 1e-5


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


def prep(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x.columns = [str(c).strip() for c in x.columns]
    x['time_dt'] = pd.to_datetime(x['time'], errors='coerce') if 'time' in x.columns else pd.NaT
    for c in ['open','high','low','close']:
        if c in x.columns:
            x[c] = pd.to_numeric(x[c], errors='coerce')
    return x[x['time_dt'].notna()].sort_values('time_dt').reset_index(drop=True)


def tr(df: pd.DataFrame) -> pd.Series:
    pc = df['close'].shift(1)
    return pd.concat([(df['high']-df['low']).abs(), (df['high']-pc).abs(), (df['low']-pc).abs()], axis=1).max(axis=1)


def atr_sma(df: pd.DataFrame, period: int = PERIOD) -> pd.Series:
    return tr(df).rolling(period, min_periods=period).mean()


def rma(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(alpha=1/period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = PERIOD) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0)
    l = -d.clip(upper=0)
    ag = rma(g, period)
    al = rma(l, period)
    rs = ag / al.replace(0, math.nan)
    out = 100 - 100/(1+rs)
    return out.where(al.ne(0), 100.0)


def row_at_or_before(df: pd.DataFrame, t: pd.Timestamp):
    z = df[df.time_dt <= t]
    return None if z.empty else z.iloc[-1]


def f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else float('nan')
    except Exception:
        return float('nan')


def boolish(v) -> bool:
    return str(v).strip().lower() in {'true','1','yes','y'}


def add_cmp(rows, feature, ea, py, tol=TOL):
    diff = abs(float(ea)-float(py)) if math.isfinite(float(ea)) and math.isfinite(float(py)) else float('inf')
    rows.append({'feature':feature,'ea_value':ea,'python_sma_value':py,'abs_diff':diff,'tolerance':tol,'passed':bool(diff <= tol)})


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--feature-csv', default=FEATURE_FILE)
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '175c'
    out.mkdir(parents=True, exist_ok=True)
    feature_path = Path(args.feature_csv)
    if not feature_path.is_absolute():
        feature_path = mt5 / feature_path
    feat = read_csv_any(feature_path)
    m15 = prep(read_csv_any(mt5 / 'goldsharp_m15.csv'))
    h1 = prep(read_csv_any(mt5 / 'goldsharp_h1.csv'))
    d1 = prep(read_csv_any(mt5 / 'goldsharp_d1.csv'))
    blockers = []
    if feat.empty: blockers.append({'id':'missing_feature_snapshot','path':str(feature_path)})
    if m15.empty: blockers.append({'id':'m15_missing'})
    if h1.empty: blockers.append({'id':'h1_missing'})
    if d1.empty: blockers.append({'id':'d1_missing'})
    rows=[]; latest={}
    if not blockers:
        fr = feat.tail(1).iloc[0]
        entry_dt = pd.to_datetime(fr['entry_dt'], errors='coerce')
        h1_time = pd.to_datetime(fr['h1_close_time'], errors='coerce')
        d1_time = pd.to_datetime(fr['d1_close_time'], errors='coerce')
        latest={'entry_dt':str(fr.get('entry_dt')),'h1_close_time':str(fr.get('h1_close_time')),'d1_close_time':str(fr.get('d1_close_time'))}
        if pd.isna(entry_dt) or pd.isna(h1_time) or pd.isna(d1_time):
            blockers.append({'id':'times_not_parseable','latest':latest})
        else:
            m15['rsi14_py'] = rsi(m15['close'])
            h1['atr14_sma_py'] = atr_sma(h1)
            h1['range_atr_sma_py'] = (h1['high'] - h1['low']) / h1['atr14_sma_py']
            h1['h1_up_py'] = h1['close'] > h1['close'].shift(1)
            d1['atr14_sma_py'] = atr_sma(d1)
            mr = row_at_or_before(m15, entry_dt)
            hr = row_at_or_before(h1, h1_time)
            dr = row_at_or_before(d1, d1_time)
            if mr is None: blockers.append({'id':'m15_match_missing'})
            if hr is None: blockers.append({'id':'h1_match_missing'})
            if dr is None: blockers.append({'id':'d1_match_missing'})
            if not blockers:
                add_cmp(rows, 'm15_rsi14', f(fr['m15_rsi14']), f(mr['rsi14_py']))
                add_cmp(rows, 'h1_atr14', f(fr['h1_atr14']), f(hr['atr14_sma_py']))
                add_cmp(rows, 'h1_range_atr', f(fr['h1_range_atr']), f(hr['range_atr_sma_py']))
                add_cmp(rows, 'd1_atr14', f(fr['d1_atr14']), f(dr['atr14_sma_py']))
                py_d1_dist = (f(mr['close']) - f(dr['close'])) / f(dr['atr14_sma_py']) if f(dr['atr14_sma_py']) != 0 else float('nan')
                add_cmp(rows, 'd1_dist_atr', f(fr['d1_dist_atr']), py_d1_dist)
                ea_h1up = boolish(fr['h1_up']); py_h1up = bool(hr['h1_up_py'])
                rows.append({'feature':'h1_up','ea_value':ea_h1up,'python_sma_value':py_h1up,'abs_diff':0 if ea_h1up==py_h1up else 1,'tolerance':0,'passed':bool(ea_h1up==py_h1up)})
    rec = pd.DataFrame(rows)
    save(rec, out / 'gold_v3_175c_sma_reconciliation.csv')
    failed = int((~rec['passed']).sum()) if not rec.empty and 'passed' in rec.columns else 0
    passed = int(rec['passed'].sum()) if not rec.empty and 'passed' in rec.columns else 0
    ready = len(blockers)==0 and failed==0
    status = 'READY' if ready else ('FORMULA_MISMATCH' if len(blockers)==0 else 'BLOCKED')
    decision = 'FEATURE_SNAPSHOT_SMA_RECONCILIATION_READY' if ready else 'FEATURE_SNAPSHOT_SMA_RECONCILIATION_REVIEW_REQUIRED'
    summary = {'step':STEP,'status':status,'ready':ready,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'feature_csv':str(feature_path),'audit_only':True,'review_only':True,'atr_formula':'rolling_SMA14_true_range','reconciliation_rows':int(len(rec)),'passed_count':passed,'failed_count':failed,'blocker_count':len(blockers),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'elapsed_seconds':round(time.time()-t0,2)}
    (out / 'gold_v3_175c_summary.json').write_text(json.dumps({**summary,'latest':latest,'blockers':blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_175c_decision.csv')
    lines=['GOLD V3 175C PASTE_ME_FEATURE_SNAPSHOT_SMA_RECONCILIATION_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines += ['', 'LATEST_TIMES']
    if latest:
        for k,v in latest.items(): lines.append(f'{k}: {v}')
    else: lines.append('NO_LATEST_TIMES')
    lines += ['', 'SMA_RECONCILIATION', rec.to_string(index=False) if not rec.empty else 'NO_RECONCILIATION']
    lines += ['', 'INTERPRETATION', 'Uses rolling SMA14 true-range ATR, matching Stage175B best probe against the EA-exported feature snapshot. If all rows pass, EA feature snapshot is accepted for feature-only later candidate probing.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2

if __name__ == '__main__':
    raise SystemExit(main())
