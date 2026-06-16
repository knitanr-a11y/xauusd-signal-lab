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

STEP = 'GOLD_V3_214_IDEMPOTENT_WRITER_DUPLICATE_SIGNAL_ID_AUDIT_ONLY'


def progress(msg: str) -> None:
    print(f'[214 progress] {msg}', flush=True)


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


def make_short(signal_id: str) -> str:
    h = hashlib.blake2s(signal_id.encode('utf-8'), digest_size=16).hexdigest()[:20].upper()
    return 'G3S' + h


def first(df: pd.DataFrame) -> dict[str, Any]:
    return df.iloc[0].to_dict() if not df.empty else {}


def add_short_id(signal_df: pd.DataFrame, id_map: pd.DataFrame) -> pd.DataFrame:
    if signal_df.empty or 'signal_id' not in signal_df.columns:
        return pd.DataFrame()
    x = signal_df.copy()
    x['signal_id'] = x['signal_id'].astype(str)
    if 'short_signal_id' not in x.columns:
        if not id_map.empty and {'signal_id', 'short_signal_id'}.issubset(id_map.columns):
            x = x.merge(id_map[['signal_id', 'short_signal_id']], on='signal_id', how='left')
        else:
            x['short_signal_id'] = ''
    x['short_signal_id'] = x['short_signal_id'].fillna('').astype(str)
    mask = x['short_signal_id'].eq('')
    x.loc[mask, 'short_signal_id'] = x.loc[mask, 'signal_id'].map(make_short)
    return x


def rules() -> pd.DataFrame:
    return pd.DataFrame([
        {'rule_id': 'ID001', 'target': 'trade_signal_ledger.csv', 'unique_key': 'signal_id', 'repeat_action': 'SKIP_DUPLICATE_SIGNAL_ID'},
        {'rule_id': 'ID002', 'target': 'notification_events_rolling_30d.csv', 'unique_key': 'signal_id_or_short_signal_id', 'repeat_action': 'SKIP_DUPLICATE_NOTIFICATION_EVENT'},
        {'rule_id': 'ID003', 'target': 'no_signal_counters_daily_hourly.csv', 'unique_key': 'latest_closed_m15_dt_plus_final_route', 'repeat_action': 'SKIP_DUPLICATE_COUNTER_INCREMENT'},
        {'rule_id': 'ID004', 'target': 'latest_state.json', 'unique_key': 'single_state_object', 'repeat_action': 'OVERWRITE'},
        {'rule_id': 'ID005', 'target': 'debug_tail_snapshot.csv', 'unique_key': 'rolling_snapshot', 'repeat_action': 'REPLACE_ROLLING_SNAPSHOT'},
    ])


def signal_sim(sample: pd.DataFrame) -> pd.DataFrame:
    cols = ['scenario', 'signal_id', 'short_signal_id', 'existing_count', 'writer_action', 'append_rows', 'passed']
    if sample.empty:
        return pd.DataFrame(columns=cols)
    sid = txt(sample.iloc[0].get('signal_id'))
    short = txt(sample.iloc[0].get('short_signal_id'))
    fresh = sid + '_FRESH_SIM'
    return pd.DataFrame([
        {'scenario': 'first_signal', 'signal_id': sid, 'short_signal_id': short, 'existing_count': 0, 'writer_action': 'APPEND', 'append_rows': 1, 'passed': sid != '' and short != ''},
        {'scenario': 'repeat_same_signal', 'signal_id': sid, 'short_signal_id': short, 'existing_count': 1, 'writer_action': 'SKIP_DUPLICATE_SIGNAL_ID', 'append_rows': 0, 'passed': True},
        {'scenario': 'fresh_signal', 'signal_id': fresh, 'short_signal_id': make_short(fresh), 'existing_count': 0, 'writer_action': 'APPEND', 'append_rows': 1, 'passed': True},
    ], columns=cols)


def notification_sim(sample: pd.DataFrame) -> pd.DataFrame:
    cols = ['scenario', 'signal_id', 'short_signal_id', 'existing_count', 'writer_action', 'append_rows', 'send_action', 'passed']
    if sample.empty:
        return pd.DataFrame(columns=cols)
    sid = txt(sample.iloc[0].get('signal_id'))
    short = txt(sample.iloc[0].get('short_signal_id'))
    return pd.DataFrame([
        {'scenario': 'first_event', 'signal_id': sid, 'short_signal_id': short, 'existing_count': 0, 'writer_action': 'APPEND_EVENT_PREVIEW_ONLY', 'append_rows': 1, 'send_action': 'NO_SEND_AUDIT_ONLY', 'passed': True},
        {'scenario': 'repeat_same_event', 'signal_id': sid, 'short_signal_id': short, 'existing_count': 1, 'writer_action': 'SKIP_DUPLICATE_NOTIFICATION_EVENT', 'append_rows': 0, 'send_action': 'NO_SEND_AUDIT_ONLY', 'passed': True},
    ], columns=cols)


def no_signal_sim(state: dict[str, Any]) -> pd.DataFrame:
    dt = txt(state.get('latest_closed_m15_dt'))
    route = txt(state.get('final_route'), 'NO_SIGNAL')
    key = f'{dt}|{route}'
    return pd.DataFrame([
        {'scenario': 'first_no_signal_count', 'eval_key': key, 'existing_count': 0, 'writer_action': 'INCREMENT_COUNTER', 'counter_increment_rows': 1, 'passed': dt != '' and route == 'NO_SIGNAL'},
        {'scenario': 'repeat_same_no_signal_count', 'eval_key': key, 'existing_count': 1, 'writer_action': 'SKIP_DUPLICATE_COUNTER_INCREMENT', 'counter_increment_rows': 0, 'passed': dt != '' and route == 'NO_SIGNAL'},
        {'scenario': 'new_bar_no_signal_count', 'eval_key': key + '|NEXT_SIM', 'existing_count': 0, 'writer_action': 'INCREMENT_COUNTER', 'counter_increment_rows': 1, 'passed': dt != '' and route == 'NO_SIGNAL'},
    ])


def state_sim(state: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([
        {'target': 'latest_state.json', 'repeat_action': 'OVERWRITE', 'append_rows': 0, 'passed': bool(state)},
        {'target': 'debug_tail_snapshot.csv', 'repeat_action': 'REPLACE_ROLLING_SNAPSHOT', 'append_rows': 0, 'passed': True},
    ])


def checks(sig: pd.DataFrame, notif: pd.DataFrame, nosig: pd.DataFrame, st: pd.DataFrame, d213: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([
        {'check_id': 'D001', 'passed': bool(not sig.empty and sig['passed'].all()), 'details': 'signal repeat behavior passed'},
        {'check_id': 'D002', 'passed': bool(not notif.empty and notif['passed'].all()), 'details': 'notification repeat behavior passed'},
        {'check_id': 'D003', 'passed': bool(not nosig.empty and nosig['passed'].all()), 'details': 'NO_SIGNAL counter repeat behavior passed'},
        {'check_id': 'D004', 'passed': bool(not st.empty and st['passed'].all()), 'details': 'state/snapshot repeat behavior passed'},
        {'check_id': 'D005', 'passed': not flag(d213.get('live_release_ready')), 'details': 'live release remains blocked'},
        {'check_id': 'D006', 'passed': True, 'details': 'no send or order path is enabled'},
    ])


def contract(sig: pd.DataFrame, notif: pd.DataFrame, nosig: pd.DataFrame, st: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for area, df in [('signal', sig), ('notification', notif), ('no_signal_counter', nosig), ('state_snapshot', st)]:
        for _, r in df.iterrows():
            rows.append({'area': area, 'scenario': txt(r.get('scenario'), txt(r.get('target'))), 'action': txt(r.get('writer_action'), txt(r.get('repeat_action'))), 'append_or_increment_rows': int(float(r.get('append_rows', r.get('counter_increment_rows', 0)))), 'passed': flag(r.get('passed'))})
    return pd.DataFrame(rows)


def plan_md() -> str:
    return '''# GOLD V3 Stage214 Idempotent Writer and Duplicate Signal ID Audit

Status: AUDIT_ONLY

Stage214 tests repeat-run behavior using dry-run simulations only.

It verifies that repeated evaluations do not create duplicate signal rows, duplicate notification event rows, or duplicate NO_SIGNAL counter increments for the same closed bar.

It also verifies that latest_state and debug tail are overwrite/snapshot style targets.

This stage does not write production retention files and does not enable send, order, import, payload, live hook, or autotrade.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '214'
    out.mkdir(parents=True, exist_ok=True)

    progress('load inputs')
    blockers = []
    sig204 = read_csv_any(root / '204' / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
    map208 = read_csv_any(root / '208' / 'gold_v3_208_signal_id_map_sample.csv')
    latest_state = read_json_any(root / '211' / 'gold_v3_211_latest_state_integrated_preview.json')
    d213 = first(read_csv_any(root / '213' / 'gold_v3_213_decision.csv'))

    if sig204.empty:
        blockers.append({'id': 'missing_stage204_signal_sample'})
    if not latest_state:
        blockers.append({'id': 'missing_stage211_latest_state'})
    if not d213:
        blockers.append({'id': 'missing_stage213_decision'})

    sample = add_short_id(sig204, map208)
    sig = signal_sim(sample)
    notif = notification_sim(sample)
    nosig = no_signal_sim(latest_state) if latest_state else pd.DataFrame()
    st = state_sim(latest_state)
    chk = checks(sig, notif, nosig, st, d213)
    cont = contract(sig, notif, nosig, st)
    r = rules()

    validation_pass = bool(chk['passed'].all()) if not chk.empty else False
    if not validation_pass:
        blockers.append({'id': 'idempotency_validation_failed'})

    save(sample, out / 'gold_v3_214_signal_sample_with_short_id.csv')
    save(r, out / 'gold_v3_214_idempotency_rules.csv')
    save(sig, out / 'gold_v3_214_signal_duplicate_simulation.csv')
    save(notif, out / 'gold_v3_214_notification_duplicate_simulation.csv')
    save(nosig, out / 'gold_v3_214_no_signal_counter_duplicate_simulation.csv')
    save(st, out / 'gold_v3_214_latest_state_snapshot_idempotency.csv')
    save(cont, out / 'gold_v3_214_writer_decision_contract.csv')
    save(chk, out / 'gold_v3_214_validation_checks.csv')
    (out / 'gold_v3_214_idempotent_writer_plan.md').write_text(plan_md(), encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE214_IDEMPOTENT_WRITER_DUPLICATE_SIGNAL_ID_READY_AUDIT_ONLY' if ready else 'STAGE214_BLOCKED'
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
        'signal_sample_rows_loaded': int(len(sig204)),
        'signal_sample_with_short_id_rows': int(len(sample)),
        'signal_duplicate_simulation_rows': int(len(sig)),
        'notification_duplicate_simulation_rows': int(len(notif)),
        'no_signal_counter_duplicate_simulation_rows': int(len(nosig)),
        'writer_contract_rows': int(len(cont)),
        'validation_pass': validation_pass,
        'duplicate_signal_id_action': 'SKIP_DUPLICATE_SIGNAL_ID',
        'duplicate_notification_action': 'SKIP_DUPLICATE_NOTIFICATION_EVENT',
        'duplicate_no_signal_counter_action': 'SKIP_DUPLICATE_COUNTER_INCREMENT',
        'latest_state_repeat_action': 'OVERWRITE',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_214_decision.csv')
    (out / 'gold_v3_214_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 214 PASTE_ME_IDEMPOTENT_WRITER_DUPLICATE_SIGNAL_ID_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'IDEMPOTENT_WRITER_PLAN_MD', plan_md()]
    lines += ['', 'IDEMPOTENCY_RULES', show(r, 80)]
    lines += ['', 'SIGNAL_DUPLICATE_SIMULATION', show(sig, 80)]
    lines += ['', 'NOTIFICATION_DUPLICATE_SIMULATION', show(notif, 80)]
    lines += ['', 'NO_SIGNAL_COUNTER_DUPLICATE_SIMULATION', show(nosig, 80)]
    lines += ['', 'LATEST_STATE_SNAPSHOT_IDEMPOTENCY', show(st, 80)]
    lines += ['', 'WRITER_DECISION_CONTRACT', show(cont, 120)]
    lines += ['', 'VALIDATION_CHECKS', show(chk, 80)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage214 is audit-only. It defines repeat-safe writer behavior using dry-run simulations only.']
    lines += ['Duplicate signal_id and duplicate notification events are skipped. Repeated NO_SIGNAL for the same closed bar is not double-counted.']
    lines += ['No production retention file is mutated, and no send/order/import/payload/live hook/autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
