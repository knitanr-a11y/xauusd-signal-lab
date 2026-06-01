#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate DISC8 provisional pre-send tagger proxy against the original 568-trade universe.

Audit-only. No OpenAI, no Discord, no MT5 order_send, no SOT mutation.

Correct purpose:
- Use original 568 AI-reviewed DISC8 trades as the base universe.
- Label 292 group-tag-filtered source-of-truth rows as actual_kept.
- Label the remaining 276 rows as actual_blocked.
- Apply the provisional live pre-send tagger proxy to the full 568 universe.
- Measure whether the proxy can reproduce actual_blocked without falsely blocking actual_kept.

This is NOT a second filter on the already-kept 292 rows.
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
    CANDIDATE_COLUMNS,
    add_indicators,
    attach_context,
    clean,
    evaluate_strategy,
    make_decision_key,
    parse_manifest,
    pips_to_price,
    read_json,
    read_ohlc_csv,
    windows_long_path,
)
from apply_gold_disc8_pre_send_tagger_audit_latest import (  # noqa: E402
    TAGGER_VALIDATION_STATUS,
    gate_for_candidate,
    provisional_tags_for_candidate,
)

DEFAULT_BASE_TRADE_CSV = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/disc8_review_trade_outcome_sample.csv")
DEFAULT_KEPT_LEDGER_CSV = Path("data/gold_disc8/source_of_truth/group_tag_filtered/group_tag_filtered_source_trade_ledger.csv")
DEFAULT_RULE_HITS_CSV = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_group_tag_filter_rule_hits.csv")
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_MANIFEST_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.json")
DEFAULT_GATE_RULES_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_pre_send_tagger_proxy_recall_568")
SCHEMA_VERSION = "gold_disc8_pre_send_tagger_proxy_recall_568_v1"

TRADE_AUDIT_COLUMNS = [
    "schema_version", "tagger_validation_status", "trade_id", "strategy_id", "direction", "entry_time",
    "truth_label", "truth_block_rule_hits", "truth_block_tags", "feature_time", "feature_join_status",
    "condition_parity_full_match", "matched_count", "condition_count", "profit_r_num", "is_win", "is_loss",
    "proxy_gate_decision", "proxy_binary", "confusion_class", "dispatch_ready", "tag_hit_count", "tag_hits",
    "block_hit_count", "block_hits", "watch_hit_count", "watch_hits", "matched_conditions", "failed_conditions", "reason",
]

CONFUSION_COLUMNS = ["truth_label", "proxy_binary", "trade_count", "win_count", "loss_count", "win_rate", "profit_factor", "avg_r", "total_r"]
STRATEGY_CONFUSION_COLUMNS = ["strategy_id"] + CONFUSION_COLUMNS
TAG_RECALL_COLUMNS = [
    "strategy_id", "tag_group", "tag_name", "truth_block_hit_count", "proxy_hit_count", "true_positive_count",
    "false_positive_count", "false_negative_count", "precision_vs_truth_block_tag", "recall_vs_truth_block_tag",
    "truth_hit_win_rate", "truth_hit_profit_factor", "truth_hit_avg_r", "truth_hit_total_r",
    "proxy_hit_win_rate", "proxy_hit_profit_factor", "proxy_hit_avg_r", "proxy_hit_total_r",
    "verdict",
]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})


def read_csv_required(path: Path, label: str) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    df = pd.read_csv(windows_long_path(p), encoding="utf-8-sig")
    if df.empty:
        raise RuntimeError(f"{label} is empty: {p}")
    return df


def read_csv_optional(path: Path) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(windows_long_path(p), encoding="utf-8-sig")


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


def trade_r(row: pd.Series | dict[str, Any]) -> float:
    getter = row.get if hasattr(row, "get") else lambda _k: None
    for col in ["profit_r_num", "profit_r"]:
        x = safe_float(getter(col))
        if x is not None:
            return float(x)
    return 0.0


def metrics(values: list[float]) -> dict[str, Any]:
    n = len(values)
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]
    pos = sum(wins)
    neg = sum(losses)
    pf = 999.0 if abs(neg) <= 1e-12 and pos > 0 else (0.0 if abs(neg) <= 1e-12 else pos / abs(neg))
    return {
        "trade_count": n,
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": None if n == 0 else len(wins) / n,
        "profit_factor": pf,
        "avg_r": None if n == 0 else sum(values) / n,
        "total_r": sum(values),
    }


def fm(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, 6)
    return value


def build_feature_frame(csv_dir: Path, args: argparse.Namespace) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=args.tail_m15))
    h1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=args.tail_h1))
    h4 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=args.tail_h4))
    d1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=args.tail_d1))
    return attach_context(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)


def build_feature_map(frame: pd.DataFrame) -> dict[pd.Timestamp, pd.Series]:
    out: dict[pd.Timestamp, pd.Series] = {}
    for _, row in frame.iterrows():
        ts = pd.to_datetime(row.get("time"), errors="coerce")
        if not pd.isna(ts):
            out[pd.Timestamp(ts)] = row
    return out


def feature_lookup_time(trade: pd.Series) -> pd.Timestamp | None:
    # Source trade ledgers use entry_time for signal open and m15_bar_open_time for source M15 bar.
    # Live audit evaluates signal row by entry_time. Fallback preserves compatibility.
    for col in ["entry_time", "m15_bar_open_time"]:
        ts = pd.to_datetime(trade.get(col), errors="coerce")
        if not pd.isna(ts):
            return pd.Timestamp(ts)
    return None


def key_set(df: pd.DataFrame) -> set[str]:
    if "trade_id" not in df.columns:
        raise RuntimeError("trade_id column is required")
    return {clean(x) for x in df["trade_id"].tolist() if clean(x)}


def build_truth_rule_maps(rule_hits: pd.DataFrame) -> tuple[dict[str, list[str]], dict[str, set[tuple[str, str, str]]]]:
    by_trade: dict[str, list[str]] = {}
    tag_by_trade: dict[str, set[tuple[str, str, str]]] = {}
    if rule_hits.empty:
        return by_trade, tag_by_trade
    for _, r in rule_hits.iterrows():
        if str(r.get("blocks_trade", "")).lower() not in {"true", "1", "yes"}:
            continue
        tid = clean(r.get("trade_id"))
        if not tid:
            continue
        rid = clean(r.get("rule_id")) or f"{clean(r.get('strategy_id'))}:{clean(r.get('tag_group'))}:{clean(r.get('tag_name'))}"
        by_trade.setdefault(tid, []).append(rid)
        tag_by_trade.setdefault(tid, set()).add((clean(r.get("strategy_id")), clean(r.get("tag_group")), clean(r.get("tag_name"))))
    return by_trade, tag_by_trade


def candidate_from_trade(trade: pd.Series, feat_row: pd.Series | None, strategy: dict[str, Any], gate_rules: dict[str, Any]) -> tuple[dict[str, Any], bool, list[str], list[str], str]:
    sid = clean(trade.get("strategy_id"))
    direction = clean(trade.get("direction"))
    entry_time = clean(trade.get("entry_time"))
    entry_price = safe_float(trade.get("entry_price"))
    tp_price = safe_float(trade.get("tp_price"))
    sl_price = safe_float(trade.get("sl_price"))
    if feat_row is None:
        parity = False
        matched: list[str] = []
        failed: list[str] = []
        reason = "FEATURE_ROW_NOT_FOUND"
    else:
        parity, matched, failed, _missing = evaluate_strategy(feat_row, strategy)
        reason = "OK" if parity else "CONDITION_RECONSTRUCTION_NOT_FULL_MATCH"
    if tp_price is None or sl_price is None:
        tp_step = pips_to_price(trade.get("tp_pips"))
        sl_step = pips_to_price(trade.get("sl_pips"))
        if entry_price is not None and tp_step is not None and sl_step is not None:
            if direction.upper() == "BUY":
                tp_price = entry_price + tp_step
                sl_price = entry_price - sl_step
            else:
                tp_price = entry_price - tp_step
                sl_price = entry_price + sl_step
    candidate = {c: "" for c in CANDIDATE_COLUMNS}
    candidate.update({
        "created_at": now_text(),
        "schema_version": SCHEMA_VERSION,
        "decision_key": make_decision_key(sid, direction, entry_time),
        "decision": "HISTORICAL_568_VALIDATION_INPUT",
        "dispatch_ready": False,
        "strategy_id": sid,
        "direction": direction,
        "entry_time": entry_time,
        "entry_price": "" if entry_price is None else entry_price,
        "tp_price": "" if tp_price is None else tp_price,
        "sl_price": "" if sl_price is None else sl_price,
        "tp_pips": clean(trade.get("tp_pips")),
        "sl_pips": clean(trade.get("sl_pips")),
        "rr": clean(trade.get("rr")) or clean(trade.get("exit_model")),
        "condition_count": len(strategy.get("conditions", [])),
        "matched_conditions": " | ".join(matched),
        "failed_conditions": " | ".join(failed),
        "requires_pre_send_tagger": bool(gate_rules.get("requires_pre_send_tagger", True)),
        "tagger_status": "HISTORICAL_568_VALIDATION_PROXY",
        "strict_no_future_ok": clean(trade.get("htf_no_future_ok"), ""),
        "context_h1_close_time": clean(trade.get("h1_source_close_time")),
        "context_h4_close_time": clean(trade.get("h4_source_close_time")),
        "context_d1_close_time": clean(trade.get("d1_source_close_time")),
        "reason": reason,
    })
    return candidate, parity, matched, failed, reason


def binary_from_proxy(gate_decision: str) -> str:
    if gate_decision == "BLOCK":
        return "proxy_block"
    return "proxy_keep"


def confusion_class(truth_label: str, proxy_binary: str) -> str:
    if truth_label == "actual_blocked" and proxy_binary == "proxy_block":
        return "true_positive_blocked"
    if truth_label == "actual_blocked" and proxy_binary == "proxy_keep":
        return "false_negative_missed_block"
    if truth_label == "actual_kept" and proxy_binary == "proxy_block":
        return "false_positive_wrong_block"
    if truth_label == "actual_kept" and proxy_binary == "proxy_keep":
        return "true_negative_kept"
    return "unknown"


def summarize_confusion(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for truth in ["actual_kept", "actual_blocked"]:
        for proxy in ["proxy_keep", "proxy_block"]:
            vals = [float(r["profit_r_num"]) for r in rows if r["truth_label"] == truth and r["proxy_binary"] == proxy]
            m = metrics(vals)
            out.append({
                "truth_label": truth,
                "proxy_binary": proxy,
                "trade_count": m["trade_count"],
                "win_count": m["win_count"],
                "loss_count": m["loss_count"],
                "win_rate": fm(m["win_rate"]),
                "profit_factor": fm(m["profit_factor"]),
                "avg_r": fm(m["avg_r"]),
                "total_r": fm(m["total_r"]),
            })
    return out


def summarize_strategy_confusion(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for sid in sorted({r["strategy_id"] for r in rows}):
        sub = [r for r in rows if r["strategy_id"] == sid]
        for base in summarize_confusion(sub):
            b = dict(base)
            b["strategy_id"] = sid
            out.append(b)
    return out


def summarize_tag_recall(rows: list[dict[str, Any]], tag_rows: list[dict[str, Any]], truth_tag_by_trade: dict[str, set[tuple[str, str, str]]]) -> list[dict[str, Any]]:
    by_trade = {r["trade_id"]: r for r in rows}
    proxy_tags = {(clean(t.get("strategy_id")), clean(t.get("tag_group")), clean(t.get("tag_name"))) for t in tag_rows}
    truth_tags = set()
    for s in truth_tag_by_trade.values():
        truth_tags.update(s)
    all_tags = sorted(proxy_tags | truth_tags)
    out = []
    for sid, tg, tn in all_tags:
        truth_set = {tid for tid, tags in truth_tag_by_trade.items() if (sid, tg, tn) in tags}
        proxy_set = {clean(t.get("trade_id")) for t in tag_rows if clean(t.get("strategy_id")) == sid and clean(t.get("tag_group")) == tg and clean(t.get("tag_name")) == tn}
        tp = truth_set & proxy_set
        fp = proxy_set - truth_set
        fn = truth_set - proxy_set
        precision = None if len(proxy_set) == 0 else len(tp) / len(proxy_set)
        recall = None if len(truth_set) == 0 else len(tp) / len(truth_set)
        truth_vals = [float(by_trade[tid]["profit_r_num"]) for tid in truth_set if tid in by_trade]
        proxy_vals = [float(by_trade[tid]["profit_r_num"]) for tid in proxy_set if tid in by_trade]
        tm = metrics(truth_vals)
        pm = metrics(proxy_vals)
        verdict = "NO_TRUTH_TAG"
        if truth_set:
            if recall is not None and recall >= 0.7 and precision is not None and precision >= 0.7:
                verdict = "PROXY_REPRODUCES_TRUTH_TAG"
            elif recall is not None and recall < 0.3:
                verdict = "LOW_RECALL_DO_NOT_PROMOTE"
            elif precision is not None and precision < 0.5:
                verdict = "LOW_PRECISION_DO_NOT_PROMOTE"
            else:
                verdict = "PARTIAL_RECALL_REVIEW"
        out.append({
            "strategy_id": sid,
            "tag_group": tg,
            "tag_name": tn,
            "truth_block_hit_count": len(truth_set),
            "proxy_hit_count": len(proxy_set),
            "true_positive_count": len(tp),
            "false_positive_count": len(fp),
            "false_negative_count": len(fn),
            "precision_vs_truth_block_tag": fm(precision),
            "recall_vs_truth_block_tag": fm(recall),
            "truth_hit_win_rate": fm(tm["win_rate"]),
            "truth_hit_profit_factor": fm(tm["profit_factor"]),
            "truth_hit_avg_r": fm(tm["avg_r"]),
            "truth_hit_total_r": fm(tm["total_r"]),
            "proxy_hit_win_rate": fm(pm["win_rate"]),
            "proxy_hit_profit_factor": fm(pm["profit_factor"]),
            "proxy_hit_avg_r": fm(pm["avg_r"]),
            "proxy_hit_total_r": fm(pm["total_r"]),
            "verdict": verdict,
        })
    return out


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    mkdirp(out_dir)

    base = read_csv_required(args.base_trade_csv, "base 568 trade CSV")
    kept = read_csv_required(args.kept_ledger_csv, "kept SOT 292 ledger CSV")
    rule_hits = read_csv_optional(args.rule_hits_csv)
    manifest_obj = read_json(args.manifest_json)
    gate_rules = read_json(args.gate_rules_json)
    manifest = {clean(s.get("strategy_id")): s for s in parse_manifest(manifest_obj)}

    kept_ids = key_set(kept)
    base_ids = key_set(base)
    missing_kept = sorted(kept_ids - base_ids)
    if missing_kept:
        raise RuntimeError(f"Kept SOT contains trade_ids not present in base universe: {missing_kept[:10]}")

    truth_rule_by_trade, truth_tag_by_trade = build_truth_rule_maps(rule_hits)
    frame = build_feature_frame(resolve(args.csv_dir), args)
    fmap = build_feature_map(frame)

    trade_rows: list[dict[str, Any]] = []
    tag_rows: list[dict[str, Any]] = []
    join_ok = 0
    parity_ok = 0
    strategy_missing = 0

    for _, trade in base.iterrows():
        tid = clean(trade.get("trade_id"))
        sid = clean(trade.get("strategy_id"))
        strategy = manifest.get(sid)
        if strategy is None:
            strategy_missing += 1
            continue
        truth = "actual_kept" if tid in kept_ids else "actual_blocked"
        ftime = feature_lookup_time(trade)
        feat = fmap.get(ftime) if ftime is not None else None
        join_status = "JOIN_OK" if feat is not None else "FEATURE_TIME_NOT_FOUND"
        if feat is not None:
            join_ok += 1
        candidate, parity, matched, failed, reason = candidate_from_trade(trade, feat, strategy, gate_rules)
        if parity:
            parity_ok += 1
        tags = provisional_tags_for_candidate(pd.Series(candidate), gate_rules)
        for t in tags:
            t2 = dict(t)
            t2["trade_id"] = tid
            tag_rows.append(t2)
        gate = gate_for_candidate(pd.Series(candidate), tags, gate_rules)
        proxy_binary = binary_from_proxy(clean(gate.get("provisional_gate_decision")))
        r_value = trade_r(trade)
        row = {
            "schema_version": SCHEMA_VERSION,
            "tagger_validation_status": TAGGER_VALIDATION_STATUS,
            "trade_id": tid,
            "strategy_id": sid,
            "direction": clean(trade.get("direction")),
            "entry_time": clean(trade.get("entry_time")),
            "truth_label": truth,
            "truth_block_rule_hits": " | ".join(sorted(set(truth_rule_by_trade.get(tid, [])))),
            "truth_block_tags": " | ".join(sorted({f"{a}:{b}:{c}" for a, b, c in truth_tag_by_trade.get(tid, set())})),
            "feature_time": "" if ftime is None else str(ftime),
            "feature_join_status": join_status,
            "condition_parity_full_match": bool(parity),
            "matched_count": len(matched),
            "condition_count": len(strategy.get("conditions", [])),
            "profit_r_num": r_value,
            "is_win": bool(r_value > 0),
            "is_loss": bool(r_value < 0),
            "proxy_gate_decision": clean(gate.get("provisional_gate_decision")),
            "proxy_binary": proxy_binary,
            "confusion_class": confusion_class(truth, proxy_binary),
            "dispatch_ready": False,
            "tag_hit_count": gate.get("tag_hit_count", 0),
            "tag_hits": gate.get("tag_hits", ""),
            "block_hit_count": gate.get("block_hit_count", 0),
            "block_hits": gate.get("block_hits", ""),
            "watch_hit_count": gate.get("watch_hit_count", 0),
            "watch_hits": gate.get("watch_hits", ""),
            "matched_conditions": candidate.get("matched_conditions", ""),
            "failed_conditions": candidate.get("failed_conditions", ""),
            "reason": reason + "; " + clean(gate.get("reason")),
        }
        trade_rows.append(row)

    confusion_rows = summarize_confusion(trade_rows)
    strategy_confusion_rows = summarize_strategy_confusion(trade_rows)
    tag_recall_rows = summarize_tag_recall(trade_rows, tag_rows, truth_tag_by_trade)

    trade_audit_csv = out_dir / "gold_disc8_proxy_recall_568_trade_audit.csv"
    confusion_csv = out_dir / "gold_disc8_proxy_recall_568_confusion_summary.csv"
    strategy_confusion_csv = out_dir / "gold_disc8_proxy_recall_568_strategy_confusion_summary.csv"
    tag_recall_csv = out_dir / "gold_disc8_proxy_recall_568_tag_recall_summary.csv"
    tag_hits_csv = out_dir / "gold_disc8_proxy_recall_568_proxy_tag_hits.csv"
    summary_json = out_dir / "gold_disc8_proxy_recall_568_summary.json"

    write_csv(trade_audit_csv, trade_rows, TRADE_AUDIT_COLUMNS)
    write_csv(confusion_csv, confusion_rows, CONFUSION_COLUMNS)
    write_csv(strategy_confusion_csv, strategy_confusion_rows, STRATEGY_CONFUSION_COLUMNS)
    write_csv(tag_recall_csv, tag_recall_rows, TAG_RECALL_COLUMNS)
    write_csv(tag_hits_csv, tag_rows, [
        "created_at", "schema_version", "tagger_validation_status", "trade_id", "decision_key", "strategy_id", "direction",
        "entry_time", "tag_group", "tag_name", "tag_source", "confidence", "reason", "evidence",
    ])

    truth_blocked = [r for r in trade_rows if r["truth_label"] == "actual_blocked"]
    truth_kept = [r for r in trade_rows if r["truth_label"] == "actual_kept"]
    tp = [r for r in trade_rows if r["confusion_class"] == "true_positive_blocked"]
    fn = [r for r in trade_rows if r["confusion_class"] == "false_negative_missed_block"]
    fp = [r for r in trade_rows if r["confusion_class"] == "false_positive_wrong_block"]
    tn = [r for r in trade_rows if r["confusion_class"] == "true_negative_kept"]
    recall_blocked = None if not truth_blocked else len(tp) / len(truth_blocked)
    false_block_rate_kept = None if not truth_kept else len(fp) / len(truth_kept)
    precision_block = None if not (tp or fp) else len(tp) / (len(tp) + len(fp))

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_568_PROXY_RECALL_VALIDATION",
        "tagger_validation_status": TAGGER_VALIDATION_STATUS,
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "dispatch_ready_forced_false": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "inputs": {
            "base_trade_csv": str(resolve(args.base_trade_csv)),
            "kept_ledger_csv": str(resolve(args.kept_ledger_csv)),
            "rule_hits_csv": str(resolve(args.rule_hits_csv)),
            "csv_dir": str(resolve(args.csv_dir)),
            "manifest_json": str(resolve(args.manifest_json)),
            "gate_rules_json": str(resolve(args.gate_rules_json)),
        },
        "outputs": {
            "summary_json": str(summary_json),
            "trade_audit_csv": str(trade_audit_csv),
            "confusion_csv": str(confusion_csv),
            "strategy_confusion_csv": str(strategy_confusion_csv),
            "tag_recall_csv": str(tag_recall_csv),
            "tag_hits_csv": str(tag_hits_csv),
        },
        "counts": {
            "base_trade_rows": int(len(base)),
            "kept_sot_rows": int(len(kept)),
            "actual_blocked_rows": int(len(base) - len(kept)),
            "evaluated_rows": int(len(trade_rows)),
            "strategy_missing_rows": int(strategy_missing),
            "feature_join_ok_rows": int(join_ok),
            "feature_join_missing_rows": int(len(trade_rows) - join_ok),
            "condition_parity_full_match_rows": int(parity_ok),
            "condition_parity_mismatch_rows": int(len(trade_rows) - parity_ok),
            "proxy_tag_hit_rows": int(len(tag_rows)),
            "true_positive_blocked_rows": int(len(tp)),
            "false_negative_missed_block_rows": int(len(fn)),
            "false_positive_wrong_block_rows": int(len(fp)),
            "true_negative_kept_rows": int(len(tn)),
            "dispatch_ready_rows": 0,
        },
        "classification_metrics": {
            "blocked_recall": fm(recall_blocked),
            "block_precision": fm(precision_block),
            "kept_false_block_rate": fm(false_block_rate_kept),
        },
        "baseline_metrics": {
            "base": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in trade_rows]).items()},
            "actual_kept": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in truth_kept]).items()},
            "actual_blocked": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in truth_blocked]).items()},
            "proxy_true_positive_blocked": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in tp]).items()},
            "proxy_false_positive_wrong_block": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in fp]).items()},
            "proxy_false_negative_missed_block": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in fn]).items()},
            "proxy_true_negative_kept": {k: fm(v) for k, v in metrics([float(r["profit_r_num"]) for r in tn]).items()},
        },
        "promotion_rule": "Do not promote unless blocked_recall is high, kept_false_block_rate is low, feature_join_missing_rows is 0, and strategy-level results do not damage kept SOT.",
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate DISC8 pre-send tagger proxy against original 568 universe. Audit-only.")
    p.add_argument("--base-trade-csv", type=Path, default=DEFAULT_BASE_TRADE_CSV)
    p.add_argument("--kept-ledger-csv", type=Path, default=DEFAULT_KEPT_LEDGER_CSV)
    p.add_argument("--rule-hits-csv", type=Path, default=DEFAULT_RULE_HITS_CSV)
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--gate-rules-json", type=Path, default=DEFAULT_GATE_RULES_JSON)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--tail-m15", type=int, default=60000)
    p.add_argument("--tail-h1", type=int, default=30000)
    p.add_argument("--tail-h4", type=int, default=10000)
    p.add_argument("--tail-d1", type=int, default=3000)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
