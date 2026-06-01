#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build DISC8 numeric pre-send tagger rules from actual AI-review tags.

Audit-only. No OpenAI, no Discord, no MT5 order_send, no SOT mutation.

This builder replaces the earlier hand-made proxy idea.
It uses the actual AI-review tag ledger as source of truth for tags, and the
trade_feature_snapshot as source of truth for pre-entry numeric features.

Outputs are candidate rules and a 568-universe kept/blocked recall audit.
Rules are NOT promoted to live routing by this script.
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
DEFAULT_AI_REVIEW_LEDGER_JSONL = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_ai_review_ledger.jsonl")
DEFAULT_TRADE_FEATURE_SNAPSHOT_CSV = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/trade_feature_snapshot.csv")
DEFAULT_BASE_TRADE_CSV = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/disc8_review_trade_outcome_sample.csv")
DEFAULT_KEPT_LEDGER_CSV = Path("data/gold_disc8/source_of_truth/group_tag_filtered/group_tag_filtered_source_trade_ledger.csv")
DEFAULT_GATE_RULES_JSON = Path("data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json")
DEFAULT_RULE_HITS_CSV = Path("data/gold_disc8/verification/ai_review_data_driven/disc8_ai_review/group_tag_filter_applied/safe/disc8_group_tag_filter_rule_hits.csv")
DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_ai_tag_numeric_tagger_from_review")
SCHEMA_VERSION = "gold_disc8_ai_tag_numeric_tagger_from_review_v1_audit_only"

TAG_KEYS = {
    "risk": ["possible_risk_tags", "risk_tags"],
    "execution": ["execution_issue_tags"],
    "system": ["system_issue_tags"],
    "positive": [
        "positive_tags", "possible_positive_tags", "good_tags", "strength_tags", "favorable_tags",
        "winning_reason_tags", "success_tags", "supporting_tags",
    ],
}
TEXT_LIKE_COLUMNS = {
    "trade_id", "order_key", "payload_key", "decision_key", "strategy_id", "symbol", "direction",
    "entry_time", "exit_time", "outcome", "result", "reason", "comment", "matched_conditions",
    "failed_conditions", "tag_name", "tag_group", "tag_role", "truth_label",
}

RULE_COLUMNS = [
    "rule_id", "strategy_id", "tag_group", "tag_name", "configured_action", "feature", "op", "threshold",
    "actual_tag_count", "proxy_hit_count", "tag_true_positive_count", "tag_precision", "tag_recall", "tag_f1",
    "actual_blocked_hit_count", "actual_kept_hit_count", "blocked_rate_inside_proxy", "kept_false_hit_rate",
    "proxy_win_rate", "proxy_profit_factor", "proxy_avg_r", "proxy_total_r", "score", "verdict",
]
CONFUSION_COLUMNS = ["truth_label", "proxy_binary", "trade_count", "win_count", "loss_count", "win_rate", "profit_factor", "avg_r", "total_r"]
TAG_RECALL_COLUMNS = [
    "strategy_id", "tag_group", "tag_name", "configured_action", "ai_tag_count", "numeric_proxy_hit_count",
    "true_positive_tag_count", "false_positive_tag_count", "false_negative_tag_count", "precision_vs_ai_tag",
    "recall_vs_ai_tag", "truth_block_hit_count", "truth_block_recalled_by_numeric_count",
    "truth_block_recall_by_numeric", "kept_false_hit_count", "kept_false_hit_rate", "verdict",
]
TRADE_AUDIT_COLUMNS = [
    "trade_id", "strategy_id", "direction", "entry_time", "truth_label", "profit_r_num", "ai_tags",
    "numeric_tag_hits", "proxy_binary", "confusion_class", "dispatch_ready",
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


def canonical_tag(value: Any) -> str:
    return clean(value).lower().replace(" ", "_").replace("-", "_")


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


def read_csv_required(path: Path, label: str) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    df = pd.read_csv(windows_long_path(p), encoding="utf-8-sig", sep=None, engine="python")
    if df.empty:
        raise RuntimeError(f"{label} is empty: {p}")
    return df


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


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    p = resolve(path)
    if not p.exists():
        raise FileNotFoundError(f"AI review ledger JSONL not found: {p}")
    rows = []
    with open(windows_long_path(p), "r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"Invalid JSONL line {line_no}: {exc}") from exc
            if isinstance(obj, dict):
                rows.append(obj)
    if not rows:
        raise RuntimeError(f"AI review ledger JSONL has no object rows: {p}")
    return rows


def normalize_tag_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [canonical_tag(x) for x in parsed if canonical_tag(x)]
            except Exception:
                pass
        parts = re.split(r"[,;|]+", text)
        return [canonical_tag(x) for x in parts if canonical_tag(x)]
    if isinstance(value, list):
        return [canonical_tag(x) for x in value if canonical_tag(x)]
    return []


def find_first(obj: Any, names: set[str]) -> Any:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k) in names:
                return v
        for v in obj.values():
            found = find_first(v, names)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_first(v, names)
            if found is not None:
                return found
    return None


def collect_tags(obj: Any) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                for group, keys in TAG_KEYS.items():
                    if str(k) in keys:
                        for tag in normalize_tag_list(v):
                            out.append((group, tag))
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)
    walk(obj)
    seen = set()
    uniq = []
    for group, tag in out:
        key = (group, tag)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(key)
    return uniq


def id_lookup_from_base(base: pd.DataFrame) -> dict[tuple[str, str], str]:
    lookup = {}
    for _, row in base.iterrows():
        tid = clean(row.get("trade_id"))
        if not tid:
            continue
        for key in ["trade_id", "order_key", "payload_key"]:
            val = clean(row.get(key))
            if val:
                lookup[(key, val)] = tid
    return lookup


def resolve_trade_id_from_review(obj: dict[str, Any], lookup: dict[tuple[str, str], str]) -> str:
    for key in ["trade_id", "order_key", "payload_key"]:
        val = clean(find_first(obj, {key}))
        if val and (key, val) in lookup:
            return lookup[(key, val)]
        if key == "trade_id" and val:
            return val
    return ""


def expand_review_tags(review_rows: list[dict[str, Any]], base: pd.DataFrame) -> pd.DataFrame:
    lookup = id_lookup_from_base(base)
    rows = []
    for obj in review_rows:
        tid = resolve_trade_id_from_review(obj, lookup)
        if not tid:
            continue
        sid = clean(find_first(obj, {"strategy_id"}))
        for group, tag in collect_tags(obj):
            rows.append({"trade_id": tid, "strategy_id": sid, "tag_group": group, "tag_name": tag})
    if not rows:
        return pd.DataFrame(columns=["trade_id", "strategy_id", "tag_group", "tag_name"])
    return pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)


def gate_target_tags(gate_rules: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    out: dict[tuple[str, str, str], str] = {}
    for field, action in [("block_rules", "block"), ("watch_only_rules", "watch_only")]:
        rules = gate_rules.get(field, []) if isinstance(gate_rules.get(field), list) else []
        for r in rules:
            sid = clean(r.get("strategy_id"))
            group = clean(r.get("tag_group"))
            tag = clean(r.get("tag_name"))
            if sid and group and tag:
                out[(sid, group, tag)] = action
    return out


def merge_universe(base: pd.DataFrame, feature: pd.DataFrame, kept: pd.DataFrame) -> pd.DataFrame:
    if "trade_id" not in base.columns or "trade_id" not in kept.columns:
        raise RuntimeError("base and kept ledgers must contain trade_id")
    if "trade_id" not in feature.columns:
        raise RuntimeError("trade_feature_snapshot must contain trade_id for DISC8 numeric tagger build")
    kept_ids = {clean(x) for x in kept["trade_id"].tolist() if clean(x)}
    base = base.copy()
    base["trade_id"] = base["trade_id"].map(clean)
    feature = feature.copy()
    feature["trade_id"] = feature["trade_id"].map(clean)
    feature = feature.drop_duplicates("trade_id", keep="last")
    merged = base.merge(feature, on="trade_id", how="left", suffixes=("", "_feat"))
    merged["truth_label"] = merged["trade_id"].apply(lambda x: "actual_kept" if x in kept_ids else "actual_blocked")
    if "strategy_id" not in merged.columns and "strategy_id_feat" in merged.columns:
        merged["strategy_id"] = merged["strategy_id_feat"]
    if "direction" not in merged.columns and "direction_feat" in merged.columns:
        merged["direction"] = merged["direction_feat"]
    return merged


def numeric_feature_columns(df: pd.DataFrame, *, min_non_null: int) -> list[str]:
    cols = []
    for col in df.columns:
        if col in TEXT_LIKE_COLUMNS or col.endswith("_time") or col.endswith("_key"):
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if int(s.notna().sum()) >= min_non_null:
            cols.append(col)
    return sorted(set(cols))


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


def thresholds_for(series: pd.Series, max_thresholds: int) -> list[float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return []
    qs = [i / (max_thresholds + 1) for i in range(1, max_thresholds + 1)]
    vals = []
    for q in qs:
        try:
            x = float(s.quantile(q))
            if math.isfinite(x):
                vals.append(x)
        except Exception:
            pass
    return sorted(set(round(x, 10) for x in vals))


def build_rule_candidates(universe: pd.DataFrame, tag_df: pd.DataFrame, targets: dict[tuple[str, str, str], str], args: argparse.Namespace) -> list[dict[str, Any]]:
    feature_cols = numeric_feature_columns(universe, min_non_null=args.min_feature_non_null)
    tag_hits = {(clean(r.trade_id), clean(r.strategy_id), clean(r.tag_group), clean(r.tag_name)) for r in tag_df.itertuples(index=False)} if not tag_df.empty else set()
    best_by_tag: dict[tuple[str, str, str], dict[str, Any]] = {}
    all_candidates: list[dict[str, Any]] = []

    for (sid, group, tag), action in sorted(targets.items()):
        sdf = universe[universe["strategy_id"].astype(str) == sid].copy()
        if sdf.empty:
            continue
        y_tag = sdf["trade_id"].map(lambda tid: (clean(tid), sid, group, tag) in tag_hits)
        actual_tag_count = int(y_tag.sum())
        if actual_tag_count < args.min_ai_tag_trades:
            continue
        for feat in feature_cols:
            vals = pd.to_numeric(sdf[feat], errors="coerce")
            if int(vals.notna().sum()) < args.min_feature_non_null:
                continue
            for thr in thresholds_for(vals, args.max_thresholds_per_feature):
                for op in ["<=", ">="]:
                    pred = vals <= thr if op == "<=" else vals >= thr
                    pred = pred.fillna(False)
                    proxy_count = int(pred.sum())
                    if proxy_count < args.min_proxy_hits:
                        continue
                    tp_tag = int((pred & y_tag).sum())
                    if tp_tag <= 0:
                        continue
                    precision = tp_tag / proxy_count
                    recall = tp_tag / actual_tag_count
                    if precision < args.min_tag_precision or recall < args.min_tag_recall:
                        continue
                    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
                    pred_rows = sdf[pred]
                    r_vals = [trade_r(row) for _, row in pred_rows.iterrows()]
                    m = metrics(r_vals)
                    actual_blocked_hit = int((pred_rows["truth_label"] == "actual_blocked").sum())
                    actual_kept_hit = int((pred_rows["truth_label"] == "actual_kept").sum())
                    blocked_rate = actual_blocked_hit / proxy_count if proxy_count else 0.0
                    kept_total = int((sdf["truth_label"] == "actual_kept").sum())
                    kept_false_rate = actual_kept_hit / kept_total if kept_total else 0.0
                    score = (f1 * 2.0) + blocked_rate - kept_false_rate
                    rule_id = f"{sid}:{group}:{tag}:{feat}:{op}:{round(thr, 6)}"
                    cand = {
                        "rule_id": rule_id,
                        "strategy_id": sid,
                        "tag_group": group,
                        "tag_name": tag,
                        "configured_action": action,
                        "feature": feat,
                        "op": op,
                        "threshold": round(float(thr), 10),
                        "actual_tag_count": actual_tag_count,
                        "proxy_hit_count": proxy_count,
                        "tag_true_positive_count": tp_tag,
                        "tag_precision": precision,
                        "tag_recall": recall,
                        "tag_f1": f1,
                        "actual_blocked_hit_count": actual_blocked_hit,
                        "actual_kept_hit_count": actual_kept_hit,
                        "blocked_rate_inside_proxy": blocked_rate,
                        "kept_false_hit_rate": kept_false_rate,
                        "proxy_win_rate": m["win_rate"],
                        "proxy_profit_factor": m["profit_factor"],
                        "proxy_avg_r": m["avg_r"],
                        "proxy_total_r": m["total_r"],
                        "score": score,
                        "verdict": "CANDIDATE_RULE_AUDIT_ONLY",
                    }
                    all_candidates.append(cand)
                    key = (sid, group, tag)
                    old = best_by_tag.get(key)
                    if old is None or (cand["score"], cand["tag_f1"], -cand["kept_false_hit_rate"]) > (old["score"], old["tag_f1"], -old["kept_false_hit_rate"]):
                        best_by_tag[key] = cand
    return sorted(best_by_tag.values(), key=lambda r: (r["strategy_id"], r["tag_group"], r["tag_name"]))


def rule_matches(row: pd.Series, rule: dict[str, Any]) -> bool:
    val = safe_float(row.get(rule["feature"]))
    if val is None:
        return False
    thr = float(rule["threshold"])
    return val <= thr if rule["op"] == "<=" else val >= thr


def apply_rules(universe: pd.DataFrame, rules: list[dict[str, Any]], tag_df: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rules_by_sid: dict[str, list[dict[str, Any]]] = {}
    for r in rules:
        rules_by_sid.setdefault(r["strategy_id"], []).append(r)
    ai_tag_set = {(clean(r.trade_id), clean(r.strategy_id), clean(r.tag_group), clean(r.tag_name)) for r in tag_df.itertuples(index=False)} if not tag_df.empty else set()
    trade_rows: list[dict[str, Any]] = []
    proxy_tag_hits: list[dict[str, Any]] = []
    tag_recall_base: list[dict[str, Any]] = []

    for _, row in universe.iterrows():
        tid = clean(row.get("trade_id"))
        sid = clean(row.get("strategy_id"))
        hits = []
        for rule in rules_by_sid.get(sid, []):
            if rule_matches(row, rule):
                hits.append(rule)
                proxy_tag_hits.append({
                    "trade_id": tid,
                    "strategy_id": sid,
                    "tag_group": rule["tag_group"],
                    "tag_name": rule["tag_name"],
                    "configured_action": rule["configured_action"],
                    "rule_id": rule["rule_id"],
                    "feature": rule["feature"],
                    "op": rule["op"],
                    "threshold": rule["threshold"],
                    "value": safe_float(row.get(rule["feature"])),
                })
        proxy_block = any(h["configured_action"] == "block" for h in hits)
        proxy_binary = "proxy_block" if proxy_block else "proxy_keep"
        truth = clean(row.get("truth_label"))
        if truth == "actual_blocked" and proxy_binary == "proxy_block":
            cc = "true_positive_blocked"
        elif truth == "actual_blocked" and proxy_binary == "proxy_keep":
            cc = "false_negative_missed_block"
        elif truth == "actual_kept" and proxy_binary == "proxy_block":
            cc = "false_positive_wrong_block"
        else:
            cc = "true_negative_kept"
        ai_tags = sorted({f"{g}:{t}" for (trade_id, strategy, g, t) in ai_tag_set if trade_id == tid and strategy == sid})
        trade_rows.append({
            "trade_id": tid,
            "strategy_id": sid,
            "direction": clean(row.get("direction")),
            "entry_time": clean(row.get("entry_time")),
            "truth_label": truth,
            "profit_r_num": trade_r(row),
            "ai_tags": " | ".join(ai_tags),
            "numeric_tag_hits": " | ".join(f"{h['tag_group']}:{h['tag_name']}" for h in hits),
            "proxy_binary": proxy_binary,
            "confusion_class": cc,
            "dispatch_ready": False,
        })
    return trade_rows, proxy_tag_hits, tag_recall_base


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


def summarize_tag_recall(universe: pd.DataFrame, tag_df: pd.DataFrame, proxy_hits: list[dict[str, Any]], rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ai_set = {(clean(r.trade_id), clean(r.strategy_id), clean(r.tag_group), clean(r.tag_name)) for r in tag_df.itertuples(index=False)} if not tag_df.empty else set()
    proxy_set = {(r["trade_id"], r["strategy_id"], r["tag_group"], r["tag_name"]) for r in proxy_hits}
    out = []
    for rule in rules:
        sid, group, tag = rule["strategy_id"], rule["tag_group"], rule["tag_name"]
        sdf = universe[universe["strategy_id"].astype(str) == sid]
        trade_ids = {clean(x) for x in sdf["trade_id"].tolist()}
        ai_hits = {tid for tid in trade_ids if (tid, sid, group, tag) in ai_set}
        proxy_hits_ids = {tid for tid in trade_ids if (tid, sid, group, tag) in proxy_set}
        tp = ai_hits & proxy_hits_ids
        fp = proxy_hits_ids - ai_hits
        fn = ai_hits - proxy_hits_ids
        precision = None if not proxy_hits_ids else len(tp) / len(proxy_hits_ids)
        recall = None if not ai_hits else len(tp) / len(ai_hits)
        truth_block = {clean(row.trade_id) for row in sdf.itertuples(index=False) if clean(getattr(row, "truth_label", "")) == "actual_blocked"}
        truth_block_recalled = truth_block & proxy_hits_ids
        actual_kept = {clean(row.trade_id) for row in sdf.itertuples(index=False) if clean(getattr(row, "truth_label", "")) == "actual_kept"}
        kept_false = actual_kept & proxy_hits_ids
        truth_block_recall = None if not truth_block else len(truth_block_recalled) / len(truth_block)
        kept_false_rate = None if not actual_kept else len(kept_false) / len(actual_kept)
        verdict = "AUDIT_ONLY_REVIEW"
        if precision is not None and recall is not None:
            if precision >= 0.7 and recall >= 0.5 and (kept_false_rate or 0) <= 0.15:
                verdict = "POTENTIALLY_PROMOTABLE_AFTER_MANUAL_REVIEW"
            elif (kept_false_rate or 0) > 0.3:
                verdict = "HIGH_FALSE_BLOCK_RISK_DO_NOT_PROMOTE"
            elif recall < 0.3:
                verdict = "LOW_RECALL_DO_NOT_PROMOTE"
        out.append({
            "strategy_id": sid,
            "tag_group": group,
            "tag_name": tag,
            "configured_action": rule["configured_action"],
            "ai_tag_count": len(ai_hits),
            "numeric_proxy_hit_count": len(proxy_hits_ids),
            "true_positive_tag_count": len(tp),
            "false_positive_tag_count": len(fp),
            "false_negative_tag_count": len(fn),
            "precision_vs_ai_tag": fm(precision),
            "recall_vs_ai_tag": fm(recall),
            "truth_block_hit_count": len(truth_block),
            "truth_block_recalled_by_numeric_count": len(truth_block_recalled),
            "truth_block_recall_by_numeric": fm(truth_block_recall),
            "kept_false_hit_count": len(kept_false),
            "kept_false_hit_rate": fm(kept_false_rate),
            "verdict": verdict,
        })
    return out


def main() -> int:
    args = parse_args()
    out_dir = resolve(args.out_dir)
    mkdirp(out_dir)
    base = read_csv_required(args.base_trade_csv, "base 568 trade CSV")
    feature = read_csv_required(args.trade_feature_snapshot_csv, "trade_feature_snapshot CSV")
    kept = read_csv_required(args.kept_ledger_csv, "kept SOT ledger CSV")
    gate_rules = read_json(args.gate_rules_json)
    review_rows = load_jsonl(args.ai_review_ledger_jsonl)
    tag_df = expand_review_tags(review_rows, base)
    targets = gate_target_tags(gate_rules)
    universe = merge_universe(base, feature, kept)
    rules = build_rule_candidates(universe, tag_df, targets, args)
    trade_rows, proxy_hits, _ = apply_rules(universe, rules, tag_df)
    confusion_rows = summarize_confusion(trade_rows)
    tag_recall_rows = summarize_tag_recall(universe, tag_df, proxy_hits, rules)

    rules_json_path = out_dir / "gold_disc8_ai_tag_numeric_tagger_rules.json"
    rules_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_rule_summary.csv"
    confusion_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_568_confusion_summary.csv"
    tag_recall_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv"
    trade_audit_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_trade_audit.csv"
    proxy_hits_csv = out_dir / "gold_disc8_ai_tag_numeric_tagger_proxy_tag_hits.csv"
    summary_json = out_dir / "gold_disc8_ai_tag_numeric_tagger_build_summary.json"

    write_csv(rules_csv, [{k: fm(v) for k, v in r.items()} for r in rules], RULE_COLUMNS)
    write_csv(confusion_csv, confusion_rows, CONFUSION_COLUMNS)
    write_csv(tag_recall_csv, tag_recall_rows, TAG_RECALL_COLUMNS)
    write_csv(trade_audit_csv, trade_rows, TRADE_AUDIT_COLUMNS)
    write_csv(proxy_hits_csv, proxy_hits, ["trade_id", "strategy_id", "tag_group", "tag_name", "configured_action", "rule_id", "feature", "op", "threshold", "value"])
    rules_obj = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_text(),
        "tag_source": "actual_ai_review_ledger",
        "feature_source": "trade_feature_snapshot_csv",
        "audit_only": True,
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "dispatch_ready_enabled": False,
        "rules": rules,
    }
    write_json(rules_json_path, rules_obj)

    truth_blocked = [r for r in trade_rows if r["truth_label"] == "actual_blocked"]
    truth_kept = [r for r in trade_rows if r["truth_label"] == "actual_kept"]
    tp = [r for r in trade_rows if r["confusion_class"] == "true_positive_blocked"]
    fn = [r for r in trade_rows if r["confusion_class"] == "false_negative_missed_block"]
    fp = [r for r in trade_rows if r["confusion_class"] == "false_positive_wrong_block"]
    tn = [r for r in trade_rows if r["confusion_class"] == "true_negative_kept"]
    blocked_recall = None if not truth_blocked else len(tp) / len(truth_blocked)
    block_precision = None if not (tp or fp) else len(tp) / (len(tp) + len(fp))
    kept_false_block_rate = None if not truth_kept else len(fp) / len(truth_kept)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "cycle_ok": True,
        "reason": "OK_AUDIT_ONLY_AI_TAG_NUMERIC_TAGGER_BUILT_FROM_REVIEW",
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "sot_mutated": False,
        "runtime_gate_rules_mutated": False,
        "dispatch_ready_enabled": False,
        "inputs": {
            "ai_review_ledger_jsonl": str(resolve(args.ai_review_ledger_jsonl)),
            "trade_feature_snapshot_csv": str(resolve(args.trade_feature_snapshot_csv)),
            "base_trade_csv": str(resolve(args.base_trade_csv)),
            "kept_ledger_csv": str(resolve(args.kept_ledger_csv)),
            "gate_rules_json": str(resolve(args.gate_rules_json)),
        },
        "outputs": {
            "rules_json": str(rules_json_path),
            "rules_csv": str(rules_csv),
            "confusion_csv": str(confusion_csv),
            "tag_recall_csv": str(tag_recall_csv),
            "trade_audit_csv": str(trade_audit_csv),
            "proxy_hits_csv": str(proxy_hits_csv),
            "summary_json": str(summary_json),
        },
        "counts": {
            "base_trade_rows": int(len(base)),
            "feature_rows": int(len(feature)),
            "kept_sot_rows": int(len(kept)),
            "ai_review_rows": int(len(review_rows)),
            "expanded_ai_tag_rows": int(len(tag_df)),
            "gate_target_tags": int(len(targets)),
            "numeric_rules_built": int(len(rules)),
            "proxy_tag_hit_rows": int(len(proxy_hits)),
            "true_positive_blocked_rows": int(len(tp)),
            "false_negative_missed_block_rows": int(len(fn)),
            "false_positive_wrong_block_rows": int(len(fp)),
            "true_negative_kept_rows": int(len(tn)),
        },
        "classification_metrics": {
            "blocked_recall": fm(blocked_recall),
            "block_precision": fm(block_precision),
            "kept_false_block_rate": fm(kept_false_block_rate),
        },
        "promotion_rule": "Do not promote unless kept_false_block_rate is low, block_precision is high, and strategy/tag recall summary marks rules as promotable after manual review.",
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build DISC8 numeric tagger from actual AI-review tags. Audit-only.")
    p.add_argument("--ai-review-ledger-jsonl", type=Path, default=DEFAULT_AI_REVIEW_LEDGER_JSONL)
    p.add_argument("--trade-feature-snapshot-csv", type=Path, default=DEFAULT_TRADE_FEATURE_SNAPSHOT_CSV)
    p.add_argument("--base-trade-csv", type=Path, default=DEFAULT_BASE_TRADE_CSV)
    p.add_argument("--kept-ledger-csv", type=Path, default=DEFAULT_KEPT_LEDGER_CSV)
    p.add_argument("--gate-rules-json", type=Path, default=DEFAULT_GATE_RULES_JSON)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--min-ai-tag-trades", type=int, default=5)
    p.add_argument("--min-proxy-hits", type=int, default=5)
    p.add_argument("--min-tag-precision", type=float, default=0.60)
    p.add_argument("--min-tag-recall", type=float, default=0.25)
    p.add_argument("--min-feature-non-null", type=int, default=30)
    p.add_argument("--max-thresholds-per-feature", type=int, default=20)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
