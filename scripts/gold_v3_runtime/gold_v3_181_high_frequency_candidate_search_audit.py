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
import gold_v3_180_selected_candidate_stability_audit as s180

STEP = 'GOLD_V3_181_HIGH_FREQUENCY_CANDIDATE_SEARCH_AUDIT_ONLY'
BENCHMARK_PF = 2.237
DEFAULT_COST_POINTS = 3.0


def progress(msg: str) -> None:
    print(f'[181 progress] {msg}', flush=True)


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def fmt_cond(col: str, op: str, val: float) -> str:
    return f'{col}{op}{val:.6g}'


def threshold_values(op: str, val: float) -> list[float]:
    # Compact grid focused on higher trade count but still near the Stage179 candidate.
    if op in ['<=', '<'] and val < 0:
        multipliers = [0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20]
    elif op in ['>=', '>'] and val > 0:
        multipliers = [0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20]
    else:
        multipliers = [0.70, 0.85, 1.00, 1.15, 1.30]
    vals = sorted({round(float(val) * m, 10) for m in multipliers})
    return vals


def build_rule_grid(base_rule: str) -> list[tuple[str, str]]:
    conds = s180.parse_rule(base_rule)
    out: list[tuple[str, str]] = []
    if not conds:
        return [('base_rule', base_rule)]
    value_grid = [threshold_values(op, val) for col, op, val in conds]

    if len(conds) == 1:
        col, op, _ = conds[0]
        for v in value_grid[0]:
            out.append((f'{col}_{op}_{v:.6g}', fmt_cond(col, op, v)))
        return out

    if len(conds) >= 2:
        (c1, o1, v1), (c2, o2, v2) = conds[:2]
        for a in value_grid[0]:
            for b in value_grid[1]:
                out.append((f'{c1}_{a:.6g}__{c2}_{b:.6g}', f'{fmt_cond(c1, o1, a)} & {fmt_cond(c2, o2, b)}'))
        # Ablation candidates: useful for frequency discovery but usually lower quality.
        for a in value_grid[0]:
            out.append((f'ablation_cond1_only_{a:.6g}', fmt_cond(c1, o1, a)))
        for b in value_grid[1]:
            out.append((f'ablation_cond2_only_{b:.6g}', fmt_cond(c2, o2, b)))
    return out


def tp_sl_hz_grid(base_tp: float, base_sl: float, base_horizon: int) -> list[tuple[str, float, float, int]]:
    tps = [30.0, 35.0, 40.0, 45.0, 50.0]
    sls = [20.0, 25.0, 30.0]
    horizons = sorted({128, int(base_horizon), 256})
    out = []
    for tp in tps:
        for sl in sls:
            for hz in horizons:
                out.append((f'tp{tp:g}_sl{sl:g}_hz{hz}', tp, sl, hz))
    return out


def score_tier(row: pd.Series, target_full_n: int, max_neg_months: int) -> str:
    try:
        full_n = int(row.get('full_n', 0))
        train_n = int(row.get('train_n', 0))
        test_n = int(row.get('test_n', 0))
        neg = int(row.get('full_neg_months', 99))
        train_pf = float(row.get('train_pf', 0))
        test_pf = float(row.get('test_pf', 0))
        full_pf = float(row.get('full_pf', 0))
        recent_pf = float(row.get('recent3m_pf', 0))
        high_pf = float(row.get('high_vol_pf', 0))
    except Exception:
        return 'Z_INVALID'

    if full_n >= target_full_n and train_n >= 50 and test_n >= 15 and neg == 0 and train_pf >= 3.0 and test_pf >= 3.0 and full_pf >= 3.0 and recent_pf >= 3.0 and high_pf >= 3.0:
        return 'A_HIGH_FREQ_STABLE'
    if full_n >= target_full_n and train_n >= 50 and test_n >= 15 and neg <= max_neg_months and train_pf > BENCHMARK_PF and test_pf > BENCHMARK_PF and full_pf > BENCHMARK_PF and recent_pf > BENCHMARK_PF and high_pf > BENCHMARK_PF:
        return 'B_HIGH_FREQ_REVIEW'
    if full_n >= target_full_n and full_pf > BENCHMARK_PF and test_pf > BENCHMARK_PF and neg <= max_neg_months:
        return 'C_FREQ_OK_WEAKER_RECENT_OR_VOL'
    if full_n >= target_full_n:
        return 'D_FREQ_ONLY_FAILED_ROBUSTNESS'
    return 'E_TOO_FEW_TRADES'


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    ap.add_argument('--target-full-n', type=int, default=150)
    ap.add_argument('--max-neg-months', type=int, default=1)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out179 = root / '179'
    out = root / '181'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage179 selected candidate')
    s179_summary = read_json(out179 / 'gold_v3_179_summary.json')
    if not s179_summary or not bool(s179_summary.get('ready', False)):
        blockers.append({'id': 'missing_or_not_ready_stage179_summary', 'path': str(out179 / 'gold_v3_179_summary.json')})

    frames: dict[str, pd.DataFrame] = {}
    source_diag_rows: list[dict[str, Any]] = []
    if not blockers:
        progress('load OHLC with Stage177 gold_2025/live contract')
        for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
            frames[tf], diag = s177.combine(tf, data_dir)
            source_diag_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({'id': 'missing_combined_ohlc', 'tf': tf})
    source_diag = pd.DataFrame(source_diag_rows)
    if not source_diag.empty:
        save(source_diag, out / 'gold_v3_181_source_coverage.csv')

    all_df = pd.DataFrame()
    if not blockers:
        base_rule = str(s179_summary.get('selected_rule', ''))
        direction = str(s179_summary.get('selected_direction', 'LONG'))
        base_tp = float(s179_summary.get('selected_tp', 40.0))
        base_sl = float(s179_summary.get('selected_sl', 20.0))
        base_hz = int(s179_summary.get('selected_horizon_m5', 192))
        cost = float(args.cost_points)

        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        rule_grid = build_rule_grid(base_rule)
        exit_grid = tp_sl_hz_grid(base_tp, base_sl, base_hz)

        progress('evaluate high-frequency threshold x TP/SL grid')
        rows: list[dict[str, Any]] = []
        total = max(1, len(rule_grid) * len(exit_grid))
        done = 0
        for rule_name, rule in rule_grid:
            for exit_name, tp, sl, hz in exit_grid:
                done += 1
                if done % 250 == 0:
                    progress(f'evaluated {done}/{total}')
                scenario = f'{rule_name}__{exit_name}'
                row = s180.eval_trades(data, frames['m5'], scenario, rule, direction, tp, sl, hz, cost)
                row['rule_variant'] = rule_name
                row['exit_variant'] = exit_name
                row['target_full_n'] = int(args.target_full_n)
                rows.append(row)
        all_df = pd.DataFrame(rows)
        if not all_df.empty:
            all_df['candidate_tier'] = all_df.apply(lambda r: score_tier(r, int(args.target_full_n), int(args.max_neg_months)), axis=1)
            save(all_df, out / 'gold_v3_181_high_frequency_all.csv')
            ranked = all_df.sort_values(
                ['candidate_tier', 'full_n', 'test_pf', 'recent3m_pf', 'high_vol_pf', 'full_pf'],
                ascending=[True, False, False, False, False, False],
            )
            save(ranked, out / 'gold_v3_181_high_frequency_ranked.csv')

    ready = len(blockers) == 0
    if not all_df.empty:
        candidates = all_df[all_df['candidate_tier'].isin(['A_HIGH_FREQ_STABLE', 'B_HIGH_FREQ_REVIEW', 'C_FREQ_OK_WEAKER_RECENT_OR_VOL'])].copy()
        selected = candidates.sort_values(['candidate_tier', 'full_n', 'test_pf', 'recent3m_pf', 'full_pf'], ascending=[True, False, False, False, False]).head(1)
        tier_counts = all_df['candidate_tier'].value_counts().to_dict()
    else:
        candidates = pd.DataFrame()
        selected = pd.DataFrame()
        tier_counts = {}

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE181_HIGH_FREQUENCY_CANDIDATES_READY_AUDIT_ONLY' if ready else 'STAGE181_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'old_pf_benchmark': BENCHMARK_PF,
        'cost_points': float(args.cost_points),
        'target_full_n': int(args.target_full_n),
        'max_neg_months': int(args.max_neg_months),
        'base_rule': s179_summary.get('selected_rule', ''),
        'evaluated_rows': int(len(all_df)) if not all_df.empty else 0,
        'candidate_rows_A_B_C': int(len(candidates)) if not candidates.empty else 0,
        'tier_counts': tier_counts,
        'selected_candidate_tier': str(selected.iloc[0]['candidate_tier']) if not selected.empty else '',
        'selected_rule': str(selected.iloc[0]['rule']) if not selected.empty else '',
        'selected_tp': float(selected.iloc[0]['tp']) if not selected.empty else math.nan,
        'selected_sl': float(selected.iloc[0]['sl']) if not selected.empty else math.nan,
        'selected_horizon_m5': int(selected.iloc[0]['horizon_m5']) if not selected.empty else 0,
        'selected_full_n': int(selected.iloc[0]['full_n']) if not selected.empty else 0,
        'selected_train_pf': float(selected.iloc[0]['train_pf']) if not selected.empty else math.nan,
        'selected_test_pf': float(selected.iloc[0]['test_pf']) if not selected.empty else math.nan,
        'selected_full_pf': float(selected.iloc[0]['full_pf']) if not selected.empty else math.nan,
        'selected_recent3m_pf': float(selected.iloc[0]['recent3m_pf']) if not selected.empty else math.nan,
        'selected_high_vol_pf': float(selected.iloc[0]['high_vol_pf']) if not selected.empty else math.nan,
        'selected_full_neg_months': int(selected.iloc[0]['full_neg_months']) if not selected.empty else 0,
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
    (out / 'gold_v3_181_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_181_decision.csv')

    def show(df: pd.DataFrame, n: int = 40) -> str:
        if df.empty:
            return 'NO_ROWS'
        cols = [
            'candidate_tier', 'scenario', 'direction', 'tp', 'sl', 'horizon_m5', 'entry_rows_before_dedup', 'dedup_n',
            'train_n', 'train_pf', 'train_wr', 'test_n', 'test_pf', 'test_wr', 'full_n', 'full_pf', 'full_wr',
            'recent3m_n', 'recent3m_pf', 'recent3m_wr', 'high_vol_n', 'high_vol_pf', 'full_neg_months', 'worst_month',
            'worst_month_sum', 'rule'
        ]
        use = [c for c in cols if c in df.columns]
        return df[use].head(n).to_string(index=False)

    ranked_show = all_df.sort_values(['candidate_tier', 'full_n', 'test_pf', 'recent3m_pf', 'high_vol_pf', 'full_pf'], ascending=[True, False, False, False, False, False]) if not all_df.empty else pd.DataFrame()
    lines = ['GOLD V3 181 PASTE_ME_HIGH_FREQUENCY_CANDIDATE_SEARCH_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'HIGH_FREQUENCY_TOP40', show(ranked_show, 40)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage181 is audit-only. It searches higher-frequency alternatives around the Stage179 selected rule by varying saved literal thresholds and nearby TP/SL/horizon settings. It does not enable live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade.',
        'A_HIGH_FREQ_STABLE requires target trade count, min train/test/full counts, zero negative months, and PF >= 3.0 in train/test/full/recent3m/high_vol. B allows one negative month and old benchmark PF. C is frequency-first and needs manual review.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
