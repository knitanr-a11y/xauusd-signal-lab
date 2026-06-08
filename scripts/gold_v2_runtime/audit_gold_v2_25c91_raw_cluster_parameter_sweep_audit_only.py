#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C91 raw cluster parameter sweep audit-only.

Final raw-only boundary test for CoreB cluster reconstruction. Sweeps entry-gap,
interval-gap, and calendar-bucket clustering parameters over RR125 raw rows.

A002 is not used. No live/final/external action is allowed.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "25C91_RAW_CLUSTER_PARAMETER_SWEEP_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c91_raw_cluster_parameter_sweep_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUT_NAMES = [
    "25c90_summary.json",
    "rr125_raw_signal_ledger.csv",
    "rr125_top_ledgers.csv",
    "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
]

GAPS_MIN = [5, 15, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440, 2880]
FAMILIES = ["entry_gap", "interval_gap", "calendar_bucket"]
PROFIT_RULES = ["sum", "mean", "median", "min", "max", "first", "last"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def out_dir() -> Path:
    out = fx_outputs() / OUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def find_file(name: str) -> Path | None:
    for c in [repo_root() / name, fx_outputs() / name]:
        if c.exists():
            return c
    for base in [fx_outputs(), repo_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found:
                return found[0]
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path | None) -> pd.DataFrame:
    return pd.read_csv(path) if path and path.exists() else pd.DataFrame()


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clean_json(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): clean_json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean_json(v) for v in x]
    if isinstance(x, float):
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return x


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean_json(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows = []
    for name, path in paths.items():
        row: dict[str, Any] = {"filename": name, "exists": bool(path and path.exists()), "path": str(path) if path else ""}
        if path and path.exists():
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
            if path.suffix.lower() == ".csv":
                row["row_count"] = len(pd.read_csv(path))
                row["columns"] = ";".join(pd.read_csv(path, nrows=0).columns)
            elif path.suffix.lower() == ".json":
                row["json_keys"] = ";".join(list(read_json(path).keys())[:20])
        rows.append(row)
    return pd.DataFrame(rows)


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["exit_dt"] = pd.to_datetime(d["exit_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit_r"), errors="coerce")
    for c in ["dataset", "direction", "origin_id", "candidate_id"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d.sort_values(["dataset", "direction", "entry_dt", "exit_dt"]).reset_index(drop=True)


def prep_top(top: pd.DataFrame) -> pd.DataFrame:
    d = top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit"), errors="coerce")
    d["same_count_num"] = pd.to_numeric(d.get("same_count"), errors="coerce")
    d["source_rule_count_num"] = pd.to_numeric(d.get("source_rule_count"), errors="coerce")
    d["unique_origins_num"] = pd.to_numeric(d.get("unique_origins"), errors="coerce")
    for c in ["dataset", "top_direction"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d.sort_values(["dataset", "entry_dt", "cluster_id"]).reset_index(drop=True)


def assign_clusters(raw: pd.DataFrame, family: str, gap_min: int) -> pd.DataFrame:
    frames = []
    gap = pd.Timedelta(minutes=gap_min)
    for (_, _), group in raw.groupby(["dataset", "direction"], dropna=False):
        g = group.sort_values(["entry_dt", "exit_dt"]).copy()
        cids = []
        cid = -1
        prev_entry = None
        current_end = None
        for _, row in g.iterrows():
            entry = row["entry_dt"]
            exit_ = row["exit_dt"]
            if family == "calendar_bucket":
                if pd.isna(entry):
                    cid_val = None
                else:
                    epoch_min = int(entry.value // (60 * 10**9))
                    cid_val = epoch_min // gap_min
                cids.append(cid_val)
                continue
            new_cluster = False
            if cid < 0 or pd.isna(entry):
                new_cluster = True
            elif family == "entry_gap":
                new_cluster = (entry - prev_entry) > gap
            elif family == "interval_gap":
                new_cluster = entry > (current_end + gap)
            if new_cluster:
                cid += 1
                current_end = exit_
            else:
                if pd.notna(exit_) and (current_end is None or exit_ > current_end):
                    current_end = exit_
            prev_entry = entry
            cids.append(cid)
        g["recon_cluster_id"] = cids
        frames.append(g)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def pval(s: pd.Series, rule: str) -> float | None:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if x.empty:
        return None
    if rule == "sum": return float(x.sum())
    if rule == "mean": return float(x.mean())
    if rule == "median": return float(x.median())
    if rule == "min": return float(x.min())
    if rule == "max": return float(x.max())
    if rule == "first": return float(x.iloc[0])
    if rule == "last": return float(x.iloc[-1])
    return None


def members_for_top(comp: pd.DataFrame, tr: pd.Series, family: str) -> pd.DataFrame:
    g = comp[(comp["dataset"].astype(str).eq(str(tr["dataset"]))) & (comp["direction"].astype(str).eq(str(tr["top_direction"])))]
    if g.empty:
        return g
    if family == "calendar_bucket":
        # choose bucket containing exact entry if present, otherwise nearest bucket by entry time
        exact = g[g["entry_dt"].eq(tr["entry_dt"])]
        if not exact.empty:
            cid = exact.iloc[0]["recon_cluster_id"]
        else:
            idx = (g["entry_dt"] - tr["entry_dt"]).abs().idxmin()
            cid = g.loc[idx, "recon_cluster_id"]
        return g[g["recon_cluster_id"].eq(cid)]
    cover = g[(g["entry_dt"] <= tr["entry_dt"]) & (g["exit_dt"] >= tr["entry_dt"])]
    if not cover.empty:
        cid = cover.iloc[0]["recon_cluster_id"]
    else:
        idx = (g["entry_dt"] - tr["entry_dt"]).abs().idxmin()
        cid = g.loc[idx, "recon_cluster_id"]
    return g[g["recon_cluster_id"].eq(cid)]


def evaluate(comp: pd.DataFrame, top: pd.DataFrame, family: str, gap: int) -> tuple[dict[str, Any], pd.DataFrame]:
    rows = []
    for _, tr in top.iterrows():
        mem = members_for_top(comp, tr, family)
        rec = {"family": family, "gap_min": gap, "dataset": tr.get("dataset"), "entry_time": tr.get("entry_time"), "cluster_id": tr.get("cluster_id"), "source_same_count": tr.get("same_count_num"), "source_rule_count": tr.get("source_rule_count_num"), "source_profit": tr.get("profit_num"), "recon_count": len(mem), "recon_unique_origins": mem["origin_id"].nunique(dropna=True) if "origin_id" in mem.columns else 0}
        rec["same_count_match"] = len(mem) == int(tr["same_count_num"]) if pd.notna(tr["same_count_num"]) else False
        rec["source_rule_count_match"] = len(mem) == int(tr["source_rule_count_num"]) if pd.notna(tr["source_rule_count_num"]) else False
        rec["unique_origins_match"] = rec["recon_unique_origins"] == int(tr["unique_origins_num"]) if pd.notna(tr["unique_origins_num"]) else False
        for pr in PROFIT_RULES:
            val = pval(mem["profit_num"], pr) if "profit_num" in mem.columns and len(mem) else None
            rec[f"profit_{pr}_match"] = abs(float(tr["profit_num"]) - float(val)) <= 1e-6 if val is not None and pd.notna(tr["profit_num"]) else False
        rows.append(rec)
    df = pd.DataFrame(rows)
    sm = {"family": family, "gap_min": gap, "raw_rows": int(len(comp)), "component_count": int(comp.groupby(["dataset", "direction", "recon_cluster_id"]).ngroups) if not comp.empty else 0, "top_rows": int(len(top)), "covered_rows": int((df["recon_count"] > 0).sum()), "same_count_exact": int(df["same_count_match"].sum()), "source_rule_count_exact": int(df["source_rule_count_match"].sum()), "unique_origins_exact": int(df["unique_origins_match"].sum())}
    for pr in PROFIT_RULES:
        sm[f"profit_{pr}_exact"] = int(df[f"profit_{pr}_match"].sum())
    sm["status"] = "FULL" if sm["same_count_exact"] == len(top) or sm["source_rule_count_exact"] == len(top) else "PARTIAL_OR_FAIL"
    return sm, df


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    paths = {name: find_file(name) for name in INPUT_NAMES}
    inv = inventory(paths)
    s90 = read_json(paths["25c90_summary.json"])
    raw = prep_raw(read_csv(paths["rr125_raw_signal_ledger.csv"]))
    top = prep_top(read_csv(paths["rr125_top_ledgers.csv"]))
    summaries = []
    detail_frames = []
    for family in FAMILIES:
        for gap in GAPS_MIN:
            comp = assign_clusters(raw, family, gap)
            sm, df = evaluate(comp, top, family, gap)
            summaries.append(sm)
            detail_frames.append(df)
    summary_df = pd.DataFrame(summaries).sort_values(["same_count_exact", "source_rule_count_exact", "unique_origins_exact", "profit_sum_exact"], ascending=False)
    detail_df = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    best = summary_df.head(1).copy()
    full = bool((summary_df["status"].astype(str) == "FULL").any()) if not summary_df.empty else False
    upstream_ok = s90.get("status") == "BASE_CONDITION_RULE_MEMBERSHIP_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    status = "RAW_CLUSTER_PARAMETER_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED" if full else "RAW_CLUSTER_PARAMETER_SWEEP_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    next_step = "HUMAN_REVIEW_RAW_CLUSTER_PARAMETER_CANDIDATE" if full else "COREB_SOURCE_RECOVERY_EXHAUSTED_DEFINE_NEW_POLICY_OR_KEEP_HISTORICAL_ONLY"
    if not upstream_ok or not inputs_ok:
        status = "RAW_CLUSTER_PARAMETER_SWEEP_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C91_INPUTS"
    decision = pd.DataFrame([["upstream_25c90_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"], ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"], ["raw_rr125_rows", len(raw), ">0", "PASS" if len(raw)>0 else "FAIL"], ["top125_rows", len(top), 125, "PASS" if len(top)==125 else "FAIL"], ["full_raw_cluster_parameter_reconstruction", full, True, "PASS" if full else "BLOCKED"], ["coreb_live_evaluator_allowed", False, False, "PASS"], ["a002_used", False, False, "PASS"]], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([["B91-001", "raw_cluster_parameter_sweep", "OPEN" if not full else "REVIEW", "HARD", "No complete match found" if not full else "Candidate requires human review"], ["B91-002", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked"], ["B91-003", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 not used"]], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "upstream_25c90_ok": upstream_ok, "inputs_ok": inputs_ok, "raw_rr125_rows": int(len(raw)), "top125_rows": int(len(top)), "best_family": str(best.iloc[0]["family"]) if not best.empty else None, "best_gap_min": int(best.iloc[0]["gap_min"]) if not best.empty else None, "best_same_count_exact": int(best.iloc[0]["same_count_exact"]) if not best.empty else 0, "best_source_rule_count_exact": int(best.iloc[0]["source_rule_count_exact"]) if not best.empty else 0, "full_match_found": full, "coreb_historical_sot_report_allowed": True, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "source_recovery_approved": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": next_step}
    inv.to_csv(out/"25c91_input_inventory.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out/"25c91_cluster_parameter_sweep_summary.csv", index=False, encoding="utf-8-sig")
    detail_df.to_csv(out/"25c91_cluster_parameter_sweep_rows.csv", index=False, encoding="utf-8-sig")
    best.to_csv(out/"25c91_best_candidate_matrix.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out/"25c91_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out/"25c91_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out/"25c91_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C91 raw cluster parameter sweep audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Sweep summary", md(summary_df, 30), "", "## Decision matrix", md(decision), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- A002 not used", "- source recovery not approved", "- live/final/external actions remain OFF"])
    (out/"GOLD_V2_25C91_RAW_CLUSTER_PARAMETER_SWEEP_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs()/"gold_v2_25c91_raw_cluster_parameter_sweep_audit_only.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
