#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare reference and regenerated GOLD_MOCHIPOYO_RR12_REFINED_205 trade CSVs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

IDENTITY_COLUMNS = ["entry_time", "pair_name", "candidate_rank", "direction", "entry_price", "base_time", "signal_time"]
NUMERIC_COLUMNS = ["entry_price", "sl_price", "tp_price", "risk_distance", "r_result", "total_score", "context_score", "base_score"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    for c in ["entry_time", "base_time", "signal_time", "exit_time"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    for c in NUMERIC_COLUMNS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(8)
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].fillna("").astype(str)
    return df


def add_key(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in IDENTITY_COLUMNS if c in df.columns]
    if not cols:
        raise RuntimeError("No identity columns available")
    out = df.copy()
    out["_key"] = out[cols].fillna("").astype(str).agg("|".join, axis=1)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reference-csv", required=True)
    p.add_argument("--regenerated-csv", required=True)
    p.add_argument("--output-prefix", default="data/results/mochipoyo/reproduce_gold_mochipoyo_rr12_refined_205/compare")
    args = p.parse_args()

    ref_path = Path(args.reference_csv)
    regen_path = Path(args.regenerated_csv)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    ref = add_key(read_csv(ref_path))
    regen = add_key(read_csv(regen_path))
    ref_keys = set(ref["_key"])
    regen_keys = set(regen["_key"])

    missing = ref[ref["_key"].isin(sorted(ref_keys - regen_keys))].copy()
    extra = regen[regen["_key"].isin(sorted(regen_keys - ref_keys))].copy()

    common_cols = [c for c in ref.columns if c in regen.columns and c != "_key"]
    ref_common = ref[ref["_key"].isin(ref_keys & regen_keys)].sort_values("_key").reset_index(drop=True)
    regen_common = regen[regen["_key"].isin(ref_keys & regen_keys)].sort_values("_key").reset_index(drop=True)

    mismatches = []
    for i in range(min(len(ref_common), len(regen_common))):
        key = ref_common.at[i, "_key"]
        for col in common_cols:
            rv = ref_common.at[i, col]
            gv = regen_common.at[i, col]
            if str(rv) != str(gv):
                mismatches.append({"key": key, "column": col, "reference": str(rv), "regenerated": str(gv)})
                if len(mismatches) >= 5000:
                    break
        if len(mismatches) >= 5000:
            break

    missing_csv = prefix.with_name(prefix.name + "_missing_from_regenerated.csv")
    extra_csv = prefix.with_name(prefix.name + "_extra_in_regenerated.csv")
    mismatch_csv = prefix.with_name(prefix.name + "_value_mismatches.csv")
    summary_json = prefix.with_name(prefix.name + "_summary.json")
    missing.to_csv(missing_csv, index=False, encoding="utf-8-sig")
    extra.to_csv(extra_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame(mismatches).to_csv(mismatch_csv, index=False, encoding="utf-8-sig")

    summary = {
        "reference_csv": str(ref_path),
        "regenerated_csv": str(regen_path),
        "reference_rows": int(len(ref)),
        "regenerated_rows": int(len(regen)),
        "reference_sha256": sha256(ref_path),
        "regenerated_sha256": sha256(regen_path),
        "exact_same_file_hash": sha256(ref_path) == sha256(regen_path),
        "identity_key_match": len(ref_keys - regen_keys) == 0 and len(regen_keys - ref_keys) == 0,
        "value_match_on_common_columns": len(mismatches) == 0,
        "missing_from_regenerated": int(len(ref_keys - regen_keys)),
        "extra_in_regenerated": int(len(regen_keys - ref_keys)),
        "value_mismatch_count_capped_5000": int(len(mismatches)),
        "files": {
            "missing_csv": str(missing_csv),
            "extra_csv": str(extra_csv),
            "mismatch_csv": str(mismatch_csv),
        },
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("compare_gold_mochipoyo_reproduction")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
