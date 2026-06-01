#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Freeze GOLD DISC8 SAFE group-tag filtered selection.

This script does NOT call OpenAI, MT5, or Discord.

It copies and audits the SAFE profile group-tag-filtered output into
`data/gold_disc8/selected/` as the next source-of-truth layer.

Source inputs:
- group_tag_filter_applied/safe/disc8_after_group_tag_filter_trade_ledger.csv
- group_tag_filter_applied/safe/disc8_blocked_by_group_tag_filter_trade_ledger.csv
- group_tag_filter_applied/safe/disc8_after_group_tag_filter_monthly_summary.csv
- group_tag_filter_applied/safe/disc8_after_group_tag_filter_strategy_summary.csv
- group_tag_filter_applied/safe/disc8_group_tag_filter_rule_hit_summary.csv
- group_tag_filter_applied/safe/disc8_group_tag_filter_audit.json
- data/gold_disc8/config/disc8_ai_group_tag_filter_rules_20260531.json

Outputs:
- selected_disc8_group_tag_filtered_strategies.csv
- group_tag_filtered_source_trade_ledger.csv
- group_tag_filtered_blocked_trade_ledger.csv
- group_tag_filtered_monthly_summary.csv
- group_tag_filtered_strategy_summary.csv
- group_tag_filter_rule_hit_summary.csv
- group_tag_filtered_selection_audit.json
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
SAFE_DIR = REPO_ROOT / "data" / "gold_disc8" / "verification" / "ai_review_data_driven" / "disc8_ai_review" / "group_tag_filter_applied" / "safe"
DEFAULT_RULE_JSON = REPO_ROOT / "data" / "gold_disc8" / "config" / "disc8_ai_group_tag_filter_rules_20260531.json"
DEFAULT_SELECTED_DIR = REPO_ROOT / "data" / "gold_disc8" / "selected"

EXPECTED = {
    "profile": "safe",
    "input_trade_rows": 568,
    "kept_trade_rows": 292,
    "blocked_trade_rows": 276,
    "configured_rule_rows": 21,
    "active_rule_rows": 21,
    "blocking_rule_rows": 18,
    "watch_only_rule_rows": 3,
    "strategy_count": 8,
    "month_count": 6,
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


def num(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def profit_factor(values: list[float]) -> float | None:
    pos = sum(v for v in values if v > 0)
    neg = abs(sum(v for v in values if v < 0))
    if neg <= 1e-12:
        return None if pos <= 1e-12 else float("inf")
    return pos / neg


def is_win(outcome: Any, profit_r: Any) -> bool:
    text = clean(outcome).upper()
    if text in {"WIN", "SMALL_WIN"}:
        return True
    if text in {"LOSS", "SMALL_LOSS", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return False
    r = num(profit_r)
    return bool(r is not None and r > 0)


def is_loss(outcome: Any, profit_r: Any) -> bool:
    text = clean(outcome).upper()
    if text in {"LOSS", "SMALL_LOSS"}:
        return True
    if text in {"WIN", "SMALL_WIN", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return False
    r = num(profit_r)
    return bool(r is not None and r < 0)


def add_common_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "strategy_id" not in out.columns and "candidate_id" in out.columns:
        out["strategy_id"] = out["candidate_id"].astype(str)
    if "strategy_id" not in out.columns:
        raise RuntimeError("trade ledger must contain strategy_id or candidate_id")
    if "trade_id" not in out.columns:
        raise RuntimeError("trade ledger must contain trade_id")
    if "entry_time" not in out.columns:
        raise RuntimeError("trade ledger must contain entry_time")
    if "profit_r" not in out.columns:
        raise RuntimeError("trade ledger must contain profit_r")
    if "outcome" not in out.columns:
        raise RuntimeError("trade ledger must contain outcome")
    out["strategy_id"] = out["strategy_id"].astype(str)
    out["trade_id"] = out["trade_id"].astype(str)
    out["profit_r_num"] = pd.to_numeric(out["profit_r"], errors="coerce").fillna(0.0)
    out["entry_time_dt"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["entry_month"] = out["entry_time_dt"].dt.strftime("%Y-%m")
    out["is_win"] = [is_win(o, r) for o, r in zip(out["outcome"], out["profit_r_num"])]
    out["is_loss"] = [is_loss(o, r) for o, r in zip(out["outcome"], out["profit_r_num"])]
    out["source_of_truth_layer"] = "gold_disc8_group_tag_filtered_safe"
    out["selection_profile"] = "safe"
    out["selection_rule_json"] = "data/gold_disc8/config/disc8_ai_group_tag_filter_rules_20260531.json"
    return out


def metrics(df: pd.DataFrame, *, all_months: list[str]) -> dict[str, Any]:
    vals = pd.to_numeric(df.get("profit_r_num", pd.Series(dtype=float)), errors="coerce").fillna(0.0).astype(float).tolist()
    n = int(len(df))
    wins = int(df.get("is_win", pd.Series(dtype=bool)).sum()) if not df.empty else 0
    losses = int(df.get("is_loss", pd.Series(dtype=bool)).sum()) if not df.empty else 0
    return {
        "trade_count": n,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": None if n == 0 else wins / n,
        "avg_r": None if n == 0 else sum(vals) / n,
        "total_r": float(sum(vals)),
        "profit_factor": profit_factor(vals),
        "active_months": int(len([m for m in df.get("entry_month", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if m])),
        "base_months": int(len(all_months)),
        "avg_trades_per_base_month": None if not all_months else n / len(all_months),
    }


def build_strategy_summary(source: pd.DataFrame, strategy_summary_in: pd.DataFrame, *, all_months: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for sid, g in source.groupby("strategy_id", dropna=False):
        m = metrics(g, all_months=all_months)
        row = {
            "strategy_id": clean(sid),
            "selected": True,
            "selection_profile": "safe",
            "source_of_truth_layer": "gold_disc8_group_tag_filtered_safe",
            "rule_json": "data/gold_disc8/config/disc8_ai_group_tag_filter_rules_20260531.json",
            **m,
        }
        # Carry through useful original strategy summary columns when available.
        if not strategy_summary_in.empty and "strategy_id" in strategy_summary_in.columns:
            hit = strategy_summary_in[strategy_summary_in["strategy_id"].astype(str).eq(str(sid))]
            if not hit.empty:
                for col in strategy_summary_in.columns:
                    if col in row or col == "scenario":
                        continue
                    row[f"summary_{col}"] = hit.iloc[0].get(col)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["profit_factor", "total_r", "trade_count"], ascending=[False, False, False], na_position="last")
    return out


def build_monthly_summary(source: pd.DataFrame, *, all_months: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for month in all_months:
        g = source[source["entry_month"].astype(str).eq(month)].copy()
        rows.append({"entry_month": month, "selection_profile": "safe", **metrics(g, all_months=[month])})
    return pd.DataFrame(rows)


def assert_equal(name: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if actual != expected:
        errors.append(f"{name}: expected={expected!r} actual={actual!r}")


def main() -> int:
    args = parse_args()
    safe_dir = args.safe_dir
    selected_dir = args.selected_dir
    selected_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "source_trade": safe_dir / "disc8_after_group_tag_filter_trade_ledger.csv",
        "blocked_trade": safe_dir / "disc8_blocked_by_group_tag_filter_trade_ledger.csv",
        "strategy_summary": safe_dir / "disc8_after_group_tag_filter_strategy_summary.csv",
        "monthly_summary": safe_dir / "disc8_after_group_tag_filter_monthly_summary.csv",
        "rule_hit_summary": safe_dir / "disc8_group_tag_filter_rule_hit_summary.csv",
        "safe_audit": safe_dir / "disc8_group_tag_filter_audit.json",
        "rule_json": args.rule_json,
    }

    source_raw = read_csv(paths["source_trade"])
    blocked_raw = read_csv(paths["blocked_trade"])
    strategy_summary_in = read_csv(paths["strategy_summary"])
    monthly_summary_in = read_csv(paths["monthly_summary"])
    rule_hit_summary = read_csv(paths["rule_hit_summary"])
    safe_audit = read_json(paths["safe_audit"])
    rule_json = read_json(paths["rule_json"])

    source = add_common_cols(source_raw)
    blocked = add_common_cols(blocked_raw)
    all_months = sorted([m for m in pd.concat([source["entry_month"], blocked["entry_month"]]).dropna().astype(str).unique().tolist() if m])
    selected_strategy_summary = build_strategy_summary(source, strategy_summary_in, all_months=all_months)
    selected_monthly_summary = build_monthly_summary(source, all_months=all_months)

    outputs = {
        "selected_strategies": selected_dir / "selected_disc8_group_tag_filtered_strategies.csv",
        "source_trade_ledger": selected_dir / "group_tag_filtered_source_trade_ledger.csv",
        "blocked_trade_ledger": selected_dir / "group_tag_filtered_blocked_trade_ledger.csv",
        "monthly_summary": selected_dir / "group_tag_filtered_monthly_summary.csv",
        "strategy_summary": selected_dir / "group_tag_filtered_strategy_summary.csv",
        "rule_hit_summary": selected_dir / "group_tag_filter_rule_hit_summary.csv",
        "audit_json": selected_dir / "group_tag_filtered_selection_audit.json",
    }

    write_csv(selected_strategy_summary, outputs["selected_strategies"])
    write_csv(source, outputs["source_trade_ledger"])
    write_csv(blocked, outputs["blocked_trade_ledger"])
    write_csv(selected_monthly_summary, outputs["monthly_summary"])
    write_csv(selected_strategy_summary, outputs["strategy_summary"])
    write_csv(rule_hit_summary, outputs["rule_hit_summary"])

    errors: list[str] = []
    assert_equal("safe_audit.profile", safe_audit.get("profile"), EXPECTED["profile"], errors)
    for k in ["input_trade_rows", "kept_trade_rows", "blocked_trade_rows", "configured_rule_rows", "active_rule_rows", "blocking_rule_rows", "watch_only_rule_rows"]:
        assert_equal(f"safe_audit.{k}", int(safe_audit.get(k, -1)), int(EXPECTED[k]), errors)
    assert_equal("source_rows", len(source), EXPECTED["kept_trade_rows"], errors)
    assert_equal("blocked_rows", len(blocked), EXPECTED["blocked_trade_rows"], errors)
    assert_equal("strategy_count", int(source["strategy_id"].nunique()), EXPECTED["strategy_count"], errors)
    assert_equal("month_count", len(all_months), EXPECTED["month_count"], errors)
    if "htf_no_future_ok" in source.columns:
        bad = source[~source["htf_no_future_ok"].astype(str).str.lower().isin({"true", "1", "yes"})]
        if len(bad) > 0:
            errors.append(f"htf_no_future_bad_rows={len(bad)}")

    source_m = metrics(source, all_months=all_months)
    blocked_m = metrics(blocked, all_months=all_months)
    audit = {
        "script": "freeze_gold_disc8_group_tag_filtered_selection.py",
        "ok": len(errors) == 0,
        "errors": errors,
        "api_used": False,
        "mt5_order_send_used": False,
        "discord_send_used": False,
        "source_of_truth_layer": "gold_disc8_group_tag_filtered_safe",
        "selection_profile": "safe",
        "input_paths": {k: str(v) for k, v in paths.items()},
        "output_paths": {k: str(v) for k, v in outputs.items()},
        "expected": EXPECTED,
        "actual": {
            "source_rows": int(len(source)),
            "blocked_rows": int(len(blocked)),
            "strategy_count": int(source["strategy_id"].nunique()),
            "strategies": sorted(source["strategy_id"].dropna().astype(str).unique().tolist()),
            "month_count": int(len(all_months)),
            "months": all_months,
        },
        "source_metrics": source_m,
        "blocked_metrics": blocked_m,
        "safe_audit_metrics": safe_audit,
        "rule_json_schema_version": rule_json.get("schema_version"),
        "rule_count": int(len(rule_json.get("rules", []))) if isinstance(rule_json.get("rules"), list) else None,
        "monthly_summary_input_rows": int(len(monthly_summary_in)),
    }
    write_json(audit, outputs["audit_json"])

    print("=" * 80)
    print("GOLD DISC8 group-tag filtered selection freeze")
    print("=" * 80)
    print(f"ok: {audit['ok']}")
    print(f"source_rows: {len(source)}")
    print(f"blocked_rows: {len(blocked)}")
    print(f"strategy_count: {source['strategy_id'].nunique()}")
    print(f"month_count: {len(all_months)}")
    print(f"win_rate: {source_m['win_rate']}")
    print(f"profit_factor: {source_m['profit_factor']}")
    print(f"total_r: {source_m['total_r']}")
    print(f"avg_trades_per_base_month: {source_m['avg_trades_per_base_month']}")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
    print("Outputs:")
    for k, v in outputs.items():
        print(f"  {k}: {v}")
    return 0 if not errors else 1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze GOLD DISC8 SAFE group-tag filtered selection.")
    p.add_argument("--safe-dir", type=Path, default=SAFE_DIR)
    p.add_argument("--rule-json", type=Path, default=DEFAULT_RULE_JSON)
    p.add_argument("--selected-dir", type=Path, default=DEFAULT_SELECTED_DIR)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
