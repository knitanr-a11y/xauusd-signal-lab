#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate provisional GOLD DISC8 pre-send tagger proxy on historical SOT trades.

Audit-only. No OpenAI, no Discord, no MT5 order_send.

This script reconstructs historical feature rows from OHLC, applies the same
provisional tagger proxy used by apply_gold_disc8_pre_send_tagger_audit_latest.py,
and summarizes whether provisional block/allow groups were historically good/bad.

Important: This is a validation audit, not a live-routing decision. Even if the
proxy looks good, dispatch remains disabled until the user explicitly promotes a
validated gate.
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

DEFAULT_LEDGER_CSV = Path("data/gold_disc8/source_of_truth/group_tag_filtered/group_tag_filtered_source_trade_ledger.csv")
DEFAULT_ALT_LEDGER_CSV = Path("group_tag_filtered_source_trade_ledger.csv")
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_MANIFEST_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.json")
DEFAULT_GATE_RULES_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_pre_send_tagger_proxy_history_validation")
SCHEMA_VERSION = "gold_disc8_pre_send_tagger_proxy_history_validation_v1"

TRADE_AUDIT_COLUMNS = [
    "schema_version", "tagger_validation_status", "trade_id", "strategy_id", "direction", "entry_time",
    "feature_time", "feature_join_status", "condition_parity_full_match", "matched_count", "condition_count",
    "input_outcome", "profit_r_num", "is_win", "is_loss", "provisional_gate_decision", "dispatch_ready",
    "tag_hit_count", "tag_hits", "block_hit_count", "block_hits", "watch_hit_count", "watch_hits",
    "matched_conditions", "failed_conditions", "reason",
]

TAG_IMPACT_COLUMNS = [
    "strategy_id", "tag_group", "tag_name", "configured_action", "hit_count", "win_count", "loss_count",
    "win_rate", "profit_factor", "avg_r", "total_r", "no_hit_count", "no_hit_win_rate", "no_hit_profit_factor",
    "no_hit_avg_r", "no_hit_total_r", "delta_avg_r_hit_minus_no_hit", "verdict",
]

GATE_IMPACT_COLUMNS = [
    "provisional_gate_decision", "trade_count", "win_count", "loss_count", "win_rate", "profit_factor",
    "avg_r", "total_r", "dispatch_ready_count",
]

STRATEGY_GATE_COLUMNS = [
    "strategy_id", "provisional_gate_decision", "trade_count", "win_count", "loss_count", "win_rate",
    "profit_factor", "avg_r", "total_r",
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


def read_ledger(path: Path) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        alt = resolve(DEFAULT_ALT_LEDGER_CSV)
        if alt.exists():
            p = alt
        else:
            raise FileNotFoundError(f"source trade ledger not found: {p}")
    df = pd.read_csv(windows_long_path(p), encoding="utf-8-sig")
    if df.empty:
        raise RuntimeError(f"source trade ledger is empty: {p}")
    return df


def build_feature_frame(csv_dir: Path, args: argparse.Namespace) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=args.tail_m15))
    h1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=args.tail_h1))
    h4 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=args.tail_h4))
    d1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=args.tail_d1))
    return attach_context(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)


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


def trade_r(row: pd.Series) -> float:
    for col in ["profit_r_num", "profit_r"]:
        x = safe_float(row.get(col))
        if x is not None:
            return float(x)
    return 0.0


def metrics(values: list[float]) -> dict[str, Any]:
    n = len(values)
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x < 0]
    pos = sum(wins)
    neg = sum(losses)
    pf: float | str
    if abs(neg) <= 1e-12:
        pf = 999.0 if pos > 0 else 0.0
    else:
        pf = pos / abs(neg)
    return {
        "trade_count": n,
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": None if n == 0 else len(wins) / n,
        "profit_factor": pf,
        "avg_r": None if n == 0 else sum(values) / n,
        "total_r": sum(values),
    }


def format_metric(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, 6)
    return value


def candidate_from_trade(trade: pd.Series, feat_row: pd.Series | None, strategy: dict[str, Any], gate_rules: dict[str, Any]) -> tuple[dict[str, Any], bool, list[str], list[str], str]:
    sid = clean(trade.get("strategy_id"))
    direction = clean(trade.get("direction"))
    entry_time = clean(trade.get("entry_time"))
    entry_price = safe_float(trade.get("entry_price"))
    tp_price = safe_float(trade.get("tp_price"))
    sl_price = safe_float(trade.get("sl_price"))
    if feat_row is None:
        matched, failed = [], []
        parity = False
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
        "decision": "HISTORICAL_VALIDATION_INPUT",
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
        "tagger_status": "HISTORICAL_VALIDATION_PROXY",
        "strict_no_future_ok": clean(trade.get("htf_no_future_ok"), ""),
        "context_h1_close_time": clean(trade.get("h1_source_close_time")),
        "context_h4_close_time": clean(trade.get("h4_source_close_time")),
        "context_d1_close_time": clean(trade.get("d1_source_close_time")),
        "reason": reason,
    })
    return candidate, parity, matched, failed, reason


def feature_lookup_time(trade: pd.Series) -> pd.Timestamp | None:
    # Historical ledger records the M15 bar open. Use it first because live audit evaluates bar rows.
    for col in ["m15_bar_open_time", "entry_time"]:
        ts = pd.to_datetime(trade.get(col), errors="coerce")
        if not pd.isna(ts):
            return pd.Timestamp(ts)
    return None


def build_feature_map(frame: pd.DataFrame) -> dict[pd.Timestamp, pd.Series]:
    out: dict[pd.Timestamp, pd.Series] = {}
    for _, row in frame.iterrows():
        ts = pd.to_datetime(row.get("time"), errors="coerce")
        if not pd.isna(ts):
            out[pd.Timestamp(ts)] = row
    return out


def summarize_gate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    groups = sorted({clean(r.get("provisional_gate_decision")) for r in rows})
    for g in groups:
        vals = [float(r.get("profit_r_num", 0.0)) for r in rows if clean(r.get("provisional_gate_decision")) == g]
        m = metrics(vals)
        out.append({
            "provisional_gate_decision": g,
            "trade_count": m["trade_count"],
            "win_count": m["win_count"],
            "loss_count": m["loss_count"],
            "win_rate": format_metric(m["win_rate"]),
            "profit_factor": format_metric(m["profit_factor"]),
            "avg_r": format_metric(m["avg_r"]),
            "total_r": format_metric(m["total_r"]),
            "dispatch_ready_count": int(sum(1 for r in rows if clean(r.get("provisional_gate_decision")) == g and bool(r.get("dispatch_ready")))),
        })
    return out


def summarize_strategy_gate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    keys = sorted({(clean(r.get("strategy_id")), clean(r.get("provisional_gate_decision"))) for r in rows})
    for sid, g in keys:
        vals = [float(r.get("profit_r_num", 0.0)) for r in rows if clean(r.get("strategy_id")) == sid and clean(r.get("provisional_gate_decision")) == g]
        m = metrics(vals)
        out.append({
            "strategy_id": sid,
            "provisional_gate_decision": g,
            "trade_count": m["trade_count"],
            "win_count": m["win_count"],
            "loss_count": m["loss_count"],
            "win_rate": format_metric(m["win_rate"]),
            "profit_factor": format_metric(m["profit_factor"]),
            "avg_r": format_metric(m["avg_r"]),
            "total_r": format_metric(m["total_r"]),
        })
    return out


def summarize_tags(trade_rows: list[dict[str, Any]], tag_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {clean(r.get("decision_key")): r for r in trade_rows}
    all_values_by_strategy: dict[str, list[float]] = {}
    for r in trade_rows:
        all_values_by_strategy.setdefault(clean(r.get("strategy_id")), []).append(float(r.get("profit_r_num", 0.0)))
    tag_keys = sorted({(clean(t.get("strategy_id")), clean(t.get("tag_group")), clean(t.get("tag_name"))) for t in tag_rows})
    out = []
    for sid, tg, tn in tag_keys:
        hit_decision_keys = {clean(t.get("decision_key")) for t in tag_rows if clean(t.get("strategy_id")) == sid and clean(t.get("tag_group")) == tg and clean(t.get("tag_name")) == tn}
        hit_vals = [float(by_key[k].get("profit_r_num", 0.0)) for k in hit_decision_keys if k in by_key]
        no_vals = [float(r.get("profit_r_num", 0.0)) for r in trade_rows if clean(r.get("strategy_id")) == sid and clean(r.get("decision_key")) not in hit_decision_keys]
        hm = metrics(hit_vals)
        nm = metrics(no_vals)
        hit_avg = hm["avg_r"]
        no_avg = nm["avg_r"]
        delta = None if hit_avg is None or no_avg is None else hit_avg - no_avg
        action = "block" if any(clean(r.get("provisional_gate_decision")) == "BLOCK" and clean(r.get("decision_key")) in hit_decision_keys for r in trade_rows) else "watch_or_info"
        verdict = "INSUFFICIENT_HITS"
        if hm["trade_count"] >= 5:
            if hit_avg is not None and no_avg is not None and hit_avg < no_avg:
                verdict = "PROXY_TAG_BAD_GROUP"
            elif hit_avg is not None and no_avg is not None and hit_avg >= no_avg:
                verdict = "PROXY_TAG_NOT_BAD_GROUP"
        out.append({
            "strategy_id": sid,
            "tag_group": tg,
            "tag_name": tn,
            "configured_action": action,
            "hit_count": hm["trade_count"],
            "win_count": hm["win_count"],
            "loss_count": hm["loss_count"],
            "win_rate": format_metric(hm["win_rate"]),
            "profit_factor": format_metric(hm["profit_factor"]),
            "avg_r": format_metric(hm["avg_r"]),
            "total_r": format_metric(hm["total_r"]),
            "no_hit_count": nm["trade_count"],
            "no_hit_win_rate": format_metric(nm["win_rate"]),
            "no_hit_profit_factor": format_metric(nm["profit_factor"]),
            "no_hit_avg_r": format_metric(nm["avg_r"]),
            "no_hit_total_r": format_metric(nm["total_r"]),
            "delta_avg_r_hit_minus_no_hit": format_metric(delta),
            "verdict": verdict,
        })
    return out


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    mkdirp(out_dir)
    ledger = read_ledger(args.ledger_csv)
    if args.strategy_id:
        wanted = {x.strip() for x in args.strategy_id.split(",") if x.strip()}
        ledger = ledger[ledger["strategy_id"].astype(str).isin(wanted)].copy()
    manifest_obj = read_json(args.manifest_json)
    gate_rules = read_json(args.gate_rules_json)
    manifest = {clean(s.get("strategy_id")): s for s in parse_manifest(manifest_obj)}
    frame = build_feature_frame(resolve(args.csv_dir), args)
    fmap = build_feature_map(frame)

    trade_audit_rows: list[dict[str, Any]] = []
    tag_rows: list[dict[str, Any]] = []
    join_ok = 0
    parity_ok = 0

    for _, trade in ledger.iterrows():
        sid = clean(trade.get("strategy_id"))
        strategy = manifest.get(sid)
        if strategy is None:
            continue
        ftime = feature_lookup_time(trade)
        feat = fmap.get(ftime) if ftime is not None else None
        join_status = "JOIN_OK" if feat is not None else "FEATURE_TIME_NOT_FOUND"
        if feat is not None:
            join_ok += 1
        candidate, parity, matched, failed, reason = candidate_from_trade(trade, feat, strategy, gate_rules)
        if parity:
            parity_ok += 1
        tags = provisional_tags_for_candidate(pd.Series(candidate), gate_rules)
        tag_rows.extend(tags)
        gate = gate_for_candidate(pd.Series(candidate), tags, gate_rules)
        row = {
            "schema_version": SCHEMA_VERSION,
            "tagger_validation_status": TAGGER_VALIDATION_STATUS,
            "trade_id": clean(trade.get("trade_id")) or clean(trade.get("order_key")),
            "strategy_id": sid,
            "direction": clean(trade.get("direction")),
            "entry_time": clean(trade.get("entry_time")),
            "feature_time": "" if ftime is None else str(ftime),
            "feature_join_status": join_status,
            "condition_parity_full_match": bool(parity),
            "matched_count": len(matched),
            "condition_count": len(strategy.get("conditions", [])),
            "input_outcome": clean(trade.get("outcome")),
            "profit_r_num": trade_r(trade),
            "is_win": bool(trade_r(trade) > 0),
            "is_loss": bool(trade_r(trade) < 0),
            "provisional_gate_decision": clean(gate.get("provisional_gate_decision")),
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
            "decision_key": clean(candidate.get("decision_key")),
        }
        trade_audit_rows.append(row)

    gate_rows = summarize_gate(trade_audit_rows)
    strategy_gate_rows = summarize_strategy_gate(trade_audit_rows)
    tag_impact_rows = summarize_tags(trade_audit_rows, tag_rows)

    trade_audit_csv = out_dir / "gold_disc8_pre_send_tagger_proxy_history_trade_audit.csv"
    tag_hits_csv = out_dir / "gold_disc8_pre_send_tagger_proxy_history_tag_hits.csv"
    gate_impact_csv = out_dir / "gold_disc8_pre_send_tagger_proxy_history_gate_impact_summary.csv"
    strategy_gate_csv = out_dir / "gold_disc8_pre_send_tagger_proxy_history_strategy_gate_summary.csv"
    tag_impact_csv = out_dir / "gold_disc8_pre_send_tagger_proxy_history_tag_impact_summary.csv"
    summary_json = out_dir / "gold_disc8_pre_send_tagger_proxy_history_validation_summary.json"

    write_csv(trade_audit_csv, trade_audit_rows, TRADE_AUDIT_COLUMNS + ["decision_key"])
    write_csv(tag_hits_csv, tag_rows, [
        "created_at", "schema_version", "tagger_validation_status", "decision_key", "strategy_id", "direction",
        "entry_time", "tag_group", "tag_name", "tag_source", "confidence", "reason", "evidence",
    ])
    write_csv(gate_impact_csv, gate_rows, GATE_IMPACT_COLUMNS)
    write_csv(strategy_gate_csv, strategy_gate_rows, STRATEGY_GATE_COLUMNS)
    write_csv(tag_impact_csv, tag_impact_rows, TAG_IMPACT_COLUMNS)

    all_values = [float(r.get("profit_r_num", 0.0)) for r in trade_audit_rows]
    all_metrics = metrics(all_values)
    block_values = [float(r.get("profit_r_num", 0.0)) for r in trade_audit_rows if clean(r.get("provisional_gate_decision")) == "BLOCK"]
    allow_values = [float(r.get("profit_r_num", 0.0)) for r in trade_audit_rows if clean(r.get("provisional_gate_decision")) == "ALLOW_PROVISIONAL"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_PROXY_HISTORY_VALIDATION",
        "tagger_validation_status": TAGGER_VALIDATION_STATUS,
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "dispatch_ready_forced_false": True,
        "inputs": {
            "ledger_csv": str(resolve(args.ledger_csv)),
            "csv_dir": str(resolve(args.csv_dir)),
            "manifest_json": str(resolve(args.manifest_json)),
            "gate_rules_json": str(resolve(args.gate_rules_json)),
        },
        "outputs": {
            "trade_audit_csv": str(trade_audit_csv),
            "tag_hits_csv": str(tag_hits_csv),
            "gate_impact_csv": str(gate_impact_csv),
            "strategy_gate_csv": str(strategy_gate_csv),
            "tag_impact_csv": str(tag_impact_csv),
            "summary_json": str(summary_json),
        },
        "counts": {
            "source_trade_rows": int(len(ledger)),
            "evaluated_trade_rows": int(len(trade_audit_rows)),
            "feature_join_ok_rows": int(join_ok),
            "feature_join_missing_rows": int(len(trade_audit_rows) - join_ok),
            "condition_parity_full_match_rows": int(parity_ok),
            "condition_parity_mismatch_rows": int(len(trade_audit_rows) - parity_ok),
            "tag_hit_rows": int(len(tag_rows)),
            "provisional_block_rows": int(len(block_values)),
            "provisional_allow_rows": int(len(allow_values)),
            "dispatch_ready_rows": 0,
        },
        "overall_metrics": {k: format_metric(v) for k, v in all_metrics.items()},
        "provisional_block_metrics": {k: format_metric(v) for k, v in metrics(block_values).items()},
        "provisional_allow_metrics": {k: format_metric(v) for k, v in metrics(allow_values).items()},
        "validation_warning": "Proxy tagger is not promotable if feature_join_missing_rows or condition_parity_mismatch_rows are large, or if blocked group is not materially worse than allowed/no-hit group.",
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate provisional DISC8 pre-send tagger proxy on historical SOT trades. Audit-only.")
    p.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--gate-rules-json", type=Path, default=DEFAULT_GATE_RULES_JSON)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--strategy-id", default="", help="Optional comma-separated strategy_id filter for quick debug.")
    p.add_argument("--tail-m15", type=int, default=60000)
    p.add_argument("--tail-h1", type=int, default=30000)
    p.add_argument("--tail-h4", type=int, default=10000)
    p.add_argument("--tail-d1", type=int, default=3000)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
