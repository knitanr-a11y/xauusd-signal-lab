#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flexible Mochipoyo CSV comparison.

Use this when either side may already be normalized/enriched, such as
minimal_candidates_notification_ok_*.csv.

It preserves existing normalized columns when present instead of forcing the
minimal CSV through normalize_minimal_candidates again.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

try:
    from scripts.mochipoyo_candidate_normalizer import (
        NORMALIZED_COLUMNS,
        ensure_normalized_columns,
        filter_allowed_slices,
        normalize_full_strict_candidates,
        normalize_minimal_candidates,
    )
    from scripts.mochipoyo_minimal_config import DEFAULT_ALLOWED_SLICES, allowed_slice_to_string, normalize_allowed_slices, validate_allowed_slices_against_pair_configs
except ModuleNotFoundError:
    from mochipoyo_candidate_normalizer import (  # type: ignore
        NORMALIZED_COLUMNS,
        ensure_normalized_columns,
        filter_allowed_slices,
        normalize_full_strict_candidates,
        normalize_minimal_candidates,
    )
    from mochipoyo_minimal_config import DEFAULT_ALLOWED_SLICES, allowed_slice_to_string, normalize_allowed_slices, validate_allowed_slices_against_pair_configs  # type: ignore

LOGICAL_KEY_COLUMNS = ["symbol", "pair_name", "candidate_rank", "direction", "signal_close_time", "entry_time", "entry_price_normalized"]
COMPARE_VALUE_COLUMNS = [
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
    "notification_eligible",
    "notification_reject_reason",
]
NUMERIC_COLUMNS = {
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
}
TIME_COLUMNS = {"signal_close_time", "entry_time"}


def read_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV not found: {p}")
    return pd.read_csv(p, encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def is_already_normalized(df: pd.DataFrame) -> bool:
    required = {"symbol", "pair_name", "candidate_rank", "direction", "signal_close_time", "entry_time", "entry_price_normalized", "payload_key", "selected_slice"}
    return required.issubset(set(df.columns))


def normalize_for_compare(df: pd.DataFrame, *, side: str) -> pd.DataFrame:
    if is_already_normalized(df):
        return ensure_normalized_columns(df.copy())
    if side == "full":
        return normalize_full_strict_candidates(df)
    return normalize_minimal_candidates(df)


def apply_pair_filter(df: pd.DataFrame, pair_name: str | None) -> pd.DataFrame:
    if df.empty or not pair_name:
        return df.copy()
    pair = str(pair_name).strip().upper()
    return df[df.get("pair_name", pd.Series(dtype="string")).astype("string").str.upper() == pair].copy()


def apply_lookback(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    if df.empty or lookback <= 0:
        return df.copy()
    work = df.copy()
    sort_cols = [c for c in ["entry_time", "signal_close_time", "payload_key"] if c in work.columns]
    if sort_cols:
        work = work.sort_values(sort_cols, na_position="last")
    if len(work) > lookback:
        work = work.tail(lookback)
    return work.reset_index(drop=True)


def filter_time_overlap(full: pd.DataFrame, minimal: pd.DataFrame, enabled: bool) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    info = {"alignment_enabled": bool(enabled), "alignment_status": "DISABLED", "alignment_start_signal_close_time": "", "alignment_end_signal_close_time": "", "alignment_full_rows_before": len(full), "alignment_full_rows_after": len(full), "alignment_minimal_rows_before": len(minimal), "alignment_minimal_rows_after": len(minimal)}
    if not enabled:
        return full.copy(), minimal.copy(), info
    if full.empty or minimal.empty:
        info["alignment_status"] = "EMPTY_SIDE"
        return full.copy(), minimal.copy(), info
    ft = pd.to_datetime(full["signal_close_time"], errors="coerce").dropna()
    mt = pd.to_datetime(minimal["signal_close_time"], errors="coerce").dropna()
    if ft.empty or mt.empty:
        info["alignment_status"] = "TIME_RANGE_EMPTY"
        return full.copy(), minimal.copy(), info
    start = max(pd.Timestamp(ft.min()), pd.Timestamp(mt.min()))
    end = min(pd.Timestamp(ft.max()), pd.Timestamp(mt.max()))
    if start > end:
        info["alignment_status"] = "NO_OVERLAP"
        return full.iloc[0:0].copy(), minimal.iloc[0:0].copy(), info
    fmask = pd.to_datetime(full["signal_close_time"], errors="coerce").between(start, end, inclusive="both")
    mmask = pd.to_datetime(minimal["signal_close_time"], errors="coerce").between(start, end, inclusive="both")
    out_f = full.loc[fmask].copy().reset_index(drop=True)
    out_m = minimal.loc[mmask].copy().reset_index(drop=True)
    info.update({"alignment_status": "APPLIED", "alignment_start_signal_close_time": start.strftime("%Y-%m-%d %H:%M:%S"), "alignment_end_signal_close_time": end.strftime("%Y-%m-%d %H:%M:%S"), "alignment_full_rows_after": len(out_f), "alignment_minimal_rows_after": len(out_m)})
    return out_f, out_m, info


def logical_key_series(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="string")
    parts: list[pd.Series] = []
    for col in LOGICAL_KEY_COLUMNS:
        if col in TIME_COLUMNS:
            parts.append(pd.to_datetime(df.get(col), errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").astype("string").fillna(""))
        else:
            parts.append(df.get(col, pd.Series([""] * len(df), index=df.index)).astype("string").fillna(""))
    key = parts[0]
    for part in parts[1:]:
        key = key + "|" + part
    return key


def same_value(a: Any, b: Any, col: str) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) != pd.isna(b):
        return False
    if col in TIME_COLUMNS:
        return bool(pd.to_datetime(a, errors="coerce") == pd.to_datetime(b, errors="coerce"))
    if col in NUMERIC_COLUMNS:
        af = pd.to_numeric(pd.Series([a]), errors="coerce").iloc[0]
        bf = pd.to_numeric(pd.Series([b]), errors="coerce").iloc[0]
        if pd.isna(af) and pd.isna(bf):
            return True
        if pd.isna(af) != pd.isna(bf):
            return False
        return abs(float(af) - float(bf)) <= 1e-5
    return str(a) == str(b)


def compare_value_diffs(matched: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in matched.iterrows():
        key = row.get("payload_key")
        for col in COMPARE_VALUE_COLUMNS:
            fc = f"{col}__full"
            mc = f"{col}__minimal"
            if fc not in matched.columns or mc not in matched.columns:
                continue
            if not same_value(row.get(fc), row.get(mc), col):
                rows.append({"payload_key": key, "column": col, "full_value": row.get(fc), "minimal_value": row.get(mc)})
    return pd.DataFrame(rows, columns=["payload_key", "column", "full_value", "minimal_value"])


def compare(full: pd.DataFrame, minimal: pd.DataFrame) -> dict[str, pd.DataFrame]:
    f = full.copy()
    m = minimal.copy()
    f["logical_key"] = logical_key_series(f)
    m["logical_key"] = logical_key_series(m)
    f_valid = f[f["payload_key"].notna()].copy()
    m_valid = m[m["payload_key"].notna()].copy()
    keys = set(f_valid["payload_key"].astype(str)).intersection(set(m_valid["payload_key"].astype(str)))
    matched = f_valid.merge(m_valid, on="payload_key", how="inner", suffixes=("__full", "__minimal"))
    key_diff = f_valid[["logical_key", "payload_key"]].merge(m_valid[["logical_key", "payload_key"]], on="logical_key", how="inner", suffixes=("_full", "_minimal"))
    key_diff = key_diff[key_diff["payload_key_full"].astype(str) != key_diff["payload_key_minimal"].astype(str)].copy()
    return {
        "matched": matched,
        "full_only": f_valid[~f_valid["payload_key"].astype(str).isin(keys)].copy(),
        "minimal_only": m_valid[~m_valid["payload_key"].astype(str).isin(keys)].copy(),
        "value_diff": compare_value_diffs(matched),
        "payload_key_diff": key_diff,
    }


def load_allowed() -> list[dict[str, str]]:
    return validate_allowed_slices_against_pair_configs(normalize_allowed_slices(DEFAULT_ALLOWED_SLICES))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Flexible compare for Mochipoyo CSVs.")
    p.add_argument("--full-csv", required=True)
    p.add_argument("--minimal-csv", required=True)
    p.add_argument("--pair-name", default=None)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--lookback-candidates", type=int, default=0)
    p.add_argument("--align-both-to-overlap-time-range", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    allowed = load_allowed()
    full = normalize_for_compare(read_csv(args.full_csv), side="full")
    minimal = normalize_for_compare(read_csv(args.minimal_csv), side="minimal")
    full = filter_allowed_slices(full, allowed)
    minimal = filter_allowed_slices(minimal, allowed)
    full = apply_pair_filter(full, args.pair_name)
    minimal = apply_pair_filter(minimal, args.pair_name)
    full = apply_lookback(full, args.lookback_candidates)
    minimal = apply_lookback(minimal, args.lookback_candidates)
    full, minimal, alignment = filter_time_overlap(full, minimal, bool(args.align_both_to_overlap_time_range))
    comp = compare(full, minimal)

    write_csv(full, out_dir / "comparison_full_filtered.csv")
    write_csv(minimal, out_dir / "comparison_minimal.csv")
    for name, df in comp.items():
        write_csv(df, out_dir / f"comparison_{name}.csv")

    status = "PASS" if all(len(comp[k]) == 0 for k in ["full_only", "minimal_only", "value_diff", "payload_key_diff"]) else "FAIL"
    summary = pd.DataFrame([
        {
            "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "full_csv": str(args.full_csv),
            "minimal_csv": str(args.minimal_csv),
            "pair_name_filter": str(args.pair_name or ""),
            "full_rows": len(full),
            "minimal_rows": len(minimal),
            "matched_rows": len(comp["matched"]),
            "full_only_rows": len(comp["full_only"]),
            "minimal_only_rows": len(comp["minimal_only"]),
            "value_diff_rows": len(comp["value_diff"]),
            "payload_key_diff_rows": len(comp["payload_key_diff"]),
            "status": status,
            **alignment,
        }
    ])
    write_csv(summary, out_dir / "comparison_summary.csv")
    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
