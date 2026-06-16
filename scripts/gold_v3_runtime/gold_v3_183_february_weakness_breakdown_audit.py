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
import gold_v3_182_candidate_portfolio_monthly_compare_audit as s182

STEP = 'GOLD_V3_183_FEBRUARY_WEAKNESS_BREAKDOWN_AUDIT_ONLY'
DEFAULT_COST_POINTS = 3.0
FOCUS_MONTH = '2026-02'
COMPARE_MONTHS = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06']

FEATURE_COLS = [
    'd1_dist_close_atr28', 'd1_dist_close_atr14', 'd1_atr14', 'd1_atr28',
    'h4_body_atr14', 'h4_range_atr14', 'h4_atr14',
    'h1_atr14', 'h1_range_atr', 'h1_body_atr14',
    'm15_rsi14', 'm15_atr14', 'm15_range_atr14', 'm15_body_atr14',
]


def progress(msg: str) -> None:
    print(f'[183 progress] {msg}', flush=True)


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


def group_metrics(df: pd.DataFrame, group_cols: list[str], pnl_col: str = 'pnl_net') -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        n, s, pf, wr = pf_sum_wr(g[pnl_col])
        row = {col: key for col, key in zip(group_cols, keys)}
        row.update({
            'trades': n,
            'wins': int((pd.to_numeric(g[pnl_col], errors='coerce') > 0).sum()),
            'losses': int((pd.to_numeric(g[pnl_col], errors='coerce') < 0).sum()),
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'pf': pf,
            'pnl_sum': s,
            'avg_pnl': s / n if n else math.nan,
            'tp_hits': int((g.get('hit_type', pd.Series(dtype=object)) == 'TP').sum()) if 'hit_type' in g.columns else 0,
            'sl_hits': int((g.get('hit_type', pd.Series(dtype=object)) == 'SL').sum()) if 'hit_type' in g.columns else 0,
            'horizon_exits': int((g.get('hit_type', pd.Series(dtype=object)) == 'HORIZON').sum()) if 'hit_type' in g.columns else 0,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def eval_candidate(data: pd.DataFrame, m5: pd.DataFrame, candidate: dict[str, Any], cost_points: float) -> pd.DataFrame:
    mask, problems = s179.literal_rule_mask(candidate['rule'], data)
    if problems:
        raise RuntimeError(f"rule parse problems for {candidate['candidate_id']}: {problems}")
    entries = data.loc[mask].copy()
    if entries.empty:
        return pd.DataFrame()
    raw = s178.compute_outcome_with_exit(entries, m5, candidate['direction'], float(candidate['tp']), float(candidate['sl']), int(candidate['horizon_m5']))
    dedup = s178.dedup_resolved_only(raw)
    if dedup.empty:
        return dedup
    dedup = dedup.copy()
    dedup['candidate_id'] = candidate['candidate_id']
    dedup['direction'] = candidate['direction']
    dedup['tp'] = float(candidate['tp'])
    dedup['sl'] = float(candidate['sl'])
    dedup['horizon_m5'] = int(candidate['horizon_m5'])
    dedup['rule'] = candidate['rule']
    dedup['pnl_net'] = pd.to_numeric(dedup['pnl_raw'], errors='coerce') - float(cost_points)
    entry_dt = pd.to_datetime(dedup['entry_dt'])
    dedup['month'] = entry_dt.dt.to_period('M').astype(str)
    dedup['date'] = entry_dt.dt.date.astype(str)
    dedup['week'] = entry_dt.dt.to_period('W-MON').astype(str)
    dedup['hour'] = entry_dt.dt.hour.astype(int)
    dedup['dow'] = entry_dt.dt.day_name()
    dedup['is_focus_month'] = dedup['month'].eq(FOCUS_MONTH)
    return dedup


def feature_win_loss(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    for candidate_id, g0 in trades.groupby('candidate_id', sort=True):
        focus = g0[g0['month'].eq(FOCUS_MONTH)].copy()
        if focus.empty:
            continue
        for col in FEATURE_COLS:
            if col not in focus.columns:
                continue
            x = pd.to_numeric(focus[col], errors='coerce')
            wins = focus[pd.to_numeric(focus['pnl_net'], errors='coerce') > 0]
            losses = focus[pd.to_numeric(focus['pnl_net'], errors='coerce') < 0]
            rows.append({
                'candidate_id': candidate_id,
                'feature': col,
                'all_mean': float(x.mean()) if len(x.dropna()) else math.nan,
                'all_median': float(x.median()) if len(x.dropna()) else math.nan,
                'win_mean': float(pd.to_numeric(wins[col], errors='coerce').mean()) if not wins.empty else math.nan,
                'loss_mean': float(pd.to_numeric(losses[col], errors='coerce').mean()) if not losses.empty else math.nan,
                'loss_minus_win_mean': float(pd.to_numeric(losses[col], errors='coerce').mean() - pd.to_numeric(wins[col], errors='coerce').mean()) if (not wins.empty and not losses.empty) else math.nan,
                'win_n': int(len(wins)),
                'loss_n': int(len(losses)),
            })
    return pd.DataFrame(rows)


def add_rank_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if 'pnl_sum' in out.columns:
        out = out.sort_values(['candidate_id', 'pnl_sum'], ascending=[True, True])
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '183'
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
        save(source_diag, out / 'gold_v3_183_source_coverage.csv')

    trades_all = pd.DataFrame()
    focus_month = pd.DataFrame()
    compare_months = pd.DataFrame()
    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        rows = []
        for c in s182.CANDIDATES:
            progress(f"evaluate {c['candidate_id']}")
            rows.append(eval_candidate(data, frames['m5'], c, float(args.cost_points)))
        trades_all = pd.concat([x for x in rows if not x.empty], ignore_index=True) if rows else pd.DataFrame()
        if trades_all.empty:
            blockers.append({'id': 'no_trades_replayed'})
        else:
            focus_month = trades_all[trades_all['month'].eq(FOCUS_MONTH)].copy()
            compare_months = trades_all[trades_all['month'].isin(COMPARE_MONTHS)].copy()
            save(trades_all, out / 'gold_v3_183_replayed_trades_all.csv')
            save(focus_month, out / 'gold_v3_183_focus_month_trades.csv')
            save(compare_months, out / 'gold_v3_183_2026_months_trades.csv')

    ready = len(blockers) == 0
    focus_summary = group_metrics(focus_month, ['candidate_id', 'month']) if ready else pd.DataFrame()
    compare_summary = group_metrics(compare_months, ['candidate_id', 'month']) if ready else pd.DataFrame()
    day_summary = add_rank_cols(group_metrics(focus_month, ['candidate_id', 'date'])) if ready else pd.DataFrame()
    week_summary = add_rank_cols(group_metrics(focus_month, ['candidate_id', 'week'])) if ready else pd.DataFrame()
    hour_summary = add_rank_cols(group_metrics(focus_month, ['candidate_id', 'hour'])) if ready else pd.DataFrame()
    dow_summary = add_rank_cols(group_metrics(focus_month, ['candidate_id', 'dow'])) if ready else pd.DataFrame()
    feature_summary = feature_win_loss(trades_all) if ready else pd.DataFrame()

    if ready:
        save(focus_summary, out / 'gold_v3_183_focus_month_summary.csv')
        save(compare_summary, out / 'gold_v3_183_2026_month_compare_summary.csv')
        save(day_summary, out / 'gold_v3_183_focus_month_by_day.csv')
        save(week_summary, out / 'gold_v3_183_focus_month_by_week.csv')
        save(hour_summary, out / 'gold_v3_183_focus_month_by_hour.csv')
        save(dow_summary, out / 'gold_v3_183_focus_month_by_dow.csv')
        save(feature_summary, out / 'gold_v3_183_focus_month_feature_win_loss.csv')

    def min_pf_for_candidate(cid: str) -> float:
        if compare_summary.empty:
            return math.nan
        x = compare_summary[compare_summary['candidate_id'].eq(cid)]
        return float(pd.to_numeric(x['pf'], errors='coerce').replace([np.inf, -np.inf], np.nan).min()) if not x.empty else math.nan

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE183_FEBRUARY_WEAKNESS_BREAKDOWN_READY_AUDIT_ONLY' if ready else 'STAGE183_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'focus_month': FOCUS_MONTH,
        'compare_months': COMPARE_MONTHS,
        'cost_points': float(args.cost_points),
        'candidate_count': len(s182.CANDIDATES),
        'focus_month_trade_rows': int(len(focus_month)) if not focus_month.empty else 0,
        'A_focus_pf': float(focus_summary.loc[focus_summary['candidate_id'].eq('A_PRECISION_BASE'), 'pf'].iloc[0]) if ready and not focus_summary[focus_summary['candidate_id'].eq('A_PRECISION_BASE')].empty else math.nan,
        'B_focus_pf': float(focus_summary.loc[focus_summary['candidate_id'].eq('B_HIGH_FREQUENCY'), 'pf'].iloc[0]) if ready and not focus_summary[focus_summary['candidate_id'].eq('B_HIGH_FREQUENCY')].empty else math.nan,
        'C_focus_pf': float(focus_summary.loc[focus_summary['candidate_id'].eq('C_BALANCED'), 'pf'].iloc[0]) if ready and not focus_summary[focus_summary['candidate_id'].eq('C_BALANCED')].empty else math.nan,
        'A_min_pf_2026_01_06': min_pf_for_candidate('A_PRECISION_BASE'),
        'B_min_pf_2026_01_06': min_pf_for_candidate('B_HIGH_FREQUENCY'),
        'C_min_pf_2026_01_06': min_pf_for_candidate('C_BALANCED'),
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
    (out / 'gold_v3_183_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_183_decision.csv')

    def show(df: pd.DataFrame, n: int = 60) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    trade_cols = ['candidate_id', 'entry_dt', 'exit_dt', 'direction', 'tp', 'sl', 'hit_type', 'pnl_raw', 'pnl_net', 'date', 'hour', 'dow']
    feature_keep = [c for c in FEATURE_COLS if c in focus_month.columns]
    focus_detail = focus_month[[c for c in trade_cols + feature_keep if c in focus_month.columns]].sort_values(['candidate_id', 'entry_dt']) if not focus_month.empty else pd.DataFrame()

    lines = ['GOLD V3 183 PASTE_ME_FEBRUARY_WEAKNESS_BREAKDOWN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'FOCUS_MONTH_SUMMARY', show(focus_summary, 20)]
    lines += ['', 'COMPARE_2026_MONTHS_SUMMARY', show(compare_summary, 40)]
    lines += ['', 'FOCUS_MONTH_BY_DAY_WORST_FIRST', show(day_summary, 80)]
    lines += ['', 'FOCUS_MONTH_BY_WEEK_WORST_FIRST', show(week_summary, 40)]
    lines += ['', 'FOCUS_MONTH_BY_HOUR_WORST_FIRST', show(hour_summary, 80)]
    lines += ['', 'FOCUS_MONTH_BY_DOW_WORST_FIRST', show(dow_summary, 40)]
    lines += ['', 'FOCUS_MONTH_FEATURE_WIN_LOSS', show(feature_summary.sort_values(['candidate_id', 'loss_minus_win_mean'], ascending=[True, True]) if not feature_summary.empty else feature_summary, 80)]
    lines += ['', 'FOCUS_MONTH_TRADE_DETAIL', show(focus_detail, 120)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage183 is audit-only. It investigates February 2026 weakness for the fixed ABC candidates. It uses entry-time OHLC-derived features for grouping and uses post-entry M5 outcomes only for audit scoring. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
        'This stage should be used to decide whether February weakness is broad market regime weakness, candidate-specific weakness, time/day concentration, or feature-threshold edge erosion. Do not use future outcomes as a live entry gate.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
