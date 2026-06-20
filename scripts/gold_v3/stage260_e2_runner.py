"""Stage260 E2 audit-only orchestration. No live hooks, orders, or notifications."""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence
import numpy as np
import pandas as pd
from stage260_e2_common import *
from stage260_e2_event import *
from stage260_e2_evaluation import *

def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def _write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

def readiness_audit(config_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Check required source files and timestamp parity without running E2."""
    cfg_data = json.loads(Path(config_path).read_text(encoding='utf-8'))
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {'status': STATUS, 'audit_only': True, 'latest_row_contract': 'closed', 'csv_time_contract': 'open_time', 'files': {}, 'source_parity': {}, 'regime_timeline': {}, 'blocked_reasons': []}
    sources = cfg_data.get('sources', {})
    if len(sources) < 2:
        report['blocked_reasons'].append('two independently acquired sources are required for source parity')
    loaded: dict[str, dict[str, pd.DataFrame]] = {}
    for source_name, tf_map in sources.items():
        loaded[source_name] = {}
        for tf in TIMEFRAME_MINUTES:
            p = tf_map.get(tf)
            key = f'{source_name}.{tf}'
            exists = bool(p and Path(p).is_file())
            report['files'][key] = {'path': p, 'exists': exists}
            if not exists:
                report['blocked_reasons'].append(f'missing {key}')
                continue
            try:
                frame = read_mt5_csv(p, tf)
                loaded[source_name][tf] = frame
                report['files'][key].update({'rows': int(len(frame)), 'first_open': str(frame['time'].iloc[0]), 'last_open': str(frame['time'].iloc[-1]), 'last_close_available': str(frame['source_close_time'].iloc[-1]), 'latest_row_kept': True})
            except Exception as exc:
                report['files'][key]['error'] = f'{type(exc).__name__}: {exc}'
                report['blocked_reasons'].append(f'invalid {key}')
    names = list(loaded)
    if len(names) >= 2:
        for tf in TIMEFRAME_MINUTES:
            if tf in loaded[names[0]] and tf in loaded[names[1]]:
                parity = source_parity(loaded[names[0]][tf], loaded[names[1]][tf], tf)
                report['source_parity'][tf] = parity
                if not parity['pass']:
                    report['blocked_reasons'].append(f'source parity failed for {tf}')
    regime_path = cfg_data.get('regime_timeline')
    report['regime_timeline']['path'] = regime_path
    if not regime_path or not Path(regime_path).is_file():
        report['regime_timeline']['exists'] = False
        report['blocked_reasons'].append('authoritative Stage258-compatible regime timeline missing')
    else:
        try:
            regime = load_regime_timeline(regime_path)
            report['regime_timeline'].update({'exists': True, 'rows': int(len(regime)), 'start': str(regime['regime_time'].min()), 'end': str(regime['regime_time'].max())})
        except Exception as exc:
            report['regime_timeline'].update({'exists': True, 'error': f'{type(exc).__name__}: {exc}'})
            report['blocked_reasons'].append('invalid regime timeline')
    report['ready_for_e2'] = len(report['blocked_reasons']) == 0
    _write_json(report, out_dir / 'stage260_e2_data_readiness.json')
    return report

def run_e2(config_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    cfg_data = json.loads(Path(config_path).read_text(encoding='utf-8'))
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ready = readiness_audit(config_path, out_dir)
    if not ready['ready_for_e2']:
        raise AuditContractError('E2 blocked by readiness audit; see stage260_e2_data_readiness.json')
    cfg = E2Config(**cfg_data.get('e2', {}))
    source_name = cfg_data['authoritative_source']
    source_files = cfg_data['sources'][source_name]
    m1 = read_mt5_csv(source_files['m1'], 'm1')
    h1 = read_mt5_csv(source_files['h1'], 'h1')
    regime = load_regime_timeline(cfg_data['regime_timeline'])
    m1_sessions, calendar = build_session_calendar(m1, cfg.session_gap_minutes)
    _write_csv(calendar, out_dir / 'stage260_e2_mt5_session_calendar.csv')
    h1_ctx = build_h1_context(h1, cfg)
    merged = causal_merge_context(m1_sessions, h1_ctx, regime)
    merged = attach_session_levels(merged, calendar)
    events_raw = add_entry_prices(detect_e2_events(merged, cfg), merged)
    events_raw = add_live_safe_flags(events_raw, cfg, cfg.base_horizon_minutes)
    events_dedup = dedup_fixed_horizon(events_raw, cfg.base_horizon_minutes)
    _write_csv(events_raw, out_dir / 'stage260_e2_events_raw.csv')
    _write_csv(events_dedup, out_dir / 'stage260_e2_events_dedup_120m.csv')
    eligible = filter_live_evaluable(events_dedup).reset_index(drop=True)
    eligible['pair_id'] = np.arange(len(eligible), dtype=int)
    control_pool = build_control_pool(merged, events_raw, cfg)
    control_pool = add_live_safe_flags(control_pool, cfg, cfg.base_horizon_minutes)
    control_pool = filter_live_evaluable(control_pool)
    controls, unmatched = match_controls(eligible, control_pool, cfg.random_seed)
    _write_csv(control_pool, out_dir / 'stage260_e2_control_pool.csv')
    _write_csv(controls, out_dir / 'stage260_e2_matched_controls.csv')
    _write_csv(unmatched, out_dir / 'stage260_e2_unmatched_events.csv')
    populations: dict[str, pd.DataFrame] = {'EVENT': eligible, 'MATCHED_CONTROL': controls}
    for shift in (-15, -10, -5, 5, 10, 15):
        populations[f'TIME_{shift:+d}'] = shifted_time_placebo(eligible, merged, shift)
    populations['DIRECTION_REVERSED'] = reverse_direction_placebo(eligible)
    populations['RANDOM_FLAG'] = random_flag_placebo(eligible, control_pool, cfg.random_seed)
    populations['DATE_RANDOMIZED'] = randomized_date_placebo(eligible, control_pool, cfg.random_seed + 1)
    populations['WEEKDAY_SWAPPED'] = weekday_swap_placebo(eligible, control_pool, cfg.random_seed + 2)
    populations['WRONG_REGIME'] = wrong_regime_placebo(eligible, control_pool, cfg.random_seed + 3)
    breach = add_entry_prices(detect_e2_events(merged, cfg, require_reclaim=False), merged)
    breach = add_live_safe_flags(breach, cfg, cfg.base_horizon_minutes)
    populations['BREACH_ONLY'] = filter_live_evaluable(breach)
    for shift in (-1.0, -0.5, 0.5, 1.0):
        shifted = add_entry_prices(detect_e2_events(merged, cfg, level_shift_atr=shift), merged)
        shifted = add_live_safe_flags(shifted, cfg, cfg.base_horizon_minutes)
        populations[f'LEVEL_{shift:+.1f}ATR'] = filter_live_evaluable(shifted)
    path_frames: list[pd.DataFrame] = []
    first_touch_frames: list[pd.DataFrame] = []
    for pop_name, pop in populations.items():
        if pop.empty:
            continue
        for horizon in HORIZONS:
            paths = evaluate_anchor_paths(pop, merged, horizon)
            if not paths.empty:
                paths['population_name'] = pop_name
                path_frames.append(paths)
            for tp in TP_VALUES:
                for sl in SL_VALUES:
                    ft = simulate_first_touch(pop, merged, horizon, tp, sl)
                    if not ft.empty:
                        ft['population_name'] = pop_name
                        first_touch_frames.append(ft)
    path_all = pd.concat(path_frames, ignore_index=True) if path_frames else pd.DataFrame()
    ft_all = pd.concat(first_touch_frames, ignore_index=True) if first_touch_frames else pd.DataFrame()
    _write_csv(path_all, out_dir / 'stage260_e2_path_metrics_all_populations.csv')
    _write_csv(ft_all, out_dir / 'stage260_e2_first_touch_all_populations.csv')
    summaries: list[dict[str, Any]] = []
    if not path_all.empty:
        for keys, g in path_all.groupby(['population_name', 'horizon_minutes'], dropna=False):
            item = {'population': keys[0], 'horizon_minutes': int(keys[1])}
            item.update(summary_stats(g))
            summaries.append(item)
    path_summary = pd.DataFrame(summaries)
    _write_csv(path_summary, out_dir / 'stage260_e2_population_path_summary.csv')
    strategy_summaries: list[dict[str, Any]] = []
    if not ft_all.empty:
        group_cols = ['population_name', 'horizon_minutes', 'tp', 'sl']
        for keys, g in ft_all.groupby(group_cols, dropna=False):
            for cost in COSTS:
                item = dict(zip(group_cols, keys))
                item['cost'] = cost
                item.update(summary_stats(g, f'net_pnl_cost{int(cost)}'))
                strategy_summaries.append(item)
    strategy_summary = pd.DataFrame(strategy_summaries)
    _write_csv(strategy_summary, out_dir / 'stage260_e2_strategy_surface_summary.csv')
    path_segmented = segmented_summaries(path_all, fixed_columns=('population_name', 'horizon_minutes'))
    _write_csv(path_segmented, out_dir / 'stage260_e2_segmented_path_summary.csv')
    cost2_rows = ft_all.copy()
    if not cost2_rows.empty:
        strategy_segmented = segmented_summaries(cost2_rows, pnl_col='net_pnl_cost2', fixed_columns=('population_name', 'horizon_minutes', 'tp', 'sl'))
    else:
        strategy_segmented = pd.DataFrame()
    _write_csv(strategy_segmented, out_dir / 'stage260_e2_segmented_cost2_strategy_summary.csv')
    strategy_diff = pd.DataFrame()
    if not strategy_summary.empty:
        key_cols = ['horizon_minutes', 'tp', 'sl', 'cost']
        event_s = strategy_summary[strategy_summary['population_name'] == 'EVENT'].copy()
        control_s = strategy_summary[strategy_summary['population_name'] == 'MATCHED_CONTROL'].copy()
        strategy_diff = event_s.merge(control_s, on=key_cols, suffixes=('_event', '_control'))
        for metric in ('expectancy', 'pnl', 'pf'):
            a, b = (f'{metric}_event', f'{metric}_control')
            if a in strategy_diff.columns and b in strategy_diff.columns:
                strategy_diff[f'{metric}_difference'] = strategy_diff[a] - strategy_diff[b]
    _write_csv(strategy_diff, out_dir / 'stage260_e2_event_vs_matched_control_strategy_difference.csv')
    paired_path = []
    if not path_all.empty:
        e = path_all[path_all['population_name'] == 'EVENT']
        c = path_all[path_all['population_name'] == 'MATCHED_CONTROL']
        paired = e.merge(c, on=['pair_id', 'horizon_minutes'], suffixes=('_event', '_control'))
        for horizon, g in paired.groupby('horizon_minutes'):
            for metric in ('mfe', 'mae', 'mfe_mae_ratio'):
                item = {'horizon_minutes': int(horizon), 'metric': metric}
                item.update(paired_bootstrap_difference(g[f'{metric}_event'], g[f'{metric}_control'], cfg.random_seed))
                paired_path.append(item)
    paired_path_df = pd.DataFrame(paired_path)
    _write_csv(paired_path_df, out_dir / 'stage260_e2_paired_event_control_bootstrap.csv')
    final = {'status': STATUS, 'audit_only': True, 'live_ready': False, 'final_signal': False, 'orders_generated': 0, 'notifications_sent': 0, 'event_definition': asdict(cfg), 'source_parity': ready['source_parity'], 'counts': {'raw_events': int(len(events_raw)), 'dedup_events': int(len(events_dedup)), 'eligible_events': int(len(eligible)), 'matched_controls': int(len(controls)), 'unmatched_events': int(len(unmatched))}, 'selection_contract': '2025H1 discovery; 2025H2 selection; 2026 fixed with no changes', 'verdict': 'POPULATION_RESULTS_GENERATED_NO_LIVE_PROMOTION', 'unresolved': ['Bid/Ask, real spread, commission, and tick slippage are not modeled', 'holiday shortened-session live parity needs a pre-known session calendar', '2026 is not a pristine unseen holdout']}
    _write_json(final, out_dir / 'stage260_e2_final_summary.json')
    return final

def parse_args(argv: Sequence[str] | None=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True, help='JSON configuration file')
    p.add_argument('--output-dir', required=True)
    p.add_argument('--mode', choices=('readiness', 'e2'), default='readiness')
    return p.parse_args(argv)

def main(argv: Sequence[str] | None=None) -> int:
    args = parse_args(argv)
    try:
        if args.mode == 'readiness':
            result = readiness_audit(args.config, args.output_dir)
        else:
            result = run_e2(args.config, args.output_dir)
    except Exception as exc:
        print(json.dumps({'status': STATUS, 'error': f'{type(exc).__name__}: {exc}'}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0

if __name__ == "__main__":
    sys.exit(main())
