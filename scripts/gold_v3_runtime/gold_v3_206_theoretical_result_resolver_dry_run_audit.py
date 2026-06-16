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

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_177_ohlc_only_rebuild_search_audit_entry as s177
import gold_v3_178_cost_spread_slippage_monthly_robustness_audit as s178

STEP = 'GOLD_V3_206_THEORETICAL_RESULT_RESOLVER_DRY_RUN_AUDIT_ONLY'
PRIMARY_COST = 3.0
STRESS_COST = 5.0
SOURCE_STAGE = 'STAGE206_THEORETICAL_RESULT_RESOLVER_DRY_RUN'
THEORETICAL_SOURCE = 'M5_OHLC_TP_SL_HORIZON_RESOLUTION_SL_PRIORITY_IF_SAME_M5'


def progress(msg: str) -> None:
    print(f'[206 progress] {msg}', flush=True)


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


def f(v: Any, default: float = math.nan) -> float:
    if missing(v):
        return default
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def i(v: Any, default: int = 0) -> int:
    if missing(v):
        return default
    try:
        return int(float(v))
    except Exception:
        return default


def theoretical_exit_price(entry_price: float, direction: str, pnl_raw: float) -> float:
    if not math.isfinite(entry_price) or not math.isfinite(pnl_raw):
        return math.nan
    if direction == 'LONG':
        return entry_price + pnl_raw
    if direction == 'SHORT':
        return entry_price - pnl_raw
    return math.nan


def holding_m5_bars(entry_dt: Any, exit_dt: Any) -> Any:
    try:
        delta = pd.Timestamp(exit_dt) - pd.Timestamp(entry_dt)
        return int(round(delta.total_seconds() / 300.0))
    except Exception:
        return ''


def resolve_one(row: pd.Series, m5: pd.DataFrame) -> dict[str, Any]:
    entry_dt = pd.Timestamp(row['entry_dt'])
    direction = s(row.get('direction')).upper()
    tp = f(row.get('tp'))
    sl = f(row.get('sl'))
    horizon_m5 = i(row.get('horizon_m5'))
    entry_price = f(row.get('entry_price', row.get('m15_close')))
    base = {
        'signal_id': s(row.get('signal_id')),
        'entry_dt': str(entry_dt),
        'role': s(row.get('role')),
        'route': s(row.get('route')),
        'candidate_id': s(row.get('candidate_id')),
        'direction': direction,
        'entry_price': entry_price,
        'tp': tp,
        'sl': sl,
        'horizon_m5': horizon_m5,
        'theoretical_exit_dt': '',
        'theoretical_exit_price': '',
        'theoretical_hit_type': 'PENDING_OR_UNRESOLVED',
        'theoretical_pnl_raw': '',
        'theoretical_pnl_cost3': '',
        'theoretical_pnl_cost5': '',
        'theoretical_r_multiple': '',
        'theoretical_holding_m5_bars': '',
        'theoretical_source': THEORETICAL_SOURCE,
        'source_stage': SOURCE_STAGE,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'audit_only': True,
    }
    if direction not in {'LONG', 'SHORT'} or not math.isfinite(tp) or not math.isfinite(sl) or horizon_m5 <= 0 or not math.isfinite(entry_price):
        base['theoretical_hit_type'] = 'UNRESOLVED_BAD_SIGNAL_ROW'
        return base
    entries = pd.DataFrame([{
        'dt': entry_dt,
        'm15_close': entry_price,
        'h1_atr14': f(row.get('h1_atr14')),
    }])
    out = s178.compute_outcome_with_exit(entries, m5, direction, tp, sl, horizon_m5)
    if out.empty:
        base['theoretical_hit_type'] = 'UNRESOLVED_M5_NOT_AVAILABLE'
        return base
    r = out.iloc[0]
    pnl_raw = f(r.get('pnl_raw'))
    exit_dt = pd.Timestamp(r.get('exit_dt'))
    exit_price = theoretical_exit_price(entry_price, direction, pnl_raw)
    base.update({
        'theoretical_exit_dt': str(exit_dt),
        'theoretical_exit_price': exit_price,
        'theoretical_hit_type': s(r.get('hit_type'), 'UNKNOWN'),
        'theoretical_pnl_raw': pnl_raw,
        'theoretical_pnl_cost3': pnl_raw - PRIMARY_COST,
        'theoretical_pnl_cost5': pnl_raw - STRESS_COST,
        'theoretical_r_multiple': pnl_raw / sl if sl and math.isfinite(sl) else '',
        'theoretical_holding_m5_bars': holding_m5_bars(entry_dt, exit_dt),
    })
    return base


def resolve_all(signal_ledger: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction', 'entry_price',
        'tp', 'sl', 'horizon_m5', 'theoretical_exit_dt', 'theoretical_exit_price',
        'theoretical_hit_type', 'theoretical_pnl_raw', 'theoretical_pnl_cost3', 'theoretical_pnl_cost5',
        'theoretical_r_multiple', 'theoretical_holding_m5_bars', 'theoretical_source', 'source_stage',
        'created_at_utc', 'audit_only'
    ]
    if signal_ledger.empty:
        return pd.DataFrame(columns=cols)
    rows = [resolve_one(r, m5) for _, r in signal_ledger.iterrows()]
    return pd.DataFrame(rows, columns=cols)


def build_reconciliation_pending(theo: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'signal_id', 'entry_dt', 'role', 'route', 'candidate_id', 'direction',
        'theoretical_hit_type', 'theoretical_pnl_cost3', 'theoretical_pnl_cost5',
        'actual_status', 'actual_net_profit_points', 'actual_net_profit_account_ccy',
        'pnl_diff_points_actual_minus_theoretical_cost3', 'execution_quality_tag', 'review_note',
        'created_at_utc', 'audit_only'
    ]
    if theo.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    for _, r in theo.iterrows():
        rows.append({
            'signal_id': s(r.get('signal_id')), 'entry_dt': s(r.get('entry_dt')), 'role': s(r.get('role')),
            'route': s(r.get('route')), 'candidate_id': s(r.get('candidate_id')), 'direction': s(r.get('direction')),
            'theoretical_hit_type': s(r.get('theoretical_hit_type')), 'theoretical_pnl_cost3': r.get('theoretical_pnl_cost3', ''),
            'theoretical_pnl_cost5': r.get('theoretical_pnl_cost5', ''),
            'actual_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN', 'actual_net_profit_points': '', 'actual_net_profit_account_ccy': '',
            'pnl_diff_points_actual_minus_theoretical_cost3': '', 'execution_quality_tag': 'PENDING_ACTUAL_EXECUTION',
            'review_note': 'Theoretical result is resolved. Actual execution comparison waits for future MT5 order/history export.',
            'created_at_utc': now, 'audit_only': True,
        })
    return pd.DataFrame(rows, columns=cols)


def pf_metrics(pnl: pd.Series) -> dict[str, Any]:
    x = pd.to_numeric(pnl, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    if x.empty:
        return {'trades': 0, 'wins': 0, 'losses': 0, 'sum_pnl': 0.0, 'pf': math.nan, 'win_rate_pct': math.nan}
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    return {
        'trades': int(len(x)),
        'wins': int((x > 0).sum()),
        'losses': int((x < 0).sum()),
        'sum_pnl': float(x.sum()),
        'pf': gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0),
        'win_rate_pct': float((x > 0).mean() * 100.0),
    }


def build_theoretical_monthly_summary(theo: pd.DataFrame) -> pd.DataFrame:
    cols = [
        'month', 'role', 'route', 'candidate_id', 'trades', 'wins', 'losses', 'win_rate_pct',
        'sum_pnl_raw', 'pf_raw', 'sum_pnl_cost3', 'pf_cost3', 'sum_pnl_cost5', 'pf_cost5',
        'tp_count', 'sl_count', 'horizon_count', 'updated_at_utc'
    ]
    if theo.empty:
        return pd.DataFrame(columns=cols)
    x = theo.copy()
    x['month'] = pd.to_datetime(x['entry_dt']).dt.to_period('M').astype(str)
    rows = []
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    for (month, role, route, candidate_id), g in x.groupby(['month', 'role', 'route', 'candidate_id'], sort=True):
        raw = pf_metrics(g['theoretical_pnl_raw'])
        c3 = pf_metrics(g['theoretical_pnl_cost3'])
        c5 = pf_metrics(g['theoretical_pnl_cost5'])
        rows.append({
            'month': month, 'role': role, 'route': route, 'candidate_id': candidate_id,
            'trades': raw['trades'], 'wins': c3['wins'], 'losses': c3['losses'], 'win_rate_pct': c3['win_rate_pct'],
            'sum_pnl_raw': raw['sum_pnl'], 'pf_raw': raw['pf'],
            'sum_pnl_cost3': c3['sum_pnl'], 'pf_cost3': c3['pf'],
            'sum_pnl_cost5': c5['sum_pnl'], 'pf_cost5': c5['pf'],
            'tp_count': int(g['theoretical_hit_type'].astype(str).eq('TP').sum()),
            'sl_count': int(g['theoretical_hit_type'].astype(str).eq('SL').sum()),
            'horizon_count': int(g['theoretical_hit_type'].astype(str).eq('HORIZON').sum()),
            'updated_at_utc': now,
        })
    return pd.DataFrame(rows, columns=cols)


def build_source_coverage(m5: pd.DataFrame, data_dir: Path, diag: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for d in diag:
        rows.append(dict(d))
    rows.append({
        'tf': 'M5_COMBINED',
        'source': 'stage177_combine_contract',
        'path': str(data_dir),
        'rows': int(len(m5)),
        'dt_min': str(m5['dt'].min()) if not m5.empty and 'dt' in m5.columns else '',
        'dt_max': str(m5['dt'].max()) if not m5.empty and 'dt' in m5.columns else '',
    })
    return pd.DataFrame(rows)


def build_plan_md() -> str:
    return '''# GOLD V3 Stage206 Theoretical Result Resolver Dry-Run

Status: AUDIT_ONLY

## Purpose

Stage206 resolves the theoretical M5 OHLC result for signal ledger rows.

This fills theoretical result fields only:

- theoretical_exit_dt
- theoretical_exit_price
- theoretical_hit_type
- theoretical_pnl_raw
- theoretical_pnl_cost3
- theoretical_pnl_cost5
- theoretical_holding_m5_bars

Actual execution remains pending until future MT5 order/history export is available.

## Rules

- Entry detection already happened before this stage.
- M5 OHLC is used only for theoretical outcome resolution.
- If TP and SL are touched in the same M5 bar, SL priority is applied.
- No actual order is placed.
- No notification is sent.

## Why this matters

Theoretical result shows strategy logic performance.
Actual execution result later shows real broker/execution performance.
The reconciliation ledger then separates strategy loss from execution cost, spread, slippage, commission, and swap effects.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '206'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load signal ledger and M5 candles')
    signal_ledger = read_csv_any(root / '204' / 'gold_v3_204_trade_signal_ledger_enriched_sample.csv')
    stage205_decision = read_csv_any(root / '205' / 'gold_v3_205_decision.csv')
    m5, diag = s177.combine('M5', data_dir)
    if signal_ledger.empty:
        blockers.append({'id': 'missing_stage204_trade_signal_ledger_enriched_sample'})
    if stage205_decision.empty:
        blockers.append({'id': 'missing_stage205_decision'})
    if m5.empty:
        blockers.append({'id': 'missing_m5_candles'})

    source_coverage = build_source_coverage(m5, data_dir, diag)
    theoretical = pd.DataFrame()
    reconciliation = pd.DataFrame()
    monthly = pd.DataFrame()
    plan = build_plan_md()

    if not blockers:
        theoretical = resolve_all(signal_ledger, m5)
        reconciliation = build_reconciliation_pending(theoretical)
        monthly = build_theoretical_monthly_summary(theoretical)
        save(theoretical, out / 'gold_v3_206_theoretical_result_ledger_resolved_sample.csv')
        save(reconciliation, out / 'gold_v3_206_execution_reconciliation_pending_actual_sample.csv')
        save(monthly, out / 'gold_v3_206_theoretical_monthly_summary_sample.csv')
        (out / 'gold_v3_206_theoretical_result_resolver_plan.md').write_text(plan, encoding='utf-8')
    save(source_coverage, out / 'gold_v3_206_source_coverage.csv')

    unresolved_count = int(theoretical['theoretical_hit_type'].astype(str).str.startswith('UNRESOLVED').sum()) if not theoretical.empty else 0
    ready = len(blockers) == 0 and unresolved_count == 0
    decision = 'STAGE206_THEORETICAL_RESULT_RESOLVER_READY_AUDIT_ONLY' if ready else ('STAGE206_READY_WITH_UNRESOLVED_THEORETICAL_ROWS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE206_BLOCKED')
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
        'signal_ledger_rows_loaded': int(len(signal_ledger)) if not signal_ledger.empty else 0,
        'm5_rows_loaded': int(len(m5)) if not m5.empty else 0,
        'theoretical_result_rows': int(len(theoretical)) if not theoretical.empty else 0,
        'unresolved_theoretical_rows': unresolved_count,
        'theoretical_tp_count': int(theoretical['theoretical_hit_type'].astype(str).eq('TP').sum()) if not theoretical.empty else 0,
        'theoretical_sl_count': int(theoretical['theoretical_hit_type'].astype(str).eq('SL').sum()) if not theoretical.empty else 0,
        'theoretical_horizon_count': int(theoretical['theoretical_hit_type'].astype(str).eq('HORIZON').sum()) if not theoretical.empty else 0,
        'actual_execution_status': 'NO_ACTUAL_ORDER_YET_DRY_RUN',
        'actual_mt5_order_placed': False,
        'actual_order_import_enabled': False,
        'theoretical_resolution_source': THEORETICAL_SOURCE,
        'sl_priority_if_same_m5_bar': True,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_206_decision.csv')
    (out / 'gold_v3_206_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 206 PASTE_ME_THEORETICAL_RESULT_RESOLVER_DRY_RUN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'THEORETICAL_RESULT_RESOLVER_PLAN_MD', plan]
    lines += ['', 'SOURCE_COVERAGE', show(source_coverage, 20)]
    lines += ['', 'THEORETICAL_RESULT_LEDGER_RESOLVED_SAMPLE', show(theoretical, 40)]
    lines += ['', 'EXECUTION_RECONCILIATION_PENDING_ACTUAL_SAMPLE', show(reconciliation, 40)]
    lines += ['', 'THEORETICAL_MONTHLY_SUMMARY_SAMPLE', show(monthly, 40)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage206 is audit-only. It resolves theoretical M5 OHLC outcomes for signal ledger rows only.',
        'Actual execution remains pending and is not imported or placed by this stage.',
        'No send, order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
