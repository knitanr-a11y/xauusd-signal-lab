#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
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

from audit_gold_disc8_numeric_rule_feature_contract import (  # noqa: E402
    CANDIDATE_AUDIT_COLUMNS,
    DEFAULT_CSV_DIR,
    DEFAULT_MANIFEST_JSON,
    DEFAULT_OUT_DIR,
    DEFAULT_RULES_JSON,
    DEFAULT_SOURCE_FEATURE_SNAPSHOT_CSV,
    DEFAULT_TAG_RECALL_CSV,
    RULE_AUDIT_COLUMNS,
    audit_rule,
    build_candidate_feature_frame,
    mkdirp,
    promotable_tags,
    read_csv_optional,
    read_json,
    resolve,
    strategy_summary,
    write_csv,
    write_json,
)
from gold_disc8_feature_contract_bridge import build_feature_frame_with_contract, filter_pre_entry_rules  # noqa: E402
from run_gold_disc8_live_decision_audit_forever_aligned import parse_manifest  # noqa: E402

SCHEMA_VERSION = "gold_disc8_numeric_rule_feature_contract_audit_v2_bridge"
EXCLUDED_COLUMNS = ["rule_id", "strategy_id", "tag_group", "tag_name", "configured_action", "feature", "op", "threshold", "excluded_reason"]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_rules(path: Path) -> list[dict[str, Any]]:
    obj = read_json(path)
    rules = obj.get("rules", [])
    if not isinstance(rules, list):
        raise RuntimeError("rules JSON missing list field: rules")
    return [r for r in rules if isinstance(r, dict)]


def write_excluded(path: Path, rows: list[dict[str, Any]]) -> None:
    out = [{c: r.get(c, "") for c in EXCLUDED_COLUMNS} for r in rows]
    write_csv(path, out, EXCLUDED_COLUMNS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="DISC8 numeric feature contract audit v2")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--rules-json", type=Path, default=DEFAULT_RULES_JSON)
    p.add_argument("--tag-recall-csv", type=Path, default=DEFAULT_TAG_RECALL_CSV)
    p.add_argument("--source-feature-snapshot-csv", type=Path, default=DEFAULT_SOURCE_FEATURE_SNAPSHOT_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--max-bars", type=int, default=12000)
    p.add_argument("--tail-m15", type=int, default=60000)
    p.add_argument("--tail-h1", type=int, default=30000)
    p.add_argument("--tail-h4", type=int, default=10000)
    p.add_argument("--tail-d1", type=int, default=3000)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    mkdirp(out_dir)

    raw_rules = load_rules(args.rules_json)
    rules, excluded = filter_pre_entry_rules(raw_rules)
    promo = promotable_tags(args.tag_recall_csv)
    manifest = parse_manifest(read_json(args.manifest_json))
    live_df = build_feature_frame_with_contract(
        resolve(args.csv_dir),
        tail_m15=args.tail_m15,
        tail_h1=args.tail_h1,
        tail_h4=args.tail_h4,
        tail_d1=args.tail_d1,
    )
    if args.max_bars and args.max_bars > 0:
        live_df = live_df.tail(args.max_bars).copy()
    live_df = live_df.reset_index(drop=True)
    cand_df = build_candidate_feature_frame(live_df, manifest)
    source_df = read_csv_optional(args.source_feature_snapshot_csv)

    rule_rows = [audit_rule(r, source_df, live_df, cand_df, promo) for r in rules]
    strat_rows = strategy_summary(rule_rows, cand_df)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_FEATURE_BRIDGE_AUDIT_ONLY",
        "created_at": now_text(),
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "live_decision_ledger_mutated": False,
        "raw_rules_loaded": len(raw_rules),
        "pre_entry_rules_kept": len(rules),
        "excluded_rules": len(excluded),
        "promotable_tags": len(promo),
        "live_rows": len(live_df),
        "candidate_rows": len(cand_df),
        "source_feature_rows": len(source_df),
        "rules_missing_candidate_feature": sum(1 for r in rule_rows if r.get("diagnosis") == "MISSING_CANDIDATE_FEATURE"),
        "rules_ok_can_hit_candidates": sum(1 for r in rule_rows if r.get("diagnosis") == "OK_RULE_CAN_HIT_CANDIDATES"),
        "rules_threshold_outside_candidate_range": sum(1 for r in rule_rows if r.get("diagnosis") == "THRESHOLD_OUTSIDE_CANDIDATE_RANGE"),
        "rules_no_hit": sum(1 for r in rule_rows if int(r.get("candidate_hit_count") or 0) == 0),
        "candidate_hit_total": sum(int(r.get("candidate_hit_count") or 0) for r in rule_rows),
        "promotable_candidate_hit_total": sum(int(r.get("candidate_hit_count") or 0) for r in rule_rows if bool(r.get("is_promotable"))),
        "outputs": {
            "summary_json": str(out_dir / "gold_disc8_numeric_rule_feature_contract_audit_v2_summary.json"),
            "rule_audit_csv": str(out_dir / "gold_disc8_numeric_rule_feature_contract_rule_audit_v2.csv"),
            "strategy_summary_csv": str(out_dir / "gold_disc8_numeric_rule_feature_contract_strategy_summary_v2.csv"),
            "excluded_rules_csv": str(out_dir / "gold_disc8_numeric_rule_feature_contract_excluded_rules_v2.csv"),
        },
    }
    write_csv(out_dir / "gold_disc8_numeric_rule_feature_contract_rule_audit_v2.csv", rule_rows, RULE_AUDIT_COLUMNS)
    write_csv(out_dir / "gold_disc8_numeric_rule_feature_contract_strategy_summary_v2.csv", strat_rows, CANDIDATE_AUDIT_COLUMNS)
    write_excluded(out_dir / "gold_disc8_numeric_rule_feature_contract_excluded_rules_v2.csv", excluded)
    write_json(out_dir / "gold_disc8_numeric_rule_feature_contract_audit_v2_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
