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

STEP = 'GOLD_V3_207_ACTUAL_EXECUTION_IMPORT_CONTRACT_AUDIT_ONLY'
SOURCE_STAGE = 'STAGE207_ACTUAL_EXECUTION_IMPORT_CONTRACT_AUDIT_ONLY'


def progress(msg: str) -> None:
    print(f'[207 progress] {msg}', flush=True)


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


def build_expected_import_schema() -> pd.DataFrame:
    rows = [
        {'canonical_field': 'signal_id', 'required': False, 'type': 'string', 'description': 'Preferred direct link to trade_signal_ledger. May be absent in manual/legacy exports.'},
        {'canonical_field': 'symbol', 'required': True, 'type': 'string', 'description': 'Trading symbol, expected XAUUSD/gold symbol variant.'},
        {'canonical_field': 'direction', 'required': True, 'type': 'string', 'description': 'LONG/SHORT, BUY/SELL accepted then normalized.'},
        {'canonical_field': 'order_id', 'required': False, 'type': 'string', 'description': 'MT5 order ticket if available.'},
        {'canonical_field': 'deal_id_entry', 'required': False, 'type': 'string', 'description': 'MT5 entry deal ticket if available.'},
        {'canonical_field': 'deal_id_exit', 'required': False, 'type': 'string', 'description': 'MT5 exit deal ticket if available.'},
        {'canonical_field': 'position_id', 'required': True, 'type': 'string', 'description': 'MT5 position id / position ticket. Required for robust grouping.'},
        {'canonical_field': 'magic_number', 'required': False, 'type': 'string', 'description': 'Strategy magic number if future live route uses one.'},
        {'canonical_field': 'volume_lots', 'required': True, 'type': 'float', 'description': 'Executed lot size.'},
        {'canonical_field': 'actual_open_time', 'required': True, 'type': 'datetime', 'description': 'Actual position open time from MT5.'},
        {'canonical_field': 'actual_close_time', 'required': True, 'type': 'datetime', 'description': 'Actual position close time from MT5.'},
        {'canonical_field': 'actual_entry_price', 'required': True, 'type': 'float', 'description': 'Actual filled entry price.'},
        {'canonical_field': 'actual_exit_price', 'required': True, 'type': 'float', 'description': 'Actual filled exit price.'},
        {'canonical_field': 'gross_profit_account_ccy', 'required': False, 'type': 'float', 'description': 'Gross P/L before commission/swap if available.'},
        {'canonical_field': 'commission', 'required': False, 'type': 'float', 'description': 'Total commission or sum of entry/exit commission.'},
        {'canonical_field': 'swap', 'required': False, 'type': 'float', 'description': 'Swap charged or credited.'},
        {'canonical_field': 'net_profit_account_ccy', 'required': True, 'type': 'float', 'description': 'Net P/L in account currency.'},
        {'canonical_field': 'close_reason', 'required': False, 'type': 'string', 'description': 'TP/SL/manual/stopout/other if available.'},
        {'canonical_field': 'comment', 'required': False, 'type': 'string', 'description': 'MT5 position/deal comment. Can contain signal id in future.'},
        {'canonical_field': 'broker_server', 'required': False, 'type': 'string', 'description': 'Broker/server name for audit only.'},
        {'canonical_field': 'account_id_hash', 'required': False, 'type': 'string', 'description': 'Hashed account id only. Do not store raw account number in shared artifacts.'},
    ]
    return pd.DataFrame(rows)


def build_field_mapping() -> pd.DataFrame:
    rows = [
        {'canonical_field': 'signal_id', 'accepted_source_names': 'signal_id, SignalID, comment_signal_id'},
        {'canonical_field': 'symbol', 'accepted_source_names': 'symbol, Symbol, instrument'},
        {'canonical_field': 'direction', 'accepted_source_names': 'direction, type, Type, side, order_type, BUY/SELL'},
        {'canonical_field': 'order_id', 'accepted_source_names': 'order_id, Order, order, ticket'},
        {'canonical_field': 'deal_id_entry', 'accepted_source_names': 'deal_id_entry, entry_deal, DealEntry'},
        {'canonical_field': 'deal_id_exit', 'accepted_source_names': 'deal_id_exit, exit_deal, DealExit'},
        {'canonical_field': 'position_id', 'accepted_source_names': 'position_id, Position, position, position_ticket'},
        {'canonical_field': 'magic_number', 'accepted_source_names': 'magic_number, Magic, magic'},
        {'canonical_field': 'volume_lots', 'accepted_source_names': 'volume_lots, Volume, volume, Lots, lots'},
        {'canonical_field': 'actual_open_time', 'accepted_source_names': 'actual_open_time, open_time, Time, time_open'},
        {'canonical_field': 'actual_close_time', 'accepted_source_names': 'actual_close_time, close_time, TimeClose, time_close'},
        {'canonical_field': 'actual_entry_price', 'accepted_source_names': 'actual_entry_price, entry_price, PriceOpen, price_open'},
        {'canonical_field': 'actual_exit_price', 'accepted_source_names': 'actual_exit_price, exit_price, PriceClose, price_close'},
        {'canonical_field': 'gross_profit_account_ccy', 'accepted_source_names': 'gross_profit, GrossProfit'},
        {'canonical_field': 'commission', 'accepted_source_names': 'commission, Commission'},
        {'canonical_field': 'swap', 'accepted_source_names': 'swap, Swap'},
        {'canonical_field': 'net_profit_account_ccy', 'accepted_source_names': 'net_profit, Profit, profit, NetProfit'},
        {'canonical_field': 'close_reason', 'accepted_source_names': 'close_reason, reason, CloseReason'},
        {'canonical_field': 'comment', 'accepted_source_names': 'comment, Comment'},
        {'canonical_field': 'broker_server', 'accepted_source_names': 'broker_server, server'},
        {'canonical_field': 'account_id_hash', 'accepted_source_names': 'account_id_hash'},
    ]
    return pd.DataFrame(rows)


def build_sample_import_rows(signal: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'symbol', 'direction', 'order_id', 'deal_id_entry', 'deal_id_exit', 'position_id',
        'magic_number', 'volume_lots', 'actual_open_time', 'actual_close_time', 'actual_entry_price',
        'actual_exit_price', 'gross_profit_account_ccy', 'commission', 'swap', 'net_profit_account_ccy',
        'close_reason', 'comment', 'broker_server', 'account_id_hash', 'row_status'
    ]
    if signal.empty:
        row = {c: '' for c in cols}
        row.update({'symbol': 'XAUUSD', 'direction': 'SHORT', 'row_status': 'SCHEMA_SAMPLE_ONLY'})
        return pd.DataFrame([row], columns=cols)
    r = signal.iloc[0]
    row = {
        'signal_id': str(r.get('signal_id', '')),
        'symbol': 'XAUUSD',
        'direction': str(r.get('direction', '')),
        'order_id': '',
        'deal_id_entry': '',
        'deal_id_exit': '',
        'position_id': '',
        'magic_number': '',
        'volume_lots': '',
        'actual_open_time': '',
        'actual_close_time': '',
        'actual_entry_price': '',
        'actual_exit_price': '',
        'gross_profit_account_ccy': '',
        'commission': '',
        'swap': '',
        'net_profit_account_ccy': '',
        'close_reason': '',
        'comment': 'future MT5 export row. No actual order imported in Stage207.',
        'broker_server': '',
        'account_id_hash': '',
        'row_status': 'NO_ACTUAL_EXPORT_YET_CONTRACT_SAMPLE',
    }
    return pd.DataFrame([row], columns=cols)


def build_join_contract(signal: pd.DataFrame, theoretical: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'candidate_id', 'direction', 'theoretical_hit_type',
        'actual_import_status', 'preferred_match_key', 'fallback_match_key', 'match_window_seconds',
        'entry_price_tolerance_points', 'match_result', 'actual_position_id', 'actual_order_id',
        'actual_net_profit_account_ccy', 'notes'
    ]
    rows = []
    sig = signal.copy()
    if sig.empty:
        return pd.DataFrame(columns=cols)
    theo = theoretical.set_index('signal_id') if not theoretical.empty and 'signal_id' in theoretical.columns else pd.DataFrame()
    for _, r in sig.iterrows():
        sid = str(r.get('signal_id', ''))
        th = theo.loc[sid].to_dict() if not theo.empty and sid in theo.index else {}
        rows.append({
            'signal_id': sid,
            'entry_dt': str(r.get('entry_dt', '')),
            'candidate_id': str(r.get('candidate_id', '')),
            'direction': str(r.get('direction', '')),
            'theoretical_hit_type': str(th.get('theoretical_hit_type', '')),
            'actual_import_status': 'NO_ACTUAL_EXPORT_YET',
            'preferred_match_key': 'signal_id embedded in comment/magic/export',
            'fallback_match_key': 'symbol + direction + open_time within window + entry price tolerance',
            'match_window_seconds': 300,
            'entry_price_tolerance_points': 3.0,
            'match_result': 'UNMATCHED_SIGNAL_PENDING_ACTUAL_EXPORT',
            'actual_position_id': '',
            'actual_order_id': '',
            'actual_net_profit_account_ccy': '',
            'notes': 'No actual import is enabled in Stage207.',
        })
    return pd.DataFrame(rows, columns=cols)


def build_unmatched_signal_sample(join_contract: pd.DataFrame) -> pd.DataFrame:
    cols = ['signal_id', 'entry_dt', 'candidate_id', 'direction', 'reason', 'status', 'review_action']
    if join_contract.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for _, r in join_contract.iterrows():
        rows.append({
            'signal_id': r.get('signal_id', ''),
            'entry_dt': r.get('entry_dt', ''),
            'candidate_id': r.get('candidate_id', ''),
            'direction': r.get('direction', ''),
            'reason': 'NO_ACTUAL_EXPORT_YET',
            'status': 'EXPECTED_IN_DRY_RUN',
            'review_action': 'Wait for future actual_execution export before judging execution quality.',
        })
    return pd.DataFrame(rows, columns=cols)


def build_orphan_execution_schema() -> pd.DataFrame:
    return pd.DataFrame([{
        'import_row_id': 'SAMPLE_IMPORT_ROW_ID',
        'symbol': 'XAUUSD',
        'direction': 'LONG_OR_SHORT',
        'position_id': '',
        'order_id': '',
        'actual_open_time': '',
        'actual_entry_price': '',
        'net_profit_account_ccy': '',
        'reason': 'ACTUAL_EXECUTION_WITHOUT_MATCHED_SIGNAL',
        'status': 'SCHEMA_ONLY_NO_ACTUAL_IMPORT',
        'review_action': 'Investigate manual trade, duplicate export, missing signal id, or wrong magic/comment.',
    }])


def build_validation_rules() -> pd.DataFrame:
    rows = [
        {'rule_id': 'V001', 'level': 'ERROR', 'rule': 'Required actual execution fields must exist before real import is accepted.'},
        {'rule_id': 'V002', 'level': 'ERROR', 'rule': 'Raw account id must not be stored in shared artifacts; store hash only.'},
        {'rule_id': 'V003', 'level': 'WARN', 'rule': 'signal_id missing: fallback match is allowed but must be marked lower confidence.'},
        {'rule_id': 'V004', 'level': 'WARN', 'rule': 'actual open time outside match window creates unmatched_signal or orphan_execution.'},
        {'rule_id': 'V005', 'level': 'WARN', 'rule': 'entry price difference beyond tolerance creates execution_quality warning.'},
        {'rule_id': 'V006', 'level': 'ERROR', 'rule': 'NO_SIGNAL rows must not create actual execution rows.'},
        {'rule_id': 'V007', 'level': 'ERROR', 'rule': 'Import contract stage must not place orders or enable live hook.'},
    ]
    return pd.DataFrame(rows)


def build_contract_md() -> str:
    return '''# GOLD V3 Stage207 Actual Execution Import Contract

Status: AUDIT_ONLY

## Purpose

Define how future MT5 account-history exports will be imported and matched to GOLD V3 signal ledger rows.

Stage207 does not import real orders, place orders, send notifications, or enable live hooks.

## Matching priority

1. Prefer direct `signal_id` match.
   - Future order comments or export rows should carry the signal id whenever possible.

2. If signal id is missing, use fallback matching:
   - symbol
   - direction
   - actual open time close to signal entry time
   - actual entry price close to intended entry price
   - optional magic number / comment

3. If a signal has no actual execution match:
   - write `unmatched_signal` row.

4. If an actual execution has no signal match:
   - write `orphan_execution` row.

## Why this matters

Actual execution performance should be the final live-performance source.
Theoretical result remains useful as a strategy reference.
Reconciliation separates strategy loss from execution cost, spread, slippage, commission, swap, and manual/external trade effects.

## Safety

This stage only creates contract/sample files under Stage207 output.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '207'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage204/206/205 outputs')
    signal = read_csv_any(root / '204' / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
    theoretical = read_csv_any(root / '206' / 'gold_v3_206_theoretical_result_ledger_resolved_sample.csv')
    stage205_decision = read_csv_any(root / '205' / 'gold_v3_205_decision.csv')
    if signal.empty:
        blockers.append({'id': 'missing_stage204_signal_ledger'})
    if theoretical.empty:
        blockers.append({'id': 'missing_stage206_theoretical_result_ledger'})
    if stage205_decision.empty:
        blockers.append({'id': 'missing_stage205_decision'})

    expected_schema = build_expected_import_schema()
    mapping = build_field_mapping()
    sample_import = build_sample_import_rows(signal)
    join_contract = build_join_contract(signal, theoretical)
    unmatched_signal = build_unmatched_signal_sample(join_contract)
    orphan_schema = build_orphan_execution_schema()
    validation_rules = build_validation_rules()
    contract_md = build_contract_md()

    save(expected_schema, out / 'gold_v3_207_actual_execution_import_expected_schema.csv')
    save(mapping, out / 'gold_v3_207_actual_execution_import_field_mapping.csv')
    save(sample_import, out / 'gold_v3_207_actual_execution_import_sample_no_real_orders.csv')
    save(join_contract, out / 'gold_v3_207_signal_actual_execution_join_contract_sample.csv')
    save(unmatched_signal, out / 'gold_v3_207_unmatched_signal_contract_sample.csv')
    save(orphan_schema, out / 'gold_v3_207_orphan_execution_contract_schema.csv')
    save(validation_rules, out / 'gold_v3_207_import_validation_rules.csv')
    (out / 'gold_v3_207_actual_execution_import_contract.md').write_text(contract_md, encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE207_ACTUAL_EXECUTION_IMPORT_CONTRACT_READY_AUDIT_ONLY' if ready else 'STAGE207_BLOCKED'
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
        'actual_order_import_enabled': False,
        'actual_mt5_order_placed': False,
        'actual_export_rows_loaded': 0,
        'signal_rows_loaded': int(len(signal)) if not signal.empty else 0,
        'theoretical_rows_loaded': int(len(theoretical)) if not theoretical.empty else 0,
        'expected_import_schema_rows': int(len(expected_schema)),
        'preferred_match_key': 'signal_id',
        'fallback_match_key': 'symbol_direction_time_window_entry_price_tolerance',
        'fallback_match_window_seconds': 300,
        'fallback_entry_price_tolerance_points': 3.0,
        'unmatched_signal_rows_sample': int(len(unmatched_signal)),
        'orphan_execution_schema_ready': True,
        'raw_account_id_allowed': False,
        'account_id_hash_only': True,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_207_decision.csv')
    (out / 'gold_v3_207_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 207 PASTE_ME_ACTUAL_EXECUTION_IMPORT_CONTRACT_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'ACTUAL_EXECUTION_IMPORT_CONTRACT_MD', contract_md]
    lines += ['', 'EXPECTED_IMPORT_SCHEMA', show(expected_schema, 80)]
    lines += ['', 'FIELD_MAPPING', show(mapping, 80)]
    lines += ['', 'SAMPLE_IMPORT_NO_REAL_ORDERS', show(sample_import, 40)]
    lines += ['', 'SIGNAL_ACTUAL_EXECUTION_JOIN_CONTRACT_SAMPLE', show(join_contract, 40)]
    lines += ['', 'UNMATCHED_SIGNAL_CONTRACT_SAMPLE', show(unmatched_signal, 40)]
    lines += ['', 'ORPHAN_EXECUTION_CONTRACT_SCHEMA', show(orphan_schema, 40)]
    lines += ['', 'IMPORT_VALIDATION_RULES', show(validation_rules, 80)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage207 is audit-only. It defines future actual execution import schema and matching rules only.',
        'No actual order export is imported, no MT5 order is placed, and no live hook/payload/autotrade is enabled.',
        'Preferred match is signal_id. Fallback match is symbol/direction/time/entry-price tolerance and must be marked lower confidence.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
