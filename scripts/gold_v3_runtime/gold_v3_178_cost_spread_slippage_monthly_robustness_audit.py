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

STEP = 'GOLD_V3_178_COST_SPREAD_SLIPPAGE_MONTHLY_ROBUSTNESS_AUDIT_ONLY'
BENCHMARK_PF = 2.237
COST_SCENARIOS = [0.0, 1.0, 2.0, 3.0, 5.0]


def progress(msg: str) -> None:
    print(f'[178 progress] {msg}', flush=True)


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


def pf_sum_wr(pnl: np.ndarray) -> tuple[int, float, float, float]:
    x = np.asarray(pnl, dtype=float)
    x = x[np.isfinite(x)]
    n = int(len(x))
    if n == 0:
        return 0, 0.0, math.nan, math.nan
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    return n, float(x.sum()), pf, float((x > 0).mean())


def metric_row(prefix: str, pnl: np.ndarray) -> dict[str, Any]:
    n, s, pf, wr = pf_sum_wr(pnl)
    return {f'{prefix}_n': n, f'{prefix}_sum': s, f'{prefix}_pf': pf, f'{prefix}_wr': wr}


def month_summary(trades: pd.DataFrame, pnl_col: str) -> tuple[int, int, float, str]:
    if trades.empty:
        return 0, 0, math.nan, ''
    m = trades.groupby('month')[pnl_col].sum().sort_index()
    neg = int((m < 0).sum())
    worst = float(m.min()) if len(m) else math.nan
    worst_month = str(m.idxmin()) if len(m) else ''
    return int(len(m)), neg, worst, worst_month


def split_masks(dt: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train = ((dt >= pd.Timestamp('2025-01-02')) & (dt < pd.Timestamp('2026-01-01'))).values
    test = (dt >= pd.Timestamp('2026-01-01')).values
    full = (dt >= pd.Timestamp('2025-01-02')).values
    return train, test, full


def compute_outcome_with_exit(entries: pd.DataFrame, m5: pd.DataFrame, direction: str, tp: float, sl: float, horizon_m5: int) -> pd.DataFrame:
    m5 = m5.sort_values('dt').reset_index(drop=True)
    times = m5['dt'].values.astype('datetime64[ns]')
    et = entries['dt'].values.astype('datetime64[ns]')
    ep = entries.m15_close.values.astype(float)
    idx = np.searchsorted(times, et, side='right')
    highs = m5.high.values.astype(float)
    lows = m5.low.values.astype(float)
    closes = m5.close.values.astype(float)
    m5_dt = pd.to_datetime(m5['dt']).reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    for i, j in enumerate(idx):
        end = min(j + horizon_m5, len(m5))
        if j >= len(m5) or end <= j:
            continue
        price = float(ep[i])
        hit_type = 'HORIZON'
        if direction == 'LONG':
            tpv = price + tp
            slv = price - sl
            ht = highs[j:end] >= tpv
            hs = lows[j:end] <= slv
            hit = ht | hs
            if hit.any():
                k = int(np.argmax(hit))
                pnl = -sl if hs[k] else tp
                hit_type = 'SL' if hs[k] else 'TP'
                exit_i = j + k
            else:
                pnl = float(max(-sl, min(tp, closes[end - 1] - price)))
                exit_i = end - 1
        else:
            tpv = price - tp
            slv = price + sl
            ht = lows[j:end] <= tpv
            hs = highs[j:end] >= slv
            hit = ht | hs
            if hit.any():
                k = int(np.argmax(hit))
                pnl = -sl if hs[k] else tp
                hit_type = 'SL' if hs[k] else 'TP'
                exit_i = j + k
            else:
                pnl = float(max(-sl, min(tp, price - closes[end - 1])))
                exit_i = end - 1
        rows.append({
            'entry_dt': pd.Timestamp(entries.iloc[i]['dt']),
            'exit_dt': pd.Timestamp(m5_dt.iloc[exit_i]),
            'entry_price': price,
            'direction': direction,
            'tp': tp,
            'sl': sl,
            'horizon_m5': horizon_m5,
            'hit_type': hit_type,
            'pnl_raw': float(pnl),
            'month': str(pd.Timestamp(entries.iloc[i]['dt']).to_period('M')),
            'h1_atr14': float(entries.iloc[i].get('h1_atr14', math.nan)),
        })
    return pd.DataFrame(rows)


def build_rule_mask(rule: str, rule_to_mask: dict[str, np.ndarray], n: int) -> np.ndarray:
    mask = np.ones(n, dtype=bool)
    for part in str(rule).split(' & '):
        part = part.strip()
        if not part:
            continue
        mask &= rule_to_mask.get(part, np.zeros(n, dtype=bool))
    return mask


def dedup_resolved_only(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    out = []
    active_exit: pd.Timestamp | None = None
    for _, r in trades.sort_values('entry_dt').iterrows():
        entry_dt = pd.Timestamp(r['entry_dt'])
        if active_exit is not None and entry_dt < active_exit:
            continue
        out.append(r)
        # The previous trade's exit is resolved before any later entry is accepted.
        active_exit = pd.Timestamp(r['exit_dt'])
    if not out:
        return trades.iloc[0:0].copy()
    return pd.DataFrame(out).reset_index(drop=True)


def recent_months_mask(trades: pd.DataFrame, k: int = 3) -> np.ndarray:
    if trades.empty:
        return np.zeros(0, dtype=bool)
    months = sorted(trades['month'].dropna().astype(str).unique())
    keep = set(months[-k:])
    return trades['month'].astype(str).isin(keep).values


def vol_bucket_masks(trades: pd.DataFrame, train_trades: pd.DataFrame) -> dict[str, np.ndarray]:
    if trades.empty or 'h1_atr14' not in trades.columns:
        return {}
    ref = pd.to_numeric(train_trades.get('h1_atr14', pd.Series(dtype=float)), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    x = pd.to_numeric(trades['h1_atr14'], errors='coerce')
    if len(ref) < 30:
        return {}
    q1, q2 = ref.quantile([0.33, 0.66]).values
    return {
        'low_vol': (x <= q1).fillna(False).values,
        'mid_vol': ((x > q1) & (x <= q2)).fillna(False).values,
        'high_vol': (x > q2).fillna(False).values,
    }


def evaluate_scope(trades: pd.DataFrame, scope_name: str, cost: float, old_rank: int, rule_row: pd.Series) -> dict[str, Any]:
    tr = trades.copy()
    tr['pnl_net'] = tr['pnl_raw'] - cost
    dt = pd.to_datetime(tr['entry_dt']) if not tr.empty else pd.Series(dtype='datetime64[ns]')
    train_idx, test_idx, full_idx = split_masks(dt)
    train_tr = tr[train_idx].copy()
    test_tr = tr[test_idx].copy()
    full_tr = tr[full_idx].copy()

    row: dict[str, Any] = {
        'old_rank': old_rank,
        'scope': scope_name,
        'cost_points': cost,
        'direction': str(rule_row.get('direction', '')),
        'tp': float(rule_row.get('tp', math.nan)),
        'sl': float(rule_row.get('sl', math.nan)),
        'horizon_m5': int(rule_row.get('horizon_m5', 0)),
        'rule': str(rule_row.get('rule', '')),
    }
    row.update(metric_row('train', train_tr['pnl_net'].values if not train_tr.empty else np.array([])))
    row.update(metric_row('test', test_tr['pnl_net'].values if not test_tr.empty else np.array([])))
    row.update(metric_row('full', full_tr['pnl_net'].values if not full_tr.empty else np.array([])))

    months, neg, worst, worst_month = month_summary(full_tr, 'pnl_net')
    row['full_months'] = months
    row['full_neg_months'] = neg
    row['worst_month_sum'] = worst
    row['worst_month'] = worst_month

    recent_mask = recent_months_mask(full_tr, 3)
    row.update(metric_row('recent3m', full_tr.loc[recent_mask, 'pnl_net'].values if len(recent_mask) else np.array([])))

    for bucket, mask in vol_bucket_masks(full_tr, train_tr).items():
        row.update(metric_row(bucket, full_tr.loc[mask, 'pnl_net'].values if len(mask) else np.array([])))

    row['beats_old_pf_2_237'] = bool(
        row.get('train_n', 0) >= 50 and row.get('test_n', 0) >= 15 and row.get('full_n', 0) >= 100 and
        row.get('train_pf', 0) > BENCHMARK_PF and row.get('test_pf', 0) > BENCHMARK_PF and row.get('full_pf', 0) > BENCHMARK_PF
    )
    row['metric_scope'] = 'COST_ROBUSTNESS_AUDIT_ONLY'
    row['uses_future_results_for_gate'] = False
    row['health_gate_applied'] = False
    row['final_live_enabled'] = False
    return row


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--max-rules', type=int, default=100)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out177 = root / '177'
    out = root / '178'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage177 candidates')
    cand = read_csv_any(out177 / 'gold_v3_177_top100_rules.csv')
    if cand.empty:
        blockers.append({'id': 'missing_stage177_top100_rules', 'path': str(out177 / 'gold_v3_177_top100_rules.csv')})

    progress('load and combine OHLC with Stage177 gold_2025 contract')
    frames: dict[str, pd.DataFrame] = {}
    raw_diag_rows: list[dict[str, Any]] = []
    for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
        frames[tf], diag = s177.combine(tf, data_dir)
        raw_diag_rows.extend(diag)
    source_diag = pd.DataFrame(raw_diag_rows)
    save(source_diag, out / 'gold_v3_178_source_coverage.csv')

    for tf, df in frames.items():
        if df.empty:
            blockers.append({'id': 'missing_combined_ohlc', 'tf': tf})

    summary_rows: list[dict[str, Any]] = []
    robust = pd.DataFrame()
    if not blockers:
        progress('build OHLC-only features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        conds = s177.base.make_conditions(data)
        names = [x[0] for x in conds]
        masks = [x[1] for x in conds]
        rule_to_mask = {n: m for n, m in zip(names, masks)}

        for old_rank, (_, r) in enumerate(cand.head(args.max_rules).iterrows(), 1):
            rule = str(r.get('rule', ''))
            direction = str(r.get('direction', ''))
            tp = float(r.get('tp'))
            sl = float(r.get('sl'))
            horizon = int(r.get('horizon_m5'))
            mask = build_rule_mask(rule, rule_to_mask, len(data))
            entries = data.loc[mask].copy()
            if entries.empty:
                blockers.append({'id': 'rule_replay_empty', 'old_rank': old_rank, 'rule': rule})
                continue
            trades_raw = compute_outcome_with_exit(entries, frames['m5'], direction, tp, sl, horizon)
            trades_dedup = dedup_resolved_only(trades_raw)
            for cost in COST_SCENARIOS:
                summary_rows.append(evaluate_scope(trades_raw, 'raw', cost, old_rank, r))
                summary_rows.append(evaluate_scope(trades_dedup, 'dedup_resolved_only', cost, old_rank, r))

        if summary_rows:
            robust = pd.DataFrame(summary_rows)
            save(robust, out / 'gold_v3_178_cost_robustness_all.csv')
            ranked = robust.sort_values(
                ['beats_old_pf_2_237', 'scope', 'cost_points', 'full_pf', 'test_pf', 'train_pf', 'full_n'],
                ascending=[False, True, True, False, False, False, False],
            )
            save(ranked.head(300), out / 'gold_v3_178_cost_robustness_top300.csv')

    ready = len(blockers) == 0
    if not robust.empty:
        key = robust[(robust['scope'].eq('dedup_resolved_only')) & (robust['cost_points'].eq(3.0))].copy()
        key_beats = bool(key['beats_old_pf_2_237'].fillna(False).any()) if not key.empty else False
        best = key.sort_values(['full_pf', 'test_pf', 'train_pf', 'full_n'], ascending=[False, False, False, False]).head(1)
    else:
        key_beats = False
        best = pd.DataFrame()

    decision = 'STAGE178_BLOCKED' if not ready else ('STAGE178_DEDUP_COST3_BEATS_OLD_PF_NEEDS_MONTHLY_REVIEW' if key_beats else 'STAGE178_NO_DEDUP_COST3_CANDIDATE_BEATS_OLD_PF')
    best_full_pf = float(best.iloc[0].full_pf) if not best.empty else math.nan
    best_train_pf = float(best.iloc[0].train_pf) if not best.empty else math.nan
    best_test_pf = float(best.iloc[0].test_pf) if not best.empty else math.nan
    best_rule = str(best.iloc[0].rule) if not best.empty else ''
    best_neg_months = int(best.iloc[0].full_neg_months) if not best.empty else 0

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'old_pf_benchmark': BENCHMARK_PF,
        'cost_scenarios_points': COST_SCENARIOS,
        'input_stage177_top_rows': int(len(cand)) if not cand.empty else 0,
        'evaluated_rows': int(len(robust)) if not robust.empty else 0,
        'best_scope': 'dedup_resolved_only_cost3',
        'best_full_pf': best_full_pf,
        'best_train_pf': best_train_pf,
        'best_test_pf': best_test_pf,
        'best_full_neg_months': best_neg_months,
        'best_rule': best_rule,
        'dedup_cost3_beats_old_pf_2_237': key_beats,
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
    (out / 'gold_v3_178_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_178_decision.csv')

    top_key = robust[(robust['scope'].eq('dedup_resolved_only')) & (robust['cost_points'].eq(3.0))].copy() if not robust.empty else pd.DataFrame()
    if not top_key.empty:
        top_key = top_key.sort_values(['beats_old_pf_2_237', 'full_pf', 'test_pf', 'train_pf', 'full_n'], ascending=[False, False, False, False, False]).head(30)

    lines = ['GOLD V3 178 PASTE_ME_COST_SPREAD_SLIPPAGE_MONTHLY_ROBUSTNESS_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += ['', 'DEDUP_COST3_TOP30', top_key.to_string(index=False) if not top_key.empty else 'NO_DEDUP_COST3_TOP30']
    lines += [
        '',
        'INTERPRETATION',
        'Stage178 replays Stage177 OHLC-only candidates only. It does not create or remove the candidate pool. It reports raw and dedup_resolved_only scopes across fixed cost scenarios. Dedup accepts an entry only when the previous trade exit_dt is already resolved by that entry time. No health gate, live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
        'A candidate passing Stage178 is still audit-only. Next review must inspect monthly negatives, recent3m, low/mid/high volatility buckets, direction concentration, and whether PF survives realistic cost assumptions before any later gate design.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
