#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply payload_key based notification ledger filtering.

This script does not send Discord messages and does not place orders.
It only answers:
- which notification_eligible rows are new
- which rows are duplicates
- what ledger/state would be updated

Typical validation:
  1st run with --commit-ledger:
    candidates_to_send > 0
    ledger rows are appended

  2nd run with the same input and --commit-ledger:
    candidates_to_send = 0
    duplicate_existing > 0

Design:
- payload_key is the primary duplicate key.
- duplicate rows inside the same input batch are skipped after the first row.
- last_notified_time_by_symbol_pair_direction is written as a state CSV for audit.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

STATUS_NEW = "NEW_NOTIFICATION_CANDIDATE"
STATUS_DUPLICATE_EXISTING = "DUPLICATE_EXISTING_LEDGER"
STATUS_DUPLICATE_IN_BATCH = "DUPLICATE_IN_INPUT_BATCH"
STATUS_NOT_ELIGIBLE = "NOT_NOTIFICATION_ELIGIBLE"
STATUS_INVALID_PAYLOAD_KEY = "INVALID_PAYLOAD_KEY"


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def collect_input_files(input_csv: str | None, input_dir: str | None, pattern: str) -> list[Path]:
    if input_csv:
        return [Path(input_csv)]
    if not input_dir:
        raise SystemExit("Either --input-csv or --input-dir is required")
    return sorted(Path(input_dir).glob(pattern))


def load_inputs(files: list[Path], symbol: str | None = None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in files:
        df = read_csv(path)
        df["source_csv"] = str(path)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True, sort=False)
    if symbol and "symbol" in out.columns:
        out = out[out["symbol"].astype("string").str.upper() == symbol.upper()].copy()
    for col in ["signal_close_time", "entry_time"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    sort_cols = [c for c in ["entry_time", "signal_close_time", "payload_key", "source_csv"] if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols, na_position="last")
    return out.reset_index(drop=True)


def load_existing_ledger(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    df = read_csv(p)
    for col in ["signal_close_time", "entry_time", "ledger_recorded_at_utc"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def existing_payload_keys(ledger: pd.DataFrame) -> set[str]:
    if ledger.empty or "payload_key" not in ledger.columns:
        return set()
    return set(ledger["payload_key"].dropna().astype(str))


def is_truthy(value: Any) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "ok"}


def eligible_mask(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    if "notification_eligible" not in df.columns:
        return pd.Series([True] * len(df), index=df.index)
    return df["notification_eligible"].map(is_truthy).fillna(False).astype(bool)


def classify_rows(df: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["ledger_status"] = pd.Series(dtype="string")
        out["ledger_reject_reason"] = pd.Series(dtype="string")
        return out

    existing = existing_payload_keys(ledger)
    seen_batch: set[str] = set()
    statuses: list[str] = []
    reasons: list[str] = []
    eligible = eligible_mask(out)

    for idx, row in out.iterrows():
        payload_key = row.get("payload_key")
        key = "" if pd.isna(payload_key) else str(payload_key).strip()
        if not key:
            statuses.append(STATUS_INVALID_PAYLOAD_KEY)
            reasons.append("payload_key is missing")
            continue
        if not bool(eligible.loc[idx]):
            statuses.append(STATUS_NOT_ELIGIBLE)
            reasons.append(str(row.get("notification_reject_reason", "not notification eligible")))
            continue
        if key in existing:
            statuses.append(STATUS_DUPLICATE_EXISTING)
            reasons.append("payload_key exists in ledger")
            continue
        if key in seen_batch:
            statuses.append(STATUS_DUPLICATE_IN_BATCH)
            reasons.append("payload_key already appeared in this input batch")
            continue
        seen_batch.add(key)
        statuses.append(STATUS_NEW)
        reasons.append("OK")

    out["ledger_status"] = statuses
    out["ledger_reject_reason"] = reasons
    return out


def build_ledger_append_rows(classified: pd.DataFrame, run_id: str) -> pd.DataFrame:
    if classified.empty:
        return pd.DataFrame()
    new = classified[classified["ledger_status"] == STATUS_NEW].copy()
    if new.empty:
        return pd.DataFrame()
    now = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z")
    cols = [
        "payload_key",
        "symbol",
        "mt5_symbol",
        "pair_name",
        "candidate_rank",
        "direction",
        "signal_close_time",
        "entry_time",
        "entry_price",
        "entry_price_normalized",
        "sl_price",
        "tp_price",
        "risk_status",
        "live_risk_status",
        "btc_live_risk_status",
        "notification_eligible",
        "notification_reject_reason",
        "source_csv",
    ]
    out = pd.DataFrame()
    for col in cols:
        out[col] = new[col] if col in new.columns else pd.NA
    out.insert(0, "ledger_recorded_at_utc", now)
    out.insert(1, "ledger_run_id", run_id)
    out["ledger_status"] = STATUS_NEW
    return out.reset_index(drop=True)


def append_ledger(ledger_path: str | Path, append_rows: pd.DataFrame) -> pd.DataFrame:
    ledger_path = Path(ledger_path)
    old = load_existing_ledger(ledger_path)
    if append_rows.empty:
        return old
    if old.empty:
        updated = append_rows.copy()
    else:
        all_cols = list(dict.fromkeys(list(old.columns) + list(append_rows.columns)))
        updated = pd.concat([old.reindex(columns=all_cols), append_rows.reindex(columns=all_cols)], ignore_index=True)
    write_csv(updated, ledger_path)
    return updated


def build_state(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame(columns=["symbol", "pair_name", "direction", "last_notified_time"])
    work = ledger.copy()
    for col in ["symbol", "pair_name", "direction"]:
        if col not in work.columns:
            work[col] = pd.NA
    if "entry_time" in work.columns:
        work["entry_time"] = pd.to_datetime(work["entry_time"], errors="coerce")
        time_col = "entry_time"
    elif "signal_close_time" in work.columns:
        work["signal_close_time"] = pd.to_datetime(work["signal_close_time"], errors="coerce")
        time_col = "signal_close_time"
    else:
        work["entry_time"] = pd.NaT
        time_col = "entry_time"
    work = work.dropna(subset=[time_col])
    if work.empty:
        return pd.DataFrame(columns=["symbol", "pair_name", "direction", "last_notified_time"])
    state = (
        work.groupby(["symbol", "pair_name", "direction"], dropna=False)[time_col]
        .max()
        .reset_index()
        .rename(columns={time_col: "last_notified_time"})
    )
    return state.sort_values(["symbol", "pair_name", "direction"]).reset_index(drop=True)


def summary_frame(classified: pd.DataFrame, ledger_append: pd.DataFrame, committed: bool, ledger_path: Path) -> pd.DataFrame:
    total = int(len(classified))
    counts = classified["ledger_status"].value_counts().to_dict() if "ledger_status" in classified.columns else {}
    return pd.DataFrame([
        {
            "run_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rows_in": total,
            "new_candidates": int(counts.get(STATUS_NEW, 0)),
            "duplicate_existing": int(counts.get(STATUS_DUPLICATE_EXISTING, 0)),
            "duplicate_in_batch": int(counts.get(STATUS_DUPLICATE_IN_BATCH, 0)),
            "not_eligible": int(counts.get(STATUS_NOT_ELIGIBLE, 0)),
            "invalid_payload_key": int(counts.get(STATUS_INVALID_PAYLOAD_KEY, 0)),
            "ledger_append_rows": int(len(ledger_append)),
            "commit_ledger": bool(committed),
            "ledger_csv": str(ledger_path),
        }
    ])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply Mochipoyo notification ledger duplicate filtering.")
    p.add_argument("--input-csv", default=None)
    p.add_argument("--input-dir", default=None)
    p.add_argument("--pattern", default="minimal_candidates_notification_ok_gold_*.csv")
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--ledger-csv", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--commit-ledger", action="store_true")
    p.add_argument("--run-id", default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = Path(args.ledger_csv)
    run_id = args.run_id or pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    input_files = collect_input_files(args.input_csv, args.input_dir, args.pattern)
    source = load_inputs(input_files, symbol=args.symbol)
    ledger_before = load_existing_ledger(ledger_path)
    classified = classify_rows(source, ledger_before)
    ledger_append = build_ledger_append_rows(classified, run_id=run_id)

    if args.commit_ledger:
        ledger_after = append_ledger(ledger_path, ledger_append)
    else:
        ledger_after = ledger_before.copy()

    state = build_state(ledger_after)
    summary = summary_frame(classified, ledger_append, bool(args.commit_ledger), ledger_path)

    to_send = classified[classified.get("ledger_status", pd.Series(dtype="string")) == STATUS_NEW].copy()
    skipped = classified[classified.get("ledger_status", pd.Series(dtype="string")) != STATUS_NEW].copy()

    write_csv(classified, out_dir / "notification_ledger_classified.csv")
    write_csv(to_send, out_dir / "notification_ledger_to_send.csv")
    write_csv(skipped, out_dir / "notification_ledger_skipped.csv")
    write_csv(ledger_append, out_dir / "notification_ledger_append_preview.csv")
    write_csv(state, out_dir / "notification_ledger_state.csv")
    write_csv(summary, out_dir / "notification_ledger_summary.csv")

    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    print(f"ledger_csv: {ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
