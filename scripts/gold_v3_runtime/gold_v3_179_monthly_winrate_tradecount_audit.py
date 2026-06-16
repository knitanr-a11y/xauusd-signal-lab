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

STEP = 'GOLD_V3_179_MONTHLY_WINRATE_TRADECOUNT_AUDIT_ONLY'
BENCHMARK_PF = 2.237
DEFAULT_COST_POINTS = 3.0


def progress(msg: str) -> None:
    print(f'[179 progress] {msg}', flush=True)


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


def pf_from_series(x: pd.Series) -> float:
    y = pd.to_numeric(x, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    if y.empty:
        return math.nan
    gp = float(y[y > 0].sum())
    gl = float(-y[y < 0].sum())
    if gl == 0:
        return math.inf if gp > 0 else 0.0
    return gp / gl


def monthly_table(trades: pd.DataFrame, cost_points: float) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    tr = trades.copy()
    tr['pnl_net'] = pd.to_numeric(tr['pnl_raw'], errors='coerce') - float(cost_points)
    tr['month'] = pd.to_datetime(tr['entry_dt']).dt.to_period('M').astype(str)
    tr['is_win'] = tr['pnl_net'] > 0
    tr['is_loss'] = tr['pnl_net'] < 0
    rows = []
    for month, g in tr.groupby('month', sort=True):
        n = int(len(g))
        wins = int(g['is_win'].sum())
        losses = int(g['is_loss'].sum())
        flats = int(n - wins - losses)
        rows.append({
            'month': month,
            'trades': n,
            'wins': wins,
            'losses': losses,
            'flats': flats,
            'win_rate': wins / n if n else math.nan,
            'pf': pf_from_series(g['pnl_net']),
            'pnl_sum': float(g['pnl_net'].sum()),
            'avg_pnl': float(g['pnl_net'].mean()),
            'tp_hits': int((g['hit_type'] == 'TP').sum()) if 'hit_type' in g.columns else 0,
            'sl_hits': int((g['hit_type'] == 'SL').sum()) if 'hit_type' in g.columns else 0,
            'horizon_exits': int((g['hit_type'] == 'HORIZON').sum()) if 'hit_type' in g.columns else 0,
        })
    return pd.DataFrame(rows)


def yearly_table(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame()
    x = monthly.copy()
    x['year'] = x['month'].astype(str).str.slice(0, 4)
    rows = []
    for year, g in x.groupby('year', sort=True):
        trades = int(g['trades'].sum())
        wins = int(g['wins'].sum())
        losses = int(g['losses'].sum())
        rows.append({
            'year': year,
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'flats': int(g['flats'].sum()),
            'win_rate': wins / trades if trades else math.nan,
            'pnl_sum': float(g['pnl_sum'].sum()),
            'negative_months': int((g['pnl_sum'] < 0).sum()),
            'positive_months': int((g['pnl_sum'] > 0).sum()),
        })
    return pd.DataFrame(rows)


def choose_candidate(robust: pd.DataFrame, cost_points: float) -> pd.Series | None:
    if robust.empty:
        return None
    x = robust[(robust['scope'].eq('dedup_resolved_only')) & (robust['cost_points'].astype(float).eq(float(cost_points)))].copy()
    if x.empty:
        return None
    x_valid = x[x.get('beats_old_pf_2_237', False).astype(bool)].copy() if 'beats_old_pf_2_237' in x.columns else pd.DataFrame()
    if not x_valid.empty:
        x = x_valid
    return x.sort_values(['full_pf', 'test_pf', 'train_pf', 'full_n'], ascending=[False, False, False, False]).iloc[0]


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    ap.add_argument('--old-rank', type=int, default=0, help='Optional Stage177 old_rank to force. Default chooses best dedup cost candidate that passes min counts/PF.')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out177 = root / '177'
    out178 = root / '178'
    out = root / '179'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []

    progress('load Stage178 robustness rows')
    robust = read_csv_any(out178 / 'gold_v3_178_cost_robustness_all.csv')
    if robust.empty:
        blockers.append({'id': 'missing_stage178_cost_robustness_all', 'path': str(out178 / 'gold_v3_178_cost_robustness_all.csv')})

    cand177 = read_csv_any(out177 / 'gold_v3_177_top100_rules.csv')
    if cand177.empty:
        blockers.append({'id': 'missing_stage177_top100_rules', 'path': str(out177 / 'gold_v3_177_top100_rules.csv')})

    selected: pd.Series | None = None
    if not robust.empty:
        if args.old_rank > 0:
            forced = robust[(robust['old_rank'].astype(int).eq(args.old_rank)) & robust['scope'].eq('dedup_resolved_only') & robust['cost_points'].astype(float).eq(float(args.cost_points))]
            if forced.empty:
                blockers.append({'id': 'forced_old_rank_not_found', 'old_rank': args.old_rank, 'cost_points': args.cost_points})
            else:
                selected = forced.iloc[0]
        else:
            selected = choose_candidate(robust, args.cost_points)
            if selected is None:
                blockers.append({'id': 'no_stage178_candidate_for_cost', 'cost_points': args.cost_points})

    frames: dict[str, pd.DataFrame] = {}
    source_diag = pd.DataFrame()
    if not blockers:
        progress('load OHLC with Stage177 gold_2025/live contract')
        raw_diag_rows: list[dict[str, Any]] = []
        for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
            frames[tf], diag = s177.combine(tf, data_dir)
            raw_diag_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({'id': 'missing_combined_ohlc', 'tf': tf})
        source_diag = pd.DataFrame(raw_diag_rows)
        save(source_diag, out / 'gold_v3_179_source_coverage.csv')

    monthly = pd.DataFrame()
    yearly = pd.DataFrame()
    selected_meta: dict[str, Any] = {}
    if not blockers and selected is not None:
        progress('replay selected candidate and build monthly table')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        conds = s177.base.make_conditions(data)
        rule_to_mask = {name: mask for name, mask in conds}
        rule = str(selected['rule'])
        mask = s178.build_rule_mask(rule, rule_to_mask, len(data))
        entries = data.loc[mask].copy()
        if entries.empty:
            blockers.append({'id': 'selected_rule_replay_empty', 'rule': rule})
        else:
            direction = str(selected['direction'])
            tp = float(selected['tp'])
            sl = float(selected['sl'])
            horizon = int(selected['horizon_m5'])
            raw_trades = s178.compute_outcome_with_exit(entries, frames['m5'], direction, tp, sl, horizon)
            dedup_trades = s178.dedup_resolved_only(raw_trades)
            monthly = monthly_table(dedup_trades, args.cost_points)
            yearly = yearly_table(monthly)
            save(dedup_trades, out / 'gold_v3_179_selected_dedup_trades.csv')
            save(monthly, out / 'gold_v3_179_selected_monthly.csv')
            save(yearly, out / 'gold_v3_179_selected_yearly.csv')
            selected_meta = {
                'selected_old_rank': int(selected['old_rank']),
                'selected_direction': direction,
                'selected_tp': tp,
                'selected_sl': sl,
                'selected_horizon_m5': horizon,
                'selected_rule': rule,
                'selected_cost_points': float(args.cost_points),
                'selected_scope': 'dedup_resolved_only',
                'selected_train_n': int(selected.get('train_n', 0)),
                'selected_test_n': int(selected.get('test_n', 0)),
                'selected_full_n': int(selected.get('full_n', 0)),
                'selected_train_pf': float(selected.get('train_pf', math.nan)),
                'selected_test_pf': float(selected.get('test_pf', math.nan)),
                'selected_full_pf': float(selected.get('full_pf', math.nan)),
                'selected_beats_old_pf_2_237': bool(selected.get('beats_old_pf_2_237', False)),
            }

    ready = len(blockers) == 0
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE179_MONTHLY_TABLE_READY_AUDIT_ONLY' if ready else 'STAGE179_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'old_pf_benchmark': BENCHMARK_PF,
        **selected_meta,
        'monthly_rows': int(len(monthly)) if not monthly.empty else 0,
        'yearly_rows': int(len(yearly)) if not yearly.empty else 0,
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
    (out / 'gold_v3_179_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_179_decision.csv')

    lines = ['GOLD V3 179 PASTE_ME_MONTHLY_WINRATE_TRADECOUNT_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'SELECTED_YEARLY', yearly.to_string(index=False) if not yearly.empty else 'NO_YEARLY_TABLE']
    lines += ['', 'SELECTED_MONTHLY', monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY_TABLE']
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage179 is audit-only. It selects the best Stage178 dedup_resolved_only candidate at the requested cost level, preferring candidates that satisfy the old PF benchmark and minimum train/test/full counts. Monthly win rate is computed after subtracting cost_points from each trade pnl. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
