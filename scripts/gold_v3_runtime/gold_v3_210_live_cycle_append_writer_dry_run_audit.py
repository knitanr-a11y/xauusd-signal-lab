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

STEP = 'GOLD_V3_210_LIVE_CYCLE_APPEND_WRITER_DRY_RUN_AUDIT_ONLY'
ROLLING_DEBUG_TAIL_ROWS = 500


def progress(msg: str) -> None:
    print(f'[210 progress] {msg}', flush=True)


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


def build_write_plan(final_route: str, signal_rows: int, notif_rows: int, counter_rows: int) -> pd.DataFrame:
    no_signal = final_route == 'NO_SIGNAL'
    rows = [
        {
            'target_file': 'latest_state.json',
            'write_mode': 'overwrite',
            'rows_or_objects': 1,
            'enabled_in_dry_run': True,
            'enabled_in_live_after_approval': True,
            'reason': 'latest evaluation state should stay compact',
        },
        {
            'target_file': 'trade_signal_ledger.csv',
            'write_mode': 'append_if_signal_only',
            'rows_or_objects': signal_rows,
            'enabled_in_dry_run': True,
            'enabled_in_live_after_approval': True,
            'reason': 'append only signal rows; no NO_SIGNAL full rows',
        },
        {
            'target_file': 'notification_events_rolling_30d.csv',
            'write_mode': 'append_if_signal_only_no_send_until_enabled',
            'rows_or_objects': notif_rows,
            'enabled_in_dry_run': True,
            'enabled_in_live_after_approval': True,
            'reason': 'record notification candidates separately from sending',
        },
        {
            'target_file': 'no_signal_counters_daily_hourly.csv',
            'write_mode': 'increment_or_append_counter',
            'rows_or_objects': counter_rows,
            'enabled_in_dry_run': True,
            'enabled_in_live_after_approval': True,
            'reason': 'NO_SIGNAL is counted, not appended as full event rows',
        },
        {
            'target_file': 'debug_tail_snapshot.csv',
            'write_mode': f'rolling_last_{ROLLING_DEBUG_TAIL_ROWS}',
            'rows_or_objects': ROLLING_DEBUG_TAIL_ROWS,
            'enabled_in_dry_run': True,
            'enabled_in_live_after_approval': True,
            'reason': 'bounded diagnostics only',
        },
        {
            'target_file': 'health_rollup_daily.csv',
            'write_mode': 'daily_rollup_increment',
            'rows_or_objects': 1,
            'enabled_in_dry_run': True,
            'enabled_in_live_after_approval': True,
            'reason': 'monitor evaluated/signal/no_signal counts',
        },
        {
            'target_file': 'actual_execution_ledger.csv',
            'write_mode': 'no_write_until_actual_import_stage',
            'rows_or_objects': 0,
            'enabled_in_dry_run': False,
            'enabled_in_live_after_approval': False,
            'reason': 'actual execution import remains disabled here',
        },
    ]
    for r in rows:
        r['latest_final_route'] = final_route
        r['no_signal_cycle'] = no_signal
        r['audit_only'] = True
    return pd.DataFrame(rows)


def build_health_rollup(counter: pd.DataFrame, summary209: dict[str, Any]) -> pd.DataFrame:
    cols = [
        'date', 'evaluated_closed_m15_rows', 'final_signal_rows', 'final_no_signal_rows',
        'primary_no_signal_rows', 'secondary_no_signal_rows', 'blocker_rows',
        'send_rows', 'execution_rows', 'actual_import_rows', 'latest_closed_m15_dt',
        'updated_at_utc', 'audit_only'
    ]
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    if counter.empty:
        return pd.DataFrame(columns=cols)
    c = counter.iloc[0]
    return pd.DataFrame([{
        'date': s(c.get('date')),
        'evaluated_closed_m15_rows': int(c.get('evaluated_closed_m15_rows', 0)),
        'final_signal_rows': int(c.get('final_signal_increment', 0)),
        'final_no_signal_rows': int(c.get('final_no_signal_increment', 0)),
        'primary_no_signal_rows': int(c.get('primary_no_signal_increment', 0)),
        'secondary_no_signal_rows': int(c.get('secondary_no_signal_increment', 0)),
        'blocker_rows': int(summary209.get('blocker_count', 0)),
        'send_rows': 0,
        'execution_rows': 0,
        'actual_import_rows': 0,
        'latest_closed_m15_dt': s(summary209.get('latest_closed_m15_dt')),
        'updated_at_utc': now,
        'audit_only': True,
    }], columns=cols)


def build_writer_checks(summary209: dict[str, Any], signal_append: pd.DataFrame, notif_append: pd.DataFrame, counter: pd.DataFrame) -> pd.DataFrame:
    final_route = s(summary209.get('latest_final_route'), 'NO_SIGNAL')
    no_signal = final_route == 'NO_SIGNAL'
    rows = [
        {'check_id': 'W001', 'passed': True, 'details': 'latest_state overwrite sample is created'},
        {'check_id': 'W002', 'passed': bool((not no_signal) or signal_append.empty), 'details': 'NO_SIGNAL must not create trade_signal append rows'},
        {'check_id': 'W003', 'passed': bool((not no_signal) or notif_append.empty), 'details': 'NO_SIGNAL must not create notification append rows'},
        {'check_id': 'W004', 'passed': bool((not no_signal) or not counter.empty), 'details': 'NO_SIGNAL must create/increment counter row'},
        {'check_id': 'W005', 'passed': True, 'details': 'send remains disabled'},
        {'check_id': 'W006', 'passed': True, 'details': 'execution remains disabled'},
        {'check_id': 'W007', 'passed': True, 'details': 'actual import remains disabled'},
        {'check_id': 'W008', 'passed': True, 'details': 'debug tail is rolling/bounded'},
    ]
    return pd.DataFrame(rows)


def build_plan_md() -> str:
    return '''# GOLD V3 Stage210 Live-Cycle Append Writer Dry-Run

Status: AUDIT_ONLY

Stage210 converts the Stage209 one-cycle packet into write-target previews.

It does not mutate the live retention files.

Write policy:

- `latest_state.json`: overwrite every cycle
- `trade_signal_ledger.csv`: append only when final route is SIGNAL
- `notification_events_rolling_30d.csv`: append only when final route is SIGNAL, but sending remains disabled
- `no_signal_counters_daily_hourly.csv`: increment or append counter row when final route is NO_SIGNAL
- `debug_tail_snapshot.csv`: rolling bounded diagnostics
- `health_rollup_daily.csv`: daily evaluated/signal/no_signal rollup
- `actual_execution_ledger.csv`: no write in this stage

NO_SIGNAL full rows are not appended.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '210'
    out.mkdir(parents=True, exist_ok=True)

    blockers = []
    progress('load Stage209 cycle outputs')
    d209 = read_csv_any(root / '209' / 'gold_v3_209_decision.csv')
    state = read_json_any(root / '209' / 'gold_v3_209_latest_state_cycle_sample.json')
    signal_append = read_csv_any(root / '209' / 'gold_v3_209_trade_signal_append_cycle_sample.csv')
    notif_append = read_csv_any(root / '209' / 'gold_v3_209_notification_event_append_cycle_sample.csv')
    counter = read_csv_any(root / '209' / 'gold_v3_209_no_signal_counter_increment_cycle_sample.csv')
    debug_tail = read_csv_any(root / '209' / 'gold_v3_209_debug_tail_snapshot_cycle_sample.csv')

    if d209.empty:
        blockers.append({'id': 'missing_stage209_decision'})
    if not state:
        blockers.append({'id': 'missing_stage209_latest_state'})

    summary209 = d209.iloc[0].to_dict() if not d209.empty else {}
    final_route = s(summary209.get('latest_final_route'), 'NO_SIGNAL')

    write_plan = build_write_plan(final_route, len(signal_append), len(notif_append), len(counter))
    health = build_health_rollup(counter, summary209)
    checks = build_writer_checks(summary209, signal_append, notif_append, counter)
    validation_pass = bool(checks['passed'].all()) if not checks.empty else False

    save(write_plan, out / 'gold_v3_210_live_cycle_write_plan.csv')
    (out / 'gold_v3_210_latest_state_write_preview.json').write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    save(signal_append, out / 'gold_v3_210_trade_signal_ledger_append_preview.csv')
    save(notif_append, out / 'gold_v3_210_notification_events_append_preview.csv')
    save(counter, out / 'gold_v3_210_no_signal_counter_increment_preview.csv')
    save(health, out / 'gold_v3_210_health_rollup_daily_preview.csv')
    save(debug_tail.tail(ROLLING_DEBUG_TAIL_ROWS), out / 'gold_v3_210_debug_tail_snapshot_rolling_preview.csv')
    save(checks, out / 'gold_v3_210_writer_validation_checks.csv')
    (out / 'gold_v3_210_live_cycle_append_writer_plan.md').write_text(build_plan_md(), encoding='utf-8')

    ready = len(blockers) == 0 and validation_pass
    decision = 'STAGE210_LIVE_CYCLE_APPEND_WRITER_DRY_RUN_READY_AUDIT_ONLY' if ready else ('STAGE210_READY_WITH_WRITER_VALIDATION_WARNINGS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE210_BLOCKED')
    summary = {
        'step': STEP,
        'status': 'READY' if len(blockers) == 0 else 'BLOCKED',
        'ready': len(blockers) == 0,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'dry_run_only': True,
        'latest_closed_m15_dt': s(summary209.get('latest_closed_m15_dt')),
        'latest_final_route': final_route,
        'latest_state_write_mode': 'overwrite_preview_only',
        'trade_signal_append_preview_rows': int(len(signal_append)),
        'notification_append_preview_rows': int(len(notif_append)),
        'no_signal_counter_increment_preview_rows': int(len(counter)),
        'health_rollup_preview_rows': int(len(health)),
        'debug_tail_preview_rows': int(len(debug_tail.tail(ROLLING_DEBUG_TAIL_ROWS))) if not debug_tail.empty else 0,
        'no_signal_full_row_append': False,
        'writer_validation_pass': validation_pass,
        'send_enabled': False,
        'execution_enabled': False,
        'actual_order_import_enabled': False,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_210_decision.csv')
    (out / 'gold_v3_210_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 210 PASTE_ME_LIVE_CYCLE_APPEND_WRITER_DRY_RUN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'LIVE_CYCLE_APPEND_WRITER_PLAN_MD', build_plan_md()]
    lines += ['', 'LIVE_CYCLE_WRITE_PLAN', show(write_plan, 80)]
    lines += ['', 'LATEST_STATE_WRITE_PREVIEW_JSON', json.dumps(state, ensure_ascii=False, indent=2, default=str) if state else '{}']
    lines += ['', 'TRADE_SIGNAL_LEDGER_APPEND_PREVIEW', show(signal_append, 40)]
    lines += ['', 'NOTIFICATION_EVENTS_APPEND_PREVIEW', show(notif_append, 40)]
    lines += ['', 'NO_SIGNAL_COUNTER_INCREMENT_PREVIEW', show(counter, 40)]
    lines += ['', 'HEALTH_ROLLUP_DAILY_PREVIEW', show(health, 40)]
    lines += ['', 'WRITER_VALIDATION_CHECKS', show(checks, 80)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage210 is audit-only. It previews writer targets for one Stage209 cycle only.']
    lines += ['No live retention files are mutated by this stage; all outputs are Stage210 previews.']
    lines += ['No send, execution, actual import, payload, live hook, or autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
