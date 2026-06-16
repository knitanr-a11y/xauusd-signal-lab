#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import re
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

STEP = 'GOLD_V3_180_SELECTED_CANDIDATE_STABILITY_AUDIT_ONLY'
BENCHMARK_PF = 2.237
DEFAULT_COST_POINTS = 3.0


def progress(msg: str) -> None:
    print(f'[180 progress] {msg}', flush=True)


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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def pf_wr_sum(pnl: pd.Series | np.ndarray) -> tuple[int, float, float, float]:
    x = pd.to_numeric(pd.Series(pnl), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    n = int(len(x))
    if n == 0:
        return 0, 0.0, math.nan, math.nan
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    return n, float(x.sum()), pf, float((x > 0).mean())


def metric(prefix: str, pnl: pd.Series | np.ndarray) -> dict[str, Any]:
    n, s, pf, wr = pf_wr_sum(pnl)
    return {f'{prefix}_n': n, f'{prefix}_sum': s, f'{prefix}_pf': pf, f'{prefix}_wr': wr}


def month_stats(trades: pd.DataFrame, pnl_col: str = 'pnl_net') -> dict[str, Any]:
    if trades.empty:
        return {'full_months': 0, 'full_neg_months': 0, 'worst_month': '', 'worst_month_sum': math.nan}
    m = trades.groupby('month')[pnl_col].sum().sort_index()
    return {
        'full_months': int(len(m)),
        'full_neg_months': int((m < 0).sum()),
        'worst_month': str(m.idxmin()) if len(m) else '',
        'worst_month_sum': float(m.min()) if len(m) else math.nan,
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
    keep = set(months[-3:])
    return tr[tr['month'].astype(str).isin(keep)].copy()


def vol_bucket_rows(tr: pd.DataFrame, train: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if tr.empty or 'h1_atr14' not in tr.columns:
        return out
    ref = pd.to_numeric(train.get('h1_atr14', pd.Series(dtype=float)), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    if len(ref) < 30:
        return out
    q1, q2 = ref.quantile([0.33, 0.66]).values
    x = pd.to_numeric(tr['h1_atr14'], errors='coerce')
    buckets = {
        'low_vol': tr[(x <= q1).fillna(False)].copy(),
        'mid_vol': tr[((x > q1) & (x <= q2)).fillna(False)].copy(),
        'high_vol': tr[(x > q2).fillna(False)].copy(),
    }
    for name, g in buckets.items():
        out.update(metric(name, g['pnl_net'] if not g.empty else np.array([])))
    return out


def eval_trades(
    data: pd.DataFrame,
    m5: pd.DataFrame,
    scenario: str,
    rule: str,
    direction: str,
    tp: float,
    sl: float,
    horizon_m5: int,
    cost_points: float,
) -> dict[str, Any]:
    mask, problems = s179.literal_rule_mask(rule, data)
    entries = data.loc[mask].copy()
    row: dict[str, Any] = {
        'scenario': scenario,
        'rule': rule,
        'direction': direction,
        'tp': float(tp),
        'sl': float(sl),
        'horizon_m5': int(horizon_m5),
        'cost_points': float(cost_points),
        'parse_problem_count': len(problems),
        'entry_rows_before_dedup': int(len(entries)),
    }
    if problems or entries.empty:
        row.update({'dedup_n': 0, 'status': 'PARSE_PROBLEM' if problems else 'EMPTY'})
        return row

    raw = s178.compute_outcome_with_exit(entries, m5, direction, float(tp), float(sl), int(horizon_m5))
    dedup = s178.dedup_resolved_only(raw)
    if dedup.empty:
        row.update({'dedup_n': 0, 'status': 'NO_DEDUP_TRADES'})
        return row
    dedup = dedup.copy()
    dedup['pnl_net'] = pd.to_numeric(dedup['pnl_raw'], errors='coerce') - float(cost_points)
    dedup['month'] = pd.to_datetime(dedup['entry_dt']).dt.to_period('M').astype(str)
    train, test, full = split_trades(dedup)
    row['dedup_n'] = int(len(dedup))
    row.update(metric('train', train['pnl_net'] if not train.empty else np.array([])))
    row.update(metric('test', test['pnl_net'] if not test.empty else np.array([])))
    row.update(metric('full', full['pnl_net'] if not full.empty else np.array([])))
    row.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])))
    row.update(month_stats(full, 'pnl_net'))
    row.update(vol_bucket_rows(full, train))
    row['tp_hits'] = int((dedup['hit_type'] == 'TP').sum())
    row['sl_hits'] = int((dedup['hit_type'] == 'SL').sum())
    row['horizon_exits'] = int((dedup['hit_type'] == 'HORIZON').sum())
    row['passes_min_counts'] = bool(row.get('train_n', 0) >= 50 and row.get('test_n', 0) >= 15 and row.get('full_n', 0) >= 100)
    row['beats_old_pf_2_237'] = bool(
        row['passes_min_counts'] and
        row.get('train_pf', 0) > BENCHMARK_PF and
        row.get('test_pf', 0) > BENCHMARK_PF and
        row.get('full_pf', 0) > BENCHMARK_PF
    )
    row['status'] = 'OK'
    return row


def parse_rule(rule: str) -> list[tuple[str, str, float]]:
    out: list[tuple[str, str, float]] = []
    for part in str(rule).split(' & '):
        expr = part.strip()
        m = s179.RULE_RE.match(expr)
        if not m:
            continue
        col, op, val = m.groups()
        out.append((col, op, float(val)))
    return out


def fmt_cond(col: str, op: str, val: float) -> str:
    return f'{col}{op}{val:.6g}'


def adjust_threshold(op: str, val: float, mode: str, pct: float) -> float:
    # relaxed means more entries; strict means fewer entries.
    if op in ['<=', '<']:
        if val < 0:
            return val * (1 - pct) if mode == 'relaxed' else val * (1 + pct)
        return val * (1 + pct) if mode == 'relaxed' else val * (1 - pct)
    if op in ['>=', '>']:
        if val < 0:
            return val * (1 + pct) if mode == 'relaxed' else val * (1 - pct)
        return val * (1 - pct) if mode == 'relaxed' else val * (1 + pct)
    return val


def build_threshold_variants(rule: str) -> list[tuple[str, str]]:
    conds = parse_rule(rule)
    variants: list[tuple[str, str]] = [('base_rule', rule)]
    if not conds:
        return variants

    for pct in [0.05, 0.10, 0.20]:
        for mode in ['relaxed', 'strict']:
            parts = [fmt_cond(c, o, adjust_threshold(o, v, mode, pct)) for c, o, v in conds]
            variants.append((f'all_{mode}_{int(pct*100)}pct', ' & '.join(parts)))
            for i, (c, o, v) in enumerate(conds, 1):
                parts = [fmt_cond(cc, oo, vv) for cc, oo, vv in conds]
                parts[i - 1] = fmt_cond(c, o, adjust_threshold(o, v, mode, pct))
                variants.append((f'cond{i}_{mode}_{int(pct*100)}pct', ' & '.join(parts)))

    if len(conds) >= 2:
        for i in range(len(conds)):
            parts = [fmt_cond(c, o, v) for j, (c, o, v) in enumerate(conds) if j != i]
            variants.append((f'drop_cond{i+1}_ablation', ' & '.join(parts)))
    return variants


def tp_sl_grid(base_tp: float, base_sl: float, base_horizon: int) -> list[tuple[str, float, float, int]]:
    tps = sorted({base_tp - 10, base_tp - 5, base_tp, base_tp + 5, base_tp + 10, base_tp + 20})
    sls = sorted({max(1.0, base_sl - 10), max(1.0, base_sl - 5), base_sl, base_sl + 5, base_sl + 10})
    horizons = sorted({max(12, base_horizon - 64), base_horizon, base_horizon + 64})
    out = []
    for tp in tps:
        for sl in sls:
            for hz in horizons:
                out.append((f'tp{tp:g}_sl{sl:g}_hz{hz}', float(tp), float(sl), int(hz)))
    return out


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out179 = root / '179'
    out = root / '180'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage179 selected candidate')
    s179_summary = read_json(out179 / 'gold_v3_179_summary.json')
    if not s179_summary or not s179_summary.get('ready', False):
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
        save(source_diag, out / 'gold_v3_180_source_coverage.csv')

    tp_grid_df = pd.DataFrame()
    threshold_df = pd.DataFrame()
    base_row: dict[str, Any] = {}
    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        rule = str(s179_summary.get('selected_rule', ''))
        direction = str(s179_summary.get('selected_direction', 'LONG'))
        base_tp = float(s179_summary.get('selected_tp', 40.0))
        base_sl = float(s179_summary.get('selected_sl', 20.0))
        base_horizon = int(s179_summary.get('selected_horizon_m5', 192))
        cost = float(args.cost_points)

        progress('evaluate base and TP/SL nearby grid')
        grid_rows = []
        for scenario, tp, sl, hz in tp_sl_grid(base_tp, base_sl, base_horizon):
            grid_rows.append(eval_trades(data, frames['m5'], scenario, rule, direction, tp, sl, hz, cost))
        tp_grid_df = pd.DataFrame(grid_rows)
        save(tp_grid_df, out / 'gold_v3_180_tp_sl_horizon_grid.csv')
        base_hits = tp_grid_df[tp_grid_df['scenario'].eq(f'tp{base_tp:g}_sl{base_sl:g}_hz{base_horizon}')]
        base_row = base_hits.iloc[0].to_dict() if not base_hits.empty else {}

        progress('evaluate threshold relaxed/strict variants')
        threshold_rows = []
        for scenario, variant_rule in build_threshold_variants(rule):
            threshold_rows.append(eval_trades(data, frames['m5'], scenario, variant_rule, direction, base_tp, base_sl, base_horizon, cost))
        threshold_df = pd.DataFrame(threshold_rows)
        save(threshold_df, out / 'gold_v3_180_threshold_sensitivity.csv')

    ready = len(blockers) == 0
    robust_grid = tp_grid_df[(tp_grid_df.get('status', '') == 'OK') & (tp_grid_df.get('beats_old_pf_2_237', False).astype(bool))].copy() if not tp_grid_df.empty else pd.DataFrame()
    robust_threshold = threshold_df[(threshold_df.get('status', '') == 'OK') & (threshold_df.get('beats_old_pf_2_237', False).astype(bool))].copy() if not threshold_df.empty else pd.DataFrame()

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE180_STABILITY_TABLES_READY_AUDIT_ONLY' if ready else 'STAGE180_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'old_pf_benchmark': BENCHMARK_PF,
        'selected_rule': s179_summary.get('selected_rule', ''),
        'selected_direction': s179_summary.get('selected_direction', ''),
        'selected_tp': s179_summary.get('selected_tp', ''),
        'selected_sl': s179_summary.get('selected_sl', ''),
        'selected_horizon_m5': s179_summary.get('selected_horizon_m5', ''),
        'cost_points': float(args.cost_points),
        'base_full_n': int(base_row.get('full_n', 0)) if base_row else 0,
        'base_full_pf': float(base_row.get('full_pf', math.nan)) if base_row else math.nan,
        'base_test_pf': float(base_row.get('test_pf', math.nan)) if base_row else math.nan,
        'base_recent3m_pf': float(base_row.get('recent3m_pf', math.nan)) if base_row else math.nan,
        'base_full_neg_months': int(base_row.get('full_neg_months', 0)) if base_row else 0,
        'tp_sl_grid_rows': int(len(tp_grid_df)) if not tp_grid_df.empty else 0,
        'tp_sl_grid_beats_old_rows': int(len(robust_grid)) if not robust_grid.empty else 0,
        'threshold_variant_rows': int(len(threshold_df)) if not threshold_df.empty else 0,
        'threshold_variant_beats_old_rows': int(len(robust_threshold)) if not robust_threshold.empty else 0,
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
    (out / 'gold_v3_180_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_180_decision.csv')

    def show_cols(df: pd.DataFrame, n: int = 30) -> str:
        if df.empty:
            return 'NO_ROWS'
        cols = [
            'scenario', 'direction', 'tp', 'sl', 'horizon_m5', 'entry_rows_before_dedup', 'dedup_n',
            'train_n', 'train_pf', 'train_wr', 'test_n', 'test_pf', 'test_wr', 'full_n', 'full_pf', 'full_wr',
            'recent3m_n', 'recent3m_pf', 'recent3m_wr', 'low_vol_n', 'low_vol_pf', 'mid_vol_n', 'mid_vol_pf',
            'high_vol_n', 'high_vol_pf', 'full_neg_months', 'worst_month', 'worst_month_sum', 'beats_old_pf_2_237', 'rule'
        ]
        use = [c for c in cols if c in df.columns]
        return df[use].head(n).to_string(index=False)

    top_grid = tp_grid_df.sort_values(['beats_old_pf_2_237', 'full_pf', 'test_pf', 'full_n'], ascending=[False, False, False, False]) if not tp_grid_df.empty else pd.DataFrame()
    top_threshold = threshold_df.sort_values(['beats_old_pf_2_237', 'scenario', 'full_pf', 'test_pf'], ascending=[False, True, False, False]) if not threshold_df.empty else pd.DataFrame()

    lines = ['GOLD V3 180 PASTE_ME_SELECTED_CANDIDATE_STABILITY_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'BASE_SELECTED_RULE', show_cols(pd.DataFrame([base_row]) if base_row else pd.DataFrame(), 5)]
    lines += ['', 'TP_SL_HORIZON_GRID_TOP30', show_cols(top_grid, 30)]
    lines += ['', 'THRESHOLD_SENSITIVITY_TOP40', show_cols(top_threshold, 40)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage180 is audit-only. It does not create a live signal and does not change the candidate pool. It replays the Stage179 selected literal rule, then tests nearby TP/SL/horizon settings and relaxed/strict threshold variants using only OHLC-derived features and M5 outcomes after entry. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
        'Use this to judge whether the selected candidate is robust or overfit. A stable candidate should not depend on one exact TP/SL or one exact threshold value, and should keep acceptable PF in test, recent3m, and high-vol buckets.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
