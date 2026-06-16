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

STEP = 'GOLD_V3_194_SCALP_STACK_ABC_OVERLAP_ROBUSTNESS_AUDIT_ONLY'
PRIMARY_COST = 3.0
STRESS_COST = 5.0
WEAK_MONTHS = ['2025-05', '2025-08', '2025-12']
DAILY_FOCUS_MONTHS = ['2026-05', '2026-06']

ABC_CANDIDATES = [
    {
        'candidate_id': 'A_PRECISION_BASE',
        'family': 'ABC',
        'priority': 1,
        'rule': 'd1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347',
        'direction': 'LONG',
        'tp': 40.0,
        'sl': 20.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'C_BALANCED_CAP60',
        'family': 'ABC',
        'priority': 2,
        'rule': 'd1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60',
        'direction': 'LONG',
        'tp': 30.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'B_HIGH_FREQUENCY_CAP40',
        'family': 'ABC',
        'priority': 3,
        'rule': 'd1_dist_close_atr28<=-0.394892 & h1_atr14<=40',
        'direction': 'LONG',
        'tp': 50.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
]


def progress(msg: str) -> None:
    print(f'[194 progress] {msg}', flush=True)


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


def add_time_cols(tr: pd.DataFrame) -> pd.DataFrame:
    x = tr.copy()
    if x.empty:
        return x
    x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    x['exit_dt'] = pd.to_datetime(x['exit_dt'])
    if 'month' not in x.columns or x['month'].isna().all():
        x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    x['entry_date'] = x['entry_dt'].dt.date.astype(str)
    return x


def pf_sum_wr(pnl: pd.Series | np.ndarray) -> tuple[int, float, float, float, float]:
    s = pd.to_numeric(pd.Series(pnl), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    n = int(len(s))
    if n == 0:
        return 0, 0.0, math.nan, math.nan, math.nan
    gross_profit = float(s[s > 0].sum())
    gross_loss = float(-s[s < 0].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
    wr = float((s > 0).mean())
    avg = float(s.mean())
    return n, float(s.sum()), pf, wr, avg


def split_trades(tr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if tr.empty:
        return tr.copy(), tr.copy(), tr.copy(), tr.copy()
    x = add_time_cols(tr)
    dt = pd.to_datetime(x['entry_dt'])
    train = x[(dt >= pd.Timestamp('2025-01-02')) & (dt < pd.Timestamp('2026-01-01'))].copy()
    test = x[dt >= pd.Timestamp('2026-01-01')].copy()
    full = x[dt >= pd.Timestamp('2025-01-02')].copy()
    if full.empty:
        recent = full.copy()
    else:
        months = sorted(full['month'].astype(str).unique())
        recent = full[full['month'].astype(str).isin(set(months[-3:]))].copy()
    return train, test, full, recent


def metric(prefix: str, tr: pd.DataFrame, pnl_col: str) -> dict[str, Any]:
    n, s, pf, wr, avg = pf_sum_wr(tr[pnl_col] if not tr.empty and pnl_col in tr.columns else [])
    return {
        f'{prefix}_n': n,
        f'{prefix}_sum': s,
        f'{prefix}_pf': pf,
        f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
        f'{prefix}_avg_net': avg,
    }


def monthly_stats(tr: pd.DataFrame, pnl_col: str) -> tuple[int, int, float, str]:
    if tr.empty or pnl_col not in tr.columns:
        return 0, 0, math.nan, ''
    x = add_time_cols(tr)
    m = x.groupby('month')[pnl_col].sum().sort_index()
    if m.empty:
        return 0, 0, math.nan, ''
    return int(len(m)), int((m < 0).sum()), float(m.min()), str(m.idxmin())


def evaluate(tr: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> dict[str, Any]:
    train, test, full, recent = split_trades(tr)
    out: dict[str, Any] = {}
    out.update(metric('train', train, pnl_col))
    out.update(metric('test', test, pnl_col))
    out.update(metric('full', full, pnl_col))
    out.update(metric('recent3m', recent, pnl_col))
    months, neg, worst, worst_month = monthly_stats(full, pnl_col)
    out.update({'full_months': months, 'full_neg_months': neg, 'worst_month_sum': worst, 'worst_month': worst_month})
    return out


def monthly_table(tr: pd.DataFrame, portfolio_id: str, pnl_col: str = 'pnl_net_cost3') -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    x = add_time_cols(tr)
    rows = []
    for month, g in x.groupby('month', sort=True):
        n, s, pf, wr, avg = pf_sum_wr(g[pnl_col])
        rows.append({
            'portfolio_id': portfolio_id,
            'month': month,
            'trades': n,
            'pnl_sum': s,
            'pf': pf,
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'avg_net': avg,
            'candidate_counts': json.dumps(g['candidate_id'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'candidate_id' in g.columns else '{}',
            'family_counts': json.dumps(g['family'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'family' in g.columns else '{}',
        })
    return pd.DataFrame(rows)


def daily_count_table(tr: pd.DataFrame, portfolio_id: str, pnl_col: str = 'pnl_net_cost3') -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    x = add_time_cols(tr)
    x = x[x['month'].astype(str).isin(DAILY_FOCUS_MONTHS)].copy()
    if x.empty:
        return pd.DataFrame()
    rows = []
    for day, g in x.groupby('entry_date', sort=True):
        n, s, pf, wr, avg = pf_sum_wr(g[pnl_col])
        rows.append({
            'portfolio_id': portfolio_id,
            'entry_date': day,
            'month': str(pd.Timestamp(day).to_period('M')),
            'trade_rows': n,
            'unique_entry_times': int(g['entry_dt'].nunique()),
            'max_same_timestamp_fires': int(g.groupby('entry_dt').size().max()) if len(g) else 0,
            'pnl_sum': s,
            'pf': pf,
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'avg_net': avg,
            'candidate_counts': json.dumps(g['candidate_id'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'candidate_id' in g.columns else '{}',
            'direction_counts': json.dumps(g['direction'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'direction' in g.columns else '{}',
        })
    return pd.DataFrame(rows)


def resolved_priority(trades: pd.DataFrame, priority: dict[str, float]) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    x = add_time_cols(trades)
    x['priority_score'] = x['candidate_id'].astype(str).map(priority).fillna(0.0)
    x = x.sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).reset_index(drop=True)
    kept = []
    active_exit = None
    used_entry_times: set[pd.Timestamp] = set()
    for _, r in x.iterrows():
        entry = pd.Timestamp(r['entry_dt'])
        if entry in used_entry_times:
            continue
        if active_exit is not None and entry < active_exit:
            continue
        kept.append(r)
        used_entry_times.add(entry)
        active_exit = pd.Timestamp(r['exit_dt'])
    if not kept:
        return x.iloc[0:0].copy()
    return pd.DataFrame(kept).reset_index(drop=True)


def build_abc(data_dir: Path, out: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}
    source_rows: list[dict[str, Any]] = []
    for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
        frames[tf], diag = s177.combine(tf, data_dir)
        source_rows.extend(diag)
        if frames[tf].empty:
            blockers.append({'id': 'missing_ohlc', 'tf': tf})
    source_diag = pd.DataFrame(source_rows)
    if not source_diag.empty:
        save(source_diag, out / 'gold_v3_194_source_coverage.csv')
    if blockers:
        return pd.DataFrame(), source_diag, blockers
    feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
    rows = []
    for c in ABC_CANDIDATES:
        mask, problems = s179.literal_rule_mask(c['rule'], feat)
        if problems:
            blockers.append({'id': 'abc_rule_problem', 'candidate_id': c['candidate_id'], 'problems': problems})
            continue
        entries = feat.loc[mask, ['dt', 'm15_close', 'h1_atr14']].copy()
        raw = s178.compute_outcome_with_exit(entries, frames['m5'], c['direction'], float(c['tp']), float(c['sl']), int(c['horizon_m5']))
        if raw.empty:
            continue
        raw['candidate_id'] = c['candidate_id']
        raw['family'] = 'ABC'
        raw['rule'] = c['rule']
        raw['priority_order'] = c['priority']
        raw['pnl_net_cost3'] = pd.to_numeric(raw['pnl_raw'], errors='coerce') - PRIMARY_COST
        raw['pnl_net_cost5'] = pd.to_numeric(raw['pnl_raw'], errors='coerce') - STRESS_COST
        rows.append(s178.dedup_resolved_only(raw))
    if not rows:
        blockers.append({'id': 'abc_trades_empty'})
        return pd.DataFrame(), source_diag, blockers
    abc_all = pd.concat(rows, ignore_index=True)
    priority = {c['candidate_id']: 1000.0 - float(c['priority']) for c in ABC_CANDIDATES}
    abc_port = resolved_priority(abc_all, priority)
    return abc_port, source_diag, blockers


def load_scalp_stack(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    selected = read_csv_any(root / '193' / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    resolved = read_csv_any(root / '193' / 'gold_v3_193_scalping_profit_stack_portfolio_trades.csv')
    raw = read_csv_any(root / '191' / 'gold_v3_191_scalping_top_trades_cost3.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_stack'})
    if resolved.empty:
        blockers.append({'id': 'missing_stage193_portfolio_trades'})
    if raw.empty:
        blockers.append({'id': 'missing_stage191_top_trades_for_lot_stack_comparison'})
    if blockers:
        return selected, resolved, raw, blockers
    ids = selected['candidate_id'].astype(str).tolist()
    resolved = resolved[resolved['candidate_id'].astype(str).isin(ids)].copy()
    raw = raw[raw['candidate_id'].astype(str).isin(ids)].copy()
    for name, df in [('resolved', resolved), ('raw', raw)]:
        if df.empty:
            blockers.append({'id': f'scalp_{name}_empty_after_selected_filter'})
            continue
        df['family'] = 'SCALP_STACK'
        if 'pnl_net_cost3' not in df.columns:
            if 'pnl_raw' in df.columns:
                df['pnl_net_cost3'] = pd.to_numeric(df['pnl_raw'], errors='coerce') - PRIMARY_COST
            else:
                blockers.append({'id': f'scalp_{name}_missing_pnl'})
        if 'pnl_net_cost5' not in df.columns:
            if 'pnl_raw' in df.columns:
                df['pnl_net_cost5'] = pd.to_numeric(df['pnl_raw'], errors='coerce') - STRESS_COST
            else:
                df['pnl_net_cost5'] = pd.to_numeric(df['pnl_net_cost3'], errors='coerce') - (STRESS_COST - PRIMARY_COST)
    return selected, add_time_cols(resolved), add_time_cols(raw), blockers


def same_entry_clusters(tr: pd.DataFrame, label: str) -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    x = add_time_cols(tr)
    rows = []
    for entry_dt, g in x.groupby('entry_dt', sort=True):
        if len(g) <= 1:
            continue
        n, s, pf, wr, avg = pf_sum_wr(g['pnl_net_cost3'])
        rows.append({
            'cluster_type': label,
            'entry_dt': entry_dt,
            'month': str(pd.Timestamp(entry_dt).to_period('M')),
            'fire_count': int(len(g)),
            'candidate_ids': '|'.join(g['candidate_id'].astype(str).tolist()),
            'direction_counts': json.dumps(g['direction'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'direction' in g.columns else '{}',
            'pnl_sum_cost3_if_lot_stack': s,
            'pf_cost3_if_lot_stack': pf,
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
        })
    return pd.DataFrame(rows)


def overlap_report(abc: pd.DataFrame, scalp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if abc.empty or scalp.empty:
        return pd.DataFrame(), pd.DataFrame()
    a = add_time_cols(abc).copy()
    s = add_time_cols(scalp).copy()
    exact = s.merge(
        a[['entry_dt', 'exit_dt', 'candidate_id', 'direction']].rename(columns={'exit_dt': 'abc_exit_dt', 'candidate_id': 'abc_candidate_id', 'direction': 'abc_direction'}),
        on='entry_dt', how='inner', suffixes=('_scalp', '_abc')
    )
    active_rows = []
    a_small = a[['entry_dt', 'exit_dt', 'candidate_id', 'direction']].sort_values('entry_dt').reset_index(drop=True)
    for _, sr in s.iterrows():
        st = pd.Timestamp(sr['entry_dt'])
        hits = a_small[(a_small['entry_dt'] <= st) & (a_small['exit_dt'] > st)]
        for _, ar in hits.iterrows():
            active_rows.append({
                'scalp_entry_dt': st,
                'scalp_exit_dt': sr['exit_dt'],
                'scalp_candidate_id': sr['candidate_id'],
                'scalp_direction': sr.get('direction', ''),
                'abc_entry_dt': ar['entry_dt'],
                'abc_exit_dt': ar['exit_dt'],
                'abc_candidate_id': ar['candidate_id'],
                'abc_direction': ar.get('direction', ''),
                'direction_conflict': str(sr.get('direction', '')) != str(ar.get('direction', '')),
                'same_direction': str(sr.get('direction', '')) == str(ar.get('direction', '')),
                'month': str(st.to_period('M')),
            })
    return exact, pd.DataFrame(active_rows)


def weak_month_detail(portfolios: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, tr in portfolios.items():
        x = add_time_cols(tr)
        for m in WEAK_MONTHS:
            g = x[x['month'].astype(str).eq(m)]
            if g.empty:
                continue
            ev = evaluate(g, 'pnl_net_cost3')
            rows.append({
                'portfolio_id': name,
                'month': m,
                'trades': ev['full_n'],
                'sum': ev['full_sum'],
                'pf': ev['full_pf'],
                'wr_pct': ev['full_wr_pct'],
                'candidate_counts': json.dumps(g['candidate_id'].astype(str).value_counts().to_dict(), ensure_ascii=False),
                'direction_counts': json.dumps(g['direction'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'direction' in g.columns else '{}',
            })
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '194'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage193 SCALP_STACK and Stage191 raw selected scalp trades')
    selected_stack, scalp_one_position, scalp_lot_stack_raw, b = load_scalp_stack(root)
    blockers.extend(b)
    progress('rebuild ABC portfolio from closed OHLC')
    abc_trades, source_diag, b = build_abc(data_dir, out)
    blockers.extend(b)

    family_summary = pd.DataFrame()
    monthly_all = pd.DataFrame()
    daily_all = pd.DataFrame()
    weak_detail = pd.DataFrame()
    exact_overlap = pd.DataFrame()
    active_overlap = pd.DataFrame()
    same_scalp_clusters = pd.DataFrame()
    combined_independent = pd.DataFrame()
    combined_abc_first = pd.DataFrame()
    combined_scalp_first = pd.DataFrame()

    if not blockers:
        progress('compute overlaps, daily counts, and combined portfolios')
        save(selected_stack, out / 'gold_v3_194_scalp_stack_selected_reference.csv')
        save(scalp_one_position, out / 'gold_v3_194_scalp_stack_one_position_trades_reference.csv')
        save(scalp_lot_stack_raw, out / 'gold_v3_194_scalp_stack_raw_selected_trades_lot_stack.csv')
        save(abc_trades, out / 'gold_v3_194_abc_portfolio_trades_rebuilt.csv')

        same_scalp_clusters = same_entry_clusters(scalp_lot_stack_raw, 'SCALP_SAME_ENTRY_RAW_SELECTED')
        save(same_scalp_clusters, out / 'gold_v3_194_scalp_same_entry_clusters_lot_stack.csv')

        exact_overlap, active_overlap = overlap_report(abc_trades, scalp_lot_stack_raw)
        save(exact_overlap, out / 'gold_v3_194_exact_entry_overlap_abc_scalp_raw.csv')
        save(active_overlap, out / 'gold_v3_194_active_window_overlap_abc_scalp_raw.csv')

        combined_independent = pd.concat([abc_trades, scalp_lot_stack_raw], ignore_index=True)
        abc_priority = {c['candidate_id']: 3000.0 - float(c['priority']) for c in ABC_CANDIDATES}
        selected_ids = selected_stack['candidate_id'].astype(str).tolist()
        scalp_priority = {cid: 2000.0 - float(i) for i, cid in enumerate(selected_ids)}
        combined_abc_first = resolved_priority(combined_independent, {**scalp_priority, **abc_priority})
        combined_scalp_first = resolved_priority(combined_independent, {**abc_priority, **{k: v + 2000.0 for k, v in scalp_priority.items()}})
        save(combined_independent, out / 'gold_v3_194_combined_independent_lot_stack_no_overlap_control.csv')
        save(combined_abc_first, out / 'gold_v3_194_combined_resolved_abc_priority_first.csv')
        save(combined_scalp_first, out / 'gold_v3_194_combined_resolved_scalp_priority_first.csv')

        portfolios_cost3 = {
            'ABC_ONLY_COST3': abc_trades,
            'SCALP_ONE_POSITION_COST3': scalp_one_position,
            'SCALP_LOT_STACK_RAW_COST3': scalp_lot_stack_raw,
            'COMBINED_INDEPENDENT_LOT_STACK_COST3': combined_independent,
            'COMBINED_ABC_PRIORITY_FIRST_COST3': combined_abc_first,
            'COMBINED_SCALP_PRIORITY_FIRST_COST3': combined_scalp_first,
        }
        portfolios_cost5 = {
            'ABC_ONLY_COST5': abc_trades,
            'SCALP_ONE_POSITION_COST5': scalp_one_position,
            'SCALP_LOT_STACK_RAW_COST5': scalp_lot_stack_raw,
            'COMBINED_ABC_PRIORITY_FIRST_COST5': combined_abc_first,
            'COMBINED_SCALP_PRIORITY_FIRST_COST5': combined_scalp_first,
        }
        summary_rows = []
        for name, tr in portfolios_cost3.items():
            row = {'portfolio_id': name, 'pnl_col': 'pnl_net_cost3'}
            row.update(evaluate(tr, 'pnl_net_cost3'))
            summary_rows.append(row)
        for name, tr in portfolios_cost5.items():
            row = {'portfolio_id': name, 'pnl_col': 'pnl_net_cost5'}
            row.update(evaluate(tr, 'pnl_net_cost5'))
            summary_rows.append(row)
        family_summary = pd.DataFrame(summary_rows)
        save(family_summary, out / 'gold_v3_194_portfolio_summary_cost3_cost5.csv')

        monthly_frames = [monthly_table(tr, name, 'pnl_net_cost3') for name, tr in portfolios_cost3.items()]
        monthly_all = pd.concat([m for m in monthly_frames if not m.empty], ignore_index=True) if monthly_frames else pd.DataFrame()
        save(monthly_all, out / 'gold_v3_194_monthly_summary_cost3.csv')

        daily_frames = [daily_count_table(tr, name, 'pnl_net_cost3') for name, tr in portfolios_cost3.items()]
        daily_all = pd.concat([d for d in daily_frames if not d.empty], ignore_index=True) if daily_frames else pd.DataFrame()
        save(daily_all, out / 'gold_v3_194_daily_counts_2026_05_06_cost3.csv')

        weak_detail = weak_month_detail({
            'SCALP_ONE_POSITION': scalp_one_position,
            'SCALP_LOT_STACK_RAW': scalp_lot_stack_raw,
            'ABC': abc_trades,
            'COMBINED_ABC_FIRST': combined_abc_first,
        })
        save(weak_detail, out / 'gold_v3_194_weak_month_detail.csv')

    def get_summary(portfolio_id: str, col: str, default: Any = math.nan) -> Any:
        if family_summary.empty:
            return default
        hit = family_summary[family_summary['portfolio_id'].eq(portfolio_id)]
        if hit.empty or col not in hit.columns:
            return default
        return hit[col].iloc[0]

    ready = len(blockers) == 0
    decision = 'STAGE194_SCALP_STACK_ABC_OVERLAP_ROBUSTNESS_READY_AUDIT_ONLY' if ready else 'STAGE194_BLOCKED'
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'primary_cost_points': PRIMARY_COST,
        'stress_cost_points': STRESS_COST,
        'abc_rebuilt_trade_count': int(len(abc_trades)) if not abc_trades.empty else 0,
        'scalp_one_position_trade_count': int(len(scalp_one_position)) if not scalp_one_position.empty else 0,
        'scalp_lot_stack_raw_trade_rows': int(len(scalp_lot_stack_raw)) if not scalp_lot_stack_raw.empty else 0,
        'scalp_lot_stack_unique_entry_times': int(scalp_lot_stack_raw['entry_dt'].nunique()) if not scalp_lot_stack_raw.empty else 0,
        'scalp_same_entry_cluster_count': int(len(same_scalp_clusters)) if not same_scalp_clusters.empty else 0,
        'scalp_same_entry_total_extra_lots': int((same_scalp_clusters['fire_count'] - 1).sum()) if not same_scalp_clusters.empty else 0,
        'exact_entry_overlap_count_raw_scap_vs_abc': int(len(exact_overlap)) if not exact_overlap.empty else 0,
        'active_window_overlap_count_raw_scalp_vs_abc': int(len(active_overlap)) if not active_overlap.empty else 0,
        'active_window_direction_conflict_count_raw_scalp_vs_abc': int(active_overlap['direction_conflict'].sum()) if not active_overlap.empty and 'direction_conflict' in active_overlap.columns else 0,
        'scalp_one_position_cost3_full_n': int(num(get_summary('SCALP_ONE_POSITION_COST3', 'full_n', 0))),
        'scalp_one_position_cost3_full_sum': num(get_summary('SCALP_ONE_POSITION_COST3', 'full_sum')),
        'scalp_one_position_cost3_full_pf': num(get_summary('SCALP_ONE_POSITION_COST3', 'full_pf')),
        'scalp_lot_stack_raw_cost3_full_n': int(num(get_summary('SCALP_LOT_STACK_RAW_COST3', 'full_n', 0))),
        'scalp_lot_stack_raw_cost3_full_sum': num(get_summary('SCALP_LOT_STACK_RAW_COST3', 'full_sum')),
        'scalp_lot_stack_raw_cost3_full_pf': num(get_summary('SCALP_LOT_STACK_RAW_COST3', 'full_pf')),
        'abc_cost3_full_n': int(num(get_summary('ABC_ONLY_COST3', 'full_n', 0))),
        'abc_cost3_full_sum': num(get_summary('ABC_ONLY_COST3', 'full_sum')),
        'abc_cost3_full_pf': num(get_summary('ABC_ONLY_COST3', 'full_pf')),
        'combined_abc_first_cost3_full_n': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_n', 0))),
        'combined_abc_first_cost3_full_sum': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_sum')),
        'combined_abc_first_cost3_full_pf': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_pf')),
        'combined_abc_first_cost3_neg_months': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_neg_months', 0))),
        'scalp_one_position_cost5_full_sum': num(get_summary('SCALP_ONE_POSITION_COST5', 'full_sum')),
        'scalp_one_position_cost5_full_pf': num(get_summary('SCALP_ONE_POSITION_COST5', 'full_pf')),
        'scalp_lot_stack_raw_cost5_full_sum': num(get_summary('SCALP_LOT_STACK_RAW_COST5', 'full_sum')),
        'scalp_lot_stack_raw_cost5_full_pf': num(get_summary('SCALP_LOT_STACK_RAW_COST5', 'full_pf')),
        'daily_focus_months': DAILY_FOCUS_MONTHS,
        'weak_months_checked': WEAK_MONTHS,
        'lot_stack_policy_note': 'lot-stack means every selected SCALP candidate firing at the same time is counted as a separate trade row. one-position means resolved priority keeps only one active SCALP trade.',
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'M5 future TP/SL/horizon is used only for post-entry audit scoring. Entry rules use closed OHLC-derived features only.',
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
    (out / 'gold_v3_194_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_194_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 194 PASTE_ME_SCALP_STACK_ABC_OVERLAP_ROBUSTNESS_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PORTFOLIO_SUMMARY_COST3_COST5', show(family_summary, 20)]
    lines += ['', 'DAILY_COUNTS_2026_05_06_COST3', show(daily_all, 160)]
    lines += ['', 'SCALP_SAME_ENTRY_CLUSTERS_LOT_STACK', show(same_scalp_clusters, 80)]
    lines += ['', 'MONTHLY_SUMMARY_COST3', show(monthly_all, 140)]
    lines += ['', 'WEAK_MONTH_DETAIL', show(weak_detail, 80)]
    lines += ['', 'EXACT_ENTRY_OVERLAP_SAMPLE_RAW_SCALP_VS_ABC', show(exact_overlap, 40)]
    lines += ['', 'ACTIVE_WINDOW_OVERLAP_SAMPLE_RAW_SCALP_VS_ABC', show(active_overlap, 60)]
    lines += ['', 'SCALP_STACK_SELECTED_REFERENCE', show(selected_stack, 20)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage194 is audit-only. It compares SCALP_STACK one-position counting versus lot-stack counting, where simultaneous selected SCALP candidate fires are counted as separate trade rows.',
        'For safety, one-position counting is the conservative base view. Lot-stack is a risk-sizing hypothesis only and should not be used live without additional drawdown and margin-risk audit.',
        'The daily table reports 2026-05 and 2026-06 trade rows and unique entry times, so it can answer how many days and how many trades occurred under each counting policy.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
