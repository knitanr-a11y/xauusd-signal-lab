#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C84 deep cluster representative reconstruction audit-only.

Deeper reconstruction attempt after 25C83 showed simple grouping is insufficient.
A002 is not used. Partial matches are not promoted.

No Discord, MT5, AI API, live hook, live evaluator, or final signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

STEP = "25C84_DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c84_deep_cluster_representative_reconstruction_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUTS = {
    "summary_25c83": "25c83_summary.json",
    "raw": "rr125_raw_signal_ledger.csv",
    "top": "rr125_top_ledgers.csv",
    "selected": "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
}

WINDOW_MINUTES = [0, 5, 15, 30, 60, 120, 240, 720, 1440, 2880]
RAW_ID_COLS = ["candidate_id", "origin_id"]
REP_RULES = ["sum", "mean", "median", "min", "max", "first", "last"]
SEARCH_TERMS = ["rr125_top_ledgers", "same_count", "source_rule_count", "cluster_id", "top_candidate_id", "representative", "groupby", "connected_components"]


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


def find_file(filename: str) -> Path | None:
    base = fx_outputs()
    direct = base / filename
    if direct.exists():
        return direct
    if base.exists():
        found = sorted(base.rglob(filename))
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
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
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
    for label, p in paths.items():
        row: dict[str, Any] = {"label": label, "filename": INPUTS[label], "exists": bool(p and p.exists()), "path": str(p) if p else ""}
        if p and p.exists():
            row["bytes"] = p.stat().st_size
            row["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                try:
                    row["row_count"] = len(pd.read_csv(p))
                    row["columns"] = ";".join(pd.read_csv(p, nrows=0).columns)
                except Exception as exc:
                    row["read_error"] = repr(exc)
        rows.append(row)
    return pd.DataFrame(rows)


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit_r"), errors="coerce")
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].astype(str).str.strip()
    return d


def prep_top(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit"), errors="coerce")
    d["same_count_num"] = pd.to_numeric(d.get("same_count"), errors="coerce")
    d["source_rule_count_num"] = pd.to_numeric(d.get("source_rule_count"), errors="coerce")
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].astype(str).str.strip()
    return d


def coreb_top(top: pd.DataFrame) -> pd.DataFrame:
    if top.empty:
        return top
    return top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()


def subset_raw_for_top(raw: pd.DataFrame, top_row: pd.Series, window_min: int, id_mode: str) -> pd.DataFrame:
    r = raw[(raw["dataset"].astype(str) == str(top_row["dataset"])) & (raw["policy"].astype(str) == str(top_row["policy"]))].copy()
    if window_min == 0:
        r = r[r["entry_dt"].eq(top_row["entry_dt"])]
    else:
        lo = top_row["entry_dt"] - pd.Timedelta(minutes=window_min)
        hi = top_row["entry_dt"] + pd.Timedelta(minutes=window_min)
        r = r[(r["entry_dt"] >= lo) & (r["entry_dt"] <= hi)]
    if "rr_bucket" in r.columns and "rr_bucket" in top_row.index:
        # Keep RR bucket compatible but allow textual RR125/RR1.25 variance by numeric string ending.
        tv = str(top_row["rr_bucket"]).upper().replace("RR", "").replace(".", "")
        rrv = r["rr_bucket"].astype(str).str.upper().str.replace("RR", "", regex=False).str.replace(".", "", regex=False)
        r = r[rrv.eq(tv) | rrv.eq("125")]
    if id_mode == "top_candidate_to_candidate_id" and "candidate_id" in r.columns:
        r = r[r["candidate_id"].astype(str).eq(str(top_row.get("top_candidate_id")))]
    elif id_mode == "top_candidate_to_origin_id" and "origin_id" in r.columns:
        r = r[r["origin_id"].astype(str).eq(str(top_row.get("top_candidate_id")))]
    elif id_mode == "origin_candidate_any" and "candidate_id" in r.columns and "origin_id" in r.columns:
        tv = str(top_row.get("top_candidate_id"))
        r = r[r["candidate_id"].astype(str).eq(tv) | r["origin_id"].astype(str).eq(tv)]
    return r


def window_count_tests(raw: pd.DataFrame, top125: pd.DataFrame) -> pd.DataFrame:
    rawp = prep_raw(raw)
    topp = prep_top(top125)
    rows = []
    for window in WINDOW_MINUTES:
        for id_mode in ["none", "top_candidate_to_candidate_id", "top_candidate_to_origin_id", "origin_candidate_any"]:
            same_exact = 0
            source_exact = 0
            uniq_origin_exact = 0
            matched_nonzero = 0
            counts = []
            for _, tr in topp.iterrows():
                sub = subset_raw_for_top(rawp, tr, window, id_mode)
                cnt = len(sub)
                counts.append(cnt)
                if cnt > 0:
                    matched_nonzero += 1
                if pd.notna(tr.get("same_count_num")) and cnt == int(tr["same_count_num"]):
                    same_exact += 1
                if pd.notna(tr.get("source_rule_count_num")) and cnt == int(tr["source_rule_count_num"]):
                    source_exact += 1
                if "origin_id" in sub.columns and "unique_origins" in tr.index:
                    uo = sub["origin_id"].nunique(dropna=True)
                    if pd.notna(pd.to_numeric(tr.get("unique_origins"), errors="coerce")) and uo == int(float(tr.get("unique_origins"))):
                        uniq_origin_exact += 1
            rows.append({
                "window_min": window,
                "id_mode": id_mode,
                "matched_nonzero": matched_nonzero,
                "same_count_exact": same_exact,
                "same_count_exact_ratio": same_exact / len(topp) if len(topp) else 0.0,
                "source_rule_count_exact": source_exact,
                "source_rule_count_exact_ratio": source_exact / len(topp) if len(topp) else 0.0,
                "unique_origins_exact": uniq_origin_exact,
                "unique_origins_exact_ratio": uniq_origin_exact / len(topp) if len(topp) else 0.0,
                "min_count": min(counts) if counts else None,
                "max_count": max(counts) if counts else None,
                "status": "FULL" if same_exact == len(topp) and source_exact == len(topp) else "PARTIAL_OR_FAIL",
            })
    return pd.DataFrame(rows).sort_values(["same_count_exact", "source_rule_count_exact", "unique_origins_exact"], ascending=False)


def rep_value(series: pd.Series, rule: str) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return None
    if rule == "sum":
        return float(s.sum())
    if rule == "mean":
        return float(s.mean())
    if rule == "median":
        return float(s.median())
    if rule == "min":
        return float(s.min())
    if rule == "max":
        return float(s.max())
    if rule == "first":
        return float(s.iloc[0])
    if rule == "last":
        return float(s.iloc[-1])
    return None


def window_profit_tests(raw: pd.DataFrame, top125: pd.DataFrame) -> pd.DataFrame:
    rawp = prep_raw(raw)
    topp = prep_top(top125)
    rows = []
    for window in WINDOW_MINUTES:
        for id_mode in ["none", "top_candidate_to_candidate_id", "top_candidate_to_origin_id", "origin_candidate_any"]:
            for rule in REP_RULES:
                exact = 0
                matched = 0
                max_diff = 0.0
                for _, tr in topp.iterrows():
                    sub = subset_raw_for_top(rawp, tr, window, id_mode)
                    val = rep_value(sub.get("profit_num", pd.Series(dtype="float64")), rule)
                    if val is None:
                        continue
                    matched += 1
                    diff = abs(float(tr["profit_num"]) - val)
                    max_diff = max(max_diff, diff)
                    if diff <= 1e-6:
                        exact += 1
                rows.append({
                    "window_min": window,
                    "id_mode": id_mode,
                    "profit_rule": rule,
                    "matched": matched,
                    "profit_exact_1e6": exact,
                    "profit_exact_ratio": exact / len(topp) if len(topp) else 0.0,
                    "max_abs_diff": max_diff if matched else None,
                    "status": "FULL" if exact == len(topp) else "PARTIAL_OR_FAIL",
                })
    return pd.DataFrame(rows).sort_values(["profit_exact_1e6", "matched"], ascending=False)


def cluster_id_sequence_tests(top125: pd.DataFrame) -> pd.DataFrame:
    topp = prep_top(top125).sort_values(["dataset", "entry_dt", "cluster_id"]).copy()
    rows = []
    if topp.empty:
        return pd.DataFrame()
    cluster_num = pd.to_numeric(topp["cluster_id"], errors="coerce")
    dense_rank_all = pd.Series(range(1, len(topp) + 1), index=topp.index)
    dense_rank_by_dataset = topp.groupby("dataset").cumcount() + 1
    rows.append({"hypothesis": "cluster_id_equals_global_row_rank", "exact": int((cluster_num == dense_rank_all).sum()), "rows": len(topp), "ratio": float((cluster_num == dense_rank_all).mean())})
    rows.append({"hypothesis": "cluster_id_equals_dataset_row_rank", "exact": int((cluster_num == dense_rank_by_dataset).sum()), "rows": len(topp), "ratio": float((cluster_num == dense_rank_by_dataset).mean())})
    rows.append({"hypothesis": "cluster_id_unique_count", "exact": int(cluster_num.nunique(dropna=True)), "rows": len(topp), "ratio": float(cluster_num.nunique(dropna=True) / len(topp))})
    rows.append({"hypothesis": "cluster_id_monotonic_in_time", "exact": bool(cluster_num.is_monotonic_increasing), "rows": len(topp), "ratio": None})
    return pd.DataFrame(rows)


def keyword_scan() -> pd.DataFrame:
    root = repo_root()
    rows = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".py", ".md", ".json", ".bat"}:
            continue
        if OUT_DIR_NAME in str(p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        hits = {term: len(re.findall(re.escape(term), text, flags=re.IGNORECASE)) for term in SEARCH_TERMS}
        total = sum(hits.values())
        if total:
            rows.append({"path": str(p.relative_to(root)), "total_hits": total, **hits})
    return pd.DataFrame(rows).sort_values("total_hits", ascending=False).head(100) if rows else pd.DataFrame()


def best_summary(counts: pd.DataFrame, profits: pd.DataFrame, clusters: pd.DataFrame, scan: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if not counts.empty:
        rows.append({"category": "same_count/source_rule_count", **counts.iloc[0].to_dict()})
    if not profits.empty:
        rows.append({"category": "representative_profit", **profits.iloc[0].to_dict()})
    if not clusters.empty:
        rows.append({"category": "cluster_id_sequence", **clusters.iloc[0].to_dict()})
    if not scan.empty:
        rows.append({"category": "keyword_scan", **scan.iloc[0].to_dict()})
    return pd.DataFrame(rows)


def decision_matrix(counts: pd.DataFrame, profits: pd.DataFrame) -> pd.DataFrame:
    count_full = bool((counts.get("status", pd.Series(dtype=str)).astype(str) == "FULL").any()) if not counts.empty else False
    profit_full = bool((profits.get("status", pd.Series(dtype=str)).astype(str) == "FULL").any()) if not profits.empty else False
    recovered = count_full and profit_full
    return pd.DataFrame([
        ["time_window_same_count_or_source_rule_count_full", count_full, True, "PASS" if count_full else "BLOCKED"],
        ["time_window_representative_profit_full", profit_full, True, "PASS" if profit_full else "BLOCKED"],
        ["deep_cluster_representative_candidate_recovered", recovered, True, "PASS" if recovered else "BLOCKED"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])


def blocker_matrix(recovered: bool) -> pd.DataFrame:
    rows = []
    if not recovered:
        rows.append(["B84-001", "deep reconstruction", "OPEN", "HARD", "No full raw->same_count/source_rule_count and representative profit reconstruction candidate found."])
    rows.extend([
        ["B84-002", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked; historical SOT remains allowed."],
        ["B84-003", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 not used."],
        ["B84-004", "external actions", "OPEN", "SAFETY", "Discord/MT5/AI/live hook/final signal remain OFF."],
    ])
    return pd.DataFrame(rows, columns=["blocker_id", "component", "status", "severity", "detail"])


def md(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def report(summary: dict[str, Any], inv: pd.DataFrame, counts: pd.DataFrame, profits: pd.DataFrame, clusters: pd.DataFrame, scan: pd.DataFrame, best: pd.DataFrame, decisions: pd.DataFrame, blockers: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 25C84 deep cluster representative reconstruction audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Decision",
        "",
        "This is a reconstruction search only. Partial matches do not unblock live.",
        "",
        "## Input inventory",
        md(inv, 20),
        "",
        "## Best candidate summary",
        md(best, 20),
        "",
        "## Window count candidate tests",
        md(counts, 30),
        "",
        "## Window profit candidate tests",
        md(profits, 30),
        "",
        "## Cluster id sequence tests",
        md(clusters, 20),
        "",
        "## Logic keyword scan",
        md(scan, 30),
        "",
        "## Decision matrix",
        md(decisions, 20),
        "",
        "## Blockers",
        md(blockers, 20),
        "",
        "## Safety",
        "",
        "- audit_only: true",
        "- A002 not used",
        "- live/final/external actions: off",
    ])


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    paths = {k: find_file(v) for k, v in INPUTS.items()}
    inv = inventory(paths)
    s83 = read_json(paths["summary_25c83"])
    raw = read_csv(paths["raw"])
    top = read_csv(paths["top"])
    selected = read_csv(paths["selected"])
    top125 = coreb_top(top)

    counts = window_count_tests(raw, top125)
    profits = window_profit_tests(raw, top125)
    clusters = cluster_id_sequence_tests(top125)
    scan = keyword_scan()
    best = best_summary(counts, profits, clusters, scan)
    decisions = decision_matrix(counts, profits)
    recovered = bool(decisions.loc[decisions["decision_item"].eq("deep_cluster_representative_candidate_recovered"), "observed"].iloc[0])
    blockers = blocker_matrix(recovered)

    upstream_ok = s83.get("status") == "CLUSTER_REPRESENTATIVE_LOGIC_NOT_RECOVERED_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    status = "RECONSTRUCTION_CANDIDATE_FOUND_HUMAN_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED" if recovered else "DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_NOT_RECOVERED_AUDIT_ONLY_LIVE_BLOCKED"
    if not (upstream_ok and inputs_ok and len(top125) == 125 and len(selected) == 125):
        status = "DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"

    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "upstream_25c83_ok": upstream_ok,
        "inputs_ok": inputs_ok,
        "top125_rows": int(len(top125)),
        "selected_rows": int(len(selected)),
        "best_same_count_exact": int(counts.iloc[0].get("same_count_exact", 0)) if not counts.empty else 0,
        "best_source_rule_count_exact": int(counts.iloc[0].get("source_rule_count_exact", 0)) if not counts.empty else 0,
        "best_profit_exact": int(profits.iloc[0].get("profit_exact_1e6", 0)) if not profits.empty else 0,
        "deep_reconstruction_candidate_recovered": recovered,
        "coreb_historical_sot_report_allowed": True,
        "coreb_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "a002_used": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": "HUMAN_REVIEW_RECONSTRUCTION_CANDIDATE_BEFORE_ANY_LIVE" if recovered else "SOURCE_ARTIFACT_REQUIRED_OR_DEFINE_NEW_COREB_COMPATIBLE_POLICY",
    }

    inv.to_csv(out / "25c84_input_inventory.csv", index=False, encoding="utf-8-sig")
    counts.to_csv(out / "25c84_window_count_candidate_tests.csv", index=False, encoding="utf-8-sig")
    profits.to_csv(out / "25c84_window_profit_candidate_tests.csv", index=False, encoding="utf-8-sig")
    clusters.to_csv(out / "25c84_cluster_id_sequence_tests.csv", index=False, encoding="utf-8-sig")
    scan.to_csv(out / "25c84_logic_keyword_scan.csv", index=False, encoding="utf-8-sig")
    best.to_csv(out / "25c84_best_candidate_summary.csv", index=False, encoding="utf-8-sig")
    decisions.to_csv(out / "25c84_recovery_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c84_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c84_summary.json", summary)
    (out / "GOLD_V2_25C84_DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_AUDIT_ONLY_REPORT.md").write_text(report(summary, inv, counts, profits, clusters, scan, best, decisions, blockers), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c84_deep_cluster_representative_reconstruction_audit_only.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
