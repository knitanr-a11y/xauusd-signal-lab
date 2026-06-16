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

STEP = 'GOLD_V3_203_RETENTION_WRITER_DRY_RUN_AUDIT_ONLY'
SECONDARY_CLASS = 'SECONDARY_AUDIT_CANDIDATE'
RETAIN_NOTIFY_DAYS = 30
ROLLING_DEBUG_ROWS = 500


def progress(msg: str) -> None:
    print(f'[203 progress] {msg}', flush=True)


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


def safe_str(v: Any, default: str = '') -> str:
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    s = str(v).strip()
    if s.lower() in {'nan', 'nat', 'none'}:
        return default
    return s


def clean_signal_text(v: Any) -> str:
    return safe_str(v, 'NO_SIGNAL') or 'NO_SIGNAL'


def parse_dt(v: Any) -> str:
    if safe_str(v, '') == '':
        return ''
    try:
        return str(pd.Timestamp(v))
    except Exception:
        return str(v)


def build_latest_state(latest: pd.DataFrame, stage202: pd.DataFrame) -> dict[str, Any]:
    row = latest.iloc[0].to_dict() if not latest.empty else {}
    d = stage202.iloc[0].to_dict() if not stage202.empty else {}
    return {
        'schema_version': 1,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'latest_closed_m15_dt': parse_dt(row.get('dt', d.get('latest_closed_m15_dt', ''))),
        'final_route': clean_signal_text(row.get('final_route', d.get('latest_final_route', 'NO_SIGNAL'))),
        'primary_signal': clean_signal_text(row.get('primary_signal', 'NO_SIGNAL')),
        'primary_candidate_id': clean_signal_text(row.get('primary_candidate_id', 'NO_SIGNAL')),
        'secondary_signal': clean_signal_text(row.get('secondary_signal', 'NO_SIGNAL')),
        'secondary_candidate_id': clean_signal_text(row.get('secondary_candidate_id', 'NO_SIGNAL')),
        'send_action': clean_signal_text(row.get('send_action', 'NO_SEND_AUDIT_ONLY')),
        'audit_only': True,
        'send_enabled': False,
        'order_enabled': False,
        'payload_enabled': False,
        'live_hook_enabled': False,
        'autotrade_enabled': False,
        'no_signal_notify': False,
    }


def build_notify_event_rows(signal_rows: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'event_dt', 'retention_policy', 'retention_days', 'route', 'role', 'candidate_id', 'direction',
        'source_closed_m15_dt', 'message_status', 'send_action', 'audit_only', 'no_signal_notify'
    ]
    if signal_rows.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in signal_rows.iterrows():
        route = clean_signal_text(r.get('final_route', 'NO_SIGNAL'))
        if route == 'NO_SIGNAL':
            continue
        role = 'PRIMARY' if route == 'PRIMARY' else SECONDARY_CLASS
        candidate = clean_signal_text(r.get('primary_candidate_id' if role == 'PRIMARY' else 'secondary_candidate_id', 'NO_SIGNAL'))
        direction = clean_signal_text(r.get('primary_signal' if role == 'PRIMARY' else 'secondary_signal', 'NO_SIGNAL'))
        rows.append({
            'event_dt': parse_dt(r.get('dt', '')),
            'retention_policy': 'ROLLING_30D_SAMPLE_ONLY',
            'retention_days': RETAIN_NOTIFY_DAYS,
            'route': route,
            'role': role,
            'candidate_id': candidate,
            'direction': direction,
            'source_closed_m15_dt': parse_dt(r.get('dt', '')),
            'message_status': 'DRY_RUN_NOT_SENT',
            'send_action': clean_signal_text(r.get('send_action', 'NO_SEND_AUDIT_ONLY')),
            'audit_only': True,
            'no_signal_notify': False,
        })
    return pd.DataFrame(rows, columns=cols)


def build_trade_signal_rows(signal_rows: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction', 'entry_price',
        'tp', 'sl', 'horizon_m5', 'status', 'source', 'audit_only', 'created_at_utc'
    ]
    if signal_rows.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for idx, r in signal_rows.iterrows():
        route = clean_signal_text(r.get('final_route', 'NO_SIGNAL'))
        if route == 'NO_SIGNAL':
            continue
        role = 'PRIMARY' if route == 'PRIMARY' else SECONDARY_CLASS
        prefix = 'primary' if role == 'PRIMARY' else 'secondary'
        candidate = clean_signal_text(r.get(f'{prefix}_candidate_id', 'NO_SIGNAL'))
        direction = clean_signal_text(r.get(f'{prefix}_signal', 'NO_SIGNAL'))
        entry_dt = parse_dt(r.get('dt', ''))
        rows.append({
            'signal_id': f'DRYRUN_{entry_dt}_{role}_{candidate}'.replace(' ', '_').replace(':', '').replace('-', ''),
            'entry_dt': entry_dt,
            'role': role,
            'route': route,
            'candidate_id': candidate,
            'direction': direction,
            'entry_price': r.get('m15_close', ''),
            'tp': r.get(f'{prefix}_tp', ''),
            'sl': r.get(f'{prefix}_sl', ''),
            'horizon_m5': r.get(f'{prefix}_horizon_m5', ''),
            'status': 'SIGNAL_ONLY_DRY_RUN',
            'source': 'stage203_dry_run_from_tail96_signal_rows',
            'audit_only': True,
            'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        })
    return pd.DataFrame(rows, columns=cols)


def trade_result_schema() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        'signal_id', 'entry_dt', 'exit_dt', 'role', 'route', 'candidate_id', 'direction',
        'entry_price', 'exit_price', 'tp', 'sl', 'horizon_m5', 'result_status', 'hit_type',
        'pnl_raw', 'pnl_cost3', 'pnl_cost5', 'r_multiple', 'holding_m5_bars',
        'close_reason', 'review_tag', 'created_at_utc', 'updated_at_utc'
    ])


def history_monthly_schema() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        'month', 'role', 'route', 'candidate_id', 'trades', 'wins', 'losses', 'win_rate_pct',
        'gross_profit', 'gross_loss', 'pf', 'sum_pnl_cost3', 'sum_pnl_cost5', 'avg_pnl_cost3',
        'max_drawdown_proxy', 'notes'
    ])


def clean_debug_tail(tail: pd.DataFrame) -> pd.DataFrame:
    if tail.empty:
        return pd.DataFrame()
    x = tail.tail(ROLLING_DEBUG_ROWS).copy()
    for col in x.columns:
        if col.endswith('candidate_id') or col.endswith('signal') or col in {'final_route', 'send_action'}:
            x[col] = x[col].apply(lambda v: clean_signal_text(v))
        else:
            x[col] = x[col].apply(lambda v: '' if safe_str(v, '') == '' else v)
    return x


def build_storage_plan_md() -> str:
    return f'''# GOLD V3 Stage203 Retention Writer Dry-Run Plan

Status: AUDIT_ONLY

## Separation principle

Notification history and trade history must be stored separately.

- Notification history is for recent operational visibility. It can be rotated after {RETAIN_NOTIFY_DAYS} days.
- Trade signal and trade result ledgers are for later review. They should be retained long-term.
- NO_SIGNAL full rows should not be appended indefinitely.

## Proposed live files

### Short retention

`notification_events_rolling_30d.csv`

- Append only when a PRIMARY or SECONDARY_AUDIT_CANDIDATE signal would have been sent.
- Keep only recent rows, for example {RETAIN_NOTIFY_DAYS} days.
- NO_SIGNAL is not appended as a notification event.

### Long retention

`trade_signal_ledger.csv`

- Append each signal candidate event.
- Used later to confirm trade count and signal frequency.

`trade_result_ledger.csv`

- Append or update after exit/resolution.
- Used later to inspect wins, losses, PF, win rate, trade count, holding time, and weak candidates.

`trade_history_monthly_summary.csv`

- Monthly rollup from the result ledger.
- Used for review without scanning all raw trades.

### Health and debug

`latest_state.json`

- Overwrite every evaluation.

`no_signal_counters_daily.csv`

- Increment counters for NO_SIGNAL instead of storing every row.

`health_rollup_daily.csv`

- Store evaluated bars, signal bars, NO_SIGNAL bars, missing-data bars, and blockers.

`debug_tail_snapshot.csv`

- Keep only last {ROLLING_DEBUG_ROWS} evaluations.

## Safety

This stage only writes dry-run sample files under Stage203 output. It does not send, order, create payload, or enable live hooks.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '203'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage202/Stage201/Stage200 outputs')
    stage202_decision = read_csv_any(root / '202' / 'gold_v3_202_decision.csv')
    latest_clean = read_csv_any(root / '202' / 'gold_v3_202_latest_compact_preview_clean.csv')
    signal_rows_clean = read_csv_any(root / '202' / 'gold_v3_202_tail96_signal_rows_compact_clean.csv')
    no_signal_counter = read_csv_any(root / '202' / 'gold_v3_202_no_signal_counters_daily_hourly_from_tail96.csv')
    health_rollup = read_csv_any(root / '202' / 'gold_v3_202_health_rollup_daily_from_tail96.csv')
    stage200_tail = read_csv_any(root / '200' / 'gold_v3_200_no_send_latest_tail96.csv')

    required = [
        ('stage202_decision', stage202_decision),
        ('latest_clean', latest_clean),
        ('no_signal_counter', no_signal_counter),
        ('health_rollup', health_rollup),
        ('stage200_tail', stage200_tail),
    ]
    for name, df in required:
        if df.empty:
            blockers.append({'id': f'missing_{name}'})

    latest_state: dict[str, Any] = {}
    notify_events = pd.DataFrame()
    signal_ledger = pd.DataFrame()
    result_schema = trade_result_schema()
    monthly_schema = history_monthly_schema()
    debug_tail = pd.DataFrame()
    storage_plan = build_storage_plan_md()

    if not blockers:
        latest_state = build_latest_state(latest_clean, stage202_decision)
        notify_events = build_notify_event_rows(signal_rows_clean)
        signal_ledger = build_trade_signal_rows(signal_rows_clean)
        debug_tail = clean_debug_tail(stage200_tail)

        (out / 'gold_v3_203_latest_state_sample.json').write_text(json.dumps(latest_state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        save(notify_events, out / 'gold_v3_203_notification_events_rolling_30d_sample.csv')
        save(signal_ledger, out / 'gold_v3_203_trade_signal_ledger_sample.csv')
        save(result_schema, out / 'gold_v3_203_trade_result_ledger_schema.csv')
        save(monthly_schema, out / 'gold_v3_203_trade_history_monthly_summary_schema.csv')
        save(no_signal_counter, out / 'gold_v3_203_no_signal_counters_daily_hourly_sample.csv')
        save(health_rollup, out / 'gold_v3_203_health_rollup_daily_sample.csv')
        save(debug_tail, out / 'gold_v3_203_debug_tail_snapshot_rolling_sample.csv')
        (out / 'gold_v3_203_retention_writer_dry_run_plan.md').write_text(storage_plan, encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE203_RETENTION_WRITER_DRY_RUN_READY_AUDIT_ONLY' if ready else 'STAGE203_BLOCKED'
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
        'short_retention_notification_days': RETAIN_NOTIFY_DAYS,
        'long_retention_trade_signal_ledger': True,
        'long_retention_trade_result_ledger': True,
        'no_signal_full_rows_append': False,
        'no_signal_counter_increment': True,
        'rolling_debug_tail_rows': ROLLING_DEBUG_ROWS,
        'latest_closed_m15_dt': str(latest_state.get('latest_closed_m15_dt', '')),
        'latest_final_route': str(latest_state.get('final_route', 'NO_SIGNAL')),
        'notification_sample_rows': int(len(notify_events)) if not notify_events.empty else 0,
        'trade_signal_ledger_sample_rows': int(len(signal_ledger)) if not signal_ledger.empty else 0,
        'trade_result_ledger_schema_ready': True,
        'monthly_summary_schema_ready': True,
        'retention_answer': 'Notification history can rotate at about 30 days. Trade signal and result ledgers should be retained long-term for later win rate, PF, trade count, and loss-reason review. NO_SIGNAL should be aggregated, not appended as full rows forever.',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_203_decision.csv')
    (out / 'gold_v3_203_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 203 PASTE_ME_RETENTION_WRITER_DRY_RUN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'RETENTION_WRITER_DRY_RUN_PLAN_MD', storage_plan]
    lines += ['', 'LATEST_STATE_SAMPLE_JSON', json.dumps(latest_state, ensure_ascii=False, indent=2, default=str) if latest_state else '{}']
    lines += ['', 'NOTIFICATION_EVENTS_ROLLING_30D_SAMPLE', show(notify_events, 40)]
    lines += ['', 'TRADE_SIGNAL_LEDGER_SAMPLE', show(signal_ledger, 40)]
    lines += ['', 'TRADE_RESULT_LEDGER_SCHEMA', show(result_schema, 20)]
    lines += ['', 'TRADE_HISTORY_MONTHLY_SUMMARY_SCHEMA', show(monthly_schema, 20)]
    lines += ['', 'NO_SIGNAL_COUNTERS_SAMPLE', show(no_signal_counter, 80)]
    lines += ['', 'HEALTH_ROLLUP_SAMPLE', show(health_rollup, 80)]
    lines += ['', 'DEBUG_TAIL_ROLLING_SAMPLE', show(debug_tail, 100)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage203 is audit-only. It creates dry-run sample retention files only.',
        'Notification history is short-retention. Trade signal/result ledgers are long-retention for later review.',
        'NO_SIGNAL full rows are not appended indefinitely; counters and rolling debug tail are used instead.',
        'No send, order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
