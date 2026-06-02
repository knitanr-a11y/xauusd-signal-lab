#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Backtest GOLD DISC8 live-decision scanner with AI-review numeric tagger audit.

This script is audit-only and deliberately separated from live operational ledgers.

Hard safety guarantees:
- No OpenAI API calls.
- No Discord sends.
- No MT5 order_send.
- No SOT mutation.
- No runtime gate rules mutation.
- No live decision ledger mutation.
- No dispatch_ready=True.
- Writes only to the requested backtest output directory.

Purpose:
- Avoid wasting time waiting for live candidates.
- Replay the same DISC8 live decision conditions over historical OHLC.
- Apply numeric tagger rules built from actual AI-review tags.
- Produce candidate/gate/monthly/strategy/tag summaries.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import sys
from collections import defaultdict
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
    evaluate_strategy,
    make_decision_key,
    parse_manifest,
    pips_to_price,
    read_json,
    read_ohlc_csv,
    windows_long_path,
)

DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_MANIFEST_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.json")
DEFAULT_NUMERIC_RULES_JSON = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_rules.json")
DEFAULT_TAG_RECALL_CSV = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv")
DEFAULT_OUT_ROOT = Path("data/runtime_logs/gold_disc8_backtest_live_decision_numeric_tagger_audit")
SCHEMA_VERSION = "gold_disc8_backtest_live_decision_numeric_tagger_audit_v1"
TAGGER_VALIDATION_STATUS = "AI_REVIEW_NUMERIC_TAGGER_BACKTEST_AUDIT_ONLY_UNPROMOTED"
PROMOTABLE_VERDICT = "POTENTIALLY_PROMOTABLE_AFTER_MANUAL_REVIEW"

CANDIDATE_COLUMNS = [
    "schema_version", "run_id", "decision_key", "strategy_id", "direction", "entry_time", "entry_price",
    "tp_price", "sl_price", "tp_pips", "sl_pips", "rr", "condition_count", "matched_conditions",
    "context_h1_close_time", "context_h4_close_time", "context_d1_close_time", "source_row_index",
]
GATE_COLUMNS = [
    "schema_version", "run_id", "decision_key", "strategy_id", "direction", "entry_time", "entry_month",
    "entry_price", "tp_price", "sl_price", "tp_pips", "sl_pips", "numeric_rule_hits", "block_hit_count",
    "block_hits", "watch_hit_count", "watch_hits", "numeric_gate_decision", "dispatch_ready", "outcome",
    "exit_time", "exit_price", "profit_r", "result_source", "reason",
]
TAG_COLUMNS = [
    "schema_version", "run_id", "decision_key", "strategy_id", "direction", "entry_time", "tag_group",
    "tag_name", "configured_action", "rule_id", "feature", "op", "threshold", "value", "tag_precision",
    "tag_recall", "tag_f1", "kept_false_hit_rate", "source_rule_verdict",
]
SUMMARY_COLUMNS = [
    "group", "key", "numeric_gate_decision", "trade_count", "win_count", "loss_count", "unresolved_count",
    "win_rate", "profit_factor", "avg_r", "total_r", "block_count", "watch_count", "allow_count",
]
RULE_EVAL_COLUMNS = [
    "decision_key", "strategy_id", "entry_time", "rule_id", "tag_group", "tag_name", "configured_action",
    "feature", "op", "threshold", "value", "matched", "reason",
]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_id_text() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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


def round6(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    return value


def load_numeric_rules(path: Path) -> list[dict[str, Any]]:
    obj = read_json(path)
    rules = obj.get("rules", [])
    if not isinstance(rules, list):
        raise RuntimeError(f"numeric rules JSON missing list field 'rules': {resolve(path)}")
    return [r for r in rules if isinstance(r, dict)]


def load_promotable_tags(path: Path, *, promotable_only: bool) -> set[tuple[str, str, str]] | None:
    if not promotable_only:
        return None
    df = read_csv_optional(path)
    if df.empty:
        return None
    required = {"strategy_id", "tag_group", "tag_name", "verdict"}
    if not required.issubset(set(df.columns)):
        return None
    hit = df[df["verdict"].astype(str).eq(PROMOTABLE_VERDICT)].copy()
    return {(clean(r.strategy_id), clean(r.tag_group), clean(r.tag_name)) for r in hit.itertuples(index=False)}


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


def evaluate_numeric_rule(row: pd.Series, rule: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    feature = clean(rule.get("feature"))
    op = clean(rule.get("op"))
    threshold = safe_float(rule.get("threshold"))
    rule_id = clean(rule.get("rule_id"))
    if not feature or not op or threshold is None:
        return False, {"rule_id": rule_id, "feature": feature, "op": op, "threshold": threshold, "value": "", "matched": False, "reason": "INVALID_RULE"}
    value = safe_float(row.get(feature))
    if value is None:
        return False, {"rule_id": rule_id, "feature": feature, "op": op, "threshold": threshold, "value": "", "matched": False, "reason": "MISSING_FEATURE_VALUE"}
    matched = op_match(value, op, threshold)
    return matched, {"rule_id": rule_id, "feature": feature, "op": op, "threshold": threshold, "value": value, "matched": matched, "reason": "OK" if matched else "NO_MATCH"}


def extract_trade_params(strategy: dict[str, Any], strategy_id: str, row: pd.Series) -> dict[str, Any]:
    direction = clean(strategy.get("direction")) or ("BUY" if "BUY" in strategy_id.upper() else "SELL")
    tp_pips = safe_float(strategy.get("tp_pips"))
    sl_pips = safe_float(strategy.get("sl_pips"))
    rr = safe_float(strategy.get("rr"))
    if tp_pips is None or sl_pips is None:
        # Fallback from strategy_id such as TP80_SL50_RR1p6.
        import re
        m = re.search(r"TP(\d+)_SL(\d+)", strategy_id.upper())
        if m:
            tp_pips = float(m.group(1))
            sl_pips = float(m.group(2))
    if rr is None and tp_pips is not None and sl_pips not in (None, 0):
        rr = tp_pips / sl_pips
    entry_price = safe_float(row.get("close"))
    tp_price = None
    sl_price = None
    if entry_price is not None and tp_pips is not None and sl_pips is not None:
        tp_step = pips_to_price(tp_pips)
        sl_step = pips_to_price(sl_pips)
        if direction.upper() == "BUY":
            tp_price = entry_price + tp_step
            sl_price = entry_price - sl_step
        else:
            tp_price = entry_price - tp_step
            sl_price = entry_price + sl_step
    return {
        "direction": direction.upper(),
        "tp_pips": tp_pips,
        "sl_pips": sl_pips,
        "rr": rr,
        "entry_price": entry_price,
        "tp_price": tp_price,
        "sl_price": sl_price,
    }


def build_feature_frame(csv_dir: Path, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    m15 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=args.tail_m15))
    h1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=args.tail_h1))
    h4 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=args.tail_h4))
    d1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=args.tail_d1))
    frame = attach_context(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)
    lower = None
    lower_path = csv_dir / args.outcome_lower_tf_file
    if lower_path.exists():
        lower = read_ohlc_csv(lower_path, tail=args.tail_lower_tf).sort_values("time").reset_index(drop=True)
    return frame, lower


def first_touch_outcome(lower: pd.DataFrame | None, candidate: dict[str, Any], horizon_minutes: int) -> dict[str, Any]:
    if lower is None or lower.empty:
        return {"outcome": "NOT_EVALUATED_NO_LOWER_TF", "exit_time": "", "exit_price": "", "profit_r": "", "result_source": "NO_LOWER_TF"}
    entry_time = pd.to_datetime(candidate.get("entry_time"), errors="coerce")
    if pd.isna(entry_time):
        return {"outcome": "NOT_EVALUATED_BAD_ENTRY_TIME", "exit_time": "", "exit_price": "", "profit_r": "", "result_source": "BAD_ENTRY_TIME"}
    tp = safe_float(candidate.get("tp_price"))
    sl = safe_float(candidate.get("sl_price"))
    entry = safe_float(candidate.get("entry_price"))
    direction = clean(candidate.get("direction"))
    rr = safe_float(candidate.get("rr"))
    if tp is None or sl is None or entry is None or not direction:
        return {"outcome": "NOT_EVALUATED_BAD_PRICES", "exit_time": "", "exit_price": "", "profit_r": "", "result_source": "BAD_PRICES"}
    end_time = pd.Timestamp(entry_time) + pd.Timedelta(minutes=horizon_minutes)
    w = lower[(lower["time"] > pd.Timestamp(entry_time)) & (lower["time"] <= end_time)].copy()
    if w.empty:
        return {"outcome": "UNRESOLVED_NO_LOWER_TF_WINDOW", "exit_time": "", "exit_price": "", "profit_r": 0.0, "result_source": "LOWER_TF_WINDOW_EMPTY"}
    for _, bar in w.iterrows():
        high = safe_float(bar.get("high"))
        low = safe_float(bar.get("low"))
        if high is None or low is None:
            continue
        # Same-bar conflict uses SL priority, matching the conservative project convention.
        if direction.upper() == "BUY":
            sl_hit = low <= sl
            tp_hit = high >= tp
            if sl_hit:
                return {"outcome": "LOSS", "exit_time": str(bar.get("time")), "exit_price": sl, "profit_r": -1.0, "result_source": "LOWER_TF_FIRST_TOUCH_SL_PRIORITY"}
            if tp_hit:
                return {"outcome": "WIN", "exit_time": str(bar.get("time")), "exit_price": tp, "profit_r": rr if rr is not None else 1.0, "result_source": "LOWER_TF_FIRST_TOUCH"}
        else:
            sl_hit = high >= sl
            tp_hit = low <= tp
            if sl_hit:
                return {"outcome": "LOSS", "exit_time": str(bar.get("time")), "exit_price": sl, "profit_r": -1.0, "result_source": "LOWER_TF_FIRST_TOUCH_SL_PRIORITY"}
            if tp_hit:
                return {"outcome": "WIN", "exit_time": str(bar.get("time")), "exit_price": tp, "profit_r": rr if rr is not None else 1.0, "result_source": "LOWER_TF_FIRST_TOUCH"}
    last_close = safe_float(w.iloc[-1].get("close"))
    if last_close is None:
        return {"outcome": "UNRESOLVED", "exit_time": str(w.iloc[-1].get("time")), "exit_price": "", "profit_r": 0.0, "result_source": "LOWER_TF_HORIZON_NO_TOUCH"}
    if direction.upper() == "BUY":
        denom = abs(entry - sl) if abs(entry - sl) > 1e-12 else 1.0
        r = (last_close - entry) / denom
    else:
        denom = abs(sl - entry) if abs(sl - entry) > 1e-12 else 1.0
        r = (entry - last_close) / denom
    return {"outcome": "UNRESOLVED", "exit_time": str(w.iloc[-1].get("time")), "exit_price": last_close, "profit_r": r, "result_source": "LOWER_TF_HORIZON_NO_TOUCH_MARK_TO_LAST"}


def gate_numeric(row: pd.Series, rules: list[dict[str, Any]], allowed_tags: set[tuple[str, str, str]] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sid = clean(row.get("strategy_id"))
    hits = []
    evals = []
    for rule in rules_for_strategy(rules, sid, allowed_tags):
        matched, detail = evaluate_numeric_rule(row, rule)
        ev = {
            "decision_key": clean(row.get("decision_key")),
            "strategy_id": sid,
            "entry_time": clean(row.get("entry_time")),
            "rule_id": clean(rule.get("rule_id")),
            "tag_group": clean(rule.get("tag_group")),
            "tag_name": clean(rule.get("tag_name")),
            "configured_action": clean(rule.get("configured_action")),
            "feature": detail.get("feature", ""),
            "op": detail.get("op", ""),
            "threshold": detail.get("threshold", ""),
            "value": detail.get("value", ""),
            "matched": bool(matched),
            "reason": detail.get("reason", ""),
        }
        evals.append(ev)
        if matched:
            hits.append(rule | {"_matched_value": detail.get("value", "")})
    blocks = [h for h in hits if clean(h.get("configured_action")) == "block"]
    watches = [h for h in hits if clean(h.get("configured_action")) == "watch_only"]
    return hits, blocks, watches, evals


def metric_rows(rows: list[dict[str, Any]], group: str, key: str) -> list[dict[str, Any]]:
    out = []
    for gate in sorted({clean(r.get("numeric_gate_decision")) for r in rows} | {"ALL"}):
        sub = rows if gate == "ALL" else [r for r in rows if clean(r.get("numeric_gate_decision")) == gate]
        n = len(sub)
        wins = [r for r in sub if clean(r.get("outcome")) == "WIN"]
        losses = [r for r in sub if clean(r.get("outcome")) == "LOSS"]
        unresolved = [r for r in sub if clean(r.get("outcome")) not in {"WIN", "LOSS"}]
        r_vals = [safe_float(r.get("profit_r")) or 0.0 for r in sub]
        pos = sum(x for x in r_vals if x > 0)
        neg = sum(x for x in r_vals if x < 0)
        pf = 999.0 if abs(neg) <= 1e-12 and pos > 0 else (0.0 if abs(neg) <= 1e-12 else pos / abs(neg))
        out.append({
            "group": group,
            "key": key,
            "numeric_gate_decision": gate,
            "trade_count": n,
            "win_count": len(wins),
            "loss_count": len(losses),
            "unresolved_count": len(unresolved),
            "win_rate": "" if n == 0 else round(len(wins) / n, 6),
            "profit_factor": round(pf, 6),
            "avg_r": "" if n == 0 else round(sum(r_vals) / n, 6),
            "total_r": round(sum(r_vals), 6),
            "block_count": sum(1 for r in sub if clean(r.get("numeric_gate_decision")) == "BLOCK"),
            "watch_count": sum(1 for r in sub if clean(r.get("numeric_gate_decision")) == "WATCH_ONLY"),
            "allow_count": sum(1 for r in sub if clean(r.get("numeric_gate_decision")) == "ALLOW_NUMERIC_AUDIT_ONLY"),
        })
    return out


def build_summaries(gate_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    monthly = []
    for month in sorted({clean(r.get("entry_month")) for r in gate_rows}):
        monthly.extend(metric_rows([r for r in gate_rows if clean(r.get("entry_month")) == month], "month", month))
    strategy = []
    for sid in sorted({clean(r.get("strategy_id")) for r in gate_rows}):
        strategy.extend(metric_rows([r for r in gate_rows if clean(r.get("strategy_id")) == sid], "strategy", sid))
    overall = metric_rows(gate_rows, "overall", "ALL")
    return monthly, strategy, overall


def main() -> int:
    args = parse_args()
    run_id = args.run_id or run_id_text()
    out_root = resolve(args.out_root)
    run_dir = out_root / "runs" / run_id
    latest_dir = out_root / "latest"
    mkdirp(run_dir)

    csv_dir = resolve(args.csv_dir)
    manifest = parse_manifest(read_json(args.manifest_json))
    rules = load_numeric_rules(args.numeric_rules_json)
    allowed_tags = load_promotable_tags(args.tag_recall_csv, promotable_only=args.promotable_only)
    frame, lower = build_feature_frame(csv_dir, args)

    if args.start_time:
        start_ts = pd.to_datetime(args.start_time)
        frame = frame[frame["time"] >= start_ts].copy()
    if args.end_time:
        end_ts = pd.to_datetime(args.end_time)
        frame = frame[frame["time"] <= end_ts].copy()
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
        ts = row.get("time")
        entry_time = str(ts)
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
                reason = "AI_REVIEW_NUMERIC_RULE_BLOCK_MATCH_BACKTEST_AUDIT_ONLY"
            elif watches:
                gate_decision = "WATCH_ONLY"
                reason = "AI_REVIEW_NUMERIC_RULE_WATCH_MATCH_BACKTEST_AUDIT_ONLY"
            else:
                gate_decision = "ALLOW_NUMERIC_AUDIT_ONLY"
                reason = "NO_AI_REVIEW_NUMERIC_RULE_MATCH_BACKTEST_AUDIT_ONLY"
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
                "reason": reason + "; dispatch_ready forced false; no live ledger mutation",
            })

    monthly_rows, strategy_rows, overall_rows = build_summaries(gate_rows)
    candidates_csv = run_dir / "gold_disc8_backtest_live_candidates.csv"
    gate_csv = run_dir / "gold_disc8_backtest_numeric_gate_audit.csv"
    tag_csv = run_dir / "gold_disc8_backtest_numeric_tag_hits.csv"
    rule_eval_csv = run_dir / "gold_disc8_backtest_numeric_rule_eval_audit.csv"
    monthly_csv = run_dir / "gold_disc8_backtest_monthly_summary.csv"
    strategy_csv = run_dir / "gold_disc8_backtest_strategy_summary.csv"
    overall_csv = run_dir / "gold_disc8_backtest_overall_summary.csv"
    summary_json = run_dir / "gold_disc8_backtest_audit_summary.json"

    write_csv(candidates_csv, candidates, CANDIDATE_COLUMNS)
    write_csv(gate_csv, gate_rows, GATE_COLUMNS)
    write_csv(tag_csv, tag_rows, TAG_COLUMNS)
    write_csv(rule_eval_csv, rule_eval_rows, RULE_EVAL_COLUMNS)
    write_csv(monthly_csv, monthly_rows, SUMMARY_COLUMNS)
    write_csv(strategy_csv, strategy_rows, SUMMARY_COLUMNS)
    write_csv(overall_csv, overall_rows, SUMMARY_COLUMNS)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_BACKTEST_AUDIT_ONLY_NO_LIVE_LEDGER_MUTATION",
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
        "allowed_promotable_tags_count": None if allowed_tags is None else len(allowed_tags),
        "inputs": {
            "csv_dir": str(csv_dir),
            "manifest_json": str(resolve(args.manifest_json)),
            "numeric_rules_json": str(resolve(args.numeric_rules_json)),
            "tag_recall_csv": str(resolve(args.tag_recall_csv)),
            "outcome_lower_tf_file": args.outcome_lower_tf_file,
            "start_time": args.start_time,
            "end_time": args.end_time,
            "max_bars": args.max_bars,
            "outcome_horizon_minutes": args.outcome_horizon_minutes,
        },
        "outputs": {
            "run_dir": str(run_dir),
            "latest_dir": str(latest_dir),
            "candidates_csv": str(candidates_csv),
            "gate_csv": str(gate_csv),
            "tag_csv": str(tag_csv),
            "rule_eval_csv": str(rule_eval_csv),
            "monthly_csv": str(monthly_csv),
            "strategy_csv": str(strategy_csv),
            "overall_csv": str(overall_csv),
            "summary_json": str(summary_json),
        },
        "counts": {
            "scanned_m15_rows": int(len(frame)),
            "strategies": int(len(manifest)),
            "condition_attempts": int(condition_attempts),
            "candidate_rows": int(len(candidates)),
            "missing_trade_param_rows": int(missing_trade_param_rows),
            "numeric_rules_loaded": int(len(rules)),
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
        "safety_note": "This backtest uses isolated run_id output directories. It never appends to or overwrites live operational ledgers.",
    }
    write_json(summary_json, summary)

    # latest is an analysis convenience copy only. It is not an operational ledger.
    if args.write_latest_copy:
        if latest_dir.exists():
            shutil.rmtree(windows_long_path(latest_dir))
        mkdirp(latest_dir)
        for src in [candidates_csv, gate_csv, tag_csv, rule_eval_csv, monthly_csv, strategy_csv, overall_csv, summary_json]:
            shutil.copy2(windows_long_path(src), windows_long_path(latest_dir / src.name))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest DISC8 live decision scanner + AI numeric tagger. Audit-only.")
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


if __name__ == "__main__":
    raise SystemExit(main())
