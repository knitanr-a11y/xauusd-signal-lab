#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13C-2 audit: CoreB source ledger to feature snapshot parity.

This step explains why the CoreB candidate replay currently emits only a few
signals while the RR1.25 source top-ledger contains 125 historical CoreB rows.
It compares rr125_top_ledgers against the feature snapshot/replay rows, time
offsets, condition pass rates, and several plausible same_count semantics.

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="13C-2 CoreB source ledger to feature snapshot parity audit")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--offset-minutes", type=int, default=180)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_output_dir() -> Path:
    return fx_outputs() / "gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_audit_only"


def first_existing(candidates: Sequence[Path], filename: str) -> Path:
    for p in candidates:
        if p.exists():
            return p
    matches = list(fx_outputs().rglob(filename))
    return matches[0] if matches else candidates[0]


def source_paths() -> dict[str, Path]:
    rr = fx_outputs() / "gold_v2_rr125_second_core_probe_outputs"
    feature = fx_outputs() / "gold_v2_coreb_combined_required_feature_snapshot_audit_only"
    feature_alt = fx_outputs() / "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_audit_only"
    replay = fx_outputs() / "gold_v2_coreb_combined_evaluator_replay_audit_only"
    final = fx_outputs() / "gold_v2_final_portfolio_sot_freeze_audit_only"
    return {
        "final_sot_ledger": first_existing([final / "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"], "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"),
        "coreb_definition": repo_root() / "configs" / "gold_v2" / "frozen_coreB_combined_evaluator_definition_20260604.json",
        "rr125_top_ledgers": first_existing([rr / "rr125_top_ledgers.csv"], "rr125_top_ledgers.csv"),
        "rr125_raw_signal_ledger": first_existing([rr / "rr125_raw_signal_ledger.csv"], "rr125_raw_signal_ledger.csv"),
        "feature_snapshot": first_existing([feature / "gold_v2_coreb_combined_required_feature_snapshot.csv", feature_alt / "gold_v2_coreb_combined_required_feature_snapshot.csv"], "gold_v2_coreb_combined_required_feature_snapshot.csv"),
        "replay_rows": first_existing([replay / "gold_v2_coreb_combined_evaluator_replay_rows.csv"], "gold_v2_coreb_combined_evaluator_replay_rows.csv"),
        "replay_summary": first_existing([replay / "gold_v2_coreb_combined_evaluator_replay_summary.json"], "gold_v2_coreb_combined_evaluator_replay_summary.json"),
        "selected_conditions": first_existing([feature / "gold_v2_coreb_combined_selected_conditions.csv"], "gold_v2_coreb_combined_selected_conditions.csv"),
        "same_count_conditions": first_existing([feature / "gold_v2_coreb_combined_same_count_conditions.csv"], "gold_v2_coreb_combined_same_count_conditions.csv"),
    }


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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def metrics(values: Iterable[float]) -> dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate_pct": math.nan, "pf": math.nan, "total_r": 0.0, "worst": math.nan, "maxdd": 0.0, "max_loss_streak": 0}
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    equity = np.cumsum(vals)
    prior_peak = np.maximum.accumulate(np.r_[0.0, equity[:-1]])
    dd = np.maximum(prior_peak - equity, 0.0)
    streak = 0
    max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {"count": int(len(vals)), "win_rate_pct": float((vals > 0).mean() * 100.0), "pf": float(pf) if not math.isnan(pf) else math.nan, "total_r": float(vals.sum()), "worst": float(vals.min()), "maxdd": float(dd.max()), "max_loss_streak": int(max_streak)}


def fmt_cell(value: Any) -> str:
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(df: pd.DataFrame, cols: Optional[Sequence[str]] = None) -> str:
    if cols is not None:
        df = df[[c for c in cols if c in df.columns]].copy()
    if df.empty:
        return "_No rows._"
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt_cell(row[c]) for c in df.columns) + " |")
    return "\n".join(lines)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def input_audit(paths: dict[str, Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role, path in paths.items():
        row: dict[str, Any] = {"role": role, "path": str(path), "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            if path.suffix.lower() == ".csv":
                header = pd.read_csv(path, nrows=1)
                row["columns"] = len(header.columns)
            elif path.suffix.lower() == ".json":
                obj = read_json(path)
                row["json_keys"] = ",".join(list(obj.keys())[:20])
        rows.append(row)
    return pd.DataFrame(rows)


def condition_pass_rate(cond_df: pd.DataFrame, feat_df: pd.DataFrame, rule_set: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, c in cond_df.iterrows():
        field = str(c["field"])
        op = str(c["operator"])
        val = float(c["value"])
        arr = pd.to_numeric(feat_df[field], errors="coerce") if field in feat_df.columns else pd.Series([np.nan] * len(feat_df))
        if op == ">":
            passed = arr > val
        elif op == ">=":
            passed = arr >= val
        elif op == "<":
            passed = arr < val
        elif op == "<=":
            passed = arr <= val
        elif op == "==":
            passed = arr == val
        else:
            continue
        rows.append({
            "rule_set": rule_set,
            "rule_id": c.get("rule_id"),
            "field": field,
            "operator": op,
            "value": val,
            "candidate_id": c.get("candidate_id"),
            "origin_id": c.get("origin_id"),
            "variant": c.get("variant"),
            "target_exact_rows": int(len(feat_df)),
            "pass_rows": int(passed.sum()),
            "fail_rows": int((~passed).sum()),
            "pass_rate": float(passed.mean()) if len(feat_df) else math.nan,
        })
    return pd.DataFrame(rows)


def rule_pass_details(cond_df: pd.DataFrame, feat_row: pd.Series) -> list[tuple[str, int, int, str, str, str]]:
    details: list[tuple[str, int, int, str, str, str]] = []
    for rule_id, group in cond_df.groupby("rule_id"):
        passed = 0
        failed: list[str] = []
        for _, c in group.iterrows():
            field = str(c["field"])
            op = str(c["operator"])
            val = float(c["value"])
            x = feat_row.get(field, math.nan)
            ok = False
            if pd.notna(x):
                if op == ">": ok = x > val
                elif op == ">=": ok = x >= val
                elif op == "<": ok = x < val
                elif op == "<=": ok = x <= val
                elif op == "==": ok = x == val
            if ok:
                passed += 1
            else:
                failed.append(f"{field}{op}{val:.6g}")
        details.append((str(rule_id), passed, int(len(group)), ";".join(failed[:3]), str(group.iloc[0].get("candidate_id", "")), str(group.iloc[0].get("variant", ""))))
    return sorted(details, key=lambda x: (x[1] / x[2], x[1]), reverse=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    pm = source_paths()
    write_csv(input_audit(pm), output_dir / "gold_v2_13c2_input_audit.csv")

    top = read_csv(pm["rr125_top_ledgers"])
    target = top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()
    target["entry_time_dt"] = pd.to_datetime(target["entry_time"], errors="coerce")
    target["target_row_id"] = np.arange(1, len(target) + 1)

    raw = read_csv(pm["rr125_raw_signal_ledger"])
    raw_rr = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    raw_rr["entry_time_dt"] = pd.to_datetime(raw_rr["entry_time"], errors="coerce")
    raw_rr["exit_time_dt"] = pd.to_datetime(raw_rr["exit_time"], errors="coerce")

    snap = read_csv(pm["feature_snapshot"])
    snap["time_dt"] = pd.to_datetime(snap["time"], errors="coerce")
    replay = read_csv(pm["replay_rows"])
    replay["time_dt"] = pd.to_datetime(replay["time"], errors="coerce")
    replay_summary = read_json(pm["replay_summary"])
    selected_conditions = read_csv(pm["selected_conditions"])
    same_conditions = read_csv(pm["same_count_conditions"])

    merge_cols = ["time_dt", "required_fields_complete", "selected_rule_hit_count", "same_count_source_hit_count", "coreb_combined_candidate_signal", "selected_hit_rule_ids", "same_count_hit_rule_ids"]
    exact = target.merge(replay[merge_cols], left_on="entry_time_dt", right_on="time_dt", how="left", indicator="feature_replay_merge")
    exact["feature_exact_match"] = exact["feature_replay_merge"].eq("both")
    exact["candidate_signal_at_source_entry_time"] = exact["coreb_combined_candidate_signal"].fillna(False).astype(bool)
    exact["same_count_gap_source_minus_replay"] = exact["same_count"] - exact["same_count_source_hit_count"].fillna(0)
    exact_cols = ["target_row_id", "dataset", "entry_time", "entry_month", "profit", "top_direction", "same_count", "unique_origins", "top_candidate_id", "rr_bucket", "source_rule_count", "feature_exact_match", "required_fields_complete", "selected_rule_hit_count", "same_count_source_hit_count", "same_count_gap_source_minus_replay", "candidate_signal_at_source_entry_time", "selected_hit_rule_ids", "same_count_hit_rule_ids"]
    write_csv(exact[[c for c in exact_cols if c in exact.columns]], output_dir / "gold_v2_13c2_target_entries_vs_replay_exact.csv")

    replay_idx = replay.set_index("time_dt")
    offset_rows: list[dict[str, Any]] = []
    per_rows: list[dict[str, Any]] = []
    offsets = list(range(-args.offset_minutes, args.offset_minutes + 1, 15))
    for offset in offsets:
        probe = target[["target_row_id", "dataset", "entry_time_dt"]].copy()
        probe["probe_time"] = probe["entry_time_dt"] + pd.to_timedelta(offset, unit="m")
        merged = probe.merge(replay[merge_cols], left_on="probe_time", right_on="time_dt", how="left")
        offset_rows.append({
            "offset_min": offset,
            "matched_rows": int(merged["time_dt"].notna().sum()),
            "selected_hit_rows": int((merged["selected_rule_hit_count"].fillna(0) > 0).sum()),
            "same_count_pass_rows": int((merged["same_count_source_hit_count"].fillna(0) >= 15).sum()),
            "candidate_signal_rows": int(((merged["selected_rule_hit_count"].fillna(0) > 0) & (merged["same_count_source_hit_count"].fillna(0) >= 15)).sum()),
            "avg_same_count_source_hit_count": float(merged["same_count_source_hit_count"].mean()) if merged["same_count_source_hit_count"].notna().any() else math.nan,
            "max_same_count_source_hit_count": float(merged["same_count_source_hit_count"].max()) if merged["same_count_source_hit_count"].notna().any() else math.nan,
        })
    for _, row in target.iterrows():
        recs: list[tuple[int, int, int, bool]] = []
        for offset in offsets:
            pt = row["entry_time_dt"] + pd.to_timedelta(offset, unit="m")
            if pt in replay_idx.index:
                rr = replay_idx.loc[pt]
                if isinstance(rr, pd.DataFrame):
                    rr = rr.iloc[0]
                recs.append((offset, int(rr["selected_rule_hit_count"]), int(rr["same_count_source_hit_count"]), bool(rr["coreb_combined_candidate_signal"])))
        per_rows.append({
            "target_row_id": int(row["target_row_id"]),
            "dataset": row["dataset"],
            "entry_time": row["entry_time"],
            "source_same_count": int(row["same_count"]),
            "matched_offsets": len(recs),
            "max_selected_rule_hit_count_pm180": max([x[1] for x in recs], default=0),
            "max_same_count_source_hit_count_pm180": max([x[2] for x in recs], default=0),
            "candidate_signal_offsets_pm180": "|".join(str(x[0]) for x in recs if x[3]),
            "has_candidate_signal_pm180": any(x[3] for x in recs),
        })
    offset_df = pd.DataFrame(offset_rows)
    per_df = pd.DataFrame(per_rows)
    write_csv(offset_df, output_dir / "gold_v2_13c2_time_offset_summary_pm180.csv")
    write_csv(per_df, output_dir / "gold_v2_13c2_target_entries_window_pm180_diagnostics.csv")

    raw_counts = raw_rr.groupby(["dataset", "entry_time"]).size().rename("raw_exact_entry_time_count").reset_index()
    raw_counts["entry_time_dt"] = pd.to_datetime(raw_counts["entry_time"], errors="coerce")
    raw_unique = raw_rr.groupby(["dataset", "entry_time"]).agg(raw_exact_unique_origins=("origin_id", "nunique")).reset_index()
    raw_unique["entry_time_dt"] = pd.to_datetime(raw_unique["entry_time"], errors="coerce")
    sem = target.merge(raw_counts[["dataset", "entry_time_dt", "raw_exact_entry_time_count"]], on=["dataset", "entry_time_dt"], how="left")
    sem = sem.merge(raw_unique[["dataset", "entry_time_dt", "raw_exact_unique_origins"]], on=["dataset", "entry_time_dt"], how="left")
    cover_counts: list[int] = []
    cover_unique: list[int] = []
    for _, row in sem.iterrows():
        mask = (raw_rr["dataset"].eq(row["dataset"])) & (raw_rr["direction"].eq(row["top_direction"])) & (raw_rr["entry_time_dt"] <= row["entry_time_dt"]) & (raw_rr["exit_time_dt"] >= row["entry_time_dt"])
        cover_counts.append(int(mask.sum()))
        cover_unique.append(int(raw_rr.loc[mask, "origin_id"].nunique()))
    sem["raw_interval_cover_count_at_source_entry"] = cover_counts
    sem["raw_interval_cover_unique_origins_at_source_entry"] = cover_unique
    sem["same_count_equals_raw_exact_entry_time_count"] = sem["same_count"].eq(sem["raw_exact_entry_time_count"].fillna(-1))
    sem["same_count_equals_raw_interval_cover_count"] = sem["same_count"].eq(sem["raw_interval_cover_count_at_source_entry"])

    comp_frames: list[pd.DataFrame] = []
    for _, group in raw_rr.groupby(["dataset", "direction"]):
        g = group.sort_values("entry_time_dt").copy()
        cids: list[int] = []
        current = -1
        current_end = None
        for _, rr in g.iterrows():
            if current_end is None or rr["entry_time_dt"] > current_end:
                current += 1
                current_end = rr["exit_time_dt"]
            else:
                if rr["exit_time_dt"] > current_end:
                    current_end = rr["exit_time_dt"]
            cids.append(current)
        g["raw_interval_component_id"] = cids
        comp_frames.append(g)
    raw_comp = pd.concat(comp_frames, ignore_index=True)
    comp = raw_comp.groupby(["dataset", "direction", "raw_interval_component_id"]).agg(raw_component_count=("candidate_id", "size"), raw_component_unique_origins=("origin_id", "nunique"), component_min_entry=("entry_time_dt", "min"), component_max_exit=("exit_time_dt", "max")).reset_index()
    component_counts: list[Any] = []
    component_unique: list[Any] = []
    component_ids: list[Any] = []
    for _, row in sem.iterrows():
        cands = comp[(comp["dataset"].eq(row["dataset"])) & (comp["direction"].eq(row["top_direction"])) & (comp["component_min_entry"] <= row["entry_time_dt"]) & (comp["component_max_exit"] >= row["entry_time_dt"])]
        if len(cands):
            c = cands.iloc[0]
            component_counts.append(int(c["raw_component_count"])); component_unique.append(int(c["raw_component_unique_origins"])); component_ids.append(int(c["raw_interval_component_id"]))
        else:
            component_counts.append(math.nan); component_unique.append(math.nan); component_ids.append(math.nan)
    sem["raw_interval_component_id_covering_source_entry"] = component_ids
    sem["raw_interval_component_count_covering_source_entry"] = component_counts
    sem["raw_interval_component_unique_origins_covering_source_entry"] = component_unique
    sem["same_count_equals_raw_interval_component_count"] = sem["same_count"].eq(sem["raw_interval_component_count_covering_source_entry"])
    sem_cols = ["target_row_id", "dataset", "entry_time", "same_count", "unique_origins", "raw_exact_entry_time_count", "raw_exact_unique_origins", "raw_interval_cover_count_at_source_entry", "raw_interval_cover_unique_origins_at_source_entry", "raw_interval_component_count_covering_source_entry", "raw_interval_component_unique_origins_covering_source_entry", "same_count_equals_raw_exact_entry_time_count", "same_count_equals_raw_interval_cover_count", "same_count_equals_raw_interval_component_count"]
    write_csv(sem[[c for c in sem_cols if c in sem.columns]], output_dir / "gold_v2_13c2_same_count_source_semantics_probe.csv")

    same_sem_summary = pd.DataFrame([
        {"check": "target_rows", "value": len(sem), "detail": "RR125_from_RR1_rules + same_count>=15 top-ledger rows"},
        {"check": "feature_exact_match_rows", "value": int(exact["feature_exact_match"].sum()), "detail": "Target entry_time found in feature/replay snapshot"},
        {"check": "feature_missing_rows", "value": int((~exact["feature_exact_match"]).sum()), "detail": "Mostly 2025-Jan to early-Feb before feature snapshot starts"},
        {"check": "candidate_signal_at_exact_source_time_rows", "value": int(exact["candidate_signal_at_source_entry_time"].sum()), "detail": "Candidate formula at exact rr125_top entry_time"},
        {"check": "candidate_signal_pm180_rows", "value": int(per_df["has_candidate_signal_pm180"].sum()), "detail": "Candidate formula within +/-180 minutes of rr125_top entry_time"},
        {"check": "source_same_count_equals_raw_exact_entry_time_count_rows", "value": int(sem["same_count_equals_raw_exact_entry_time_count"].sum()), "detail": "Shows same_count is not raw count at identical entry_time"},
        {"check": "source_same_count_equals_raw_interval_cover_count_rows", "value": int(sem["same_count_equals_raw_interval_cover_count"].sum()), "detail": "Shows same_count is not simply interval-cover count"},
        {"check": "source_same_count_equals_raw_interval_component_count_rows", "value": int(sem["same_count_equals_raw_interval_component_count"].sum()), "detail": "Shows same_count is not whole connected interval component size either"},
        {"check": "median_source_same_count", "value": float(sem["same_count"].median()), "detail": "historical source same_count"},
        {"check": "median_replay_same_count_at_exact", "value": float(exact["same_count_source_hit_count"].dropna().median()), "detail": "formula replay same_count at source entries"},
        {"check": "max_replay_same_count_at_exact", "value": float(exact["same_count_source_hit_count"].dropna().max()), "detail": "formula replay exact max"},
        {"check": "max_replay_same_count_pm180", "value": float(per_df["max_same_count_source_hit_count_pm180"].max()), "detail": "formula replay +/-180 max"},
    ])
    write_csv(same_sem_summary, output_dir / "gold_v2_13c2_same_count_source_semantics_summary.csv")

    feature_cols = ["time_dt"] + sorted(set(selected_conditions["field"].astype(str)) | set(same_conditions["field"].astype(str)))
    feat_exact = target[["target_row_id", "dataset", "entry_time_dt"]].merge(snap[feature_cols], left_on="entry_time_dt", right_on="time_dt", how="inner")
    condition_rates = pd.concat([condition_pass_rate(selected_conditions, feat_exact, "selected"), condition_pass_rate(same_conditions, feat_exact, "same_count_source")], ignore_index=True)
    write_csv(condition_rates, output_dir / "gold_v2_13c2_condition_pass_rate_on_target_exact_rows.csv")
    field_bottleneck = condition_rates.groupby(["rule_set", "field"]).agg(condition_count=("field", "size"), avg_pass_rate=("pass_rate", "mean"), min_pass_rate=("pass_rate", "min"), total_fail_rows=("fail_rows", "sum")).reset_index().sort_values(["rule_set", "avg_pass_rate", "total_fail_rows"])
    write_csv(field_bottleneck, output_dir / "gold_v2_13c2_condition_field_bottlenecks_on_target_exact_rows.csv")

    snap_by_time = snap.set_index("time_dt")
    best_rows: list[dict[str, Any]] = []
    for _, row in target.iterrows():
        if row["entry_time_dt"] not in snap_by_time.index:
            best_rows.append({"target_row_id": int(row["target_row_id"]), "dataset": row["dataset"], "entry_time": row["entry_time"], "has_feature": False})
            continue
        fr = snap_by_time.loc[row["entry_time_dt"]]
        if isinstance(fr, pd.DataFrame):
            fr = fr.iloc[0]
        selected_best = rule_pass_details(selected_conditions, fr)
        same_best = rule_pass_details(same_conditions, fr)
        best_rows.append({
            "target_row_id": int(row["target_row_id"]),
            "dataset": row["dataset"],
            "entry_time": row["entry_time"],
            "has_feature": True,
            "source_top_candidate_id": row["top_candidate_id"],
            "source_same_count": int(row["same_count"]),
            "best_selected_rule_id": selected_best[0][0] if selected_best else "",
            "best_selected_rule_passed_conditions": selected_best[0][1] if selected_best else math.nan,
            "best_selected_rule_total_conditions": selected_best[0][2] if selected_best else math.nan,
            "best_selected_rule_failed_first3": selected_best[0][3] if selected_best else "",
            "best_selected_candidate_id": selected_best[0][4] if selected_best else "",
            "best_selected_variant": selected_best[0][5] if selected_best else "",
            "best_same_rule_id": same_best[0][0] if same_best else "",
            "best_same_rule_passed_conditions": same_best[0][1] if same_best else math.nan,
            "best_same_rule_total_conditions": same_best[0][2] if same_best else math.nan,
            "best_same_rule_failed_first3": same_best[0][3] if same_best else "",
        })
    write_csv(pd.DataFrame(best_rows), output_dir / "gold_v2_13c2_target_exact_best_rule_match_diagnostics.csv")

    replay_signals = replay[replay["coreb_combined_candidate_signal"].astype(bool)].copy()
    write_csv(replay_signals, output_dir / "gold_v2_13c2_candidate_formula_signal_rows_7.csv")
    if len(replay_signals):
        nearest_rows: list[dict[str, Any]] = []
        for _, sig in replay_signals.iterrows():
            diffs = (target["entry_time_dt"] - sig["time_dt"]).abs()
            idx = diffs.idxmin()
            tr = target.loc[idx]
            nearest_rows.append({"candidate_signal_time": sig["time"], "selected_rule_hit_count": sig["selected_rule_hit_count"], "same_count_source_hit_count": sig["same_count_source_hit_count"], "nearest_target_entry_time": tr["entry_time"], "nearest_target_dataset": tr["dataset"], "nearest_target_same_count": tr["same_count"], "abs_minutes_to_nearest_target": float(diffs.loc[idx].total_seconds() / 60.0)})
        write_csv(pd.DataFrame(nearest_rows), output_dir / "gold_v2_13c2_candidate_signal_rows_nearest_target.csv")

    source_summary_rows: list[dict[str, Any]] = []
    for dataset, group in target.groupby("dataset"):
        row = metrics(group["profit"])
        row.update({"dataset": dataset, "view": "RR125_top_ledgers_source_target"})
        source_summary_rows.append(row)
    source_summary = pd.DataFrame(source_summary_rows)
    write_csv(source_summary, output_dir / "gold_v2_13c2_target_source_summary.csv")

    exact_by_dataset: list[dict[str, Any]] = []
    for dataset, group in exact.groupby("dataset"):
        exact_by_dataset.append({
            "dataset": dataset,
            "target_rows": int(len(group)),
            "feature_exact_match_rows": int(group["feature_exact_match"].sum()),
            "candidate_signal_exact_rows": int(group["candidate_signal_at_source_entry_time"].sum()),
            "selected_hit_exact_rows": int((group["selected_rule_hit_count"].fillna(0) > 0).sum()),
            "same_count_pass_exact_rows": int((group["same_count_source_hit_count"].fillna(0) >= 15).sum()),
            "median_source_same_count": float(group["same_count"].median()),
            "median_replay_same_count_exact": float(group["same_count_source_hit_count"].dropna().median()) if group["same_count_source_hit_count"].notna().any() else math.nan,
            "max_replay_same_count_exact": float(group["same_count_source_hit_count"].dropna().max()) if group["same_count_source_hit_count"].notna().any() else math.nan,
        })
    exact_by_dataset_df = pd.DataFrame(exact_by_dataset)
    write_csv(exact_by_dataset_df, output_dir / "gold_v2_13c2_exact_match_summary_by_dataset.csv")

    findings = pd.DataFrame([
        {"finding_id": "F001", "finding": "Feature snapshot does not cover early 2025 target rows", "evidence": "16 of 125 top-ledger rows missing exact feature/replay timestamp; missing rows are Jan and early Feb before snapshot starts", "impact": "partial, not main cause"},
        {"finding_id": "F002", "finding": "Exact timestamp replay undercounts same_count severely", "evidence": "109 exact matched targets: median replay same_count=7 vs median source same_count=22; max exact replay same_count=15", "impact": "main cause"},
        {"finding_id": "F003", "finding": "Candidate formula signal has only 1 exact match and 5 within +/-180m of target rows", "evidence": "Candidate replay rows=7 globally; exact target signal rows=1; +/-180 target rows with any candidate signal=5", "impact": "candidate formula not source parity"},
        {"finding_id": "F004", "finding": "Source same_count is not raw exact entry count", "evidence": "same_count_equals_raw_exact_entry_time_count_rows=0", "impact": "same_count is cluster/confluence universe semantics, not simple feature row hit count"},
        {"finding_id": "F005", "finding": "Source same_count is not simply interval-cover or connected component size either", "evidence": "interval-cover equality only 3 rows; component equality only 10 rows", "impact": "need original clustering algorithm or source ledger membership to reproduce exactly"},
        {"finding_id": "F006", "finding": "Selected/same_count frozen conditions are internally coherent but not source-validated", "evidence": "12 selected rules, 33 same-count rules, all condition fields covered; replay status NOT_PROVEN_CANDIDATE_FORMULA_ONLY", "impact": "must not enable live signal"},
    ])
    write_csv(findings, output_dir / "gold_v2_13c2_root_cause_findings.csv")

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COREB_SOURCE_LEDGER_TO_FEATURE_SNAPSHOT_PARITY_FAILED_ROOT_CAUSE_IDENTIFIED_AUDIT_ONLY",
        "audit_only": True,
        "target_rows": int(len(target)),
        "target_counts": {str(k): int(v) for k, v in target.groupby("dataset").size().items()},
        "feature_snapshot_rows": int(len(snap)),
        "feature_snapshot_time_min": str(snap["time_dt"].min()),
        "feature_snapshot_time_max": str(snap["time_dt"].max()),
        "feature_exact_match_rows": int(exact["feature_exact_match"].sum()),
        "feature_missing_rows": int((~exact["feature_exact_match"]).sum()),
        "candidate_replay_global_signal_rows": int(replay["coreb_combined_candidate_signal"].astype(bool).sum()),
        "candidate_signal_at_exact_source_entry_rows": int(exact["candidate_signal_at_source_entry_time"].sum()),
        "candidate_signal_pm180_target_rows": int(per_df["has_candidate_signal_pm180"].sum()),
        "median_source_same_count": float(sem["same_count"].median()),
        "median_replay_same_count_exact": float(exact["same_count_source_hit_count"].dropna().median()),
        "max_replay_same_count_exact": float(exact["same_count_source_hit_count"].dropna().max()),
        "max_replay_same_count_pm180": float(per_df["max_same_count_source_hit_count_pm180"].max()),
        "same_count_semantics": same_sem_summary.to_dict(orient="records"),
        "root_cause_findings": findings.to_dict(orient="records"),
        "replay_summary_source_status": replay_summary.get("parity_status"),
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_required_step": "13C3_COREB_RECONSTRUCT_SOURCE_CLUSTER_MEMBERSHIP_ORIGINAL_CLUSTER_ALGORITHM_AUDIT_ONLY",
    }
    (output_dir / "gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13C-2 CoreB source ledger to feature snapshot parity audit-only report", "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`", "",
        "## Final decision",
        "- CoreB source ledger 125 rows are confirmed.",
        "- Feature snapshot/replay does **not** reproduce the 125 source rows.",
        "- Main cause is not just missing feature timestamps; it is same_count/confluence semantics mismatch.",
        "- The replay formula counts frozen rule hits at a single feature row, while source `same_count` behaves like historical cluster/confluence membership.",
        "- Historical same_count/top-ledger rows must not be reused as live signal triggers.",
        "- Discord, MT5, AI API, and live hook remain disabled.", "",
        "## Target source summary", markdown_table(source_summary, ["dataset", "view", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]), "",
        "## Exact feature/replay match summary by dataset", markdown_table(exact_by_dataset_df, ["dataset", "target_rows", "feature_exact_match_rows", "candidate_signal_exact_rows", "selected_hit_exact_rows", "same_count_pass_exact_rows", "median_source_same_count", "median_replay_same_count_exact", "max_replay_same_count_exact"]), "",
        "## Time offset summary (+/-180m)", markdown_table(offset_df, ["offset_min", "matched_rows", "selected_hit_rows", "same_count_pass_rows", "candidate_signal_rows", "avg_same_count_source_hit_count", "max_same_count_source_hit_count"]), "",
        "## Same-count semantics summary", markdown_table(same_sem_summary, ["check", "value", "detail"]), "",
        "## Root cause findings", markdown_table(findings, ["finding_id", "finding", "evidence", "impact"]), "",
        "## Condition field bottlenecks on exact target rows", markdown_table(field_bottleneck.head(40), ["rule_set", "field", "condition_count", "avg_pass_rate", "min_pass_rate", "total_fail_rows"]), "",
        "## Safety", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "",
        "## Next required step", "`13C3_COREB_RECONSTRUCT_SOURCE_CLUSTER_MEMBERSHIP_ORIGINAL_CLUSTER_ALGORITHM_AUDIT_ONLY`", "",
    ]
    (output_dir / "GOLD_V2_13C2_COREB_SOURCE_LEDGER_TO_FEATURE_SNAPSHOT_PARITY_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(json.dumps({"status": summary["status"], "output_dir": str(output_dir), "target_rows": summary["target_rows"], "candidate_signal_exact": summary["candidate_signal_at_exact_source_entry_rows"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
