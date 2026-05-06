#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filter Mochipoyo event candidates to rows whose first-touch data exists.

This prevents old H1/H4/D1-derived events from becoming NO_DATA when M1/M5
history starts later than the higher-timeframe CSVs.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd


TOUCH_TF_BY_BASE_TF = {"M1": "M1", "M5": "M5", "M15": "M5", "H1": "M5"}


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_time_range(path: Path) -> tuple[pd.Timestamp, pd.Timestamp, int]:
    df = pd.read_csv(path, sep=sniff_sep(path), encoding="utf-8-sig", usecols=["time"])
    t = pd.to_datetime(df["time"], errors="coerce").dropna().sort_values()
    if t.empty:
        raise RuntimeError(f"No valid time rows: {path}")
    return pd.Timestamp(t.iloc[0]), pd.Timestamp(t.iloc[-1]), int(len(t))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--events-csv", required=True)
    p.add_argument("--m1-csv", required=True)
    p.add_argument("--m5-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--summary-json", default=None)
    args = p.parse_args()

    ranges = {
        "M1": read_time_range(Path(args.m1_csv)),
        "M5": read_time_range(Path(args.m5_csv)),
    }
    df = pd.read_csv(args.events_csv, encoding="utf-8-sig")
    before = len(df)
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    df["touch_tf_expected"] = df["base_tf"].astype(str).str.upper().map(lambda x: TOUCH_TF_BY_BASE_TF.get(x, "M5"))

    keep = []
    drop_reasons = []
    for _, row in df.iterrows():
        tf = str(row["touch_tf_expected"])
        t = row["entry_time"]
        if pd.isna(t):
            keep.append(False); drop_reasons.append("invalid_entry_time"); continue
        start, end, _ = ranges[tf]
        if t < start:
            keep.append(False); drop_reasons.append(f"before_{tf}_history")
        elif t > end:
            keep.append(False); drop_reasons.append(f"after_{tf}_history")
        else:
            keep.append(True); drop_reasons.append("")
    df["touch_range_drop_reason"] = drop_reasons
    kept_df = df[pd.Series(keep, index=df.index)].copy().sort_values("entry_time", kind="mergesort")
    dropped_df = df[~pd.Series(keep, index=df.index)].copy()

    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json) if args.summary_json else output_csv.with_suffix(".summary.json")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    kept_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    summary = {
        "input_rows": int(before),
        "output_rows": int(len(kept_df)),
        "dropped_rows": int(len(dropped_df)),
        "output_csv": str(output_csv),
        "ranges": {tf: {"start": str(v[0]), "end": str(v[1]), "rows": v[2]} for tf, v in ranges.items()},
        "dropped_by_reason": dropped_df["touch_range_drop_reason"].value_counts().to_dict() if len(dropped_df) else {},
        "by_pair": kept_df["pair_name"].value_counts().to_dict() if len(kept_df) else {},
        "by_rank": kept_df["candidate_rank"].value_counts().to_dict() if len(kept_df) else {},
        "by_direction": kept_df["direction"].value_counts().to_dict() if len(kept_df) else {},
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("filter_mochipoyo_events_by_touch_range")
    print(f"input_rows: {before}")
    print(f"output_rows: {len(kept_df)}")
    print(f"dropped_rows: {len(dropped_df)}")
    print(f"output_csv: {output_csv}")
    print(f"summary_json: {summary_json}")
    print("dropped_by_reason:")
    print(pd.Series(summary["dropped_by_reason"]).to_string() if summary["dropped_by_reason"] else "none")
    if len(kept_df):
        print("by_pair:")
        print(kept_df["pair_name"].value_counts().to_string())
        print("by_rank:")
        print(kept_df["candidate_rank"].value_counts().to_string())
        print("by_direction:")
        print(kept_df["direction"].value_counts().to_string())
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
