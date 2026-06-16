#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_196_SCALP_ONE_POSITION_FULL_PERIOD_FILTER_SENSITIVITY_AUDIT_ONLY'
PRIMARY_COST = 3.0
FOCUS_MONTHS = ['2026-05', '2026-06']
BAD_JUNE_HOURS = [4, 8, 9, 10, 13, 20]
WEAK_DAYS = ['2026-05-20', '2026-05-28', '2026-06-02', '2026-06-10', '2026-06-15']


def progress(msg: str) -> None:
    print(f'[196 progress] {msg}', flush=True)


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


def num(x: Any, default: float = 0.0) -> float:
    try:
        v = pd.to_numeric(pd.Series([x]), errors='coerce').iloc[0]
        if pd.isna(v) or not math.isfinite(float(v)):
            return default
        return float(v)
    except Exception:
        return default


def add_cols(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if x.empty:
        return x
    x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    x['exit_dt'] = pd.to_datetime(x['exit_dt'])
    x = x.sort_values('entry_dt').reset_index(drop=True)
    x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    x['entry_date'] = x['entry_dt'].dt.date.astype(str)
    x['entry_hour'] = x['entry_dt'].dt.hour.astype(int)
    x['weekday'] = x['entry_dt'].dt.day_name()
    if 'pnl_net_cost3' not in x.columns and 'pnl_raw' in x.columns:
        x['pnl_net_cost3'] = pd.to_numeric(x['pnl_raw'], errors='coerce') - PRIMARY_COST
    if 'pnl_net_cost5' not in x.columns:
        if 'pnl_raw' in x.columns:
            x['pnl_net_cost5'] = pd.to_numeric(x['pnl_raw'], errors='coerce') - 5.0
        elif 'pnl_net_cost3' in x.columns:
            x['pnl_net_cost5'] = pd.to_numeric(x['pnl_net_cost3'], errors='coerce') - 2.0
    return x


def pf_sum_wr(pnl: pd.Series | np.ndarray) -> tuple[int, float, float, float, float]:
    s = pd.to_numeric(pd.Series(pnl), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    n = int(len(s))
    if n == 0:
        return 0, 0.0, math.nan, math.nan, math.nan
    gp = float(s[s > 0].sum())
    gl = float(-s[s < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    wr = float((s > 0).mean())
    avg = float(s.mean())
    return n, float(s.sum()), pf, wr, avg


def split_eval(df: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> dict[str, Any]:
    x = add_cols(df)
    if x.empty:
        out: dict[str, Any] = {}
        for p in ['train', 'test', 'full', 'recent3m', 'may2026', 'jun2026', 'weakdays']:
            out.update({f'{p}_n': 0, f'{p}_sum': 0.0, f'{p}_pf': math.nan, f'{p}_wr_pct': math.nan, f'{p}_avg': math.nan})
        out.update({'full_months': 0, 'full_neg_months': 0, 'worst_month': '', 'worst_month_sum': math.nan})
        return out
    dt = x['entry_dt']
    subsets = {
        'train': x[(dt >= pd.Timestamp('2025-01-02')) & (dt < pd.Timestamp('2026-01-01'))],
        'test': x[dt >= pd.Timestamp('2026-01-01')],
        'full': x[dt >= pd.Timestamp('2025-01-02')],
        'may2026': x[x['month'].eq('2026-05')],
        'jun2026': x[x['month'].eq('2026-06')],
        'weakdays': x[x['entry_date'].isin(WEAK_DAYS)],
    }
    full = subsets['full']
    if not full.empty:
        months = sorted(full['month'].unique())
        subsets['recent3m'] = full[full['month'].isin(months[-3:])]
    else:
        subsets['recent3m'] = full
    out = {}
    for name, g in subsets.items():
        n, s, pf, wr, avg = pf_sum_wr(g[pnl_col] if pnl_col in g.columns else [])
        out.update({f'{name}_n': n, f'{name}_sum': s, f'{name}_pf': pf, f'{name}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan, f'{name}_avg': avg})
    m = full.groupby('month')[pnl_col].sum().sort_index() if not full.empty else pd.Series(dtype=float)
    out['full_months'] = int(len(m))
    out['full_neg_months'] = int((m < 0).sum()) if len(m) else 0
    out['worst_month'] = str(m.idxmin()) if len(m) else ''
    out['worst_month_sum'] = float(m.min()) if len(m) else math.nan
    return out


def apply_daily_max(df: pd.DataFrame, max_per_day: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = add_cols(df)
    x['_day_rank'] = x.groupby('entry_date').cumcount() + 1
    return x[x['_day_rank'] <= max_per_day].drop(columns=['_day_rank']).reset_index(drop=True)


def apply_candidate_daily_max(df: pd.DataFrame, max_per_day: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = add_cols(df)
    x['_cand_day_rank'] = x.groupby(['entry_date', 'candidate_id']).cumcount() + 1
    return x[x['_cand_day_rank'] <= max_per_day].drop(columns=['_cand_day_rank']).reset_index(drop=True)


def apply_candidate_cooldown(df: pd.DataFrame, bars_m15: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = add_cols(df)
    keep = []
    last_by_candidate: dict[str, pd.Timestamp] = {}
    delta = pd.Timedelta(minutes=15 * bars_m15)
    for _, r in x.iterrows():
        cid = str(r['candidate_id'])
        t = pd.Timestamp(r['entry_dt'])
        last = last_by_candidate.get(cid)
        if last is not None and t < last + delta:
            continue
        keep.append(r)
        last_by_candidate[cid] = t
    return pd.DataFrame(keep).reset_index(drop=True) if keep else x.iloc[0:0].copy()


def build_filters(df: pd.DataFrame) -> list[tuple[str, str, Callable[[pd.DataFrame], pd.DataFrame]]]:
    x = add_cols(df)
    filters: list[tuple[str, str, Callable[[pd.DataFrame], pd.DataFrame]]] = []
    filters.append(('BASE_NO_FILTER', 'baseline', lambda d: add_cols(d)))

    # Single-hour exclusions tested across the full period, not just focus months.
    for h in sorted(x['entry_hour'].dropna().unique().astype(int)):
        filters.append((f'exclude_hour_{h:02d}', 'time_single_full_period', lambda d, h=h: add_cols(d)[add_cols(d)['entry_hour'] != h]))
    for hours in [[4, 9], [4, 8, 9], [4, 8, 9, 10], BAD_JUNE_HOURS]:
        label = 'exclude_hours_' + '_'.join(f'{h:02d}' for h in hours)
        filters.append((label, 'time_group_full_period', lambda d, hours=set(hours): add_cols(d)[~add_cols(d)['entry_hour'].isin(hours)]))

    # Candidate-specific time restrictions. These are evaluated over full period.
    for cid in sorted(x['candidate_id'].astype(str).unique()):
        for hours in [[4], [9], [4, 9], [4, 8, 9]]:
            label = f'{cid}__exclude_hours_' + '_'.join(f'{h:02d}' for h in hours)
            filters.append((label, 'candidate_time_full_period', lambda d, cid=cid, hours=set(hours): add_cols(d)[~((add_cols(d)['candidate_id'].astype(str).eq(cid)) & (add_cols(d)['entry_hour'].isin(hours))) ]))

    # ATR caps/filters only if h1_atr14 exists.
    if 'h1_atr14' in x.columns:
        atr = pd.to_numeric(x['h1_atr14'], errors='coerce')
        for q in [0.70, 0.80, 0.90, 0.95]:
            cap = float(atr.quantile(q))
            filters.append((f'h1_atr14_le_q{int(q*100)}_{cap:.3f}', 'atr_cap_full_period', lambda d, cap=cap: add_cols(d)[pd.to_numeric(add_cols(d)['h1_atr14'], errors='coerce') <= cap]))
        for cap in [20.0, 25.0, 30.0, 40.0, 50.0, 60.0]:
            filters.append((f'h1_atr14_le_{cap:g}', 'atr_cap_fixed_full_period', lambda d, cap=cap: add_cols(d)[pd.to_numeric(add_cols(d)['h1_atr14'], errors='coerce') <= cap]))

    # Live-reproducible count controls.
    for n in [3, 4, 5, 6, 8, 10]:
        filters.append((f'daily_max_trades_{n}', 'daily_count_control_full_period', lambda d, n=n: apply_daily_max(d, n)))
    for n in [1, 2, 3]:
        filters.append((f'candidate_daily_max_{n}', 'candidate_day_count_control_full_period', lambda d, n=n: apply_candidate_daily_max(d, n)))
    for bars in [1, 2, 4, 8]:
        filters.append((f'candidate_cooldown_{bars}_m15bars', 'candidate_cooldown_full_period', lambda d, bars=bars: apply_candidate_cooldown(d, bars)))
    return filters


def score_result(row: dict[str, Any], base: dict[str, Any]) -> float:
    # Full-period first. Focus months can support, not dominate.
    full_delta = num(row.get('full_sum')) - num(base.get('full_sum'))
    test_delta = num(row.get('test_sum')) - num(base.get('test_sum'))
    recent_delta = num(row.get('recent3m_sum')) - num(base.get('recent3m_sum'))
    pf_delta = min(num(row.get('full_pf')), 5.0) - min(num(base.get('full_pf')), 5.0)
    neg_delta = num(base.get('full_neg_months')) - num(row.get('full_neg_months'))
    n_loss = num(base.get('full_n')) - num(row.get('full_n'))
    weak_delta = num(row.get('weakdays_sum')) - num(base.get('weakdays_sum'))
    return full_delta + 0.8 * test_delta + 0.5 * recent_delta + 120.0 * pf_delta + 150.0 * neg_delta + 0.4 * weak_delta - 0.15 * n_loss


def monthly_compare(base: pd.DataFrame, filtered: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for mode, df in [('base', base), ('filtered', filtered)]:
        x = add_cols(df)
        for m, g in x.groupby('month', sort=True):
            n, s, pf, wr, avg = pf_sum_wr(g['pnl_net_cost3'])
            rows.append({'filter_id': label, 'mode': mode, 'month': m, 'trades': n, 'sum': s, 'pf': pf, 'wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan, 'avg': avg})
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    src = root / '193'
    out = root / '196'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('read Stage193 SCALP one-position trades')
    trades = read_csv_any(src / 'gold_v3_193_scalping_profit_stack_portfolio_trades.csv')
    selected = read_csv_any(src / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    if trades.empty:
        blockers.append({'id': 'missing_stage193_one_position_trades'})
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_watchlist'})

    ranked = pd.DataFrame()
    viable = pd.DataFrame()
    best_monthly = pd.DataFrame()
    best_trades = pd.DataFrame()
    base_eval: dict[str, Any] = {}

    if not blockers:
        ids = set(selected['candidate_id'].astype(str))
        data = add_cols(trades)
        data = data[data['candidate_id'].astype(str).isin(ids)].copy()
        if data.empty:
            blockers.append({'id': 'no_trades_after_selected_filter'})
        else:
            base_eval = split_eval(data, 'pnl_net_cost3')
            rows = []
            filtered_cache: dict[str, pd.DataFrame] = {}
            progress('evaluate full-period filters')
            for filter_id, filter_type, fn in build_filters(data):
                try:
                    f = add_cols(fn(data))
                except Exception as e:
                    rows.append({'filter_id': filter_id, 'filter_type': filter_type, 'error': repr(e)})
                    continue
                ev = split_eval(f, 'pnl_net_cost3')
                row = {'filter_id': filter_id, 'filter_type': filter_type, 'error': ''}
                row.update(ev)
                row['removed_trades'] = int(base_eval.get('full_n', 0) - ev.get('full_n', 0))
                row['full_sum_delta'] = float(ev.get('full_sum', 0.0) - base_eval.get('full_sum', 0.0))
                row['test_sum_delta'] = float(ev.get('test_sum', 0.0) - base_eval.get('test_sum', 0.0))
                row['recent3m_sum_delta'] = float(ev.get('recent3m_sum', 0.0) - base_eval.get('recent3m_sum', 0.0))
                row['weakdays_sum_delta'] = float(ev.get('weakdays_sum', 0.0) - base_eval.get('weakdays_sum', 0.0))
                row['passes_full_period_primary_gate'] = bool(
                    ev.get('full_sum', -1e9) >= base_eval.get('full_sum', 0.0)
                    and ev.get('test_sum', -1e9) >= 0
                    and ev.get('recent3m_sum', -1e9) >= 0
                    and ev.get('full_pf', 0.0) >= base_eval.get('full_pf', 0.0)
                    and ev.get('full_neg_months', 999) <= base_eval.get('full_neg_months', 999)
                    and ev.get('full_n', 0) >= 0.70 * base_eval.get('full_n', 1)
                )
                row['score_full_period_first'] = score_result(row, base_eval)
                rows.append(row)
                filtered_cache[filter_id] = f
            ranked = pd.DataFrame(rows)
            if not ranked.empty:
                ranked = ranked.sort_values(['passes_full_period_primary_gate', 'score_full_period_first', 'full_sum'], ascending=[False, False, False]).reset_index(drop=True)
                ranked.insert(0, 'rank', np.arange(1, len(ranked) + 1))
                viable = ranked[(ranked['passes_full_period_primary_gate'] == True) & (ranked['filter_id'] != 'BASE_NO_FILTER')].copy()
                save(ranked, out / 'gold_v3_196_filter_sensitivity_all_results.csv')
                save(viable, out / 'gold_v3_196_filter_sensitivity_viable_full_period_first.csv')
                best_id = str(viable.iloc[0]['filter_id']) if not viable.empty else str(ranked.iloc[0]['filter_id'])
                best_trades = filtered_cache.get(best_id, data)
                save(best_trades, out / 'gold_v3_196_best_filter_trades.csv')
                best_monthly = monthly_compare(data, best_trades, best_id)
                save(best_monthly, out / 'gold_v3_196_best_filter_monthly_compare.csv')
            save(pd.DataFrame([{'portfolio_id': 'BASE_SCALP_ONE_POSITION_COST3', **base_eval}]), out / 'gold_v3_196_base_summary.csv')

    ready = len(blockers) == 0
    best = viable.iloc[0].to_dict() if not viable.empty else (ranked.iloc[0].to_dict() if not ranked.empty else {})
    decision = 'STAGE196_FULL_PERIOD_FILTER_CANDIDATES_READY_AUDIT_ONLY' if ready and not viable.empty else ('STAGE196_READY_NO_FULL_PERIOD_FILTER_PROMOTION_AUDIT_ONLY' if ready else 'STAGE196_BLOCKED')
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'source_stage': 'Stage193 SCALP_ONE_POSITION trades',
        'principle': 'Any time restriction must be judged by full-period performance first. 2026-05/2026-06 weak days are supporting diagnostics only.',
        'base_full_n': int(base_eval.get('full_n', 0)) if base_eval else 0,
        'base_full_sum': float(base_eval.get('full_sum', math.nan)) if base_eval else math.nan,
        'base_full_pf': float(base_eval.get('full_pf', math.nan)) if base_eval else math.nan,
        'base_full_neg_months': int(base_eval.get('full_neg_months', 0)) if base_eval else 0,
        'base_test_sum': float(base_eval.get('test_sum', math.nan)) if base_eval else math.nan,
        'base_recent3m_sum': float(base_eval.get('recent3m_sum', math.nan)) if base_eval else math.nan,
        'base_may2026_sum': float(base_eval.get('may2026_sum', math.nan)) if base_eval else math.nan,
        'base_jun2026_sum': float(base_eval.get('jun2026_sum', math.nan)) if base_eval else math.nan,
        'base_weakdays_sum': float(base_eval.get('weakdays_sum', math.nan)) if base_eval else math.nan,
        'result_rows': int(len(ranked)) if not ranked.empty else 0,
        'viable_full_period_first_count': int(len(viable)) if not viable.empty else 0,
        'best_filter_id': best.get('filter_id', ''),
        'best_filter_type': best.get('filter_type', ''),
        'best_full_n': int(num(best.get('full_n'))) if best else 0,
        'best_full_sum': num(best.get('full_sum'), math.nan) if best else math.nan,
        'best_full_pf': num(best.get('full_pf'), math.nan) if best else math.nan,
        'best_full_neg_months': int(num(best.get('full_neg_months'))) if best else 0,
        'best_test_sum': num(best.get('test_sum'), math.nan) if best else math.nan,
        'best_recent3m_sum': num(best.get('recent3m_sum'), math.nan) if best else math.nan,
        'best_may2026_sum': num(best.get('may2026_sum'), math.nan) if best else math.nan,
        'best_jun2026_sum': num(best.get('jun2026_sum'), math.nan) if best else math.nan,
        'best_weakdays_sum': num(best.get('weakdays_sum'), math.nan) if best else math.nan,
        'best_removed_trades': int(num(best.get('removed_trades'))) if best else 0,
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'Uses already-resolved Stage193 audit trades. Tested filters use entry-time/candidate/ATR/count data only, not future outcome.',
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
    (out / 'gold_v3_196_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_196_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        cols = ['rank', 'filter_id', 'filter_type', 'passes_full_period_primary_gate', 'full_n', 'removed_trades', 'full_sum', 'full_sum_delta', 'full_pf', 'test_sum', 'test_sum_delta', 'recent3m_sum', 'recent3m_sum_delta', 'may2026_sum', 'jun2026_sum', 'weakdays_sum', 'weakdays_sum_delta', 'full_neg_months', 'worst_month', 'worst_month_sum', 'score_full_period_first']
        use = [c for c in cols if c in df.columns]
        return df[use].head(n).to_string(index=False)

    lines = ['GOLD V3 196 PASTE_ME_SCALP_ONE_POSITION_FULL_PERIOD_FILTER_SENSITIVITY_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'TOP_FILTER_RESULTS_FULL_PERIOD_FIRST', show(ranked, 80)]
    lines += ['', 'VIABLE_FULL_PERIOD_FIRST_FILTERS', show(viable, 80)]
    lines += ['', 'BEST_FILTER_MONTHLY_COMPARE', best_monthly.head(120).to_string(index=False) if not best_monthly.empty else 'NO_ROWS']
    lines += [
        '',
        'INTERPRETATION',
        'Stage196 is audit-only. Time restrictions are evaluated over the full period first. 2026-05/2026-06 weak-day improvements are not enough by themselves.',
        'A filter is viable only if it does not reduce full-period net profit, does not worsen full PF, keeps test/recent3m profit positive, does not add negative months, and retains at least 70% of full trades.',
        'No filter is promoted automatically. No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
