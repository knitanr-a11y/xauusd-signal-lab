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
import gold_v3_177_ohlc_only_rebuild_search_audit_entry as s177
import gold_v3_200_primary_secondary_no_send_preview_packet_audit as s200

STEP = 'GOLD_V3_211_INTEGRATED_NO_SEND_CYCLE_RUNNER_AUDIT_ONLY'
SECONDARY = 'SECONDARY_AUDIT_CANDIDATE'
SHORT_PREFIX = 'G3S'
HASH_CHARS = 20
ROLLING_DEBUG_TAIL_ROWS = 500


def progress(msg: str) -> None:
    print(f'[211 progress] {msg}', flush=True)


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
    return SHORT_PREFIX + h


def selected_candidates_file(root: Path) -> Path:
    matches = sorted((root / '193').glob('gold_v3_193_scalping_selected_profit_stack_*.csv'))
    return matches[0] if matches else root / '193' / 'gold_v3_193_scalping_selected_profit_stack_missing.csv'


def row_identity(row: pd.Series) -> dict[str, Any]:
    route = s(row.get('final_route'), 'NO_SIGNAL')
    if route == 'PRIMARY':
        prefix = 'primary'
        role = 'PRIMARY'
    elif route == SECONDARY:
        prefix = 'secondary'
        role = SECONDARY
    else:
        return {'role': 'NO_SIGNAL', 'signal_id': '', 'short_signal_id': '', 'candidate_id': 'NO_SIGNAL', 'direction': 'NO_SIGNAL', 'tp': '', 'sl': '', 'horizon_m5': ''}
    dt_txt = pd.Timestamp(row['dt']).strftime('%Y%m%d_%H%M%S')
    candidate = s(row.get(f'{prefix}_candidate_id'), 'NO_SIGNAL')
    direction = s(row.get(f'{prefix}_direction'), 'NO_SIGNAL')
    full_id = f'{dt_txt}_{role}_{candidate}'
    return {
        'role': role,
        'signal_id': full_id,
        'short_signal_id': make_short(full_id),
        'candidate_id': candidate,
        'direction': direction,
        'tp': n(row.get(f'{prefix}_tp')),
        'sl': n(row.get(f'{prefix}_sl')),
        'horizon_m5': n(row.get(f'{prefix}_horizon_m5')),
    }


def latest_state(row: pd.Series, ident: dict[str, Any]) -> dict[str, Any]:
    return {
        'schema_version': 1,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'latest_closed_m15_dt': str(pd.Timestamp(row['dt'])),
        'final_route': s(row.get('final_route'), 'NO_SIGNAL'),
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


def signal_append(row: pd.Series, ident: dict[str, Any]) -> pd.DataFrame:
    cols = ['signal_id', 'short_signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction', 'entry_price', 'tp', 'sl', 'horizon_m5', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14', 'status', 'created_at_utc', 'audit_only']
    if ident.get('role') == 'NO_SIGNAL':
        return pd.DataFrame(columns=cols)
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
        'status': 'DRY_RUN_SIGNAL_APPEND_PREVIEW',
        'created_at_utc': now,
        'audit_only': True,
    }], columns=cols)


def notification_append(row: pd.Series, ident: dict[str, Any]) -> pd.DataFrame:
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


def no_signal_counter(row: pd.Series, ident: dict[str, Any]) -> pd.DataFrame:
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
    }])


def health_rollup(row: pd.Series, counter: pd.DataFrame) -> pd.DataFrame:
    c = counter.iloc[0]
    return pd.DataFrame([{
        'date': c['date'],
        'evaluated_closed_m15_rows': int(c['evaluated_closed_m15_rows']),
        'final_signal_rows': int(c['final_signal_increment']),
        'final_no_signal_rows': int(c['final_no_signal_increment']),
        'primary_no_signal_rows': int(c['primary_no_signal_increment']),
        'secondary_no_signal_rows': int(c['secondary_no_signal_increment']),
        'blocker_rows': 0,
        'send_rows': 0,
        'execution_rows': 0,
        'actual_import_rows': 0,
        'latest_closed_m15_dt': str(pd.Timestamp(row['dt'])),
        'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'audit_only': True,
    }])


def write_plan(route: str, signal_rows: int, notif_rows: int, counter_rows: int, debug_rows: int) -> pd.DataFrame:
    return pd.DataFrame([
        {'target_file': 'latest_state.json', 'write_mode': 'overwrite_preview_only', 'rows_or_objects': 1, 'audit_only': True},
        {'target_file': 'trade_signal_ledger.csv', 'write_mode': 'append_if_signal_only_preview', 'rows_or_objects': signal_rows, 'audit_only': True},
        {'target_file': 'notification_events_rolling_30d.csv', 'write_mode': 'append_if_signal_only_preview_no_send', 'rows_or_objects': notif_rows, 'audit_only': True},
        {'target_file': 'no_signal_counters_daily_hourly.csv', 'write_mode': 'counter_increment_preview', 'rows_or_objects': counter_rows, 'audit_only': True},
        {'target_file': 'debug_tail_snapshot.csv', 'write_mode': f'rolling_last_{ROLLING_DEBUG_TAIL_ROWS}_preview', 'rows_or_objects': debug_rows, 'audit_only': True},
        {'target_file': 'health_rollup_daily.csv', 'write_mode': 'daily_rollup_preview', 'rows_or_objects': 1, 'audit_only': True},
        {'target_file': 'actual_execution_ledger.csv', 'write_mode': 'no_write_actual_import_disabled', 'rows_or_objects': 0, 'audit_only': True},
    ]).assign(latest_final_route=route)


def validation_checks(route: str, sig: pd.DataFrame, notif: pd.DataFrame, counter: pd.DataFrame) -> pd.DataFrame:
    no_signal = route == 'NO_SIGNAL'
    return pd.DataFrame([
        {'check_id': 'I001', 'passed': True, 'details': 'OHLC detector was rebuilt in this stage'},
        {'check_id': 'I002', 'passed': bool((not no_signal) or sig.empty), 'details': 'NO_SIGNAL does not append trade_signal rows'},
        {'check_id': 'I003', 'passed': bool((not no_signal) or notif.empty), 'details': 'NO_SIGNAL does not append notification rows'},
        {'check_id': 'I004', 'passed': bool((not no_signal) or not counter.empty), 'details': 'NO_SIGNAL increments counter'},
        {'check_id': 'I005', 'passed': True, 'details': 'send disabled'},
        {'check_id': 'I006', 'passed': True, 'details': 'execution disabled'},
        {'check_id': 'I007', 'passed': True, 'details': 'payload/live hook/autotrade disabled'},
    ])


def plan_md() -> str:
    return '''# GOLD V3 Stage211 Integrated No-Send Cycle Runner

Status: AUDIT_ONLY

Stage211 rebuilds the latest cycle from OHLC and produces no-send write previews in one stage.

Integrated flow:

1. Read closed M15/H1/H4/D1 candles.
2. Build features using the Stage177 feature contract.
3. Detect PRIMARY and SECONDARY_AUDIT_CANDIDATE candidates.
4. Decide final route with PRIMARY priority.
5. Generate signal_id and short_signal_id only if SIGNAL exists.
6. Build latest_state preview.
7. Build append previews or NO_SIGNAL counter preview.
8. Keep send, execution, actual import, payload, live hook, and autotrade disabled.

This stage does not mutate live retention files.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '211'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}

    progress('load stage prerequisites and OHLC')
    selected_path = selected_candidates_file(root)
    selected = read_csv_any(selected_path)
    d208 = read_csv_any(root / '208' / 'gold_v3_208_decision.csv')
    d210 = read_csv_any(root / '210' / 'gold_v3_210_decision.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_secondary_candidates'})
    if d208.empty:
        blockers.append({'id': 'missing_stage208_decision'})
    if d210.empty:
        blockers.append({'id': 'missing_stage210_decision'})

    if not blockers:
        for tf in ['m15', 'h1', 'h4', 'd1']:
            frames[tf], diag = s177.combine(tf, data_dir)
            source_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({'id': 'missing_ohlc', 'tf': tf})
        if source_rows:
            save(pd.DataFrame(source_rows), out / 'gold_v3_211_source_coverage.csv')

    tail = pd.DataFrame()
    latest = {}
    ident = {'role': 'NO_SIGNAL'}
    state = {}
    sig = pd.DataFrame()
    notif = pd.DataFrame()
    counter = pd.DataFrame()
    health = pd.DataFrame()
    plan = pd.DataFrame()
    checks = pd.DataFrame()
    abc_entries = pd.DataFrame()
    sec_entries = pd.DataFrame()
    detector_problems: list[dict[str, Any]] = []

    if not blockers:
        progress('rebuild features and detector entries')
        feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
        abc_entries, abc_problems = s200.build_abc_entries(feat)
        priority = s200.selected_priority(selected)
        sec_entries, sec_problems = s200.build_secondary_entries(feat, selected, priority)
        detector_problems.extend(abc_problems + sec_problems)
        if detector_problems:
            blockers.append({'id': 'detector_problems', 'count': len(detector_problems), 'sample': detector_problems[:5]})
        else:
            save(abc_entries, out / 'gold_v3_211_primary_detector_entries.csv')
            save(sec_entries, out / 'gold_v3_211_secondary_detector_entries.csv')
            tail = s200.build_tail_packet(feat, abc_entries, sec_entries)
            save(tail, out / 'gold_v3_211_integrated_tail96.csv')
            latest = tail.iloc[-1].to_dict() if not tail.empty else {}
            ident = row_identity(pd.Series(latest)) if latest else {'role': 'NO_SIGNAL'}
            state = latest_state(pd.Series(latest), ident) if latest else {}
            sig = signal_append(pd.Series(latest), ident) if latest else pd.DataFrame()
            notif = notification_append(pd.Series(latest), ident) if latest else pd.DataFrame()
            counter = no_signal_counter(pd.Series(latest), ident) if latest else pd.DataFrame()
            health = health_rollup(pd.Series(latest), counter) if latest and not counter.empty else pd.DataFrame()
            route = s(latest.get('final_route'), 'NO_SIGNAL') if latest else 'NO_SIGNAL'
            plan = write_plan(route, len(sig), len(notif), len(counter), min(len(tail), ROLLING_DEBUG_TAIL_ROWS))
            checks = validation_checks(route, sig, notif, counter)
            (out / 'gold_v3_211_latest_state_integrated_preview.json').write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
            save(sig, out / 'gold_v3_211_trade_signal_append_integrated_preview.csv')
            save(notif, out / 'gold_v3_211_notification_append_integrated_preview.csv')
            save(counter, out / 'gold_v3_211_no_signal_counter_integrated_preview.csv')
            save(health, out / 'gold_v3_211_health_rollup_integrated_preview.csv')
            save(plan, out / 'gold_v3_211_integrated_write_plan.csv')
            save(checks, out / 'gold_v3_211_integrated_validation_checks.csv')
            save(tail.tail(ROLLING_DEBUG_TAIL_ROWS), out / 'gold_v3_211_debug_tail_integrated_preview.csv')
            (out / 'gold_v3_211_integrated_no_send_cycle_plan.md').write_text(plan_md(), encoding='utf-8')

    validation_pass = bool(checks['passed'].all()) if not checks.empty and 'passed' in checks.columns else False
    ready = len(blockers) == 0 and validation_pass
    route = s(latest.get('final_route'), 'NO_SIGNAL') if latest else 'NO_SIGNAL'
    decision = 'STAGE211_INTEGRATED_NO_SEND_CYCLE_RUNNER_READY_AUDIT_ONLY' if ready else ('STAGE211_READY_WITH_VALIDATION_WARNINGS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE211_BLOCKED')
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
        'integrated_from_ohlc': True,
        'latest_closed_m15_dt': str(latest.get('dt', '')) if latest else '',
        'latest_final_route': route,
        'latest_role': ident.get('role', 'NO_SIGNAL'),
        'latest_signal_id': ident.get('signal_id', ''),
        'latest_short_signal_id': ident.get('short_signal_id', ''),
        'tail96_rows': int(len(tail)) if not tail.empty else 0,
        'tail96_primary_signal_rows': int(tail['primary_signal'].astype(str).ne('NO_SIGNAL').sum()) if not tail.empty else 0,
        'tail96_secondary_signal_rows': int(tail['secondary_signal'].astype(str).ne('NO_SIGNAL').sum()) if not tail.empty else 0,
        'tail96_final_signal_rows': int(tail['final_route'].astype(str).ne('NO_SIGNAL').sum()) if not tail.empty else 0,
        'trade_signal_append_preview_rows': int(len(sig)),
        'notification_append_preview_rows': int(len(notif)),
        'no_signal_counter_preview_rows': int(len(counter)),
        'health_rollup_preview_rows': int(len(health)),
        'validation_pass': validation_pass,
        'no_signal_full_row_append': False,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_211_decision.csv')
    (out / 'gold_v3_211_summary.json').write_text(json.dumps({**summary, 'blockers': blockers, 'detector_problems': detector_problems}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 211 PASTE_ME_INTEGRATED_NO_SEND_CYCLE_RUNNER_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'INTEGRATED_NO_SEND_CYCLE_PLAN_MD', plan_md()]
    lines += ['', 'LATEST_STATE_INTEGRATED_PREVIEW_JSON', json.dumps(state, ensure_ascii=False, indent=2, default=str) if state else '{}']
    lines += ['', 'INTEGRATED_WRITE_PLAN', show(plan, 80)]
    lines += ['', 'TRADE_SIGNAL_APPEND_INTEGRATED_PREVIEW', show(sig, 40)]
    lines += ['', 'NOTIFICATION_APPEND_INTEGRATED_PREVIEW', show(notif, 40)]
    lines += ['', 'NO_SIGNAL_COUNTER_INTEGRATED_PREVIEW', show(counter, 40)]
    lines += ['', 'HEALTH_ROLLUP_INTEGRATED_PREVIEW', show(health, 40)]
    lines += ['', 'INTEGRATED_VALIDATION_CHECKS', show(checks, 80)]
    lines += ['', 'LATEST_TAIL96_LAST10', show(tail.tail(10), 20)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage211 is audit-only. It rebuilds detector output from closed OHLC and previews one no-send live cycle.']
    lines += ['No live retention files are mutated; all outputs are Stage211 previews.']
    lines += ['No send, execution, actual import, payload, live hook, or autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
