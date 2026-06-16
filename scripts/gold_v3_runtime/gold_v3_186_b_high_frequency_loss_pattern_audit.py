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

STEP = 'GOLD_V3_186_B_HIGH_FREQUENCY_LOSS_PATTERN_AUDIT_ONLY'
DEFAULT_COST_POINTS = 3.0
BENCHMARK_PF = 2.237
B_CANDIDATE = {
    'candidate_id': 'B_HIGH_FREQUENCY',
    'rule': 'd1_dist_close_atr28<=-0.394892',
    'direction': 'LONG',
    'tp': 50.0,
    'sl': 30.0,
    'horizon_m5': 192,
}
FEATURE_COLS = [
    'd1_dist_close_atr28', 'd1_dist_close_atr14', 'd1_atr14', 'd1_atr28',
    'h4_body_atr14', 'h4_range_atr14', 'h4_atr14',
    'h1_atr14', 'h1_range_atr', 'h1_body_atr14',
    'm15_rsi14', 'm15_atr14', 'm15_range_atr14', 'm15_body_atr14',
]
WEAK_MONTHS = ['2026-02', '2026-03', '2026-06']
CAPS = [None, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 120.0]


def progress(msg: str) -> None:
    print(f'[186 progress] {msg}', flush=True)


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


def group_metrics(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        n, s, pf, wr = pf_sum_wr(g['pnl_net'])
        row = {col: key for col, key in zip(group_cols, keys)}
        row.update({
            'trades': n,
            'wins': int((g['pnl_net'] > 0).sum()),
            'losses': int((g['pnl_net'] < 0).sum()),
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'pf': pf,
            'pnl_sum': s,
            'avg_pnl': s / n if n else math.nan,
            'tp_hits': int((g['hit_type'] == 'TP').sum()) if 'hit_type' in g.columns else 0,
            'sl_hits': int((g['hit_type'] == 'SL').sum()) if 'hit_type' in g.columns else 0,
            'horizon_exits': int((g['hit_type'] == 'HORIZON').sum()) if 'hit_type' in g.columns else 0,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def metric(prefix: str, pnl: pd.Series | np.ndarray) -> dict[str, Any]:
    n, s, pf, wr = pf_sum_wr(pnl)
    return {f'{prefix}_n': n, f'{prefix}_sum': s, f'{prefix}_pf': pf, f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan}


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


def replay_b(data: pd.DataFrame, m5: pd.DataFrame, cost_points: float, h1_cap: float | None = None, exclude_hours: set[int] | None = None) -> pd.DataFrame:
    mask, problems = s179.literal_rule_mask(B_CANDIDATE['rule'], data)
    if problems:
        raise RuntimeError(f'B rule parse problems: {problems}')
    if h1_cap is not None:
        mask = mask & (pd.to_numeric(data['h1_atr14'], errors='coerce') <= float(h1_cap))
    entries = data.loc[mask].copy()
    if entries.empty:
        return pd.DataFrame()
    if exclude_hours:
        h = pd.to_datetime(entries['dt']).dt.hour.astype(int)
        entries = entries.loc[~h.isin(exclude_hours)].copy()
        if entries.empty:
            return pd.DataFrame()
    raw = s178.compute_outcome_with_exit(entries, m5, B_CANDIDATE['direction'], float(B_CANDIDATE['tp']), float(B_CANDIDATE['sl']), int(B_CANDIDATE['horizon_m5']))
    dedup = s178.dedup_resolved_only(raw)
    if dedup.empty:
        return dedup
    dedup = dedup.copy()
    dedup['candidate_id'] = B_CANDIDATE['candidate_id']
    dedup['pnl_net'] = pd.to_numeric(dedup['pnl_raw'], errors='coerce') - float(cost_points)
    entry_dt = pd.to_datetime(dedup['entry_dt'])
    dedup['month'] = entry_dt.dt.to_period('M').astype(str)
    dedup['date'] = entry_dt.dt.date.astype(str)
    dedup['week'] = entry_dt.dt.to_period('W-MON').astype(str)
    dedup['hour'] = entry_dt.dt.hour.astype(int)
    dedup['dow'] = entry_dt.dt.day_name()
    return dedup


def feature_win_loss(trades: pd.DataFrame, subset_name: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    wins = trades[trades['pnl_net'] > 0]
    losses = trades[trades['pnl_net'] < 0]
    for col in FEATURE_COLS:
        if col not in trades.columns:
            continue
        rows.append({
            'subset': subset_name,
            'feature': col,
            'all_n': int(pd.to_numeric(trades[col], errors='coerce').notna().sum()),
            'all_mean': float(pd.to_numeric(trades[col], errors='coerce').mean()),
            'all_median': float(pd.to_numeric(trades[col], errors='coerce').median()),
            'win_n': int(len(wins)),
            'win_mean': float(pd.to_numeric(wins[col], errors='coerce').mean()) if not wins.empty else math.nan,
            'loss_n': int(len(losses)),
            'loss_mean': float(pd.to_numeric(losses[col], errors='coerce').mean()) if not losses.empty else math.nan,
            'loss_minus_win_mean': float(pd.to_numeric(losses[col], errors='coerce').mean() - pd.to_numeric(wins[col], errors='coerce').mean()) if (not wins.empty and not losses.empty) else math.nan,
        })
    return pd.DataFrame(rows)


def cap_sensitivity(data: pd.DataFrame, m5: pd.DataFrame, cost_points: float) -> pd.DataFrame:
    rows = []
    for cap in CAPS:
        tr = replay_b(data, m5, cost_points, h1_cap=cap)
        label = 'NO_CAP' if cap is None else f'h1_atr14_le_{cap:g}'
        row = {'variant': label, 'h1_atr14_cap': '' if cap is None else float(cap)}
        if tr.empty:
            row.update({'status': 'EMPTY'})
        else:
            train, test, full = split_trades(tr)
            row.update(metric('train', train['pnl_net'] if not train.empty else np.array([])))
            row.update(metric('test', test['pnl_net'] if not test.empty else np.array([])))
            row.update(metric('full', full['pnl_net'] if not full.empty else np.array([])))
            row.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])))
            weak = full[full['month'].isin(WEAK_MONTHS)].copy()
            row.update(metric('weak_months', weak['pnl_net'] if not weak.empty else np.array([])))
            m = full.groupby('month')['pnl_net'].sum() if not full.empty else pd.Series(dtype=float)
            row['full_neg_months'] = int((m < 0).sum()) if len(m) else 0
            row['worst_month'] = str(m.idxmin()) if len(m) else ''
            row['worst_month_sum'] = float(m.min()) if len(m) else math.nan
            row['dedup_n'] = int(len(tr))
            row['status'] = 'OK'
            row['passes_basic_review'] = bool(row.get('full_n', 0) >= 150 and row.get('test_n', 0) >= 50 and row.get('test_pf', 0) > BENCHMARK_PF and row.get('full_pf', 0) > BENCHMARK_PF and row.get('recent3m_pf', 0) > BENCHMARK_PF and row.get('full_neg_months', 99) == 0)
        rows.append(row)
    return pd.DataFrame(rows)


def hour_exclusion_sensitivity(trades: pd.DataFrame, data: pd.DataFrame, m5: pd.DataFrame, cost_points: float) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    by_hour = group_metrics(trades, ['hour']).sort_values(['pf', 'pnl_sum'], ascending=[True, True])
    bad_hours = [int(h) for h in by_hour[(by_hour['trades'] >= 5) & (by_hour['pf'] < BENCHMARK_PF)]['hour'].head(6).tolist()]
    rows = []
    scenarios: list[tuple[str, set[int]]] = [('NO_EXCLUDE', set())]
    for h in bad_hours:
        scenarios.append((f'exclude_hour_{h}', {h}))
    if bad_hours:
        scenarios.append(('exclude_all_bad_hours', set(bad_hours)))
    for label, ex in scenarios:
        tr = replay_b(data, m5, cost_points, exclude_hours=ex)
        row = {'variant': label, 'excluded_hours_mt5': ','.join(map(str, sorted(ex))) if ex else ''}
        if tr.empty:
            row.update({'status': 'EMPTY'})
        else:
            train, test, full = split_trades(tr)
            row.update(metric('train', train['pnl_net'] if not train.empty else np.array([])))
            row.update(metric('test', test['pnl_net'] if not test.empty else np.array([])))
            row.update(metric('full', full['pnl_net'] if not full.empty else np.array([])))
            row.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])))
            weak = full[full['month'].isin(WEAK_MONTHS)].copy()
            row.update(metric('weak_months', weak['pnl_net'] if not weak.empty else np.array([])))
            m = full.groupby('month')['pnl_net'].sum() if not full.empty else pd.Series(dtype=float)
            row['full_neg_months'] = int((m < 0).sum()) if len(m) else 0
            row['worst_month'] = str(m.idxmin()) if len(m) else ''
            row['worst_month_sum'] = float(m.min()) if len(m) else math.nan
            row['dedup_n'] = int(len(tr))
            row['status'] = 'OK'
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '186'
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
        save(source_diag, out / 'gold_v3_186_source_coverage.csv')

    trades = pd.DataFrame()
    monthly = pd.DataFrame()
    by_hour = pd.DataFrame()
    by_dow = pd.DataFrame()
    by_date_weak = pd.DataFrame()
    by_week_weak = pd.DataFrame()
    feature_all = pd.DataFrame()
    caps = pd.DataFrame()
    hour_ex = pd.DataFrame()

    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        progress('replay B')
        trades = replay_b(data, frames['m5'], float(args.cost_points))
        if trades.empty:
            blockers.append({'id': 'b_replay_empty'})
        else:
            weak_trades = trades[trades['month'].isin(WEAK_MONTHS)].copy()
            monthly = group_metrics(trades, ['month'])
            by_hour = group_metrics(trades, ['hour']).sort_values(['pf', 'pnl_sum'], ascending=[True, True])
            by_dow = group_metrics(trades, ['dow']).sort_values(['pf', 'pnl_sum'], ascending=[True, True])
            by_date_weak = group_metrics(weak_trades, ['month', 'date']).sort_values(['pnl_sum', 'pf'], ascending=[True, True])
            by_week_weak = group_metrics(weak_trades, ['month', 'week']).sort_values(['pnl_sum', 'pf'], ascending=[True, True])
            feature_all = pd.concat([
                feature_win_loss(trades, 'full'),
                feature_win_loss(weak_trades, 'weak_months_2026_02_03_06'),
                feature_win_loss(trades[trades['month'].eq('2026-02')].copy(), '2026_02'),
                feature_win_loss(trades[trades['month'].eq('2026-06')].copy(), '2026_06'),
            ], ignore_index=True)
            caps = cap_sensitivity(data, frames['m5'], float(args.cost_points))
            hour_ex = hour_exclusion_sensitivity(trades, data, frames['m5'], float(args.cost_points))
            save(trades, out / 'gold_v3_186_b_trades.csv')
            save(monthly, out / 'gold_v3_186_b_monthly.csv')
            save(by_hour, out / 'gold_v3_186_b_by_hour_mt5.csv')
            save(by_dow, out / 'gold_v3_186_b_by_dow.csv')
            save(by_date_weak, out / 'gold_v3_186_b_weak_months_by_date.csv')
            save(by_week_weak, out / 'gold_v3_186_b_weak_months_by_week.csv')
            save(feature_all, out / 'gold_v3_186_b_feature_win_loss.csv')
            save(caps, out / 'gold_v3_186_b_h1_atr_cap_sensitivity.csv')
            save(hour_ex, out / 'gold_v3_186_b_hour_exclusion_sensitivity.csv')

    ready = len(blockers) == 0
    train, test, full = split_trades(trades) if not trades.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE186_B_LOSS_PATTERN_REVIEW_READY_AUDIT_ONLY' if ready else 'STAGE186_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'candidate_id': B_CANDIDATE['candidate_id'],
        'rule': B_CANDIDATE['rule'],
        'cost_points': float(args.cost_points),
        'weak_months': WEAK_MONTHS,
        **metric('train', train['pnl_net'] if not train.empty else np.array([])),
        **metric('test', test['pnl_net'] if not test.empty else np.array([])),
        **metric('full', full['pnl_net'] if not full.empty else np.array([])),
        **metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])),
        'worst_month': str(monthly.sort_values('pnl_sum').iloc[0]['month']) if not monthly.empty else '',
        'worst_month_pf': float(monthly.sort_values('pnl_sum').iloc[0]['pf']) if not monthly.empty else math.nan,
        'worst_month_sum': float(monthly.sort_values('pnl_sum').iloc[0]['pnl_sum']) if not monthly.empty else math.nan,
        'worst_hour_mt5': int(by_hour.iloc[0]['hour']) if not by_hour.empty else -1,
        'worst_hour_pf': float(by_hour.iloc[0]['pf']) if not by_hour.empty else math.nan,
        'best_cap_variant_by_test_pf': str(caps.sort_values(['test_pf', 'full_n'], ascending=[False, False]).iloc[0]['variant']) if not caps.empty and 'test_pf' in caps.columns else '',
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
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
    (out / 'gold_v3_186_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_186_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 186 PASTE_ME_B_HIGH_FREQUENCY_LOSS_PATTERN_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'MONTHLY', show(monthly, 30)]
    lines += ['', 'BY_HOUR_MT5_WORST_FIRST', show(by_hour, 80)]
    lines += ['', 'BY_DOW_WORST_FIRST', show(by_dow, 30)]
    lines += ['', 'WEAK_MONTHS_BY_DATE_WORST_FIRST', show(by_date_weak, 80)]
    lines += ['', 'WEAK_MONTHS_BY_WEEK_WORST_FIRST', show(by_week_weak, 60)]
    lines += ['', 'FEATURE_WIN_LOSS', show(feature_all.sort_values(['subset', 'loss_minus_win_mean'], ascending=[True, True]) if not feature_all.empty else feature_all, 120)]
    lines += ['', 'H1_ATR_CAP_SENSITIVITY', show(caps.sort_values(['passes_basic_review', 'test_pf', 'full_n'], ascending=[False, False, False]) if not caps.empty else caps, 40)]
    lines += ['', 'HOUR_EXCLUSION_SENSITIVITY_MT5', show(hour_ex, 40)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage186 is audit-only. It investigates B_HIGH_FREQUENCY loss patterns by month, MT5 hour, weekday, weak-month date/week, entry-time feature differences, and simple h1_atr14/hour exclusion sensitivity. M5 future outcomes are used only for audit scoring, not as entry gates.',
        'Do not remove B or add a live filter only because one weak month improves. Any proposed filter must be rechecked across full/train/test/recent3m and portfolio overlap in a later stage.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
