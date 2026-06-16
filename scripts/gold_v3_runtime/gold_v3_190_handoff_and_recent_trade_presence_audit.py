#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_177_ohlc_only_rebuild_search_audit_entry as s177
import gold_v3_179_monthly_winrate_tradecount_audit as s179

STEP = 'GOLD_V3_190_HANDOFF_AND_RECENT_TRADE_PRESENCE_AUDIT_ONLY'

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

KEY_OUTPUTS = {
    '187': 'PRIMARY ABC CAP portfolio refreeze: A / C_CAP60 / B_CAP40, A>C>B priority audit view.',
    '188': 'Live parity audit: recent closed rows batch vs stepwise live-style recomputation matched.',
    '189': 'Audit-only live detector snapshot: latest closed row signal detector, no send/order.',
    '190': 'This handoff plus yesterday/today recent entry-signal presence audit.',
}


def progress(msg: str) -> None:
    print(f'[190 progress] {msg}', flush=True)


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
    out['is_signal'] = out['priority_signal'].ne('NO_SIGNAL')
    return out, problems_all


def enrich_signal_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out['mt5_date'] = pd.to_datetime(out['dt']).dt.date.astype(str)
    out['mt5_hour'] = pd.to_datetime(out['dt']).dt.hour.astype(int)
    chosen_tp = []
    chosen_sl = []
    chosen_dir = []
    tp_price = []
    sl_price = []
    for _, row in out.iterrows():
        cid = str(row.get('priority_signal', 'NO_SIGNAL'))
        c = next((x for x in PRIMARY_CANDIDATES if x['candidate_id'] == cid), None)
        entry = safe_num(row.get('m15_close', math.nan))
        if c and c['direction'] == 'LONG' and math.isfinite(entry):
            chosen_tp.append(float(c['tp']))
            chosen_sl.append(float(c['sl']))
            chosen_dir.append(c['direction'])
            tp_price.append(entry + float(c['tp']))
            sl_price.append(entry - float(c['sl']))
        else:
            chosen_tp.append(math.nan)
            chosen_sl.append(math.nan)
            chosen_dir.append('')
            tp_price.append(math.nan)
            sl_price.append(math.nan)
    out['selected_direction'] = chosen_dir
    out['tp_distance'] = chosen_tp
    out['sl_distance'] = chosen_sl
    out['entry_reference_price'] = pd.to_numeric(out['m15_close'], errors='coerce')
    out['tp_reference_price'] = tp_price
    out['sl_reference_price'] = sl_price
    return out


def first_signal_events(signal_rows: pd.DataFrame, all_recent_rows: pd.DataFrame) -> pd.DataFrame:
    if signal_rows.empty or all_recent_rows.empty:
        return pd.DataFrame()
    x = all_recent_rows.sort_values('dt').copy()
    prev_pri = x['priority_signal'].shift(1).fillna('NO_SIGNAL')
    x['is_new_signal_event'] = x['priority_signal'].ne('NO_SIGNAL') & (x['priority_signal'].ne(prev_pri) | prev_pri.eq('NO_SIGNAL'))
    return enrich_signal_rows(x[x['is_new_signal_event']].copy())


def make_daily_summary(recent: pd.DataFrame, signal_rows: pd.DataFrame, events: pd.DataFrame, dates: list[str]) -> pd.DataFrame:
    rows = []
    for d in dates:
        day_rows = recent[recent['mt5_date'].eq(d)].copy() if not recent.empty else pd.DataFrame()
        sig = signal_rows[signal_rows['mt5_date'].eq(d)].copy() if not signal_rows.empty else pd.DataFrame()
        ev = events[events['mt5_date'].eq(d)].copy() if not events.empty else pd.DataFrame()
        rows.append({
            'mt5_date': d,
            'closed_m15_rows': int(len(day_rows)),
            'raw_signal_rows': int(len(sig)),
            'new_signal_events': int(len(ev)),
            'had_trade_signal': bool(len(ev) > 0),
            'priority_signal_counts': json.dumps(sig['priority_signal'].value_counts().to_dict(), ensure_ascii=False) if not sig.empty else '{}',
            'event_times': '|'.join(pd.to_datetime(ev['dt']).astype(str).tolist()) if not ev.empty else '',
            'event_priority_signals': '|'.join(ev['priority_signal'].astype(str).tolist()) if not ev.empty else '',
        })
    return pd.DataFrame(rows)


def write_handoff_md(path: Path, summary: dict[str, Any], daily_summary: pd.DataFrame) -> None:
    daily_md = daily_summary.to_markdown(index=False) if not daily_summary.empty else 'NO_DAILY_ROWS'
    lines = [
        '# GOLD V3 Stage190 Handoff - Primary ABC CAP Audit-only',
        '',
        f"Created UTC: {summary.get('created_at_utc')}",
        '',
        '## Current status',
        '',
        '- GOLD V3 remains audit-only.',
        '- A / C_CAP60 / B_CAP40 are all PRIMARY candidates.',
        '- Priority audit view: A > C > B.',
        '- Stage188 live parity passed: closed-row batch and stepwise live-style calculations matched.',
        '- Stage189 audit-only detector snapshot is ready.',
        '',
        '## Primary candidates',
        '',
        '1. A_PRECISION_BASE: `d1_dist_close_atr28<=-0.438769 & h4_body_atr14>=0.883347`, LONG TP40 SL20 horizon192',
        '2. C_BALANCED_CAP60: `d1_dist_close_atr28<=-0.263261 & h4_body_atr14>=0.530008 & h1_atr14<=60`, LONG TP30 SL30 horizon192',
        '3. B_HIGH_FREQUENCY_CAP40: `d1_dist_close_atr28<=-0.394892 & h1_atr14<=40`, LONG TP50 SL30 horizon192',
        '',
        '## Yesterday/today recent signal presence',
        '',
        daily_md,
        '',
        '## Guardrails',
        '',
        '- Do not read/use/fallback to GOLD V2 / old GOLD / DISC8 / Stage41.',
        '- CSV latest row is treated as CLOSED; open/as-of interpretation is prohibited.',
        '- No candidate pool removal.',
        '- No F002 bypass.',
        '- No final live signal approval.',
        '- No Discord notification.',
        '- No MT5 order.',
        '- No AI API.',
        '- No live hook.',
        '- No payload.',
        '- No autotrade.',
        '- NO_SIGNAL must not notify Discord.',
        '',
        '## Next recommended stage',
        '',
        'Stage191 should remain audit-only and can prepare a runbook for repeated Stage189 detector snapshots and manual review of signal events, without enabling Discord/MT5/live hook.',
        '',
    ]
    path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--tail-days', type=int, default=2)
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '190'
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
        save(source_diag, out / 'gold_v3_190_source_coverage.csv')

    data = pd.DataFrame()
    recent = pd.DataFrame()
    signal_rows = pd.DataFrame()
    events = pd.DataFrame()
    daily_summary = pd.DataFrame()
    latest_dt = ''
    latest_date = ''
    today = ''
    yesterday = ''

    if not blockers:
        progress('build features and detect recent signals')
        data, signal_problems = add_signals(s177.base.merge_features(frames['m15'], frames['h1'], frames['h4'], frames['d1']))
        if signal_problems:
            blockers.append({'id': 'signal_rule_parse_problem', 'details': signal_problems})
        if data.empty:
            blockers.append({'id': 'feature_data_empty'})
        else:
            data = data.sort_values('dt').reset_index(drop=True)
            latest_ts = pd.to_datetime(data['dt'].iloc[-1])
            latest_dt = str(latest_ts)
            today_date = latest_ts.date()
            yesterday_date = today_date - timedelta(days=1)
            today = str(today_date)
            yesterday = str(yesterday_date)
            latest_date = today
            dates = [yesterday, today]
            x = data.copy()
            x['mt5_date'] = pd.to_datetime(x['dt']).dt.date.astype(str)
            recent = x[x['mt5_date'].isin(dates)].copy()
            if recent.empty:
                blockers.append({'id': 'recent_yesterday_today_rows_empty', 'dates': dates})
            else:
                recent = enrich_signal_rows(recent)
                signal_rows = recent[recent['is_signal']].copy()
                events = first_signal_events(signal_rows, recent)
                daily_summary = make_daily_summary(recent, signal_rows, events, dates)
                core_cols = [
                    'dt', 'mt5_date', 'priority_signal', 'fired_candidates',
                    'signal_A_PRECISION_BASE', 'signal_C_BALANCED_CAP60', 'signal_B_HIGH_FREQUENCY_CAP40',
                    'selected_direction', 'entry_reference_price', 'tp_reference_price', 'sl_reference_price',
                    'd1_dist_close_atr28', 'h4_body_atr14', 'h1_atr14', 'm15_close',
                ]
                save(recent[[c for c in core_cols if c in recent.columns]], out / 'gold_v3_190_yesterday_today_detector_rows.csv')
                save(signal_rows[[c for c in core_cols if c in signal_rows.columns]], out / 'gold_v3_190_yesterday_today_signal_rows.csv')
                save(events[[c for c in core_cols if c in events.columns] + ['is_new_signal_event'] if 'is_new_signal_event' in events.columns else [c for c in core_cols if c in events.columns]], out / 'gold_v3_190_yesterday_today_new_signal_events.csv')
                save(daily_summary, out / 'gold_v3_190_yesterday_today_daily_summary.csv')

    ready = len(blockers) == 0
    yesterday_had = bool(daily_summary[daily_summary['mt5_date'].eq(yesterday)]['had_trade_signal'].iloc[0]) if not daily_summary.empty and yesterday else False
    today_had = bool(daily_summary[daily_summary['mt5_date'].eq(today)]['had_trade_signal'].iloc[0]) if not daily_summary.empty and today else False
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': 'STAGE190_HANDOFF_AND_RECENT_TRADE_PRESENCE_READY_AUDIT_ONLY' if ready else 'STAGE190_BLOCKED',
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'latest_closed_m15_dt': latest_dt,
        'latest_mt5_date': latest_date,
        'yesterday_mt5_date': yesterday,
        'today_mt5_date': today,
        'yesterday_had_trade_signal_event': yesterday_had,
        'today_had_trade_signal_event': today_had,
        'yesterday_raw_signal_rows': int(daily_summary[daily_summary['mt5_date'].eq(yesterday)]['raw_signal_rows'].iloc[0]) if not daily_summary.empty and yesterday else 0,
        'today_raw_signal_rows': int(daily_summary[daily_summary['mt5_date'].eq(today)]['raw_signal_rows'].iloc[0]) if not daily_summary.empty and today else 0,
        'yesterday_new_signal_events': int(daily_summary[daily_summary['mt5_date'].eq(yesterday)]['new_signal_events'].iloc[0]) if not daily_summary.empty and yesterday else 0,
        'today_new_signal_events': int(daily_summary[daily_summary['mt5_date'].eq(today)]['new_signal_events'].iloc[0]) if not daily_summary.empty and today else 0,
        'primary_candidate_ids_priority_order': [c['candidate_id'] for c in PRIMARY_CANDIDATES],
        'time_basis': 'CSV/MT5 timestamp. No JST conversion is applied.',
        'recent_trade_definition': 'audit-only entry-signal event on closed M15. This is not a real executed order.',
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
    write_handoff_md(out / 'GOLD_V3_190_HANDOFF_PRIMARY_ABC_CAP_AUDIT_ONLY.md', summary, daily_summary)
    (out / 'gold_v3_190_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')
    save(pd.DataFrame([summary]), out / 'gold_v3_190_decision.csv')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 190 PASTE_ME_HANDOFF_AND_RECENT_TRADE_PRESENCE_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'PRIMARY_CANDIDATES', pd.DataFrame(PRIMARY_CANDIDATES).to_string(index=False)]
    lines += ['', 'KEY_OUTPUTS', pd.DataFrame([{'stage': k, 'meaning': v} for k, v in KEY_OUTPUTS.items()]).to_string(index=False)]
    lines += ['', 'YESTERDAY_TODAY_DAILY_SUMMARY', show(daily_summary, 10)]
    lines += ['', 'YESTERDAY_TODAY_NEW_SIGNAL_EVENTS', show(events, 40)]
    lines += ['', 'YESTERDAY_TODAY_RAW_SIGNAL_ROWS', show(signal_rows, 60)]
    lines += ['', 'YESTERDAY_TODAY_RECENT_ROWS_TAIL', show(recent.tail(40) if not recent.empty else recent, 40)]
    lines += ['', 'HANDOFF_MD_PATH', str(out / 'GOLD_V3_190_HANDOFF_PRIMARY_ABC_CAP_AUDIT_ONLY.md')]
    lines += ['', 'DATA_COVERAGE', source_diag.to_string(index=False) if not source_diag.empty else 'NO_DATA_COVERAGE']
    lines += [
        '',
        'INTERPRETATION',
        'Stage190 is audit-only. The yesterday/today trade presence check means closed-M15 entry-signal events only; it does not prove a real executed trade and it does not enable MT5 orders or Discord notifications.',
        'If no entry-signal event exists for a date, there was no ABC PRIMARY CAP detector trade signal on that MT5 date. NO_SIGNAL must not notify Discord.',
        'The handoff markdown summarizes Stage187-190 state and guardrails for the next chat.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': summary['decision'], 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
