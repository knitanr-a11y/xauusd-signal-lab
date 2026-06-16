#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import shutil
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


def add_month(tr: pd.DataFrame) -> pd.DataFrame:
    x = tr.copy()
    x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    x['exit_dt'] = pd.to_datetime(x['exit_dt'])
    if 'month' not in x.columns or x['month'].isna().all():
        x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    return x


def pf_sum_wr(pnl: pd.Series | np.ndarray) -> tuple[int, float, float, float, float]:
    x = pd.to_numeric(pd.Series(pnl), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    n = int(len(x))
    if n == 0:
        return 0, 0.0, math.nan, math.nan, math.nan
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    wr = float((x > 0).mean())
    avg = float(x.mean())
    return n, float(x.sum()), pf, wr, avg


def split_trades(tr: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if tr.empty:
        return tr.copy(), tr.copy(), tr.copy(), tr.copy()
    x = add_month(tr)
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
    if tr.empty:
        return 0, 0, math.nan, ''
    m = tr.groupby('month')[pnl_col].sum().sort_index()
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
    x = add_month(tr)
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


def resolved_priority(trades: pd.DataFrame, priority: dict[str, float]) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    x = add_month(trades)
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
    priority = {c['candidate_id']: 1000.0 - c['priority'] for c in ABC_CANDIDATES}
    abc_port = resolved_priority(abc_all, priority)
    return abc_port, source_diag, blockers


def load_scalp_stack(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    src = root / '193'
    selected = read_csv_any(src / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    trades = read_csv_any(src / 'gold_v3_193_scalping_profit_stack_portfolio_trades.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_stack'})
    if trades.empty:
        blockers.append({'id': 'missing_stage193_portfolio_trades'})
    if blockers:
        return selected, trades, blockers
    ids = selected['candidate_id'].astype(str).tolist()
    trades = trades[trades['candidate_id'].astype(str).isin(ids)].copy()
    trades = add_month(trades)
    trades['family'] = 'SCALP_STACK'
    if 'pnl_net_cost3' not in trades.columns:
        if 'pnl_raw' in trades.columns:
            trades['pnl_net_cost3'] = pd.to_numeric(trades['pnl_raw'], errors='coerce') - PRIMARY_COST
        else:
            blockers.append({'id': 'scalp_trades_missing_pnl'})
    if 'pnl_net_cost5' not in trades.columns:
        if 'pnl_raw' in trades.columns:
            trades['pnl_net_cost5'] = pd.to_numeric(trades['pnl_raw'], errors='coerce') - STRESS_COST
        else:
            trades['pnl_net_cost5'] = pd.to_numeric(trades['pnl_net_cost3'], errors='coerce') - (STRESS_COST - PRIMARY_COST)
    return selected, trades, blockers


def overlap_report(abc: pd.DataFrame, scalp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if abc.empty or scalp.empty:
        return pd.DataFrame(), pd.DataFrame()
    a = add_month(abc).copy()
    s = add_month(scalp).copy()
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
    active = pd.DataFrame(active_rows)
    return exact, active


def family_summary_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
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
    progress('load Stage193 SCALP_STACK')
    selected_stack, scalp_trades, b = load_scalp_stack(root)
    blockers.extend(b)
    progress('rebuild ABC portfolio from closed OHLC')
    abc_trades, source_diag, b = build_abc(data_dir, out)
    blockers.extend(b)

    family_summary = pd.DataFrame()
    combined_independent = pd.DataFrame()
    combined_abc_first = pd.DataFrame()
    combined_scalp_first = pd.DataFrame()
    exact_overlap = pd.DataFrame()
    active_overlap = pd.DataFrame()
    monthly_all = pd.DataFrame()
    weak_detail = pd.DataFrame()

    if not blockers:
        save(selected_stack, out / 'gold_v3_194_scalp_stack_selected_reference.csv')
        save(scalp_trades, out / 'gold_v3_194_scalp_stack_portfolio_trades_reference.csv')
        save(abc_trades, out / 'gold_v3_194_abc_portfolio_trades_rebuilt.csv')
        exact_overlap, active_overlap = overlap_report(abc_trades, scalp_trades)
        save(exact_overlap, out / 'gold_v3_194_exact_entry_overlap_abc_scalp.csv')
        save(active_overlap, out / 'gold_v3_194_active_window_overlap_abc_scalp.csv')

        combined_independent = pd.concat([abc_trades, scalp_trades], ignore_index=True)
        abc_priority = {cid: 2000.0 - i for i, cid in enumerate(ABC_CANDIDATES)}
        scalp_priority = {cid: 1000.0 - i for i, cid in enumerate(selected_stack['candidate_id'].astype(str).tolist())}
        priority_abc_first = {**scalp_priority, **abc_priority}
        priority_scalp_first = {**{k: v + 2000.0 for k, v in scalp_priority.items()}, **{k: v for k, v in abc_priority.items()}}
        combined_abc_first = resolved_priority(combined_independent, priority_abc_first)
        combined_scalp_first = resolved_priority(combined_independent, priority_scalp_first)
        save(combined_independent, out / 'gold_v3_194_combined_independent_no_overlap_control.csv')
        save(combined_abc_first, out / 'gold_v3_194_combined_resolved_abc_priority_first.csv')
        save(combined_scalp_first, out / 'gold_v3_194_combined_resolved_scalp_priority_first.csv')

        summaries: list[dict[str, Any]] = []
        for name, tr in [
            ('ABC_ONLY_COST3', abc_trades),
            ('SCALP_STACK_ONLY_COST3', scalp_trades),
            ('COMBINED_INDEPENDENT_COST3', combined_independent),
            ('COMBINED_ABC_PRIORITY_FIRST_COST3', combined_abc_first),
            ('COMBINED_SCALP_PRIORITY_FIRST_COST3', combined_scalp_first),
        ]:
            row = {'portfolio_id': name, 'pnl_col': 'pnl_net_cost3'}
            row.update(evaluate(tr, 'pnl_net_cost3'))
            summaries.append(row)
        for name, tr in [
            ('ABC_ONLY_COST5', abc_trades),
            ('SCALP_STACK_ONLY_COST5', scalp_trades),
            ('COMBINED_ABC_PRIORITY_FIRST_COST5', combined_abc_first),
            ('COMBINED_SCALP_PRIORITY_FIRST_COST5', combined_scalp_first),
        ]:
            row = {'portfolio_id': name, 'pnl_col': 'pnl_net_cost5'}
            row.update(evaluate(tr, 'pnl_net_cost5'))
            summaries.append(row)
        family_summary = family_summary_table(summaries)
        save(family_summary, out / 'gold_v3_194_portfolio_summary_cost3_cost5.csv')

        monthly_frames = []
        for name, tr in [
            ('ABC_ONLY_COST3', abc_trades),
            ('SCALP_STACK_ONLY_COST3', scalp_trades),
            ('COMBINED_ABC_PRIORITY_FIRST_COST3', combined_abc_first),
            ('COMBINED_SCALP_PRIORITY_FIRST_COST3', combined_scalp_first),
        ]:
            monthly_frames.append(monthly_table(tr, name, 'pnl_net_cost3'))
        monthly_all = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()
        save(monthly_all, out / 'gold_v3_194_monthly_summary_cost3.csv')

        weak_rows = []
        for name, tr in [('SCALP_STACK', scalp_trades), ('ABC', abc_trades), ('COMBINED_ABC_FIRST', combined_abc_first)]:
            x = add_month(tr)
            for m in WEAK_MONTHS:
                g = x[x['month'].astype(str).eq(m)]
                if g.empty:
                    continue
                ev = evaluate(g, 'pnl_net_cost3')
                weak_rows.append({
                    'portfolio_id': name,
                    'month': m,
                    'trades': ev['full_n'],
                    'sum': ev['full_sum'],
                    'pf': ev['full_pf'],
                    'wr_pct': ev['full_wr_pct'],
                    'candidate_counts': json.dumps(g['candidate_id'].astype(str).value_counts().to_dict(), ensure_ascii=False),
                    'direction_counts': json.dumps(g['direction'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'direction' in g.columns else '{}',
                })
        weak_detail = pd.DataFrame(weak_rows)
        save(weak_detail, out / 'gold_v3_194_weak_month_detail.csv')

        if (root / '193' / 'gold_v3_193_scalping_profit_stack_monthly.csv').exists():
            try:
                shutil.copyfile(root / '193' / 'gold_v3_193_scalping_profit_stack_monthly.csv', out / 'gold_v3_194_stage193_scalp_monthly_reference.csv')
            except Exception:
                pass

    ready = len(blockers) == 0
    def get_summary(portfolio_id: str, col: str, default: Any = math.nan) -> Any:
        if family_summary.empty:
            return default
        hit = family_summary[family_summary['portfolio_id'].eq(portfolio_id)]
        if hit.empty or col not in hit.columns:
            return default
        return hit[col].iloc[0]

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
        'scalp_stack_trade_count': int(len(scalp_trades)) if not scalp_trades.empty else 0,
        'exact_entry_overlap_count': int(len(exact_overlap)) if not exact_overlap.empty else 0,
        'active_window_overlap_count': int(len(active_overlap)) if not active_overlap.empty else 0,
        'active_window_direction_conflict_count': int(active_overlap['direction_conflict'].sum()) if not active_overlap.empty and 'direction_conflict' in active_overlap.columns else 0,
        'abc_cost3_full_n': int(num(get_summary('ABC_ONLY_COST3', 'full_n', 0))),
        'abc_cost3_full_sum': num(get_summary('ABC_ONLY_COST3', 'full_sum')),
        'abc_cost3_full_pf': num(get_summary('ABC_ONLY_COST3', 'full_pf')),
        'abc_cost3_neg_months': int(num(get_summary('ABC_ONLY_COST3', 'full_neg_months', 0))),
        'scalp_cost3_full_n': int(num(get_summary('SCALP_STACK_ONLY_COST3', 'full_n', 0))),
        'scalp_cost3_full_sum': num(get_summary('SCALP_STACK_ONLY_COST3', 'full_sum')),
        'scalp_cost3_full_pf': num(get_summary('SCALP_STACK_ONLY_COST3', 'full_pf')),
        'scalp_cost3_neg_months': int(num(get_summary('SCALP_STACK_ONLY_COST3', 'full_neg_months', 0))),
        'combined_abc_first_cost3_full_n': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_n', 0))),
        'combined_abc_first_cost3_full_sum': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_sum')),
        'combined_abc_first_cost3_full_pf': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_pf')),
        'combined_abc_first_cost3_neg_months': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_neg_months', 0))),
        'combined_scalp_first_cost3_full_n': int(num(get_summary('COMBINED_SCALP_PRIORITY_FIRST_COST3', 'full_n', 0))),
        'combined_scalp_first_cost3_full_sum': num(get_summary('COMBINED_SCALP_PRIORITY_FIRST_COST3', 'full_sum')),
        'combined_scalp_first_cost3_full_pf': num(get_summary('COMBINED_SCALP_PRIORITY_FIRST_COST3', 'full_pf')),
        'combined_scalp_first_cost3_neg_months': int(num(get_summary('COMBINED_SCALP_PRIORITY_FIRST_COST3', 'full_neg_months', 0))),
        'scalp_cost5_full_sum': num(get_summary('SCALP_STACK_ONLY_COST5', 'full_sum')),
        'scalp_cost5_full_pf': num(get_summary('SCALP_STACK_ONLY_COST5', 'full_pf')),
        'scalp_cost5_neg_months': int(num(get_summary('SCALP_STACK_ONLY_COST5', 'full_neg_months', 0))),
        'weak_months_checked': WEAK_MONTHS,
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
    lines += ['', 'MONTHLY_SUMMARY_COST3', show(monthly_all, 120)]
    lines += ['', 'WEAK_MONTH_DETAIL', show(weak_detail, 80)]
    lines += ['', 'EXACT_ENTRY_OVERLAP_SAMPLE', show(exact_overlap, 40)]
    lines += ['', 'ACTIVE_WINDOW_OVERLAP_SAMPLE', show(active_overlap, 60)]
    lines += ['', 'SCALP_STACK_SELECTED_REFERENCE', show(selected_stack, 20)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage194 is audit-only. It checks SCALP_STACK against ABC PRIMARY candidates for exact same-entry overlap, active-window overlap, direction conflicts, cost5 stress, weak month details, and combined portfolio behavior.',
        'ABC and SCALP_STACK remain separate audit families. No scalping candidate is promoted to PRIMARY in this stage.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
