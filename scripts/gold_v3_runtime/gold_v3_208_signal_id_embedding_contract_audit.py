#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_208_SIGNAL_ID_EMBEDDING_CONTRACT_AUDIT_ONLY'
PREFIX = 'G3S'
HASH_CHARS = 20
MAX_COMMENT_LEN = 31


def progress(msg: str) -> None:
    print(f'[208 progress] {msg}', flush=True)


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


def missing(v: Any) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except Exception:
        pass
    return str(v).strip() == '' or str(v).strip().lower() in {'nan', 'nat', 'none'}


def s(v: Any, default: str = '') -> str:
    return default if missing(v) else str(v).strip()


def compact(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]+', '_', text).strip('_')


def short_id(full_id: str) -> str:
    h = hashlib.blake2s(full_id.encode('utf-8'), digest_size=16).hexdigest()[:HASH_CHARS].upper()
    return PREFIX + h


def make_contract(signal: pd.DataFrame) -> pd.DataFrame:
    cols = ['signal_id', 'short_signal_id', 'short_len', 'exec_comment', 'comment_len', 'entry_dt', 'role', 'route', 'candidate_id', 'direction', 'format_version', 'status']
    rows = []
    for _, r in signal.iterrows():
        full = s(r.get('signal_id'))
        if not full:
            dt = pd.Timestamp(r.get('entry_dt')).strftime('%Y%m%d_%H%M%S')
            full = f'{dt}_{compact(s(r.get("role"), "ROLE"))}_{compact(s(r.get("candidate_id"), "CAND"))}'
        sid = short_id(full)
        rows.append({
            'signal_id': full,
            'short_signal_id': sid,
            'short_len': len(sid),
            'exec_comment': sid,
            'comment_len': len(sid),
            'entry_dt': s(r.get('entry_dt')),
            'role': s(r.get('role')),
            'route': s(r.get('route')),
            'candidate_id': s(r.get('candidate_id')),
            'direction': s(r.get('direction')),
            'format_version': 'GOLD_V3_SIGNAL_ID_V1',
            'status': 'CONTRACT_SAMPLE_ONLY_NO_SEND_NO_EXECUTION',
        })
    return pd.DataFrame(rows, columns=cols)


def locations() -> pd.DataFrame:
    return pd.DataFrame([
        {'artifact': 'trade_signal_ledger.csv', 'field': 'signal_id', 'required': True, 'purpose': 'canonical key'},
        {'artifact': 'trade_signal_ledger.csv', 'field': 'short_signal_id', 'required': True, 'purpose': 'compact key'},
        {'artifact': 'notification_events_rolling_30d.csv', 'field': 'signal_id', 'required': True, 'purpose': 'notification to signal link'},
        {'artifact': 'notification_events_rolling_30d.csv', 'field': 'short_signal_id', 'required': True, 'purpose': 'compact display'},
        {'artifact': 'future execution comment', 'field': 'comment', 'required': True, 'purpose': 'carry short key for later import'},
        {'artifact': 'actual_execution_ledger.csv', 'field': 'short_signal_id', 'required': True, 'purpose': 'join import to signal map'},
        {'artifact': 'execution_reconciliation_ledger.csv', 'field': 'signal_id', 'required': True, 'purpose': 'canonical reconciliation key'},
    ])


def id_map(contract: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    if contract.empty:
        return pd.DataFrame(columns=['short_signal_id', 'signal_id', 'entry_dt', 'candidate_id', 'direction', 'created_at_utc', 'audit_only'])
    return pd.DataFrame([{
        'short_signal_id': r['short_signal_id'],
        'signal_id': r['signal_id'],
        'entry_dt': r['entry_dt'],
        'candidate_id': r['candidate_id'],
        'direction': r['direction'],
        'created_at_utc': now,
        'audit_only': True,
    } for _, r in contract.iterrows()])


def notification_sample(contract: pd.DataFrame) -> pd.DataFrame:
    if contract.empty:
        return pd.DataFrame()
    return pd.DataFrame([{
        'event_dt': r['entry_dt'],
        'signal_id': r['signal_id'],
        'short_signal_id': r['short_signal_id'],
        'route': r['route'],
        'role': r['role'],
        'candidate_id': r['candidate_id'],
        'direction': r['direction'],
        'send_action': 'NO_SEND_AUDIT_ONLY',
        'message_status': 'DRY_RUN_NOT_SENT',
        'audit_only': True,
    } for _, r in contract.iterrows()])


def comment_sample(contract: pd.DataFrame) -> pd.DataFrame:
    if contract.empty:
        return pd.DataFrame()
    return pd.DataFrame([{
        'signal_id': r['signal_id'],
        'short_signal_id': r['short_signal_id'],
        'future_comment_value': r['exec_comment'],
        'comment_len': r['comment_len'],
        'future_import_join': 'extract short_signal_id then resolve through signal_id_map',
        'status': 'CONTRACT_SAMPLE_ONLY_NO_EXECUTION',
    } for _, r in contract.iterrows()])


def checks(contract: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if contract.empty:
        rows.append({'check_id': 'C000', 'passed': False, 'details': 'no rows'})
        return pd.DataFrame(rows)
    rows.append({'check_id': 'C001', 'passed': bool(contract['signal_id'].notna().all()), 'details': 'full id exists'})
    rows.append({'check_id': 'C002', 'passed': bool(contract['short_signal_id'].is_unique), 'details': 'short id unique in sample'})
    rows.append({'check_id': 'C003', 'passed': bool((contract['comment_len'] <= MAX_COMMENT_LEN).all()), 'details': 'comment length within local contract'})
    rows.append({'check_id': 'C004', 'passed': bool(contract['short_signal_id'].astype(str).str.match(r'^G3S[A-F0-9]+$').all()), 'details': 'short id format'})
    rows.append({'check_id': 'C005', 'passed': True, 'details': 'no send or execution enabled'})
    return pd.DataFrame(rows)


def contract_md() -> str:
    return '''# GOLD V3 Stage208 Signal ID Embedding Contract

Status: AUDIT_ONLY

Stage208 fixes the identity link between signal ledger, notification sample, future execution comment, actual execution ledger, and reconciliation ledger.

`signal_id` is the full canonical key.

`short_signal_id` is a compact deterministic key generated from the full key.

Future execution comments should carry the compact key. Future imports can then resolve the compact key back to full `signal_id` through `signal_id_map`.

This stage only creates contract samples. It does not send, execute, import actual history, create payload, or enable live hooks.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '208'
    out.mkdir(parents=True, exist_ok=True)

    blockers = []
    progress('load inputs')
    signal = read_csv_any(root / '204' / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
    d207 = read_csv_any(root / '207' / 'gold_v3_207_decision.csv')
    if signal.empty:
        blockers.append({'id': 'missing_stage204_signal_ledger'})
    if d207.empty:
        blockers.append({'id': 'missing_stage207_decision'})

    c = make_contract(signal)
    loc = locations()
    mp = id_map(c)
    ns = notification_sample(c)
    cs = comment_sample(c)
    vc = checks(c)
    md = contract_md()

    save(c, out / 'gold_v3_208_signal_id_contract_sample.csv')
    save(mp, out / 'gold_v3_208_signal_id_map_sample.csv')
    save(loc, out / 'gold_v3_208_embedding_locations.csv')
    save(ns, out / 'gold_v3_208_notification_event_with_signal_id_sample.csv')
    save(cs, out / 'gold_v3_208_execution_comment_contract_sample.csv')
    save(vc, out / 'gold_v3_208_signal_id_validation_checks.csv')
    (out / 'gold_v3_208_signal_id_embedding_contract.md').write_text(md, encoding='utf-8')

    validation_pass = bool(vc['passed'].all()) if not vc.empty and 'passed' in vc.columns else False
    ready = len(blockers) == 0 and validation_pass
    decision = 'STAGE208_SIGNAL_ID_EMBEDDING_CONTRACT_READY_AUDIT_ONLY' if ready else ('STAGE208_READY_WITH_VALIDATION_WARNINGS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE208_BLOCKED')
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
        'signal_rows_loaded': int(len(signal)) if not signal.empty else 0,
        'signal_id_contract_rows': int(len(c)) if not c.empty else 0,
        'short_signal_id_prefix': PREFIX,
        'short_hash_chars': HASH_CHARS,
        'max_comment_chars_by_local_contract': MAX_COMMENT_LEN,
        'validation_pass': validation_pass,
        'preferred_actual_match_after_embedding': 'short_signal_id_in_future_comment_resolved_to_full_signal_id',
        'actual_order_import_enabled': False,
        'actual_mt5_order_placed': False,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_208_decision.csv')
    (out / 'gold_v3_208_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 208 PASTE_ME_SIGNAL_ID_EMBEDDING_CONTRACT_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'SIGNAL_ID_EMBEDDING_CONTRACT_MD', md]
    lines += ['', 'SIGNAL_ID_CONTRACT_SAMPLE', show(c, 40)]
    lines += ['', 'SIGNAL_ID_MAP_SAMPLE', show(mp, 40)]
    lines += ['', 'EMBEDDING_LOCATIONS', show(loc, 80)]
    lines += ['', 'NOTIFICATION_EVENT_WITH_SIGNAL_ID_SAMPLE', show(ns, 40)]
    lines += ['', 'EXECUTION_COMMENT_CONTRACT_SAMPLE', show(cs, 40)]
    lines += ['', 'SIGNAL_ID_VALIDATION_CHECKS', show(vc, 80)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage208 is audit-only. It defines signal_id and short_signal_id embedding contracts only.']
    lines += ['Future execution comments can carry short_signal_id so actual execution can be matched back to full signal_id.']
    lines += ['No actual export is imported, no execution is placed, and no send/live hook/payload/autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
