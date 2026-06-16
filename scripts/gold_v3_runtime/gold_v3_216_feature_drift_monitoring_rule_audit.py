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

STEP = 'GOLD_V3_216_FEATURE_DRIFT_MONITORING_RULE_AUDIT_ONLY'


def progress(msg: str) -> None:
    print(f'[216 progress] {msg}', flush=True)


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


def txt(v: Any, default: str = '') -> str:
    if v is None:
        return default
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    x = str(v).strip()
    return default if x.lower() in {'', 'nan', 'nat', 'none'} else x


def flag(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return txt(v).lower() in {'true', '1', 'yes'}


def first(df: pd.DataFrame) -> dict[str, Any]:
    return df.iloc[0].to_dict() if not df.empty else {}


def monitor_rules() -> pd.DataFrame:
    return pd.DataFrame([
        {'rule_id': 'FD001', 'condition': 'tail_overlap_route_parity_pass == False', 'severity': 'BLOCK', 'action': 'stop live release review and investigate route mismatch'},
        {'rule_id': 'FD002', 'condition': 'feature drift exists and route parity pass == True', 'severity': 'WARN', 'action': 'record drift rows and continue audit-only review'},
        {'rule_id': 'FD003', 'condition': 'feature drift occurs on latest SIGNAL row', 'severity': 'REVIEW', 'action': 'manual review before enabling any send/order path'},
        {'rule_id': 'FD004', 'condition': 'feature drift warn repeats across multiple consecutive audits', 'severity': 'REVIEW', 'action': 'confirm H1/H4 closed-bar merge freshness and rerun parity'},
        {'rule_id': 'FD005', 'condition': 'NO_SIGNAL rows have feature drift but route stays NO_SIGNAL', 'severity': 'WARN', 'action': 'do not block, keep monitoring'},
    ])


def summarize_drift(drift: pd.DataFrame) -> pd.DataFrame:
    if drift.empty:
        return pd.DataFrame(columns=['feature', 'drift_rows', 'max_abs_diff', 'affected_final_routes'])
    x = drift.copy()
    x['abs_diff'] = pd.to_numeric(x.get('abs_diff', 0), errors='coerce').fillna(0.0)
    rows = []
    for feat, g in x.groupby('feature', dropna=False):
        routes = sorted(set(g.get('stage211_final_route', pd.Series(dtype=str)).astype(str).tolist()))
        rows.append({'feature': feat, 'drift_rows': int(len(g)), 'max_abs_diff': float(g['abs_diff'].max()), 'affected_final_routes': ','.join(routes)})
    return pd.DataFrame(rows)


def classify_current(d212: dict[str, Any], drift: pd.DataFrame) -> pd.DataFrame:
    route_pass = flag(d212.get('tail_overlap_route_parity_pass'))
    warn_rows = int(float(d212.get('feature_drift_warn_rows', 0) or 0))
    rows = []
    if not route_pass:
        rows.append({'current_case': 'ROUTE_PARITY_FAIL', 'severity': 'BLOCK', 'blocks_live_review': True, 'reason': 'route parity failed'})
    elif warn_rows > 0:
        signal_affected = False
        if not drift.empty and 'stage211_final_route' in drift.columns:
            signal_affected = drift['stage211_final_route'].astype(str).ne('NO_SIGNAL').any()
        rows.append({'current_case': 'FEATURE_DRIFT_ROUTE_PARITY_PASS', 'severity': 'REVIEW' if signal_affected else 'WARN', 'blocks_live_review': bool(signal_affected), 'reason': 'feature drift found but route parity passed'})
    else:
        rows.append({'current_case': 'NO_DRIFT_ROUTE_PARITY_PASS', 'severity': 'PASS', 'blocks_live_review': False, 'reason': 'no feature drift'})
    return pd.DataFrame(rows)


def validation(d212: dict[str, Any], current: pd.DataFrame, d215: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([
        {'check_id': 'F001', 'passed': flag(d212.get('ready')), 'details': 'Stage212 decision is ready'},
        {'check_id': 'F002', 'passed': flag(d212.get('tail_overlap_route_parity_pass')), 'details': 'route parity passed'},
        {'check_id': 'F003', 'passed': not current.empty, 'details': 'current drift case classified'},
        {'check_id': 'F004', 'passed': flag(d215.get('ready')), 'details': 'Stage215 signal replay ready'},
        {'check_id': 'F005', 'passed': True, 'details': 'send/order/import/payload/live hook remain disabled'},
    ])


def plan_md() -> str:
    return '''# GOLD V3 Stage216 Feature Drift Monitoring Rule Audit

Status: AUDIT_ONLY

Stage216 defines how feature drift warnings from Stage212 should be treated.

Policy:

- route parity mismatch is BLOCK
- feature drift with route parity pass is WARN
- feature drift on an actual SIGNAL row requires manual review before any send/order enablement
- repeated drift should trigger merge freshness investigation
- NO_SIGNAL rows with unchanged route do not block by themselves

This stage does not enable send, execution, actual import, payload, live hook, or autotrade.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '216'
    out.mkdir(parents=True, exist_ok=True)

    progress('load Stage212 and Stage215 outputs')
    blockers = []
    d212 = first(read_csv_any(root / '212' / 'gold_v3_212_decision.csv'))
    drift = read_csv_any(root / '212' / 'gold_v3_212_feature_drift_warning_rows.csv')
    d215 = first(read_csv_any(root / '215' / 'gold_v3_215_decision.csv'))
    if not d212:
        blockers.append({'id': 'missing_stage212_decision'})
    if not d215:
        blockers.append({'id': 'missing_stage215_decision'})

    rules = monitor_rules()
    drift_summary = summarize_drift(drift)
    current = classify_current(d212, drift) if d212 else pd.DataFrame()
    checks = validation(d212, current, d215)
    validation_pass = bool(checks['passed'].all()) if not checks.empty else False
    if not validation_pass:
        blockers.append({'id': 'feature_drift_monitor_validation_failed'})

    save(rules, out / 'gold_v3_216_feature_drift_monitoring_rules.csv')
    save(drift_summary, out / 'gold_v3_216_feature_drift_summary.csv')
    save(current, out / 'gold_v3_216_current_drift_classification.csv')
    save(checks, out / 'gold_v3_216_validation_checks.csv')
    (out / 'gold_v3_216_feature_drift_monitoring_plan.md').write_text(plan_md(), encoding='utf-8')

    ready = len(blockers) == 0
    cur = first(current)
    decision = 'STAGE216_FEATURE_DRIFT_MONITORING_RULE_READY_AUDIT_ONLY' if ready else 'STAGE216_BLOCKED'
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
        'stage212_decision': txt(d212.get('decision')),
        'stage212_route_parity_pass': flag(d212.get('tail_overlap_route_parity_pass')),
        'stage212_feature_drift_warn_rows': int(float(d212.get('feature_drift_warn_rows', 0) or 0)) if d212 else 0,
        'current_drift_case': txt(cur.get('current_case')),
        'current_drift_severity': txt(cur.get('severity')),
        'current_drift_blocks_live_review': flag(cur.get('blocks_live_review')),
        'monitor_rule_rows': int(len(rules)),
        'validation_pass': validation_pass,
        'live_release_ready': False,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_216_decision.csv')
    (out / 'gold_v3_216_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 216 PASTE_ME_FEATURE_DRIFT_MONITORING_RULE_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'FEATURE_DRIFT_MONITORING_PLAN_MD', plan_md()]
    lines += ['', 'FEATURE_DRIFT_MONITORING_RULES', show(rules, 80)]
    lines += ['', 'FEATURE_DRIFT_SUMMARY', show(drift_summary, 80)]
    lines += ['', 'CURRENT_DRIFT_CLASSIFICATION', show(current, 40)]
    lines += ['', 'VALIDATION_CHECKS', show(checks, 80)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage216 is audit-only. It defines when feature drift is WARN, REVIEW, or BLOCK.']
    lines += ['Current case is based on Stage212 route parity and feature drift warning rows.']
    lines += ['No send, execution, actual import, payload, live hook, or autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
