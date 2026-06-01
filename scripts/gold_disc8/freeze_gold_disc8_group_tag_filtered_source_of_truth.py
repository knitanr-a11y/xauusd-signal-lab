#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Freeze GOLD DISC8 SAFE group-tag-filtered result as source of truth.

This script does NOT call OpenAI, MT5, Discord, or OHLC redetection.

Inputs are already-produced SAFE group tag filter outputs:
- disc8_after_group_tag_filter_trade_ledger.csv
- disc8_after_group_tag_filter_strategy_summary.csv
- disc8_group_tag_filter_audit.json
- disc8_ai_group_tag_filter_rules_20260531.json

Outputs under data/gold_disc8/source_of_truth/group_tag_filtered/:
- selected_disc8_group_tag_filtered_strategies.csv
- group_tag_filtered_source_trade_ledger.csv
- group_tag_filtered_source_trade_audit.json
- group_tag_filtered_monthly_summary.csv
- group_tag_filtered_strategy_summary.csv

These outputs are intended to become the stable input for later notification/live-candidate work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAFE_DIR = REPO_ROOT / "data" / "gold_disc8" / "verification" / "ai_review_data_driven" / "disc8_ai_review" / "group_tag_filter_applied" / "safe"
DEFAULT_RULE_JSON = REPO_ROOT / "data" / "gold_disc8" / "config" / "disc8_ai_group_tag_filter_rules_20260531.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "gold_disc8" / "source_of_truth" / "group_tag_filtered"
EXPECTED_DISC8_IDS = [
    "DISC_01_BUY_TP200_SL100_RR2",
    "DISC_02_BUY_TP80_SL50_RR1p6",
    "DISC_04_BUY_TP150_SL100_RR1p5",
    "DISC_05_BUY_TP80_SL50_RR1p6",
    "DISC_06_SELL_TP80_SL50_RR1p6",
    "DISC_08_BUY_TP200_SL100_RR2",
    "DISC_09_BUY_TP80_SL50_RR1p6",
    "DISC_11_SELL_TP80_SL50_RR1p6",
]


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(wpath(path), "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    r = as_float(profit_r)
    return bool(r is not None and r > 0)


def is_loss(outcome: Any, profit_r: Any) -> bool:
    text = clean(outcome).upper()
    if text in {"LOSS", "SMALL_LOSS"}:
        return True
    r = as_float(profit_r)
    return bool(r is not None and r < 0)


def add_metrics_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "profit_r" not in out.columns:
        raise RuntimeError("trade ledger must contain profit_r")
    if "outcome" not in out.columns:
        raise RuntimeError("trade ledger must contain outcome")
    if "entry_time" not in out.columns:
        raise RuntimeError("trade ledger must contain entry_time")
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


def monthly_summary(df: pd.DataFrame, *, all_months: list[str]) -> pd.DataFrame:
    rows = []
    for month in all_months:
        g = df[df["entry_month"].astype(str).eq(month)].copy()
        rows.append({"entry_month": month, **metrics(g, all_months=[month])})
    return pd.DataFrame(rows)


def strategy_summary(df: pd.DataFrame, *, all_months: list[str]) -> pd.DataFrame:
    rows = []
    for sid, g in df.groupby("strategy_id", dropna=False):
        rows.append({"strategy_id": sid, **metrics(g, all_months=all_months)})
    return pd.DataFrame(rows).sort_values("strategy_id").reset_index(drop=True)


def first_nonempty(df: pd.DataFrame, columns: list[str], default: str = "") -> str:
    for col in columns:
        if col not in df.columns:
            continue
        for value in df[col].tolist():
            text = clean(value)
            if text:
                return text
    return default


def selected_strategy_rows(trades: pd.DataFrame, strategy_metrics: pd.DataFrame, audit: dict[str, Any], rule_json_path: Path) -> pd.DataFrame:
    rows = []
    metric_by_sid = {clean(r.get("strategy_id")): r for _, r in strategy_metrics.iterrows()}
    for sid in sorted(trades["strategy_id"].dropna().astype(str).unique().tolist()):
        g = trades[trades["strategy_id"].astype(str).eq(sid)].copy()
        m = metric_by_sid.get(sid, {})
        row = {
            "selected": True,
            "selection_source": "gold_disc8_safe_group_tag_filter",
            "source_of_truth_version": "gold_disc8_group_tag_filtered_sot_20260531_v1",
            "filter_profile": clean(audit.get("profile"), "safe"),
            "strategy_id": sid,
            "candidate_id": first_nonempty(g, ["candidate_id", "strategy_id"], sid),
            "strategy_key": first_nonempty(g, ["strategy_key", "strategy_id"], sid),
            "strategy_alias": first_nonempty(g, ["strategy_alias", "strategy_id"], sid),
            "condition_id": first_nonempty(g, ["condition_id", "strategy_id"], sid),
            "direction": first_nonempty(g, ["direction"]),
            "exit_model": first_nonempty(g, ["exit_model"]),
            "machine_rule": first_nonempty(g, ["machine_rule"]),
            "notification_title": first_nonempty(g, ["notification_title"]),
            "notification_reason_jp": first_nonempty(g, ["notification_reason_jp"]),
            "rule_json": str(rule_json_path).replace("\\", "/"),
            "block_rule_rows": int(audit.get("blocking_rule_rows", 0)),
            "watch_only_rule_rows": int(audit.get("watch_only_rule_rows", 0)),
            "trade_count": int(m.get("trade_count", len(g))) if not isinstance(m, dict) else int(m.get("trade_count", len(g))),
            "win_count": int(m.get("win_count", int(g["is_win"].sum()))) if not isinstance(m, dict) else int(m.get("win_count", int(g["is_win"].sum()))),
            "loss_count": int(m.get("loss_count", int(g["is_loss"].sum()))) if not isinstance(m, dict) else int(m.get("loss_count", int(g["is_loss"].sum()))),
            "win_rate": m.get("win_rate", None) if not isinstance(m, dict) else m.get("win_rate", None),
            "avg_r": m.get("avg_r", None) if not isinstance(m, dict) else m.get("avg_r", None),
            "total_r": m.get("total_r", None) if not isinstance(m, dict) else m.get("total_r", None),
            "profit_factor": m.get("profit_factor", None) if not isinstance(m, dict) else m.get("profit_factor", None),
            "active_months": int(m.get("active_months", 0)) if not isinstance(m, dict) else int(m.get("active_months", 0)),
            "base_months": int(m.get("base_months", 0)) if not isinstance(m, dict) else int(m.get("base_months", 0)),
            "avg_trades_per_base_month": m.get("avg_trades_per_base_month", None) if not isinstance(m, dict) else m.get("avg_trades_per_base_month", None),
            "selection_reason": "SAFE group-tag filter retained this DISC strategy with positive post-filter stats; source ledger is fixed CSV, no OHLC redetection.",
        }
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    trade_csv = args.safe_dir / "disc8_after_group_tag_filter_trade_ledger.csv"
    strategy_csv = args.safe_dir / "disc8_after_group_tag_filter_strategy_summary.csv"
    audit_json = args.safe_dir / "disc8_group_tag_filter_audit.json"
    monthly_csv = args.safe_dir / "disc8_after_group_tag_filter_monthly_summary.csv"

    for p in [trade_csv, strategy_csv, audit_json, args.rule_json]:
        if not p.exists():
            raise FileNotFoundError(f"Required input not found: {p}")

    raw_trades = read_csv(trade_csv)
    trades = add_metrics_columns(raw_trades)
    input_strategy_summary = read_csv(strategy_csv)
    audit = read_json(audit_json)
    rule_config = read_json(args.rule_json)

    if "strategy_id" not in trades.columns:
        raise RuntimeError("trade ledger must contain strategy_id")
    present_ids = sorted(trades["strategy_id"].dropna().astype(str).unique().tolist())
    missing_ids = [sid for sid in EXPECTED_DISC8_IDS if sid not in present_ids]
    extra_ids = [sid for sid in present_ids if sid not in EXPECTED_DISC8_IDS]
    duplicate_trade_ids = int(trades["trade_id"].duplicated().sum()) if "trade_id" in trades.columns else -1
    all_months = sorted([m for m in trades["entry_month"].dropna().astype(str).unique().tolist() if m])
    recomputed_strategy = strategy_summary(trades, all_months=all_months)
    selected = selected_strategy_rows(trades, input_strategy_summary, audit, args.rule_json)
    monthly = monthly_summary(trades, all_months=all_months)

    # Add immutable source-of-truth markers to the ledger copy.
    ledger = trades.copy()
    ledger.insert(0, "source_of_truth_version", "gold_disc8_group_tag_filtered_sot_20260531_v1")
    ledger.insert(1, "source_of_truth_profile", clean(audit.get("profile"), "safe"))
    ledger.insert(2, "source_of_truth_row_index", range(len(ledger)))
    ledger.insert(3, "source_of_truth_rule_json", str(args.rule_json).replace("\\", "/"))

    outputs = {
        "selected_strategies_csv": out_dir / "selected_disc8_group_tag_filtered_strategies.csv",
        "source_trade_ledger_csv": out_dir / "group_tag_filtered_source_trade_ledger.csv",
        "monthly_summary_csv": out_dir / "group_tag_filtered_monthly_summary.csv",
        "strategy_summary_csv": out_dir / "group_tag_filtered_strategy_summary.csv",
        "audit_json": out_dir / "group_tag_filtered_source_trade_audit.json",
    }
    write_csv(selected, outputs["selected_strategies_csv"])
    write_csv(ledger, outputs["source_trade_ledger_csv"])
    write_csv(monthly, outputs["monthly_summary_csv"])
    write_csv(recomputed_strategy, outputs["strategy_summary_csv"])

    overall = metrics(trades, all_months=all_months)
    audit_out = {
        "script": "freeze_gold_disc8_group_tag_filtered_source_of_truth.py",
        "source_of_truth_version": "gold_disc8_group_tag_filtered_sot_20260531_v1",
        "profile": clean(audit.get("profile"), "safe"),
        "no_ai_api_call": True,
        "no_mt5_order_send": True,
        "no_discord_send": True,
        "no_ohlc_redetection": True,
        "inputs": {
            "safe_trade_csv": str(trade_csv),
            "safe_trade_csv_sha256": sha256_file(trade_csv),
            "safe_strategy_csv": str(strategy_csv),
            "safe_strategy_csv_sha256": sha256_file(strategy_csv),
            "safe_monthly_csv": str(monthly_csv) if monthly_csv.exists() else "",
            "safe_audit_json": str(audit_json),
            "safe_audit_json_sha256": sha256_file(audit_json),
            "rule_json": str(args.rule_json),
            "rule_json_sha256": sha256_file(args.rule_json),
        },
        "outputs": {k: str(v) for k, v in outputs.items()},
        "checks": {
            "expected_strategy_count": 8,
            "selected_strategy_rows": int(len(selected)),
            "present_strategy_ids": present_ids,
            "missing_expected_strategy_ids": missing_ids,
            "extra_strategy_ids": extra_ids,
            "source_trade_rows": int(len(ledger)),
            "duplicate_trade_ids": duplicate_trade_ids,
            "audit_kept_trade_rows": int(audit.get("kept_trade_rows", -1)),
            "audit_blocked_trade_rows": int(audit.get("blocked_trade_rows", -1)),
            "audit_input_trade_rows": int(audit.get("input_trade_rows", -1)),
            "rows_match_safe_audit": int(len(ledger)) == int(audit.get("kept_trade_rows", -999999)),
            "strategy_set_ok": missing_ids == [] and extra_ids == [] and int(len(selected)) == 8,
            "trade_id_unique_ok": duplicate_trade_ids == 0,
            "overall_ok": missing_ids == [] and extra_ids == [] and int(len(selected)) == 8 and duplicate_trade_ids == 0 and int(len(ledger)) == int(audit.get("kept_trade_rows", -999999)),
        },
        "overall_metrics": overall,
        "rule_config_summary": {
            "configured_rule_rows": int(len(rule_config.get("rules", []))) if isinstance(rule_config.get("rules"), list) else None,
            "policy": rule_config.get("policy", {}),
        },
    }
    write_json(audit_out, outputs["audit_json"])

    print("=" * 80)
    print("GOLD DISC8 group-tag-filtered source of truth freeze")
    print("=" * 80)
    print(f"profile: {audit_out['profile']}")
    print(f"selected_strategy_rows: {len(selected)}")
    print(f"source_trade_rows: {len(ledger)}")
    print(f"duplicate_trade_ids: {duplicate_trade_ids}")
    print(f"missing_expected_strategy_ids: {missing_ids}")
    print(f"extra_strategy_ids: {extra_ids}")
    print(f"rows_match_safe_audit: {audit_out['checks']['rows_match_safe_audit']}")
    print(f"overall_ok: {audit_out['checks']['overall_ok']}")
    print("overall_metrics:")
    for key in ["trade_count", "win_count", "loss_count", "win_rate", "avg_r", "total_r", "profit_factor", "avg_trades_per_base_month"]:
        print(f"  {key}: {overall.get(key)}")
    print("Outputs:")
    for key, path in outputs.items():
        print(f"  {key}: {path}")
    return 0 if audit_out["checks"]["overall_ok"] else 2


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze GOLD DISC8 group-tag-filtered SAFE output as source of truth.")
    p.add_argument("--safe-dir", type=Path, default=DEFAULT_SAFE_DIR)
    p.add_argument("--rule-json", type=Path, default=DEFAULT_RULE_JSON)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
