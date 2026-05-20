#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Search numeric pre-entry conditions for BTC strict-5 AI tag filters.

This script consumes completed BTC strict-5 backtest AI review outputs and the
feature snapshot CSV.  It does NOT call AI and does NOT change rules.

Goal:
- Take exclusion candidates such as A_FILTER_CANDIDATE from
  btc_strict_5_ai_tag_exclusion_summary.csv.
- Identify the actual trades carrying that AI tag from trade_ai_review_ledger.jsonl.
- Search simple numeric pre-entry predicates that approximate those tagged
  trades, then report whether excluding trades matched by that numeric predicate
  preserves/improves PF, total R, and drawdown.

Examples of searched predicates:
- h4_close_vs_ema20_atr <= X
- h4_close_vs_ema50_atr >= X
- m15_signal_candle_close_pos <= X
- m15_signal_candle_range_atr_ratio >= X
- pairwise AND of the best single predicates

Safety:
- no AI call
- no MT5 call
- no order_send
- no Discord send
- diagnostic only; output is a candidate list, not a rule change
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AI_REVIEW_DIR = Path("data/research_results/btc_strict_5_backtest_ai_review")
DEFAULT_EXCLUSION_DIR = DEFAULT_AI_REVIEW_DIR / "ai_tag_exclusion_diagnostics"
DEFAULT_OUT_DIR = DEFAULT_AI_REVIEW_DIR / "ai_tag_numeric_condition_diagnostics"
SCHEMA_VERSION = "btc_strict_5_ai_tag_numeric_condition_diagnostics_v1"
TAG_KEYS = [
    ("possible_risk_tags", "risk"),
    ("possible_positive_tags", "positive"),
    ("execution_issue_tags", "execution"),
    ("system_issue_tags", "system"),
]
NON_INFORMATIVE_TAGS = {
    "", "-", "none", "null", "n/a", "na", "unknown", "unclear",
    "no_clear_positive_tag", "no_positive_tag", "no_risk_tag", "no_clear_risk_tag",
}
DEFAULT_FEATURES = [
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


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def resolve_optional(value: str, fallback: Path) -> Path:
    text = str(value or "").strip()
    return resolve_repo_path(text) if text else resolve_repo_path(fallback)


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_csv_auto(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.is_dir():
        raise IsADirectoryError(f"CSV path is a directory: {p}")
    return pd.read_csv(windows_long_path(p), encoding="utf-8-sig", sep=None, engine="python")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError(f"Invalid JSON object at {path}:{line_no}")
            rows.append(obj)
    return rows


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


def canonical_tag_name(value: Any) -> str:
    return clean_str(value).strip().lower().replace(" ", "_").replace("-", "_")


def is_informative_tag(value: Any) -> bool:
    return canonical_tag_name(value) not in NON_INFORMATIVE_TAGS


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [canonical_tag_name(v) for v in value if is_informative_tag(v)]
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                obj = json.loads(text)
                if isinstance(obj, list):
                    return normalize_list(obj)
            except Exception:
                pass
        return [canonical_tag_name(v) for v in text.replace(";", ",").split(",") if is_informative_tag(v)]
    return [canonical_tag_name(value)] if is_informative_tag(value) else []


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def review_trade_id(row: dict[str, Any]) -> str:
    for key in ["trade_id", "order_key", "payload_key"]:
        text = clean_str(row.get(key))
        if text:
            return text
    return ""


def build_trade_tag_table(ai_review_jsonl: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for review in read_jsonl(ai_review_jsonl):
        trade_id = review_trade_id(review)
        strategy_id = clean_str(review.get("strategy_id"))
        for key, group in TAG_KEYS:
            for tag in normalize_list(review.get(key)):
                rows.append({
                    "trade_id": trade_id,
                    "strategy_id": strategy_id,
                    "tag_name": tag,
                    "tag_group": group,
                    "review_key": key,
                })
    if not rows:
        return pd.DataFrame(columns=["trade_id", "strategy_id", "tag_name", "tag_group", "review_key"])
    return pd.DataFrame(rows).drop_duplicates(["trade_id", "strategy_id", "tag_name", "tag_group"])


def profit_factor(values: pd.Series | np.ndarray | list[float]) -> float:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").dropna().astype(float).to_numpy()
    if len(arr) == 0:
        return 0.0
    pos = float(arr[arr > 0].sum())
    neg_abs = float(-arr[arr < 0].sum())
    if neg_abs <= 1e-12:
        return math.inf if pos > 0 else 0.0
    return pos / neg_abs


def max_drawdown(values: pd.Series | np.ndarray | list[float]) -> float:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").dropna().astype(float).to_numpy()
    if len(arr) == 0:
        return 0.0
    eq = np.r_[0.0, np.cumsum(arr)]
    dd = np.maximum.accumulate(eq) - eq
    return float(dd.max())


def max_losing_streak(values: pd.Series | np.ndarray | list[float]) -> int:
    arr = pd.to_numeric(pd.Series(values), errors="coerce").dropna().astype(float).to_numpy()
    best = cur = 0
    for value in arr:
        if value < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def perf(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "total_r": 0.0, "avg_r": 0.0, "pf": 0.0, "max_dd_r": 0.0, "max_losing_streak": 0}
    r = pd.to_numeric(df["profit_r"], errors="coerce").dropna()
    return {
        "trades": int(len(r)),
        "wins": int((r > 0).sum()),
        "losses": int((r < 0).sum()),
        "win_rate": float((r > 0).mean()) if len(r) else 0.0,
        "total_r": float(r.sum()) if len(r) else 0.0,
        "avg_r": float(r.mean()) if len(r) else 0.0,
        "pf": float(profit_factor(r)),
        "max_dd_r": float(max_drawdown(r)),
        "max_losing_streak": int(max_losing_streak(r)),
    }


def grade_condition(base_perf: dict[str, Any], kept_perf: dict[str, Any], *, precision: float, recall: float, min_precision: float, min_recall: float) -> str:
    if precision < min_precision or recall < min_recall:
        return "D_WEAK_TAG_REPRODUCTION"
    if kept_perf["pf"] >= base_perf["pf"] and kept_perf["total_r"] >= base_perf["total_r"] and kept_perf["max_dd_r"] <= base_perf["max_dd_r"]:
        return "A_NUMERIC_FILTER_CANDIDATE"
    if kept_perf["pf"] >= base_perf["pf"] and kept_perf["max_dd_r"] <= base_perf["max_dd_r"]:
        return "B_WATCH_PF_DD_IMPROVES_TOTAL_R_DROPS"
    if kept_perf["pf"] >= 2.0 and kept_perf["max_dd_r"] < base_perf["max_dd_r"]:
        return "C_WATCH_DD_IMPROVES"
    return "D_DO_NOT_FILTER"


def thresholds_for(series: pd.Series, target_series: pd.Series, max_thresholds: int) -> list[float]:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    tgt = pd.to_numeric(target_series, errors="coerce").dropna()
    if vals.empty:
        return []
    qs = np.linspace(0.05, 0.95, 19)
    thresholds = set(float(x) for x in vals.quantile(qs).dropna().tolist())
    if not tgt.empty:
        thresholds.update(float(x) for x in tgt.quantile(qs).dropna().tolist())
    thresholds.update(float(x) for x in vals.dropna().unique().tolist()[: max_thresholds * 2] if np.isfinite(x))
    out = sorted(x for x in thresholds if np.isfinite(x))
    if len(out) > max_thresholds:
        idx = np.linspace(0, len(out) - 1, max_thresholds).round().astype(int)
        out = [out[i] for i in sorted(set(idx.tolist()))]
    return out


def condition_mask(df: pd.DataFrame, feature: str, op: str, threshold: float) -> pd.Series:
    s = pd.to_numeric(df[feature], errors="coerce")
    if op == "<=":
        return (s <= threshold).fillna(False)
    if op == ">=":
        return (s >= threshold).fillna(False)
    raise ValueError(f"unsupported op: {op}")


def evaluate_mask(
    base: pd.DataFrame,
    target_ids: set[str],
    mask: pd.Series,
    *,
    strategy_id: str,
    tag_name: str,
    tag_group: str,
    condition_text: str,
    condition_type: str,
    min_removed: int,
    min_kept: int,
    min_precision: float,
    min_recall: float,
) -> dict[str, Any] | None:
    pred = mask.fillna(False)
    removed = base[pred].copy()
    kept = base[~pred].copy()
    if len(removed) < min_removed or len(kept) < min_kept:
        return None
    target_mask = base["trade_id"].astype(str).isin(target_ids)
    tp = int((pred & target_mask).sum())
    fp = int((pred & ~target_mask).sum())
    fn = int((~pred & target_mask).sum())
    target_count = int(target_mask.sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / target_count if target_count else 0.0
    base_perf = perf(base)
    removed_perf = perf(removed)
    kept_perf = perf(kept)
    grade = grade_condition(base_perf, kept_perf, precision=precision, recall=recall, min_precision=min_precision, min_recall=min_recall)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "strategy_id": strategy_id,
        "tag_name": tag_name,
        "tag_group": tag_group,
        "condition_type": condition_type,
        "condition_text": condition_text,
        "target_tagged_trades": target_count,
        "matched_tagged_trades": tp,
        "matched_untagged_trades": fp,
        "missed_tagged_trades": fn,
        "tag_precision": precision,
        "tag_recall": recall,
        "baseline_trades": base_perf["trades"],
        "baseline_pf": base_perf["pf"],
        "baseline_total_r": base_perf["total_r"],
        "baseline_avg_r": base_perf["avg_r"],
        "baseline_max_dd_r": base_perf["max_dd_r"],
        "baseline_max_losing_streak": base_perf["max_losing_streak"],
        "removed_trades": removed_perf["trades"],
        "removed_pf": removed_perf["pf"],
        "removed_total_r": removed_perf["total_r"],
        "removed_avg_r": removed_perf["avg_r"],
        "kept_trades": kept_perf["trades"],
        "kept_pf": kept_perf["pf"],
        "kept_total_r": kept_perf["total_r"],
        "kept_avg_r": kept_perf["avg_r"],
        "kept_max_dd_r": kept_perf["max_dd_r"],
        "kept_max_losing_streak": kept_perf["max_losing_streak"],
        "pf_delta": kept_perf["pf"] - base_perf["pf"] if math.isfinite(kept_perf["pf"]) and math.isfinite(base_perf["pf"]) else np.nan,
        "total_r_delta": kept_perf["total_r"] - base_perf["total_r"],
        "max_dd_delta": kept_perf["max_dd_r"] - base_perf["max_dd_r"],
        "diagnostic_grade": grade,
        "numeric_filter_candidate": grade.startswith("A_"),
        "watch_candidate": grade.startswith("B_") or grade.startswith("C_"),
        "removed_trade_ids": "|".join(removed["trade_id"].astype(str).tolist()),
    }


def monthly_rows_for_condition(base: pd.DataFrame, mask: pd.Series, row: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    work = base.copy()
    work["entry_month"] = pd.to_datetime(work["entry_time"], errors="coerce").dt.strftime("%Y-%m")
    variants = {
        "baseline": work,
        "removed_by_condition": work[mask.fillna(False)],
        "kept_after_condition": work[~mask.fillna(False)],
    }
    for variant, df in variants.items():
        for month, g in df.groupby("entry_month", dropna=False):
            p = perf(g)
            p.update({
                "strategy_id": row["strategy_id"],
                "tag_name": row["tag_name"],
                "tag_group": row["tag_group"],
                "condition_text": row["condition_text"],
                "condition_type": row["condition_type"],
                "variant": variant,
                "month": clean_str(month, "UNKNOWN"),
            })
            out.append(p)
    return out


def load_focus_candidates(exclusion_summary_csv: Path, focus_grade: str) -> pd.DataFrame:
    df = read_csv_auto(exclusion_summary_csv)
    if df.empty:
        return df
    df["tag_name"] = df["tag_name"].map(canonical_tag_name)
    if focus_grade:
        df = df[df["diagnostic_grade"].astype(str).eq(focus_grade)].copy()
    return df.reset_index(drop=True)


def prepare_joined(trade_outcome_csv: Path, feature_snapshot_csv: Path) -> pd.DataFrame:
    outcomes = read_csv_auto(trade_outcome_csv)
    features = read_csv_auto(feature_snapshot_csv)
    for df in [outcomes, features]:
        if "trade_id" not in df.columns:
            raise ValueError("trade_id column required")
        df["trade_id"] = df["trade_id"].astype(str)
    base_cols = ["trade_id", "strategy_id", "direction", "entry_time", "profit_r", "outcome"]
    keep = [c for c in base_cols if c in outcomes.columns]
    out = outcomes[keep].merge(features, on="trade_id", how="left", suffixes=("", "_feature"))
    if "strategy_id" not in out.columns and "strategy_id_feature" in out.columns:
        out["strategy_id"] = out["strategy_id_feature"]
    out["profit_r"] = pd.to_numeric(out["profit_r"], errors="coerce")
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    return out


def search_for_candidate(
    joined: pd.DataFrame,
    tag_rows: pd.DataFrame,
    cand: pd.Series,
    features: list[str],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strategy_id = clean_str(cand.get("strategy_id"))
    tag_name = canonical_tag_name(cand.get("tag_name"))
    tag_group = clean_str(cand.get("tag_group"))
    base = joined[joined["strategy_id"].astype(str).eq(strategy_id)].copy()
    if base.empty:
        return [], []
    target_ids = set(tag_rows[
        tag_rows["strategy_id"].astype(str).eq(strategy_id)
        & tag_rows["tag_name"].astype(str).eq(tag_name)
        & (tag_rows["tag_group"].astype(str).eq(tag_group) if tag_group else True)
    ]["trade_id"].astype(str).tolist())
    if not target_ids:
        return [], []
    single_rows: list[dict[str, Any]] = []
    mask_cache: dict[str, pd.Series] = {}
    usable_features = [f for f in features if f in base.columns and pd.to_numeric(base[f], errors="coerce").notna().sum() >= args.min_feature_nonnull]
    target_df = base[base["trade_id"].astype(str).isin(target_ids)]
    for feature in usable_features:
        thresholds = thresholds_for(base[feature], target_df[feature], args.max_thresholds_per_feature)
        for threshold in thresholds:
            for op in ["<=", ">="]:
                text = f"{feature} {op} {threshold:.10g}"
                mask = condition_mask(base, feature, op, threshold)
                row = evaluate_mask(
                    base,
                    target_ids,
                    mask,
                    strategy_id=strategy_id,
                    tag_name=tag_name,
                    tag_group=tag_group,
                    condition_text=text,
                    condition_type="single",
                    min_removed=args.min_removed_trades,
                    min_kept=args.min_kept_trades,
                    min_precision=args.min_precision,
                    min_recall=args.min_recall,
                )
                if row is None:
                    continue
                row["feature_1"] = feature
                row["op_1"] = op
                row["threshold_1"] = threshold
                row["feature_2"] = ""
                row["op_2"] = ""
                row["threshold_2"] = ""
                single_rows.append(row)
                mask_cache[text] = mask
    single_rows = sorted(single_rows, key=lambda r: (r["numeric_filter_candidate"], r["watch_candidate"], r["tag_precision"], r["tag_recall"], r["pf_delta"], r["kept_pf"]), reverse=True)
    pair_rows: list[dict[str, Any]] = []
    top_for_pairs = single_rows[: args.top_single_conditions_for_pairs]
    for a, b in itertools.combinations(top_for_pairs, 2):
        if a.get("feature_1") == b.get("feature_1"):
            continue
        text = f"({a['condition_text']}) AND ({b['condition_text']})"
        mask = mask_cache[a["condition_text"]] & mask_cache[b["condition_text"]]
        row = evaluate_mask(
            base,
            target_ids,
            mask,
            strategy_id=strategy_id,
            tag_name=tag_name,
            tag_group=tag_group,
            condition_text=text,
            condition_type="pair_and",
            min_removed=args.min_removed_trades,
            min_kept=args.min_kept_trades,
            min_precision=args.min_precision,
            min_recall=args.min_recall,
        )
        if row is None:
            continue
        row["feature_1"] = a.get("feature_1", "")
        row["op_1"] = a.get("op_1", "")
        row["threshold_1"] = a.get("threshold_1", "")
        row["feature_2"] = b.get("feature_1", "")
        row["op_2"] = b.get("op_1", "")
        row["threshold_2"] = b.get("threshold_1", "")
        pair_rows.append(row)
    all_rows = single_rows + pair_rows
    monthly: list[dict[str, Any]] = []
    selected = [r for r in all_rows if r["numeric_filter_candidate"] or r["watch_candidate"]]
    selected = sorted(selected, key=lambda r: (r["numeric_filter_candidate"], r["tag_precision"], r["tag_recall"], r["pf_delta"], r["kept_pf"]), reverse=True)[: args.monthly_top_n]
    for row in selected:
        if row["condition_type"] == "single":
            mask = condition_mask(base, row["feature_1"], row["op_1"], float(row["threshold_1"]))
        else:
            m1 = condition_mask(base, row["feature_1"], row["op_1"], float(row["threshold_1"]))
            m2 = condition_mask(base, row["feature_2"], row["op_2"], float(row["threshold_2"]))
            mask = m1 & m2
        monthly.extend(monthly_rows_for_condition(base, mask, row))
    return all_rows, monthly


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BTC strict 5 AI tag numeric condition diagnostics.")
    p.add_argument("--ai-review-dir", type=Path, default=DEFAULT_AI_REVIEW_DIR)
    p.add_argument("--exclusion-dir", type=Path, default=DEFAULT_EXCLUSION_DIR)
    p.add_argument("--trade-outcome-csv", default="")
    p.add_argument("--feature-snapshot-csv", default="")
    p.add_argument("--ai-review-jsonl", default="")
    p.add_argument("--exclusion-summary-csv", default="")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--focus-grade", default="A_FILTER_CANDIDATE")
    p.add_argument("--features", default="", help="Comma-separated feature list. Default uses built-in pre-entry compact features.")
    p.add_argument("--max-thresholds-per-feature", type=int, default=45)
    p.add_argument("--top-single-conditions-for-pairs", type=int, default=18)
    p.add_argument("--monthly-top-n", type=int, default=20)
    p.add_argument("--min-feature-nonnull", type=int, default=10)
    p.add_argument("--min-removed-trades", type=int, default=3)
    p.add_argument("--min-kept-trades", type=int, default=10)
    p.add_argument("--min-precision", type=float, default=0.55)
    p.add_argument("--min-recall", type=float, default=0.40)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    ai_dir = resolve_repo_path(args.ai_review_dir)
    exclusion_dir = resolve_repo_path(args.exclusion_dir)
    trade_outcome_csv = resolve_optional(args.trade_outcome_csv, ai_dir / "trade_outcome_ledger.csv")
    feature_snapshot_csv = resolve_optional(args.feature_snapshot_csv, ai_dir / "trade_feature_snapshot.csv")
    ai_review_jsonl = resolve_optional(args.ai_review_jsonl, ai_dir / "trade_ai_review_ledger.jsonl")
    exclusion_summary_csv = resolve_optional(args.exclusion_summary_csv, exclusion_dir / "btc_strict_5_ai_tag_exclusion_summary.csv")
    out_dir = resolve_repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in [trade_outcome_csv, feature_snapshot_csv, ai_review_jsonl, exclusion_summary_csv]:
        if not p.exists():
            raise SystemExit(f"required input not found: {p}")
        if p.is_dir():
            raise SystemExit(f"required input is a directory, not a file: {p}")
    features = [x.strip() for x in args.features.split(",") if x.strip()] if args.features.strip() else list(DEFAULT_FEATURES)
    joined = prepare_joined(trade_outcome_csv, feature_snapshot_csv)
    tag_rows = build_trade_tag_table(ai_review_jsonl)
    focus = load_focus_candidates(exclusion_summary_csv, args.focus_grade)
    all_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    for _, cand in focus.iterrows():
        rows, month = search_for_candidate(joined, tag_rows, cand, features, args)
        all_rows.extend(rows)
        monthly_rows.extend(month)
    summary_df = pd.DataFrame(all_rows)
    monthly_df = pd.DataFrame(monthly_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(
            ["numeric_filter_candidate", "watch_candidate", "tag_precision", "tag_recall", "pf_delta", "kept_pf"],
            ascending=[False, False, False, False, False, False],
        ).reset_index(drop=True)
    selected_df = summary_df[(summary_df["numeric_filter_candidate"] | summary_df["watch_candidate"])] if not summary_df.empty else pd.DataFrame()
    paths = {
        "condition_summary_csv": out_dir / "btc_strict_5_ai_tag_numeric_condition_summary.csv",
        "selected_candidates_csv": out_dir / "btc_strict_5_ai_tag_numeric_condition_selected_candidates.csv",
        "monthly_csv": out_dir / "btc_strict_5_ai_tag_numeric_condition_monthly.csv",
        "diagnostics_json": out_dir / "btc_strict_5_ai_tag_numeric_condition_diagnostics_summary.json",
    }
    write_csv(summary_df, paths["condition_summary_csv"])
    write_csv(selected_df, paths["selected_candidates_csv"])
    write_csv(monthly_df, paths["monthly_csv"])
    grade_counts = summary_df["diagnostic_grade"].value_counts().to_dict() if not summary_df.empty else {}
    diag = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "inputs": {
            "trade_outcome_csv": str(trade_outcome_csv),
            "feature_snapshot_csv": str(feature_snapshot_csv),
            "ai_review_jsonl": str(ai_review_jsonl),
            "exclusion_summary_csv": str(exclusion_summary_csv),
        },
        "outputs": {k: str(v) for k, v in paths.items()},
        "settings": {
            "focus_grade": args.focus_grade,
            "features": features,
            "max_thresholds_per_feature": int(args.max_thresholds_per_feature),
            "top_single_conditions_for_pairs": int(args.top_single_conditions_for_pairs),
            "min_removed_trades": int(args.min_removed_trades),
            "min_kept_trades": int(args.min_kept_trades),
            "min_precision": float(args.min_precision),
            "min_recall": float(args.min_recall),
        },
        "rows": {
            "joined_trades": int(len(joined)),
            "trade_tag_rows": int(len(tag_rows)),
            "focus_candidates": int(len(focus)),
            "condition_summary": int(len(summary_df)),
            "selected_candidates": int(len(selected_df)),
            "monthly_rows": int(len(monthly_df)),
        },
        "grade_counts": grade_counts,
        "safety": {
            "ai_called": False,
            "mt5_calls": False,
            "order_send": False,
            "discord_send": False,
            "runtime_trading_ledger_mutation": False,
            "diagnostic_only": True,
            "ai_tags_are_hypotheses_only": True,
        },
    }
    write_json(paths["diagnostics_json"], diag)
    print(json.dumps(diag, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
