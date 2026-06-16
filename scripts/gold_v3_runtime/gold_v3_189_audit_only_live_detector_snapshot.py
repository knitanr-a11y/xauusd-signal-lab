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

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_177_ohlc_only_rebuild_search_audit_entry as s177
import gold_v3_179_monthly_winrate_tradecount_audit as s179

STEP = 'GOLD_V3_189_AUDIT_ONLY_LIVE_DETECTOR_SNAPSHOT'

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

FEATURES = [
    'd1_dist_close_atr28',
    'h4_body_atr14',
    'h1_atr14',
    'm15_open',
    'm15_high',
    'm15_low',
    'm15_close',
    'h1_close',
    'h4_close',
    'd1_close',
]


def progress(msg: str) -> None:
    print(f'[189 progress] {msg}', flush=True)


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def safe_num(x: Any) -> float:
    v = pd.to_numeric(pd.Series([x]), errors='coerce').iloc[0]
    if pd.isna(v):
        return math.nan
    return float(v)


def choose_priority(fired: list[str]) -> str:
    if not fired:
        return 'NO_SIGNAL'
    order = {c['candidate_id']: int(c['priority']) for c in PRIMARY_CANDIDATES}
    return sorted(fired, key=lambda x: (order.get(x, 999), x))[0]


def add_signals(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    out = df.copy()
    problems_all: list[dict[str, Any]] = []
    for c in PRIMARY_CANDIDATES:
        mask, problems = s179.literal_rule_mask(c['rule'], out)
        col = f"signal_{c['candidate_id']}"
        if problems:
            out[col] = False
            problems_all.append({'candidate_id': c['candidate_id'], 'problems': problems})
        else:
            out[col] = mask.astype(bool)
    fired_lists = []
    priorities = []
    for _, row in out.iterrows():
        fired = [c['candidate_id'] for c in PRIMARY_CANDIDATES if bool(row.get(f"signal_{c['candidate_id']}", False))]
        fired_lists.append('|'.join(fired))
        priorities.append(choose_priority(fired))
    out['fired_candidates'] = fired_lists
    out['priority_signal'] = priorities
    return out, problems_all


def latest_row_ready(data: pd.DataFrame) -> tuple[pd.Series | None, list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    if data.empty:
        return None, [{'id': 'feature_data_empty'}]
    latest = data.sort_values('dt').iloc[-1]
    missing = []
    for col in ['d1_dist_close_atr28', 'h4_body_atr14', 'h1_atr14']:
        if col not in latest.index or pd.isna(latest[col]):
            missing.append(col)
    if missing:
        blockers.append({'id': 'latest_closed_row_feature_missing', 'latest_dt': str(latest.get('dt', '')), 'missing': missing})
    return latest, blockers


def snapshot_from_row(row: pd.Series) -> dict[str, Any]:
    fired = str(row.get('fired_candidates', ''))
    priority = str(row.get('priority_signal', 'NO_SIGNAL'))
    chosen = next((c for c in PRIMARY_CANDIDATES if c['candidate_id'] == priority), None)
    entry_price = safe_num(row.get('m15_close', math.nan))
    if chosen and chosen['direction'] == 'LONG' and math.isfinite(entry_price):
        tp_price = entry_price + float(chosen['tp'])
        sl_price = entry_price - float(chosen['sl'])
    else:
        tp_price = math.nan
        sl_price = math.nan
    snap: dict[str, Any] = {
        'snapshot_created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'latest_closed_m15_dt': str(row.get('dt', '')),
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'csv_latest_row_contract': 'CLOSED',
        'priority_signal': priority,
        'fired_candidates': fired,
        'is_signal': bool(priority != 'NO_SIGNAL'),
        'selected_candidate_id': chosen['candidate_id'] if chosen else '',
        'selected_priority': int(chosen['priority']) if chosen else 0,
        'direction': chosen['direction'] if chosen else '',
        'entry_reference_price': entry_price,
        'tp_distance': float(chosen['tp']) if chosen else math.nan,
        'sl_distance': float(chosen['sl']) if chosen else math.nan,
        'tp_reference_price': tp_price,
        'sl_reference_price': sl_price,
        'horizon_m5': int(chosen['horizon_m5']) if chosen else 0,
        'would_notify_discord': False,
        'would_send_mt5_order': False,
        'would_call_ai_api': False,
        'would_emit_payload': False,
        'no_signal_discord_notify': False,
        'audit_only': True,
        'review_only': True,
    }
    for col in FEATURES:
        snap[col] = safe_num(row.get(col, math.nan))
    for c in PRIMARY_CANDIDATES:
        snap[f"signal_{c['candidate_id']}"] = bool(row.get(f"signal_{c['candidate_id']}", False))
    return snap


def candidate_rows(row: pd.Series) -> pd.DataFrame:
    rows = []
    entry_price = safe_num(row.get('m15_close', math.nan))
    for c in PRIMARY_CANDIDATES:
        fired = bool(row.get(f"signal_{c['candidate_id']}", False))
        rows.append({
            'candidate_id': c['candidate_id'],
            'priority': c['priority'],
            'rule': c['rule'],
            'direction': c['direction'],
            'tp': c['tp'],
            'sl': c['sl'],
            'horizon_m5': c['horizon_m5'],
            'signal': fired,
            'entry_reference_price': entry_price if fired else math.nan,
            'tp_reference_price': entry_price + float(c['tp']) if fired and math.isfinite(entry_price) else math.nan,
            'sl_reference_price': entry_price - float(c['sl']) if fired and math.isfinite(entry_price) else math.nan,
        })
    return pd.DataFrame(rows)


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--tail-n', type=int, default=20)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '189'
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
        save(source_diag, out / 'gold_v3_189_source_coverage.csv')

    snapshot: dict[str, Any] = {}
    cand_df = pd.DataFrame()
    tail = pd.DataFrame()
    data = pd.DataFrame()
    if not blockers:
        progress('build closed-row features and detect signals')
        data, signal_problems = add_signals(s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']))
        if signal_problems:
            blockers.append({'id': 'signal_rule_parse_problem', 'details': signal_problems})
        row, row_blockers = latest_row_ready(data)
        blockers.extend(row_blockers)
        if row is not None and not row_blockers and not signal_problems:
            snapshot = snapshot_from_row(row)
            cand_df = candidate_rows(row)
            tail_cols = ['dt', 'priority_signal', 'fired_candidates'] + [f"signal_{c['candidate_id']}" for c in PRIMARY_CANDIDATES] + ['d1_dist_close_atr28', 'h4_body_atr14', 'h1_atr14', 'm15_close']
            tail = data[[c for c in tail_cols if c in data.columns]].sort_values('dt').tail(int(args.tail_n)).copy()
            (out / 'gold_v3_189_latest_detector_snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
            save(pd.DataFrame([snapshot]), out / 'gold_v3_189_latest_detector_snapshot.csv')
            save(cand_df, out / 'gold_v3_189_candidate_signal_rows.csv')
            save(tail, out / 'gold_v3_189_recent_detector_tail.csv')
            message_lines = [
                '[GOLD_V3_189_AUDIT_ONLY_DETECTOR]',
                f"latest_closed_m15_dt={snapshot['latest_closed_m15_dt']}",
                f"priority_signal={snapshot['priority_signal']}",
                f"fired_candidates={snapshot['fired_candidates']}",
                f"entry_reference_price={snapshot['entry_reference_price']}",
                f"tp_reference_price={snapshot['tp_reference_price']}",
                f"sl_reference_price={snapshot['sl_reference_price']}",
                'audit_only=True',
                'discord_enabled=False',
                'mt5_order_enabled=False',
                'payload_enabled=False',
                'no_signal_discord_notify=False',
            ]
            (out / 'gold_v3_189_audit_only_message_preview.txt').write_text('\n'.join(message_lines) + '\n', encoding='utf-8')

    ready = len(blockers) == 0
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE189_AUDIT_ONLY_LIVE_DETECTOR_SNAPSHOT_READY' if ready else 'STAGE189_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'latest_closed_m15_dt': snapshot.get('latest_closed_m15_dt', ''),
        'priority_signal': snapshot.get('priority_signal', ''),
        'fired_candidates': snapshot.get('fired_candidates', ''),
        'is_signal': bool(snapshot.get('is_signal', False)),
        'selected_candidate_id': snapshot.get('selected_candidate_id', ''),
        'entry_reference_price': snapshot.get('entry_reference_price', math.nan),
        'tp_reference_price': snapshot.get('tp_reference_price', math.nan),
        'sl_reference_price': snapshot.get('sl_reference_price', math.nan),
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
    (out / 'gold_v3_189_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_189_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 189 PASTE_ME_AUDIT_ONLY_LIVE_DETECTOR_SNAPSHOT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PRIMARY_CANDIDATES', pd.DataFrame(PRIMARY_CANDIDATES).to_string(index=False)]
    lines += ['', 'LATEST_DETECTOR_SNAPSHOT', pd.DataFrame([snapshot]).to_string(index=False) if snapshot else 'NO_SNAPSHOT']
    lines += ['', 'CANDIDATE_SIGNAL_ROWS', show(cand_df, 20)]
    lines += ['', 'RECENT_DETECTOR_TAIL', show(tail, 30)]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage189 is audit-only. It creates a latest closed-row detector snapshot for the PRIMARY ABC CAP portfolio. It does not send Discord, does not place MT5 orders, does not call AI API, does not emit live payload, and does not enable autotrade.',
        'If priority_signal is NO_SIGNAL, no Discord notification is allowed. CSV latest row is treated as CLOSED by contract; open/as-of interpretation remains prohibited.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
