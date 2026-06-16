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

STEP = 'GOLD_V3_197_SCALP_ONE_POSITION_FILTERED_V1_FREEZE_AUDIT_ONLY'
PRIMARY_COST = 3.0
STRESS_COST = 5.0
FILTERED_SCALP_ID = 'SCALP_ONE_POSITION_FILTERED_V1'
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
    print(f'[197 progress] {msg}', flush=True)


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
    x = x.sort_values('entry_dt').reset_index(drop=True)
    x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    x['entry_date'] = x['entry_dt'].dt.date.astype(str)
    x['entry_hour'] = x['entry_dt'].dt.hour.astype(int)
    x['entry_weekday'] = x['entry_dt'].dt.day_name()
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
    if full.empty:
        recent = full.copy()
    else:
        months = sorted(full['month'].astype(str).unique())
        recent = full[full['month'].astype(str).isin(set(months[-3:]))].copy()
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


def selected_priority(selected: pd.DataFrame) -> dict[str, float]:
    s = selected.copy().reset_index(drop=True)
    if 'profit_rate_score' in s.columns:
        return dict(zip(s['candidate_id'].astype(str), pd.to_numeric(s['profit_rate_score'], errors='coerce').fillna(0.0)))
    if 'selected_order' in s.columns:
        return {str(r['candidate_id']): 1000.0 - float(r['selected_order']) for _, r in s.iterrows()}
    return {str(cid): 1000.0 - i for i, cid in enumerate(s['candidate_id'].astype(str).tolist())}


def apply_filtered_v1(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = add_time_cols(raw)
    x['filtered_v1_removed'] = x['candidate_id'].astype(str).eq(FILTER_CANDIDATE_ID) & x['entry_hour'].eq(FILTER_EXCLUDED_HOUR)
    removed = x[x['filtered_v1_removed']].copy()
    kept = x[~x['filtered_v1_removed']].copy()
    return kept.reset_index(drop=True), removed.reset_index(drop=True)


def build_abc(data_dir: Path, out: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
        frames[tf], diag = s177.combine(tf, data_dir)
        rows.extend(diag)
        if frames[tf].empty:
            blockers.append({'id': 'missing_ohlc', 'tf': tf})
    source_diag = pd.DataFrame(rows)
    if not source_diag.empty:
        save(source_diag, out / 'gold_v3_197_source_coverage.csv')
    if blockers:
        return pd.DataFrame(), source_diag, blockers
    feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
    trade_frames = []
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
        trade_frames.append(s178.dedup_resolved_only(raw))
    if not trade_frames:
        blockers.append({'id': 'abc_trades_empty'})
        return pd.DataFrame(), source_diag, blockers
    abc_all = pd.concat(trade_frames, ignore_index=True)
    priority = {c['candidate_id']: 4000.0 - float(c['priority']) for c in ABC_CANDIDATES}
    abc_port = resolved_priority(abc_all, priority)
    return abc_port, source_diag, blockers


def build_detector_entries(feat: pd.DataFrame, selected: pd.DataFrame, priority: dict[str, float]) -> pd.DataFrame:
    if feat.empty or selected.empty:
        return pd.DataFrame()
    rows = []
    for _, c in selected.iterrows():
        cid = str(c['candidate_id'])
        rule = str(c.get('rule', ''))
        if not rule:
            continue
        mask, problems = s179.literal_rule_mask(rule, feat)
        if problems:
            continue
        m = feat.loc[mask, ['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].copy()
        if m.empty:
            continue
        m = m.rename(columns={'dt': 'entry_dt'})
        m['candidate_id'] = cid
        m['direction'] = str(c.get('direction', ''))
        m['tp'] = num(c.get('tp'), math.nan)
        m['sl'] = num(c.get('sl'), math.nan)
        m['horizon_m5'] = int(num(c.get('horizon_m5'), 0))
        m['rule'] = rule
        rows.append(m)
    if not rows:
        return pd.DataFrame()
    det = pd.concat(rows, ignore_index=True)
    det = add_time_cols(det.rename(columns={'m15_close': 'entry_price'}))
    det['filtered_v1_removed'] = det['candidate_id'].astype(str).eq(FILTER_CANDIDATE_ID) & det['entry_hour'].eq(FILTER_EXCLUDED_HOUR)
    det = det[~det['filtered_v1_removed']].copy()
    det['priority_score'] = det['candidate_id'].astype(str).map(priority).fillna(0.0)
    return det.sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).reset_index(drop=True)


def latest_detector_snapshot(data_dir: Path, selected: pd.DataFrame, priority: dict[str, float], out: Path) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}
    source_rows: list[dict[str, Any]] = []
    for tf in ['m15', 'h1', 'h4', 'd1']:
        frames[tf], diag = s177.combine(tf, data_dir)
        source_rows.extend(diag)
        if frames[tf].empty:
            blockers.append({'id': 'detector_missing_ohlc', 'tf': tf})
    if blockers:
        return pd.DataFrame(), {}, pd.DataFrame(source_rows), blockers
    feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
    det = build_detector_entries(feat, selected, priority)
    # one priority signal per closed M15 timestamp for the last 96 rows
    tail_dt = feat[['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].tail(96).copy()
    if det.empty:
        tail_dt['priority_signal'] = 'NO_SIGNAL'
        tail_dt['candidate_id'] = ''
        latest = tail_dt.iloc[-1].to_dict() if not tail_dt.empty else {}
        return tail_dt, latest, pd.DataFrame(source_rows), blockers
    det_tail = det[det['entry_dt'].isin(set(pd.to_datetime(tail_dt['dt'])))].copy()
    if not det_tail.empty:
        picked = det_tail.sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).drop_duplicates('entry_dt', keep='first')
        merged = tail_dt.merge(picked[['entry_dt', 'candidate_id', 'direction', 'tp', 'sl', 'horizon_m5', 'priority_score']].rename(columns={'entry_dt': 'dt'}), on='dt', how='left')
    else:
        merged = tail_dt.copy()
        for col in ['candidate_id', 'direction', 'tp', 'sl', 'horizon_m5', 'priority_score']:
            merged[col] = np.nan
    merged['priority_signal'] = np.where(merged['candidate_id'].astype(str).fillna('').ne('nan') & merged['candidate_id'].notna(), merged['direction'].astype(str), 'NO_SIGNAL')
    latest = merged.iloc[-1].to_dict() if not merged.empty else {}
    return merged, latest, pd.DataFrame(source_rows), blockers


def detector_parity(det: pd.DataFrame, raw_filtered: pd.DataFrame) -> pd.DataFrame:
    if det.empty or raw_filtered.empty:
        return pd.DataFrame([{'parity_scope': 'raw_filtered_candidate_entry', 'detector_rows': int(len(det)), 'trade_rows': int(len(raw_filtered)), 'missing_in_trades': math.nan, 'extra_in_trades': math.nan}])
    d = det.copy()
    r = add_time_cols(raw_filtered)
    d['key'] = d['candidate_id'].astype(str) + '|' + pd.to_datetime(d['entry_dt']).astype(str)
    r['key'] = r['candidate_id'].astype(str) + '|' + pd.to_datetime(r['entry_dt']).astype(str)
    ds = set(d['key'].astype(str))
    rs = set(r['key'].astype(str))
    return pd.DataFrame([{
        'parity_scope': 'raw_filtered_candidate_entry',
        'detector_rows': int(len(ds)),
        'trade_rows': int(len(rs)),
        'missing_in_trades': int(len(ds - rs)),
        'extra_in_trades': int(len(rs - ds)),
        'parity_pass': len(ds - rs) == 0 and len(rs - ds) == 0,
    }])


def overlap_report(abc: pd.DataFrame, scalp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if abc.empty or scalp.empty:
        return pd.DataFrame(), pd.DataFrame()
    a = add_time_cols(abc)
    s = add_time_cols(scalp)
    exact = s.merge(a[['entry_dt', 'exit_dt', 'candidate_id', 'direction']].rename(columns={'exit_dt': 'abc_exit_dt', 'candidate_id': 'abc_candidate_id', 'direction': 'abc_direction'}), on='entry_dt', how='inner')
    active_rows = []
    a_small = a[['entry_dt', 'exit_dt', 'candidate_id', 'direction']].sort_values('entry_dt').reset_index(drop=True)
    for _, sr in s.iterrows():
        st = pd.Timestamp(sr['entry_dt'])
        hits = a_small[(a_small['entry_dt'] <= st) & (a_small['exit_dt'] > st)]
        for _, ar in hits.iterrows():
            active_rows.append({
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
    return exact, pd.DataFrame(active_rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '197'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage193/Stage191 scalp selected raw trades')
    selected = read_csv_any(root / '193' / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    raw = read_csv_any(root / '191' / 'gold_v3_191_scalping_top_trades_cost3.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_watchlist'})
    if raw.empty:
        blockers.append({'id': 'missing_stage191_top_trades_cost3'})

    filtered_one = pd.DataFrame()
    base_one = pd.DataFrame()
    raw_filtered = pd.DataFrame()
    raw_removed = pd.DataFrame()
    abc = pd.DataFrame()
    combined_abc_first = pd.DataFrame()
    combined_scalp_first = pd.DataFrame()
    portfolio_summary = pd.DataFrame()
    monthly = pd.DataFrame()
    daily = pd.DataFrame()
    latest_tail = pd.DataFrame()
    latest_info: dict[str, Any] = {}
    parity = pd.DataFrame()
    exact_overlap = pd.DataFrame()
    active_overlap = pd.DataFrame()

    if not blockers:
        selected_ids = selected['candidate_id'].astype(str).tolist()
        priority = selected_priority(selected)
        raw_selected = add_time_cols(raw[raw['candidate_id'].astype(str).isin(set(selected_ids))].copy())
        raw_selected['family'] = 'SCALP_STACK_FILTERED_V1'
        if raw_selected.empty:
            blockers.append({'id': 'raw_selected_empty'})
        else:
            raw_filtered, raw_removed = apply_filtered_v1(raw_selected)
            base_one = resolved_priority(raw_selected, priority)
            filtered_one = resolved_priority(raw_filtered, priority)
            for df in [base_one, filtered_one, raw_filtered, raw_removed]:
                if not df.empty:
                    df['family'] = 'SCALP_STACK_FILTERED_V1'
            save(selected, out / 'gold_v3_197_selected_scalp_watchlist_reference.csv')
            save(raw_selected, out / 'gold_v3_197_scalp_raw_selected_before_filter.csv')
            save(raw_filtered, out / 'gold_v3_197_scalp_raw_selected_after_filtered_v1.csv')
            save(raw_removed, out / 'gold_v3_197_scalp_raw_removed_by_filtered_v1.csv')
            save(base_one, out / 'gold_v3_197_scalp_one_position_base_rebuilt.csv')
            save(filtered_one, out / 'gold_v3_197_scalp_one_position_filtered_v1_trades.csv')

            progress('rebuild ABC and combined portfolios')
            abc, source_diag, b = build_abc(data_dir, out)
            blockers.extend(b)
            if not blockers:
                save(abc, out / 'gold_v3_197_abc_portfolio_trades_rebuilt.csv')
                abc_priority = {c['candidate_id']: 5000.0 - float(c['priority']) for c in ABC_CANDIDATES}
                scalp_priority_low = {cid: 2000.0 + score for cid, score in priority.items()}
                scalp_priority_high = {cid: 6000.0 + score for cid, score in priority.items()}
                combined_raw = pd.concat([abc, raw_filtered], ignore_index=True)
                combined_abc_first = resolved_priority(combined_raw, {**scalp_priority_low, **abc_priority})
                combined_scalp_first = resolved_priority(combined_raw, {**abc_priority, **scalp_priority_high})
                save(combined_raw, out / 'gold_v3_197_combined_raw_abc_plus_filtered_scalp.csv')
                save(combined_abc_first, out / 'gold_v3_197_combined_abc_priority_first.csv')
                save(combined_scalp_first, out / 'gold_v3_197_combined_scalp_priority_first.csv')
                exact_overlap, active_overlap = overlap_report(abc, raw_filtered)
                save(exact_overlap, out / 'gold_v3_197_exact_entry_overlap_abc_filtered_scalp.csv')
                save(active_overlap, out / 'gold_v3_197_active_window_overlap_abc_filtered_scalp.csv')

                rows = []
                portfolios = {
                    'SCALP_BASE_ONE_POSITION_COST3': base_one,
                    'SCALP_FILTERED_V1_COST3': filtered_one,
                    'ABC_ONLY_COST3': abc,
                    'COMBINED_ABC_PRIORITY_FIRST_COST3': combined_abc_first,
                    'COMBINED_SCALP_PRIORITY_FIRST_COST3': combined_scalp_first,
                    'SCALP_FILTERED_V1_COST5': filtered_one,
                    'COMBINED_ABC_PRIORITY_FIRST_COST5': combined_abc_first,
                }
                for name, df in portfolios.items():
                    pnl_col = 'pnl_net_cost5' if name.endswith('COST5') else 'pnl_net_cost3'
                    row = {'portfolio_id': name, 'pnl_col': pnl_col}
                    row.update(evaluate(df, pnl_col))
                    rows.append(row)
                portfolio_summary = pd.DataFrame(rows)
                save(portfolio_summary, out / 'gold_v3_197_portfolio_summary_cost3_cost5.csv')

                monthly_frames = []
                daily_frames = []
                for name, df in [
                    ('SCALP_BASE_ONE_POSITION_COST3', base_one),
                    ('SCALP_FILTERED_V1_COST3', filtered_one),
                    ('ABC_ONLY_COST3', abc),
                    ('COMBINED_ABC_PRIORITY_FIRST_COST3', combined_abc_first),
                ]:
                    monthly_frames.append(monthly_table(df, name, 'pnl_net_cost3'))
                    daily_frames.append(daily_table(df, name, 'pnl_net_cost3'))
                monthly = pd.concat([m for m in monthly_frames if not m.empty], ignore_index=True) if monthly_frames else pd.DataFrame()
                daily = pd.concat([d for d in daily_frames if not d.empty], ignore_index=True) if daily_frames else pd.DataFrame()
                save(monthly, out / 'gold_v3_197_monthly_summary_cost3.csv')
                save(daily, out / 'gold_v3_197_daily_counts_2026_05_06_cost3.csv')

                progress('build latest closed M15 detector snapshot')
                latest_tail, latest_info, det_source, b = latest_detector_snapshot(data_dir, selected, priority, out)
                blockers.extend(b)
                save(latest_tail, out / 'gold_v3_197_latest_detector_tail96.csv')
                det_entries = build_detector_entries(s177.base.merge_features(s177.combine('m15', data_dir)[0], s177.combine('h1', data_dir)[0], s177.combine('h4', data_dir)[0], s177.combine('d1', data_dir)[0]).sort_values('dt').reset_index(drop=True), selected, priority) if not blockers else pd.DataFrame()
                parity = detector_parity(det_entries, raw_filtered)
                save(parity, out / 'gold_v3_197_detector_raw_entry_parity.csv')

    def get_summary(portfolio_id: str, col: str, default: Any = math.nan) -> Any:
        if portfolio_summary.empty:
            return default
        hit = portfolio_summary[portfolio_summary['portfolio_id'].astype(str).eq(portfolio_id)]
        if hit.empty or col not in hit.columns:
            return default
        return hit[col].iloc[0]

    ready = len(blockers) == 0
    decision = 'STAGE197_SCALP_ONE_POSITION_FILTERED_V1_FREEZE_READY_AUDIT_ONLY' if ready else 'STAGE197_BLOCKED'
    latest_candidate = str(latest_info.get('candidate_id', '')) if latest_info else ''
    latest_signal = str(latest_info.get('priority_signal', 'NO_SIGNAL')) if latest_info else 'NO_SIGNAL'
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
        'scalp_raw_selected_rows_before_filter': int(len(raw_selected)) if 'raw_selected' in locals() and not raw_selected.empty else 0,
        'scalp_raw_removed_by_filter_rows': int(len(raw_removed)) if not raw_removed.empty else 0,
        'scalp_base_one_position_n': int(len(base_one)) if not base_one.empty else 0,
        'scalp_filtered_v1_one_position_n': int(len(filtered_one)) if not filtered_one.empty else 0,
        'scalp_base_full_sum_cost3': num(get_summary('SCALP_BASE_ONE_POSITION_COST3', 'full_sum')),
        'scalp_base_full_pf_cost3': num(get_summary('SCALP_BASE_ONE_POSITION_COST3', 'full_pf')),
        'scalp_filtered_full_sum_cost3': num(get_summary('SCALP_FILTERED_V1_COST3', 'full_sum')),
        'scalp_filtered_full_pf_cost3': num(get_summary('SCALP_FILTERED_V1_COST3', 'full_pf')),
        'scalp_filtered_test_sum_cost3': num(get_summary('SCALP_FILTERED_V1_COST3', 'test_sum')),
        'scalp_filtered_recent3m_sum_cost3': num(get_summary('SCALP_FILTERED_V1_COST3', 'recent3m_sum')),
        'scalp_filtered_may2026_sum_cost3': num(get_summary('SCALP_FILTERED_V1_COST3', '2026_05_sum')),
        'scalp_filtered_jun2026_sum_cost3': num(get_summary('SCALP_FILTERED_V1_COST3', '2026_06_sum')),
        'scalp_filtered_full_neg_months_cost3': int(num(get_summary('SCALP_FILTERED_V1_COST3', 'full_neg_months'))),
        'scalp_filtered_full_sum_cost5': num(get_summary('SCALP_FILTERED_V1_COST5', 'full_sum')),
        'scalp_filtered_full_pf_cost5': num(get_summary('SCALP_FILTERED_V1_COST5', 'full_pf')),
        'abc_full_sum_cost3': num(get_summary('ABC_ONLY_COST3', 'full_sum')),
        'abc_full_pf_cost3': num(get_summary('ABC_ONLY_COST3', 'full_pf')),
        'combined_abc_first_full_n_cost3': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_n'))),
        'combined_abc_first_full_sum_cost3': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_sum')),
        'combined_abc_first_full_pf_cost3': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_pf')),
        'combined_abc_first_full_neg_months_cost3': int(num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST3', 'full_neg_months'))),
        'combined_abc_first_full_sum_cost5': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST5', 'full_sum')),
        'combined_abc_first_full_pf_cost5': num(get_summary('COMBINED_ABC_PRIORITY_FIRST_COST5', 'full_pf')),
        'exact_entry_overlap_count': int(len(exact_overlap)) if not exact_overlap.empty else 0,
        'active_window_overlap_count': int(len(active_overlap)) if not active_overlap.empty else 0,
        'active_window_direction_conflict_count': int(active_overlap['direction_conflict'].sum()) if not active_overlap.empty and 'direction_conflict' in active_overlap.columns else 0,
        'latest_closed_m15_dt': str(latest_info.get('dt', '')) if latest_info else '',
        'latest_scalp_priority_signal': latest_signal if latest_signal and latest_signal != 'nan' else 'NO_SIGNAL',
        'latest_scalp_candidate_id': '' if latest_candidate == 'nan' else latest_candidate,
        'recent_tail96_signal_rows': int((latest_tail.get('priority_signal', pd.Series(dtype=str)).astype(str) != 'NO_SIGNAL').sum()) if not latest_tail.empty else 0,
        'detector_raw_entry_parity_pass': bool(parity.get('parity_pass', pd.Series([False])).iloc[0]) if not parity.empty and 'parity_pass' in parity.columns else False,
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'Entry detector uses closed OHLC-derived features and MT5 hour filter only. M5 future TP/SL/horizon is used only for audit scoring.',
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
    (out / 'gold_v3_197_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_197_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 197 PASTE_ME_SCALP_ONE_POSITION_FILTERED_V1_FREEZE_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PORTFOLIO_SUMMARY_COST3_COST5', show(portfolio_summary, 20)]
    lines += ['', 'MONTHLY_SUMMARY_COST3', show(monthly, 120)]
    lines += ['', 'DAILY_COUNTS_2026_05_06_COST3', show(daily, 160)]
    lines += ['', 'RAW_REMOVED_BY_FILTERED_V1', show(raw_removed, 60)]
    lines += ['', 'DETECTOR_RAW_ENTRY_PARITY', show(parity, 20)]
    lines += ['', 'LATEST_DETECTOR_TAIL96', show(latest_tail, 120)]
    lines += ['', 'ACTIVE_WINDOW_OVERLAP_SAMPLE', show(active_overlap, 60)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage197 is audit-only. It freezes SCALP_ONE_POSITION_FILTERED_V1 as a review candidate: selected Stage193 scalp stack with only SCALP_002 SHORT MT5 hour 09 excluded.',
        'The filter is applied before one-position resolution, so same-timestamp/active-window alternatives are handled by the same priority resolver.',
        'ABC remains PRIMARY. SCALP_ONE_POSITION_FILTERED_V1 remains SECONDARY/WATCHLIST until separate approval.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
