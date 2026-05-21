#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build GOLD strict-7 AI-tag numeric rules with positive/balance support.

This is the no-source-patch builder used by scripts/build_gold_strict_7_ai_tag_numeric_rules.bat.
It avoids mutating build_gold_strict_7_ai_tag_numeric_rules.py locally.

It reuses the stable base builder helpers, but replaces the tag expansion and
candidate/rule assembly so positive tags and win/loss balance audit fields are
included directly in the generated ai_tag_numeric_rules.json.

No AI call. No MT5 call. No Discord. No order_send.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

import build_gold_strict_7_ai_tag_numeric_rules as base

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AI_REVIEW_DIR = Path("data/runtime_logs/trade_ai_review_backtest_gold_strict_7")
DEFAULT_OUTPUT_JSON = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json")
DEFAULT_OUTPUT_CSV = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules_summary.csv")
DEFAULT_TAG_BALANCE_AUDIT_CSV = Path("data/runtime_state/gold/strict_7/ai_tag_win_loss_balance_audit.csv")
SCHEMA_VERSION = "gold_strict_7_ai_tag_numeric_rules_v3_positive_balance_audit_no_patch"

POSITIVE_TAG_KEYS = [
    "positive_tags",
    "possible_positive_tags",
    "good_tags",
    "strength_tags",
    "favorable_tags",
    "winning_reason_tags",
    "success_tags",
    "supporting_tags",
]


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


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    mkdirp(p.parent)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    mkdirp(p.parent)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def clean_str(value: Any, default: str = "") -> str:
    return base.clean_str(value, default)


def canonical_tag(tag: Any) -> str:
    return base.canonical_tag(tag)


def safe_float(value: Any, default: float | None = None) -> float | None:
    return base.safe_float(value, default)


def is_informative_tag(tag: Any) -> bool:
    return base.is_informative_tag(canonical_tag(tag))


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
                    return [canonical_tag(x) for x in parsed if is_informative_tag(x)]
            except Exception:
                pass
        return [canonical_tag(x) for x in text.replace(";", ",").split(",") if is_informative_tag(x)]
    if isinstance(value, list):
        return [canonical_tag(x) for x in value if is_informative_tag(x)]
    return []


def explode_review_tags(rows: list[dict[str, Any]]) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for row in rows:
        seen: set[tuple[str, str, str]] = set()
        for json_key, tag_group, tag_role in [
            ("possible_risk_tags", "risk", "risk"),
            ("risk_tags", "risk", "risk"),
            ("execution_issue_tags", "execution", "risk"),
            ("system_issue_tags", "system", "risk"),
        ]:
            for tag_name in normalize_tag_list(row.get(json_key, [])):
                key = (tag_name, tag_group, tag_role)
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "trade_id": clean_str(row.get("trade_id")),
                    "order_key": clean_str(row.get("order_key")),
                    "payload_key": clean_str(row.get("payload_key")),
                    "strategy_id": clean_str(row.get("strategy_id")),
                    "symbol": clean_str(row.get("symbol")),
                    "tag_name": tag_name,
                    "tag_group": tag_group,
                    "tag_role": tag_role,
                })
        for json_key in POSITIVE_TAG_KEYS:
            for tag_name in normalize_tag_list(row.get(json_key, [])):
                key = (tag_name, "positive", "positive")
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "trade_id": clean_str(row.get("trade_id")),
                    "order_key": clean_str(row.get("order_key")),
                    "payload_key": clean_str(row.get("payload_key")),
                    "strategy_id": clean_str(row.get("strategy_id")),
                    "symbol": clean_str(row.get("symbol")),
                    "tag_name": tag_name,
                    "tag_group": "positive",
                    "tag_role": "positive",
                })
    return pd.DataFrame(out)


def build_candidate_rows(feature_df: pd.DataFrame, tag_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if feature_df.empty or tag_df.empty:
        return pd.DataFrame()
    keys = ["trade_id", "order_key", "payload_key"]
    feature = feature_df.copy()
    tag_work = tag_df.copy()
    for k in keys:
        if k not in feature.columns:
            feature[k] = ""
        if k not in tag_work.columns:
            tag_work[k] = ""
    joined = tag_work.merge(feature, on=keys, how="left", suffixes=("_tag", ""))
    if "strategy_id" not in joined.columns and "strategy_id_tag" in joined.columns:
        joined["strategy_id"] = joined["strategy_id_tag"]
    joined["strategy_id"] = joined["strategy_id"].fillna(joined.get("strategy_id_tag", "")).astype(str)
    rows: list[dict[str, Any]] = []
    for strategy_id, sdf in joined.groupby("strategy_id", dropna=False):
        strategy_id = clean_str(strategy_id)
        if not strategy_id:
            continue
        trade_base = feature[feature["strategy_id"].astype(str) == strategy_id].copy() if "strategy_id" in feature.columns else feature.copy()
        if trade_base.empty:
            continue
        tag_pairs = sdf[["tag_name", "tag_group", "tag_role"]].drop_duplicates().itertuples(index=False, name=None)
        for tag_name, tag_group, tag_role in tag_pairs:
            tag_name = clean_str(tag_name)
            tag_group = clean_str(tag_group)
            tag_role = clean_str(tag_role, "positive" if tag_group == "positive" else "risk")
            if not tag_name or tag_group not in {"risk", "execution", "system", "positive"}:
                continue
            tagged_keys = sdf[(sdf["tag_name"] == tag_name) & (sdf["tag_group"] == tag_group)][keys].drop_duplicates()
            work = trade_base.copy()
            work = work.merge(tagged_keys.assign(_tag_hit=True), on=keys, how="left")
            work["tag_name"] = tag_name
            work["tag_group"] = tag_group
            hit = work["_tag_hit"].eq(True)
            if int(hit.sum()) < args.min_tag_trades:
                continue
            work.loc[~hit, "tag_name"] = "__NO_TAG__"
            work.loc[~hit, "tag_group"] = tag_group
            for feat in base.FEATURES:
                if feat not in work.columns:
                    continue
                for thr in base.feature_thresholds(work[feat], args.max_thresholds_per_feature):
                    for op in ["<=", ">="]:
                        res = base.evaluate_condition(work, tag_name, tag_group, feat, op, thr)
                        if not res:
                            continue
                        res["strategy_id"] = strategy_id
                        res["tag_role"] = tag_role
                        res["condition_type"] = "single"
                        res["condition_text"] = f"{feat} {op} {thr}"
                        if (
                            res["tag_precision"] >= args.min_precision
                            and res["tag_recall"] >= args.min_recall
                            and res["removed_trades"] >= args.min_removed_trades
                            and res["kept_trades"] >= args.min_kept_trades
                        ):
                            rows.append(res)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["strategy_id", "tag_name", "tag_group", "tag_precision", "tag_recall", "removed_trades"],
        ascending=[True, True, True, False, False, False],
    )
    return out


def load_tag_balance_audit(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = read_csv(path)
    for col in ["strategy_id", "tag_group", "tag_name", "tag_role"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    return df


def enrich_candidates_with_tag_balance(candidates: pd.DataFrame, audit_df: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty or audit_df.empty:
        return candidates
    work = candidates.copy()
    if "tag_role" not in work.columns:
        work["tag_role"] = work["tag_group"].apply(lambda x: "positive" if clean_str(x) == "positive" else "risk")
    join_cols = ["strategy_id", "tag_group", "tag_name", "tag_role"]
    keep_cols = join_cols + [
        "tag_hit_count", "tag_win_count", "tag_loss_count", "tag_win_rate", "tag_avg_r", "tag_pf",
        "wins_with_tag_rate", "losses_with_tag_rate", "verdict", "display_level_suggestion",
    ]
    available = [c for c in keep_cols if c in audit_df.columns]
    if not set(join_cols).issubset(set(available)):
        return work
    return work.merge(audit_df[available].drop_duplicates(join_cols), on=join_cols, how="left")


def build_rules(candidates: pd.DataFrame, args: argparse.Namespace) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    if candidates.empty:
        return [], pd.DataFrame()
    work = candidates.groupby(["strategy_id", "tag_name", "tag_group"], dropna=False).head(args.max_rules_per_strategy_tag).copy()
    rules: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for i, (_, row) in enumerate(work.iterrows(), start=1):
        feature = clean_str(row.get("feature_1"))
        op = clean_str(row.get("op_1"))
        threshold = safe_float(row.get("threshold_1"))
        if not feature or not op or threshold is None:
            continue
        tag_role = clean_str(row.get("tag_role"), "positive" if clean_str(row.get("tag_group")) == "positive" else "risk")
        conditions = [{"feature": feature, "op": op, "threshold": threshold, "aliases": base.FEATURE_ALIASES.get(feature, [])}]
        rule = {
            "rule_id": f"GOLD_STRICT7_TAG_RULE_{i:04d}",
            "symbol": "GOLD",
            "strategy_id": clean_str(row.get("strategy_id")),
            "tag_name": clean_str(row.get("tag_name")),
            "tag_group": clean_str(row.get("tag_group")),
            "tag_role": tag_role,
            "severity": "WATCH",
            "action": "INFO" if tag_role == "positive" else "WARN",
            "diagnostic_grade": "NUMERIC_TAG_APPROXIMATION",
            "condition_type": "single",
            "condition_text": clean_str(row.get("condition_text")),
            "conditions": conditions,
            "tag_precision": safe_float(row.get("tag_precision")),
            "tag_recall": safe_float(row.get("tag_recall")),
            "tag_total": safe_float(row.get("tag_total")),
            "baseline_pf": safe_float(row.get("baseline_pf")),
            "kept_pf": safe_float(row.get("kept_pf")),
            "removed_trades": safe_float(row.get("removed_trades")),
            "kept_trades": safe_float(row.get("kept_trades")),
            "verdict": clean_str(row.get("verdict")),
            "display_level_suggestion": clean_str(row.get("display_level_suggestion")),
            "tag_hit_count": safe_float(row.get("tag_hit_count")),
            "tag_win_count": safe_float(row.get("tag_win_count")),
            "tag_loss_count": safe_float(row.get("tag_loss_count")),
            "tag_win_rate": safe_float(row.get("tag_win_rate")),
            "tag_avg_r": safe_float(row.get("tag_avg_r")),
            "tag_pf": safe_float(row.get("tag_pf")),
            "wins_with_tag_rate": safe_float(row.get("wins_with_tag_rate")),
            "losses_with_tag_rate": safe_float(row.get("losses_with_tag_rate")),
            "source": "gold_strict_7_ai_review_feature_snapshot_tags_v3_no_patch",
            "note": "Deterministic numeric approximation of historical strict-7 AI-review tag; no AI call at notification time.",
        }
        rules.append(rule)
        flat = {k: v for k, v in rule.items() if k != "conditions"}
        flat["conditions_json"] = json.dumps(conditions, ensure_ascii=False, default=str)
        summary_rows.append(flat)
    return rules, pd.DataFrame(summary_rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GOLD strict 7 AI-tag numeric rules JSON, no local source patching.")
    p.add_argument("--ai-review-dir", type=Path, default=DEFAULT_AI_REVIEW_DIR)
    p.add_argument("--feature-snapshot-csv", type=Path, default=None)
    p.add_argument("--ai-review-jsonl", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    p.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    p.add_argument("--tag-balance-audit-csv", type=Path, default=DEFAULT_TAG_BALANCE_AUDIT_CSV)
    p.add_argument("--allow-non-strict7-strategy-rules", action="store_true")
    p.add_argument("--min-tag-trades", type=int, default=3)
    p.add_argument("--min-precision", type=float, default=0.55)
    p.add_argument("--min-recall", type=float, default=0.30)
    p.add_argument("--min-removed-trades", type=int, default=2)
    p.add_argument("--min-kept-trades", type=int, default=3)
    p.add_argument("--max-thresholds-per-feature", type=int, default=30)
    p.add_argument("--max-rules-per-strategy-tag", type=int, default=2)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    allowed_strategy_ids = base.strict7_strategy_ids()
    ai_dir = resolve(args.ai_review_dir)
    feature_csv = resolve(args.feature_snapshot_csv) if args.feature_snapshot_csv else ai_dir / "trade_feature_snapshot.csv"
    review_jsonl = resolve(args.ai_review_jsonl) if args.ai_review_jsonl else ai_dir / "trade_ai_review_ledger.jsonl"
    output_json = resolve(args.output_json)
    output_csv = resolve(args.output_csv)
    audit_csv = resolve(args.tag_balance_audit_csv)
    if not feature_csv.exists():
        raise SystemExit(f"feature snapshot CSV not found: {feature_csv}. Run GOLD strict-7 post-trade/backtest AI review pipeline first.")
    if not review_jsonl.exists():
        raise SystemExit(f"AI review JSONL not found: {review_jsonl}. Run GOLD strict-7 post-trade/backtest AI review pipeline first.")
    feature_df_raw = read_csv(feature_csv)
    feature_df, strategy_alignment = base.filter_feature_rows_to_strict7(
        feature_df_raw,
        allowed_strategy_ids,
        allow_non_strict7_strategy_rules=bool(args.allow_non_strict7_strategy_rules),
    )
    review_rows = base.read_jsonl(review_jsonl)
    tag_df = explode_review_tags(review_rows)
    tag_strategy_ids_raw = base.unique_clean_values(tag_df, "strategy_id") if not tag_df.empty else []
    audit_df = load_tag_balance_audit(audit_csv)
    candidates = build_candidate_rows(feature_df, tag_df, args)
    candidates = enrich_candidates_with_tag_balance(candidates, audit_df)
    rules, summary_df = build_rules(candidates, args)
    rule_strategy_ids = sorted({clean_str(rule.get("strategy_id")) for rule in rules if clean_str(rule.get("strategy_id"))})
    unexpected_rule_strategy_ids = sorted(set(rule_strategy_ids) - set(allowed_strategy_ids))
    if unexpected_rule_strategy_ids and not args.allow_non_strict7_strategy_rules:
        raise SystemExit(
            "Generated non-strict7 AI-tag numeric rules. Refusing to write JSON. "
            f"unexpected_rule_strategy_ids={unexpected_rule_strategy_ids}; allowed_strategy_ids={allowed_strategy_ids}"
        )
    strategy_alignment.update({
        "tag_strategy_ids_raw": tag_strategy_ids_raw,
        "candidate_strategy_ids": base.unique_clean_values(candidates, "strategy_id") if not candidates.empty else [],
        "rule_strategy_ids": rule_strategy_ids,
        "unexpected_rule_strategy_ids": unexpected_rule_strategy_ids,
    })
    obj = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "symbol": "GOLD",
        "input_ai_review_dir": str(ai_dir),
        "input_feature_snapshot_csv": str(feature_csv),
        "input_ai_review_jsonl": str(review_jsonl),
        "input_tag_balance_audit_csv": str(audit_csv),
        "strategy_alignment": strategy_alignment,
        "settings": {
            "min_tag_trades": int(args.min_tag_trades),
            "min_precision": float(args.min_precision),
            "min_recall": float(args.min_recall),
            "min_removed_trades": int(args.min_removed_trades),
            "min_kept_trades": int(args.min_kept_trades),
            "max_thresholds_per_feature": int(args.max_thresholds_per_feature),
            "max_rules_per_strategy_tag": int(args.max_rules_per_strategy_tag),
            "allow_non_strict7_strategy_rules": bool(args.allow_non_strict7_strategy_rules),
        },
        "rows": {
            "feature_snapshot_rows_raw": int(len(feature_df_raw)),
            "feature_snapshot_rows_strict7": int(len(feature_df)),
            "ai_review_rows": int(len(review_rows)),
            "tag_rows": int(len(tag_df)),
            "tag_balance_audit_rows": int(len(audit_df)),
            "candidate_rows": int(len(candidates)),
            "rules_count": int(len(rules)),
        },
        "rules_count": int(len(rules)),
        "combo_rules_count": 0,
        "combo_rules": [],
        "rules": rules,
        "safety": {"ai_called": False, "mt5_calls": False, "order_send": False, "discord_send": False},
    }
    write_json(output_json, obj)
    write_csv(summary_df, output_csv)
    print(json.dumps({
        "cycle_ok": True,
        "schema_version": SCHEMA_VERSION,
        "rules_count": len(rules),
        "rule_strategy_ids": rule_strategy_ids,
        "tag_rows": int(len(tag_df)),
        "tag_balance_audit_rows": int(len(audit_df)),
        "filtered_out_feature_rows": strategy_alignment.get("filtered_out_feature_rows", 0),
        "input_ai_review_dir": str(ai_dir),
        "output_json": str(output_json),
        "output_csv": str(output_csv),
        "candidate_rows": int(len(candidates)),
    }, ensure_ascii=False, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
