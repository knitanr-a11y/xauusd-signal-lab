#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Apply DISC8 AI-review numeric tagger rules to latest live candidates.

Audit-only. No OpenAI, no Discord, no MT5 order_send, no SOT mutation.

This is the safe replacement for the previous hand-made proxy route.
It reads numeric rules built from actual AI-review tags and applies them to
latest DISC8 decision candidates after joining the current OHLC-derived feature row.

Even when a candidate is provisionally allowed, dispatch_ready is always False.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
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

from run_gold_disc8_live_decision_audit_forever_aligned import (  # noqa: E402
    add_indicators,
    attach_context,
    clean,
    read_ohlc_csv,
    windows_long_path,
)

DEFAULT_CANDIDATES_CSV = Path("data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_candidates.csv")
DEFAULT_DECISION_SUMMARY_JSON = Path("data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_audit_summary.json")
DEFAULT_RULES_JSON = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_rules.json")
DEFAULT_TAG_RECALL_CSV = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv")
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_latest_audit/latest")
SCHEMA_VERSION = "gold_disc8_ai_tag_numeric_tagger_latest_audit_v1_no_dispatch"
TAGGER_VALIDATION_STATUS = "AI_REVIEW_NUMERIC_TAGGER_AUDIT_ONLY_UNPROMOTED"
PROMOTABLE_VERDICT = "POTENTIALLY_PROMOTABLE_AFTER_MANUAL_REVIEW"

TAG_HIT_COLUMNS = [
    "created_at", "schema_version", "tagger_validation_status", "decision_key", "strategy_id", "direction",
    "entry_time", "tag_group", "tag_name", "configured_action", "rule_id", "feature", "op", "threshold",
    "value", "tag_precision", "tag_recall", "tag_f1", "kept_false_hit_rate", "source_rule_verdict",
]
GATE_COLUMNS = [
    "created_at", "schema_version", "tagger_validation_status", "decision_key", "strategy_id", "direction", "entry_time",
    "input_decision", "feature_join_status", "numeric_rule_hits", "block_hit_count", "block_hits",
    "watch_hit_count", "watch_hits", "numeric_gate_decision", "dispatch_ready", "reason",
]
RULE_EVAL_COLUMNS = [
    "decision_key", "strategy_id", "entry_time", "rule_id", "tag_group", "tag_name", "configured_action",
    "feature", "op", "threshold", "value", "matched", "reason",
]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"JSON not found: {p}")
    with open(windows_long_path(p), "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON root must be object: {p}")
    return obj


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_csv_required(path: Path, label: str) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    return pd.read_csv(windows_long_path(p), encoding="utf-8-sig")


def read_csv_optional(path: Path) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(windows_long_path(p), encoding="utf-8-sig")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def op_match(value: float, op: str, threshold: float) -> bool:
    if op == "<=":
        return value <= threshold
    if op == ">=":
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == ">":
        return value > threshold
    raise ValueError(f"unsupported op: {op}")


def build_feature_frame(csv_dir: Path, args: argparse.Namespace) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=args.tail_m15))
    h1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=args.tail_h1))
    h4 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=args.tail_h4))
    d1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=args.tail_d1))
    return attach_context(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)


def feature_map(frame: pd.DataFrame) -> dict[pd.Timestamp, pd.Series]:
    out: dict[pd.Timestamp, pd.Series] = {}
    for _, row in frame.iterrows():
        ts = pd.to_datetime(row.get("time"), errors="coerce")
        if not pd.isna(ts):
            out[pd.Timestamp(ts)] = row
    return out


def load_rules(path: Path) -> list[dict[str, Any]]:
    obj = read_json(path)
    rules = obj.get("rules", [])
    if not isinstance(rules, list):
        raise RuntimeError(f"rules JSON missing list field 'rules': {resolve(path)}")
    return [r for r in rules if isinstance(r, dict)]


def load_promotable_filter(path: Path, *, promotable_only: bool) -> set[tuple[str, str, str]] | None:
    if not promotable_only:
        return None
    df = read_csv_optional(path)
    if df.empty:
        return None
    required = {"strategy_id", "tag_group", "tag_name", "verdict"}
    if not required.issubset(set(df.columns)):
        return None
    filt = df[df["verdict"].astype(str).eq(PROMOTABLE_VERDICT)].copy()
    return {(clean(r.strategy_id), clean(r.tag_group), clean(r.tag_name)) for r in filt.itertuples(index=False)}


def candidate_feature_row(candidate: pd.Series, fmap: dict[pd.Timestamp, pd.Series]) -> tuple[dict[str, Any], str]:
    combined = {str(k): candidate.get(k) for k in candidate.index}
    ts = pd.to_datetime(candidate.get("entry_time"), errors="coerce")
    if pd.isna(ts):
        return combined, "ENTRY_TIME_PARSE_FAILED"
    feat = fmap.get(pd.Timestamp(ts))
    if feat is None:
        return combined, "FEATURE_ROW_NOT_FOUND"
    for k, v in feat.to_dict().items():
        # Preserve candidate fields when they already exist; add OHLC/indicator features otherwise.
        if k not in combined or clean(combined.get(k)) == "":
            combined[k] = v
        else:
            combined[f"feature_{k}"] = v
    return combined, "JOIN_OK"


def evaluate_rule(row: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    feature = clean(rule.get("feature"))
    op = clean(rule.get("op"))
    threshold = safe_float(rule.get("threshold"))
    rule_id = clean(rule.get("rule_id"))
    if not feature or not op or threshold is None:
        return False, {"rule_id": rule_id, "feature": feature, "op": op, "threshold": threshold, "value": "", "matched": False, "reason": "INVALID_RULE"}
    value = safe_float(row.get(feature))
    if value is None:
        return False, {"rule_id": rule_id, "feature": feature, "op": op, "threshold": threshold, "value": "", "matched": False, "reason": "MISSING_FEATURE_VALUE"}
    ok = op_match(value, op, threshold)
    return ok, {"rule_id": rule_id, "feature": feature, "op": op, "threshold": threshold, "value": value, "matched": ok, "reason": "OK" if ok else "NO_MATCH"}


def rules_for_strategy(rules: list[dict[str, Any]], strategy_id: str, allowed_tags: set[tuple[str, str, str]] | None) -> list[dict[str, Any]]:
    out = []
    for r in rules:
        sid = clean(r.get("strategy_id"))
        group = clean(r.get("tag_group"))
        tag = clean(r.get("tag_name"))
        if sid != strategy_id:
            continue
        if allowed_tags is not None and (sid, group, tag) not in allowed_tags:
            continue
        out.append(r)
    return out


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    mkdirp(out_dir)

    candidates = read_csv_required(args.candidates_csv, "latest candidates CSV")
    decision_summary = read_json(args.decision_summary_json) if resolve(args.decision_summary_json).exists() else {}
    rules = load_rules(args.rules_json)
    allowed_tags = load_promotable_filter(args.tag_recall_csv, promotable_only=args.promotable_only)
    frame = build_feature_frame(resolve(args.csv_dir), args)
    fmap = feature_map(frame)

    tag_hits: list[dict[str, Any]] = []
    gate_rows: list[dict[str, Any]] = []
    rule_eval_rows: list[dict[str, Any]] = []
    feature_join_ok = 0
    missing_feature_rules = 0
    evaluated_rules = 0

    for _, cand in candidates.iterrows():
        sid = clean(cand.get("strategy_id"))
        decision_key = clean(cand.get("decision_key"))
        direction = clean(cand.get("direction"))
        entry_time = clean(cand.get("entry_time"))
        combined, join_status = candidate_feature_row(cand, fmap)
        if join_status == "JOIN_OK":
            feature_join_ok += 1
        matched_rules = []
        for rule in rules_for_strategy(rules, sid, allowed_tags):
            evaluated_rules += 1
            ok, detail = evaluate_rule(combined, rule)
            if detail["reason"] == "MISSING_FEATURE_VALUE":
                missing_feature_rules += 1
            row_eval = {
                "decision_key": decision_key,
                "strategy_id": sid,
                "entry_time": entry_time,
                "rule_id": clean(rule.get("rule_id")),
                "tag_group": clean(rule.get("tag_group")),
                "tag_name": clean(rule.get("tag_name")),
                "configured_action": clean(rule.get("configured_action")),
                "feature": detail.get("feature", ""),
                "op": detail.get("op", ""),
                "threshold": detail.get("threshold", ""),
                "value": detail.get("value", ""),
                "matched": bool(ok),
                "reason": detail.get("reason", ""),
            }
            rule_eval_rows.append(row_eval)
            if not ok:
                continue
            matched_rules.append(rule)
            tag_hits.append({
                "created_at": now_text(),
                "schema_version": SCHEMA_VERSION,
                "tagger_validation_status": TAGGER_VALIDATION_STATUS,
                "decision_key": decision_key,
                "strategy_id": sid,
                "direction": direction,
                "entry_time": entry_time,
                "tag_group": clean(rule.get("tag_group")),
                "tag_name": clean(rule.get("tag_name")),
                "configured_action": clean(rule.get("configured_action")),
                "rule_id": clean(rule.get("rule_id")),
                "feature": clean(rule.get("feature")),
                "op": clean(rule.get("op")),
                "threshold": rule.get("threshold", ""),
                "value": row_eval.get("value", ""),
                "tag_precision": rule.get("tag_precision", ""),
                "tag_recall": rule.get("tag_recall", ""),
                "tag_f1": rule.get("tag_f1", ""),
                "kept_false_hit_rate": rule.get("kept_false_hit_rate", ""),
                "source_rule_verdict": rule.get("verdict", ""),
            })
        block_hits = [r for r in matched_rules if clean(r.get("configured_action")) == "block"]
        watch_hits = [r for r in matched_rules if clean(r.get("configured_action")) == "watch_only"]
        if block_hits:
            gate_decision = "BLOCK"
            reason = "AI_REVIEW_NUMERIC_RULE_BLOCK_MATCH_AUDIT_ONLY"
        elif watch_hits:
            gate_decision = "WATCH_ONLY"
            reason = "AI_REVIEW_NUMERIC_RULE_WATCH_MATCH_AUDIT_ONLY"
        else:
            gate_decision = "ALLOW_NUMERIC_AUDIT_ONLY"
            reason = "NO_AI_REVIEW_NUMERIC_RULE_MATCH_AUDIT_ONLY"
        gate_rows.append({
            "created_at": now_text(),
            "schema_version": SCHEMA_VERSION,
            "tagger_validation_status": TAGGER_VALIDATION_STATUS,
            "decision_key": decision_key,
            "strategy_id": sid,
            "direction": direction,
            "entry_time": entry_time,
            "input_decision": clean(cand.get("decision")),
            "feature_join_status": join_status,
            "numeric_rule_hits": " | ".join(f"{clean(r.get('tag_group'))}:{clean(r.get('tag_name'))}" for r in matched_rules),
            "block_hit_count": len(block_hits),
            "block_hits": " | ".join(clean(r.get("rule_id")) for r in block_hits),
            "watch_hit_count": len(watch_hits),
            "watch_hits": " | ".join(clean(r.get("rule_id")) for r in watch_hits),
            "numeric_gate_decision": gate_decision,
            "dispatch_ready": False,
            "reason": reason + "; dispatch_ready forced false; no Discord/MT5/OpenAI",
        })

    tag_hits_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_latest_tag_hits.csv"
    gate_audit_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_latest_gate_audit.csv"
    rule_eval_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_latest_rule_eval_audit.csv"
    summary_json = out_dir / "gold_disc8_ai_tag_numeric_tagger_latest_audit_summary.json"
    write_csv(tag_hits_csv, tag_hits, TAG_HIT_COLUMNS)
    write_csv(gate_audit_csv, gate_rows, GATE_COLUMNS)
    write_csv(rule_eval_csv, rule_eval_rows, RULE_EVAL_COLUMNS)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_AI_REVIEW_NUMERIC_TAGGER_LATEST_APPLIED",
        "tagger_validation_status": TAGGER_VALIDATION_STATUS,
        "promotable_only": bool(args.promotable_only),
        "allowed_promotable_tags_count": None if allowed_tags is None else len(allowed_tags),
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "decision_ledger_mutated": False,
        "dispatch_ready_forced_false": True,
        "inputs": {
            "candidates_csv": str(resolve(args.candidates_csv)),
            "decision_summary_json": str(resolve(args.decision_summary_json)),
            "rules_json": str(resolve(args.rules_json)),
            "tag_recall_csv": str(resolve(args.tag_recall_csv)),
            "csv_dir": str(resolve(args.csv_dir)),
            "decision_summary_candidates_detected": decision_summary.get("candidates_detected"),
            "decision_summary_pending_tagger_count": decision_summary.get("pending_tagger_count"),
        },
        "outputs": {
            "summary_json": str(summary_json),
            "tag_hits_csv": str(tag_hits_csv),
            "gate_audit_csv": str(gate_audit_csv),
            "rule_eval_csv": str(rule_eval_csv),
        },
        "counts": {
            "candidate_rows": int(len(candidates)),
            "feature_join_ok_rows": int(feature_join_ok),
            "feature_join_missing_rows": int(len(candidates) - feature_join_ok),
            "numeric_rules_loaded": int(len(rules)),
            "rule_evaluations": int(evaluated_rules),
            "rule_missing_feature_evaluations": int(missing_feature_rules),
            "tag_hit_rows": int(len(tag_hits)),
            "gate_audit_rows": int(len(gate_rows)),
            "block_rows": int(sum(1 for r in gate_rows if r.get("numeric_gate_decision") == "BLOCK")),
            "watch_rows": int(sum(1 for r in gate_rows if r.get("numeric_gate_decision") == "WATCH_ONLY")),
            "allow_rows": int(sum(1 for r in gate_rows if r.get("numeric_gate_decision") == "ALLOW_NUMERIC_AUDIT_ONLY")),
            "dispatch_ready_rows": 0,
        },
        "promotion_rule": "This latest audit does not enable dispatch. Promote only after repeated live audit review and explicit user approval.",
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply DISC8 AI-review numeric tagger to latest candidates. Audit-only.")
    p.add_argument("--candidates-csv", type=Path, default=DEFAULT_CANDIDATES_CSV)
    p.add_argument("--decision-summary-json", type=Path, default=DEFAULT_DECISION_SUMMARY_JSON)
    p.add_argument("--rules-json", type=Path, default=DEFAULT_RULES_JSON)
    p.add_argument("--tag-recall-csv", type=Path, default=DEFAULT_TAG_RECALL_CSV)
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--promotable-only", action="store_true", default=True, help="Use only tag_recall rows marked POTENTIALLY_PROMOTABLE_AFTER_MANUAL_REVIEW when available.")
    p.add_argument("--all-rules", action="store_false", dest="promotable_only", help="Evaluate all numeric rules from rules JSON.")
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=800)
    p.add_argument("--tail-d1", type=int, default=500)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
