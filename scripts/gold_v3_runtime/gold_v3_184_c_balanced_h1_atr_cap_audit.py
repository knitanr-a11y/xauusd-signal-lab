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

STEP = 'GOLD_V3_184_C_BALANCED_H1_ATR_CAP_AUDIT_ONLY'
DEFAULT_COST_POINTS = 3.0
BENCHMARK_PF = 2.237
FOCUS_MONTH = '2026-02'
CANDIDATE = {
    'candidate_id': 'C_BALANCED',
    'rule': 'd1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008',
    'direction': 'LONG',
    'tp': 30.0,
    'sl': 30.0,
    'horizon_m5': 192,
}
DEFAULT_CAPS = [None, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0]


def progress(msg: str) -> None:
    print(f'[184 progress] {msg}', flush=True)


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
    return {f'{prefix}_n': n, f'{prefix}_sum': s, f'{prefix}_pf': pf, f'{prefix}_wr': wr, f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan}


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


def monthly_table(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    for month, g in trades.groupby('month', sort=True):
        n, s, pf, wr = pf_sum_wr(g['pnl_net'])
        rows.append({
            'month': month,
            'trades': n,
            'wins': int((g['pnl_net'] > 0).sum()),
            'losses': int((g['pnl_net'] < 0).sum()),
            'win_rate_pct': wr * 100.0,
            'pf': pf,
            'pnl_sum': s,
            'avg_pnl': s / n if n else math.nan,
            'tp_hits': int((g['hit_type'] == 'TP').sum()),
            'sl_hits': int((g['hit_type'] == 'SL').sum()),
            'horizon_exits': int((g['hit_type'] == 'HORIZON').sum()),
        })
    return pd.DataFrame(rows)


def replay_variant(data: pd.DataFrame, m5: pd.DataFrame, h1_atr14_cap: float | None, cost_points: float) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    mask, problems = s179.literal_rule_mask(CANDIDATE['rule'], data)
    if problems:
        raise RuntimeError(f'rule parse problems: {problems}')
    if h1_atr14_cap is not None:
        if 'h1_atr14' not in data.columns:
            raise RuntimeError('h1_atr14 column missing')
        mask = mask & (pd.to_numeric(data['h1_atr14'], errors='coerce') <= float(h1_atr14_cap))
    entries = data.loc[mask].copy()
    cap_label = 'NO_CAP' if h1_atr14_cap is None else f'h1_atr14_le_{h1_atr14_cap:g}'
    summary: dict[str, Any] = {
        'variant': cap_label,
        'candidate_id': CANDIDATE['candidate_id'],
        'rule': CANDIDATE['rule'],
        'h1_atr14_cap': '' if h1_atr14_cap is None else float(h1_atr14_cap),
        'direction': CANDIDATE['direction'],
        'tp': CANDIDATE['tp'],
        'sl': CANDIDATE['sl'],
        'horizon_m5': CANDIDATE['horizon_m5'],
        'entry_rows_before_dedup': int(len(entries)),
        'cost_points': float(cost_points),
    }
    if entries.empty:
        summary.update({'status': 'EMPTY', 'dedup_n': 0})
        return summary, pd.DataFrame(), pd.DataFrame()
    raw = s178.compute_outcome_with_exit(entries, m5, CANDIDATE['direction'], float(CANDIDATE['tp']), float(CANDIDATE['sl']), int(CANDIDATE['horizon_m5']))
    dedup = s178.dedup_resolved_only(raw)
    if dedup.empty:
        summary.update({'status': 'NO_DEDUP_TRADES', 'dedup_n': 0})
        return summary, raw, dedup
    dedup = dedup.copy()
    dedup['variant'] = cap_label
    dedup['pnl_net'] = pd.to_numeric(dedup['pnl_raw'], errors='coerce') - float(cost_points)
    dedup['month'] = pd.to_datetime(dedup['entry_dt']).dt.to_period('M').astype(str)
    train, test, full = split_trades(dedup)
    summary['dedup_n'] = int(len(dedup))
    summary.update(metric('train', train['pnl_net'] if not train.empty else np.array([])))
    summary.update(metric('test', test['pnl_net'] if not test.empty else np.array([])))
    summary.update(metric('full', full['pnl_net'] if not full.empty else np.array([])))
    summary.update(metric('recent3m', recent3m(full)['pnl_net'] if not full.empty else np.array([])))
    focus = full[full['month'].eq(FOCUS_MONTH)].copy()
    summary.update(metric('focus_2026_02', focus['pnl_net'] if not focus.empty else np.array([])))
    m = full.groupby('month')['pnl_net'].sum().sort_index() if not full.empty else pd.Series(dtype=float)
    summary['full_months'] = int(len(m))
    summary['full_neg_months'] = int((m < 0).sum()) if len(m) else 0
    summary['worst_month'] = str(m.idxmin()) if len(m) else ''
    summary['worst_month_sum'] = float(m.min()) if len(m) else math.nan
    summary['tp_hits'] = int((dedup['hit_type'] == 'TP').sum())
    summary['sl_hits'] = int((dedup['hit_type'] == 'SL').sum())
    summary['horizon_exits'] = int((dedup['hit_type'] == 'HORIZON').sum())
    summary['passes_core_review'] = bool(
        summary.get('train_n', 0) >= 50 and summary.get('test_n', 0) >= 15 and summary.get('full_n', 0) >= 100 and
        summary.get('train_pf', 0) > BENCHMARK_PF and summary.get('test_pf', 0) > BENCHMARK_PF and summary.get('full_pf', 0) > BENCHMARK_PF and
        summary.get('recent3m_pf', 0) > BENCHMARK_PF and summary.get('full_neg_months', 99) <= 0
    )
    summary['status'] = 'OK'
    monthly = monthly_table(dedup)
    if not monthly.empty:
        monthly.insert(0, 'variant', cap_label)
    return summary, raw, dedup


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--cost-points', type=float, default=DEFAULT_COST_POINTS)
    ap.add_argument('--caps', default='')
    args = ap.parse_args()

    caps: list[float | None]
    if args.caps.strip():
        caps = [None]
        for part in args.caps.split(','):
            part = part.strip()
            if part:
                caps.append(float(part))
    else:
        caps = DEFAULT_CAPS

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '184'
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
        save(source_diag, out / 'gold_v3_184_source_coverage.csv')

    summary_df = pd.DataFrame()
    monthly_all = pd.DataFrame()
    trades_all = pd.DataFrame()
    if not blockers:
        progress('build features')
        data = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1'])
        rows = []
        monthly_rows = []
        trade_rows = []
        for cap in caps:
            progress(f'evaluate cap={cap}')
            row, _raw, dedup = replay_variant(data, frames['m5'], cap, float(args.cost_points))
            rows.append(row)
            if not dedup.empty:
                trade_rows.append(dedup)
                mt = monthly_table(dedup)
                if not mt.empty:
                    mt.insert(0, 'variant', row['variant'])
                    monthly_rows.append(mt)
        summary_df = pd.DataFrame(rows)
        monthly_all = pd.concat(monthly_rows, ignore_index=True) if monthly_rows else pd.DataFrame()
        trades_all = pd.concat(trade_rows, ignore_index=True) if trade_rows else pd.DataFrame()
        save(summary_df, out / 'gold_v3_184_h1_atr_cap_summary.csv')
        save(monthly_all, out / 'gold_v3_184_monthly_by_cap.csv')
        save(trades_all, out / 'gold_v3_184_trades_by_cap.csv')

    ready = len(blockers) == 0
    selectable = summary_df[(summary_df.get('status', '') == 'OK') & (summary_df.get('passes_core_review', False).astype(bool))].copy() if not summary_df.empty else pd.DataFrame()
    if not selectable.empty:
        selectable = selectable.sort_values(['focus_2026_02_pf', 'full_n', 'test_pf', 'recent3m_pf'], ascending=[False, False, False, False])
        best = selectable.iloc[0].to_dict()
    else:
        best = {}

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE184_C_BALANCED_H1_ATR_CAP_REVIEW_READY_AUDIT_ONLY' if ready else 'STAGE184_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'candidate_id': CANDIDATE['candidate_id'],
        'base_rule': CANDIDATE['rule'],
        'cost_points': float(args.cost_points),
        'tested_caps': ['NO_CAP' if c is None else c for c in caps],
        'variant_rows': int(len(summary_df)) if not summary_df.empty else 0,
        'passes_core_review_rows': int(len(selectable)) if not selectable.empty else 0,
        'best_variant': str(best.get('variant', '')),
        'best_full_n': int(best.get('full_n', 0)) if best else 0,
        'best_full_pf': float(best.get('full_pf', math.nan)) if best else math.nan,
        'best_test_pf': float(best.get('test_pf', math.nan)) if best else math.nan,
        'best_recent3m_pf': float(best.get('recent3m_pf', math.nan)) if best else math.nan,
        'best_focus_2026_02_pf': float(best.get('focus_2026_02_pf', math.nan)) if best else math.nan,
        'best_focus_2026_02_n': int(best.get('focus_2026_02_n', 0)) if best else 0,
        'best_full_neg_months': int(best.get('full_neg_months', 0)) if best else 0,
        'time_basis': 'CSV/MT5 timestamp hour; no JST conversion is applied in this audit.',
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
    (out / 'gold_v3_184_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_184_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    show_cols = [
        'variant', 'h1_atr14_cap', 'entry_rows_before_dedup', 'dedup_n', 'train_n', 'train_pf', 'train_wr_pct',
        'test_n', 'test_pf', 'test_wr_pct', 'full_n', 'full_pf', 'full_wr_pct', 'recent3m_n', 'recent3m_pf',
        'focus_2026_02_n', 'focus_2026_02_pf', 'focus_2026_02_wr_pct', 'focus_2026_02_sum',
        'full_neg_months', 'worst_month', 'worst_month_sum', 'tp_hits', 'sl_hits', 'horizon_exits', 'passes_core_review'
    ]
    summary_show = summary_df[[c for c in show_cols if c in summary_df.columns]].copy() if not summary_df.empty else pd.DataFrame()
    if not summary_show.empty:
        summary_show = summary_show.sort_values(['passes_core_review', 'focus_2026_02_pf', 'full_n'], ascending=[False, False, False])

    month_show = monthly_all[monthly_all['month'].isin(['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06'])].copy() if not monthly_all.empty else pd.DataFrame()

    lines = ['GOLD V3 184 PASTE_ME_C_BALANCED_H1_ATR_CAP_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'CAP_SUMMARY', show(summary_show, 40)]
    lines += ['', 'MONTHLY_2026_BY_CAP', show(month_show, 120)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage184 is audit-only. It tests C_BALANCED plus an entry-time h1_atr14 upper cap. h1_atr14 is an OHLC-derived feature available at the entry decision time when computed from closed candles. M5 future outcomes are used only for audit scoring, not as entry gates.',
        'Hour/time fields in prior Stage183 are CSV/MT5 timestamps. No JST conversion is applied unless a later stage explicitly implements it.',
        'Do not accept a cap only because it fixes 2026-02. A useful cap must preserve full/test/recent3m PF, trade count, and zero negative months across the full audit period.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
