from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    family: str
    live_parity: bool
    grid_rel: str
    events_rel: str
    population_name: str
    horizon: int
    tp: float
    sl: float


SPECS = [
    CandidateSpec('E2','PRICE_SWEEP_RECLAIM',False,'stage260_e2_real/stage260_e2_strategy_grid_event_control_no_regime.csv','stage260_e2_real/stage260_e2_events_dedup120.csv','EVENT',60,15.0,5.0),
    CandidateSpec('E3','PRICE_LEVEL_BREAK_RETEST',False,'stage260_e3_real/stage260_e3_strategy_grid_event_control.csv','stage260_e3_real/stage260_e3_events_dedup120.csv','E3_TRUE',60,10.0,5.0),
    CandidateSpec('E4','PRICE_COMPRESSION_EXPANSION',False,'stage260_e4_real/stage260_e4_strategy_grid_event_control.csv','stage260_e4_real/stage260_e4_events_dedup120.csv','E4A_TRUE',240,25.0,15.0),
    CandidateSpec('E5','PRICE_DISPLACEMENT_CONTINUATION',True,'stage260_e5_strategy_grid.csv','stage260_e5_events_live_reproducible.csv','E5_TRUE',240,25.0,10.0),
    CandidateSpec('E6','PRICE_DISPLACEMENT_REVERSAL',True,'stage260_e6_real/stage260_e6_strategy_grid.csv','stage260_e6_events_live_reproducible.csv','E6_TRUE',240,10.0,15.0),
    CandidateSpec('E7','TICK_VOLUME_IMPULSE',True,'stage260_e7_real/stage260_e7_strategy_grid.csv','stage260_e7_real/stage260_e7_events_live_reproducible.csv','E7_TRUE',240,25.0,10.0),
    CandidateSpec('E8','TICK_VOLUME_ABSORPTION',True,'stage260_e8_real/stage260_e8_strategy_grid.csv','stage260_e8_real/stage260_e8_events_live_reproducible.csv','E8_TRUE',60,20.0,15.0),
]


def pf(s: pd.Series) -> float:
    x = pd.to_numeric(s, errors='coerce').dropna()
    wins = float(x[x > 0].sum())
    losses = float(-x[x < 0].sum())
    return wins / losses if losses > 0 else (math.inf if wins > 0 else math.nan)


def max_dd(s: pd.Series) -> float:
    x = pd.to_numeric(s, errors='coerce').fillna(0).to_numpy(float)
    if len(x) == 0:
        return 0.0
    equity = np.cumsum(x)
    peak = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    return float(np.max(peak - equity))


def losing_streak(s: pd.Series) -> int:
    best = cur = 0
    for value in pd.to_numeric(s, errors='coerce').dropna():
        cur = cur + 1 if value < 0 else 0
        best = max(best, cur)
    return int(best)


def load_candidate(base: Path, spec: CandidateSpec) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    events = pd.read_csv(base / spec.events_rel)
    events['entry_time'] = pd.to_datetime(events['entry_time'], errors='raise')
    events = events.sort_values('entry_time').drop_duplicates('entry_time', keep='first').reset_index(drop=True)
    events['candidate_id'] = spec.candidate_id
    events['candidate_family'] = spec.family
    events['live_parity_tier'] = 'LIVE_PARITY_PASS' if spec.live_parity else 'DIAGNOSTIC_ONLY'
    keep = ['candidate_id','candidate_family','live_parity_tier','entry_time','direction']
    keep += [c for c in ['half','quarter','month','candidate_key'] if c in events.columns]
    events = events[keep]

    grid = pd.read_csv(base / spec.grid_rel)
    grid['entry_time'] = pd.to_datetime(grid['entry_time'], errors='raise')
    selected = grid[
        grid['population_name'].eq(spec.population_name)
        & grid['horizon'].eq(spec.horizon)
        & np.isclose(grid['tp'], spec.tp)
        & np.isclose(grid['sl'], spec.sl)
    ].copy()
    if selected['entry_time'].duplicated().any():
        raise AssertionError(f'{spec.candidate_id}: duplicate fixed-cell entry_time')
    selected['candidate_id'] = spec.candidate_id
    selected['candidate_family'] = spec.family
    selected['live_parity_tier'] = 'LIVE_PARITY_PASS' if spec.live_parity else 'DIAGNOSTIC_ONLY'
    selected['fixed_horizon'] = spec.horizon
    selected['fixed_tp'] = spec.tp
    selected['fixed_sl'] = spec.sl
    selected['exit_time'] = selected['entry_time'] + pd.to_timedelta(selected['exit_min'], unit='m')
    selected['cost2_pnl'] = selected['net_cost2']
    trades = selected[[
        'candidate_id','candidate_family','live_parity_tier','entry_time','direction','half','quarter','month',
        'fixed_horizon','fixed_tp','fixed_sl','result','exit_min','exit_time','gross_pnl','cost2_pnl'
    ]].sort_values('entry_time').reset_index(drop=True)
    full_count, evaluated = len(events), len(trades)
    coverage = {
        'candidate_id': spec.candidate_id,
        'family': spec.family,
        'live_parity': spec.live_parity,
        'full_event_count': full_count,
        'fixed_cell_evaluated_count': evaluated,
        'missing_fixed_horizon_outcome_count': full_count - evaluated,
        'evaluation_coverage': evaluated / full_count if full_count else math.nan,
        'fixed_horizon': spec.horizon,
        'fixed_tp': spec.tp,
        'fixed_sl': spec.sl,
    }
    return events, trades, coverage


def metrics(name: str, ledger: pd.DataFrame, full_count: int, suppressed: int = 0) -> dict[str, Any]:
    z = ledger.sort_values(['entry_time','candidate_id']).reset_index(drop=True)
    s = z['cost2_pnl']
    monthly = z.assign(month_key=z['entry_time'].dt.strftime('%Y-%m')).groupby('month_key')['cost2_pnl'].sum()
    contribution = z.groupby('candidate_id')['cost2_pnl'].sum()
    abs_share = contribution.abs() / contribution.abs().sum() if contribution.abs().sum() else contribution * np.nan
    return {
        'portfolio': name,
        'evaluated_trade_count': len(z),
        'full_event_stream_count': full_count,
        'outcome_coverage': len(z) / full_count if full_count else math.nan,
        'suppressed_event_count': suppressed,
        'pnl': float(s.sum()),
        'expectancy': float(s.mean()) if len(s) else math.nan,
        'pf': pf(s),
        'win_rate': float((s > 0).mean()) if len(s) else math.nan,
        'max_dd': max_dd(s),
        'max_losing_streak': losing_streak(s),
        'positive_months': int((monthly > 0).sum()),
        'negative_months': int((monthly < 0).sum()),
        'months_observed': int(len(monthly)),
        'max_abs_candidate_pnl_share': float(abs_share.max()) if len(abs_share) else math.nan,
    }


def by_half(name: str, ledger: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for half in ['2025H1','2025H2','2026H1']:
        g = ledger[ledger['half'].eq(half)].sort_values(['entry_time','candidate_id'])
        s = g['cost2_pnl']
        rows.append({
            'portfolio': name, 'half': half, 'count': len(g), 'pnl': float(s.sum()),
            'expectancy': float(s.mean()) if len(s) else math.nan, 'pf': pf(s),
            'win_rate': float((s > 0).mean()) if len(s) else math.nan,
            'max_dd': max_dd(s), 'max_losing_streak': losing_streak(s),
        })
    return rows


def first_come(events: pd.DataFrame, trades: pd.DataFrame, fixed_120: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = trades.set_index(['candidate_id','entry_time'])
    active_until = pd.Timestamp.min
    accepted, suppressed = [], []
    for _, event in events.sort_values(['entry_time','candidate_id']).iterrows():
        t = pd.Timestamp(event['entry_time'])
        if t < active_until:
            suppressed.append(event.to_dict())
            continue
        key = (event['candidate_id'], t)
        if key in lookup.index:
            row = lookup.loc[key]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            item = row.to_dict()
            item['candidate_id'] = event['candidate_id']
            item['candidate_family'] = event['candidate_family']
            item['live_parity_tier'] = event['live_parity_tier']
            item['entry_time'] = t
            accepted.append(item)
            active_until = t + pd.Timedelta(minutes=120) if fixed_120 else pd.Timestamp(item['exit_time'])
        else:
            item = event.to_dict()
            item.update({'cost2_pnl': np.nan, 'gross_pnl': np.nan, 'result': 'OUTCOME_UNAVAILABLE', 'exit_time': pd.NaT})
            accepted.append(item)
            active_until = t + pd.Timedelta(minutes=120 if fixed_120 else 240)
    return pd.DataFrame(accepted), pd.DataFrame(suppressed)


def overlap(a: pd.DataFrame, b: pd.DataFrame, minutes: int) -> dict[str, Any]:
    aa = a[['entry_time','direction']].sort_values('entry_time').reset_index(drop=True)
    bb = b[['entry_time','direction']].sort_values('entry_time').reset_index(drop=True)
    pairs = []
    for i, ra in aa.iterrows():
        dt = (bb['entry_time'] - ra['entry_time']).abs()
        for j in np.flatnonzero((dt <= pd.Timedelta(minutes=minutes)).to_numpy()):
            pairs.append((dt.iloc[j], i, int(j)))
    pairs.sort(key=lambda x: (x[0], x[1], x[2]))
    used_a, used_b, matches = set(), set(), []
    for delta, i, j in pairs:
        if i in used_a or j in used_b:
            continue
        used_a.add(i); used_b.add(j)
        matches.append((delta, aa.iloc[i]['direction'], bb.iloc[j]['direction']))
    count = len(matches)
    same = sum(x[1] == x[2] for x in matches)
    union = len(aa) + len(bb) - count
    return {
        'matched_pairs': count,
        'jaccard_like': count / union if union else math.nan,
        'same_direction_rate': same / count if count else math.nan,
    }


def run(base: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    events_parts, trades_parts, coverage_rows = [], [], []
    for spec in SPECS:
        events, trades, coverage = load_candidate(base, spec)
        events_parts.append(events)
        trades_parts.append(trades)
        coverage_rows.append(coverage)
    events = pd.concat(events_parts, ignore_index=True).sort_values(['entry_time','candidate_id'])
    trades = pd.concat(trades_parts, ignore_index=True).sort_values(['entry_time','candidate_id'])
    live_events = events[events['live_parity_tier'].eq('LIVE_PARITY_PASS')].copy()
    live_trades = trades[trades['live_parity_tier'].eq('LIVE_PARITY_PASS')].copy()

    pd.DataFrame(coverage_rows).to_csv(out/'stage261_candidate_outcome_coverage.csv', index=False)
    live_events.to_csv(out/'stage261_live_candidate_event_ledger.csv', index=False)
    live_trades.to_csv(out/'stage261_live_candidate_fixed_cell_trade_ledger.csv', index=False)

    p1 = live_trades.copy()
    acc2, sup2 = first_come(live_events, live_trades, False)
    acc3, sup3 = first_come(live_events, live_trades, True)
    p2 = acc2[acc2['cost2_pnl'].notna()].copy()
    p3 = acc3[acc3['cost2_pnl'].notna()].copy()
    p4_events = live_events[live_events['candidate_id'].isin(['E5','E7'])]
    p4 = live_trades[live_trades['candidate_id'].isin(['E5','E7'])].copy()

    portfolio_rows = [
        metrics('P1_PARALLEL_EQUAL_UNIT', p1, len(live_events)),
        metrics('P2_ONE_ACTIVE_FIRST_COME', p2, len(acc2), len(sup2)),
        metrics('P3_ONE_ACTIVE_120M', p3, len(acc3), len(sup3)),
        metrics('P4_E5_E7_PREDECLARED_COMPLEMENT', p4, len(p4_events)),
    ]
    portfolio_rows[1]['accepted_outcome_unavailable'] = int(acc2['cost2_pnl'].isna().sum())
    portfolio_rows[2]['accepted_outcome_unavailable'] = int(acc3['cost2_pnl'].isna().sum())
    pd.DataFrame(portfolio_rows).to_csv(out/'stage261_portfolio_summary.csv', index=False)

    half_rows = []
    for name, ledger in [('P1_PARALLEL_EQUAL_UNIT',p1),('P2_ONE_ACTIVE_FIRST_COME',p2),('P3_ONE_ACTIVE_120M',p3),('P4_E5_E7_PREDECLARED_COMPLEMENT',p4)]:
        half_rows.extend(by_half(name, ledger))
    pd.DataFrame(half_rows).to_csv(out/'stage261_portfolio_by_half.csv', index=False)

    daily = live_trades.assign(day=live_trades['entry_time'].dt.floor('D')).pivot_table(
        index='day', columns='candidate_id', values='cost2_pnl', aggfunc='sum', fill_value=0.0
    )
    daily.corr().to_csv(out/'stage261_live_candidate_daily_correlation.csv')
    overlap_rows = []
    ids = ['E5','E6','E7','E8']
    for i, a in enumerate(ids):
        for b in ids[i+1:]:
            row = overlap(live_events[live_events.candidate_id.eq(a)], live_events[live_events.candidate_id.eq(b)], 120)
            overlap_rows.append({'candidate_a':a,'candidate_b':b,'window_min':120,**row})
    pd.DataFrame(overlap_rows).to_csv(out/'stage261_live_candidate_overlap120.csv', index=False)

    coverage = pd.DataFrame(coverage_rows)
    p2_missing = int(acc2['cost2_pnl'].isna().sum())
    full_coverage = bool((coverage[coverage.live_parity]['evaluation_coverage'] == 1.0).all())
    summary = {
        'status':'GOLD_V3_261_INSUFFICIENT_COMMON_LEDGER_BLOCKED_AUDIT_ONLY',
        'audit_only':True,
        'live_ready':False,
        'all_live_fixed_outcome_coverage_100pct':full_coverage,
        'p2_accepted_outcome_unavailable':p2_missing,
        'portfolio_summary':portfolio_rows,
        'formal_verdict':'INSUFFICIENT_COMMON_LEDGER_BLOCKED',
        'diagnostic_secondary_verdict':'NEW_INFORMATION_REQUIRED',
        'operating_state':'NO_LIVE_PROMOTION_AUDIT_ONLY',
    }
    (out/'stage261_final_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, default=Path('/mnt/data'))
    parser.add_argument('--out', type=Path, default=Path('/mnt/data/stage261_portfolio'))
    args = parser.parse_args()
    run(args.base, args.out)


if __name__ == '__main__':
    main()
