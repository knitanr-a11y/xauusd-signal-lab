#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT, REPO_ROOT / "scripts"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backtest_gold_disc8_live_decision_numeric_tagger_audit import (  # noqa: E402
    CANDIDATE_COLUMNS,
    GATE_COLUMNS,
    RULE_EVAL_COLUMNS,
    SUMMARY_COLUMNS,
    TAG_COLUMNS,
    DEFAULT_CSV_DIR,
    DEFAULT_MANIFEST_JSON,
    DEFAULT_NUMERIC_RULES_JSON,
    DEFAULT_OUT_ROOT,
    DEFAULT_TAG_RECALL_CSV,
    build_summaries,
    extract_trade_params,
    first_touch_outcome,
    gate_numeric,
    load_numeric_rules,
    load_promotable_tags,
    resolve,
    round6,
    safe_float,
    write_csv,
    write_json,
)
from gold_disc8_feature_contract_bridge import filter_pre_entry_rules, build_feature_frame_with_contract  # noqa: E402
from run_gold_disc8_live_decision_audit_forever_aligned import (  # noqa: E402
    clean,
    evaluate_strategy,
    make_decision_key,
    parse_manifest,
    read_json,
    read_ohlc_csv,
    windows_long_path,
)

SCHEMA_VERSION = "gold_disc8_backtest_live_decision_numeric_tagger_audit_v2_bridge_no_future"
EXCLUDED_RULE_COLUMNS = ["rule_id", "strategy_id", "tag_group", "tag_name", "configured_action", "feature", "op", "threshold", "excluded_reason"]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_id_text() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_excluded(path: Path, rows: list[dict[str, Any]]) -> None:
    out = [{c: r.get(c, "") for c in EXCLUDED_RULE_COLUMNS} for r in rows]
    write_csv(path, out, EXCLUDED_RULE_COLUMNS)


def load_lower_tf(csv_dir: Path, args: argparse.Namespace) -> pd.DataFrame | None:
    p = csv_dir / args.outcome_lower_tf_file
    if not p.exists():
        return None
    return read_ohlc_csv(p, tail=args.tail_lower_tf).sort_values("time").reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest DISC8 numeric gate v2 with feature bridge. Audit-only.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--numeric-rules-json", type=Path, default=DEFAULT_NUMERIC_RULES_JSON)
    p.add_argument("--tag-recall-csv", type=Path, default=DEFAULT_TAG_RECALL_CSV)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--run-id", type=str, default="")
    p.add_argument("--start-time", type=str, default="")
    p.add_argument("--end-time", type=str, default="")
    p.add_argument("--max-bars", type=int, default=12000)
    p.add_argument("--promotable-only", action="store_true", default=True)
    p.add_argument("--all-rules", action="store_false", dest="promotable_only")
    p.add_argument("--outcome-lower-tf-file", type=str, default="goldsharp_m5.csv")
    p.add_argument("--outcome-horizon-minutes", type=int, default=2880)
    p.add_argument("--write-latest-copy", action="store_true", default=True)
    p.add_argument("--no-latest-copy", action="store_false", dest="write_latest_copy")
    p.add_argument("--tail-m15", type=int, default=60000)
    p.add_argument("--tail-h1", type=int, default=30000)
    p.add_argument("--tail-h4", type=int, default=10000)
    p.add_argument("--tail-d1", type=int, default=3000)
    p.add_argument("--tail-lower-tf", type=int, default=250000)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or run_id_text()
    out_root = resolve(args.out_root)
    run_dir = out_root / "runs" / (run_id + "_v2")
    latest_dir = out_root / "latest_v2"
    run_dir.mkdir(parents=True, exist_ok=True)

    csv_dir = resolve(args.csv_dir)
    manifest = parse_manifest(read_json(args.manifest_json))
    raw_rules = load_numeric_rules(args.numeric_rules_json)
    rules, excluded_rules = filter_pre_entry_rules(raw_rules)
    allowed_tags = load_promotable_tags(args.tag_recall_csv, promotable_only=args.promotable_only)
    frame = build_feature_frame_with_contract(csv_dir, tail_m15=args.tail_m15, tail_h1=args.tail_h1, tail_h4=args.tail_h4, tail_d1=args.tail_d1)
    lower = load_lower_tf(csv_dir, args)

    if args.start_time:
        frame = frame[frame["time"] >= pd.to_datetime(args.start_time)].copy()
    if args.end_time:
        frame = frame[frame["time"] <= pd.to_datetime(args.end_time)].copy()
    if args.max_bars and args.max_bars > 0:
        frame = frame.tail(args.max_bars).copy()
    frame = frame.reset_index(drop=True)

    candidates: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    tag_rows: list[dict[str, Any]] = []
    rule_eval_rows: list[dict[str, Any]] = []
    condition_attempts = 0
    missing_trade_param_rows = 0

    for i, row in frame.iterrows():
        entry_time = str(row.get("time"))
        for strategy in manifest:
            sid = clean(strategy.get("strategy_id"))
            if not sid:
                continue
            condition_attempts += 1
            ok, matched, failed, missing = evaluate_strategy(row, strategy)
            if not ok:
                continue
            params = extract_trade_params(strategy, sid, row)
            if params["entry_price"] is None or params["tp_price"] is None or params["sl_price"] is None:
                missing_trade_param_rows += 1
                continue
            direction = params["direction"]
            decision_key = make_decision_key(sid, direction, entry_time)
            candidate = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "decision_key": decision_key,
                "strategy_id": sid,
                "direction": direction,
                "entry_time": entry_time,
                "entry_price": round6(params["entry_price"]),
                "tp_price": round6(params["tp_price"]),
                "sl_price": round6(params["sl_price"]),
                "tp_pips": params["tp_pips"],
                "sl_pips": params["sl_pips"],
                "rr": round6(params["rr"]),
                "condition_count": len(strategy.get("conditions", [])),
                "matched_conditions": " | ".join(matched),
                "context_h1_close_time": clean(row.get("h1_close_time")),
                "context_h4_close_time": clean(row.get("h4_close_time")),
                "context_d1_close_time": clean(row.get("d1_close_time")),
                "source_row_index": i,
            }
            candidates.append(candidate)
            combined = row.copy()
            combined["decision_key"] = decision_key
            combined["strategy_id"] = sid
            combined["direction"] = direction
            combined["entry_time"] = entry_time
            hits, blocks, watches, evals = gate_numeric(combined, rules, allowed_tags)
            rule_eval_rows.extend(evals)
            for hit in hits:
                tag_rows.append({
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_id,
                    "decision_key": decision_key,
                    "strategy_id": sid,
                    "direction": direction,
                    "entry_time": entry_time,
                    "tag_group": clean(hit.get("tag_group")),
                    "tag_name": clean(hit.get("tag_name")),
                    "configured_action": clean(hit.get("configured_action")),
                    "rule_id": clean(hit.get("rule_id")),
                    "feature": clean(hit.get("feature")),
                    "op": clean(hit.get("op")),
                    "threshold": hit.get("threshold", ""),
                    "value": round6(hit.get("_matched_value", "")),
                    "tag_precision": round6(hit.get("tag_precision", "")),
                    "tag_recall": round6(hit.get("tag_recall", "")),
                    "tag_f1": round6(hit.get("tag_f1", "")),
                    "kept_false_hit_rate": round6(hit.get("kept_false_hit_rate", "")),
                    "source_rule_verdict": clean(hit.get("verdict")),
                })
            if blocks:
                gate_decision = "BLOCK"
                reason = "AI_REVIEW_NUMERIC_RULE_BLOCK_MATCH_V2_BRIDGE_AUDIT_ONLY"
            elif watches:
                gate_decision = "WATCH_ONLY"
                reason = "AI_REVIEW_NUMERIC_RULE_WATCH_MATCH_V2_BRIDGE_AUDIT_ONLY"
            else:
                gate_decision = "ALLOW_NUMERIC_AUDIT_ONLY"
                reason = "NO_AI_REVIEW_NUMERIC_RULE_MATCH_V2_BRIDGE_AUDIT_ONLY"
            outcome = first_touch_outcome(lower, candidate, args.outcome_horizon_minutes)
            gate_rows.append({
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "decision_key": decision_key,
                "strategy_id": sid,
                "direction": direction,
                "entry_time": entry_time,
                "entry_month": str(pd.to_datetime(entry_time).to_period("M")),
                "entry_price": candidate["entry_price"],
                "tp_price": candidate["tp_price"],
                "sl_price": candidate["sl_price"],
                "tp_pips": candidate["tp_pips"],
                "sl_pips": candidate["sl_pips"],
                "numeric_rule_hits": " | ".join(f"{clean(h.get('tag_group'))}:{clean(h.get('tag_name'))}" for h in hits),
                "block_hit_count": len(blocks),
                "block_hits": " | ".join(clean(h.get("rule_id")) for h in blocks),
                "watch_hit_count": len(watches),
                "watch_hits": " | ".join(clean(h.get("rule_id")) for h in watches),
                "numeric_gate_decision": gate_decision,
                "dispatch_ready": False,
                "outcome": outcome["outcome"],
                "exit_time": outcome["exit_time"],
                "exit_price": round6(outcome["exit_price"]),
                "profit_r": round6(outcome["profit_r"]),
                "result_source": outcome["result_source"],
                "reason": reason + "; future/post-entry rules excluded; dispatch_ready false; no live ledger mutation",
            })

    monthly_rows, strategy_rows, overall_rows = build_summaries(gate_rows)
    paths = {
        "candidates": run_dir / "gold_disc8_backtest_live_candidates_v2.csv",
        "gate": run_dir / "gold_disc8_backtest_numeric_gate_audit_v2.csv",
        "tag": run_dir / "gold_disc8_backtest_numeric_tag_hits_v2.csv",
        "rule_eval": run_dir / "gold_disc8_backtest_numeric_rule_eval_audit_v2.csv",
        "monthly": run_dir / "gold_disc8_backtest_monthly_summary_v2.csv",
        "strategy": run_dir / "gold_disc8_backtest_strategy_summary_v2.csv",
        "overall": run_dir / "gold_disc8_backtest_overall_summary_v2.csv",
        "excluded": run_dir / "gold_disc8_backtest_excluded_future_rules_v2.csv",
        "summary": run_dir / "gold_disc8_backtest_audit_summary_v2.json",
    }
    write_csv(paths["candidates"], candidates, CANDIDATE_COLUMNS)
    write_csv(paths["gate"], gate_rows, GATE_COLUMNS)
    write_csv(paths["tag"], tag_rows, TAG_COLUMNS)
    write_csv(paths["rule_eval"], rule_eval_rows, RULE_EVAL_COLUMNS)
    write_csv(paths["monthly"], monthly_rows, SUMMARY_COLUMNS)
    write_csv(paths["strategy"], strategy_rows, SUMMARY_COLUMNS)
    write_csv(paths["overall"], overall_rows, SUMMARY_COLUMNS)
    write_excluded(paths["excluded"], excluded_rules)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_BACKTEST_AUDIT_ONLY_V2_BRIDGE_NO_FUTURE_RULES_NO_LIVE_LEDGER_MUTATION",
        "run_id": run_id,
        "created_at": now_text(),
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "live_decision_ledger_mutated": False,
        "dispatch_ready_forced_false": True,
        "promotable_only": bool(args.promotable_only),
        "raw_numeric_rules_loaded": len(raw_rules),
        "pre_entry_rules_kept": len(rules),
        "future_rules_excluded": len(excluded_rules),
        "allowed_promotable_tags_count": None if allowed_tags is None else len(allowed_tags),
        "counts": {
            "scanned_m15_rows": int(len(frame)),
            "strategies": int(len(manifest)),
            "condition_attempts": int(condition_attempts),
            "candidate_rows": int(len(candidates)),
            "missing_trade_param_rows": int(missing_trade_param_rows),
            "rule_eval_rows": int(len(rule_eval_rows)),
            "tag_hit_rows": int(len(tag_rows)),
            "gate_rows": int(len(gate_rows)),
            "block_rows": int(sum(1 for r in gate_rows if r["numeric_gate_decision"] == "BLOCK")),
            "watch_rows": int(sum(1 for r in gate_rows if r["numeric_gate_decision"] == "WATCH_ONLY")),
            "allow_rows": int(sum(1 for r in gate_rows if r["numeric_gate_decision"] == "ALLOW_NUMERIC_AUDIT_ONLY")),
            "win_rows": int(sum(1 for r in gate_rows if r["outcome"] == "WIN")),
            "loss_rows": int(sum(1 for r in gate_rows if r["outcome"] == "LOSS")),
            "unresolved_rows": int(sum(1 for r in gate_rows if r["outcome"] not in {"WIN", "LOSS"})),
            "dispatch_ready_rows": 0,
        },
        "outputs": {k: str(v) for k, v in paths.items()},
    }
    write_json(paths["summary"], summary)
    if args.write_latest_copy:
        if latest_dir.exists():
            shutil.rmtree(windows_long_path(latest_dir))
        latest_dir.mkdir(parents=True, exist_ok=True)
        for src in paths.values():
            shutil.copy2(windows_long_path(src), windows_long_path(latest_dir / src.name))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
