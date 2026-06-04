#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13C-3 audit: reconstruct CoreB source cluster membership.

This audit tries to reconstruct the RR1.25 CoreB source `same_count` and
cluster membership from `rr125_raw_signal_ledger.csv` and `rr125_top_ledgers.csv`.
It deliberately does not use historical cluster_id/same_count as a live trigger.

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


BASE = files_dir_from_repo() / "FX_OUTPUTS"
OUT = BASE / "gold_v2_13c3_coreb_reconstruct_source_cluster_membership_audit_only"
OUT.mkdir(parents=True, exist_ok=True)


def find_file(name: str) -> Path:
    direct = BASE / name
    if direct.exists():
        return direct
    matches = list(BASE.rglob(name))
    return matches[0] if matches else direct


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(name: str) -> pd.DataFrame:
    path = find_file(name)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def metrics(values: Iterable[float]) -> dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate_pct": math.nan, "pf": math.nan, "total_r": 0.0, "worst": math.nan, "maxdd": 0.0, "max_loss_streak": 0}
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    equity = np.cumsum(vals)
    previous_peak = np.maximum.accumulate(np.r_[0.0, equity[:-1]])
    drawdown = np.maximum(previous_peak - equity, 0.0)
    streak = max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {"count": int(len(vals)), "win_rate_pct": float((vals > 0).mean() * 100.0), "pf": float(pf) if not math.isnan(pf) else math.nan, "total_r": float(vals.sum()), "worst": float(vals.min()), "maxdd": float(drawdown.max()), "max_loss_streak": int(max_streak)}


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


def input_audit(names: Sequence[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in names:
        path = find_file(name)
        row: dict[str, Any] = {"filename": name, "path": str(path), "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            if name.endswith(".csv"):
                row["columns"] = len(pd.read_csv(path, nrows=1).columns)
        rows.append(row)
    return pd.DataFrame(rows)


def build_connected_components(raw_rr: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for (_, _), group in raw_rr.groupby(["dataset", "direction"]):
        g = group.sort_values("entry_time_dt").copy()
        cids: list[int] = []
        current = -1
        current_end = None
        for _, row in g.iterrows():
            if current_end is None or row.entry_time_dt > current_end:
                current += 1
                current_end = row.exit_time_dt
            elif row.exit_time_dt > current_end:
                current_end = row.exit_time_dt
            cids.append(current)
        g["raw_connected_component_id"] = cids
        frames.append(g)
    return pd.concat(frames, ignore_index=True)


def main() -> int:
    raw = read_csv("rr125_raw_signal_ledger.csv")
    top = read_csv("rr125_top_ledgers.csv")
    for df in [raw, top]:
        for col in ["entry_time", "exit_time"]:
            if col in df.columns:
                df[col + "_dt"] = pd.to_datetime(df[col], errors="coerce")

    raw_rr = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    top_rr = top[top["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    target = top_rr[top_rr["filter"].astype(str).eq("same_count>=15")].copy()
    target = target.sort_values(["dataset", "entry_time_dt", "cluster_id"]).reset_index(drop=True)
    target["target_row_id"] = np.arange(1, len(target) + 1)

    write_csv(input_audit(["rr125_raw_signal_ledger.csv", "rr125_top_ledgers.csv", "gold_v2_final_portfolio_2025_2026_sot_ledger.csv"]), OUT / "gold_v2_13c3_input_audit.csv")

    source_clusters = top_rr[["dataset", "policy", "cluster_id", "entry_time", "entry_month", "profit", "top_direction", "same_count", "unique_origins", "top_candidate_id", "rr_bucket", "source_rule_count"]].drop_duplicates(["dataset", "policy", "cluster_id", "entry_time", "top_direction"]).sort_values(["dataset", "entry_time", "cluster_id"]).reset_index(drop=True)
    source_clusters["is_target_same_count_ge15"] = source_clusters["same_count"] >= 15
    source_clusters["passes_unique_origins_ge2"] = source_clusters["unique_origins"] >= 2
    write_csv(source_clusters, OUT / "gold_v2_13c3_source_top_cluster_inventory_from_top_ledgers.csv")

    source_summary_rows: list[dict[str, Any]] = []
    for dataset, group in target.groupby("dataset"):
        row = metrics(group["profit"])
        row.update(dataset=dataset, view="RR125_top_ledgers_same_count_ge15")
        source_summary_rows.append(row)
    source_summary = pd.DataFrame(source_summary_rows)
    write_csv(source_summary, OUT / "gold_v2_13c3_target_source_summary.csv")

    raw_rr = raw_rr.sort_values(["dataset", "direction", "entry_time_dt"]).reset_index(drop=True)
    groups = {(ds, direction): (g["entry_time_dt"].values.astype("datetime64[ns]"), g.reset_index(drop=True)) for (ds, direction), g in raw_rr.groupby(["dataset", "direction"])}

    windows = [15, 30, 45, 60, 75, 90, 105, 120, 150, 180, 240, 360, 480, 720, 1440]
    sweep_rows: list[dict[str, Any]] = []
    for window_min in windows:
        delta = np.timedelta64(window_min, "m")
        for mode in ["backward", "forward", "center"]:
            diffs: list[float] = []
            exact = within1 = within3 = ge15 = 0
            src_counts: list[float] = []
            recon_counts: list[float] = []
            for _, row in target.iterrows():
                times, _ = groups[(row["dataset"], row["top_direction"])]
                t = np.datetime64(row["entry_time_dt"])
                if mode == "backward":
                    lo, hi = t - delta, t
                elif mode == "forward":
                    lo, hi = t, t + delta
                else:
                    lo, hi = t - delta, t + delta
                left = np.searchsorted(times, lo, "left")
                right = np.searchsorted(times, hi, "right")
                count = int(right - left)
                diff = abs(count - int(row["same_count"]))
                diffs.append(diff)
                exact += diff == 0
                within1 += diff <= 1
                within3 += diff <= 3
                ge15 += count >= 15
                src_counts.append(float(row["same_count"]))
                recon_counts.append(float(count))
            corr = float(np.corrcoef(src_counts, recon_counts)[0, 1]) if len(set(recon_counts)) > 1 else math.nan
            sweep_rows.append({"algorithm": f"entry_window_{mode}_{window_min}m", "mode": mode, "window_min": window_min, "exact_same_count_rows": exact, "within1_rows": within1, "within3_rows": within3, "mae": float(np.mean(diffs)), "median_abs_error": float(np.median(diffs)), "count_ge15_rows": ge15, "corr_with_source_same_count": corr})
    algorithm_sweep = pd.DataFrame(sweep_rows).sort_values(["exact_same_count_rows", "within1_rows", "mae"], ascending=[False, False, True])
    write_csv(algorithm_sweep, OUT / "gold_v2_13c3_reconstruction_algorithm_sweep.csv")

    best = algorithm_sweep.iloc[0]
    best_mode = str(best["mode"])
    best_window = int(best["window_min"])
    best_delta = pd.Timedelta(minutes=best_window)
    best_rows: list[dict[str, Any]] = []
    for _, row in target.iterrows():
        g = raw_rr[(raw_rr["dataset"].eq(row["dataset"])) & (raw_rr["direction"].eq(row["top_direction"]))]
        t = row["entry_time_dt"]
        if best_mode == "backward":
            mask = (g.entry_time_dt >= t - best_delta) & (g.entry_time_dt <= t)
        elif best_mode == "forward":
            mask = (g.entry_time_dt >= t) & (g.entry_time_dt <= t + best_delta)
        else:
            mask = (g.entry_time_dt >= t - best_delta) & (g.entry_time_dt <= t + best_delta)
        members = g[mask]
        best_rows.append({"target_row_id": int(row.target_row_id), "dataset": row.dataset, "cluster_id": row.cluster_id, "entry_time": row.entry_time, "source_same_count": int(row.same_count), "reconstructed_count": int(len(members)), "abs_error": abs(int(len(members)) - int(row.same_count)), "source_unique_origins": int(row.unique_origins), "reconstructed_unique_origins": int(members.origin_id.nunique()), "source_top_candidate_id": row.top_candidate_id, "reconstructed_top_candidate_mode": members.candidate_id.mode().iloc[0] if len(members) else None, "window_mode": best_mode, "window_min": best_window})
    write_csv(pd.DataFrame(best_rows), OUT / "gold_v2_13c3_best_static_window_membership_probe.csv")

    raw_comp = build_connected_components(raw_rr)
    component_agg = raw_comp.groupby(["dataset", "direction", "raw_connected_component_id"]).agg(component_count=("candidate_id", "size"), component_unique_origins=("origin_id", "nunique"), component_min_entry=("entry_time_dt", "min"), component_max_exit=("exit_time_dt", "max")).reset_index()
    component_rows: list[dict[str, Any]] = []
    for _, row in target.iterrows():
        cover = component_agg[(component_agg.dataset.eq(row.dataset)) & (component_agg.direction.eq(row.top_direction)) & (component_agg.component_min_entry <= row.entry_time_dt) & (component_agg.component_max_exit >= row.entry_time_dt)]
        if len(cover):
            c = cover.iloc[0]
            recon_count = int(c.component_count)
            recon_unique = int(c.component_unique_origins)
            component_id = int(c.raw_connected_component_id)
        else:
            recon_count = None
            recon_unique = None
            component_id = None
        component_rows.append({"target_row_id": int(row.target_row_id), "dataset": row.dataset, "cluster_id": row.cluster_id, "entry_time": row.entry_time, "source_same_count": int(row.same_count), "raw_connected_component_id": component_id, "raw_connected_component_count": recon_count, "raw_connected_component_unique_origins": recon_unique, "same_count_matches_component_count": recon_count == int(row.same_count) if recon_count is not None else False})
    component_probe = pd.DataFrame(component_rows)
    write_csv(component_probe, OUT / "gold_v2_13c3_raw_connected_component_probe.csv")

    sequence_probe = target[["target_row_id", "dataset", "cluster_id", "entry_time", "same_count", "unique_origins", "top_candidate_id", "profit"]].copy()
    sequence_probe["prev_cluster_id"] = sequence_probe.groupby("dataset")["cluster_id"].shift(1)
    sequence_probe["cluster_gap_from_previous"] = sequence_probe["cluster_id"] - sequence_probe["prev_cluster_id"]
    sequence_probe["prev_entry_time"] = sequence_probe.groupby("dataset")["entry_time"].shift(1)
    sequence_probe["minutes_from_previous_target"] = (pd.to_datetime(sequence_probe["entry_time"]) - pd.to_datetime(sequence_probe["prev_entry_time"])).dt.total_seconds() / 60.0
    write_csv(sequence_probe, OUT / "gold_v2_13c3_source_cluster_id_sequence_probe.csv")

    candidate_summary = target.groupby(["dataset", "top_candidate_id"]).agg(target_rows=("cluster_id", "size"), avg_same_count=("same_count", "mean"), median_same_count=("same_count", "median"), avg_profit=("profit", "mean")).reset_index()
    write_csv(candidate_summary, OUT / "gold_v2_13c3_target_by_candidate_id.csv")

    summary_table = pd.DataFrame([
        {"probe": "best_static_entry_window", "best_algorithm": best["algorithm"], "exact_same_count_rows": int(best["exact_same_count_rows"]), "within1_rows": int(best["within1_rows"]), "within3_rows": int(best["within3_rows"]), "mae": float(best["mae"]), "verdict": "FAIL_NOT_EXACT"},
        {"probe": "raw_connected_component", "best_algorithm": "interval_connected_component", "exact_same_count_rows": int(component_probe.same_count_matches_component_count.sum()), "within1_rows": math.nan, "within3_rows": math.nan, "mae": float((component_probe.raw_connected_component_count.fillna(0) - component_probe.source_same_count).abs().mean()), "verdict": "FAIL_NOT_EXACT"},
        {"probe": "source_cluster_id_available_in_top_ledgers", "best_algorithm": "top_ledgers_source_cluster_id", "exact_same_count_rows": int(len(target)), "within1_rows": int(len(target)), "within3_rows": int(len(target)), "mae": 0.0, "verdict": "SOURCE_AVAILABLE_BUT_MEMBERSHIP_NOT_RECONSTRUCTED"},
    ])
    write_csv(summary_table, OUT / "gold_v2_13c3_cluster_reconstruction_summary_table.csv")

    findings = pd.DataFrame([
        {"finding_id": "F001", "finding": "top_ledgers already stores source cluster_id/same_count/source_rule_count, but raw ledger has no row-level cluster membership", "evidence": f"target rows={len(target)}; rr125_raw_signal_ledger has no cluster_id column", "impact": "source cluster summary is audit-usable, live reconstruction remains blocked"},
        {"finding_id": "F002", "finding": "best static entry-window approximation is not sufficient", "evidence": f"best={best['algorithm']}; exact same_count rows={int(best['exact_same_count_rows'])}/125; MAE={float(best['mae']):.3f}", "impact": "cannot replace source same_count with a fixed entry-time window"},
        {"finding_id": "F003", "finding": "raw connected interval component is not sufficient", "evidence": f"component exact matches={int(component_probe.same_count_matches_component_count.sum())}/125", "impact": "same_count is not raw interval connected component size"},
        {"finding_id": "F004", "finding": "cluster_id gaps imply selection from a larger source cluster universe", "evidence": "same_count>=15 top ledger skips lower-count clusters; source cluster inventory exists only as summary rows", "impact": "original clustering algorithm or cluster membership ledger is needed"},
        {"finding_id": "F005", "finding": "live CoreB must remain blocked", "evidence": "same_count membership is not derived from a live-computable replay formula yet", "impact": "no live CoreB signal / no external actions"},
    ])
    write_csv(findings, OUT / "gold_v2_13c3_root_cause_findings.csv")

    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "COREB_SOURCE_CLUSTER_MEMBERSHIP_RECONSTRUCTION_FAILED_ORIGINAL_ALGORITHM_REQUIRED_AUDIT_ONLY", "audit_only": True, "target_rows": int(len(target)), "target_counts": {str(k): int(v) for k, v in target.groupby("dataset").size().items()}, "source_top_cluster_inventory_rows": int(len(source_clusters)), "rr125_raw_signal_rows": int(len(raw_rr)), "best_static_window_algorithm": str(best["algorithm"]), "best_static_window_exact_same_count_rows": int(best["exact_same_count_rows"]), "best_static_window_within1_rows": int(best["within1_rows"]), "best_static_window_within3_rows": int(best["within3_rows"]), "best_static_window_mae": float(best["mae"]), "connected_component_exact_same_count_rows": int(component_probe.same_count_matches_component_count.sum()), "status_reason": "No tested raw-ledger-only cluster reconstruction reproduced source same_count for all 125 rows. top_ledgers contains cluster summary, but raw row membership/original clustering algorithm is still missing.", "live_coreb_allowed": False, "final_signal_allowed": False, "step13_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_required_step": "13C4_FIND_OR_RESTORE_ORIGINAL_COREB_CLUSTERING_SCRIPT_OR_FREEZE_SOURCE_TOP_LEDGER_AS_NON_LIVE_SOT_AUDIT_ONLY", "findings": findings.to_dict(orient="records")}
    (OUT / "gold_v2_13c3_coreb_reconstruct_source_cluster_membership_summary.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = ["# GOLD V2 13C-3 CoreB reconstruct source cluster membership audit-only report", "", f"Created UTC: {manifest['created_utc']}", f"Status: `{manifest['status']}`", "", "## Final decision", "- CoreB source top-ledger cluster summary is available.", "- Row-level source cluster membership / original clustering algorithm was **not reconstructed** from `rr125_raw_signal_ledger.csv` alone.", "- Tested raw-ledger-only approximations do not reproduce `same_count` for all 125 rows.", "- Therefore CoreB live evaluator remains blocked; historical `cluster_id` / `same_count` must not be used as live triggers.", "- Discord, MT5, AI API, and live hook remain disabled.", "", "## Target source summary", markdown_table(source_summary, ["dataset", "view", "count", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]), "", "## Reconstruction summary table", markdown_table(summary_table, ["probe", "best_algorithm", "exact_same_count_rows", "within1_rows", "within3_rows", "mae", "verdict"]), "", "## Best static window algorithms", markdown_table(algorithm_sweep.head(20), ["algorithm", "mode", "window_min", "exact_same_count_rows", "within1_rows", "within3_rows", "mae", "median_abs_error", "count_ge15_rows", "corr_with_source_same_count"]), "", "## Source cluster ID sequence sample", markdown_table(sequence_probe.head(30), ["target_row_id", "dataset", "cluster_id", "entry_time", "same_count", "unique_origins", "top_candidate_id", "cluster_gap_from_previous", "minutes_from_previous_target"]), "", "## Findings", markdown_table(findings, ["finding_id", "finding", "evidence", "impact"]), "", "## Safety", "- live_coreb_allowed: false", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "", "## Next required step", "`13C4_FIND_OR_RESTORE_ORIGINAL_COREB_CLUSTERING_SCRIPT_OR_FREEZE_SOURCE_TOP_LEDGER_AS_NON_LIVE_SOT_AUDIT_ONLY`", ""]
    (OUT / "GOLD_V2_13C3_COREB_RECONSTRUCT_SOURCE_CLUSTER_MEMBERSHIP_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    zip_path = BASE / "gold_v2_13c3_coreb_reconstruct_source_cluster_membership_audit.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in OUT.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": manifest["status"], "output_dir": str(OUT), "zip": str(zip_path), "target_rows": manifest["target_rows"], "best_exact": manifest["best_static_window_exact_same_count_rows"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
