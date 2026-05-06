#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare Mochipoyo full strict scan output with minimal scan output.

Initial implementation scope:
- Normalize an existing full strict output CSV.
- Optionally normalize an existing minimal output CSV.
- If both sides are provided, compare by payload_key and fallback logical key.
- Write comparison CSVs and a summary CSV.

This script intentionally does not run the full strict scanner and does not run
minimal scanner logic yet.  It is the comparison/reporting skeleton that will be
wired to real scanner calls after the minimal scanner module exists.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:  # Package import from repository root.
    from scripts.mochipoyo_candidate_normalizer import (
        NORMALIZED_COLUMNS,
        filter_allowed_slices,
        normalize_full_strict_candidates,
        normalize_minimal_candidates,
    )
    from scripts.mochipoyo_minimal_config import (
        DEFAULT_ALLOWED_SLICES,
        allowed_slice_to_string,
        normalize_allowed_slices,
        validate_allowed_slices_against_pair_configs,
    )
except ModuleNotFoundError:  # Direct execution from scripts/.
    from mochipoyo_candidate_normalizer import (  # type: ignore
        NORMALIZED_COLUMNS,
        filter_allowed_slices,
        normalize_full_strict_candidates,
        normalize_minimal_candidates,
    )
    from mochipoyo_minimal_config import (  # type: ignore
        DEFAULT_ALLOWED_SLICES,
        allowed_slice_to_string,
        normalize_allowed_slices,
        validate_allowed_slices_against_pair_configs,
    )

COMPARE_VALUE_COLUMNS: list[str] = [
    "symbol",
    "mt5_symbol",
    "pair_name",
    "candidate_rank",
    "direction",
    "signal_close_time",
    "entry_time",
    "entry_price_normalized",
    "sl_price",
    "tp_price",
    "risk_status",
    "reason_text",
    "base_time",
    "base_close_time",
    "context_time",
    "context_close_time",
    "pivot_time",
    "pivot_confirmed_time",
    "risk_distance",
    "reward_distance",
    "rr",
    "current_spread_price",
    "mode_spread_price",
    "effective_spread_price",
    "spread_to_sl_ratio",
    "effective_rr_after_spread",
    "net_sl_after_spread_price",
    "net_tp_after_spread_price",
]

LOGICAL_KEY_COLUMNS: list[str] = [
    "symbol",
    "pair_name",
    "candidate_rank",
    "direction",
    "signal_close_time",
    "entry_time",
    "entry_price_normalized",
]

NUMERIC_COMPARE_TOLERANCE = 1e-5


def read_csv_safe(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return pd.read_csv(p, encoding="utf-8-sig")


def load_allowed_slices(path: str | Path | None) -> list[dict[str, str]]:
    if path is None:
        rows: Iterable[Mapping[str, Any] | str] = DEFAULT_ALLOWED_SLICES
    else:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise RuntimeError(f"allowed_slices_json must contain a list: {p}")
        rows = data
    return validate_allowed_slices_against_pair_configs(normalize_allowed_slices(rows))


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = ensure_parent(path)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def empty_normalized_df() -> pd.DataFrame:
    return pd.DataFrame(columns=NORMALIZED_COLUMNS)


def apply_lookback(df: pd.DataFrame, lookback_candidates: int) -> pd.DataFrame:
    if df.empty or lookback_candidates <= 0:
        return df.copy()
    sort_cols = [c for c in ["entry_time", "signal_close_time", "payload_key"] if c in df.columns]
    work = df.copy()
    if sort_cols:
        work = work.sort_values(sort_cols, na_position="last")
    if len(work) > lookback_candidates:
        work = work.tail(lookback_candidates)
    return work.reset_index(drop=True)


def logical_key_frame(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="string")
    parts = []
    for col in LOGICAL_KEY_COLUMNS:
        if col not in df.columns:
            parts.append(pd.Series([""] * len(df), index=df.index, dtype="string"))
        elif col in {"signal_close_time", "entry_time"}:
            parts.append(pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").astype("string").fillna(""))
        else:
            parts.append(df[col].astype("string").fillna(""))
    key = parts[0]
    for part in parts[1:]:
        key = key + "|" + part
    return key


def _same_value(left: Any, right: Any, col: str) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if pd.isna(left) != pd.isna(right):
        return False
    if col in {"signal_close_time", "entry_time", "base_time", "base_close_time", "context_time", "context_close_time", "pivot_time", "pivot_confirmed_time"}:
        ldt = pd.to_datetime(left, errors="coerce")
        rdt = pd.to_datetime(right, errors="coerce")
        if pd.isna(ldt) and pd.isna(rdt):
            return True
        return bool(ldt == rdt)
    if col in {
        "sl_price",
        "tp_price",
        "risk_distance",
        "reward_distance",
        "rr",
        "current_spread_price",
        "mode_spread_price",
        "effective_spread_price",
        "spread_to_sl_ratio",
        "effective_rr_after_spread",
        "net_sl_after_spread_price",
        "net_tp_after_spread_price",
    }:
        lf = pd.to_numeric(pd.Series([left]), errors="coerce").iloc[0]
        rf = pd.to_numeric(pd.Series([right]), errors="coerce").iloc[0]
        if pd.isna(lf) and pd.isna(rf):
            return True
        if pd.isna(lf) != pd.isna(rf):
            return False
        return abs(float(lf) - float(rf)) <= NUMERIC_COMPARE_TOLERANCE
    return str(left) == str(right)


def compare_value_diffs(matched: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if matched.empty:
        return pd.DataFrame(columns=["payload_key", "column", "full_value", "minimal_value"])
    for _, row in matched.iterrows():
        payload_key = row.get("payload_key")
        for col in COMPARE_VALUE_COLUMNS:
            full_col = f"{col}__full"
            minimal_col = f"{col}__minimal"
            if full_col not in matched.columns or minimal_col not in matched.columns:
                continue
            full_value = row.get(full_col)
            minimal_value = row.get(minimal_col)
            if not _same_value(full_value, minimal_value, col):
                rows.append(
                    {
                        "payload_key": payload_key,
                        "column": col,
                        "full_value": full_value,
                        "minimal_value": minimal_value,
                    }
                )
    return pd.DataFrame(rows, columns=["payload_key", "column", "full_value", "minimal_value"])


def compare_payload_keys_by_logical_key(full_df: pd.DataFrame, minimal_df: pd.DataFrame) -> pd.DataFrame:
    if full_df.empty or minimal_df.empty:
        return pd.DataFrame(columns=["logical_key", "payload_key_full", "payload_key_minimal"])
    full = full_df.copy()
    minimal = minimal_df.copy()
    full["logical_key"] = logical_key_frame(full)
    minimal["logical_key"] = logical_key_frame(minimal)
    merged = full[["logical_key", "payload_key"]].merge(
        minimal[["logical_key", "payload_key"]],
        on="logical_key",
        how="inner",
        suffixes=("_full", "_minimal"),
    )
    if merged.empty:
        return pd.DataFrame(columns=["logical_key", "payload_key_full", "payload_key_minimal"])
    return merged[merged["payload_key_full"].astype(str) != merged["payload_key_minimal"].astype(str)].copy()


def compare_full_vs_minimal(full_df: pd.DataFrame, minimal_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    full = full_df.copy()
    minimal = minimal_df.copy()
    if "payload_key" not in full.columns:
        full["payload_key"] = pd.NA
    if "payload_key" not in minimal.columns:
        minimal["payload_key"] = pd.NA

    full_valid = full[full["payload_key"].notna()].copy()
    minimal_valid = minimal[minimal["payload_key"].notna()].copy()

    matched_keys = set(full_valid["payload_key"].astype(str)).intersection(set(minimal_valid["payload_key"].astype(str)))
    full_only = full_valid[~full_valid["payload_key"].astype(str).isin(matched_keys)].copy()
    minimal_only = minimal_valid[~minimal_valid["payload_key"].astype(str).isin(matched_keys)].copy()

    matched = full_valid.merge(
        minimal_valid,
        on="payload_key",
        how="inner",
        suffixes=("__full", "__minimal"),
    )
    value_diff = compare_value_diffs(matched)
    payload_key_diff = compare_payload_keys_by_logical_key(full_valid, minimal_valid)

    return {
        "matched": matched,
        "full_only": full_only,
        "minimal_only": minimal_only,
        "value_diff": value_diff,
        "payload_key_diff": payload_key_diff,
    }


def normalize_full_csv(path: str | Path, allowed_slices: list[dict[str, str]], lookback_candidates: int) -> pd.DataFrame:
    raw = read_csv_safe(path)
    normalized = normalize_full_strict_candidates(raw)
    filtered = filter_allowed_slices(normalized, allowed_slices)
    return apply_lookback(filtered, lookback_candidates)


def normalize_minimal_csv(path: str | Path, allowed_slices: list[dict[str, str]], lookback_candidates: int) -> pd.DataFrame:
    raw = read_csv_safe(path)
    normalized = normalize_minimal_candidates(raw)
    filtered = filter_allowed_slices(normalized, allowed_slices)
    return apply_lookback(filtered, lookback_candidates)


def build_summary(
    *,
    args: argparse.Namespace,
    allowed_slices: list[dict[str, str]],
    full_df: pd.DataFrame,
    minimal_df: pd.DataFrame,
    comparison: dict[str, pd.DataFrame] | None,
    errors: list[dict[str, Any]],
) -> pd.DataFrame:
    if comparison is None:
        matched_rows = 0
        full_only_rows = 0
        minimal_only_rows = 0
        value_diff_rows = 0
        payload_key_diff_rows = 0
        status = "PLACEHOLDER_NO_MINIMAL_CSV"
    else:
        matched_rows = int(len(comparison["matched"]))
        full_only_rows = int(len(comparison["full_only"]))
        minimal_only_rows = int(len(comparison["minimal_only"]))
        value_diff_rows = int(len(comparison["value_diff"]))
        payload_key_diff_rows = int(len(comparison["payload_key_diff"]))
        status = "PASS" if all(x == 0 for x in [full_only_rows, minimal_only_rows, value_diff_rows, payload_key_diff_rows]) else "FAIL"
    if errors:
        status = "ERROR"
    return pd.DataFrame(
        [
            {
                "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "full_csv": str(args.full_csv) if args.full_csv else "",
                "minimal_csv": str(args.minimal_csv) if args.minimal_csv else "",
                "as_of_time": str(args.as_of_time or ""),
                "lookback_candidates": int(args.lookback_candidates),
                "allowed_slices_count": int(len(allowed_slices)),
                "allowed_slices": ",".join(allowed_slice_to_string(x) for x in allowed_slices),
                "full_rows": int(len(full_df)),
                "minimal_rows": int(len(minimal_df)),
                "matched_rows": matched_rows,
                "full_only_rows": full_only_rows,
                "minimal_only_rows": minimal_only_rows,
                "value_diff_rows": value_diff_rows,
                "payload_key_diff_rows": payload_key_diff_rows,
                "error_rows": int(len(errors)),
                "status": status,
            }
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize and compare Mochipoyo full strict vs minimal candidate CSVs.")
    parser.add_argument("--full-csv", required=True, help="Existing full strict output CSV, usually payload/fixed candidate CSV.")
    parser.add_argument("--minimal-csv", default=None, help="Existing minimal output CSV. Optional until minimal scanner exists.")
    parser.add_argument("--allowed-slices-json", default=None, help="Optional JSON list of allowed slices. Defaults to built-in spec slices.")
    parser.add_argument("--out-dir", required=True, help="Directory for comparison outputs.")
    parser.add_argument("--as-of-time", default=None, help="Reserved for future scanner-run mode. Not used for CSV-only mode yet.")
    parser.add_argument("--lookback-candidates", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, Any]] = []

    try:
        allowed_slices = load_allowed_slices(args.allowed_slices_json)
    except Exception as exc:
        allowed_slices = []
        errors.append({"stage": "load_allowed_slices", "error": str(exc)})

    full_df = empty_normalized_df()
    minimal_df = empty_normalized_df()
    comparison: dict[str, pd.DataFrame] | None = None

    if not errors:
        try:
            full_df = normalize_full_csv(args.full_csv, allowed_slices, args.lookback_candidates)
        except Exception as exc:
            errors.append({"stage": "normalize_full_csv", "error": str(exc), "path": str(args.full_csv)})

    if not errors and args.minimal_csv:
        try:
            minimal_df = normalize_minimal_csv(args.minimal_csv, allowed_slices, args.lookback_candidates)
        except Exception as exc:
            errors.append({"stage": "normalize_minimal_csv", "error": str(exc), "path": str(args.minimal_csv)})

    if not errors and args.minimal_csv:
        comparison = compare_full_vs_minimal(full_df, minimal_df)

    write_csv(full_df, out_dir / "comparison_full_filtered.csv")
    write_csv(minimal_df, out_dir / "comparison_minimal.csv")

    if comparison is None:
        write_csv(pd.DataFrame(), out_dir / "comparison_matched.csv")
        write_csv(pd.DataFrame(), out_dir / "comparison_full_only.csv")
        write_csv(pd.DataFrame(), out_dir / "comparison_minimal_only.csv")
        write_csv(pd.DataFrame(columns=["payload_key", "column", "full_value", "minimal_value"]), out_dir / "comparison_value_diff.csv")
        write_csv(pd.DataFrame(columns=["logical_key", "payload_key_full", "payload_key_minimal"]), out_dir / "comparison_payload_key_diff.csv")
    else:
        write_csv(comparison["matched"], out_dir / "comparison_matched.csv")
        write_csv(comparison["full_only"], out_dir / "comparison_full_only.csv")
        write_csv(comparison["minimal_only"], out_dir / "comparison_minimal_only.csv")
        write_csv(comparison["value_diff"], out_dir / "comparison_value_diff.csv")
        write_csv(comparison["payload_key_diff"], out_dir / "comparison_payload_key_diff.csv")

    errors_df = pd.DataFrame(errors, columns=["stage", "error", "path"])
    write_csv(errors_df, out_dir / "comparison_errors.csv")

    summary = build_summary(
        args=args,
        allowed_slices=allowed_slices,
        full_df=full_df,
        minimal_df=minimal_df,
        comparison=comparison,
        errors=errors,
    )
    write_csv(summary, out_dir / "comparison_summary.csv")

    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    return 1 if not summary.empty and str(summary.iloc[0]["status"]) == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
