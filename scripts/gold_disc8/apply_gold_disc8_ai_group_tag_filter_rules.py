#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Apply GOLD DISC8 AI group tag filter rules.

This script does NOT call OpenAI, MT5, or Discord.

It applies a fixed strategy-specific AI tag filter rule JSON to:
- disc8_review_trade_outcome_sample.csv
- trade_ai_review_ledger.jsonl

It produces:
- filtered trade ledger
- blocked trade ledger
- watch-only trade ledger
- monthly summary
- strategy summary
- rule hit summary
- audit JSON

Profiles:
- safe: apply only rules with action == "block". positive/watch rules remain watch-only.
- greedy_exact: apply rules with action == "block" plus watch_only positive rules as block, reproducing the greedy path more closely.
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
BASE_OUT_DIR = REPO_ROOT / "data" / "gold_disc8" / "verification" / "ai_review_data_driven" / "disc8_ai_review"
DEFAULT_RULE_JSON = REPO_ROOT / "data" / "gold_disc8" / "config" / "disc8_ai_group_tag_filter_rules_20260531.json"
DEFAULT_TRADE_CSV = BASE_OUT_DIR / "disc8_review_trade_outcome_sample.csv"
DEFAULT_REVIEW_JSONL = BASE_OUT_DIR / "trade_ai_review_ledger.jsonl"
DEFAULT_OUTPUT_DIR = BASE_OUT_DIR / "group_tag_filter_applied"

NON_INFORMATIVE_TAGS = {"", "-", "none", "null", "n/a", "na", "unknown", "unclear", "no_clear_positive_tag", "no_positive_tag", "no_risk_tag", "no_clear_risk_tag"}


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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    with open(wpath(path), "r", encoding="utf-8-sig") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON root must be object: {path}")
    return obj


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


def normalize_review_tags(review_rows: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for r in review_rows:
        base = {
            "trade_id": clean(r.get("trade_id")),
            "order_key": clean(r.get("order_key")),
            "payload_key": clean(r.get("payload_key")),
            "symbol": clean(r.get("symbol"), "GOLD"),
            "strategy_id": clean(r.get("strategy_id")),
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
    return pd.DataFrame(rows).drop_duplicates(subset=["trade_id", "strategy_id", "tag_name", "tag_group"], keep="first")


def add_trade_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "trade_id" not in out.columns:
        raise RuntimeError("trade CSV must contain trade_id")
    if "strategy_id" not in out.columns:
        if "candidate_id" in out.columns:
            out["strategy_id"] = out["candidate_id"].astype(str)
        else:
            raise RuntimeError("trade CSV must contain strategy_id or candidate_id")
    if "strategy_key" not in out.columns:
        out["strategy_key"] = out["strategy_id"].astype(str)
    if "symbol" not in out.columns:
        out["symbol"] = "GOLD"
    if "entry_time" not in out.columns:
        raise RuntimeError("trade CSV must contain entry_time")
    if "outcome" not in out.columns:
        raise RuntimeError("trade CSV must contain outcome")
    if "profit_r" not in out.columns:
        raise RuntimeError("trade CSV must contain profit_r")
    out["trade_id"] = out["trade_id"].astype(str)
    out["strategy_id"] = out["strategy_id"].astype(str)
    out["profit_r_num"] = pd.to_numeric(out["profit_r"], errors="coerce").fillna(0.0)
    out["entry_time_dt"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["entry_month"] = out["entry_time_dt"].dt.strftime("%Y-%m")
    out["is_win"] = [is_win(o, r) for o, r in zip(out["outcome"], out["profit_r_num"])]
    out["is_loss"] = [is_loss(o, r) for o, r in zip(out["outcome"], out["profit_r_num"])]
    return out


def metrics(df: pd.DataFrame, *, all_months: list[str]) -> dict[str, Any]:
    n = int(len(df))
    values = pd.to_numeric(df.get("profit_r_num", pd.Series(dtype=float)), errors="coerce").fillna(0.0).astype(float).tolist()
    wins = int(df.get("is_win", pd.Series(dtype=bool)).sum()) if not df.empty else 0
    losses = int(df.get("is_loss", pd.Series(dtype=bool)).sum()) if not df.empty else 0
    month_count = int(len(all_months))
    return {
        "trade_count": n,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": None if n == 0 else wins / n,
        "avg_r": None if n == 0 else sum(values) / n,
        "total_r": sum(values),
        "profit_factor": profit_factor(values),
        "active_months": int(len([m for m in df.get("entry_month", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if m])) if not df.empty else 0,
        "base_months": month_count,
        "avg_trades_per_base_month": None if month_count == 0 else n / month_count,
    }


def select_active_rules(config: dict[str, Any], *, profile: str) -> pd.DataFrame:
    rows = []
    for r in config.get("rules", []):
        if not isinstance(r, dict) or not r.get("enabled", True):
            continue
        action = clean(r.get("action"), "block")
        if profile == "safe" and action != "block":
            active_action = action
            blocks = False
        elif profile == "greedy_exact" and action in {"block", "watch_only"}:
            active_action = "block"
            blocks = True
        else:
            active_action = action
            blocks = action == "block"
        row = dict(r)
        row["active_action"] = active_action
        row["blocks_trade"] = bool(blocks)
        row["strategy_id"] = clean(row.get("strategy_id"))
        row["tag_group"] = canonical_tag(row.get("tag_group"))
        row["tag_name"] = canonical_tag(row.get("tag_name"))
        rows.append(row)
    return pd.DataFrame(rows)


def build_hits(trades: pd.DataFrame, tags: pd.DataFrame, rules: pd.DataFrame) -> pd.DataFrame:
    hit_rows = []
    if tags.empty or rules.empty:
        return pd.DataFrame()
    tag_key_df = tags[["trade_id", "strategy_id", "tag_group", "tag_name"]].copy()
    for _, rule in rules.iterrows():
        mask = (
            tag_key_df["strategy_id"].astype(str).eq(str(rule["strategy_id"]))
            & tag_key_df["tag_group"].astype(str).eq(str(rule["tag_group"]))
            & tag_key_df["tag_name"].astype(str).eq(str(rule["tag_name"]))
        )
        matched = tag_key_df[mask].copy()
        if matched.empty:
            continue
        for trade_id in matched["trade_id"].dropna().astype(str).unique().tolist():
            hit_rows.append({
                "trade_id": trade_id,
                "strategy_id": rule["strategy_id"],
                "rule_id": clean(rule.get("rule_id")),
                "rule_group": clean(rule.get("rule_group")),
                "tag_group": rule["tag_group"],
                "tag_name": rule["tag_name"],
                "configured_action": clean(rule.get("action")),
                "active_action": clean(rule.get("active_action")),
                "blocks_trade": bool(rule.get("blocks_trade")),
                "source_step": int(rule.get("source_step")) if pd.notna(rule.get("source_step")) else None,
            })
    if not hit_rows:
        return pd.DataFrame()
    hits = pd.DataFrame(hit_rows).drop_duplicates(subset=["trade_id", "rule_id"], keep="first")
    return hits.merge(trades[["trade_id", "entry_time", "entry_month", "outcome", "profit_r_num", "is_win", "is_loss"]], on="trade_id", how="left")


def summarize_by_month(scenario: str, df: pd.DataFrame, all_months: list[str]) -> pd.DataFrame:
    rows = []
    for m in all_months:
        g = df[df["entry_month"].astype(str).eq(m)].copy()
        mm = metrics(g, all_months=[m])
        rows.append({"scenario": scenario, "entry_month": m, **mm})
    return pd.DataFrame(rows)


def summarize_by_strategy(scenario: str, df: pd.DataFrame, all_months: list[str]) -> pd.DataFrame:
    rows = []
    for sid, g in df.groupby("strategy_id", dropna=False):
        rows.append({"scenario": scenario, "strategy_id": sid, **metrics(g, all_months=all_months)})
    return pd.DataFrame(rows)


def summarize_rule_hits(hits: pd.DataFrame) -> pd.DataFrame:
    if hits.empty:
        return pd.DataFrame()
    rows = []
    for keys, g in hits.groupby(["rule_group", "strategy_id", "tag_group", "tag_name", "active_action", "blocks_trade"], dropna=False):
        rule_group, strategy_id, tag_group, tag_name, active_action, blocks_trade = keys
        vals = pd.to_numeric(g["profit_r_num"], errors="coerce").fillna(0.0).tolist()
        rows.append({
            "rule_group": rule_group,
            "strategy_id": strategy_id,
            "tag_group": tag_group,
            "tag_name": tag_name,
            "active_action": active_action,
            "blocks_trade": bool(blocks_trade),
            "hit_trades": int(g["trade_id"].nunique()),
            "hit_wins": int(g["is_win"].sum()),
            "hit_losses": int(g["is_loss"].sum()),
            "hit_win_rate": None if len(g) == 0 else float(g["is_win"].sum()) / float(len(g)),
            "hit_avg_r": None if len(g) == 0 else float(sum(vals)) / float(len(g)),
            "hit_total_r": float(sum(vals)),
            "hit_profit_factor": profit_factor(vals),
        })
    return pd.DataFrame(rows).sort_values(["blocks_trade", "hit_trades", "hit_avg_r"], ascending=[False, False, True], na_position="last")


def main() -> int:
    args = parse_args()
    out_dir = args.output_dir / args.profile
    out_dir.mkdir(parents=True, exist_ok=True)

    config = read_json(args.rule_json)
    trades = add_trade_columns(read_csv(args.trade_csv))
    reviews = read_jsonl(args.review_jsonl)
    tags = normalize_review_tags(reviews)
    rules = select_active_rules(config, profile=args.profile)
    hits = build_hits(trades, tags, rules)

    block_ids = set(hits.loc[hits.get("blocks_trade", pd.Series(dtype=bool)).astype(bool), "trade_id"].astype(str).tolist()) if not hits.empty else set()
    watch_ids = set(hits.loc[~hits.get("blocks_trade", pd.Series(dtype=bool)).astype(bool), "trade_id"].astype(str).tolist()) if not hits.empty else set()

    blocked = trades[trades["trade_id"].isin(block_ids)].copy()
    kept = trades[~trades["trade_id"].isin(block_ids)].copy()
    watch = trades[trades["trade_id"].isin(watch_ids)].copy()
    all_months = sorted([m for m in trades["entry_month"].dropna().astype(str).unique().tolist() if m])

    base_m = metrics(trades, all_months=all_months)
    kept_m = metrics(kept, all_months=all_months)
    blocked_m = metrics(blocked, all_months=all_months)
    watch_m = metrics(watch, all_months=all_months)

    scenario_df = pd.DataFrame([
        {"scenario": "base", **base_m},
        {"scenario": f"after_group_tag_filter__{args.profile}", **kept_m},
        {"scenario": f"blocked_by_group_tag_filter__{args.profile}", **blocked_m},
        {"scenario": f"watch_only_hits__{args.profile}", **watch_m},
    ])

    write_csv(kept, out_dir / "disc8_after_group_tag_filter_trade_ledger.csv")
    write_csv(blocked, out_dir / "disc8_blocked_by_group_tag_filter_trade_ledger.csv")
    write_csv(watch, out_dir / "disc8_watch_only_group_tag_hits_trade_ledger.csv")
    write_csv(hits, out_dir / "disc8_group_tag_filter_rule_hits.csv")
    write_csv(scenario_df, out_dir / "disc8_group_tag_filter_scenarios.csv")
    write_csv(summarize_by_month("base", trades, all_months), out_dir / "disc8_group_tag_filter_base_monthly_summary.csv")
    write_csv(summarize_by_month(f"after_group_tag_filter__{args.profile}", kept, all_months), out_dir / "disc8_after_group_tag_filter_monthly_summary.csv")
    write_csv(summarize_by_strategy("base", trades, all_months), out_dir / "disc8_group_tag_filter_base_strategy_summary.csv")
    write_csv(summarize_by_strategy(f"after_group_tag_filter__{args.profile}", kept, all_months), out_dir / "disc8_after_group_tag_filter_strategy_summary.csv")
    write_csv(summarize_rule_hits(hits), out_dir / "disc8_group_tag_filter_rule_hit_summary.csv")

    audit = {
        "script": "apply_gold_disc8_ai_group_tag_filter_rules.py",
        "profile": args.profile,
        "rule_json": str(args.rule_json),
        "trade_csv": str(args.trade_csv),
        "review_jsonl": str(args.review_jsonl),
        "output_dir": str(out_dir),
        "input_trade_rows": int(len(trades)),
        "input_review_rows": int(len(reviews)),
        "review_tag_rows": int(len(tags)),
        "configured_rule_rows": int(len(config.get("rules", []))),
        "active_rule_rows": int(len(rules)),
        "blocking_rule_rows": int(rules["blocks_trade"].sum()) if "blocks_trade" in rules.columns and not rules.empty else 0,
        "watch_only_rule_rows": int((~rules["blocks_trade"].astype(bool)).sum()) if "blocks_trade" in rules.columns and not rules.empty else 0,
        "rule_hit_rows": int(len(hits)),
        "blocked_trade_rows": int(len(blocked)),
        "kept_trade_rows": int(len(kept)),
        "watch_only_trade_rows": int(len(watch)),
        "base_metrics": base_m,
        "after_filter_metrics": kept_m,
        "blocked_metrics": blocked_m,
        "watch_only_metrics": watch_m,
        "remaining_ratio": None if base_m["trade_count"] == 0 else kept_m["trade_count"] / base_m["trade_count"],
        "removed_ratio": None if base_m["trade_count"] == 0 else blocked_m["trade_count"] / base_m["trade_count"],
    }
    write_json(audit, out_dir / "disc8_group_tag_filter_audit.json")

    print("=" * 80)
    print("GOLD DISC8 group tag filter applied")
    print("=" * 80)
    print(f"profile: {args.profile}")
    print(f"input_trade_rows: {len(trades)}")
    print(f"input_review_rows: {len(reviews)}")
    print(f"active_rule_rows: {len(rules)}")
    print(f"blocking_rule_rows: {audit['blocking_rule_rows']}")
    print(f"watch_only_rule_rows: {audit['watch_only_rule_rows']}")
    print(f"blocked_trade_rows: {len(blocked)}")
    print(f"kept_trade_rows: {len(kept)}")
    print(f"base_win_rate: {base_m['win_rate']}")
    print(f"after_win_rate: {kept_m['win_rate']}")
    print(f"base_profit_factor: {base_m['profit_factor']}")
    print(f"after_profit_factor: {kept_m['profit_factor']}")
    print(f"base_avg_trades_per_base_month: {base_m['avg_trades_per_base_month']}")
    print(f"after_avg_trades_per_base_month: {kept_m['avg_trades_per_base_month']}")
    print(f"output_dir: {out_dir}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply GOLD DISC8 AI group tag filter rules.")
    p.add_argument("--rule-json", type=Path, default=DEFAULT_RULE_JSON)
    p.add_argument("--trade-csv", type=Path, default=DEFAULT_TRADE_CSV)
    p.add_argument("--review-jsonl", type=Path, default=DEFAULT_REVIEW_JSONL)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--profile", choices=["safe", "greedy_exact"], default="safe")
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
