#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_204_TRADE_LEDGER_ENRICHED_DRY_RUN_AUDIT_ONLY'
SECONDARY_CLASS = 'SECONDARY_AUDIT_CANDIDATE'
SOURCE_STAGE = 'STAGE204_DRY_RUN_FROM_STAGE200_TAIL96'
COST_MODEL = 'cost3_primary_cost5_stress'


def progress(msg: str) -> None:
    print(f'[204 progress] {msg}', flush=True)


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
    if missing(v):
        return default
    try:
        f = float(v)
        if math.isfinite(f):
            return f
    except Exception:
        pass
    return v


def ts(v: Any) -> str:
    if missing(v):
        return ''
    try:
        return str(pd.Timestamp(v))
    except Exception:
        return str(v)


def signal_rows_from_tail(tail: pd.DataFrame) -> pd.DataFrame:
    if tail.empty:
        return pd.DataFrame()
    x = tail.copy()
    final = x['final_route'].astype(str) if 'final_route' in x.columns else pd.Series(['NO_SIGNAL'] * len(x))
    return x[final.ne('NO_SIGNAL')].copy().reset_index(drop=True)


def row_to_signal_ledger(r: pd.Series) -> dict[str, Any]:
    route = s(r.get('final_route'), 'NO_SIGNAL')
    role = 'PRIMARY' if route == 'PRIMARY' else SECONDARY_CLASS
    prefix = 'primary' if role == 'PRIMARY' else 'secondary'
    entry_dt = ts(r.get('dt'))
    candidate_id = s(r.get(f'{prefix}_candidate_id'), 'NO_SIGNAL')
    direction = s(r.get(f'{prefix}_direction'), s(r.get(f'{prefix}_signal'), 'NO_SIGNAL'))
    signal_id = f'{entry_dt}_{role}_{candidate_id}'.replace(' ', '_').replace(':', '').replace('-', '')
    return {
        'signal_id': signal_id,
        'entry_dt': entry_dt,
        'role': role,
        'route': route,
        'candidate_id': candidate_id,
        'direction': direction,
        'entry_price': n(r.get('m15_close')),
        'tp': n(r.get(f'{prefix}_tp')),
        'sl': n(r.get(f'{prefix}_sl')),
        'horizon_m5': n(r.get(f'{prefix}_horizon_m5')),
        'rule_version': 'GOLD_V3_STAGE199_FILTERED_V1_OHLC_RECOMPUTED' if role == SECONDARY_CLASS else 'GOLD_V3_STAGE187_PRIMARY_ABC_CAP',
        'source_stage': SOURCE_STAGE,
        'cost_model': COST_MODEL,
        'm15_close': n(r.get('m15_close')),
        'h1_atr14': n(r.get('h1_atr14')),
        'd1_dist_close_atr28': n(r.get('d1_dist_close_atr28')),
        'h4_body_atr14': n(r.get('h4_body_atr14')),
        'final_route': route,
        'send_action': s(r.get('send_action'), 'NO_SEND_AUDIT_ONLY'),
        'status': 'SIGNAL_ONLY_DRY_RUN',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'audit_only': True,
    }


def build_enriched_signal_ledger(tail: pd.DataFrame) -> pd.DataFrame:
    sig = signal_rows_from_tail(tail)
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction', 'entry_price',
        'tp', 'sl', 'horizon_m5', 'rule_version', 'source_stage', 'cost_model',
        'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14',
        'final_route', 'send_action', 'status', 'created_at_utc', 'audit_only'
    ]
    if sig.empty:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([row_to_signal_ledger(r) for _, r in sig.iterrows()], columns=cols)


def build_result_schema_sample(signal_ledger: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'exit_dt', 'role', 'route', 'candidate_id', 'direction',
        'entry_price', 'exit_price', 'tp', 'sl', 'horizon_m5', 'result_status', 'hit_type',
        'pnl_raw', 'pnl_cost3', 'pnl_cost5', 'r_multiple', 'holding_m5_bars',
        'close_reason', 'loss_reason_tag', 'review_note', 'source_stage', 'cost_model',
        'created_at_utc', 'updated_at_utc', 'audit_only'
    ]
    if signal_ledger.empty:
        sample = {
            'signal_id': 'SAMPLE_SIGNAL_ID',
            'entry_dt': 'YYYY-MM-DD HH:MM:SS',
            'exit_dt': 'YYYY-MM-DD HH:MM:SS',
            'role': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
            'route': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
            'candidate_id': 'CANDIDATE_ID',
            'direction': 'LONG_OR_SHORT',
            'entry_price': '',
            'exit_price': '',
            'tp': '',
            'sl': '',
            'horizon_m5': '',
            'result_status': 'RESOLVED_OR_OPEN_OR_CANCELLED',
            'hit_type': 'TP_OR_SL_OR_HORIZON_OR_MANUAL',
            'pnl_raw': '',
            'pnl_cost3': '',
            'pnl_cost5': '',
            'r_multiple': '',
            'holding_m5_bars': '',
            'close_reason': '',
            'loss_reason_tag': '',
            'review_note': '',
            'source_stage': SOURCE_STAGE,
            'cost_model': COST_MODEL,
            'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            'updated_at_utc': '',
            'audit_only': True,
        }
        return pd.DataFrame([sample], columns=cols)
    rows = []
    for _, r in signal_ledger.iterrows():
        rows.append({
            'signal_id': r['signal_id'],
            'entry_dt': r['entry_dt'],
            'exit_dt': '',
            'role': r['role'],
            'route': r['route'],
            'candidate_id': r['candidate_id'],
            'direction': r['direction'],
            'entry_price': r['entry_price'],
            'exit_price': '',
            'tp': r['tp'],
            'sl': r['sl'],
            'horizon_m5': r['horizon_m5'],
            'result_status': 'PENDING_DRY_RUN',
            'hit_type': '',
            'pnl_raw': '',
            'pnl_cost3': '',
            'pnl_cost5': '',
            'r_multiple': '',
            'holding_m5_bars': '',
            'close_reason': '',
            'loss_reason_tag': '',
            'review_note': '',
            'source_stage': SOURCE_STAGE,
            'cost_model': COST_MODEL,
            'created_at_utc': r['created_at_utc'],
            'updated_at_utc': '',
            'audit_only': True,
        })
    return pd.DataFrame(rows, columns=cols)


def build_monthly_schema_sample(signal_ledger: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'month', 'role', 'route', 'candidate_id', 'trades', 'wins', 'losses', 'open_or_pending',
        'win_rate_pct', 'gross_profit', 'gross_loss', 'pf', 'sum_pnl_cost3', 'sum_pnl_cost5',
        'avg_pnl_cost3', 'avg_pnl_cost5', 'max_loss_streak', 'weak_hour_notes', 'loss_reason_top',
        'source_result_ledger', 'updated_at_utc'
    ]
    if signal_ledger.empty:
        return pd.DataFrame([{
            'month': 'YYYY-MM',
            'role': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
            'route': 'PRIMARY_OR_SECONDARY_AUDIT_CANDIDATE',
            'candidate_id': 'ALL_OR_CANDIDATE_ID',
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'open_or_pending': 0,
            'win_rate_pct': '',
            'gross_profit': '',
            'gross_loss': '',
            'pf': '',
            'sum_pnl_cost3': '',
            'sum_pnl_cost5': '',
            'avg_pnl_cost3': '',
            'avg_pnl_cost5': '',
            'max_loss_streak': '',
            'weak_hour_notes': '',
            'loss_reason_top': '',
            'source_result_ledger': 'trade_result_ledger.csv',
            'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        }], columns=cols)
    x = signal_ledger.copy()
    x['month'] = pd.to_datetime(x['entry_dt']).dt.to_period('M').astype(str)
    rows = []
    for (month, role, route, candidate_id), g in x.groupby(['month', 'role', 'route', 'candidate_id'], sort=True):
        rows.append({
            'month': month,
            'role': role,
            'route': route,
            'candidate_id': candidate_id,
            'trades': int(len(g)),
            'wins': 0,
            'losses': 0,
            'open_or_pending': int(len(g)),
            'win_rate_pct': '',
            'gross_profit': '',
            'gross_loss': '',
            'pf': '',
            'sum_pnl_cost3': '',
            'sum_pnl_cost5': '',
            'avg_pnl_cost3': '',
            'avg_pnl_cost5': '',
            'max_loss_streak': '',
            'weak_hour_notes': '',
            'loss_reason_top': '',
            'source_result_ledger': 'trade_result_ledger.csv',
            'updated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        })
    return pd.DataFrame(rows, columns=cols)


def validate_signal_ledger(df: pd.DataFrame) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if df.empty:
        return issues
    required = ['signal_id', 'entry_dt', 'role', 'candidate_id', 'direction', 'entry_price', 'tp', 'sl', 'horizon_m5']
    for col in required:
        if col not in df.columns:
            issues.append({'id': 'missing_col', 'col': col})
        else:
            bad = df[col].apply(missing).sum()
            if bad:
                issues.append({'id': 'missing_required_values', 'col': col, 'count': int(bad)})
    return issues


def build_plan_md() -> str:
    return '''# GOLD V3 Stage204 Trade Ledger Enriched Dry-Run Plan

Status: AUDIT_ONLY

## Purpose

The long-retention trade ledger must be useful for later review.

It must include not only signal time and candidate id, but also TP, SL, horizon, source stage, cost model, and the main entry-time features.

## Required signal ledger fields

- signal_id
- entry_dt
- role
- route
- candidate_id
- direction
- entry_price
- tp
- sl
- horizon_m5
- rule_version
- source_stage
- cost_model
- m15_close
- h1_atr14
- d1_dist_close_atr28
- h4_body_atr14
- final_route
- status

## Required result ledger fields

- signal_id
- entry_dt
- exit_dt
- role
- candidate_id
- direction
- entry_price
- exit_price
- hit_type
- pnl_raw
- pnl_cost3
- pnl_cost5
- r_multiple
- holding_m5_bars
- loss_reason_tag
- review_note

## Why this matters

Later review needs to answer:

- which candidate loses
- which role loses
- win rate
- PF
- trade count
- weak time ranges
- whether cost5 stress breaks the strategy
- whether losses cluster by feature state

Stage204 is a dry-run only. It does not send, order, create payload, or enable live hooks.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '204'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage200/203 sources')
    stage200_tail = read_csv_any(root / '200' / 'gold_v3_200_no_send_latest_tail96.csv')
    stage203_decision = read_csv_any(root / '203' / 'gold_v3_203_decision.csv')
    if stage200_tail.empty:
        blockers.append({'id': 'missing_stage200_tail96'})
    if stage203_decision.empty:
        blockers.append({'id': 'missing_stage203_decision'})

    signal_ledger = pd.DataFrame()
    result_schema = pd.DataFrame()
    monthly_schema = pd.DataFrame()
    validation_issues: list[dict[str, Any]] = []
    plan = build_plan_md()

    if not blockers:
        signal_ledger = build_enriched_signal_ledger(stage200_tail)
        result_schema = build_result_schema_sample(signal_ledger)
        monthly_schema = build_monthly_schema_sample(signal_ledger)
        validation_issues = validate_signal_ledger(signal_ledger)
        save(signal_ledger, out / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
        save(result_schema, out / 'gold_v3_204_trade_result_ledger_schema_sample.csv')
        save(monthly_schema, out / 'gold_v3_204_trade_history_monthly_summary_schema_sample.csv')
        save(pd.DataFrame(validation_issues), out / 'gold_v3_204_trade_signal_ledger_validation_issues.csv')
        (out / 'gold_v3_204_trade_ledger_enriched_plan.md').write_text(plan, encoding='utf-8')

    ready = len(blockers) == 0 and len(validation_issues) == 0
    decision = 'STAGE204_TRADE_LEDGER_ENRICHED_DRY_RUN_READY_AUDIT_ONLY' if ready else ('STAGE204_READY_WITH_LEDGER_VALIDATION_WARNINGS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE204_BLOCKED')
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
        'signal_ledger_rows': int(len(signal_ledger)) if not signal_ledger.empty else 0,
        'result_schema_rows': int(len(result_schema)) if not result_schema.empty else 0,
        'monthly_schema_rows': int(len(monthly_schema)) if not monthly_schema.empty else 0,
        'ledger_validation_issue_count': int(len(validation_issues)),
        'tp_sl_horizon_present_in_signal_ledger': bool(len(validate_signal_ledger(signal_ledger)) == 0) if not signal_ledger.empty else True,
        'retention_answer': 'Long-retention trade signal ledger must include TP/SL/horizon, source stage, cost model, and entry-time features. Trade result ledger must support win rate, PF, trade count, and loss-reason review.',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_204_decision.csv')
    (out / 'gold_v3_204_summary.json').write_text(json.dumps({**summary, 'blockers': blockers, 'validation_issues': validation_issues}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 204 PASTE_ME_TRADE_LEDGER_ENRICHED_DRY_RUN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'TRADE_LEDGER_ENRICHED_PLAN_MD', plan]
    lines += ['', 'TRADE_SIGNAL_LEDGER_ENRICHED_SAMPLE', show(signal_ledger, 40)]
    lines += ['', 'TRADE_RESULT_LEDGER_SCHEMA_SAMPLE', show(result_schema, 40)]
    lines += ['', 'TRADE_HISTORY_MONTHLY_SUMMARY_SCHEMA_SAMPLE', show(monthly_schema, 40)]
    lines += ['', 'TRADE_SIGNAL_LEDGER_VALIDATION_ISSUES', 'NO_ISSUES' if not validation_issues else json.dumps(validation_issues, ensure_ascii=False, indent=2)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage204 is audit-only. It enriches the long-retention trade signal/result ledger dry-run design.',
        'The signal ledger now carries TP, SL, horizon, cost model, source stage, and entry-time features for later review.',
        'No send, order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
