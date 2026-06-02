#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, csv, json, shutil, sys
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT, REPO_ROOT / 'scripts']:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from build_gold_disc8_ai_tag_numeric_tagger_from_review import clean, fm, metrics, resolve, safe_float, windows_long_path  # noqa:E402

SCHEMA_VERSION = 'gold_disc8_top3_candidate_rule_consolidation_v1_audit_only'
DEFAULT_REPLAY_ROOT = Path('data/runtime_logs/gold_disc8_top3_candidate_rule_replay_568/latest')
DEFAULT_OUT_ROOT = Path('data/runtime_logs/gold_disc8_top3_candidate_rule_consolidation')
DEFAULT_STRATEGIES = 'DISC_08_BUY_TP200_SL100_RR2,DISC_01_BUY_TP200_SL100_RR2,DISC_09_BUY_TP80_SL50_RR1p6'
EXPECTED_ROWS = 568

FILE_AUDIT_COLS = 'label path exists rows columns required status note'.split()
GROUP_COLS = 'group_id strategy_id feature op threshold tags source_rule_count unique_hit_count win_count loss_count flat_count win_rate profit_factor avg_r total_r ai_block_hit_count ai_allow_hit_count precision_vs_ai_block ai_allow_false_hit_rate positive_month_count worst_month worst_month_total_r best_month best_month_total_r classification demo_action reason'.split()
STRATEGY_COLS = 'strategy_id trade_count ai_block_count ai_allow_count candidate_block_count captured_ai_block_count false_block_ai_allow_count candidate_block_total_r candidate_block_pf candidate_rule_groups block_candidate_groups watch_candidate_groups ai_review_continue_groups reject_groups recommendation reason'.split()
TAG_COLS = 'tag_group tag_name strategy_count group_count block_candidate_groups watch_candidate_groups ai_review_continue_groups reject_groups total_unique_hits total_r ai_block_hit_count ai_allow_hit_count recommendation'.split()
MONTH_COLS = 'group_id strategy_id feature op threshold entry_month hit_count win_count loss_count flat_count win_rate profit_factor avg_r total_r ai_block_hit_count ai_allow_hit_count'.split()
SUMMARY_COLS = 'classification demo_action group_count unique_hit_count total_r ai_block_hit_count ai_allow_hit_count'.split()


def now_text() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def run_id_text() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def mkdirp(p: Path) -> None:
    Path(windows_long_path(p)).mkdir(parents=True, exist_ok=True)


def wjson(p: Path, obj: dict[str, Any]) -> None:
    mkdirp(p.parent)
    with open(windows_long_path(p), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def wcsv(p: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    mkdirp(p.parent)
    with open(windows_long_path(p), 'w', encoding='utf-8-sig', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        wr.writeheader()
        for r in rows:
            wr.writerow({c: r.get(c, '') for c in cols})


def read_csv(path: Path, label: str) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f'{label} not found: {p}')
    return pd.read_csv(windows_long_path(p), encoding='utf-8-sig', sep=None, engine='python')


def audit_file(label: str, path: Path, required: bool, note: str) -> dict[str, Any]:
    p = resolve(path)
    r = {'label': label, 'path': str(p), 'exists': p.exists(), 'rows': '', 'columns': '', 'required': required, 'status': 'OK' if p.exists() else ('MISSING_REQUIRED' if required else 'MISSING_OPTIONAL'), 'note': note}
    if p.exists() and p.suffix.lower() == '.csv':
        try:
            df = pd.read_csv(windows_long_path(p), encoding='utf-8-sig', sep=None, engine='python')
            r['rows'] = len(df)
            r['columns'] = ' | '.join(map(str, df.columns))
        except Exception as e:
            r['status'] = 'READ_ERROR'
            r['note'] = f'{note}; {type(e).__name__}: {e}'
    return r


def fnum(x: Any, default: float | None = None) -> float | None:
    y = safe_float(x)
    return default if y is None else float(y)


def rval(row: Any) -> float:
    x = fnum(row.get('profit_r_num'), 0.0)
    return 0.0 if x is None else float(x)


def group_key(row: Any) -> tuple[str, str, str, str]:
    return (clean(row.get('strategy_id')), clean(row.get('feature')), clean(row.get('op')), clean(row.get('threshold')))


def classify_group(row: dict[str, Any], a: argparse.Namespace) -> tuple[str, str, str]:
    hit = int(row.get('unique_hit_count') or 0)
    total_r = float(row.get('total_r') or 0.0)
    precision = fnum(row.get('precision_vs_ai_block'), 0.0) or 0.0
    false_rate = fnum(row.get('ai_allow_false_hit_rate'), 1.0) or 1.0
    pos_months = int(row.get('positive_month_count') or 0)
    ai_block = int(row.get('ai_block_hit_count') or 0)
    if hit < a.min_hit_count:
        return 'REJECT_CANDIDATE', 'REJECT', 'too_few_hits'
    if total_r >= 0:
        if ai_block >= a.ai_review_min_ai_block_hit:
            return 'AI_REVIEW_CONTINUE', 'AI_REVIEW', 'captures_ai_block_but_block_side_not_negative'
        return 'REJECT_CANDIDATE', 'REJECT', 'block_side_not_negative'
    if precision >= a.block_min_precision and false_rate <= a.block_max_false_rate and pos_months <= a.block_max_positive_months:
        return 'BLOCK_CANDIDATE', 'DEMO_BLOCK_CANDIDATE', 'negative_block_high_precision_low_false_block'
    if precision >= a.watch_min_precision and false_rate <= a.watch_max_false_rate and ai_block >= a.watch_min_ai_block_hit:
        return 'WATCH_CANDIDATE', 'DEMO_WATCH_CANDIDATE', 'negative_block_but_needs_demo_watch_or_extra_guard'
    if ai_block >= a.ai_review_min_ai_block_hit:
        return 'AI_REVIEW_CONTINUE', 'AI_REVIEW', 'numeric_signal_exists_but_quality_not_enough'
    return 'REJECT_CANDIDATE', 'REJECT', 'weak_numeric_evidence'


def build_groups(hit: pd.DataFrame, a: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if hit.empty:
        return [], []
    rows = hit.to_dict('records')
    buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for r in rows:
        buckets.setdefault(group_key(r), []).append(r)
    group_rows: list[dict[str, Any]] = []
    month_rows: list[dict[str, Any]] = []
    idx = 1
    for key, rs in sorted(buckets.items()):
        sid, feat, op, threshold = key
        by_tid: dict[str, dict[str, Any]] = {}
        tags: set[str] = set()
        source_rule_ids: set[str] = set()
        for r in rs:
            tid = clean(r.get('trade_id'))
            if not tid:
                continue
            by_tid.setdefault(tid, r)
            tg = clean(r.get('tag_group'))
            tn = clean(r.get('tag_name'))
            if tg and tn:
                tags.add(f'{tg}:{tn}')
            rid = clean(r.get('rule_id'))
            if rid:
                source_rule_ids.add(rid)
        unique = list(by_tid.values())
        vals = [rval(r) for r in unique]
        m = metrics(vals)
        months = []
        for mo in sorted({clean(r.get('entry_month')) for r in unique}):
            sub = [r for r in unique if clean(r.get('entry_month')) == mo]
            mv = [rval(r) for r in sub]
            mm = metrics(mv)
            months.append((mo, float(mm['total_r'])))
            month_rows.append({'group_id': '', 'strategy_id': sid, 'feature': feat, 'op': op, 'threshold': threshold, 'entry_month': mo, 'hit_count': len(sub), 'win_count': sum(v > 0 for v in mv), 'loss_count': sum(v < 0 for v in mv), 'flat_count': sum(v == 0 for v in mv), 'win_rate': fm(mm['win_rate']), 'profit_factor': fm(mm['profit_factor']), 'avg_r': fm(mm['avg_r']), 'total_r': fm(mm['total_r']), 'ai_block_hit_count': sum(clean(r.get('ai_decision')) == 'AI_BLOCK' for r in sub), 'ai_allow_hit_count': sum(clean(r.get('ai_decision')) == 'AI_ALLOW' for r in sub)})
        ai_block = sum(clean(r.get('ai_decision')) == 'AI_BLOCK' for r in unique)
        ai_allow = sum(clean(r.get('ai_decision')) == 'AI_ALLOW' for r in unique)
        hit_count = len(unique)
        positive_month_count = sum(1 for _, tr in months if tr > 0)
        worst = min(months, key=lambda x: x[1]) if months else ('', 0.0)
        best = max(months, key=lambda x: x[1]) if months else ('', 0.0)
        group_id = f'G{idx:03d}'
        idx += 1
        base = {'group_id': group_id, 'strategy_id': sid, 'feature': feat, 'op': op, 'threshold': threshold, 'tags': ' | '.join(sorted(tags)), 'source_rule_count': len(source_rule_ids), 'unique_hit_count': hit_count, 'win_count': sum(v > 0 for v in vals), 'loss_count': sum(v < 0 for v in vals), 'flat_count': sum(v == 0 for v in vals), 'win_rate': fm(m['win_rate']), 'profit_factor': fm(m['profit_factor']), 'avg_r': fm(m['avg_r']), 'total_r': fm(m['total_r']), 'ai_block_hit_count': ai_block, 'ai_allow_hit_count': ai_allow, 'precision_vs_ai_block': fm(None if hit_count == 0 else ai_block / hit_count), 'ai_allow_false_hit_rate': fm(None if hit_count == 0 else ai_allow / hit_count), 'positive_month_count': positive_month_count, 'worst_month': worst[0], 'worst_month_total_r': fm(worst[1]), 'best_month': best[0], 'best_month_total_r': fm(best[1])}
        cls, action, reason = classify_group(base, a)
        base.update({'classification': cls, 'demo_action': action, 'reason': reason})
        group_rows.append(base)
        for mr in month_rows:
            if mr['strategy_id'] == sid and mr['feature'] == feat and mr['op'] == op and mr['threshold'] == threshold and not mr['group_id']:
                mr['group_id'] = group_id
    group_rows = sorted(group_rows, key=lambda r: (r['classification'], float(r['total_r'] or 0), -int(r['unique_hit_count'] or 0)))
    return group_rows, month_rows


def strategy_summary(trade: pd.DataFrame, groups: list[dict[str, Any]], target_strategies: list[str]) -> list[dict[str, Any]]:
    out = []
    for sid in target_strategies:
        sub = trade[trade['strategy_id'].astype(str).map(clean).eq(sid)].copy()
        if sub.empty:
            out.append({'strategy_id': sid, 'recommendation': 'NO_DATA', 'reason': 'target_strategy_not_present_in_trade_audit'})
            continue
        block = sub[sub['candidate_replay_decision'].astype(str).map(clean).eq('BLOCK')]
        vals = [rval(r) for _, r in block.iterrows()]
        bm = metrics(vals)
        gs = [g for g in groups if g['strategy_id'] == sid]
        block_groups = [g for g in gs if g['classification'] == 'BLOCK_CANDIDATE']
        watch_groups = [g for g in gs if g['classification'] == 'WATCH_CANDIDATE']
        ai_groups = [g for g in gs if g['classification'] == 'AI_REVIEW_CONTINUE']
        reject_groups = [g for g in gs if g['classification'] == 'REJECT_CANDIDATE']
        if block_groups:
            rec = 'DEMO_BLOCK_CANDIDATE_AVAILABLE'
            reason = 'has_consolidated_block_candidate_groups'
        elif watch_groups:
            rec = 'DEMO_WATCH_ONLY_FIRST'
            reason = 'has_watch_candidates_but_no_block_candidate'
        elif ai_groups:
            rec = 'AI_REVIEW_CONTINUE'
            reason = 'numeric_candidates_not_safe_enough'
        else:
            rec = 'NO_NUMERIC_GATE_CANDIDATE'
            reason = 'no_usable_consolidated_candidate'
        out.append({'strategy_id': sid, 'trade_count': len(sub), 'ai_block_count': int(sub['ai_decision'].astype(str).map(clean).eq('AI_BLOCK').sum()), 'ai_allow_count': int(sub['ai_decision'].astype(str).map(clean).eq('AI_ALLOW').sum()), 'candidate_block_count': len(block), 'captured_ai_block_count': int(block['ai_decision'].astype(str).map(clean).eq('AI_BLOCK').sum()) if not block.empty else 0, 'false_block_ai_allow_count': int(block['ai_decision'].astype(str).map(clean).eq('AI_ALLOW').sum()) if not block.empty else 0, 'candidate_block_total_r': fm(bm['total_r']), 'candidate_block_pf': fm(bm['profit_factor']), 'candidate_rule_groups': len(gs), 'block_candidate_groups': len(block_groups), 'watch_candidate_groups': len(watch_groups), 'ai_review_continue_groups': len(ai_groups), 'reject_groups': len(reject_groups), 'recommendation': rec, 'reason': reason})
    return out


def tag_summary(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for g in groups:
        for tag in clean(g.get('tags')).split('|'):
            tag = clean(tag)
            if ':' not in tag:
                continue
            tg, tn = tag.split(':', 1)
            buckets.setdefault((clean(tg), clean(tn)), []).append(g)
    out = []
    for (tg, tn), gs in sorted(buckets.items()):
        block = sum(g['classification'] == 'BLOCK_CANDIDATE' for g in gs)
        watch = sum(g['classification'] == 'WATCH_CANDIDATE' for g in gs)
        ai = sum(g['classification'] == 'AI_REVIEW_CONTINUE' for g in gs)
        rej = sum(g['classification'] == 'REJECT_CANDIDATE' for g in gs)
        if block:
            rec = 'NUMERIC_BLOCK_CANDIDATE_EXISTS'
        elif watch:
            rec = 'WATCH_CANDIDATE_EXISTS'
        elif ai:
            rec = 'AI_REVIEW_CONTINUE'
        else:
            rec = 'REJECT_OR_NO_USEFUL_NUMERIC_SIGNAL'
        out.append({'tag_group': tg, 'tag_name': tn, 'strategy_count': len({g['strategy_id'] for g in gs}), 'group_count': len(gs), 'block_candidate_groups': block, 'watch_candidate_groups': watch, 'ai_review_continue_groups': ai, 'reject_groups': rej, 'total_unique_hits': sum(int(g.get('unique_hit_count') or 0) for g in gs), 'total_r': fm(sum(float(g.get('total_r') or 0.0) for g in gs)), 'ai_block_hit_count': sum(int(g.get('ai_block_hit_count') or 0) for g in gs), 'ai_allow_hit_count': sum(int(g.get('ai_allow_hit_count') or 0) for g in gs), 'recommendation': rec})
    return sorted(out, key=lambda r: (r['recommendation'], float(r['total_r'] or 0)))


def classification_summary(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for cls in ['BLOCK_CANDIDATE', 'WATCH_CANDIDATE', 'AI_REVIEW_CONTINUE', 'REJECT_CANDIDATE']:
        gs = [g for g in groups if g['classification'] == cls]
        out.append({'classification': cls, 'demo_action': ' | '.join(sorted({clean(g.get('demo_action')) for g in gs if clean(g.get('demo_action'))})), 'group_count': len(gs), 'unique_hit_count': sum(int(g.get('unique_hit_count') or 0) for g in gs), 'total_r': fm(sum(float(g.get('total_r') or 0.0) for g in gs)), 'ai_block_hit_count': sum(int(g.get('ai_block_hit_count') or 0) for g in gs), 'ai_allow_hit_count': sum(int(g.get('ai_allow_hit_count') or 0) for g in gs)})
    return out


def gate_json(groups: list[dict[str, Any]], strat_rows: list[dict[str, Any]], a: argparse.Namespace) -> dict[str, Any]:
    def rule_obj(g: dict[str, Any]) -> dict[str, Any]:
        return {'strategy_id': g['strategy_id'], 'feature': g['feature'], 'op': g['op'], 'threshold': fnum(g['threshold']), 'tags': clean(g.get('tags')).split(' | ') if clean(g.get('tags')) else [], 'classification': g['classification'], 'demo_action': g['demo_action'], 'metrics': {'unique_hit_count': int(g.get('unique_hit_count') or 0), 'total_r': fnum(g.get('total_r'), 0.0), 'profit_factor': fnum(g.get('profit_factor')), 'precision_vs_ai_block': fnum(g.get('precision_vs_ai_block')), 'ai_allow_false_hit_rate': fnum(g.get('ai_allow_false_hit_rate')), 'positive_month_count': int(g.get('positive_month_count') or 0), 'best_month': g.get('best_month'), 'best_month_total_r': fnum(g.get('best_month_total_r')), 'worst_month': g.get('worst_month'), 'worst_month_total_r': fnum(g.get('worst_month_total_r'))}, 'reason': g.get('reason')}
    return {'schema_version': SCHEMA_VERSION, 'audit_only': True, 'do_not_use_as_runtime_config': True, 'dispatch_ready_enabled': False, 'no_ai_api_call': True, 'no_discord_send': True, 'no_mt5_order_send': True, 'sot_mutated': False, 'runtime_gate_rules_mutated': False, 'live_decision_ledger_mutated': False, 'created_at': now_text(), 'purpose': 'Consolidate DISC8 top3 numeric candidate rules before demo MT5 gate design. This is not an executable runtime config.', 'target_strategies': [clean(x) for x in a.strategies.split(',') if clean(x)], 'classification_thresholds': {'min_hit_count': a.min_hit_count, 'block_min_precision': a.block_min_precision, 'block_max_false_rate': a.block_max_false_rate, 'block_max_positive_months': a.block_max_positive_months, 'watch_min_precision': a.watch_min_precision, 'watch_max_false_rate': a.watch_max_false_rate, 'watch_min_ai_block_hit': a.watch_min_ai_block_hit}, 'block_candidates': [rule_obj(g) for g in groups if g['classification'] == 'BLOCK_CANDIDATE'], 'watch_candidates': [rule_obj(g) for g in groups if g['classification'] == 'WATCH_CANDIDATE'], 'ai_review_continue': [rule_obj(g) for g in groups if g['classification'] == 'AI_REVIEW_CONTINUE'], 'strategy_recommendations': strat_rows}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Consolidate top3 DISC8 candidate rules for demo gate design. Audit-only.')
    p.add_argument('--replay-root', type=Path, default=DEFAULT_REPLAY_ROOT)
    p.add_argument('--out-root', type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument('--run-id', default='')
    p.add_argument('--strategies', default=DEFAULT_STRATEGIES)
    p.add_argument('--expected-trade-rows', type=int, default=EXPECTED_ROWS)
    p.add_argument('--min-hit-count', type=int, default=5)
    p.add_argument('--block-min-precision', type=float, default=0.80)
    p.add_argument('--block-max-false-rate', type=float, default=0.20)
    p.add_argument('--block-max-positive-months', type=int, default=1)
    p.add_argument('--watch-min-precision', type=float, default=0.60)
    p.add_argument('--watch-max-false-rate', type=float, default=0.40)
    p.add_argument('--watch-min-ai-block-hit', type=int, default=5)
    p.add_argument('--ai-review-min-ai-block-hit', type=int, default=5)
    p.add_argument('--no-latest-copy', action='store_false', dest='write_latest_copy', default=True)
    return p.parse_args()


def main() -> int:
    a = parse_args()
    run_id = a.run_id or run_id_text()
    replay = resolve(a.replay_root)
    root = resolve(a.out_root)
    run = root / 'runs' / run_id
    latest = root / 'latest'
    mkdirp(run)
    paths = {
        'input_audit': run / 'gold_disc8_top3_candidate_rule_consolidation_input_audit.csv',
        'consolidated_groups': run / 'gold_disc8_top3_candidate_rule_consolidated_groups.csv',
        'classification_summary': run / 'gold_disc8_top3_candidate_rule_classification_summary.csv',
        'strategy_summary': run / 'gold_disc8_top3_candidate_rule_strategy_summary.csv',
        'tag_summary': run / 'gold_disc8_top3_candidate_rule_tag_summary.csv',
        'monthly_group_summary': run / 'gold_disc8_top3_candidate_rule_monthly_group_summary.csv',
        'demo_gate_candidate_json': run / 'gold_disc8_demo_runtime_gate_candidate.audit_only.json',
        'summary': run / 'gold_disc8_top3_candidate_rule_consolidation_summary.json',
    }
    input_files = {
        'candidate_rules': replay / 'gold_disc8_top3_candidate_rule_replay_candidate_rules.csv',
        'trade_audit': replay / 'gold_disc8_top3_candidate_rule_replay_trade_audit.csv',
        'rule_hit_detail': replay / 'gold_disc8_top3_candidate_rule_replay_rule_hit_detail.csv',
        'rule_summary': replay / 'gold_disc8_top3_candidate_rule_replay_rule_summary.csv',
        'replay_summary': replay / 'gold_disc8_top3_candidate_rule_replay_summary.json',
    }
    audits = [audit_file(k, v, True, 'top3 replay latest input') for k, v in input_files.items()]
    wcsv(paths['input_audit'], audits, FILE_AUDIT_COLS)
    missing = [r for r in audits if r['required'] and not r['exists']]
    if missing:
        s = {'schema_version': SCHEMA_VERSION, 'cycle_ok': False, 'reason': 'STOP_MISSING_REQUIRED_INPUT_FILES', 'run_id': run_id, 'created_at': now_text(), 'missing_required_labels': [r['label'] for r in missing], 'no_ai_api_call': True, 'no_discord_send': True, 'no_mt5_order_send': True, 'sot_mutated': False, 'runtime_gate_rules_mutated': False, 'live_decision_ledger_mutated': False, 'dispatch_ready_forced_false': True, 'outputs': {k: str(v) for k, v in paths.items()}}
        wjson(paths['summary'], s)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 2
    candidate = read_csv(input_files['candidate_rules'], 'candidate rules')
    trade = read_csv(input_files['trade_audit'], 'trade audit')
    hit = read_csv(input_files['rule_hit_detail'], 'rule hit detail')
    _rule_summary = read_csv(input_files['rule_summary'], 'rule summary')
    problems = []
    for c in ['trade_id', 'strategy_id', 'ai_decision', 'candidate_replay_decision', 'profit_r_num', 'dispatch_ready']:
        if c not in trade.columns:
            problems.append(f'trade_audit missing {c}')
    for c in ['rule_id', 'trade_id', 'strategy_id', 'entry_month', 'ai_decision', 'profit_r_num', 'tag_group', 'tag_name', 'feature', 'op', 'threshold']:
        if c not in hit.columns:
            problems.append(f'rule_hit_detail missing {c}')
    if len(trade) != a.expected_trade_rows:
        problems.append(f'trade_audit rows expected {a.expected_trade_rows}, actual {len(trade)}')
    if 'dispatch_ready' in trade.columns and trade['dispatch_ready'].astype(str).str.lower().isin(['true', '1', 'yes']).any():
        problems.append('dispatch_ready true row exists')
    if problems:
        s = {'schema_version': SCHEMA_VERSION, 'cycle_ok': False, 'reason': 'STOP_INPUT_CONTRACT_FAILED', 'run_id': run_id, 'created_at': now_text(), 'problems': problems, 'counts': {'candidate_rules_rows': len(candidate), 'trade_rows': len(trade), 'hit_rows': len(hit)}, 'no_ai_api_call': True, 'no_discord_send': True, 'no_mt5_order_send': True, 'sot_mutated': False, 'runtime_gate_rules_mutated': False, 'live_decision_ledger_mutated': False, 'dispatch_ready_forced_false': True, 'outputs': {k: str(v) for k, v in paths.items()}}
        wjson(paths['summary'], s)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 3
    groups, month_rows = build_groups(hit, a)
    if not groups:
        s = {'schema_version': SCHEMA_VERSION, 'cycle_ok': False, 'reason': 'STOP_NO_CONSOLIDATED_GROUPS', 'run_id': run_id, 'created_at': now_text(), 'counts': {'candidate_rules_rows': len(candidate), 'trade_rows': len(trade), 'hit_rows': len(hit)}, 'no_ai_api_call': True, 'no_discord_send': True, 'no_mt5_order_send': True, 'sot_mutated': False, 'runtime_gate_rules_mutated': False, 'live_decision_ledger_mutated': False, 'dispatch_ready_forced_false': True, 'outputs': {k: str(v) for k, v in paths.items()}}
        wjson(paths['summary'], s)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 4
    targets = [clean(x) for x in a.strategies.split(',') if clean(x)]
    strat_rows = strategy_summary(trade, groups, targets)
    tag_rows = tag_summary(groups)
    cls_rows = classification_summary(groups)
    gate = gate_json(groups, strat_rows, a)
    wcsv(paths['consolidated_groups'], groups, GROUP_COLS)
    wcsv(paths['classification_summary'], cls_rows, SUMMARY_COLS)
    wcsv(paths['strategy_summary'], strat_rows, STRATEGY_COLS)
    wcsv(paths['tag_summary'], tag_rows, TAG_COLS)
    wcsv(paths['monthly_group_summary'], month_rows, MONTH_COLS)
    wjson(paths['demo_gate_candidate_json'], gate)
    counts = {r['classification']: int(r['group_count']) for r in cls_rows}
    s = {'schema_version': SCHEMA_VERSION, 'cycle_ok': True, 'reason': 'OK_AUDIT_ONLY_TOP3_CANDIDATE_RULE_CONSOLIDATION', 'run_id': run_id, 'created_at': now_text(), 'source_of_truth': 'top3 candidate replay latest outputs only; no OHLC rediscovery; no AI review', 'target_strategies': targets, 'no_ai_api_call': True, 'no_discord_send': True, 'no_mt5_order_send': True, 'sot_mutated': False, 'runtime_gate_rules_mutated': False, 'live_decision_ledger_mutated': False, 'dispatch_ready_forced_false': True, 'dispatch_ready_rows': 0, 'counts': {'candidate_rules_rows': len(candidate), 'trade_rows': len(trade), 'rule_hit_rows': len(hit), 'consolidated_groups': len(groups), 'block_candidate_groups': counts.get('BLOCK_CANDIDATE', 0), 'watch_candidate_groups': counts.get('WATCH_CANDIDATE', 0), 'ai_review_continue_groups': counts.get('AI_REVIEW_CONTINUE', 0), 'reject_groups': counts.get('REJECT_CANDIDATE', 0)}, 'classification_summary': cls_rows, 'outputs': {k: str(v) for k, v in paths.items()}, 'do_not_execute': 'This creates an audit-only demo gate candidate JSON. It is not runtime config and must not enable dispatch_ready/Discord/MT5 by itself.'}
    wjson(paths['summary'], s)
    if a.write_latest_copy:
        if latest.exists():
            shutil.rmtree(windows_long_path(latest))
        mkdirp(latest)
        for p in paths.values():
            shutil.copy2(windows_long_path(p), windows_long_path(latest / p.name))
    print(json.dumps(s, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
