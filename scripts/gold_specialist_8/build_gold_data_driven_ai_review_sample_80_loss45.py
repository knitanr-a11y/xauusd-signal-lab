#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build GOLD data-driven DISC8 AI review sample, max 80 rows per signal.

This script is AUDIT-ONLY.
It does NOT call OpenAI, does NOT send Discord, and does NOT send MT5 orders.
It only builds and audits a deterministic AI-review sample from an existing
static_rule_trade_ledger.csv.

Sampling policy:
- target candidate_ids are read from disc8_static_rule_definitions_20260531.json
- max 80 rows per candidate_id
- max 45 loss rows per candidate_id
- max 35 non-loss rows per candidate_id
- max total 640 rows
- deterministic balanced selection by split/month/review_bucket
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULE_JSON = REPO_ROOT / "data" / "gold_specialist_8" / "config" / "disc8_static_rule_definitions_20260531.json"
DEFAULT_TRADE_LEDGER = REPO_ROOT / "data" / "gold_specialist_8" / "verification" / "data_driven_static_rebacktest" / "static_rule_trade_ledger.csv"
DEFAULT_OUT_ROOT = REPO_ROOT / "data" / "gold_specialist_8" / "verification" / "ai_review_data_driven" / "sample_80_loss45"
DEFAULT_LATEST_ROOT = REPO_ROOT / "data" / "gold_specialist_8" / "verification" / "ai_review_data_driven"

MAX_PER_STRATEGY = 80
MAX_LOSS_PER_STRATEGY = 45
MAX_NON_LOSS_PER_STRATEGY = 35
MAX_TOTAL = 640
HELPER_COLUMNS = [
    "__source_row_id",
    "profit_r_num",
    "outcome_upper",
    "entry_time_dt",
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


def write_json(obj: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def load_rules(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"DISC8 rule JSON not found: {path}")
    with open(wpath(path), "r", encoding="utf-8") as f:
        obj = json.load(f)
    rules = obj.get("rules", []) if isinstance(obj, dict) else []
    if not isinstance(rules, list) or not rules:
        raise RuntimeError(f"DISC8 rule JSON has no rules: {path}")
    return rules


def parse_bool_series(s: pd.Series) -> pd.Series:
    """Parse bool-like Series robustly.

    Important: pandas astype(bool) treats non-empty strings such as 'False' as True,
    so do not use astype(bool) for audit columns loaded from CSV.
    """
    if s.dtype == bool:
        return s.fillna(False)
    text = s.astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "t", "yes", "y"})


def classify_review_bucket(row: pd.Series) -> str:
    outcome = str(row.get("outcome", "")).upper()
    profit_r = pd.to_numeric(pd.Series([row.get("profit_r")]), errors="coerce").iloc[0]
    minutes = pd.to_numeric(pd.Series([row.get("minutes_to_close")]), errors="coerce").iloc[0]
    if outcome == "LOSS" or (pd.notna(profit_r) and profit_r < 0):
        if pd.notna(minutes) and minutes <= 15:
            return "LOSS_QUICK_15M"
        if pd.notna(minutes) and minutes <= 60:
            return "LOSS_FAST_60M"
        if pd.notna(minutes) and minutes >= 720:
            return "LOSS_LONG_12H_PLUS"
        return "LOSS_NORMAL"
    if outcome in {"WIN", "SMALL_WIN"} or (pd.notna(profit_r) and profit_r > 0):
        if pd.notna(minutes) and minutes <= 60:
            return "WIN_FAST_60M"
        if pd.notna(minutes) and minutes >= 720:
            return "WIN_LONG_12H_PLUS"
        return "WIN_NORMAL"
    return "NON_LOSS_OTHER"


def ensure_sampling_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "entry_time" not in work.columns:
        raise RuntimeError("trade ledger must contain entry_time")
    if "candidate_id" not in work.columns:
        raise RuntimeError("trade ledger must contain candidate_id")
    if "profit_r" not in work.columns:
        raise RuntimeError("trade ledger must contain profit_r")
    if "outcome" not in work.columns:
        raise RuntimeError("trade ledger must contain outcome")
    work["profit_r_num"] = pd.to_numeric(work["profit_r"], errors="coerce")
    work["outcome_upper"] = work["outcome"].astype(str).str.upper()
    work["entry_time_dt"] = pd.to_datetime(work["entry_time"], errors="coerce")
    if work["entry_time_dt"].isna().all():
        raise RuntimeError("entry_time could not be parsed at all")
    if "entry_month" not in work.columns:
        work["entry_month"] = work["entry_time_dt"].dt.strftime("%Y-%m")
    if "split" not in work.columns:
        work["split"] = "unknown"
    work["review_bucket"] = work.apply(classify_review_bucket, axis=1)
    return work


def balanced_take(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    if df.empty or limit <= 0:
        return df.iloc[0:0].copy()
    work = ensure_sampling_columns(df)
    sort_cols = ["split", "entry_month", "review_bucket", "entry_time_dt", "candidate_id"]
    if "__source_row_id" in work.columns:
        sort_cols.append("__source_row_id")
    work = work.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)

    groups: dict[tuple[str, str, str], list[int]] = {}
    for idx, row in work.iterrows():
        key = (
            str(row.get("split", "unknown")),
            str(row.get("entry_month", "unknown")),
            str(row.get("review_bucket", "unknown")),
        )
        groups.setdefault(key, []).append(int(idx))

    selected_idx: list[int] = []
    keys = sorted(groups.keys())
    pos = {k: 0 for k in keys}
    while len(selected_idx) < limit:
        advanced = False
        for key in keys:
            kpos = pos[key]
            vals = groups[key]
            if kpos < len(vals):
                selected_idx.append(vals[kpos])
                pos[key] = kpos + 1
                advanced = True
                if len(selected_idx) >= limit:
                    break
        if not advanced:
            break
    out = work.loc[selected_idx].copy()
    return out.sort_values(["entry_time_dt", "candidate_id"], kind="mergesort").reset_index(drop=True)


def build_sample(trades: pd.DataFrame, candidate_ids: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[pd.DataFrame] = []
    rejected_parts: list[pd.DataFrame] = []
    work = trades.copy().reset_index(drop=True)
    work["__source_row_id"] = range(len(work))
    work = ensure_sampling_columns(work)
    work["review_sample_policy"] = "max80_loss45_nonloss35"

    for candidate_id in candidate_ids:
        cand = work[work["candidate_id"].astype(str).eq(candidate_id)].copy()
        loss = cand[(cand["outcome_upper"].eq("LOSS")) | (cand["profit_r_num"] < 0)].copy()
        non_loss = cand[~cand["__source_row_id"].isin(loss["__source_row_id"])].copy()

        loss_take = balanced_take(loss, MAX_LOSS_PER_STRATEGY)
        non_loss_take = balanced_take(non_loss, MAX_NON_LOSS_PER_STRATEGY)
        sample = pd.concat([loss_take, non_loss_take], ignore_index=True)
        sample = ensure_sampling_columns(sample) if not sample.empty else sample
        sample = sample.sort_values(["entry_time_dt", "candidate_id"], kind="mergesort").reset_index(drop=True)
        if len(sample) > MAX_PER_STRATEGY:
            sample = sample.head(MAX_PER_STRATEGY).copy()
        sample["ai_review_sample_selected"] = True
        sample["ai_review_sample_reason"] = sample["review_bucket"] if not sample.empty else ""
        rows.append(sample)

        selected_source_ids = set(sample.get("__source_row_id", pd.Series(dtype=int)).astype(int).tolist()) if not sample.empty else set()
        rejected = cand[~cand["__source_row_id"].isin(selected_source_ids)].copy()
        rejected["ai_review_sample_selected"] = False
        rejected["ai_review_sample_reason"] = "NOT_SELECTED_BY_80_LOSS45_POLICY"
        rejected_parts.append(rejected)

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    rejected_out = pd.concat(rejected_parts, ignore_index=True) if rejected_parts else pd.DataFrame()
    for df in [out, rejected_out]:
        if not df.empty:
            df.sort_values(["candidate_id", "entry_time_dt"], kind="mergesort", inplace=True)
            df.drop(columns=HELPER_COLUMNS, errors="ignore", inplace=True)
            df.reset_index(drop=True, inplace=True)
    return out, rejected_out


def is_loss_df(df: pd.DataFrame) -> pd.Series:
    profit = pd.to_numeric(df.get("profit_r"), errors="coerce")
    outcome = df.get("outcome", pd.Series(index=df.index, dtype=str)).astype(str).str.upper()
    return outcome.eq("LOSS") | (profit < 0)


def summarize_strategy(full: pd.DataFrame, sample: pd.DataFrame, candidate_ids: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    full_work = ensure_sampling_columns(full)
    sample_work = ensure_sampling_columns(sample) if not sample.empty else sample.copy()
    for candidate_id in candidate_ids:
        f = full_work[full_work["candidate_id"].astype(str).eq(candidate_id)].copy()
        s = sample_work[sample_work["candidate_id"].astype(str).eq(candidate_id)].copy() if not sample_work.empty else sample_work.copy()
        f_loss = f[is_loss_df(f)]
        s_loss = s[is_loss_df(s)] if not s.empty else s
        if not s.empty:
            entry_dt = pd.to_datetime(s["entry_time"], errors="coerce")
            months = entry_dt.dt.strftime("%Y-%m").nunique()
            earliest = str(entry_dt.min())
            latest = str(entry_dt.max())
        else:
            months = 0
            earliest = ""
            latest = ""
        rows.append({
            "candidate_id": candidate_id,
            "full_trades": int(len(f)),
            "full_losses": int(len(f_loss)),
            "full_non_losses": int(len(f) - len(f_loss)),
            "sample_total": int(len(s)),
            "sample_losses": int(len(s_loss)),
            "sample_non_losses": int(len(s) - len(s_loss)),
            "sample_train_count": int(s.get("split", pd.Series(dtype=str)).astype(str).eq("train").sum()) if not s.empty and "split" in s.columns else 0,
            "sample_test_count": int(s.get("split", pd.Series(dtype=str)).astype(str).eq("test").sum()) if not s.empty and "split" in s.columns else 0,
            "sample_months": int(months),
            "earliest_entry": earliest,
            "latest_entry": latest,
            "ok_sample_total_le_80": bool(len(s) <= MAX_PER_STRATEGY),
            "ok_sample_losses_le_45": bool(len(s_loss) <= MAX_LOSS_PER_STRATEGY),
            "ok_sample_non_losses_le_35": bool((len(s) - len(s_loss)) <= MAX_NON_LOSS_PER_STRATEGY),
        })
    return pd.DataFrame(rows)


def monthly_distribution(sample: pd.DataFrame) -> pd.DataFrame:
    if sample.empty:
        return pd.DataFrame(columns=["candidate_id", "entry_month", "split", "review_bucket", "rows"])
    work = sample.copy()
    if "entry_month" not in work.columns:
        work["entry_month"] = pd.to_datetime(work["entry_time"], errors="coerce").dt.strftime("%Y-%m")
    if "split" not in work.columns:
        work["split"] = "unknown"
    if "review_bucket" not in work.columns:
        work["review_bucket"] = work.apply(classify_review_bucket, axis=1)
    return (
        work.groupby(["candidate_id", "entry_month", "split", "review_bucket"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["candidate_id", "entry_month", "split", "review_bucket"], kind="mergesort")
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build DISC8 AI review sample max80/loss45 without API calls.")
    p.add_argument("--rule-json", type=Path, default=DEFAULT_RULE_JSON)
    p.add_argument("--trade-ledger-csv", type=Path, default=DEFAULT_TRADE_LEDGER)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--latest-root", type=Path, default=DEFAULT_LATEST_ROOT)
    p.add_argument("--allow-missing-candidates", action="store_true", help="Do not fail when DISC8 candidates are missing from the source ledger.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S")
    run_dir = args.out_root / now.strftime("%Y") / now.strftime("%m") / stamp

    rules = load_rules(args.rule_json)
    candidate_ids = [str(r["candidate_id"]) for r in sorted(rules, key=lambda x: int(x.get("selected_order", 999)))]
    trades = read_csv(args.trade_ledger_csv)
    if "candidate_id" not in trades.columns:
        raise RuntimeError("trade ledger must contain candidate_id")

    selected = trades[trades["candidate_id"].astype(str).isin(candidate_ids)].copy()
    present = sorted(selected["candidate_id"].astype(str).unique().tolist())
    missing = [cid for cid in candidate_ids if cid not in set(present)]
    if missing and not args.allow_missing_candidates:
        raise RuntimeError(f"Missing DISC8 candidate_ids in source trade ledger: {missing}")

    if "htf_no_future_ok" in selected.columns:
        htf_ok = parse_bool_series(selected["htf_no_future_ok"])
        future_bad = int((~htf_ok).sum())
        if future_bad > 0:
            raise RuntimeError(f"HTF no-future audit failed: {future_bad} rows have htf_no_future_ok=False")
    else:
        future_bad = None

    sample, rejected = build_sample(selected, candidate_ids)
    if len(sample) > MAX_TOTAL:
        raise RuntimeError(f"sample_total exceeds max_total: {len(sample)} > {MAX_TOTAL}")

    summary = summarize_strategy(selected, sample, candidate_ids)
    if not summary["ok_sample_total_le_80"].all():
        raise RuntimeError("Per-strategy sample_total exceeded 80")
    if not summary["ok_sample_losses_le_45"].all():
        raise RuntimeError("Per-strategy sample_losses exceeded 45")
    if not summary["ok_sample_non_losses_le_35"].all():
        raise RuntimeError("Per-strategy sample_non_losses exceeded 35")

    monthly = monthly_distribution(sample)

    sample_csv = run_dir / "ai_review_sample_80_loss45.csv"
    summary_csv = run_dir / "ai_review_sample_80_loss45_summary_by_strategy.csv"
    monthly_csv = run_dir / "ai_review_sample_80_loss45_monthly_distribution.csv"
    rejected_csv = run_dir / "ai_review_sample_80_loss45_rejected.csv"
    audit_json = run_dir / "ai_review_sample_80_loss45_audit_summary.json"

    write_csv(sample, sample_csv)
    write_csv(summary, summary_csv)
    write_csv(monthly, monthly_csv)
    write_csv(rejected, rejected_csv)

    ok = bool(
        not missing
        and len(sample) <= MAX_TOTAL
        and summary["ok_sample_total_le_80"].all()
        and summary["ok_sample_losses_le_45"].all()
        and summary["ok_sample_non_losses_le_35"].all()
        and (future_bad in (None, 0))
    )
    audit = {
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "api_used": False,
        "mt5_order_send_used": False,
        "discord_send_used": False,
        "rule_json": str(args.rule_json),
        "trade_ledger_csv": str(args.trade_ledger_csv),
        "run_dir": str(run_dir),
        "source_trade_rows": int(len(trades)),
        "selected_source_rows": int(len(selected)),
        "sample_total": int(len(sample)),
        "rejected_rows": int(len(rejected)),
        "max_total": MAX_TOTAL,
        "max_per_strategy": MAX_PER_STRATEGY,
        "max_loss_per_strategy": MAX_LOSS_PER_STRATEGY,
        "max_non_loss_per_strategy": MAX_NON_LOSS_PER_STRATEGY,
        "candidate_ids": candidate_ids,
        "present_candidate_ids": present,
        "missing_candidate_ids": missing,
        "htf_future_bad_rows": future_bad,
        "estimated_api_calls_if_reviewed": int(len(sample)),
        "outputs": {
            "sample_csv": str(sample_csv),
            "summary_by_strategy_csv": str(summary_csv),
            "monthly_distribution_csv": str(monthly_csv),
            "rejected_csv": str(rejected_csv),
            "audit_json": str(audit_json),
        },
        "ok": ok,
    }
    write_json(audit, audit_json)

    args.latest_root.mkdir(parents=True, exist_ok=True)
    latest_map = {
        sample_csv: args.latest_root / "latest_ai_review_sample_80_loss45.csv",
        summary_csv: args.latest_root / "latest_ai_review_sample_80_loss45_summary_by_strategy.csv",
        monthly_csv: args.latest_root / "latest_ai_review_sample_80_loss45_monthly_distribution.csv",
        rejected_csv: args.latest_root / "latest_ai_review_sample_80_loss45_rejected.csv",
        audit_json: args.latest_root / "latest_ai_review_sample_80_loss45_audit_summary.json",
    }
    for src, dst in latest_map.items():
        shutil.copyfile(wpath(src), wpath(dst))
    with open(wpath(args.latest_root / "latest_sample_80_loss45_run_dir.txt"), "w", encoding="utf-8", newline="") as f:
        f.write(str(run_dir))

    print("=" * 80)
    print("GOLD data-driven DISC8 AI review sample 80/loss45 - AUDIT ONLY")
    print("=" * 80)
    print(f"API used                : {audit['api_used']}")
    print(f"source trade rows       : {audit['source_trade_rows']}")
    print(f"selected source rows    : {audit['selected_source_rows']}")
    print(f"sample total            : {audit['sample_total']} / {MAX_TOTAL}")
    print(f"rejected rows           : {audit['rejected_rows']}")
    print(f"estimated API calls     : {audit['estimated_api_calls_if_reviewed']}")
    print(f"HTF future bad rows     : {audit['htf_future_bad_rows']}")
    print("")
    print("Summary by strategy:")
    show_cols = [
        "candidate_id",
        "full_trades",
        "full_losses",
        "full_non_losses",
        "sample_total",
        "sample_losses",
        "sample_non_losses",
        "sample_train_count",
        "sample_test_count",
        "sample_months",
    ]
    print(summary[show_cols].to_string(index=False))
    print("")
    print(f"sample csv : {sample_csv}")
    print(f"summary csv: {summary_csv}")
    print(f"monthly csv: {monthly_csv}")
    print(f"audit json : {audit_json}")
    return 0 if ok else 8


if __name__ == "__main__":
    raise SystemExit(main())
