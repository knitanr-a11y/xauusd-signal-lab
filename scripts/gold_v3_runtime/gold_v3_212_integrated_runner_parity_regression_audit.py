#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_212_INTEGRATED_RUNNER_PARITY_REGRESSION_AUDIT_ONLY'


def progress(msg: str) -> None:
    print(f'[212 progress] {msg}', flush=True)


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


def read_json_any(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def s(v: Any, default: str = '') -> str:
    if v is None:
        return default
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    t = str(v).strip()
    return default if t.lower() in {'', 'nan', 'nat', 'none'} else t


def i(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def d(v: Any) -> pd.Timestamp | None:
    try:
        if s(v) == '':
            return None
        return pd.Timestamp(v)
    except Exception:
        return None


def first(df: pd.DataFrame) -> dict[str, Any]:
    return df.iloc[0].to_dict() if not df.empty else {}


def source_presence(root: Path) -> pd.DataFrame:
    files = [
        ('stage200_decision', root / '200' / 'gold_v3_200_decision.csv'),
        ('stage200_tail96', root / '200' / 'gold_v3_200_no_send_latest_tail96.csv'),
        ('stage209_decision', root / '209' / 'gold_v3_209_decision.csv'),
        ('stage209_latest_state', root / '209' / 'gold_v3_209_latest_state_cycle_sample.json'),
        ('stage210_decision', root / '210' / 'gold_v3_210_decision.csv'),
        ('stage210_write_plan', root / '210' / 'gold_v3_210_live_cycle_write_plan.csv'),
        ('stage211_decision', root / '211' / 'gold_v3_211_decision.csv'),
        ('stage211_tail96', root / '211' / 'gold_v3_211_integrated_tail96.csv'),
        ('stage211_latest_state', root / '211' / 'gold_v3_211_latest_state_integrated_preview.json'),
        ('stage211_write_plan', root / '211' / 'gold_v3_211_integrated_write_plan.csv'),
    ]
    return pd.DataFrame([{'source': name, 'path': str(path), 'exists': path.exists()} for name, path in files])


def latest_summary(d200: dict[str, Any], d209: dict[str, Any], d210: dict[str, Any], d211: dict[str, Any]) -> pd.DataFrame:
    rows = []
    rows.append({
        'stage': '200_no_send_packet',
        'latest_dt': s(d200.get('latest_closed_m15_dt')),
        'final_route': s(d200.get('latest_final_route'), 'NO_SIGNAL'),
        'primary_signal_rows_tail96': i(d200.get('tail96_primary_signal_rows')),
        'secondary_signal_rows_tail96': i(d200.get('tail96_secondary_signal_rows')),
        'final_signal_rows_tail96': i(d200.get('tail96_final_route_signal_rows')),
    })
    rows.append({
        'stage': '209_cycle_packet_from_stage200',
        'latest_dt': s(d209.get('latest_closed_m15_dt')),
        'final_route': s(d209.get('latest_final_route'), 'NO_SIGNAL'),
        'primary_signal_rows_tail96': '',
        'secondary_signal_rows_tail96': '',
        'final_signal_rows_tail96': '',
    })
    rows.append({
        'stage': '210_writer_preview_from_stage209',
        'latest_dt': s(d210.get('latest_closed_m15_dt')),
        'final_route': s(d210.get('latest_final_route'), 'NO_SIGNAL'),
        'primary_signal_rows_tail96': '',
        'secondary_signal_rows_tail96': '',
        'final_signal_rows_tail96': '',
    })
    rows.append({
        'stage': '211_integrated_from_ohlc',
        'latest_dt': s(d211.get('latest_closed_m15_dt')),
        'final_route': s(d211.get('latest_final_route'), 'NO_SIGNAL'),
        'primary_signal_rows_tail96': i(d211.get('tail96_primary_signal_rows')),
        'secondary_signal_rows_tail96': i(d211.get('tail96_secondary_signal_rows')),
        'final_signal_rows_tail96': i(d211.get('tail96_final_signal_rows')),
    })
    return pd.DataFrame(rows)


def classify_freshness(latest: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ref = latest[latest['stage'].eq('211_integrated_from_ohlc')]
    ref_dt = d(ref.iloc[0]['latest_dt']) if not ref.empty else None
    ref_route = s(ref.iloc[0]['final_route']) if not ref.empty else ''
    for _, r in latest.iterrows():
        st = s(r['stage'])
        cur_dt = d(r['latest_dt'])
        cur_route = s(r['final_route'])
        if st == '211_integrated_from_ohlc':
            cls = 'REFERENCE'
            passed = True
            note = 'integrated runner reference'
        elif cur_dt is None or ref_dt is None:
            cls = 'MISSING_DT'
            passed = False
            note = 'cannot compare freshness without dt'
        elif cur_dt == ref_dt:
            cls = 'SAME_DT_ROUTE_MATCH' if cur_route == ref_route else 'SAME_DT_ROUTE_MISMATCH'
            passed = cur_route == ref_route
            note = 'same latest closed dt, route must match'
        elif cur_dt < ref_dt:
            cls = 'INPUT_FRESHNESS_DRIFT_ACCEPTED'
            passed = True
            note = 'older split-stage output compared to newer integrated OHLC run'
        else:
            cls = 'REFERENCE_OLDER_THAN_SPLIT_STAGE'
            passed = False
            note = 'integrated runner should not be older than split-stage output'
        rows.append({
            'stage': st,
            'stage_latest_dt': s(r['latest_dt']),
            'stage_final_route': cur_route,
            'integrated_latest_dt': str(ref_dt) if ref_dt is not None else '',
            'integrated_final_route': ref_route,
            'classification': cls,
            'passed': passed,
            'note': note,
        })
    return pd.DataFrame(rows)


def overlap_parity(t200: pd.DataFrame, t211: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if t200.empty or t211.empty:
        return pd.DataFrame(), pd.DataFrame([{'check': 'tail_overlap_available', 'passed': False, 'details': 'missing tail data'}])
    a = t200.copy()
    b = t211.copy()
    a['dt_key'] = pd.to_datetime(a['dt'])
    b['dt_key'] = pd.to_datetime(b['dt'])
    cols = ['dt_key', 'primary_signal', 'secondary_signal', 'final_route', 'primary_candidate_id', 'secondary_candidate_id', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']
    aa = a[[c for c in cols if c in a.columns]].copy()
    bb = b[[c for c in cols if c in b.columns]].copy()
    merged = aa.merge(bb, on='dt_key', how='inner', suffixes=('_stage200', '_stage211'))
    if merged.empty:
        return merged, pd.DataFrame([{'check': 'tail_overlap_available', 'passed': False, 'details': 'no overlapping dt rows'}])
    checks = []
    for col in ['primary_signal', 'secondary_signal', 'final_route']:
        left = f'{col}_stage200'
        right = f'{col}_stage211'
        if left in merged.columns and right in merged.columns:
            mismatch = merged[merged[left].astype(str).fillna('') != merged[right].astype(str).fillna('')]
            checks.append({'check': f'overlap_{col}_parity', 'passed': mismatch.empty, 'mismatch_rows': int(len(mismatch)), 'details': f'{col} must match on overlapping dt rows'})
    for col in ['m15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']:
        left = f'{col}_stage200'
        right = f'{col}_stage211'
        if left in merged.columns and right in merged.columns:
            lnum = pd.to_numeric(merged[left], errors='coerce')
            rnum = pd.to_numeric(merged[right], errors='coerce')
            diff = (lnum - rnum).abs()
            mismatch = merged[diff.fillna(0.0) > 1e-9]
            checks.append({'check': f'overlap_{col}_parity', 'passed': mismatch.empty, 'mismatch_rows': int(len(mismatch)), 'details': f'{col} must match on overlapping dt rows'})
    checks.append({'check': 'tail_overlap_rows', 'passed': True, 'mismatch_rows': 0, 'details': f'overlap_rows={len(merged)}'})
    return merged, pd.DataFrame(checks)


def writer_policy_parity(d210: dict[str, Any], d211: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for stage, dct in [('210_split_writer', d210), ('211_integrated_writer', d211)]:
        route = s(dct.get('latest_final_route'), 'NO_SIGNAL')
        no_signal = route == 'NO_SIGNAL'
        sig_rows = i(dct.get('trade_signal_append_preview_rows'))
        if stage == '210_split_writer':
            notif_rows = i(dct.get('notification_append_preview_rows'))
            counter_rows = i(dct.get('no_signal_counter_increment_preview_rows'))
        else:
            notif_rows = i(dct.get('notification_append_preview_rows'))
            counter_rows = i(dct.get('no_signal_counter_preview_rows'))
        rows.append({
            'stage': stage,
            'latest_dt': s(dct.get('latest_closed_m15_dt')),
            'route': route,
            'expected_signal_append_rows_for_route': 0 if no_signal else 1,
            'actual_signal_append_rows': sig_rows,
            'expected_notification_append_rows_for_route': 0 if no_signal else 1,
            'actual_notification_append_rows': notif_rows,
            'expected_counter_rows_for_route': 1,
            'actual_counter_rows': counter_rows,
            'policy_pass': ((not no_signal) or (sig_rows == 0 and notif_rows == 0 and counter_rows == 1)) and (no_signal or (sig_rows >= 1 and notif_rows >= 1)),
        })
    return pd.DataFrame(rows)


def state_parity(d211: dict[str, Any], state211: dict[str, Any]) -> pd.DataFrame:
    rows = []
    pairs = [
        ('latest_closed_m15_dt', 'latest_closed_m15_dt'),
        ('latest_final_route', 'final_route'),
        ('latest_signal_id', 'signal_id'),
        ('latest_short_signal_id', 'short_signal_id'),
    ]
    for dkey, skey in pairs:
        dv = s(d211.get(dkey))
        sv = s(state211.get(skey))
        rows.append({'field': dkey, 'decision_value': dv, 'state_value': sv, 'passed': dv == sv, 'note': 'decision and latest_state must match'})
    return pd.DataFrame(rows)


def plan_md() -> str:
    return '''# GOLD V3 Stage212 Integrated Runner Parity and Regression Audit

Status: AUDIT_ONLY

Stage212 compares the split-stage dry-run outputs with the Stage211 integrated OHLC runner output.

Comparison policy:

- If latest closed timestamps are the same, final route must match.
- If Stage211 is newer because OHLC was refreshed, classify as input freshness drift, not a blocker.
- On overlapping tail rows, detector route and feature values must match exactly.
- Writer policy must remain consistent: NO_SIGNAL creates no signal/notification append rows and increments counter.

No send, execution, actual import, payload, live hook, or autotrade is enabled.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '212'
    out.mkdir(parents=True, exist_ok=True)

    progress('load split and integrated outputs')
    blockers: list[dict[str, Any]] = []
    presence = source_presence(root)
    required_missing = presence[~presence['exists']].copy()
    if not required_missing.empty:
        blockers.append({'id': 'missing_required_outputs', 'count': int(len(required_missing)), 'missing': required_missing['source'].tolist()})

    d200_df = read_csv_any(root / '200' / 'gold_v3_200_decision.csv')
    d209_df = read_csv_any(root / '209' / 'gold_v3_209_decision.csv')
    d210_df = read_csv_any(root / '210' / 'gold_v3_210_decision.csv')
    d211_df = read_csv_any(root / '211' / 'gold_v3_211_decision.csv')
    t200 = read_csv_any(root / '200' / 'gold_v3_200_no_send_latest_tail96.csv')
    t211 = read_csv_any(root / '211' / 'gold_v3_211_integrated_tail96.csv')
    state211 = read_json_any(root / '211' / 'gold_v3_211_latest_state_integrated_preview.json')

    d200, d209, d210, d211 = first(d200_df), first(d209_df), first(d210_df), first(d211_df)
    latest = latest_summary(d200, d209, d210, d211)
    freshness = classify_freshness(latest)
    overlap, overlap_checks = overlap_parity(t200, t211)
    writer = writer_policy_parity(d210, d211)
    state = state_parity(d211, state211)

    save(presence, out / 'gold_v3_212_source_presence.csv')
    save(latest, out / 'gold_v3_212_latest_summary_comparison.csv')
    save(freshness, out / 'gold_v3_212_freshness_classification.csv')
    save(overlap, out / 'gold_v3_212_tail_overlap_rows.csv')
    save(overlap_checks, out / 'gold_v3_212_tail_overlap_parity_checks.csv')
    save(writer, out / 'gold_v3_212_writer_policy_parity.csv')
    save(state, out / 'gold_v3_212_integrated_state_parity.csv')
    (out / 'gold_v3_212_integrated_runner_parity_plan.md').write_text(plan_md(), encoding='utf-8')

    freshness_pass = bool(freshness['passed'].all()) if not freshness.empty else False
    overlap_pass = bool(overlap_checks['passed'].all()) if not overlap_checks.empty else False
    writer_pass = bool(writer['policy_pass'].all()) if not writer.empty else False
    state_pass = bool(state['passed'].all()) if not state.empty else False

    if not freshness_pass:
        blockers.append({'id': 'freshness_or_route_parity_failed'})
    if not overlap_pass:
        blockers.append({'id': 'tail_overlap_parity_failed'})
    if not writer_pass:
        blockers.append({'id': 'writer_policy_parity_failed'})
    if not state_pass:
        blockers.append({'id': 'integrated_state_parity_failed'})

    ready = len(blockers) == 0
    decision = 'STAGE212_INTEGRATED_RUNNER_PARITY_REGRESSION_PASS_AUDIT_ONLY' if ready else 'STAGE212_BLOCKED'
    stage211_dt = s(d211.get('latest_closed_m15_dt'))
    stage200_dt = s(d200.get('latest_closed_m15_dt'))
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'dry_run_only': True,
        'stage200_latest_dt': stage200_dt,
        'stage211_latest_dt': stage211_dt,
        'latest_dt_same': stage200_dt == stage211_dt,
        'freshness_classification_pass': freshness_pass,
        'tail_overlap_rows': int(len(overlap)) if not overlap.empty else 0,
        'tail_overlap_parity_pass': overlap_pass,
        'writer_policy_parity_pass': writer_pass,
        'integrated_state_parity_pass': state_pass,
        'stage211_latest_final_route': s(d211.get('latest_final_route'), 'NO_SIGNAL'),
        'stage211_trade_signal_append_preview_rows': i(d211.get('trade_signal_append_preview_rows')),
        'stage211_notification_append_preview_rows': i(d211.get('notification_append_preview_rows')),
        'stage211_no_signal_counter_preview_rows': i(d211.get('no_signal_counter_preview_rows')),
        'source_csv_mutated': False,
        'contract_mutated': False,
        'open_asof_allowed': False,
        'candidate_pool_removed': False,
        'f002_exclusion_bypassed': False,
        'final_live_enabled': False,
        'send_enabled': False,
        'execution_enabled': False,
        'actual_order_import_enabled': False,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_212_decision.csv')
    (out / 'gold_v3_212_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 212 PASTE_ME_INTEGRATED_RUNNER_PARITY_REGRESSION_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'INTEGRATED_RUNNER_PARITY_PLAN_MD', plan_md()]
    lines += ['', 'LATEST_SUMMARY_COMPARISON', show(latest, 20)]
    lines += ['', 'FRESHNESS_CLASSIFICATION', show(freshness, 20)]
    lines += ['', 'TAIL_OVERLAP_PARITY_CHECKS', show(overlap_checks, 80)]
    lines += ['', 'WRITER_POLICY_PARITY', show(writer, 20)]
    lines += ['', 'INTEGRATED_STATE_PARITY', show(state, 20)]
    lines += ['', 'SOURCE_PRESENCE', show(presence, 40)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage212 is audit-only. It compares split-stage outputs with Stage211 integrated OHLC runner outputs.']
    lines += ['Different latest dt caused by newer OHLC input is classified as input freshness drift, not a blocker.']
    lines += ['Overlapping tail rows must match exactly for detector routes/features.']
    lines += ['No send, execution, actual import, payload, live hook, or autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
