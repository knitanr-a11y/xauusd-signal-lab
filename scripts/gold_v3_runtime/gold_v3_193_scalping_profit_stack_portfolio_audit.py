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

STEP = 'GOLD_V3_193_SCALPING_PROFIT_STACK_PORTFOLIO_AUDIT_ONLY'
PRIMARY_COST = 3.0
MIN_CANDIDATE_FULL_N = 120
MIN_CANDIDATE_TEST_N = 30
MIN_CANDIDATE_RECENT3M_N = 10
MIN_CANDIDATE_FULL_PF = 1.45
MIN_CANDIDATE_TEST_PF = 1.45
MIN_CANDIDATE_RECENT3M_PF = 1.20
MAX_CANDIDATE_NEG_MONTHS = 5
MAX_STACK_CANDIDATES = 8


def progress(msg: str) -> None:
    print(f'[193 progress] {msg}', flush=True)


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


def add_month_col(tr: pd.DataFrame) -> pd.DataFrame:
    x = tr.copy()
    if 'month' not in x.columns or x['month'].isna().all():
        x['month'] = pd.to_datetime(x['entry_dt']).dt.to_period('M').astype(str)
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
    x = tr.copy()
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


def metric(prefix: str, tr: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> dict[str, Any]:
    n, s, pf, wr, avg = pf_sum_wr(tr[pnl_col] if not tr.empty and pnl_col in tr.columns else [])
    return {
        f'{prefix}_n': n,
        f'{prefix}_sum': s,
        f'{prefix}_pf': pf,
        f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
        f'{prefix}_avg_net': avg,
    }


def monthly_stats(tr: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> tuple[int, int, float, str]:
    if tr.empty or pnl_col not in tr.columns:
        return 0, 0, math.nan, ''
    m = tr.groupby('month')[pnl_col].sum().sort_index()
    if m.empty:
        return 0, 0, math.nan, ''
    return int(len(m)), int((m < 0).sum()), float(m.min()), str(m.idxmin())


def evaluate_trades(tr: pd.DataFrame, prefix: str = '') -> dict[str, Any]:
    x = add_month_col(tr)
    train, test, full, recent = split_trades(x)
    out: dict[str, Any] = {}
    out.update(metric('train', train))
    out.update(metric('test', test))
    out.update(metric('full', full))
    out.update(metric('recent3m', recent))
    months, neg, worst, worst_month = monthly_stats(full)
    out.update({'full_months': months, 'full_neg_months': neg, 'worst_month_sum': worst, 'worst_month': worst_month})
    if prefix:
        return {f'{prefix}_{k}': v for k, v in out.items()}
    return out


def portfolio_score(row: dict[str, Any]) -> float:
    full_sum = num(row.get('full_sum'))
    test_sum = num(row.get('test_sum'))
    recent_sum = num(row.get('recent3m_sum'))
    avg = num(row.get('full_avg_net'))
    full_pf = min(num(row.get('full_pf')), 4.0)
    test_pf = min(num(row.get('test_pf')), 4.0)
    recent_pf = min(num(row.get('recent3m_pf')), 4.0)
    neg = num(row.get('full_neg_months'))
    n = num(row.get('full_n'))
    # Stacking objective: profit amount + efficiency + robustness, not pure trade count.
    return full_sum + 0.8 * test_sum + 0.6 * recent_sum + 90.0 * full_pf + 70.0 * test_pf + 50.0 * recent_pf + 40.0 * avg + 0.10 * n - 120.0 * neg


def candidate_score(row: pd.Series) -> float:
    full_sum = num(row.get('full_sum'))
    test_sum = num(row.get('test_sum'))
    recent_sum = num(row.get('recent3m_sum'))
    avg = num(row.get('full_avg_net'))
    full_pf = min(num(row.get('full_pf')), 5.0)
    test_pf = min(num(row.get('test_pf')), 5.0)
    recent_pf = min(num(row.get('recent3m_pf')), 5.0)
    neg = num(row.get('full_neg_months'))
    n = num(row.get('full_n'))
    return full_sum + 0.8 * test_sum + 0.6 * recent_sum + 110.0 * full_pf + 80.0 * test_pf + 60.0 * recent_pf + 50.0 * avg + 0.05 * n - 140.0 * neg


def resolved_priority_portfolio(trades: pd.DataFrame, candidate_priority: dict[str, float]) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    x = trades.copy()
    x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    x['exit_dt'] = pd.to_datetime(x['exit_dt'])
    x['candidate_priority_score'] = x['candidate_id'].map(candidate_priority).fillna(0.0)
    x = x.sort_values(['entry_dt', 'candidate_priority_score'], ascending=[True, False]).reset_index(drop=True)
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


def monthly_table(tr: pd.DataFrame, label: str) -> pd.DataFrame:
    x = add_month_col(tr)
    if x.empty:
        return pd.DataFrame()
    rows = []
    for month, g in x.groupby('month', sort=True):
        n, s, pf, wr, avg = pf_sum_wr(g['pnl_net_cost3'])
        rows.append({
            'portfolio_id': label,
            'month': month,
            'trades': n,
            'pnl_sum': s,
            'pf': pf,
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'avg_net': avg,
            'candidate_counts': json.dumps(g['candidate_id'].value_counts().to_dict(), ensure_ascii=False),
        })
    return pd.DataFrame(rows)


def build_candidate_table(cost3: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in cost3.iterrows():
        cid = str(r.get('candidate_id', ''))
        tr = trades[trades['candidate_id'].astype(str).eq(cid)].copy()
        eval_row = evaluate_trades(tr)
        row = {k: r.get(k) for k in ['candidate_id', 'rank_source', 'profile_id', 'direction', 'tp', 'sl', 'horizon_m5', 'rule', 'cost_points'] if k in r.index}
        row.update(eval_row)
        row['profit_rate_score'] = candidate_score(pd.Series(row))
        row['passes_profit_stack_filter'] = bool(
            num(row.get('full_n')) >= MIN_CANDIDATE_FULL_N
            and num(row.get('test_n')) >= MIN_CANDIDATE_TEST_N
            and num(row.get('recent3m_n')) >= MIN_CANDIDATE_RECENT3M_N
            and num(row.get('full_sum')) > 0
            and num(row.get('test_sum')) > 0
            and num(row.get('recent3m_sum')) > 0
            and num(row.get('full_pf')) >= MIN_CANDIDATE_FULL_PF
            and num(row.get('test_pf')) >= MIN_CANDIDATE_TEST_PF
            and num(row.get('recent3m_pf')) >= MIN_CANDIDATE_RECENT3M_PF
            and num(row.get('full_neg_months')) <= MAX_CANDIDATE_NEG_MONTHS
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(['passes_profit_stack_filter', 'profit_rate_score'], ascending=[False, False]).reset_index(drop=True)
        out.insert(0, 'profit_stack_rank', np.arange(1, len(out) + 1))
    return out


def greedy_stack(candidates: pd.DataFrame, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if candidates.empty or trades.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    cand = candidates[candidates['passes_profit_stack_filter']].copy()
    if cand.empty:
        cand = candidates.head(10).copy()
    cand = cand.head(20).copy()
    selected: list[str] = []
    remaining = cand['candidate_id'].astype(str).tolist()
    steps: list[dict[str, Any]] = []
    current_score = -1e18
    best_portfolio = pd.DataFrame()
    priority_scores = dict(zip(cand['candidate_id'].astype(str), cand['profit_rate_score'].astype(float)))
    for step in range(1, MAX_STACK_CANDIDATES + 1):
        best_add = None
        best_eval = None
        best_tr = None
        for cid in remaining:
            ids = selected + [cid]
            raw = trades[trades['candidate_id'].astype(str).isin(ids)].copy()
            port = resolved_priority_portfolio(raw, priority_scores)
            ev = evaluate_trades(port)
            ev['portfolio_score'] = portfolio_score(ev)
            ev['candidate_count'] = len(ids)
            ev['candidate_ids'] = '|'.join(ids)
            ev['added_candidate_id'] = cid
            ev['step'] = step
            if best_eval is None or ev['portfolio_score'] > best_eval['portfolio_score']:
                best_eval = ev
                best_add = cid
                best_tr = port
        if best_eval is None or best_add is None or best_tr is None:
            break
        # Allow only meaningful improvement, but first candidate is always accepted.
        if step > 1 and best_eval['portfolio_score'] <= current_score + 1e-9:
            break
        selected.append(best_add)
        remaining = [x for x in remaining if x != best_add]
        current_score = float(best_eval['portfolio_score'])
        steps.append(best_eval)
        best_portfolio = best_tr.copy()
        if not remaining:
            break
    steps_df = pd.DataFrame(steps)
    selected_df = cand[cand['candidate_id'].astype(str).isin(selected)].copy()
    if not selected_df.empty:
        selected_df['selected_order'] = selected_df['candidate_id'].astype(str).map({cid: i + 1 for i, cid in enumerate(selected)})
        selected_df = selected_df.sort_values('selected_order')
    return steps_df, selected_df, best_portfolio


def stack_scenarios(candidates: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty or trades.empty:
        return pd.DataFrame()
    cand = candidates[candidates['passes_profit_stack_filter']].copy()
    if cand.empty:
        cand = candidates.copy()
    cand = cand.sort_values('profit_rate_score', ascending=False).head(15)
    priority_scores = dict(zip(cand['candidate_id'].astype(str), cand['profit_rate_score'].astype(float)))
    rows = []
    for k in range(1, min(12, len(cand)) + 1):
        ids = cand.head(k)['candidate_id'].astype(str).tolist()
        raw = trades[trades['candidate_id'].astype(str).isin(ids)].copy()
        independent = raw.copy()
        resolved = resolved_priority_portfolio(raw, priority_scores)
        for mode, tr in [('independent_sum_no_overlap_control', independent), ('resolved_priority_portfolio', resolved)]:
            ev = evaluate_trades(tr)
            ev['portfolio_score'] = portfolio_score(ev)
            ev.update({
                'scenario_id': f'top{k}_{mode}',
                'mode': mode,
                'candidate_count': k,
                'candidate_ids': '|'.join(ids),
                'raw_rows_before_portfolio_dedup': int(len(raw)),
                'portfolio_rows_after_dedup': int(len(tr)),
            })
            rows.append(ev)
    return pd.DataFrame(rows).sort_values('portfolio_score', ascending=False).reset_index(drop=True)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    src = root / '191'
    out = root / '193'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    cost_path = src / 'gold_v3_191_scalping_top_cost_sensitivity.csv'
    trades_path = src / 'gold_v3_191_scalping_top_trades_cost3.csv'
    monthly_path = src / 'gold_v3_191_scalping_top_monthly_cost3.csv'
    source_cov_path = src / 'gold_v3_191_source_coverage.csv'

    progress('read Stage191 candidate cost sensitivity and trades')
    cost = read_csv_any(cost_path)
    trades = read_csv_any(trades_path)
    if cost.empty:
        blockers.append({'id': 'missing_stage191_cost_sensitivity', 'path': str(cost_path)})
    if trades.empty:
        blockers.append({'id': 'missing_stage191_top_trades', 'path': str(trades_path)})
    if source_cov_path.exists():
        try:
            shutil.copyfile(source_cov_path, out / 'gold_v3_193_source_coverage_from_stage191.csv')
        except Exception:
            pass
    if monthly_path.exists():
        try:
            shutil.copyfile(monthly_path, out / 'gold_v3_193_stage191_monthly_reference.csv')
        except Exception:
            pass

    candidate_table = pd.DataFrame()
    greedy_steps = pd.DataFrame()
    selected_stack = pd.DataFrame()
    portfolio_trades = pd.DataFrame()
    scenarios = pd.DataFrame()
    portfolio_monthly = pd.DataFrame()

    if not blockers:
        required_tr = ['candidate_id', 'entry_dt', 'exit_dt', 'pnl_net_cost3']
        missing_tr = [c for c in required_tr if c not in trades.columns]
        if missing_tr:
            blockers.append({'id': 'stage191_trades_missing_columns', 'missing': missing_tr})
        else:
            trades = add_month_col(trades)
            trades['entry_dt'] = pd.to_datetime(trades['entry_dt'])
            trades['exit_dt'] = pd.to_datetime(trades['exit_dt'])
            trades['pnl_net_cost3'] = pd.to_numeric(trades['pnl_net_cost3'], errors='coerce')
            cost3 = cost[pd.to_numeric(cost.get('cost_points', pd.Series(dtype=float)), errors='coerce').eq(PRIMARY_COST)].copy()
            if cost3.empty:
                blockers.append({'id': 'no_cost3_rows_in_stage191_cost_sensitivity'})
            else:
                candidate_table = build_candidate_table(cost3, trades)
                greedy_steps, selected_stack, portfolio_trades = greedy_stack(candidate_table, trades)
                scenarios = stack_scenarios(candidate_table, trades)
                if not portfolio_trades.empty:
                    portfolio_monthly = monthly_table(portfolio_trades, 'GREEDY_PROFIT_STACK_RESOLVED')
                save(candidate_table, out / 'gold_v3_193_scalping_candidate_profit_rate_ranking.csv')
                save(selected_stack, out / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
                save(greedy_steps, out / 'gold_v3_193_scalping_greedy_stack_steps.csv')
                save(scenarios, out / 'gold_v3_193_scalping_stack_scenarios.csv')
                save(portfolio_trades, out / 'gold_v3_193_scalping_profit_stack_portfolio_trades.csv')
                save(portfolio_monthly, out / 'gold_v3_193_scalping_profit_stack_monthly.csv')

    ready = len(blockers) == 0
    best_scenario = scenarios.iloc[0].to_dict() if not scenarios.empty else {}
    final_step = greedy_steps.iloc[-1].to_dict() if not greedy_steps.empty else {}
    best_candidate = candidate_table.iloc[0].to_dict() if not candidate_table.empty else {}
    decision = 'STAGE193_SCALPING_PROFIT_STACK_WATCHLIST_READY_AUDIT_ONLY' if ready and not selected_stack.empty else ('STAGE193_READY_NO_STACK_SELECTED_AUDIT_ONLY' if ready else 'STAGE193_BLOCKED')
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'source_stage': 'Stage191 top 30 scalping candidates',
        'primary_cost_points': PRIMARY_COST,
        'stacking_objective': 'Stack multiple high profit-rate scalping candidates by marginal portfolio contribution, not simple trade count.',
        'candidate_rows_loaded': int(len(candidate_table)) if not candidate_table.empty else 0,
        'candidates_passing_profit_stack_filter': int(candidate_table['passes_profit_stack_filter'].sum()) if not candidate_table.empty and 'passes_profit_stack_filter' in candidate_table.columns else 0,
        'selected_stack_count': int(len(selected_stack)) if not selected_stack.empty else 0,
        'best_single_candidate_id': best_candidate.get('candidate_id', ''),
        'best_single_profile_id': best_candidate.get('profile_id', ''),
        'best_single_direction': best_candidate.get('direction', ''),
        'best_single_tp': num(best_candidate.get('tp'), math.nan) if best_candidate else math.nan,
        'best_single_sl': num(best_candidate.get('sl'), math.nan) if best_candidate else math.nan,
        'best_single_full_n': int(num(best_candidate.get('full_n'))) if best_candidate else 0,
        'best_single_full_sum': num(best_candidate.get('full_sum'), math.nan) if best_candidate else math.nan,
        'best_single_full_pf': num(best_candidate.get('full_pf'), math.nan) if best_candidate else math.nan,
        'greedy_final_candidate_count': int(final_step.get('candidate_count', 0)) if final_step else 0,
        'greedy_final_candidate_ids': final_step.get('candidate_ids', ''),
        'greedy_final_full_n': int(num(final_step.get('full_n'))) if final_step else 0,
        'greedy_final_full_sum': num(final_step.get('full_sum'), math.nan) if final_step else math.nan,
        'greedy_final_full_pf': num(final_step.get('full_pf'), math.nan) if final_step else math.nan,
        'greedy_final_test_sum': num(final_step.get('test_sum'), math.nan) if final_step else math.nan,
        'greedy_final_test_pf': num(final_step.get('test_pf'), math.nan) if final_step else math.nan,
        'greedy_final_recent3m_sum': num(final_step.get('recent3m_sum'), math.nan) if final_step else math.nan,
        'greedy_final_recent3m_pf': num(final_step.get('recent3m_pf'), math.nan) if final_step else math.nan,
        'greedy_final_neg_months': int(num(final_step.get('full_neg_months'))) if final_step else 0,
        'best_scenario_id': best_scenario.get('scenario_id', ''),
        'best_scenario_candidate_count': int(num(best_scenario.get('candidate_count'))) if best_scenario else 0,
        'best_scenario_full_sum': num(best_scenario.get('full_sum'), math.nan) if best_scenario else math.nan,
        'best_scenario_full_pf': num(best_scenario.get('full_pf'), math.nan) if best_scenario else math.nan,
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'Uses Stage191 post-entry audit metrics only. No new entry rule uses future outcome.',
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
    (out / 'gold_v3_193_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_193_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        cols = [
            'profit_stack_rank', 'selected_order', 'candidate_id', 'profile_id', 'direction', 'tp', 'sl', 'horizon_m5', 'rank_source',
            'full_n', 'full_sum', 'full_pf', 'full_avg_net', 'test_n', 'test_sum', 'test_pf', 'recent3m_n', 'recent3m_sum', 'recent3m_pf',
            'full_neg_months', 'worst_month', 'worst_month_sum', 'profit_rate_score', 'passes_profit_stack_filter', 'rule',
            'step', 'added_candidate_id', 'candidate_count', 'candidate_ids', 'portfolio_score', 'scenario_id', 'mode', 'portfolio_rows_after_dedup'
        ]
        use = [c for c in cols if c in df.columns]
        return df[use].head(n).to_string(index=False)

    lines = ['GOLD V3 193 PASTE_ME_SCALPING_PROFIT_STACK_PORTFOLIO_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'SELECTED_PROFIT_STACK_WATCHLIST', show(selected_stack, 30)]
    lines += ['', 'GREEDY_STACK_STEPS', show(greedy_steps, 30)]
    lines += ['', 'STACK_SCENARIOS_TOP', show(scenarios, 60)]
    lines += ['', 'CANDIDATE_PROFIT_RATE_RANKING_TOP', show(candidate_table, 60)]
    lines += ['', 'PROFIT_STACK_MONTHLY', portfolio_monthly.to_string(index=False) if not portfolio_monthly.empty else 'NO_ROWS']
    lines += [
        '',
        'INTERPRETATION',
        'Stage193 is audit-only. It treats scalping as stacking multiple high profit-rate candidates, not simply increasing raw trade count.',
        'The greedy stack chooses candidates by marginal portfolio contribution after resolved-priority de-duplication, so overlapping signals do not inflate trade count.',
        'The selected stack is WATCHLIST only. It is not PRIMARY and does not enable Discord, MT5 order, payload, AI API, live hook, or autotrade.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
