#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Audit DISC8 numeric rule feature contract.

Why this exists:
- The 568 AI-review source validation showed useful numeric tagger quality.
- The live-decision backtest produced many candidates but zero numeric tag hits.
- That means the numeric rule feature contract may not match the live/backtest
  feature frame, or thresholds may be outside the live candidate distribution.

Audit-only hard guarantees:
- No OpenAI API call.
- No Discord send.
- No MT5 order_send.
- No SOT mutation.
- No runtime gate rule mutation.
- No live decision ledger mutation.
- No dispatch_ready=True.

Outputs are written only under data/runtime_logs/gold_disc8_numeric_rule_feature_contract_audit/.
"""
from __future__ import annotations

import argparse
import csv
import difflib
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
    evaluate_strategy,
    parse_manifest,
    read_json,
    read_ohlc_csv,
    windows_long_path,
)

DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_MANIFEST_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.json")
DEFAULT_RULES_JSON = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_rules.json")
DEFAULT_TAG_RECALL_CSV = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review/gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv")
DEFAULT_SOURCE_FEATURE_SNAPSHOT_CSV = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_feature_snapshot.csv")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_numeric_rule_feature_contract_audit")
SCHEMA_VERSION = "gold_disc8_numeric_rule_feature_contract_audit_v1"
PROMOTABLE_VERDICT = "POTENTIALLY_PROMOTABLE_AFTER_MANUAL_REVIEW"

RULE_AUDIT_COLUMNS = [
    "rule_id", "strategy_id", "tag_group", "tag_name", "configured_action", "is_promotable",
    "feature", "op", "threshold", "source_feature_exact_exists", "live_feature_exact_exists",
    "candidate_feature_exact_exists", "resolved_source_feature", "resolved_live_feature", "resolved_candidate_feature",
    "resolution_status", "source_non_null", "source_min", "source_p05", "source_p50", "source_p95", "source_max",
    "candidate_rows_for_strategy", "candidate_non_null", "candidate_min", "candidate_p05", "candidate_p50",
    "candidate_p95", "candidate_max", "threshold_in_candidate_range", "candidate_hit_count", "candidate_hit_rate",
    "live_rows", "live_non_null", "live_min", "live_p05", "live_p50", "live_p95", "live_max",
    "threshold_in_live_range", "live_hit_count", "live_hit_rate", "diagnosis", "close_feature_suggestions",
]
CANDIDATE_AUDIT_COLUMNS = [
    "strategy_id", "candidate_rows", "rule_count", "promotable_rule_count", "rules_with_exact_feature",
    "rules_with_resolved_feature", "rules_missing_feature", "total_rule_evaluations", "total_hit_count",
    "hit_rate", "missing_feature_names",
]
SUMMARY_COLUMNS = ["metric", "value"]


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


def read_csv_optional(path: Path) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(windows_long_path(p), encoding="utf-8-sig", sep=None, engine="python")


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


def fm(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float):
        return round(value, 8)
    return value


def stats(series: pd.Series | None) -> dict[str, Any]:
    if series is None:
        return {"non_null": 0, "min": "", "p05": "", "p50": "", "p95": "", "max": ""}
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"non_null": 0, "min": "", "p05": "", "p50": "", "p95": "", "max": ""}
    return {
        "non_null": int(len(s)),
        "min": fm(float(s.min())),
        "p05": fm(float(s.quantile(0.05))),
        "p50": fm(float(s.quantile(0.50))),
        "p95": fm(float(s.quantile(0.95))),
        "max": fm(float(s.max())),
    }


def threshold_in_range(threshold: float | None, st: dict[str, Any]) -> str:
    if threshold is None or st.get("non_null", 0) == 0:
        return "UNKNOWN"
    lo = safe_float(st.get("min"))
    hi = safe_float(st.get("max"))
    if lo is None or hi is None:
        return "UNKNOWN"
    return "YES" if lo <= threshold <= hi else "NO"


def op_hit(series: pd.Series | None, op: str, threshold: float | None) -> tuple[int, float]:
    if series is None or threshold is None:
        return 0, 0.0
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return 0, 0.0
    if op == "<=":
        hit = s <= threshold
    elif op == ">=":
        hit = s >= threshold
    elif op == "<":
        hit = s < threshold
    elif op == ">":
        hit = s > threshold
    else:
        return 0, 0.0
    n = int(hit.sum())
    return n, float(n / len(s))


def load_rules(path: Path) -> list[dict[str, Any]]:
    obj = read_json(path)
    rules = obj.get("rules", [])
    if not isinstance(rules, list):
        raise RuntimeError(f"rules JSON missing list field 'rules': {resolve(path)}")
    return [r for r in rules if isinstance(r, dict)]


def promotable_tags(path: Path) -> set[tuple[str, str, str]]:
    df = read_csv_optional(path)
    if df.empty:
        return set()
    required = {"strategy_id", "tag_group", "tag_name", "verdict"}
    if not required.issubset(set(df.columns)):
        return set()
    p = df[df["verdict"].astype(str).eq(PROMOTABLE_VERDICT)]
    return {(clean(r.strategy_id), clean(r.tag_group), clean(r.tag_name)) for r in p.itertuples(index=False)}


def build_feature_frame(csv_dir: Path, args: argparse.Namespace) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_m15.csv", tail=args.tail_m15))
    h1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h1.csv", tail=args.tail_h1))
    h4 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_h4.csv", tail=args.tail_h4))
    d1 = add_indicators(read_ohlc_csv(csv_dir / "goldsharp_d1.csv", tail=args.tail_d1))
    frame = attach_context(m15, h1, h4, d1).sort_values("time").reset_index(drop=True)
    if args.start_time:
        frame = frame[frame["time"] >= pd.to_datetime(args.start_time)].copy()
    if args.end_time:
        frame = frame[frame["time"] <= pd.to_datetime(args.end_time)].copy()
    if args.max_bars and args.max_bars > 0:
        frame = frame.tail(args.max_bars).copy()
    return frame.reset_index(drop=True)


def build_candidate_feature_frame(frame: pd.DataFrame, manifest: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for i, row in frame.iterrows():
        for strategy in manifest:
            ok, matched, failed, missing = evaluate_strategy(row, strategy)
            if not ok:
                continue
            r = row.to_dict()
            r["source_row_index"] = i
            r["strategy_id"] = clean(strategy.get("strategy_id"))
            r["direction"] = clean(strategy.get("direction"))
            r["entry_time"] = str(row.get("time"))
            r["condition_count"] = len(strategy.get("conditions", []))
            r["matched_conditions"] = " | ".join(matched)
            rows.append(r)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def feature_aliases(feature: str) -> list[str]:
    f = clean(feature)
    aliases = [f]
    if f.startswith("m15_"):
        aliases.append(f[4:])
    else:
        aliases.append("m15_" + f)
    if f.endswith("_feat"):
        aliases.append(f[:-5])
    if f.startswith("feature_"):
        aliases.append(f[8:])
    if f.startswith("h1_"):
        aliases.append("h1_" + f[3:])
    if f.startswith("h4_"):
        aliases.append("h4_" + f[3:])
    if f.startswith("d1_"):
        aliases.append("d1_" + f[3:])
    # Common source-snapshot naming variants.
    aliases.extend([
        f + "_num",
        f + "_x",
        f + "_y",
        f.replace("_at_entry", ""),
        f.replace("m15_", ""),
    ])
    out = []
    for a in aliases:
        if a and a not in out:
            out.append(a)
    return out


def resolve_feature(df: pd.DataFrame, feature: str) -> tuple[str, str]:
    if df.empty:
        return "", "EMPTY_FRAME"
    cols = list(df.columns)
    if feature in cols:
        return feature, "EXACT"
    for a in feature_aliases(feature):
        if a in cols:
            return a, "ALIAS"
    return "", "MISSING"


def suggestions(df: pd.DataFrame, feature: str, limit: int = 6) -> str:
    if df.empty:
        return ""
    cols = [str(c) for c in df.columns]
    sugg = difflib.get_close_matches(feature, cols, n=limit, cutoff=0.45)
    return " | ".join(sugg)


def diagnose(rule: dict[str, Any], source_status: str, live_status: str, cand_status: str, cand_stats: dict[str, Any], threshold: float | None, cand_hit_count: int) -> str:
    if cand_status == "MISSING":
        return "MISSING_CANDIDATE_FEATURE"
    if cand_status == "EMPTY_FRAME":
        return "NO_CANDIDATE_ROWS"
    if int(cand_stats.get("non_null", 0)) == 0:
        return "CANDIDATE_FEATURE_ALL_NAN"
    if threshold_in_range(threshold, cand_stats) == "NO":
        return "THRESHOLD_OUTSIDE_CANDIDATE_RANGE"
    if cand_hit_count == 0:
        return "THRESHOLD_INSIDE_RANGE_BUT_NO_HIT_OR_STRICT_EDGE"
    if source_status == "MISSING" and cand_status != "MISSING":
        return "SOURCE_FEATURE_MISSING_BUT_CANDIDATE_RESOLVED"
    if live_status == "MISSING":
        return "LIVE_FRAME_FEATURE_MISSING_BUT_CANDIDATE_RESOLVED"
    return "OK_RULE_CAN_HIT_CANDIDATES"


def audit_rule(rule: dict[str, Any], source_df: pd.DataFrame, live_df: pd.DataFrame, cand_df: pd.DataFrame, promo: set[tuple[str, str, str]]) -> dict[str, Any]:
    sid = clean(rule.get("strategy_id"))
    group = clean(rule.get("tag_group"))
    tag = clean(rule.get("tag_name"))
    feature = clean(rule.get("feature"))
    op = clean(rule.get("op"))
    threshold = safe_float(rule.get("threshold"))
    is_promo = (sid, group, tag) in promo

    source_feature, source_status = resolve_feature(source_df, feature)
    live_feature, live_status = resolve_feature(live_df, feature)
    cand_feature, cand_status = resolve_feature(cand_df, feature)

    source_sid_df = source_df
    if not source_df.empty and "strategy_id" in source_df.columns:
        source_sid_df = source_df[source_df["strategy_id"].astype(str).map(clean).eq(sid)].copy()
    cand_sid_df = cand_df
    if not cand_df.empty and "strategy_id" in cand_df.columns:
        cand_sid_df = cand_df[cand_df["strategy_id"].astype(str).map(clean).eq(sid)].copy()

    source_series = source_sid_df[source_feature] if source_feature and source_feature in source_sid_df.columns else None
    live_series = live_df[live_feature] if live_feature and live_feature in live_df.columns else None
    cand_series = cand_sid_df[cand_feature] if cand_feature and cand_feature in cand_sid_df.columns else None
    source_st = stats(source_series)
    live_st = stats(live_series)
    cand_st = stats(cand_series)
    source_hit_count, source_hit_rate = op_hit(source_series, op, threshold)
    live_hit_count, live_hit_rate = op_hit(live_series, op, threshold)
    cand_hit_count, cand_hit_rate = op_hit(cand_series, op, threshold)

    return {
        "rule_id": clean(rule.get("rule_id")),
        "strategy_id": sid,
        "tag_group": group,
        "tag_name": tag,
        "configured_action": clean(rule.get("configured_action")),
        "is_promotable": bool(is_promo),
        "feature": feature,
        "op": op,
        "threshold": fm(threshold),
        "source_feature_exact_exists": feature in source_df.columns if not source_df.empty else False,
        "live_feature_exact_exists": feature in live_df.columns if not live_df.empty else False,
        "candidate_feature_exact_exists": feature in cand_df.columns if not cand_df.empty else False,
        "resolved_source_feature": source_feature,
        "resolved_live_feature": live_feature,
        "resolved_candidate_feature": cand_feature,
        "resolution_status": f"source={source_status};live={live_status};candidate={cand_status}",
        "source_non_null": source_st["non_null"],
        "source_min": source_st["min"],
        "source_p05": source_st["p05"],
        "source_p50": source_st["p50"],
        "source_p95": source_st["p95"],
        "source_max": source_st["max"],
        "candidate_rows_for_strategy": int(len(cand_sid_df)),
        "candidate_non_null": cand_st["non_null"],
        "candidate_min": cand_st["min"],
        "candidate_p05": cand_st["p05"],
        "candidate_p50": cand_st["p50"],
        "candidate_p95": cand_st["p95"],
        "candidate_max": cand_st["max"],
        "threshold_in_candidate_range": threshold_in_range(threshold, cand_st),
        "candidate_hit_count": cand_hit_count,
        "candidate_hit_rate": fm(cand_hit_rate),
        "live_rows": int(len(live_df)),
        "live_non_null": live_st["non_null"],
        "live_min": live_st["min"],
        "live_p05": live_st["p05"],
        "live_p50": live_st["p50"],
        "live_p95": live_st["p95"],
        "live_max": live_st["max"],
        "threshold_in_live_range": threshold_in_range(threshold, live_st),
        "live_hit_count": live_hit_count,
        "live_hit_rate": fm(live_hit_rate),
        "diagnosis": diagnose(rule, source_status, live_status, cand_status, cand_st, threshold, cand_hit_count),
        "close_feature_suggestions": suggestions(cand_df if not cand_df.empty else live_df, feature),
    }


def strategy_summary(rows: list[dict[str, Any]], cand_df: pd.DataFrame) -> list[dict[str, Any]]:
    out = []
    for sid in sorted({clean(r.get("strategy_id")) for r in rows}):
        sub = [r for r in rows if clean(r.get("strategy_id")) == sid]
        crows = 0
        if not cand_df.empty and "strategy_id" in cand_df.columns:
            crows = int((cand_df["strategy_id"].astype(str).map(clean) == sid).sum())
        missing = sorted({clean(r.get("feature")) for r in sub if str(r.get("diagnosis", "")).startswith("MISSING")})
        evals = sum(int(r.get("candidate_non_null") or 0) for r in sub)
        hits = sum(int(r.get("candidate_hit_count") or 0) for r in sub)
        out.append({
            "strategy_id": sid,
            "candidate_rows": crows,
            "rule_count": len(sub),
            "promotable_rule_count": sum(1 for r in sub if bool(r.get("is_promotable"))),
            "rules_with_exact_feature": sum(1 for r in sub if bool(r.get("candidate_feature_exact_exists"))),
            "rules_with_resolved_feature": sum(1 for r in sub if clean(r.get("resolved_candidate_feature"))),
            "rules_missing_feature": sum(1 for r in sub if "candidate=MISSING" in clean(r.get("resolution_status"))),
            "total_rule_evaluations": evals,
            "total_hit_count": hits,
            "hit_rate": "" if evals == 0 else round(hits / evals, 8),
            "missing_feature_names": " | ".join(missing),
        })
    return out


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    mkdirp(out_dir)

    rules = load_rules(args.rules_json)
    promo = promotable_tags(args.tag_recall_csv)
    manifest = parse_manifest(read_json(args.manifest_json))
    live_df = build_feature_frame(resolve(args.csv_dir), args)
    cand_df = build_candidate_feature_frame(live_df, manifest)
    source_df = read_csv_optional(args.source_feature_snapshot_csv)

    rule_rows = [audit_rule(r, source_df, live_df, cand_df, promo) for r in rules]
    strat_rows = strategy_summary(rule_rows, cand_df)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_FEATURE_CONTRACT_DIAGNOSED",
        "created_at": now_text(),
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "live_decision_ledger_mutated": False,
        "dispatch_ready_rows": 0,
        "inputs": {
            "csv_dir": str(resolve(args.csv_dir)),
            "manifest_json": str(resolve(args.manifest_json)),
            "rules_json": str(resolve(args.rules_json)),
            "tag_recall_csv": str(resolve(args.tag_recall_csv)),
            "source_feature_snapshot_csv": str(resolve(args.source_feature_snapshot_csv)),
            "max_bars": args.max_bars,
            "start_time": args.start_time,
            "end_time": args.end_time,
        },
        "counts": {
            "rules_loaded": int(len(rules)),
            "promotable_tags": int(len(promo)),
            "live_rows": int(len(live_df)),
            "candidate_rows": int(len(cand_df)),
            "source_feature_rows": int(len(source_df)),
            "rules_ok_can_hit_candidates": int(sum(1 for r in rule_rows if r.get("diagnosis") == "OK_RULE_CAN_HIT_CANDIDATES")),
            "rules_missing_candidate_feature": int(sum(1 for r in rule_rows if r.get("diagnosis") == "MISSING_CANDIDATE_FEATURE")),
            "rules_candidate_all_nan": int(sum(1 for r in rule_rows if r.get("diagnosis") == "CANDIDATE_FEATURE_ALL_NAN")),
            "rules_threshold_outside_candidate_range": int(sum(1 for r in rule_rows if r.get("diagnosis") == "THRESHOLD_OUTSIDE_CANDIDATE_RANGE")),
            "rules_no_hit": int(sum(1 for r in rule_rows if int(r.get("candidate_hit_count") or 0) == 0)),
            "candidate_hit_total": int(sum(int(r.get("candidate_hit_count") or 0) for r in rule_rows)),
            "promotable_candidate_hit_total": int(sum(int(r.get("candidate_hit_count") or 0) for r in rule_rows if bool(r.get("is_promotable")))),
        },
        "outputs": {
            "summary_json": str(out_dir / "gold_disc8_numeric_rule_feature_contract_audit_summary.json"),
            "rule_audit_csv": str(out_dir / "gold_disc8_numeric_rule_feature_contract_rule_audit.csv"),
            "strategy_summary_csv": str(out_dir / "gold_disc8_numeric_rule_feature_contract_strategy_summary.csv"),
        },
        "interpretation_hint": "If rules are MISSING_CANDIDATE_FEATURE, feature names differ. If threshold outside candidate range, source snapshot and live/backtest distribution differ. If threshold inside range but no hit, inspect strict inequality edge or strategy candidate subset.",
    }

    write_csv(out_dir / "gold_disc8_numeric_rule_feature_contract_rule_audit.csv", rule_rows, RULE_AUDIT_COLUMNS)
    write_csv(out_dir / "gold_disc8_numeric_rule_feature_contract_strategy_summary.csv", strat_rows, CANDIDATE_AUDIT_COLUMNS)
    write_json(out_dir / "gold_disc8_numeric_rule_feature_contract_audit_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit DISC8 numeric rule feature contract. Audit-only.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    p.add_argument("--rules-json", type=Path, default=DEFAULT_RULES_JSON)
    p.add_argument("--tag-recall-csv", type=Path, default=DEFAULT_TAG_RECALL_CSV)
    p.add_argument("--source-feature-snapshot-csv", type=Path, default=DEFAULT_SOURCE_FEATURE_SNAPSHOT_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--start-time", type=str, default="")
    p.add_argument("--end-time", type=str, default="")
    p.add_argument("--max-bars", type=int, default=12000)
    p.add_argument("--tail-m15", type=int, default=60000)
    p.add_argument("--tail-h1", type=int, default=30000)
    p.add_argument("--tail-h4", type=int, default=10000)
    p.add_argument("--tail-d1", type=int, default=3000)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
