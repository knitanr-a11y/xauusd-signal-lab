#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build GOLD strict-7 AI-tag numeric rules JSON for notification-time scoring.

This builder converts completed post-trade AI review tags into deterministic
single-feature numeric rules that can be applied at notification time.

Inputs by default come from the GOLD strict-7 backtest AI-review pipeline:
  data/runtime_logs/trade_ai_review_backtest_gold_strict_7/trade_feature_snapshot.csv
  data/runtime_logs/trade_ai_review_backtest_gold_strict_7/trade_ai_review_ledger.jsonl

No AI call is made here. No MT5 call. No order_send. No Discord send.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from gold_strict_7_signal_specs import get_signal_specs, validate_signal_specs

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AI_REVIEW_DIR = Path("data/runtime_logs/trade_ai_review_backtest_gold_strict_7")
DEFAULT_OUTPUT_JSON = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json")
DEFAULT_OUTPUT_CSV = Path("data/runtime_state/gold/strict_7/ai_tag_numeric_rules_summary.csv")
SCHEMA_VERSION = "gold_strict_7_ai_tag_numeric_rules_v2_strict7_source_guard"

FEATURES = [
    "entry_position_in_m15_range_100_pct",
    "m15_signal_candle_range_atr_ratio",
    "m15_signal_candle_body_ratio",
    "m15_signal_candle_close_pos",
    "m15_ema20_distance_atr",
    "m15_ema50_distance_atr",
    "m15_ema200_distance_atr",
    "m15_macd_hist_at_entry",
    "m15_macd_hist_delta_at_entry",
    "m15_recent_large_candle_count_20",
    "m15_recent_breakout_high_count_20",
    "m15_recent_breakout_low_count_20",
    "h1_close_vs_ema20_atr",
    "h1_close_vs_ema50_atr",
    "h1_close_vs_ema200_atr",
    "h4_close_vs_ema20_atr",
    "h4_close_vs_ema50_atr",
    "d1_close_vs_ema20_atr",
]

FEATURE_ALIASES = {
    "entry_position_in_m15_range_100_pct": ["entry_position_pct", "trigger_entry_position_pct"],
    "m15_signal_candle_range_atr_ratio": ["range_atr", "trigger_range_atr", "trigger_range_atr14"],
    "m15_signal_candle_body_ratio": ["body_ratio", "trigger_body_ratio"],
    "m15_signal_candle_close_pos": ["close_pos", "trigger_close_pos"],
    "m15_ema20_distance_atr": ["ema20_distance_atr", "trigger_ema20_distance_atr"],
    "m15_ema50_distance_atr": ["ema50_distance_atr", "trigger_ema50_distance_atr"],
    "m15_ema200_distance_atr": ["ema200_distance_atr", "trigger_ema200_distance_atr"],
    "m15_macd_hist_at_entry": ["macd_hist", "trigger_macd_hist"],
    "m15_macd_hist_delta_at_entry": ["macd_hist_delta", "trigger_macd_hist_delta"],
    "h1_close_vs_ema20_atr": ["h1_close_vs_ema20_atr"],
    "h1_close_vs_ema50_atr": ["h1_close_vs_ema50_atr"],
    "h1_close_vs_ema200_atr": ["h1_close_vs_ema200_atr"],
    "h4_close_vs_ema20_atr": ["h4_close_vs_ema20_atr"],
    "h4_close_vs_ema50_atr": ["h4_close_vs_ema50_atr"],
    "d1_close_vs_ema20_atr": ["d1_close_vs_ema20_atr"],
}

NON_INFORMATIVE_TAGS = {
    "", "-", "none", "null", "n/a", "na", "unknown", "unclear",
    "no_clear_positive_tag", "no_positive_tag", "no_risk_tag", "no_clear_risk_tag",
}


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


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not Path(path).exists():
        return rows
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def canonical_tag(tag: Any) -> str:
    return clean_str(tag).lower().replace(" ", "_").replace("-", "_")


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def unique_clean_values(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values: list[str] = []
    for value in df[column].dropna().tolist():
        text = clean_str(value)
        if text:
            values.append(text)
    return sorted(set(values))


def strict7_strategy_ids() -> list[str]:
    validate_signal_specs()
    return [spec.strategy_id for spec in get_signal_specs()]


def filter_feature_rows_to_strict7(
    feature_df: pd.DataFrame,
    allowed_strategy_ids: list[str],
    *,
    allow_non_strict7_strategy_rules: bool,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    before_rows = int(len(feature_df))
    if "strategy_id" not in feature_df.columns:
        raise SystemExit(
            "trade_feature_snapshot.csv has no strategy_id column. "
            "Refusing to build notification-time AI-tag rules because strict7 alignment cannot be verified."
        )
    allowed = set(allowed_strategy_ids)
    before_strategy_ids = unique_clean_values(feature_df, "strategy_id")
    matched_strategy_ids = sorted(set(before_strategy_ids) & allowed)
    unexpected_strategy_ids = sorted(set(before_strategy_ids) - allowed)
    if not matched_strategy_ids:
        raise SystemExit(
            "No GOLD strict-7 strategy_id rows were found in trade_feature_snapshot.csv. "
            "This usually means the builder is pointing at an old GOLD AI review folder. "
            f"found_strategy_ids={before_strategy_ids}; expected_any={allowed_strategy_ids}"
        )
    if unexpected_strategy_ids and not allow_non_strict7_strategy_rules:
        # Do not fail; filter them out. The hard failure is only when there are no strict7 rows at all.
        # This lets mixed diagnostic folders be used safely without producing old-strategy rules.
        pass
    mask = feature_df["strategy_id"].astype(str).isin(allowed)
    filtered = feature_df[mask.fillna(False)].copy()
    summary = {
        "allowed_strategy_ids": allowed_strategy_ids,
        "feature_strategy_ids_before_filter": before_strategy_ids,
        "feature_strategy_ids_matched_strict7": matched_strategy_ids,
        "feature_strategy_ids_filtered_out": unexpected_strategy_ids,
        "feature_rows_before_filter": before_rows,
        "feature_rows_after_filter": int(len(filtered)),
        "filtered_out_feature_rows": int(before_rows - len(filtered)),
        "allow_non_strict7_strategy_rules": bool(allow_non_strict7_strategy_rules),
    }
    return filtered, summary


def is_informative_tag(tag: str) -> bool:
    return canonical_tag(tag) not in NON_INFORMATIVE_TAGS


def explode_review_tags(rows: list[dict[str, Any]]) -> pd.DataFrame:
    out: list[dict[str, Any]] = []
    for row in rows:
        seen: set[tuple[str, str]] = set()
        for json_key, tag_group in [
            ("possible_risk_tags", "risk"),
            ("execution_issue_tags", "execution"),
            ("system_issue_tags", "system"),
        ]:
            tags = row.get(json_key, [])
            if isinstance(tags, str):
                tags = [x.strip() for x in tags.replace(";", ",").split(",") if x.strip()]
            if not isinstance(tags, list):
                tags = []
            for tag in tags:
                tag_name = canonical_tag(tag)
                if not is_informative_tag(tag_name):
                    continue
                key = (tag_name, tag_group)
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
                })
    return pd.DataFrame(out)


def feature_thresholds(series: pd.Series, max_thresholds: int) -> list[float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 5:
        return []
    qs = [i / (max_thresholds + 1) for i in range(1, max_thresholds + 1)]
    vals = sorted(set(float(x) for x in s.quantile(qs).tolist() if pd.notna(x)))
    return vals


def profit_factor(values: pd.Series) -> float | None:
    r = pd.to_numeric(values, errors="coerce").dropna()
    if r.empty:
        return None
    wins = float(r[r > 0].sum())
    losses = abs(float(r[r < 0].sum()))
    if losses <= 1e-12:
        return None if wins <= 1e-12 else 999.0
    return wins / losses


def evaluate_condition(df: pd.DataFrame, tag_name: str, tag_group: str, feature: str, op: str, threshold: float) -> dict[str, Any] | None:
    value = pd.to_numeric(df[feature], errors="coerce")
    if op == "<=":
        pred = value <= threshold
    elif op == ">=":
        pred = value >= threshold
    else:
        return None
    pred = pred.fillna(False)
    actual = (df["tag_name"] == tag_name) & (df["tag_group"] == tag_group)
    removed = df[pred].copy()
    kept = df[~pred].copy()
    tp = int((pred & actual).sum())
    tag_total = int(actual.sum())
    removed_trades = int(pred.sum())
    if removed_trades <= 0 or tag_total <= 0:
        return None
    precision = tp / removed_trades if removed_trades else 0.0
    recall = tp / tag_total if tag_total else 0.0
    return {
        "tag_name": tag_name,
        "tag_group": tag_group,
        "feature_1": feature,
        "op_1": op,
        "threshold_1": float(threshold),
        "tag_precision": float(precision),
        "tag_recall": float(recall),
        "tag_total": int(tag_total),
        "removed_trades": int(removed_trades),
        "kept_trades": int(len(kept)),
        "baseline_pf": profit_factor(df.get("profit_r", pd.Series(dtype=float))),
        "kept_pf": profit_factor(kept.get("profit_r", pd.Series(dtype=float))),
        "removed_avg_r": safe_float(pd.to_numeric(removed.get("profit_r", pd.Series(dtype=float)), errors="coerce").mean()),
        "kept_avg_r": safe_float(pd.to_numeric(kept.get("profit_r", pd.Series(dtype=float)), errors="coerce").mean()),
    }


def build_candidate_rows(feature_df: pd.DataFrame, tag_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if feature_df.empty or tag_df.empty:
        return pd.DataFrame()
    keys = ["trade_id", "order_key", "payload_key"]
    feature = feature_df.copy()
    for k in keys:
        if k not in feature.columns:
            feature[k] = ""
        if k not in tag_df.columns:
            tag_df[k] = ""
    # Join each tag row to its feature row. Duplicated tag rows are intentional: one row per tag.
    joined = tag_df.merge(feature, on=keys, how="left", suffixes=("_tag", ""))
    if "strategy_id" not in joined.columns and "strategy_id_tag" in joined.columns:
        joined["strategy_id"] = joined["strategy_id_tag"]
    joined["strategy_id"] = joined["strategy_id"].fillna(joined.get("strategy_id_tag", "")).astype(str)
    rows: list[dict[str, Any]] = []
    for strategy_id, sdf in joined.groupby("strategy_id", dropna=False):
        strategy_id = clean_str(strategy_id)
        if not strategy_id:
            continue
        # Build one row per trade per strategy for negative/positive examples.
        trade_base = feature[feature["strategy_id"].astype(str) == strategy_id].copy() if "strategy_id" in feature.columns else feature.copy()
        if trade_base.empty:
            continue
        tag_pairs = sdf[["tag_name", "tag_group"]].drop_duplicates().itertuples(index=False, name=None)
        for tag_name, tag_group in tag_pairs:
            tag_name = clean_str(tag_name)
            tag_group = clean_str(tag_group)
            if not tag_name or tag_group not in {"risk", "execution", "system"}:
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
            for feat in FEATURES:
                if feat not in work.columns:
                    continue
                for thr in feature_thresholds(work[feat], args.max_thresholds_per_feature):
                    for op in ["<=", ">="]:
                        res = evaluate_condition(work, tag_name, tag_group, feat, op, thr)
                        if not res:
                            continue
                        res["strategy_id"] = strategy_id
                        res["condition_type"] = "single"
                        res["condition_text"] = f"{feat} {op} {thr}"
                        if res["tag_precision"] >= args.min_precision and res["tag_recall"] >= args.min_recall and res["removed_trades"] >= args.min_removed_trades and res["kept_trades"] >= args.min_kept_trades:
                            rows.append(res)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.sort_values(["strategy_id", "tag_name", "tag_group", "tag_precision", "tag_recall", "removed_trades"], ascending=[True, True, True, False, False, False])
    return out


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
        conditions = [{"feature": feature, "op": op, "threshold": threshold, "aliases": FEATURE_ALIASES.get(feature, [])}]
        rule = {
            "rule_id": f"GOLD_STRICT7_TAG_RULE_{i:04d}",
            "symbol": "GOLD",
            "strategy_id": clean_str(row.get("strategy_id")),
            "tag_name": clean_str(row.get("tag_name")),
            "tag_group": clean_str(row.get("tag_group")),
            "severity": "WATCH",
            "action": "WARN",
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
            "source": "gold_strict_7_ai_review_feature_snapshot_tags",
            "note": "Deterministic numeric approximation of historical strict-7 AI-review tag; no AI call at notification time.",
        }
        rules.append(rule)
        flat = {k: v for k, v in rule.items() if k != "conditions"}
        flat["conditions_json"] = json.dumps(conditions, ensure_ascii=False, default=str)
        summary_rows.append(flat)
    return rules, pd.DataFrame(summary_rows)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GOLD strict 7 AI-tag numeric rules JSON.")
    p.add_argument("--ai-review-dir", type=Path, default=DEFAULT_AI_REVIEW_DIR)
    p.add_argument("--feature-snapshot-csv", type=Path, default=None)
    p.add_argument("--ai-review-jsonl", type=Path, default=None)
    p.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    p.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    p.add_argument("--allow-non-strict7-strategy-rules", action="store_true", help="Emergency override. Default behavior filters feature rows to the seven GOLD strict-7 strategy IDs and refuses sources with no strict7 rows.")
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
    allowed_strategy_ids = strict7_strategy_ids()
    ai_dir = resolve(args.ai_review_dir)
    feature_csv = resolve(args.feature_snapshot_csv) if args.feature_snapshot_csv else ai_dir / "trade_feature_snapshot.csv"
    review_jsonl = resolve(args.ai_review_jsonl) if args.ai_review_jsonl else ai_dir / "trade_ai_review_ledger.jsonl"
    output_json = resolve(args.output_json)
    output_csv = resolve(args.output_csv)
    if not feature_csv.exists():
        raise SystemExit(f"feature snapshot CSV not found: {feature_csv}. Run GOLD strict-7 post-trade/backtest AI review pipeline first.")
    if not review_jsonl.exists():
        raise SystemExit(f"AI review JSONL not found: {review_jsonl}. Run GOLD strict-7 post-trade/backtest AI review pipeline first.")
    feature_df_raw = read_csv(feature_csv)
    feature_df, strategy_alignment = filter_feature_rows_to_strict7(
        feature_df_raw,
        allowed_strategy_ids,
        allow_non_strict7_strategy_rules=bool(args.allow_non_strict7_strategy_rules),
    )
    review_rows = read_jsonl(review_jsonl)
    tag_df = explode_review_tags(review_rows)
    tag_strategy_ids_raw = unique_clean_values(tag_df, "strategy_id") if not tag_df.empty else []
    candidates = build_candidate_rows(feature_df, tag_df, args)
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
        "candidate_strategy_ids": unique_clean_values(candidates, "strategy_id") if not candidates.empty else [],
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
            "candidate_rows": int(len(candidates)),
            "rules_count": int(len(rules)),
        },
        "rules_count": int(len(rules)),
        "rules": rules,
        "safety": {"ai_called": False, "mt5_calls": False, "order_send": False, "discord_send": False},
    }
    write_json(output_json, obj)
    write_csv(summary_df, output_csv)
    print(json.dumps({
        "cycle_ok": True,
        "rules_count": len(rules),
        "rule_strategy_ids": rule_strategy_ids,
        "filtered_out_feature_rows": strategy_alignment.get("filtered_out_feature_rows", 0),
        "input_ai_review_dir": str(ai_dir),
        "output_json": str(output_json),
        "output_csv": str(output_csv),
        "candidate_rows": int(len(candidates)),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())