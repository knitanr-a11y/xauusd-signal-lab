#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit timing columns for a Mochipoyo portfolio CSV.

Checks:
- context_close_time <= base_close_time
- signal_close_time >= base_close_time, when both columns exist
- entry_time >= signal_close_time
- base_pivot_confirmed_time <= signal_close_time, when populated
- context_pivot_confirmed_time <= signal_close_time, when populated
- exit_time >= entry_time, when populated

This script does not change trades or outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


TIME_COLS = [
    "context_close_time",
    "base_close_time",
    "signal_close_time",
    "entry_time",
    "base_pivot_confirmed_time",
    "context_pivot_confirmed_time",
    "exit_time",
]


def parse_time(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def violation_df(df: pd.DataFrame, mask: pd.Series, name: str) -> pd.DataFrame:
    out = df[mask].copy()
    out.insert(0, "violation", name)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Audit Mochipoyo timing columns.")
    p.add_argument("--portfolio-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/selected/gold_mochipoyo_rr12_fixed_preset_timing_audit")
    args = p.parse_args()

    src = Path(args.portfolio_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src, encoding="utf-8-sig")
    for c in TIME_COLS:
        if c in df.columns:
            df["_" + c] = parse_time(df[c])

    violations = []
    counts = {}

    def add_check(name: str, ok_mask: pd.Series) -> None:
        bad = ~ok_mask.fillna(False)
        counts[name] = int(bad.sum())
        if bad.any():
            violations.append(violation_df(df, bad, name))

    if {"_context_close_time", "_base_close_time"}.issubset(df.columns):
        add_check("context_close_time_lte_base_close_time", df["_context_close_time"] <= df["_base_close_time"])
    else:
        counts["context_close_time_lte_base_close_time"] = None

    if {"_signal_close_time", "_base_close_time"}.issubset(df.columns):
        add_check("signal_close_time_gte_base_close_time", df["_signal_close_time"] >= df["_base_close_time"])
    else:
        counts["signal_close_time_gte_base_close_time"] = None

    if {"_entry_time", "_signal_close_time"}.issubset(df.columns):
        add_check("entry_time_gte_signal_close_time", df["_entry_time"] >= df["_signal_close_time"])
    else:
        counts["entry_time_gte_signal_close_time"] = None

    if {"_base_pivot_confirmed_time", "_signal_close_time"}.issubset(df.columns):
        populated = df["base_pivot_confirmed_time"].fillna("").astype(str).str.len() > 0
        ok = (~populated) | (df["_base_pivot_confirmed_time"] <= df["_signal_close_time"])
        add_check("base_pivot_confirmed_time_lte_signal_close_time", ok)
    else:
        counts["base_pivot_confirmed_time_lte_signal_close_time"] = None

    if {"_context_pivot_confirmed_time", "_signal_close_time"}.issubset(df.columns):
        populated = df["context_pivot_confirmed_time"].fillna("").astype(str).str.len() > 0
        ok = (~populated) | (df["_context_pivot_confirmed_time"] <= df["_signal_close_time"])
        add_check("context_pivot_confirmed_time_lte_signal_close_time", ok)
    else:
        counts["context_pivot_confirmed_time_lte_signal_close_time"] = None

    if {"_exit_time", "_entry_time"}.issubset(df.columns):
        populated = df["exit_time"].fillna("").astype(str).str.len() > 0
        ok = (~populated) | (df["_exit_time"] >= df["_entry_time"])
        add_check("exit_time_gte_entry_time", ok)
    else:
        counts["exit_time_gte_entry_time"] = None

    viol = pd.concat(violations, ignore_index=True) if violations else df.iloc[0:0].copy()
    viol_csv = prefix.with_name(prefix.name + "_violations.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    viol.to_csv(viol_csv, index=False, encoding="utf-8-sig")

    checked = {k: v for k, v in counts.items() if v is not None}
    summary = {
        "source": str(src),
        "rows": int(len(df)),
        "checks": counts,
        "total_violations": int(sum(checked.values())) if checked else None,
        "violations_csv": str(viol_csv),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("audit_mochipoyo_timing")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
