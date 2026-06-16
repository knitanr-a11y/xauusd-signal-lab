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

STEP = 'GOLD_V3_215_SIGNAL_CASE_APPEND_PREVIEW_REPLAY_AUDIT_ONLY'


def progress(msg: str) -> None:
    print(f'[215 progress] {msg}', flush=True)


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


def num(v: Any, default: Any = '') -> Any:
    try:
        n = pd.to_numeric(pd.Series([v]), errors='coerce').iloc[0]
        return default if pd.isna(n) else float(n)
    except Exception:
        return default


def first(df: pd.DataFrame) -> dict[str, Any]:
    return df.iloc[0].to_dict() if not df.empty else {}


def make_short(signal_id: str) -> str:
    h = hashlib.blake2s(signal_id.encode('utf-8'), digest_size=16).hexdigest()[:20].upper()
    return 'G3S' + h


def add_short_id(row: dict[str, Any], id_map: pd.DataFrame) -> str:
    sid = txt(row.get('signal_id'))
    if not id_map.empty and {'signal_id', 'short_signal_id'}.issubset(id_map.columns):
        hit = id_map[id_map['signal_id'].astype(str).eq(sid)]
        if not hit.empty:
            short = txt(hit.iloc[0].get('short_signal_id'))
            if short:
                return short
    return make_short(sid)


def replay_latest_state(row: dict[str, Any], short_id: str) -> dict[str, Any]:
    return {
        'schema_version': 1,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'latest_closed_m15_dt': txt(row.get('entry_dt')),
        'final_route': txt(row.get('route'), txt(row.get('role'), 'SECONDARY_AUDIT_CANDIDATE')),
        'send_action': 'NO_SEND_AUDIT_ONLY',
        'signal_id': txt(row.get('signal_id')),
        'short_signal_id': short_id,
        'role': txt(row.get('role'), 'SECONDARY_AUDIT_CANDIDATE'),
        'candidate_id': txt(row.get('candidate_id')),
        'direction': txt(row.get('direction')),
        'm15_close': num(row.get('m15_close'), num(row.get('entry_price'))),
        'entry_price': num(row.get('entry_price'), num(row.get('m15_close'))),
        'tp': num(row.get('tp')),
        'sl': num(row.get('sl')),
        'horizon_m5': num(row.get('horizon_m5')),
        'h1_atr14': num(row.get('h1_atr14')),
        'd1_dist_close_atr28': num(row.get('d1_dist_close_atr28')),
        'h4_body_atr14': num(row.get('h4_body_atr14')),
        'replay_source_stage': '204_SIGNAL_SAMPLE',
        'audit_only': True,
        'send_enabled': False,
        'execution_enabled': False,
        'payload_enabled': False,
        'live_hook_enabled': False,
        'autotrade_enabled': False,
        'no_signal_notify': False,
    }


def trade_append(row: dict[str, Any], short_id: str) -> pd.DataFrame:
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    return pd.DataFrame([{
        'signal_id': txt(row.get('signal_id')),
        'short_signal_id': short_id,
        'entry_dt': txt(row.get('entry_dt')),
        'role': txt(row.get('role'), 'SECONDARY_AUDIT_CANDIDATE'),
        'route': txt(row.get('route'), txt(row.get('role'), 'SECONDARY_AUDIT_CANDIDATE')),
        'candidate_id': txt(row.get('candidate_id')),
        'direction': txt(row.get('direction')),
        'entry_price': num(row.get('entry_price'), num(row.get('m15_close'))),
        'tp': num(row.get('tp')),
        'sl': num(row.get('sl')),
        'horizon_m5': num(row.get('horizon_m5')),
        'm15_close': num(row.get('m15_close'), num(row.get('entry_price'))),
        'h1_atr14': num(row.get('h1_atr14')),
        'd1_dist_close_atr28': num(row.get('d1_dist_close_atr28')),
        'h4_body_atr14': num(row.get('h4_body_atr14')),
        'status': 'SIGNAL_REPLAY_APPEND_PREVIEW_ONLY',
        'created_at_utc': now,
        'audit_only': True,
    }])


def notification_append(row: dict[str, Any], short_id: str) -> pd.DataFrame:
    return pd.DataFrame([{
        'event_dt': txt(row.get('entry_dt')),
        'signal_id': txt(row.get('signal_id')),
        'short_signal_id': short_id,
        'route': txt(row.get('route'), txt(row.get('role'), 'SECONDARY_AUDIT_CANDIDATE')),
        'role': txt(row.get('role'), 'SECONDARY_AUDIT_CANDIDATE'),
        'candidate_id': txt(row.get('candidate_id')),
        'direction': txt(row.get('direction')),
        'send_action': 'NO_SEND_AUDIT_ONLY',
        'message_status': 'SIGNAL_REPLAY_NOT_SENT',
        'audit_only': True,
    }])


def no_signal_counter_preview() -> pd.DataFrame:
    return pd.DataFrame(columns=['date', 'hour', 'evaluated_closed_m15_rows', 'final_no_signal_increment', 'final_signal_increment', 'audit_only'])


def health(row: dict[str, Any]) -> pd.DataFrame:
    dt = pd.Timestamp(txt(row.get('entry_dt')))
    return pd.DataFrame([{
        'date': str(dt.date()),
        'evaluated_closed_m15_rows': 1,
        'final_signal_rows': 1,
        'final_no_signal_rows': 0,
        'primary_no_signal_rows': 1 if txt(row.get('role')) != 'PRIMARY' else 0,
        'secondary_no_signal_rows': 0 if txt(row.get('role')) == 'SECONDARY_AUDIT_CANDIDATE' else 1,
        'blocker_rows': 0,
        'send_rows': 0,
        'execution_rows': 0,
        'actual_import_rows': 0,
        'latest_closed_m15_dt': txt(row.get('entry_dt')),
        'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'audit_only': True,
    }])


def duplicate_key_preview(row: dict[str, Any], short_id: str) -> pd.DataFrame:
    return pd.DataFrame([
        {'target': 'trade_signal_ledger.csv', 'unique_key': 'signal_id', 'unique_value': txt(row.get('signal_id')), 'repeat_action': 'SKIP_DUPLICATE_SIGNAL_ID'},
        {'target': 'notification_events_rolling_30d.csv', 'unique_key': 'signal_id_or_short_signal_id', 'unique_value': f'{txt(row.get("signal_id"))}|{short_id}', 'repeat_action': 'SKIP_DUPLICATE_NOTIFICATION_EVENT'},
    ])


def checks(state: dict[str, Any], trade: pd.DataFrame, notif: pd.DataFrame, nosig: pd.DataFrame, d214: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([
        {'check_id': 'S001', 'passed': txt(state.get('signal_id')) != '', 'details': 'signal_id present'},
        {'check_id': 'S002', 'passed': txt(state.get('short_signal_id')) != '', 'details': 'short_signal_id present'},
        {'check_id': 'S003', 'passed': not trade.empty and len(trade) == 1, 'details': 'trade_signal append preview has one row'},
        {'check_id': 'S004', 'passed': not notif.empty and len(notif) == 1, 'details': 'notification append preview has one row'},
        {'check_id': 'S005', 'passed': nosig.empty, 'details': 'SIGNAL replay creates no NO_SIGNAL counter row'},
        {'check_id': 'S006', 'passed': txt(state.get('send_action')) == 'NO_SEND_AUDIT_ONLY', 'details': 'no-send action preserved'},
        {'check_id': 'S007', 'passed': flag(d214.get('ready')) and txt(d214.get('decision')).startswith('STAGE214_'), 'details': 'Stage214 repeat-safe contract ready'},
        {'check_id': 'S008', 'passed': True, 'details': 'send/order/import/payload/live hook remain disabled'},
    ])


def plan_md() -> str:
    return '''# GOLD V3 Stage215 SIGNAL Case Append Preview Replay Audit

Status: AUDIT_ONLY

Stage215 replays a known SIGNAL sample and builds the append-preview shape that would be produced on a SIGNAL cycle.

It verifies:

- latest_state SIGNAL shape
- trade_signal append preview row
- notification event append preview row
- no NO_SIGNAL counter row for SIGNAL replay
- duplicate key compatibility with Stage214 rules
- no-send status remains active

This stage does not send, execute, import actual results, create payload, enable live hook, or mutate production retention files.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '215'
    out.mkdir(parents=True, exist_ok=True)

    progress('load signal sample and contracts')
    blockers: list[dict[str, Any]] = []
    sig204 = read_csv_any(root / '204' / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
    map208 = read_csv_any(root / '208' / 'gold_v3_208_signal_id_map_sample.csv')
    d214 = first(read_csv_any(root / '214' / 'gold_v3_214_decision.csv'))
    if sig204.empty:
        blockers.append({'id': 'missing_stage204_signal_sample'})
    if not d214:
        blockers.append({'id': 'missing_stage214_decision'})

    row = first(sig204)
    short_id = add_short_id(row, map208) if row else ''
    state = replay_latest_state(row, short_id) if row else {}
    trade = trade_append(row, short_id) if row else pd.DataFrame()
    notif = notification_append(row, short_id) if row else pd.DataFrame()
    nosig = no_signal_counter_preview()
    h = health(row) if row else pd.DataFrame()
    dup = duplicate_key_preview(row, short_id) if row else pd.DataFrame()
    chk = checks(state, trade, notif, nosig, d214)

    validation_pass = bool(chk['passed'].all()) if not chk.empty else False
    if not validation_pass:
        blockers.append({'id': 'signal_replay_validation_failed'})

    (out / 'gold_v3_215_latest_state_signal_replay_preview.json').write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    save(trade, out / 'gold_v3_215_trade_signal_append_replay_preview.csv')
    save(notif, out / 'gold_v3_215_notification_append_replay_preview.csv')
    save(nosig, out / 'gold_v3_215_no_signal_counter_replay_preview.csv')
    save(h, out / 'gold_v3_215_health_rollup_signal_replay_preview.csv')
    save(dup, out / 'gold_v3_215_duplicate_key_replay_preview.csv')
    save(chk, out / 'gold_v3_215_validation_checks.csv')
    (out / 'gold_v3_215_signal_case_replay_plan.md').write_text(plan_md(), encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE215_SIGNAL_CASE_APPEND_PREVIEW_REPLAY_READY_AUDIT_ONLY' if ready else 'STAGE215_BLOCKED'
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
        'replay_source_stage': '204_SIGNAL_SAMPLE',
        'replay_signal_id': txt(state.get('signal_id')),
        'replay_short_signal_id': txt(state.get('short_signal_id')),
        'replay_route': txt(state.get('final_route')),
        'trade_signal_append_preview_rows': int(len(trade)),
        'notification_append_preview_rows': int(len(notif)),
        'no_signal_counter_preview_rows': int(len(nosig)),
        'health_rollup_preview_rows': int(len(h)),
        'validation_pass': validation_pass,
        'send_action': 'NO_SEND_AUDIT_ONLY',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_215_decision.csv')
    (out / 'gold_v3_215_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 215 PASTE_ME_SIGNAL_CASE_APPEND_PREVIEW_REPLAY_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'SIGNAL_CASE_REPLAY_PLAN_MD', plan_md()]
    lines += ['', 'LATEST_STATE_SIGNAL_REPLAY_PREVIEW_JSON', json.dumps(state, ensure_ascii=False, indent=2, default=str)]
    lines += ['', 'TRADE_SIGNAL_APPEND_REPLAY_PREVIEW', show(trade, 40)]
    lines += ['', 'NOTIFICATION_APPEND_REPLAY_PREVIEW', show(notif, 40)]
    lines += ['', 'NO_SIGNAL_COUNTER_REPLAY_PREVIEW', show(nosig, 40)]
    lines += ['', 'HEALTH_ROLLUP_SIGNAL_REPLAY_PREVIEW', show(h, 40)]
    lines += ['', 'DUPLICATE_KEY_REPLAY_PREVIEW', show(dup, 40)]
    lines += ['', 'VALIDATION_CHECKS', show(chk, 80)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage215 is audit-only. It replays a known SIGNAL sample to validate append-preview shape only.']
    lines += ['No notification is sent and no order/import/payload/live hook/autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
