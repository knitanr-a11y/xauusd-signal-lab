#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare Mochipoyo full strict scan output with minimal scan output.

This script normalizes existing full strict and minimal candidate CSVs, optionally
filters by pair, optionally aligns time ranges, and writes comparison CSVs.

Readiness statuses:
- PLACEHOLDER_NO_MINIMAL_CSV: full side normalized, but no minimal side supplied.
- NORMALIZED_ONLY_NO_RISK: comparison rows exist, but risk_status or SL/TP are not ready.
- PASS/FAIL: only used when both sides are supplied and risk fields are ready.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:
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
except ModuleNotFoundError:
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


def apply_pair_filter(df: pd.DataFrame, pair_name: str | None) -> pd.DataFrame:
    if df.empty or not pair_name:
        return df.copy()
    if "pair_name" not in df.columns:
        return df.iloc[0:0].copy()
    pair = str(pair_name).strip().upper()
    return df[df["pair_name"].astype("string").str.upper() == pair].copy()


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


def _time_range(df: pd.DataFrame) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if df.empty or "signal_close_time" not in df.columns:
        return None, None
    times = pd.to_datetime(df["signal_close_time"], errors="coerce").dropna()
    if times.empty:
        return None, None
    return pd.Timestamp(times.min()), pd.Timestamp(times.max())


def _filter_time_range(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if df.empty or "signal_close_time" not in df.columns:
        return df.copy()
    times = pd.to_datetime(df["signal_close_time"], errors="coerce")
    return df.loc[times.between(start, end, inclusive="both")].copy().reset_index(drop=True)


def apply_time_alignment(
    full_df: pd.DataFrame,
    minimal_df: pd.DataFrame,
    *,
    align_minimal_to_full: bool,
    align_both_to_overlap: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Apply requested time alignment and return updated frames plus summary info."""
    info: dict[str, Any] = {
        "alignment_enabled": bool(align_minimal_to_full or align_both_to_overlap),
        "alignment_mode": "DISABLED",
        "alignment_status": "DISABLED",
        "alignment_full_min_signal_close_time": "",
        "alignment_full_max_signal_close_time": "",
        "alignment_minimal_min_signal_close_time": "",
        "alignment_minimal_max_signal_close_time": "",
        "alignment_start_signal_close_time": "",
        "alignment_end_signal_close_time": "",
        "alignment_full_rows_before": int(len(full_df)),
        "alignment_full_rows_after": int(len(full_df)),
        "alignment_minimal_rows_before": int(len(minimal_df)),
        "alignment_minimal_rows_after": int(len(minimal_df)),
    }
    if not (align_minimal_to_full or align_both_to_overlap):
        return full_df.copy(), minimal_df.copy(), info
    if full_df.empty or minimal_df.empty:
        info.update({"alignment_mode": "OVERLAP" if align_both_to_overlap else "MINIMAL_TO_FULL", "alignment_status": "EMPTY_SIDE"})
        return full_df.copy(), minimal_df.copy(), info

    f_start, f_end = _time_range(full_df)
    m_start, m_end = _time_range(minimal_df)
    if f_start is None or f_end is None or m_start is None or m_end is None:
        info.update({"alignment_mode": "OVERLAP" if align_both_to_overlap else "MINIMAL_TO_FULL", "alignment_status": "TIME_RANGE_EMPTY"})
        return full_df.copy(), minimal_df.copy(), info

    info.update(
        {
            "alignment_full_min_signal_close_time": f_start.strftime("%Y-%m-%d %H:%M:%S"),
            "alignment_full_max_signal_close_time": f_end.strftime("%Y-%m-%d %H:%M:%S"),
            "alignment_minimal_min_signal_close_time": m_start.strftime("%Y-%m-%d %H:%M:%S"),
            "alignment_minimal_max_signal_close_time": m_end.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    if align_both_to_overlap:
        start = max(f_start, m_start)
        end = min(f_end, m_end)
        info["alignment_mode"] = "OVERLAP"
        if start > end:
            info["alignment_status"] = "NO_OVERLAP"
            return full_df.iloc[0:0].copy(), minimal_df.iloc[0:0].copy(), info
        out_full = _filter_time_range(full_df, start, end)
        out_minimal = _filter_time_range(minimal_df, start, end)
    else:
        start, end = f_start, f_end
        info["alignment_mode"] = "MINIMAL_TO_FULL"
        out_full = full_df.copy()
        out_minimal = _filter_time_range(minimal_df, start, end)

    info.update(
        {
            "alignment_status": "APPLIED",
            "alignment_start_signal_close_time": start.strftime("%Y-%m-%d %H:%M:%S"),
            "alignment_end_signal_close_time": end.strftime("%Y-%m-%d %H:%M:%S"),
            "alignment_full_rows_after": int(len(out_full)),
            "alignment_minimal_rows_after": int(len(out_minimal)),
        }
    )
    return out_full.reset_index(drop=True), out_minimal.reset_index(drop=True), info


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


def _non_empty_notna(df: pd.DataFrame, col: str) -> bool:
    return bool(col in df.columns and len(df) > 0 and df[col].notna().any())


def risk_readiness(df: pd.DataFrame, *, require_btc_spread: bool = True) -> dict[str, bool]:
    if df.empty:
        return {"risk_ready": False, "risk_price_ready": False, "btc_spread_required": False, "btc_spread_ready": False, "comparison_ready": False}
    risk_ready = _non_empty_notna(df, "risk_status")
    risk_price_ready = _non_empty_notna(df, "sl_price") and _non_empty_notna(df, "tp_price")
    has_btc = bool("symbol" in df.columns and df["symbol"].astype("string").str.upper().eq("BTC").any())
    btc_spread_required = bool(require_btc_spread and has_btc)
    btc_spread_cols = ["current_spread_price", "mode_spread_price", "effective_spread_price", "spread_to_sl_ratio", "effective_rr_after_spread", "net_sl_after_spread_price", "net_tp_after_spread_price"]
    btc_spread_ready = True
    if btc_spread_required:
        btc_df = df[df["symbol"].astype("string").str.upper() == "BTC"].copy()
        btc_spread_ready = all(_non_empty_notna(btc_df, col) for col in btc_spread_cols)
    return {
        "risk_ready": bool(risk_ready),
        "risk_price_ready": bool(risk_price_ready),
        "btc_spread_required": bool(btc_spread_required),
        "btc_spread_ready": bool(btc_spread_ready),
        "comparison_ready": bool(risk_ready and risk_price_ready and btc_spread_ready),
    }


def combined_readiness(full_df: pd.DataFrame, minimal_df: pd.DataFrame, *, has_minimal: bool) -> dict[str, bool]:
    full_flags = risk_readiness(full_df)
    minimal_flags = risk_readiness(minimal_df) if has_minimal else {"risk_ready": False, "risk_price_ready": False, "btc_spread_required": False, "btc_spread_ready": False, "comparison_ready": False}
    return {
        "full_risk_ready": full_flags["risk_ready"],
        "full_risk_price_ready": full_flags["risk_price_ready"],
        "full_btc_spread_required": full_flags["btc_spread_required"],
        "full_btc_spread_ready": full_flags["btc_spread_ready"],
        "full_comparison_ready": full_flags["comparison_ready"],
        "minimal_risk_ready": minimal_flags["risk_ready"],
        "minimal_risk_price_ready": minimal_flags["risk_price_ready"],
        "minimal_btc_spread_required": minimal_flags["btc_spread_required"],
        "minimal_btc_spread_ready": minimal_flags["btc_spread_ready"],
        "minimal_comparison_ready": minimal_flags["comparison_ready"],
        "both_comparison_ready": bool(full_flags["comparison_ready"] and (minimal_flags["comparison_ready"] if has_minimal else False)),
    }


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
    if col in {"sl_price", "tp_price", "risk_distance", "reward_distance", "rr", "current_spread_price", "mode_spread_price", "effective_spread_price", "spread_to_sl_ratio", "effective_rr_after_spread", "net_sl_after_spread_price", "net_tp_after_spread_price"}:
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
                rows.append({"payload_key": payload_key, "column": col, "full_value": full_value, "minimal_value": minimal_value})
    return pd.DataFrame(rows, columns=["payload_key", "column", "full_value", "minimal_value"])


def compare_payload_keys_by_logical_key(full_df: pd.DataFrame, minimal_df: pd.DataFrame) -> pd.DataFrame:
    if full_df.empty or minimal_df.empty:
        return pd.DataFrame(columns=["logical_key", "payload_key_full", "payload_key_minimal"])
    full = full_df.copy()
    minimal = minimal_df.copy()
    full["logical_key"] = logical_key_frame(full)
    minimal["logical_key"] = logical_key_frame(minimal)
    merged = full[["logical_key", "payload_key"]].merge(minimal[["logical_key", "payload_key"]], on="logical_key", how="inner", suffixes=("_full", "_minimal"))
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
    matched = full_valid.merge(minimal_valid, on="payload_key", how="inner", suffixes=("__full", "__minimal"))
    return {
        "matched": matched,
        "full_only": full_valid[~full_valid["payload_key"].astype(str).isin(matched_keys)].copy(),
        "minimal_only": minimal_valid[~minimal_valid["payload_key"].astype(str).isin(matched_keys)].copy(),
        "value_diff": compare_value_diffs(matched),
        "payload_key_diff": compare_payload_keys_by_logical_key(full_valid, minimal_valid),
    }


def normalize_full_csv(path: str | Path, allowed_slices: list[dict[str, str]], lookback_candidates: int, pair_name: str | None = None) -> pd.DataFrame:
    raw = read_csv_safe(path)
    normalized = normalize_full_strict_candidates(raw)
    filtered = filter_allowed_slices(normalized, allowed_slices)
    filtered = apply_pair_filter(filtered, pair_name)
    return apply_lookback(filtered, lookback_candidates)


def normalize_minimal_csv(path: str | Path, allowed_slices: list[dict[str, str]], lookback_candidates: int, pair_name: str | None = None) -> pd.DataFrame:
    raw = read_csv_safe(path)
    normalized = normalize_minimal_candidates(raw)
    filtered = filter_allowed_slices(normalized, allowed_slices)
    filtered = apply_pair_filter(filtered, pair_name)
    return apply_lookback(filtered, lookback_candidates)


def build_summary(
    *,
    args: argparse.Namespace,
    allowed_slices: list[dict[str, str]],
    full_df: pd.DataFrame,
    minimal_df: pd.DataFrame,
    comparison: dict[str, pd.DataFrame] | None,
    errors: list[dict[str, Any]],
    alignment_info: dict[str, Any],
) -> pd.DataFrame:
    has_minimal = bool(args.minimal_csv)
    readiness = combined_readiness(full_df, minimal_df, has_minimal=has_minimal)
    if comparison is None:
        matched_rows = full_only_rows = minimal_only_rows = value_diff_rows = payload_key_diff_rows = 0
        status = "PLACEHOLDER_NO_MINIMAL_CSV"
    else:
        matched_rows = int(len(comparison["matched"]))
        full_only_rows = int(len(comparison["full_only"]))
        minimal_only_rows = int(len(comparison["minimal_only"]))
        value_diff_rows = int(len(comparison["value_diff"]))
        payload_key_diff_rows = int(len(comparison["payload_key_diff"]))
        if not readiness["both_comparison_ready"]:
            status = "NORMALIZED_ONLY_NO_RISK"
        else:
            status = "PASS" if all(x == 0 for x in [full_only_rows, minimal_only_rows, value_diff_rows, payload_key_diff_rows]) else "FAIL"
    if errors:
        status = "ERROR"
    row = {
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "full_csv": str(args.full_csv) if args.full_csv else "",
        "minimal_csv": str(args.minimal_csv) if args.minimal_csv else "",
        "pair_name_filter": str(args.pair_name or ""),
        "align_minimal_to_full_time_range": bool(args.align_minimal_to_full_time_range),
        "align_both_to_overlap_time_range": bool(args.align_both_to_overlap_time_range),
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
    row.update(alignment_info)
    row.update(readiness)
    return pd.DataFrame([row])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize and compare Mochipoyo full strict vs minimal candidate CSVs.")
    parser.add_argument("--full-csv", required=True)
    parser.add_argument("--minimal-csv", default=None)
    parser.add_argument("--allowed-slices-json", default=None)
    parser.add_argument("--pair-name", default=None)
    parser.add_argument("--align-minimal-to-full-time-range", action="store_true", help="Filter minimal rows to full side's signal_close_time min/max range.")
    parser.add_argument("--align-both-to-overlap-time-range", action="store_true", help="Filter both full and minimal rows to their overlapping signal_close_time range.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--as-of-time", default=None)
    parser.add_argument("--lookback-candidates", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, Any]] = []
    alignment_info: dict[str, Any] = {
        "alignment_enabled": bool(args.align_minimal_to_full_time_range or args.align_both_to_overlap_time_range),
        "alignment_mode": "DISABLED",
        "alignment_status": "DISABLED",
        "alignment_full_min_signal_close_time": "",
        "alignment_full_max_signal_close_time": "",
        "alignment_minimal_min_signal_close_time": "",
        "alignment_minimal_max_signal_close_time": "",
        "alignment_start_signal_close_time": "",
        "alignment_end_signal_close_time": "",
        "alignment_full_rows_before": 0,
        "alignment_full_rows_after": 0,
        "alignment_minimal_rows_before": 0,
        "alignment_minimal_rows_after": 0,
    }

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
            full_df = normalize_full_csv(args.full_csv, allowed_slices, args.lookback_candidates, args.pair_name)
        except Exception as exc:
            errors.append({"stage": "normalize_full_csv", "error": str(exc), "path": str(args.full_csv)})

    if not errors and args.minimal_csv:
        try:
            minimal_df = normalize_minimal_csv(args.minimal_csv, allowed_slices, args.lookback_candidates, args.pair_name)
            full_df, minimal_df, alignment_info = apply_time_alignment(
                full_df,
                minimal_df,
                align_minimal_to_full=bool(args.align_minimal_to_full_time_range),
                align_both_to_overlap=bool(args.align_both_to_overlap_time_range),
            )
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
    summary = build_summary(args=args, allowed_slices=allowed_slices, full_df=full_df, minimal_df=minimal_df, comparison=comparison, errors=errors, alignment_info=alignment_info)
    write_csv(summary, out_dir / "comparison_summary.csv")
    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    return 1 if not summary.empty and str(summary.iloc[0]["status"]) == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
