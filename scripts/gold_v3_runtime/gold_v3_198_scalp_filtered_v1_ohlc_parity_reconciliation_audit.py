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

STEP = 'GOLD_V3_198_SCALP_FILTERED_V1_OHLC_PARITY_RECONCILIATION_AUDIT_ONLY'
PRIMARY_COST = 3.0
STRESS_COST = 5.0
FILTER_CANDIDATE_ID = 'SCALP_002_tp15_sl5_hz64_SHORT'
FILTER_EXCLUDED_HOUR = 9


def progress(msg: str) -> None:
    print(f'[198 progress] {msg}', flush=True)


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


def add_time_cols(df: pd.DataFrame, entry_col: str = 'entry_dt') -> pd.DataFrame:
    x = df.copy()
    if x.empty:
        return x
    if entry_col in x.columns:
        x[entry_col] = pd.to_datetime(x[entry_col])
        x['entry_dt'] = x[entry_col]
    if 'exit_dt' in x.columns:
        x['exit_dt'] = pd.to_datetime(x['exit_dt'])
    x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    x['entry_date'] = x['entry_dt'].dt.date.astype(str)
    x['entry_hour'] = x['entry_dt'].dt.hour.astype(int)
    return x.sort_values(['entry_dt', 'candidate_id'] if 'candidate_id' in x.columns else ['entry_dt']).reset_index(drop=True)


def make_key(df: pd.DataFrame) -> pd.Series:
    x = add_time_cols(df)
    return x['candidate_id'].astype(str) + '|' + pd.to_datetime(x['entry_dt']).dt.strftime('%Y-%m-%d %H:%M:%S')


def selected_priority(selected: pd.DataFrame) -> dict[str, float]:
    s = selected.copy().reset_index(drop=True)
    if 'profit_rate_score' in s.columns:
        return dict(zip(s['candidate_id'].astype(str), pd.to_numeric(s['profit_rate_score'], errors='coerce').fillna(0.0)))
    if 'selected_order' in s.columns:
        return {str(r['candidate_id']): 1000.0 - float(r['selected_order']) for _, r in s.iterrows()}
    return {str(cid): 1000.0 - i for i, cid in enumerate(s['candidate_id'].astype(str).tolist())}


def apply_filtered_v1(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = add_time_cols(df)
    removed_mask = x['candidate_id'].astype(str).eq(FILTER_CANDIDATE_ID) & x['entry_hour'].eq(FILTER_EXCLUDED_HOUR)
    return x[~removed_mask].copy().reset_index(drop=True), x[removed_mask].copy().reset_index(drop=True)


def resolved_priority(df: pd.DataFrame, priority: dict[str, float]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = add_time_cols(df)
    x['priority_score'] = x['candidate_id'].astype(str).map(priority).fillna(0.0)
    x = x.sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).reset_index(drop=True)
    kept = []
    active_exit = None
    used_entry_times: set[pd.Timestamp] = set()
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


def build_detector_entries(feat: pd.DataFrame, selected: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
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
        rows.append(m)
    det = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return add_time_cols(det) if not det.empty else det, problems


def recompute_outcomes(detector_entries: pd.DataFrame, m5: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
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
        scored['pnl_net_cost3'] = pd.to_numeric(scored['pnl_raw'], errors='coerce') - PRIMARY_COST
        scored['pnl_net_cost5'] = pd.to_numeric(scored['pnl_raw'], errors='coerce') - STRESS_COST
        out.append(scored)
    return add_time_cols(pd.concat(out, ignore_index=True)) if out else pd.DataFrame()


def compare_sets(left: pd.DataFrame, right: pd.DataFrame, left_name: str, right_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    l = add_time_cols(left).copy() if not left.empty else left.copy()
    r = add_time_cols(right).copy() if not right.empty else right.copy()
    if not l.empty:
        l['key'] = make_key(l)
    if not r.empty:
        r['key'] = make_key(r)
    ls = set(l['key'].astype(str)) if not l.empty else set()
    rs = set(r['key'].astype(str)) if not r.empty else set()
    summary = pd.DataFrame([{
        'left_name': left_name,
        'right_name': right_name,
        'left_rows': int(len(l)),
        'right_rows': int(len(r)),
        'left_unique_keys': int(len(ls)),
        'right_unique_keys': int(len(rs)),
        'left_only_keys': int(len(ls - rs)),
        'right_only_keys': int(len(rs - ls)),
        'matched_keys': int(len(ls & rs)),
        'parity_pass': len(ls - rs) == 0 and len(rs - ls) == 0,
    }])
    left_only = l[l['key'].astype(str).isin(ls - rs)].copy() if not l.empty else pd.DataFrame()
    right_only = r[r['key'].astype(str).isin(rs - ls)].copy() if not r.empty else pd.DataFrame()
    return summary, left_only, right_only


def classify_detector_only(det_only: pd.DataFrame, recomputed: pd.DataFrame, raw_min: pd.Timestamp | None, raw_max: pd.Timestamp | None, m5: pd.DataFrame) -> pd.DataFrame:
    if det_only.empty:
        return pd.DataFrame()
    x = add_time_cols(det_only).copy()
    scored_keys = set(make_key(recomputed).astype(str)) if not recomputed.empty else set()
    x['key'] = make_key(x)
    m5_times = pd.to_datetime(m5['dt']).sort_values().reset_index(drop=True) if not m5.empty and 'dt' in m5.columns else pd.Series(dtype='datetime64[ns]')
    m5_max = pd.Timestamp(m5_times.max()) if len(m5_times) else pd.NaT
    m5_min = pd.Timestamp(m5_times.min()) if len(m5_times) else pd.NaT
    reasons = []
    m5_bars_after = []
    for _, r in x.iterrows():
        entry = pd.Timestamp(r['entry_dt'])
        if len(m5_times):
            bars_after = int((m5_times > entry).sum())
        else:
            bars_after = 0
        m5_bars_after.append(bars_after)
        if raw_min is not None and entry < raw_min:
            reasons.append('before_stage191_raw_min_entry_dt')
        elif raw_max is not None and entry > raw_max:
            reasons.append('after_stage191_raw_max_entry_dt')
        elif str(r['key']) not in scored_keys:
            if len(m5_times) == 0 or entry >= m5_max:
                reasons.append('not_m5_scorable_after_entry')
            else:
                reasons.append('detected_but_not_recomputed_scored_unknown')
        else:
            reasons.append('recomputed_scored_but_absent_from_stage191_artifact')
    x['m5_min_dt'] = str(m5_min) if not pd.isna(m5_min) else ''
    x['m5_max_dt'] = str(m5_max) if not pd.isna(m5_max) else ''
    x['m5_bars_after_entry'] = m5_bars_after
    x['classification'] = reasons
    return x


def count_by(df: pd.DataFrame, cols: list[str], value_name: str = 'count') -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return df.groupby(cols, dropna=False).size().reset_index(name=value_name).sort_values(value_name, ascending=False)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '198'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage193 selected and Stage191 artifact')
    selected = read_csv_any(root / '193' / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    stage191_raw = read_csv_any(root / '191' / 'gold_v3_191_scalping_top_trades_cost3.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_watchlist'})
    if stage191_raw.empty:
        blockers.append({'id': 'missing_stage191_top_trades_cost3_artifact'})

    frames: dict[str, pd.DataFrame] = {}
    source_rows: list[dict[str, Any]] = []
    if not blockers:
        progress('load OHLC through Stage177 contract')
        for tf in ['m15', 'm5', 'h1', 'h4', 'd1']:
            frames[tf], diag = s177.combine(tf, data_dir)
            source_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({'id': 'missing_ohlc', 'tf': tf})
        if source_rows:
            save(pd.DataFrame(source_rows), out / 'gold_v3_198_source_coverage.csv')

    detector = pd.DataFrame()
    detector_filtered = pd.DataFrame()
    recomputed = pd.DataFrame()
    recomputed_filtered = pd.DataFrame()
    stage191_filtered = pd.DataFrame()
    stage191_removed = pd.DataFrame()
    detector_removed = pd.DataFrame()
    recomputed_removed = pd.DataFrame()
    base_one = pd.DataFrame()
    recomputed_one = pd.DataFrame()
    comparisons = []
    det_vs_recomp_left_only = pd.DataFrame()
    det_vs_recomp_right_only = pd.DataFrame()
    recomp_vs_art_left_only = pd.DataFrame()
    recomp_vs_art_right_only = pd.DataFrame()
    classified = pd.DataFrame()
    detector_problems: list[dict[str, Any]] = []

    if not blockers:
        selected_ids = set(selected['candidate_id'].astype(str))
        stage191_selected = add_time_cols(stage191_raw[stage191_raw['candidate_id'].astype(str).isin(selected_ids)].copy())
        stage191_filtered, stage191_removed = apply_filtered_v1(stage191_selected)
        save(stage191_selected, out / 'gold_v3_198_stage191_selected_before_filter.csv')
        save(stage191_filtered, out / 'gold_v3_198_stage191_selected_after_filtered_v1.csv')
        save(stage191_removed, out / 'gold_v3_198_stage191_removed_by_filtered_v1.csv')

        progress('build closed-OHLC detector entries')
        feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
        detector, detector_problems = build_detector_entries(feat, selected)
        detector_filtered, detector_removed = apply_filtered_v1(detector)
        save(detector, out / 'gold_v3_198_ohlc_detector_entries_before_filter.csv')
        save(detector_filtered, out / 'gold_v3_198_ohlc_detector_entries_after_filtered_v1.csv')
        save(detector_removed, out / 'gold_v3_198_ohlc_detector_removed_by_filtered_v1.csv')

        progress('recompute TP/SL/horizon outcomes from M5 OHLC')
        recomputed = recompute_outcomes(detector, frames['m5'], selected)
        recomputed_filtered, recomputed_removed = apply_filtered_v1(recomputed)
        save(recomputed, out / 'gold_v3_198_ohlc_recomputed_scored_trades_before_filter.csv')
        save(recomputed_filtered, out / 'gold_v3_198_ohlc_recomputed_scored_trades_after_filtered_v1.csv')
        save(recomputed_removed, out / 'gold_v3_198_ohlc_recomputed_removed_by_filtered_v1.csv')

        priority = selected_priority(selected)
        base_one = resolved_priority(stage191_filtered, priority)
        recomputed_one = resolved_priority(recomputed_filtered, priority)
        save(base_one, out / 'gold_v3_198_stage191_filtered_v1_one_position.csv')
        save(recomputed_one, out / 'gold_v3_198_ohlc_recomputed_filtered_v1_one_position.csv')

        for left, right, ln, rn, prefix in [
            (detector_filtered, recomputed_filtered, 'ohlc_detector_filtered_entries', 'ohlc_recomputed_scored_filtered_trades', 'detector_vs_recomputed'),
            (recomputed_filtered, stage191_filtered, 'ohlc_recomputed_scored_filtered_trades', 'stage191_artifact_filtered_trades', 'recomputed_vs_stage191_artifact'),
            (recomputed_one, base_one, 'ohlc_recomputed_filtered_one_position', 'stage191_filtered_one_position', 'one_position_recomputed_vs_stage191'),
        ]:
            comp, lo, ro = compare_sets(left, right, ln, rn)
            comp['comparison_id'] = prefix
            comparisons.append(comp)
            save(lo, out / f'gold_v3_198_{prefix}_left_only.csv')
            save(ro, out / f'gold_v3_198_{prefix}_right_only.csv')
            if prefix == 'detector_vs_recomputed':
                det_vs_recomp_left_only, det_vs_recomp_right_only = lo, ro
            if prefix == 'recomputed_vs_stage191_artifact':
                recomp_vs_art_left_only, recomp_vs_art_right_only = lo, ro

        raw_min = pd.Timestamp(stage191_filtered['entry_dt'].min()) if not stage191_filtered.empty else None
        raw_max = pd.Timestamp(stage191_filtered['entry_dt'].max()) if not stage191_filtered.empty else None
        classified = classify_detector_only(recomp_vs_art_left_only, recomputed_filtered, raw_min, raw_max, frames['m5'])
        save(classified, out / 'gold_v3_198_recomputed_only_vs_stage191_classified.csv')
        save(count_by(classified, ['classification']), out / 'gold_v3_198_recomputed_only_classification_counts.csv')
        save(count_by(classified, ['month', 'candidate_id', 'classification']), out / 'gold_v3_198_recomputed_only_by_month_candidate.csv')

    comparison_summary = pd.concat(comparisons, ignore_index=True) if comparisons else pd.DataFrame()
    if not comparison_summary.empty:
        save(comparison_summary, out / 'gold_v3_198_parity_comparison_summary.csv')

    ready = len(blockers) == 0
    det_vs_recomp_pass = bool(comparison_summary.loc[comparison_summary['comparison_id'].eq('detector_vs_recomputed'), 'parity_pass'].iloc[0]) if ready and not comparison_summary.empty and comparison_summary['comparison_id'].eq('detector_vs_recomputed').any() else False
    recomputed_vs_artifact_pass = bool(comparison_summary.loc[comparison_summary['comparison_id'].eq('recomputed_vs_stage191_artifact'), 'parity_pass'].iloc[0]) if ready and not comparison_summary.empty and comparison_summary['comparison_id'].eq('recomputed_vs_stage191_artifact').any() else False
    one_position_pass = bool(comparison_summary.loc[comparison_summary['comparison_id'].eq('one_position_recomputed_vs_stage191'), 'parity_pass'].iloc[0]) if ready and not comparison_summary.empty and comparison_summary['comparison_id'].eq('one_position_recomputed_vs_stage191').any() else False
    decision = 'STAGE198_OHLC_RECOMPUTE_PARITY_PASS_STAGE191_ARTIFACT_DIFF_FOUND_AUDIT_ONLY' if ready and det_vs_recomp_pass and not recomputed_vs_artifact_pass else ('STAGE198_OHLC_AND_ARTIFACT_PARITY_PASS_AUDIT_ONLY' if ready and det_vs_recomp_pass and recomputed_vs_artifact_pass else ('STAGE198_READY_REVIEW_REQUIRED_AUDIT_ONLY' if ready else 'STAGE198_BLOCKED'))

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'purpose': 'Confirm whether SCALP_ONE_POSITION_FILTERED_V1 entry/outcome can be reproduced from closed OHLC and isolate Stage191 artifact differences.',
        'filtered_rule': f'{FILTER_CANDIDATE_ID} excluded when MT5 entry_hour == {FILTER_EXCLUDED_HOUR}',
        'selected_candidate_count': int(len(selected)) if not selected.empty else 0,
        'stage191_selected_filtered_rows': int(len(stage191_filtered)) if not stage191_filtered.empty else 0,
        'ohlc_detector_filtered_rows': int(len(detector_filtered)) if not detector_filtered.empty else 0,
        'ohlc_recomputed_filtered_rows': int(len(recomputed_filtered)) if not recomputed_filtered.empty else 0,
        'stage191_filtered_one_position_rows': int(len(base_one)) if not base_one.empty else 0,
        'ohlc_recomputed_filtered_one_position_rows': int(len(recomputed_one)) if not recomputed_one.empty else 0,
        'detector_vs_recomputed_parity_pass': det_vs_recomp_pass,
        'recomputed_vs_stage191_artifact_parity_pass': recomputed_vs_artifact_pass,
        'one_position_recomputed_vs_stage191_parity_pass': one_position_pass,
        'detector_rule_problem_count': int(len(detector_problems)),
        'recomputed_only_vs_stage191_count': int(len(recomp_vs_art_left_only)) if not recomp_vs_art_left_only.empty else 0,
        'stage191_only_vs_recomputed_count': int(len(recomp_vs_art_right_only)) if not recomp_vs_art_right_only.empty else 0,
        'recomputed_only_top_classification': str(classified['classification'].value_counts().idxmax()) if not classified.empty else '',
        'recomputed_only_top_classification_count': int(classified['classification'].value_counts().max()) if not classified.empty else 0,
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        'ohlc_reproducibility_statement': 'Entry detection uses only closed OHLC-derived features and MT5 hour. Recomputed outcomes use M5 OHLC only after entry for audit scoring.',
        'future_info_policy': 'M5 future TP/SL/horizon is used only after entry for scoring; no future outcome is used in entry detector.',
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
    (out / 'gold_v3_198_summary.json').write_text(json.dumps({**summary, 'blockers': blockers, 'detector_problems': detector_problems}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_198_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 198 PASTE_ME_SCALP_FILTERED_V1_OHLC_PARITY_RECONCILIATION_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PARITY_COMPARISON_SUMMARY', show(comparison_summary, 20)]
    lines += ['', 'RECOMPUTED_ONLY_CLASSIFICATION_COUNTS', show(read_csv_any(out / 'gold_v3_198_recomputed_only_classification_counts.csv'), 30)]
    lines += ['', 'RECOMPUTED_ONLY_BY_MONTH_CANDIDATE_SAMPLE', show(read_csv_any(out / 'gold_v3_198_recomputed_only_by_month_candidate.csv'), 80)]
    lines += ['', 'RECOMPUTED_ONLY_SAMPLE', show(classified, 80)]
    lines += ['', 'STAGE191_ONLY_SAMPLE', show(recomp_vs_art_right_only, 40)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage198 is audit-only. It separates two questions: (1) can the detector entries be recomputed from closed OHLC, and (2) does the older Stage191 artifact contain exactly the same rows.',
        'If detector_vs_recomputed_parity_pass is True, the OHLC detector and M5 OHLC scoring are internally reproducible.',
        'If recomputed_vs_stage191_artifact_parity_pass is False while detector_vs_recomputed is True, the mismatch is an artifact-scope issue, not an OHLC reproducibility failure.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
