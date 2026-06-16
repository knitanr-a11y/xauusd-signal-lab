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

STEP = 'GOLD_V3_201_NO_SEND_PREVIEW_PACKET_FORMAT_AUDIT_ONLY'
SECONDARY_CLASS = 'SECONDARY_AUDIT_CANDIDATE'
SECONDARY_ID = 'SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED'


def progress(msg: str) -> None:
    print(f'[201 progress] {msg}', flush=True)


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


def is_missing(v: Any) -> bool:
    if v is None:
        return True
    try:
        if pd.isna(v):
            return True
    except Exception:
        pass
    s = str(v).strip()
    return s == '' or s.lower() in {'nan', 'nat', 'none'}


def text_value(v: Any, no_signal: str = 'NO_SIGNAL') -> str:
    return no_signal if is_missing(v) else str(v)


def numeric_text(v: Any) -> str:
    if is_missing(v):
        return '-'
    try:
        f = float(v)
        if not math.isfinite(f):
            return '-'
        if abs(f - round(f)) < 1e-9:
            return str(int(round(f)))
        return f'{f:.2f}'
    except Exception:
        return str(v)


def metric_text(v: Any, decimals: int = 2) -> str:
    if is_missing(v):
        return '-'
    try:
        f = float(v)
        if not math.isfinite(f):
            return '-'
        return f'{f:.{decimals}f}'
    except Exception:
        return str(v)


def latest_role_row(latest: pd.Series, prefix: str, role_label: str) -> dict[str, str]:
    candidate = text_value(latest.get(f'{prefix}_candidate_id'), 'NO_SIGNAL')
    direction = text_value(latest.get(f'{prefix}_direction'), 'NO_SIGNAL')
    return {
        'role': role_label,
        'candidate': candidate,
        'direction': direction,
        'tp': '-' if candidate == 'NO_SIGNAL' else numeric_text(latest.get(f'{prefix}_tp')),
        'sl': '-' if candidate == 'NO_SIGNAL' else numeric_text(latest.get(f'{prefix}_sl')),
        'horizon_m5': '-' if candidate == 'NO_SIGNAL' else numeric_text(latest.get(f'{prefix}_horizon_m5')),
    }


def find_metric(summary: pd.DataFrame, portfolio_id: str, field: str) -> Any:
    if summary.empty or 'portfolio_id' not in summary.columns:
        return None
    hit = summary[summary['portfolio_id'].astype(str).eq(portfolio_id)]
    if hit.empty or field not in hit.columns:
        return None
    return hit.iloc[0][field]


def build_packet(latest: pd.Series, stage199_summary: pd.DataFrame, stage200_decision: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    latest_dt = text_value(latest.get('dt'), '-')
    final_route = text_value(latest.get('final_route'), 'NO_SIGNAL')
    primary_signal = text_value(latest.get('primary_signal'), 'NO_SIGNAL')
    secondary_signal = text_value(latest.get('secondary_signal'), 'NO_SIGNAL')
    no_send_reason = 'NO_SIGNAL' if final_route == 'NO_SIGNAL' else 'AUDIT_ONLY_PREVIEW_NO_SEND'
    primary = latest_role_row(latest, 'primary', 'PRIMARY')
    secondary = latest_role_row(latest, 'secondary', SECONDARY_CLASS)
    role_df = pd.DataFrame([primary, secondary])

    abc_sum = find_metric(stage199_summary, 'ABC_ONLY_COST3', 'full_sum')
    abc_pf = find_metric(stage199_summary, 'ABC_ONLY_COST3', 'full_pf')
    abc_n = find_metric(stage199_summary, 'ABC_ONLY_COST3', 'full_n')
    abc_neg = find_metric(stage199_summary, 'ABC_ONLY_COST3', 'full_neg_months')
    sec_sum = find_metric(stage199_summary, 'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_sum')
    sec_pf = find_metric(stage199_summary, 'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_pf')
    sec_n = find_metric(stage199_summary, 'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_n')
    sec_neg = find_metric(stage199_summary, 'SCALP_FILTERED_V1_OHLC_RECOMPUTED_COST3', 'full_neg_months')
    combo_sum = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_sum')
    combo_pf = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_pf')
    combo_n = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_n')
    combo_neg = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST3', 'full_neg_months')
    combo5_sum = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', 'full_sum')
    combo5_pf = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', 'full_pf')
    combo5_neg = find_metric(stage199_summary, 'COMBINED_ABC_PRIORITY_FIRST_OHLC_SCALP_COST5', 'full_neg_months')

    lines = [
        '# GOLD V3 Stage201 No-Send Preview Packet',
        '',
        'Status: AUDIT_ONLY / NO_SEND',
        f'Latest closed M15: {latest_dt}',
        f'Final route: {final_route}',
        f'No-send reason: {no_send_reason}',
        'Send action: NO_SEND_AUDIT_ONLY',
        '',
        '## Latest signal preview',
        '',
        '| Role | Candidate | Direction | TP | SL | Horizon M5 |',
        '|---|---|---|---:|---:|---:|',
        f"| PRIMARY | {primary['candidate']} | {primary['direction']} | {primary['tp']} | {primary['sl']} | {primary['horizon_m5']} |",
        f"| {SECONDARY_CLASS} | {secondary['candidate']} | {secondary['direction']} | {secondary['tp']} | {secondary['sl']} | {secondary['horizon_m5']} |",
        '',
        '## Metrics reference cost3',
        '',
        '| Portfolio | n | Sum | PF | Neg months |',
        '|---|---:|---:|---:|---:|',
        f'| ABC_PRIMARY | {numeric_text(abc_n)} | {metric_text(abc_sum)} | {metric_text(abc_pf, 3)} | {numeric_text(abc_neg)} |',
        f'| {SECONDARY_CLASS} | {numeric_text(sec_n)} | {metric_text(sec_sum)} | {metric_text(sec_pf, 3)} | {numeric_text(sec_neg)} |',
        f'| COMBINED_ABC_FIRST | {numeric_text(combo_n)} | {metric_text(combo_sum)} | {metric_text(combo_pf, 3)} | {numeric_text(combo_neg)} |',
        '',
        '## Cost5 stress reference',
        '',
        f'COMBINED_ABC_FIRST cost5: sum={metric_text(combo5_sum)}, PF={metric_text(combo5_pf, 3)}, neg_months={numeric_text(combo5_neg)}',
        '',
        'cost5 is an all-in worse-execution stress proxy. It can include wider spread, slippage, commission conversion, and execution drag. It is not spread-only.',
        '',
        '## Safety',
        '',
        '- Preview only: no send.',
        '- Discord send: OFF',
        '- MT5 order: OFF',
        '- Payload/live hook/autotrade: OFF',
        '- NO_SIGNAL sends nothing.',
    ]
    return '\n'.join(lines) + '\n', role_df


def compact_tail(tail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if tail.empty:
        return pd.DataFrame(), pd.DataFrame()
    x = tail.copy()
    signal = x[(x.get('primary_signal', pd.Series(dtype=str)).astype(str).ne('NO_SIGNAL')) | (x.get('secondary_signal', pd.Series(dtype=str)).astype(str).ne('NO_SIGNAL'))].copy()
    latest = x.tail(1).copy()
    cols = [
        'dt', 'm15_close', 'h1_atr14', 'd1_dist_close_atr28', 'h4_body_atr14',
        'primary_candidate_id', 'primary_signal', 'secondary_candidate_id', 'secondary_signal',
        'final_route', 'send_action'
    ]
    cols = [c for c in cols if c in x.columns]
    return latest[cols].copy(), signal[cols].copy()


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '201'
    out.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    progress('load Stage200 and Stage199 outputs')
    tail = read_csv_any(root / '200' / 'gold_v3_200_no_send_latest_tail96.csv')
    stage200_decision = read_csv_any(root / '200' / 'gold_v3_200_decision.csv')
    stage199_summary = read_csv_any(root / '199' / 'gold_v3_199_portfolio_summary_cost3_cost5.csv')
    if tail.empty:
        blockers.append({'id': 'missing_stage200_tail96'})
    if stage200_decision.empty:
        blockers.append({'id': 'missing_stage200_decision'})
    if stage199_summary.empty:
        blockers.append({'id': 'missing_stage199_portfolio_summary'})

    latest_compact = pd.DataFrame()
    signal_compact = pd.DataFrame()
    role_df = pd.DataFrame()
    packet = ''

    if not blockers:
        latest = tail.iloc[-1]
        packet, role_df = build_packet(latest, stage199_summary, stage200_decision)
        latest_compact, signal_compact = compact_tail(tail)
        save(role_df, out / 'gold_v3_201_latest_role_preview.csv')
        save(latest_compact, out / 'gold_v3_201_latest_compact_preview.csv')
        save(signal_compact, out / 'gold_v3_201_tail96_signal_rows_compact.csv')
        (out / 'gold_v3_201_no_send_preview_packet_clean.md').write_text(packet, encoding='utf-8')

    packet_lower = packet.lower()
    nan_present = 'nan' in packet_lower
    watchlist_present = 'watchlist' in packet_lower
    ready = len(blockers) == 0 and not nan_present and not watchlist_present
    decision = 'STAGE201_NO_SEND_PREVIEW_PACKET_FORMAT_PASS_AUDIT_ONLY' if ready else ('STAGE201_READY_WITH_FORMAT_WARNINGS_AUDIT_ONLY' if len(blockers) == 0 else 'STAGE201_BLOCKED')

    latest_dt = latest_compact['dt'].iloc[0] if not latest_compact.empty and 'dt' in latest_compact.columns else ''
    latest_route = latest_compact['final_route'].iloc[0] if not latest_compact.empty and 'final_route' in latest_compact.columns else 'NO_SIGNAL'

    summary = {
        'step': STEP,
        'status': 'READY' if len(blockers) == 0 else 'BLOCKED',
        'ready': len(blockers) == 0,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'no_send_preview_only': True,
        'send_enabled': False,
        'primary_role': 'ABC_PRIMARY',
        'secondary_role': SECONDARY_CLASS,
        'secondary_id': SECONDARY_ID,
        'latest_closed_m15_dt': str(latest_dt),
        'latest_final_route': str(latest_route),
        'tail96_signal_rows_compact': int(len(signal_compact)) if not signal_compact.empty else 0,
        'nan_string_present_in_packet': bool(nan_present),
        'watchlist_string_present_in_packet': bool(watchlist_present),
        'packet_format_pass': bool(not nan_present and not watchlist_present and len(blockers) == 0),
        'cost_interpretation': 'cost5 is an all-in worse-execution stress proxy, including wider spread, slippage, commission conversion, and execution drag. It is not spread-only.',
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
    save(pd.DataFrame([summary]), out / 'gold_v3_201_decision.csv')
    (out / 'gold_v3_201_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        if df.empty:
            return 'NO_ROWS'
        return df.head(n).to_string(index=False)

    lines = ['GOLD V3 201 PASTE_ME_NO_SEND_PREVIEW_PACKET_FORMAT_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'NO_SEND_PREVIEW_PACKET_CLEAN_MD', packet if packet else 'NO_PACKET']
    lines += ['', 'LATEST_ROLE_PREVIEW', show(role_df, 20)]
    lines += ['', 'LATEST_COMPACT_PREVIEW', show(latest_compact, 20)]
    lines += ['', 'TAIL96_SIGNAL_ROWS_COMPACT', show(signal_compact, 80)]
    lines += [
        '',
        'INTERPRETATION',
        'Stage201 is audit-only. It formats the Stage200 no-send preview packet and verifies that NO_SIGNAL rows do not display nan/nan/nan.',
        'The secondary scalping system is SECONDARY_AUDIT_CANDIDATE, not watchlist.',
        'No Discord, MT5 order, payload, AI API, live hook, or autotrade is enabled.',
    ]
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': len(blockers) == 0, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if len(blockers) == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
