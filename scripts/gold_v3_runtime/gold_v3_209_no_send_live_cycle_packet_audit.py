#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_209_NO_SEND_LIVE_CYCLE_PACKET_AUDIT_ONLY'
SECONDARY = 'SECONDARY_AUDIT_CANDIDATE'
PREFIX = 'G3S'
HASH_CHARS = 20


def progress(msg: str) -> None:
    print(f'[209 progress] {msg}', flush=True)


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


def bad(v: Any) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except Exception:
        pass
    return str(v).strip() == '' or str(v).strip().lower() in {'nan', 'nat', 'none'}


def s(v: Any, default: str = '') -> str:
    return default if bad(v) else str(v).strip()


def n(v: Any, default: Any = '') -> Any:
    return default if bad(v) else v


def make_short(full_id: str) -> str:
    h = hashlib.blake2s(full_id.encode('utf-8'), digest_size=16).hexdigest()[:HASH_CHARS].upper()
    return PREFIX + h


def latest_row(tail: pd.DataFrame) -> pd.Series:
    x = tail.copy()
    x['dt2'] = pd.to_datetime(x['dt'])
    return x.sort_values('dt2').iloc[-1]


def role_from_route(route: str) -> str:
    if route == 'PRIMARY':
        return 'PRIMARY'
    if route == SECONDARY:
        return SECONDARY
    return 'NO_SIGNAL'


def build_signal_identity(row: pd.Series) -> dict[str, Any]:
    route = s(row.get('final_route'), 'NO_SIGNAL')
    role = role_from_route(route)
    if role == 'NO_SIGNAL':
        return {'signal_id': '', 'short_signal_id': '', 'role': role, 'candidate_id': 'NO_SIGNAL', 'direction': 'NO_SIGNAL', 'tp': '', 'sl': '', 'horizon_m5': ''}
    prefix = 'primary' if role == 'PRIMARY' else 'secondary'
    dt_txt = pd.Timestamp(row['dt']).strftime('%Y%m%d_%H%M%S')
    candidate = s(row.get(f'{prefix}_candidate_id'), 'NO_SIGNAL')
    direction = s(row.get(f'{prefix}_direction'), s(row.get(f'{prefix}_signal'), 'NO_SIGNAL'))
    full_id = f'{dt_txt}_{role}_{candidate}'
    return {
        'signal_id': full_id,
        'short_signal_id': make_short(full_id),
        'role': role,
        'candidate_id': candidate,
        'direction': direction,
        'tp': n(row.get(f'{prefix}_tp')),
        'sl': n(row.get(f'{prefix}_sl')),
        'horizon_m5': n(row.get(f'{prefix}_horizon_m5')),
    }


def build_latest_state(row: pd.Series, ident: dict[str, Any]) -> dict[str, Any]:
    route = s(row.get('final_route'), 'NO_SIGNAL')
    return {
        'schema_version': 1,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'latest_closed_m15_dt': str(pd.Timestamp(row['dt'])),
        'final_route': route,
        'send_action': 'NO_SEND_AUDIT_ONLY',
        'signal_id': ident.get('signal_id', ''),
        'short_signal_id': ident.get('short_signal_id', ''),
        'role': ident.get('role', 'NO_SIGNAL'),
        'candidate_id': ident.get('candidate_id', 'NO_SIGNAL'),
        'direction': ident.get('direction', 'NO_SIGNAL'),
        'm15_close': n(row.get('m15_close')),
        'h1_atr14': n(row.get('h1_atr14')),
        'd1_dist_close_atr28': n(row.get('d1_dist_close_atr28')),
        'h4_body_atr14': n(row.get('h4_body_atr14')),
        'audit_only': True,
        'send_enabled': False,
        'execution_enabled': False,
        'payload_enabled': False,
        'live_hook_enabled': False,
        'autotrade_enabled': False,
        'no_signal_notify': False,
    }


def empty_signal_cols() -> list[str]:
    return ['signal_id', 'short_signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction', 'entry_price', 'tp', 'sl', 'horizon_m5', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14', 'status', 'created_at_utc', 'audit_only']


def build_signal_append(row: pd.Series, ident: dict[str, Any]) -> pd.DataFrame:
    if ident.get('role') == 'NO_SIGNAL':
        return pd.DataFrame(columns=empty_signal_cols())
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    return pd.DataFrame([{
        'signal_id': ident['signal_id'],
        'short_signal_id': ident['short_signal_id'],
        'entry_dt': str(pd.Timestamp(row['dt'])),
        'role': ident['role'],
        'route': s(row.get('final_route')),
        'candidate_id': ident['candidate_id'],
        'direction': ident['direction'],
        'entry_price': n(row.get('m15_close')),
        'tp': ident['tp'],
        'sl': ident['sl'],
        'horizon_m5': ident['horizon_m5'],
        'm15_close': n(row.get('m15_close')),
        'h1_atr14': n(row.get('h1_atr14')),
        'd1_dist_close_atr28': n(row.get('d1_dist_close_atr28')),
        'h4_body_atr14': n(row.get('h4_body_atr14')),
        'status': 'DRY_RUN_SIGNAL_APPEND_SAMPLE',
        'created_at_utc': now,
        'audit_only': True,
    }], columns=empty_signal_cols())


def build_notification_append(row: pd.Series, ident: dict[str, Any]) -> pd.DataFrame:
    cols = ['event_dt', 'signal_id', 'short_signal_id', 'route', 'role', 'candidate_id', 'direction', 'send_action', 'message_status', 'audit_only']
    if ident.get('role') == 'NO_SIGNAL':
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([{
        'event_dt': str(pd.Timestamp(row['dt'])),
        'signal_id': ident['signal_id'],
        'short_signal_id': ident['short_signal_id'],
        'route': s(row.get('final_route')),
        'role': ident['role'],
        'candidate_id': ident['candidate_id'],
        'direction': ident['direction'],
        'send_action': 'NO_SEND_AUDIT_ONLY',
        'message_status': 'DRY_RUN_NOT_SENT',
        'audit_only': True,
    }], columns=cols)


def build_no_signal_counter(row: pd.Series, ident: dict[str, Any]) -> pd.DataFrame:
    cols = ['date', 'hour', 'evaluated_closed_m15_rows', 'final_no_signal_increment', 'final_signal_increment', 'primary_no_signal_increment', 'secondary_no_signal_increment', 'audit_only']
    dt = pd.Timestamp(row['dt'])
    no_signal = ident.get('role') == 'NO_SIGNAL'
    return pd.DataFrame([{
        'date': str(dt.date()),
        'hour': int(dt.hour),
        'evaluated_closed_m15_rows': 1,
        'final_no_signal_increment': int(no_signal),
        'final_signal_increment': int(not no_signal),
        'primary_no_signal_increment': int(s(row.get('primary_signal'), 'NO_SIGNAL') == 'NO_SIGNAL'),
        'secondary_no_signal_increment': int(s(row.get('secondary_signal'), 'NO_SIGNAL') == 'NO_SIGNAL'),
        'audit_only': True,
    }], columns=cols)


def build_cycle_plan_md() -> str:
    return '''# GOLD V3 Stage209 No-Send Live-Cycle Packet

Status: AUDIT_ONLY

Stage209 simulates one live evaluation cycle without sending or executing.

Cycle logic:

1. Read the latest closed M15 preview row.
2. Decide final route.
3. If final route is SIGNAL, generate signal_id and short_signal_id.
4. Build latest_state sample.
5. If SIGNAL, prepare notification and trade_signal append samples.
6. If NO_SIGNAL, prepare only counter increment sample.
7. Keep send, execution, payload, live hook, and autotrade disabled.

This stage is a dry-run packet only.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '209'
    out.mkdir(parents=True, exist_ok=True)

    blockers = []
    progress('load Stage200 tail and Stage208 decision')
    tail = read_csv_any(root / '200' / 'gold_v3_200_no_send_latest_tail96.csv')
    d208 = read_csv_any(root / '208' / 'gold_v3_208_decision.csv')
    if tail.empty:
        blockers.append({'id': 'missing_stage200_tail96'})
    if d208.empty:
        blockers.append({'id': 'missing_stage208_decision'})

    latest_state = {}
    signal_append = pd.DataFrame(columns=empty_signal_cols())
    notification_append = pd.DataFrame()
    counter = pd.DataFrame()
    row_count = 0
    final_route = 'NO_SIGNAL'
    latest_dt = ''
    ident = {'role': 'NO_SIGNAL'}
    if not blockers:
        r = latest_row(tail)
        latest_dt = str(pd.Timestamp(r['dt']))
        final_route = s(r.get('final_route'), 'NO_SIGNAL')
        ident = build_signal_identity(r)
        latest_state = build_latest_state(r, ident)
        signal_append = build_signal_append(r, ident)
        notification_append = build_notification_append(r, ident)
        counter = build_no_signal_counter(r, ident)
        row_count = 1
        (out / 'gold_v3_209_latest_state_cycle_sample.json').write_text(json.dumps(latest_state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        save(signal_append, out / 'gold_v3_209_trade_signal_append_cycle_sample.csv')
        save(notification_append, out / 'gold_v3_209_notification_event_append_cycle_sample.csv')
        save(counter, out / 'gold_v3_209_no_signal_counter_increment_cycle_sample.csv')
        save(tail.tail(96), out / 'gold_v3_209_debug_tail_snapshot_cycle_sample.csv')
        (out / 'gold_v3_209_no_send_live_cycle_plan.md').write_text(build_cycle_plan_md(), encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE209_NO_SEND_LIVE_CYCLE_PACKET_READY_AUDIT_ONLY' if ready else 'STAGE209_BLOCKED'
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
        'cycle_rows_evaluated': row_count,
        'latest_closed_m15_dt': latest_dt,
        'latest_final_route': final_route,
        'latest_role': ident.get('role', 'NO_SIGNAL'),
        'latest_signal_id': ident.get('signal_id', ''),
        'latest_short_signal_id': ident.get('short_signal_id', ''),
        'signal_append_rows': int(len(signal_append)),
        'notification_append_rows': int(len(notification_append)),
        'no_signal_counter_increment_rows': int(len(counter)),
        'no_signal_full_row_append': False,
        'latest_state_overwrite_sample': True,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_209_decision.csv')
    (out / 'gold_v3_209_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 209 PASTE_ME_NO_SEND_LIVE_CYCLE_PACKET_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'NO_SEND_LIVE_CYCLE_PLAN_MD', build_cycle_plan_md()]
    lines += ['', 'LATEST_STATE_CYCLE_SAMPLE_JSON', json.dumps(latest_state, ensure_ascii=False, indent=2, default=str) if latest_state else '{}']
    lines += ['', 'TRADE_SIGNAL_APPEND_CYCLE_SAMPLE', show(signal_append, 40)]
    lines += ['', 'NOTIFICATION_EVENT_APPEND_CYCLE_SAMPLE', show(notification_append, 40)]
    lines += ['', 'NO_SIGNAL_COUNTER_INCREMENT_CYCLE_SAMPLE', show(counter, 40)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage209 is audit-only. It simulates one latest closed M15 live-cycle packet only.']
    lines += ['If latest route is NO_SIGNAL, no signal/notification append is created; only latest_state and NO_SIGNAL counter samples are produced.']
    lines += ['No send, execution, actual import, payload, live hook, or autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
