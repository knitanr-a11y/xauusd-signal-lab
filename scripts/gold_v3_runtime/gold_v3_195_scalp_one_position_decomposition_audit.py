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

STEP = 'GOLD_V3_195_SCALP_ONE_POSITION_DECOMPOSITION_AUDIT_ONLY'
PRIMARY_COST = 3.0
STRESS_COST = 5.0
FOCUS_MONTHS = ['2026-05', '2026-06']
FOCUS_DAYS = ['2026-05-20', '2026-05-28', '2026-06-02', '2026-06-10', '2026-06-15']


def progress(msg: str) -> None:
    print(f'[195 progress] {msg}', flush=True)


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


def add_time_cols(tr: pd.DataFrame) -> pd.DataFrame:
    x = tr.copy()
    if x.empty:
        return x
    x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    x['exit_dt'] = pd.to_datetime(x['exit_dt'])
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


def summarize_group(g: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> dict[str, Any]:
    n, total, pf, wr, avg, gp, gl = pf_sum_wr(g[pnl_col] if pnl_col in g.columns else [])
    out = {
        'trades': n,
        'pnl_sum': total,
        'pf': pf,
        'win_rate_pct': wr * 100.0 if math.isfinite(wr) else math.nan,
        'avg_net': avg,
        'gross_profit': gp,
        'gross_loss': gl,
        'tp_hits': int((g.get('hit_type', pd.Series(dtype=str)).astype(str) == 'TP').sum()) if not g.empty else 0,
        'sl_hits': int((g.get('hit_type', pd.Series(dtype=str)).astype(str) == 'SL').sum()) if not g.empty else 0,
        'horizon_exits': int((g.get('hit_type', pd.Series(dtype=str)).astype(str) == 'HORIZON').sum()) if not g.empty else 0,
    }
    return out


def group_summary(df: pd.DataFrame, by: list[str], label_col: str = '', pnl_col: str = 'pnl_net_cost3') -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for keys, g in df.groupby(by, sort=True, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(by, keys)}
        row.update(summarize_group(g, pnl_col))
        if 'candidate_id' in g.columns:
            row['candidate_counts'] = json.dumps(g['candidate_id'].astype(str).value_counts().to_dict(), ensure_ascii=False)
        if 'direction' in g.columns:
            row['direction_counts'] = json.dumps(g['direction'].astype(str).value_counts().to_dict(), ensure_ascii=False)
        if label_col:
            row['summary_type'] = label_col
        rows.append(row)
    out = pd.DataFrame(rows)
    if 'pnl_sum' in out.columns:
        out = out.sort_values(by + ['pnl_sum'], ascending=[True] * len(by) + [False])
    return out


def split_summary(df: pd.DataFrame, pnl_col: str = 'pnl_net_cost3') -> dict[str, Any]:
    x = add_time_cols(df)
    dt = pd.to_datetime(x['entry_dt']) if not x.empty else pd.Series(dtype='datetime64[ns]')
    train = x[(dt >= pd.Timestamp('2025-01-02')) & (dt < pd.Timestamp('2026-01-01'))].copy() if not x.empty else x.copy()
    test = x[dt >= pd.Timestamp('2026-01-01')].copy() if not x.empty else x.copy()
    full = x[dt >= pd.Timestamp('2025-01-02')].copy() if not x.empty else x.copy()
    recent = full[full['month'].isin(sorted(full['month'].unique())[-3:])].copy() if not full.empty else full.copy()
    out = {}
    for name, g in [('train', train), ('test', test), ('full', full), ('recent3m', recent)]:
        s = summarize_group(g, pnl_col)
        out.update({f'{name}_{k}': v for k, v in s.items() if k in ['trades', 'pnl_sum', 'pf', 'win_rate_pct', 'avg_net']})
    months = full.groupby('month')[pnl_col].sum().sort_index() if not full.empty else pd.Series(dtype=float)
    out['full_months'] = int(len(months))
    out['full_neg_months'] = int((months < 0).sum()) if len(months) else 0
    out['worst_month'] = str(months.idxmin()) if len(months) else ''
    out['worst_month_sum'] = float(months.min()) if len(months) else math.nan
    return out


def focus_day_trade_detail(df: pd.DataFrame) -> pd.DataFrame:
    x = add_time_cols(df)
    x = x[x['entry_date'].isin(FOCUS_DAYS)].copy()
    if x.empty:
        return pd.DataFrame()
    cols = [
        'entry_date', 'entry_dt', 'exit_dt', 'candidate_id', 'direction', 'profile_id', 'hit_type',
        'entry_price', 'tp', 'sl', 'horizon_m5', 'pnl_raw', 'pnl_net_cost3', 'pnl_net_cost5', 'h1_atr14', 'rule'
    ]
    use = [c for c in cols if c in x.columns]
    return x.sort_values(['entry_dt', 'candidate_id'])[use].reset_index(drop=True)


def losing_day_candidate_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    x = add_time_cols(df)
    focus = x[x['entry_date'].isin(FOCUS_DAYS)].copy()
    if focus.empty:
        return pd.DataFrame()
    return group_summary(focus, ['entry_date', 'candidate_id', 'direction'], 'focus_day_candidate')


def hit_type_by_candidate(df: pd.DataFrame) -> pd.DataFrame:
    x = add_time_cols(df)
    focus = x[x['month'].isin(FOCUS_MONTHS)].copy()
    if focus.empty or 'hit_type' not in focus.columns:
        return pd.DataFrame()
    return group_summary(focus, ['month', 'candidate_id', 'direction', 'hit_type'], 'focus_month_candidate_hit')


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    src = root / '193'
    src194 = root / '194'
    out = root / '195'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('read Stage193 SCALP one-position portfolio trades')
    trades = read_csv_any(src / 'gold_v3_193_scalping_profit_stack_portfolio_trades.csv')
    selected = read_csv_any(src / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    if trades.empty:
        blockers.append({'id': 'missing_stage193_scalp_one_position_trades', 'path': str(src / 'gold_v3_193_scalping_profit_stack_portfolio_trades.csv')})
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_watchlist', 'path': str(src / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')})

    all_summary = pd.DataFrame()
    month_summary = pd.DataFrame()
    day_summary = pd.DataFrame()
    candidate_month = pd.DataFrame()
    direction_month = pd.DataFrame()
    hour_month = pd.DataFrame()
    focus_detail = pd.DataFrame()
    focus_candidate = pd.DataFrame()
    hit_candidate = pd.DataFrame()
    top_losses = pd.DataFrame()
    day_rank = pd.DataFrame()

    if not blockers:
        ids = selected['candidate_id'].astype(str).tolist()
        x = add_time_cols(trades)
        x = x[x['candidate_id'].astype(str).isin(ids)].copy()
        if x.empty:
            blockers.append({'id': 'no_trades_after_selected_candidate_filter'})
        else:
            focus = x[x['month'].isin(FOCUS_MONTHS)].copy()
            save(x, out / 'gold_v3_195_scalp_one_position_trades_all.csv')
            save(focus, out / 'gold_v3_195_scalp_one_position_trades_2026_05_06.csv')

            all_row = split_summary(x, 'pnl_net_cost3')
            all_row['portfolio_id'] = 'SCALP_ONE_POSITION_COST3'
            all_summary = pd.DataFrame([all_row])
            save(all_summary, out / 'gold_v3_195_scalp_one_position_overall_summary.csv')

            month_summary = group_summary(x, ['month'], 'monthly')
            save(month_summary, out / 'gold_v3_195_scalp_one_position_monthly_summary.csv')

            day_summary = group_summary(focus, ['entry_date'], 'daily_2026_05_06')
            if not day_summary.empty:
                day_summary['is_negative_day'] = day_summary['pnl_sum'] < 0
                day_summary['is_focus_weak_day'] = day_summary['entry_date'].isin(FOCUS_DAYS)
            save(day_summary, out / 'gold_v3_195_scalp_one_position_daily_2026_05_06.csv')

            candidate_month = group_summary(focus, ['month', 'candidate_id', 'direction'], 'candidate_month_2026_05_06')
            save(candidate_month, out / 'gold_v3_195_scalp_one_position_candidate_month_2026_05_06.csv')

            direction_month = group_summary(focus, ['month', 'direction'], 'direction_month_2026_05_06')
            save(direction_month, out / 'gold_v3_195_scalp_one_position_direction_month_2026_05_06.csv')

            hour_month = group_summary(focus, ['month', 'entry_hour'], 'hour_month_2026_05_06')
            save(hour_month, out / 'gold_v3_195_scalp_one_position_hour_month_2026_05_06.csv')

            focus_detail = focus_day_trade_detail(x)
            save(focus_detail, out / 'gold_v3_195_scalp_one_position_focus_day_trade_detail.csv')

            focus_candidate = losing_day_candidate_breakdown(x)
            save(focus_candidate, out / 'gold_v3_195_scalp_one_position_focus_day_candidate_breakdown.csv')

            hit_candidate = hit_type_by_candidate(x)
            save(hit_candidate, out / 'gold_v3_195_scalp_one_position_hit_type_by_candidate_2026_05_06.csv')

            top_losses = x.sort_values('pnl_net_cost3').head(100)
            save(top_losses, out / 'gold_v3_195_scalp_one_position_top_losses.csv')

            day_rank = day_summary.sort_values('pnl_sum').reset_index(drop=True) if not day_summary.empty else pd.DataFrame()
            save(day_rank, out / 'gold_v3_195_scalp_one_position_worst_days_2026_05_06.csv')

            # Copy Stage194 daily table as reference if available.
            p194 = src194 / 'gold_v3_194_daily_counts_2026_05_06_cost3.csv'
            if p194.exists():
                ref = read_csv_any(p194)
                if not ref.empty:
                    save(ref[ref.get('portfolio_id', pd.Series(dtype=str)).astype(str).eq('SCALP_ONE_POSITION_COST3')], out / 'gold_v3_195_stage194_one_position_daily_reference.csv')

    ready = len(blockers) == 0
    def daily_value(day: str, col: str, default: Any = math.nan) -> Any:
        if day_summary.empty:
            return default
        hit = day_summary[day_summary['entry_date'].astype(str).eq(day)]
        if hit.empty or col not in hit.columns:
            return default
        return hit[col].iloc[0]

    decision = 'STAGE195_SCALP_ONE_POSITION_DECOMPOSITION_READY_AUDIT_ONLY' if ready else 'STAGE195_BLOCKED'
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'source_stage': 'Stage193 SCALP one-position portfolio trades',
        'focus_months': FOCUS_MONTHS,
        'focus_weak_days': FOCUS_DAYS,
        'cost_points': PRIMARY_COST,
        'selected_candidate_count': int(len(selected)) if not selected.empty else 0,
        'trade_rows_all': int(len(trades)) if not trades.empty else 0,
        'focus_month_trade_rows': int(len(trades[add_time_cols(trades)['month'].isin(FOCUS_MONTHS)])) if not trades.empty else 0,
        'may_2026_trades': int(daily_value('dummy', 'trades', 0)) if False else int(day_summary[day_summary.get('month', pd.Series(dtype=str)).astype(str).eq('2026-05')]['trades'].sum()) if not day_summary.empty and 'month' in day_summary.columns else 0,
        'june_2026_trades': int(day_summary[day_summary.get('month', pd.Series(dtype=str)).astype(str).eq('2026-06')]['trades'].sum()) if not day_summary.empty and 'month' in day_summary.columns else 0,
        'may_2026_positive_days': int(((day_summary.get('month', pd.Series(dtype=str)).astype(str).eq('2026-05')) & (day_summary.get('pnl_sum', pd.Series(dtype=float)) > 0)).sum()) if not day_summary.empty else 0,
        'may_2026_negative_days': int(((day_summary.get('month', pd.Series(dtype=str)).astype(str).eq('2026-05')) & (day_summary.get('pnl_sum', pd.Series(dtype=float)) < 0)).sum()) if not day_summary.empty else 0,
        'june_2026_positive_days': int(((day_summary.get('month', pd.Series(dtype=str)).astype(str).eq('2026-06')) & (day_summary.get('pnl_sum', pd.Series(dtype=float)) > 0)).sum()) if not day_summary.empty else 0,
        'june_2026_negative_days': int(((day_summary.get('month', pd.Series(dtype=str)).astype(str).eq('2026-06')) & (day_summary.get('pnl_sum', pd.Series(dtype=float)) < 0)).sum()) if not day_summary.empty else 0,
        'weak_day_2026_05_20_sum': float(daily_value('2026-05-20', 'pnl_sum')),
        'weak_day_2026_05_28_sum': float(daily_value('2026-05-28', 'pnl_sum')),
        'weak_day_2026_06_02_sum': float(daily_value('2026-06-02', 'pnl_sum')),
        'weak_day_2026_06_10_sum': float(daily_value('2026-06-10', 'pnl_sum')),
        'weak_day_2026_06_15_sum': float(daily_value('2026-06-15', 'pnl_sum')),
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'future_info_policy': 'Uses already-resolved Stage193 audit trades. No entry rule uses future outcome.',
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
    (out / 'gold_v3_195_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_195_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    neg_days = day_summary[day_summary['pnl_sum'] < 0].copy() if not day_summary.empty and 'pnl_sum' in day_summary.columns else pd.DataFrame()
    lines = ['GOLD V3 195 PASTE_ME_SCALP_ONE_POSITION_DECOMPOSITION_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'OVERALL_SUMMARY', show(all_summary, 10)]
    lines += ['', 'DAILY_SUMMARY_2026_05_06', show(day_summary, 120)]
    lines += ['', 'NEGATIVE_DAY_SUMMARY_2026_05_06', show(neg_days, 40)]
    lines += ['', 'FOCUS_DAY_CANDIDATE_BREAKDOWN', show(focus_candidate, 120)]
    lines += ['', 'FOCUS_DAY_TRADE_DETAIL', show(focus_detail, 160)]
    lines += ['', 'CANDIDATE_MONTH_2026_05_06', show(candidate_month, 120)]
    lines += ['', 'DIRECTION_MONTH_2026_05_06', show(direction_month, 30)]
    lines += ['', 'HOUR_MONTH_2026_05_06', show(hour_month, 80)]
    lines += ['', 'HIT_TYPE_BY_CANDIDATE_2026_05_06', show(hit_candidate, 120)]
    lines += ['', 'TOP_LOSSES_ALL_PERIOD', show(top_losses, 80)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage195 is audit-only. It decomposes SCALP_ONE_POSITION only, focusing on 2026-05 and 2026-06 plus weak days identified in Stage194.',
        'This is still a review artifact. No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
