#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C92 nearby component oracle boundary audit-only.

For each CoreB top row, searches nearby reconstructed raw components and checks
whether any nearby component has the historical same_count/source_rule_count.
This is an oracle boundary test and not deployable live logic.

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

STEP = "25C92_NEARBY_COMPONENT_ORACLE_BOUNDARY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c92_nearby_component_oracle_boundary_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUT_NAMES = ["25c91_summary.json", "rr125_raw_signal_ledger.csv", "rr125_top_ledgers.csv", "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv"]
GAPS_MIN = [5, 15, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440, 2880]
FAMILIES = ["entry_gap", "interval_gap", "calendar_bucket"]
NEARBY_MIN = [0, 15, 30, 60, 120, 240, 720, 1440]


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
        row = {"filename": name, "exists": bool(path and path.exists()), "path": str(path) if path else ""}
        if path and path.exists():
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
            if path.suffix.lower() == ".csv":
                row["row_count"] = len(pd.read_csv(path))
                row["columns"] = ";".join(pd.read_csv(path, nrows=0).columns)
        rows.append(row)
    return pd.DataFrame(rows)


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["exit_dt"] = pd.to_datetime(d["exit_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit_r"), errors="coerce")
    for c in ["dataset", "direction", "origin_id"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d.sort_values(["dataset", "direction", "entry_dt", "exit_dt"]).reset_index(drop=True)


def prep_top(top: pd.DataFrame) -> pd.DataFrame:
    d = top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["same_count_num"] = pd.to_numeric(d.get("same_count"), errors="coerce")
    d["source_rule_count_num"] = pd.to_numeric(d.get("source_rule_count"), errors="coerce")
    d["unique_origins_num"] = pd.to_numeric(d.get("unique_origins"), errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit"), errors="coerce")
    for c in ["dataset", "top_direction"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d.sort_values(["dataset", "entry_dt", "cluster_id"]).reset_index(drop=True)


def assign_clusters(raw: pd.DataFrame, family: str, gap_min: int) -> pd.DataFrame:
    frames = []
    gap = pd.Timedelta(minutes=gap_min)
    for (_, _), group in raw.groupby(["dataset", "direction"], dropna=False):
        g = group.sort_values(["entry_dt", "exit_dt"]).copy()
        cid = -1
        prev_entry = None
        current_end = None
        cids = []
        for _, row in g.iterrows():
            entry = row["entry_dt"]
            exit_ = row["exit_dt"]
            if family == "calendar_bucket":
                cid_val = int(entry.value // (60 * 10**9)) // gap_min if pd.notna(entry) else None
                cids.append(cid_val)
                continue
            if cid < 0 or pd.isna(entry):
                new_cluster = True
            elif family == "entry_gap":
                new_cluster = (entry - prev_entry) > gap
            else:
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


def component_table(comp: pd.DataFrame) -> pd.DataFrame:
    if comp.empty:
        return pd.DataFrame()
    return comp.groupby(["dataset", "direction", "recon_cluster_id"], dropna=False).agg(
        component_count=("entry_time", "size"),
        component_unique_origins=("origin_id", "nunique"),
        component_min_entry=("entry_dt", "min"),
        component_max_entry=("entry_dt", "max"),
        component_min_exit=("exit_dt", "min"),
        component_max_exit=("exit_dt", "max"),
        component_profit_sum=("profit_num", "sum"),
        component_profit_mean=("profit_num", "mean"),
        component_profit_min=("profit_num", "min"),
        component_profit_max=("profit_num", "max"),
    ).reset_index()


def evaluate_components(ct: pd.DataFrame, top: pd.DataFrame, family: str, gap: int, nearby: int) -> tuple[dict[str, Any], pd.DataFrame]:
    rows = []
    delta = pd.Timedelta(minutes=nearby)
    for _, tr in top.iterrows():
        cands = ct[(ct["dataset"].astype(str).eq(str(tr["dataset"]))) & (ct["direction"].astype(str).eq(str(tr["top_direction"])))].copy() if not ct.empty else pd.DataFrame()
        if not cands.empty:
            cands["distance_min"] = (cands["component_min_entry"] - tr["entry_dt"]).abs().dt.total_seconds() / 60.0
            if nearby == 0:
                nearby_cands = cands[(cands["component_min_entry"] <= tr["entry_dt"]) & (cands["component_max_exit"] >= tr["entry_dt"])]
            else:
                nearby_cands = cands[(cands["component_min_entry"] <= tr["entry_dt"] + delta) & (cands["component_max_exit"] >= tr["entry_dt"] - delta)]
        else:
            nearby_cands = pd.DataFrame()
        cnt_match = src_match = uniq_match = profit_sum_match = False
        best_distance = None
        matched_component_count = None
        if not nearby_cands.empty:
            cnt_match = bool((nearby_cands["component_count"].astype(float) == float(tr["same_count_num"])).any())
            src_match = bool((nearby_cands["component_count"].astype(float) == float(tr["source_rule_count_num"])).any())
            uniq_match = bool((nearby_cands["component_unique_origins"].astype(float) == float(tr["unique_origins_num"])).any())
            profit_sum_match = bool((nearby_cands["component_profit_sum"].astype(float).round(6) == round(float(tr["profit_num"]), 6)).any())
            if cnt_match:
                matched = nearby_cands[nearby_cands["component_count"].astype(float) == float(tr["same_count_num"])].sort_values("distance_min").iloc[0]
            else:
                matched = nearby_cands.sort_values("distance_min").iloc[0]
            best_distance = float(matched["distance_min"])
            matched_component_count = int(matched["component_count"])
        rows.append({"family": family, "gap_min": gap, "nearby_min": nearby, "dataset": tr.get("dataset"), "entry_time": tr.get("entry_time"), "cluster_id": tr.get("cluster_id"), "nearby_component_count": len(nearby_cands), "same_count_oracle_match": cnt_match, "source_rule_count_oracle_match": src_match, "unique_origins_oracle_match": uniq_match, "profit_sum_oracle_match": profit_sum_match, "nearest_distance_min": best_distance, "nearest_or_matched_component_count": matched_component_count, "source_same_count": tr.get("same_count_num")})
    df = pd.DataFrame(rows)
    sm = {"family": family, "gap_min": gap, "nearby_min": nearby, "top_rows": len(top), "same_count_oracle_exact": int(df["same_count_oracle_match"].sum()), "source_rule_count_oracle_exact": int(df["source_rule_count_oracle_match"].sum()), "unique_origins_oracle_exact": int(df["unique_origins_oracle_match"].sum()), "profit_sum_oracle_exact": int(df["profit_sum_oracle_match"].sum()), "avg_nearby_components": float(df["nearby_component_count"].mean()) if len(df) else None}
    sm["status"] = "FULL_ORACLE" if sm["same_count_oracle_exact"] == len(top) or sm["source_rule_count_oracle_exact"] == len(top) else "PARTIAL_OR_FAIL"
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
    s91 = read_json(paths["25c91_summary.json"])
    raw = prep_raw(read_csv(paths["rr125_raw_signal_ledger.csv"]))
    top = prep_top(read_csv(paths["rr125_top_ledgers.csv"]))
    summaries = []
    details = []
    for family in FAMILIES:
        for gap in GAPS_MIN:
            ct = component_table(assign_clusters(raw, family, gap))
            for nearby in NEARBY_MIN:
                sm, df = evaluate_components(ct, top, family, gap, nearby)
                summaries.append(sm)
                details.append(df)
    summary_df = pd.DataFrame(summaries).sort_values(["same_count_oracle_exact", "source_rule_count_oracle_exact", "unique_origins_oracle_exact"], ascending=False)
    detail_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    best = summary_df.head(1).copy()
    full_oracle = bool((summary_df["status"].astype(str) == "FULL_ORACLE").any()) if not summary_df.empty else False
    upstream_ok = s91.get("status") == "RAW_CLUSTER_PARAMETER_SWEEP_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    status = "NEARBY_COMPONENT_ORACLE_FULL_COUNT_FOUND_AUDIT_ONLY_NOT_LIVE_LOGIC" if full_oracle else "NEARBY_COMPONENT_ORACLE_BOUNDARY_NOT_FULL_AUDIT_ONLY_LIVE_BLOCKED"
    next_step = "DERIVE_NON_ORACLE_ASSOCIATION_RULE_HUMAN_REVIEW_REQUIRED" if full_oracle else "RAW_ONLY_COMPONENT_RECONSTRUCTION_BOUNDARY_EXHAUSTED_HISTORICAL_ONLY_OR_NEW_POLICY"
    if not upstream_ok or not inputs_ok:
        status = "NEARBY_COMPONENT_ORACLE_BOUNDARY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C92_INPUTS"
    decision = pd.DataFrame([["upstream_25c91_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"], ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"], ["raw_rr125_rows", len(raw), ">0", "PASS" if len(raw)>0 else "FAIL"], ["top125_rows", len(top), 125, "PASS" if len(top)==125 else "FAIL"], ["full_oracle_count_available", full_oracle, "diagnostic_only", "FOUND" if full_oracle else "NOT_FOUND"], ["coreb_live_evaluator_allowed", False, False, "PASS"], ["a002_used", False, False, "PASS"]], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([["B92-001", "non_oracle_cluster_logic", "OPEN", "HARD", "Oracle search is not deployable live logic"], ["B92-002", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked"], ["B92-003", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 not used"]], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "upstream_25c91_ok": upstream_ok, "inputs_ok": inputs_ok, "raw_rr125_rows": int(len(raw)), "top125_rows": int(len(top)), "best_family": str(best.iloc[0]["family"]) if not best.empty else None, "best_gap_min": int(best.iloc[0]["gap_min"]) if not best.empty else None, "best_nearby_min": int(best.iloc[0]["nearby_min"]) if not best.empty else None, "best_same_count_oracle_exact": int(best.iloc[0]["same_count_oracle_exact"]) if not best.empty else 0, "best_source_rule_count_oracle_exact": int(best.iloc[0]["source_rule_count_oracle_exact"]) if not best.empty else 0, "full_oracle_match_found": full_oracle, "coreb_historical_sot_report_allowed": True, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "source_recovery_approved": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": next_step}
    inv.to_csv(out/"25c92_input_inventory.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out/"25c92_nearby_component_oracle_summary.csv", index=False, encoding="utf-8-sig")
    detail_df.to_csv(out/"25c92_nearby_component_oracle_rows.csv", index=False, encoding="utf-8-sig")
    best.to_csv(out/"25c92_best_candidate_matrix.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out/"25c92_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out/"25c92_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out/"25c92_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C92 nearby component oracle boundary audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Oracle summary", md(summary_df, 30), "", "## Decision matrix", md(decision), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- oracle matching is not live logic", "- A002 not used", "- source recovery not approved", "- live/final/external actions remain OFF"])
    (out/"GOLD_V2_25C92_NEARBY_COMPONENT_ORACLE_BOUNDARY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs()/"gold_v2_25c92_nearby_component_oracle_boundary_audit_only.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.startswith("NEARBY_COMPONENT") else 2


if __name__ == "__main__":
    raise SystemExit(main())
