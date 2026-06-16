#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = 'GOLD_V3_213_READINESS_GATE_SUMMARY_REMAINING_BLOCKERS_AUDIT_ONLY'

STAGE_FILES = {
    '187_primary_abc_cap_refreeze': ('187', 'gold_v3_187_decision.csv'),
    '199_secondary_recomputed_freeze': ('199', 'gold_v3_199_decision.csv'),
    '205_actual_execution_contract': ('205', 'gold_v3_205_decision.csv'),
    '206_theoretical_resolver': ('206', 'gold_v3_206_decision.csv'),
    '207_actual_import_contract': ('207', 'gold_v3_207_decision.csv'),
    '208_signal_id_embedding': ('208', 'gold_v3_208_decision.csv'),
    '211_integrated_no_send_runner': ('211', 'gold_v3_211_decision.csv'),
    '212_integrated_runner_parity': ('212', 'gold_v3_212_decision.csv'),
}


def progress(msg: str) -> None:
    print(f'[213 progress] {msg}', flush=True)


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


def s(v: Any, default: str = '') -> str:
    if v is None:
        return default
    try:
        if pd.isna(v):
            return default
    except Exception:
        pass
    t = str(v).strip()
    return default if t.lower() in {'', 'nan', 'nat', 'none'} else t


def b(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return s(v).lower() in {'true', '1', 'yes', 'y'}


def i(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def first(df: pd.DataFrame) -> dict[str, Any]:
    return df.iloc[0].to_dict() if not df.empty else {}


def load_stage_decisions(root: Path) -> pd.DataFrame:
    rows = []
    for stage, (folder, fname) in STAGE_FILES.items():
        path = root / folder / fname
        df = read_csv_any(path)
        row = first(df)
        rows.append({
            'stage_key': stage,
            'path': str(path),
            'exists': path.exists(),
            'decision': s(row.get('decision')),
            'status': s(row.get('status')),
            'ready': b(row.get('ready')),
            'blocker_count': i(row.get('blocker_count')),
            'audit_only': b(row.get('audit_only')) if row else False,
            'send_enabled': b(row.get('send_enabled')),
            'execution_enabled': b(row.get('execution_enabled')),
            'discord_enabled': b(row.get('discord_enabled')),
            'mt5_order_enabled': b(row.get('mt5_order_enabled')),
            'live_hook_enabled': b(row.get('live_hook_enabled')),
            'payload_enabled': b(row.get('payload_enabled')),
            'autotrade_enabled': b(row.get('autotrade_enabled')),
            'no_signal_discord_notify': b(row.get('no_signal_discord_notify')),
        })
    return pd.DataFrame(rows)


def build_capability_matrix(stages: pd.DataFrame) -> pd.DataFrame:
    def stage_ready(key: str) -> bool:
        hit = stages[stages['stage_key'].eq(key)]
        return bool(not hit.empty and hit.iloc[0]['exists'] and hit.iloc[0]['ready'] and int(hit.iloc[0]['blocker_count']) == 0)

    rows = [
        {'capability': 'PRIMARY_ABC_CAP_PORTFOLIO_FROZEN', 'status': 'READY' if stage_ready('187_primary_abc_cap_refreeze') else 'NOT_READY', 'source_stage': '187', 'unlocks_live': False},
        {'capability': 'SECONDARY_AUDIT_CANDIDATE_FROZEN', 'status': 'READY' if stage_ready('199_secondary_recomputed_freeze') else 'NOT_READY', 'source_stage': '199', 'unlocks_live': False},
        {'capability': 'THEORETICAL_RESULT_RESOLVER_READY', 'status': 'READY' if stage_ready('206_theoretical_resolver') else 'NOT_READY', 'source_stage': '206', 'unlocks_live': False},
        {'capability': 'ACTUAL_EXECUTION_LEDGER_CONTRACT_READY', 'status': 'READY' if stage_ready('205_actual_execution_contract') else 'NOT_READY', 'source_stage': '205', 'unlocks_live': False},
        {'capability': 'ACTUAL_EXECUTION_IMPORT_CONTRACT_READY', 'status': 'READY' if stage_ready('207_actual_import_contract') else 'NOT_READY', 'source_stage': '207', 'unlocks_live': False},
        {'capability': 'SIGNAL_ID_EMBEDDING_CONTRACT_READY', 'status': 'READY' if stage_ready('208_signal_id_embedding') else 'NOT_READY', 'source_stage': '208', 'unlocks_live': False},
        {'capability': 'INTEGRATED_NO_SEND_RUNNER_READY', 'status': 'READY' if stage_ready('211_integrated_no_send_runner') else 'NOT_READY', 'source_stage': '211', 'unlocks_live': False},
        {'capability': 'INTEGRATED_ROUTE_PARITY_READY', 'status': 'READY_WITH_WARN' if stage_ready('212_integrated_runner_parity') else 'NOT_READY', 'source_stage': '212', 'unlocks_live': False},
    ]
    return pd.DataFrame(rows)


def build_hard_blocks(stages: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {'block_id': 'HB001', 'category': 'LIVE_WRITE', 'blocker': 'live retention writer not enabled', 'required_before_live': True, 'current_status': 'BLOCKED_BY_AUDIT_ONLY'},
        {'block_id': 'HB002', 'category': 'DISCORD', 'blocker': 'Discord send not enabled and not approved', 'required_before_live': True, 'current_status': 'BLOCKED_BY_AUDIT_ONLY'},
        {'block_id': 'HB003', 'category': 'MT5_EXECUTION', 'blocker': 'MT5 order execution not enabled and not approved', 'required_before_live': True, 'current_status': 'BLOCKED_BY_AUDIT_ONLY'},
        {'block_id': 'HB004', 'category': 'ACTUAL_IMPORT', 'blocker': 'actual execution import contract exists but real import is not enabled', 'required_before_live': False, 'current_status': 'BLOCKED_FOR_ACTUAL_PERFORMANCE_REVIEW'},
        {'block_id': 'HB005', 'category': 'SIGNAL_CASE', 'blocker': 'integrated runner has not yet observed a latest SIGNAL cycle after Stage211', 'required_before_live': True, 'current_status': 'NEEDS_SIGNAL_APPEND_PREVIEW_CASE'},
        {'block_id': 'HB006', 'category': 'DUPLICATE_PROTECTION', 'blocker': 'duplicate signal_id handling across repeated cycles not audited yet', 'required_before_live': True, 'current_status': 'NEEDS_IDEMPOTENCY_AUDIT'},
        {'block_id': 'HB007', 'category': 'FEATURE_DRIFT_MONITOR', 'blocker': 'feature drift warning should be monitored after Stage212', 'required_before_live': False, 'current_status': 'WARN_MONITORING_RECOMMENDED'},
    ]
    return pd.DataFrame(rows)


def build_safety_matrix(stages: pd.DataFrame) -> pd.DataFrame:
    fields = ['send_enabled', 'execution_enabled', 'discord_enabled', 'mt5_order_enabled', 'live_hook_enabled', 'payload_enabled', 'autotrade_enabled', 'no_signal_discord_notify']
    rows = []
    for field in fields:
        any_true = bool(stages[field].fillna(False).astype(bool).any()) if field in stages.columns else False
        rows.append({
            'safety_flag': field,
            'expected': False,
            'observed_any_true_in_stage_decisions': any_true,
            'passed': not any_true,
        })
    return pd.DataFrame(rows)


def build_next_actions() -> pd.DataFrame:
    return pd.DataFrame([
        {'order': 1, 'next_stage': '214_IDEMPOTENT_WRITER_AND_DUPLICATE_SIGNAL_ID_AUDIT_ONLY', 'purpose': 'audit repeated cycles so the same signal_id is not appended twice', 'live_unlock': False},
        {'order': 2, 'next_stage': '215_SIGNAL_CASE_APPEND_PREVIEW_REPLAY_AUDIT_ONLY', 'purpose': 'force/replay a known SIGNAL row to verify append preview and notification preview shapes', 'live_unlock': False},
        {'order': 3, 'next_stage': '216_FEATURE_DRIFT_MONITORING_RULE_AUDIT_ONLY', 'purpose': 'define when feature drift warn becomes blocker', 'live_unlock': False},
        {'order': 4, 'next_stage': '217_LIVE_RETENTION_WRITER_DRY_RUN_TO_STAGING_AUDIT_ONLY', 'purpose': 'write to staging files only, not production retention files', 'live_unlock': False},
        {'order': 5, 'next_stage': 'HUMAN_APPROVAL_GATE', 'purpose': 'human decision before any real send/order/import/live hook', 'live_unlock': False},
    ])


def readiness_summary(stages: pd.DataFrame, caps: pd.DataFrame, hard: pd.DataFrame, safety: pd.DataFrame) -> dict[str, Any]:
    all_required_stages_ready = bool(stages['exists'].all() and stages['ready'].all() and (stages['blocker_count'].fillna(999).astype(int) == 0).all())
    safety_pass = bool(safety['passed'].all())
    hard_required_open = int(hard[hard['required_before_live'].astype(bool)].shape[0])
    caps_ready = int(caps[caps['status'].astype(str).str.startswith('READY')].shape[0])
    return {
        'all_required_stage_decisions_ready': all_required_stages_ready,
        'safety_all_off_pass': safety_pass,
        'capabilities_ready_count': caps_ready,
        'capabilities_total': int(len(caps)),
        'required_hard_blocks_remaining': hard_required_open,
        'live_release_ready': False,
        'recommended_status': 'NO_SEND_INTEGRATED_DRY_RUN_READY_LIVE_RELEASE_BLOCKED',
    }


def plan_md() -> str:
    return '''# GOLD V3 Stage213 Readiness Gate Summary and Remaining Blockers

Status: AUDIT_ONLY

Stage213 summarizes current readiness and lists remaining blockers before any live release.

It does not approve live trading, notifications, actual execution import, payload, or live hooks.

The output separates:

- capabilities already ready
- safety flags that must remain off
- hard blockers before live release
- recommended next audit stages

A READY Stage213 means the summary is complete, not that live trading is approved.
'''


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    args = ap.parse_args()

    data_dir = gy.mt5_files_dir(args.mt5_files_dir)
    root = data_dir / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '213'
    out.mkdir(parents=True, exist_ok=True)

    progress('load readiness inputs')
    stages = load_stage_decisions(root)
    caps = build_capability_matrix(stages)
    hard = build_hard_blocks(stages)
    safety = build_safety_matrix(stages)
    next_actions = build_next_actions()
    rs = readiness_summary(stages, caps, hard, safety)

    blockers: list[dict[str, Any]] = []
    if not bool(stages['exists'].all()):
        blockers.append({'id': 'missing_required_stage_decisions'})
    if not bool(safety['passed'].all()):
        blockers.append({'id': 'safety_flag_enabled_unexpectedly'})

    save(stages, out / 'gold_v3_213_stage_decision_readiness.csv')
    save(caps, out / 'gold_v3_213_capability_matrix.csv')
    save(hard, out / 'gold_v3_213_remaining_hard_blocks.csv')
    save(safety, out / 'gold_v3_213_safety_flag_matrix.csv')
    save(next_actions, out / 'gold_v3_213_recommended_next_actions.csv')
    (out / 'gold_v3_213_readiness_gate_summary.md').write_text(plan_md(), encoding='utf-8')

    ready = len(blockers) == 0
    decision = 'STAGE213_READINESS_GATE_SUMMARY_READY_LIVE_RELEASE_BLOCKED_AUDIT_ONLY' if ready else 'STAGE213_BLOCKED'
    summary = {
        'step': STEP,
        'status': 'READY' if ready else 'BLOCKED',
        'ready': ready,
        'decision': decision,
        'created_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'output_dir': str(out),
        'audit_only': True,
        'review_only': True,
        'dry_run_only': True,
        **rs,
        'source_csv_mutated': False,
        'contract_mutated': False,
        'open_asof_allowed': False,
        'candidate_pool_removed': False,
        'f002_exclusion_bypassed': False,
        'final_live_enabled': False,
        'send_enabled': False,
        'execution_enabled': False,
        'actual_order_import_enabled': False,
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
    save(pd.DataFrame([summary]), out / 'gold_v3_213_decision.csv')
    (out / 'gold_v3_213_summary.json').write_text(json.dumps({**summary, 'blockers': blockers}, ensure_ascii=False, indent=2), encoding='utf-8')

    def show(df: pd.DataFrame, n: int = 80) -> str:
        return 'NO_ROWS' if df.empty else df.head(n).to_string(index=False)

    lines = ['GOLD V3 213 PASTE_ME_READINESS_GATE_SUMMARY_REMAINING_BLOCKERS_AUDIT']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'READINESS_GATE_SUMMARY_MD', plan_md()]
    lines += ['', 'STAGE_DECISION_READINESS', show(stages, 80)]
    lines += ['', 'CAPABILITY_MATRIX', show(caps, 80)]
    lines += ['', 'REMAINING_HARD_BLOCKS', show(hard, 80)]
    lines += ['', 'SAFETY_FLAG_MATRIX', show(safety, 80)]
    lines += ['', 'RECOMMENDED_NEXT_ACTIONS', show(next_actions, 80)]
    lines += ['', 'INTERPRETATION']
    lines += ['Stage213 is audit-only. READY means the readiness summary was created, not that live release is approved.']
    lines += ['Current recommended status remains no-send integrated dry-run ready, live release blocked.']
    lines += ['No send, execution, actual import, payload, live hook, or autotrade is enabled.']
    lines += ['', 'BLOCKERS', 'NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False, indent=2)]
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    progress('done')
    print(json.dumps({'ready': ready, 'decision': decision, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
