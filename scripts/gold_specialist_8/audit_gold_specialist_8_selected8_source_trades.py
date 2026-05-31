#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Audit GOLD specialist 8 selected_8 source trade ledger before any AI review.

No OpenAI API call. No MT5 order send. No Discord send.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

SELECTED_CSV = Path("data/gold_specialist_8/config/selected_8_strategies.csv")
LEDGER_CSV = Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_ledger.csv")
REVIEW_LEDGER_JSONL = Path("data/gold_specialist_8/verification/ai_review_selected8/trade_ai_review_ledger.jsonl")
OUT_JSON = Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_selected8_source_trade_audit.json")

REQUIRED_SELECTED_COLS = [
    "selected_id",
    "source_file",
    "source_strategy_id",
    "strategy_base",
    "exit_model",
    "direction",
    "jst_hours",
    "weekday_filter",
    "safe_open_excluded",
    "expected_trades",
    "expected_wr",
    "expected_pf",
    "expected_test_pf",
    "notes",
]

REQUIRED_LEDGER_COLS = [
    "source_file",
    "selected_id",
    "source_strategy_id",
    "strategy_id",
    "entry_time",
    "direction",
    "entry_price",
    "tp",
    "sl",
    "outcome",
    "pnl",
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


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    last_error: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(wpath(path), encoding=enc)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"failed to read CSV {path}: {last_error}")


def read_jsonl_count(path: Path) -> int:
    if not path.exists() or path.is_dir():
        return 0
    count = 0
    with open(wpath(path), "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(str(value).strip().replace("%", ""))
    except ValueError:
        return None


def as_int(value: Any) -> int | None:
    f = as_float(value)
    if f is None:
        return None
    return int(round(f))


def normalize_direction(value: Any) -> str:
    return str(value).strip().upper() if value is not None and not pd.isna(value) else ""


def direction_price_anomalies(df: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if df.empty:
        return out
    for i, row in df.iterrows():
        direction = normalize_direction(row.get("direction"))
        entry = as_float(row.get("entry_price"))
        tp = as_float(row.get("tp"))
        sl = as_float(row.get("sl"))
        if entry is None or tp is None or sl is None:
            continue
        bad = False
        reason = ""
        if direction == "BUY" and not (tp > entry and sl < entry):
            bad = True
            reason = "BUY expects tp > entry > sl"
        if direction == "SELL" and not (tp < entry and sl > entry):
            bad = True
            reason = "SELL expects tp < entry < sl"
        if bad:
            out.append({
                "row_index": int(i),
                "source_strategy_id": str(row.get("source_strategy_id", "")),
                "entry_time": str(row.get("entry_time", "")),
                "direction": direction,
                "entry_price": entry,
                "tp": tp,
                "sl": sl,
                "reason": reason,
            })
            if len(out) >= 50:
                break
    return out


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit GOLD specialist 8 selected_8 source trade ledger before AI review.")
    p.add_argument("--selected-csv", type=Path, default=SELECTED_CSV)
    p.add_argument("--ledger-csv", type=Path, default=LEDGER_CSV)
    p.add_argument("--review-ledger-jsonl", type=Path, default=REVIEW_LEDGER_JSONL)
    p.add_argument("--output-json", type=Path, default=OUT_JSON)
    p.add_argument("--require-all-8", action="store_true")
    p.add_argument("--require-count-match", action="store_true")
    p.add_argument("--allow-missing-tp-sl", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    selected = read_csv_if_exists(args.selected_csv)
    ledger = read_csv_if_exists(args.ledger_csv)
    review_ledger_rows = read_jsonl_count(args.review_ledger_jsonl)

    selected_missing_cols = [c for c in REQUIRED_SELECTED_COLS if c not in selected.columns]
    ledger_missing_cols = [c for c in REQUIRED_LEDGER_COLS if c not in ledger.columns]

    selected_ids = selected["source_strategy_id"].astype(str).str.strip().tolist() if "source_strategy_id" in selected.columns else []
    selected_ids_set = set(selected_ids)
    source_ids = set(ledger["source_strategy_id"].astype(str).str.strip().tolist()) if "source_strategy_id" in ledger.columns else set()

    selected_counts = {sid: int((selected["source_strategy_id"].astype(str).str.strip() == sid).sum()) for sid in selected_ids_set} if "source_strategy_id" in selected.columns else {}
    source_counts = {str(k): int(v) for k, v in ledger["source_strategy_id"].astype(str).str.strip().value_counts().to_dict().items()} if "source_strategy_id" in ledger.columns else {}

    expected_by_strategy: dict[str, int | None] = {}
    count_mismatches: list[dict[str, Any]] = []
    if "source_strategy_id" in selected.columns and "expected_trades" in selected.columns:
        for _, row in selected.iterrows():
            sid = str(row.get("source_strategy_id", "")).strip()
            expected = as_int(row.get("expected_trades"))
            expected_by_strategy[sid] = expected
            actual = source_counts.get(sid, 0)
            if expected is not None and actual != expected:
                count_mismatches.append({"source_strategy_id": sid, "expected_trades": expected, "actual_source_rows": actual})

    missing_selected_in_source = sorted([sid for sid in selected_ids_set if source_counts.get(sid, 0) <= 0])
    extra_source_strategies = sorted([sid for sid in source_ids if sid not in selected_ids_set])

    missing_entry_time = int(ledger["entry_time"].isna().sum() + (ledger["entry_time"].astype(str).str.strip() == "").sum()) if "entry_time" in ledger.columns and not ledger.empty else 0
    missing_direction = int(ledger["direction"].isna().sum() + (ledger["direction"].astype(str).str.strip() == "").sum()) if "direction" in ledger.columns and not ledger.empty else 0
    missing_outcome = int(ledger["outcome"].isna().sum() + (ledger["outcome"].astype(str).str.strip() == "").sum()) if "outcome" in ledger.columns and not ledger.empty else 0
    unresolved_count = 0
    if "outcome" in ledger.columns and not ledger.empty:
        unresolved_count = int(ledger["outcome"].astype(str).str.upper().str.contains("UNRESOLVED|PENDING|UNKNOWN|NONE|NAN", regex=True, na=True).sum())

    missing_tp = int(ledger["tp"].isna().sum()) if "tp" in ledger.columns and not ledger.empty else 0
    missing_sl = int(ledger["sl"].isna().sum()) if "sl" in ledger.columns and not ledger.empty else 0
    price_anomalies = direction_price_anomalies(ledger) if not ledger_missing_cols else []

    audit = {
        "selected_csv": str(args.selected_csv),
        "ledger_csv": str(args.ledger_csv),
        "review_ledger_jsonl": str(args.review_ledger_jsonl),
        "selected_exists": args.selected_csv.exists(),
        "ledger_exists": args.ledger_csv.exists(),
        "selected_rows": int(len(selected)),
        "source_rows": int(len(ledger)),
        "group_rows": 0,
        "component_rows": 0,
        "review_ledger_rows": int(review_ledger_rows),
        "ai_api_calls": 0,
        "mt5_order_sends": 0,
        "discord_sends": 0,
        "selected_missing_columns": selected_missing_cols,
        "ledger_missing_columns": ledger_missing_cols,
        "selected_strategy_count": len(selected_ids_set),
        "expected_selected_strategy_count": 8,
        "source_strategy_count": len(source_ids),
        "selected_counts": selected_counts,
        "expected_trades_by_strategy": expected_by_strategy,
        "source_strategy_counts": source_counts,
        "missing_selected_strategy_ids_in_source": missing_selected_in_source,
        "extra_source_strategy_ids": extra_source_strategies,
        "count_mismatches": count_mismatches,
        "missing_entry_time_rows": missing_entry_time,
        "missing_direction_rows": missing_direction,
        "missing_outcome_rows": missing_outcome,
        "unresolved_or_pending_outcome_rows": unresolved_count,
        "missing_tp_rows": missing_tp,
        "missing_sl_rows": missing_sl,
        "direction_price_anomalies_sample": price_anomalies,
    }

    ok = True
    errors = []
    if not args.selected_csv.exists():
        ok = False; errors.append("selected_csv_missing")
    if not args.ledger_csv.exists():
        ok = False; errors.append("ledger_csv_missing")
    if selected_missing_cols:
        ok = False; errors.append("selected_required_columns_missing")
    if ledger_missing_cols:
        ok = False; errors.append("ledger_required_columns_missing")
    if args.require_all_8 and len(selected) != 8:
        ok = False; errors.append("selected_rows_not_8")
    if args.require_all_8 and len(selected_ids_set) != 8:
        ok = False; errors.append("selected_strategy_count_not_8")
    if args.require_all_8 and missing_selected_in_source:
        ok = False; errors.append("selected_strategy_missing_in_source_ledger")
    if extra_source_strategies:
        ok = False; errors.append("source_ledger_contains_non_selected_strategy")
    if args.require_count_match and count_mismatches:
        ok = False; errors.append("expected_trades_count_mismatch")
    if missing_entry_time or missing_direction or missing_outcome:
        ok = False; errors.append("required_trade_fields_missing")
    if not args.allow_missing_tp_sl and (missing_tp or missing_sl):
        ok = False; errors.append("tp_or_sl_missing")
    if price_anomalies:
        ok = False; errors.append("tp_sl_direction_price_anomaly")
    if review_ledger_rows > 0:
        # Existing ledger rows are not modified here, but they must be visible before any future AI run.
        errors.append("review_ledger_already_has_rows_observe_before_ai")

    audit["ok_for_ai_review_later"] = bool(ok)
    audit["errors"] = errors
    write_json(args.output_json, audit)

    print("=" * 80)
    print("GOLD specialist 8 selected_8 source trade audit - NO API")
    print("=" * 80)
    print(f"selected rows      : {audit['selected_rows']}")
    print(f"source rows        : {audit['source_rows']}")
    print(f"group rows         : {audit['group_rows']}")
    print(f"component rows     : {audit['component_rows']}")
    print(f"review ledger rows : {audit['review_ledger_rows']}")
    print(f"AI API calls       : {audit['ai_api_calls']}")
    print(f"selected strategies: {audit['selected_strategy_count']}/{audit['expected_selected_strategy_count']}")
    print("")
    print("source strategy counts:")
    for sid, count in sorted(source_counts.items(), key=lambda kv: kv[0]):
        expected = expected_by_strategy.get(sid)
        suffix = f" expected={expected}" if expected is not None else " expected=<missing>"
        print(f"  {count:6d}  {sid}{suffix}")
    print("")
    if missing_selected_in_source:
        print("MISSING selected strategy_ids in source ledger:")
        for sid in missing_selected_in_source:
            print(f"  - {sid}")
    if count_mismatches:
        print("COUNT MISMATCHES:")
        for item in count_mismatches:
            print(f"  - {item['source_strategy_id']}: expected={item['expected_trades']} actual={item['actual_source_rows']}")
    if errors:
        print("ERRORS / WARNINGS:")
        for err in errors:
            print(f"  - {err}")
    print("")
    print(f"audit json: {args.output_json}")

    if not ok:
        return 8
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
