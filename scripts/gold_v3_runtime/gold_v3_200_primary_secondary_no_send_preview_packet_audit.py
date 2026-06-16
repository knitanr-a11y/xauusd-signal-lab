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

STEP = 'GOLD_V3_200_PRIMARY_SECONDARY_NO_SEND_PREVIEW_PACKET_AUDIT_ONLY'
SECONDARY_ID = 'SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED'
SECONDARY_CLASS = 'SECONDARY_AUDIT_CANDIDATE'
FILTER_CANDIDATE_ID = 'SCALP_002_tp15_sl5_hz64_SHORT'
FILTER_EXCLUDED_HOUR = 9

ABC_CANDIDATES = [
    {
        'candidate_id': 'A_PRECISION_BASE',
        'role': 'PRIMARY',
        'priority': 1,
        'rule': 'd1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347',
        'direction': 'LONG',
        'tp': 40.0,
        'sl': 20.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'C_BALANCED_CAP60',
        'role': 'PRIMARY',
        'priority': 2,
        'rule': 'd1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60',
        'direction': 'LONG',
        'tp': 30.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
    {
        'candidate_id': 'B_HIGH_FREQUENCY_CAP40',
        'role': 'PRIMARY',
        'priority': 3,
        'rule': 'd1_dist_close_atr28<=-0.394892 & h1_atr14<=40',
        'direction': 'LONG',
        'tp': 50.0,
        'sl': 30.0,
        'horizon_m5': 192,
    },
]


def progress(msg: str) -> None:
    print(f'[200 progress] {msg}', flush=True)


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


def num(x: Any, default: float = math.nan) -> float:
    try:
        v = pd.to_numeric(pd.Series([x]), errors='coerce').iloc[0]
        if pd.isna(v) or not math.isfinite(float(v)):
            return default
        return float(v)
    except Exception:
        return default


def selected_priority(selected: pd.DataFrame) -> dict[str, float]:
    s = selected.copy().reset_index(drop=True)
    if 'profit_rate_score' in s.columns:
        return dict(zip(s['candidate_id'].astype(str), pd.to_numeric(s['profit_rate_score'], errors='coerce').fillna(0.0)))
    if 'selected_order' in s.columns:
        return {str(r['candidate_id']): 1000.0 - float(r['selected_order']) for _, r in s.iterrows()}
    return {str(cid): 1000.0 - i for i, cid in enumerate(s['candidate_id'].astype(str).tolist())}


def add_time_cols(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if x.empty:
        return x
    if 'dt' in x.columns and 'entry_dt' not in x.columns:
        x['entry_dt'] = pd.to_datetime(x['dt'])
    elif 'entry_dt' in x.columns:
        x['entry_dt'] = pd.to_datetime(x['entry_dt'])
    x['month'] = x['entry_dt'].dt.to_period('M').astype(str)
    x['entry_date'] = x['entry_dt'].dt.date.astype(str)
    x['entry_hour'] = x['entry_dt'].dt.hour.astype(int)
    return x.sort_values(['entry_dt', 'priority_score'] if 'priority_score' in x.columns else ['entry_dt']).reset_index(drop=True)


def build_abc_entries(feat: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows = []
    problems: list[dict[str, Any]] = []
    for c in ABC_CANDIDATES:
        mask, p = s179.literal_rule_mask(c['rule'], feat)
        if p:
            problems.append({'candidate_id': c['candidate_id'], 'problem': p})
            continue
        m = feat.loc[mask, ['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].copy()
        if m.empty:
            continue
        m['candidate_id'] = c['candidate_id']
        m['role'] = 'PRIMARY'
        m['direction'] = c['direction']
        m['tp'] = c['tp']
        m['sl'] = c['sl']
        m['horizon_m5'] = c['horizon_m5']
        m['rule'] = c['rule']
        m['priority_score'] = 5000.0 - float(c['priority'])
        rows.append(m)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return add_time_cols(out) if not out.empty else out, problems


def build_secondary_entries(feat: pd.DataFrame, selected: pd.DataFrame, priority: dict[str, float]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows = []
    problems: list[dict[str, Any]] = []
    for _, c in selected.iterrows():
        cid = str(c['candidate_id'])
        rule = str(c.get('rule', '')).strip()
        if not rule:
            problems.append({'candidate_id': cid, 'problem': 'missing_rule'})
            continue
        mask, p = s179.literal_rule_mask(rule, feat)
        if p:
            problems.append({'candidate_id': cid, 'problem': p})
            continue
        m = feat.loc[mask, ['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].copy()
        if m.empty:
            continue
        m['candidate_id'] = cid
        m['role'] = SECONDARY_CLASS
        m['direction'] = str(c.get('direction', ''))
        m['tp'] = num(c.get('tp'))
        m['sl'] = num(c.get('sl'))
        m['horizon_m5'] = int(num(c.get('horizon_m5'), 0))
        m['rule'] = rule
        m['secondary_id'] = SECONDARY_ID
        m['priority_score'] = 1000.0 + priority.get(cid, 0.0)
        rows.append(m)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if out.empty:
        return out, problems
    out = add_time_cols(out)
    removed = out['candidate_id'].astype(str).eq(FILTER_CANDIDATE_ID) & out['entry_hour'].eq(FILTER_EXCLUDED_HOUR)
    out = out[~removed].copy().reset_index(drop=True)
    return out, problems


def pick_one(df: pd.DataFrame, role: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    x = add_time_cols(df)
    x = x.sort_values(['entry_dt', 'priority_score'], ascending=[True, False]).drop_duplicates('entry_dt', keep='first')
    x['picked_role'] = role
    return x.reset_index(drop=True)


def build_tail_packet(feat: pd.DataFrame, abc_entries: pd.DataFrame, sec_entries: pd.DataFrame) -> pd.DataFrame:
    tail = feat[['dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14']].tail(96).copy()
    tail['entry_dt'] = pd.to_datetime(tail['dt'])
    abc_picked = pick_one(abc_entries[abc_entries['entry_dt'].isin(set(tail['entry_dt']))], 'PRIMARY') if not abc_entries.empty else pd.DataFrame()
    sec_picked = pick_one(sec_entries[sec_entries['entry_dt'].isin(set(tail['entry_dt']))], SECONDARY_CLASS) if not sec_entries.empty else pd.DataFrame()
    if not abc_picked.empty:
        tail = tail.merge(abc_picked[['entry_dt', 'candidate_id', 'direction', 'tp', 'sl', 'horizon_m5', 'priority_score']].rename(columns={
            'candidate_id': 'primary_candidate_id',
            'direction': 'primary_direction',
            'tp': 'primary_tp',
            'sl': 'primary_sl',
            'horizon_m5': 'primary_horizon_m5',
            'priority_score': 'primary_priority_score',
        }), on='entry_dt', how='left')
    else:
        for col in ['primary_candidate_id', 'primary_direction', 'primary_tp', 'primary_sl', 'primary_horizon_m5', 'primary_priority_score']:
            tail[col] = np.nan
    if not sec_picked.empty:
        tail = tail.merge(sec_picked[['entry_dt', 'candidate_id', 'direction', 'tp', 'sl', 'horizon_m5', 'priority_score']].rename(columns={
            'candidate_id': 'secondary_candidate_id',
            'direction': 'secondary_direction',
            'tp': 'secondary_tp',
            'sl': 'secondary_sl',
            'horizon_m5': 'secondary_horizon_m5',
            'priority_score': 'secondary_priority_score',
        }), on='entry_dt', how='left')
    else:
        for col in ['secondary_candidate_id', 'secondary_direction', 'secondary_tp', 'secondary_sl', 'secondary_horizon_m5', 'secondary_priority_score']:
            tail[col] = np.nan
    tail['primary_signal'] = np.where(tail['primary_candidate_id'].notna(), tail['primary_direction'].astype(str), 'NO_SIGNAL')
    tail['secondary_signal'] = np.where(tail['secondary_candidate_id'].notna(), tail['secondary_direction'].astype(str), 'NO_SIGNAL')
    tail['final_route'] = np.where(tail['primary_signal'].ne('NO_SIGNAL'), 'PRIMARY', np.where(tail['secondary_signal'].ne('NO_SIGNAL'), SECONDARY_CLASS, 'NO_SIGNAL'))
    tail['send_action'] = 'NO_SEND_AUDIT_ONLY'
    return tail


def metric_lookup(summary_df: pd.DataFrame, portfolio_id: str, fields: list[str]) -> dict[str, Any]:
    if summary_df.empty:
        return {f: '' for f in fields}
    hit = summary_df[summary_df['portfolio_id'].astype(str).eq(portfolio_id)] if 'portfolio_id' in summary_df.columns else pd.DataFrame()
    if hit.empty:
        return {f: '' for f in fields}
    row = hit.iloc[0]
    return {f: row.get(f, '') for f in fields}


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '200'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage199 summary and Stage193 selected candidates')
    selected = read_csv_any(root / '193' / 'gold_v3_193_scalping_selected_profit_stack_watchlist.csv')
    stage199_summary = read_csv_any(root / '199' / 'gold_v3_199_portfolio_summary_cost3_cost5.csv')
    stage199_decision = read_csv_any(root / '199' / 'gold_v3_199_decision.csv')
    if selected.empty:
        blockers.append({'id': 'missing_stage193_selected_candidates'})
    if stage199_summary.empty:
        blockers.append({'id': 'missing_stage199_portfolio_summary'})

    frames: dict[str, pd.DataFrame] = {}
    source_rows: list[dict[str, Any]] = []
    if not blockers:
        progress('load closed OHLC and build features')
        for tf in ['m15', 'h1', 'h4', 'd1']:
            frames[tf], diag = s177.combine(tf, data_dir)
            source_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({'id': 'missing_ohlc', 'tf': tf})
        if source_rows:
            save(pd.DataFrame(source_rows), out / 'gold_v3_200_source_coverage.csv')

    latest: dict[str, Any] = {}
    tail_packet = pd.DataFrame()
    no_send_packet_md = ''
    abc_entries = pd.DataFrame()
    secondary_entries = pd.DataFrame()
    problems: list[dict[str, Any]] = []

    if not blockers:
        feat = s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']).sort_values('dt').reset_index(drop=True)
        abc_entries, abc_problems = build_abc_entries(feat)
        priority = selected_priority(selected)
        secondary_entries, sec_problems = build_secondary_entries(feat, selected, priority)
        problems.extend(abc_problems + sec_problems)
        if problems:
            blockers.append({'id': 'rule_detector_problems', 'count': len(problems), 'sample': problems[:5]})
        else:
            save(abc_entries, out / 'gold_v3_200_primary_detector_entries.csv')
            save(secondary_entries, out / 'gold_v3_200_secondary_detector_entries.csv')
            tail_packet = build_tail_packet(feat, abc_entries, secondary_entries)
            save(tail_packet, out / 'gold_v3_200_no_send_latest_tail96.csv')
            latest = tail_packet.iloc[-1].to_dict() if not tail_packet.empty else {}

            fields = ['full_n', 'full_sum', 'full_pf', 'full_neg_months', 'test_sum', 'recent3m_sum', '2026_05_sum', '2026_06_sum']
            abc_metrics = metric_lookup(stage199_summary, 'ABC_ONLY_COST3', fields)
            sec_metrics = metric_lookup(stage199_summary, 'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', fields)
            combo_metrics = metric_lookup(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', fields)
            combo_cost5 = metric_lookup(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', ['full_sum', 'full_pf', 'full_neg_months'])

            route = str(latest.get('final_route', 'NO_SIGNAL')) if latest else 'NO_SIGNAL'
            no_send_reason = 'NO_SIGNAL' if route == 'NO_SIGNAL' else 'AUDIT_ONLY_PREVIEW_NO_SEND'
            packet_lines = [
                '# GOLD V3 Stage200 No-Send Preview Packet',
                '',
                'Status: AUDIT_ONLY / NO_SEND',
                f'Latest closed M15: {latest.get("dt", "")}',
                f'Final route: {route}',
                f'No-send reason: {no_send_reason}',
                '',
                '## PRIMARY',
                f'Candidate: {latest.get("primary_candidate_id", "") if pd.notna(latest.get("primary_candidate_id", np.nan)) else "NO_SIGNAL"}',
                f'Direction: {latest.get("primary_direction", "") if pd.notna(latest.get("primary_direction", np.nan)) else "NO_SIGNAL"}',
                f'TP/SL/Horizon: {latest.get("primary_tp", "")}/{latest.get("primary_sl", "")}/{latest.get("primary_horizon_m5", "")}',
                '',
                '## SECONDARY_AUDIT_CANDIDATE',
                f'Candidate: {latest.get("secondary_candidate_id", "") if pd.notna(latest.get("secondary_candidate_id", np.nan)) else "NO_SIGNAL"}',
                f'Direction: {latest.get("secondary_direction", "") if pd.notna(latest.get("secondary_direction", np.nan)) else "NO_SIGNAL"}',
                f'TP/SL/Horizon: {latest.get("secondary_tp", "")}/{latest.get("secondary_sl", "")}/{latest.get("secondary_horizon_m5", "")}',
                '',
                '## Metrics reference cost3',
                f'ABC_ONLY: n={abc_metrics.get("full_n", "")}, sum={abc_metrics.get("full_sum", "")}, PF={abc_metrics.get("full_pf", "")}, neg_months={abc_metrics.get("full_neg_months", "")}',
                f'SECONDARY: n={sec_metrics.get("full_n", "")}, sum={sec_metrics.get("full_sum", "")}, PF={sec_metrics.get("full_pf", "")}, neg_months={sec_metrics.get("full_neg_months", "")}',
                f'COMBINED_ABC_FIRST: n={combo_metrics.get("full_n", "")}, sum={combo_metrics.get("full_sum", "")}, PF={combo_metrics.get("full_pf", "")}, neg_months={combo_metrics.get("full_neg_months", "")}',
                '',
                '## Cost5 stress reference',
                f'COMBINED_ABC_FIRST cost5: sum={combo_cost5.get("full_sum", "")}, PF={combo_cost5.get("full_pf", "")}, neg_months={combo_cost5.get("full_neg_months", "")}',
                '',
                '## Safety',
                '- This is a preview packet only.',
                '- Discord send: OFF',
                '- MT5 order: OFF',
                '- payload/live hook/autotrade: OFF',
                '- NO_SIGNAL sends nothing.',
            ]
            no_send_packet_md = '\n'.join(packet_lines) + '\n'
            (out / 'gold_v3_200_no_send_preview_packet.md').write_text(no_send_packet_md, encoding='utf-8')

    ready = len(blockers) == 0
    latest_route = str(latest.get('final_route', 'NO_SIGNAL')) if latest else 'NO_SIGNAL'
    decision = 'STAGE200_NO_SEND_PREVIEW_PACKET_READY_AUDIT_ONLY' if ready else 'STAGE200_BLOCKED'
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'send_enabled': False,
        'no_send_preview_only': True,
        'primary_role': 'ABC_PRIMARY',
        'secondary_role': SECONDARY_CLASS,
        'secondary_id': SECONDARY_ID,
        'terminology_note': 'Do not classify the secondary scalping candidate as a watchlist.',
        'latest_closed_m15_dt': str(latest.get('dt', '')) if latest else '',
        'latest_final_route': latest_route,
        'latest_primary_candidate_id': '' if not latest or pd.isna(latest.get('primary_candidate_id', np.nan)) else str(latest.get('primary_candidate_id')),
        'latest_primary_signal': 'NO_SIGNAL' if not latest or pd.isna(latest.get('primary_direction', np.nan)) else str(latest.get('primary_direction')),
        'latest_secondary_candidate_id': '' if not latest or pd.isna(latest.get('secondary_candidate_id', np.nan)) else str(latest.get('secondary_candidate_id')),
        'latest_secondary_signal': 'NO_SIGNAL' if not latest or pd.isna(latest.get('secondary_direction', np.nan)) else str(latest.get('secondary_direction')),
        'tail96_primary_signal_rows': int(tail_packet['primary_signal'].astype(str).ne('NO_SIGNAL').sum()) if not tail_packet.empty else 0,
        'tail96_secondary_signal_rows': int(tail_packet['secondary_signal'].astype(str).ne('NO_SIGNAL').sum()) if not tail_packet.empty else 0,
        'tail96_final_route_signal_rows': int(tail_packet['final_route'].astype(str).ne('NO_SIGNAL').sum()) if not tail_packet.empty else 0,
        'cost_interpretation': 'cost5 is an all-in worse-execution stress proxy, including wider spread, slippage, commission conversion, and execution drag. It is not spread-only.',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_200_decision.csv')
    (out / 'gold_v3_200_summary.json').write_text(json.dumps({**summary, 'blockers': blockers, 'problems': problems}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 200 PASTE_ME_PRIMARY_SECONDARY_NO_SEND_PREVIEW_PACKET_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'NO_SEND_PREVIEW_PACKET_MD', no_send_packet_md if no_send_packet_md else 'NO_PACKET']
    lines += ['', 'LATEST_TAIL96', show(tail_packet, 120)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage200 is audit-only. It previews the packet shape only and sends nothing.',
        'ABC remains PRIMARY. The scalping system is SECONDARY_AUDIT_CANDIDATE, not watchlist.',
        'NO_SIGNAL must not notify Discord.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
