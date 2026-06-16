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

STEP = 'GOLD_V3_174_FEATURE_SNAPSHOT_INPUT_AUDIT_ONLY'
REQUIRED_FEATURE_COLUMNS = [
    'entry_dt','symbol','m15_open','m15_high','m15_low','m15_close','m15_tick_volume','m15_rsi14',
    'h1_close_time','h1_open','h1_high','h1_low','h1_close','h1_atr14','h1_range_atr','h1_up',
    'd1_close_time','d1_open','d1_high','d1_low','d1_close','d1_atr14','d1_dist_atr','exported_at','is_closed',
]
CANDLE_COLUMNS = ['time','open','high','low','close','tick_volume','spread','real_volume']
CANDLE_FILES = {
    'M1': 'goldsharp_m1.csv',
    'M5': 'goldsharp_m5.csv',
    'M15': 'goldsharp_m15.csv',
    'H1': 'goldsharp_h1.csv',
    'H4': 'goldsharp_h4.csv',
    'D1': 'goldsharp_d1.csv',
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


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else float('nan')
    except Exception:
        return float('nan')


def boolish(v) -> bool:
    return str(v).strip().lower() in {'true','1','yes','y'}


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--feature-csv', default='gold_v3_live_feature_snapshot.csv')
    args = ap.parse_args()

    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '174'
    out.mkdir(parents=True, exist_ok=True)

    feature_path = Path(args.feature_csv)
    if not feature_path.is_absolute():
        feature_path = mt5 / feature_path

    blockers = []
    warnings = []
    feature_df = read_csv_any(feature_path)
    feature_checks = []
    candle_checks = []
    candidate_rows = []

    if feature_df.empty:
        blockers.append({'id':'missing_or_unreadable_feature_snapshot','path':str(feature_path)})
    else:
        missing = [c for c in REQUIRED_FEATURE_COLUMNS if c not in feature_df.columns]
        if missing:
            blockers.append({'id':'missing_feature_columns','missing':missing,'path':str(feature_path),'columns':list(feature_df.columns)})
        feature_checks.append({'check':'feature_snapshot_readable','passed':True,'rows':len(feature_df),'path':str(feature_path)})
        feature_checks.append({'check':'required_columns_present','passed':not missing,'missing':','.join(missing)})
        if not missing:
            latest = feature_df.tail(1).iloc[0]
            for col in ['entry_dt','h1_close_time','d1_close_time','exported_at']:
                ok = pd.notna(pd.to_datetime(latest[col], errors='coerce'))
                feature_checks.append({'check':f'{col}_parseable','passed':bool(ok),'value':str(latest[col])})
                if not ok:
                    blockers.append({'id':f'{col}_not_parseable','value':str(latest[col])})
            closed = boolish(latest['is_closed'])
            feature_checks.append({'check':'latest_row_is_closed','passed':closed,'value':str(latest['is_closed'])})
            if not closed:
                blockers.append({'id':'latest_feature_row_not_closed','value':str(latest['is_closed'])})
            for col in ['m15_rsi14','h1_atr14','h1_range_atr','d1_atr14','d1_dist_atr']:
                val = num(latest[col])
                ok = math.isfinite(val)
                feature_checks.append({'check':f'{col}_finite','passed':ok,'value':val})
                if not ok:
                    blockers.append({'id':f'{col}_not_finite','value':str(latest[col])})
            rsi = num(latest['m15_rsi14']); h1r = num(latest['h1_range_atr']); d1d = num(latest['d1_dist_atr']); h1up = boolish(latest['h1_up'])
            candidate_specs = [
                ('P1_D1', d1d <= -1.641755654337, f'd1_dist_atr={d1d:.6f} <= -1.641756'),
                ('P3_RSI', rsi >= 73.861004, f'm15_rsi14={rsi:.6f} >= 73.861004'),
                ('P4_H1_D1_STRICT', (h1r <= 0.737217834712 and d1d <= -0.781481), f'h1_range_atr={h1r:.6f} <= 0.737218 and d1_dist_atr={d1d:.6f} <= -0.781481'),
                ('P5_H1UP_CUR', (h1up and d1d <= 1.247038 and h1r <= 0.744978), f'h1_up={h1up}; d1_dist_atr={d1d:.6f} <= 1.247038; h1_range_atr={h1r:.6f} <= 0.744978'),
            ]
            for lab, passed, detail in candidate_specs:
                candidate_rows.append({'candidate':lab,'passed':bool(passed),'detail':detail})

    for tf, fn in CANDLE_FILES.items():
        p = mt5 / fn
        df = read_csv_any(p)
        row = {'timeframe':tf,'file':fn,'path':str(p),'exists':p.exists(),'readable':not df.empty,'rows':int(len(df)) if not df.empty else 0,'required_columns_ok':False,'latest_time':'','duplicate_time_count':0}
        if df.empty:
            if tf in ['M15','H1','D1']:
                warnings.append({'id':f'{tf}_candle_csv_missing_or_unreadable','path':str(p)})
        else:
            miss = [c for c in CANDLE_COLUMNS if c not in df.columns]
            row['required_columns_ok'] = not miss
            if miss:
                warnings.append({'id':f'{tf}_candle_missing_columns','missing':miss,'path':str(p)})
            if 'time' in df.columns:
                t = pd.to_datetime(df['time'], errors='coerce')
                row['latest_time'] = str(df['time'].iloc[-1])
                row['duplicate_time_count'] = int(t.duplicated().sum())
                if row['duplicate_time_count']:
                    warnings.append({'id':f'{tf}_duplicate_time','count':row['duplicate_time_count']})
            if len(df) < 100 and tf in ['M15','H1','D1']:
                warnings.append({'id':f'{tf}_low_row_count','rows':len(df)})
        candle_checks.append(row)

    save(pd.DataFrame(feature_checks), out / 'gold_v3_174_feature_snapshot_checks.csv')
    save(pd.DataFrame(candle_checks), out / 'gold_v3_174_candle_input_checks.csv')
    save(pd.DataFrame(candidate_rows), out / 'gold_v3_174_feature_candidate_probe.csv')

    ready = len(blockers) == 0
    status = 'READY' if ready else 'BLOCKED'
    decision = 'FEATURE_SNAPSHOT_INPUT_READY' if ready else 'FEATURE_SNAPSHOT_INPUT_BLOCKED'
    latest_summary = {}
    if not feature_df.empty and all(c in feature_df.columns for c in REQUIRED_FEATURE_COLUMNS):
        latest = feature_df.tail(1).iloc[0]
        latest_summary = {c: str(latest[c]) for c in REQUIRED_FEATURE_COLUMNS}

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
        'latest_row_closed_required': True,
        'open_asof_allowed': False,
        'source_csv_mutated': False,
        'contract_mutated': False,
        'candidate_pool_removed': False,
        'f002_exclusion_bypassed': False,
        'final_live_enabled': False,
        'feature_rows': int(len(feature_df)) if not feature_df.empty else 0,
        'candidate_probe_passed_count': int(sum(1 for r in candidate_rows if r.get('passed'))),
        'blocker_count': len(blockers),
        'warning_count': len(warnings),
        'elapsed_seconds': round(time.time()-t0,2),
    }
    (out / 'gold_v3_174_summary.json').write_text(json.dumps({**summary,'blockers':blockers,'warnings':warnings,'latest':latest_summary}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_174_decision.csv')

    lines = []
    lines.append('GOLD V3 174 PASTE_ME_FEATURE_SNAPSHOT_INPUT_AUDIT')
    for k, v in summary.items():
        lines.append(f'{k}: {v}')
    lines += ['', 'LATEST_FEATURE_ROW']
    if latest_summary:
        for k, v in latest_summary.items():
            lines.append(f'{k}: {v}')
    else:
        lines.append('NO_LATEST_FEATURE_ROW')
    lines += ['', 'FEATURE_CHECKS', pd.DataFrame(feature_checks).to_string(index=False) if feature_checks else 'NO_FEATURE_CHECKS']
    lines += ['', 'CANDLE_INPUT_CHECKS', pd.DataFrame(candle_checks).to_string(index=False) if candle_checks else 'NO_CANDLE_CHECKS']
    lines += ['', 'CANDIDATE_PROBE', pd.DataFrame(candidate_rows).to_string(index=False) if candidate_rows else 'NO_CANDIDATE_PROBE']
    lines += ['', 'INTERPRETATION', 'Validates the EA-exported GOLD V3 feature snapshot and probes feature-only later candidates. Current bucket and P2_DEN still require policy_key/score reconstruction before full Stage170 parity.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    lines += ['', 'WARNINGS', 'NO_WARNINGS' if not warnings else json.dumps(warnings, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2

if __name__ == '__main__':
    raise SystemExit(main())
