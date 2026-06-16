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
import gold_v3_179_monthly_winrate_tradecount_audit as s179

STEP = 'GOLD_V3_187_PRIMARY_ABC_CAP_PORTFOLIO_REFREEZE_AUDIT_ONLY'
DEFAULT_COST_POINTS = 3.0
BENCHMARK_PF = 2.237

PRIMARY_CANDIDATES = [
    {
        'candidate_id': 'A_PRECISION_BASE',
        'role': 'PRIMARY',
        'priority_acb': 1,
        'priority_cab': 2,
        'description': 'Primary precision candidate. Unchanged from Stage185.',
        'rule': 'd1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347',
        'direction': 'LONG',
        'tp': 40.0,
        'sl': 20.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'B_HIGH_FREQUENCY_CAP40',
        'role': 'PRIMARY',
        'priority_acb': 3,
        'priority_cab': 3,
        'description': 'Primary high-frequency candidate with Stage186 h1_atr14 cap.',
        'rule': 'd1_dist_close_atr28<=-0.394892 & h1_atr14<=40',
        'direction': 'LONG',
        'tp': 50.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'C_BALANCED_CAP60',
        'role': 'PRIMARY',
        'priority_acb': 2,
        'priority_cab': 1,
        'description': 'Primary balanced candidate with Stage184 h1_atr14 cap.',
        'rule': 'd1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60',
        'direction': 'LONG',
        'tp': 30.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
]

PRIORITY_SCENARIOS = {
    'ACB_PRIORITY_A_GT_C_GT_B': 'priority_acb',
    'CAB_PRIORITY_C_GT_A_GT_B': 'priority_cab',
}


def progress(msg: str) -> None:
    print(f'[187 progress] {msg}', flush=True)


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def pf_sum_wr(pnl: pd.Series | np.ndarray) -> tuple[int, float, float, float]:
    x = pd.to_numeric(pd.Series(pnl), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    n = int(len(x))
    if n == 0:
        return 0, 0.0, math.nan, math.nan
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    return n, float(x.sum()), pf, float((x > 0).mean())


def metric(prefix: str, pnl: pd.Series | np.ndarray) -> dict[str, Any]:
    n, s, pf, wr = pf_sum_wr(pnl)
    return {f'{prefix}_n': n, f'{prefix}_sum': s, f'{prefix}_pf': pf, f'{prefix}_wr': wr, f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan}


def split_trades(tr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if tr.empty:
        return tr.copy(), tr.copy(), tr.copy()
    dt = pd.to_datetime(tr['entry_dt'])
    train = tr[(dt >= pd.Timestamp('2025-01-02')) & (dt < pd.Timestamp('2026-01-01'))].copy()
    test = tr[dt >= pd.Timestamp('2026-01-01')].copy()
    full = tr[dt >= pd.Timestamp('2025-01-02')].copy()
    return train, test, full


def recent3m(tr: pd.DataFrame) -> pd.DataFrame:
    if tr.empty:
        return tr.copy()
    months = sorted(tr['month'].astype(str).unique())
    keep = set(months[-3:])
    return tr[tr['month'].astype(str).isin(keep)].copy()


def monthly_table(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    for month, g in trades.groupby('month', sort=True):
        n, s, pf, wr = pf_sum_wr(g['pnl_net'])
        rows.append({
            'month': month,
            'trades': n,
            'wins': int((g['pnl_net'] > 0).sum()),
            'losses': int((g['pnl_net'] < 0).sum()),
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'pf': pf,
            'pnl_sum': s,
            'avg_pnl': s / n if n else math.nan,
            'tp_hits': int((g['hit_type'] == 'TP').sum()),
            'sl_hits': int((g['hit_type'] == 'SL').sum()),
            'horizon_exits': int((g['hit_type'] == 'HORIZON').sum()),
        })
    return pd.DataFrame(rows)


def evaluate_candidate(data: pd.DataFrame, m5: pd.DataFrame, candidate: dict[str, Any], cost_points: float) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    mask, problems = s179.literal_rule_mask(candidate['rule'], data)
    summary: dict[str, Any] = {
        'candidate_id': candidate['candidate_id'],
        'role': candidate['role'],
        'priority_acb': int(candidate['priority_acb']),
        'priority_cab': int(candidate['priority_cab']),
        'description': candidate['description'],
        'direction': candidate['direction'],
        'tp': float(candidate['tp']),
        'sl': float(candidate['sl']),
        'horizon_m5': int(candidate['horizon_m5']),
        'rule': candidate['rule'],
        'cost_points': float(cost_points),
        'rule_eval_problem_count': len(problems),
    }
    if problems:
        summary.update({'status': 'PARSE_PROBLEM', 'dedup_n': 0, 'problems': problems})
        return summary, pd.DataFrame(), pd.DataFrame()
    entries = data.loc[mask].copy()
    summary['entry_rows_before_dedup'] = int(len(entries))
    if entries.empty:
        summary.update({'status': 'EMPTY', 'dedup_n': 0})
        return summary, entries, pd.DataFrame()
    raw = s178.compute_outcome_with_exit(entries, m5, candidate['direction'], float(candidate['tp']), float(candidate['sl']), int(candidate['horizon_m5']))
    dedup = s178.dedup_resolved_only(raw)
    if dedup.empty:
        summary.update({'status': 'NO_DEDUP_TRADES', 'dedup_n': 0})
        return summary, entries, dedup
    dedup = dedup.copy()
    dedup['candidate_id'] = candidate['candidate_id']
    dedup['role'] = candidate['role']
    dedup['priority_acb'] = int(candidate['priority_acb'])
    dedup['priority_cab'] = int(candidate['priority_cab'])
    dedup['direction'] = candidate['direction']
    dedup['tp'] = float(candidate['tp'])
    dedup['sl'] = float(candidate['sl'])
    dedup['horizon_m5'] = int(candidate['horizon_m5'])
    dedup['rule'] = candidate['rule']
    dedup['pnl_net'] = pd.to_numeric(dedup['pnl_raw'], errors='coerce') - float(cost_points)
    dedup['month'] = pd.to_datetime(dedup['entry_dt']).dt.to_period('M').astype(str)
    train, test, full = split_trades(dedup)
    summary['dedup_n'] = int(len(dedup))
    summary.update(metric('train', train['pnl_net'] if not train.empty else np.array([])))
    summary.update(metric('test', test['pnl_net'] if not test.empty else np.array([])))
    summary.update(metric('full', full['pnl_net'] if not full.empty else np.array([])))
    summary.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])))
    m = full.groupby('month')['pnl_net'].sum().sort_index() if not full.empty else pd.Series(dtype=float)
    summary['full_months'] = int(len(m))
    summary['full_neg_months'] = int((m < 0).sum()) if len(m) else 0
    summary['worst_month'] = str(m.idxmin()) if len(m) else ''
    summary['worst_month_sum'] = float(m.min()) if len(m) else math.nan
    summary['tp_hits'] = int((dedup['hit_type'] == 'TP').sum())
    summary['sl_hits'] = int((dedup['hit_type'] == 'SL').sum())
    summary['horizon_exits'] = int((dedup['hit_type'] == 'HORIZON').sum())
    summary['beats_old_pf_2_237'] = bool(
        summary.get('train_n', 0) >= 50 and summary.get('test_n', 0) >= 15 and summary.get('full_n', 0) >= 100 and
        summary.get('train_pf', 0) > BENCHMARK_PF and summary.get('test_pf', 0) > BENCHMARK_PF and summary.get('full_pf', 0) > BENCHMARK_PF and
        summary.get('recent3m_pf', 0) > BENCHMARK_PF and summary.get('full_neg_months', 99) == 0
    )
    summary['status'] = 'OK'
    return summary, entries, dedup


def overlap_summary(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if trades.empty:
        return pd.DataFrame(), pd.DataFrame()
    t = trades.copy()
    t['entry_dt_str'] = pd.to_datetime(t['entry_dt']).astype(str)
    grouped = t.groupby('entry_dt_str').agg(
        candidate_count=('candidate_id', 'nunique'),
        candidates=('candidate_id', lambda x: '|'.join(sorted(set(map(str, x))))),
        first_month=('month', 'first'),
    ).reset_index()
    overlaps = grouped[grouped['candidate_count'] >= 2].copy()
    dist = grouped.groupby(['candidate_count', 'candidates']).size().reset_index(name='rows').sort_values(['candidate_count', 'rows'], ascending=[False, False])
    return overlaps, dist


def priority_unique_portfolio(trades: pd.DataFrame, priority_col: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    t['entry_dt_str'] = pd.to_datetime(t['entry_dt']).astype(str)
    t = t.sort_values(['entry_dt_str', priority_col, 'candidate_id'])
    out = t.groupby('entry_dt_str', as_index=False).head(1).copy()
    out['priority_scenario_col'] = priority_col
    return out


def portfolio_summary(name: str, trades: pd.DataFrame) -> dict[str, Any]:
    train, test, full = split_trades(trades) if not trades.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    out: dict[str, Any] = {'portfolio_scenario': name, 'trades': int(len(trades)) if not trades.empty else 0}
    out.update(metric('train', train['pnl_net'] if not train.empty else np.array([])))
    out.update(metric('test', test['pnl_net'] if not test.empty else np.array([])))
    out.update(metric('full', full['pnl_net'] if not full.empty else np.array([])))
    out.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])))
    m = full.groupby('month')['pnl_net'].sum().sort_index() if not full.empty else pd.Series(dtype=float)
    out['full_neg_months'] = int((m < 0).sum()) if len(m) else 0
    out['worst_month'] = str(m.idxmin()) if len(m) else ''
    out['worst_month_sum'] = float(m.min()) if len(m) else math.nan
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '187'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}
    source_diag_rows: list[dict[str, Any]] = []
    progress('load OHLC with Stage177 gold_2025/live contract')
    for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
        frames[tf], diag = s177.combine(tf, data_dir)
        source_diag_rows.extend(diag)
        if frames[tf].empty:
            blockers.append({'id': 'missing_combined_ohlc', 'tf': tf})
    source_diag = pd.DataFrame(source_diag_rows)
    if not source_diag.empty:
        save(source_diag, out / 'gold_v3_187_source_coverage.csv')

    cand_summary = pd.DataFrame()
    trades_all = pd.DataFrame()
    monthly_all = pd.DataFrame()
    overlaps = pd.DataFrame()
    overlap_dist = pd.DataFrame()
    portfolio_summaries = pd.DataFrame()
    portfolio_monthly_rows: list[pd.DataFrame] = []

    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        summaries = []
        trade_rows = []
        monthly_rows = []
        for c in PRIMARY_CANDIDATES:
            progress(f"evaluate {c['candidate_id']}")
            s, _entries, dedup = evaluate_candidate(data, frames['m5'], c, float(args.cost_points))
            summaries.append(s)
            if s.get('status') != 'OK':
                blockers.append({'id': 'candidate_not_ok', 'candidate_id': c['candidate_id'], 'status': s.get('status'), 'problems': s.get('problems', [])})
            if not dedup.empty:
                trade_rows.append(dedup)
                mt = monthly_table(dedup)
                if not mt.empty:
                    mt.insert(0, 'candidate_id', c['candidate_id'])
                    monthly_rows.append(mt)
        cand_summary = pd.DataFrame(summaries)
        trades_all = pd.concat(trade_rows, ignore_index=True) if trade_rows else pd.DataFrame()
        monthly_all = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()
        overlaps, overlap_dist = overlap_summary(trades_all)
        p_summaries = []
        for scenario_name, priority_col in PRIORITY_SCENARIOS.items():
            p_trades = priority_unique_portfolio(trades_all, priority_col)
            save(p_trades, out / f'gold_v3_187_{scenario_name.lower()}_trades.csv')
            p_monthly = monthly_table(p_trades)
            if not p_monthly.empty:
                p_monthly.insert(0, 'portfolio_scenario', scenario_name)
                portfolio_monthly_rows.append(p_monthly)
                save(p_monthly, out / f'gold_v3_187_{scenario_name.lower()}_monthly.csv')
            p_summaries.append(portfolio_summary(scenario_name, p_trades))
        portfolio_summaries = pd.DataFrame(p_summaries)

        save(pd.DataFrame(PRIMARY_CANDIDATES), out / 'gold_v3_187_primary_abc_cap_candidates.csv')
        (out / 'gold_v3_187_primary_abc_cap_candidates.json').write_text(json.dumps({'audit_only': True, 'primary_candidates': PRIMARY_CANDIDATES}, ensure_ascii=False, indent=2), encoding='utf-8')
        save(cand_summary, out / 'gold_v3_187_candidate_summary.csv')
        save(trades_all, out / 'gold_v3_187_trades_by_candidate.csv')
        save(monthly_all, out / 'gold_v3_187_monthly_by_candidate.csv')
        save(overlaps, out / 'gold_v3_187_overlap_entry_timestamps.csv')
        save(overlap_dist, out / 'gold_v3_187_overlap_distribution.csv')
        save(portfolio_summaries, out / 'gold_v3_187_priority_portfolio_summary.csv')
        if portfolio_monthly_rows:
            save(pd.concat(portfolio_monthly_rows, ignore_index=True), out / 'gold_v3_187_priority_portfolio_monthly_all.csv')

    ready = len(blockers) == 0
    best_portfolio = {}
    if not portfolio_summaries.empty:
        best_portfolio = portfolio_summaries.sort_values(['full_pf', 'test_pf', 'recent3m_pf', 'trades'], ascending=[False, False, False, False]).iloc[0].to_dict()
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE187_PRIMARY_ABC_CAP_PORTFOLIO_REFREEZE_READY_AUDIT_ONLY' if ready else 'STAGE187_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'primary_candidate_count': len(PRIMARY_CANDIDATES),
        'primary_candidate_ids': [c['candidate_id'] for c in PRIMARY_CANDIDATES],
        'cost_points': float(args.cost_points),
        'all_candidates_primary': True,
        'b_current_variant': 'B_HIGH_FREQUENCY_CAP40',
        'c_current_variant': 'C_BALANCED_CAP60',
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'candidate_summary_rows': int(len(cand_summary)) if not cand_summary.empty else 0,
        'candidate_trade_rows_total': int(len(trades_all)) if not trades_all.empty else 0,
        'unique_entry_timestamps': int(trades_all['entry_dt'].nunique()) if not trades_all.empty else 0,
        'overlap_entry_timestamps': int(len(overlaps)) if not overlaps.empty else 0,
        'best_priority_scenario': str(best_portfolio.get('portfolio_scenario', '')),
        'best_priority_trades': int(best_portfolio.get('trades', 0)) if best_portfolio else 0,
        'best_priority_full_pf': float(best_portfolio.get('full_pf', math.nan)) if best_portfolio else math.nan,
        'best_priority_test_pf': float(best_portfolio.get('test_pf', math.nan)) if best_portfolio else math.nan,
        'best_priority_recent3m_pf': float(best_portfolio.get('recent3m_pf', math.nan)) if best_portfolio else math.nan,
        'best_priority_full_wr_pct': float(best_portfolio.get('full_wr_pct', math.nan)) if best_portfolio else math.nan,
        'best_priority_full_neg_months': int(best_portfolio.get('full_neg_months', 0)) if best_portfolio else 0,
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
    (out / 'gold_v3_187_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_187_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    cand_cols = ['candidate_id', 'role', 'priority_acb', 'priority_cab', 'direction', 'tp', 'sl', 'horizon_m5', 'entry_rows_before_dedup', 'dedup_n', 'train_n', 'train_pf', 'test_n', 'test_pf', 'full_n', 'full_pf', 'full_wr_pct', 'recent3m_n', 'recent3m_pf', 'full_neg_months', 'worst_month', 'worst_month_sum', 'tp_hits', 'sl_hits', 'horizon_exits', 'beats_old_pf_2_237', 'rule']
    cand_show = cand_summary[[c for c in cand_cols if c in cand_summary.columns]].sort_values('priority_acb') if not cand_summary.empty else pd.DataFrame()
    monthly_show = monthly_all.sort_values(['candidate_id', 'month']) if not monthly_all.empty else pd.DataFrame()

    portfolio_monthly_all = pd.concat(portfolio_monthly_rows, ignore_index=True) if portfolio_monthly_rows else pd.DataFrame()

    lines = ['GOLD V3 187 PASTE_ME_PRIMARY_ABC_CAP_PORTFOLIO_REFREEZE_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PRIMARY_CANDIDATES', pd.DataFrame(PRIMARY_CANDIDATES).to_string(index=False)]
    lines += ['', 'CANDIDATE_SUMMARY', show(cand_show, 20)]
    lines += ['', 'MONTHLY_BY_CANDIDATE', show(monthly_show, 80)]
    lines += ['', 'OVERLAP_DISTRIBUTION', show(overlap_dist, 30)]
    lines += ['', 'OVERLAP_ENTRY_TIMESTAMPS_SAMPLE', show(overlaps, 80)]
    lines += ['', 'PRIORITY_PORTFOLIO_SUMMARY', show(portfolio_summaries, 20)]
    lines += ['', 'PRIORITY_PORTFOLIO_MONTHLY', show(portfolio_monthly_all, 80)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage187 is audit-only. It refreezes A, B, and C as PRIMARY candidates with B using Stage186 h1_atr14<=40 and C using Stage184 h1_atr14<=60. This does not enable live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade.',
        'Two priority audit views are included: A>C>B and C>A>B. These are duplicate timestamp review views only and are not live execution approval.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
