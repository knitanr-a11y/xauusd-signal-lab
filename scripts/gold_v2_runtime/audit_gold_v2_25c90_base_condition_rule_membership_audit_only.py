#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C90 base-condition rule membership audit-only.

Tests whether source-universe membership requires base_condition + added_filter_text
rather than added_filter_text/candidate/origin values alone.

A002 is not used. No live/final/external action is allowed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "25C90_BASE_CONDITION_RULE_MEMBERSHIP_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c90_base_condition_rule_membership_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUT_NAMES = [
    "25c89_summary.json",
    "rr125_raw_signal_ledger.csv",
    "rr125_top_ledgers.csv",
    "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "frozen_coreB_same_count_source_universe_20260604.json",
]

TUPLE_MODES = [
    ["base_condition_norm"],
    ["base_condition_norm", "added_filter_text_norm"],
    ["base_condition_norm", "candidate_id", "added_filter_text_norm"],
    ["base_condition_norm", "origin_id", "added_filter_text_norm"],
    ["base_condition_norm", "variant", "added_filter_text_norm"],
    ["base_condition_norm", "candidate_id", "origin_id", "variant", "added_filter_text_norm"],
]
COUNT_STYLES = ["same_entry", "interval_component"]
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
    for c in [repo_root() / "configs" / "gold_v2" / name, repo_root() / name, fx_outputs() / name]:
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


def norm(v: Any) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def norm_expr(s: Any) -> str:
    x = norm(s).lower()
    x = x.replace("&&", " and ").replace("&", " and ")
    x = re.sub(r"\s+and\s+", " and ", x)
    x = re.sub(r"\s*(<=|>=|==|<|>)\s*", r" \1 ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x


def cond_obj_to_expr(objs: Any) -> str:
    rows = []
    if isinstance(objs, dict):
        objs = [objs]
    if not isinstance(objs, list):
        return ""
    for o in objs:
        if not isinstance(o, dict):
            continue
        field = o.get("field") or o.get("feature")
        op = o.get("operator") or o.get("op")
        val = o.get("value") if "value" in o else o.get("threshold")
        if field is None or op is None or val is None:
            continue
        try:
            fv = float(val)
            val_s = f"{fv:.6g}"
        except Exception:
            val_s = norm(val)
        rows.append(f"{norm(field)} {norm(op)} {val_s}")
    return norm_expr(" and ".join(rows))


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


def source_rule_inventory(obj: dict[str, Any]) -> pd.DataFrame:
    rules = obj.get("source_universe_rules") or obj.get("rules") or []
    rows: list[dict[str, Any]] = []
    if isinstance(rules, dict):
        rules = list(rules.values())
    for i, r in enumerate(rules if isinstance(rules, list) else []):
        if not isinstance(r, dict):
            continue
        rows.append({
            "rule_id": norm(r.get("rule_id") or f"rule_{i:04d}"),
            "candidate_id": norm(r.get("candidate_id")),
            "origin_id": norm(r.get("origin_id")),
            "variant": norm(r.get("variant")),
            "base_condition_norm": cond_obj_to_expr(r.get("base_condition_objects") or r.get("base_condition") or r.get("base_conditions")),
            "added_filter_text_norm": norm_expr(r.get("added_filter_text")),
            "source_row_count": r.get("source_row_count"),
        })
    df = pd.DataFrame(rows)
    for c in ["rule_id", "candidate_id", "origin_id", "variant", "base_condition_norm", "added_filter_text_norm"]:
        if c not in df.columns:
            df[c] = ""
    return df.drop_duplicates().reset_index(drop=True)


def prep_raw(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.copy()
    d["entry_dt"] = pd.to_datetime(d["entry_time"], errors="coerce")
    d["exit_dt"] = pd.to_datetime(d["exit_time"], errors="coerce")
    d["profit_num"] = pd.to_numeric(d.get("profit_r"), errors="coerce")
    for c in ["dataset", "policy", "direction", "candidate_id", "origin_id", "variant", "rr_bucket"]:
        if c in d.columns:
            d[c] = d[c].map(norm)
    d["base_condition_norm"] = d["base_condition"].map(norm_expr) if "base_condition" in d.columns else ""
    d["added_filter_text_norm"] = d["added_filter_text"].map(norm_expr) if "added_filter_text" in d.columns else ""
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
            d[c] = d[c].map(norm)
    return d


def coreb_top(top: pd.DataFrame) -> pd.DataFrame:
    return top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy() if not top.empty else top


def tuple_filter_raw(raw: pd.DataFrame, rules: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    r = raw[raw["policy"].astype(str).eq("RR125_from_RR1_rules")].copy()
    if rules.empty or any(c not in rules.columns or c not in r.columns for c in cols):
        return r.iloc[0:0].copy()
    tuples = rules[cols].drop_duplicates().copy()
    tuples = tuples[~tuples.apply(lambda row: all(norm(v) == "" for v in row), axis=1)]
    # Require all selected columns non-empty to avoid broad NaN/blank tuple matching.
    for c in cols:
        tuples = tuples[tuples[c].astype(str).str.len() > 0]
    return r.merge(tuples, on=cols, how="inner")


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


def pval(s: pd.Series, rule: str) -> float | None:
    x = pd.to_numeric(s, errors="coerce").dropna()
    if x.empty:
        return None
    return {"sum": x.sum(), "mean": x.mean(), "median": x.median(), "min": x.min(), "max": x.max(), "first": x.iloc[0], "last": x.iloc[-1]}[rule]


def evaluate(mode: str, style: str, raw: pd.DataFrame, top: pd.DataFrame, rules: pd.DataFrame, cols: list[str]) -> tuple[dict[str, Any], pd.DataFrame]:
    filt = tuple_filter_raw(raw, rules, cols)
    comp = build_components(filt) if style == "interval_component" else filt
    rows = []
    for _, tr in top.iterrows():
        if style == "same_entry":
            members = filt[(filt["dataset"].astype(str).eq(str(tr["dataset"]))) & (filt["direction"].astype(str).eq(str(tr["top_direction"]))) & (filt["entry_dt"].eq(tr["entry_dt"]))]
        else:
            cover = comp[(comp["dataset"].astype(str).eq(str(tr["dataset"]))) & (comp["direction"].astype(str).eq(str(tr["top_direction"]))) & (comp["entry_dt"] <= tr["entry_dt"]) & (comp["exit_dt"] >= tr["entry_dt"])] if not comp.empty else pd.DataFrame()
            if cover.empty:
                members = comp.iloc[0:0].copy() if not comp.empty else pd.DataFrame()
            else:
                cid = cover.iloc[0]["recon_component_id"]
                members = comp[(comp["dataset"].astype(str).eq(str(tr["dataset"]))) & (comp["direction"].astype(str).eq(str(tr["top_direction"]))) & (comp["recon_component_id"].eq(cid))]
        rec = {"mode": mode, "style": style, "dataset": tr.get("dataset"), "entry_time": tr.get("entry_time"), "cluster_id": tr.get("cluster_id"), "recon_count": len(members), "source_same_count": tr.get("same_count_num"), "source_rule_count": tr.get("source_rule_count_num"), "recon_unique_origins": members["origin_id"].nunique(dropna=True) if "origin_id" in members.columns else 0}
        rec["same_count_match"] = len(members) == int(tr["same_count_num"]) if pd.notna(tr["same_count_num"]) else False
        rec["source_rule_count_match"] = len(members) == int(tr["source_rule_count_num"]) if pd.notna(tr["source_rule_count_num"]) else False
        rec["unique_origins_match"] = rec["recon_unique_origins"] == int(tr["unique_origins_num"]) if pd.notna(tr["unique_origins_num"]) else False
        for pr in PROFIT_RULES:
            val = pval(members["profit_num"], pr) if "profit_num" in members.columns and len(members) else None
            rec[f"profit_{pr}_match"] = abs(float(tr["profit_num"]) - float(val)) <= 1e-6 if val is not None and pd.notna(tr["profit_num"]) else False
        rows.append(rec)
    df = pd.DataFrame(rows)
    sm = {"mode": mode, "style": style, "tuple_cols": ";".join(cols), "rule_tuple_count": int(rules[cols].drop_duplicates().shape[0]) if all(c in rules.columns for c in cols) else 0, "filtered_raw_rows": int(len(filt)), "top_rows": int(len(top)), "covered_rows": int((df["recon_count"] > 0).sum()) if not df.empty else 0, "same_count_exact": int(df["same_count_match"].sum()), "source_rule_count_exact": int(df["source_rule_count_match"].sum()), "unique_origins_exact": int(df["unique_origins_match"].sum())}
    for pr in PROFIT_RULES:
        col = f"profit_{pr}_match"
        sm[f"profit_{pr}_exact"] = int(df[col].sum())
    sm["status"] = "FULL" if sm["same_count_exact"] == len(top) or sm["source_rule_count_exact"] == len(top) else "PARTIAL_OR_FAIL"
    return sm, df


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty:
        return "_No rows._"
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
    s89 = read_json(paths["25c89_summary.json"])
    rules = source_rule_inventory(read_json(paths["frozen_coreB_same_count_source_universe_20260604.json"]))
    raw = prep_raw(read_csv(paths["rr125_raw_signal_ledger.csv"]))
    top = prep_top(coreb_top(read_csv(paths["rr125_top_ledgers.csv"]))).sort_values(["dataset", "entry_dt", "cluster_id"]).reset_index(drop=True)
    summaries = []
    details = []
    for cols in TUPLE_MODES:
        mode = "+".join(cols)
        for style in COUNT_STYLES:
            sm, df = evaluate(mode, style, raw, top, rules, cols)
            summaries.append(sm)
            details.append(df)
    summary_df = pd.DataFrame(summaries).sort_values(["same_count_exact", "source_rule_count_exact", "unique_origins_exact"], ascending=False)
    detail_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    best = summary_df.head(1).copy()
    full = bool((summary_df["status"].astype(str) == "FULL").any()) if not summary_df.empty else False
    upstream_ok = s89.get("status") == "SOURCE_UNIVERSE_RULE_TUPLE_MEMBERSHIP_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    status = "BASE_CONDITION_RULE_MEMBERSHIP_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED" if full else "BASE_CONDITION_RULE_MEMBERSHIP_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    next_step = "HUMAN_REVIEW_BASE_CONDITION_MEMBERSHIP_CANDIDATE" if full else "REVIEW_NORMALIZATION_OR_STOP_SOURCE_RECOVERY_AND_DEFINE_NEW_POLICY"
    if not upstream_ok or not inputs_ok:
        status = "BASE_CONDITION_RULE_MEMBERSHIP_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C90_INPUTS"
    decision = pd.DataFrame([["upstream_25c89_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"], ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"], ["source_rule_rows", len(rules), ">0", "PASS" if len(rules)>0 else "FAIL"], ["top125_rows", len(top), 125, "PASS" if len(top)==125 else "FAIL"], ["full_base_condition_membership_reconstruction", full, True, "PASS" if full else "BLOCKED"], ["coreb_live_evaluator_allowed", False, False, "PASS"], ["a002_used", False, False, "PASS"]], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([["B90-001", "base_condition_membership", "OPEN" if not full else "REVIEW", "HARD", "No complete match found" if not full else "Candidate requires human review"], ["B90-002", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked"], ["B90-003", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 not used"]], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "upstream_25c89_ok": upstream_ok, "inputs_ok": inputs_ok, "source_rule_rows": int(len(rules)), "top125_rows": int(len(top)), "best_mode": str(best.iloc[0]["mode"]) if not best.empty else None, "best_style": str(best.iloc[0]["style"]) if not best.empty else None, "best_same_count_exact": int(best.iloc[0]["same_count_exact"]) if not best.empty else 0, "best_source_rule_count_exact": int(best.iloc[0]["source_rule_count_exact"]) if not best.empty else 0, "full_match_found": full, "coreb_historical_sot_report_allowed": True, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "source_recovery_approved": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": next_step}
    inv.to_csv(out/"25c90_input_inventory.csv", index=False, encoding="utf-8-sig")
    rules.to_csv(out/"25c90_source_rule_base_condition_inventory.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(out/"25c90_reconstruction_summary.csv", index=False, encoding="utf-8-sig")
    detail_df.to_csv(out/"25c90_reconstruction_rows.csv", index=False, encoding="utf-8-sig")
    best.to_csv(out/"25c90_best_candidate_matrix.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out/"25c90_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out/"25c90_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out/"25c90_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C90 base-condition rule membership audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Reconstruction summary", md(summary_df, 30), "", "## Decision matrix", md(decision), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- A002 not used", "- source recovery not approved", "- live/final/external actions remain OFF"])
    (out/"GOLD_V2_25C90_BASE_CONDITION_RULE_MEMBERSHIP_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs()/"gold_v2_25c90_base_condition_rule_membership_audit_only.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
