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

STEP = 'GOLD_V3_205_ACTUAL_EXECUTION_LEDGER_CONTRACT_DRY_RUN_AUDIT_ONLY'
SOURCE_STAGE = 'STAGE205_ACTUAL_EXECUTION_LEDGER_CONTRACT_DRY_RUN'
COST_MODEL = 'actual_execution_plus_theoretical_reference'


def progress(msg: str) -> None:
    print(f'[205 progress] {msg}', flush=True)


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
    s = str(v).strip()
    return s == '' or s.lower() in {'nan', 'nat', 'none'}


def s(v: Any, default: str = '') -> str:
    return default if missing(v) else str(v)


def n(v: Any, default: Any = '') -> Any:
    return default if missing(v) else v


def build_actual_execution_contract(signal_ledger: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction',
        'symbol', 'account_id_hash', 'broker_server', 'magic_number',
        'order_id', 'deal_id_entry', 'deal_id_exit', 'position_id',
        'order_type', 'volume_lots', 'requested_entry_price', 'actual_entry_price',
        'entry_slippage_points', 'entry_spread_points', 'entry_commission',
        'requested_exit_price', 'actual_exit_price', 'exit_slippage_points',
        'exit_spread_points', 'exit_commission', 'swap',
        'gross_profit_account_ccy', 'net_profit_account_ccy', 'net_profit_points',
        'actual_open_time', 'actual_close_time', 'actual_holding_seconds',
        'actual_status', 'actual_close_reason', 'actual_comment',
        'source_signal_ledger', 'source_execution_export', 'created_at_utc', 'updated_at_utc',
        'audit_only'
    ]
    rows = []
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    if signal_ledger.empty:
        rows.append({
            'signal_id': 'SAMPLE_SIGNAL_ID', 'entry_dt': 'YYYY-MM-DD HH:MM:SS', 'role': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
            'route': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE', 'candidate_id': 'CANDIDATE_ID', 'direction': 'LONG_OR_SHORT',
            'symbol': 'XAUUSD', 'account_id_hash': '', 'broker_server': '', 'magic_number': '',
            'order_id': '', 'deal_id_entry': '', 'deal_id_exit': '', 'position_id': '',
            'order_type': '', 'volume_lots': '', 'requested_entry_price': '', 'actual_entry_price': '',
            'entry_slippage_points': '', 'entry_spread_points': '', 'entry_commission': '',
            'requested_exit_price': '', 'actual_exit_price': '', 'exit_slippage_points': '',
            'exit_spread_points': '', 'exit_commission': '', 'swap': '',
            'gross_profit_account_ccy': '', 'net_profit_account_ccy': '', 'net_profit_points': '',
            'actual_open_time': '', 'actual_close_time': '', 'actual_holding_seconds': '',
            'actual_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN', 'actual_close_reason': '', 'actual_comment': '',
            'source_signal_ledger': 'trade_signal_ledger.csv', 'source_execution_export': '', 'created_at_utc': now, 'updated_at_utc': '',
            'audit_only': True,
        })
    else:
        for _, r in signal_ledger.iterrows():
            rows.append({
                'signal_id': s(r.get('signal_id')), 'entry_dt': s(r.get('entry_dt')), 'role': s(r.get('role')),
                'route': s(r.get('route')), 'candidate_id': s(r.get('candidate_id')), 'direction': s(r.get('direction')),
                'symbol': 'XAUUSD', 'account_id_hash': '', 'broker_server': '', 'magic_number': '',
                'order_id': '', 'deal_id_entry': '', 'deal_id_exit': '', 'position_id': '',
                'order_type': s(r.get('direction')), 'volume_lots': '',
                'requested_entry_price': n(r.get('entry_price')), 'actual_entry_price': '',
                'entry_slippage_points': '', 'entry_spread_points': '', 'entry_commission': '',
                'requested_exit_price': '', 'actual_exit_price': '', 'exit_slippage_points': '',
                'exit_spread_points': '', 'exit_commission': '', 'swap': '',
                'gross_profit_account_ccy': '', 'net_profit_account_ccy': '', 'net_profit_points': '',
                'actual_open_time': '', 'actual_close_time': '', 'actual_holding_seconds': '',
                'actual_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN', 'actual_close_reason': '',
                'actual_comment': 'Contract row only. No MT5 order was placed by this audit.',
                'source_signal_ledger': 'gold_v3_204_trade_signal_ledger_enriched_sample.csv',
                'source_execution_export': 'future_mt5_account_history_export.csv',
                'created_at_utc': now, 'updated_at_utc': '', 'audit_only': True,
            })
    return pd.DataFrame(rows, columns=cols)


def build_theoretical_reference_schema(signal_ledger: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction',
        'entry_price', 'tp', 'sl', 'horizon_m5', 'theoretical_exit_dt', 'theoretical_exit_price',
        'theoretical_hit_type', 'theoretical_pnl_raw', 'theoretical_pnl_cost3', 'theoretical_pnl_cost5',
        'theoretical_source', 'created_at_utc', 'audit_only'
    ]
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    rows = []
    if signal_ledger.empty:
        rows.append({c: '' for c in cols})
        rows[0].update({'signal_id': 'SAMPLE_SIGNAL_ID', 'theoretical_source': 'future_m5_ohlc_resolution', 'created_at_utc': now, 'audit_only': True})
    else:
        for _, r in signal_ledger.iterrows():
            rows.append({
                'signal_id': s(r.get('signal_id')), 'entry_dt': s(r.get('entry_dt')), 'role': s(r.get('role')), 'route': s(r.get('route')),
                'candidate_id': s(r.get('candidate_id')), 'direction': s(r.get('direction')), 'entry_price': n(r.get('entry_price')),
                'tp': n(r.get('tp')), 'sl': n(r.get('sl')), 'horizon_m5': n(r.get('horizon_m5')),
                'theoretical_exit_dt': '', 'theoretical_exit_price': '', 'theoretical_hit_type': 'PENDING_DRY_RUN',
                'theoretical_pnl_raw': '', 'theoretical_pnl_cost3': '', 'theoretical_pnl_cost5': '',
                'theoretical_source': 'future_m5_ohlc_resolution', 'created_at_utc': now, 'audit_only': True,
            })
    return pd.DataFrame(rows, columns=cols)


def build_reconciliation_contract(signal_ledger: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction',
        'theoretical_hit_type', 'actual_status', 'actual_close_reason',
        'theoretical_pnl_cost3', 'actual_net_profit_points', 'actual_net_profit_account_ccy',
        'pnl_diff_points_actual_minus_theoretical_cost3', 'entry_slippage_points', 'exit_slippage_points',
        'total_commission', 'swap', 'execution_quality_tag', 'review_note', 'created_at_utc', 'audit_only'
    ]
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    rows = []
    if signal_ledger.empty:
        rows.append({c: '' for c in cols})
        rows[0].update({'signal_id': 'SAMPLE_SIGNAL_ID', 'actual_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN', 'execution_quality_tag': 'PENDING', 'created_at_utc': now, 'audit_only': True})
    else:
        for _, r in signal_ledger.iterrows():
            rows.append({
                'signal_id': s(r.get('signal_id')), 'entry_dt': s(r.get('entry_dt')), 'role': s(r.get('role')), 'route': s(r.get('route')),
                'candidate_id': s(r.get('candidate_id')), 'direction': s(r.get('direction')),
                'theoretical_hit_type': 'PENDING_DRY_RUN', 'actual_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN', 'actual_close_reason': '',
                'theoretical_pnl_cost3': '', 'actual_net_profit_points': '', 'actual_net_profit_account_ccy': '',
                'pnl_diff_points_actual_minus_theoretical_cost3': '', 'entry_slippage_points': '', 'exit_slippage_points': '',
                'total_commission': '', 'swap': '', 'execution_quality_tag': 'PENDING_NO_ACTUAL_EXECUTION',
                'review_note': 'Actual execution row will be filled from future MT5 order/history export, not by this audit.',
                'created_at_utc': now, 'audit_only': True,
            })
    return pd.DataFrame(rows, columns=cols)


def build_actual_monthly_schema() -> pd.DataFrame:
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    return pd.DataFrame([{
        'month': 'YYYY-MM',
        'role': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
        'route': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
        'candidate_id': 'ALL_OR_CANDIDATE_ID',
        'actual_trades': 0,
        'actual_wins': 0,
        'actual_losses': 0,
        'actual_win_rate_pct': '',
        'actual_gross_profit_account_ccy': '',
        'actual_gross_loss_account_ccy': '',
        'actual_pf': '',
        'actual_net_profit_account_ccy': '',
        'actual_avg_profit_account_ccy': '',
        'avg_entry_slippage_points': '',
        'avg_exit_slippage_points': '',
        'total_commission': '',
        'total_swap': '',
        'theoretical_pnl_cost3': '',
        'actual_minus_theoretical_cost3_points': '',
        'execution_quality_notes': '',
        'updated_at_utc': now,
    }])


def build_contract_md() -> str:
    return '''# GOLD V3 Stage205 Actual Execution Ledger Contract Dry-Run

Status: AUDIT_ONLY

## Purpose

Final performance review should use actual execution results.

Theoretical M5 OHLC results remain useful, but actual MT5 fills and exits are the most realistic source for live performance.

## Recommended structure

1. `trade_signal_ledger.csv`
   - signal occurrence and intended setup

2. `theoretical_result_ledger.csv`
   - M5 OHLC TP/SL/HORIZON resolution
   - used to judge strategy logic independent of execution quality

3. `actual_execution_ledger.csv`
   - actual MT5 order/deal/position history
   - used to judge real trade performance

4. `execution_reconciliation_ledger.csv`
   - compares theoretical result versus actual execution result
   - used to separate strategy losses from spread/slippage/commission/execution losses

## Actual execution fields to preserve

- signal_id
- order_id / deal_id / position_id
- actual entry and close time
- requested and actual entry price
- requested and actual exit price
- lot size
- commission
- swap
- spread/slippage proxies
- gross and net profit
- close reason

## Safety

Stage205 creates contract/sample files only. It does not send, order, create payload, or enable live hooks.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '205'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage204 enriched signal ledger')
    signal_ledger = read_csv_any(root / '204' / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
    stage204_decision = read_csv_any(root / '204' / 'gold_v3_204_decision.csv')
    if signal_ledger.empty:
        blockers.append({'id': 'missing_stage204_trade_signal_ledger_enriched_sample'})
    if stage204_decision.empty:
        blockers.append({'id': 'missing_stage204_decision'})

    actual_contract = pd.DataFrame()
    theoretical_contract = pd.DataFrame()
    reconciliation = pd.DataFrame()
    monthly_schema = pd.DataFrame()
    contract_md = build_contract_md()

    if not blockers:
        actual_contract = build_actual_execution_contract(signal_ledger)
        theoretical_contract = build_theoretical_reference_schema(signal_ledger)
        reconciliation = build_reconciliation_contract(signal_ledger)
        monthly_schema = build_actual_monthly_schema()
        save(actual_contract, out / 'gold_v3_205_actual_execution_ledger_contract_sample.csv')
        save(theoretical_contract, out / 'gold_v3_205_theoretical_result_ledger_contract_sample.csv')
        save(reconciliation, out / 'gold_v3_205_execution_reconciliation_ledger_contract_sample.csv')
        save(monthly_schema, out / 'gold_v3_205_actual_execution_monthly_summary_schema.csv')
        (out / 'gold_v3_205_actual_execution_ledger_contract.md').write_text(contract_md, encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE205_ACTUAL_EXECUTION_LEDGER_CONTRACT_READY_AUDIT_ONLY' if ready else 'STAGE205_BLOCKED'
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
        'signal_ledger_rows_loaded': int(len(signal_ledger)) if not signal_ledger.empty else 0,
        'actual_execution_contract_rows': int(len(actual_contract)) if not actual_contract.empty else 0,
        'theoretical_result_contract_rows': int(len(theoretical_contract)) if not theoretical_contract.empty else 0,
        'reconciliation_contract_rows': int(len(reconciliation)) if not reconciliation.empty else 0,
        'actual_order_import_enabled': False,
        'actual_mt5_order_placed': False,
        'actual_execution_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN',
        'performance_review_policy': 'Use actual execution ledger for final live performance. Keep theoretical M5 OHLC result ledger to separate strategy logic from execution cost/slippage/commission effects.',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_205_decision.csv')
    (out / 'gold_v3_205_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 205 PASTE_ME_ACTUAL_EXECUTION_LEDGER_CONTRACT_DRY_RUN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'ACTUAL_EXECUTION_LEDGER_CONTRACT_MD', contract_md]
    lines += ['', 'ACTUAL_EXECUTION_LEDGER_CONTRACT_SAMPLE', show(actual_contract, 40)]
    lines += ['', 'THEORETICAL_RESULT_LEDGER_CONTRACT_SAMPLE', show(theoretical_contract, 40)]
    lines += ['', 'EXECUTION_RECONCILIATION_LEDGER_CONTRACT_SAMPLE', show(reconciliation, 40)]
    lines += ['', 'ACTUAL_EXECUTION_MONTHLY_SUMMARY_SCHEMA', show(monthly_schema, 20)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage205 is audit-only. It defines actual execution ledger and reconciliation ledger contracts only.',
        'Final live performance should be reviewed by actual execution results, while theoretical results remain useful to separate strategy logic from execution quality.',
        'No actual MT5 order is placed. No send, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
