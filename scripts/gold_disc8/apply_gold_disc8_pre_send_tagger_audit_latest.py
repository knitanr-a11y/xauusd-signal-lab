#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Apply provisional GOLD DISC8 pre-send tagger to latest decision candidates.

Audit-only by design.
No OpenAI, no Discord, no MT5 order_send, and no mutation of the common decision ledger.

This script reads the latest candidate CSV produced by:
  run_gold_disc8_live_decision_audit_forever_aligned.py

It emits provisional tag hits and gate-audit rows. Even if the gate result is
ALLOW, dispatch_ready remains False because the tagger is not validated yet.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CANDIDATES_CSV = Path("data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_candidates.csv")
DEFAULT_DECISION_SUMMARY_JSON = Path("data/runtime_logs/gold_disc8_live_decision_audit/latest/gold_disc8_live_decision_audit_summary.json")
DEFAULT_GATE_RULES_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_pre_send_tagger_audit/latest")
SCHEMA_VERSION = "gold_disc8_pre_send_tagger_audit_v1_provisional_no_dispatch"
TAGGER_VALIDATION_STATUS = "PROVISIONAL_AUDIT_ONLY"

TAG_HIT_COLUMNS = [
    "created_at", "schema_version", "tagger_validation_status", "decision_key", "strategy_id", "direction",
    "entry_time", "tag_group", "tag_name", "tag_source", "confidence", "reason", "evidence",
]

GATE_AUDIT_COLUMNS = [
    "created_at", "schema_version", "tagger_validation_status", "decision_key", "strategy_id", "direction",
    "entry_time", "input_decision", "tag_hit_count", "tag_hits", "block_hit_count", "block_hits",
    "watch_hit_count", "watch_hits", "provisional_gate_decision", "dispatch_ready", "reason",
]


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def as_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


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


def read_csv(path: Path) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return pd.read_csv(windows_long_path(p), encoding="utf-8-sig")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def actual_value(text: str, feature: str) -> float | None:
    # Extract "feature op threshold actual=value" from matched/failed condition text.
    pat = re.compile(re.escape(feature) + r"\s*(?:<=|>=|<|>)\s*-?\d+(?:\.\d+)?\s+actual=([A-Za-z0-9_+\-.]+)")
    m = pat.search(text)
    if not m:
        return None
    token = m.group(1)
    if token.upper() in {"NA", "NAN", "NONE", ""}:
        return None
    return as_float(token)


def condition_text(row: pd.Series) -> str:
    return clean(row.get("matched_conditions")) + " | " + clean(row.get("failed_conditions"))


def add_tag(rows: list[dict[str, Any]], row: pd.Series, *, tag_group: str, tag_name: str, tag_source: str, confidence: str, reason: str, evidence: str) -> None:
    rows.append({
        "created_at": now_text(),
        "schema_version": SCHEMA_VERSION,
        "tagger_validation_status": TAGGER_VALIDATION_STATUS,
        "decision_key": clean(row.get("decision_key")),
        "strategy_id": clean(row.get("strategy_id")),
        "direction": clean(row.get("direction")),
        "entry_time": clean(row.get("entry_time")),
        "tag_group": tag_group,
        "tag_name": tag_name,
        "tag_source": tag_source,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
    })


def rule_tag_names(gate_rules: dict[str, Any], strategy_id: str, *, action: str = "block") -> set[tuple[str, str]]:
    field = "block_rules" if action == "block" else "watch_only_rules"
    rules = gate_rules.get(field, []) if isinstance(gate_rules.get(field), list) else []
    return {
        (clean(r.get("tag_group")), clean(r.get("tag_name")))
        for r in rules
        if clean(r.get("strategy_id")) == strategy_id
    }


def provisional_tags_for_candidate(row: pd.Series, gate_rules: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    sid = clean(row.get("strategy_id"))
    direction = clean(row.get("direction")).upper()
    text = condition_text(row)
    block_tags = rule_tag_names(gate_rules, sid, action="block")
    watch_tags = rule_tag_names(gate_rules, sid, action="watch")

    macd_hist = actual_value(text, "macd_hist")
    h1_donch_pos_8 = actual_value(text, "h1_donch_pos_8")
    h4_ret_48_atr = actual_value(text, "h4_ret_48_atr")
    h4_dist_ema200_atr = actual_value(text, "h4_dist_ema200_atr")
    h4_donch_pos_32 = actual_value(text, "h4_donch_pos_32")
    h4_ret_8_atr = actual_value(text, "h4_ret_8_atr")
    h4_donch_pos_4 = actual_value(text, "h4_donch_pos_4")
    donch_pos_32 = actual_value(text, "donch_pos_32")
    donch_pos_72 = actual_value(text, "donch_pos_72")
    donch_pos_8 = actual_value(text, "donch_pos_8")
    ret_96_atr = actual_value(text, "ret_96_atr")
    entry_price = as_float(row.get("entry_price"))
    tp_price = as_float(row.get("tp_price"))
    sl_price = as_float(row.get("sl_price"))

    def wants(tag_group: str, tag_name: str) -> bool:
        return (tag_group, tag_name) in block_tags or (tag_group, tag_name) in watch_tags

    # Execution sanity: should almost never hit, but exact and safe.
    if wants("execution", "tp_sl_distance_invalid"):
        invalid = entry_price is None or tp_price is None or sl_price is None or abs(tp_price - entry_price) <= 0 or abs(sl_price - entry_price) <= 0
        if not invalid and direction == "BUY":
            invalid = not (tp_price > entry_price and sl_price < entry_price)
        if not invalid and direction == "SELL":
            invalid = not (tp_price < entry_price and sl_price > entry_price)
        if invalid:
            add_tag(out, row, tag_group="execution", tag_name="tp_sl_distance_invalid", tag_source="deterministic_price_sanity", confidence="HIGH", reason="TP/SL direction or distance invalid", evidence=f"entry={entry_price} tp={tp_price} sl={sl_price} direction={direction}")

    # Late signal: only emit when strategy has macd_late_signal gate and MACD is very extended.
    if wants("risk", "macd_late_signal") and macd_hist is not None:
        if abs(macd_hist) >= 3.026:
            add_tag(out, row, tag_group="risk", tag_name="macd_late_signal", tag_source="provisional_numeric_proxy", confidence="MEDIUM", reason="MACD histogram is extended at signal time", evidence=f"macd_hist={macd_hist}")

    # HTF context conflict: direction vs HTF momentum/location. Conservative proxies.
    if wants("risk", "against_h1_context"):
        conflict = False
        evidence = []
        if direction == "BUY" and h1_donch_pos_8 is not None and h1_donch_pos_8 < 0.409:
            conflict = True; evidence.append(f"h1_donch_pos_8={h1_donch_pos_8}<0.409")
        if direction == "SELL" and h1_donch_pos_8 is not None and h1_donch_pos_8 > 0.75:
            conflict = True; evidence.append(f"h1_donch_pos_8={h1_donch_pos_8}>0.75")
        if conflict:
            add_tag(out, row, tag_group="risk", tag_name="against_h1_context", tag_source="provisional_numeric_proxy", confidence="LOW", reason="H1 context appears opposed to trade direction", evidence="; ".join(evidence))

    if wants("risk", "against_h4_context"):
        conflict = False
        evidence = []
        if direction == "BUY" and h4_ret_48_atr is not None and h4_ret_48_atr < 0:
            conflict = True; evidence.append(f"h4_ret_48_atr={h4_ret_48_atr}<0")
        if direction == "SELL" and h4_ret_48_atr is not None and h4_ret_48_atr > 0.9836:
            conflict = True; evidence.append(f"h4_ret_48_atr={h4_ret_48_atr}>0.9836")
        if direction == "SELL" and h4_dist_ema200_atr is not None and h4_dist_ema200_atr > 0.5223:
            conflict = True; evidence.append(f"h4_dist_ema200_atr={h4_dist_ema200_atr}>0.5223")
        if conflict:
            add_tag(out, row, tag_group="risk", tag_name="against_h4_context", tag_source="provisional_numeric_proxy", confidence="LOW", reason="H4 context appears opposed to trade direction", evidence="; ".join(evidence))

    # Poor pullback: candidate is not sufficiently pulled back or is entering extended position.
    if wants("risk", "poor_pullback_structure"):
        poor = False
        evidence = []
        if direction == "BUY" and donch_pos_32 is not None and donch_pos_32 > 0.80:
            poor = True; evidence.append(f"donch_pos_32={donch_pos_32}>0.80")
        if direction == "BUY" and donch_pos_72 is not None and donch_pos_72 > 0.90:
            poor = True; evidence.append(f"donch_pos_72={donch_pos_72}>0.90")
        if direction == "SELL" and h1_donch_pos_8 is not None and h1_donch_pos_8 < 0.60:
            poor = True; evidence.append(f"h1_donch_pos_8={h1_donch_pos_8}<0.60 for SELL pullback")
        if poor:
            add_tag(out, row, tag_group="risk", tag_name="poor_pullback_structure", tag_source="provisional_numeric_proxy", confidence="LOW", reason="Pullback structure proxy is weak", evidence="; ".join(evidence))

    # High volatility chase: extended move / breakout chase proxy.
    if wants("risk", "high_volatility_chase"):
        chase = False
        evidence = []
        for name, value, thr in [
            ("macd_hist", macd_hist, 3.026),
            ("ret_96_atr", ret_96_atr, 12.0),
            ("h4_ret_8_atr", h4_ret_8_atr, 2.196),
        ]:
            if value is not None and abs(value) >= thr:
                chase = True; evidence.append(f"{name}={value} abs>={thr}")
        if h4_donch_pos_32 is not None and h4_donch_pos_32 > 0.9956:
            chase = True; evidence.append(f"h4_donch_pos_32={h4_donch_pos_32}>0.9956")
        if h4_donch_pos_4 is not None and h4_donch_pos_4 > 1.906:
            chase = True; evidence.append(f"h4_donch_pos_4={h4_donch_pos_4}>1.906")
        if chase:
            add_tag(out, row, tag_group="risk", tag_name="high_volatility_chase", tag_source="provisional_numeric_proxy", confidence="LOW", reason="Volatility/chase proxy is active", evidence="; ".join(evidence))

    # Positive watch-only tags are deliberately conservative and never dispatch-ready.
    if wants("positive", "m15_trend_20_direction_up") and direction == "BUY" and donch_pos_8 is not None and donch_pos_8 > 0.5705:
        add_tag(out, row, tag_group="positive", tag_name="m15_trend_20_direction_up", tag_source="provisional_numeric_proxy", confidence="LOW", reason="M15 short-term range position supports upward context", evidence=f"donch_pos_8={donch_pos_8}")
    if wants("positive", "h1_trend_20_direction_up") and direction == "BUY" and h1_donch_pos_8 is not None and h1_donch_pos_8 > 0.409:
        add_tag(out, row, tag_group="positive", tag_name="h1_trend_20_direction_up", tag_source="provisional_numeric_proxy", confidence="LOW", reason="H1 short-term range position supports upward context", evidence=f"h1_donch_pos_8={h1_donch_pos_8}")
    if wants("positive", "h4_trend_up") and direction == "BUY" and h4_ret_8_atr is not None and h4_ret_8_atr > 2.196:
        add_tag(out, row, tag_group="positive", tag_name="h4_trend_up", tag_source="provisional_numeric_proxy", confidence="LOW", reason="H4 short-term momentum supports upward context", evidence=f"h4_ret_8_atr={h4_ret_8_atr}")

    # Remove duplicates while preserving deterministic order.
    seen = set()
    uniq = []
    for r in out:
        key = (r["decision_key"], r["strategy_id"], r["tag_group"], r["tag_name"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def gate_for_candidate(row: pd.Series, tag_hits: list[dict[str, Any]], gate_rules: dict[str, Any]) -> dict[str, Any]:
    sid = clean(row.get("strategy_id"))
    decision_key = clean(row.get("decision_key"))
    block_rules = gate_rules.get("block_rules", []) if isinstance(gate_rules.get("block_rules"), list) else []
    watch_rules = gate_rules.get("watch_only_rules", []) if isinstance(gate_rules.get("watch_only_rules"), list) else []
    block_hits = []
    watch_hits = []
    for tag in tag_hits:
        if clean(tag.get("decision_key")) != decision_key:
            continue
        tg = clean(tag.get("tag_group"))
        tn = clean(tag.get("tag_name"))
        for rule in block_rules:
            if clean(rule.get("strategy_id")) == sid and clean(rule.get("tag_group")) == tg and clean(rule.get("tag_name")) == tn:
                block_hits.append(clean(rule.get("rule_id")) or f"{sid}:{tg}:{tn}")
        for rule in watch_rules:
            if clean(rule.get("strategy_id")) == sid and clean(rule.get("tag_group")) == tg and clean(rule.get("tag_name")) == tn:
                watch_hits.append(clean(rule.get("rule_id")) or f"{sid}:{tg}:{tn}")
    if block_hits:
        provisional = "BLOCK"
        reason = "PROVISIONAL_BLOCK_RULE_MATCH_AUDIT_ONLY"
    elif watch_hits:
        provisional = "WATCH_ONLY"
        reason = "PROVISIONAL_WATCH_RULE_MATCH_AUDIT_ONLY"
    else:
        provisional = "ALLOW_PROVISIONAL"
        reason = "NO_PROVISIONAL_BLOCK_OR_WATCH_MATCH_AUDIT_ONLY"
    return {
        "created_at": now_text(),
        "schema_version": SCHEMA_VERSION,
        "tagger_validation_status": TAGGER_VALIDATION_STATUS,
        "decision_key": decision_key,
        "strategy_id": sid,
        "direction": clean(row.get("direction")),
        "entry_time": clean(row.get("entry_time")),
        "input_decision": clean(row.get("decision")),
        "tag_hit_count": len([t for t in tag_hits if clean(t.get("decision_key")) == decision_key]),
        "tag_hits": " | ".join(f"{clean(t.get('tag_group'))}:{clean(t.get('tag_name'))}" for t in tag_hits if clean(t.get("decision_key")) == decision_key),
        "block_hit_count": len(set(block_hits)),
        "block_hits": " | ".join(sorted(set(block_hits))),
        "watch_hit_count": len(set(watch_hits)),
        "watch_hits": " | ".join(sorted(set(watch_hits))),
        "provisional_gate_decision": provisional,
        "dispatch_ready": False,
        "reason": reason + "; dispatch_ready forced false until historical/live validation passes",
    }


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = read_csv(args.candidates_csv)
    decision_summary = read_json(args.decision_summary_json)
    gate_rules = read_json(args.gate_rules_json)

    tag_hits: list[dict[str, Any]] = []
    for _, row in candidates.iterrows():
        tag_hits.extend(provisional_tags_for_candidate(row, gate_rules))
    gate_rows = [gate_for_candidate(row, tag_hits, gate_rules) for _, row in candidates.iterrows()]

    tag_hits_csv = out_dir / "gold_disc8_pre_send_tag_hits.csv"
    gate_audit_csv = out_dir / "gold_disc8_pre_send_gate_audit.csv"
    summary_json = out_dir / "gold_disc8_pre_send_tagger_audit_summary.json"
    write_csv(tag_hits_csv, tag_hits, TAG_HIT_COLUMNS)
    write_csv(gate_audit_csv, gate_rows, GATE_AUDIT_COLUMNS)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_PROVISIONAL_TAGGER_NO_DISPATCH",
        "tagger_validation_status": TAGGER_VALIDATION_STATUS,
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "decision_ledger_mutated": False,
        "dispatch_ready_forced_false": True,
        "inputs": {
            "candidates_csv": str(resolve(args.candidates_csv)),
            "decision_summary_json": str(resolve(args.decision_summary_json)),
            "gate_rules_json": str(resolve(args.gate_rules_json)),
            "decision_summary_candidates_detected": decision_summary.get("candidates_detected"),
            "decision_summary_pending_tagger_count": decision_summary.get("pending_tagger_count"),
        },
        "outputs": {
            "tag_hits_csv": str(tag_hits_csv),
            "gate_audit_csv": str(gate_audit_csv),
            "summary_json": str(summary_json),
        },
        "counts": {
            "candidate_rows": int(len(candidates)),
            "tag_hit_rows": int(len(tag_hits)),
            "gate_audit_rows": int(len(gate_rows)),
            "provisional_block_rows": int(sum(1 for r in gate_rows if r.get("provisional_gate_decision") == "BLOCK")),
            "provisional_watch_rows": int(sum(1 for r in gate_rows if r.get("provisional_gate_decision") == "WATCH_ONLY")),
            "provisional_allow_rows": int(sum(1 for r in gate_rows if r.get("provisional_gate_decision") == "ALLOW_PROVISIONAL")),
            "dispatch_ready_rows": int(sum(1 for r in gate_rows if bool(r.get("dispatch_ready")))),
        },
        "safety_note": "These tags are provisional numeric proxies and must not be used for live notification/order routing until validated against source trade ledger and AI review ledger.",
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply provisional DISC8 pre-send tagger to latest candidates. Audit-only.")
    p.add_argument("--candidates-csv", type=Path, default=DEFAULT_CANDIDATES_CSV)
    p.add_argument("--decision-summary-json", type=Path, default=DEFAULT_DECISION_SUMMARY_JSON)
    p.add_argument("--gate-rules-json", type=Path, default=DEFAULT_GATE_RULES_JSON)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
