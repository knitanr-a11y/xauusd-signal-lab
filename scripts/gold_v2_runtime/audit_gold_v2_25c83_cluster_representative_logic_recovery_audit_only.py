#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C83 cluster representative logic recovery audit-only.

Audits whether CoreB top-ledger cluster representative logic can be recovered
from currently available local artifacts. A002 is not used.

No Discord, MT5, AI API, live hook, live evaluator, or final signal.
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

STEP = "25C83_CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c83_cluster_representative_logic_recovery_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUTS = {
    "summary_25c82": "25c82_summary.json",
    "raw": "rr125_raw_signal_ledger.csv",
    "top": "rr125_top_ledgers.csv",
    "selected": "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "final_sot": "gold_v2_13c_coreb_final_sot_rows.csv",
}

BASIC_RAW_GROUPS = [
    ["dataset", "entry_time", "policy"],
    ["dataset", "entry_time", "policy", "top_direction"],
    ["dataset", "entry_time", "policy", "rr_bucket"],
    ["dataset", "entry_time", "policy", "base_condition"],
    ["dataset", "entry_time", "policy", "added_filter_text"],
    ["dataset", "entry_time", "policy", "candidate_id"],
    ["dataset", "entry_time", "policy", "origin_id"],
    ["dataset", "entry_time", "policy", "base_condition", "added_filter_text"],
    ["dataset", "entry_time", "policy", "origin_id", "base_condition", "added_filter_text"],
]

REP_PROFIT_FUNCS = {
    "sum_raw_profit_r": "sum",
    "mean_raw_profit_r": "mean",
    "median_raw_profit_r": "median",
    "min_raw_profit_r": "min",
    "max_raw_profit_r": "max",
    "first_raw_profit_r": "first",
    "last_raw_profit_r": "last",
}


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


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(p: Path | None) -> pd.DataFrame:
    if p is None or not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def read_json(p: Path | None) -> dict[str, Any]:
    if p is None or not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
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


def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean_json(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def norm_time(s: pd.Series) -> pd.Series:
    t = pd.to_datetime(s, errors="coerce")
    out = t.dt.strftime("%Y-%m-%d %H:%M:%S")
    return out.fillna(s.astype(str).str.strip())


def norm_int(s: pd.Series) -> pd.Series:
    n = pd.to_numeric(s, errors="coerce")
    out = n.round(0).astype("Int64").astype(str)
    return out.where(n.notna(), s.astype(str).str.strip())


def norm_float(s: pd.Series, ndigits: int = 6) -> pd.Series:
    n = pd.to_numeric(s, errors="coerce")
    out = n.round(ndigits).map(lambda v: f"{v:.{ndigits}f}" if pd.notna(v) else "")
    return out.where(n.notna(), s.astype(str).str.strip())


def prep_common(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in ["dataset", "cluster_id", "top_candidate_id", "candidate_id", "origin_id", "same_count", "source_rule_count"]:
        if c in d.columns:
            d[c] = norm_int(d[c])
    if "entry_time" in d.columns:
        d["entry_time"] = norm_time(d["entry_time"])
    for c in ["profit", "profit_r", "coreb_profit_r"]:
        if c in d.columns:
            d[c] = norm_float(d[c], 6)
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].astype(str).str.strip()
    return d


def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows = []
    for label, p in paths.items():
        row: dict[str, Any] = {"label": label, "filename": INPUTS[label], "exists": bool(p and p.exists()), "path": str(p) if p else ""}
        if p and p.exists():
            row["bytes"] = p.stat().st_size
            row["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                try:
                    tmp = pd.read_csv(p, nrows=0)
                    row["columns"] = ";".join(tmp.columns)
                    row["row_count"] = len(pd.read_csv(p))
                except Exception as exc:
                    row["read_error"] = repr(exc)
        rows.append(row)
    return pd.DataFrame(rows)


def coreb_top(top: pd.DataFrame) -> pd.DataFrame:
    if top.empty:
        return top
    return top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()


def top_profile(top125: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in top125.columns:
        s = top125[c]
        rows.append({"column": c, "non_null": int(s.notna().sum()), "unique": int(s.nunique(dropna=True)), "sample_values": "; ".join(map(str, s.dropna().astype(str).head(5).tolist()))})
    return pd.DataFrame(rows)


def group_count_tests(raw: pd.DataFrame, top125: pd.DataFrame) -> pd.DataFrame:
    rawp = prep_common(raw)
    topp = prep_common(top125)
    rows = []
    if rawp.empty or topp.empty:
        return pd.DataFrame([{"test": "input_present", "status": "FAIL"}])
    for cols in BASIC_RAW_GROUPS:
        avail = [c for c in cols if c in rawp.columns and c in topp.columns]
        if avail != cols:
            continue
        counts = rawp.groupby(avail, dropna=False).size().reset_index(name="raw_group_count")
        joined = topp.merge(counts, on=avail, how="left")
        same_num = pd.to_numeric(joined.get("same_count"), errors="coerce") if "same_count" in joined.columns else pd.Series(dtype="float64")
        src_num = pd.to_numeric(joined.get("source_rule_count"), errors="coerce") if "source_rule_count" in joined.columns else pd.Series(dtype="float64")
        raw_num = pd.to_numeric(joined["raw_group_count"], errors="coerce")
        rows.append({
            "group_cols": "+".join(avail),
            "top_rows": len(topp),
            "matched_raw_groups": int(joined["raw_group_count"].notna().sum()),
            "same_count_exact": int((same_num == raw_num).sum()) if not same_num.empty else 0,
            "same_count_exact_ratio": float((same_num == raw_num).mean()) if len(joined) and not same_num.empty else 0.0,
            "source_rule_count_exact": int((src_num == raw_num).sum()) if not src_num.empty else 0,
            "source_rule_count_exact_ratio": float((src_num == raw_num).mean()) if len(joined) and not src_num.empty else 0.0,
            "status": "FULL" if (not same_num.empty and int((same_num == raw_num).sum()) == len(topp)) else "PARTIAL_OR_FAIL",
        })
    return pd.DataFrame(rows).sort_values(["same_count_exact", "source_rule_count_exact"], ascending=False)


def representative_profit_tests(raw: pd.DataFrame, top125: pd.DataFrame) -> pd.DataFrame:
    rawp = prep_common(raw)
    topp = prep_common(top125)
    rows = []
    if rawp.empty or topp.empty or "profit_r" not in rawp.columns or "profit" not in topp.columns:
        return pd.DataFrame([{"test": "input_present_or_profit_cols", "status": "FAIL"}])
    candidate_groups = [
        ["dataset", "entry_time", "policy"],
        ["dataset", "entry_time", "policy", "top_direction"],
        ["dataset", "entry_time", "policy", "rr_bucket"],
        ["dataset", "entry_time", "policy", "base_condition"],
        ["dataset", "entry_time", "policy", "added_filter_text"],
        ["dataset", "entry_time", "policy", "candidate_id"],
        ["dataset", "entry_time", "policy", "origin_id"],
        ["dataset", "entry_time", "policy", "base_condition", "added_filter_text"],
    ]
    rawp["profit_r_num"] = pd.to_numeric(rawp["profit_r"], errors="coerce")
    topp["profit_num"] = pd.to_numeric(topp["profit"], errors="coerce")
    for cols in candidate_groups:
        avail = [c for c in cols if c in rawp.columns and c in topp.columns]
        if avail != cols:
            continue
        for name, func in REP_PROFIT_FUNCS.items():
            agg = rawp.groupby(avail, dropna=False)["profit_r_num"].agg(func).reset_index(name="candidate_profit")
            joined = topp.merge(agg, on=avail, how="left")
            diff = (joined["profit_num"] - joined["candidate_profit"]).abs()
            rows.append({
                "group_cols": "+".join(avail),
                "candidate_rule": name,
                "top_rows": len(topp),
                "matched_groups": int(joined["candidate_profit"].notna().sum()),
                "profit_exact_1e6": int((diff <= 1e-6).sum()),
                "profit_exact_ratio": float((diff <= 1e-6).mean()) if len(joined) else 0.0,
                "max_abs_diff": float(diff.max()) if diff.notna().any() else None,
                "status": "FULL" if int((diff <= 1e-6).sum()) == len(topp) else "PARTIAL_OR_FAIL",
            })
    return pd.DataFrame(rows).sort_values(["profit_exact_1e6", "matched_groups"], ascending=False)


def raw_to_top_binding(raw: pd.DataFrame, top125: pd.DataFrame) -> pd.DataFrame:
    rawp = prep_common(raw)
    topp = prep_common(top125)
    if rawp.empty or topp.empty:
        return pd.DataFrame([{"binding": "input_present", "status": "FAIL"}])
    rows = []
    simple_keys = [
        ["dataset", "entry_time", "policy"],
        ["dataset", "entry_time", "policy", "base_condition", "added_filter_text"],
        ["dataset", "entry_time", "policy", "candidate_id"],
        ["dataset", "entry_time", "policy", "origin_id"],
    ]
    for cols in simple_keys:
        avail = [c for c in cols if c in rawp.columns and c in topp.columns]
        if avail != cols:
            continue
        raw_keys = rawp[avail].drop_duplicates()
        top_keys = topp[avail].drop_duplicates()
        joined = top_keys.merge(raw_keys, on=avail, how="inner")
        rows.append({"binding_key": "+".join(avail), "top_unique_keys": len(top_keys), "matched_raw_keys": len(joined), "status": "FULL_KEY_COVERAGE" if len(joined) == len(top_keys) else "PARTIAL"})
    return pd.DataFrame(rows)


def decision_matrix(same_tests: pd.DataFrame, profit_tests: pd.DataFrame) -> pd.DataFrame:
    same_full = (not same_tests.empty) and (same_tests.get("status", pd.Series(dtype=str)).astype(str).eq("FULL").any())
    profit_full = (not profit_tests.empty) and (profit_tests.get("status", pd.Series(dtype=str)).astype(str).eq("FULL").any())
    recovered = bool(same_full and profit_full)
    return pd.DataFrame([
        ["same_count_obvious_raw_group", same_full, "FULL_REQUIRED", "PASS" if same_full else "BLOCKED"],
        ["representative_profit_simple_rule", profit_full, "FULL_REQUIRED", "PASS" if profit_full else "BLOCKED"],
        ["cluster_representative_logic_recovered", recovered, True, "PASS" if recovered else "BLOCKED"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])


def blocker_matrix(recovered: bool) -> pd.DataFrame:
    rows = []
    if not recovered:
        rows.append(["B83-001", "cluster representative logic", "OPEN", "HARD", "No full source-backed raw->same_count/representative-profit rule recovered."])
    rows.extend([
        ["B83-002", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked until source-backed cluster representative logic is recovered."],
        ["B83-003", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is not used."],
        ["B83-004", "external actions", "OPEN", "SAFETY", "Discord/MT5/AI/live hook/final signal remain OFF."],
    ])
    return pd.DataFrame(rows, columns=["blocker_id", "component", "status", "severity", "detail"])


def md_table(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def report(summary: dict[str, Any], inv: pd.DataFrame, profile: pd.DataFrame, binding: pd.DataFrame, same_tests: pd.DataFrame, profit_tests: pd.DataFrame, decisions: pd.DataFrame, blockers: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 25C83 cluster representative logic recovery audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Decision",
        "",
        "CoreB historical SOT remains reportable, but live/future reconstruction remains blocked unless the raw->cluster representative generator is recovered.",
        "",
        "## Input inventory",
        md_table(inv, 20),
        "",
        "## Top 125 column profile",
        md_table(profile, 40),
        "",
        "## Raw to top key binding attempts",
        md_table(binding, 30),
        "",
        "## same_count/source_rule_count candidate tests",
        md_table(same_tests, 30),
        "",
        "## representative profit candidate tests",
        md_table(profit_tests, 30),
        "",
        "## Recovery decision matrix",
        md_table(decisions, 20),
        "",
        "## Blockers",
        md_table(blockers, 20),
        "",
        "## Safety",
        "",
        "- audit_only: true",
        "- A002 not used",
        "- Discord/MT5/AI/live_hook/final_signal: false",
    ])


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    paths = {k: find_file(v) for k, v in INPUTS.items()}
    inv = inventory(paths)
    s82 = read_json(paths["summary_25c82"])
    raw = read_csv(paths["raw"])
    top = read_csv(paths["top"])
    selected = read_csv(paths["selected"])

    top125 = coreb_top(top)
    profile = top_profile(top125)
    binding = raw_to_top_binding(raw, top125)
    same_tests = group_count_tests(raw, top125)
    profit_tests = representative_profit_tests(raw, top125)
    decisions = decision_matrix(same_tests, profit_tests)
    recovered = bool(decisions.loc[decisions["decision_item"].eq("cluster_representative_logic_recovered"), "observed"].iloc[0])
    blockers = blocker_matrix(recovered)

    upstream_ok = s82.get("status") == "LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_READY_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    top125_ok = len(top125) == 125
    selected_ok = len(selected) == 125

    status = "CLUSTER_REPRESENTATIVE_LOGIC_RECOVERED_AUDIT_ONLY_REVIEW_REQUIRED_BEFORE_LIVE" if recovered else "CLUSTER_REPRESENTATIVE_LOGIC_NOT_RECOVERED_AUDIT_ONLY_LIVE_BLOCKED"
    if not (upstream_ok and inputs_ok and top125_ok and selected_ok):
        status = "CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"

    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "upstream_25c82_ok": upstream_ok,
        "inputs_ok": inputs_ok,
        "top125_rows": int(len(top125)),
        "selected_rows": int(len(selected)),
        "same_count_full_rule_found": bool((same_tests.get("status", pd.Series(dtype=str)).astype(str) == "FULL").any()) if not same_tests.empty else False,
        "representative_profit_full_rule_found": bool((profit_tests.get("status", pd.Series(dtype=str)).astype(str) == "FULL").any()) if not profit_tests.empty else False,
        "cluster_representative_logic_recovered": recovered,
        "coreb_historical_sot_report_allowed": True,
        "coreb_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "a002_used": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": "REQUEST_ORIGINAL_CLUSTERING_SCRIPT_OR_MEMBERSHIP_LEDGER" if not recovered else "HUMAN_REVIEW_RECOVERED_CLUSTER_RULE_BEFORE_ANY_LIVE_STEP",
    }

    inv.to_csv(out / "25c83_input_inventory.csv", index=False, encoding="utf-8-sig")
    profile.to_csv(out / "25c83_top_row_column_profile.csv", index=False, encoding="utf-8-sig")
    binding.to_csv(out / "25c83_raw_to_top_binding_attempts.csv", index=False, encoding="utf-8-sig")
    same_tests.to_csv(out / "25c83_same_count_candidate_tests.csv", index=False, encoding="utf-8-sig")
    profit_tests.to_csv(out / "25c83_representative_profit_candidate_tests.csv", index=False, encoding="utf-8-sig")
    decisions.to_csv(out / "25c83_recovery_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c83_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c83_summary.json", summary)
    (out / "GOLD_V2_25C83_CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_AUDIT_ONLY_REPORT.md").write_text(report(summary, inv, profile, binding, same_tests, profit_tests, decisions, blockers), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c83_cluster_representative_logic_recovery_audit_only.zip"
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
