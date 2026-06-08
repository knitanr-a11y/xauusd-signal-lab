#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C88 source-universe filtered component reconstruction audit-only.

Builds interval connected components after filtering raw RR125 rows by identities
found in frozen_coreB_same_count_source_universe_20260604.json.

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

STEP = "25C88_SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c88_source_universe_filtered_component_reconstruction_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUT_NAMES = [
    "25c87_summary.json",
    "rr125_raw_signal_ledger.csv",
    "rr125_top_ledgers.csv",
    "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "frozen_coreB_same_count_source_universe_20260604.json",
]

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
    candidates = [repo_root() / "configs" / "gold_v2" / name, repo_root() / name, fx_outputs() / name]
    for c in candidates:
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


def collect_values(obj: Any) -> dict[str, set[str]]:
    keys = {"candidate_id": set(), "origin_id": set(), "variant": set(), "added_filter_text": set(), "rule_id": set()}

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k in list(keys):
                if k in x and x[k] is not None:
                    keys[k].add(str(x[k]).strip())
            for v in x.values():
                if isinstance(v, (list, dict)):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return keys


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["exit_dt"] = pd.to_datetime(d["exit_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit_r"), errors="coerce")
    for c in ["dataset", "policy", "direction", "candidate_id", "origin_id", "variant", "added_filter_text", "rr_bucket"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d


def prep_top(top: pd.DataFrame) -> pd.DataFrame:
    d = top.copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit"), errors="coerce")
    d["same_count_num"] = pd.to_numeric(d.get("same_count"), errors="coerce")
    d["source_rule_count_num"] = pd.to_numeric(d.get("source_rule_count"), errors="coerce")
    d["unique_origins_num"] = pd.to_numeric(d.get("unique_origins"), errors="coerce")
    for c in ["dataset", "policy", "top_direction", "rr_bucket", "top_candidate_id"]:
        if c in d.columns:
            d[c] = d[c].astype(str).str.strip()
    return d


def coreb_top(top: pd.DataFrame) -> pd.DataFrame:
    if top.empty:
        return top
    return top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()


def filter_raw(raw: pd.DataFrame, vals: dict[str, set[str]], mode: str) -> pd.DataFrame:
    r = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    if mode == "all_rr125_raw_baseline":
        return r
    mask = pd.Series(False, index=r.index)
    if "added_filter_text" in r.columns and vals["added_filter_text"]:
        m_filter = r["added_filter_text"].isin(vals["added_filter_text"])
    else:
        m_filter = pd.Series(False, index=r.index)
    if "candidate_id" in r.columns and vals["candidate_id"]:
        m_cand = r["candidate_id"].isin(vals["candidate_id"])
    else:
        m_cand = pd.Series(False, index=r.index)
    if "origin_id" in r.columns and vals["origin_id"]:
        m_orig = r["origin_id"].isin(vals["origin_id"])
    else:
        m_orig = pd.Series(False, index=r.index)
    if "variant" in r.columns and vals["variant"]:
        m_var = r["variant"].isin(vals["variant"])
    else:
        m_var = pd.Series(False, index=r.index)
    if mode == "added_filter_text_in_source_universe":
        mask = m_filter
    elif mode == "candidate_id_in_source_universe":
        mask = m_cand
    elif mode == "origin_id_in_source_universe":
        mask = m_orig
    elif mode == "variant_in_source_universe":
        mask = m_var
    elif mode == "candidate_or_origin_or_filter_in_source_universe":
        mask = m_filter | m_cand | m_orig
    elif mode == "candidate_and_filter_in_source_universe":
        mask = m_filter & m_cand
    elif mode == "origin_and_filter_in_source_universe":
        mask = m_filter & m_orig
    else:
        mask = pd.Series(True, index=r.index)
    return r[mask].copy()


def build_components(raw: pd.DataFrame) -> pd.DataFrame:
    frames = []
    if raw.empty:
        return pd.DataFrame()
    for (_, _), group in raw.groupby(["dataset", "direction"], dropna=False):
        g = group.sort_values(["entry_dt", "exit_dt"]).copy()
        cid = -1
        current_end = None
        cids = []
        for _, row in g.iterrows():
            if pd.isna(row["entry_dt"]):
                cids.append(None)
                continue
            if current_end is None or row["entry_dt"] > current_end:
                cid += 1
                current_end = row["exit_dt"]
            elif pd.notna(row["exit_dt"]) and row["exit_dt"] > current_end:
                current_end = row["exit_dt"]
            cids.append(cid)
        g["recon_component_id"] = cids
        frames.append(g)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def agg_profit(s: pd.Series, rule: str) -> float | None:
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


def evaluate_mode(mode: str, rawp: pd.DataFrame, topp: pd.DataFrame, vals: dict[str, set[str]]) -> tuple[dict[str, Any], pd.DataFrame]:
    filt = filter_raw(rawp, vals, mode)
    comp = build_components(filt)
    rows = []
    for _, tr in topp.iterrows():
        cover = comp[(comp["dataset"].astype(str).eq(str(tr["dataset"]))) & (comp["direction"].astype(str).eq(str(tr["top_direction"]))) & (comp["entry_dt"] <= tr["entry_dt"]) & (comp["exit_dt"] >= tr["entry_dt"])] if not comp.empty else pd.DataFrame()
        if cover.empty:
            rec = {"mode": mode, "dataset": tr.get("dataset"), "entry_time": tr.get("entry_time"), "cluster_id": tr.get("cluster_id"), "source_same_count": tr.get("same_count_num"), "recon_count": None, "recon_unique_origins": None, "same_count_match": False, "unique_origins_match": False}
        else:
            component_id = cover.iloc[0]["recon_component_id"]
            members = comp[(comp["dataset"].astype(str).eq(str(tr["dataset"]))) & (comp["direction"].astype(str).eq(str(tr["top_direction"]))) & (comp["recon_component_id"].eq(component_id))]
            rec = {"mode": mode, "dataset": tr.get("dataset"), "entry_time": tr.get("entry_time"), "cluster_id": tr.get("cluster_id"), "source_same_count": tr.get("same_count_num"), "recon_component_id": component_id, "recon_count": len(members), "recon_unique_origins": members["origin_id"].nunique(dropna=True) if "origin_id" in members.columns else None, "same_count_match": len(members) == int(tr["same_count_num"]) if pd.notna(tr["same_count_num"]) else False, "source_rule_count_match": len(members) == int(tr["source_rule_count_num"]) if pd.notna(tr["source_rule_count_num"]) else False, "unique_origins_match": (members["origin_id"].nunique(dropna=True) == int(tr["unique_origins_num"])) if "origin_id" in members.columns and pd.notna(tr["unique_origins_num"]) else False}
            for rule in PROFIT_RULES:
                val = agg_profit(members["profit_num"], rule)
                rec[f"profit_{rule}_match"] = abs(float(tr["profit_num"]) - val) <= 1e-6 if val is not None and pd.notna(tr["profit_num"]) else False
        rows.append(rec)
    df = pd.DataFrame(rows)
    summary = {"mode": mode, "filtered_raw_rows": len(filt), "component_rows": len(comp), "top_rows": len(topp), "covered_rows": int(df["recon_count"].notna().sum()) if "recon_count" in df.columns else 0, "same_count_exact": int(df["same_count_match"].sum()) if "same_count_match" in df.columns else 0, "source_rule_count_exact": int(df.get("source_rule_count_match", pd.Series(False)).sum()), "unique_origins_exact": int(df["unique_origins_match"].sum()) if "unique_origins_match" in df.columns else 0}
    for rule in PROFIT_RULES:
        col = f"profit_{rule}_match"
        summary[f"profit_{rule}_exact"] = int(df[col].sum()) if col in df.columns else 0
    summary["status"] = "FULL" if summary["same_count_exact"] == len(topp) or summary["source_rule_count_exact"] == len(topp) else "PARTIAL_OR_FAIL"
    return summary, df


def md(df: pd.DataFrame, max_rows: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    paths = {name: find_file(name) for name in INPUT_NAMES}
    inv = inventory(paths)
    s87 = read_json(paths["25c87_summary.json"])
    vals = collect_values(read_json(paths["frozen_coreB_same_count_source_universe_20260604.json"]))
    identity_summary = pd.DataFrame([[k, len(v), ";".join(sorted(list(v))[:10])] for k, v in vals.items()], columns=["identity", "unique_values", "sample_values"])
    rawp = prep_raw(read_csv(paths["rr125_raw_signal_ledger.csv"]))
    topp = prep_top(coreb_top(read_csv(paths["rr125_top_ledgers.csv"]))).sort_values(["dataset", "entry_dt", "cluster_id"]).reset_index(drop=True)
    modes = ["all_rr125_raw_baseline", "added_filter_text_in_source_universe", "candidate_id_in_source_universe", "origin_id_in_source_universe", "variant_in_source_universe", "candidate_or_origin_or_filter_in_source_universe", "candidate_and_filter_in_source_universe", "origin_and_filter_in_source_universe"]
    summaries = []
    detail_frames = []
    for mode in modes:
        sm, df = evaluate_mode(mode, rawp, topp, vals)
        summaries.append(sm)
        detail_frames.append(df)
    summary_df = pd.DataFrame(summaries).sort_values(["same_count_exact", "source_rule_count_exact", "unique_origins_exact"], ascending=False)
    detail_df = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    best = summary_df.head(1).copy()
    full = bool((summary_df["status"].astype(str) == "FULL").any()) if not summary_df.empty else False
    upstream_ok = s87.get("status") == "CONDITION_OBJECT_TIME_ALIGNMENT_REPLAY_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    if full:
        status = "SOURCE_UNIVERSE_FILTERED_COMPONENT_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
        next_step = "HUMAN_REVIEW_FILTERED_COMPONENT_CANDIDATE_BEFORE_ANY_LIVE"
    else:
        status = "SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
        next_step = "DEFINE_NEW_COREB_COMPATIBLE_POLICY_OR_STOP_LIVE_RECOVERY"
    if not upstream_ok or not inputs_ok:
        status = "SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C88_INPUTS"
    decision = pd.DataFrame([["upstream_25c87_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"], ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"], ["top125_rows", len(topp), 125, "PASS" if len(topp)==125 else "FAIL"], ["full_component_reconstruction", full, True, "PASS" if full else "BLOCKED"], ["coreb_live_evaluator_allowed", False, False, "PASS"], ["a002_used", False, False, "PASS"]], columns=["decision_item", "observed", "required", "status"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "upstream_25c87_ok": upstream_ok, "inputs_ok": inputs_ok, "top125_rows": int(len(topp)), "best_mode": str(best.iloc[0]["mode"]) if not best.empty else None, "best_same_count_exact": int(best.iloc[0]["same_count_exact"]) if not best.empty else 0, "best_source_rule_count_exact": int(best.iloc[0]["source_rule_count_exact"]) if not best.empty else 0, "full_match_found": full, "coreb_historical_sot_report_allowed": True, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "source_recovery_approved": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": next_step}
    inv.to_csv(out/"25c88_input_inventory.csv", index=False, encoding="utf-8-sig")
    identity_summary.to_csv(out/"25c88_source_universe_identity_summary.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out/"25c88_filtered_component_reconstruction_summary.csv", index=False, encoding="utf-8-sig")
    detail_df.to_csv(out/"25c88_filtered_component_reconstruction_rows.csv", index=False, encoding="utf-8-sig")
    best.to_csv(out/"25c88_best_candidate_matrix.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out/"25c88_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers = pd.DataFrame([["B88-001", "filtered_component_reconstruction", "OPEN" if not full else "REVIEW", "HARD", "No complete match found" if not full else "Candidate requires human review"], ["B88-002", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked"], ["B88-003", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 not used"]], columns=["blocker_id", "component", "status", "severity", "detail"])
    blockers.to_csv(out/"25c88_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out/"25c88_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C88 source-universe filtered component reconstruction audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Identity summary", md(identity_summary), "", "## Filtered component reconstruction summary", md(summary_df, 20), "", "## Decision matrix", md(decision), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- A002 not used", "- source recovery not approved", "- live/final/external actions remain OFF"])
    (out/"GOLD_V2_25C88_SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs()/"gold_v2_25c88_source_universe_filtered_component_reconstruction_audit_only.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
