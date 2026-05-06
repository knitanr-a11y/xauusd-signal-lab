#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate pair-level trigger state for the Mochipoyo minimal live loop.

This script does NOT scan candidates, send Discord messages, or place orders.
It only reads the trigger timeframe CSV for each required pair, compares the
latest confirmed close_time with a persisted state CSV, and decides whether the
pair should be scanned.

Design:
- GOLD_H4_M5_SCALP triggers on M5 close_time updates.
- GOLD_H4_M15_DAYTRADE triggers on M15 close_time updates.
- GOLD_D1_H1_DAYTRADE triggers on H1 close_time updates.
- BTC_H4_M15_DAYTRADE triggers on M15 close_time updates, but can be excluded
  with --symbol GOLD while BTC candidate timing validation is still pending.

Initial state behavior:
- By default, missing state rows are INITIALIZE_ONLY, not SCAN_REQUIRED.
- With --scan-on-initial-state, missing state rows become SCAN_REQUIRED.

Typical validation:
  1st run:
    state missing -> INITIALIZE_ONLY rows, save state

  2nd run:
    same CSV -> SKIPPED_NO_NEW_BAR rows

  3rd run:
    manually edit one state close_time older -> only that pair becomes
    SCAN_REQUIRED
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:
    from scripts.mochipoyo_minimal_config import (
        DEFAULT_ALLOWED_SLICES,
        build_csv_overrides_from_args,
        filter_allowed_slices_for_pair,
        get_pair_config,
        get_required_pair_names,
        normalize_allowed_slices,
        resolve_csv_path,
        validate_allowed_slices_against_pair_configs,
    )
    from scripts.mochipoyo_safe_csv_reader import read_ohlc_csv_safe
except ModuleNotFoundError:
    from mochipoyo_minimal_config import (  # type: ignore
        DEFAULT_ALLOWED_SLICES,
        build_csv_overrides_from_args,
        filter_allowed_slices_for_pair,
        get_pair_config,
        get_required_pair_names,
        normalize_allowed_slices,
        resolve_csv_path,
        validate_allowed_slices_against_pair_configs,
    )
    from mochipoyo_safe_csv_reader import read_ohlc_csv_safe  # type: ignore

STATUS_SCAN_REQUIRED = "SCAN_REQUIRED"
STATUS_SKIPPED_NO_NEW_BAR = "SKIPPED_NO_NEW_BAR"
STATUS_INITIALIZE_ONLY = "INITIALIZE_ONLY"
STATUS_ERROR = "ERROR"


def read_state(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, encoding="utf-8-sig")
    for col in ["last_seen_close_time", "updated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def state_lookup(state: pd.DataFrame) -> dict[str, pd.Series]:
    if state.empty or "pair_name" not in state.columns:
        return {}
    out: dict[str, pd.Series] = {}
    for _, row in state.iterrows():
        pair_name = str(row.get("pair_name", "")).strip().upper()
        if pair_name:
            out[pair_name] = row
    return out


def allowed_for_symbol(symbol: str | None) -> list[dict[str, str]]:
    rows = validate_allowed_slices_against_pair_configs(normalize_allowed_slices(DEFAULT_ALLOWED_SLICES))
    if not symbol:
        return rows
    sym = symbol.strip().upper()
    filtered = []
    for row in rows:
        cfg = get_pair_config(row["pair_name"])
        if str(cfg.get("symbol", "")).upper() == sym:
            filtered.append(row)
    return filtered


def get_latest_trigger_close_time(
    *,
    pair_name: str,
    cfg: Mapping[str, Any],
    csv_dir: str | Path,
    csv_overrides: Mapping[str, str | Path | None] | None,
    csv_sep: str,
    tail_bars: int,
) -> tuple[pd.Timestamp | None, dict[str, Any]]:
    trigger_tf = str(cfg.get("trigger_timeframe") or cfg.get("base_timeframe")).upper()
    base_tf = str(cfg.get("base_timeframe")).upper()
    csv_key = str(cfg.get("base_csv_key"))
    path = resolve_csv_path(csv_dir, csv_key, csv_overrides)
    result = read_ohlc_csv_safe(
        path,
        base_tf,
        tail_bars=max(int(tail_bars), 5),
        requires_spread=bool(cfg.get("requires_spread", False) and cfg.get("spread_source_csv_key") == csv_key),
        csv_sep=csv_sep,
    )
    meta = {
        "csv_key": csv_key,
        "csv_path": str(path),
        "trigger_timeframe": trigger_tf,
        "base_timeframe": base_tf,
        "read_status": result.read_status,
        "read_error_reason": result.error_reason,
        "rows_valid": result.rows_valid,
        "latest_time": result.latest_time,
        "latest_close_time": result.latest_close_time,
        "separator": result.separator,
    }
    if not result.ok or result.latest_close_time is None:
        return None, meta
    return pd.Timestamp(result.latest_close_time), meta


def classify_pair(
    *,
    pair_name: str,
    cfg: Mapping[str, Any],
    latest_close_time: pd.Timestamp | None,
    previous_row: pd.Series | None,
    scan_on_initial_state: bool,
    meta: Mapping[str, Any],
) -> dict[str, Any]:
    now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    previous_close_time = None
    if previous_row is not None and "last_seen_close_time" in previous_row.index:
        previous_close_time = pd.to_datetime(previous_row.get("last_seen_close_time"), errors="coerce")
        if pd.isna(previous_close_time):
            previous_close_time = None

    if latest_close_time is None:
        status = STATUS_ERROR
        reason = str(meta.get("read_error_reason") or "latest_close_time missing")
        should_scan = False
    elif previous_close_time is None:
        status = STATUS_SCAN_REQUIRED if scan_on_initial_state else STATUS_INITIALIZE_ONLY
        reason = "no previous state"
        should_scan = bool(scan_on_initial_state)
    elif latest_close_time > previous_close_time:
        status = STATUS_SCAN_REQUIRED
        reason = "new confirmed trigger close_time"
        should_scan = True
    elif latest_close_time == previous_close_time:
        status = STATUS_SKIPPED_NO_NEW_BAR
        reason = "trigger close_time unchanged"
        should_scan = False
    else:
        status = STATUS_ERROR
        reason = "latest close_time is older than state"
        should_scan = False

    return {
        "pair_name": pair_name,
        "symbol": str(cfg.get("symbol", "")),
        "trigger_timeframe": str(cfg.get("trigger_timeframe") or cfg.get("base_timeframe")),
        "base_timeframe": str(cfg.get("base_timeframe", "")),
        "latest_close_time": latest_close_time,
        "previous_close_time": previous_close_time,
        "trigger_status": status,
        "should_scan": bool(should_scan),
        "trigger_reason": reason,
        "updated_at": now,
        **dict(meta),
    }


def build_updated_state(previous: pd.DataFrame, decisions: pd.DataFrame, *, commit_initialize_only: bool, commit_scan_required: bool) -> pd.DataFrame:
    rows_by_pair: dict[str, dict[str, Any]] = {}
    if not previous.empty:
        for _, row in previous.iterrows():
            pair = str(row.get("pair_name", "")).strip().upper()
            if pair:
                rows_by_pair[pair] = row.to_dict()

    for _, row in decisions.iterrows():
        pair = str(row.get("pair_name", "")).strip().upper()
        status = str(row.get("trigger_status", ""))
        latest = pd.to_datetime(row.get("latest_close_time"), errors="coerce")
        if not pair or pd.isna(latest):
            continue
        should_update = False
        if status == STATUS_INITIALIZE_ONLY and commit_initialize_only:
            should_update = True
        elif status == STATUS_SCAN_REQUIRED and commit_scan_required:
            should_update = True
        elif status == STATUS_SKIPPED_NO_NEW_BAR and pair not in rows_by_pair:
            should_update = True
        if not should_update:
            continue
        rows_by_pair[pair] = {
            "pair_name": pair,
            "symbol": row.get("symbol"),
            "trigger_timeframe": row.get("trigger_timeframe"),
            "base_timeframe": row.get("base_timeframe"),
            "last_seen_close_time": latest,
            "last_trigger_status": status,
            "last_trigger_reason": row.get("trigger_reason"),
            "updated_at": row.get("updated_at"),
        }
    out = pd.DataFrame(list(rows_by_pair.values()))
    if out.empty:
        return pd.DataFrame(columns=["pair_name", "symbol", "trigger_timeframe", "base_timeframe", "last_seen_close_time", "last_trigger_status", "last_trigger_reason", "updated_at"])
    out["last_seen_close_time"] = pd.to_datetime(out["last_seen_close_time"], errors="coerce")
    return out.sort_values(["symbol", "pair_name"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate Mochipoyo pair trigger state.")
    p.add_argument("--csv-dir", required=True)
    p.add_argument("--state-csv", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default="GOLD", help="Optional symbol filter. Use GOLD while BTC candidate timing is pending.")
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--tail-bars", type=int, default=20, help="Small tail read for trigger close_time detection only.")
    p.add_argument("--scan-on-initial-state", action="store_true")
    p.add_argument("--commit-state", action="store_true")
    p.add_argument("--commit-scan-required", action="store_true", help="Also update state for SCAN_REQUIRED rows. For validation, usually leave false until scan succeeds.")
    p.add_argument("--gold-m1-csv")
    p.add_argument("--gold-m5-csv")
    p.add_argument("--gold-m15-csv")
    p.add_argument("--gold-h1-csv")
    p.add_argument("--gold-h4-csv")
    p.add_argument("--gold-d1-csv")
    p.add_argument("--btc-m1-csv")
    p.add_argument("--btc-m5-csv")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state_csv)
    previous = read_state(state_path)
    lookup = state_lookup(previous)
    allowed = allowed_for_symbol(args.symbol)
    pair_names = get_required_pair_names(allowed)
    overrides = build_csv_overrides_from_args(args)

    decisions = []
    for pair_name in pair_names:
        cfg = get_pair_config(pair_name)
        latest, meta = get_latest_trigger_close_time(
            pair_name=pair_name,
            cfg=cfg,
            csv_dir=args.csv_dir,
            csv_overrides=overrides,
            csv_sep=args.csv_sep,
            tail_bars=int(args.tail_bars),
        )
        decisions.append(
            classify_pair(
                pair_name=pair_name,
                cfg=cfg,
                latest_close_time=latest,
                previous_row=lookup.get(pair_name),
                scan_on_initial_state=bool(args.scan_on_initial_state),
                meta=meta,
            )
        )

    decisions_df = pd.DataFrame(decisions)
    to_scan = decisions_df[decisions_df["should_scan"].fillna(False).astype(bool)].copy() if not decisions_df.empty else pd.DataFrame()
    state_after = build_updated_state(
        previous,
        decisions_df,
        commit_initialize_only=bool(args.commit_state),
        commit_scan_required=bool(args.commit_state and args.commit_scan_required),
    )

    write_csv(decisions_df, out_dir / "pair_trigger_decisions.csv")
    write_csv(to_scan, out_dir / "pair_trigger_to_scan.csv")
    write_csv(state_after, out_dir / "pair_trigger_state_preview.csv")
    if args.commit_state:
        write_csv(state_after, state_path)

    counts = decisions_df["trigger_status"].value_counts().to_dict() if not decisions_df.empty else {}
    summary = pd.DataFrame([
        {
            "run_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol_filter": str(args.symbol or ""),
            "pairs": int(len(decisions_df)),
            "scan_required": int(counts.get(STATUS_SCAN_REQUIRED, 0)),
            "initialize_only": int(counts.get(STATUS_INITIALIZE_ONLY, 0)),
            "skipped_no_new_bar": int(counts.get(STATUS_SKIPPED_NO_NEW_BAR, 0)),
            "error": int(counts.get(STATUS_ERROR, 0)),
            "to_scan_rows": int(len(to_scan)),
            "commit_state": bool(args.commit_state),
            "commit_scan_required": bool(args.commit_scan_required),
            "state_csv": str(state_path),
        }
    ])
    write_csv(summary, out_dir / "pair_trigger_summary.csv")
    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    print(f"state_csv: {state_path}")
    return 0 if int(summary.iloc[0]["error"]) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
