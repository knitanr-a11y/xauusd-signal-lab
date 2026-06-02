#!/usr/bin/env python3
"""Evaluate GOLD V2 AI tag Phase 1 results.

Joins AI tags with the hidden truth file and writes summaries under FX_OUTPUTS.
This script does not call any API, MT5, or Discord.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd


def pf_from_r(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    wins = sum(v for v in vals if v > 0)
    losses = -sum(v for v in vals if v < 0)
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def summarize(df: pd.DataFrame, group_col: str, r_col: str = "selected_profit_r") -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(group_col, dropna=False):
        r = g[r_col].fillna(0).astype(float).tolist()
        rows.append({
            group_col: key,
            "count": int(len(g)),
            "win_count": int((g[r_col] > 0).sum()),
            "loss_count": int((g[r_col] < 0).sum()),
            "win_rate": float((g[r_col] > 0).mean()) if len(g) else 0.0,
            "pf": pf_from_r(r),
            "total_r": float(sum(r)),
            "avg_r": float(np.mean(r)) if r else 0.0,
            "blocked_loss_r_if_blocked": float(-sum(v for v in r if v < 0)),
            "missed_win_r_if_blocked": float(sum(v for v in r if v > 0)),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["count", "total_r"], ascending=[False, False])


def parse_tag_list(value) -> List[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [str(x).strip() for x in obj if str(x).strip()]
    except Exception:
        pass
    text = text.strip("[]")
    out = []
    for part in text.split(","):
        tag = part.strip().strip("'\"")
        if tag:
            out.append(tag)
    return out


def explode_tags(df: pd.DataFrame, tag_col: str) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        for tag in parse_tag_list(row.get(tag_col, "")):
            item = row.to_dict()
            item["tag"] = tag
            rows.append(item)
    return pd.DataFrame(rows)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tags", required=True)
    p.add_argument("--truth", required=True)
    p.add_argument("--outdir", required=True)
    args = p.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    tags = pd.read_csv(args.tags)
    truth = pd.read_csv(args.truth)
    df = tags.merge(truth, on="snapshot_id", how="left", suffixes=("_ai", ""))
    joined_path = outdir / "gold_v2_ai_phase1_joined_for_eval.csv"
    df.to_csv(joined_path, index=False, encoding="utf-8-sig")

    summary_files = []
    for col in ["api_status", "decision", "stack_permission", "reason_code", "test_month", "regime", "top_direction"]:
        if col in df.columns:
            s = summarize(df, col)
            path = outdir / f"gold_v2_ai_phase1_summary_by_{col}.csv"
            s.to_csv(path, index=False, encoding="utf-8-sig")
            summary_files.append(path)

    for tag_col in ["quality_tags", "risk_tags", "block_tags"]:
        if tag_col in df.columns:
            exploded = explode_tags(df, tag_col)
            exploded_path = outdir / f"gold_v2_ai_phase1_exploded_{tag_col}.csv"
            exploded.to_csv(exploded_path, index=False, encoding="utf-8-sig")
            if len(exploded):
                s = summarize(exploded, "tag")
                path = outdir / f"gold_v2_ai_phase1_summary_by_{tag_col}.csv"
                s.to_csv(path, index=False, encoding="utf-8-sig")
                summary_files.append(path)

    if "decision" in df.columns and "selected_profit_r" in df.columns:
        df["blocked_by_decision_or_stack"] = (
            df["decision"].astype(str).eq("BLOCK") | df["stack_permission"].astype(str).eq("BLOCK")
        )
        kept = df[~df["blocked_by_decision_or_stack"]]
        blocked = df[df["blocked_by_decision_or_stack"]]
        replay = pd.DataFrame([{
            "policy": "block_if_decision_or_stack_BLOCK",
            "all_count": len(df),
            "kept_count": len(kept),
            "blocked_count": len(blocked),
            "all_pf": pf_from_r(df["selected_profit_r"].fillna(0).astype(float)),
            "kept_pf": pf_from_r(kept["selected_profit_r"].fillna(0).astype(float)),
            "blocked_pf": pf_from_r(blocked["selected_profit_r"].fillna(0).astype(float)),
            "all_total_r": float(df["selected_profit_r"].fillna(0).sum()),
            "kept_total_r": float(kept["selected_profit_r"].fillna(0).sum()),
            "blocked_total_r": float(blocked["selected_profit_r"].fillna(0).sum()),
            "blocked_loss_r": float(-blocked.loc[blocked["selected_profit_r"] < 0, "selected_profit_r"].sum()),
            "missed_win_r": float(blocked.loc[blocked["selected_profit_r"] > 0, "selected_profit_r"].sum()),
        }])
        replay.to_csv(outdir / "gold_v2_ai_phase1_block_replay_summary.csv", index=False, encoding="utf-8-sig")

    print(f"wrote joined file: {joined_path}")
    for f in summary_files:
        print(f"wrote summary: {f}")
    print(f"wrote outputs to: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
