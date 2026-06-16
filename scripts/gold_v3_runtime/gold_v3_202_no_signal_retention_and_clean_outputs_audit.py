#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_202_NO_SIGNAL_RETENTION_AND_CLEAN_OUTPUTS_AUDIT_ONLY'
SECONDARY_CLASS = 'SECONDARY_AUDIT_CANDIDATE'


STRING_SIGNAL_COLS = [
    'primary_candidate_id', 'primary_signal', 'secondary_candidate_id', 'secondary_signal',
    'final_route', 'send_action', 'candidate', 'direction', 'role'
]
NUMERIC_DISPLAY_COLS = [
    'primary_tp', 'primary_sl', 'primary_horizon_m5', 'secondary_tp', 'secondary_sl', 'secondary_horizon_m5',
    'tp', 'sl', 'horizon_m5', 'primary_priority_score', 'secondary_priority_score'
]


def progress(msg: str) -> None:
    print(f'[202 progress] {msg}', flush=True)


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ['utf-8-sig', 'utf-8', 'cp932']:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            pass
    return pd.DataFrame()


def is_missing(v: Any) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except Exception:
        pass
    s = str(v).strip()
    return s == '' or s.lower() in {'nan', 'nat', 'none'}


def clean_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = df.copy()
    for col in x.columns:
        if col in STRING_SIGNAL_COLS or col.endswith('_candidate_id') or col.endswith('_signal'):
            x[col] = x[col].apply(lambda v: 'NO_SIGNAL' if is_missing(v) else str(v))
        elif col in NUMERIC_DISPLAY_COLS or col.endswith('_tp') or col.endswith('_sl') or col.endswith('_horizon_m5') or col.endswith('_priority_score'):
            x[col] = x[col].apply(lambda v: '-' if is_missing(v) else v)
        else:
            x[col] = x[col].apply(lambda v: '' if is_missing(v) else v)
    return x


def contains_bad_text(df: pd.DataFrame) -> dict[str, bool]:
    if df.empty:
        return {'nan': False, 'legacy_secondary_label': False}
    text = df.to_csv(index=False).lower()
    return {
        'nan': 'nan' in text,
        'legacy_secondary_label': 'watchlist' in text,
    }


def build_retention_policy() -> str:
    return '''# GOLD V3 Stage202 No-Signal Retention Policy

Status: AUDIT_ONLY

## Recommended live retention model

Do not append every NO_SIGNAL row forever.

Use this structure instead:

1. `latest_state.json`
   - overwritten every evaluation
   - contains latest closed M15 timestamp, PRIMARY route, SECONDARY_AUDIT_CANDIDATE route, and safety flags

2. `signal_events.csv`
   - append only when PRIMARY or SECONDARY_AUDIT_CANDIDATE signal exists
   - contains entry timestamp, role, candidate, direction, TP, SL, horizon, and decision route

3. `no_signal_counters_daily.csv`
   - one row per date / role / route
   - count NO_SIGNAL evaluations without storing every full row

4. `health_rollup_daily.csv`
   - one row per date
   - counts evaluated closed bars, signal bars, NO_SIGNAL bars, missing-data bars, and blocker bars

5. `debug_tail_snapshot.csv`
   - rolling last N rows only, for example last 96 or last 500 closed M15 evaluations
   - overwritten or rotated; not an infinite append log

## Rationale

Storing every NO_SIGNAL row is useful during audit, but it can grow files quickly in live operation.

Counting NO_SIGNAL by day/hour gives enough information for health monitoring:

- detector is running
- closed bars are being evaluated
- signal frequency is not unexpectedly zero
- missing data or blockers can be noticed

Signal rows should be retained in detail because they define action candidates. NO_SIGNAL rows should usually be retained as aggregates plus a small rolling debug sample.

## Required safety behavior

- NO_SIGNAL sends nothing.
- NO_SIGNAL does not create an order.
- NO_SIGNAL does not create a live payload.
- PRIMARY remains the main route.
- SECONDARY_AUDIT_CANDIDATE remains secondary until explicit later approval.
'''


def daily_counter_from_tail(tail: pd.DataFrame) -> pd.DataFrame:
    if tail.empty or 'dt' not in tail.columns:
        return pd.DataFrame()
    x = tail.copy()
    x['dt'] = pd.to_datetime(x['dt'])
    x['date'] = x['dt'].dt.date.astype(str)
    x['hour'] = x['dt'].dt.hour.astype(int)
    rows = []
    for (date, hour), g in x.groupby(['date', 'hour'], sort=True):
        primary_no = int(g.get('primary_signal', pd.Series(dtype=str)).astype(str).eq('NO_SIGNAL').sum()) if 'primary_signal' in g.columns else int(len(g))
        secondary_no = int(g.get('secondary_signal', pd.Series(dtype=str)).astype(str).eq('NO_SIGNAL').sum()) if 'secondary_signal' in g.columns else int(len(g))
        final_no = int(g.get('final_route', pd.Series(dtype=str)).astype(str).eq('NO_SIGNAL').sum()) if 'final_route' in g.columns else int(len(g))
        rows.append({
            'date': date,
            'hour': hour,
            'evaluated_closed_m15_rows': int(len(g)),
            'primary_no_signal_count': primary_no,
            'secondary_no_signal_count': secondary_no,
            'final_no_signal_count': final_no,
            'final_signal_count': int(len(g) - final_no),
        })
    return pd.DataFrame(rows)


def health_rollup_from_tail(tail: pd.DataFrame) -> pd.DataFrame:
    if tail.empty or 'dt' not in tail.columns:
        return pd.DataFrame()
    x = tail.copy()
    x['dt'] = pd.to_datetime(x['dt'])
    x['date'] = x['dt'].dt.date.astype(str)
    rows = []
    for date, g in x.groupby('date', sort=True):
        final_no = int(g.get('final_route', pd.Series(dtype=str)).astype(str).eq('NO_SIGNAL').sum()) if 'final_route' in g.columns else int(len(g))
        rows.append({
            'date': date,
            'evaluated_closed_m15_rows': int(len(g)),
            'final_no_signal_count': final_no,
            'final_signal_count': int(len(g) - final_no),
            'primary_signal_count': int(g.get('primary_signal', pd.Series(dtype=str)).astype(str).ne('NO_SIGNAL').sum()) if 'primary_signal' in g.columns else 0,
            'secondary_signal_count': int(g.get('secondary_signal', pd.Series(dtype=str)).astype(str).ne('NO_SIGNAL').sum()) if 'secondary_signal' in g.columns else 0,
            'blocker_count': 0,
        })
    return pd.DataFrame(rows)


def latest_state_from_latest(latest: pd.DataFrame, decision: pd.DataFrame) -> dict[str, Any]:
    row = latest.iloc[0].to_dict() if not latest.empty else {}
    drow = decision.iloc[0].to_dict() if not decision.empty else {}
    return {
        'latest_closed_m15_dt': row.get('dt', drow.get('latest_closed_m15_dt', '')),
        'final_route': row.get('final_route', drow.get('latest_final_route', 'NO_SIGNAL')),
        'primary_signal': row.get('primary_signal', drow.get('latest_primary_signal', 'NO_SIGNAL')),
        'primary_candidate_id': row.get('primary_candidate_id', ''),
        'secondary_signal': row.get('secondary_signal', drow.get('latest_secondary_signal', 'NO_SIGNAL')),
        'secondary_candidate_id': row.get('secondary_candidate_id', ''),
        'send_action': row.get('send_action', 'NO_SEND_AUDIT_ONLY'),
        'audit_only': True,
        'send_enabled': False,
        'discord_enabled': False,
        'mt5_order_enabled': False,
        'payload_enabled': False,
        'live_hook_enabled': False,
        'autotrade_enabled': False,
        'no_signal_discord_notify': False,
    }


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '202'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage201/Stage200 outputs')
    latest = read_csv_any(root / '201' / 'gold_v3_201_latest_compact_preview.csv')
    tail_signal = read_csv_any(root / '201' / 'gold_v3_201_tail96_signal_rows_compact.csv')
    role_preview = read_csv_any(root / '201' / 'gold_v3_201_latest_role_preview.csv')
    stage201_decision = read_csv_any(root / '201' / 'gold_v3_201_decision.csv')
    stage200_tail = read_csv_any(root / '200' / 'gold_v3_200_no_send_latest_tail96.csv')
    if latest.empty:
        blockers.append({'id': 'missing_stage201_latest_compact_preview'})
    if role_preview.empty:
        blockers.append({'id': 'missing_stage201_latest_role_preview'})
    if stage201_decision.empty:
        blockers.append({'id': 'missing_stage201_decision'})
    if stage200_tail.empty:
        blockers.append({'id': 'missing_stage200_tail96'})

    latest_clean = pd.DataFrame()
    tail_signal_clean = pd.DataFrame()
    role_clean = pd.DataFrame()
    daily_counter = pd.DataFrame()
    health_rollup = pd.DataFrame()
    latest_state: dict[str, Any] = {}
    policy = build_retention_policy()

    if not blockers:
        latest_clean = clean_display_df(latest)
        tail_signal_clean = clean_display_df(tail_signal)
        role_clean = clean_display_df(role_preview)
        save(latest_clean, out / 'gold_v3_202_latest_compact_preview_clean.csv')
        save(tail_signal_clean, out / 'gold_v3_202_tail96_signal_rows_compact_clean.csv')
        save(role_clean, out / 'gold_v3_202_latest_role_preview_clean.csv')
        daily_counter = daily_counter_from_tail(clean_display_df(stage200_tail))
        health_rollup = health_rollup_from_tail(clean_display_df(stage200_tail))
        save(daily_counter, out / 'gold_v3_202_no_signal_counters_daily_hourly_from_tail96.csv')
        save(health_rollup, out / 'gold_v3_202_health_rollup_daily_from_tail96.csv')
        latest_state = latest_state_from_latest(latest_clean, stage201_decision)
        (out / 'gold_v3_202_latest_state_sample.json').write_text(json.dumps(latest_state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        (out / 'gold_v3_202_no_signal_retention_policy.md').write_text(policy, encoding='utf-8')

    bad_latest = contains_bad_text(latest_clean)
    bad_tail = contains_bad_text(tail_signal_clean)
    bad_role = contains_bad_text(role_clean)
    any_nan = bool(bad_latest['nan'] or bad_tail['nan'] or bad_role['nan'])
    any_legacy = bool(bad_latest['legacy_secondary_label'] or bad_tail['legacy_secondary_label'] or bad_role['legacy_secondary_label'])
    ready = len(blockers) == 0 and not any_nan and not any_legacy
    decision = 'STAGE202_NO_SIGNAL_RETENTION_AND_CLEAN_OUTPUTS_PASS_AUDIT_ONLY' if ready else ('STAGE202_READY_WITH_FORMAT_WARNINGS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE202_BLOCKED')

    summary = {
        'step': STEP,
        'status': 'READY' if len(blockers) == 0 else 'BLOCKED',
        'ready': len(blockers) == 0,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'clean_output_pass': bool(ready),
        'nan_string_present_in_clean_csv_outputs': bool(any_nan),
        'legacy_secondary_label_present_in_clean_csv_outputs': bool(any_legacy),
        'latest_closed_m15_dt': str(latest_state.get('latest_closed_m15_dt', '')),
        'latest_final_route': str(latest_state.get('final_route', 'NO_SIGNAL')),
        'recommended_no_signal_live_storage': 'Do not append every NO_SIGNAL full row indefinitely. Store latest_state overwrite, append signal events only, keep daily/hourly NO_SIGNAL counters, daily health rollup, and a rolling debug tail.',
        'no_signal_event_rows_should_be_appended': False,
        'signal_event_rows_should_be_appended': True,
        'no_signal_counter_rows_should_be_incremented': True,
        'rolling_debug_tail_recommended': True,
        'rolling_debug_tail_suggested_rows': 500,
        'cost_interpretation': 'cost5 is an all-in worse-execution stress proxy, including wider spread, slippage, commission conversion, and execution drag. It is not spread-only.',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_202_decision.csv')
    (out / 'gold_v3_202_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 202 PASTE_ME_NO_SIGNAL_RETENTION_AND_CLEAN_OUTPUTS_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'NO_SIGNAL_RETENTION_POLICY_MD', policy]
    lines += ['', 'LATEST_ROLE_PREVIEW_CLEAN', show(role_clean, 20)]
    lines += ['', 'LATEST_COMPACT_PREVIEW_CLEAN', show(latest_clean, 20)]
    lines += ['', 'TAIL96_SIGNAL_ROWS_COMPACT_CLEAN', show(tail_signal_clean, 80)]
    lines += ['', 'NO_SIGNAL_COUNTERS_DAILY_HOURLY_FROM_TAIL96', show(daily_counter, 80)]
    lines += ['', 'HEALTH_ROLLUP_DAILY_FROM_TAIL96', show(health_rollup, 80)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage202 is audit-only. It cleans display CSV outputs and defines a practical NO_SIGNAL retention policy.',
        'Recommended live storage: append detailed signal events, aggregate NO_SIGNAL counts, overwrite latest state, and keep only a rolling debug tail.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
