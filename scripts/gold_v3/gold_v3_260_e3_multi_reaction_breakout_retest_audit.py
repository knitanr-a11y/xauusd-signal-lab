from __future__ import annotations

from pathlib import Path
import json
import math
import sys
from typing import Any

import numpy as np
import pandas as pd

BASE = Path('/mnt/data')
OUT = BASE / 'stage260_e3_real'
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(2603)
DEFINITION_COMMIT = '90e74d958a42bb586bf74f80784a54555e8f960f'

sys.path.insert(0, str(BASE))
from stage260_event_audit_utils import (
    combine_tf, atr_context, evaluate_population, summarize_paths, summarize_grid,
    pf, paired_bootstrap, event_distance_mask, dedup_custom_population,
    shift_events, reverse_events, weekday_shift,
)
from stage260_e3_levels import (
    causal_percentile, make_h1_with_atr, build_confirmed_reactions, build_level_context,
    build_m15_context, detect_breakouts, complete_retest_acceptance,
)

def log(msg: str) -> None:
    print(msg, flush=True)

def build_controls(x: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if events.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    event_times = events['entry_time'].to_numpy(dtype='datetime64[ns]')
    near_event = event_distance_mask(x['decision_time'], event_times, 60)
    recent_event = np.zeros(len(x), dtype=bool)
    ev = np.sort(event_times)
    t = x['decision_time'].to_numpy(dtype='datetime64[ns]')
    idx = np.searchsorted(ev, t, side='right') - 1
    ok = idx >= 0
    recent_event[ok] = (t[ok] - ev[idx[ok]]) <= np.timedelta64(180, 'm')
    rows: list[dict[str, Any]] = []
    valid = x['entry_price'].notna() & x['h1_atr14'].notna() & x['h4_atr_band'].notna() & ~near_event & ~recent_event
    for direction in ['LONG', 'SHORT']:
        if direction == 'LONG':
            level = x['res_level']; touches = x['res_touch_count']; dist = (x['close'] - level) / x['h1_atr14']
        else:
            level = x['sup_level']; touches = x['sup_touch_count']; dist = (level - x['close']) / x['h1_atr14']
        mask = valid & level.notna() & touches.ge(3) & dist.ge(.05) & dist.le(.50)
        for _, r in x.loc[mask].iterrows():
            rows.append({
                'decision_time': r['decision_time'], 'entry_time': r['decision_time'], 'entry_price': r['entry_price'],
                'direction': direction, 'level': float(r['res_level'] if direction == 'LONG' else r['sup_level']),
                'touch_count': int(r['res_touch_count'] if direction == 'LONG' else r['sup_touch_count']),
                'level_quality': str(r['res_quality'] if direction == 'LONG' else r['sup_quality']),
                'weekday': int(r['weekday']), 'server_hour': int(r['server_hour']), 'month': r['month'],
                'quarter': r['quarter'], 'half': r['half'], 'h1_atr14': r['h1_atr14'],
                'h1_atr_pct': r['h1_atr_pct'], 'h1_atr_band': r['h1_atr_band'],
                'h4_atr14': r['h4_atr14'], 'h4_atr_pct': r['h4_atr_pct'], 'h4_atr_band': r['h4_atr_band'],
                'population': 'MATCHED_CONTROL',
            })
    pool = pd.DataFrame(rows).sort_values('entry_time').reset_index(drop=True)
    if pool.empty:
        return pool, pd.DataFrame(), events.copy()
    available = np.ones(len(pool), dtype=bool)
    matched_rows = []; unmatched_rows = []
    arrs = {
        'weekday': pool['weekday'].to_numpy(), 'hour': pool['server_hour'].to_numpy(),
        'direction': pool['direction'].to_numpy(), 'h1': pool['h1_atr_band'].astype(str).to_numpy(),
        'h4': pool['h4_atr_band'].astype(str).to_numpy(), 'quality': pool['level_quality'].astype(str).to_numpy(),
        'month': pool['month'].to_numpy(), 'quarter': pool['quarter'].to_numpy(),
    }
    for _, e in events.sort_values('entry_time').iterrows():
        exact = (
            available & (arrs['weekday'] == int(e.weekday)) & (arrs['hour'] == int(e.server_hour))
            & (arrs['direction'] == e.direction) & (arrs['h1'] == str(e.h1_atr_band))
            & (arrs['h4'] == str(e.h4_atr_band)) & (arrs['quality'] == str(e.level_quality))
        )
        tier = 'SAME_MONTH'; mask = exact & (arrs['month'] == e.month)
        if not mask.any():
            tier = 'SAME_QUARTER'; mask = exact & (arrs['quarter'] == e.quarter)
        if not mask.any():
            tier = 'WITHIN_90D'; dd = (pool['entry_time'] - e.entry_time).abs().to_numpy(); mask = exact & (dd <= np.timedelta64(90, 'D'))
        inds = np.flatnonzero(mask)
        if not len(inds):
            unmatched_rows.append(e.to_dict()); continue
        sub = pool.iloc[inds]
        score = (
            (sub['entry_time'] - e.entry_time).abs().dt.total_seconds().to_numpy() / 86400
            + (sub['h1_atr_pct'] - e.h1_atr_pct).abs().to_numpy() * .25
            + (sub['h4_atr_pct'] - e.h4_atr_pct).abs().to_numpy() * .25
            + abs(sub['touch_count'].to_numpy(float) - float(e.touch_count)) * .05
            + RNG.random(len(sub)) * 1e-8
        )
        chosen = inds[int(np.argmin(score))]; available[chosen] = False
        z = pool.iloc[chosen].to_dict(); z['pair_id'] = int(e.pair_id); z['match_tier'] = tier
        matched_rows.append(z)
    return pool, pd.DataFrame(matched_rows), pd.DataFrame(unmatched_rows)

def make_breakout_only(breakouts: pd.DataFrame, m1: pd.DataFrame, name: str) -> pd.DataFrame:
    if breakouts.empty: return pd.DataFrame()
    z = breakouts.copy(); z['entry_time'] = z['decision_time']
    price = m1.set_index('time')['open']; z['entry_price'] = z['entry_time'].map(price)
    z = z[z['entry_price'].notna()].copy(); z['population'] = name
    return dedup_custom_population(z, 120)

def make_retest_only(retests: pd.DataFrame, x: pd.DataFrame, m1: pd.DataFrame, name: str) -> pd.DataFrame:
    if retests.empty: return pd.DataFrame()
    z = retests.copy(); z['entry_time'] = z['retest_time']; z['decision_time'] = z['retest_time']
    price = m1.set_index('time')['open']; z['entry_price'] = z['entry_time'].map(price)
    ctx = x.set_index('decision_time')
    for c in ['weekday','server_hour','month','quarter','half','h1_atr14','h1_atr_pct','h1_atr_band','h4_atr14','h4_atr_pct','h4_atr_band']:
        z[c] = z['entry_time'].map(ctx[c])
    z = z[z['entry_price'].notna()].copy(); z['population'] = name
    return dedup_custom_population(z, 120)

def random_controls_like(x: pd.DataFrame, events: pd.DataFrame, name: str) -> pd.DataFrame:
    eligible = x[x['entry_price'].notna() & x['h1_atr_band'].notna() & x['h4_atr_band'].notna()].copy()
    if eligible.empty or events.empty: return pd.DataFrame()
    n = min(len(events), len(eligible)); sample = eligible.iloc[RNG.choice(len(eligible), size=n, replace=False)].copy()
    dirs = events['direction'].to_numpy().copy(); RNG.shuffle(dirs)
    sample['direction'] = dirs[:n]; sample['entry_time'] = sample['decision_time']; sample['population'] = name
    sample['level_quality'] = 'RANDOM'; sample['touch_count'] = np.nan
    return dedup_custom_population(sample, 120)

def summarize_discovery(grid: pd.DataFrame) -> tuple[dict[str, Any] | None, pd.DataFrame, pd.DataFrame]:
    if grid.empty: return None, pd.DataFrame(), pd.DataFrame()
    h1 = grid[(grid['population_name'] == 'E3_TRUE') & (grid['half'] == '2025H1')]
    rows = []
    for key, g in h1.groupby(['horizon','tp','sl']):
        s = g['net_cost2']; rows.append({'horizon': key[0], 'tp': key[1], 'sl': key[2], 'count': len(g), 'expectancy': s.mean(), 'pf': pf(s), 'pnl': s.sum()})
    ds = pd.DataFrame(rows).sort_values(['expectancy','pf'], ascending=False) if rows else pd.DataFrame()
    if ds.empty: return None, ds, pd.DataFrame()
    r = ds.iloc[0]; chosen = {'horizon': int(r.horizon), 'tp': float(r.tp), 'sl': float(r.sl)}
    cell = grid[(grid['population_name'] == 'E3_TRUE') & (grid['horizon'] == r.horizon) & (grid['tp'] == r.tp) & (grid['sl'] == r.sl)]
    out = []
    for half, g in cell.groupby('half'):
        s = g['net_cost2']; out.append({'half': half, **chosen, 'count': len(g), 'cost2_expectancy': s.mean(), 'cost2_pf': pf(s), 'cost2_pnl': s.sum()})
    return chosen, ds, pd.DataFrame(out)

def synthetic_tests() -> None:
    p = causal_percentile([1,2,3,100], 3, 3)
    assert np.isnan(p[:3]).all() and p[3] == 1.0
    times = pd.date_range('2025-01-01', periods=7, freq='h')
    h = pd.DataFrame({'time': times, 'source_close_time': times + pd.Timedelta(hours=1),
                      'open':[9,9,9,10,8,8,8], 'high':[10,10,11,15,10,9,9],
                      'low':[8,8,8,9,7,7,7], 'close':[9,9,10,14,10,9,9]})
    h['h1_atr14'] = 4.0; h['h1_index'] = np.arange(len(h))
    rx = build_confirmed_reactions(h)
    assert not rx.empty
    row = rx[rx.side.eq('RESISTANCE')].iloc[0]
    assert row.confirm_time == h.source_close_time.iloc[int(row.pivot_index)+2]

def main() -> None:
    synthetic_tests(); log('synthetic contract tests: PASS')
    m1 = combine_tf(BASE, 'm1'); m15 = combine_tf(BASE, 'm15'); h1 = combine_tf(BASE, 'h1'); h4 = combine_tf(BASE, 'h4')
    log(f'rows m1={len(m1)} m15={len(m15)} h1={len(h1)} h4={len(h4)}')
    h1x = make_h1_with_atr(h1)
    reactions = build_confirmed_reactions(h1x)
    reactions.to_csv(OUT / 'stage260_e3_confirmed_h1_reactions.csv', index=False)
    log(f'confirmed reactions={len(reactions)}')
    levels3 = build_level_context(h1x, reactions, 3)
    levels3.to_csv(OUT / 'stage260_e3_h1_level_context_t3plus.csv', index=False)
    log(f'level contexts={len(levels3)}')
    h1c = atr_context(h1, 'h1', 1000, 200)
    h4c = atr_context(h4, 'h4', 500, 100)
    x3 = build_m15_context(m15, levels3, h1c, h4c, m1)
    breakouts = detect_breakouts(x3, min_touches=3, population='E3_TRUE')
    retests, events, failures = complete_retest_acceptance(breakouts, x3, 'E3_TRUE')
    breakouts.to_csv(OUT / 'stage260_e3_breakouts_raw.csv', index=False)
    retests.to_csv(OUT / 'stage260_e3_first_retests.csv', index=False)
    failures.to_csv(OUT / 'stage260_e3_failed_after_breakout.csv', index=False)
    events.to_csv(OUT / 'stage260_e3_events_dedup120.csv', index=False)
    log(f'breakouts={len(breakouts)} retests={len(retests)} events={len(events)}')
    pool, matched, unmatched = build_controls(x3, events)
    pool.to_csv(OUT / 'stage260_e3_control_pool.csv', index=False)
    matched.to_csv(OUT / 'stage260_e3_matched_controls.csv', index=False)
    unmatched.to_csv(OUT / 'stage260_e3_unmatched_events.csv', index=False)
    log(f'controls matched={len(matched)} unmatched={len(unmatched)} pool={len(pool)}')
    ep, eg = evaluate_population(events, 'E3_TRUE', m1)
    cp, cg = evaluate_population(matched, 'MATCHED_CONTROL', m1)
    paths = pd.concat([ep, cp], ignore_index=True)
    grid = pd.concat([eg, cg], ignore_index=True)
    paths.to_csv(OUT / 'stage260_e3_path_metrics_event_control.csv', index=False)
    grid.to_csv(OUT / 'stage260_e3_strategy_grid_event_control.csv', index=False)
    path_summary = summarize_paths(paths); grid_summary = summarize_grid(grid)
    path_summary.to_csv(OUT / 'stage260_e3_path_summary_event_control.csv', index=False)
    grid_summary.to_csv(OUT / 'stage260_e3_strategy_summary_event_control.csv', index=False)
    paired_bootstrap(ep, cp, 120, 5000).to_csv(OUT / 'stage260_e3_paired_bootstrap120.csv', index=False)
    placebo_pops: list[tuple[str,pd.DataFrame]] = []
    for minutes in [-30,-15,15,30]:
        placebo_pops.append((f'TIME_{minutes:+d}', shift_events(events, minutes, m1, f'TIME_{minutes:+d}')))
    placebo_pops.append(('DIRECTION_REVERSED', reverse_events(events, 'DIRECTION_REVERSED')))
    placebo_pops.append(('BREAKOUT_ONLY', make_breakout_only(breakouts, m1, 'BREAKOUT_ONLY')))
    placebo_pops.append(('RETEST_ONLY', make_retest_only(retests, x3, m1, 'RETEST_ONLY')))
    levels2 = build_level_context(h1x, reactions, 2)
    x2 = build_m15_context(m15, levels2, h1c, h4c, m1)
    weak_breakouts = detect_breakouts(x2, min_touches=2, population='WEAK_T2')
    _, weak_events, _ = complete_retest_acceptance(weak_breakouts, x2, 'WEAK_T2')
    placebo_pops.append(('WEAK_T2', weak_events))
    for shift in [-.25,.25]:
        b = detect_breakouts(x3, min_touches=3, level_shift_atr=shift, population=f'LEVEL_{shift:+.2f}ATR')
        _, e, _ = complete_retest_acceptance(b, x3, f'LEVEL_{shift:+.2f}ATR')
        placebo_pops.append((f'LEVEL_{shift:+.2f}ATR', e))
    placebo_pops.append(('RANDOM_FLAG', random_controls_like(x3, events, 'RANDOM_FLAG')))
    placebo_pops.append(('WEEKDAY_SHIFT', weekday_shift(events, m1, 'WEEKDAY_SHIFT')))
    pp_all=[]; pg_all=[]; count_rows=[]
    for name, pop in placebo_pops:
        if pop is None or pop.empty:
            count_rows.append({'population_name': name, 'count': 0}); continue
        pp, pg = evaluate_population(pop, name, m1)
        pp_all.append(pp); pg_all.append(pg); count_rows.append({'population_name': name, 'count': len(pop), 'complete120': int((pp.horizon == 120).sum()) if not pp.empty else 0})
    pp_all = pd.concat(pp_all, ignore_index=True) if pp_all else pd.DataFrame()
    pg_all = pd.concat(pg_all, ignore_index=True) if pg_all else pd.DataFrame()
    pd.DataFrame(count_rows).to_csv(OUT / 'stage260_e3_placebo_counts.csv', index=False)
    pp_all.to_csv(OUT / 'stage260_e3_placebo_path_metrics.csv', index=False)
    pg_all.to_csv(OUT / 'stage260_e3_placebo_strategy_grid.csv', index=False)
    summarize_paths(pp_all).to_csv(OUT / 'stage260_e3_placebo_path_summary.csv', index=False)
    gs = summarize_grid(pg_all); gs.to_csv(OUT / 'stage260_e3_placebo_strategy_summary.csv', index=False)
    chosen, discovery, frozen = summarize_discovery(eg)
    discovery.to_csv(OUT / 'stage260_e3_discovery_2025H1_grid_summary.csv', index=False)
    frozen.to_csv(OUT / 'stage260_e3_frozen_discovery_cell_by_half.csv', index=False)
    paired120 = ep[ep.horizon.eq(120)].merge(cp[cp.horizon.eq(120)], on=['pair_id','horizon'], suffixes=('_event','_control'))
    paired120.to_csv(OUT / 'stage260_e3_paired_path120.csv', index=False)
    if len(paired120):
        event_mfe = float(paired120.mfe_event.mean()); control_mfe = float(paired120.mfe_control.mean())
        event_mae = float(paired120.mae_event.mean()); control_mae = float(paired120.mae_control.mean())
        mfe_diff = event_mfe-control_mfe; mae_diff = event_mae-control_mae
    else:
        event_mfe=control_mfe=event_mae=control_mae=mfe_diff=mae_diff=math.nan
    true_grid0 = grid_summary[(grid_summary.population_name == 'E3_TRUE') & (grid_summary.cost == 0.0)]
    best0 = true_grid0.sort_values('expectancy', ascending=False).head(1)
    best0_exp = float(best0.expectancy.iloc[0]) if len(best0) else math.nan
    h1r = frozen[frozen.half.eq('2025H1')] if not frozen.empty else pd.DataFrame()
    h2r = frozen[frozen.half.eq('2025H2')] if not frozen.empty else pd.DataFrame()
    criteria = {
        'criterion_1_mfe_diff_ge_2': bool(np.isfinite(mfe_diff) and mfe_diff >= 2.0),
        'criterion_2_mae_not_worse_gt_1': bool(np.isfinite(mae_diff) and mae_diff <= 1.0),
        'criterion_3_best_cost0_expectancy_ge_3': bool(np.isfinite(best0_exp) and best0_exp >= 3.0),
        'criterion_4_2025H1_cost2_positive_pf_ge_1_10': bool(len(h1r) and h1r.cost2_expectancy.iloc[0] > 0 and h1r.cost2_pf.iloc[0] >= 1.10),
        'criterion_5_2025H2_frozen_positive_pf_ge_1_10': bool(len(h2r) and h2r.cost2_expectancy.iloc[0] > 0 and h2r.cost2_pf.iloc[0] >= 1.10),
    }
    core_pass = criteria['criterion_1_mfe_diff_ge_2'] and criteria['criterion_2_mae_not_worse_gt_1'] and criteria['criterion_3_best_cost0_expectancy_ge_3']
    placebo_best=[]
    if not gs.empty:
        for name,g in gs[gs.cost.eq(0.0)].groupby('population_name'):
            r=g.sort_values('expectancy',ascending=False).iloc[0]
            placebo_best.append({'population_name':name,'best_cost0_expectancy':r.expectancy,'horizon':r.horizon,'tp':r.tp,'sl':r.sl,'pf':r.pf})
    pb = pd.DataFrame(placebo_best).sort_values('best_cost0_expectancy',ascending=False) if placebo_best else pd.DataFrame()
    pb.to_csv(OUT / 'stage260_e3_placebo_best_cost0.csv', index=False)
    status = 'GOLD_V3_260_E3_MULTI_REACTION_BREAKOUT_RETEST_REJECTED_AUDIT_ONLY' if not core_pass else 'GOLD_V3_260_E3_CORE_PASS_PLACEBO_STABILITY_REVIEW_REQUIRED_AUDIT_ONLY'
    summary = {
        'status': status, 'audit_only': True, 'live_ready': False, 'final_signal': False,
        'mt5_orders': 0, 'discord_notifications': 0, 'definition_commit': DEFINITION_COMMIT,
        'counts': {'confirmed_reactions': len(reactions), 'raw_breakouts': len(breakouts), 'first_retests': len(retests),
                   'dedup120_events': len(events), 'matched_controls': len(matched), 'unmatched_events': len(unmatched),
                   'complete_event_paths_120': int((ep.horizon==120).sum()) if not ep.empty else 0,
                   'complete_control_paths_120': int((cp.horizon==120).sum()) if not cp.empty else 0},
        'core_metrics': {'paired_event120_mfe_mean': event_mfe if np.isfinite(event_mfe) else None,
                         'paired_control120_mfe_mean': control_mfe if np.isfinite(control_mfe) else None,
                         'paired_mfe_difference': mfe_diff if np.isfinite(mfe_diff) else None,
                         'paired_event120_mae_mean': event_mae if np.isfinite(event_mae) else None,
                         'paired_control120_mae_mean': control_mae if np.isfinite(control_mae) else None,
                         'paired_mae_difference': mae_diff if np.isfinite(mae_diff) else None,
                         'best_full_grid_cost0_expectancy': best0_exp if np.isfinite(best0_exp) else None},
        'discovery_cell': chosen, 'frozen_by_half': frozen.to_dict(orient='records') if not frozen.empty else [],
        'criteria': criteria, 'early_core_pass': core_pass,
        'placebo_best_cost0': pb.to_dict(orient='records') if not pb.empty else [],
        'exact_stage258_regime_available': False, 'regime_proxy_invented': False,
        'preknown_holiday_short_session_calendar_available': False,
        'verdict': 'EARLY_REJECT_BEFORE_FEATURE_MINING' if not core_pass else 'REVIEW_REQUIRED',
        'operating_state': 'NO_LIVE_PROMOTION_AUDIT_ONLY',
    }
    (OUT/'stage260_e3_final_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    log(json.dumps(summary,ensure_ascii=False,indent=2,default=str))

if __name__ == '__main__':
    main()
