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

STEP = 'GOLD_V3_192_SCALPING_FREQUENCY_NARROWING_AUDIT_ONLY'
PRIMARY_COST = 3.0

MIN_FULL_N_HIGH_FREQ = 300
MIN_TEST_N_HIGH_FREQ = 100
MIN_RECENT3M_N_HIGH_FREQ = 30
MIN_FULL_PF = 1.20
MIN_TEST_PF = 1.20
MIN_RECENT3M_PF = 1.10
MAX_NEG_MONTHS_HIGH_FREQ = 6

# High-frequency scalping should increase opportunities but not silently accept negative splits.
REQUIRED_POSITIVE_SPLITS = ['train_sum', 'test_sum', 'full_sum', 'recent3m_sum']


def progress(msg: str) -> None:
    print(f'[192 progress] {msg}', flush=True)


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


def as_num(s: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(s, errors='coerce').replace([np.inf, -np.inf], np.nan).fillna(default)


def add_frequency_scores(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    for col in ['full_n', 'test_n', 'recent3m_n', 'train_sum', 'test_sum', 'full_sum', 'recent3m_sum', 'full_pf', 'test_pf', 'recent3m_pf', 'full_neg_months', 'tp', 'sl', 'horizon_m5']:
        if col in x.columns:
            x[col] = as_num(x[col])
        else:
            x[col] = 0.0
    x['positive_all_splits_stage192'] = True
    for col in REQUIRED_POSITIVE_SPLITS:
        x['positive_all_splits_stage192'] &= x[col] > 0
    x['is_high_frequency_candidate'] = (
        (x['full_n'] >= MIN_FULL_N_HIGH_FREQ)
        & (x['test_n'] >= MIN_TEST_N_HIGH_FREQ)
        & (x['recent3m_n'] >= MIN_RECENT3M_N_HIGH_FREQ)
        & (x['full_pf'] >= MIN_FULL_PF)
        & (x['test_pf'] >= MIN_TEST_PF)
        & (x['recent3m_pf'] >= MIN_RECENT3M_PF)
        & (x['full_neg_months'] <= MAX_NEG_MONTHS_HIGH_FREQ)
        & x['positive_all_splits_stage192']
    )
    x['is_balanced_high_frequency_candidate'] = (
        x['is_high_frequency_candidate']
        & (x['full_pf'] >= 1.50)
        & (x['test_pf'] >= 1.50)
        & (x['recent3m_pf'] >= 1.50)
        & (x['full_neg_months'] <= 4)
    )
    x['is_small_tp_frequency_candidate'] = x['is_high_frequency_candidate'] & (x['tp'] <= 10.0)
    x['frequency_score'] = (
        2.00 * x['full_n']
        + 3.00 * x['test_n']
        + 5.00 * x['recent3m_n']
        + 0.20 * x['full_sum']
        + 0.30 * x['test_sum']
        + 0.20 * x['recent3m_sum']
        + 30.0 * np.minimum(x['full_pf'], 3.0)
        + 30.0 * np.minimum(x['test_pf'], 3.0)
        + 20.0 * np.minimum(x['recent3m_pf'], 3.0)
        - 70.0 * x['full_neg_months']
    )
    x['frequency_first_rank'] = x['frequency_score'].rank(method='first', ascending=False).astype(int)
    x['profit_first_rank_source'] = as_num(x.get('rank', pd.Series(index=x.index, dtype=float))).astype(int)
    x['scalp_candidate_id'] = [f"SCALP_FREQ_{i:03d}" for i in range(1, len(x) + 1)]
    return x


def profile_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (profile_id, direction), g in df.groupby(['profile_id', 'direction'], dropna=False):
        hi = g[g['is_high_frequency_candidate']]
        bal = g[g['is_balanced_high_frequency_candidate']]
        best = g.sort_values('frequency_score', ascending=False).iloc[0]
        rows.append({
            'profile_id': profile_id,
            'direction': direction,
            'rows': int(len(g)),
            'high_freq_candidates': int(len(hi)),
            'balanced_high_freq_candidates': int(len(bal)),
            'best_frequency_score': float(best['frequency_score']),
            'best_full_n': int(best['full_n']),
            'best_test_n': int(best['test_n']),
            'best_recent3m_n': int(best['recent3m_n']),
            'best_full_sum': float(best['full_sum']),
            'best_test_sum': float(best['test_sum']),
            'best_recent3m_sum': float(best['recent3m_sum']),
            'best_full_pf': float(best['full_pf']),
            'best_test_pf': float(best['test_pf']),
            'best_recent3m_pf': float(best['recent3m_pf']),
            'best_neg_months': int(best['full_neg_months']),
            'best_rule': str(best['rule']),
        })
    return pd.DataFrame(rows).sort_values(['high_freq_candidates', 'best_frequency_score'], ascending=[False, False])


def select_candidates(freq: pd.DataFrame) -> pd.DataFrame:
    if freq.empty:
        return pd.DataFrame()
    selected: list[pd.Series] = []
    # 1. Most frequent among candidates that still keep all profit splits positive.
    high = freq[freq['is_high_frequency_candidate']].sort_values('frequency_score', ascending=False)
    if not high.empty:
        selected.append(high.iloc[0])
    # 2. Balanced PF high-frequency candidate.
    bal = freq[freq['is_balanced_high_frequency_candidate']].sort_values('frequency_score', ascending=False)
    if not bal.empty:
        selected.append(bal.iloc[0])
    # 3. Small-TP option if available, for user's scalping frequency objective.
    small = freq[freq['is_small_tp_frequency_candidate']].sort_values('frequency_score', ascending=False)
    if not small.empty:
        selected.append(small.iloc[0])
    # 4. Absolute highest full_n with positive splits, even if it is rough, as watch-only volume ceiling.
    loose = freq[freq['positive_all_splits_stage192']].sort_values(['full_n', 'frequency_score'], ascending=[False, False])
    if not loose.empty:
        selected.append(loose.iloc[0])
    if not selected:
        return pd.DataFrame()
    out = pd.DataFrame(selected).drop_duplicates(subset=['profile_id', 'direction', 'rule']).reset_index(drop=True)
    roles = []
    for i, r in out.iterrows():
        if bool(r.get('is_small_tp_frequency_candidate', False)):
            roles.append('SMALL_TP_HIGH_FREQ_WATCH')
        elif bool(r.get('is_balanced_high_frequency_candidate', False)):
            roles.append('BALANCED_HIGH_FREQ_WATCH')
        elif bool(r.get('is_high_frequency_candidate', False)):
            roles.append('HIGH_FREQ_VOLUME_WATCH')
        else:
            roles.append('LOOSE_MAX_FREQUENCY_WATCH')
    out.insert(0, 'stage192_role', roles)
    out.insert(1, 'stage192_selected_id', [f'SCALP_STAGE192_{i+1:02d}' for i in range(len(out))])
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    src = root / '191'
    out = root / '192'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    search_path = src / 'gold_v3_191_scalping_search_results_top5000.csv'
    eligible_path = src / 'gold_v3_191_scalping_eligible_profit_candidates.csv'
    source_cov_path = src / 'gold_v3_191_source_coverage.csv'

    progress('read Stage191 scalping results')
    results = read_csv_any(search_path)
    eligible = read_csv_any(eligible_path)
    if results.empty:
        blockers.append({'id': 'missing_stage191_results', 'path': str(search_path), 'action': 'run Stage191 first'})
    if source_cov_path.exists():
        try:
            shutil.copyfile(source_cov_path, out / 'gold_v3_192_source_coverage_from_stage191.csv')
        except Exception:
            pass

    freq = pd.DataFrame()
    high = pd.DataFrame()
    balanced = pd.DataFrame()
    small_tp = pd.DataFrame()
    selected = pd.DataFrame()
    prof = pd.DataFrame()

    if not blockers:
        needed = ['profile_id', 'direction', 'tp', 'sl', 'horizon_m5', 'rule', 'full_n', 'test_n', 'recent3m_n', 'train_sum', 'test_sum', 'full_sum', 'recent3m_sum', 'full_pf', 'test_pf', 'recent3m_pf', 'full_neg_months']
        missing = [c for c in needed if c not in results.columns]
        if missing:
            blockers.append({'id': 'stage191_results_missing_columns', 'missing': missing})
        else:
            freq = add_frequency_scores(results)
            freq = freq.sort_values('frequency_score', ascending=False).reset_index(drop=True)
            freq['frequency_first_rank'] = np.arange(1, len(freq) + 1)
            high = freq[freq['is_high_frequency_candidate']].copy()
            balanced = freq[freq['is_balanced_high_frequency_candidate']].copy()
            small_tp = freq[freq['is_small_tp_frequency_candidate']].copy()
            selected = select_candidates(freq)
            prof = profile_summary(freq)
            save(freq.head(2000), out / 'gold_v3_192_scalping_frequency_ranked_top2000.csv')
            save(high.head(500), out / 'gold_v3_192_scalping_high_frequency_candidates.csv')
            save(balanced.head(500), out / 'gold_v3_192_scalping_balanced_high_frequency_candidates.csv')
            save(small_tp.head(500), out / 'gold_v3_192_scalping_small_tp_frequency_candidates.csv')
            save(selected, out / 'gold_v3_192_scalping_selected_frequency_watchlist.csv')
            save(prof, out / 'gold_v3_192_scalping_profile_frequency_summary.csv')
            if not eligible.empty:
                save(eligible.head(500), out / 'gold_v3_192_stage191_eligible_reference.csv')

    ready = len(blockers) == 0
    best_high = high.iloc[0].to_dict() if not high.empty else {}
    best_bal = balanced.iloc[0].to_dict() if not balanced.empty else {}
    best_small = small_tp.iloc[0].to_dict() if not small_tp.empty else {}
    decision = 'STAGE192_SCALPING_HIGH_FREQUENCY_WATCHLIST_READY_AUDIT_ONLY' if ready and not selected.empty else ('STAGE192_SCALPING_FREQUENCY_REVIEW_READY_NO_WATCHLIST_AUDIT_ONLY' if ready else 'STAGE192_BLOCKED')
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'source_stage': 'Stage191',
        'primary_cost_points': PRIMARY_COST,
        'frequency_objective': 'Increase scalping trade count while keeping train/test/full/recent3m net profit positive after cost3.',
        'min_full_n_high_freq': MIN_FULL_N_HIGH_FREQ,
        'min_test_n_high_freq': MIN_TEST_N_HIGH_FREQ,
        'min_recent3m_n_high_freq': MIN_RECENT3M_N_HIGH_FREQ,
        'min_full_pf': MIN_FULL_PF,
        'min_test_pf': MIN_TEST_PF,
        'min_recent3m_pf': MIN_RECENT3M_PF,
        'max_neg_months_high_freq': MAX_NEG_MONTHS_HIGH_FREQ,
        'stage191_result_rows_loaded': int(len(results)) if not results.empty else 0,
        'high_frequency_candidate_count': int(len(high)) if not high.empty else 0,
        'balanced_high_frequency_candidate_count': int(len(balanced)) if not balanced.empty else 0,
        'small_tp_high_frequency_candidate_count': int(len(small_tp)) if not small_tp.empty else 0,
        'selected_watchlist_count': int(len(selected)) if not selected.empty else 0,
        'best_high_freq_profile_id': best_high.get('profile_id', ''),
        'best_high_freq_direction': best_high.get('direction', ''),
        'best_high_freq_tp': float(best_high.get('tp', math.nan)) if best_high else math.nan,
        'best_high_freq_sl': float(best_high.get('sl', math.nan)) if best_high else math.nan,
        'best_high_freq_horizon_m5': int(best_high.get('horizon_m5', 0)) if best_high else 0,
        'best_high_freq_full_n': int(best_high.get('full_n', 0)) if best_high else 0,
        'best_high_freq_test_n': int(best_high.get('test_n', 0)) if best_high else 0,
        'best_high_freq_recent3m_n': int(best_high.get('recent3m_n', 0)) if best_high else 0,
        'best_high_freq_full_sum': float(best_high.get('full_sum', math.nan)) if best_high else math.nan,
        'best_high_freq_test_sum': float(best_high.get('test_sum', math.nan)) if best_high else math.nan,
        'best_high_freq_recent3m_sum': float(best_high.get('recent3m_sum', math.nan)) if best_high else math.nan,
        'best_high_freq_full_pf': float(best_high.get('full_pf', math.nan)) if best_high else math.nan,
        'best_high_freq_test_pf': float(best_high.get('test_pf', math.nan)) if best_high else math.nan,
        'best_high_freq_recent3m_pf': float(best_high.get('recent3m_pf', math.nan)) if best_high else math.nan,
        'best_high_freq_neg_months': int(best_high.get('full_neg_months', 0)) if best_high else 0,
        'best_high_freq_rule': best_high.get('rule', ''),
        'best_balanced_rule': best_bal.get('rule', ''),
        'best_small_tp_rule': best_small.get('rule', ''),
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
    (out / 'gold_v3_192_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_192_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        cols = [
            'frequency_first_rank', 'rank', 'stage192_role', 'stage192_selected_id', 'profile_id', 'direction', 'tp', 'sl', 'horizon_m5',
            'full_n', 'test_n', 'recent3m_n', 'train_sum', 'test_sum', 'full_sum', 'recent3m_sum',
            'full_pf', 'test_pf', 'recent3m_pf', 'full_wr_pct', 'full_neg_months', 'worst_month', 'worst_month_sum',
            'frequency_score', 'rule'
        ]
        use_cols = [c for c in cols if c in df.columns]
        return df[use_cols].head(n).to_string(index=False)

    lines = ['GOLD V3 192 PASTE_ME_SCALPING_FREQUENCY_NARROWING_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'SELECTED_FREQUENCY_WATCHLIST', show(selected, 20)]
    lines += ['', 'HIGH_FREQUENCY_CANDIDATES_TOP', show(high, 80)]
    lines += ['', 'BALANCED_HIGH_FREQUENCY_CANDIDATES_TOP', show(balanced, 80)]
    lines += ['', 'SMALL_TP_HIGH_FREQUENCY_CANDIDATES_TOP', show(small_tp, 80)]
    lines += ['', 'PROFILE_FREQUENCY_SUMMARY', show(prof, 80)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage192 is audit-only. It re-ranks Stage191 scalping candidates with a frequency-first objective because the user wants more scalping trade opportunities.',
        'This does not promote any scalping candidate to PRIMARY. The selected rows are WATCHLIST only. Further monthly, overlap with ABC, live parity, and cost robustness are required before any live use.',
        'Frequency is measured with Stage191 dedup/resolved trade count metrics after closed-row entry detection and cost3 audit scoring. It is not a real executed trade count.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
