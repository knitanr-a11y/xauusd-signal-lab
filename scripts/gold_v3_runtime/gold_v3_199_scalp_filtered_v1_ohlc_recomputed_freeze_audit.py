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

STEP = 'GOLD_V3_199_SCALP_FILTERED_V1_OHLC_RECOMPUTED_FREEZE_AUDIT_ONLY'
PRIMARY_COST = 3.0
STRESS_COST = 5.0
FILTERED_SCALP_ID = 'SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED'
FILTER_CANDIDATE_ID = 'SCALP_002_tp15_sl5_hz64_SHORT'
FILTER_EXCLUDED_HOUR = 9
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
    print(f'[199 progress] {msg}', flush=True)


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


def add_time_cols(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if x.empty:
        return x
    x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    if 'exit_dt' in x.columns:
        x['exit_dt'] = pd.to_datetime(x['exit_dt'])
    x = x.sort_values(['entry_dt', 'candidate_id'] if 'candidate_id' in x.columns else ['entry_dt']).reset_index(drop=True)
    x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    x['entry_date'] = x['entry_dt'].dt.date.astype(str)
    x['entry_hour'] = x['entry_dt'].dt.hour.astype(int)
    if 'pnl_net_cost3' not in x.columns and 'pnl_raw' in x.columns:
        x['pnl_net_cost3'] = pd.to_numeric(x['pnl_raw'], errors='coerce') - PRIMARY_COST
    if 'pnl_net_cost5' not in x.columns:
        if 'pnl_raw' in x.columns:
            x['pnl_net_cost5'] = pd.to_numeric(x['pnl_raw'], errors='coerce') - STRESS_COST
        elif 'pnl_net_cost3' in x.columns:
            x['pnl_net_cost5'] = pd.to_numeric(x['pnl_net_cost3'], errors='coerce') - (STRESS_COST - PRIMARY_COST)
    return x


def pf_sum_wr(pnl: pd.Series | np.ndarray) -> tuple[int, float, float, float, float, float, float]:
    s = pd.to_numeric(pd.Series(pnl), errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
    n = int(len(s))
    if n == 0:
        return 0, 0.0, math.nan, math.nan, math.nan, 0.0, 0.0
    gp = float(s[s > 0].sum())
    gl = float(-s[s < 0].sum())
    pf = gp / gl if gl > 0 else (math.inf if gp > 0 else 0.0)
    wr = float((s > 0).mean())
    avg = float(s.mean())
    return n, float(s.sum()), pf, wr, avg, gp, gl


def split_trades(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy(), df.copy(), df.copy()
    x = add_time_cols(df)
    dt = x['entry_dt']
    train = x[(dt >= pd.Timestamp('2025-01-02')) & (dt < pd.Timestamp('2026-01-01'))].copy()
    test = x[dt >= pd.Timestamp('2026-01-01')].copy()
    full = x[dt >= pd.Timestamp('2025-01-02')].copy()
    recent = full[full['month'].astype(str).isin(sorted(full['month'].astype(str).unique())[-3:])].copy() if not full.empty else full.copy()
    return train, test, full, recent


def metric(prefix: str, df: pd.DataFrame, pnl_col: str) -> dict[str, Any]:
    n, s, pf, wr, avg, gp, gl = pf_sum_wr(df[pnl_col] if not df.empty and pnl_col in df.columns else [])
    return {
        f'{prefix}_n': n,
        f'{prefix}_sum': s,
        f'{prefix}_pf': pf,
        f'{prefix}_wr_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
        f'{prefix}_avg': avg,
        f'{prefix}_gross_profit': gp,
        f'{prefix}_gross_loss': gl,
    }


def evaluate(df: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> dict[str, Any]:
    train, test, full, recent = split_trades(df)
    out: dict[str, Any] = {}
    out.update(metric('train', train, pnl_col))
    out.update(metric('test', test, pnl_col))
    out.update(metric('full', full, pnl_col))
    out.update(metric('recent3m', recent, pnl_col))
    if full.empty:
        out.update({'full_months': 0, 'full_neg_months': 0, 'worst_month': '', 'worst_month_sum': math.nan})
    else:
        m = full.groupby('month')[pnl_col].sum().sort_index()
        out.update({'full_months': int(len(m)), 'full_neg_months': int((m < 0).sum()), 'worst_month': str(m.idxmin()), 'worst_month_sum': float(m.min())})
    for month in DAILY_FOCUS_MONTHS:
        g = full[full['month'].astype(str).eq(month)] if not full.empty else full
        n, s, pf, wr, avg, gp, gl = pf_sum_wr(g[pnl_col] if not g.empty and pnl_col in g.columns else [])
        key = month.replace('-', '_')
        out[f'{key}_n'] = n
        out[f'{key}_sum'] = s
        out[f'{key}_pf'] = pf
        out[f'{key}_wr_pct'] = wr * 100.0 if math.isfinite(wr) else math.nan
    return out


def monthly_table(df: pd.DataFrame, portfolio_id: str, pnl_col: str = 'pnl_net_cost3') -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    x = add_time_cols(df)
    rows = []
    for month, g in x.groupby('month', sort=True):
        n, s, pf, wr, avg, gp, gl = pf_sum_wr(g[pnl_col])
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


def daily_table(df: pd.DataFrame, portfolio_id: str, pnl_col: str = 'pnl_net_cost3') -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    x = add_time_cols(df)
    x = x[x['month'].astype(str).isin(DAILY_FOCUS_MONTHS)].copy()
    rows = []
    for day, g in x.groupby('entry_date', sort=True):
        n, s, pf, wr, avg, gp, gl = pf_sum_wr(g[pnl_col])
        rows.append({
            'portfolio_id': portfolio_id,
            'entry_date': day,
            'month': str(pd.Timestamp(day).to_period('M')),
            'trades': n,
            'unique_entry_times': int(g['entry_dt'].nunique()),
            'pnl_sum': s,
            'pf': pf,
            'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
            'avg_net': avg,
            'candidate_counts': json.dumps(g['candidate_id'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'candidate_id' in g.columns else '{}',
            'direction_counts': json.dumps(g['direction'].astype(str).value_counts().to_dict(), ensure_ascii=False) if 'direction' in g.columns else '{}',
        })
    return pd.DataFrame(rows)


def selected_priority(selected: pd.DataFrame) -> dict[str, float]:
    s = selected.copy().reset_index(drop=True)
    if 'profit_rate_score' in s.columns:
        return dict(zip(s['candidate_id'].astype(str), pd.to_numeric(s['profit_rate_score'], errors='coerce').fillna(0.0)))
    if 'selected_order' in s.columns:
        return {str(r['candidate_id']): 1000.0 - float(r['selected_order']) for _, r in s.iterrows()}
    return {str(cid): 1000.0 - i for i, cid in enumerate(s['candidate_id'].astype(str).tolist())}


def resolved_priority(df: pd.DataFrame, priority: dict[str, float]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = add_time_cols(df)
    x['priority_score'] = x['candidate_id'].astype(str).map(priority).fillna(0.0)
    x = x.sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).reset_index(drop=True)
    kept = []
    used_entry_times: set[pd.Timestamp] = set()
    active_exit: pd.Timestamp | None = None
    for _, r in x.iterrows():
        entry = pd.Timestamp(r['entry_dt'])
        if entry in used_entry_times:
            continue
        if active_exit is not None and entry < active_exit:
            continue
        kept.append(r)
        used_entry_times.add(entry)
        active_exit = pd.Timestamp(r['exit_dt']) if 'exit_dt' in r and not pd.isna(r['exit_dt']) else entry
    return pd.DataFrame(kept).reset_index(drop=True) if kept else x.iloc[0:0].copy()


def apply_filtered_v1(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = add_time_cols(df)
    removed = x['candidate_id'].astype(str).eq(FILTER_CANDIDATE_ID) & x['entry_hour'].eq(FILTER_EXCLUDED_HOUR)
    return x[~removed].copy().reset_index(drop=True), x[removed].copy().reset_index(drop=True)


def build_scalp_detector_entries(feat: pd.DataFrame, selected: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows = []
    problems: list[dict[str, Any]] = []
    for _, c in selected.iterrows():
        cid = str(c['candidate_id'])
        rule = str(c.get('rule', '')).strip()
        if not rule:
            problems.append({'candidate_id': cid, 'problem': 'missing_rule'})
            continue
        mask, rule_problems = s179.literal_rule_mask(rule, feat)
        if rule_problems:
            problems.append({'candidate_id': cid, 'problem': 'rule_parse', 'details': rule_problems})
            continue
        m = feat.loc[mask, ['dt', 'm15_close', 'h1_atr14']].copy()
        if m.empty:
            continue
        m = m.rename(columns={'dt': 'entry_dt', 'm15_close': 'entry_price'})
        m['candidate_id'] = cid
        m['profile_id'] = str(c.get('profile_id', ''))
        m['direction'] = str(c.get('direction', ''))
        m['tp'] = float(c.get('tp', math.nan))
        m['sl'] = float(c.get('sl', math.nan))
        m['horizon_m5'] = int(float(c.get('horizon_m5', 0)))
        m['rule'] = rule
        m['family'] = FILTERED_SCALP_ID
        rows.append(m)
    det = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return add_time_cols(det) if not det.empty else det, problems


def recompute_scalp_outcomes(detector_entries: pd.DataFrame, m5: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    if detector_entries.empty:
        return pd.DataFrame()
    out = []
    for _, c in selected.iterrows():
        cid = str(c['candidate_id'])
        sub = detector_entries[detector_entries['candidate_id'].astype(str).eq(cid)].copy()
        if sub.empty:
            continue
        entries = sub.rename(columns={'entry_dt': 'dt', 'entry_price': 'm15_close'})[['dt', 'm15_close', 'h1_atr14']].copy()
        scored = s178.compute_outcome_with_exit(entries, m5, str(c.get('direction', '')), float(c.get('tp', math.nan)), float(c.get('sl', math.nan)), int(float(c.get('horizon_m5', 0))))
        if scored.empty:
            continue
        scored['candidate_id'] = cid
        scored['profile_id'] = str(c.get('profile_id', ''))
        scored['rule'] = str(c.get('rule', ''))
        scored['family'] = FILTERED_SCALP_ID
        scored['pnl_net_cost3'] = pd.to_numeric(scored['pnl_raw'], errors='coerce') - PRIMARY_COST
        scored['pnl_net_cost5'] = pd.to_numeric(scored['pnl_raw'], errors='coerce') - STRESS_COST
        out.append(scored)
    return add_time_cols(pd.concat(out, ignore_index=True)) if out else pd.DataFrame()


def build_abc(feat: pd.DataFrame, m5: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    trade_frames = []
    for c in ABC_CANDIDATES:
        mask, problems = s179.literal_rule_mask(c['rule'], feat)
        if problems:
            blockers.append({'id': 'abc_rule_problem', 'candidate_id': c['candidate_id'], 'problems': problems})
            continue
        entries = feat.loc[mask, ['dt', 'm15_close', 'h1_atr14']].copy()
        raw = s178.compute_outcome_with_exit(entries, m5, c['direction'], float(c['tp']), float(c['sl']), int(c['horizon_m5']))
        if raw.empty:
            continue
        raw['candidate_id'] = c['candidate_id']
        raw['family'] = 'ABC'
        raw['rule'] = c['rule']
        raw['priority_order'] = c['priority']
        raw['pnl_net_cost3'] = pd.to_numeric(raw['pnl_raw'], errors='coerce') - PRIMARY_COST
        raw['pnl_net_cost5'] = pd.to_numeric(raw['pnl_raw'], errors='coerce') - STRESS_COST
        trade_frames.append(s178.dedup_resolved_only(raw))
    if not trade_frames:
        blockers.append({'id': 'abc_trades_empty'})
        return pd.DataFrame(), blockers
    abc_all = pd.concat(trade_frames, ignore_index=True)
    priority = {c['candidate_id']: 5000.0 - float(c['priority']) for c in ABC_CANDIDATES}
    return resolved_priority(abc_all, priority), blockers


def latest_snapshot(feat: pd.DataFrame, selected: pd.DataFrame, priority: dict[str, float]) -> tuple[pd.DataFrame, dict[str, Any]]:
    det, _ = build_scalp_detector_entries(feat, selected)
    if det.empty:
        tail = feat[['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].tail(96).copy()
        tail['priority_signal'] = 'NO_SIGNAL'
        tail['candidate_id'] = ''
        return tail, tail.iloc[-1].to_dict() if not tail.empty else {}
    det_f, _ = apply_filtered_v1(det)
    det_f['priority_score'] = det_f['candidate_id'].astype(str).map(priority).fillna(0.0)
    tail = feat[['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].tail(96).copy()
    picked = det_f[det_f['entry_dt'].isin(set(pd.to_datetime(tail['dt'])))].sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).drop_duplicates('entry_dt', keep='first')
    merged = tail.merge(picked[['entry_dt', 'candidate_id', 'direction', 'tp', 'sl', 'horizon_m5', 'priority_score']].rename(columns={'entry_dt': 'dt'}), on='dt', how='left')
    merged['priority_signal'] = np.where(merged['candidate_id'].notna(), merged['direction'].astype(str), 'NO_SIGNAL')
    return merged, merged.iloc[-1].to_dict() if not merged.empty else {}


def overlap_report(abc: pd.DataFrame, scalp_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if abc.empty or scalp_raw.empty:
        return pd.DataFrame(), pd.DataFrame()
    a = add_time_cols(abc)
    s = add_time_cols(scalp_raw)
    exact = s.merge(a[['entry_dt', 'exit_dt', 'candidate_id', 'direction']].rename(columns={'exit_dt': 'abc_exit_dt', 'candidate_id': 'abc_candidate_id', 'direction': 'abc_direction'}), on='entry_dt', how='inner')
    rows = []
    a_small = a[['entry_dt', 'exit_dt', 'candidate_id', 'direction']].sort_values('entry_dt').reset_index(drop=True)
    for _, sr in s.iterrows():
        st = pd.Timestamp(sr['entry_dt'])
        hits = a_small[(a_small['entry_dt'] <= st) & (a_small['exit_dt'] > st)]
        for _, ar in hits.iterrows():
            rows.append({
                'scalp_entry_dt': st,
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
    return exact, pd.DataFrame(rows)


def compare_stage197(stage197_summary: pd.DataFrame, portfolio_summary: pd.DataFrame) -> pd.DataFrame:
    if stage197_summary.empty or portfolio_summary.empty:
        return pd.DataFrame()
    out = []
    def get199(pid: str, col: str) -> float:
        hit = portfolio_summary[portfolio_summary['portfolio_id'].astype(str).eq(pid)]
        if hit.empty or col not in hit.columns:
            return math.nan
        return num(hit[col].iloc[0], math.nan)
    s197 = stage197_summary.iloc[0]
    rows = [
        ('scalp_full_sum_cost3', num(s197.get('scalp_filtered_full_sum_cost3'), math.nan), get199('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_sum')),
        ('scalp_full_pf_cost3', num(s197.get('scalp_filtered_full_pf_cost3'), math.nan), get199('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_pf')),
        ('scalp_full_n_cost3', num(s197.get('scalp_filtered_v1_one_position_n'), math.nan), get199('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_n')),
        ('combined_abc_first_full_sum_cost3', num(s197.get('combined_abc_first_full_sum_cost3'), math.nan), get199('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_sum')),
        ('combined_abc_first_full_pf_cost3', num(s197.get('combined_abc_first_full_pf_cost3'), math.nan), get199('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_pf')),
    ]
    for name, old, new in rows:
        out.append({'metric': name, 'stage197_artifact_based': old, 'stage199_ohlc_recomputed': new, 'delta_199_minus_197': new - old if math.isfinite(old) and math.isfinite(new) else math.nan})
    return pd.DataFrame(out)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '199'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load selected candidates and OHLC')
    selected = read_csv_any(root / '193' / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_watchlist'})
    frames: dict[str, pd.DataFrame] = {}
    source_rows: list[dict[str, Any]] = []
    if not blockers:
        for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
            frames[tf], diag = s177.combine(tf, data_dir)
            source_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({'id': 'missing_ohlc', 'tf': tf})
        if source_rows:
            save(pd.DataFrame(source_rows), out / 'gold_v3_199_source_coverage.csv')

    scalp_detector = pd.DataFrame()
    scalp_raw = pd.DataFrame()
    scalp_raw_filtered = pd.DataFrame()
    scalp_removed = pd.DataFrame()
    scalp_one = pd.DataFrame()
    abc = pd.DataFrame()
    combined_abc_first = pd.DataFrame()
    combined_scalp_first = pd.DataFrame()
    portfolio_summary = pd.DataFrame()
    monthly = pd.DataFrame()
    daily = pd.DataFrame()
    latest_tail = pd.DataFrame()
    latest_info: dict[str, Any] = {}
    exact_overlap = pd.DataFrame()
    active_overlap = pd.DataFrame()
    stage197_compare = pd.DataFrame()
    detector_problems: list[dict[str, Any]] = []

    if not blockers:
        progress('build OHLC features')
        feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
        progress('recompute SCALP_FILTERED_V1 from closed OHLC')
        scalp_detector, detector_problems = build_scalp_detector_entries(feat, selected)
        if detector_problems:
            blockers.append({'id': 'scalp_detector_rule_problems', 'count': len(detector_problems), 'details': detector_problems[:5]})
        else:
            scalp_raw = recompute_scalp_outcomes(scalp_detector, frames['m5'], selected)
            scalp_raw_filtered, scalp_removed = apply_filtered_v1(scalp_raw)
            priority = selected_priority(selected)
            scalp_one = resolved_priority(scalp_raw_filtered, priority)
            for df in [scalp_detector, scalp_raw, scalp_raw_filtered, scalp_removed, scalp_one]:
                if not df.empty:
                    df['family'] = FILTERED_SCALP_ID
            save(scalp_detector, out / 'gold_v3_199_scalp_detector_entries_before_filter.csv')
            save(scalp_raw, out / 'gold_v3_199_scalp_ohlc_recomputed_scored_before_filter.csv')
            save(scalp_raw_filtered, out / 'gold_v3_199_scalp_ohlc_recomputed_scored_after_filtered_v1.csv')
            save(scalp_removed, out / 'gold_v3_199_scalp_ohlc_recomputed_removed_by_filtered_v1.csv')
            save(scalp_one, out / 'gold_v3_199_scalp_filtered_v1_ohlc_recomputed_one_position.csv')

            progress('rebuild ABC and combined portfolios')
            abc, b = build_abc(feat, frames['m5'])
            blockers.extend(b)
            if not blockers:
                save(abc, out / 'gold_v3_199_abc_portfolio_rebuilt.csv')
                abc_priority = {c['candidate_id']: 5000.0 - float(c['priority']) for c in ABC_CANDIDATES}
                scalp_low = {cid: 2000.0 + score for cid, score in priority.items()}
                scalp_high = {cid: 6000.0 + score for cid, score in priority.items()}
                combined_raw = pd.concat([abc, scalp_raw_filtered], ignore_index=True)
                combined_abc_first = resolved_priority(combined_raw, {**scalp_low, **abc_priority})
                combined_scalp_first = resolved_priority(combined_raw, {**abc_priority, **scalp_high})
                save(combined_raw, out / 'gold_v3_199_combined_raw_abc_plus_ohlc_scalp.csv')
                save(combined_abc_first, out / 'gold_v3_199_combined_abc_priority_first_ohlc_scalp.csv')
                save(combined_scalp_first, out / 'gold_v3_199_combined_scalp_priority_first_ohlc_scalp.csv')
                exact_overlap, active_overlap = overlap_report(abc, scalp_raw_filtered)
                save(exact_overlap, out / 'gold_v3_199_exact_entry_overlap_abc_ohlc_scalp.csv')
                save(active_overlap, out / 'gold_v3_199_active_window_overlap_abc_ohlc_scalp.csv')

                rows = []
                portfolios = {
                    'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3': scalp_one,
                    'ABC_ONLY_COST3': abc,
                    'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3': combined_abc_first,
                    'COMBINED_SCALP_PRIORITY_FIRST_OHLC_SCALP_COST3': combined_scalp_first,
                    'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST5': scalp_one,
                    'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5': combined_abc_first,
                }
                for name, df in portfolios.items():
                    pnl_col = 'pnl_net_cost5' if name.endswith('COST5') else 'pnl_net_cost3'
                    row = {'portfolio_id': name, 'pnl_col': pnl_col}
                    row.update(evaluate(df, pnl_col))
                    rows.append(row)
                portfolio_summary = pd.DataFrame(rows)
                save(portfolio_summary, out / 'gold_v3_199_portfolio_summary_cost3_cost5.csv')

                monthly_frames = []
                daily_frames = []
                for name, df in [
                    ('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', scalp_one),
                    ('ABC_ONLY_COST3', abc),
                    ('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', combined_abc_first),
                ]:
                    monthly_frames.append(monthly_table(df, name, 'pnl_net_cost3'))
                    daily_frames.append(daily_table(df, name, 'pnl_net_cost3'))
                monthly = pd.concat([m for m in monthly_frames if not m.empty], ignore_index=True) if monthly_frames else pd.DataFrame()
                daily = pd.concat([d for d in daily_frames if not d.empty], ignore_index=True) if daily_frames else pd.DataFrame()
                save(monthly, out / 'gold_v3_199_monthly_summary_cost3.csv')
                save(daily, out / 'gold_v3_199_daily_counts_2026_05_06_cost3.csv')

                latest_tail, latest_info = latest_snapshot(feat, selected, priority)
                save(latest_tail, out / 'gold_v3_199_latest_detector_tail96.csv')

                stage197_summary = read_csv_any(root / '197' / 'gold_v3_197_decision.csv')
                stage197_compare = compare_stage197(stage197_summary, portfolio_summary)
                save(stage197_compare, out / 'gold_v3_199_compare_against_stage197_artifact_based.csv')

                handoff_lines = [
                    '# GOLD V3 Stage199 SCALP FILTERED V1 OHLC Recomputed Handoff',
                    '',
                    f'Decision: STAGE199_SCALP_FILTERED_V1_OHLC_RECOMPUTED_FREEZE_READY_AUDIT_ONLY',
                    '',
                    '## Status',
                    '- Audit-only',
                    '- ABC remains PRIMARY',
                    '- SCALP_FILTERED_V1_OHLC_RECOMPUTED remains SECONDARY/WATCHLIST until explicit approval',
                    '- Discord / MT5 order / payload / AI API / live hook / autotrade remain OFF',
                    '',
                    '## SCALP_FILTERED_V1 definition',
                    '- Build selected Stage193 scalp candidate entries from closed M15/H1/H4/D1 OHLC features.',
                    '- Exclude SCALP_002_tp15_sl5_hz64_SHORT when MT5 entry_hour == 09.',
                    '- Score outcomes with M5 OHLC after entry for audit only.',
                    '- Resolve to one active scalp position by priority.',
                    '',
                    '## Next suggested stage',
                    'Stage200: audit-only no-send preview packet for ABC PRIMARY + SCALP_FILTERED_V1 SECONDARY, or final handoff/checklist before any notification discussion.',
                ]
                (out / 'gold_v3_199_handoff.md').write_text('\n'.join(handoff_lines) + '\n', encoding='utf-8')

    def get_summary(pid: str, col: str, default: Any = math.nan) -> Any:
        if portfolio_summary.empty:
            return default
        hit = portfolio_summary[portfolio_summary['portfolio_id'].astype(str).eq(pid)]
        if hit.empty or col not in hit.columns:
            return default
        return hit[col].iloc[0]

    ready = len(blockers) == 0
    decision = 'STAGE199_SCALP_FILTERED_V1_OHLC_RECOMPUTED_FREEZE_READY_AUDIT_ONLY' if ready else 'STAGE199_BLOCKED'
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'filtered_scalp_id': FILTERED_SCALP_ID,
        'filter_rule': f'{FILTER_CANDIDATE_ID} excluded when MT5 entry_hour == {FILTER_EXCLUDED_HOUR}',
        'primary_cost_points': PRIMARY_COST,
        'stress_cost_points': STRESS_COST,
        'selected_candidate_count': int(len(selected)) if not selected.empty else 0,
        'scalp_detector_rows_before_filter': int(len(scalp_detector)) if not scalp_detector.empty else 0,
        'scalp_raw_recomputed_rows_before_filter': int(len(scalp_raw)) if not scalp_raw.empty else 0,
        'scalp_raw_recomputed_rows_after_filter': int(len(scalp_raw_filtered)) if not scalp_raw_filtered.empty else 0,
        'scalp_removed_by_filter_rows': int(len(scalp_removed)) if not scalp_removed.empty else 0,
        'scalp_one_position_rows': int(len(scalp_one)) if not scalp_one.empty else 0,
        'scalp_full_sum_cost3': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_sum')),
        'scalp_full_pf_cost3': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_pf')),
        'scalp_full_neg_months_cost3': int(num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_neg_months'))),
        'scalp_test_sum_cost3': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'test_sum')),
        'scalp_recent3m_sum_cost3': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'recent3m_sum')),
        'scalp_2026_05_sum_cost3': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', '2026_05_sum')),
        'scalp_2026_06_sum_cost3': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', '2026_06_sum')),
        'scalp_full_sum_cost5': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST5', 'full_sum')),
        'scalp_full_pf_cost5': num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST5', 'full_pf')),
        'scalp_full_neg_months_cost5': int(num(get_summary('SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST5', 'full_neg_months'))),
        'abc_full_sum_cost3': num(get_summary('ABC_ONLY_COST3', 'full_sum')),
        'abc_full_pf_cost3': num(get_summary('ABC_ONLY_COST3', 'full_pf')),
        'combined_abc_first_full_n_cost3': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_n'))),
        'combined_abc_first_full_sum_cost3': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_sum')),
        'combined_abc_first_full_pf_cost3': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_pf')),
        'combined_abc_first_full_neg_months_cost3': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_neg_months'))),
        'combined_abc_first_full_sum_cost5': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', 'full_sum')),
        'combined_abc_first_full_pf_cost5': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', 'full_pf')),
        'combined_abc_first_full_neg_months_cost5': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', 'full_neg_months'))),
        'exact_entry_overlap_count': int(len(exact_overlap)) if not exact_overlap.empty else 0,
        'active_window_overlap_count': int(len(active_overlap)) if not active_overlap.empty else 0,
        'active_window_direction_conflict_count': int(active_overlap['direction_conflict'].sum()) if not active_overlap.empty and 'direction_conflict' in active_overlap.columns else 0,
        'latest_closed_m15_dt': str(latest_info.get('dt', '')) if latest_info else '',
        'latest_scalp_priority_signal': str(latest_info.get('priority_signal', 'NO_SIGNAL')) if latest_info else 'NO_SIGNAL',
        'latest_scalp_candidate_id': '' if str(latest_info.get('candidate_id', '')) == 'nan' else str(latest_info.get('candidate_id', '')) if latest_info else '',
        'recent_tail96_signal_rows': int((latest_tail.get('priority_signal', pd.Series(dtype=str)).astype(str) != 'NO_SIGNAL').sum()) if not latest_tail.empty else 0,
        'stage198_ohlc_reproducibility_basis': 'Stage198 detector_vs_recomputed_parity_pass was True. Stage199 therefore uses OHLC-recomputed rows as the comparison basis.',
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'Entry detector uses closed OHLC-derived features and MT5 hour filter only. M5 future TP/SL/horizon is used only after entry for audit scoring.',
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
    (out / 'gold_v3_199_summary.json').write_text(json.dumps({**summary, 'blockers': blockers, 'detector_problems': detector_problems}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_199_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 199 PASTE_ME_SCALP_FILTERED_V1_OHLC_RECOMPUTED_FREEZE_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PORTFOLIO_SUMMARY_COST3_COST5', show(portfolio_summary, 20)]
    lines += ['', 'MONTHLY_SUMMARY_COST3', show(monthly, 120)]
    lines += ['', 'DAILY_COUNTS_2026_05_06_COST3', show(daily, 160)]
    lines += ['', 'SCALP_OHLC_REMOVED_BY_FILTERED_V1', show(scalp_removed, 60)]
    lines += ['', 'COMPARE_AGAINST_STAGE197_ARTIFACT_BASED', show(stage197_compare, 20)]
    lines += ['', 'LATEST_DETECTOR_TAIL96', show(latest_tail, 120)]
    lines += ['', 'ACTIVE_WINDOW_OVERLAP_SAMPLE', show(active_overlap, 60)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage199 is audit-only. It promotes the Stage198 OHLC-recomputed route to the audit comparison basis for SCALP_FILTERED_V1 review.',
        'ABC remains PRIMARY. SCALP_FILTERED_V1_OHLC_RECOMPUTED remains SECONDARY/WATCHLIST until explicit later approval.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
