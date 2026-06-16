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
import gold_v3_179_monthly_winrate_tradecount_audit as s179

STEP = 'GOLD_V3_188_PRIMARY_ABC_CAP_LIVE_PARITY_AUDIT_ONLY'
DEFAULT_LIVE_N = 96
EPS = 1e-9

PRIMARY_CANDIDATES = [
    {
        'candidate_id': 'A_PRECISION_BASE',
        'priority': 1,
        'rule': 'd1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347',
        'direction': 'LONG',
        'tp': 40.0,
        'sl': 20.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'C_BALANCED_CAP60',
        'priority': 2,
        'rule': 'd1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60',
        'direction': 'LONG',
        'tp': 30.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'B_HIGH_FREQUENCY_CAP40',
        'priority': 3,
        'rule': 'd1_dist_close_atr28<=-0.394892 & h1_atr14<=40',
        'direction': 'LONG',
        'tp': 50.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
]

COMPARE_COLS = [
    'm15_open', 'm15_high', 'm15_low', 'm15_close',
    'h1_atr14', 'h4_body_atr14', 'd1_dist_close_atr28',
    'h1_close', 'h4_close', 'd1_close',
]


def progress(msg: str) -> None:
    print(f'[188 progress] {msg}', flush=True)


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def choose_priority(fired: list[str]) -> str:
    if not fired:
        return 'NO_SIGNAL'
    order = {c['candidate_id']: int(c['priority']) for c in PRIMARY_CANDIDATES}
    return sorted(fired, key=lambda x: (order.get(x, 999), x))[0]


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    fired_cols = []
    for c in PRIMARY_CANDIDATES:
        mask, problems = s179.literal_rule_mask(c['rule'], out)
        col = f"signal_{c['candidate_id']}"
        out[col] = False if problems else mask.astype(bool)
        fired_cols.append(col)
    fired_lists = []
    priority = []
    for _, row in out.iterrows():
        fired = [c['candidate_id'] for c in PRIMARY_CANDIDATES if bool(row.get(f"signal_{c['candidate_id']}", False))]
        fired_lists.append('|'.join(fired))
        priority.append(choose_priority(fired))
    out['fired_candidates'] = fired_lists
    out['priority_signal'] = priority
    return out


def latest_ready_rows(data: pd.DataFrame, live_n: int) -> pd.DataFrame:
    needed = ['dt', 'd1_dist_close_atr28', 'h4_body_atr14', 'h1_atr14']
    ok = data.copy()
    for c in needed:
        if c not in ok.columns:
            return pd.DataFrame()
        ok = ok[ok[c].notna()]
    return ok.sort_values('dt').tail(live_n).copy()


def truncate_frame(df: pd.DataFrame, dt: pd.Timestamp) -> pd.DataFrame:
    if df.empty or 'dt' not in df.columns:
        return pd.DataFrame()
    return df[df['dt'] <= dt].copy().sort_values('dt').reset_index(drop=True)


def compare_one(batch_row: pd.Series, live_row: pd.Series) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dt = pd.to_datetime(batch_row['dt'])
    cmp_rows: list[dict[str, Any]] = []
    max_abs = 0.0
    mismatch_cols: list[str] = []
    for col in COMPARE_COLS:
        if col not in batch_row.index or col not in live_row.index:
            cmp_rows.append({'dt': str(dt), 'field': col, 'status': 'MISSING_FIELD'})
            mismatch_cols.append(col)
            continue
        bv = pd.to_numeric(pd.Series([batch_row[col]]), errors='coerce').iloc[0]
        lv = pd.to_numeric(pd.Series([live_row[col]]), errors='coerce').iloc[0]
        if pd.isna(bv) and pd.isna(lv):
            diff = 0.0
            match = True
        elif pd.notna(bv) and pd.notna(lv):
            diff = abs(float(bv) - float(lv))
            match = diff <= EPS
        else:
            diff = math.nan
            match = False
        if pd.notna(diff):
            max_abs = max(max_abs, float(diff))
        if not match:
            mismatch_cols.append(col)
        cmp_rows.append({
            'dt': str(dt),
            'field': col,
            'batch_value': bv,
            'live_step_value': lv,
            'abs_diff': diff,
            'match': bool(match),
            'status': 'OK' if match else 'MISMATCH',
        })
    signal_match = True
    sig_mismatch: list[str] = []
    signal_fields = [f"signal_{c['candidate_id']}" for c in PRIMARY_CANDIDATES] + ['fired_candidates', 'priority_signal']
    for col in signal_fields:
        b = batch_row.get(col, '')
        l = live_row.get(col, '')
        if bool(b) != bool(l) if col.startswith('signal_') else str(b) != str(l):
            signal_match = False
            sig_mismatch.append(col)
    row = {
        'dt': str(dt),
        'batch_priority_signal': str(batch_row.get('priority_signal', '')),
        'live_priority_signal': str(live_row.get('priority_signal', '')),
        'batch_fired_candidates': str(batch_row.get('fired_candidates', '')),
        'live_fired_candidates': str(live_row.get('fired_candidates', '')),
        'feature_match': len(mismatch_cols) == 0,
        'signal_match': signal_match,
        'row_match': bool(len(mismatch_cols) == 0 and signal_match),
        'max_abs_feature_diff': max_abs,
        'feature_mismatch_cols': '|'.join(mismatch_cols),
        'signal_mismatch_cols': '|'.join(sig_mismatch),
    }
    return row, cmp_rows


def make_latest_snapshot(row: pd.Series) -> dict[str, Any]:
    fired = str(row.get('fired_candidates', ''))
    priority = str(row.get('priority_signal', 'NO_SIGNAL'))
    chosen = next((c for c in PRIMARY_CANDIDATES if c['candidate_id'] == priority), None)
    return {
        'latest_closed_m15_dt': str(row.get('dt', '')),
        'priority_signal': priority,
        'fired_candidates': fired,
        'direction': chosen['direction'] if chosen else '',
        'tp': chosen['tp'] if chosen else math.nan,
        'sl': chosen['sl'] if chosen else math.nan,
        'horizon_m5': chosen['horizon_m5'] if chosen else math.nan,
        'd1_dist_close_atr28': row.get('d1_dist_close_atr28', math.nan),
        'h4_body_atr14': row.get('h4_body_atr14', math.nan),
        'h1_atr14': row.get('h1_atr14', math.nan),
        'm15_close': row.get('m15_close', math.nan),
    }


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--live-n', type=int, default=DEFAULT_LIVE_N)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '188'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}
    source_diag_rows: list[dict[str, Any]] = []

    progress('load OHLC with Stage177 gold_2025/live contract')
    for tf in ['m15', 'h1', 'h4', 'd1']:
        frames[tf], diag = s177.combine(tf, data_dir)
        source_diag_rows.extend(diag)
        if frames[tf].empty:
            blockers.append({'id': 'missing_combined_ohlc', 'tf': tf})
    source_diag = pd.DataFrame(source_diag_rows)
    if not source_diag.empty:
        save(source_diag, out / 'gold_v3_188_source_coverage.csv')

    batch = pd.DataFrame()
    targets = pd.DataFrame()
    parity_rows: list[dict[str, Any]] = []
    feature_cmp_rows: list[dict[str, Any]] = []
    latest_snapshot: dict[str, Any] = {}

    if not blockers:
        progress('build batch features and signals')
        batch = add_signals(s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']))
        targets = latest_ready_rows(batch, int(args.live_n))
        if targets.empty:
            blockers.append({'id': 'no_latest_ready_rows'})
        else:
            progress(f'run stepwise live parity rows={len(targets)}')
            for _, brow in targets.iterrows():
                dt = pd.to_datetime(brow['dt'])
                lm15 = truncate_frame(frames['m15'], dt)
                lh1 = truncate_frame(frames['h1'], dt)
                lh4 = truncate_frame(frames['h4'], dt)
                ld1 = truncate_frame(frames['d1'], dt)
                if lm15.empty or lh1.empty or lh4.empty or ld1.empty:
                    parity_rows.append({'dt': str(dt), 'row_match': False, 'status': 'TRUNCATED_FRAME_EMPTY'})
                    continue
                live = add_signals(s177.base.merge_features(lm15, lh1, lh4, ld1))
                if live.empty:
                    parity_rows.append({'dt': str(dt), 'row_match': False, 'status': 'LIVE_FEATURE_EMPTY'})
                    continue
                lrow = live.iloc[-1]
                row, cmp_rows = compare_one(brow, lrow)
                row['status'] = 'OK' if row['row_match'] else 'MISMATCH'
                parity_rows.append(row)
                feature_cmp_rows.extend(cmp_rows)
            latest_snapshot = make_latest_snapshot(targets.iloc[-1])
            save(targets, out / 'gold_v3_188_batch_latest_rows_with_signals.csv')

    parity = pd.DataFrame(parity_rows)
    feature_cmp = pd.DataFrame(feature_cmp_rows)
    if not parity.empty:
        save(parity, out / 'gold_v3_188_stepwise_live_parity_rows.csv')
    if not feature_cmp.empty:
        save(feature_cmp, out / 'gold_v3_188_stepwise_feature_compare.csv')
    if latest_snapshot:
        (out / 'gold_v3_188_latest_signal_snapshot.json').write_text(json.dumps(latest_snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
        save(pd.DataFrame([latest_snapshot]), out / 'gold_v3_188_latest_signal_snapshot.csv')

    parity_fail_rows = int((~parity['row_match']).sum()) if not parity.empty and 'row_match' in parity.columns else 0
    latest_signal = latest_snapshot.get('priority_signal', '') if latest_snapshot else ''
    latest_fired = latest_snapshot.get('fired_candidates', '') if latest_snapshot else ''
    ready = len(blockers) == 0 and parity_fail_rows == 0

    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE188_PRIMARY_ABC_CAP_LIVE_PARITY_PASS_AUDIT_ONLY' if ready else 'STAGE188_LIVE_PARITY_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'live_n_requested': int(args.live_n),
        'parity_rows': int(len(parity)) if not parity.empty else 0,
        'parity_fail_rows': parity_fail_rows,
        'latest_closed_m15_dt': latest_snapshot.get('latest_closed_m15_dt', ''),
        'latest_priority_signal': latest_signal,
        'latest_fired_candidates': latest_fired,
        'primary_candidate_ids_priority_order': [c['candidate_id'] for c in PRIMARY_CANDIDATES],
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
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
    (out / 'gold_v3_188_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_188_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    latest_cols = ['dt', 'priority_signal', 'fired_candidates', 'd1_dist_close_atr28', 'h4_body_atr14', 'h1_atr14', 'm15_close'] + [f"signal_{c['candidate_id']}" for c in PRIMARY_CANDIDATES]
    latest_table = targets[[c for c in latest_cols if c in targets.columns]].tail(20).copy() if not targets.empty else pd.DataFrame()
    fail_table = parity[~parity['row_match']].copy() if not parity.empty and 'row_match' in parity.columns else pd.DataFrame()

    lines = ['GOLD V3 188 PASTE_ME_PRIMARY_ABC_CAP_LIVE_PARITY_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PRIMARY_CANDIDATES', pd.DataFrame(PRIMARY_CANDIDATES).to_string(index=False)]
    lines += ['', 'LATEST_SIGNAL_SNAPSHOT', pd.DataFrame([latest_snapshot]).to_string(index=False) if latest_snapshot else 'NO_LATEST_SNAPSHOT']
    lines += ['', 'LATEST_20_BATCH_ROWS_WITH_SIGNALS', show(latest_table, 25)]
    lines += ['', 'PARITY_ROWS_TAIL', show(parity.tail(25) if not parity.empty else parity, 25)]
    lines += ['', 'PARITY_FAIL_ROWS', show(fail_table, 50)]
    lines += ['', 'FEATURE_COMPARE_FAIL_SAMPLE', show(feature_cmp[feature_cmp['match'].eq(False)].head(60) if not feature_cmp.empty and 'match' in feature_cmp.columns else pd.DataFrame(), 60)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage188 is audit-only. It checks that PRIMARY ABC CAP signals can be detected from closed CSV/MT5 OHLC rows and that stepwise live-style recomputation matches batch recomputation for recent rows.',
        'CSV latest row is treated as CLOSED by contract. No open/as-of interpretation is allowed. No live signal, payload, Discord, MT5 order, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
