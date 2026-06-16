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
import gold_v3_180_selected_candidate_stability_audit as s180

STEP = 'GOLD_V3_182_CANDIDATE_PORTFOLIO_MONTHLY_COMPARE_AUDIT_ONLY'
BENCHMARK_PF = 2.237
DEFAULT_COST_POINTS = 3.0

CANDIDATES = [
    {
        'candidate_id': 'A_PRECISION_BASE',
        'description': 'Stage179 precision candidate: strongest PF, lower frequency.',
        'rule': 'd1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347',
        'direction': 'LONG',
        'tp': 40.0,
        'sl': 20.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'B_HIGH_FREQUENCY',
        'description': 'Stage181 selected high-frequency candidate: most trades while A-tier stable.',
        'rule': 'd1_dist_close_atr28<=-0.394892',
        'direction': 'LONG',
        'tp': 50.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'C_BALANCED',
        'description': 'Stage181 balance candidate: higher frequency than base with stronger PF than max-frequency.',
        'rule': 'd1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008',
        'direction': 'LONG',
        'tp': 30.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
]


def progress(msg: str) -> None:
    print(f'[182 progress] {msg}', flush=True)


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


def metric(prefix: str, pnl: pd.Series | np.ndarray) -> dict[str, Any]:
    n, s, pf, wr = pf_sum_wr(pnl)
    return {f'{prefix}_n': n, f'{prefix}_sum': s, f'{prefix}_pf': pf, f'{prefix}_wr': wr, f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan}


def monthly_for_candidate(trades: pd.DataFrame, candidate: dict[str, Any], cost_points: float) -> pd.DataFrame:
    monthly = s179.monthly_table(trades, cost_points)
    if monthly.empty:
        return monthly
    monthly.insert(0, 'candidate_id', candidate['candidate_id'])
    monthly.insert(1, 'direction', candidate['direction'])
    monthly.insert(2, 'tp', float(candidate['tp']))
    monthly.insert(3, 'sl', float(candidate['sl']))
    monthly.insert(4, 'horizon_m5', int(candidate['horizon_m5']))
    monthly.insert(5, 'rule', candidate['rule'])
    return monthly


def yearly_for_candidate(monthly: pd.DataFrame, candidate: dict[str, Any]) -> pd.DataFrame:
    y = s179.yearly_table(monthly.drop(columns=['candidate_id', 'direction', 'tp', 'sl', 'horizon_m5', 'rule'], errors='ignore')) if not monthly.empty else pd.DataFrame()
    if y.empty:
        return y
    y.insert(0, 'candidate_id', candidate['candidate_id'])
    return y


def eval_candidate(data: pd.DataFrame, m5: pd.DataFrame, candidate: dict[str, Any], cost_points: float) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    mask, problems = s179.literal_rule_mask(candidate['rule'], data)
    entries = data.loc[mask].copy()
    summary: dict[str, Any] = {
        'candidate_id': candidate['candidate_id'],
        'description': candidate['description'],
        'direction': candidate['direction'],
        'tp': float(candidate['tp']),
        'sl': float(candidate['sl']),
        'horizon_m5': int(candidate['horizon_m5']),
        'rule': candidate['rule'],
        'cost_points': float(cost_points),
        'parse_problem_count': len(problems),
        'entry_rows_before_dedup': int(len(entries)),
    }
    if problems or entries.empty:
        summary.update({'status': 'PARSE_PROBLEM' if problems else 'EMPTY', 'dedup_n': 0})
        return pd.DataFrame(), pd.DataFrame(), summary, problems

    raw = s178.compute_outcome_with_exit(entries, m5, candidate['direction'], float(candidate['tp']), float(candidate['sl']), int(candidate['horizon_m5']))
    dedup = s178.dedup_resolved_only(raw)
    if dedup.empty:
        summary.update({'status': 'NO_DEDUP_TRADES', 'dedup_n': 0})
        return raw, dedup, summary, problems

    dedup = dedup.copy()
    dedup['candidate_id'] = candidate['candidate_id']
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
        summary.get('train_pf', 0) > BENCHMARK_PF and summary.get('test_pf', 0) > BENCHMARK_PF and summary.get('full_pf', 0) > BENCHMARK_PF
    )
    summary['status'] = 'OK'
    return raw, dedup, summary, problems


def monthly_pivot(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame()
    keep_cols = ['month', 'candidate_id', 'trades', 'win_rate_pct', 'pf', 'pnl_sum']
    x = monthly[keep_cols].copy()
    parts = []
    for field in ['trades', 'win_rate_pct', 'pf', 'pnl_sum']:
        p = x.pivot(index='month', columns='candidate_id', values=field).reset_index()
        p.columns = ['month'] + [f'{c}_{field}' for c in p.columns[1:]]
        parts.append(p)
    out = parts[0]
    for p in parts[1:]:
        out = out.merge(p, on='month', how='outer')
    return out.sort_values('month').reset_index(drop=True)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '182'
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
        save(source_diag, out / 'gold_v3_182_source_coverage.csv')

    candidate_summary = pd.DataFrame()
    monthly_all = pd.DataFrame()
    yearly_all = pd.DataFrame()
    trades_all = pd.DataFrame()
    pivot = pd.DataFrame()

    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        summary_rows: list[dict[str, Any]] = []
        monthly_rows: list[pd.DataFrame] = []
        yearly_rows: list[pd.DataFrame] = []
        trades_rows: list[pd.DataFrame] = []
        for c in CANDIDATES:
            progress(f"evaluate {c['candidate_id']}")
            _raw, dedup, summary, problems = eval_candidate(data, frames['m5'], c, float(args.cost_points))
            if problems:
                blockers.append({'id': 'candidate_rule_parse_problem', 'candidate_id': c['candidate_id'], 'problems': problems})
            summary_rows.append(summary)
            if not dedup.empty:
                trades_rows.append(dedup)
                m = monthly_for_candidate(dedup, c, float(args.cost_points))
                y = yearly_for_candidate(m, c)
                monthly_rows.append(m)
                yearly_rows.append(y)
        candidate_summary = pd.DataFrame(summary_rows)
        monthly_all = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()
        yearly_all = pd.concat(yearly_rows, ignore_index=True) if yearly_rows else pd.DataFrame()
        trades_all = pd.concat(trades_rows, ignore_index=True) if trades_rows else pd.DataFrame()
        pivot = monthly_pivot(monthly_all)

        save(candidate_summary, out / 'gold_v3_182_candidate_summary.csv')
        save(monthly_all, out / 'gold_v3_182_monthly_by_candidate.csv')
        save(yearly_all, out / 'gold_v3_182_yearly_by_candidate.csv')
        save(trades_all, out / 'gold_v3_182_dedup_trades_by_candidate.csv')
        save(pivot, out / 'gold_v3_182_monthly_pivot.csv')

    ready = len(blockers) == 0
    best_by_full_n = candidate_summary.sort_values(['full_n', 'test_pf', 'recent3m_pf'], ascending=[False, False, False]).head(1) if not candidate_summary.empty and 'full_n' in candidate_summary.columns else pd.DataFrame()
    best_by_pf = candidate_summary.sort_values(['full_pf', 'test_pf', 'full_n'], ascending=[False, False, False]).head(1) if not candidate_summary.empty and 'full_pf' in candidate_summary.columns else pd.DataFrame()

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE182_CANDIDATE_PORTFOLIO_MONTHLY_COMPARE_READY_AUDIT_ONLY' if ready else 'STAGE182_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'old_pf_benchmark': BENCHMARK_PF,
        'cost_points': float(args.cost_points),
        'candidate_count': len(CANDIDATES),
        'monthly_rows': int(len(monthly_all)) if not monthly_all.empty else 0,
        'pivot_rows': int(len(pivot)) if not pivot.empty else 0,
        'best_frequency_candidate': str(best_by_full_n.iloc[0]['candidate_id']) if not best_by_full_n.empty else '',
        'best_frequency_full_n': int(best_by_full_n.iloc[0]['full_n']) if not best_by_full_n.empty else 0,
        'best_frequency_test_pf': float(best_by_full_n.iloc[0]['test_pf']) if not best_by_full_n.empty else math.nan,
        'best_pf_candidate': str(best_by_pf.iloc[0]['candidate_id']) if not best_by_pf.empty else '',
        'best_pf_full_pf': float(best_by_pf.iloc[0]['full_pf']) if not best_by_pf.empty else math.nan,
        'best_pf_full_n': int(best_by_pf.iloc[0]['full_n']) if not best_by_pf.empty else 0,
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
    (out / 'gold_v3_182_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_182_decision.csv')

    def show(df: pd.DataFrame, n: int = 60) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    candidate_cols = [
        'candidate_id', 'description', 'direction', 'tp', 'sl', 'horizon_m5', 'entry_rows_before_dedup', 'dedup_n',
        'train_n', 'train_pf', 'train_wr_pct', 'test_n', 'test_pf', 'test_wr_pct', 'full_n', 'full_pf', 'full_wr_pct',
        'recent3m_n', 'recent3m_pf', 'recent3m_wr_pct', 'full_neg_months', 'worst_month', 'worst_month_sum',
        'tp_hits', 'sl_hits', 'horizon_exits', 'beats_old_pf_2_237', 'rule'
    ]
    cand_show = candidate_summary[[c for c in candidate_cols if c in candidate_summary.columns]].sort_values(['full_n'], ascending=False) if not candidate_summary.empty else pd.DataFrame()
    monthly_cols = ['candidate_id', 'month', 'trades', 'wins', 'losses', 'win_rate_pct', 'pf', 'pnl_sum', 'avg_pnl', 'tp_hits', 'sl_hits', 'horizon_exits']
    mon_show = monthly_all[[c for c in monthly_cols if c in monthly_all.columns]].sort_values(['candidate_id', 'month']) if not monthly_all.empty else pd.DataFrame()

    lines = ['GOLD V3 182 PASTE_ME_CANDIDATE_PORTFOLIO_MONTHLY_COMPARE_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'CANDIDATE_SUMMARY', show(cand_show, 20)]
    lines += ['', 'YEARLY_BY_CANDIDATE', show(yearly_all, 20)]
    lines += ['', 'MONTHLY_BY_CANDIDATE', show(mon_show, 80)]
    lines += ['', 'MONTHLY_PIVOT_QUICK_VIEW', show(pivot, 30)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage182 is audit-only. It compares three fixed candidate variants: precision base, high-frequency, and balanced. Metrics are computed after dedup_resolved_only and cost_points subtraction. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
        'Use this table to decide whether to keep one candidate, run a portfolio gate, or continue searching. Passing Stage182 is not live approval.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
