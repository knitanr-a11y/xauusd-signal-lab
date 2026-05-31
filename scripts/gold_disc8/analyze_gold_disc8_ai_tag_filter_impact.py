#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Analyze DISC8 AI-tag filter impact.

This script does NOT call OpenAI, MT5, or Discord.

Purpose:
- Use existing DISC8 AI reviews and deterministic outcome sample.
- Simulate excluding trades that received suspect AI tags.
- Measure exact impact on trade count, monthly average, win rate, avg R, total R, PF.
- Detect whether filtering improves quality but reduces trade count too much.

Inputs default to data/gold_disc8 paths:
- disc8_review_trade_outcome_sample.csv
- trade_ai_review_ledger.jsonl
- trade_ai_tag_summary.csv

Outputs:
- disc8_ai_tag_filter_strategy_tag_individual_impact.csv
- disc8_ai_tag_filter_scenarios.csv
- disc8_ai_tag_filter_monthly_counts.csv
- disc8_ai_tag_filter_strategy_counts.csv
- disc8_ai_tag_filter_greedy_path.csv
- disc8_ai_tag_filter_excluded_trades.csv
- disc8_ai_tag_filter_impact_summary.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "gold_disc8" / "verification" / "ai_review_data_driven" / "disc8_ai_review"
DEFAULT_OUTCOME_CSV = DEFAULT_OUT_DIR / "disc8_review_trade_outcome_sample.csv"
DEFAULT_REVIEW_JSONL = DEFAULT_OUT_DIR / "trade_ai_review_ledger.jsonl"
DEFAULT_TAG_SUMMARY_CSV = DEFAULT_OUT_DIR / "trade_ai_tag_summary.csv"
DEFAULT_OUTPUT_DIR = DEFAULT_OUT_DIR / "tag_filter_impact"

NON_INFORMATIVE_TAGS = {
    "",
    "-",
    "none",
    "null",
    "n/a",
    "na",
    "unknown",
    "unclear",
    "no_clear_positive_tag",
    "no_positive_tag",
    "no_risk_tag",
    "no_clear_risk_tag",
}


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(wpath(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(wpath(path), index=False, encoding="utf-8-sig")


def write_json(obj: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSONL not found: {path}")
    rows: list[dict[str, Any]] = []
    with open(wpath(path), "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception as exc:
                raise RuntimeError(f"Invalid JSONL at {path}:{line_no}: {exc!r}") from exc
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    s = str(value).strip()
    return s if s else default


def canonical_tag(value: Any) -> str:
    return clean(value).strip().lower().replace(" ", "_").replace("-", "_")


def tag_is_informative(tag: str) -> bool:
    return canonical_tag(tag) not in NON_INFORMATIVE_TAGS


def as_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def is_win(outcome: Any, profit_r: Any) -> bool:
    text = clean(outcome).upper()
    if text in {"WIN", "SMALL_WIN"}:
        return True
    if text in {"LOSS", "SMALL_LOSS", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return False
    r = as_float(profit_r)
    return bool(r is not None and r > 0)


def is_loss(outcome: Any, profit_r: Any) -> bool:
    text = clean(outcome).upper()
    if text in {"LOSS", "SMALL_LOSS"}:
        return True
    if text in {"WIN", "SMALL_WIN", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return False
    r = as_float(profit_r)
    return bool(r is not None and r < 0)


def profit_factor(values: list[float]) -> float | None:
    pos = sum(v for v in values if v > 0)
    neg = abs(sum(v for v in values if v < 0))
    if neg <= 1e-12:
        return None if pos <= 1e-12 else float("inf")
    return pos / neg


def safe_pf_text(pf: float | None) -> str:
    if pf is None:
        return ""
    if math.isinf(pf):
        return "INF"
    return f"{pf:.6f}"


def add_trade_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "trade_id" not in out.columns:
        raise RuntimeError("outcome CSV must contain trade_id. Run payload audit pipeline first.")
    if "strategy_id" not in out.columns:
        if "candidate_id" in out.columns:
            out["strategy_id"] = out["candidate_id"].astype(str)
        else:
            raise RuntimeError("outcome CSV must contain strategy_id or candidate_id")
    if "strategy_key" not in out.columns:
        out["strategy_key"] = out["strategy_id"].astype(str)
    if "symbol" not in out.columns:
        out["symbol"] = "GOLD"
    if "profit_r" not in out.columns:
        raise RuntimeError("outcome CSV must contain profit_r")
    if "outcome" not in out.columns:
        raise RuntimeError("outcome CSV must contain outcome")
    if "entry_time" not in out.columns:
        raise RuntimeError("outcome CSV must contain entry_time")
    out["trade_id"] = out["trade_id"].astype(str)
    out["strategy_id"] = out["strategy_id"].astype(str)
    out["profit_r_num"] = pd.to_numeric(out["profit_r"], errors="coerce").fillna(0.0)
    out["entry_time_dt"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["entry_month"] = out["entry_time_dt"].dt.strftime("%Y-%m")
    out["is_win"] = [is_win(o, r) for o, r in zip(out["outcome"], out["profit_r_num"])]
    out["is_loss"] = [is_loss(o, r) for o, r in zip(out["outcome"], out["profit_r_num"])]
    return out


def metrics(df: pd.DataFrame, *, all_months: list[str] | None = None) -> dict[str, Any]:
    n = int(len(df))
    wins = int(df["is_win"].sum()) if "is_win" in df.columns else 0
    losses = int(df["is_loss"].sum()) if "is_loss" in df.columns else 0
    values = pd.to_numeric(df.get("profit_r_num", pd.Series(dtype=float)), errors="coerce").fillna(0.0).astype(float).tolist()
    months = sorted([m for m in df.get("entry_month", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if m])
    month_denominator = len(all_months) if all_months is not None and len(all_months) > 0 else len(months)
    return {
        "trade_count": n,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": None if n == 0 else wins / n,
        "avg_r": None if n == 0 else sum(values) / n,
        "total_r": sum(values),
        "profit_factor": profit_factor(values),
        "active_months": int(len(months)),
        "month_denominator": int(month_denominator),
        "avg_trades_per_active_month": None if len(months) == 0 else n / len(months),
        "avg_trades_per_base_month": None if month_denominator == 0 else n / month_denominator,
    }


def metric_row(prefix: str, m: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{k}": v for k, v in m.items()}


def pct(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None or abs(float(denom)) <= 1e-12:
        return None
    return float(numer) / float(denom)


def normalize_review_tags(review_rows: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for r in review_rows:
        base = {
            "trade_id": clean(r.get("trade_id")),
            "order_key": clean(r.get("order_key")),
            "payload_key": clean(r.get("payload_key")),
            "symbol": clean(r.get("symbol"), "GOLD"),
            "strategy_id": clean(r.get("strategy_id")),
            "outcome": clean(r.get("outcome")),
            "profit_r": as_float(r.get("profit_r")),
        }
        seen: set[tuple[str, str]] = set()
        for source_key, group in [
            ("possible_risk_tags", "risk"),
            ("possible_positive_tags", "positive"),
            ("execution_issue_tags", "execution"),
            ("system_issue_tags", "system"),
        ]:
            tags = r.get(source_key, [])
            if isinstance(tags, str):
                tags = [x.strip() for x in tags.replace(";", ",").split(",") if x.strip()]
            if not isinstance(tags, list):
                tags = []
            for tag in tags:
                tag_name = canonical_tag(tag)
                if not tag_is_informative(tag_name):
                    continue
                key = (tag_name, group)
                if key in seen:
                    continue
                seen.add(key)
                row = dict(base)
                row.update({"tag_name": tag_name, "tag_group": group, "tag_source_key": source_key})
                rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["trade_id", "strategy_id", "tag_name", "tag_group"])
    out = pd.DataFrame(rows)
    return out.drop_duplicates(subset=["trade_id", "strategy_id", "tag_name", "tag_group"], keep="first")


def get_suspect_candidates(summary_df: pd.DataFrame) -> pd.DataFrame:
    df = summary_df.copy()
    if "should_investigate" not in df.columns:
        raise RuntimeError("tag summary CSV must contain should_investigate")
    mask = df["should_investigate"].astype(str).str.lower().isin({"true", "1", "yes", "y"})
    cand = df[mask].copy()
    if cand.empty:
        return cand
    cand["tag_name"] = cand["tag_name"].map(canonical_tag)
    cand["tag_group"] = cand["tag_group"].map(canonical_tag)
    cand["strategy_id"] = cand["strategy_id"].astype(str)
    for col in ["overall_avg_r_diff", "overall_win_rate_diff", "profit_factor", "trade_count", "avg_r", "win_rate"]:
        if col in cand.columns:
            cand[col] = pd.to_numeric(cand[col], errors="coerce")
    sort_cols = [c for c in ["overall_avg_r_diff", "profit_factor", "overall_win_rate_diff", "trade_count"] if c in cand.columns]
    ascending = [True, True, True, False][: len(sort_cols)]
    if sort_cols:
        cand = cand.sort_values(sort_cols, ascending=ascending, na_position="last", kind="mergesort")
    return cand.reset_index(drop=True)


def trade_ids_for_strategy_tag(tags_df: pd.DataFrame, strategy_id: str, tag_name: str, tag_group: str) -> set[str]:
    if tags_df.empty:
        return set()
    mask = (
        tags_df["strategy_id"].astype(str).eq(str(strategy_id))
        & tags_df["tag_name"].astype(str).eq(str(tag_name))
        & tags_df["tag_group"].astype(str).eq(str(tag_group))
    )
    return set(tags_df.loc[mask, "trade_id"].dropna().astype(str).tolist())


def trade_ids_for_global_tag(tags_df: pd.DataFrame, tag_name: str, tag_group: str) -> set[str]:
    if tags_df.empty:
        return set()
    mask = tags_df["tag_name"].astype(str).eq(str(tag_name)) & tags_df["tag_group"].astype(str).eq(str(tag_group))
    return set(tags_df.loc[mask, "trade_id"].dropna().astype(str).tolist())


def scenario_row(name: str, base_df: pd.DataFrame, kept_df: pd.DataFrame, excluded_ids: set[str], *, all_months: list[str]) -> dict[str, Any]:
    base = metrics(base_df, all_months=all_months)
    after = metrics(kept_df, all_months=all_months)
    excluded = metrics(base_df[base_df["trade_id"].isin(excluded_ids)].copy(), all_months=all_months)
    row: dict[str, Any] = {"scenario": name}
    row.update(metric_row("base", base))
    row.update(metric_row("after", after))
    row.update(metric_row("excluded", excluded))
    row["removed_trades"] = int(base["trade_count"] - after["trade_count"])
    row["remaining_ratio"] = pct(after["trade_count"], base["trade_count"])
    row["trade_count_drop_ratio"] = None if row["remaining_ratio"] is None else 1.0 - row["remaining_ratio"]
    row["win_rate_change"] = None if after["win_rate"] is None or base["win_rate"] is None else after["win_rate"] - base["win_rate"]
    row["avg_r_change"] = None if after["avg_r"] is None or base["avg_r"] is None else after["avg_r"] - base["avg_r"]
    row["total_r_change"] = after["total_r"] - base["total_r"]
    row["pf_change"] = None if after["profit_factor"] is None or base["profit_factor"] is None or math.isinf(after["profit_factor"]) or math.isinf(base["profit_factor"]) else after["profit_factor"] - base["profit_factor"]
    return row


def monthly_counts(scenario: str, df: pd.DataFrame, *, all_months: list[str]) -> pd.DataFrame:
    if df.empty:
        rows = []
    else:
        rows = df.groupby("entry_month", dropna=False).size().reset_index(name="trade_count").to_dict("records")
    present = {clean(r.get("entry_month")): int(r.get("trade_count", 0)) for r in rows}
    out_rows = []
    for month in all_months:
        out_rows.append({"scenario": scenario, "entry_month": month, "trade_count": int(present.get(month, 0))})
    return pd.DataFrame(out_rows)


def strategy_counts(scenario: str, df: pd.DataFrame, *, all_months: list[str]) -> pd.DataFrame:
    rows = []
    for strategy_id, g in df.groupby("strategy_id", dropna=False):
        m = metrics(g, all_months=all_months)
        rows.append({"scenario": scenario, "strategy_id": strategy_id, **m})
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    outcome_df = add_trade_columns(read_csv(args.trade_outcome_csv))
    review_rows = read_jsonl(args.ai_review_jsonl)
    tag_summary = read_csv(args.tag_summary_csv)
    review_tags = normalize_review_tags(review_rows)
    suspects = get_suspect_candidates(tag_summary)

    all_months = sorted([m for m in outcome_df["entry_month"].dropna().astype(str).unique().tolist() if m])
    if not all_months:
        raise RuntimeError("No valid entry_month values in outcome CSV")
    base_metrics = metrics(outcome_df, all_months=all_months)

    # Individual strategy-tag impact.
    individual_rows: list[dict[str, Any]] = []
    candidate_exclusion_map: dict[str, set[str]] = {}
    for idx, cand in suspects.iterrows():
        strategy_id = clean(cand.get("strategy_id"))
        tag_name = canonical_tag(cand.get("tag_name"))
        tag_group = canonical_tag(cand.get("tag_group"))
        candidate_key = f"{strategy_id}::{tag_group}::{tag_name}"
        excluded_ids = trade_ids_for_strategy_tag(review_tags, strategy_id, tag_name, tag_group)
        candidate_exclusion_map[candidate_key] = excluded_ids
        strategy_base = outcome_df[outcome_df["strategy_id"].astype(str).eq(strategy_id)].copy()
        strategy_after = strategy_base[~strategy_base["trade_id"].isin(excluded_ids)].copy()
        global_after = outcome_df[~outcome_df["trade_id"].isin(excluded_ids)].copy()
        row = {
            "candidate_rank": int(idx + 1),
            "candidate_key": candidate_key,
            "strategy_id": strategy_id,
            "tag_name": tag_name,
            "tag_group": tag_group,
            "summary_trade_count": int(cand.get("trade_count", 0) if pd.notna(cand.get("trade_count", 0)) else 0),
            "matched_excluded_trades": int(len(excluded_ids)),
            "summary_win_rate": cand.get("win_rate"),
            "summary_avg_r": cand.get("avg_r"),
            "summary_profit_factor": cand.get("profit_factor"),
            "summary_overall_win_rate_diff": cand.get("overall_win_rate_diff"),
            "summary_overall_avg_r_diff": cand.get("overall_avg_r_diff"),
            "investigation_reason": clean(cand.get("investigation_reason")),
        }
        row.update(metric_row("strategy_base", metrics(strategy_base, all_months=all_months)))
        row.update(metric_row("strategy_after", metrics(strategy_after, all_months=all_months)))
        row.update(metric_row("global_after", metrics(global_after, all_months=all_months)))
        row["strategy_removed_trades"] = int(len(strategy_base) - len(strategy_after))
        row["strategy_remaining_ratio"] = pct(len(strategy_after), len(strategy_base))
        row["strategy_win_rate_change"] = None if row["strategy_after_win_rate"] is None or row["strategy_base_win_rate"] is None else row["strategy_after_win_rate"] - row["strategy_base_win_rate"]
        row["strategy_avg_r_change"] = None if row["strategy_after_avg_r"] is None or row["strategy_base_avg_r"] is None else row["strategy_after_avg_r"] - row["strategy_base_avg_r"]
        row["strategy_total_r_change"] = row["strategy_after_total_r"] - row["strategy_base_total_r"]
        individual_rows.append(row)
    individual_df = pd.DataFrame(individual_rows)

    # Scenario: apply all strategy-specific suspect filters.
    all_strategy_suspect_ids: set[str] = set()
    excluded_detail_rows: list[dict[str, Any]] = []
    for key, ids in candidate_exclusion_map.items():
        strategy_id, tag_group, tag_name = key.split("::", 2)
        all_strategy_suspect_ids.update(ids)
        for trade_id in sorted(ids):
            excluded_detail_rows.append({
                "scenario": "all_strategy_suspect_tags",
                "trade_id": trade_id,
                "strategy_id": strategy_id,
                "tag_group": tag_group,
                "tag_name": tag_name,
            })
    all_strategy_after = outcome_df[~outcome_df["trade_id"].isin(all_strategy_suspect_ids)].copy()

    # Global tag-family scenarios for each unique suspect tag.
    scenario_rows = [scenario_row("base", outcome_df, outcome_df, set(), all_months=all_months)]
    scenario_rows.append(scenario_row("all_strategy_suspect_tags", outcome_df, all_strategy_after, all_strategy_suspect_ids, all_months=all_months))

    global_scenario_ids: dict[str, set[str]] = {}
    unique_global_tags = suspects[["tag_group", "tag_name"]].drop_duplicates().to_dict("records") if not suspects.empty else []
    for item in unique_global_tags:
        tag_group = canonical_tag(item.get("tag_group"))
        tag_name = canonical_tag(item.get("tag_name"))
        scenario = f"global_tag::{tag_group}::{tag_name}"
        ids = trade_ids_for_global_tag(review_tags, tag_name, tag_group)
        global_scenario_ids[scenario] = ids
        kept = outcome_df[~outcome_df["trade_id"].isin(ids)].copy()
        scenario_rows.append(scenario_row(scenario, outcome_df, kept, ids, all_months=all_months))

    # Greedy quality-improvement path with strategy-specific candidate filters.
    greedy_rows: list[dict[str, Any]] = []
    current_ids: set[str] = set()
    current_df = outcome_df.copy()
    current_m = metrics(current_df, all_months=all_months)
    min_remaining_ratio = float(args.min_remaining_ratio)
    min_avg_trades_per_base_month = float(args.min_avg_trades_per_base_month)
    for rank, cand in suspects.iterrows():
        strategy_id = clean(cand.get("strategy_id"))
        tag_name = canonical_tag(cand.get("tag_name"))
        tag_group = canonical_tag(cand.get("tag_group"))
        key = f"{strategy_id}::{tag_group}::{tag_name}"
        ids = set(candidate_exclusion_map.get(key, set()))
        new_ids = current_ids | ids
        test_df = outcome_df[~outcome_df["trade_id"].isin(new_ids)].copy()
        test_m = metrics(test_df, all_months=all_months)
        remaining_ratio = pct(test_m["trade_count"], base_metrics["trade_count"])
        avg_month = test_m.get("avg_trades_per_base_month")
        improves_total_r = test_m["total_r"] > current_m["total_r"]
        improves_avg_r = (test_m["avg_r"] is not None and current_m["avg_r"] is not None and test_m["avg_r"] > current_m["avg_r"])
        improves_pf = False
        if test_m["profit_factor"] is not None and current_m["profit_factor"] is not None and not math.isinf(current_m["profit_factor"]):
            improves_pf = math.isinf(test_m["profit_factor"]) or test_m["profit_factor"] > current_m["profit_factor"]
        passes_trade_floor = (remaining_ratio is not None and remaining_ratio >= min_remaining_ratio) and (avg_month is None or avg_month >= min_avg_trades_per_base_month)
        accept = bool((improves_total_r or improves_avg_r or improves_pf) and passes_trade_floor and len(new_ids - current_ids) > 0)
        greedy_rows.append({
            "step": int(rank + 1),
            "accepted": accept,
            "candidate_key": key,
            "strategy_id": strategy_id,
            "tag_name": tag_name,
            "tag_group": tag_group,
            "newly_excluded_trades": int(len(new_ids - current_ids)),
            "candidate_total_excluded_trades": int(len(ids)),
            "before_trade_count": current_m["trade_count"],
            "after_trade_count_if_added": test_m["trade_count"],
            "remaining_ratio_if_added": remaining_ratio,
            "avg_trades_per_base_month_if_added": avg_month,
            "before_total_r": current_m["total_r"],
            "after_total_r_if_added": test_m["total_r"],
            "before_avg_r": current_m["avg_r"],
            "after_avg_r_if_added": test_m["avg_r"],
            "before_pf": current_m["profit_factor"],
            "after_pf_if_added": test_m["profit_factor"],
            "accept_reason": "accepted" if accept else "rejected_no_quality_improvement_or_trade_floor",
        })
        if accept:
            current_ids = new_ids
            current_df = test_df
            current_m = test_m
    greedy_after = outcome_df[~outcome_df["trade_id"].isin(current_ids)].copy()
    scenario_rows.append(scenario_row("greedy_strategy_suspect_tags", outcome_df, greedy_after, current_ids, all_months=all_months))
    greedy_df = pd.DataFrame(greedy_rows)

    scenarios_df = pd.DataFrame(scenario_rows)
    large_drop_ratio = float(args.large_drop_ratio)
    if not scenarios_df.empty:
        scenarios_df["trade_count_drop_warning"] = scenarios_df["trade_count_drop_ratio"].fillna(0.0) >= large_drop_ratio
        scenarios_df["needs_signal_candidate_increase_check"] = scenarios_df["trade_count_drop_warning"]

    monthly_parts = [monthly_counts("base", outcome_df, all_months=all_months)]
    monthly_parts.append(monthly_counts("all_strategy_suspect_tags", all_strategy_after, all_months=all_months))
    monthly_parts.append(monthly_counts("greedy_strategy_suspect_tags", greedy_after, all_months=all_months))
    for scenario, ids in global_scenario_ids.items():
        monthly_parts.append(monthly_counts(scenario, outcome_df[~outcome_df["trade_id"].isin(ids)].copy(), all_months=all_months))
    monthly_df = pd.concat(monthly_parts, ignore_index=True, sort=False)

    strategy_parts = [strategy_counts("base", outcome_df, all_months=all_months)]
    strategy_parts.append(strategy_counts("all_strategy_suspect_tags", all_strategy_after, all_months=all_months))
    strategy_parts.append(strategy_counts("greedy_strategy_suspect_tags", greedy_after, all_months=all_months))
    strategy_df = pd.concat(strategy_parts, ignore_index=True, sort=False)

    excluded_detail_df = pd.DataFrame(excluded_detail_rows).drop_duplicates() if excluded_detail_rows else pd.DataFrame(columns=["scenario", "trade_id", "strategy_id", "tag_group", "tag_name"])

    outputs = {
        "individual_impact_csv": out_dir / "disc8_ai_tag_filter_strategy_tag_individual_impact.csv",
        "scenarios_csv": out_dir / "disc8_ai_tag_filter_scenarios.csv",
        "monthly_counts_csv": out_dir / "disc8_ai_tag_filter_monthly_counts.csv",
        "strategy_counts_csv": out_dir / "disc8_ai_tag_filter_strategy_counts.csv",
        "greedy_path_csv": out_dir / "disc8_ai_tag_filter_greedy_path.csv",
        "excluded_trades_csv": out_dir / "disc8_ai_tag_filter_excluded_trades.csv",
        "summary_json": out_dir / "disc8_ai_tag_filter_impact_summary.json",
    }
    write_csv(individual_df, outputs["individual_impact_csv"])
    write_csv(scenarios_df, outputs["scenarios_csv"])
    write_csv(monthly_df, outputs["monthly_counts_csv"])
    write_csv(strategy_df, outputs["strategy_counts_csv"])
    write_csv(greedy_df, outputs["greedy_path_csv"])
    write_csv(excluded_detail_df, outputs["excluded_trades_csv"])

    all_suspect_row = scenarios_df[scenarios_df["scenario"].eq("all_strategy_suspect_tags")].iloc[0].to_dict() if not scenarios_df.empty and scenarios_df["scenario"].eq("all_strategy_suspect_tags").any() else {}
    greedy_row = scenarios_df[scenarios_df["scenario"].eq("greedy_strategy_suspect_tags")].iloc[0].to_dict() if not scenarios_df.empty and scenarios_df["scenario"].eq("greedy_strategy_suspect_tags").any() else {}
    summary = {
        "script": "analyze_gold_disc8_ai_tag_filter_impact.py",
        "trade_outcome_csv": str(args.trade_outcome_csv),
        "ai_review_jsonl": str(args.ai_review_jsonl),
        "tag_summary_csv": str(args.tag_summary_csv),
        "output_dir": str(out_dir),
        "inputs": {
            "outcome_rows": int(len(outcome_df)),
            "review_rows": int(len(review_rows)),
            "review_tag_rows": int(len(review_tags)),
            "tag_summary_rows": int(len(tag_summary)),
            "suspect_strategy_tag_rows": int(len(suspects)),
            "base_months": all_months,
        },
        "base_metrics": base_metrics,
        "all_strategy_suspect_tags": all_suspect_row,
        "greedy_strategy_suspect_tags": greedy_row,
        "warnings": {
            "large_drop_ratio_threshold": large_drop_ratio,
            "all_strategy_suspect_tags_large_drop": bool(all_suspect_row.get("trade_count_drop_warning", False)) if all_suspect_row else None,
            "greedy_strategy_suspect_tags_large_drop": bool(greedy_row.get("trade_count_drop_warning", False)) if greedy_row else None,
        },
        "outputs": {k: str(v) for k, v in outputs.items()},
    }
    write_json(summary, outputs["summary_json"])

    print("=" * 80)
    print("GOLD DISC8 AI tag filter impact analysis")
    print("=" * 80)
    print(f"outcome_rows: {len(outcome_df)}")
    print(f"review_rows: {len(review_rows)}")
    print(f"review_tag_rows: {len(review_tags)}")
    print(f"suspect_strategy_tag_rows: {len(suspects)}")
    print(f"base_trade_count: {base_metrics['trade_count']}")
    print(f"base_avg_trades_per_base_month: {base_metrics['avg_trades_per_base_month']}")
    if all_suspect_row:
        print("-- all_strategy_suspect_tags --")
        print(f"after_trade_count: {all_suspect_row.get('after_trade_count')}")
        print(f"removed_trades: {all_suspect_row.get('removed_trades')}")
        print(f"remaining_ratio: {all_suspect_row.get('remaining_ratio')}")
        print(f"after_avg_trades_per_base_month: {all_suspect_row.get('after_avg_trades_per_base_month')}")
        print(f"after_win_rate: {all_suspect_row.get('after_win_rate')}")
        print(f"after_avg_r: {all_suspect_row.get('after_avg_r')}")
        print(f"after_total_r: {all_suspect_row.get('after_total_r')}")
        print(f"after_profit_factor: {safe_pf_text(all_suspect_row.get('after_profit_factor'))}")
        print(f"trade_count_drop_warning: {all_suspect_row.get('trade_count_drop_warning')}")
    if greedy_row:
        print("-- greedy_strategy_suspect_tags --")
        print(f"after_trade_count: {greedy_row.get('after_trade_count')}")
        print(f"removed_trades: {greedy_row.get('removed_trades')}")
        print(f"remaining_ratio: {greedy_row.get('remaining_ratio')}")
        print(f"after_avg_trades_per_base_month: {greedy_row.get('after_avg_trades_per_base_month')}")
        print(f"after_win_rate: {greedy_row.get('after_win_rate')}")
        print(f"after_avg_r: {greedy_row.get('after_avg_r')}")
        print(f"after_total_r: {greedy_row.get('after_total_r')}")
        print(f"after_profit_factor: {safe_pf_text(greedy_row.get('after_profit_factor'))}")
        print(f"trade_count_drop_warning: {greedy_row.get('trade_count_drop_warning')}")
    print("Outputs:")
    for key, path in outputs.items():
        print(f"  {key}: {path}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze exact DISC8 AI-tag filter impact.")
    p.add_argument("--trade-outcome-csv", type=Path, default=DEFAULT_OUTCOME_CSV)
    p.add_argument("--ai-review-jsonl", type=Path, default=DEFAULT_REVIEW_JSONL)
    p.add_argument("--tag-summary-csv", type=Path, default=DEFAULT_TAG_SUMMARY_CSV)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--large-drop-ratio", type=float, default=0.50, help="Warn if a scenario removes this fraction or more of base trades.")
    p.add_argument("--min-remaining-ratio", type=float, default=0.50, help="Greedy path will not accept filters below this remaining ratio.")
    p.add_argument("--min-avg-trades-per-base-month", type=float, default=0.0, help="Greedy path trade-frequency floor.")
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
