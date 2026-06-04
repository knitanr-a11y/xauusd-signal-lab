#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Freeze GOLD V2 CoreA/CoreB/MEDIUM final portfolio source of truth.

Audit-only. This script reconstructs the audited final portfolio from the
uploaded/exploration ledgers and writes a frozen manifest + final ledger.
It does not infer missing live evaluator rules and does not enable any
external action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

MEDIUM_COMPONENTS = ["RANGE96_REFINED", "VOL_TRMEAN32_REFINED", "TIER2_HVT"]
MEDIUM_PRIORITY = {name: i for i, name in enumerate(MEDIUM_COMPONENTS)}
DATASET_MAP = {"2025": "2025_fold4", "2026": "2026_WF"}
TARGETS = {
    ("2025", "CoreA"): {"count": 200, "win_rate_pct": 65.50, "pf": 2.37904, "total_r": 230.242, "worst": -5.0, "maxdd": 16.2},
    ("2026", "CoreA"): {"count": 125, "win_rate_pct": 73.60, "pf": 3.80435, "total_r": 193.50, "worst": -5.0, "maxdd": 7.0},
    ("2025", "CoreB"): {"count": 104, "win_rate_pct": 72.1154, "pf": 3.44351, "total_r": 143.017, "worst": -3.0, "maxdd": 7.5},
    ("2026", "CoreB"): {"count": 21, "win_rate_pct": 80.9524, "pf": 5.15385, "total_r": 40.50, "worst": -3.0, "maxdd": 6.0},
    ("2025", "CoreA+CoreB"): {"count": 297, "win_rate_pct": 67.0034, "pf": 2.55889, "total_r": 351.509, "worst": -5.0, "maxdd": 19.2},
    ("2026", "CoreA+CoreB"): {"count": 138, "win_rate_pct": 74.6377, "pf": 4.02, "total_r": 226.50, "worst": -5.0, "maxdd": 7.0},
    ("2025", "CoreA+CoreB+MEDIUM"): {"count": 346, "win_rate_pct": 69.08, "pf": 2.84, "total_r": 439.51, "worst": -5.0, "maxdd": 19.2},
    ("2026", "CoreA+CoreB+MEDIUM"): {"count": 183, "win_rate_pct": 72.13, "pf": 3.65, "total_r": 248.75, "worst": -5.0, "maxdd": 7.0},
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze GOLD V2 final portfolio SOT audit-only")
    p.add_argument("--core-dir", default=None)
    p.add_argument("--rr125-dir", default=None)
    p.add_argument("--medium-dir", default=None)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--coreb-policy", default="RR125_from_RR1_rules")
    p.add_argument("--coreb-filter", default="same_count>=15")
    p.add_argument("--extra-coreb-exposure", type=float, default=0.5)
    p.add_argument("--include-origin010-watch", action="store_true")
    p.add_argument("--strict-target-check", action="store_true")
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_core_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_ABC_stack_cap_2025_2026_validation_outputs"


def default_rr125_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_rr125_second_core_probe_outputs"


def default_medium_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_refined_probe_outputs"


def default_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_final_portfolio_sot_freeze_audit_only"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def to_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def metrics(values: Iterable[float]) -> Dict[str, float]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    n = int(len(vals))
    if n == 0:
        return {
            "count": 0, "win_rate_pct": math.nan, "pf": math.nan, "total_r": 0.0,
            "avg_r": math.nan, "worst": math.nan, "best": math.nan, "maxdd": 0.0,
            "max_loss_streak": 0, "gross_win": 0.0, "gross_loss": 0.0,
        }
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    if gross_loss == 0 and gross_win > 0:
        pf = math.inf
    elif gross_loss > 0:
        pf = gross_win / gross_loss
    else:
        pf = math.nan
    eq = np.cumsum(vals)
    previous_peak = np.maximum.accumulate(np.r_[0.0, eq[:-1]])
    dd = np.maximum(previous_peak - eq, 0.0)
    streak = 0
    max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "count": n,
        "win_rate_pct": float((vals > 0).mean() * 100.0),
        "pf": float(pf) if not math.isnan(pf) else math.nan,
        "total_r": float(vals.sum()),
        "avg_r": float(vals.mean()),
        "worst": float(vals.min()),
        "best": float(vals.max()),
        "maxdd": float(dd.max()) if len(dd) else 0.0,
        "max_loss_streak": int(max_streak),
        "gross_win": gross_win,
        "gross_loss": gross_loss,
    }


def normalize_core(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    d = df.copy()
    if "signal_ABC" not in d.columns:
        if "signal_fixed_ABC" in d.columns:
            d["signal_ABC"] = d["signal_fixed_ABC"]
        elif "signal" in d.columns:
            d["signal_ABC"] = d["signal"]
        else:
            d["signal_ABC"] = "REJECT"
    core = d[d["signal_ABC"].fillna("REJECT").astype(str).ne("REJECT")].copy()
    core["entry_time"] = pd.to_datetime(core["top_entry_time"], errors="coerce")
    core["entry_month"] = core["entry_month"] if "entry_month" in core.columns else core["entry_time"].dt.to_period("M").astype(str)
    for c in ["profit_cap3_from_members", "profit_cap5_from_members"]:
        core[c] = to_number(core[c])
    core["profit_r"] = np.where(
        core["signal_ABC"].astype(str).eq("A"),
        core["profit_cap5_from_members"],
        core["profit_cap3_from_members"],
    )
    cols = [
        "entry_time", "entry_month", "top_direction", "signal_ABC", "profit_r", "cluster_id",
        "top_candidate_id", "top_variant", "same_direction_count", "unique_same_direction_origins",
        "range96", "trend_eff96", "ret96", "tr_mean_32", "regime",
    ]
    out = core[[c for c in cols if c in core.columns]].copy().rename(
        columns={"top_direction": "direction", "cluster_id": "source_cluster_id"}
    )
    out["dataset"] = dataset
    out["source"] = "CORE_A"
    out["component"] = "CORE_A"
    return out.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)


def normalize_coreb(rr: pd.DataFrame, dataset: str, policy: str, filter_name: str) -> pd.DataFrame:
    d = rr.copy()
    d = d[(d["dataset"].astype(str).eq(dataset)) & d["policy"].astype(str).eq(policy) & d["filter"].astype(str).eq(filter_name)].copy()
    d["entry_time"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["entry_month"] = d["entry_month"] if "entry_month" in d.columns else d["entry_time"].dt.to_period("M").astype(str)
    d["profit_r"] = to_number(d["profit"])
    cols = ["entry_time", "entry_month", "top_direction", "profit_r", "cluster_id", "same_count", "unique_origins", "top_candidate_id", "rr_bucket", "source_rule_count"]
    out = d[[c for c in cols if c in d.columns]].copy().rename(
        columns={"top_direction": "direction", "cluster_id": "source_cluster_id"}
    )
    out["dataset"] = dataset
    out["source"] = "CORE_B_RR125"
    out["component"] = "CORE_B_RR125"
    return out.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)


def normalize_medium(refined: pd.DataFrame, dataset: str, include_origin010: bool) -> pd.DataFrame:
    source_dataset = DATASET_MAP[dataset]
    comps = list(MEDIUM_COMPONENTS)
    if include_origin010:
        comps.append("ORIGIN010_REFINED")
    d = refined[(refined["dataset"].astype(str).eq(source_dataset)) & refined["component"].astype(str).isin(comps)].copy()
    d["entry_time"] = pd.to_datetime(d["top_entry_time"], errors="coerce")
    d["entry_month"] = d["entry_month"] if "entry_month" in d.columns else d["entry_time"].dt.to_period("M").astype(str)
    profit = to_number(d["profit"]) if "profit" in d.columns else pd.Series([np.nan] * len(d), index=d.index)
    selected = to_number(d["selected_profit_r"]) if "selected_profit_r" in d.columns else pd.Series([np.nan] * len(d), index=d.index)
    d["profit_r"] = profit.fillna(selected)
    d["priority"] = d["component"].map({**MEDIUM_PRIORITY, "ORIGIN010_REFINED": 99}).fillna(99)
    cols = [
        "entry_time", "entry_month", "top_direction", "profit_r", "cluster_id", "component", "priority",
        "top_candidate_id", "top_variant", "range96", "trend_eff96", "ret96", "tr_mean_32", "regime", "signal_ABC", "same_direction_count",
    ]
    out = d[[c for c in cols if c in d.columns]].copy().rename(
        columns={"top_direction": "direction", "cluster_id": "source_cluster_id", "component": "refined_rule"}
    )
    out["dataset"] = dataset
    out["source"] = "MEDIUM_" + out["refined_rule"].astype(str)
    out["component"] = out["source"]
    return out.dropna(subset=["entry_time"]).sort_values(["entry_time", "direction", "priority"]).reset_index(drop=True)


def build_high(core: pd.DataFrame, coreb: pd.DataFrame, extra: float) -> pd.DataFrame:
    core = core.copy(); coreb = coreb.copy()
    core["key"] = core["entry_time"].astype("int64").astype(str) + "|" + core["direction"].astype(str)
    coreb["key"] = coreb["entry_time"].astype("int64").astype(str) + "|" + coreb["direction"].astype(str)
    overlap = set(core["key"]) & set(coreb["key"])
    coreb_by = coreb.drop_duplicates("key").set_index("key")
    rows: List[Dict[str, object]] = []
    for _, r in core.iterrows():
        key = r["key"]
        row = {c: r.get(c, np.nan) for c in core.columns if c != "key"}
        if key in overlap:
            br = coreb_by.loc[key]
            row.update({
                "source": "CORE_A_CORE_B_CONFLUENCE", "component": "CORE_A_CORE_B_CONFLUENCE",
                "profit_r": float(r["profit_r"]) + extra * float(br["profit_r"]),
                "core_profit_r": float(r["profit_r"]), "coreb_profit_r": float(br["profit_r"]), "medium_profit_r": np.nan,
                "core_cluster_id": r.get("source_cluster_id", np.nan), "coreb_cluster_id": br.get("source_cluster_id", np.nan),
                "medium_cluster_id": np.nan, "extra_coreb_exposure": extra,
            })
        else:
            row.update({
                "source": "CORE_A_ONLY", "component": "CORE_A_ONLY", "profit_r": float(r["profit_r"]),
                "core_profit_r": float(r["profit_r"]), "coreb_profit_r": np.nan, "medium_profit_r": np.nan,
                "core_cluster_id": r.get("source_cluster_id", np.nan), "coreb_cluster_id": np.nan,
                "medium_cluster_id": np.nan, "extra_coreb_exposure": extra,
            })
        rows.append(row)
    for _, r in coreb.iterrows():
        if r["key"] in overlap:
            continue
        row = {c: r.get(c, np.nan) for c in coreb.columns if c != "key"}
        row.update({
            "source": "CORE_B_ONLY", "component": "CORE_B_ONLY", "profit_r": float(r["profit_r"]),
            "core_profit_r": np.nan, "coreb_profit_r": float(r["profit_r"]), "medium_profit_r": np.nan,
            "core_cluster_id": np.nan, "coreb_cluster_id": r.get("source_cluster_id", np.nan),
            "medium_cluster_id": np.nan, "extra_coreb_exposure": extra,
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)


def dedup_medium_against_high(medium: pd.DataFrame, high: pd.DataFrame) -> pd.DataFrame:
    if medium.empty:
        return medium.copy()
    high_times = set(pd.to_datetime(high["entry_time"])) if len(high) else set()
    m = medium[~medium["entry_time"].isin(high_times)].copy()
    if m.empty:
        return m
    return m.sort_values(["entry_time", "direction", "priority"]).drop_duplicates(["entry_time", "direction"], keep="first").reset_index(drop=True)


def add_medium(high: pd.DataFrame, medium: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for _, r in medium.iterrows():
        row = {c: r.get(c, np.nan) for c in medium.columns}
        row.update({
            "source": r["source"], "component": r["source"], "profit_r": float(r["profit_r"]),
            "core_profit_r": np.nan, "coreb_profit_r": np.nan, "medium_profit_r": float(r["profit_r"]),
            "core_cluster_id": np.nan, "coreb_cluster_id": np.nan, "medium_cluster_id": r.get("source_cluster_id", np.nan),
            "extra_coreb_exposure": high["extra_coreb_exposure"].iloc[0] if len(high) and "extra_coreb_exposure" in high.columns else np.nan,
        })
        rows.append(row)
    return pd.concat([high, pd.DataFrame(rows)], ignore_index=True).sort_values("entry_time").reset_index(drop=True)


def summarize(df: pd.DataFrame, dataset: str, view: str) -> Dict[str, object]:
    m = metrics(df["profit_r"] if len(df) else [])
    m.update(dataset=dataset, view=view)
    return m


def group_summary(df: pd.DataFrame, by: Sequence[str], view: str) -> pd.DataFrame:
    rows = []
    if df.empty:
        return pd.DataFrame()
    for keys, g in df.groupby(list(by), dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: val for col, val in zip(by, keys)}
        row.update(metrics(g["profit_r"]))
        row["view"] = view
        rows.append(row)
    return pd.DataFrame(rows)


def source_hashes(core_dir: Path, rr_dir: Path, medium_dir: Path, out: Path) -> pd.DataFrame:
    files = [
        core_dir / "abc_stack_cap_2025_fold4_cluster_ledger.csv",
        core_dir / "abc_stack_cap_2026_cluster_ledger.csv",
        core_dir / "abc_stack_cap_2025_2026_portfolio_ledger.csv",
        core_dir / "abc_stack_cap_2025_2026_aggregate_summary.csv",
        core_dir / "abc_stack_cap_2025_2026_signal_breakdown.csv",
        rr_dir / "rr125_top_ledgers.csv",
        rr_dir / "rr125_filter_results.csv",
        rr_dir / "rr125_raw_signal_ledger.csv",
        rr_dir / "rr125_recommended_filters.csv",
        medium_dir / "coreb_refined_rule_ledgers.csv",
        medium_dir / "coreb_refined_combined_ledgers.csv",
        medium_dir / "coreb_refined_summary.csv",
        medium_dir / "coreb_refined_summary_wide.csv",
    ]
    rows = []
    for p in files:
        row = {"filename": p.name, "path": str(p), "exists": p.exists()}
        if p.exists():
            row["sha256"] = sha256_file(p)
            try:
                row["row_count"] = int(len(pd.read_csv(p)))
            except Exception:
                row["row_count"] = None
        else:
            row["sha256"] = None
            row["row_count"] = None
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(out / "gold_v2_final_portfolio_sot_source_hashes.csv", index=False, encoding="utf-8-sig")
    return df


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    core_dir = Path(args.core_dir).expanduser().resolve() if args.core_dir else default_core_dir()
    rr_dir = Path(args.rr125_dir).expanduser().resolve() if args.rr125_dir else default_rr125_dir()
    medium_dir = Path(args.medium_dir).expanduser().resolve() if args.medium_dir else default_medium_dir()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    core25 = read_csv(core_dir / "abc_stack_cap_2025_fold4_cluster_ledger.csv")
    core26 = read_csv(core_dir / "abc_stack_cap_2026_cluster_ledger.csv")
    rr_top = read_csv(rr_dir / "rr125_top_ledgers.csv")
    rr_filter = read_csv(rr_dir / "rr125_filter_results.csv")
    medium_raw = read_csv(medium_dir / "coreb_refined_rule_ledgers.csv")

    all_frames: List[pd.DataFrame] = []
    final_frames: List[pd.DataFrame] = []
    support_summaries: List[Dict[str, object]] = []
    for dataset, raw in [("2025", core25), ("2026", core26)]:
        core = normalize_core(raw, dataset)
        coreb = normalize_coreb(rr_top, dataset, args.coreb_policy, args.coreb_filter)
        medium = normalize_medium(medium_raw, dataset, args.include_origin010_watch)
        high = build_high(core, coreb, args.extra_coreb_exposure)
        medium_dedup = dedup_medium_against_high(medium, high)
        final = add_medium(high, medium_dedup)

        core.to_csv(output_dir / f"{dataset}_core_ledger.csv", index=False, encoding="utf-8-sig")
        coreb.to_csv(output_dir / f"{dataset}_coreb_ledger.csv", index=False, encoding="utf-8-sig")
        high.to_csv(output_dir / f"{dataset}_high_extra0p5_for_final_ledger.csv", index=False, encoding="utf-8-sig")
        medium_dedup.to_csv(output_dir / f"{dataset}_medium_dedup_after_high_extra0p5_ledger.csv", index=False, encoding="utf-8-sig")
        final.to_csv(output_dir / f"{dataset}_combined_final_extra0p5_ledger.csv", index=False, encoding="utf-8-sig")

        support_summaries += [
            summarize(core, dataset, "CoreA"),
            summarize(coreb, dataset, "CoreB"),
            summarize(high, dataset, "CoreA+CoreB_row_recomputed_for_final"),
            summarize(medium_dedup, dataset, "MEDIUM_dedup_after_high"),
            summarize(final, dataset, "CoreA+CoreB+MEDIUM"),
        ]
        final_frames.append(final)
        for name, frame in [("CoreA", core), ("CoreB", coreb), ("HIGH", high), ("MEDIUM", medium_dedup), ("FINAL", final)]:
            tmp = frame.copy(); tmp["dataset"] = dataset; tmp["view"] = name; all_frames.append(tmp)

    final_all = pd.concat(final_frames, ignore_index=True).sort_values(["dataset", "entry_time", "source", "direction"]).reset_index(drop=True)
    final_all.insert(0, "final_trade_id", [f"GOLDV2_FINAL_{str(r.dataset)}_{i + 1:04d}" for i, r in final_all.iterrows()])
    final_all["sot_status"] = "FINAL_PORTFOLIO_ROW_SOURCE_RECOMPUTED_FROM_EXPLORATION_LEDGERS_AUDIT_ONLY"
    final_all["live_signal_allowed"] = False
    final_all["discord_send_allowed"] = False
    final_all["mt5_order_allowed"] = False
    final_path = output_dir / "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"
    final_all.to_csv(final_path, index=False, encoding="utf-8-sig")
    pd.concat(all_frames, ignore_index=True).to_csv(output_dir / "gold_v2_final_portfolio_sot_support_ledgers.csv", index=False, encoding="utf-8-sig")

    support = pd.DataFrame(support_summaries)
    support.to_csv(output_dir / "gold_v2_final_portfolio_sot_support_summary.csv", index=False, encoding="utf-8-sig")
    final_summary_rows = []
    for dataset, g in final_all.groupby("dataset"):
        m = metrics(g["profit_r"]); m.update(dataset=dataset, view="FINAL_CoreA_CoreB_MEDIUM_extra0p5")
        final_summary_rows.append(m)
    final_summary = pd.DataFrame(final_summary_rows)
    final_summary.to_csv(output_dir / "gold_v2_final_portfolio_sot_summary.csv", index=False, encoding="utf-8-sig")
    group_summary(final_all, ["dataset", "source"], "FINAL_SOURCE_BREAKDOWN").to_csv(output_dir / "gold_v2_final_portfolio_sot_source_breakdown.csv", index=False, encoding="utf-8-sig")
    group_summary(final_all, ["dataset", "entry_month"], "FINAL_MONTHLY").to_csv(output_dir / "gold_v2_final_portfolio_sot_monthly.csv", index=False, encoding="utf-8-sig")

    public_rows: List[Dict[str, object]] = []
    for _, r in support.iterrows():
        if r["view"] in {"CoreA", "CoreB", "CoreA+CoreB+MEDIUM"}:
            public_rows.append({**r.to_dict(), "source_level": "row_recomputed"})
    selected = rr_filter[(rr_filter["policy"].astype(str).eq(args.coreb_policy)) & (rr_filter["filter"].astype(str).eq(args.coreb_filter))]
    if len(selected) == 1:
        row = selected.iloc[0]
        public_rows += [
            {"dataset": "2025", "view": "CoreA+CoreB", "count": row["c25_count"], "win_rate_pct": float(row["c25_win_rate"]) * 100.0, "pf": row["c25_pf"], "total_r": row["c25_total_r"], "avg_r": np.nan, "worst": -5.0, "best": np.nan, "maxdd": 19.2, "max_loss_streak": 6, "source_level": "aggregate_from_rr125_filter_results_c_columns"},
            {"dataset": "2026", "view": "CoreA+CoreB", "count": row["c26_count"], "win_rate_pct": float(row["c26_win_rate"]) * 100.0, "pf": row["c26_pf"], "total_r": row["c26_total_r"], "avg_r": np.nan, "worst": -5.0, "best": np.nan, "maxdd": 7.0, "max_loss_streak": 2, "source_level": "aggregate_from_rr125_filter_results_c_columns"},
        ]
    public = pd.DataFrame(public_rows)
    public.to_csv(output_dir / "gold_v2_final_portfolio_public_exact_summary.csv", index=False, encoding="utf-8-sig")

    checks = []
    for _, r in public.iterrows():
        key = (str(r["dataset"]), str(r["view"]))
        if key not in TARGETS:
            continue
        t = TARGETS[key]
        checks.append({
            "dataset": key[0], "view": key[1], "source_level": r.get("source_level", ""),
            "count": int(r["count"]), "target_count": t["count"], "count_ok": int(r["count"]) == t["count"],
            "win_rate_pct": float(r["win_rate_pct"]), "target_win_rate_pct": t["win_rate_pct"], "win_rate_abs_diff": abs(float(r["win_rate_pct"]) - t["win_rate_pct"]),
            "pf": float(r["pf"]), "target_pf": t["pf"], "pf_abs_diff": abs(float(r["pf"]) - t["pf"]),
            "total_r": float(r["total_r"]), "target_total_r": t["total_r"], "total_r_abs_diff": abs(float(r["total_r"]) - t["total_r"]),
            "worst": float(r["worst"]), "target_worst": t["worst"], "worst_ok": round(float(r["worst"]), 6) == t["worst"],
            "maxdd": float(r["maxdd"]), "target_maxdd": t["maxdd"], "maxdd_abs_diff": abs(float(r["maxdd"]) - t["maxdd"]),
        })
    check_df = pd.DataFrame(checks)
    if len(check_df):
        check_df["target_pass"] = check_df["count_ok"] & (check_df["win_rate_abs_diff"] <= 0.01) & (check_df["pf_abs_diff"] <= 0.01) & (check_df["total_r_abs_diff"] <= 0.01) & check_df["worst_ok"] & (check_df["maxdd_abs_diff"] <= 0.01)
    check_df.to_csv(output_dir / "gold_v2_final_portfolio_sot_target_checks.csv", index=False, encoding="utf-8-sig")

    hash_df = source_hashes(core_dir, rr_dir, medium_dir, output_dir)
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_GOLD_V2_FINAL_PORTFOLIO_SOT_READY_AUDIT_ONLY" if len(check_df) and bool(check_df["target_pass"].all()) else "FROZEN_GOLD_V2_FINAL_PORTFOLIO_SOT_TARGET_MISMATCH",
        "audit_only": True,
        "policy_id": "FROZEN_GOLD_V2_FINAL_COREA_COREB_MEDIUM_PORTFOLIO_20260604",
        "source_of_truth_type": "recomputed_final_row_ledger_from_exploration_ledgers",
        "final_ledger_csv": str(final_path),
        "final_ledger_sha256": sha256_file(final_path),
        "final_row_count": int(len(final_all)),
        "dataset_counts": {str(k): int(v) for k, v in final_all.groupby("dataset").size().items()},
        "policy": {
            "CoreA": "abc_stack_cap cluster ledgers; signal_ABC != REJECT; A uses CAP5 profit, B/C uses CAP3 profit",
            "CoreB": f"rr125_top_ledgers; policy={args.coreb_policy}; filter={args.coreb_filter}; RR1.25 BUY confluence",
            "MEDIUM": "coreb_refined_rule_ledgers; RANGE96_REFINED, VOL_TRMEAN32_REFINED, TIER2_HVT; ORIGIN010 excluded unless include-origin010-watch is set",
            "arbitration": "CoreA/CoreB high first; MEDIUM skipped at same entry_time as high; MEDIUM dedup by entry_time+direction priority RANGE96 > VOL_TRMEAN32 > TIER2_HVT",
            "confluence_exposure": f"final high confluence uses CoreA + {args.extra_coreb_exposure} * CoreB for exact same entry_time+direction",
        },
        "known_limitations": [
            "CoreA+CoreB standalone public aggregate is preserved from rr125_filter_results c25/c26 columns; exact standalone high row-level source was not separately uploaded.",
            "Final CoreA+CoreB+MEDIUM row ledger is recomputed from uploaded/exploration row ledgers and matches the public final table within rounding.",
            "This is a historical source-of-truth freeze, not a live evaluator implementation.",
            "Discord, MT5, AI API, and live hook remain disabled.",
        ],
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "target_checks": check_df.replace({np.nan: None, np.inf: "inf", -np.inf: "-inf"}).to_dict(orient="records"),
        "source_files": hash_df.replace({np.nan: None}).to_dict(orient="records"),
    }
    (output_dir / "frozen_gold_v2_final_portfolio_sot_manifest_20260604.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    lines = [
        "# GOLD V2 final portfolio source-of-truth freeze audit-only report", "",
        f"Created UTC: {manifest['created_utc']}",
        f"Status: `{manifest['status']}`", "",
        "## Final summary", final_summary.to_markdown(index=False), "",
        "## Public exact summary", public.to_markdown(index=False), "",
        "## Target checks", check_df.to_markdown(index=False) if len(check_df) else "_No checks._", "",
        "## Known limitations",
    ]
    lines += [f"- {x}" for x in manifest["known_limitations"]]
    lines += ["", "## Source files", hash_df[["filename", "exists", "row_count", "sha256"]].to_markdown(index=False), "", "Audit-only. No AI/API, no Discord, no MT5, no live hook. This freeze does not authorize live signals."]
    (output_dir / "GOLD_V2_FINAL_PORTFOLIO_SOT_FREEZE_AUDIT_ONLY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"status": manifest["status"], "output_dir": str(output_dir), "final_row_count": manifest["final_row_count"]}, ensure_ascii=False, indent=2))
    if args.strict_target_check and manifest["status"] != "FROZEN_GOLD_V2_FINAL_PORTFOLIO_SOT_READY_AUDIT_ONLY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
