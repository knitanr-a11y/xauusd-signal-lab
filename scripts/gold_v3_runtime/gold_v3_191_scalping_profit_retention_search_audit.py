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
from typing import Any

import numpy as np
import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_177_ohlc_only_rebuild_search_audit_entry as s177
import gold_v3_178_cost_spread_slippage_monthly_robustness_audit as s178

STEP = 'GOLD_V3_191_SCALPING_PROFIT_RETENTION_SEARCH_AUDIT_ONLY'
PRIMARY_COST = 3.0
COST_SCENARIOS = [0.0, 1.0, 2.0, 3.0, 5.0]

# Small-TP scalping profiles. TP is never below 5.0.
SCALP_PROFILES = [
    {'profile_id': 'tp5_sl2p5_hz12', 'tp': 5.0, 'sl': 2.5, 'horizon_m5': 12},
    {'profile_id': 'tp5_sl2p5_hz24', 'tp': 5.0, 'sl': 2.5, 'horizon_m5': 24},
    {'profile_id': 'tp5_sl2p5_hz48', 'tp': 5.0, 'sl': 2.5, 'horizon_m5': 48},
    {'profile_id': 'tp7p5_sl2p5_hz24', 'tp': 7.5, 'sl': 2.5, 'horizon_m5': 24},
    {'profile_id': 'tp7p5_sl3_hz36', 'tp': 7.5, 'sl': 3.0, 'horizon_m5': 36},
    {'profile_id': 'tp10_sl3p5_hz36', 'tp': 10.0, 'sl': 3.5, 'horizon_m5': 36},
    {'profile_id': 'tp10_sl5_hz48', 'tp': 10.0, 'sl': 5.0, 'horizon_m5': 48},
    {'profile_id': 'tp12p5_sl5_hz64', 'tp': 12.5, 'sl': 5.0, 'horizon_m5': 64},
    {'profile_id': 'tp15_sl5_hz64', 'tp': 15.0, 'sl': 5.0, 'horizon_m5': 64},
]

SEARCH_FEATURES = [
    'd1_dist_close_atr14', 'd1_dist_close_atr28', 'd1_dist_ema20_atr28', 'd1_dist_sma50_atr28',
    'd1_rsi14', 'd1_body_atr14', 'd1_range_atr14',
    'h4_dist_ema20_atr28', 'h4_body_atr14', 'h4_body_abs_atr14', 'h4_range_atr14', 'h4_rsi14',
    'h1_dist_ema20_atr28', 'h1_atr14', 'h1_body_atr14', 'h1_body_abs_atr14', 'h1_range_atr14', 'h1_rsi14',
    'm15_close_ema20_dist_atr28', 'm15_close_sma50_dist_atr28', 'm15_body_atr14', 'm15_body_abs_atr14', 'm15_range_atr14', 'm15_rsi14',
]
QUANTILES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.33, 0.40, 0.50, 0.60, 0.67, 0.75, 0.80, 0.85, 0.90, 0.95]
MIN_RAW_ROWS = 150
MIN_TRAIN_N = 50
MIN_TEST_N = 15
MIN_FULL_N = 80
TOP_SINGLE_FOR_PAIR = 45
MAX_TOP_RESULTS = 250


def progress(msg: str) -> None:
    print(f'[191 progress] {msg}', flush=True)


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
    return {
        f'{prefix}_n': n,
        f'{prefix}_sum': s,
        f'{prefix}_pf': pf,
        f'{prefix}_wr': wr,
        f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
    }


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
    return tr[tr['month'].astype(str).isin(set(months[-3:]))].copy()


def fast_dedup(tr: pd.DataFrame) -> pd.DataFrame:
    if tr.empty:
        return tr.copy()
    x = tr.sort_values('entry_dt').reset_index(drop=True)
    entry_ns = pd.to_datetime(x['entry_dt']).astype('int64').values
    exit_ns = pd.to_datetime(x['exit_dt']).astype('int64').values
    keep_idx: list[int] = []
    active_exit = None
    for i, e in enumerate(entry_ns):
        if active_exit is not None and e < active_exit:
            continue
        keep_idx.append(i)
        active_exit = exit_ns[i]
    return x.iloc[keep_idx].reset_index(drop=True)


def monthly_summary(tr: pd.DataFrame, pnl_col: str = 'pnl_net') -> tuple[int, int, float, str]:
    if tr.empty:
        return 0, 0, math.nan, ''
    m = tr.groupby('month')[pnl_col].sum().sort_index()
    neg = int((m < 0).sum())
    worst = float(m.min()) if len(m) else math.nan
    worst_month = str(m.idxmin()) if len(m) else ''
    return int(len(m)), neg, worst, worst_month


def evaluate_trades(tr: pd.DataFrame, cost: float) -> dict[str, Any]:
    if tr.empty:
        out: dict[str, Any] = {}
        for p in ['train', 'test', 'full', 'recent3m']:
            out.update(metric(p, []))
        out.update({'full_months': 0, 'full_neg_months': 0, 'worst_month_sum': math.nan, 'worst_month': ''})
        return out
    x = tr.copy()
    x['pnl_net'] = pd.to_numeric(x['pnl_raw'], errors='coerce') - float(cost)
    train, test, full = split_trades(x)
    out = {}
    out.update(metric('train', train['pnl_net'] if not train.empty else []))
    out.update(metric('test', test['pnl_net'] if not test.empty else []))
    out.update(metric('full', full['pnl_net'] if not full.empty else []))
    out.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else []))
    months, neg, worst, worst_month = monthly_summary(full, 'pnl_net')
    out.update({'full_months': months, 'full_neg_months': neg, 'worst_month_sum': worst, 'worst_month': worst_month})
    out['tp_hits'] = int((x['hit_type'] == 'TP').sum())
    out['sl_hits'] = int((x['hit_type'] == 'SL').sum())
    out['horizon_exits'] = int((x['hit_type'] == 'HORIZON').sum())
    return out


def profit_objective(row: dict[str, Any]) -> float:
    # Profit retention first, then robust PF and recent/test contribution.
    full_sum = float(row.get('full_sum', 0.0) or 0.0)
    test_sum = float(row.get('test_sum', 0.0) or 0.0)
    recent_sum = float(row.get('recent3m_sum', 0.0) or 0.0)
    full_pf = float(row.get('full_pf', 0.0) if math.isfinite(float(row.get('full_pf', 0.0) or 0.0)) else 20.0)
    test_pf = float(row.get('test_pf', 0.0) if math.isfinite(float(row.get('test_pf', 0.0) or 0.0)) else 20.0)
    neg_penalty = 250.0 * int(row.get('full_neg_months', 0) or 0)
    n_bonus = 0.05 * float(row.get('full_n', 0) or 0)
    return full_sum + 0.75 * test_sum + 0.50 * recent_sum + 20.0 * min(full_pf, 20.0) + 10.0 * min(test_pf, 20.0) + n_bonus - neg_penalty


def build_condition_library(data: pd.DataFrame) -> list[dict[str, Any]]:
    conds: list[dict[str, Any]] = []
    for col in SEARCH_FEATURES:
        if col not in data.columns:
            continue
        x = pd.to_numeric(data[col], errors='coerce').replace([np.inf, -np.inf], np.nan)
        if x.notna().sum() < 1000:
            continue
        qs = x.quantile(QUANTILES).dropna().to_dict()
        seen: set[tuple[str, float]] = set()
        for q, val in qs.items():
            v = float(val)
            for op in ['<=', '>=']:
                key = (op, round(v, 6))
                if key in seen:
                    continue
                seen.add(key)
                if op == '<=':
                    mask = (x <= v).fillna(False).values
                else:
                    mask = (x >= v).fillna(False).values
                n = int(mask.sum())
                if n < MIN_RAW_ROWS:
                    continue
                conds.append({
                    'condition': f'{col}{op}{v:.6f}',
                    'feature': col,
                    'op': op,
                    'threshold': v,
                    'q': q,
                    'raw_rows': n,
                    'mask': mask,
                })
    return conds


def make_profile_raw(data: pd.DataFrame, m5: pd.DataFrame, direction: str, profile: dict[str, Any]) -> pd.DataFrame:
    entries = data[['dt', 'm15_close', 'h1_atr14']].copy()
    raw = s178.compute_outcome_with_exit(entries, m5, direction, float(profile['tp']), float(profile['sl']), int(profile['horizon_m5']))
    if raw.empty:
        return raw
    dt_to_pos = pd.Series(np.arange(len(data), dtype=int), index=pd.to_datetime(data['dt'])).to_dict()
    raw['row_pos'] = pd.to_datetime(raw['entry_dt']).map(dt_to_pos).astype('Int64')
    raw = raw[raw['row_pos'].notna()].copy()
    raw['row_pos'] = raw['row_pos'].astype(int)
    raw['profile_id'] = profile['profile_id']
    raw['direction'] = direction
    return raw


def subset_and_dedup(raw: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    if raw.empty:
        return raw.copy()
    keep = mask[raw['row_pos'].values]
    return fast_dedup(raw.loc[keep].copy())


def make_rule(row_or_rows: list[dict[str, Any]]) -> str:
    return ' & '.join(r['condition'] for r in row_or_rows)


def evaluate_condition(raw: pd.DataFrame, mask: np.ndarray, profile: dict[str, Any], direction: str, rule: str, rule_type: str, raw_rows: int) -> dict[str, Any]:
    tr = subset_and_dedup(raw, mask)
    met = evaluate_trades(tr, PRIMARY_COST)
    out: dict[str, Any] = {
        'profile_id': profile['profile_id'],
        'direction': direction,
        'tp': float(profile['tp']),
        'sl': float(profile['sl']),
        'horizon_m5': int(profile['horizon_m5']),
        'rule_type': rule_type,
        'rule': rule,
        'cost_points': PRIMARY_COST,
        'raw_entry_rows': int(raw_rows),
        'dedup_rows': int(len(tr)),
    }
    out.update(met)
    out['eligible_min_counts'] = bool(out.get('train_n', 0) >= MIN_TRAIN_N and out.get('test_n', 0) >= MIN_TEST_N and out.get('full_n', 0) >= MIN_FULL_N)
    out['profit_positive_all_splits'] = bool(out.get('train_sum', 0) > 0 and out.get('test_sum', 0) > 0 and out.get('full_sum', 0) > 0 and out.get('recent3m_sum', 0) > 0)
    out['objective_score_profit_first'] = profit_objective(out)
    return out


def monthly_table(tr: pd.DataFrame, cost: float, candidate_id: str) -> pd.DataFrame:
    if tr.empty:
        return pd.DataFrame()
    x = tr.copy()
    x['pnl_net'] = pd.to_numeric(x['pnl_raw'], errors='coerce') - float(cost)
    rows = []
    for month, g in x.groupby('month', sort=True):
        n, s, pf, wr = pf_sum_wr(g['pnl_net'])
        rows.append({
            'candidate_id': candidate_id,
            'month': month,
            'trades': n,
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'pf': pf,
            'pnl_sum': s,
            'tp_hits': int((g['hit_type'] == 'TP').sum()),
            'sl_hits': int((g['hit_type'] == 'SL').sum()),
            'horizon_exits': int((g['hit_type'] == 'HORIZON').sum()),
        })
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--pair-top', type=int, default=TOP_SINGLE_FOR_PAIR)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '191'
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
        save(source_diag, out / 'gold_v3_191_source_coverage.csv')

    results = pd.DataFrame()
    cost_sens = pd.DataFrame()
    top_trades = pd.DataFrame()
    top_monthly = pd.DataFrame()

    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
        data = data[data['dt'] >= pd.Timestamp('2025-01-02')].copy().reset_index(drop=True)
        conds = build_condition_library(data)
        save(pd.DataFrame([{k: v for k, v in c.items() if k != 'mask'} for c in conds]), out / 'gold_v3_191_condition_library.csv')
        if not conds:
            blockers.append({'id': 'condition_library_empty'})
        else:
            all_rows: list[dict[str, Any]] = []
            raw_cache: dict[tuple[str, str], pd.DataFrame] = {}
            for profile in SCALP_PROFILES:
                for direction in ['LONG', 'SHORT']:
                    progress(f"profile {profile['profile_id']} {direction}: precompute outcomes")
                    raw = make_profile_raw(data, frames['m5'], direction, profile)
                    raw_cache[(profile['profile_id'], direction)] = raw
                    if raw.empty:
                        continue
                    single_rows: list[dict[str, Any]] = []
                    for c in conds:
                        row = evaluate_condition(raw, c['mask'], profile, direction, c['condition'], 'single', c['raw_rows'])
                        single_rows.append(row)
                    single_df = pd.DataFrame(single_rows).sort_values('objective_score_profit_first', ascending=False)
                    all_rows.extend(single_rows)
                    top_conds = []
                    for _, sr in single_df.head(int(args.pair_top)).iterrows():
                        cond = next(c for c in conds if c['condition'] == sr['rule'])
                        top_conds.append(cond)
                    pair_rows: list[dict[str, Any]] = []
                    for c1, c2 in itertools.combinations(top_conds, 2):
                        if c1['feature'] == c2['feature'] and c1['op'] == c2['op']:
                            continue
                        mask = c1['mask'] & c2['mask']
                        raw_rows = int(mask.sum())
                        if raw_rows < MIN_RAW_ROWS:
                            continue
                        rule = make_rule([c1, c2])
                        pair_rows.append(evaluate_condition(raw, mask, profile, direction, rule, 'pair', raw_rows))
                    all_rows.extend(pair_rows)
            results = pd.DataFrame(all_rows)
            if results.empty:
                blockers.append({'id': 'no_search_results'})
            else:
                results = results.sort_values(['eligible_min_counts', 'profit_positive_all_splits', 'objective_score_profit_first', 'full_sum'], ascending=[False, False, False, False]).reset_index(drop=True)
                results.insert(0, 'rank', np.arange(1, len(results) + 1))
                save(results.head(5000), out / 'gold_v3_191_scalping_search_results_top5000.csv')
                eligible = results[(results['eligible_min_counts']) & (results['profit_positive_all_splits'])].copy()
                save(eligible.head(500), out / 'gold_v3_191_scalping_eligible_profit_candidates.csv')

                # Cost sensitivity and trade/monthly details for top candidates.
                cost_rows: list[dict[str, Any]] = []
                trades_rows: list[pd.DataFrame] = []
                monthly_rows: list[pd.DataFrame] = []
                top_source = eligible.head(30) if not eligible.empty else results.head(30)
                for idx, r in top_source.reset_index(drop=True).iterrows():
                    candidate_id = f"SCALP_{idx+1:03d}_{r['profile_id']}_{r['direction']}"
                    profile = {'profile_id': r['profile_id'], 'tp': r['tp'], 'sl': r['sl'], 'horizon_m5': r['horizon_m5']}
                    raw = raw_cache[(str(r['profile_id']), str(r['direction']))]
                    mask = np.ones(len(data), dtype=bool)
                    for part in str(r['rule']).split(' & '):
                        hit = next((c for c in conds if c['condition'] == part.strip()), None)
                        if hit is None:
                            mask &= False
                        else:
                            mask &= hit['mask']
                    tr = subset_and_dedup(raw, mask)
                    tr = tr.copy()
                    tr['candidate_id'] = candidate_id
                    tr['rule'] = r['rule']
                    tr['profile_id'] = r['profile_id']
                    tr['pnl_net_cost3'] = pd.to_numeric(tr['pnl_raw'], errors='coerce') - PRIMARY_COST
                    trades_rows.append(tr)
                    monthly_rows.append(monthly_table(tr, PRIMARY_COST, candidate_id))
                    for cost in COST_SCENARIOS:
                        met = evaluate_trades(tr, cost)
                        row = {
                            'candidate_id': candidate_id,
                            'rank_source': int(r['rank']),
                            'profile_id': r['profile_id'],
                            'direction': r['direction'],
                            'tp': float(r['tp']),
                            'sl': float(r['sl']),
                            'horizon_m5': int(r['horizon_m5']),
                            'rule': r['rule'],
                            'cost_points': float(cost),
                        }
                        row.update(met)
                        cost_rows.append(row)
                cost_sens = pd.DataFrame(cost_rows)
                top_trades = pd.concat(trades_rows, ignore_index=True) if trades_rows else pd.DataFrame()
                top_monthly = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()
                save(cost_sens, out / 'gold_v3_191_scalping_top_cost_sensitivity.csv')
                save(top_trades, out / 'gold_v3_191_scalping_top_trades_cost3.csv')
                save(top_monthly, out / 'gold_v3_191_scalping_top_monthly_cost3.csv')

    ready = len(blockers) == 0
    best = results.iloc[0].to_dict() if not results.empty else {}
    eligible_count = int(((results['eligible_min_counts']) & (results['profit_positive_all_splits'])).sum()) if not results.empty else 0
    decision = 'STAGE191_SCALPING_PROFIT_CANDIDATES_READY_AUDIT_ONLY' if ready and eligible_count > 0 else ('STAGE191_SCALPING_SEARCH_READY_NO_ROBUST_PROFIT_CANDIDATE_AUDIT_ONLY' if ready else 'STAGE191_BLOCKED')
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
        'cost_scenarios': COST_SCENARIOS,
        'scalp_profile_count': len(SCALP_PROFILES),
        'search_feature_count': len(SEARCH_FEATURES),
        'result_rows': int(len(results)) if not results.empty else 0,
        'eligible_profit_candidate_count': eligible_count,
        'best_rank': int(best.get('rank', 0)) if best else 0,
        'best_profile_id': best.get('profile_id', ''),
        'best_direction': best.get('direction', ''),
        'best_tp': float(best.get('tp', math.nan)) if best else math.nan,
        'best_sl': float(best.get('sl', math.nan)) if best else math.nan,
        'best_horizon_m5': int(best.get('horizon_m5', 0)) if best else 0,
        'best_rule': best.get('rule', ''),
        'best_full_n': int(best.get('full_n', 0)) if best else 0,
        'best_full_sum_cost3': float(best.get('full_sum', math.nan)) if best else math.nan,
        'best_full_pf_cost3': float(best.get('full_pf', math.nan)) if best else math.nan,
        'best_test_sum_cost3': float(best.get('test_sum', math.nan)) if best else math.nan,
        'best_test_pf_cost3': float(best.get('test_pf', math.nan)) if best else math.nan,
        'best_recent3m_sum_cost3': float(best.get('recent3m_sum', math.nan)) if best else math.nan,
        'best_recent3m_pf_cost3': float(best.get('recent3m_pf', math.nan)) if best else math.nan,
        'best_full_neg_months_cost3': int(best.get('full_neg_months', 0)) if best else 0,
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'M5 future TP/SL/horizon is used only after entry detection for audit scoring, never for entry rules.',
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
    (out / 'gold_v3_191_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_191_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    top_cols = ['rank', 'profile_id', 'direction', 'tp', 'sl', 'horizon_m5', 'rule_type', 'raw_entry_rows', 'dedup_rows', 'train_n', 'train_sum', 'train_pf', 'test_n', 'test_sum', 'test_pf', 'full_n', 'full_sum', 'full_pf', 'full_wr_pct', 'recent3m_n', 'recent3m_sum', 'recent3m_pf', 'full_neg_months', 'worst_month', 'worst_month_sum', 'objective_score_profit_first', 'rule']
    top_show = results[[c for c in top_cols if c in results.columns]].head(60) if not results.empty else pd.DataFrame()
    eligible_show = results[(results['eligible_min_counts']) & (results['profit_positive_all_splits'])][[c for c in top_cols if c in results.columns]].head(60) if not results.empty else pd.DataFrame()

    lines = ['GOLD V3 191 PASTE_ME_SCALPING_PROFIT_RETENTION_SEARCH_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'SCALP_PROFILES', pd.DataFrame(SCALP_PROFILES).to_string(index=False)]
    lines += ['', 'TOP_RESULTS_COST3_PROFIT_FIRST', show(top_show, 60)]
    lines += ['', 'ELIGIBLE_PROFIT_CANDIDATES_COST3', show(eligible_show, 60)]
    lines += ['', 'TOP_COST_SENSITIVITY', show(cost_sens, 120)]
    lines += ['', 'TOP_MONTHLY_COST3', show(top_monthly, 120)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage191 is audit-only. It explores scalping-style TP/SL profiles with TP no smaller than 5.0 and prioritizes net profit retention after cost_points=3.0 over raw win rate.',
        'Cost sensitivity is included because small TP/SL profiles are highly sensitive to spread/slippage costs. A candidate that only works at cost 0 or 1 should not be promoted without further audit.',
        'M5 future bars are used only for post-entry audit scoring. Entry rules use closed OHLC-derived features only. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
